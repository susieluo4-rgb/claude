---
name: RL-系统录入自动化 v1.7
description: 将 ESG / Industry / Porter / QL&RF 四个 TXT 分析报告自动填入打分模板 Excel 的自动化脚本。支持多格式自动识别、通用行业Block解析、QL表格智能解析。最多支持5个行业。
metadata:
  version: "1.7"
  last_updated: "2026-04-08"
  notes: |
    v1.7: S维度正则支持"X分，Management"格式（寒武纪等）；
    icagr正则支持"未来3年"无空格格式；
    QL section headers覆盖更多变体（供应链风险/公司治理与财务运作/并购与商誉等）；
    find_row优先精确匹配。
    v1.6: find_row精确优先 + QL双格式支持。
    v1.5: 通用化改造——QL表格直接提取。
---

# 系统录入自动化 Skill v1.5

将四个 TXT 源文件中的分数、数值、评论文字填入打分模板 Excel（`打分—新V 2.1.3.xlsx`），输出为 `打分—新V 2.1.3_自动填充.xlsx`。

---

## ⚠️ 核心原则：先诊断，再修改

**每次运行新公司前，必须先检查文件格式。** 不同公司的 TXT 文件格式差异很大，主要体现在：

| 文件 | 常见差异 |
|------|---------|
| Industry | 子行业标题格式（`#` vs `##`）、行业数量（2-5个） |
| Porter | 标题关键字、评分格式 |
| QL&RF | Section格式（`### 一、` vs `#### 第一部分：`）、是否含表格、风险点名称 |

**调试步骤**：
```bash
# 1. 先看文件结构（关键标题行）
head -5 "$BASE/ESG"
grep -n "^#\|^\*\*\|渗透率\|Cycle Score\|Growth Score" "$BASE/Industry" | head -20
grep -n "^\*\*[^*]" "$BASE/Portet Model" | head -10
grep -n "###\|风险点\|^\|" "$BASE/QL&RF" | head -20

# 2. 检查TXT文件中是否有残留旧公司数据（如"云南锗业"、"002428"）
grep -c "云南锗业\|002428" "$BASE/ESG" "$BASE/Industry" "$BASE/Portet Model" "$BASE/QL&RF"
```

---

## 一、文件对应关系

| TXT 文件 | 内容类型 | 主要用途 |
|---------|---------|---------|
| `ESG` | ESG E/S/G 三个维度评分 + 基础数据 | 填入 I/J 列（Exposure/Management 分数） |
| `Industry` | 2-5 个子行业分析 | 填入 I 列（Cycle/Growth/Scalable/Transparency/Market Size 等） |
| `Portet Model` | Porter 五力分析 | 填入 I 列（Competition/Supplier/Customer/Entry Barrier/Substitution） |
| `QL&RF` | 财务数据 + 风险穿透文字 | 填入 I/L 列（数值+评论） |

**基础路径**: `/Users/zhuang225/Research/自动化 测试/`

**TXT 文件查找**：脚本按环境变量 `SCORE_ESG`/`SCORE_IND`/`SCORE_PORT`/`SCORE_QL` 查找，如未设置则默认从基础路径加载。实际文件名可能不带 `.txt` 后缀（如 `ESG`、`Industry`），脚本直接按文件名打开。

---

## 二、ESG.txt 解析规则

ESG.txt 格式相对稳定，核心格式为：

- **E/G 维度**：`**标题（中英）**` → `**Exposure分数**：**X**分` + `**Management分数**：**X**分`
- **S 维度（部分公司）**：分数内嵌在标题行末尾 `【Exposure: X, Management: Y】`

### 2.1 基础数据（行2-6）

```python
# 标签 → 单位关键词 → 取数字（避免年份被误匹配）
for lbl, unit in [
    ('**Carbon Emission(GHG) Scope 1+2**', '吨'),
    ('**Carbon Emission(GHG) Scope 1+2+3**', '吨'),
    ('**Electricity Consumption**', '兆瓦'),
    ('**Water Consumption**', '立方'),
]:
    m = re.search(rf'{re.escape(lbl)}[^\n]*', esg)
```

### 2.2 E/G 维度评分

```python
E_HEADINGS = {
    'Climate Change': '**1.1 Climate Change 气候变化**',
    'Natural Resources': '**1.2 Natural Resources 自然资源**',
    # ...
}
exp_m = re.search(r'\*\*Exposure[分数]*\*\*[^\d]*(\d+(?:\.\d+)?)', block)
mgt_m = re.search(r'\*\*Management[分数]*\*\*[^\d]*(\d+(?:\.\d+)?)', block)
```

### 2.3 S 维度评分（含内嵌格式）

两种格式共存：
```python
# 格式A（宁德时代等）：`**2.1 Human Capital 人力资本 【Exposure: 3, Management: 3】`
em_m = re.search(r'【Exposure:\s*(\d+(?:\.\d+)?),\s*Management:\s*(\d+(?:\.\d+)?)】', heading_line)

# 格式B（寒武纪等）：`**2.1 Human Capital 人力资本 【Exposure: 4分， Management: 4分】`
# 注意：数字后可能有"分"字，逗号为全角"，"
em_m = re.search(r'【Exposure:\s*(\d+)分?[，,]\s*Management:\s*(\d+)分?】', heading_line)
```

---

## 三、Industry.txt 解析规则

### ⚠️ 第一步：诊断文件格式

```bash
# 查看所有标题行，确定：
# 1. 行业数量（几个 # 开头的主要标题）
# 2. 子行业标题格式（是 # 还是 ##）
# 3. 行业数量
grep -n "^#" Industry | head -10
```

**常见两种格式：**

**格式A（云南锗业）**：子行业用一级 `#` 标题
```
# 云南锗业 锗材料产品行业分析报告
# 云南锗业太阳能锗单晶片(4英寸)
# 云南锗业及光纤用四氯化锗行业分析报告
...
```

**格式B（宁德时代）**：单一行业用 `##` 子章节
```
# 宁德时代动力电池行业分析报告
## **1.1 市场规模**
## **1.3 行业周期阶段与评分 Cycle Score: 2.5**
# 宁德时代储能电池行业分析报告
## **1.1 市场规模**
...
```

### 3.1 行业 Block 定义

根据诊断结果，修改 `INDUSTRY_HEADERS` 列表。**每个条目 = (起始标题, [结束标题列表])**，用 `$$` 表示文件末尾：

```python
# 格式A（云南锗业，4个行业）
INDUSTRY_HEADERS = [
    ('# 云南锗业 锗材料产品行业分析报告',  ['# 云南锗业太阳能锗单晶片']),
    ('# 云南锗业太阳能锗单晶片(4英寸)',   ['# 云南锗业及光纤用四氯化锗行业分析报告']),
    ('# 云南锗业及光纤用四氯化锗行业分析报告', ['# 云南锗业红外系锗产品行业分析报告']),
    ('# 云南锗业红外系锗产品行业分析报告',  ['$$']),
    ('# 第5个行业（如有）',               ['$$']),
]

# 格式B（宁德时代，2个行业）
INDUSTRY_HEADERS = [
    ('# 宁德时代动力电池行业分析报告',    ['# 宁德时代储能电池行业分析报告']),
    ('# 宁德时代储能电池行业分析报告',    ['$$']),
    ('# 第3个行业（如有）',               ['$$']),
    ('# 第4个行业（如有）',               ['$$']),
    ('# 第5个行业（如有）',               ['$$']),
]
```

**关键**：`blk(text, start, ends)` 的 `ends` 中每个关键词前**必须加 `\n`**，防止 `## 1.1` 被 `# 1.1` 误匹配。

### 3.2 每个 Block 提取的指标

```python
ind_metric_kw = {
    'cycle':        'Cycle Score',
    'growth':       'Growth Score',
    'scalable':     'Expansion Score',
    'transparency': 'Transparency Score',
    'penetration':  '渗透率',       # ⚠️ 必须加入，否则L列缺失
}

# icagr：支持"未来 3 年"和"未来3年"两种格式（空格可变）
def icagr(b, pat=r'未来\s*3\s*年预期增速'):
    m = re.search(pat + r'.*?(\d+(?:\.\d+)?)\s*%', b)
    return round(float(m.group(1))/100, 4) if m else None

# Market Size：处理中文逗号分隔的数字
m = re.search(r'约[^\d亿]*(\d+(?:[，,]\d+)*(?:\.\d+)?)[^\d亿]*亿', b)
if m:
    num = float(m.group(1).replace('，', '').replace(',', ''))
    ind_vals[(ind_idx, 'mkt_size')] = round(num * 100)
```

### 3.3 parse_industry_row_label() 必须包含 penetration

```python
def parse_industry_row_label(en_str):
    # ... cycl/growth/scalable/transparency/competition/supplier/customer/entry/substitution 分支 ...
    if 'penetration' in s:         # ⚠️ 必须有此分支
        return (ind_idx, 'penetration')
    return None
```

---

## 四、Porter.txt 解析规则

### 4.1 诊断格式

```bash
grep -n "^\*\*[^*]" Portet\ Model | head -15
```

### 4.2 Porter Block 定义

**与 Industry.txt 的行业顺序一一对应**，修改 `PORTER_HEADERS` 匹配公司实际标题：

```python
# 宁德时代（2个行业）
PORTER_HEADERS = [
    ('**宁德时代动力电池 竞争力分析报告**', ['### **宁德时代储能电池 竞争力分析报告**', '$$']),
    ('### **宁德时代储能电池 竞争力分析报告**', ['$$']),
    ('第3个行业竞争力分析报告（如有）',   ['$$']),
    ('第4个行业竞争力分析报告（如有）',   ['$$']),
    ('第5个行业竞争力分析报告（如有）',   ['$$']),
]
```

### 4.3 提取指标

```python
def pscore(b, kw):
    # 格式：**Competition**：[4.5]
    m = re.search(rf'\*{re.escape(kw)}\*.*?\[(\d+(?:\.\d+)?)\]', b, re.DOTALL)
    return float(m.group(1)) if m else None
```

---

## 五、QL&RF.txt 解析规则

### ⚠️ 最重要：先诊断 QL 文件结构

```bash
# 查看Section格式（判断是 ### 一、 还是 #### 第一部分：）
grep -n "###" QL\&RF | head -15

# 查看是否含风险表格
grep -n "风险点" QL\&RF | head -5
```

**两种常见格式：**

**格式A（云南锗业）**：`### **一、分析内容**` 结构
```
### **一、增长能见度**
**分析：** 文字内容...
```

**格式B（宁德时代）**：`#### **第一部分：**` + Markdown 表格
```
#### **第一部分：地缘政治与供应链风险**
| 风险点 | 描述性文字 | 数据/分析 |
| **美国（北美）业务占比** | 直接收入占比较低... | **估算 <5%** ... |
```

### 5.1 推荐：直接从表格提取（格式B最优方案）

宁德时代验证过的方案，从风险表格直接解析：

```python
def parse_ql_table_block(ql, section_start_kw, section_end_kw='### **核心风险摘要'):
    s = ql.find(section_start_kw)
    if s == -1: return None
    e = ql.find(section_end_kw, s)
    if e == -1: e = len(ql)
    return ql[s:e]

def extract_ql_table_rows(block):
    """提取 markdown 表格行：[(风险点, 描述文字, 数据文字)]"""
    if not block: return []
    rows = []
    for line in block.split('\n'):
        # | **风险点** | 描述 | 数据 |
        m = re.match(r'\|\s*\*{0,2}([^*]+?)\*{0,2}\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|', line)
        if m:
            risk_name = m.group(1).strip()
            desc = m.group(2).strip()
            data = m.group(3).strip()
            if risk_name and risk_name != '风险点':
                rows.append((risk_name, desc, data))
    return rows

# 解析四个风险section
ql_table_data = {}
section_headers = [
    # 格式A（冒号后有空格，全角句号）：#### **第一部分：xxx**
    '#### **第一部分：地缘政治与供应链风险**',
    '#### **第二部分：财务与政策依赖风险**',
    '#### **第三部分：外汇与货币风险**',
    '#### **第四部分：资本运作与公司治理风险**',
    # 格式B（顿号，无空格）：#### **一、xxx**
    '#### **一、 地缘政治与供应链安全风险**',
    '#### **一、 地缘政治与供应链风险**',
    '#### **二、 运营与财务风险**',
    '#### **二、 公司治理与财务运作风险**',
    '#### **三、 汇率与融资风险**',
    '#### **四、 公司治理与资本运作风险**',
    '#### **四、 并购与商誉风险**',
]
for hdr in section_headers:
    block = parse_ql_table_block(ql, hdr)
    for risk_name, desc, data in extract_ql_table_rows(block):
        ql_table_data[risk_name] = (desc, data)

# 动态生成评论映射（不再需要硬编码）
ql_en_comment_map = {k: f"{v[0]} {v[1]}" for k, v in ql_table_data.items()}
ql_comment_map = ql_en_comment_map  # get_ql_comment() 回退时使用
```

### 5.2 find_row() 精确优先原则

```python
def find_row(*keywords):
    """优先精确匹配（含#前缀），再回退到模糊匹配"""
    kw_raw = [k.strip() for k in keywords]
    kw_norm = [k.lower().replace(' ','').replace('#','') for k in keywords]

    # 第一轮：精确匹配（含#的原始字符串）
    for en,row in en_to_row.items():
        if all(kw in en for kw in kw_raw): return row

    # 第二轮：标准化模糊匹配
    for en,row in en_to_row.items():
        en_n=en.lower().replace(' ','').replace('#','')
        if all(kw.lower().replace(' ','') in en_n for kw in keywords): return row
    return None
```

**作用**：避免 `# Tax transparancy.` 被 `tax transparancy` 匹配到 `Tax Transparency` 行（两行同时存在的模板）。

### 5.3 ql_i_map：必须根据公司更新

**ql_i_map 是公司专属数据，每次必须手动核对更新。**

宁德时代参考值（2023年年报）：

```python
ql_i_map = {
    '美国（北美）业务占比':          0.05,     # <5%
    '成本自主可控占比':             100,       # 100%
    '进口原材料占比':               0.80,      # 80%（锂钴镍依存度高）
    '主要原材料或大宗商品价格变化，YTD %': -0.80,  # 碳酸锂跌幅80%
    '运输仓储费用占毛利比例%':      0.147,     # 14.7%
    '减：软件销售增值税退税':       0,         # 不适用
    '政府补贴(公司/行业）':         178000,   # 17.8亿元=178000万
    '最近5年更换董秘次数':         0,
    'FX Gain/Loss \n（CNY/USD ／10%）年报中有披露': 238000,  # 23.8亿元
    'FX Gain/Loss \n（CNY/USD ／10%）or 汇兑损益\n占当年N': 238000,
    '关联销售(mn RMB)':            14800,     # 1.48亿元=14800万
    '关联采购':                    6700,      # 0.67亿元=6700万
}
```

**如何确定ql_i_map值**：从 QL&RF.txt 的数据列中提取，单位统一为**万元**（与 Excel I 列一致）。

---

## 六、写入规则

### 6.1 绿色格子（theme:6）强制写3

```python
def is_green(cell):
    fg = cell.fill.fgColor
    return fg.type == 'theme' and fg.theme == 6

write_i = 3.0 if is_green(c9) else iv
write_j = 3.0 if is_green(c10) else jv
```

### 6.2 跳过行（不填）

- 行 143（Turnover vs. peers）：同行比较，TXT 无法自动提取
- 行 154（Leverage vs. peers）：同行比较，TXT 无法自动提取

### 6.3 精度规则

| 指标 | 精度 | 示例 |
|-----|------|------|
| Growth (-2Y CAGR) | 3位小数 | `0.071` |
| Growth (3Y CAGR) | 4位小数 | `0.2350` |
| Marketing ratio | 2位小数 | `0.03` |
| Leverage self | 4位小数 | `0.5501` |
| Market Size | 整数（×100） | `274600`（2746亿×100） |
| 渗透率 | 2位小数 | `0.38`（38%除100） |

### 6.4 L列评论文字写入

**行业评分行（行71-130）**：

```python
ind_metric_kw = {
    'cycle', 'growth', 'scalable', 'transparency', 'penetration'  # ← 必须包含penetration
}
ind_comments = {}
for ind_idx, block in ind_blocks.items():
    for metric, kw in ind_metric_kw.items():
        cmt = ind_metric_comment(block, kw)
        if cmt: ind_comments[(ind_idx, metric)] = cmt
```

**行177-251**：通过 `get_ql_comment()` 模糊匹配 `ql_comment_map`，将 QL 风险数据写入。未匹配到则留空。

**行66 ticker**：根据当前公司填写，如 `300750.SZ`。

---

## 七、blk() 函数说明（通用工具）

```python
def blk(text, start, ends):
    """从 start 截取到最近的 end_kw 之前（用 \n+ek 防止 ## 行内 # 误匹配）"""
    s = text.find(start)
    if s == -1: return None
    e = len(text)
    for ek in ends:
        x = text.find('\n' + ek, s + len(start))  # ← \n 前缀防误匹配
        if x != -1: e = min(e, x)
    return text[s:e]
```

**常见错误**：
- ❌ `ends = ['云南锗业太阳能锗单晶片']` → 可能匹配行内文字
- ✅ `ends = ['\n云南锗业太阳能锗单晶片']` → 精确匹配行首

---

## 八、换公司检查清单

当切换到新公司时，按以下顺序检查并修改：

### Step 1: 诊断文件格式
```bash
# 统计关键信息
grep -c "^#" Industry           # 行业数量
grep -n "^\*\*[^*]" Portet\ Model | head -5  # Porter标题格式
grep -n "###" QL\&RF | head -10  # QL Section格式
```

### Step 2: 更新 INDUSTRY_HEADERS
- [ ] 根据实际行业数量修改条目（不足5个时填 `['$$']`）
- [ ] 修改起始/结束标题关键字匹配公司名称

### Step 3: 更新 PORTER_HEADERS
- [ ] 与 Industry 顺序一一对应
- [ ] 修改标题关键字

### Step 4: 更新 ql_i_map
- [ ] 从 QL&RF.txt 数据列提取新公司的数值
- [ ] 单位统一为**万元**

### Step 5: 更新 Ticker
- [ ] 行66：`fills[ticker_row] = ('300750.SZ', None)` 改为新公司代码

### Step 6: 验证
```bash
# 运行后扫描残留旧公司数据
python3 -c "
import openpyxl
wb = openpyxl.load_workbook('打分—新V 2.1.3_自动填充.xlsx')
for r in wb.active.iter_rows():
    for c in r:
        if c.value and isinstance(c.value, str) and ('云南' in c.value or '002428' in c.value):
            print(f'行{r.row} 列{c.column}: {c.value[:50]}')
"
```

---

## 九、常见问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| Industry/Porter 全为空 | `INDUSTRY_HEADERS` 标题不匹配 | 用 `grep "^#" Industry` 核对实际标题 |
| Market Size 解析为 `2` | 数字含中文逗号 `2，746` | 正则加 `replace('，', '')` |
| L列行73/74无评论 | `ind_metric_kw` 缺 `'penetration'` | 添加 `'penetration': '渗透率'` |
| L列177+全是旧公司数据 | `ql_section_block` 解析失败 + 硬编码 `ql_comment_map` | 改用 `parse_ql_table_block` 从表格提取 |
| 精度不对（如Market Size小数） | `round()` 精度问题 | Market Size 用 `round(num*100)` 不带小数 |

---

## 十、主脚本调用

```bash
cd "/Users/zhuang225/Research/自动化 测试"
SCORE_ESG="ESG" SCORE_IND="Industry" SCORE_PORT="Portet Model" SCORE_QL="QL&RF" python3 auto_fill_score.py
```

输出：`打分—新V 2.1.3_自动填充.xlsx`
