# Changelog - rl-company-research-model

All notable changes to this skill are documented here.

---

## [v2.3] (2026-04-27) — ftshare 字段名修复 + 年报过滤 + IS 推导

### 修复（3 个关键 Bug）

1. **IS 字段名不匹配**（`_add_ftshare_fallback` IS_MAP）：ftshare IS 实际字段名与映射不一致
   - `gross_profit` → ftshare 不提供，改为 `revenue - cost` 推导
   - `sell_exp` → 实际是 `sale_expense`
   - `admin_exp` → 实际是 `manag_expense`
   - `finance_exp` → 实际是 `financial_cost`
   - `oper_profit` → 实际是 `profit`
   - `income_tax` → ftshare 不提供，改为 `pbt - np` 推导
   - `minority_profit` → ftshare 不提供，改为 `np - np_attr` 推导
   - 费用项新增加 `negate` 标志，统一存负数
2. **季报覆盖年报**：ftshare items 排序为 annual → q3 → q2 → q1，后处理的季报会覆盖年报数据
   - 修复：IS/BS/CF 三个循环中新增加 `report_type != 'annual'` 过滤
3. **FT_ROW IS 段字段名更新**：对齐 ftshare 实际字段名

### 数据填充提升

| 修复前 | 修复后 |
|--------|--------|
| IS revenue 显示 Q1 数据（847亿 vs 年报 4237亿） | IS 正确显示年报数据 |
| IS gp/cogs/op/tax 全部 MISSING | gp/cogs/op/tax/minority_np 全部正确推导 |
| 696 字段（含重复季度） | 174 字段（6 年 × ~29 字段，全量年报正确数据） |

---

## [v2.2] (2026-04-27) — ftshare 升 P0，iFind 降为 P0.5

### 核心变更

- **数据优先级反转**：ftshare 免费无限，优先调用；iFind 降为 P0.5 补充，只在 ftshare 缺失字段时调用
  - 旧版：iFind (P0) → ftshare (P0.5)，iFind token 消耗大
  - 新版：ftshare (P0) → iFind (P0.5)，节省 token
- **新增 ftshare 字段映射表**：`FT_ROW` 常量定义 ftshare → IS_ROW 字段对照
- **SKILL.md v2.2 描述更新**：数据获取流程改为 ftshare 优先

### 降级触发条件

| 场景 | 数据源 |
|------|--------|
| 三张表主体数据 | ftshare (P0) |
| 所得税/税金及附加/一致预期 | iFind (P0.5) |
| 分部数据 | PDF (P1) |
| P0+P0.5 均失败 | 东方财富妙想 (P2) |

---

## [v2.0] (2026-04-27) — iFind 优先，PDF 降级为兜底

### 核心变更

- **数据优先级反转**：iFind 优先，P0；PDF 降级为 P1 兜底
  - 旧版：PDF (P0) → iFind (P1)，每次建模先跑 PDF，白跑一趟
  - 新版：iFind (P0) → PDF (P1)，iFind 效率高时直接出结果
- **新增 iFind 健康检查**（步骤 1.0）：调用前测试可用性，失败直接降级 PDF
- **分部数据无论如何从 PDF 提取**：iFind 没有业务分部收入/毛利率

### 触发条件

| 场景 | 数据源 |
|------|--------|
| iFind 可用 | 历史三张表/季度数据/一致预期 → iFind (P0) |
| iFind 限流/失败 | 历史三张表 → PDF (P1) |
| 分部数据（始终触发） | 分部收入/毛利率 → PDF (P1) |
| iFind + PDF 均失败 | 东方财富妙想 (P2) |

### 回滚

如需回滚到 v1.1：

```bash
cp ~/.claude/skills/rl-company-research-model/archive/v1.1/SKILL.md \
   ~/.claude/skills/rl-company-research-model/SKILL.md
cp ~/.claude/skills/rl-company-research-model/archive/v1.1/scripts/build_model.py \
   ~/.claude/skills/rl-company-research-model/scripts/build_model.py
```

---

## [v1.1] (2026-04-22) — ASM_COL 独立列修复、季度 Q5→Q2 修复

- 修复 ASM_COL 与 YEAR_COL 列号错位问题
- 修复季度 Sheet Q5 列（不存在）错误引用
- 修复 EPS 公式引用
- 修复 section_title 行号偏移

---

## [v1.0] (2026-04-12) — 初始版本

- 完整财务建模：三张表 + 业务拆分 + 模型假设，预测至 2030E
- PDF 优先数据源架构
- 投行风格 Excel 美化
