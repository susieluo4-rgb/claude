#!/usr/bin/env python3
"""
持仓监控主脚本 — 编排层

功能：
- 加载 Obsidian 持仓配置
- 并发查询 ifind MCP（行情/新闻/事件/股东/ESG/风险）
- 独立判断每类告警类型
- 写入 SQLite 历史记录
- 推送飞书通知
"""

import sys
import os
import json
import argparse
import subprocess
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

# 确保导入路径正确
sys.path.insert(0, os.path.dirname(__file__))

from portfolio_loader import load_portfolio_config, get_holding_by_code
from alert_history import (
    insert_alert,
    was_alerted_today,
    query_history,
    get_alert_summary,
    get_unsent_alerts,
)
from feishu_formatter import (
    format_single_alert,
    format_summary,
    format_history_table,
)

# ============================================================================
# ifind API 调用（通过 call-node.js 直接请求 ifind API，不走 MCP）
# ============================================================================

IFIND_CALL_NODE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "Research", "ifind mcp&skill", "call-node.js"
)


def call_ifind_api(server_type: str, tool_name: str, query: str) -> dict:
    """
    通过 call-node.js 调用 ifind API。
    server_type: 'stock' | 'news' | 'edb' | 'fund'
    tool_name: MCP 工具名（如 'get_stock_performance'）
    query: 查询字符串
    """
    script = f"""
const {{ call }} = require('{IFIND_CALL_NODE}');
(async () => {{
    const result = await call('{server_type}', '{tool_name}', {{ query: '{query}' }});
    console.log(JSON.stringify(result, null, 2));
}})().catch(e => {{ console.error(e.message); process.exit(1); }});
"""
    try:
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return {}
        return json.loads(result.stdout)
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        return {}


# ============================================================================
# 各类型告警判断函数（独立）
# ============================================================================

def check_price_alerts(holding: dict, recent_perf: dict) -> list[dict]:
    """检查价格涨跌幅告警"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not recent_perf:
        return alerts

    change_pct = recent_perf.get("change_pct", 0)  # 涨跌幅 %

    # 跌幅告警
    drop_threshold = alerts_cfg.get("price_drop_pct")
    if drop_threshold and change_pct < 0 and abs(change_pct) >= drop_threshold:
        if not was_alerted_today(code, "PRICE_DROP"):
            trigger = abs(change_pct)
            alerts.append({
                "type": "PRICE_DROP",
                "trigger_value": -trigger,
                "threshold_value": drop_threshold,
                "headline": f"当前价 {recent_perf.get('price', 'N/A')} 元（较昨日 {change_pct:+.2f}%）",
            })

    # 涨幅告警
    rise_threshold = alerts_cfg.get("price_rise_pct")
    if rise_threshold and change_pct > 0 and change_pct >= rise_threshold:
        if not was_alerted_today(code, "PRICE_RISE"):
            alerts.append({
                "type": "PRICE_RISE",
                "trigger_value": change_pct,
                "threshold_value": rise_threshold,
                "headline": f"当前价 {recent_perf.get('price', 'N/A')} 元（较昨日 {change_pct:+.2f}%）",
            })

    return alerts


def check_volume_spike(holding: dict, recent_perf: dict) -> list[dict]:
    """检查成交量放大告警"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not recent_perf:
        return alerts

    volume_ratio = recent_perf.get("volume_ratio", 0)  # 量比（今日成交量/昨日成交量）
    threshold = alerts_cfg.get("volume_spike")

    if threshold and volume_ratio > 0 and volume_ratio >= threshold:
        if not was_alerted_today(code, "VOLUME_SPIKE"):
            alerts.append({
                "type": "VOLUME_SPIKE",
                "trigger_value": volume_ratio,
                "threshold_value": threshold,
                "headline": f"成交量较昨日放大 {volume_ratio:.1f} 倍",
            })

    return alerts


def check_negative_news(holding: dict, news_items: list) -> list[dict]:
    """检查负面新闻告警"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not alerts_cfg.get("negative_news"):
        return alerts

    # 负面关键词
    NEGATIVE_KEYWORDS = [
        "违规", "处罚", "监管函", "警示函", "立案", "调查",
        "造假", "欺诈", "诉讼", "仲裁", "减持", "业绩亏损",
        "下滑", "不及预期", "风险警示", "ST", "退市",
    ]

    negative_found = []
    for item in news_items:
        title = item.get("title", "") or ""
        content = item.get("content", "") or ""
        text = title + content
        if any(kw in text for kw in NEGATIVE_KEYWORDS):
            negative_found.append(title[:60])

    if negative_found:
        if not was_alerted_today(code, "NEGATIVE_NEWS"):
            alerts.append({
                "type": "NEGATIVE_NEWS",
                "trigger_value": len(negative_found),
                "threshold_value": 1,
                "headline": f"发现 {len(negative_found)} 条负面新闻：{' | '.join(negative_found[:2])}",
            })

    return alerts


def check_esg_downgrade(holding: dict, esg_data: dict) -> list[dict]:
    """检查 ESG 评级下调"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not alerts_cfg.get("esg_downgrade"):
        return alerts

    # 检查 ESG 评级变化（需要前后两次数据对比）
    # 简化：如果当前评级为 CCC/BB 或以下，或有"下调"关键词
    rating = str(esg_data.get("rating", "")).strip().upper()
    down_keywords = ["下调", "调降", "降级", "负面"]

    if any(kw in str(esg_data) for kw in down_keywords) or rating in ("CCC", "CC", "C"):
        if not was_alerted_today(code, "ESG_DOWNGRADE"):
            alerts.append({
                "type": "ESG_DOWNGRADE",
                "trigger_value": 1,
                "threshold_value": 1,
                "headline": f"ESG 评级：{esg_data.get('rating', 'N/A')}，{esg_data.get('agency', 'N/A')} 发布",
            })

    return alerts


def check_analyst_downgrade(holding: dict, events: list) -> list[dict]:
    """检查券商下调评级事件"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not alerts_cfg.get("analyst_downgrade"):
        return alerts

    downgrade_keywords = ["下调", "调降", "降级", "卖出", "减持评级"]

    for event in events:
        event_type = str(event.get("type", "")).lower()
        title = str(event.get("title", ""))
        if "评级" in event_type or any(kw in title for kw in downgrade_keywords):
            if not was_alerted_today(code, "ANALYST_DOWNGRADE"):
                alerts.append({
                    "type": "ANALYST_DOWNGRADE",
                    "trigger_value": 1,
                    "threshold_value": 1,
                    "headline": title[:60],
                })
            break

    return alerts


def check_large_shareholder_reduce(holding: dict, shareholder_data: dict) -> list[dict]:
    """检查大股东减持"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not alerts_cfg.get("large_shareholder_reduce"):
        return alerts

    # 检查大股东/董监高近期是否有减持事件
    # shareholder_data 应包含 top_holders 或 change_ratio
    top_holders = shareholder_data.get("top_holders", [])
    threshold = alerts_cfg.get("shareholder_reduce_threshold", 0.5)  # 默认减持 0.5% 以上告警

    for holder in top_holders:
        change = holder.get("change_ratio", 0) or holder.get("change_pct", 0)
        if change and change < 0 and abs(change) >= threshold:
            if not was_alerted_today(code, "LARGE_SHAREHOLDER_REDUCE"):
                alerts.append({
                    "type": "LARGE_SHAREHOLDER_REDUCE",
                    "trigger_value": abs(change),
                    "threshold_value": threshold,
                    "headline": f"大股东 {holder.get('name', 'N/A')} 减持 {abs(change):.2f}%",
                })
            break

    return alerts


# ============================================================================
# 数据获取（并发）
# ============================================================================

def fetch_performance(code: str) -> dict:
    """获取股票行情数据"""
    result = call_ifind_api(
        "stock",
        "get_stock_performance",
        f"{code} 最近 5 日涨跌幅、成交量、换手率"
    )
    data = result.get("data", {})
    if isinstance(data, list) and data:
        latest = data[-1]
        prev = data[-2] if len(data) > 1 else latest
        price = latest.get("close", 0)
        prev_price = prev.get("close", price)
        change_pct = ((price - prev_price) / prev_price * 100) if prev_price else 0
        volume_ratio = (
            latest.get("volume", 0) / prev.get("volume", 1)
            if prev.get("volume") else 0
        )
        return {
            "price": price,
            "change_pct": change_pct,
            "volume_ratio": volume_ratio,
            "volume": latest.get("volume", 0),
        }
    return {}


def fetch_news(code: str, name: str, days: int = 3) -> list:
    """获取近期新闻"""
    result = call_ifind_api("news", "search_news", f"{name} {code} 近 {days} 天新闻")
    if isinstance(result, dict):
        return result.get("data", []) or []
    return []


def fetch_events(code: str, name: str) -> list:
    """获取近期重大事项"""
    result = call_ifind_api("stock", "get_stock_events", f"{name} {code} 近期重大事项")
    if isinstance(result, dict):
        return result.get("data", []) or []
    return []


def fetch_shareholders(code: str, name: str) -> dict:
    """获取股东数据"""
    result = call_ifind_api("stock", "get_stock_shareholders", f"{name} {code} 前十大股东及变动")
    if isinstance(result, dict):
        return result.get("data", {})
    return {}


def fetch_esg(code: str, name: str) -> dict:
    """获取 ESG 数据"""
    result = call_ifind_api("stock", "get_esg_data", f"{name} {code} ESG 评级及变动")
    if isinstance(result, dict):
        return result.get("data", {})
    return {}


# ============================================================================
# 单标的扫描
# ============================================================================

def scan_single_holding(holding: dict) -> list[dict]:
    """
    对单只持仓执行全量告警扫描。
    返回触发的告警列表（尚未入库）。
    """
    code = holding["code"]
    name = holding["name"]
    all_alerts = []

    # 并发拉取所有数据
    with ThreadPoolExecutor(max_workers=6) as executor:
        perf_future = executor.submit(fetch_performance, code)
        news_future = executor.submit(fetch_news, code, name)
        events_future = executor.submit(fetch_events, code, name)
        sh_future = executor.submit(fetch_shareholders, code, name)
        esg_future = executor.submit(fetch_esg, code, name)

        perf = perf_future.result()
        news = news_future.result()
        events = events_future.result()
        shareholders = sh_future.result()
        esg = esg_future.result()

    # 独立判断每类告警
    all_alerts.extend(check_price_alerts(holding, perf))
    all_alerts.extend(check_volume_spike(holding, perf))
    all_alerts.extend(check_negative_news(holding, news))
    all_alerts.extend(check_esg_downgrade(holding, esg))
    all_alerts.extend(check_analyst_downgrade(holding, events))
    all_alerts.extend(check_large_shareholder_reduce(holding, shareholders))

    return all_alerts


# ============================================================================
# 飞书推送
# ============================================================================

FEISHU_SESSION_ID = "782328a8-8c4c-4be3-b18c-57ad4ad0ae89"
FEISHU_REPLY_TO = "ou_aae8836476a244334c897fb11b9efd1a"


def send_to_feishu(message: str):
    """通过 OpenClaw 发送飞书消息"""
    cmd = [
        "openclaw", "agent",
        "--session-id", FEISHU_SESSION_ID,
        "--channel", "feishu",
        "--reply-to", FEISHU_REPLY_TO,
        "--deliver",
        "-m", message,
        "--json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


# ============================================================================
# 扫描并推送（主流程）
# ============================================================================

def run_scan(specific_code: Optional[str] = None, push: bool = True) -> list[dict]:
    """执行全量持仓扫描，发现告警则入库并推送飞书"""
    try:
        holdings = load_portfolio_config()
    except FileNotFoundError as e:
        print(f"错误：{e}")
        return []

    # 按 code 过滤
    if specific_code:
        holdings = [h for h in holdings if h["code"] == specific_code]
        if not holdings:
            print(f"未找到持仓：{specific_code}")
            return []

    triggered_alerts = []

    for holding in holdings:
        code = holding["code"]
        name = holding["name"]
        print(f"正在扫描：{name} ({code}) ...")

        alerts = scan_single_holding(holding)

        for alert in alerts:
            # 写入数据库
            alert_id = insert_alert(
                code=code,
                name=name,
                alert_type=alert["type"],
                trigger_value=alert["trigger_value"],
                threshold_value=alert["threshold_value"],
                headline=alert.get("headline", ""),
            )
            alert["id"] = alert_id
            alert["code"] = code
            alert["name"] = name
            triggered_alerts.append(alert)

            # 推送飞书
            if push:
                msg = format_single_alert(
                    name=name,
                    code=code,
                    alert_type=alert["type"],
                    trigger_value=alert["trigger_value"],
                    threshold_value=alert["threshold_value"],
                    headline=alert.get("headline", ""),
                )
                ok = send_to_feishu(msg)
                print(f"  {'✓' if ok else '✗'} {alert['type']} 告警{'已推送飞书' if ok else '推送失败'}")

    return triggered_alerts


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="持仓监控")
    parser.add_argument("action", nargs="?", default="scan",
                        choices=["scan", "history", "summary"],
                        help="执行动作：scan=扫描告警, history=查历史, summary=汇总")
    parser.add_argument("code", nargs="?", default=None, help="股票代码（如 300750）")
    parser.add_argument("--days", type=int, default=7, help="历史查询天数（默认7天）")
    parser.add_argument("--type", dest="alert_type", default=None, help="告警类型过滤")
    parser.add_argument("--no-push", action="store_true", help="仅扫描不入库不推送（测试用）")
    args = parser.parse_args()

    if args.action == "scan":
        if args.code:
            # 去掉 .SH/.SZ/.HK 后缀简化输入
            code = args.code
            print(f"扫描单标的：{code}")
        else:
            code = None
            print("全量持仓扫描开始...")

        alerts = run_scan(specific_code=code, push=not args.no_push)

        if not alerts:
            print("未发现告警 ✓")
        else:
            print(f"\n共触发 {len(alerts)} 条告警")

    elif args.action == "history":
        rows = query_history(
            days=args.days,
            code=args.code,
            alert_type=args.alert_type,
        )
        print(format_history_table(rows))

    elif args.action == "summary":
        alerts = get_unsent_alerts()
        summary = get_alert_summary(days=args.days)
        msg = format_summary(alerts=alerts, summary_by_stock=summary, days=args.days)
        print(msg)
        if alerts:
            ok = send_to_feishu(msg)
            print(f"\n{'✓ 已推送飞书' if ok else '✗ 推送失败'}")


if __name__ == "__main__":
    main()
