#!/usr/bin/env python3
"""
Outlook Wind 文件夹增量拉取脚本
从 Outlook 3.Broker Report/Wind 文件夹拉取券商报告邮件，解析并落入 Raw 仓库

数据流：
  Outlook Wind 文件夹 → list_folder_messages() → read_message() → raw/broker_reports/
  持仓匹配: save_to_raw() 中按持仓公司过滤

触发方式：
  每2小时 Cron: 0 */2 * * * python3 .../email_incremental_scan.py >> .../logs/email_scan.log 2>&1
  手动干跑: python3 .../email_incremental_scan.py --dry-run
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# 共享报告模块
sys.path.insert(0, str(Path(__file__).parent))
from rl_radar_report import build_report, send_report

# ========== 路径常量 ==========
VAULT_COMPANY_LIST = "/Users/zhuang225/Research/Vault_公司基本面Agent/11_公司列表"
RAW_DEST = Path("/Users/zhuang225/Research/Vault_共享知识库/raw")
RAW_BROKER_REPORTS = RAW_DEST / "broker_reports"
RAW_NOTES = RAW_DEST / "notes"
RAW_LOGS = RAW_DEST / "logs"
LAST_SYNC_FILE = RAW_DEST / "last_wind_sync.json"

# Wind 文件夹 ID（3.Broker Report/Wind）
WIND_FOLDER_ID = "AAMkAGY4YTZmYzk4LWQ2ZGItNGZkOS1iOGU5LTM0Nzc1MzM1MWYyMgAuAAAAAABX5NYTIBJXTZkkPEe4uTx4AQDZPRXOogd1RaaQO7mRC0GQAASA5eUMAAA="

# 持仓公司列表 (名称 → 代码)
PORTFOLIO_COMPANIES = {
    "戈碧迦": "920438.BJ",
    "阜博集团": "3738.HK",
    "迈富时": "2556.HK",
    "美图公司": "1357.HK",
    "金蝶国际": "0268.HK",
    "深信服": "300454.SZ",
    "航宇科技": "688239.SH",
    "景旺电子": "603228.SH",
    "范式智能": "6682.HK",
    "圣邦股份": "300661.SZ",
    "太辰光": "300570.SZ",
    "迅捷兴": "688655.SH",
    "FORTIOR": "1304.HK",
    "新雷能": "300593.SZ",
    "铂力特": "688333.SH",
    "陕西华达": "301517.SZ",
    "瑞芯微": "603893.SH",
    "鼎阳科技": "688112.SH",
    "英诺赛科": "2577.HK",
    "通合科技": "300491.SZ",
    "沪电股份": "002463.SZ",
    "鸿泉物联": "688288.SH",
    "华力创通": "300045.SZ",
    "信科移动": "688387.SH",
    "致尚科技": "301486.SZ",
    "泡泡玛特": "9992.HK",
    "耐普矿机": "300818.SZ",
    "耐世特": "01316.HK",
    "中芯国际": "688981.SH",
    "比亚迪": "002594.SZ",
    "百济神州": "688235.SH",
    "地平线机器人": "9660.HK",
    "福耀玻璃": "600660.SH",
    "禾赛科技": "HSAI",
    "恒瑞医药": "600276.SH",
    "和黄医药": "00013.HK",
    "康方生物": "09926.HK",
    "康龙化成": "300759.SZ",
    "科伦博泰": "06990.HK",
    "科博达": "603786.SH",
    "凯莱英": "002821.SZ",
    "宁德时代": "300750.SZ",
    "荃信生物": "02509.HK",
    "速腾聚创": "02498.HK",
    "泰格医药": "300347.SZ",
    "星宇股份": "601799.SH",
    "信达生物": "01801.HK",
    "药明康德": "603259.SH",
    "药明生物": "02269.HK",
    "药明合联": "02268.HK",
    "中集安瑞科": "03899.HK",
}


# ========== Outlook Graph API 调用（内联，避免外部依赖）==========

def get_valid_token():
    """从 outlook_auth.py 获取有效 token"""
    cred_path = Path.home() / ".outlook-microsoft" / "credentials.json"
    if not cred_path.exists():
        return None, None, None
    try:
        with open(cred_path) as f:
            creds = json.load(f)
        token = creds.get("access_token")
        return token, None, None
    except Exception:
        return None, None, None


GRAPH_BASE_URL = "https://microsoftgraph.chinacloudapi.cn"


def api_call(method, path, token, data=None, params=None):
    """调用 Microsoft Graph API"""
    import requests
    url = f"{GRAPH_BASE_URL}/v1.0{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PATCH":
            resp = requests.patch(url, headers=headers, json=data, timeout=30)
        else:
            return None, f"不支持的方法: {method}"
    except Exception as e:
        return None, f"网络错误: {e}"

    if resp.status_code == 401:
        return None, "AUTH: Token 失效"

    if not resp.ok:
        try:
            err = resp.json()
            return None, f"API错误: {err.get('error', {}).get('message', resp.text[:100])}"
        except Exception:
            return None, f"HTTP {resp.status_code}"

    return resp.json() if resp.text else {}, ""


def list_folder_messages(token, folder_id, top=50, days_back=2):
    """列出指定文件夹中的邮件"""
    cutoff = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z"
    params = {
        "$top": top,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,receivedDateTime,isRead,hasAttachments,bodyPreview",
        "$filter": f"receivedDateTime ge {cutoff}"
    }
    path = f"/me/mailFolders/{folder_id}/messages"
    data, err = api_call("GET", path, token, params=params)
    if err:
        return [], err

    messages = data.get("value", [])
    result = []
    for msg in messages:
        result.append({
            "id": msg.get("id"),
            "subject": msg.get("subject", "(无主题)"),
            "from": msg.get("from", {}).get("emailAddress", {}).get("name", ""),
            "from_email": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
            "received": msg.get("receivedDateTime", ""),
            "isRead": msg.get("isRead", True),
            "hasAttachments": msg.get("hasAttachments", False),
            "preview": msg.get("bodyPreview", "")
        })
    return result, ""


def read_message_detail(token, msg_id):
    """读取邮件完整内容（含 body）"""
    params = {
        "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,isRead,hasAttachments,body,attachments"
    }
    path = f"/me/messages/{msg_id}"
    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

    body_content = ""
    body_raw = data.get("body", {}).get("content", "")
    body_type = data.get("body", {}).get("contentType", "")

    if body_type == "text":
        body_content = body_raw
    elif body_type == "html":
        # 去除 HTML 标签
        body_content = re.sub(r'<[^>]+>', ' ', body_raw)
        body_content = re.sub(r'\s+', ' ', body_content).strip()

    attachments = []
    for att in data.get("attachments", []):
        attachments.append({
            "id": att.get("id"),
            "name": att.get("name", "未命名"),
            "size": att.get("size", 0),
            "type": att.get("@odata.type", "").split(".")[-1]
        })

    return {
        "id": data.get("id"),
        "subject": data.get("subject", "(无主题)"),
        "from": data.get("from", {}).get("emailAddress", {}).get("name", ""),
        "from_email": data.get("from", {}).get("emailAddress", {}).get("address", ""),
        "to": [r.get("emailAddress", {}).get("address", "") for r in data.get("toRecipients", [])],
        "received": data.get("receivedDateTime", ""),
        "isRead": data.get("isRead", True),
        "hasAttachments": data.get("hasAttachments", False),
        "body": body_content[:5000],
        "attachments": attachments
    }, ""


# ========== 同步状态 ==========

def get_last_sync() -> Optional[Dict]:
    """读取上次同步状态"""
    if not Path(LAST_SYNC_FILE).exists():
        return None
    try:
        with open(LAST_SYNC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_last_sync(last_received: str, count: int):
    """保存当前同步状态"""
    Path(LAST_SYNC_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_SYNC_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "last_received": last_received,
            "count": count,
            "updated": datetime.now().isoformat()
        }, f, ensure_ascii=False)


# ========== Wind 邮件解析 ==========

def parse_wind_email(subject: str, body: str, sender: str) -> Dict[str, Any]:
    """
    解析 Wind 券商报告邮件
    返回: {"reports": [], "announcements": [], "is_relevant": bool, "summary": str}
    """
    result = {
        "reports": [],     # 研报/分析报告
        "announcements": [],  # 公告/数据
        "is_relevant": False,
        "summary": body[:200] if body else subject
    }

    # 提取股票代码（支持 A股/港股/美股格式）
    stock_codes = re.findall(r'\b\d{4,6}\.[A-Z]{2}\b', subject + " " + body)
    stock_codes += re.findall(r'\b[0-9]{4,6}\b', subject + " " + body)

    # 匹配持仓公司
    matched_companies = []
    for name, code in PORTFOLIO_COMPANIES.items():
        if name in subject or name in body:
            matched_companies.append((name, code, "name"))
        elif code.split(".")[0] in (subject + " " + body):
            matched_companies.append((name, code, "code"))

    if matched_companies:
        result["is_relevant"] = True
        # 去重
        seen = set()
        unique = []
        for c in matched_companies:
            if c[0] not in seen:
                seen.add(c[0])
                unique.append(c)
        result["matched_companies"] = unique

    # 判断内容类型
    text = (subject + " " + body).lower()
    if any(kw in text for kw in ["研报", "报告", "评级", "目标价", "观点", "首次覆盖", "增持", "买入", "推荐"]):
        result["type"] = "research_report"
    elif any(kw in text for kw in ["公告", "年报", "季报", "半年报", "业绩", "分红", "利润"]):
        result["type"] = "announcement"
    elif any(kw in text for kw in ["数据", "宏观", "行业", "策略", "周报", "月报"]):
        result["type"] = "macro_industry"
    else:
        result["type"] = "other"

    return result


# ========== Raw 写入 ==========

def save_to_raw(msg: Dict, parsed: Dict):
    """将 Wind 邮件保存到 Raw 仓库"""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    RAW_BROKER_REPORTS.mkdir(parents=True, exist_ok=True)
    RAW_NOTES.mkdir(parents=True, exist_ok=True)

    received = msg.get("received", "")[:10]  # YYYY-MM-DD
    subject = msg.get("subject", "无主题")[:50]
    safe_subject = re.sub(r'[\\/:*?"<>|]', '_', subject)

    # 关联持仓公司
    companies = []
    if parsed.get("matched_companies"):
        companies = [c[0] for c in parsed["matched_companies"]]

    filepath = RAW_BROKER_REPORTS / f"wind_{received}_{ts}_{safe_subject}.md"

    lines = [
        f"# Wind 券商报告 — {received}",
        f"**主题**: {subject}",
        f"**发件人**: {msg.get('from', '')}",
        f"**收件时间**: {msg.get('received', '')}",
        f"**类型**: {parsed.get('type', 'unknown')}",
    ]
    if companies:
        lines.append(f"**持仓关联**: {', '.join(companies)}")
    lines.append("")
    lines.append("## 正文")
    lines.append(parsed.get("summary", ""))
    if parsed.get("is_relevant"):
        lines.append("")
        lines.append("## 持仓相关公司")
        for name, code, match_type in parsed.get("matched_companies", []):
            lines.append(f"- **{name}** ({code}) — 命中方式: {match_type}")

    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


# ========== 持仓优先级报告 ==========

def generate_portfolio_priority_report(all_parsed: List[Dict]) -> str:
    """根据持仓公司生成优先级报告"""
    priority_items = []

    for parsed in all_parsed:
        if not parsed.get("is_relevant"):
            continue
        for name, code, _ in parsed.get("matched_companies", []):
            ptype = parsed.get("type", "other")
            if ptype == "research_report":
                level = "🟡 中"
                reason = "券商研报"
            elif ptype == "announcement":
                level = "🔴 高"
                reason = "公司公告"
            else:
                level = "🟢 低"
                reason = "行业/宏观"
            subject = parsed.get("msg", {}).get("subject", "")[:60] if parsed.get("msg") else ""
            priority_items.append({
                "level": level,
                "company": name,
                "code": code,
                "type": ptype,
                "subject": subject,
                "reason": reason,
            })

    if not priority_items:
        return "**无持仓相关重要信息**\n"

    order = {"🔴 高": 0, "🟡 中": 1, "🟢 低": 2}
    priority_items.sort(key=lambda x: (order.get(x["level"], 2), x["company"]))

    lines = ["## 📊 持仓相关优先级排序\n"]
    lines.append("| 优先级 | 公司 | 代码 | 类型 | 标题 |")
    lines.append("|--------|------|------|------|------|")
    for item in priority_items:
        lines.append(
            f"| {item['level']} | {item['company']} | {item['code']} "
            f"| {item['type']} | {item['subject']} |"
        )

    high = sum(1 for x in priority_items if x["level"] == "🔴 高")
    mid = sum(1 for x in priority_items if x["level"] == "🟡 中")
    low = sum(1 for x in priority_items if x["level"] == "🟢 低")
    lines.append(f"\n**汇总**：🔴 高 {high} 条 | 🟡 中 {mid} 条 | 🟢 低 {low} 条")
    return "\n".join(lines)


# ========== 主流程 ==========

def scan_wind_folder(dry_run: bool = False) -> Dict[str, Any]:
    """扫描 Wind 文件夹并落入 Raw"""
    token, _, _ = get_valid_token()
    if not token:
        return {"error": "无法获取 Outlook token，请先运行 outlook_auth.py authorize"}

    last_sync = get_last_sync()
    last_received = last_sync.get("last_received") if last_sync else None
    print(f"📧 上次同步时间: {last_received or '无'}")

    # 获取近2天邮件（最多50封）
    messages, err = list_folder_messages(token, WIND_FOLDER_ID, top=50, days_back=2)
    if err:
        return {"error": err}

    print(f"📬 近2天共获取 {len(messages)} 封 Wind 文件夹邮件")

    # 过滤：跳过已处理的（按 receivedDateTime）
    new_messages = []
    for msg in messages:
        received = msg.get("received", "")
        if last_received and received <= last_received:
            continue
        new_messages.append(msg)

    print(f"🆕 新邮件: {len(new_messages)} 封")

    if dry_run:
        for m in new_messages:
            print(f"  [干跑] {m['received'][:10]} | {m['from'][:20]} | {m['subject'][:50]}")
        return {"dry_run": True, "count": len(new_messages)}

    all_saved = []
    processed = []
    all_parsed = []

    for msg in new_messages:
        msg_id = msg["id"]
        print(f"\n📧 处理: {msg['subject'][:50]}")

        detail, err = read_message_detail(token, msg_id)
        if err or not detail:
            print(f"  ❌ 读取失败: {err}")
            continue

        # 解析邮件
        parsed = parse_wind_email(
            subject=msg["subject"],
            body=detail.get("body", ""),
            sender=msg.get("from", "")
        )
        parsed["msg"] = msg
        all_parsed.append(parsed)

        # 保存到 Raw
        filepath = save_to_raw(detail, parsed)
        all_saved.append(filepath)
        processed.append(msg["received"])
        print(f"  ✅ 已保存 → {Path(filepath).name}")

    # 生成持仓优先级报告
    print("\n" + "=" * 60)
    print("📊 持仓相关优先级报告")
    print("=" * 60)
    priority_report = generate_portfolio_priority_report(all_parsed)
    print(priority_report)

    # 更新同步状态
    if processed:
        latest = max(processed)
        save_last_sync(latest, len(processed))
        print(f"\n✅ 已更新同步状态: last_received={latest}")

    return {
        "total_messages": len(messages),
        "new_messages": len(new_messages),
        "saved_files": len(all_saved),
        "saved_paths": all_saved,
        "priority_report": priority_report,
    }


def main():
    parser = argparse.ArgumentParser(description="Outlook Wind 文件夹增量拉取")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不保存文件")
    parser.add_argument("--days", type=int, default=2, help="拉取最近几天邮件(默认2)")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件报告（手动触发时使用）")
    args = parser.parse_args()

    RAW_LOGS.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("📡 Outlook Wind 文件夹增量拉取 — " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    result = scan_wind_folder(dry_run=args.dry_run)

    if "error" in result:
        print(f"❌ 错误: {result['error']}")
        return 1

    if args.dry_run:
        print(f"\n🔍 干跑完成: 发现 {result['count']} 封新邮件")
        return 0

    # 构建报告
    priority_report = result.get("priority_report", "**无持仓相关重要信息**\n")
    report = build_report(
        scan_type="wind_folder_incremental_scan",
        summary={
            "total_messages": result["total_messages"],
            "new_messages": result["new_messages"],
            "saved_files": result["saved_files"],
        },
        files=[{"path": p, "action": "saved"} for p in result.get("saved_paths", [])],
        errors=[],
        next_actions=[],
    )
    report["email_body_extra"] = priority_report

    send_email = not args.no_email
    send_report(report, send_email=send_email, send_stdout=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
