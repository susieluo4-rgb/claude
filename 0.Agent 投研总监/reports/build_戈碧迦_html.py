#!/usr/bin/env python3
"""生成戈碧迦投研HTML报告"""

import os
import re

base = '/Users/zhuang225/0.Agent 投研总监/reports/戈碧迦_2026-04-10'

def read_report(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return f"报告文件不存在: {path}"

def md_to_html(md_content):
    """Markdown -> HTML 转换"""
    html = md_content

    # 标题 (顺序: h3 -> h2 -> h1)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # 表格 - 使用正确正则
    def convert_table(m):
        table = m.group(0)
        rows = [r for r in table.split('\n') if r.strip()]
        if len(rows) < 2:
            return table
        header = rows[0].strip('|').split('|')
        header_html = '<thead><tr>' + ''.join(f'<th>{c.strip()}</th>' for c in header) + '</tr></thead>'
        body_rows = []
        for row in rows[2:]:
            cols = row.strip('|').split('|')
            body_rows.append('<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in cols) + '</tr>')
        body_html = '<tbody>' + ''.join(body_rows) + '</tbody>'
        return f'<table class="report-table">{header_html}{body_html}</table>'

    html = re.sub(r'(\|.+\|\n\|[-| :]+\|(?:\n\|[^\n]+\|)+)', convert_table, html, flags=re.M)

    # 粗体
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # 斜体
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # 分割线
    html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)
    # 行内代码
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # 列表
    lines = html.split('\n')
    result = []
    in_list = False
    for line in lines:
        m = re.match(r'^[-*] (.+)', line)
        if m:
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append(f'<li>{m.group(1).strip()}</li>')
        else:
            if in_list:
                result.append('</ul>')
                in_list = False
            result.append(line)
    if in_list:
        result.append('</ul>')
    html = '\n'.join(result)

    # 段落包裹
    blocks = re.split(r'\n{2,}', html)
    wrapped = []
    for block in blocks:
        b = block.strip()
        if not b:
            continue
        if re.match(r'^<(h[1-6]|table|ul|ol|hr|div|blockquote)', b):
            wrapped.append(b)
        else:
            wrapped.append(f'<p>{b}</p>')
    html = '\n'.join(wrapped)

    return html

# ========== 读取所有报告 ==========
reports = {
    '00_综合报告': f'{base}/00_综合报告.md',
    '01_宏观环境': f'{base}/01_宏观环境.md',
    '02_行业分析': f'{base}/02_行业分析.md',
    '03_数据校验': f'{base}/03_数据校验.md',
    '04_基本面研究': f'{base}/04_基本面研究.md',
    '05_市场情绪': f'{base}/05_市场情绪.md',
    '06_技术分析': f'{base}/06_技术分析.md',
    '07_风险评估': f'{base}/07_风险评估.md',
    '08_基金经理评估': f'{base}/08_基金经理评估.md',
    '09_综合报告': f'{base}/09_综合报告.md',
}

html_parts = {}
for name, path in reports.items():
    content = read_report(path)
    html_parts[name] = md_to_html(content)

# ========== KPI 网格 ==========
kpi_html = """
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">投资评级</div>
        <div class="kpi-value" style="color:#D32F2F">看空 (Sell)</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">质量评分</div>
        <div class="kpi-value" style="color:#FF9800">C-档</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">风险等级</div>
        <div class="kpi-value" style="color:#D32F2F">高 8.18/10</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">最新股价</div>
        <div class="kpi-value">42.19 元</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">总市值</div>
        <div class="kpi-value">61.4 亿</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">PE (2025E)</div>
        <div class="kpi-value" style="color:#D32F2F">215x</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">合理估值</div>
        <div class="kpi-value" style="color:#00C853">18-22 元</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">下行空间</div>
        <div class="kpi-value" style="color:#D32F2F">-50% ~ -65%</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">建议仓位</div>
        <div class="kpi-value" style="color:#D32F2F">0-2%</div>
    </div>
</div>
"""

# ========== 情绪/趋势标签 ==========
summary_box = """
<div class="summary-box">
    <strong>投资评级：看空（Sell / Avoid）</strong> |
    质量评分：C-档 |
    风险等级：<span class="risk-high">高</span> |
    建议操作：现有持仓清仓或减至0-2%，卖出区间41.50-43.00元；未持仓不建仓
</div>
"""

# ========== Agent结论表格 ==========
agent_conclusions = """
<div class="agent-summary">
<h2>各Agent结论汇总</h2>
<table class="report-table">
<thead><tr><th>Agent</th><th>结论</th><th>评分</th></tr></thead>
<tbody>
<tr><td>宏观Agent</td><td>中性偏有利</td><td><span class="tag tag-neutral">中性</span></td></tr>
<tr><td>行业Agent</td><td>平稳偏下行</td><td><span class="tag tag-warn">谨慎</span></td></tr>
<tr><td>数据校验Agent</td><td>基本一致，应收异常</td><td><span class="tag tag-neutral">B档</span></td></tr>
<tr><td>基本面Agent</td><td>盈利能力C，成长性C</td><td><span class="tag tag-bad">C+</span></td></tr>
<tr><td>情绪Agent</td><td>偏热，业绩与情绪背离</td><td><span class="tag tag-warn">7.3/10</span></td></tr>
<tr><td>技术Agent</td><td>V型反转，短期偏多</td><td><span class="tag tag-good">偏多</span></td></tr>
<tr><td>风险控制Agent</td><td>估值泡沫+应收风险</td><td><span class="tag tag-bad">高 8.18</span></td></tr>
<tr><td><strong>基金经理Agent</strong></td><td><strong>看空，不介入</strong></td><td><span class="tag tag-bad">C-档</span></td></tr>
</tbody>
</table>
</div>
"""

# ========== 催化剂时间轴 ==========
catalyst_html = """
<div class="catalyst-section">
<h2>催化剂时间轴</h2>
<div class="timeline">
    <div class="timeline-item short-term">
        <div class="timeline-dot"></div>
        <div class="timeline-content">
            <div class="timeline-label">短期（1-3月）</div>
            <ul>
                <li>2025年报披露（关注应收/存货质量）</li>
                <li>融资余额变化趋势（是否开始下降）</li>
                <li>技术面回踩40.50-41.00确认支撑</li>
            </ul>
        </div>
    </div>
    <div class="timeline-item mid-term">
        <div class="timeline-dot"></div>
        <div class="timeline-content">
            <div class="timeline-label">中期（3-6月）</div>
            <ul>
                <li>2026Q1/Q2财报（半导体载板收入占比）</li>
                <li>智迦玻纤子公司建设进度</li>
                <li>纳米微晶客户是否恢复下单</li>
            </ul>
        </div>
    </div>
    <div class="timeline-item long-term">
        <div class="timeline-dot"></div>
        <div class="timeline-content">
            <div class="timeline-label">长期（6-12月）</div>
            <ul>
                <li>半导体玻璃基板产业化进展</li>
                <li>AI手机换机周期实质启动</li>
                <li>北交所流动性政策改革</li>
            </ul>
        </div>
    </div>
</div>
</div>
"""

# ========== 完整HTML ==========
full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>戈碧迦 (920438.BJ) 投研报告 2026-04-10</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;line-height:1.65;color:#333;background:#f5f5f5;}}

/* Header */
header{{background:linear-gradient(135deg,#1a237e,#283593);color:#fff;padding:3px 20px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.12);}}
.top-bar{{display:flex;justify-content:space-between;align-items:center;max-width:1200px;margin:0 auto;}}
header h1{{font-size:14px;line-height:1.2;}}
header .subtitle{{opacity:0.85;font-size:12px;margin-top:1px;}}
.top-bar .date{{font-size:12px;opacity:0.9;white-space:nowrap;}}

/* KPI Grid */
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:14px;margin-bottom:20px;}}
.kpi-card{{background:#f8f9fa;border-radius:8px;padding:14px 10px;text-align:center;border:1px solid #e8eaf6;}}
.kpi-label{{font-size:12px;color:#777;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.3px;line-height:1.3;}}
.kpi-value{{font-size:17px;font-weight:700;color:#1a237e;}}

/* Summary Box */
.summary-box{{background:linear-gradient(135deg,#ffebee,#fff3e0);border:1px solid #ef9a9a;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;}}
.risk-high{{color:#D32F2F;font-weight:700;}}

/* Agent Summary */
.agent-summary{{margin:20px 0;}}

/* Tags */
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;}}
.tag-good{{background:#E8F5E9;color:#2E7D32;}}
.tag-neutral{{background:#FFF8E1;color:#F57F17;}}
.tag-warn{{background:#FFF3E0;color:#E65100;}}
.tag-bad{{background:#FFEBEE;color:#C62828;}}

/* Timeline */
.catalyst-section{{margin:20px 0;}}
.timeline{{position:relative;padding-left:24px;}}
.timeline::before{{content:'';position:absolute;left:8px;top:0;bottom:0;width:2px;background:#e0e0e0;}}
.timeline-item{{position:relative;margin-bottom:16px;}}
.timeline-dot{{position:absolute;left:-20px;top:4px;width:12px;height:12px;border-radius:50%;border:2px solid #fff;}}
.timeline-item.short-term .timeline-dot{{background:#2196F3;}}
.timeline-item.mid-term .timeline-dot{{background:#FF9800;}}
.timeline-item.long-term .timeline-dot{{background:#4CAF50;}}
.timeline-label{{font-size:12px;font-weight:700;color:#555;margin-bottom:4px;}}
.timeline-content ul{{margin-left:16px;font-size:13px;}}

/* Container */
.container{{display:flex;max-width:1200px;margin:0 auto;min-height:calc(100vh - 60px);}}

/* Sidebar */
.sidebar{{width:170px;background:#fff;padding:16px 10px;position:sticky;top:38px;height:calc(100vh - 38px);overflow-y:auto;border-right:1px solid #e0e0e0;flex-shrink:0;}}
.sidebar h3{{font-size:13px;color:#1a237e;margin-bottom:10px;padding:0 6px;}}
.nav-item{{display:block;padding:7px 10px;font-size:12px;color:#555;cursor:pointer;border-radius:4px;margin-bottom:2px;transition:all 0.15s;}}
.nav-item:hover{{background:#e8eaf6;color:#1a237e;}}
.nav-item.active{{background:#3949ab;color:#fff;font-weight:600;}}

/* Main Content */
.main{{flex:1;padding:16px 24px;max-width:960px;background:#fff;margin:12px 12px 12px 0;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.08);}}
.section{{display:none;}}
.section.active{{display:block;}}
.main h1{{font-size:20px;color:#1a237e;margin:20px 0 12px;padding-bottom:8px;border-bottom:2px solid #e8eaf6;}}
.main h2{{font-size:16px;color:#283593;margin:16px 0 8px;}}
.main h3{{font-size:14px;color:#3949ab;margin:12px 0 6px;}}
.main p{{margin:6px 0;font-size:14px;}}

/* Tables */
.report-table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;}}
.report-table th{{background:#3949ab;color:#fff;padding:8px 12px;text-align:left;font-weight:500;}}
.report-table td{{padding:7px 12px;border-bottom:1px solid #eee;}}
.report-table tr:hover td{{background:#f8f9fa;}}
.report-table .num{{text-align:right;font-variant-numeric:tabular-nums;}}

/* Lists */
.main ul{{margin:8px 0 8px 20px;font-size:14px;}}
.main li{{margin:3px 0;}}

/* HR */
hr{{border:none;border-top:1px solid #e0e0e0;margin:16px 0;}}

/* Search */
.search-box{{padding:8px 20px;background:#fff;border-bottom:1px solid #e0e0e0;}}
.search-box input{{width:100%;max-width:400px;padding:7px 12px;border:1px solid #ddd;border-radius:6px;font-size:13px;outline:none;}}
.search-box input:focus{{border-color:#3949ab;box-shadow:0 0 0 2px rgba(57,73,171,0.15);}}
mark{{background:#FFF176;padding:1px 3px;border-radius:2px;}}

/* Footer */
.footer{{text-align:center;padding:20px 0;color:#999;font-size:12px;border-top:1px solid #e0e0e0;margin-top:24px;}}

/* Print button */
.print-btn{{position:fixed;bottom:24px;right:24px;background:#3949ab;color:#fff;border:none;border-radius:50%;width:48px;height:48px;font-size:20px;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.2);z-index:200;display:flex;align-items:center;justify-content:center;transition:all 0.2s;}}
.print-btn:hover{{background:#1a237e;transform:scale(1.1);}}

/* Code */
code{{background:#f5f5f5;padding:2px 6px;border-radius:3px;font-size:12px;color:#C62828;}}

/* Print */
@media print{{
    header{{position:static;}}
    .sidebar,.search-box,.print-btn{{display:none !important;}}
    .section{{display:block !important;page-break-after:always;}}
    .main{{margin:0;box-shadow:none;}}
}}
</style>
</head>
<body>

<header>
    <div class="top-bar">
        <div>
            <h1>戈碧迦 (920438.BJ) 投研报告</h1>
            <div class="subtitle">多Agent协同研究 | 光学光电子 / 光学玻璃</div>
        </div>
        <div class="date">2026-04-10</div>
    </div>
</header>

<div class="search-box">
    <input type="text" id="searchInput" placeholder="搜索报告内容... (Ctrl+F)">
</div>

<div class="container">
    <nav class="sidebar">
        <h3>报告导航</h3>
        <a class="nav-item active" onclick="showSection('summary', this)">综合报告</a>
        <a class="nav-item" onclick="showSection('macro', this)">01 宏观环境</a>
        <a class="nav-item" onclick="showSection('industry', this)">02 行业分析</a>
        <a class="nav-item" onclick="showSection('datacheck', this)">03 数据校验</a>
        <a class="nav-item" onclick="showSection('fundamental', this)">04 基本面研究</a>
        <a class="nav-item" onclick="showSection('sentiment', this)">05 市场情绪</a>
        <a class="nav-item" onclick="showSection('technical', this)">06 技术分析</a>
        <a class="nav-item" onclick="showSection('risk', this)">07 风险评估</a>
        <a class="nav-item" onclick="showSection('pm', this)">08 基金经理评估</a>
        <a class="nav-item" onclick="showSection('final', this)">09 综合报告</a>
    </nav>

    <div class="main">
        <!-- 综合报告 -->
        <div id="summary" class="section active">
            <h1>戈碧迦 (920438.BJ) 综合投研报告</h1>
            {kpi_html}
            {summary_box}
            {agent_conclusions}
            {catalyst_html}
            <h2>报告摘要</h2>
            {html_parts.get('00_综合报告', '')}
        </div>

        <!-- 01 宏观环境 -->
        <div id="macro" class="section">
            <h1>01 宏观环境分析</h1>
            {html_parts.get('01_宏观环境', '')}
        </div>

        <!-- 02 行业分析 -->
        <div id="industry" class="section">
            <h1>02 行业分析</h1>
            {html_parts.get('02_行业分析', '')}
        </div>

        <!-- 03 数据校验 -->
        <div id="datacheck" class="section">
            <h1>03 数据校验</h1>
            {html_parts.get('03_数据校验', '')}
        </div>

        <!-- 04 基本面研究 -->
        <div id="fundamental" class="section">
            <h1>04 基本面研究</h1>
            {html_parts.get('04_基本面研究', '')}
        </div>

        <!-- 05 市场情绪 -->
        <div id="sentiment" class="section">
            <h1>05 市场情绪</h1>
            {html_parts.get('05_市场情绪', '')}
        </div>

        <!-- 06 技术分析 -->
        <div id="technical" class="section">
            <h1>06 技术分析</h1>
            {html_parts.get('06_技术分析', '')}
        </div>

        <!-- 07 风险评估 -->
        <div id="risk" class="section">
            <h1>07 风险评估</h1>
            {html_parts.get('07_风险评估', '')}
        </div>

        <!-- 08 基金经理评估 -->
        <div id="pm" class="section">
            <h1>08 基金经理评估</h1>
            {html_parts.get('08_基金经理评估', '')}
        </div>

        <!-- 09 综合报告 -->
        <div id="final" class="section">
            <h1>09 综合报告</h1>
            {html_parts.get('09_综合报告', '')}
        </div>

        <div class="footer">
            本报告由AI多Agent系统自动生成 | 数据来源：iFind, AlphaPai, 公开研报 | 仅供参考，不构成投资建议
        </div>
    </div>
</div>

<button class="print-btn" onclick="window.print()" title="导出PDF">📄</button>

<script>
function showSection(id, el) {{
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    if (el) el.classList.add('active');
    window.scrollTo({{top: 0, behavior: 'smooth'}});
}}

// Search
const searchInput = document.getElementById('searchInput');
let searchTimeout;
searchInput.addEventListener('input', function() {{
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {{
        const query = this.value.trim();
        if (!query) {{
            document.querySelectorAll('mark').forEach(m => {{
                const p = m.parentNode;
                p.replaceChild(document.createTextNode(m.textContent), m);
                p.normalize();
            }});
            return;
        }}
        // Remove previous highlights
        document.querySelectorAll('mark').forEach(m => {{
            const p = m.parentNode;
            p.replaceChild(document.createTextNode(m.textContent), m);
            p.normalize();
        }});
        // Highlight in active section
        const active = document.querySelector('.section.active');
        if (!active) return;
        const walker = document.createTreeWalker(active, NodeFilter.SHOW_TEXT, null, false);
        const textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);
        textNodes.forEach(node => {{
            const text = node.textContent;
            const idx = text.toLowerCase().indexOf(query.toLowerCase());
            if (idx !== -1 && node.parentNode.tagName !== 'MARK') {{
                const before = text.substring(0, idx);
                const match = text.substring(idx, idx + query.length);
                const after = text.substring(idx + query.length);
                const frag = document.createDocumentFragment();
                if (before) frag.appendChild(document.createTextNode(before));
                const mark = document.createElement('mark');
                mark.textContent = match;
                frag.appendChild(mark);
                if (after) frag.appendChild(document.createTextNode(after));
                node.parentNode.replaceChild(frag, node);
            }}
        }});
    }}, 200);
}});

// Ctrl+F focus
document.addEventListener('keydown', function(e) {{
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {{
        e.preventDefault();
        searchInput.focus();
    }}
}});
</script>

</body>
</html>
"""

output_path = f'{base}/index.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f'HTML report generated: {output_path}')
print(f'File size: {os.path.getsize(output_path)} bytes')
