"""从 Obsidian markdown 表格加载持仓配置（支持多格式）"""

import os
import re
from typing import Optional

# 持仓配置目录
VAULT_DIR = os.path.expanduser("~/Research/Vault_基金经理Agent")
DEFAULT_PORTFOLIO_PATH = os.path.join(VAULT_DIR, "润铭.md")


def _auto_detect_columns(first_line: str) -> dict:
    """
    根据表头行自动判断格式，返回列名到索引的映射。
    支持：
    - 润铭格式：| Ticker | Name | 润铭 | ...
    - CIF 格式：| iFind Ticker | 中文名称 | Weight | ...
    """
    # 清理：去掉首尾 | 并分割
    cols = [c.strip() for c in first_line.strip().strip("|").split("|")]
    mapping = {}

    for i, col in enumerate(cols):
        col_lower = col.lower()
        if col_lower in ("ticker", "ifind ticker"):
            mapping["ticker"] = i
        elif col_lower in ("name", "中文名称"):
            mapping["name"] = i
        elif col_lower in ("润铭", "weight"):
            mapping["weight"] = i

    return mapping


def _infer_portfolio_name(path: str) -> str:
    """从文件路径推断组合名称（去掉 .md 后缀）"""
    name = os.path.splitext(os.path.basename(path))[0]
    # 进一步清理数字前缀（如有）
    name = re.sub(r"^\d+_", "", name)
    return name


def get_all_portfolios() -> list[dict]:
    """扫描 Vault 目录，返回所有可用组合列表"""
    portfolios = []
    if not os.path.isdir(VAULT_DIR):
        return portfolios
    for fname in os.listdir(VAULT_DIR):
        if fname.endswith(".md") and not fname.startswith("0"):
            path = os.path.join(VAULT_DIR, fname)
            name = _infer_portfolio_name(path)
            portfolios.append({"name": name, "path": path})
    return portfolios


def _is_header_line(line: str) -> bool:
    """判断是否为表头行（包含列名关键词）"""
    lower = line.lower()
    return any(kw in lower for kw in ("ticker", "润铭", "weight", "中文名称", "name"))


def _is_separator_line(line: str) -> bool:
    """判断是否为分隔线行（包含 ---）"""
    return "---" in line


def load_portfolio_config(path: Optional[str] = None) -> list[dict]:
    """
    解析 Obsidian markdown 表格格式的持仓配置文件。

    自动跳过表头行和分隔线，统一按列 1=Ticker, 2=Name, 3=Weight 解析。
    支持润铭格式和 CIF 格式（都是 3 列表格，只是列名不同）。
    """
    config_path = path or DEFAULT_PORTFOLIO_PATH

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"持仓配置文件不存在：{config_path}\n"
            "请确认文件路径是否正确。"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    holdings = []

    for line in content.split("\n"):
        line = line.strip()
        # 跳过空行、markdown 标题行、非表格行
        if not line or line.startswith("#") or not line.startswith("|"):
            continue
        # 跳过分隔线
        if _is_separator_line(line):
            continue
        # 跳过表头行
        if _is_header_line(line):
            continue

        # 解析数据行（列 1=Ticker, 2=Name, 3=Weight）
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue

        ticker = parts[1]
        name = parts[2]
        pct_str = parts[3].replace("%", "").strip()

        if not ticker or not name:
            continue

        try:
            position_pct = float(pct_str) if pct_str else 0.0
        except ValueError:
            position_pct = 0.0

        holdings.append({
            "code": ticker,
            "name": name,
            "cost": 0.0,
            "position_pct": position_pct,
            "alerts": _default_alerts(),
        })

    if not holdings:
        raise ValueError(f"持仓配置为空或格式错误：{config_path}")

    return holdings


def _default_alerts() -> dict:
    """默认告警配置（可按需调整）"""
    return {
        "price_drop_pct": 5,       # 跌幅 >5% 告警
        "price_rise_pct": 5,       # 涨幅 >5% 告警
        "volume_spike": 2.0,        # 成交量放大超过平日 X 倍
        "negative_news": True,      # 负面新闻即告警
        "new_announcement": True,   # 24小时内新公告即告警
        "esg_downgrade": False,
        "analyst_downgrade": True,
        "large_shareholder_reduce": True,
    }


def get_holding_by_code(code: str, path: Optional[str] = None) -> Optional[dict]:
    """根据股票代码查找单条持仓配置"""
    holdings = load_portfolio_config(path)
    for h in holdings:
        if h["code"] == code:
            return h
    return None


def get_all_codes(path: Optional[str] = None) -> list[str]:
    """获取所有持仓代码"""
    holdings = load_portfolio_config(path)
    return [h["code"] for h in holdings]


def get_portfolio_name(path: str) -> str:
    """从文件路径推断组合名称"""
    return _infer_portfolio_name(path)
