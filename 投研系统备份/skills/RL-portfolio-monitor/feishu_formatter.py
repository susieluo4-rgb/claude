"""飞书消息格式化"""

from datetime import datetime
from typing import Optional


ALERT_EMOJI = {
    "PRICE_DROP": "🔴",
    "PRICE_RISE": "🟢",
    "VOLUME_SPIKE": "🟡",
    "NEGATIVE_NEWS": "🔴",
    "NEW_ANNOUNCEMENT": "📋",
    "ESG_DOWNGRADE": "🔴",
    "ANALYST_DOWNGRADE": "🟡",
    "LARGE_SHAREHOLDER_REDUCE": "🟡",
}

ALERT_TYPE_NAME = {
    "PRICE_DROP": "价格下跌",
    "PRICE_RISE": "价格上涨",
    "VOLUME_SPIKE": "成交量放大",
    "NEGATIVE_NEWS": "负面新闻",
    "NEW_ANNOUNCEMENT": "新公告发布",
    "ESG_DOWNGRADE": "ESG 评级下调",
    "ANALYST_DOWNGRADE": "券商下调评级",
    "LARGE_SHAREHOLDER_REDUCE": "大股东减持",
}


def format_single_alert(
    name: str,
    code: str,
    alert_type: str,
    trigger_value: float,
    threshold_value: float,
    headline: str = "",
    ann_summary: str = "",
) -> str:
    """格式化单条告警为飞书消息"""
    emoji = ALERT_EMOJI.get(alert_type, "🔔")
    type_name = ALERT_TYPE_NAME.get(alert_type, alert_type)

    msg = f"{emoji} 【持仓预警】{name} {code}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"类型：{type_name}\n"
    msg += f"触发：{_format_trigger_value(alert_type, trigger_value)}\n"
    msg += f"阈值：{_format_threshold(alert_type, threshold_value)}\n"

    if headline:
        msg += f"摘要：{headline}\n"

    # 公告摘要（新公告类型独有）
    if alert_type == "NEW_ANNOUNCEMENT" and ann_summary:
        msg += f"\n📋 公告内容：\n{ann_summary}\n"

    msg += f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    return msg


def format_summary(
    alerts: list[dict],
    summary_by_stock: dict,
    days: int = 7,
) -> str:
    """格式化日度汇总消息"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    total = len(alerts)

    lines = []
    lines.append(f"📊 【持仓监控日报】{date_str}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")

    if total == 0:
        lines.append("今日无告警 👍")
    else:
        lines.append(f"近 {days} 天共 {total} 条告警：\n")

        for code, info in summary_by_stock.items():
            name = info["name"]
            emoji_counts = {}
            for a in info["alerts"]:
                t = a["type"]
                emoji = ALERT_EMOJI.get(t, "⚪")
                emoji_counts[f"{emoji} {ALERT_TYPE_NAME.get(t, t)}"] = a["count"]

            alerts_str = " / ".join(
                f"{k} {v}次" for k, v in emoji_counts.items()
            )
            lines.append(f"  • {name} — {alerts_str}")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"ℹ️ 数据截至 {datetime.now().strftime('%H:%M')}")
    return "\n".join(lines)


def format_history_table(rows: list[dict]) -> str:
    """格式化历史查询结果为 Markdown 表格"""
    if not rows:
        return "暂无告警记录"

    lines = []
    lines.append("📋 告警历史")
    lines.append("")
    lines.append("| 时间 | 股票 | 代码 | 类型 | 触发值 | 摘要 |")
    lines.append("|------|------|------|------|--------|------|")

    for r in rows:
        created = r["created_at"][:16] if r.get("created_at") else ""
        name = r.get("name", "")
        code = r.get("code", "")
        alert_type = r.get("alert_type", "")
        type_name = ALERT_TYPE_NAME.get(alert_type, alert_type)
        trigger = _format_trigger_value(alert_type, r.get("trigger_value", 0))
        headline = (r.get("headline") or "")[:30]
        lines.append(
            f"| {created} | {name} | {code} | {type_name} | {trigger} | {headline} |"
        )

    return "\n".join(lines)


def _format_trigger_value(alert_type: str, value: float) -> str:
    if alert_type in ("PRICE_DROP", "PRICE_RISE"):
        return f"{value:+.2f}%"
    elif alert_type == "VOLUME_SPIKE":
        return f"{value:.1f} 倍"
    elif alert_type == "ESG_DOWNGRADE":
        return f"评级变化 {value:.0f} 级"
    else:
        return f"{value}"


def _format_threshold(alert_type: str, value: float) -> str:
    if alert_type in ("PRICE_DROP", "PRICE_RISE"):
        return f"{alert_type == 'PRICE_DROP' and '跌幅' or '涨幅'} > {value:.1f}%"
    elif alert_type == "VOLUME_SPIKE":
        return f"成交量放大 > {value:.1f} 倍"
    elif alert_type == "ESG_DOWNGRADE":
        return f"ESG 评级下调 > {value:.0f} 级"
    elif alert_type == "LARGE_SHAREHOLDER_REDUCE":
        return f"减持比例 > {value:.2f}%"
    else:
        return f"> {value}"
