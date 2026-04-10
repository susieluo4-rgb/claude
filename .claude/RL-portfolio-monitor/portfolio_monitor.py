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
import time
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
# HTML 报告生成
# ============================================================================

def generate_html_report(
    all_perf_data: list[dict],
    triggered_alerts: list[dict],
    output_path: str,
) -> str:
    """生成持仓监控 HTML 报告，返回文件路径"""
    from datetime import datetime

    # 整理数据
    rows = []
    total_contribution = 0.0
    for d in all_perf_data:
        has_data = d.get("has_data", False)
        change = d["change_pct"]
        if has_data:
            contribution = (d["position_pct"] / 100) * change
            total_contribution += contribution
            if change >= 5:
                badge = f'<span class="badge-red">{change:+.2f}%</span>'
                row_class = "row-red"
            elif change >= 3:
                badge = f'<span class="badge-red-light">{change:+.2f}%</span>'
                row_class = "row-red-light"
            elif change <= -5:
                badge = f'<span class="badge-green">{change:+.2f}%</span>'
                row_class = "row-green"
            elif change <= -3:
                badge = f'<span class="badge-green-light">{change:+.2f}%</span>'
                row_class = "row-green-light"
            else:
                badge = f'<span class="badge-neutral">{change:+.2f}%</span>'
                row_class = ""
            change_str = f"{change:+.2f}%"
            contrib_str = f"{contribution:+.3f}%"
        else:
            badge = '<span class="badge-na">N/A</span>'
            row_class = "row-na"
            change_str = "N/A"
            contrib_str = "N/A"
            contribution = 0.0

        rows.append({
            "name": d["name"],
            "code": d["code"],
            "position_pct": d["position_pct"],
            "change_str": change_str,
            "contrib_str": contrib_str,
            "badge": badge,
            "row_class": row_class,
            "has_data": has_data,
        })

    # 按持仓占比排序（由大到小）
    rows.sort(key=lambda x: x["position_pct"], reverse=True)

    # 告警分类颜色
    alert_badge = {
        "PRICE_DROP": '<span class="badge-red">价格下跌</span>',
        "PRICE_RISE": '<span class="badge-green">价格上涨</span>',
        "VOLUME_SPIKE": '<span class="badge-yellow">成交量放大</span>',
        "NEGATIVE_NEWS": '<span class="badge-red">负面新闻</span>',
        "NEW_ANNOUNCEMENT": '<span class="badge-blue">新公告</span>',
        "ESG_DOWNGRADE": '<span class="badge-red">ESG下调</span>',
        "ANALYST_DOWNGRADE": '<span class="badge-yellow">评级下调</span>',
        "LARGE_SHAREHOLDER_REDUCE": '<span class="badge-yellow">大股东减持</span>',
    }

    alert_rows = ""
    for a in triggered_alerts:
        badge = alert_badge.get(a.get("type", ""), f'<span class="badge-neutral">{a.get("type","")}</span>')
        trigger = a.get("trigger_value", "")
        headline = a.get("headline", "")
        alert_rows += f"""
        <tr>
          <td>{a.get('name', '')}</td>
          <td>{a.get('code', '')}</td>
          <td>{badge}</td>
          <td>{trigger}</td>
          <td>{headline}</td>
        </tr>"""

    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_rows = [r for r in rows if r["has_data"]]
    na_rows = [r for r in rows if not r["has_data"]]
    total_up = sum(1 for r in data_rows if r["change_str"].startswith("+"))
    total_down = sum(1 for r in data_rows if r["change_str"].startswith("-"))
    total_flat = len(data_rows) - total_up - total_down

    # 有数据按涨跌幅排序，N/A 排最后
    sorted_rows = sorted(data_rows, key=lambda x: x["change_str"], reverse=True) + na_rows

    perf_rows_html = "\n".join(
        f'<tr class="{r["row_class"]}">'
        f'<td>{r["name"]}</td>'
        f'<td>{r["code"]}</td>'
        f'<td class="num">{r["position_pct"]:.2f}%</td>'
        f'<td class="num">{r["badge"]}</td>'
        f'<td class="num">{r["contrib_str"]}</td>'
        f'</tr>'
        for r in sorted_rows
    )

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>持仓监控日报 {date_str}</title>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d27;
    --border: #2a2d3a;
    --text: #e0e3eb;
    --text-muted: #8b8fa3;
    --accent: #3b82f6;
    --red: #22c55e;
    --red-light: #86efac;
    --green: #ef4444;
    --green-light: #f87171;
    --yellow: #eab308;
    --yellow-light: #fde047;
    --blue: #6366f1;
    --mono: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; line-height: 1.5; }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }}
  .subtitle {{ color: var(--text-muted); font-size: 0.85rem; margin-bottom: 24px; }}
  .kpi-row {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 24px; min-width: 140px; }}
  .kpi .label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }}
  .kpi .value {{ font-size: 1.5rem; font-weight: 700; font-family: var(--mono); }}
  .kpi .value.red {{ color: var(--red); }}
  .kpi .value.green {{ color: var(--green); }}
  .kpi .value.up {{ color: var(--red-light); }}
  .kpi .value.down {{ color: var(--green-light); }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
  .card h2 {{ font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-bottom: 14px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
  th {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }}
  th.sortable {{ cursor: pointer; user-select: none; transition: color 0.15s; }}
  th.sortable:hover {{ color: var(--text); }}
  th .sort-arrow {{ font-size: 0.65rem; margin-left: 3px; opacity: 0.3; }}
  th.active-sort .sort-arrow {{ opacity: 1; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid var(--border); }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .num {{ font-family: var(--mono); text-align: right; }}
  .badge-red {{ background: rgba(239,68,68,0.15); color: #f87171; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-red-light {{ background: rgba(239,68,68,0.08); color: #fca5a5; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-green {{ background: rgba(34,197,94,0.15); color: #86efac; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-green-light {{ background: rgba(34,197,94,0.08); color: #bbf7d0; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-yellow {{ background: rgba(234,179,8,0.15); color: #fde047; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-blue {{ background: rgba(99,102,241,0.15); color: #a5b4fc; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-na {{ background: rgba(139,143,163,0.08); color: #8b8fa3; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-neutral {{ background: rgba(139,143,163,0.15); color: #8b8fa3; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  /* 公告情感 badge */
  .badge-ann-major-pos {{ background: rgba(34,197,94,0.2); color: #4ade80; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 700; }}
  .badge-ann-pos {{ background: rgba(34,197,94,0.12); color: #86efac; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-pos-light {{ background: rgba(34,197,94,0.06); color: #bbf7d0; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-neutral {{ background: rgba(139,143,163,0.1); color: #8b8fa3; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-neg-light {{ background: rgba(239,68,68,0.06); color: #fca5a5; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-neg {{ background: rgba(239,68,68,0.12); color: #f87171; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-major-neg {{ background: rgba(239,68,68,0.2); color: #f87171; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 700; }}
  .row-red {{ background: rgba(239,68,68,0.04); }}
  .row-green {{ background: rgba(34,197,94,0.04); }}
  .row-red-light {{ background: rgba(239,68,68,0.02); }}
  .row-green-light {{ background: rgba(34,197,94,0.02); }}
  .row-na {{ opacity: 0.5; }}
  .no-alerts {{ color: var(--text-muted); text-align: center; padding: 24px; }}
  .footer {{ text-align: center; color: var(--text-muted); font-size: 0.75rem; margin-top: 24px; }}
  .contrib-total {{ font-family: var(--mono); font-size: 1.1rem; font-weight: 700; padding: 12px 16px; background: rgba(59,130,246,0.1); border-radius: 8px; margin-bottom: 16px; display: inline-block; }}
  @media (max-width: 700px) {{ table {{ font-size: 0.8rem; }} th, td {{ padding: 6px 8px; }} }}
</style>
</head>
<body>
<div class="container">

<h1>📊 持仓监控日报</h1>
<p class="subtitle">{date_str} · 数据截至 {time_str.split()[-1]}</p>

<div class="kpi-row">
  <div class="kpi">
    <div class="label">持仓数量</div>
    <div class="value">{len(all_perf_data)}</div>
  </div>
  <div class="kpi">
    <div class="label">上涨</div>
    <div class="value up">▲ {total_up}</div>
  </div>
  <div class="kpi">
    <div class="label">下跌</div>
    <div class="value down">▼ {total_down}</div>
  </div>
  <div class="kpi">
    <div class="label">平盘</div>
    <div class="value">{total_flat}</div>
  </div>
  <div class="kpi">
    <div class="label">触发告警</div>
    <div class="value {'red' if triggered_alerts else ''}">{len(triggered_alerts)}</div>
  </div>
  <div class="kpi">
    <div class="label">组合贡献</div>
    <div class="value {'red' if total_contribution >= 0 else 'green'}">{total_contribution:+.3f}%</div>
  </div>
</div>

<div class="card">
  <h2>持仓明细（按涨跌幅排序）</h2>
  <div class="contrib-total">组合今日估算涨跌幅：<span style="color:{'var(--red)' if total_contribution>=0 else 'var(--green)'}">{total_contribution:+.3f}%</span></div>
  <table>
    <thead>
      <tr>
        <th>公司名称</th>
        <th>代码</th>
        <th class="num">持仓占比</th>
        <th class="num">今日涨跌幅</th>
        <th class="num">组合贡献</th>
      </tr>
    </thead>
    <tbody>
      {perf_rows_html}
    </tbody>
  </table>
</div>
"""

    if triggered_alerts:
        html += f"""
<div class="card">
  <h2>触发告警（{len(triggered_alerts)} 条）</h2>
  <table>
    <thead>
      <tr>
        <th>公司</th>
        <th>代码</th>
        <th>类型</th>
        <th>触发值</th>
        <th>摘要</th>
      </tr>
    </thead>
    <tbody>
      {alert_rows}
    </tbody>
  </table>
</div>
"""
    else:
        html += """
<div class="card">
  <h2>触发告警</h2>
  <div class="no-alerts">✅ 今日无告警</div>
</div>
"""

    html += f"""
<div class="footer">
  由 RL-Portfolio-Monitor 生成 · {time_str} · 数据来源：同花顺 iFinD
</div>
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


# ============================================================================
# 交互式 HTML 报告（带刷新按钮）
# ============================================================================

def generate_interactive_html(
    all_perf_data: list[dict],
    triggered_alerts: list[dict],
    last_refresh_time: str = "",
) -> str:
    """生成带刷新按钮的交互式 HTML 报告"""
    from datetime import datetime

    rows = []
    total_contribution = 0.0
    for d in all_perf_data:
        has_data = d.get("has_data", False)
        change = d["change_pct"]
        if has_data:
            contribution = (d["position_pct"] / 100) * change
            total_contribution += contribution
            if change >= 5:
                badge = f'<span class="badge-red">{change:+.2f}%</span>'
                row_class = "row-red"
            elif change >= 3:
                badge = f'<span class="badge-red-light">{change:+.2f}%</span>'
                row_class = "row-red-light"
            elif change <= -5:
                badge = f'<span class="badge-green">{change:+.2f}%</span>'
                row_class = "row-green"
            elif change <= -3:
                badge = f'<span class="badge-green-light">{change:+.2f}%</span>'
                row_class = "row-green-light"
            else:
                badge = f'<span class="badge-neutral">{change:+.2f}%</span>'
                row_class = ""
            change_str = f"{change:+.2f}%"
            contrib_str = f"{contribution:+.3f}%"
        else:
            badge = '<span class="badge-na">N/A</span>'
            row_class = "row-na"
            change_str = "N/A"
            contrib_str = "N/A"
            contribution = 0.0

        rows.append({
            "name": d["name"],
            "code": d["code"],
            "position_pct": d["position_pct"],
            "change_str": change_str,
            "contrib_str": contrib_str,
            "badge": badge,
            "row_class": row_class,
            "has_data": has_data,
        })

    rows.sort(key=lambda x: x["position_pct"], reverse=True)

    alert_badge = {
        "PRICE_DROP": '<span class="badge-red">价格下跌</span>',
        "PRICE_RISE": '<span class="badge-green">价格上涨</span>',
        "VOLUME_SPIKE": '<span class="badge-yellow">成交量放大</span>',
        "NEGATIVE_NEWS": '<span class="badge-red">负面新闻</span>',
        "NEW_ANNOUNCEMENT": '<span class="badge-blue">新公告</span>',
        "ESG_DOWNGRADE": '<span class="badge-red">ESG下调</span>',
        "ANALYST_DOWNGRADE": '<span class="badge-yellow">评级下调</span>',
        "LARGE_SHAREHOLDER_REDUCE": '<span class="badge-yellow">大股东减持</span>',
    }

    alert_rows = ""
    for a in triggered_alerts:
        badge = alert_badge.get(a.get("type", ""), f'<span class="badge-neutral">{a.get("type","")}</span>')
        trigger = a.get("trigger_value", "")
        headline = a.get("headline", "")
        alert_rows += f"""
        <tr>
          <td>{a.get('name', '')}</td>
          <td>{a.get('code', '')}</td>
          <td>{badge}</td>
          <td>{trigger}</td>
          <td>{headline}</td>
        </tr>"""

    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_rows = [r for r in rows if r["has_data"]]
    na_rows = [r for r in rows if not r["has_data"]]
    total_up = sum(1 for r in data_rows if r["change_str"].startswith("+"))
    total_down = sum(1 for r in data_rows if r["change_str"].startswith("-"))
    total_flat = len(data_rows) - total_up - total_down
    sorted_rows = sorted(data_rows, key=lambda x: x["change_str"], reverse=True) + na_rows

    # 扫描所有持仓公告情感
    ann_results = scan_all_announcements()
    ann_by_code = {}
    for a in ann_results:
        code = a["code"]
        if code not in ann_by_code:
            ann_by_code[code] = []
        ann_by_code[code].append(a)

    # 为每行添加公告 badge
    for r in sorted_rows:
        anns = ann_by_code.get(r["code"], [])
        if anns:
            # 取最新一条公告的标签
            latest = anns[0]
            badge_html = get_announcement_badge(latest["tag"])
            title_short = latest["title"][:30]
            r["ann_badge"] = f'<span title="{title_short}">{badge_html} {title_short}</span>'
        else:
            r["ann_badge"] = '<span class="badge-ann-neutral">无新公告</span>'

    perf_rows_html = "\n".join(
        f'<tr class="{r["row_class"]}" data-code="{r["code"]}">'
        f'<td>{r["name"]}</td>'
        f'<td>{r["code"]}</td>'
        f'<td class="num">{r["position_pct"]:.2f}%</td>'
        f'<td class="num">{r["badge"]}</td>'
        f'<td class="num">{r["contrib_str"]}</td>'
        f'<td class="num">{r["ann_badge"]}</td>'
        f'</tr>'
        for r in sorted_rows
    )

    refresh_info = f"最后刷新：{last_refresh_time}" if last_refresh_time else "尚未刷新"

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>持仓监控日报 {date_str}</title>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d27;
    --border: #2a2d3a;
    --text: #e0e3eb;
    --text-muted: #8b8fa3;
    --accent: #3b82f6;
    --red: #22c55e;
    --red-light: #86efac;
    --green: #ef4444;
    --green-light: #f87171;
    --yellow: #eab308;
    --yellow-light: #fde047;
    --blue: #6366f1;
    --mono: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px; line-height: 1.5; }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }}
  .subtitle {{ color: var(--text-muted); font-size: 0.85rem; margin-bottom: 24px; }}
  .kpi-row {{ display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 24px; min-width: 140px; }}
  .kpi .label {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }}
  .kpi .value {{ font-size: 1.5rem; font-weight: 700; font-family: var(--mono); }}
  .kpi .value.red {{ color: var(--red); }}
  .kpi .value.green {{ color: var(--green); }}
  .kpi .value.up {{ color: var(--red-light); }}
  .kpi .value.down {{ color: var(--green-light); }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
  .card h2 {{ font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); margin-bottom: 14px; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
  th {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }}
  th.sortable {{ cursor: pointer; user-select: none; transition: color 0.15s; }}
  th.sortable:hover {{ color: var(--text); }}
  th .sort-arrow {{ font-size: 0.65rem; margin-left: 3px; opacity: 0.3; }}
  th.active-sort .sort-arrow {{ opacity: 1; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid var(--border); }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .num {{ font-family: var(--mono); text-align: right; }}
  .badge-red {{ background: rgba(239,68,68,0.15); color: #f87171; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-red-light {{ background: rgba(239,68,68,0.08); color: #fca5a5; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-green {{ background: rgba(34,197,94,0.15); color: #86efac; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-green-light {{ background: rgba(34,197,94,0.08); color: #bbf7d0; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-yellow {{ background: rgba(234,179,8,0.15); color: #fde047; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-blue {{ background: rgba(99,102,241,0.15); color: #a5b4fc; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-na {{ background: rgba(139,143,163,0.08); color: #8b8fa3; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  .badge-neutral {{ background: rgba(139,143,163,0.15); color: #8b8fa3; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }}
  /* 公告情感 badge */
  .badge-ann-major-pos {{ background: rgba(34,197,94,0.2); color: #4ade80; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 700; }}
  .badge-ann-pos {{ background: rgba(34,197,94,0.12); color: #86efac; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-pos-light {{ background: rgba(34,197,94,0.06); color: #bbf7d0; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-neutral {{ background: rgba(139,143,163,0.1); color: #8b8fa3; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-neg-light {{ background: rgba(239,68,68,0.06); color: #fca5a5; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-neg {{ background: rgba(239,68,68,0.12); color: #f87171; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; }}
  .badge-ann-major-neg {{ background: rgba(239,68,68,0.2); color: #f87171; padding: 1px 6px; border-radius: 3px; font-size: 0.75rem; font-weight: 700; }}
  .row-red {{ background: rgba(239,68,68,0.04); }}
  .row-green {{ background: rgba(34,197,94,0.04); }}
  .row-red-light {{ background: rgba(239,68,68,0.02); }}
  .row-green-light {{ background: rgba(34,197,94,0.02); }}
  .row-na {{ opacity: 0.5; }}
  .no-alerts {{ color: var(--text-muted); text-align: center; padding: 24px; }}
  .footer {{ text-align: center; color: var(--text-muted); font-size: 0.75rem; margin-top: 24px; }}
  .contrib-total {{ font-family: var(--mono); font-size: 1.1rem; font-weight: 700; padding: 12px 16px; background: rgba(59,130,246,0.1); border-radius: 8px; margin-bottom: 16px; display: inline-block; }}
  @media (max-width: 700px) {{ table {{ font-size: 0.8rem; }} th, td {{ padding: 6px 8px; }} }}

  /* 刷新按钮区域 */
  .refresh-bar {{ display: flex; gap: 12px; margin-bottom: 20px; align-items: center; flex-wrap: wrap; }}
  .btn {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 10px 20px; border: none; border-radius: 8px;
    font-size: 0.9rem; font-weight: 600; cursor: pointer;
    transition: all 0.2s; color: white;
  }}
  .btn:active {{ transform: scale(0.97); }}
  .btn:disabled {{ opacity: 0.5; cursor: not-allowed; transform: none; }}
  .btn-price {{ background: var(--accent); }}
  .btn-price:hover:not(:disabled) {{ background: #2563eb; }}
  .btn-alert {{ background: #f59e0b; }}
  .btn-alert:hover:not(:disabled) {{ background: #d97706; }}
  .btn-refresh {{ background: #8b5cf6; }}
  .btn-refresh:hover:not(:disabled) {{ background: #7c3aed; }}
  .refresh-info {{ color: var(--text-muted); font-size: 0.8rem; margin-left: auto; }}
  .loading {{ display: inline-block; width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.3); border-radius: 50%;
    border-top-color: white; animation: spin 0.8s linear infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .toast {{
    position: fixed; bottom: 24px; right: 24px;
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px 20px;
    color: var(--text); font-size: 0.85rem;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    opacity: 0; transform: translateY(20px);
    transition: all 0.3s; z-index: 1000;
  }}
  .toast.show {{ opacity: 1; transform: translateY(0); }}
  .row-updating {{ animation: pulse 1s ease-in-out; }}
  @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}
</style>
</head>
<body>
<div class="container">

<h1>📊 持仓监控日报</h1>
<p class="subtitle">{date_str} · {refresh_info}</p>

<div class="refresh-bar">
  <button class="btn btn-price" id="btn-price" onclick="refreshPrices()">
    <span id="price-icon">📈</span> 股价刷新
  </button>
  <button class="btn btn-alert" id="btn-alert" onclick="refreshAlerts()">
    <span id="alert-icon">🔔</span> 预警刷新
  </button>
  <button class="btn btn-refresh" id="btn-ann" onclick="refreshAnnouncements()">
    <span id="ann-icon">📋</span> 公告刷新
  </button>
  <span class="refresh-info" id="refresh-info">{refresh_info}</span>
</div>

<div class="kpi-row">
  <div class="kpi">
    <div class="label">持仓数量</div>
    <div class="value">{len(all_perf_data)}</div>
  </div>
  <div class="kpi">
    <div class="label">上涨</div>
    <div class="value up">▲ {total_up}</div>
  </div>
  <div class="kpi">
    <div class="label">下跌</div>
    <div class="value down">▼ {total_down}</div>
  </div>
  <div class="kpi">
    <div class="label">平盘</div>
    <div class="value">{total_flat}</div>
  </div>
  <div class="kpi">
    <div class="label">触发告警</div>
    <div class="value {'red' if triggered_alerts else ''}">{len(triggered_alerts)}</div>
  </div>
  <div class="kpi">
    <div class="label">组合贡献</div>
    <div class="value {'red' if total_contribution >= 0 else 'green'}">{total_contribution:+.3f}%</div>
  </div>
</div>

<div class="card">
  <h2>持仓明细（点击表头排序）</h2>
  <div class="contrib-total">组合今日估算涨跌幅：<span id="total-contrib" style="color:{'var(--green)' if total_contribution>=0 else 'var(--red)'}">{total_contribution:+.3f}%</span></div>
  <table>
    <thead>
      <tr>
        <th>公司名称</th>
        <th>代码</th>
        <th class="num sortable" id="th-position" onclick="sortBy('position')"><span>持仓占比</span><span class="sort-arrow" id="arrow-position">▼</span></th>
        <th class="num sortable" id="th-change" onclick="sortBy('change')"><span>今日涨跌幅</span><span class="sort-arrow" id="arrow-change">▼</span></th>
        <th class="num sortable" id="th-contrib" onclick="sortBy('contrib')"><span>组合贡献</span><span class="sort-arrow" id="arrow-contrib">▼</span></th>
        <th>最新公告</th>
      </tr>
    </thead>
    <tbody id="perf-table">
      {perf_rows_html}
    </tbody>
  </table>
</div>
"""

    if triggered_alerts:
        html += f"""
<div class="card">
  <h2>触发告警（{len(triggered_alerts)} 条）</h2>
  <table id="alert-table">
    <thead>
      <tr>
        <th>公司</th>
        <th>代码</th>
        <th>类型</th>
        <th>触发值</th>
        <th>摘要</th>
      </tr>
    </thead>
    <tbody>
      {alert_rows}
    </tbody>
  </table>
</div>
"""
    else:
        html += """
<div class="card">
  <h2>触发告警</h2>
  <div class="no-alerts" id="no-alerts">✅ 今日无告警</div>
  <table id="alert-table" style="display:none">
    <thead>
      <tr><th>公司</th><th>代码</th><th>类型</th><th>触发值</th><th>摘要</th></tr>
    </thead>
    <tbody id="alert-tbody"></tbody>
  </table>
</div>
"""

    html += f"""
<div class="footer">
  由 RL-Portfolio-Monitor 生成 · 数据来源：同花顺 iFinD
</div>
</div>

<div class="toast" id="toast"></div>

<script>
const ALERT_BADGE = {json.dumps({
    "PRICE_DROP": "🔴 价格下跌",
    "PRICE_RISE": "🟢 价格上涨",
    "VOLUME_SPIKE": "🟡 成交量放大",
    "NEGATIVE_NEWS": "🔴 负面新闻",
    "NEW_ANNOUNCEMENT": "📋 新公告",
    "ESG_DOWNGRADE": "🔴 ESG下调",
    "ANALYST_DOWNGRADE": "🟡 评级下调",
    "LARGE_SHAREHOLDER_REDUCE": "🟡 大股东减持",
}, ensure_ascii=False)};

let alertCount = {len(triggered_alerts)};

// 排序状态
let currentSort = {{ key: 'change', asc: false }};

function toggleSort(key) {{
  if (currentSort.key === key) {{
    currentSort.asc = !currentSort.asc;
  }} else {{
    currentSort.key = key;
    currentSort.asc = key === 'name';
  }}
  updateSortArrows();
  applySort();
}}

function updateSortArrows() {{
  const arrows = {{
    'position': document.getElementById('arrow-position'),
    'change': document.getElementById('arrow-change'),
    'contrib': document.getElementById('arrow-contrib'),
  }};
  const ths = {{
    'position': document.getElementById('th-position'),
    'change': document.getElementById('th-change'),
    'contrib': document.getElementById('th-contrib'),
  }};
  // 清除所有 active
  Object.values(ths).forEach(th => {{ if (th) th.classList.remove('active-sort'); }});
  Object.values(arrows).forEach(a => {{ if (a) a.textContent = '▼'; }});

  const arrow = arrows[currentSort.key];
  const th = ths[currentSort.key];
  if (arrow) arrow.textContent = currentSort.asc ? '▲' : '▼';
  if (th) th.classList.add('active-sort');
}}

function applySort() {{
  const tbody = document.getElementById('perf-table');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {{
    const aVal = getSortValue(a);
    const bVal = getSortValue(b);
    return currentSort.asc ? aVal - bVal : bVal - aVal;
  }});
  rows.forEach(r => tbody.appendChild(r));
}}

function getSortValue(row) {{
  const cells = row.querySelectorAll('td');
  switch (currentSort.key) {{
    case 'position':
      return parseFloat(cells[2]?.textContent) || 0;
    case 'change': {{
      const text = cells[3]?.textContent || '0';
      const n = parseFloat(text.replace(/[%+]/g, ''));
      return isNaN(n) ? -9999 : n;
    }}
    case 'contrib': {{
      const text = cells[4]?.textContent || '0';
      const n = parseFloat(text.replace(/[%+]/g, ''));
      return isNaN(n) ? -9999 : n;
    }}
    default: return 0;
  }}
}}

function showToast(msg, duration=3000) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}}

function sortBy(key) {{
  toggleSort(key);
}}

function updateRefreshInfo() {{
  document.getElementById('refresh-info').textContent =
    '最后刷新：' + new Date().toLocaleString('zh-CN');
}}

function formatChange(pct) {{
  if (pct === null || pct === undefined) return '<span class="badge-na">N/A</span>';
  const v = parseFloat(pct);
  let cls = 'badge-neutral';
  if (v <= -5) cls = 'badge-green';
  else if (v <= -3) cls = 'badge-green-light';
  else if (v >= 5) cls = 'badge-red';
  else if (v >= 3) cls = 'badge-red-light';
  return `<span class="${{cls}}">${{v >= 0 ? '+' : ''}}${{v.toFixed(2)}}%</span>`;
}}

function formatContrib(pct, posPct) {{
  if (pct === null || pct === undefined) return 'N/A';
  const contrib = (posPct / 100) * parseFloat(pct);
  const v = contrib.toFixed(3);
  return `${{v >= 0 ? '+' : ''}}${{v}}%`;
}}

function updateKPIs(data) {{
  const withData = data.filter(d => d.has_data);
  const up = withData.filter(d => d.change_pct > 0).length;
  const down = withData.filter(d => d.change_pct < 0).length;
  const flat = withData.length - up - down;
  let totalContrib = 0;
  withData.forEach(d => {{ totalContrib += (d.position_pct / 100) * d.change_pct; }});

  const kpis = document.querySelectorAll('.kpi .value');
  if (kpis.length >= 6) {{
    kpis[0].textContent = data.length;
    kpis[1].textContent = '▲ ' + up;
    kpis[2].textContent = '▼ ' + down;
    kpis[3].textContent = flat;
    kpis[4].textContent = alertCount;
    const tc = document.getElementById('total-contrib');
    tc.textContent = (totalContrib >= 0 ? '+' : '') + totalContrib.toFixed(3) + '%';
    tc.style.color = totalContrib >= 0 ? 'var(--red)' : 'var(--green)';
    if (alertCount > 0) {{
      kpis[4].classList.add('red');
    }}
  }}
}}

function updatePerfTable(data) {{
  // 按当前排序规则
  const sortFn = (a, b) => {{
    let aVal, bVal;
    switch (currentSort.key) {{
      case 'position':
        aVal = a.position_pct; bVal = b.position_pct;
        break;
      case 'change':
        aVal = a.has_data ? a.change_pct : -9999;
        bVal = b.has_data ? b.change_pct : -9999;
        break;
      case 'contrib':
        aVal = a.has_data ? (a.position_pct / 100) * a.change_pct : -9999;
        bVal = b.has_data ? (b.position_pct / 100) * b.change_pct : -9999;
        break;
      default:
        aVal = 0; bVal = 0;
    }}
    return currentSort.asc ? aVal - bVal : bVal - aVal;
  }};
  data.sort(sortFn);

  const tbody = document.getElementById('perf-table');
  tbody.innerHTML = data.map(d => {{
    const rowCls = d.has_data
      ? (d.change_pct >= 5 ? 'row-red' : d.change_pct >= 3 ? 'row-red-light' :
         d.change_pct <= -5 ? 'row-green' : d.change_pct <= -3 ? 'row-green-light' : '')
      : 'row-na';
    const annBadge = d.ann_badge || '<span class="badge-ann-neutral">无新公告</span>';
    return `<tr class="${{rowCls}}" data-code="${{d.code}}">
      <td>${{d.name}}</td>
      <td>${{d.code}}</td>
      <td class="num">${{d.position_pct.toFixed(2)}}%</td>
      <td class="num">${{formatChange(d.has_data ? d.change_pct : null)}}</td>
      <td class="num">${{formatContrib(d.has_data ? d.change_pct : null, d.position_pct)}}</td>
      <td class="num">${{annBadge}}</td>
    </tr>`;
  }}).join('');

  updateKPIs(data);
}}

function updateAlertTable(alerts) {{
  alertCount = alerts.length;
  const kpis = document.querySelectorAll('.kpi .value');
  if (kpis.length >= 5) kpis[4].textContent = alerts.length;

  if (alerts.length === 0) {{
    const noAlerts = document.getElementById('no-alerts');
    if (noAlerts) noAlerts.style.display = '';
    const table = document.getElementById('alert-table');
    if (table) table.style.display = 'none';
    return;
  }}

  const noAlerts = document.getElementById('no-alerts');
  if (noAlerts) noAlerts.style.display = 'none';
  const table = document.getElementById('alert-table');
  if (table) table.style.display = '';

  const tbody = document.getElementById('alert-tbody') || document.querySelector('#alert-table tbody');
  if (tbody) {{
    tbody.innerHTML = alerts.map(a => {{
      const badge = ALERT_BADGE[a.type] || a.type;
      return `<tr>
        <td>${{a.name || ''}}</td>
        <td>${{a.code || ''}}</td>
        <td>${{badge}}</td>
        <td>${{a.trigger_value || ''}}</td>
        <td>${{a.headline || ''}}</td>
      </tr>`;
    }}).join('');
  }}
}}

async function refreshPrices() {{
  const btn = document.getElementById('btn-price');
  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> 刷新中...';
  showToast('📈 正在刷新股价...');

  try {{
    const resp = await fetch('/api/refresh_prices');
    const result = await resp.json();
    if (result.data) {{
      updatePerfTable(result.data);
      updateRefreshInfo();
      showToast(`✅ 股价刷新完成：${{result.ok}}/${{result.count}} 只获取到数据`);
    }}
  }} catch (e) {{
    showToast('❌ 刷新失败：' + e.message);
  }}
  btn.disabled = false;
  btn.innerHTML = '<span id="price-icon">📈</span> 股价刷新';
}}

async function refreshAlerts() {{
  const btn = document.getElementById('btn-alert');
  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> 刷新中...';
  showToast('🔔 正在刷新预警信息（需要较长时间）...');

  try {{
    const resp = await fetch('/api/refresh_all');
    const result = await resp.json();
    if (result.status === 'started') {{
      showToast('⏳ 全量扫描已启动，请耐心等待...', 5000);
      // 后台轮询等待完成
      pollAlertRefresh();
    }}
  }} catch (e) {{
    showToast('❌ 刷新失败：' + e.message);
  }}
  btn.disabled = false;
  btn.innerHTML = '<span id="alert-icon">🔔</span> 预警刷新';
}}

async function refreshAnnouncements() {{
  const btn = document.getElementById('btn-ann');
  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> 刷新中...';
  showToast('📋 正在扫描公告情感...');

  try {{
    const resp = await fetch('/api/refresh_announcements');
    const result = await resp.json();
    if (result.data) {{
      updateAnnouncements(result.data);
      updateRefreshInfo();
      showToast(`✅ 公告扫描完成：${{result.count}} 条`);
    }}
  }} catch (e) {{
    showToast('❌ 刷新失败：' + e.message);
  }}
  btn.disabled = false;
  btn.innerHTML = '<span id="ann-icon">📋</span> 公告刷新';
}}

function updateAnnouncements(annData) {{
  // annData: {{code: {{tag, title}}, ...}}
  document.querySelectorAll('#perf-table tr').forEach(row => {{
    const code = row.dataset.code;
    if (!code) return;
    const ann = annData[code];
    const cells = row.querySelectorAll('td');
    if (cells.length < 6) return;
    if (ann) {{
      cells[5].innerHTML = ann.badge_html;
    }} else {{
      cells[5].innerHTML = '<span class="badge-ann-neutral">无新公告</span>';
    }}
  }});
}}

async function pollAlertRefresh() {{
  // 每 10 秒检查一次状态
  for (let i = 0; i < 60; i++) {{
    await new Promise(r => setTimeout(r, 10000));
    try {{
      const resp = await fetch('/api/status');
      const s = await resp.json();
      // 如果有新的告警数据，更新页面
      if (s.alerts > 0 || s.with_data > 0) {{
        // 触发一次全页面刷新
        location.reload();
        return;
      }}
    }} catch(e) {{}}
  }}
  showToast('⏰ 预警刷新超时，建议手动刷新页面');
}}

// 自动轮询 /api/status 更新最后刷新时间
setInterval(async () => {{
  try {{
    const resp = await fetch('/api/status');
    const s = await resp.json();
    if (s.last_refresh) {{
      document.getElementById('refresh-info').textContent =
        '最后刷新：' + s.last_refresh + ' | 告警 ' + s.alerts + ' 条';
    }}
  }} catch(e) {{}}
}}, 30000);
</script>
</body>
</html>"""

    return html

# ============================================================================
# ifind API 调用（通过 call-node.js 直接请求 ifind API，不走 MCP）
# ============================================================================

IFIND_CALL_NODE = os.path.expanduser(
    "~/Research/ifind mcp&skill/call-node.js"
)


def call_ifind_api(server_type: str, tool_name: str, query: str = "", **kwargs) -> dict:
    """
    通过 call-node.js 调用 ifind API。
    server_type: 'stock' | 'news' | 'edb' | 'fund'
    tool_name: MCP 工具名（如 'get_stock_performance'）
    query: 查询字符串（可省略，如 search_news/search_notice 用 kwargs 传参）
    kwargs: 额外参数如 time_start, time_end 等
    """
    # 构建参数字典
    params = kwargs.copy()
    if query:
        params["query"] = query
    params_str = json.dumps(params, ensure_ascii=False)

    # 构建脚本（不使用 f-string 避免 {}{} 转义问题）
    script = (
        "const { call } = require('" + IFIND_CALL_NODE + "');"
        "(async () => {"
        "    const result = await call('" + server_type + "', '" + tool_name + "', " + params_str + ");"
        "    console.log(JSON.stringify(result, null, 2));"
        "})().catch(e => { console.error(e.message); process.exit(1); });"
    )
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
    """检查 ESG 评分下降"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not alerts_cfg.get("esg_downgrade"):
        return alerts

    latest = esg_data.get("latest")
    previous = esg_data.get("previous")

    if not latest or not previous:
        return alerts

    latest_score = latest.get("score", 0)
    previous_score = previous.get("score", 0)
    change = latest_score - previous_score  # 正数=上升，负数=下降

    threshold = alerts_cfg.get("esg_drop_threshold", 1.0)  # 默认下降 >1 分告警
    if change < 0 and abs(change) >= threshold:
        if not was_alerted_today(code, "ESG_DOWNGRADE"):
            alerts.append({
                "type": "ESG_DOWNGRADE",
                "trigger_value": abs(change),
                "threshold_value": threshold,
                "headline": f"ESG 评分下降 {abs(change):.2f} 分（{previous_score:.2f} → {latest_score:.2f}）",
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
    """检查大股东减持（比较前十大股东前后两期数据）"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not alerts_cfg.get("large_shareholder_reduce"):
        return alerts

    # shareholder_data: {top_holders: [...], history: [{date, total_pct}...]}
    history = shareholder_data.get("history", [])
    if len(history) < 2:
        return alerts

    # 获取最新和前一期的总持股比例
    latest_total = history[0].get("total_pct", 0)
    previous_total = history[1].get("total_pct", 0)
    change = latest_total - previous_total  # 负数表示减持

    threshold = alerts_cfg.get("shareholder_reduce_threshold", 0.5)  # 默认减持 >0.5% 告警
    if change < 0 and abs(change) >= threshold:
        if not was_alerted_today(code, "LARGE_SHAREHOLDER_REDUCE"):
            alerts.append({
                "type": "LARGE_SHAREHOLDER_REDUCE",
                "trigger_value": abs(change),
                "threshold_value": threshold,
                "headline": f"前十大股东合计减持 {abs(change):.2f}%（{previous_total:.2f}% → {latest_total:.2f}%）",
            })

    return alerts


# ============================================================================
# 数据获取（并发）
# ============================================================================

def fetch_performance(code: str) -> dict:
    """获取股票行情数据（通过近3日收盘价计算涨跌幅）"""
    result = call_ifind_api(
        "stock",
        "get_stock_performance",
        f"{code} 近3日收盘价"
    )
    try:
        inner = json.loads(result.get("data", {}).get("result", {}).get("content", [{}])[0].get("text", "{}"))
        table_text = inner.get("data", {}).get("answer", "")
        all_rows = table_text.strip().split("\n")

        # 第一步：解析表头，找到 收盘价 的列索引
        price_idx = None
        data_start = 0
        for i, r in enumerate(all_rows):
            r = r.strip()
            if not r:
                continue
            if r.startswith("|证券代码"):
                cells = [c.strip() for c in r.split("|")]
                for j, col in enumerate(cells):
                    if "收盘价" in col:
                        price_idx = j
                data_start = i + 1
                break

        if price_idx is None:
            return {}

        # 第二步：提取数据行（排除分隔线和注释）
        data_rows = []
        for r in all_rows[data_start:]:
            r = r.strip()
            if not r:
                continue
            if r.startswith("#") or r.startswith("```"):
                continue
            cells = [c.strip() for c in r.split("|")]
            if all(c in ("", "---") for c in cells):
                continue
            if r.startswith("|") and len(cells) > price_idx:
                data_rows.append(cells)

        if len(data_rows) < 2:
            return {}

        # 取前两行：最新价和昨日收盘价（API 按倒序返回）
        try:
            today_price = float(data_rows[0][price_idx])
            yesterday_price = float(data_rows[1][price_idx])
            if today_price <= 0 or yesterday_price <= 0:
                return {}
            change_pct = (today_price - yesterday_price) / yesterday_price * 100
        except (ValueError, IndexError):
            return {}
        return {
            "price": today_price,
            "change_pct": round(change_pct, 4),
            "volume_ratio": 0,
        }
    except Exception:
        return {}


def fetch_news(code: str, name: str, days: int = 3) -> list:
    """获取近期新闻"""
    from datetime import datetime, timedelta
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    result = call_ifind_api("news", "search_news", f"{name} {code}", time_start=start, time_end=end)
    try:
        inner_data = result.get("data", {}).get("result", {}).get("content", [{}])[0].get("text", "{}")
        inner = json.loads(inner_data)
        news_list = json.loads(inner.get("data", {}).get("data", "[]"))
        return [{"title": n.get("资讯标题", ""), "content": n.get("资讯内容", "")} for n in news_list]
    except Exception:
        return []


def fetch_events(code: str, name: str) -> list:
    """获取近期重大事项"""
    result = call_ifind_api("stock", "get_stock_events", f"{name} {code} 近期重大事项")
    try:
        if isinstance(result, dict):
            inner_data = result.get("data", {}).get("result", {}).get("content", [{}])[0].get("text", "{}")
            inner = json.loads(inner_data)
            # 解析事件列表（表格格式）
            table_text = inner.get("data", {}).get("answer", "")
            rows = [r.strip() for r in table_text.strip().split("\n") if r.strip() and not r.startswith("#") and not r.startswith("|证券代码")]
            events = []
            for row in rows:
                cells = [c.strip() for c in row.split("|")]
                # 过滤纯分隔线
                if all(c in ("", "---") for c in cells):
                    continue
                # 只保留有内容的行（至少3个单元格）
                if len(cells) >= 3:
                    events.append({
                        "type": cells[1] if len(cells) > 1 else "",  # 事项类型
                        "title": cells[2] if len(cells) > 2 else "",  # 事项内容
                        "date": cells[3] if len(cells) > 3 else "",
                    })
            return events
    except Exception:
        pass
    return []


def fetch_shareholders(code: str, name: str) -> dict:
    """获取股东数据（解析表格格式）"""
    result = call_ifind_api("stock", "get_stock_shareholders", f"{name} {code} 前十大股东及变动")
    try:
        if isinstance(result, dict):
            inner_data = result.get("data", {}).get("result", {}).get("content", [{}])[0].get("text", "{}")
            inner = json.loads(inner_data)
            table_text = inner.get("data", {}).get("answer", "")
            # 解析表格：跳过表头和分隔线，取数据行
            rows = [r.strip() for r in table_text.strip().split("\n") if r.strip()]
            header_row = None
            data_rows = []
            for r in rows:
                if r.startswith("|证券代码"):
                    header_row = [c.strip() for c in r.split("|")]
                    continue
                if r.startswith("| ---"):
                    continue
                cells = [c.strip() for c in r.split("|")]
                if all(c in ("", "---") for c in cells):
                    continue
                if r.startswith("|") and len(cells) >= 4:
                    data_rows.append(cells)

            if not data_rows:
                return {}
            # 返回最新一期（前十大股东列表）和历史期次
            # 格式：{top_holders: [{name, shares, pct, nature}...], history: [{date, total_pct}...]}
            latest = data_rows[0]
            history = []
            for row in data_rows:
                date = row[3] if len(row) > 3 else ""
                total_pct_str = row[4] if len(row) > 4 else ""
                try:
                    total_pct = float(total_pct_str.replace("%", ""))
                except (ValueError, AttributeError):
                    total_pct = 0
                history.append({"date": date, "total_pct": total_pct})

            # 提取前十大股东（每5列一个股东：名称、数量、比例、股份性质、股东性质）
            holders = []
            col = 5  # 第1大股东从第5列开始
            while col + 4 < len(latest):
                name_cell = latest[col] if len(latest) > col else ""
                shares_cell = latest[col + 1] if len(latest) > col + 1 else ""
                pct_cell = latest[col + 2] if len(latest) > col + 2 else ""
                nature_cell = latest[col + 3] if len(latest) > col + 3 else ""
                if name_cell and name_cell not in ("", "N/A"):
                    try:
                        pct = float(pct_cell.replace("%", ""))
                    except (ValueError, AttributeError):
                        pct = 0
                    holders.append({
                        "name": name_cell,
                        "shares": shares_cell,
                        "pct": pct,
                        "nature": nature_cell,
                    })
                col += 5
                if len(holders) >= 10:
                    break

            return {"top_holders": holders, "history": history}
    except Exception:
        pass
    return {"top_holders": [], "history": []}


def fetch_esg(code: str, name: str) -> dict:
    """获取 ESG 数据"""
    result = call_ifind_api("stock", "get_esg_data", f"{name} {code} ESG 评级及变动")
    try:
        if isinstance(result, dict):
            inner_data = result.get("data", {}).get("result", {}).get("content", [{}])[0].get("text", "{}")
            inner = json.loads(inner_data)
            table_text = inner.get("data", {}).get("answer", "")
            # 解析表格，提取日期和ESG评分
            rows = [r.strip() for r in table_text.strip().split("\n") if r.strip()]
            scores = []
            for r in rows:
                cells = [c.strip() for c in r.split("|")]
                if len(cells) >= 4 and cells[0] and not cells[0].startswith("证券代码"):
                    date = cells[3]
                    score_str = cells[4] if len(cells) > 4 else ""
                    try:
                        score = float(score_str) if score_str else None
                    except (ValueError, TypeError):
                        score = None
                    if score is not None:
                        scores.append({"date": date, "score": score})
            if len(scores) >= 2:
                # 按日期排序（最新期优先）
                scores.sort(key=lambda x: x["date"], reverse=True)
                return {"latest": scores[0], "previous": scores[1]}
            elif len(scores) == 1:
                return {"latest": scores[0], "previous": None}
    except Exception:
        pass
    return {"latest": None, "previous": None}


def fetch_announcements(code: str, name: str) -> list:
    """获取近 48 小时内新公告列表"""
    from datetime import datetime, timedelta
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    result = call_ifind_api("news", "search_notice", f"{name} {code}", time_start=start, time_end=end)
    try:
        inner_data = result.get("data", {}).get("result", {}).get("content", [{}])[0].get("text", "{}")
        inner = json.loads(inner_data)
        notice_list = json.loads(inner.get("data", {}).get("data", "[]"))
        return [
            {"title": n.get("公告标题", ""), "content": n.get("公告片段内容", ""), "date": n.get("日期", "")}
            for n in notice_list
        ]
    except Exception:
        return []


# ============================================================================
# 新增告警：24 小时新公告 + 情感分析（整合自 RL-alphapai）
# ============================================================================

ANNOUNCEMENT_KEYWORDS = {
    # 重大事项类
    "业绩预告", "业绩快报", "业绩亏损", "业绩修正",
    "分红", "送股", "转增", "配股", "增发",
    "股权激励", "员工持股", "回购", "增持", "减持",
    "重大合同", "中标", "合作", "投资",
    "资产重组", "并购", "收购", "剥离",
    "监管函", "警示函", "问询函", "立案", "调查",
    "风险提示", "ST", "*ST", "退市",
    "高管变动", "董事辞职", "总裁变更",
    "分红实施", "权益分派",
}

ANNOUNCEMENT_CATEGORY = {
    "业绩预告": "📊 业绩",
    "业绩快报": "📊 业绩",
    "业绩亏损": "📊 业绩",
    "业绩修正": "📊 业绩",
    "分红": "💰 分红",
    "送股": "💰 分红",
    "转增": "💰 分红",
    "配股": "💰 融资",
    "增发": "💰 融资",
    "股权激励": "🏛️ 股权",
    "员工持股": "🏛️ 股权",
    "回购": "🏛️ 股权",
    "增持": "🏛️ 股东",
    "减持": "🏛️ 股东",
    "重大合同": "📋 经营",
    "中标": "📋 经营",
    "合作": "📋 经营",
    "投资": "📋 经营",
    "资产重组": "🔄 重组",
    "并购": "🔄 重组",
    "收购": "🔄 重组",
    "剥离": "🔄 重组",
    "监管函": "⚠️ 监管",
    "警示函": "⚠️ 监管",
    "问询函": "⚠️ 监管",
    "立案": "⚠️ 监管",
    "调查": "⚠️ 监管",
    "风险提示": "⚠️ 风险",
    "ST": "⚠️ 风险",
    "*ST": "⚠️ 风险",
    "退市": "⚠️ 风险",
    "高管变动": "👤 人事",
    "董事辞职": "👤 人事",
    "总裁变更": "👤 人事",
    "分红实施": "💰 分红",
    "权益分派": "💰 分红",
}

# 公告情感关键词（整合自 RL-alphapai daily_announcement_monitor.py）
ANNOUNCEMENT_POSITIVE = [
    "业绩增长", "净利润", "营收增长", "超预期", "大幅增长", "突破", "创新高",
    "中标", "大单", "订单", "签约", "战略合作", "扩产", "产能扩张",
    "回购", "增持", "评级上调", "目标价", "首予", "买入", "推荐",
    "全球首发", "填补空白", "量产", "商业化", "市场份额", "份额提升",
]

ANNOUNCEMENT_NEGATIVE = [
    "业绩下降", "亏损", "净利润下降", "不及预期", "大幅下降", "首亏", "续亏",
    "终止", "取消", "减持", "评级下调", "出售", "转让",
    "诉讼", "仲裁", "处罚", "监管函", "警示函", "问询函", "立案调查",
    "停产", "安全事故", "质量事故", "召回",
]

# 重大利好/利空关键词
ANNOUNCEMENT_MAJOR_POSITIVE = ["全球首发", "填补空白", "创新高", "超预期"]
ANNOUNCEMENT_MAJOR_NEGATIVE = ["处罚", "立案调查", "安全事故", "质量事故", "监管函"]


def analyze_announcement_sentiment(title: str, content: str = "") -> tuple[str, str, str]:
    """基于关键词分析公告情感

    Returns:
        (情感分类, 情感标签, 简短评论)
        情感分类: "正面" / "负面" / "中性"
        情感标签: "+++" / "++" / "+" / "=" / "-" / "--" / "---"
    """
    text = (title + " " + content)[:500]
    for kw in ANNOUNCEMENT_NEGATIVE:
        if kw in text:
            if kw in ANNOUNCEMENT_MAJOR_NEGATIVE:
                return "负面", "---", f"重大利空：{kw}"
            return "负面", "--", f"负面：{kw}"
    for kw in ANNOUNCEMENT_POSITIVE:
        if kw in text:
            if kw in ANNOUNCEMENT_MAJOR_POSITIVE:
                return "正面", "+++", f"重大利好：{kw}"
            return "正面", "++", f"正面：{kw}"
    return "中性", "=", "常规公告"


def get_announcement_badge(tag: str) -> str:
    """获取情感标签对应的 HTML badge"""
    badge_map = {
        "+++": '<span class="badge-ann-major-pos">+++</span>',
        "++": '<span class="badge-ann-pos">++</span>',
        "+": '<span class="badge-ann-pos-light">+</span>',
        "=": '<span class="badge-ann-neutral">=</span>',
        "-": '<span class="badge-ann-neg-light">-</span>',
        "--": '<span class="badge-ann-neg">--</span>',
        "---": '<span class="badge-ann-major-neg">---</span>',
    }
    return badge_map.get(tag, f'<span class="badge-ann-neutral">{tag}</span>')


def check_new_announcement(holding: dict, announcements: list) -> list[dict]:
    """检查 24 小时内是否有新公告（含情感分析）"""
    alerts = []
    alerts_cfg = holding.get("alerts", {})
    code = holding["code"]
    name = holding["name"]

    if not alerts_cfg.get("new_announcement"):
        return alerts

    if not announcements:
        return alerts

    # 过滤出 24 小时内的有效公告（有标题的）
    recent = [
        a for a in announcements
        if a.get("title") and str(a.get("title", "")).strip()
    ]

    if not recent:
        return alerts

    # 分类整理 + 情感分析
    categorized = {}
    sentiment_list = []
    for ann in recent:
        title = str(ann.get("title", ""))
        content = str(ann.get("content", ""))[:200]
        category = "📋 其他"
        for kw, cat in ANNOUNCEMENT_CATEGORY.items():
            if kw in title:
                category = cat
                break
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(title[:50])

        # 情感分析
        sentiment, tag, comment = analyze_announcement_sentiment(title, content)
        sentiment_list.append({
            "title": title[:60],
            "sentiment": sentiment,
            "tag": tag,
            "comment": comment,
        })

    # 按类别生成摘要
    summary_parts = []
    for cat, titles in categorized.items():
        unique = list(dict.fromkeys(titles))[:3]  # 每类最多3条，去重
        summary_parts.append(f"{cat} {len(titles)}条")
        for t in unique:
            summary_parts.append(f"  • {t}")

    headline = "; ".join(f"{k}" for k, v in categorized.items() for _ in range(1))

    if not was_alerted_today(code, "NEW_ANNOUNCEMENT"):
        alerts.append({
            "type": "NEW_ANNOUNCEMENT",
            "trigger_value": len(recent),
            "threshold_value": 1,
            "headline": f"近24小时 {len(recent)} 条新公告",
            "ann_summary": "\n".join(summary_parts),
            "announcements": recent,
        })

    return alerts


# ============================================================================
# 全量公告情感扫描（整合自 RL-alphapai daily_announcement_monitor.py）
# ============================================================================

def scan_all_announcements() -> list[dict]:
    """扫描所有持仓股票的公告，返回情感分析结果

    Returns:
        [{"code", "name", "title", "date", "sentiment", "tag", "comment"}, ...]
    """
    try:
        holdings = load_portfolio_config()
    except FileNotFoundError:
        return []

    results = []
    seen_codes = set()

    def fetch_one(holding):
        code = holding["code"]
        name = holding["name"]
        announcements = fetch_announcements(code, name)
        out = []
        for ann in announcements:
            title = ann.get("title", "")
            date = ann.get("date", "")
            content = ann.get("content", "")[:200]
            sentiment, tag, comment = analyze_announcement_sentiment(title, content)
            key = (code, date, title[:20])
            if key not in seen_codes:
                seen_codes.add(key)
                out.append({
                    "code": code,
                    "name": name,
                    "title": title,
                    "date": date,
                    "content": content,
                    "sentiment": sentiment,
                    "tag": tag,
                    "comment": comment,
                })
        return out

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_one, h) for h in holdings]
        for future in as_completed(futures):
            try:
                results.extend(future.result())
            except Exception:
                pass

    results.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 保存到本地 vault（按公司分组）
    by_company = {}
    for r in results:
        code = r["code"]
        if code not in by_company:
            by_company[code] = {"name": r["name"], "announcements": []}
        by_company[code]["announcements"].append(r)

    for code, info in by_company.items():
        save_announcements_to_vault(code, info["name"], info["announcements"])

    return results


def save_announcements_to_vault(code: str, name: str, announcements: list):
    """将公告保存到 基本面-公司列表 对应文件夹

    路径: ~/Research/Vault_公司基本面Agent/11_公司列表/{首字母}/{name}_{code}/公告/
    """
    if not announcements:
        return

    # 获取首字母
    first_char = name[0].upper()
    if not first_char.isalpha():
        first_char = "#"

    company_dir = os.path.expanduser(
        f"~/Research/Vault_公司基本面Agent/11_公司列表/{first_char}/{name}_{code}/公告"
    )
    os.makedirs(company_dir, exist_ok=True)

    # 按日期分组，每天一个文件
    by_date = {}
    for ann in announcements:
        date = ann.get("date", "")[:10] or "未知日期"
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(ann)

    for date, anns in by_date.items():
        safe_date = date.replace("-", "")
        filename = f"{company_dir}/公告_{safe_date}.md"

        lines = [
            f"# {name}（{code}）公告汇总",
            f"",
            f"> 日期：{date}",
            f"> 扫描时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> 数据来源：同花顺 iFinD search_notice",
            f"",
            f"---",
            f"",
            f"共 {len(anns)} 条公告",
            f"",
        ]

        for ann in anns:
            title = ann.get("title", "无标题")
            content = ann.get("content", "")
            sentiment = ann.get("sentiment", "中性")
            tag = ann.get("tag", "=")
            comment = ann.get("comment", "")

            lines.append(f"## [{tag}] {title}")
            lines.append(f"")
            lines.append(f"- **情感**：{sentiment}（{comment}）")
            lines.append(f"- **日期**：{ann.get('date', '')}")
            if content:
                lines.append(f"- **摘要**：{content}")
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


# ============================================================================
# 单标的扫描
# ============================================================================

def scan_single_holding(holding: dict) -> tuple[list[dict], dict]:
    """
    对单只持仓执行全量告警扫描。
    返回 (告警列表, 行情数据)。
    行情数据用于扫描结束后的持仓贡献汇总表。
    """
    code = holding["code"]
    name = holding["name"]
    all_alerts = []

    # 并发拉取所有数据（限制并发数以避免API限流）
    with ThreadPoolExecutor(max_workers=2) as executor:
        perf_future = executor.submit(fetch_performance, code)
        news_future = executor.submit(fetch_news, code, name)
        events_future = executor.submit(fetch_events, code, name)
        sh_future = executor.submit(fetch_shareholders, code, name)
        esg_future = executor.submit(fetch_esg, code, name)
        ann_future = executor.submit(fetch_announcements, code, name)

        perf = perf_future.result()
        news = news_future.result()
        events = events_future.result()
        shareholders = sh_future.result()
        esg = esg_future.result()
        announcements = ann_future.result()

    # 独立判断每类告警
    all_alerts.extend(check_price_alerts(holding, perf))
    all_alerts.extend(check_volume_spike(holding, perf))
    all_alerts.extend(check_negative_news(holding, news))
    all_alerts.extend(check_new_announcement(holding, announcements))
    all_alerts.extend(check_esg_downgrade(holding, esg))
    all_alerts.extend(check_analyst_downgrade(holding, events))
    all_alerts.extend(check_large_shareholder_reduce(holding, shareholders))

    return all_alerts, perf


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

    # 按 code 过滤（支持部分匹配，如 "300454" 匹配 "300454.SZ"）
    if specific_code:
        holdings = [h for h in holdings if
                    h["code"] == specific_code or
                    h["code"].startswith(specific_code + ".") or
                    h["code"].split(".")[0] == specific_code]
        if not holdings:
            print(f"未找到持仓：{specific_code}")
            return []

    triggered_alerts = []
    # 收集所有持仓的行情数据（用于持仓贡献汇总表）
    all_perf_data = []

    for holding in holdings:
        code = holding["code"]
        name = holding["name"]
        print(f"正在扫描：{name} ({code}) ...")

        alerts, perf = scan_single_holding(holding)
        time.sleep(0.5)

        # 收集行情数据（has_data 标记是否获取到有效行情）
        has_data = bool(perf.get("price", 0))
        all_perf_data.append({
            "code": code,
            "name": name,
            "position_pct": holding["position_pct"],
            "change_pct": perf.get("change_pct", 0),
            "price": perf.get("price", 0),
            "has_data": has_data,
        })

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
                    ann_summary=alert.get("ann_summary", ""),
                )
                ok = send_to_feishu(msg)
                print(f"  {'✓' if ok else '✗'} {alert['type']} 告警{'已推送飞书' if ok else '推送失败'}")

    # ── 扫描结束后：输出持仓贡献汇总表 ──
    if all_perf_data:
        print("\n" + "=" * 70)
        print("  持仓监控 — 今日行情汇总")
        print("=" * 70)
        print(f"{'公司名称':<12} {'代码':<12} {'持仓占比':>8} {'今日涨跌幅':>10} {'组合贡献':>10}")
        print("-" * 70)

        total_contribution = 0.0
        rows = []
        for d in all_perf_data:
            # 只对有数据的股票累加组合贡献
            if d.get("has_data"):
                contribution = (d["position_pct"] / 100) * d["change_pct"]
                total_contribution += contribution
            else:
                contribution = 0.0
            change = d["change_pct"]
            flag = " 🟢" if change <= -3 else (" 🔴" if change >= 3 else "")
            rows.append({
                "name": d["name"],
                "code": d["code"],
                "position_pct": d["position_pct"],
                "change_pct": change,
                "contribution": contribution,
                "flag": flag,
                "has_data": d.get("has_data", False),
            })

        # 按持仓占比排序（由大到小）
        rows.sort(key=lambda x: x["position_pct"], reverse=True)

        for r in rows:
            if r["has_data"]:
                change_str = f"{r['change_pct']:+.2f}%"
                contrib_str = f"{r['contribution']:+.3f}%"
            else:
                change_str = "N/A"
                contrib_str = "N/A"
            print(
                f"  {r['name']:<12} {r['code']:<12} {r['position_pct']:>6.2f}%  "
                f"{change_str:>10}{r['flag']}  {contrib_str:>10}"
            )

        print("-" * 70)
        # 只统计有数据的股票合计
        total_with_data = sum(
            (d["position_pct"] / 100) * d["change_pct"]
            for d in all_perf_data if d.get("has_data")
        )
        print(f"  {'组合今日估算涨跌幅':>30} {total_with_data:>+.3f}%")
        print("=" * 70)
        data_count = sum(1 for d in all_perf_data if d.get("has_data"))
        print(f"\nℹ️  组合贡献 = 持仓占比 × 今日涨跌幅")
        print(f"ℹ️  共扫描 {len(all_perf_data)} 只持仓（{data_count} 只获取到行情） | 告警 {len(triggered_alerts)} 条")

    return triggered_alerts, all_perf_data


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
    parser.add_argument("--html", action="store_true", help="同时生成 HTML 报告")
    parser.add_argument("--serve", action="store_true", help="启动交互式 HTTP 服务（带刷新按钮）")
    parser.add_argument("--port", type=int, default=8765, help="HTTP 服务端口（默认 8765）")
    args = parser.parse_args()

    if args.serve:
        from portfolio_server import run_server
        run_server(port=args.port)
        return

    if args.action == "scan":
        if args.code:
            code = args.code
            print(f"扫描单标的：{code}")
        else:
            code = None
            print("全量持仓扫描开始...")

        alerts, perf_data = run_scan(specific_code=code, push=not args.no_push)

        if not alerts:
            print("未发现告警 ✓")
        else:
            print(f"\n共触发 {len(alerts)} 条告警")

        # 生成 HTML 报告
        if args.html:
            from datetime import date
            today = date.today().isoformat()
            suffix = f"_{code}" if code else "_full"
            html_path = os.path.expanduser(f"~/.claude/skills/RL-portfolio-monitor/reports/portfolio_report_{today}{suffix}.html")
            os.makedirs(os.path.dirname(html_path), exist_ok=True)
            generated_path = generate_html_report(perf_data, alerts, html_path)
            print(f"\n📄 HTML 报告已生成：{generated_path}")

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

        if args.html:
            # summary 模式也支持 HTML
            from datetime import date
            today = date.today().isoformat()
            html_path = os.path.expanduser(f"~/.claude/skills/RL-portfolio-monitor/reports/portfolio_summary_{today}.html")
            os.makedirs(os.path.dirname(html_path), exist_ok=True)
            # 将 perf_data 构造为 summary 格式
            perf_data = []
            generated_path = generate_html_report(perf_data, alerts, html_path)
            print(f"\n📄 HTML 报告已生成：{generated_path}")


if __name__ == "__main__":
    main()
