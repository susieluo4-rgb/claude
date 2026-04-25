#!/usr/bin/env python3
"""
Outlook 日历操作脚本 - 世纪互联版
支持查看/创建/更新/删除日程和会议
"""
import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent))
from outlook_auth import get_valid_token, GRAPH_BASE_URL

# 中国时区
CST = timezone(timedelta(hours=8))


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


def parse_datetime(dt_str):
    """解析 ISO datetime 字符串"""
    if not dt_str:
        return None
    try:
        # 处理 2026-04-26T14:00:00Z 格式
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def format_datetime(dt):
    """格式化为易读形式"""
    if not dt:
        return "N/A"
    return dt.astimezone(CST).strftime("%Y-%m-%d %H:%M")


def list_events(token, start, end, top=50):
    """获取日程列表"""
    path = "/me/calendarView"
    params = {
        "startDateTime": start.isoformat(),
        "endDateTime": end.isoformat(),
        "$top": top,
        "$orderby": "start/dateTime",
        "$select": "id,subject,start,end,location,isAllDay,showAs,bodyPreview,attendees,organizer"
    }

    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

    events = []
    for ev in data.get("value", []):
        start_dt = parse_datetime(ev.get("start", {}).get("dateTime", ""))
        end_dt = parse_datetime(ev.get("end", {}).get("dateTime", ""))

        events.append({
            "id": ev.get("id"),
            "subject": ev.get("subject", "(无标题)"),
            "start": format_datetime(start_dt),
            "end": format_datetime(end_dt),
            "start_iso": ev.get("start", {}).get("dateTime", ""),
            "end_iso": ev.get("end", {}).get("dateTime", ""),
            "location": ev.get("location", {}).get("displayName", ""),
            "isAllDay": ev.get("isAllDay", False),
            "showAs": ev.get("showAs", ""),
            "preview": ev.get("bodyPreview", ""),
            "organizer": ev.get("organizer", {}).get("emailAddress", {}).get("name", ""),
            "attendees_count": len(ev.get("attendees", []))
        })
    return events, ""


def get_today_events(token):
    """今日日程"""
    today = datetime.now(CST).date()
    start = datetime.combine(today, datetime.min.time()).replace(tzinfo=CST)
    end = datetime.combine(today, datetime.max.time()).replace(tzinfo=CST)
    return list_events(token, start, end)


def get_week_events(token):
    """本周日程"""
    today = datetime.now(CST).date()
    start_monday = today - timedelta(days=today.weekday())
    end_sunday = start_monday + timedelta(days=6)

    start = datetime.combine(start_monday, datetime.min.time()).replace(tzinfo=CST)
    end = datetime.combine(end_sunday, datetime.max.time()).replace(tzinfo=CST)
    return list_events(token, start, end)


def read_event(token, event_id):
    """读取日程详情"""
    path = f"/me/events/{event_id}"
    params = {
        "$select": "id,subject,start,end,location,isAllDay,showAs,body,attendees,organizer,isOnlineMeeting,onlineMeeting"
    }

    data, err = api_call("GET", path, token, params=params)
    if err:
        return None, err

    start_dt = parse_datetime(data.get("start", {}).get("dateTime", ""))
    end_dt = parse_datetime(data.get("end", {}).get("dateTime", ""))

    attendees = []
    for att in data.get("attendees", []):
        attendees.append({
            "name": att.get("emailAddress", {}).get("name", ""),
            "email": att.get("emailAddress", {}).get("address", ""),
            "status": att.get("status", {}).get("response", "none")
        })

    return {
        "id": data.get("id"),
        "subject": data.get("subject", "(无标题)"),
        "start": format_datetime(start_dt),
        "end": format_datetime(end_dt),
        "start_iso": data.get("start", {}).get("dateTime", ""),
        "end_iso": data.get("end", {}).get("dateTime", ""),
        "location": data.get("location", {}).get("displayName", ""),
        "isAllDay": data.get("isAllDay", False),
        "showAs": data.get("showAs", ""),
        "body": data.get("body", {}).get("content", "")[:500],
        "organizer": data.get("organizer", {}).get("emailAddress", {}).get("name", ""),
        "attendees": attendees,
        "isOnlineMeeting": data.get("isOnlineMeeting", False),
        "meetingUrl": data.get("onlineMeeting", {}).get("joinUrl", "") if data.get("isOnlineMeeting") else ""
    }, ""


def create_event(token, subject, start_iso, end_iso, body=None, location=None, attendees=None):
    """创建日程"""
    event = {
        "subject": subject,
        "start": {"dateTime": start_iso, "timeZone": "Asia/Shanghai"},
        "end": {"dateTime": end_iso, "timeZone": "Asia/Shanghai"},
        "showAs": "busy"
    }

    if body:
        event["body"] = {"contentType": "text", "content": body}
    if location:
        event["location"] = {"displayName": location}
    if attendees:
        event["attendees"] = [{"emailAddress": {"address": a}, "type": "required"} for a in attendees]

    data, err = api_call("POST", "/me/events", token, data=event)
    if err:
        return None, err

    return {
        "id": data.get("id"),
        "subject": data.get("subject"),
        "start": data.get("start", {}).get("dateTime", ""),
        "end": data.get("end", {}).get("dateTime", "")
    }, ""


def quick_create(token, subject, start_iso, duration_hours=1):
    """快速创建1小时日程"""
    start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    start = start.astimezone(CST)
    end = start + timedelta(hours=duration_hours)

    start_str = start.strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end.strftime("%Y-%m-%dT%H:%M:%S")

    return create_event(token, subject, start_str, end_str)


def update_event(token, event_id, **kwargs):
    """更新日程"""
    update_data = {}

    if "subject" in kwargs:
        update_data["subject"] = kwargs["subject"]
    if "start" in kwargs:
        update_data["start"] = {"dateTime": kwargs["start"], "timeZone": "Asia/Shanghai"}
    if "end" in kwargs:
        update_data["end"] = {"dateTime": kwargs["end"], "timeZone": "Asia/Shanghai"}
    if "body" in kwargs:
        update_data["body"] = {"contentType": "text", "content": kwargs["body"]}
    if "location" in kwargs:
        update_data["location"] = {"displayName": kwargs["location"]}

    data, err = api_call("PATCH", f"/me/events/{event_id}", token, data=update_data)
    if err:
        return None, err

    return {"success": True, "event_id": event_id}, ""


def delete_event(token, event_id):
    """删除日程"""
    _, err = api_call("DELETE", f"/me/events/{event_id}", token)
    if err:
        return None, err
    return {"success": True, "event_id": event_id}, ""


def list_calendars(token):
    """列出所有日历"""
    data, err = api_call("GET", "/me/calendars", token)
    if err:
        return None, err

    calendars = []
    for cal in data.get("value", []):
        calendars.append({
            "id": cal.get("id"),
            "name": cal.get("name"),
            "color": cal.get("hexColor", ""),
            "isDefault": cal.get("isDefaultCalendar", False)
        })
    return calendars, ""


def query_freebusy(token, email, start_iso, end_iso):
    """查询忙闲状态"""
    body = {
        "timeSlotInterval": "PT30M",
        "availabilityViewInterval": "PT30M",
        "sessions": [{
            "email": email,
            "viewKind": 1
        }],
        "startTime": {"dateTime": start_iso, "timeZone": "Asia/Shanghai"},
        "endTime": {"dateTime": end_iso, "timeZone": "Asia/Shanghai"}
    }

    data, err = api_call("POST", "/me/calendar/getSchedule", token, data=body)
    if err:
        return None, err

    schedules = data.get("value", [])
    if not schedules:
        return [], ""

    slots = []
    for schedule in schedules:
        for item in schedule.get("scheduleItems", []):
            start_dt = parse_datetime(item.get("start", ""))
            end_dt = parse_datetime(item.get("end", ""))
            slots.append({
                "subject": item.get("subject", "忙"),
                "start": format_datetime(start_dt),
                "end": format_datetime(end_dt),
                "status": item.get("status", ""),
                "isPrivate": item.get("isPrivate", False)
            })

    return {
        "email": email,
        "slots": slots
    }, ""


def format_events_list(events):
    """格式化日程列表"""
    if not events:
        return "没有日程"

    lines = []
    current_date = ""
    for ev in events:
        date_str = ev.get("start", "")[:10]
        if date_str != current_date:
            current_date = date_str
            lines.append(f"\n📅 {date_str}")
            lines.append("-" * 40)

        start = ev.get("start", "")[11:16] if len(ev.get("start", "")) > 16 else ""
        end = ev.get("end", "")[11:16] if len(ev.get("end", "")) > 16 else ""
        allday = " [全天]" if ev.get("isAllDay") else ""
        loc = f" 📍{ev['location']}" if ev.get("location") else ""
        att = f" 👥{ev['attendees_count']}" if ev.get("attendees_count", 0) > 0 else ""

        lines.append(f"  ⏰ {start}-{end}{allday} {ev.get('subject', '')}{loc}{att}")

    return "\n".join(lines)


if __name__ == "__main__":
    token, _, _ = get_valid_token()
    if not token:
        print("错误: 无法获取 token，请先完成授权")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "today"
    args = sys.argv[2:]

    result = None
    error = ""

    if cmd == "today":
        result, error = get_today_events(token)

    elif cmd == "week":
        result, error = get_week_events(token)

    elif cmd == "events":
        if len(args) < 2:
            print("用法: events <开始ISO时间> <结束ISO时间>")
            print("例: events 2026-04-25T00:00:00 2026-04-30T23:59:59")
            sys.exit(1)
        start = datetime.fromisoformat(args[0].replace("Z", "+00:00")).astimezone(CST)
        end = datetime.fromisoformat(args[1].replace("Z", "+00:00")).astimezone(CST)
        result, error = list_events(token, start, end)

    elif cmd == "read":
        if not args:
            print("用法: read <日程ID>")
            sys.exit(1)
        result, error = read_event(token, args[0])

    elif cmd == "create":
        if len(args) < 4:
            print("用法: create <标题> <开始时间> <结束时间> [内容]")
            print("例: create '团队会议' '2026-04-26 14:00' '2026-04-26 15:00' '讨论Q2计划'")
            sys.exit(1)
        result, error = create_event(token, args[0], args[1], args[2], args[3] if len(args) > 3 else None)

    elif cmd == "quick":
        if len(args) < 2:
            print("用法: quick <标题> <开始时间> [时长(小时)]")
            print("例: quick '快速会议' '2026-04-26 14:00' 1")
            sys.exit(1)
        duration = int(args[2]) if len(args) > 2 else 1
        result, error = quick_create(token, args[0], args[1], duration)

    elif cmd == "update":
        if len(args) < 3:
            print("用法: update <日程ID> <field> <value>")
            sys.exit(1)
        result, error = update_event(token, args[0], **{args[1]: args[2]})

    elif cmd == "delete":
        if not args:
            print("用法: delete <日程ID>")
            sys.exit(1)
        result, error = delete_event(token, args[0])

    elif cmd == "calendars":
        result, error = list_calendars(token)

    elif cmd == "freebusy":
        if len(args) < 3:
            print("用法: freebusy <邮箱> <开始时间> <结束时间>")
            print("例: freebusy 'user@company.com' '2026-04-26 09:00' '2026-04-26 18:00'")
            sys.exit(1)
        result, error = query_freebusy(token, args[0], args[1], args[2])

    else:
        print(f"未知命令: {cmd}")
        print("用法: outlook_calendar.py <today|week|events|read|create|quick|update|delete|calendars|freebusy> [参数]")
        sys.exit(1)

    if error:
        print(f"错误: {error}")
        sys.exit(1)

    if result is not None:
        if isinstance(result, list) and result and "start" in result[0]:
            # 是日程列表，用友好格式输出
            print(format_events_list(result))
        elif isinstance(result, dict) and "slots" in result:
            # 忙闲查询
            print(f"📊 {result['email']} 的日程:")
            for slot in result.get("slots", []):
                print(f"  {slot['start']} - {slot['end']}: {slot['subject']}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
