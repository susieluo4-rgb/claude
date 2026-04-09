---
name: RL-company-research-model-V2.3
description: 自动化A股/港股公司研究建模工具。当用户输入一个上市公司名称，自动完成：(1)扫描 Research 文件夹的财报/纪要等研究材料；(2)通过 iFind 获取历史财务数据与一致预期；(3)按照 CATL 模板格式建立完整财务模型（三张表+业务拆分+模型假设），预测至2030年；(4)添加季度三张表及未来4季度 I/S 预测；(5)基本面研究打分sheet（行业/竞争力/Momentum/财务质量）；(6)估值sheet（PE/PEGY）。当用户说"帮我研究[公司名] level 2"、"研究[公司] level 2"、"帮我建[公司名]的模型"、"对[公司]做基本面研究"、"给[公司]建财务模型"、"研究一下[股票代码/公司]"时必须触发此skill。"level 2"是此skill的专属触发关键词。
---

# 公司研究建模 Skill

用户输入一个上市公司名称后，按以下6个阶段自动完成完整的研究模型。每个阶段有明确的输入/输出，失败时有降级策略。

---

## 阶段零：初始化

### 0.1 解析公司信息
从用户输入中提取公司名称或股票代码。如果只有名称没有代码，先用 iFind 或 web search 确认股票代码（格式：XXXXXX.SH / .SZ / .HK）。

### 0.2 扫描 Research 文件夹
扫描 `/mnt/Research/`（或用户选定的工作文件夹）下与该公司相关的所有文件：
- 财报 PDF（年报、半年报、季报）
- 会议纪要（txt/docx）
- 研报（PDF/docx）
- 历史数据（csv/xlsx）

记录找到的文件列表，后续建模时优先使用这些材料中的数据。

### 0.3 确定输出文件名
输出文件命名规则：`{公司名称}_{股票代码}_研究模型_{YYYYMMDD}.xlsx`
保存至用户的工作文件夹。

---

## 阶段一：数据获取

### 1.1 iFind 数据获取（最高优先级）

参考 ifind-data skill 中的 API 规范，依次获取以下数据：

**历史财务数据（年报，近6年）：**
```python
# 利润表
indicators = "revenue,operprofit,netprofit,parentnetprofit,grossmargin,netmargin,opermargin,ebitda,eps_basic"

# 资产负债表
indicators = "totalassets,totalliabilities,equity,cashandequivalents,accountsreceivable,inventories,fixedassets,shortborrowings,longborrowings,parentequity"

# 现金流量表
indicators = "operatecashflow,investcashflow,financecashflow,freecashflow,capex"

# reporttype: "0"（年报）
```

**季度历史数据（近12个季度）：**
```python
# 同上 indicators，reporttype 使用 "" 或不传（返回所有期别），然后筛选季报数据
# 或者用 reporttype: "2"(Q1) "1"(H1) "3"(Q3) 分别获取
```

**一致预期（最高优先级用于预测部分）：**
```python
indicators = "west_revenue_FY1,west_revenue_FY2,west_revenue_FY3,west_netprofit_FY1,west_netprofit_FY2,west_netprofit_FY3,west_eps_FY1,west_eps_FY2,west_eps_FY3,west_grossmargin_FY1,west_grossmargin_FY2"
```

**估值数据：**
```python
indicators = "pe_ttm,pb_lf,ps_ttm,ev,ev2ebitda,west_avgprice,west_ratingvalue,west_buyrating,west_holdrating,west_sellrating"
```

**行业分类：**
```python
indicators = "industry_sw1,industry_sw2"  # 申万一级/二级行业
```

### 1.2 Research 文件夹补充
解析找到的财报和研报，提取：
- 业务分部收入（用于业务拆分）
- 分析师对未来的预测数字
- 业务描述（用于基本面打分）

### 1.3 Web Search 补充（最低优先级）
如果 iFind 和 Research 材料都无法覆盖某项关键数据（尤其是业务拆分的细分收入），用 WebSearch 补充。

### 1.4 数据整理原则
- **优先级**：iFind 一致预期 > Research 研报数字 > Web Search 推测
- 对于无法获取的数据，使用合理的行业平均或历史趋势插值
- 所有估计数据在 Excel 中用蓝色字体标注，注明来源

---

## 阶段二：年度财务模型（三张表 + 业务拆分）

参考 `references/excel_template_structure.md` 中的详细 Sheet 结构。

### 2.1 Sheet 结构（按顺序创建）

| Sheet名 | 说明 |
|---------|------|
| 摘要 | 公司概况 + 关键财务指标汇总 |
| 模型假设 | 所有可调参数（蓝色可改），驱动三张表 |
| 业务拆分 | 分部收入增速/毛利率假设 → 汇总至模型假设 |
| 利润表 | 历史6年 + 预测至2030E（7年预测） |
| 资产负债表 | 同上 |
| 现金流量表 | 同上 |

### 2.2 年份范围
- **历史数据**：最近6个完整财年（已披露）
- **预测数据**：2026E 至 2030E（5年预测）
- 第一个预测年 = 当前年份（若当年年报未披露则从上一年开始预测）

### 2.3 模型假设 Sheet 设计

模型假设 Sheet 是整个模型的控制中心，包含以下分区（参考 CATL 模板）：
- **A. 收入假设**：各年营收增长率（**由业务拆分 Sheet 汇总得出的公式引用，绿色**）
- **B. 盈利能力**：综合毛利率（**由业务拆分 Sheet 汇总得出的公式引用，绿色**）、三费费率、财务收入、税率、归母比例
- **C. 资本开支 & 折旧**：D&A、Capex
- **D. 营运资本**：应收账款/存货/应付账款周转天数
- **E. 资本结构**：股息率、净债务变动
- **F. DCF/估值参数**：WACC参数、股本、当前股价

**关键约束：营收增速和毛利率必须来自业务拆分，模型假设中这两项为绿色公式引用，不是蓝色手动输入。**

**颜色规范**（严格遵守）：
- 蓝色：可手动修改的假设输入（RGB: 0,0,255）
- 黑色：公式计算结果（RGB: 0,0,0）
- 绿色：跨 Sheet 引用（RGB: 0,128,0）

### 2.4 业务拆分 Sheet 设计（核心数据输入源）

业务拆分 Sheet 是模型的唯一营收数据输入源，各项假设（蓝色输入）→ 自动汇总→ 联动模型假设。

**Sheet 结构**：
```
行号  │ A(标签)  │ B(历史)  │ C(历史)  │ ... │ 预测年1 │ 预测年2 │ ...
─────┼──────────┼─────────┼─────────┼─────┼────────┼────────┼─────
     │ 分部1收入 │  数值   │  数值   │     │  蓝色  │  蓝色  │    ← 手动输入
     │ 分部1增速 │  计算值  │  计算值  │     │  蓝色  │  蓝色  │    ← 手动输入（增速）
     │ 分部1毛利率│  数值   │  数值   │     │  蓝色  │  蓝色  │    ← 手动输入
     │ 分部1毛利额│ =收入×毛利率│       │     │ =收入×毛利率│       │    ← 公式计算
─────┼──────────┼─────────┼─────────┼─────┼────────┼────────┼─────
     │ 分部2...  │         │         │     │        │        │
...
─────┼──────────┼─────────┼─────────┼─────┼────────┼────────┼─────
     │ **汇总：总收入**│ =SUM收入│        │     │ =SUM收入│        │    ← 公式汇总
     │ **汇总：总毛利**│ =SUM毛利│        │     │ =SUM毛利│        │    ← 公式汇总
     │ **综合毛利率** │ =总毛利/总收入│      │     │ =总毛利/总收入│   │    ← 公式（≠加权平均）
     │ **营收增速**   │ =(本期-上期)/上期│    │     │ =(本-上)/上 │    ← 公式
```

**综合毛利率计算逻辑**（必须严格遵守）：
1. 各分部毛利额 = 该分部收入 × 该分部毛利率（各自独立计算）
2. 总毛利额 = Σ 各分部毛利额（直接求和，非加权平均）
3. 总收入 = Σ 各分部收入
4. 综合毛利率 = 总毛利额 / 总收入

**模型假设中的联动**（绿色公式引用）：
- `模型假设!rev_growth` → `=业务拆分!综合营收增速`（跨Sheet引用，绿色）
- `模型假设!gross_margin` → `=业务拆分!综合毛利率`（跨Sheet引用，绿色）

如无法获取分部数据，则只做整体收入+毛利率假设，业务拆分 Sheet 的汇总行直接等于该分部数据。

### 2.5 三张表公式结构

三张表通过公式与模型假设联动：
- **利润表**：收入 = 上期 × (1 + 增长率)；毛利 = 收入 × 毛利率；各费用 = 收入 × 费率；净利润通过税率计算
- **资产负债表**：应收账款/存货/应付账款用周转天数公式；现金 = 现金流量表期末余额；股东权益滚动
- **现金流量表**：经营现金流 = 净利润 + D&A - 营运资本变动；Capex = 假设值；融资现金流 = 净债务变动 - 分红

---

## 阶段三：季度数据

参考 `references/quarterly_model.md`。

### 3.1 季度历史 Sheet（三张表）

创建以下三个 Sheet：
- 利润表_季度
- 资产负债表_季度（选做，若季报未全披露则仅做 IS）
- 现金流量表_季度（选做）

**历史范围**：过去12-16个季度（约3-4年）

**数据来源**：iFind financial_report + reporttype 按季度筛选

**Sheet 结构**：
- 列：Q1/Q2/Q3/Q4 按时间序列排列（格式：2023Q1, 2023Q2...）
- 行：与年度 IS 一致的科目（营收、毛利、各费用、净利润、EPS）
- 底部添加同比增速行（YoY）和环比增速行（QoQ）

### 3.2 未来4季度 I/S 预测

在利润表_季度 Sheet 的右侧，预测下一年的4个季度：

**季节性规律处理**：
- 计算每个季度占全年的历史比例（近2-3年平均）
- 季度预测 = 对应全年预测值 × 该季度历史占比

**与年度吻合**：
- 4个季度利润表数字加总 = 年度利润表中对应年份的数字
- 用公式链接确保：`SUM(Q1:Q4) = 年度_利润表!{对应年份}`

**季度预测范围**：仅预测 I/S（利润表）

---

## 阶段四：基本面研究打分

创建 Sheet 名：**基本面研究**

参考 `references/scoring_rubric.md` 中的详细评分标准。

### 4.1 Sheet 布局

```
【基本面研究 — {公司名称}】

A. 行业质量评分 (1-5分)          分值: X.X
B. 竞争力评分 (1-5分)            分值: X.X
C. Momentum评分 (1-5分)          分值: X.X
D. 财务质量评分 (1-5分)          分值: X.X

★ 综合质量得分                   X.X / 5.0
（权重：行业20% + 竞争力30% + Momentum25% + 财务25%）
```

### 4.2 A. 行业质量评分（1-5分）

评分维度：
| 维度 | 说明 | 数据来源 |
|------|------|----------|
| 行业规模 | TAM大小（万亿/千亿/百亿...） | web search/研报 |
| 行业增速 | 未来5年CAGR预测 | iFind行业/研报 |
| 延展性 | 是否有新市场/新应用场景 | 定性判断 |
| 行业透明度 | 竞争格局是否清晰 | 定性判断 |
| 政策支持度 | 政策顺风/逆风 | 定性判断 |

在 Sheet 中展示每个维度的评分(1-5)和依据说明，并给出加权平均分。

### 4.3 B. 竞争力评分（1-5分）

波特五力分析 + 护城河评估：

| 维度 | 评分要点 |
|------|---------|
| 供应商议价能力 | 原材料集中度 |
| 客户议价能力 | 客户集中度/粘性 |
| 替代品威胁 | 技术替代风险 |
| 新进入者威胁 | 进入壁垒高低 |
| 同业竞争强度 | 市场集中度 CR3/CR5 |
| 技术壁垒 | 专利数/研发投入占比 |
| 定价权 | 历史毛利率趋势 |
| 垄断/头部地位 | 市场份额 |

### 4.4 C. Momentum 评分（1-5分）

基于财务模型中的预测数据自动计算：

| 时间维度 | 指标 | 数据来源 |
|---------|------|---------|
| 未来4个季度 | 营收/归母净利 YoY增速 | 季度预测 Sheet |
| 未来1年 (FY1) | 营收/净利增速 | 年度预测 + iFind 一致预期 |
| 未来3年 CAGR | 营收/净利3年复合增速 | 年度预测 2026-2028 |
| 业绩预测修正 | 近1月上调/下调次数 | iFind west_netprofit_up1m/down1m |

评分规则：
- 5分：4季度/1年/3年均加速增长，分析师持续上调
- 4分：整体向上，个别季度有扰动
- 3分：稳健增长，无明显加速
- 2分：增速放缓或有较大不确定性
- 1分：负增长或严重下行风险

### 4.5 D. 财务质量评分（1-5分）

基于历史财务数据计算：

| 指标 | 评分逻辑 |
|------|---------|
| ROE | 近3年平均ROE >20%=5分, >15%=4分, >10%=3分 |
| 毛利率水平 | 与行业对比，趋势改善=加分 |
| 归母净利率 | 趋势与水平综合评估 |
| 经营现金流质量 | CFO/净利润 比率（应>1） |
| 资产负债率 | 负债率及变化趋势 |
| 自由现金流 | FCF/净利润，正值稳定=加分 |
| 应收账款天数趋势 | 缩短=加分 |

---

## 阶段五：估值

创建 Sheet 名：**估值分析**

### 5.1 PE 估值法

```
【PE 估值法】

                历史      FY1E     FY2E     FY3E
EPS (元)         X.XX     X.XX     X.XX     X.XX
PE倍数假设         --       XX.Xx    XX.Xx    XX.Xx
目标股价          --       XXX      XXX      XXX

当前股价:   XXX元
当前PE(TTM): XX.Xx
历史PE中枢:  XX.Xx (近3年)
PE区间:      XX-XXx (近3年)
```

PE倍数假设来源（优先级）：
1. iFind 一致预期目标价对应的隐含PE
2. 可比公司PE中位数（参考可比公司数据）
3. 历史PE中枢 ± 合理溢价/折价

### 5.2 PEGY 估值法

```
【PEGY 估值法 (Price/Earnings to Growth + Yield)】

FY1E EPS:         X.XX元
FY1E PE (当前):   XX.Xx
净利润增速 (FY1):  XX%
股息率 (TTM):      X.X%

PEG (PE/增速):     X.XX  （<1=低估，>2=高估）
PEGY (PE/(增速+股息率)):  X.XX

合理PEGY区间:  0.8-1.2x（参考可比公司）
PEGY隐含目标价:   XXX元
```

### 5.3 综合估值结论

```
【估值汇总】

                    目标价     当前股价   上行空间
PE法（1年）          XXX元      XXX元     +XX%
PEGY法               XXX元      XXX元     +XX%
分析师平均目标价      XXX元      XXX元     +XX%

评级参考：
  > +20% 强烈推荐
  10-20% 推荐
  -10%~10% 中性
  < -10% 谨慎
```

---

## 阶段六：最终收尾

### 6.1 摘要 Sheet 更新
将以下内容填入摘要 Sheet：
- 公司基本信息（股票代码、行业、股本、当前股价、市值）
- 关键财务指标历史+预测汇总表（营收、归母净利、毛利率、PE）
- 综合质量评分
- 估值结论

### 6.2 质量检查
- 用 `scripts/recalc.py` 重新计算所有公式
- 检查三张表是否有 #REF!, #DIV/0! 等错误
- 验证季度加总 = 年度数字
- 检查资产负债表是否平衡（资产 = 负债 + 权益）

### 6.3 保存并提供给用户
保存至用户工作文件夹，提供 computer:// 链接。

---

## 执行顺序 & TodoList

开始执行时，创建如下 TodoList：

1. 解析公司信息，确认股票代码
2. 扫描 Research 文件夹，列出相关文件
3. iFind 获取历史财务数据（年报 + 季报）
4. iFind 获取一致预期数据
5. iFind 获取估值/市场数据
6. 整理数据，确定业务分部
7. 创建 Excel 文件，搭建 Sheet 框架
8. 填入模型假设 Sheet
9. 填入业务拆分 Sheet
10. 填入年度三张表（历史 + 预测公式）
11. 填入季度三张表（历史）
12. 添加季度 I/S 预测
13. 创建基本面研究打分 Sheet
14. 创建估值分析 Sheet
15. 更新摘要 Sheet
16. 公式重算 & 质量检查
17. 保存并提交用户

---

## ⚠️ Excel 公式架构（核心约束，每次构建前必须重新阅读）

**这是本 skill 最容易犯错的地方。预测列写死数值 = 交出了死表，用户改一个假设全表不动，模型毫无价值。**

### 根本原则：预测列全部写公式字符串，严禁写 Python 计算结果

```python
# ❌ 绝对禁止 — Python 算完后写死数字（静态，改假设不更新）
ws_is.cell(row=4, column=9).value = 4798          # 2026E Revenue — 死数！

# ✅ 必须这样 — 写 Excel 公式字符串（改假设自动重算）
ws_is.cell(row=4, column=9).value = '=H4*(1+模型假设!$B$5)'
# 注：ASM_ROW['rev_growth']=5，所以引用$B$5；行号必须与 ASM_ROW 定义完全一致
# ⚠️ 写模型假设数据时，列号必须直接用 ASM_COL[yr]，禁止加偏移量（+1），否则数据与公式引用错位
```

---

### 代码架构要求：脚本开头必须集中定义行列常量

在构建脚本最顶部，用常量字典统一定义所有 Sheet 的行号和列号。**禁止在公式字符串里硬编码行号数字**，全部引用常量：

```python
from openpyxl.utils import get_column_letter as gcl

# ========== 行列位置常量（统一定义，后面所有公式都引用这里）==========

# 【业务拆分】Sheet 行号（每个分段占4行：收入/增速/毛利率/毛利额）
# 汇总区在所有分段之后
BS_SEG_ROWS = []   # 动态：[seg1_rev_row, seg1_gro_row, seg1_gm_row, seg1_gp_row, seg2_..., ...]
# 汇总行号（在所有分段行之后动态计算）
BS_ROW = {
    'total_rev': None,   # 汇总总收入（动态，取决于有多少个分段）
    'total_gp':  None,   # 汇总总毛利额（动态）
    'blended_gm':None,   # 综合毛利率 = total_gp / total_rev（动态）
    'rev_growth': None,  # 营收增速 = (本期-上期)/上期（动态）
}

# 【模型假设】Sheet 各假设行号（列 B=FY1E, C=FY2E, D=FY3E, E=FY4E, F=FY5E）
# ⚠️ 营收增速(row5)和毛利率(row7)是绿色跨Sheet引用，不是蓝色手动输入
ASM_ROW = {
    'rev_growth':   5,   # 营收增长率 ← 绿色，引用业务拆分!rev_growth
    'gross_margin': 7,   # 毛利率     ← 绿色，引用业务拆分!blended_gm
    'sell_rate':    8,   # 销售费用率（蓝色手动输入）
    'admin_rate':   9,   # 管理费用率（蓝色手动输入）
    'rd_rate':     10,   # 研发费用率（蓝色手动输入）
    'finance_cost':11,   # 净财务费用（蓝色手动输入）
    'tax_rate':    12,   # 有效税率（蓝色手动输入）
    'parent_ratio':13,   # 归母/合并比例（蓝色手动输入）
    'da':          15,   # D&A折旧摊销（蓝色手动输入）
    'capex':       16,   # Capex（蓝色手动输入，正值=流出金额）
    'ar_days':     18,   # 应收账款天数（蓝色手动输入）
    'inv_days':    19,   # 存货天数（蓝色手动输入）
    'ap_days':     20,   # 应付账款天数（蓝色手动输入）
    'div_payout':  22,   # 股息支付率（蓝色手动输入）
    'shares':      28,   # 总股本（蓝色手动输入）
}
# ⚠️ 模型假设行号说明（行3=年份标题行）：
#   Row4=▌A收入假设（分节标题），Row5=营收增长率（←绿色跨Sheet引用），
#   Row6=▌B盈利能力（分节标题），Row7=毛利率（←绿色跨Sheet引用），Row8-13=其他费用/税率
#   Row14=▌C Capex（分节标题），Row15=D&A，Row16=Capex，
#   Row17=▌D营运资本（分节标题），Row18-20=AR/INV/AP天数
#   Row21=▌E资本结构（分节标题），Row22=股息支付率
#   Row23=▌F估值参数（分节标题），Row24-28=无风险利率/Beta/MRP/WACC/总股本，Row29=股价

# 【利润表】行号
IS_ROW = {
    'revenue': 4, 'yoy': 5, 'cogs': 6, 'gp': 7, 'gm': 8,
    'selling': 10, 'admin': 11, 'rd': 12, 'rd_rate': 13, 'finance': 14,
    'op': 16, 'op_margin': 17, 'ebitda': 18, 'ebitda_margin': 19,
    'np': 21, 'np_attr': 22, 'np_attr_yoy': 23, 'np_margin': 24, 'eps': 25,
}

# 【资产负债表】行号
BS_ROW = {
    'cash': 5, 'ar': 6, 'inv': 7, 'other_ca': 8, 'ca': 9,
    'fa': 11, 'other_nca': 12, 'nca': 13, 'ta': 14,
    'std': 17, 'ap': 18, 'other_cl': 19, 'cl': 20,
    'ltd': 22, 'other_ncl': 23, 'ncl': 24, 'tl': 25,
    'parent_eq': 28, 'minority': 29, 'equity': 30,
    'bs_check': 31, 'leverage': 33, 'net_debt_eq': 34,
}

# 【现金流量表】行号
CF_ROW = {
    'oper': 4, 'capex': 5, 'fcf': 6,
    'invest': 8, 'finance_cf': 9,
    'net_chg': 11, 'beg_cash': 12, 'end_cash': 13,
}

# 年份 → 数据列号（1-based，openpyxl）
YEAR_COL = {
    '2019A': 2, '2020A': 3, '2021A': 4, '2022A': 5,
    '2023A': 6, '2024A': 7, '2025A': 8,
    '2026E': 9, '2027E': 10, '2028E': 11, '2029E': 12, '2030E': 13,
}

# 预测年份 → 模型假设列号（B=2, C=3, D=4, E=5, F=6）
ASM_COL = {'2026E': 2, '2027E': 3, '2028E': 4, '2029E': 5, '2030E': 6}

ALL_YEARS  = ['2019A','2020A','2021A','2022A','2023A','2024A','2025A',
              '2026E','2027E','2028E','2029E','2030E']
HIST_YEARS = [y for y in ALL_YEARS if y.endswith('A')]
PRED_YEARS = [y for y in ALL_YEARS if y.endswith('E')]

def dc(yr):   return gcl(YEAR_COL[yr])    # 数据列字母（IS/BS/CF用）
def ac(yr):   return gcl(ASM_COL[yr])     # 假设列字母（模型假设用）
def prev(yr): return ALL_YEARS[ALL_YEARS.index(yr) - 1]  # 上一年份
```

---

### 利润表预测列公式模板

```python
for yr in PRED_YEARS:
    col = YEAR_COL[yr]

    # 营收 = 上期营收 × (1 + 增长率)
    ws_is.cell(IS_ROW['revenue'], col).value = \
        f'={dc(prev(yr))}{IS_ROW["revenue"]}*(1+模型假设!${ac(yr)}${ASM_ROW["rev_growth"]})'

    # 毛利润 = 营收 × 毛利率
    ws_is.cell(IS_ROW['gp'], col).value = \
        f'={dc(yr)}{IS_ROW["revenue"]}*模型假设!${ac(yr)}${ASM_ROW["gross_margin"]}'

    # 营业成本 = -(营收 - 毛利润)
    ws_is.cell(IS_ROW['cogs'], col).value = \
        f'=-({dc(yr)}{IS_ROW["revenue"]}-{dc(yr)}{IS_ROW["gp"]})'

    # 各费用 = -营收 × 费率
    ws_is.cell(IS_ROW['selling'], col).value = \
        f'=-{dc(yr)}{IS_ROW["revenue"]}*模型假设!${ac(yr)}${ASM_ROW["sell_rate"]}'
    ws_is.cell(IS_ROW['admin'],   col).value = \
        f'=-{dc(yr)}{IS_ROW["revenue"]}*模型假设!${ac(yr)}${ASM_ROW["admin_rate"]}'
    ws_is.cell(IS_ROW['rd'],      col).value = \
        f'=-{dc(yr)}{IS_ROW["revenue"]}*模型假设!${ac(yr)}${ASM_ROW["rd_rate"]}'

    # 财务费用 = -净财务费用假设（绝对值）
    ws_is.cell(IS_ROW['finance'], col).value = \
        f'=-模型假设!${ac(yr)}${ASM_ROW["finance_cost"]}'

    # 营业利润 = 毛利润 + 各费用（各费用已含负号）
    ws_is.cell(IS_ROW['op'], col).value = (
        f'={dc(yr)}{IS_ROW["gp"]}'
        f'+{dc(yr)}{IS_ROW["selling"]}+{dc(yr)}{IS_ROW["admin"]}'
        f'+{dc(yr)}{IS_ROW["rd"]}+{dc(yr)}{IS_ROW["finance"]}'
    )
    # EBITDA = 营业利润 + D&A
    ws_is.cell(IS_ROW['ebitda'], col).value = \
        f'={dc(yr)}{IS_ROW["op"]}+模型假设!${ac(yr)}${ASM_ROW["da"]}'

    # 净利润（合并）= 营业利润 × (1 - 税率)
    ws_is.cell(IS_ROW['np'], col).value = \
        f'={dc(yr)}{IS_ROW["op"]}*(1-模型假设!${ac(yr)}${ASM_ROW["tax_rate"]})'

    # 归母净利润 = 净利润 × 归母比例
    ws_is.cell(IS_ROW['np_attr'], col).value = \
        f'={dc(yr)}{IS_ROW["np"]}*模型假设!${ac(yr)}${ASM_ROW["parent_ratio"]}'

    # EPS = 归母净利润 / 总股本
    ws_is.cell(IS_ROW['eps'], col).value = \
        f'={dc(yr)}{IS_ROW["np_attr"]}/模型假设!${ac("2026E")}${ASM_ROW["shares"]}'

    # 比率行（公式，黑色字体）
    ws_is.cell(IS_ROW['yoy'],   col).value = \
        f'=({dc(yr)}{IS_ROW["revenue"]}-{dc(prev(yr))}{IS_ROW["revenue"]})/{dc(prev(yr))}{IS_ROW["revenue"]}'
    ws_is.cell(IS_ROW['gm'],    col).value = \
        f'={dc(yr)}{IS_ROW["gp"]}/{dc(yr)}{IS_ROW["revenue"]}'
    ws_is.cell(IS_ROW['rd_rate'],col).value = \
        f'=-{dc(yr)}{IS_ROW["rd"]}/{dc(yr)}{IS_ROW["revenue"]}'
    ws_is.cell(IS_ROW['op_margin'], col).value = \
        f'={dc(yr)}{IS_ROW["op"]}/{dc(yr)}{IS_ROW["revenue"]}'
    ws_is.cell(IS_ROW['ebitda_margin'], col).value = \
        f'={dc(yr)}{IS_ROW["ebitda"]}/{dc(yr)}{IS_ROW["revenue"]}'
    ws_is.cell(IS_ROW['np_attr_yoy'], col).value = \
        f'=({dc(yr)}{IS_ROW["np_attr"]}-{dc(prev(yr))}{IS_ROW["np_attr"]})/{dc(prev(yr))}{IS_ROW["np_attr"]}'
    ws_is.cell(IS_ROW['np_margin'], col).value = \
        f'={dc(yr)}{IS_ROW["np_attr"]}/{dc(yr)}{IS_ROW["revenue"]}'
```

---

### 资产负债表预测列公式模板

```python
for yr in PRED_YEARS:
    col = YEAR_COL[yr]; p = prev(yr)

    # 应收账款 = 营收 × 应收天数 / 365
    ws_bs.cell(BS_ROW['ar'], col).value = \
        f'=利润表!{dc(yr)}{IS_ROW["revenue"]}*模型假设!${ac(yr)}${ASM_ROW["ar_days"]}/365'
    # 存货 = |COGS| × 存货天数 / 365（COGS在IS为负，取负）
    ws_bs.cell(BS_ROW['inv'], col).value = \
        f'=-利润表!{dc(yr)}{IS_ROW["cogs"]}*模型假设!${ac(yr)}${ASM_ROW["inv_days"]}/365'
    # 其他流动资产：上期×0.99
    ws_bs.cell(BS_ROW['other_ca'], col).value = f'={dc(p)}{BS_ROW["other_ca"]}*0.99'
    # 流动资产合计
    ws_bs.cell(BS_ROW['ca'], col).value = \
        f'=SUM({dc(yr)}{BS_ROW["cash"]}:{dc(yr)}{BS_ROW["other_ca"]})'
    # 固定资产净值 = 上期 + Capex流出 - D&A
    ws_bs.cell(BS_ROW['fa'], col).value = \
        f'={dc(p)}{BS_ROW["fa"]}+模型假设!${ac(yr)}${ASM_ROW["capex"]}-模型假设!${ac(yr)}${ASM_ROW["da"]}'
    # 其他非流动资产：保持
    ws_bs.cell(BS_ROW['other_nca'], col).value = f'={dc(p)}{BS_ROW["other_nca"]}'
    # 非流动资产/资产总计
    ws_bs.cell(BS_ROW['nca'], col).value = \
        f'={dc(yr)}{BS_ROW["fa"]}+{dc(yr)}{BS_ROW["other_nca"]}'
    ws_bs.cell(BS_ROW['ta'], col).value = \
        f'={dc(yr)}{BS_ROW["ca"]}+{dc(yr)}{BS_ROW["nca"]}'
    # 应付账款 = |COGS| × 应付天数 / 365
    ws_bs.cell(BS_ROW['ap'], col).value = \
        f'=-利润表!{dc(yr)}{IS_ROW["cogs"]}*模型假设!${ac(yr)}${ASM_ROW["ap_days"]}/365'
    # 短期借款/其他流动负债：保持
    ws_bs.cell(BS_ROW['std'],      col).value = f'={dc(p)}{BS_ROW["std"]}'
    ws_bs.cell(BS_ROW['other_cl'], col).value = f'={dc(p)}{BS_ROW["other_cl"]}*0.98'
    ws_bs.cell(BS_ROW['cl'], col).value = \
        f'={dc(yr)}{BS_ROW["std"]}+{dc(yr)}{BS_ROW["ap"]}+{dc(yr)}{BS_ROW["other_cl"]}'
    ws_bs.cell(BS_ROW['ltd'],       col).value = f'={dc(p)}{BS_ROW["ltd"]}'
    ws_bs.cell(BS_ROW['other_ncl'], col).value = f'={dc(p)}{BS_ROW["other_ncl"]}'
    ws_bs.cell(BS_ROW['ncl'], col).value = \
        f'={dc(yr)}{BS_ROW["ltd"]}+{dc(yr)}{BS_ROW["other_ncl"]}'
    ws_bs.cell(BS_ROW['tl'], col).value = \
        f'={dc(yr)}{BS_ROW["cl"]}+{dc(yr)}{BS_ROW["ncl"]}'
    # 归母权益 = 上期 + 归母净利 × (1 - 派息率)
    ws_bs.cell(BS_ROW['parent_eq'], col).value = (
        f'={dc(p)}{BS_ROW["parent_eq"]}'
        f'+利润表!{dc(yr)}{IS_ROW["np_attr"]}'
        f'*(1-模型假设!${ac(yr)}${ASM_ROW["div_payout"]})'
    )
    ws_bs.cell(BS_ROW['minority'], col).value = f'={dc(p)}{BS_ROW["minority"]}*1.01'
    ws_bs.cell(BS_ROW['equity'], col).value = \
        f'={dc(yr)}{BS_ROW["parent_eq"]}+{dc(yr)}{BS_ROW["minority"]}'
    # 验证行（= 负债+权益，应等于资产总计）
    ws_bs.cell(BS_ROW['bs_check'], col).value = \
        f'={dc(yr)}{BS_ROW["tl"]}+{dc(yr)}{BS_ROW["equity"]}'
    ws_bs.cell(BS_ROW['leverage'], col).value = \
        f'={dc(yr)}{BS_ROW["tl"]}/{dc(yr)}{BS_ROW["ta"]}'
    ws_bs.cell(BS_ROW['net_debt_eq'], col).value = \
        f'=({dc(yr)}{BS_ROW["std"]}+{dc(yr)}{BS_ROW["ltd"]}-{dc(yr)}{BS_ROW["cash"]})/{dc(yr)}{BS_ROW["equity"]}'
    # 货币资金 ← 来自现金流量表期末余额（跨Sheet引用）
    ws_bs.cell(BS_ROW['cash'], col).value = \
        f'=现金流量表!{dc(yr)}{CF_ROW["end_cash"]}'
```

---

### 现金流量表预测列公式模板

```python
for yr in PRED_YEARS:
    col = YEAR_COL[yr]; p = prev(yr)

    # 经营现金流 = 净利润 + D&A - 营运资本变动
    ws_cf.cell(CF_ROW['oper'], col).value = (
        f'=利润表!{dc(yr)}{IS_ROW["np"]}'
        f'+模型假设!${ac(yr)}${ASM_ROW["da"]}'
        f'-((资产负债表!{dc(yr)}{BS_ROW["ar"]}-资产负债表!{dc(p)}{BS_ROW["ar"]})'
        f'+(资产负债表!{dc(yr)}{BS_ROW["inv"]}-资产负债表!{dc(p)}{BS_ROW["inv"]})'
        f'-(资产负债表!{dc(yr)}{BS_ROW["ap"]}-资产负债表!{dc(p)}{BS_ROW["ap"]}))'
    )
    # Capex（负值）= -Capex假设
    ws_cf.cell(CF_ROW['capex'], col).value = \
        f'=-模型假设!${ac(yr)}${ASM_ROW["capex"]}'
    # FCF = 经营 + Capex
    ws_cf.cell(CF_ROW['fcf'], col).value = \
        f'={dc(yr)}{CF_ROW["oper"]}+{dc(yr)}{CF_ROW["capex"]}'
    # 投资活动现金流 ≈ -Capex - 其他投资
    ws_cf.cell(CF_ROW['invest'], col).value = \
        f'=-模型假设!${ac(yr)}${ASM_ROW["capex"]}-15'
    # 筹资活动现金流 = -分红（归母净利 × 派息率）
    ws_cf.cell(CF_ROW['finance_cf'], col).value = \
        f'=-利润表!{dc(yr)}{IS_ROW["np_attr"]}*模型假设!${ac(yr)}${ASM_ROW["div_payout"]}'
    # 净现金增量
    ws_cf.cell(CF_ROW['net_chg'], col).value = \
        f'={dc(yr)}{CF_ROW["oper"]}+{dc(yr)}{CF_ROW["invest"]}+{dc(yr)}{CF_ROW["finance_cf"]}'
    # 期初现金 = 上期期末
    ws_cf.cell(CF_ROW['beg_cash'], col).value = \
        f'={dc(p)}{CF_ROW["end_cash"]}'
    # 期末现金 = 期初 + 净增量
    ws_cf.cell(CF_ROW['end_cash'], col).value = \
        f'={dc(yr)}{CF_ROW["beg_cash"]}+{dc(yr)}{CF_ROW["net_chg"]}'
```

---

### 业务拆分 Sheet 构建代码（新建 Sheet 时执行）

```python
def build_business_split_sheet(wb, segments_data, HIST_YEARS, PRED_YEARS, YEAR_COL):
    """
    segments_data: [
        {
            'name': '分部1名称',
            'hist_rev': {yr: float, ...},    # 历史收入（亿元）
            'hist_gm':  {yr: float, ...},    # 历史毛利率（%或小数均可）
            'pred_growth': {yr: float, ...}, # 预测增速（小数，如0.15）
            'pred_gm':  {yr: float, ...},     # 预测毛利率（小数）
        },
        ...
    ]
    """
    from openpyxl.utils import get_column_letter as gcl
    from openpyxl.styles import Font

    wb['业务拆分'] = ws_bs = wb.create_sheet('业务拆分')

    # ---------- 动态分配行号 ----------
    # 每个分部占4行：[收入, 增速, 毛利率, 毛利额]
    BS_SEG_ROWS = []
    row = 3  # 从第3行开始（row1=标题公司名, row2=空白或标签）
    for seg in segments_data:
        BS_SEG_ROWS.append({
            'name': seg['name'],
            'rev_row':  row,
            'gro_row':  row + 1,
            'gm_row':   row + 2,
            'gp_row':   row + 3,
        })
        row += 4

    # 汇总区紧接分段之后
    BS_ROW = {
        'total_rev':   row,
        'total_gp':    row + 1,
        'blended_gm':  row + 2,
        'rev_growth':  row + 3,
    }

    # 辅助函数
    def dc(yr): return gcl(YEAR_COL[yr])
    def prev(yr): return ALL_YEARS[ALL_YEARS.index(yr) - 1]

    # ---------- 列1：标签 ----------
    ws_bs.cell(1, 1, f'【业务拆分】')
    for seg in BS_SEG_ROWS:
        ws_bs.cell(seg['rev_row'], 1, seg['name'] + ' 收入')
        ws_bs.cell(seg['gro_row'], 1, seg['name'] + ' 增速')
        ws_bs.cell(seg['gm_row'],  1, seg['name'] + ' 毛利率')
        ws_bs.cell(seg['gp_row'],  1, seg['name'] + ' 毛利额')
    ws_bs.cell(BS_ROW['total_rev'],  1, '汇总：总收入')
    ws_bs.cell(BS_ROW['total_gp'],   1, '汇总：总毛利额')
    ws_bs.cell(BS_ROW['blended_gm'], 1, '综合毛利率')
    ws_bs.cell(BS_ROW['rev_growth'], 1, '营收增速')

    # ---------- 年份标题行（row=2） ----------
    for yr in ALL_YEARS:
        col = YEAR_COL[yr]
        ws_bs.cell(2, col, yr)

    # ---------- 历史数据（数值） ----------
    for seg in BS_SEG_ROWS:
        for yr in HIST_YEARS:
            col = YEAR_COL[yr]
            rev = seg['hist_rev'].get(yr, 0)
            gm  = seg['hist_gm'].get(yr, 0)
            # 收入（蓝色）
            c = ws_bs.cell(seg['rev_row'], col, rev)
            c.font = Font(color='0000FF')  # 蓝色
            # 毛利率（蓝色）
            c = ws_bs.cell(seg['gm_row'], col, gm)
            c.font = Font(color='0000FF')
            # 增速：计算值（黑色）
            p_yr = prev(yr)
            if p_yr in seg['hist_rev'] and seg['hist_rev'][p_yr] != 0:
                gro = seg['hist_rev'][yr] / seg['hist_rev'][p_yr] - 1
                ws_bs.cell(seg['gro_row'], col, gro)
            # 毛利额 = 收入 × 毛利率（黑色公式）
            ws_bs.cell(seg['gp_row'], col).value = \
                f'={dc(yr)}{seg["rev_row"]}*{dc(yr)}{seg["gm_row"]}'

    # 历史年汇总行
    for yr in HIST_YEARS:
        col = YEAR_COL[yr]
        # 总收入 = SUM各分部收入
        rev_refs = '+'.join([f'{dc(yr)}{s["rev_row"]}' for s in BS_SEG_ROWS])
        ws_bs.cell(BS_ROW['total_rev'], col).value = f'={rev_refs}'
        # 总毛利额 = SUM各分部毛利额
        gp_refs = '+'.join([f'{dc(yr)}{s["gp_row"]}' for s in BS_SEG_ROWS])
        ws_bs.cell(BS_ROW['total_gp'], col).value = f'={gp_refs}'
        # 综合毛利率 = 总毛利额 / 总收入（黑色公式）
        ws_bs.cell(BS_ROW['blended_gm'], col).value = \
            f'={dc(yr)}{BS_ROW["total_gp"]}/{dc(yr)}{BS_ROW["total_rev"]}'
        # 营收增速
        p_yr = prev(yr)
        if p_yr in HIST_YEARS:
            ws_bs.cell(BS_ROW['rev_growth'], col).value = \
                f'=({dc(yr)}{BS_ROW["total_rev"]}-{dc(prev(yr))}{BS_ROW["total_rev"]})/{dc(prev(yr))}{BS_ROW["total_rev"]}'
        # 历史年增速和毛利率不标蓝，由实际数据算出

    # ---------- 预测数据（蓝色=手动输入） ----------
    for yr in PRED_YEARS:
        col = YEAR_COL[yr]
        for seg in BS_SEG_ROWS:
            # 增速（蓝色输入）
            gro = seg['pred_growth'].get(yr, 0.0)
            c = ws_bs.cell(seg['gro_row'], col, gro)
            c.font = Font(color='0000FF')
            # 毛利率（蓝色输入）
            gm = seg['pred_gm'].get(yr, 0.0)
            c = ws_bs.cell(seg['gm_row'], col, gm)
            c.font = Font(color='0000FF')
            # 收入 = 上期收入 × (1 + 增速)（公式）
            ws_bs.cell(seg['rev_row'], col).value = \
                f'={dc(prev(yr))}{seg["rev_row"]}*(1+{dc(yr)}{seg["gro_row"]})'
            # 毛利额 = 收入 × 毛利率（公式）
            ws_bs.cell(seg['gp_row'], col).value = \
                f'={dc(yr)}{seg["rev_row"]}*{dc(yr)}{seg["gm_row"]}'

        # 汇总行（公式，非手动）
        rev_refs = '+'.join([f'{dc(yr)}{s["rev_row"]}' for s in BS_SEG_ROWS])
        ws_bs.cell(BS_ROW['total_rev'], col).value = f'={rev_refs}'
        gp_refs = '+'.join([f'{dc(yr)}{s["gp_row"]}' for s in BS_SEG_ROWS])
        ws_bs.cell(BS_ROW['total_gp'], col).value = f'={gp_refs}'
        # 综合毛利率 = 总毛利额 / 总收入（黑色公式，不是加权平均）
        ws_bs.cell(BS_ROW['blended_gm'], col).value = \
            f'={dc(yr)}{BS_ROW["total_gp"]}/{dc(yr)}{BS_ROW["total_rev"]}'
        # 营收增速
        ws_bs.cell(BS_ROW['rev_growth'], col).value = \
            f'=({dc(yr)}{BS_ROW["total_rev"]}-{dc(prev(yr))}{BS_ROW["total_rev"]})/{dc(prev(yr))}{BS_ROW["total_rev"]}'

    return BS_ROW, BS_SEG_ROWS
```

### 模型假设 Sheet — 业务拆分联动代码（构建模型假设 Sheet 时执行）

```python
def link_asm_to_bs(ws_asm, BS_ROW, YEAR_COL, ASM_COL, PRED_YEARS):
    """
    将模型假设 Sheet 的营收增速和毛利率改为绿色跨Sheet公式引用
    注意：rev_growth(row5) 和 gross_margin(row7) 不再是蓝色手动输入，
    而是直接引用业务拆分 Sheet 的汇总结果（绿色）
    """
    from openpyxl.styles import Font

    for yr in PRED_YEARS:
        col_asm = ASM_COL[yr]   # 模型假设列（B/C/D/E/F）
        col_bs  = YEAR_COL[yr]  # 业务拆分列（同一数字）

        # 营收增速 ← 业务拆分!rev_growth（绿色跨Sheet引用）
        c_rev = ws_asm.cell(ASM_ROW['rev_growth'], col_asm)
        c_rev.value = f'=业务拆分!{gcl(col_bs)}{BS_ROW["rev_growth"]}'
        c_rev.font = Font(color='008000')   # 绿色

        # 毛利率 ← 业务拆分!blended_gm（绿色跨Sheet引用）
        c_gm = ws_asm.cell(ASM_ROW['gross_margin'], col_asm)
        c_gm.value = f'=业务拆分!{gcl(col_bs)}{BS_ROW["blended_gm"]}'
        c_gm.font = Font(color='008000')   # 绿色
```

### 完整流程顺序

```python
# 1. 创建/加载 workbook
wb = Workbook()
ws_asm = wb['模型假设']
ws_is  = wb['利润表']
# ... 其他 sheet

# 2. 先构建业务拆分 Sheet（得到 BS_ROW）
segments_data = [...]  # 来自 iFind 或财报的业务分部数据
BS_ROW, BS_SEG_ROWS = build_business_split_sheet(wb, segments_data, HIST_YEARS, PRED_YEARS, YEAR_COL)

# 3. 再将模型假设的 rev_growth 和 gross_margin 链接到业务拆分
link_asm_to_bs(ws_asm, BS_ROW, YEAR_COL, ASM_COL, PRED_YEARS)

# 4. 此时利润表的预测列公式不需要变化（仍引用模型假设）
# 业务拆分 Sheet 变了 → 模型假设联动 → 利润表自动更新 ✓
```

---

### 构建完成后的公式验证（必须执行）

```python
def verify_formulas_written(wb):
    """确认预测列写入的是公式字符串，而非静态数值"""
    ws_is = wb['利润表']
    ws_asm = wb['模型假设']
    PRED_YEARS = ['2026E','2027E','2028E','2029E','2030E']
    YEAR_COL   = {'2026E':9,'2027E':10,'2028E':11,'2029E':12,'2030E':13}
    ASM_COL    = {'2026E':2,'2027E':3,'2028E':4,'2029E':5,'2030E':6}
    IS_ROW     = {'revenue':4, 'gp':7, 'np_attr':22}
    errors = []

    # 1. 利润表预测列必须为公式
    for yr in PRED_YEARS:
        for key in ['revenue','gp','np_attr']:
            val = ws_is.cell(IS_ROW[key], YEAR_COL[yr]).value
            if isinstance(val, (int, float)):
                errors.append(f"❌ 利润表 {yr} {key} = 静态数值 {val}，应为公式！")

    # 2. 模型假设的 rev_growth 和 gross_margin 必须为绿色跨Sheet引用（公式，非数值）
    for yr in PRED_YEARS:
        col_asm = ASM_COL[yr]
        rev_gm = ws_asm.cell(ASM_ROW['gross_margin'], col_asm).value
        rev_gr  = ws_asm.cell(ASM_ROW['rev_growth'],   col_asm).value
        if isinstance(rev_gm, (int, float)):
            errors.append(f"❌ 模型假设 {yr} gross_margin = 静态数值 {rev_gm}，应为 =业务拆分!XX 公式！")
        if isinstance(rev_gr, (int, float)):
            errors.append(f"❌ 模型假设 {yr} rev_growth = 静态数值 {rev_gr}，应为 =业务拆分!XX 公式！")
        if isinstance(rev_gm, str) and not rev_gm.startswith('='):
            errors.append(f"❌ 模型假设 {yr} gross_margin 未以=开头: {rev_gm}")
        if isinstance(rev_gr, str) and not rev_gr.startswith('='):
            errors.append(f"❌ 模型假设 {yr} rev_growth 未以=开头: {rev_gr}")

    if errors:
        print("\n".join(errors))
        raise ValueError("模型假设联动验证失败！")
    print("✓ 所有预测列均为 Excel 公式字符串")
    print("✓ 模型假设的 rev_growth 和 gross_margin 为跨Sheet绿色引用")

verify_formulas_written(wb)
```

## ⚠️ 重建模型常见问题（2025A实战经验）

当公司有新年报披露，需要将模型从"预测"更新为"实际"时，以下是泰格医药2025A重建时遇到的问题及改进方案。

### 问题一：YEAR_COL/ASM_COL 年份映射错位

**现象**：旧模型最后一列是`2025E`（预测），新模型需要将`2025A`（实际）作为最新历史年，预测起始改为`2026E`。如果映射写错，公式引用会全部错位。

**正确映射**：
```python
YEAR_COL = {
    '2020A': 2, '2021A': 3, '2022A': 4, '2023A': 5, '2024A': 6, '2025A': 7,
    '2026E': 8, '2027E': 9, '2028E': 10, '2029E': 11, '2030E': 12,
}
# ASM_COL 与 YEAR_COL 完全相同（不是 YEAR_COL + 1）
```

**检查方法**：模型假设 Sheet 的年份标题行（row 3）必须与 YEAR_COL 一一对应。

---

### 问题二：iFind 返回的 BS 数据是 MRQ 而非 period-specific

**现象**：调用`get_stock_financials`取 2025A 的资产负债表，返回的`total_assets`是 143.9亿，而非年报披露的 283.59亿。原因是 iFind 默认返回 MRQ（最近季度末）数据，不是指定年份的年末数据。

**解决方案**：分两步取 BS 数据：
1. 先查`get_stock_info`或`get_stock_summary`确认最新资产负债表的项目明细
2. 对 BS 每个科目单独用`get_stock_financials`指定 date 范围获取 period-specific 数据
3. 或者直接使用`get_stock_shareholders`+`get_stock_summary`中的最新完整 BS 数据

**验证方法**：填完 BS 后立即检查 `total_assets = 现金+应收+存货+...+固定资产+...`，必须与实际年报一致。

---

### 问题三：IS 历史列用了假设的费用率推导，导致数据失真

**现象**：旧代码用毛利率和三费费率假设反推利润表各项，结果 2025A 归母净利算出 4.61亿，实际是 8.88亿。

**解决方案**：IS 历史数据必须直接使用 iFind 返回的实际费用项目：
```python
# ✅ 正确：从 iFind 获取实际费用数据
d['sell_exp']   = float(resp['data'][0].get('sell_exp', 0) or 0) / 1e8
d['admin_exp']  = float(resp['data'][0].get('admin_exp', 0) or 0) / 1e8
d['rd_exp']     = float(resp['data'][0].get('rd_exp', 0) or 0) / 1e8
d['fin_exp']    = float(resp['data'][0].get('fin_exp', 0) or 0) / 1e8
d['tax']        = float(resp['data'][0].get('tax', 0) or 0) / 1e8

# ❌ 错误：用费率假设推导（丢失了实际数据）
sell_exp = revenue * 0.035  # 不要这样！
```

---

### 问题四：BS 历史列缺少某些科目导致 KeyError

**现象**：iFind 返回的 BS 数据不一定包含所有科目（如`other_ncl`、`other_ca`、`other_cl`、`other_nca`），直接用`d['other_ncl']`会触发 KeyError。

**解决方案**：所有 BS 科目的读取和写入都使用`.get()`带默认值：
```python
# 读取时
nca = d['fa'] + d.get('other_nca', 0)
cl = d['std'] + d['ap'] + d.get('other_cl', 0)
ncl = d['ltd'] + d.get('other_ncl', 0.5)

# 写入时
ws_bs.cell(BS_ROW['other_nca'], col, d.get('other_nca', 0))
ws_bs.cell(BS_ROW['other_ncl'], col, d.get('other_ncl', 0.5))
ws_bs.cell(BS_ROW['other_cl'],  col, d.get('other_cl', 0))
```

**默认值参考**：
| 科目 | 默认值 | 说明 |
|------|--------|------|
| other_nca | 0 | 其他非流动资产，小公司可能无 |
| other_ncl | 0.5 | 其他非流动负债，小公司用较小值 |
| other_ca | 0 | 其他流动资产 |
| other_cl | 0 | 其他流动负债 |

---

### 问题五：BS 聚合计算必须显式推导，不能信任 iFind 的汇总数

**现象**：即使 iFind 返回了`total_assets`，它可能是 MRQ 数据而非 period-specific。直接用它会导致后续公式引用错误数据。

**解决方案**：CA/NCA/TA/CL/NCL/TL/Equity 全部用组件显式计算：
```python
ca = d['cash'] + d['ar'] + d['inv'] + d.get('other_ca', 0)
nca = d['fa'] + d.get('other_nca', 0)
ta = ca + nca
cl = d['std'] + d['ap'] + d.get('other_cl', 0)
ncl = d['ltd'] + d.get('other_ncl', 0.5)
tl = cl + ncl
equity = d['parent_eq'] + d['minority']

# 验证：资产负债表必须平衡
assert abs(ta - (tl + equity)) < 0.01, f"BS不平衡！TA={ta}, TL+EQ={tl+equity}"
```

---

### 问题六：重建模型后的验证清单

每次重建或更新模型后，必须执行以下验证：

```python
def verify_historical_data(wb, HIST_DATA):
    """验证历史数据填入正确"""
    errors = []
    
    # 1. BS 平衡检查
    bs = wb['资产负债表']
    for yr, col in [('2024A', 6), ('2025A', 7)]:
        ta = bs.cell(BS_ROW['ta'], col).value
        check = bs.cell(BS_ROW['bs_check'], col).value
        if abs(ta - check) > 0.1:
            errors.append(f"❌ {yr} BS不平衡: TA={ta}, Check={check}")
    
    # 2. IS 关键指标抽查
    is_sheet = wb['利润表']
    for yr, col in [('2024A', 6), ('2025A', 7)]:
        np_attr = is_sheet.cell(IS_ROW['np_attr'], col).value
        expected = HIST_DATA[yr]['np_attr']
        if np_attr is None or abs(np_attr - expected) > 0.1:
            errors.append(f"❌ {yr} 归母净利不匹配: {np_attr} vs 预期{expected}")
    
    # 3. CF 期末现金 = BS 货币资金
    cf = wb['现金流量表']
    for yr, col in [('2024A', 6), ('2025A', 7)]:
        cf_cash = cf.cell(CF_ROW['end_cash'], col).value
        bs_cash = bs.cell(BS_ROW['cash'], col).value
        if abs(cf_cash - bs_cash) > 0.01:
            errors.append(f"❌ {yr} 现金不一致: CF={cf_cash}, BS={bs_cash}")
    
    if errors:
        print("\n".join(errors))
        raise ValueError("历史数据验证失败！")
    print("✓ 历史数据验证通过")

verify_historical_data(wb, HIST_DATA)
```

---

### 问题七：公司最新年报未披露（如2025A缺失）时的动态处理

**现象**：当前日期是2026年，但某公司（比如药明康德）2025年年报尚未披露。若直接运行写死2025A的脚本，会报 `KeyError: '2025A'`。

**核心原则**：年份映射必须从实际获取到的数据**动态推导**，而不是写死。

**解决方案：构建脚本时加入动态年份检测逻辑**

```python
# ========== 第一步：从 iFind 获取可用历史年份 ==========
# 调用 iFind get_stock_financials 获取近6年年报
# 根据返回的 report_date 字段确定哪些年份有数据
# 假设获取到 ['2020A', '2021A', '2022A', '2023A', '2024A']（没有2025A）

available_hist_years = []   # 自动检测，实际有哪些A年
for yr in ['2024A', '2023A', '2022A', '2021A', '2020A', '2019A']:
    data = get_stock_financials(ticker, yr, indicators=...)
    if data and data.get('revenue'):
        available_hist_years.append(yr)
# available_hist_years = ['2020A', '2021A', '2022A', '2023A', '2024A']

# ========== 第二步：动态构建年份映射 ==========
# 基础年（最早历史年），通常固定为6年前
BASE_YEAR = '2020A'
all_hist_sorted = sorted(available_hist_years)   # ['2020A', '2021A', ..., '2024A']
latest_hist = all_hist_sorted[-1]                # '2024A'
pred_start = str(int(latest_hist[:4]) + 1) + 'E' # '2025E'（若latest=2024A则从2025E开始预测）

# YEAR_COL = {历史年: 列号, 预测年: 列号}
YEAR_COL = {}
col = 2
for yr in all_hist_sorted:
    YEAR_COL[yr] = col; col += 1
for i in range(5):   # 5年预测
    yr = str(int(pred_start[:4]) + i) + 'E'
    YEAR_COL[yr] = col; col += 1

# ASM_COL 与 YEAR_COL 完全一致
ASM_COL = dict(YEAR_COL)

ALL_YEARS  = list(YEAR_COL.keys())
HIST_YEARS = [y for y in ALL_YEARS if y.endswith('A')]
PRED_YEARS = [y for y in ALL_YEARS if y.endswith('E')]
# 例如: HIST_YEARS=['2020A',..,'2024A'], PRED_YEARS=['2025E',..,'2029E']
```

**与固定写死的对比**：

| 场景 | 泰格医药（2025A已披露） | 药明康德（2025A未披露） |
|------|----------------------|----------------------|
| latest_hist | 2025A | 2024A |
| 预测起始年 | 2026E | 2025E |
| HIST_YEARS | 2020A~2025A | 2020A~2024A |
| PRED_YEARS | 2026E~2030E | 2025E~2029E |
| YEAR_COL['2025A'] | 存在 | **不存在（动态跳过）** |

**关键代码约束**：
1. `HIST_DATA` dict 只填充实际获取到的年份，不写不存在的年份
2. 所有遍历历史数据的代码使用 `HIST_YEARS`（动态推导），禁止硬编码 `['2020A', ..., '2025A']`
3. 预测起始年由 `latest_hist` 决定，而非固定 "2026E"
4. Excel 年份标题行（row 3）由 `ALL_YEARS` 动态生成

**验证**：运行前检查
```python
# 确保 HIST_DATA 的 key 和 HIST_YEARS 完全一致
assert set(HIST_DATA.keys()) == set(HIST_YEARS), \
    f"HIST_DATA keys {set(HIST_DATA.keys())} vs HIST_YEARS {set(HIST_YEARS)} 不匹配！"
print(f"✓ 最新历史年: {latest_hist}, 预测起始: {PRED_YEARS[0]}")
```

---

### 完整的 HIST_DATA 结构（参考泰格医药 2025A）

```python
HIST_DATA = {
    '2025A': {
        # IS
        'revenue': 68.33, 'yoy': 0.035, 'gp': 18.73, 'cogs': -49.60,
        'sell_exp': -2.35, 'admin_exp': -7.26, 'rd_exp': -2.58,
        'fin_exp': -1.00, 'op_profit': 10.09, 'tax': 1.98,
        'np': 8.05, 'np_attr': 8.88, 'eps': 1.04,
        # CF
        'oper_cf': 11.18, 'invest_cf': 4.92, 'finance_cf': -19.27,
        # BS
        'cash': 44.00, 'ar': 14.06, 'inv': 0.42, 'other_ca': 3.29,
        'fa': 11.88, 'other_nca': 209.94,
        'std': 5.11, 'ap': 3.65, 'other_cl': 19.59,
        'ltd': 3.80, 'other_ncl': 8.87,
        'parent_eq': 209.60, 'minority': 32.97,
    },
    # ... 其他年份
}
```

---

## 重要注意事项

### 关于 iFind API 调用
- 每次调用前必须先 `get_access_token`
- 季度数据：用 `reporttype` 参数或通过日期范围获取所有期别再筛选
- 若某 indicator 权限不足，换用等价指标（参见 ifind-data skill）
- 所有金额单位以"亿元人民币"为准（需注意 iFinD 返回单位可能是元，需÷1亿）

### 关于 Excel 构建
- 使用 openpyxl 创建文件
- **预测列必须全部使用 Excel 公式字符串** — 完整代码模板见上方「⚠️ Excel 公式架构」章节
- 历史列写入数值，预测列写入以 `=` 开头的公式字符串，两者颜色规范不同
- **业务拆分 Sheet 中的蓝色输入**：各分部预测期的收入增速、预测毛利率
- **模型假设 Sheet 中的绿色引用**：`rev_growth`（第5行）和 `gross_margin`（第7行）必须是通过 `link_asm_to_bs()` 写入的跨 Sheet 绿色公式，**禁止手动填入蓝色数值**
- 构建完成后调用 `verify_formulas_written(wb)` 确认公式写入正确

### 关于预测假设（业务拆分驱动）
- 预测期的业务拆分数据（各分部增速、毛利率）来源优先级：iFind 一致预期 > 研报数字 > 合理外推
- FY1/FY2/FY3：优先使用 iFind 一致预期反推
- FY4/FY5（2029/2030）无一致预期时，参照 FY3 趋势合理外推
- **模型假设 Sheet 的营收增速和综合毛利率无需手动输入**，由业务拆分 Sheet 自动汇总得出
- 将数据来源标注在业务拆分 Sheet 的备注列

### 关于质量评分
- 评分应基于客观数据，避免主观夸大
- 每项评分必须附上依据说明
- 综合评分保留1位小数

---

## 参考文件

- `references/excel_template_structure.md` — Excel 各 Sheet 详细列结构
- `references/scoring_rubric.md` — 四个维度评分详细标准与示例
