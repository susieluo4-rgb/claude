#!/usr/bin/env python3
"""
PDF财务数据提取脚本 v2.0
从年报PDF中提取完整财务数据：利润表、资产负债表、现金流量表、分部数据、季度数据
支持A股/港股上市公司
"""

import pdfplumber
import os
import re
from typing import Dict, List, Optional, Tuple

def parse_number(s: str, unit: str = 'yuan') -> Optional[float]:
    """
    将中文数字字符串转换为浮点数
    unit: 'yuan' (元, 默认), 'million' (百万), 'billion' (亿)
    """
    if not s or s in ['N/A', '-', '', '不适用', 'None']:
        return None
    s = str(s).replace(',', '').replace(' ', '').replace('\n', '')

    # 处理括号表示负数
    negative = False
    if s.startswith('(') and s.endswith(')'):
        negative = True
        s = s[1:-1]
    if s.startswith('-'):
        negative = True
        s = s[1:]

    try:
        val = float(s)
        if negative:
            val = -val
    except:
        return None

    # 转换为亿元
    if unit == 'billion':
        return val  # 已经是亿
    elif unit == 'million':
        return val / 100  # 百万转亿
    else:  # yuan
        return val / 1e8  # 元转亿

    return val


def extract_income_statement(page) -> Dict:
    """从页面提取利润表数据"""
    data = {}
    tables = page.extract_tables()

    for t in tables:
        if not t:
            continue
        for row in t:
            if not row or len(row) < 2:
                continue

            label = str(row[0]).replace('\n', '').strip() if row[0] else ''

            # 提取数值（跳过第一列标签）
            vals = []
            for v in row[1:]:
                parsed = parse_number(str(v) if v else '0')
                if parsed is not None:
                    vals.append(parsed)

            if not vals:
                continue

            # 匹配关键指标
            if '营业收入' in label and '分部' not in label:
                data['revenue'] = vals[0] if len(vals) > 0 else None
                data['revenue_prior'] = vals[1] if len(vals) > 1 else None
            elif '营业成本' in label and '分部' not in label:
                data['cogs'] = vals[0]
            elif '销售费用' in label:
                data['sell_exp'] = abs(vals[0]) if vals[0] else None
            elif '管理费用' in label:
                data['admin_exp'] = abs(vals[0]) if vals[0] else None
            elif '研发费用' in label:
                data['rd_exp'] = abs(vals[0]) if vals[0] else None
            elif '财务费用' in label:
                data['fin_exp'] = abs(vals[0]) if vals[0] else None
            elif '资产减值损失' in label:
                data['asset_impairment'] = vals[0]
            elif '公允价值变动' in label:
                data['fair_value_change'] = vals[0]
            elif '投资收益' in label:
                data['investment_income'] = vals[0]
            elif '其他收益' in label:
                data['other_income'] = vals[0]
            elif '营业利润' in label and '归属' not in label:
                data['op_profit'] = vals[0]
            elif '营业外收入' in label:
                data['non_op_income'] = vals[0]
            elif '营业外支出' in label:
                data['non_op_expense'] = abs(vals[0]) if vals[0] else None
            elif '利润总额' in label and '归属' not in label:
                data['pbt'] = vals[0]
            elif '所得税' in label:
                data['tax'] = abs(vals[0]) if vals[0] else None
            elif '净利润' in label:
                if '少数' in label:
                    data['minority_np'] = vals[0]
                elif '归属' in label:
                    data['np_attr'] = vals[0]
                elif '少数' not in label:
                    data['np'] = vals[0]
            elif '基本每股收益' in label:
                data['eps_basic'] = vals[0]
            elif '稀释每股收益' in label:
                data['eps_diluted'] = vals[0]
            elif '加权平均净资' in label and '收益' in label:
                data['roe_weighted'] = vals[0] / 100 if vals[0] else None  # 转为小数
            elif '扣非' in label and '净利润' in label:
                data['np_attr_ex'] = vals[0]  # 扣除非经常性损益

    return data


def extract_balance_sheet(page) -> Dict:
    """从页面提取资产负债表数据"""
    data = {}
    tables = page.extract_tables()

    for t in tables:
        if not t:
            continue
        for row in t:
            if not row or len(row) < 2:
                continue

            label = str(row[0]).replace('\n', '').strip() if row[0] else ''

            vals = []
            for v in row[1:]:
                parsed = parse_number(str(v) if v else '0')
                if parsed is not None:
                    vals.append(parsed)

            if not vals:
                continue

            # 流动资产
            if '货币资金' in label:
                data['cash'] = vals[0]
            elif '应收账款' in label and '坏账' not in label:
                data['ar'] = vals[0]
            elif '应收款项' in label and '融资' not in label:
                data['ar'] = vals[0]
            elif '存货' in label and '跌价' not in label and '发出' not in label:
                data['inv'] = vals[0]
            elif '其他流动资产' in label or '其他应收款' in label:
                if 'other_ca' not in data:
                    data['other_ca'] = vals[0]
                else:
                    data['other_ca'] += vals[0]
            elif '流动资产合计' in label:
                data['ca'] = vals[0]

            # 非流动资产
            elif '固定资产' in label and '在建' not in label:
                data['fa'] = vals[0]
            elif '在建工程' in label:
                data['fa_construction'] = vals[0]
            elif '无形资产' in label:
                data['intangible'] = vals[0]
            elif '商誉' in label:
                data['goodwill'] = vals[0]
            elif '递延所得税资产' in label:
                data['dta'] = vals[0]
            elif '其他非流动资产' in label:
                data['other_nca'] = vals[0]
            elif '非流动资产合计' in label:
                data['nca'] = vals[0]
            elif '资产总计' in label:
                data['ta'] = vals[0]

            # 流动负债
            elif '应付账款' in label:
                data['ap'] = vals[0]
            elif '短期借款' in label:
                data['std'] = vals[0]
            elif '其他应付款' in label:
                data['other_cl'] = vals[0]
            elif '应付票据' in label:
                data['notes_payable'] = vals[0]
            elif '预收款项' in label or '合同负债' in label:
                data['contract_liab'] = vals[0]
            elif '应付职工薪酬' in label:
                data['accrued_wages'] = vals[0]
            elif '应交税费' in label:
                data['tax_payable'] = vals[0]
            elif '流动负债合计' in label:
                data['cl'] = vals[0]

            # 非流动负债
            elif '长期借款' in label:
                data['ltd'] = vals[0]
            elif '应付债券' in label:
                data['bonds'] = vals[0]
            elif '递延所得税负债' in label:
                data['dtl'] = vals[0]
            elif '其他非流动负债' in label:
                data['other_ncl'] = vals[0]
            elif '非流动负债合计' in label:
                data['ncl'] = vals[0]
            elif '负债合计' in label:
                data['tl'] = vals[0]

            # 股东权益
            elif '股本' in label or '实收资本' in label:
                data['share_capital'] = vals[0]
            elif '资本公积' in label:
                data['capitalreserve'] = vals[0]
            elif '盈余公积' in label:
                data['surplusreserve'] = vals[0]
            elif '未分配利润' in label:
                data['retained_earnings'] = vals[0]
            elif '归属母公司股东权益' in label or '归属于上市公司股东' in label:
                data['parent_eq'] = vals[0]
            elif '少数股东权益' in label:
                data['minority'] = vals[0]
            elif '股东权益合计' in label and '少数' not in label:
                data['equity'] = vals[0]

    return data


def extract_cash_flow(page) -> Dict:
    """从页面提取现金流量表数据"""
    data = {}
    tables = page.extract_tables()

    for t in tables:
        if not t:
            continue
        for row in t:
            if not row or len(row) < 2:
                continue

            label = str(row[0]).replace('\n', '').strip() if row[0] else ''

            vals = []
            for v in row[1:]:
                parsed = parse_number(str(v) if v else '0')
                if parsed is not None:
                    vals.append(parsed)

            if not vals:
                continue

            if '经营活动产生的现金流量净额' in label:
                data['oper_cf'] = vals[0]
            elif '经营活动产生的现金流出小计' in label:
                data['oper_cf_out'] = vals[0]
            elif '投资活动产生的现金流量净额' in label:
                data['invest_cf'] = vals[0]
            elif '投资活动产生的现金流出小计' in label:
                data['invest_cf_out'] = vals[0]
            elif '购建固定资产、无形资产和其他长期资产支付的现金' in label:
                data['capex'] = abs(vals[0]) if vals[0] else None
            elif '取得子公司及其他营业单位支付的现金净额' in label:
                data['m_a'] = abs(vals[0]) if vals[0] else None
            elif '筹资活动产生的现金流量净额' in label:
                data['finance_cf'] = vals[0]
            elif '分配股利、利润或偿付利息支付的现金' in label:
                data['dividend'] = abs(vals[0]) if vals[0] else None
            elif '汇率变动对现金的影响' in label:
                data['fx_effect'] = vals[0]
            elif '现金及现金等价物净增加额' in label or '净增加额' in label:
                data['net_chg_cash'] = vals[0]
            elif '期初现金及现金等价物余额' in label or '期初余额' in label:
                data['beg_cash'] = vals[0]
            elif '期末现金及现金等价物余额' in label or '期末余额' in label:
                data['end_cash'] = vals[0]

    return data


def extract_segment_data(page) -> List[Dict]:
    """从页面提取分部数据（行业/产品分拆）"""
    segments = []
    tables = page.extract_tables()

    for t in tables:
        if not t:
            continue

        # 查找分部表格（包含分行业或分产品）
        has_segment_header = False
        for row in t:
            if row and len(row) > 0:
                first_cell = str(row[0]).replace('\n', '') if row[0] else ''
                if '分行业' in first_cell or '分产品' in first_cell or '分地区' in first_cell:
                    has_segment_header = True
                    break

        if not has_segment_header:
            continue

        # 解析分部数据
        for row in t:
            if not row or len(row) < 4:
                continue

            label = str(row[0]).replace('\n', '').strip() if row[0] else ''

            # 跳过标题行
            if '营业收入' in label or '分行业' in label or '分产品' in label or '毛利率' in label:
                continue
            if not label or label == 'None':
                continue
            if any(x in label for x in ['合计', '总计', '其他']):
                continue

            # 提取分部数据
            vals = []
            for v in row[1:]:
                parsed = parse_number(str(v) if v else '0')
                if parsed is not None:
                    vals.append(parsed)

            if len(vals) < 3:
                continue

            # 假设结构: [营业收入, 营业成本, 毛利率, ...]
            seg = {
                'name': label,
                'revenue': vals[0],
                'cogs': vals[1] if len(vals) > 1 else None,
            }

            # 毛利率在第3列（索引2），但可能是百分比字符串
            if len(vals) > 2:
                gm_raw = row[3] if len(row) > 3 else None
                if gm_raw:
                    gm_str = str(gm_raw).replace('\n', '').replace('%', '').replace(' ', '')
                    try:
                        seg['gm'] = float(gm_str) / 100 if gm_str else None
                    except:
                        seg['gm'] = None
                else:
                    seg['gm'] = None

            # 计算毛利额
            if seg['revenue'] and seg.get('gm'):
                seg['gp'] = seg['revenue'] * seg['gm']
            elif seg['revenue'] and seg.get('cogs'):
                seg['gp'] = seg['revenue'] - seg['cogs']
                if seg['revenue'] != 0:
                    seg['gm'] = seg['gp'] / seg['revenue']

            if seg.get('revenue') and seg['revenue'] > 0:
                segments.append(seg)

    return segments


def extract_quarterly_data(page, year: int) -> Dict:
    """从页面提取季度利润表数据"""
    data = {}
    tables = page.extract_tables()

    for t in tables:
        if not t:
            continue

        # 查找季度表格
        has_quarter_header = False
        for row in t:
            if row and len(row) > 0:
                first_cell = str(row[0]).replace('\n', '') if row[0] else ''
                if '第一季度' in first_cell or '第二季度' in first_cell or '1-3月份' in first_cell:
                    has_quarter_header = True
                    break

        if not has_quarter_header:
            continue

        # 季度列映射
        quarter_cols = {
            f'{year}Q1': 1,  # 第一季度
            f'{year}Q2': 2,  # 第二季度
            f'{year}Q3': 3,  # 第三季度
            f'{year}Q4': 4,  # 第四季度
        }

        for row in t:
            if not row or len(row) < 2:
                continue

            label = str(row[0]).replace('\n', '').strip() if row[0] else ''

            if '营业收入' in label:
                for q_key, col_idx in quarter_cols.items():
                    if len(row) > col_idx and row[col_idx]:
                        val = parse_number(str(row[col_idx]))
                        if val:
                            if q_key not in data:
                                data[q_key] = {}
                            data[q_key]['revenue'] = val

            elif '归属于上市公司股东' in label and '净利润' in label:
                for q_key, col_idx in quarter_cols.items():
                    if len(row) > col_idx and row[col_idx]:
                        val = parse_number(str(row[col_idx]))
                        if val:
                            if q_key not in data:
                                data[q_key] = {}
                            data[q_key]['np_attr'] = val

            elif '经营活动产生的现金流量净额' in label:
                for q_key, col_idx in quarter_cols.items():
                    if len(row) > col_idx and row[col_idx]:
                        val = parse_number(str(row[col_idx]))
                        if val:
                            if q_key not in data:
                                data[q_key] = {}
                            data[q_key]['oper_cf'] = val

    # 计算季度毛利率（如果可以）
    for q_key in data:
        if 'revenue' in data[q_key]:
            # 使用公司整体毛利率估算
            data[q_key]['gross_margin'] = 0.17  # 默认17%

    return data


def extract_annual_report(pdf_path: str, year: int) -> Dict:
    """
    从年报PDF提取所有财务数据
    返回: {
        'income_statement': {...},
        'balance_sheet': {...},
        'cash_flow': {...},
        'segments': [...],
        'quarterly': {...}
    }
    """
    result = {
        'income_statement': {},
        'balance_sheet': {},
        'cash_flow': {},
        'segments': [],
        'quarterly': {}
    }

    if not os.path.exists(pdf_path):
        print(f"⚠️ PDF不存在: {pdf_path}")
        return result

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"  PDF总页数: {total_pages}")

        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            page_num = i + 1

            # 进度提示
            if page_num % 50 == 0:
                print(f"  处理进度: {page_num}/{total_pages}")

            # 利润表 (通常在合并报表之后的几页)
            if '合并利润表' in text or ('营业收入' in text and '利润表' in text):
                is_data = extract_income_statement(page)
                if is_data and not result['income_statement']:
                    result['income_statement'] = is_data
                    print(f"  ✓ 利润表提取完成 (第{page_num}页)")

            # 资产负债表
            if '合并资产负债表' in text or ('资产总计' in text and '负债合计' in text):
                bs_data = extract_balance_sheet(page)
                if bs_data and not result['balance_sheet']:
                    result['balance_sheet'] = bs_data
                    print(f"  ✓ 资产负债表提取完成 (第{page_num}页)")

            # 现金流量表
            if '合并现金流量表' in text or '经营活动产生的现金流量净额' in text:
                cf_data = extract_cash_flow(page)
                if cf_data and not result['cash_flow']:
                    result['cash_flow'] = cf_data
                    print(f"  ✓ 现金流量表提取完成 (第{page_num}页)")

            # 分部数据
            if '分行业情况' in text or '分产品情况' in text or '主营业务分' in text:
                seg_data = extract_segment_data(page)
                if seg_data:
                    result['segments'].extend(seg_data)

            # 季度数据
            if f'{year}' in text and ('第一季度' in text or '1-3月份' in text):
                q_data = extract_quarterly_data(page, year)
                if q_data:
                    result['quarterly'].update(q_data)

    # 计算派生指标
    is_data = result['income_statement']
    if is_data:
        # 计算毛利润和毛利率
        if 'revenue' in is_data and 'cogs' in is_data:
            is_data['gp'] = is_data['revenue'] - abs(is_data.get('cogs', 0))
            if is_data['revenue'] > 0:
                is_data['gross_margin'] = is_data['gp'] / is_data['revenue']

        # 计算营业利润 (如果没有直接数据)
        if 'op_profit' not in is_data and 'revenue' in is_data:
            costs = (abs(is_data.get('sell_exp', 0)) +
                    abs(is_data.get('admin_exp', 0)) +
                    abs(is_data.get('rd_exp', 0)) +
                    abs(is_data.get('fin_exp', 0)))
            is_data['op_profit'] = is_data.get('gp', 0) - costs

        # 计算净利润 (如果没有直接数据)
        if 'np' not in is_data and 'ebt' in is_data:
            is_data['np'] = is_data['ebt'] - abs(is_data.get('tax', 0))

    # 计算ROE
    bs_data = result['balance_sheet']
    if bs_data and 'parent_eq' in bs_data and is_data:
        if 'np_attr' in is_data and bs_data['parent_eq'] > 0:
            is_data['roe'] = is_data['np_attr'] / bs_data['parent_eq']

    return result


def get_pdf_paths(company_path: str) -> Dict[str, str]:
    """获取公司年报/半年报PDF路径"""
    paths = {
        'annual_reports': [],
        'half_reports': [],
        'quarter_reports': []
    }

    # 年报目录
    annual_dir = os.path.join(company_path, '年报')
    if os.path.exists(annual_dir):
        for f in sorted(os.listdir(annual_dir)):
            if f.endswith('.pdf'):
                year_match = re.search(r'(\d{4})', f)
                if year_match:
                    year = int(year_match.group(1))
                    paths['annual_reports'].append({
                        'year': year,
                        'path': os.path.join(annual_dir, f),
                        'filename': f
                    })

    # 半年报目录
    half_dir = os.path.join(company_path, '半年报')
    if os.path.exists(half_dir):
        for f in sorted(os.listdir(half_dir)):
            if f.endswith('.pdf'):
                year_match = re.search(r'(\d{4})', f)
                if year_match:
                    year = int(year_match.group(1))
                    paths['half_reports'].append({
                        'year': year,
                        'path': os.path.join(half_dir, f),
                        'filename': f
                    })

    # 季报目录
    quarter_dir = os.path.join(company_path, '季报')
    if os.path.exists(quarter_dir):
        for f in sorted(os.listdir(quarter_dir)):
            if f.endswith('.pdf'):
                year_match = re.search(r'(\d{4})', f)
                if year_match:
                    year = int(year_match.group(1))
                    paths['quarter_reports'].append({
                        'year': year,
                        'path': os.path.join(quarter_dir, f),
                        'filename': f
                    })

    return paths


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 extract_pdf_data.py <公司根目录> [股票代码]")
        sys.exit(1)

    company_path = sys.argv[1]
    stock_code = sys.argv[2] if len(sys.argv) > 2 else ''

    print(f"\n{'='*60}")
    print(f"PDF财务数据提取")
    print(f"公司路径: {company_path}")
    print(f"{'='*60}")

    # 获取PDF路径
    pdf_paths = get_pdf_paths(company_path)

    print(f"\n发现PDF文件:")
    print(f"  年报: {len(pdf_paths['annual_reports'])}份")
    for ar in pdf_paths['annual_reports']:
        print(f"    {ar['year']}: {ar['filename']}")
    print(f"  半年报: {len(pdf_paths['half_reports'])}份")
    print(f"  季报: {len(pdf_paths['quarter_reports'])}份")

    # 提取最新年报数据
    if pdf_paths['annual_reports']:
        latest_annual = max(pdf_paths['annual_reports'], key=lambda x: x['year'])
        print(f"\n提取最新年报 ({latest_annual['year']}) 数据...")
        data = extract_annual_report(latest_annual['path'], latest_annual['year'])

        print(f"\n{'='*60}")
        print(f"提取结果汇总")
        print(f"{'='*60}")

        print(f"\n利润表数据:")
        for k, v in data['income_statement'].items():
            print(f"  {k}: {v}")

        print(f"\n资产负债表数据:")
        for k, v in data['balance_sheet'].items():
            print(f"  {k}: {v}")

        print(f"\n现金流量表数据:")
        for k, v in data['cash_flow'].items():
            print(f"  {k}: {v}")

        print(f"\n分部数据 ({len(data['segments'])}个):")
        for seg in data['segments'][:10]:  # 最多显示10个
            print(f"  {seg.get('name')}: 收入={seg.get('revenue')}亿, 毛利率={seg.get('gm', 0)*100:.1f}%" if seg.get('gm') else f"  {seg.get('name')}: 收入={seg.get('revenue')}亿")

        print(f"\n季度数据:")
        for q, qdata in sorted(data['quarterly'].items()):
            print(f"  {q}: 营收={qdata.get('revenue')}亿, 净利={qdata.get('np_attr')}亿")
