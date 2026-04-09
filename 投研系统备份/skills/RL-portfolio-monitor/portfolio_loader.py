"""从 Obsidian markdown 表格加载持仓配置"""

import os
import re
from typing import Optional

# 持仓配置路径
DEFAULT_PORTFOLIO_PATH = os.path.expanduser(
    "~/Research/Vault_基金经理Agent/润铭.md"
)


def load_portfolio_config(path: Optional[str] = None) -> list[dict]:
    """
    解析 Obsidian markdown 表格格式的持仓配置文件。

    表格格式：
    | Ticker | Name | 润铭 |
    | 920438.BJ | 戈碧迦 | 15.79% |
    ...

    第一列为 Ticker（股票代码）
    第二列为 Name（公司简称）
    第三列为 润铭（组合占比 %）
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

    # 解析 markdown 表格（跳过表头和分隔线）
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        # 跳过表头行、分隔线、空行
        if not line or line.startswith("| Ticker") or line.startswith("| ---"):
            continue
        # 跳过末尾文件夹引用行（如果有）
        if "基金经理agent持仓润铭" in line or "基金经理agen" in line:
            continue

        # 解析表格行：| 920438.BJ | 戈碧迦 | 15.79% |
        parts = [p.strip() for p in line.split("|")]
        # parts[0] 是空字符串，parts[1]=Ticker，parts[2]=Name，parts[3]=占比，parts[4]可能为空
        if len(parts) >= 4:
            ticker = parts[1].strip()
            name = parts[2].strip()
            pct_str = parts[3].strip().replace("%", "").strip()

            if not ticker or not name or ticker == "Ticker":
                continue

            try:
                position_pct = float(pct_str) if pct_str else 0.0
            except ValueError:
                position_pct = 0.0

            # 推断成本：表格中没有，用 0 占位（成本非必须，用于参考）
            holdings.append({
                "code": ticker,
                "name": name,
                "cost": 0.0,  # 表格中无成本数据
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
