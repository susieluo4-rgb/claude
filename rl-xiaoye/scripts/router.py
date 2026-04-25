#!/usr/bin/env python3
"""
小野私人助理 - 意图识别与路由
"""
import re
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class Intent:
    """意图结构"""
    type: str  # email_digest, email_send, calendar_query, ...
    params: Dict[str, Any]
    confidence: float
    original_text: str

    def to_dict(self) -> Dict:
        return asdict(self)


class IntentRouter:
    """意图路由器"""

    # 意图模式注册表
    PATTERNS = {
        # 邮件
        "email_digest": [
            r"(查|看看|扫|检查)(一下)?(的?新?)?邮件",
            r"邮件摘要",
            r"有什么新邮件",
            r"邮箱",
        ],
        "email_send": [
            r"发(送?|一封)?邮件(给|至)(.+)",
            r"给(.+?)发邮件",
            r"发封邮件",
        ],

        # 日历
        "calendar_query": [
            r"(今天|明天|这周|下周)(有什么安排|几点有会|的日程)",
            r"查看日程",
            r"日程",
            r"有什么(会议|会)",
        ],
        "calendar_create": [
            r"(帮我)?约(.+)",
            r"创建会议",
            r"安排(.+)",
            r"预约(.+)",
        ],

        # 持仓
        "portfolio_summary": [
            r"(我的)?持仓怎么样",
            r"(我的)?持仓(今日)?回报",
        ],
        "portfolio_alert": [
            r"持仓(告警|监控|扫描)",
            r"(我的)?持仓",
            r"持仓怎么样",
        ],

        # 投研
        "research": [
            r"投研(.+)",
            r"研究(.+)",
            r"分析(.+?)(公司|$)",
            r"组合诊断",
        ],

        # 日报
        "daily_report": [
            r"(生成|今天)?日报",
            r"今日市场",
        ],

        # 生活
        "reminder": [
            r"提醒我(.+)",
            r"(帮我)?设置提醒(.+)",
        ],
        "weather": [
            r"天气(怎么样|如何)",
            r"今天天气",
        ],
        "date_query": [
            r"(今天|明天|昨天)?(几号|什么日子|星期几)",
            r"几号了",
        ],

        # 系统
        "status": [
            r"小野.?(状态|state)",
        ],
        "help": [
            r"小野.?(帮助|help)",
            r"(帮我|给我).?看看",
        ],
        "mute": [
            r"小野.?(静音|闭嘴|休息)",
        ],
    }

    def __init__(self):
        self.last_intent: Optional[Intent] = None

    def recognize(self, text: str) -> Intent:
        """识别用户意图"""
        original_text = text.strip()
        text = original_text

        # 优先检查"小野"前缀
        if text.startswith("小野"):
            suffix = text[2:].strip()
            if not suffix:
                return Intent(
                    type="help",
                    params={},
                    confidence=1.0,
                    original_text=original_text
                )
            # 检查系统命令 (状态/帮助/静音)
            for intent_type, patterns in self.PATTERNS.items():
                if intent_type in ["status", "help", "mute"]:
                    for pattern in patterns:
                        if re.search(pattern, original_text):
                            params = self._extract_params(intent_type, re.search(pattern, original_text), suffix)
                            return Intent(
                                type=intent_type,
                                params=params,
                                confidence=0.9,
                                original_text=original_text
                            )
            # 非系统命令，继续用处理后的 suffix
            text = suffix

        for intent_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    params = self._extract_params(intent_type, match, text)
                    intent = Intent(
                        type=intent_type,
                        params=params,
                        confidence=0.9,
                        original_text=text
                    )
                    self.last_intent = intent
                    return intent

        # 默认降级到关键词匹配
        return self._fallback_keyword(text)

    def _extract_params(self, intent_type: str, match: re.Match, text: str) -> Dict[str, Any]:
        """提取参数"""
        params = {}

        if intent_type == "email_send":
            # 提取收件人
            m = re.search(r"给(.+?)发|发.*?给(.+)", text)
            if m:
                params["recipient"] = (m.group(1) or m.group(2)).strip()
        elif intent_type == "calendar_create":
            # 提取时间和内容
            time_match = re.search(r"(今天|明天|后天|本周|下周|这周|下周)", text)
            if time_match:
                params["time"] = time_match.group(1)
            # 提取会议内容
            content_match = re.search(r"约(.+?)(的|上|时|）|$)", text)
            if content_match:
                params["content"] = content_match.group(1).strip()
        elif intent_type == "research":
            # 提取公司名
            m = re.search(r"(投研|研究|分析)(.+?)(公司|$)", text)
            if m:
                params["company"] = m.group(2).strip()
            else:
                # 组合诊断
                if "组合诊断" in text:
                    params["company"] = None
                    params["is_portfolio"] = True
        elif intent_type == "reminder":
            # 提取提醒内容
            m = re.search(r"提醒我(.+)", text)
            if m:
                params["content"] = m.group(1).strip()
            # 提取时间
            time_match = re.search(r"(明天|今天|后天|上午|下午|早上|晚上)?(.*?)(开会|会议|拜访|提交|完成)", text)
            if time_match:
                params["content"] = text
        elif intent_type == "weather":
            params["location"] = "当前位置"
        elif intent_type == "date_query":
            params["date"] = "today"

        return params

    def _fallback_keyword(self, text: str) -> Intent:
        """降级到关键词匹配"""
        keywords_map = {
            "邮件": "email_digest",
            "持仓": "portfolio_alert",
            "投研": "research",
            "研究": "research",
            "日历": "calendar_query",
            "日程": "calendar_query",
            "日报": "daily_report",
            "提醒": "reminder",
            "天气": "weather",
            "帮助": "help",
        }

        for kw, intent in keywords_map.items():
            if kw in text:
                return Intent(
                    type=intent,
                    params={},
                    confidence=0.5,
                    original_text=text
                )

        return Intent(
            type="unknown",
            params={},
            confidence=0.0,
            original_text=text
        )


class SessionContext:
    """会话上下文"""

    def __init__(self, session_file: str = None):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.last_topic: Optional[str] = None
        self.last_action: Optional[str] = None
        self.context: Dict[str, Any] = {
            "current_company": None,
            "pending_reply_email": None,
            "last_digest_time": None,
        }

    def update(self, intent: Intent):
        """更新上下文"""
        self.last_topic = intent.type.split("_")[0]
        self.last_action = intent.type

        # 更新特定上下文
        if intent.type == "research" and "company" in intent.params:
            self.context["current_company"] = intent.params["company"]
        elif intent.type == "email_digest":
            self.context["last_digest_time"] = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "last_topic": self.last_topic,
            "last_action": self.last_action,
            "context": self.context,
        }


if __name__ == "__main__":
    # 测试
    router = IntentRouter()

    test_inputs = [
        "查一下邮件",
        "今天有什么安排",
        "我的持仓怎么样",
        "投研宁德时代",
        "提醒我明天9点开会",
        "天气怎么样",
        "小野状态",
    ]

    for text in test_inputs:
        intent = router.recognize(text)
        print(f"输入: {text}")
        print(f"意图: {intent.type}, 置信度: {intent.confidence}, 参数: {intent.params}")
        print("---")
