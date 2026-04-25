#!/usr/bin/env python3
"""
Outlook 邮件操作脚本 - 世纪互联版
支持读取/搜索/标记/发送邮件
"""
import json
import os
import sys
import requests
import re
import base64
from pathlib import Path
from datetime import datetime

# 导入认证模块
sys.path.insert(0, str(Path(__file__).parent))
from outlook_auth import get_valid_token, get_env_client_id, GRAPH_BASE_URL


def api_call(method, path, token, data=None, params=None):
    """调用 Microsoft Graph API"""
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
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            return None, f"不支持的 HTTP 方法: {method}"
    except requests.exceptions.RequestException as e:
        return None, f"网络错误: {e}"

    if resp.status_code == 401:
        return None, "AUTH_002: Token 已失效，请运行 outlook_auth.py refresh"

    if not resp.ok:
        try:
            err = resp.json()
            return None, f"API_002: {err.get('error', {}).get('message', resp.text)[:100]}"
        except Exception:
            return None, f"API_002: HTTP {resp.status_code}"

    return resp.json() if resp.text else {}, ""


def list_inbox(token, top=10, filter_unread=False):
    """读取收件箱"""
    path = "/me/mailFolders/inbox/messages"
    params = {
        "$top": top,
        "$orderby": "receivedDateTime desc",
        "$select": "id,subject,from,toRecipients,receivedDateTime,isRead,hasAttachments,importance,bodyPreview"
    }
    if filter_unread:
        params["$filter"] = "isRead eq false"

    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

    messages = data.get("value", [])
    result = []
    for msg in messages:
        result.append({
            "id": msg.get("id"),
            "subject": msg.get("subject", "(无主题)"),
            "from": msg.get("from", {}).get("emailAddress", {}).get("name", ""),
            "from_email": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
            "to": [r.get("emailAddress", {}).get("address", "") for r in msg.get("toRecipients", [])],
            "received": msg.get("receivedDateTime", ""),
            "isRead": msg.get("isRead", True),
            "hasAttachments": msg.get("hasAttachments", False),
            "importance": msg.get("importance", "normal"),
            "preview": msg.get("bodyPreview", "")
        })
    return result, ""


def search_messages(token, query, top=10):
    """搜索邮件"""
    path = "/me/mailFolders/inbox/messages"
    params = {
        "$top": top,
        "$orderby": "receivedDateTime desc",
        "$search": f'"{query}"',
        "$select": "id,subject,from,toRecipients,receivedDateTime,isRead,hasAttachments,importance,bodyPreview"
    }

    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

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


def get_messages_from(token, sender, top=10):
    """按发件人筛选"""
    # URL encode the sender email
    path = f"/me/mailFolders/inbox/messages"
    params = {
        "$top": top,
        "$orderby": "receivedDateTime desc",
        "$filter": f"from/emailAddress/address eq '{sender}'",
        "$select": "id,subject,from,toRecipients,receivedDateTime,isRead,hasAttachments,importance,bodyPreview"
    }

    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

    messages = data.get("value", [])
    result = []
    for msg in messages:
        result.append({
            "id": msg.get("id"),
            "subject": msg.get("subject", "(无主题)"),
            "from": msg.get("from", {}).get("emailAddress", {}).get("name", ""),
            "from_email": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
            "to": [r.get("emailAddress", {}).get("address", "") for r in msg.get("toRecipients", [])],
            "received": msg.get("receivedDateTime", ""),
            "isRead": msg.get("isRead", True),
            "hasAttachments": msg.get("hasAttachments", False),
            "preview": msg.get("bodyPreview", "")
        })
    return result, ""


def read_message(token, msg_id):
    """读取邮件详情"""
    path = f"/me/messages/{msg_id}"
    params = {
        "$select": "id,subject,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,isRead,hasAttachments,importance,body,attachments"
    }

    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

    # 解析邮件正文
    body_content = ""
    body_type = data.get("body", {}).get("contentType", "")
    body_raw = data.get("body", {}).get("content", "")

    if body_type == "text":
        body_content = body_raw
    elif body_type == "html":
        # 简单提取 HTML 中的文本
        body_content = re.sub(r'<[^>]+>', ' ', body_raw)
        body_content = re.sub(r'\s+', ' ', body_content).strip()

    # 解析附件
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
        "cc": [r.get("emailAddress", {}).get("address", "") for r in data.get("ccRecipients", [])],
        "received": data.get("receivedDateTime", ""),
        "isRead": data.get("isRead", True),
        "importance": data.get("importance", "normal"),
        "hasAttachments": data.get("hasAttachments", False),
        "attachments": attachments,
        "body": body_content[:2000]  # 限制长度
    }, ""


def list_attachments(token, msg_id):
    """获取邮件附件列表"""
    path = f"/me/messages/{msg_id}/attachments"
    params = {"$select": "id,name,size,contentType,isInline"}

    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

    attachments = []
    for att in data.get("value", []):
        att_type = att.get("@odata.type", "").split(".")[-1]
        attachments.append({
            "id": att.get("id"),
            "name": att.get("name", "未命名"),
            "size": att.get("size", 0),
            "type": att_type,
            "contentType": att.get("contentType", ""),
            "isInline": att.get("isInline", False)
        })
    return attachments, ""


def mark_read(token, msg_id, read=True):
    """标记已读/未读"""
    path = f"/me/messages/{msg_id}"
    data, err = api_call("PATCH", path, token, data={"isRead": read})
    if err:
        return None, err
    return {"success": True, "msg_id": msg_id, "isRead": read}, ""


def flag_message(token, msg_id, flag=True):
    """标记重要/取消重要"""
    followup_flag = {"flagStatus": "flagged" if flag else "notFlagged"}
    data, err = api_call("PATCH", f"/me/messages/{msg_id}", token, data=followup_flag)
    if err:
        return None, err
    return {"success": True, "msg_id": msg_id, "flagged": flag}, ""


def delete_message(token, msg_id):
    """删除邮件"""
    _, err = api_call("DELETE", f"/me/messages/{msg_id}", token)
    if err:
        return None, err
    return {"success": True, "msg_id": msg_id}, ""


def move_message(token, msg_id, dest_folder_id):
    """移动邮件到文件夹"""
    path = f"/me/messages/{msg_id}/move"
    data, err = api_call("POST", path, token, data={"destinationId": dest_folder_id})
    if err:
        return None, err
    return {"success": True, "msg_id": msg_id, "newFolderId": data.get("id", "")}, ""


def archive_message(token, msg_id):
    """归档邮件"""
    # 首先获取 "归档" 文件夹 ID
    folders_data, err = api_call("GET", "/me/mailFolders", token)
    if err:
        return None, err

    archive_folder_id = None
    for folder in folders_data.get("value", []):
        if folder.get("displayName") == "Archive":
            archive_folder_id = folder.get("id")
            break

    if not archive_folder_id:
        return None, "未找到 Archive 文件夹"

    return move_message(token, msg_id, archive_folder_id)


def send_message(token, subject, to_address, body, cc=None):
    """发送邮件"""
    msg = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "text",
                "content": body
            },
            "toRecipients": [
                {"emailAddress": {"address": to_address}}
            ]
        }
    }
    if cc:
        msg["message"]["ccRecipients"] = [{"emailAddress": {"address": c}} for c in cc]

    data, err = api_call("POST", "/me/sendMail", token, data=msg)
    if err:
        return None, err
    return {"success": True, "subject": subject, "to": to_address}, ""


def reply_message(token, msg_id, body):
    """回复邮件"""
    data, err = api_call("POST", f"/me/messages/{msg_id}/reply", token, data={"message": {"body": {"contentType": "text", "content": body}}})
    if err:
        return None, err
    return {"success": True, "msg_id": msg_id}, ""


def list_folders(token):
    """列出所有邮件文件夹"""
    data, err = api_call("GET", "/me/mailFolders", token)
    if err:
        return None, err

    folders = []
    for f in data.get("value", []):
        folders.append({
            "id": f.get("id"),
            "name": f.get("displayName"),
            "unreadCount": f.get("unreadItemCount", 0),
            "totalCount": f.get("totalItemCount", 0)
        })
    return folders, ""


def get_stats(token):
    """获取邮箱统计"""
    folders, err = list_folders(token)
    if err:
        return None, err

    stats = {"folders": folders, "total_unread": sum(f.get("unreadCount", 0) for f in folders)}
    return stats, ""


def format_message_list(messages, show_preview=True):
    """格式化邮件列表输出"""
    if not messages:
        return "没有邮件"

    lines = []
    for i, msg in enumerate(messages, 1):
        read_icon = " " if msg.get("isRead", True) else "●"
        att_icon = "📎" if msg.get("hasAttachments", False) else " "
        subject = msg.get("subject", "(无主题)")[:50]
        sender = msg.get("from", "")[:20]
        received = msg.get("received", "")[:16]

        line = f"{read_icon}{att_icon} [{received}] {sender}: {subject}"
        if show_preview and msg.get("preview"):
            line += f"\n   └ {msg.get('preview', '')[:80]}"
        lines.append(line)

    return "\n".join(lines)


if __name__ == "__main__":
    token, _, _ = get_valid_token()
    if not token:
        print("错误: 无法获取 token，请先完成授权")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "inbox"
    args = sys.argv[2:]

    result = None
    error = ""

    if cmd == "inbox":
        top = int(args[0]) if args else 10
        result, error = list_inbox(token, top=top)

    elif cmd == "unread":
        top = int(args[0]) if args else 10
        result, error = list_inbox(token, top=top, filter_unread=True)

    elif cmd == "from":
        if not args:
            print("用法: from <发件人邮箱或名称>")
            sys.exit(1)
        result, error = get_messages_from(token, args[0])

    elif cmd == "search":
        if not args:
            print("用法: search <关键词>")
            sys.exit(1)
        result, error = search_messages(token, " ".join(args))

    elif cmd == "read":
        if not args:
            print("用法: read <邮件ID>")
            sys.exit(1)
        result, error = read_message(token, args[0])

    elif cmd == "attachments":
        if not args:
            print("用法: attachments <邮件ID>")
            sys.exit(1)
        result, error = list_attachments(token, args[0])

    elif cmd == "mark-read":
        if not args:
            print("用法: mark-read <邮件ID>")
            sys.exit(1)
        result, error = mark_read(token, args[0], read=True)

    elif cmd == "mark-unread":
        if not args:
            print("用法: mark-unread <邮件ID>")
            sys.exit(1)
        result, error = mark_read(token, args[0], read=False)

    elif cmd == "flag":
        if not args:
            print("用法: flag <邮件ID>")
            sys.exit(1)
        result, error = flag_message(token, args[0], flag=True)

    elif cmd == "unflag":
        if not args:
            print("用法: unflag <邮件ID>")
            sys.exit(1)
        result, error = flag_message(token, args[0], flag=False)

    elif cmd == "delete":
        if not args:
            print("用法: delete <邮件ID>")
            sys.exit(1)
        result, error = delete_message(token, args[0])

    elif cmd == "archive":
        if not args:
            print("用法: archive <邮件ID>")
            sys.exit(1)
        result, error = archive_message(token, args[0])

    elif cmd == "move":
        if len(args) < 2:
            print("用法: move <邮件ID> <目标文件夹ID>")
            sys.exit(1)
        result, error = move_message(token, args[0], args[1])

    elif cmd == "send":
        if len(args) < 3:
            print("用法: send <主题> <收件人> <正文>")
            sys.exit(1)
        result, error = send_message(token, args[0], args[1], args[2])

    elif cmd == "reply":
        if len(args) < 2:
            print("用法: reply <邮件ID> <回复内容>")
            sys.exit(1)
        result, error = reply_message(token, args[0], args[1])

    elif cmd == "folders":
        result, error = list_folders(token)

    elif cmd == "stats":
        result, error = get_stats(token)

    else:
        print(f"未知命令: {cmd}")
        print("用法: outlook_mail.py <inbox|unread|from|search|read|attachments|mark-read|mark-unread|flag|unflag|delete|archive|move|send|reply|folders|stats> [参数]")
        sys.exit(1)

    if error:
        print(f"错误: {error}")
        sys.exit(1)

    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
