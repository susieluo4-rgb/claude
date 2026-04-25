#!/usr/bin/env python3
"""
小野私人助理 - 日历模块
基于 Google Calendar MCP 实现日程管理
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List


# Google Calendar MCP 工具前缀
CALENDAR_MCP_TOOL = "mcp__claude_ai_Google_Calendar__"

# 预设的日历 ID
CALENDAR_ID = "susieluo4@gmail.com"


class CalendarModule:
    """日历模块"""

    def __init__(self):
        self.calendar_id = CALENDAR_ID

    def query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        查询日程

        params 可以包含:
        - date: "today", "tomorrow", "week", 具体日期
        """
        date_param = params.get("date", "today")
        now = datetime.now()

        if date_param == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif date_param == "tomorrow":
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif date_param == "week":
            # 本周
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        else:
            # 假设是具体日期
            try:
                date_obj = datetime.strptime(date_param, "%Y-%m-%d")
                start = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                end = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            except:
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        return {
            "success": True,
            "action": "mcp_call",
            "tool": f"{CALENDAR_MCP_TOOL}list_events",
            "params": {
                "calendarId": self.calendar_id,
                "startTime": start.isoformat(),
                "endTime": end.isoformat(),
                "pageSize": 20
            },
            "message": f"正在查询 {date_param} 的日程..."
        }

    def create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建日程

        params 可以包含:
        - title: 会议标题
        - start_time: 开始时间 (ISO 格式或自然语言)
        - end_time: 结束时间
        - description: 描述
        - attendees: 参会人员邮箱列表
        """
        title = params.get("title", "新会议")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        description = params.get("description", "")
        attendees = params.get("attendees", [])

        # 解析时间
        if not start_time:
            return {
                "success": False,
                "error": "请提供开始时间"
            }

        # 解析开始时间
        start_dt = self._parse_datetime(start_time)
        if not start_dt:
            return {
                "success": False,
                "error": f"无法解析开始时间: {start_time}，请使用 YYYY-MM-DD HH:MM 格式"
            }

        # 如果没有结束时间，默认1小时
        if end_time:
            end_dt = self._parse_datetime(end_time)
        else:
            end_dt = start_dt + timedelta(hours=1)

        if not end_dt:
            return {
                "success": False,
                "error": f"无法解析结束时间: {end_time}"
            }

        return {
            "success": True,
            "action": "mcp_call",
            "tool": f"{CALENDAR_MCP_TOOL}create_event",
            "params": {
                "calendarId": self.calendar_id,
                "summary": title,
                "startTime": start_dt.isoformat(),
                "endTime": end_dt.isoformat(),
                "description": description,
                "timeZone": "Asia/Shanghai"
            },
            "message": f"✅ 正在创建日程: {title}\n   时间: {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}"
        }

    def delete(self, event_id: str) -> Dict[str, Any]:
        """删除日程"""
        return {
            "success": True,
            "action": "mcp_call",
            "tool": f"{CALENDAR_MCP_TOOL}delete_event",
            "params": {
                "calendarId": self.calendar_id,
                "eventId": event_id
            },
            "message": "正在删除日程..."
        }

    def suggest_time(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        建议会议时间

        params 可以包含:
        - attendees: 参会人员邮箱列表
        - duration_minutes: 时长（分钟）
        - start_time: 开始搜索的时间
        - end_time: 结束搜索的时间
        """
        attendees = params.get("attendees", [self.calendar_id])
        duration = params.get("duration_minutes", 60)
        start_time = params.get("start_time")
        end_time = params.get("end_time")

        if not start_time:
            start_time = datetime.now().isoformat()
        if not end_time:
            end_time = (datetime.now() + timedelta(days=7)).isoformat()

        attendees_param = ",".join(attendees) if isinstance(attendees, list) else attendees

        return {
            "success": True,
            "action": "mcp_call",
            "tool": f"{CALENDAR_MCP_TOOL}suggest_time",
            "params": {
                "attendeeEmails": attendees,
                "durationMinutes": duration,
                "startTime": start_time,
                "endTime": end_time
            },
            "message": f"正在搜索 {duration} 分钟的空闲时间..."
        }

    def _parse_datetime(self, time_str: str) -> Optional[datetime]:
        """
        解析时间字符串

        支持格式:
        - YYYY-MM-DD HH:MM
        - YYYY-MM-DDTHH:MM:SS
        - 自然语言: 今天 15:00, 明天 14:00, 周三 10:00
        """
        now = datetime.now()

        # ISO 格式
        try:
            return datetime.fromisoformat(time_str)
        except:
            pass

        # 标准格式 YYYY-MM-DD HH:MM
        match = re.match(r"(\d{4}-\d{2}-\d{2})\s*(\d{1,2}):(\d{2})", time_str)
        if match:
            date_part, hour, minute = match.groups()
            return datetime.strptime(f"{date_part} {hour}:{minute}", "%Y-%m-%d %H:%M")

        # 自然语言
        weekday_map = {
            "周一": 0, "星期一": 0,
            "周二": 1, "星期二": 1,
            "周三": 2, "星期三": 2,
            "周四": 3, "星期四": 3,
            "周五": 4, "星期五": 4,
            "周六": 5, "星期六": 5,
            "周日": 6, "星期天": 6,
        }

        # 今天/明天/后天
        if "明天" in time_str:
            base = now + timedelta(days=1)
        elif "后天" in time_str:
            base = now + timedelta(days=2)
        elif "今天" in time_str:
            base = now
        else:
            # 检查周几
            for weekday_name, weekday_num in weekday_map.items():
                if weekday_name in time_str:
                    days_ahead = (weekday_num - now.weekday()) % 7
                    if days_ahead == 0 and "周" in time_str:
                        days_ahead = 7
                    base = now + timedelta(days=days_ahead)
                    break
            else:
                return None
        else:
            base = now

        # 提取时间
        time_match = re.search(r"(\d{1,2}):(\d{2})", time_str)
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            return base.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # 默认时间
        return base.replace(hour=9, minute=0, second=0, microsecond=0)

    def format_events(self, events: List[Dict]) -> str:
        """格式化事件列表为可读输出"""
        if not events:
            return "📅 暂无日程"

        lines = ["📅 日程\n"]
        current_date = ""

        for event in events:
            start = event.get("start", {})
            start_dt = start.get("dateTime", "")
            summary = event.get("summary", "无标题")

            try:
                dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                date_str = dt.strftime("%m月%d日")
                time_str = dt.strftime("%H:%M")
            except:
                date_str = "未知"
                time_str = ""

            if date_str != current_date:
                lines.append(f"\n📆 {date_str}")
                current_date = date_str

            lines.append(f"  {time_str} {summary}")

        return "\n".join(lines)


def parse_natural_time(text: str) -> Dict[str, Any]:
    """
    解析自然语言时间描述

    返回:
    - title: 从文本中提取的会议标题
    - start_time: 开始时间
    - end_time: 结束时间
    """
    now = datetime.now()
    result = {
        "title": "新会议",
        "start_time": None,
        "end_time": None,
        "description": ""
    }

    # 提取标题
    time_patterns = [
        r"(.+?)\s*(\d{1,2}:\d{2})",
        r"(.+?)\s*(明天|今天|后天)",
        r"(.+?)\s*(周一|周二|周三|周四|周五|周六|周日)",
    ]

    for pattern in time_patterns:
        match = re.search(pattern, text)
        if match:
            potential_title = match.group(1).strip()
            if potential_title and potential_title not in ["提醒", "会议", "约"]:
                result["title"] = potential_title
            break

    # 提取时间
    time_match = re.search(r"(\d{1,2}):(\d{2})", text)
    if time_match:
        hour, minute = int(time_match.group(1)), int(time_match.group(2))
        if "明天" in text:
            start = now + timedelta(days=1)
        elif "后天" in text:
            start = now + timedelta(days=2)
        else:
            start = now
        start = start.replace(hour=hour, minute=minute, second=0, microsecond=0)
        result["start_time"] = start.isoformat()
        result["end_time"] = (start + timedelta(hours=1)).isoformat()

    return result
