#!/usr/bin/env python3
"""
纪要追踪分析 — 邮件输出模板
生成纪要对比报告的邮件正文，格式参考用户提供范例：
  Summary
  --量化指标1
  --量化指标2
  结论：{公司}纪要追踪完成。{综合方向}。{估值说明}。{操作建议}

复用路径: ~/.claude/skills/RL纪要追踪分析/scripts/email_template.py
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


def format_direction_emoji(direction: str) -> str:
    """将方向文字转为emoji符号"""
    mapping = {
        "向好": "↑",
        "向差": "↓",
        "中性": "→",
        "positive": "↑",
        "negative": "↓",
        "neutral": "→",
    }
    return mapping.get(direction, "→")


def format_direction_text(direction: str) -> str:
    """将方向文字转为中文描述"""
    mapping = {
        "向好": "综合方向向好",
        "向差": "综合方向向差",
        "中性": "综合方向中性",
        "positive": "综合方向向好",
        "negative": "综合方向向差",
        "neutral": "综合方向中性",
    }
    return mapping.get(direction, f"综合方向{direction}")


def build_summary_bullets(
    quantitative: List[Dict[str, Any]],
    qualitative: List[Dict[str, Any]]
) -> str:
    """
    构建 Summary 部分 bullets
    格式：--{指标名}：{值}；{变化方向}
    """
    lines = []

    # 量化指标
    for item in quantitative:
        indicator = item.get("indicator", "")
        new_value = item.get("new_value", "")
        old_value = item.get("old_value", "")
        direction = item.get("direction", "")
        change = item.get("change", "")

        # 简化显示
        if old_value and old_value != new_value:
            line = f"{indicator}：{new_value}（旧：{old_value}，{direction}）"
        else:
            line = f"{indicator}：{new_value}"

        lines.append(f"--{line}")

    # 定性判断
    for item in qualitative:
        dimension = item.get("dimension", "")
        new_judgment = item.get("new_judgment", "")
        old_judgment = item.get("old_judgment", "")
        change = item.get("change", "")

        if old_judgment and old_judgment != new_judgment:
            line = f"{dimension}：{new_judgment}（旧：{old_judgment}，{change}）"
        else:
            line = f"{dimension}：{new_judgment}"

        lines.append(f"--{line}")

    return "\n".join(lines)


def build_conclusion(
    company: str,
    stock_code: str,
    overall_direction: str,
    valuation_note: str = "",
    recommendation: str = "",
    key_findings: Optional[List[str]] = None
) -> str:
    """
    构建结论部分
    格式：结论：{公司}纪要追踪完成。{综合方向}。{估值说明}。{操作建议}
    """
    direction_text = format_direction_text(overall_direction)
    direction_emoji = format_direction_emoji(overall_direction)

    conclusion_parts = [
        f"{company}（{stock_code}）纪要追踪完成。",
        direction_emoji + direction_text,
    ]

    if valuation_note:
        conclusion_parts.append(valuation_note)

    if key_findings:
        conclusion_parts.append("；".join(key_findings))

    if recommendation:
        conclusion_parts.append(recommendation)

    return "。".join(conclusion_parts) + "。"


def build_email_content(
    company: str,
    stock_code: str,
    report_date: str,
    overall_direction: str,
    quantitative_indicators: List[Dict[str, Any]],
    qualitative_assessments: List[Dict[str, Any]],
    model_suggestions: Optional[List[str]] = None,
    valuation_note: str = "",
    recommendation: str = "",
    key_findings: Optional[List[str]] = None,
) -> str:
    """
    生成完整的邮件正文

    参数：
        company: 公司名
        stock_code: 股票代码
        report_date: 报告日期
        overall_direction: 综合方向（向好/向差/中性）
        quantitative_indicators: 量化指标列表 [{indicator, old_value, new_value, direction, change}, ...]
        qualitative_assessments: 定性评估列表 [{dimension, old_judgment, new_judgment, change}, ...]
        model_suggestions: 模型调整建议列表
        valuation_note: 估值说明（如"2026年PE 20倍"）
        recommendation: 操作建议（如"建议买入"）
        key_findings: 关键发现列表

    返回：
        邮件正文文本
    """
    summary_bullets = build_summary_bullets(quantitative_indicators, qualitative_assessments)
    conclusion = build_conclusion(
        company, stock_code, overall_direction,
        valuation_note, recommendation, key_findings
    )

    email_body = f"""Summary
{summary_bullets}

结论：{conclusion}"""

    if model_suggestions:
        email_body += "\n\n模型调整建议："
        for i, suggestion in enumerate(model_suggestions, 1):
            email_body += f"\n{i}. {suggestion}"

    email_body += f"\n\n---\n纪要追踪对比报告 {report_date}"

    return email_body


def build_email_subject(
    company: str,
    report_date: str,
    overall_direction: str,
    recommendation: str = "",
    key_metrics: Optional[List[str]] = None,
) -> str:
    """
    构建邮件主题
    格式：CC--MN-- {日期} --{公司名}--{核心内容摘要}

    参数：
        company: 公司名
        report_date: 报告日期（YYYYMMDD格式）
        overall_direction: 综合方向（向好/向差/中性）
        recommendation: 操作建议（如"建议买入"）
        key_metrics: 关键指标列表（如["Q1净利润+30%", "毛利率24%创新高"]）

    返回：
        邮件主题字符串
    """
    # 日期格式化
    if len(report_date) == 10:  # YYYY-MM-DD -> YYYYMMDD
        date_formatted = report_date.replace("-", "")
    else:
        date_formatted = report_date.replace("-", "")

    # 方向符号
    direction_map = {
        "向好": "↑",
        "向差": "↓",
        "中性": "→",
        "positive": "↑",
        "negative": "↓",
        "neutral": "→",
    }
    direction_symbol = direction_map.get(overall_direction, "→")

    # 核心内容摘要
    summary_parts = []
    if key_metrics:
        for metric in key_metrics[:3]:  # 最多3个关键指标
            summary_parts.append(metric)
    if recommendation:
        summary_parts.append(recommendation)

    content_summary = "，".join(summary_parts) if summary_parts else f"纪要追踪{direction_symbol}"

    subject = f"CC--MN-- {date_formatted} --{company}--{content_summary}"

    return subject


def print_email_preview(
    company: str,
    stock_code: str,
    overall_direction: str,
    quantitative_indicators: List[Dict[str, Any]],
    qualitative_assessments: List[Dict[str, Any]],
    **kwargs
):
    """打印邮件预览到 stdout"""
    report_date = datetime.now().strftime("%Y-%m-%d")
    date_formatted = report_date.replace("-", "")

    email_body = build_email_content(
        company=company,
        stock_code=stock_code,
        report_date=report_date,
        overall_direction=overall_direction,
        quantitative_indicators=quantitative_indicators,
        qualitative_assessments=qualitative_assessments,
        **kwargs
    )

    # 生成邮件主题
    key_metrics = kwargs.get("key_findings", [])
    if not key_metrics:
        # 从量化指标中提取关键数据作为备用
        key_metrics = [f"{q.get('indicator', '')}：{q.get('new_value', '')}"
                       for q in quantitative_indicators[:3]]

    email_subject = build_email_subject(
        company=company,
        report_date=date_formatted,
        overall_direction=overall_direction,
        recommendation=kwargs.get("recommendation", ""),
        key_metrics=key_metrics,
    )

    print("\n" + "=" * 60)
    print(f"📧 纪要追踪邮件预览 — {company}（{stock_code}）")
    print("=" * 60)
    print(f"\n📌 邮件主题：")
    print(f"   {email_subject}")
    print(f"\n📄 邮件正文：")
    print(email_body)
    print("=" * 60)
    print("\n💡 以上为邮件正文，可直接复制发送或修改后发送。")
    print("\n[EMAIL BODY START]" + email_body + "[EMAIL BODY END]")


# ========== 示例用法 ==========
if __name__ == "__main__":
    # 示例：威迈斯纪要追踪
    quantitative = [
        {"indicator": "研发费用率（2026Q1）", "old_value": "6.57%", "new_value": "8.07%", "direction": "↑向好", "change": "+1.50pp"},
        {"indicator": "第四代产品占比", "old_value": "<20%", "new_value": "接近30%", "direction": "↑向好", "change": "+10pp+"},
        {"indicator": "车载电源市场份额", "old_value": "21.2%", "new_value": "21.2%", "direction": "→持平", "change": "0pp"},
        {"indicator": "2025年毛利率", "old_value": "20.94%", "new_value": "20.94%", "direction": "→持平", "change": "0pp"},
        {"indicator": "2026年Q1毛利率", "old_value": "24.03%", "new_value": "24.03%", "direction": "→持平", "change": "0pp（历史新高）"},
    ]

    qualitative = [
        {"dimension": "盈利能力趋势", "old_judgment": "毛利率上行", "new_judgment": "Q1毛利率24.03%创历史新高", "change": "→确认"},
        {"dimension": "海外业务", "old_judgment": "海外毛利率30-40%", "new_judgment": "海外业务带动整体毛利率提升", "change": "→确认"},
        {"dimension": "研发投入", "old_judgment": "研发费用率6.57%", "new_judgment": "Q1研发费用率8.07%，投入强度进一步提升", "change": "↑改善"},
        {"dimension": "第五代产品", "old_judgment": "客户验证中", "new_judgment": "正处于客户验证阶段，市场投放按计划推进", "change": "→无变化"},
    ]

    model_suggestions = [
        "2026年研发费用率：当前预测6.5-7% → 建议调整为7-8%",
        "第四代产品占比：当前预测<20% → 建议更新至30%（2025年实际）",
    ]

    key_findings = [
        "Q1业绩超预期验证盈利改善逻辑",
        "海外业务持续放量",
    ]

    valuation_note = "2026年PE 21倍（华泰一致预期）"
    recommendation = "建议买入"

    print_email_preview(
        company="威迈斯",
        stock_code="688612.SH",
        overall_direction="中性",
        quantitative_indicators=quantitative,
        qualitative_assessments=qualitative,
        model_suggestions=model_suggestions,
        valuation_note=valuation_note,
        recommendation=recommendation,
        key_findings=key_findings,
    )
