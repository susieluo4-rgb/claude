# 计划：新建 `company-financial-model` Skill

## Context

用户希望为 A股/港股上市公司创建一个完整的财务建模 skill，需要包含收入结构拆分、三张表、未来 5 年预测（结合 ifind 一致预期），以及可手动修改的核心假设驱动器。

现有 skill 覆盖不足：
- `3-statement-model`：填写模板为主，不含从零建模、收入拆分、一致预期对接
- `dcf-model`：纯 DCF 估值，美股导向，无收入分部拆分
- `model-update`：更新已有模型，非从零搭建
- `equity-research/earnings`：分析报告导向，非建模

本 skill 定位：**A/H 股上市公司一体化财务建模**，从数据获取→收入拆分→三张表→假设驱动预测→估值一站式完成。

---

## 新 Skill 位置

```
/Users/zhuang225/.claude/skills/financial-analysis/company-financial-model/SKILL.md
```

> 也可放入现有插件目录 `/Users/zhuang225/.claude/plugins/cache/financial-services-plugins/financial-analysis/0.1.0/skills/company-financial-model/SKILL.md`，后者更易被系统识别。**建议放插件目录。**

---

## Skill 设计方案

### SKILL.md 头部（description 触发场景）

```yaml
---
name: company-financial-model
description: |
  为 A 股 / 港股上市公司从零搭建完整财务模型。包含：
  (1) 收入结构拆分（分部/产品/地区）；
  (2) 三张报表（利润表、资产负债表、现金流量表）历史整理；
  (3) 未来 5 年预测，自动拉取 ifind 一致预期作为基准；
  (4) 可编辑核心假设驱动器，修改假设后预测值联动更新；
  (5) 相对估值模块（PE/PB/EV-EBITDA）+ 目标价区间。
  触发：建财务模型、搭建三张表、收入拆分建模、做预测模型、
        帮我建个模型、对 [公司] 做财务预测、未来 5 年预测。
---
```

---

### 工作流（7 步）

#### Step 1：数据采集（ifind 优先）
| 数据需求 | ifind 工具 |
|---------|-----------|
| 历史财务（3-5 年） | `get_stock_financials` |
| 公司基本信息、股本 | `get_stock_info` + `get_stock_summary` |
| 行情与估值倍数 | `get_stock_perfomance` |
| 风险指标（Beta） | `get_risk_indicators` |
| **一致预期（核心）** | `get_stock_financials` (consensus fields) |
| 股东结构 | `get_stock_shareholders` |
| 同行对标 | `search_stocks` |
| 宏观/行业数据 | `get_edb_data` / `search_edb` |
| 重大事件 | `get_stock_events` + `search_news` |

采集后输出数据概览并请用户确认，再进入下一步。

#### Step 2：收入结构拆分（Revenue Decomposition）
- 根据年报分部披露，将收入拆分为：产品线 / 业务分部 / 地区
- 输出分部收入矩阵（历史 3-5 年）：绝对值 + 占比 + 增速
- 识别核心增长驱动（量/价拆解，若数据可得）
- 建议格式：**Revenue Bridge 模块**，独立 Tab（`Revenue`）

#### Step 3：三张表历史整理（Historical Financials）
- 利润表（IS）：收入 → 毛利 → EBIT → EBITDA → 净利润
- 资产负债表（BS）：关键科目，支持资产负债率、ROE 计算
- 现金流量表（CF）：经营/投资/筹资三部分
- 挂钩检验：BS平衡、现金衔接、净利润勾稽
- 历史 3 年（最多 5 年），单位：人民币百万

#### Step 4：核心假设驱动器（Assumptions Tab）
这是建模的核心——**所有预测值均由此 Tab 的假设驱动，不允许硬编码预测值**。

假设驱动器分组：

```
【收入假设】
  - 分部增速 Y1~Y5（可分段填写，默认从一致预期初始化）
  - 一致预期 vs 自定义切换开关（Toggle）

【利润率假设】
  - 毛利率 Y1~Y5
  - 销售费用率、管理费用率、研发费用率 Y1~Y5
  - 税率（有效税率）

【资产负债表假设】
  - DSO（应收账款周转天数）
  - DIO（库存周转天数）
  - DPO（应付账款周转天数）
  - CapEx（占收入%）
  - D&A（占固定资产%）

【分红与融资】
  - 分红比率
  - 股本变动假设

【情景选择器】
  - 下拉：乐观 / 基准 / 保守（三套假设）
```

#### Step 5：未来 5 年预测（Projections）
- 所有预测单元格 = Excel 公式，引用 Assumptions Tab
- 分部收入 → 合并收入 → IS 预测 → BS 预测 → CF 预测
- 三张表之间完整勾稽
- 自动对比一致预期（Consensus vs Model 列）

#### Step 6：估值模块（Valuation）
- **相对估值**：PE / PB / EV-EBITDA（历史均值、同行中位数、当前水平）
- **目标价区间**：基于不同情景的合理估值区间
- 可选：简化 DCF（引用 `dcf-model` skill）
- 输出：估值汇总表 + 目标价瀑布图数据

#### Step 7：质量检验 & 交付
- BS 平衡检验（资产 = 负债 + 股东权益，每期 = 0）
- 现金勾稽（CF 期末现金 = BS 现金，每期 = 0）
- 净利润勾稽（IS 净利润 = CF 净利润起始行）
- 运行 `recalc.py` 直到 status = "success"
- 交付文件：`[股票代码]_[公司简称]_财务模型_[日期].xlsx`

---

### Excel 文件 Tab 结构

| Tab | 内容 |
|-----|------|
| `Assumptions` | 核心假设驱动器（所有输入集中于此） |
| `Revenue` | 收入结构拆分（历史 + 预测） |
| `IS` | 利润表（历史 + 预测） |
| `BS` | 资产负债表（历史 + 预测） |
| `CF` | 现金流量表（历史 + 预测） |
| `Valuation` | 相对估值 + 目标价 |
| `Checks` | 平衡检验 Dashboard |
| `Consensus` | ifind 一致预期原始数据 |

---

### 与现有 skill 的差异化

| 维度 | 本 skill | dcf-model | 3-statement-model |
|------|---------|-----------|------------------|
| 数据源 | ifind 优先（A/H股） | SEC/Web | 模板填充 |
| 起点 | 从零建模 | 从零建模 | 填已有模板 |
| 收入拆分 | ✅ 核心模块 | ❌ | ❌ |
| 一致预期 | ✅ ifind 自动填充 | ❌ | ❌ |
| 三张表 | ✅ | 仅 FCF | ✅ |
| 估值 | ✅ 相对估值+DCF | ✅ DCF | ❌ |
| 核心假设驱动 | ✅ 独立 Tab，可调 | ✅ 场景块 | 有限 |

---

### 颜色/格式规范（复用现有标准）

- 蓝色字体：硬编码输入（历史数据、外部参数）
- 黑色字体：公式/计算
- 绿色字体：跨 Tab 引用
- 浅灰填充：Assumptions Tab 输入区
- 深蓝标题：`#1F4E79` 白色粗体
- 一致预期行：浅橙 `#FCE4D6`，用于与自定义假设视觉区分

---

## 关键文件

| 文件 | 用途 |
|------|------|
| 现有 `3-statement-model/SKILL.md` | 三张表勾稽逻辑、格式规范复用 |
| 现有 `dcf-model/SKILL.md` | 假设块结构、sensitivity 方法复用 |
| 现有 `model-update/SKILL.md` | 一致预期对比格式参考 |
| CLAUDE.md | ifind MCP 工具优先级定义 |

---

## 验证方式

1. 对一只 A 股公司（如 `000858.SZ` 五粮液 或 `600519.SH` 茅台）运行：
   - `get_stock_financials` 验证历史数据拉取
   - `get_stock_info` 验证公司信息
   - 检验 ifind 是否返回一致预期字段
2. 运行 skill 后检验 Excel：
   - Checks Tab 所有检验项 = 0
   - 切换情景选择器，预测值联动变化
   - 修改 Assumptions Tab 任意假设，对应 IS/BS/CF 自动更新
3. `recalc.py` 返回 `status: success`

---

## 用户确认的设计决策

| 问题 | 用户选择 |
|------|---------|
| 市场范围 | **A/H/美股通用**（A/H 股优先 ifind；美股 fallback web/SEC） |
| 收入拆分层级 | **分部/产品线**（不做量×价深度拆解） |
| 估值模块 | **内嵌相对估值**（PE/PB/EV-EBITDA）+ DCF 需要时调用 `/dcf-model` |
| 模型语言 | **中文**（行标签、Tab 名、注释全中文） |

### 多市场数据源适配

| 市场 | 数据源优先级 |
|------|------------|
| A 股 (SH/SZ) | ifind MCP → web 搜索 |
| 港股 (HK) | ifind MCP → web 搜索（港元计价，注明换算） |
| 美股 | SEC EDGAR / web 搜索（FactSet/Daloopa 如已认证） |
