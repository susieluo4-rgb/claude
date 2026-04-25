#!/usr/bin/env python3
"""
小野私人助理 - rl-portfolio-monitor 封装层
"""
import subprocess
import os
from typing import Dict, Any, Optional


class PortfolioMonitorIntegration:
    """持仓监控集成"""

    def __init__(self):
        self.skill_path = os.path.expanduser("~/.claude/skills/rl-portfolio-monitor")
        self.script_path = os.path.join(self.skill_path, "portfolio_monitor.py")

    def scan(self, portfolio: Optional[str] = None, stock: Optional[str] = None) -> Dict[str, Any]:
        """扫描持仓"""
        try:
            cmd = ["python3", self.script_path, "scan"]
            if portfolio:
                cmd.extend(["--portfolio", portfolio])
            if stock:
                cmd.append(stock)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.skill_path,
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

    def summary(self, portfolio: Optional[str] = None) -> Dict[str, Any]:
        """获取持仓汇总"""
        try:
            cmd = ["python3", self.script_path, "summary"]
            if portfolio:
                cmd.extend(["--portfolio", portfolio])

            result = subprocess.run(
                cmd,
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
            return {"success": False, "output": None, "error": "持仓汇总超时"}
        except Exception as e:
            return {"success": False, "output": None, "error": str(e)}

    def history(self, days: int = 7, stock: Optional[str] = None) -> Dict[str, Any]:
        """查询告警历史"""
        try:
            cmd = ["python3", self.script_path, "history", "--days", str(days)]
            if stock:
                cmd.extend(["--stock", stock])

            result = subprocess.run(
                cmd,
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
