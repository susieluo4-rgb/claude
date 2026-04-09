---
name: RL-html-report-builder-V1.0
description: 投研报告HTML报告构建工具。将多Agent生成的Markdown报告合成为可搜索、可打印的交互式HTML报告。当用户说"生成HTML报告"、"构建投研报告"、"合成报告为HTML"、"生成index.html"时触发此skill。此skill负责维护 build_{公司名}_html.py 报告构建脚本，包含CSS样式表、KPI网格、Markdown→HTML转换（含表格正则）等核心逻辑。
---

# 投研报告 HTML 构建 Skill

将多Agent输出的 Markdown 报告（00_综合报告.md ~ 08_基金经理评估.md）合成为单一交互式 HTML 页面。

---

## 核心文件结构

```
reports/{公司名}_{日期}/
├── 00_综合报告.md
├── 01_宏观环境.md
├── 02_行业分析.md
├── 03_数据校验.md
├── 04_基本面研究.md
├── 05_市场情绪.md
├── 06_技术分析.md
├── 07_风险评估.md
├── 08_基金经理评估.md
├── 09_综合报告.md          ← 可选
└── index.html              ← 本skill输出
```

构建脚本命名规范：`build_{公司名}_html.py`，存放于 `reports/` 目录下。

---

## CSS 核心规范（必须严格遵守）

### KPI 网格

```css
.kpi-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(155px,1fr)); gap:14px; margin-bottom:20px; }
.kpi-card { background:#f8f9fa; border-radius:8px; padding:14px 10px; text-align:center; border:1px solid #e8eaf6; }
.kpi-label { font-size:12px; color:#777; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.3px; line-height:1.3; }
.kpi-value { font-size:17px; font-weight:700; color:#1a237e; }
```

**关键参数说明：**
- `minmax(155px,1fr)`：中文标签（如"营收增速"、"净利润(亿元)"）4-6字符时，140px 会导致文字换行拥挤，155px 是安全阈值
- `font-size:12px`：标签文字最小 12px，11px 太小导致多字符标签挤压
- `line-height:1.3`：提供足够垂直呼吸空间
- `padding:14px 10px`：水平 padding 略小于垂直，避免过宽

### 报告头部（压缩版）

```css
header { background:linear-gradient(135deg,#1a237e,#283593); color:#fff; padding:3px 20px; position:sticky; top:0; z-index:100; box-shadow:0 2px 8px rgba(0,0,0,0.12); }
header h1 { font-size:14px; line-height:1.2; }
header .subtitle { opacity:0.85; font-size:12px; margin-top:1px; }
```

目标：头部高度压缩到 35px 左右，不影响下方报告阅读。

### 表格

```css
.report-table { width:100%; border-collapse:collapse; margin:12px 0; font-size:13px; }
.report-table th { background:#3949ab; color:#fff; padding:8px 12px; text-align:left; font-weight:500; }
.report-table td { padding:7px 12px; border-bottom:1px solid #eee; }
.report-table tr:hover td { background:#f8f9fa; }
.report-table .num { text-align:right; font-variant-numeric:tabular-nums; }
```

---

## Markdown → HTML 转换核心逻辑

### 表格正则（关键！）

**❌ 错误写法（只捕获第一行数据）：**
```python
html = re.sub(r'(\|.+\|\n\|[-| :]+\|\n.+)+', convert_table, html, flags=re.M)
```

`(.+)+` 在多行场景下贪婪匹配且只能捕获最后一个重复组，导致每张表只有第一行数据行被包裹在 `<tbody>`，其余行变成游离文本外露。

**✅ 正确写法（2026-04-09 修正）：**
```python
html = re.sub(r'(\|.+\|\n\|[-| :]+\|(?:\n\|[^\n|]+\|)+)', convert_table, html, flags=re.M)
```

关键改动：`[^\n|]+` 替代 `.+`，避免贪婪匹配；显式 `(?:\n\|...\|)+` 精确匹配每行数据行。

```python
def convert_table(m):
    table = m.group(0)
    rows = [r for r in table.split('\n') if r.strip()]
    if len(rows) < 2:
        return table
    header = rows[0].strip('|').split('|')
    header_html = '<thead><tr>' + ''.join(f'<th>{c.strip()}</th>' for c in header) + '</tr></thead>'
    body_rows = []
    for row in rows[2:]:          # 跳过表头和分隔行
        cols = row.strip('|').split('|')
        body_rows.append('<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in cols) + '</tr>')
    body_html = '<tbody>' + ''.join(body_rows) + '</tbody>'
    return f'<table class="report-table">{header_html}{body_html}</table>'
```

### 标题转换

```python
html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
```

### 其他格式

```python
html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)  # 粗体
html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)             # 斜体
html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)      # 分割线

# 列表（需要跨行处理）
lines = html.split('\n')
result = []
in_list = False
for line in lines:
    if re.match(r'^[-*] (.+)', line):
        if not in_list:
            result.append('<ul>')
            in_list = True
        result.append(f'<li>{line[2:].strip()}</li>')
    else:
        if in_list:
            result.append('</ul>')
            in_list = False
        result.append(line)
if in_list:
    result.append('</ul>')
html = '\n'.join(result)
```

---

## HTML 页面结构模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{公司名} ({股票代码}) 投研报告 {日期}</title>
<style>
/* 全部CSS见上方核心规范 */
</style>
</head>
<body>

<header>
    <div class="top-bar">
        <div>
            <h1>{公司名} ({股票代码}) 投研报告</h1>
            <div class="subtitle">多Agent协同研究 | {行业/板块}</div>
        </div>
        <div class="date">{日期}</div>
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
        <!-- ... 其他nav-item -->
    </nav>

    <div class="main">
        <!-- 综合报告 -->
        <div id="summary" class="section active">
            <h1>{公司名} 综合投研报告</h1>
            {kpi_html}
            <div class="summary-box">
                <strong>投资评级：推荐买入</strong> | 目标价 {HKD} | 潜在涨幅 {+%} | 风险等级：{低/中/高}
            </div>
            {html_parts.get('00_综合报告', '')}
        </div>

        <!-- 其他板块... -->

        <div class="footer">
            本报告由AI多Agent系统自动生成 | 数据来源：iFind | 仅供参考，不构成投资建议
        </div>
    </div>
</div>

<button class="print-btn" onclick="window.print()">导出PDF</button>

<script>
// section切换 + 搜索功能
</script>
</body>
</html>
```

---

## KPI 网格数据模板

```python
kpi_html = """
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">投资评级</div>
        <div class="kpi-value" style="color:#00C853">推荐买入</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">目标价 (HKD)</div>
        <div class="kpi-value">XX</div>
    </div>
    <!-- ... 其他 KPI cards ... -->
</div>
"""
```

---

## 构建脚本标准框架

```python
#!/usr/bin/env python3
"""生成{公司名}投研HTML报告"""

import os
import re

def read_report(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return f"报告文件不存在: {path}"

def md_to_html(md_content):
    """Markdown → HTML 转换（已修复表格正则）"""
    html = md_content
    # 标题
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    # 表格（✅ 正确写法）
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
    # ⚠️ 关键：使用 [^\n|]+ 而非 .+，避免贪婪导致多行数据丢失
    html = re.sub(r'(\|.+\|\n\|[-| :]+\|(?:\n\|[^\n|]+\|)+)', convert_table, html, flags=re.M)
    # 粗体/斜体/分割线/列表...
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)
    # 列表处理...
    return html

# ========== 报告文件映射 ==========
base = '/Users/zhuang225/0.Agent 投研总监/reports/{公司名}_{日期}'
reports = {
    '00_综合报告': f'{base}/00_综合报告.md',
    '01_宏观环境': f'{base}/01_宏观环境.md',
    # ...
}

# 转换所有报告
html_parts = {}
for name, path in reports.items():
    content = read_report(path)
    html_parts[name] = md_to_html(content)

# KPI + HTML 组装...
output_path = f'{base}/index.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f'✅ HTML报告已生成: {output_path}')
```

---

## 已知 Bug 与修复记录

### Bug 1：表格正则贪婪匹配（2026-04-09 修复）

**症状**：每张 Markdown 表格只有第一行数据被转换为 `<tr>`，其余行以原始文本形式外露在 `<table>` 标签之外。

**根因**：正则 `r'(\|.+\|\n\|[-| :]+\|\n.+)+'` 中 `.+` 贪婪匹配且 `(.+)+` 只捕获最后一个重复组，无法正确处理多行数据行。

**修复**：改用 `r'(\|.+\|\n\|[-| :]+\|(?:\n\|[^\n|]+\|)+)'`，`[^\n|]+` 逐行匹配非贪婪。

**修复后遗留问题处理**：若已有生成错误的 HTML 文件，用以下脚本修复：
```python
import re
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 将 </table> 后游离的 <tbody>... 合并回前一张表
def fix_orphaned_tbody(html):
    pattern = r'(<table[^>]*>)(.*?)(</table>)\s*<tbody>(.*?)</tbody>'
    def replace_table(m):
        table_open, table_inner, table_close, orphaned_rows = m.group(1), m.group(2), m.group(3), m.group(4)
        existing_tbody = re.search(r'<tbody>.*?</tbody>', table_inner, re.DOTALL)
        if existing_tbody:
            existing_trs = re.findall(r'<tr>.*?</tr>', existing_tbody.group(0), re.DOTALL)
            orphaned_trs = re.findall(r'<tr>.*?</tr>', orphaned_rows, re.DOTALL)
            all_rows = ''.join(existing_trs + orphaned_trs)
            table_inner = table_inner.replace(existing_tbody.group(0), f'<tbody>{all_rows}</tbody>')
        else:
            table_inner += f'<tbody>{orphaned_rows}</tbody>'
        return f'{table_open}{table_inner}{table_close}'
    return re.sub(pattern, replace_table, html, flags=re.DOTALL)

html = fix_orphaned_tbody(html)
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)
```

### Bug 2：CSS 颜色双 `#` 符号

**症状**：`.summary-box { background:linear-gradient(135deg,#e8eaf6,##c5cae9); }` — `##` 导致渐变失效。

**修复**：`##c5cae9` → `#c5cae9`（去除多余 `#`）。

### Bug 3：KPI 标签文字挤压

**症状**：140px minmax + 11px 标签字体，导致"营收增速"(4字)、"净利润(亿元)"(6字) 等长标签换行或挤压。

**修复**：minmax 140px→155px，font-size 11px→12px，padding 调整为 `14px 10px`。

---

## 输出文件规范

| 文件 | 路径 | 说明 |
|------|------|------|
| HTML 报告 | `reports/{公司名}_{日期}/index.html` | 最终交付物 |
| 构建脚本 | `reports/build_{公司名}_html.py` | 可复用脚本 |

---

## 触发关键词

- "生成HTML报告"
- "构建投研报告"
- "合成报告为HTML"
- "生成index.html"
- "修复报告HTML"
- "帮我把markdown报告合成html"

*版本：v1.0 | 2026-04-09*
*经验积累：敏实集团(0425.HK)报告构建*
