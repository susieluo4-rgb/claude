#!/usr/bin/env python3
"""
小野私人助理 - 投研模块
通过集成 投研团队 提供投研功能
"""
import subprocess
import os
from typing import Dict, Any, Optional


class ResearchModule:
    """投研模块"""

    SKILL_PATH = os.path.expanduser("~/.claude/skills/投研团队")

    def start(self, company: str, skip_model: bool = False) -> Dict[str, Any]:
        """
        启动投研流程

        注意: 实际通过 Skill tool 调用更可靠
        这里返回指令，指导用户或调用方使用 Skill
        """
        return {
            "success": True,
            "action": "skill_trigger",
            "skill": "投研团队",
            "params": {"company": company, "skip_model": skip_model},
            "message": f"正在启动投研团队，分析 {company}..."
        }

    def quick_research(self, company: str) -> Dict[str, Any]:
        """快速研究"""
        return {
            "success": True,
            "action": "skill_trigger",
            "skill": "投研团队",
            "params": {"company": company, "quick": True},
            "message": f"正在快速分析 {company}..."
        }

    def portfolio_diagnosis(self) -> Dict[str, Any]:
        """组合诊断"""
        return {
            "success": True,
            "action": "skill_trigger",
            "skill": "投研团队",
            "params": {"mode": "portfolio_diagnosis"},
            "message": "正在执行组合诊断..."
        }

    def format_response(self, result: Dict[str, Any]) -> str:
        """格式化投研响应"""
        if not result["success"]:
            return f"❌ 投研启动失败: {result.get('error', '未知错误')}"

        return f"✅ {result.get('message', '投研已启动')}"
