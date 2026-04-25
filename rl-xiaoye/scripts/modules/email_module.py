#!/usr/bin/env python3
"""
小野私人助理 - 邮件模块
支持三个数据源：qq-email (MCP)、outlook-microsoft (Script)、rl-email-assistant (Script)
"""
import subprocess
import os
from typing import Dict, Any, Optional


class EmailModule:
    """邮件模块 - 多数据源集成"""

    # 数据源配置
    DATASOURCES = {
        "qq-email": {
            "type": "mcp",
            "tool": "mcp__claude_ai_Gmail__",  # qq-email 通过 Gmail MCP 接口
            "enabled": True,
            "priority": 1,  # 优先使用
        },
        "outlook-microsoft": {
            "type": "script",
            "path": "~/.claude/skills/outlook-microsoft/scripts/outlook_mail.py",
            "enabled": True,
            "priority": 2,
        },
        "rl-email-assistant": {
            "type": "script",
            "path": "~/.claude/skills/rl-email-assistant/scripts/email_assistant.py",
            "enabled": True,
            "priority": 3,
        }
    }

    def __init__(self, preferred_source: str = "qq-email"):
        self.preferred_source = preferred_source

    def digest(self, max_count: int = 20, source: str = None) -> Dict[str, Any]:
        """
        获取邮件摘要

        Args:
            max_count: 最大邮件数量
            source: 指定数据源，默认使用 qq-email
        """
        source = source or self.preferred_source

        # 按优先级尝试各数据源
        if source == "qq-email" or source is None:
            result = self._digest_qq_email(max_count)
            if result["success"]:
                return result

        if source in ["outlook-microsoft", None]:
            result = self._digest_outlook(max_count)
            if result["success"]:
                return result

        if source in ["rl-email-assistant", None]:
            return self._digest_email_assistant(max_count)

        return {"success": False, "error": "所有邮件数据源均不可用"}

    def _digest_qq_email(self, max_count: int) -> Dict[str, Any]:
        """通过 QQ Email MCP 获取邮件"""
        # 注意: qq-email MCP 的实际工具名需要检查
        # 这里返回指令让调用方使用 MCP 工具
        return {
            "success": True,
            "action": "mcp_call",
            "tool": "mcp__claude_ai_Gmail__search_threads",
            "params": {"pageSize": max_count, "query": "in:inbox"},
            "message": "正在通过 QQ邮箱 获取邮件..."
        }

    def _digest_outlook(self, max_count: int) -> Dict[str, Any]:
        """通过 Outlook 获取邮件"""
        outlook_path = os.path.expanduser(
            self.DATASOURCES["outlook-microsoft"]["path"]
        )
        try:
            result = subprocess.run(
                ["python3", outlook_path, "inbox", str(max_count)],
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Outlook 邮件获取超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _digest_email_assistant(self, max_count: int) -> Dict[str, Any]:
        """通过 rl-email-assistant 获取邮件"""
        assistant_path = os.path.expanduser(
            self.DATASOURCES["rl-email-assistant"]["path"]
        )
        try:
            result = subprocess.run(
                ["python3", assistant_path, "digest", "--max", str(max_count)],
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "邮件摘要超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def alert(self) -> Dict[str, Any]:
        """检查紧急邮件 (P1)"""
        # 优先使用 rl-email-assistant 的 alert 功能
        assistant_path = os.path.expanduser(
            self.DATASOURCES["rl-email-assistant"]["path"]
        )
        try:
            result = subprocess.run(
                ["python3", assistant_path, "alert"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send(self, to: str, subject: str, body: str, source: str = "qq-email") -> Dict[str, Any]:
        """
        发送邮件

        Args:
            to: 收件人
            subject: 主题
            body: 正文
            source: 数据源
        """
        if source == "qq-email":
            return {
                "success": True,
                "action": "mcp_call",
                "tool": "mcp__claude_ai_Gmail__create_draft",
                "params": {"to": [to], "subject": subject, "body": body},
                "message": f"正在通过 QQ邮箱 发送邮件给 {to}..."
            }
        elif source == "outlook-microsoft":
            outlook_path = os.path.expanduser(
                self.DATASOURCES["outlook-microsoft"]["path"]
            )
            try:
                result = subprocess.run(
                    ["python3", outlook_path, "send", subject, to, body],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"不支持的数据源: {source}"}

    def search(self, query: str, source: str = "qq-email") -> Dict[str, Any]:
        """搜索邮件"""
        if source == "qq-email":
            return {
                "success": True,
                "action": "mcp_call",
                "tool": "mcp__claude_ai_Gmail__search_threads",
                "params": {"query": query},
                "message": f"正在搜索: {query}..."
            }
        elif source == "outlook-microsoft":
            outlook_path = os.path.expanduser(
                self.DATASOURCES["outlook-microsoft"]["path"]
            )
            try:
                result = subprocess.run(
                    ["python3", outlook_path, "search", query],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": f"不支持的数据源: {source}"}

    def format_response(self, result: Dict[str, Any], intent_type: str = "digest") -> str:
        """格式化邮件响应"""
        if not result["success"]:
            return f"❌ 获取邮件失败: {result.get('error', '未知错误')}"

        # 如果是 MCP 调用，返回提示
        if result.get("action") == "mcp_call":
            return result.get("message", "正在获取邮件...")

        output = result.get("output", "")
        if not output:
            return "📬 暂无新邮件"

        # 简单格式化输出
        lines = output.strip().split("\n")
        if lines:
            header = lines[0] if lines else ""
            return f"📬 {header}\n\n" + "\n".join(lines[1:]) if len(lines) > 1 else output

        return f"📬 邮件摘要\n\n{output}"
