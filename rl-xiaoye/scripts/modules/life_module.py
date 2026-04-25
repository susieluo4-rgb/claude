#!/usr/bin/env python3
"""
小野私人助理 - 生活管家模块
提供提醒、天气、日期查询等生活功能
"""
import re
from typing import Dict, Any
from datetime import datetime, timedelta


class LifeModule:
    """生活管家模块"""

    def set_reminder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        设置提醒

        params 可以包含:
        - content: 提醒内容
        - time: 时间描述 (如 "明天9点", "下周一15:00")
        """
        content = params.get("content", "")
        time_desc = params.get("time", "")

        # 解析时间
        parsed_time = self._parse_time(time_desc)

        if not parsed_time:
            return {
                "success": False,
                "error": "无法解析时间，请明确说明如'明天9点'或'下周一15:00'"
            }

        return {
            "success": True,
            "action": "cron_create",
            "params": {
                "content": content or time_desc,
                "time": parsed_time
            },
            "message": f"✅ 已设置提醒: {content or time_desc} @ {parsed_time['formatted']}"
        }

    def weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        查询天气

        params 可以包含:
        - location: 位置 (默认"当前位置")
        """
        location = params.get("location", "当前位置")

        # 这里可以通过 WebSearch 或 Weather API 获取
        # 返回指令让调用方执行
        return {
            "success": True,
            "action": "web_search",
            "query": f"{location} 天气",
            "message": f"正在查询 {location} 的天气..."
        }

    def date_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        日期查询

        params 可以包含:
        - date: "today", "tomorrow", "yesterday"
        """
        date_param = params.get("date", "today")

        now = datetime.now()

        if date_param == "today":
            target = now
        elif date_param == "tomorrow":
            target = now + timedelta(days=1)
        elif date_param == "yesterday":
            target = now - timedelta(days=1)
        else:
            target = now

        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[target.weekday()]

        return {
            "success": True,
            "output": {
                "date": target.strftime("%Y年%m月%d日"),
                "weekday": weekday,
                "is_weekend": target.weekday() >= 5
            }
        }

    def _parse_time(self, time_desc: str) -> Dict[str, Any]:
        """解析时间描述"""
        now = datetime.now()

        # 匹配模式: 明天9点, 今天15:00, 下周一10:30
        patterns = [
            (r"明天(\d{1,2})[:点](\d{0,2})", 1),
            (r"今天(\d{1,2})[:点](\d{0,2})", 0),
            (r"后天(\d{1,2})[:点](\d{0,2})", 2),
            (r"下周一(\d{1,2})[:点](\d{0,2})", 7),
        ]

        for pattern, days_offset in patterns:
            match = re.search(pattern, time_desc)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0

                target = now + timedelta(days=days_offset)
                target = target.replace(hour=hour, minute=minute, second=0, microsecond=0)

                return {
                    "datetime": target,
                    "formatted": target.strftime("%Y-%m-%d %H:%M"),
                    "cron": f"{minute} {hour} {target.day} {target.month} *"
                }

        # 如果没有明确时间，默认明天早上9点
        if time_desc:
            target = now + timedelta(days=1)
            target = target.replace(hour=9, minute=0, second=0, microsecond=0)
            return {
                "datetime": target,
                "formatted": target.strftime("%Y-%m-%d %H:%M"),
                "cron": f"0 9 {target.day} {target.month} *"
            }

        return None

    def format_response(self, result: Dict[str, Any], intent_type: str = "reminder") -> str:
        """格式化生活响应"""
        if not result["success"]:
            return f"❌ 操作失败: {result.get('error', '未知错误')}"

        message = result.get("message", "")

        if intent_type == "weather":
            return f"🌤️ {message}"
        elif intent_type == "date_query":
            output = result.get("output", {})
            date_str = output.get("date", "")
            weekday = output.get("weekday", "")
            return f"📅 今天是 {date_str} ({weekday})"
        else:
            return message or "✅ 操作完成"
