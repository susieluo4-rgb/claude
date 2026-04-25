#!/usr/bin/env python3
"""
小野私人助理 - 邮件模块
通过集成 rl-email-assistant 提供邮件功能
"""
import subprocess
import os
from typing import Dict, Any


class EmailModule:
    """邮件模块"""

    SKILL_PATH = os.path.expanduser("~/.claude/skills/rl-email-assistant")
    SCRIPT_PATH = os.path.join(SKILL_PATH, "scripts/email_assistant.py")

    def digest(self, max_count: int = 20) -> Dict[str, Any]:
        """获取邮件摘要"""
        try:
            result = subprocess.run(
                ["python3", self.SCRIPT_PATH, "digest", "--max", str(max_count)],
                capture_output=True,
                text=True,
                cwd=self.SKILL_PATH,
                timeout=60
            )
            return {
                "success": True,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": None, "error": "邮件摘要超时"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def alert(self) -> Dict[str, Any]:
        """检查紧急邮件 (P1)"""
        try:
            result = subprocess.run(
                ["python3", self.SCRIPT_PATH, "alert"],
                capture_output=True,
                text=True,
                cwd=self.SKILL_PATH,
                timeout=30
            )
            return {
                "success": True,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def send(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """发送邮件"""
        sender_script = os.path.join(self.SKILL_PATH, "scripts/sender.py")
        try:
            result = subprocess.run(
                ["python3", sender_script, to, subject, body],
                capture_output=True,
                text=True,
                cwd=self.SKILL_PATH,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def format_response(self, result: Dict[str, Any]) -> str:
        """格式化邮件响应"""
        if not result["success"]:
            return f"❌ 获取邮件失败: {result.get('error', '未知错误')}"

        output = result.get("output", "")
        if not output:
            return "📬 暂无新邮件"

        # 简单格式化输出
        lines = output.strip().split("\n")
        if lines:
            header = lines[0] if lines else ""
            return f"📬 {header}\n\n" + "\n".join(lines[1:]) if len(lines) > 1 else output

        return f"📬 邮件摘要\n\n{output}"
