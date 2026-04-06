---
name: RL-system-entry-automation
description: 将 ESG / Industry / Porter / QL&RF 四个 TXT 分析报告自动填入打分模板 Excel 的自动化脚本。覆盖分数提取、评论文字写入、精度规则、绿色格子处理。
metadata:
  version: "1.1"
  last_updated: "2026-04-01"
  notes: 参考文件仅在 skill 建立初期用于验证逻辑，后续运行不依赖任何参考文件。
---

# 系统录入自动化 Skill

将四个 TXT 源文件中的分数、数值、评论文字填入打分模板 Excel（`打分—新V 2.1.3.xlsx`），输出为 `打分—新V 2.1.3_自动填充.xlsx`。

---

## 一、文件对应关系

| TXT 文件 | 内容类型 | 主要用途 |
|---------|---------|---------|
| `ESG - YYYYMMDDHHMMSS.txt` | ESG E/S/G 三个维度评分 + 基础数据 | 填入 I/J 列（Exposure/Management 分数） |
| `Industry - YYYYMMDDHHMMSS.txt` | 4 个子行业分析 | 填入 I 列（Cycle/Growth/Scalable/Transparency/Market Size 等） |
| `Portet Model - YYYYMMDDHHMMSS.txt` | Porter 五力分析 | 填入 I 列（Competition/Supplier/Customer/Entry Barrier/Substitution） |
| `QL&RF - YYYYMMDDHHMMSS.txt` | 财务数据 + 风险穿透文字 | 填入 I/L 列（数值+评论） |

**基础路径**: `/Users/zhuang225/Research/自动化 测试/`

---

## 二、ESG.txt 解析规则

### 2.1 基础数据（行2-6）
用正则直接搜索标签，提取数值：

```
碳排放 Scope 1+2: 搜索 "**Carbon Emission(GHG) Scope 1+2**"，到"吨"之前取数字
碳排放 Scope 1+2+3: 同上，取"12,566.92"
用电量: 兆瓦 → 取 "1,983.6"
用水量: 立方 → 取 "353,100"
Female on board: 百分比数值 → 0.375（37.5% ÷ 100）
```

**注意**：在单位关键词（吨/兆瓦/立方）之后截取，避免年份"2022"被误匹配。

### 2.2 E/G 维度评分
格式：`**标题（中英）**` 后跟 `**Exposure分数**：**X**分` 和 `**Management分数**：**X**分`

```python
# E 维度 headings
E_HEADINGS = {
    'Climate Change':         '**1.1 Climate Change 气候变化**',
    'Natural Resources':      '**1.2 Natural Resources 自然资源**',
    'Pollution & Waste':    '**1.3 Pollution & Waste 污染与废物**',
    'Environmental Opportunities': '**1.4 Environmental Opportunities 环境机遇**',
}
# G 维度 headings（3.1 ~ 3.21，同理）

# 解析：全文搜索标题→取后800字符→找下一个标题之前→提取Exposure/Management
exp_m = re.search(r'\*\*Exposure[分数]*\*\*[^\d]*(\d+(?:\.\d+)?)', block)
mgt_m = re.search(r'\*\*Management[分数]*\*\*[^\d]*(\d+(?:\.\d+)?)', block)
```

### 2.3 S 维度评分（特殊格式）
S 维度的 Exposure 和 Management 分数**内嵌在标题行末尾**，格式为：
`**2.1 Human Capital 人力资本 【Exposure: 3, Management: 3】`

```python
# 云南锗业 (002428) S维度评分解析
em_m = re.search(r'【Exposure:\s*(\d+(?:\.\d+)?),\s*Management:\s*(\d+(?:\.\d+)?)】', heading_line)
```

---

## 三、Industry.txt 解析规则

### 3.1 四个行业 Block 边界
使用 `blk(text, start, ends)` 函数，搜索 `\n+end_kw` 防止 `## 1.1` 被误匹配：

```python
b1 = blk(ind, '# 云南锗业 锗材料产品行业分析报告', ['# 云南锗业太阳能锗单晶片'])
b2 = blk(ind, '# 云南锗业太阳能锗单晶片(4英寸)行业分析报告', ['# 云南锗业及光纤用四氯化锗行业分析报告'])
b3 = blk(ind, '# 云南锗业及光纤用四氯化锗行业分析报告', ['# 云南锗业红外系锗产品行业分析报告'])
b4 = blk(ind, '# 云南锗业红外系锗产品行业分析报告', [])
```

### 3.2 每个 Block 提取的指标
使用 `sval(block, keyword)` 提取：

| 指标 | keyword | 说明 |
|-----|---------|------|
| Cycle Score | `Cycle Score` | 直接取整数值 |
| Growth Score | `Growth Score` | 2.3, 2.2 等 |
| Scalable Score | `Expansion Score` | 2.7, 1.7 等 |
| Transparency Score | `Transparency Score` | 1.5 |
| Market Size | `约**X**亿` → 正则 `约[^\d亿]*(\d+(?:\.\d+)?)[^\d亿]*亿` | 原始亿，乘以100填入（15亿→1500） |
| Growth 3Y CAGR | `icagr(b)` → "未来 3 年预期增速.*?(\d+(?:\.\d+)?)\s*%" | 除以100保留4位小数 |
| Growth -2Y CAGR | `FY-2 ~ FY0.*?(\d+(?:\.\d+)?)\s*%` | **保留3位小数**（round(x/100, 3)） |
| Penetration | `渗透率.*?(\d+(?:\.\d+)?)\s*%` | 除以100 |

**Ind5（不存在于 TXT，跳过）**

---

## 四、Porter.txt 解析规则

### 4.1 四个行业 Block 边界
```python
bp1 = blk(port, '锗材料产品 竞争力分析报告', ['云南锗业太阳能锗单晶片', '$$'])
bp2 = blk(port, '太阳能锗单晶片(4英寸)', ['云南锗业光纤用四氯化锗', '$$'])
bp3 = blk(port, '云南锗业光纤用四氯化锗 竞争力分析报告', ['云南锗业红外系锗产品', '$$'])
bp4 = blk(port, '云南锗业红外系锗产品 竞争力分析报告', ['$$'])
```

### 4.2 提取指标
格式：`**Competition**：[4]` → 用正则 `\*\*{kw}\*.*?\[(\d+(?:\.\d+)?)\]`

| 指标 | keyword |
|-----|---------|
| Competition | `Competition` |
| Supplier | `Supplier` |
| Customer | `Customer` |
| Entry Barrier | `Entry Barrier` |
| Substitution | `Substitution` |

---

## 五、QL&RF.txt 解析规则

### 5.1 Visibility（增长能见度）
格式：`**评分：2/5分**`（不是"增长能见度评分.X分"）
```python
re.search(r'\*\*评分\*\*[^\d]*(\d+)/5分', ql)
```

### 5.2 Margin（毛利率）
```python
margin_self: 云南锗业.*?(\d+(?:\.\d+)?)\s*%   → round(x/100, 2)
margin_p1:   驰宏锌锗表格行，用 lookahead (?=\s*\|) 锚定表格行
margin_p2:   中金岭南表格行
margin_p3:   罗平锌电表格行
```
**注意**：同行毛利率在 markdown 表格里（`| 驰宏锌锗 | 23.07 | ...`），数值后**没有%**，需要用 `(?=\s*\|)` 锚定到表格行再提取。

### 5.3 Marketing Ratio（销售费用率）
```python
re.search(r'销售费用率[^\d]*?(\d+(?:\.\d+)?)\s*%', ql)  → round(x/100, 2)
```

### 5.4 R&D
```python
rd_personnel: 研发人员[^\d]*?(\d+)\s*人  # 文本含"数量为"，不能用"为?"

rd_personnel_ratio:
  # 从"占员工总数（1,157人）"提取总数
  re.search(r'占员工总数[^\d]*?(\d+)', ql)
  → round(rd_personnel / total, 2)

rd_ratio: 研发费用率[^\d]*?(\d+(?:\.\d+)?)\s*%  → round(x/100, 4)
patents:   专利[^\d]*?(\d+)\s*余项
```

### 5.5 Turnover / Leverage（自身）
```python
turnover_self: 存货周转率[^\d]*?(\d+(?:\.\d+)?)
leverage_self: 资产负债率[^\d]*?(\d+(?:\.\d+)?)\s*%  → round(x/100, 4)
```
**同行 peer（turnover_p1-p3, leverage_p1-p3）：从 TXT 表格解析困难，跳过填写。**

---

## 六、写入规则

### 6.1 绿色格子（theme:6）强制写3
写入前检查每个格子的填充色是否为 `theme:6`（绿色），若是则强制写入 3.0。

```python
def is_green(cell):
    fill = cell.fill
    if fill and fill.fgColor:
        fg = fill.fgColor
        if fg.type == 'theme' and fg.theme == 6:
            return True
    return False

write_i = 3.0 if is_green(c9) else iv
write_j = 3.0 if is_green(c10) else jv
```

### 6.2 跳过行（不填）
行 143（Turnover vs. peers）、行 154（Leverage vs. peers）来自 peer 比较，TXT 中无法自动提取，跳过填写（留空）。

### 6.3 精度规则

| 指标 | 精度 |
|-----|------|
| Growth (-2Y CAGR) | 3位小数（例：0.071） |
| Growth (3Y CAGR) | 4位小数 |
| Marketing ratio | 2位小数（例：0.03 而非 0.0293） |
| Leverage self | 4位小数 |
| Market Size | 整数或最近似（Ind3: 460 而非 459.99） |

### 6.4 L列评论文字（行1-251）

**ql_comment_map 已生效**：脚本运行时自动将匹配到的评论文字写入 L 列，无需额外操作。

**匹配逻辑**：`get_ql_comment(en_label)` 将 Excel E列中文 label 与 `ql_comment_map` 中文 key 做模糊匹配（去空格/下划线/换行后包含关系），匹配成功即将对应评论写入 L 列（column 12）。未匹配到则留空。

**ql_i_map**：以下行同步写入 I 列数值（直接从 ql_comment_map 的数值型条目写入）：

| 行 | 项目 | I值 | 说明 |
|----|------|-----|------|
| 177 | 美国（北美）业务占比 | 0.1699 | 16.99% |
| 178 | 成本自主可控占比 | 100 | 100% |
| 179 | 进口原材料占比 | 0 | ~0% |
| 182 | 原材料价格变化YTD % | 0.105 | 10.5% |
| 191 | 运输仓储费用占毛利% | 0.0865 | 8.65% |
| 192 | 减：软件销售增值税退税 | 374 | 万元 |
| 193 | 政府补贴 | 1868 | 万元 |
| 195 | 最近5年更换董秘次数 | 0 | |
| 212 | FX Gain/Loss | -9.6 | 万元 |
| 237 | 汇兑损益占NI比例 | -9.6 | 万元 |
| 238 | 关联销售 | 1157 | 万元 |
| 239 | 关联采购 | 384 | 万元 |

---

## 七、blk() 函数说明（通用工具）

```python
def blk(text, start, ends):
    """从 start 截取到最近的 end_kw 之前（用 \\n+ek 防止被 ## 行内 # 误匹配）"""
    s = text.find(start)
    if s == -1: return None
    e = len(text)
    for ek in ends:
        x = text.find('\n' + ek, s + len(start))
        if x != -1: e = min(e, x)
    return text[s:e]
```

**关键**：`ends` 中的关键词前面**必须加 `\n`**，因为 `## 1.1` 这样的行也会匹配到 `#`，加了 `\n` 就可以精确找到行首的 `#`。

---

## 八、主脚本调用

```bash
cd "/Users/zhuang225/Research/自动化 测试"
python3 auto_fill_score.py
```

输出：`打分—新V 2.1.3_自动填充.xlsx`
