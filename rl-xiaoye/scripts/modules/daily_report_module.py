#!/usr/bin/env python3
"""
小野私人助理 - 日报模块
通过集成 rl-daily-report 提供日报功能
"""
import subprocess
import os
from typing import Dict, Any


class DailyReportModule:
    """日报模块"""

    SKILL_PATH = os.path.expanduser("~/.claude/skills/rl-daily-report")

    def generate(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        生成市场日报

        params 可以包含:
        - recipients: 发送列表
        - portfolio: 指定组合
        """
        try:
            # 调用 rl-daily-report
            daily_script = os.path.join(self.SKILL_PATH, "scripts/daily_report.py")

            cmd = ["python3", daily_script]
            if params and params.get("portfolio"):
                cmd.extend(["--portfolio", params["portfolio"]])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.SKILL_PATH,
                timeout=300  # 日报生成可能较慢
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "output": None, "error": "日报生成超时"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def format_response(self, result: Dict[str, Any]) -> str:
        """格式化日报响应"""
        if not result["success"]:
            return f"❌ 日报生成失败: {result.get('error', '未知错误')}"

        output = result.get("output", "")
        if not output:
            return "✅ 日报已生成"

        return f"📰 市场日报\n\n{output}"
