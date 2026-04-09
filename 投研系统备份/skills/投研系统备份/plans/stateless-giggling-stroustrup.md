# 宁德时代 (300750) 完整财务模型建设计划

## Context
用户需要为宁德时代建立一份机构级 Excel 财务模型，包含：
- 历史三表（IS / BS / CF）
- 业务拆分（动力电池 / 储能 / 材料 / 其他）
- 未来预测（3-5年）
- 估值（DCF + 可比公司倍数）

## 数据来源
| 数据需求 | 工具 |
|---------|------|
| 历史三表（2019–2024） | ifind `get_stock_financials` |
| 业务分部收入拆分 | ifind `search_notice`（年报分部数据） |
| 行情 / 估值倍数 | ifind `get_stock_perfomance` |
| 同行可比公司 | ifind `search_stocks` + `get_stock_financials` |
| 宏观/行业数据 | ifind `get_edb_data` |

## 执行步骤

### Step 1 — 历史财务数据拉取
- 调用 `get_stock_financials` 拉取 2019–2024 全年三表数据
- 指标：营收、毛利率、EBIT、净利润、EPS、资产负债、经营/投资/融资现金流
- 整理为标准化格式

### Step 2 — 业务拆分数据
- 调用 `search_notice` 搜索宁德时代 2021–2024 年报中的"分部信息"
- 提取：动力电池系统、储能系统、电池材料、其他各业务收入 / 毛利
- 如公告数据不足，补充用行业报告推算

### Step 3 — 可比公司数据
- 同行：比亚迪(002594)、亿纬锂能(300014)、国轩高科(002074)、欣旺达(300207)
- 拉取 PE / PB / EV/EBITDA / EV/Revenue 倍数

### Step 4 — 预测模型（2025E–2027E）
- 收入驱动：装机量增长 × 电池单价
- 业务拆分预测：动力/储能/材料各分部独立预测
- 利润表：毛利率路径 + 费用率假设
- 现金流：资本开支 + 营运资金变动

### Step 5 — 估值
- DCF：WACC 计算（CAPM）+ 永续增长率敏感性分析
- 可比倍数：EV/EBITDA、PE、PB 区间

### Step 6 — Excel 输出
使用 `financial-analysis:dcf-model` skill 作为主框架，补充业务拆分 sheet
- Sheet 结构：
  1. `Summary` — 执行摘要 + 估值区间
  2. `Income Statement` — 历史 + 预测
  3. `Balance Sheet`
  4. `Cash Flow`
  5. `Segment Breakdown` — 业务拆分历史 + 预测
  6. `DCF` — WACC + 自由现金流折现
  7. `Comps` — 可比公司倍数表
  8. `Assumptions` — 所有假设汇总

## 关键 Skill
- 主框架：`financial-analysis:dcf-model`
- 数据填充补充：`financial-analysis:3-statement-model`
- 可比分析：`financial-analysis:comps-analysis`

## 验证方式
- 资产负债表平衡检验（资产 = 负债 + 权益）
- 现金流量表与利润表 / 资产负债表勾稽
- DCF 隐含价格与当前股价对比合理性
- 可比倍数与市场估值交叉验证
