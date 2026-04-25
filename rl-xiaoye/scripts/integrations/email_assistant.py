#!/usr/bin/env python3
"""
小野私人助理 - rl-email-assistant 封装层
"""
import subprocess
import os
import sys
from typing import Dict, Any


# 添加 skills 路径
EMAIL_SKILL_PATH = os.path.expanduser("~/.claude/skills/rl-email-assistant")
sys.path.insert(0, os.path.join(EMAIL_SKILL_PATH, "scripts"))


class EmailAssistantIntegration:
    """邮件助理集成"""

    def __init__(self):
        self.skill_path = EMAIL_SKILL_PATH
        self.script_path = os.path.join(self.skill_path, "scripts/email_assistant.py")

    def digest(self, max_count: int = 20) -> Dict[str, Any]:
        """获取邮件摘要"""
        try:
            result = subprocess.run(
                ["python3", self.script_path, "digest", "--max", str(max_count)],
                capture_output=True,
                text=True,
                cwd=self.skill_path,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": None, "error": "邮件摘要超时"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def alert(self) -> Dict[str, Any]:
        """检查紧急邮件"""
        try:
            result = subprocess.run(
                ["python3", self.script_path, "alert"],
                capture_output=True,
                text=True,
                cwd=self.skill_path,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def send(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """发送邮件"""
        sender_script = os.path.join(self.skill_path, "scripts/sender.py")
        try:
            result = subprocess.run(
                ["python3", sender_script, to, subject, body],
                capture_output=True,
                text=True,
                cwd=self.skill_path,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}
