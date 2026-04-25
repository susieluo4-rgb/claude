#!/usr/bin/env python3
"""
小野私人助理 - 持仓模块
通过集成 rl-portfolio-monitor 提供持仓监控功能
"""
import subprocess
import os
from typing import Dict, Any, Optional


class PortfolioModule:
    """持仓模块"""

    SKILL_PATH = os.path.expanduser("~/.claude/skills/rl-portfolio-monitor")
    SCRIPT_PATH = os.path.join(self.SKILL_PATH, "portfolio_monitor.py") if hasattr(self, 'SKILL_PATH') else None

    def __init__(self):
        self.SKILL_PATH = os.path.expanduser("~/.claude/skills/rl-portfolio-monitor")
        self.SCRIPT_PATH = os.path.join(self.SKILL_PATH, "portfolio_monitor.py")

    def summary(self, portfolio: Optional[str] = None) -> Dict[str, Any]:
        """获取持仓汇总"""
        try:
            cmd = ["python3", self.SCRIPT_PATH, "summary"]
            if portfolio:
                cmd.extend(["--portfolio", portfolio])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.SKILL_PATH,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": None, "error": "持仓汇总超时"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def scan(self, portfolio: Optional[str] = None, stock: Optional[str] = None) -> Dict[str, Any]:
        """扫描持仓告警"""
        try:
            cmd = ["python3", self.SCRIPT_PATH, "scan"]
            if portfolio:
                cmd.extend(["--portfolio", portfolio])
            if stock:
                cmd.append(stock)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.SKILL_PATH,
                timeout=120
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": None, "error": "持仓扫描超时"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def history(self, days: int = 7, stock: Optional[str] = None) -> Dict[str, Any]:
        """查询告警历史"""
        try:
            cmd = ["python3", self.SCRIPT_PATH, "history", "--days", str(days)]
            if stock:
                cmd.extend(["--stock", stock])

            result = subprocess.run(
                cmd,
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

    def format_response(self, result: Dict[str, Any], intent_type: str = "summary") -> str:
        """格式化持仓响应"""
        if not result["success"]:
            return f"❌ 获取持仓失败: {result.get('error', '未知错误')}"

        output = result.get("output", "")
        if not output:
            return "📊 暂无持仓数据"

        prefix = "📊 持仓监控"
        if intent_type == "alert":
            prefix = "📊 持仓告警"

        return f"{prefix}\n\n{output}"
