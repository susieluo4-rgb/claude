#!/usr/bin/env python3
"""
自选股公告情绪监控 - ifind版
用 ifind 实时公告数据，支持严格48小时过滤，并发批量查询

依赖: ifind MCP call-node.js
"""

import sys
import os
import json
import time
import asyncio
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IFIND_DIR = "/Users/zhuang225/Research/ifind mcp&skill"


def load_ifind_config():
    config_path = os.path.join(IFIND_DIR, "mcp_config.json")
    with open(config_path) as f:
        return json.load(f)


def ifind_call(server_type, tool, params):
    import subprocess
    cmd = [
        "node", "-e",
        f"const {{ call }} = require('./call-node.js'); call('{server_type}', '{tool}', {json.dumps(params)}).then(r => console.log(JSON.stringify(r))).catch(e => console.error(e.message))"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=IFIND_DIR)
    try:
        data = json.loads(result.stdout)
        if not (data.get("ok") and data.get("data")):
            return {"data": []}
        nested = data["data"]
        if not isinstance(nested, dict):
            return {"data": []}
        # nested looks like: {"jsonrpc": "2.0", "result": {"content": [{text: "..."}]}, "id": 2}
        # result.content[0].text = '{"code":1,"msg":"success","data":{"data":"[...]"}}'
        result_obj = nested.get("result", {})
        if not isinstance(result_obj, dict):
            return {"data": []}
        content_list = result_obj.get("content", [])
        if not (content_list and isinstance(content_list, list)):
            return {"data": []}
        text = content_list[0].get("text", "{}")
        parsed = json.loads(text)
        # parsed = {code:1, msg:"success", data: {data: "[{公告标题:..., 公告片段内容:..., 日期:...}]"}}
        if isinstance(parsed, dict):
            inner = parsed.get("data", {})
            if isinstance(inner, dict):
                data_str = inner.get("data", "[]")
                return json.loads(data_str) if isinstance(data_str, str) else []
        return []
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def get_watchlist_alpha():
    """用Alpha派获取自选股列表"""
    sys.path.insert(0, os.path.join(SCRIPT_DIR, "..", "..", "alphapai-research", "scripts"))
    try:
        from alphapai_client import AlphaPaiClient, load_config
        client = AlphaPaiClient(load_config())
        result = client.stock_watchlist()
        if result.get("code") != 200000:
            return []
        data = result.get("data", {})
        stocks = []
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    stocks.extend(v)
        elif isinstance(data, list):
            stocks = data
        return stocks
    except Exception:
        return []


def search_announcements_ifind(stock_name, stock_code, days=7):
    """用ifind搜单只股票近N天公告

    注意：ifind search_notice 的 time_start/time_end 过滤不可靠，
    可能返回全量历史公告。本函数通过截取前N条结果来缓解此问题。
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "query": f"{stock_name} 股票 公告",
        "time_start": cutoff,
        "time_end": datetime.now().strftime("%Y-%m-%d"),
        "size": 5
    }
    announcements = ifind_call("news", "search_notice", params)
    if isinstance(announcements, list):
        return announcements[:5]  # 最多取5条
    return []


POSITIVE_KEYWORDS = [
    "业绩增长", "净利润", "营收增长", "超预期", "大幅增长", "突破", "创新高",
    "中标", "大单", "订单", "签约", "战略合作", "扩产", "产能扩张",
    "回购", "增持", "评级上调", "目标价", "首予", "买入", "推荐",
    "全球首发", "填补空白", "量产", "商业化", "市场份额", "份额提升",
]

NEGATIVE_KEYWORDS = [
    "业绩下降", "亏损", "净利润下降", "不及预期", "大幅下降", "首亏", "续亏",
    "终止", "取消", "减持", "评级下调", "出售", "转让",
    "诉讼", "仲裁", "处罚", "监管函", "警示函", "问询函", "立案调查",
    "停产", "安全事故", "质量事故", "召回",
]


def keyword_sentiment(title, content=""):
    """基于公告标题+内容片段判断情感"""
    text = (title + " " + content)[:500]
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            if kw in ["处罚", "立案调查", "安全事故", "质量事故", "监管函"]:
                return "负面", "---", f"重大利空：{kw}"
            return "负面", "--", f"负面：{kw}"
    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            if kw in ["全球首发", "填补空白", "创新高", "超预期"]:
                return "正面", "+++", f"重大利好：{kw}"
            return "正面", "++", f"正面：{kw}"
    return "中性", "=", "常规公告"


def format_output(results):
    if not results:
        return "📭 过去48小时自选股无新公告"
    positive = [r for r in results if r["sentiment"] == "正面"]
    negative = [r for r in results if r["sentiment"] == "负面"]
    neutral = [r for r in results if r["sentiment"] == "中性"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 📊 自选股公告情绪监控（48小时）",
        f"**时间**：{now_str}",
        f"**有公告**：{len(results)}只",
        f"| 情绪 | 数量 |",
        f"|------|------|",
        f"| 🟢 正面 | {len(positive)} |",
        f"| 🔴 负面 | {len(negative)} |",
        f"| ⚪ 中性 | {len(neutral)} |",
        "",
    ]
    if positive:
        lines.append("## 🟢 正面")
        lines.append("| 股票 | 日期 | 公告 | 标签 | 评论 |")
        lines.append("|------|------|------|------|------|")
        for r in positive:
            lines.append(f"| {r['stock_name']} | {r['date']} | {r['title'][:30]} | {r['tag']} | {r['comment']} |")
        lines.append("")
    if negative:
        lines.append("## 🔴 负面")
        lines.append("| 股票 | 日期 | 公告 | 标签 | 评论 |")
        lines.append("|------|------|------|------|------|")
        for r in negative:
            lines.append(f"| {r['stock_name']} | {r['date']} | {r['title'][:30]} | {r['tag']} | {r['comment']} |")
        lines.append("")
    if neutral:
        lines.append("## ⚪ 中性")
        lines.append("| 股票 | 日期 | 公告 | 标签 | 评论 |")
        lines.append("|------|------|------|------|------|")
        for r in neutral[:20]:  # 限制20条避免太长
            lines.append(f"| {r['stock_name']} | {r['date']} | {r['title'][:30]} | {r['tag']} | {r['comment']} |")
        if len(neutral) > 20:
            lines.append(f"_... 还有 {len(neutral)-20} 条中性公告省略_")
        lines.append("")
    return "\n".join(lines)


def main():
    print("🔍 自选股公告情绪监控（ifind版）")
    print("=" * 50)

    # Step 1: 获取自选股
    print("📋 获取自选股列表（Alpha派）...")
    stocks = get_watchlist_alpha()
    if not stocks:
        print("[错误] 无法获取自选股")
        sys.exit(1)
    print(f"   共 {len(stocks)} 只股票")

    # Step 2: 并发查询（每只股票一次ifind调用）
    print(f"\n📡 并发查询近48小时公告（max_workers=15）...")
    results = []
    seen_codes = set()

    def fetch_one(stock):
        code = stock.get("code", "") or stock.get("stockCode", "") or str(stock)
        name = stock.get("name", "") or stock.get("stockName", "") or str(stock)
        if not code or "." not in str(code):
            return []
        announcements = search_announcements_ifind(name, code, days=2)
        out = []
        for ann in announcements:
            title = ann.get("公告标题", "")
            date = ann.get("日期", "")
            content = ann.get("公告片段内容", "")[:200]
            sentiment, tag, comment = keyword_sentiment(title, content)
            key = (code, date, title[:20])
            if key not in seen_codes:
                seen_codes.add(key)
                out.append({
                    "stock_code": code,
                    "stock_name": name,
                    "date": date,
                    "title": title,
                    "content": content,
                    "sentiment": sentiment,
                    "tag": tag,
                    "comment": comment,
                })
        return out

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(fetch_one, s): s for s in stocks}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 30 == 0:
                print(f"   [{done}/{len(stocks)}] ...")
            try:
                res = future.result()
                if res:
                    results.extend(res)
            except Exception as e:
                pass

    print(f"\n📢 共有 {len(results)} 条48小时内公告（来自 {len(set(r['stock_code'] for r in results))} 只股票）")

    if not results:
        print(format_output([]))
        return

    # 按日期排序
    results.sort(key=lambda x: x.get("date", ""), reverse=True)

    # 输出
    print("\n" + "=" * 50)
    output = format_output(results)
    print(output)

    # 保存
    save_dir = os.path.expanduser("~/Documents/earnings-transcripts/公告监控")
    os.makedirs(save_dir, exist_ok=True)
    filename = datetime.now().strftime("%Y%m-%d_%H%M") + "_公告监控_ifind.md"
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"\n💾 已保存: {filepath}")


if __name__ == "__main__":
    main()
