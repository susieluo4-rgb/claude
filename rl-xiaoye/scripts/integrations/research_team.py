#!/usr/bin/env python3
"""
小野私人助理 - 投研团队 封装层
用于触发投研流程
"""


class ResearchTeamIntegration:
    """投研团队集成"""

    def __init__(self):
        self.skill_name = "投研团队"

    def start_research(self, company: str, skip_model: bool = False) -> dict:
        """
        启动投研流程

        返回指令信息，实际通过 Skill tool 调用
        """
        return {
            "success": True,
            "action": "skill_trigger",
            "skill": self.skill_name,
            "params": {
                "company": company,
                "skip_model": skip_model
            },
            "message": f"正在启动投研团队，分析 {company}..."
        }

    def quick_research(self, company: str) -> dict:
        """快速研究"""
        return {
            "success": True,
            "action": "skill_trigger",
            "skill": self.skill_name,
            "params": {
                "company": company,
                "quick": True
            },
            "message": f"正在快速分析 {company}..."
        }

    def portfolio_diagnosis(self) -> dict:
        """组合诊断"""
        return {
            "success": True,
            "action": "skill_trigger",
            "skill": self.skill_name,
            "params": {
                "mode": "portfolio_diagnosis"
            },
            "message": "正在执行组合诊断..."
        }

    def get_checkpoint(self, company_path: str) -> dict:
        """
        读取 Checkpoint

        注意: 实际由调用方通过 checkpoint_utils.py 实现
        """
        return {
            "success": True,
            "action": "checkpoint_read",
            "path": company_path,
            "message": "正在读取投研进度..."
        }
