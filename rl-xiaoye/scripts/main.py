#!/usr/bin/env python3
"""
小野私人助理 - 主入口

用法:
    python3 main.py "查一下邮件"
    python3 main.py "今天有什么安排"
    python3 main.py "我的持仓怎么样"
    python3 main.py "投研宁德时代"
    python3 main.py "提醒我明天9点开会"

交互模式:
    python3 main.py
"""
import sys
import os
import json
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from router import IntentRouter, SessionContext
from modules.email_module import EmailModule
from modules.calendar_module import CalendarModule
from modules.portfolio_module import PortfolioModule
from modules.research_module import ResearchModule
from modules.daily_report_module import DailyReportModule
from modules.life_module import LifeModule


class Xiaoye:
    """小野私人助理"""

    def __init__(self):
        self.router = IntentRouter()
        self.context = SessionContext()
        self.email_module = EmailModule()
        self.calendar_module = CalendarModule()
        self.portfolio_module = PortfolioModule()
        self.research_module = ResearchModule()
        self.daily_report_module = DailyReportModule()
        self.life_module = LifeModule()

    def process(self, user_input: str) -> str:
        """处理用户输入"""
        # 1. 意图识别
        intent = self.router.recognize(user_input)
        self.context.update(intent)

        # 2. 执行对应模块
        result = self._execute(intent)

        # 3. 格式化输出
        return self._format_output(intent, result)

    def _execute(self, intent):
        """执行意图"""
        intent_type = intent.type
        params = intent.params

        if intent_type == "email_digest":
            return self.email_module.digest()
        elif intent_type == "email_send":
            return {"success": True, "message": "请提供邮件内容，格式: 发邮件给 xxx，主题: xxx，内容: xxx"}
        elif intent_type == "calendar_query":
            return self.calendar_module.query(params)
        elif intent_type == "calendar_create":
            return self.calendar_module.create(params)
        elif intent_type == "portfolio_summary":
            return self.portfolio_module.summary()
        elif intent_type == "portfolio_alert":
            return self.portfolio_module.scan()
        elif intent_type == "research":
            return self.research_module.start(params.get("company", ""))
        elif intent_type == "daily_report":
            return self.daily_report_module.generate()
        elif intent_type == "reminder":
            return self.life_module.set_reminder(params)
        elif intent_type == "weather":
            return self.life_module.weather(params)
        elif intent_type == "date_query":
            return self.life_module.date_query(params)
        elif intent_type == "status":
            return self._get_status()
        elif intent_type == "help":
            return self._get_help()
        elif intent_type == "mute":
            return {"success": True, "message": "🔇 小野已静音，有事叫我"}
        else:
            return {"success": False, "error": "抱歉，我不明白您的意思"}

    def _format_output(self, intent, result) -> str:
        """格式化输出"""
        intent_type = intent.type

        if not result.get("success", False):
            error = result.get("error", "未知错误")
            return f"❌ 操作失败: {error}"

        # 检查是否有直接消息
        if "message" in result:
            return result["message"]

        # 检查是否有动作指令（需要调用方通过 Skill/MCP 执行）
        if "action" in result:
            action = result["action"]
            if action == "skill_trigger":
                skill = result.get("skill", "")
                params = result.get("params", {})
                company = params.get("company", "")
                if params.get("is_portfolio"):
                    return f"✅ {result.get('message', '正在执行组合诊断')}\n请在 Claude Code 中输入: 组合诊断"
                return f"✅ {result.get('message', '正在启动投研')}\n请在 Claude Code 中输入: 投研 {company}"
            elif action == "mcp_call":
                return f"✅ {result.get('message', '正在查询')}\n(需要通过 Google Calendar MCP 执行)"
            elif action == "cron_create":
                return f"✅ {result.get('message', '提醒已设置')}"
            elif action == "web_search":
                return f"✅ {result.get('message', '正在查询')}\n(需要通过 WebSearch 执行)"

        # 检查是否有输出
        output = result.get("output")
        if output:
            if isinstance(output, str):
                return output
            elif isinstance(output, dict):
                # 日期查询等返回 dict
                if intent_type == "date_query":
                    return self.life_module.format_response(result, intent_type)

        # 默认返回
        return "✅ 操作完成"

    def _get_status(self) -> dict:
        """获取状态"""
        return {
            "success": True,
            "message": f"""小野状态
---
📧 邮件: 已连接
📅 日历: Google Calendar
📊 持仓: rl-portfolio-monitor
📈 投研: 投研团队
⏰ 提醒: 已就绪
---
🕐 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        }

    def _get_help(self) -> dict:
        """获取帮助"""
        return {
            "success": True,
            "message": """小野私人助理 v1.0

📧 邮件
  "查一下邮件" / "邮件摘要"
  "发邮件给 xxx"

📅 日历
  "今天有什么安排"
  "帮我约 明天下午3点 xxx"

📊 持仓
  "我的持仓怎么样"
  "持仓告警"

📈 投研
  "投研 xxx 公司"
  "分析 xxx"
  "组合诊断"

📰 日报
  "生成日报"

⏰ 生活
  "提醒我 明天9点开会"
  "天气怎么样"

🔧 系统
  "小野 状态" - 查看状态
  "小野 帮助" - 显示帮助"""
        }


def main():
    """主入口"""
    xiaoye = Xiaoye()

    if len(sys.argv) > 1:
        # 命令行模式
        user_input = " ".join(sys.argv[1:])
        response = xiaoye.process(user_input)
        print(response)
    else:
        # 交互模式
        print("小野私人助理 v1.0")
        print("说 '退出' 或 'exit' 结束\n")

        while True:
            try:
                user_input = input("👤 你: ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            if user_input.lower() in ["退出", "exit", "quit"]:
                print("👋 再见！")
                break

            response = xiaoye.process(user_input)
            print(f"\n🤖 小野: {response}\n")


if __name__ == "__main__":
    main()
