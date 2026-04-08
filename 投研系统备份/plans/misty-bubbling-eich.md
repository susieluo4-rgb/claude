# Company Research Model Skill 优化计划

## Context

用户需要优化 `company-research-model` skill，方向是：**工作流优化** + **数据获取 & Excel 结构优化**。

该 skill 用于自动为 A 股/港股公司建立完整财务研究模型（6阶段 pipeline），核心问题是：
1. 路径硬编码错误（`/mnt/Research/` 不存在，实际是 `/Users/zhuang225/Research/`）
2. 纯 prompt-based skill 无执行框架，LLM 每次都从零理解指令，效率低且一致性差
3. iFind API 调用完全串行，17个独立步骤无并行化
4. recalc.py 只存在于 `skills-temp`，plugin cache 版本缺失
5. 数据校验逻辑缺失（三张表平衡、季度加总=年度等）

---

## 优化方案

### 1. 修复路径引用错误

**问题**：`SKILL.md` 中写的是 `/mnt/Research/`，但实际 macOS 路径是 `/Users/zhuang225/Research/`。

**修改**：`SKILL.md` 中所有 `/mnt/Research/` 替换为 `~/Research/`（Home 路径形式，跨平台兼容）。

### 2. 统一引用路径（确定单一 source of truth）

**现状**：
- 活跃版本：`~/.openclaw/skills-temp/skills/pors/company-research-model/`
- Plugin cache：`~/.claude/plugins/cache/company-research/0.1.0/skills/company-research-model/`
- Source 文件：`~/Research/company-research-model.skill`

**方案**：修改 `SKILL.md` 后，重新打包 `.skill` 文件发布到 plugin cache，确保 `scripts/recalc.py` 也被包含。

### 3. 阶段一数据获取并行化

**现状**：iFind API 调用完全串行，每阶段等待上一阶段完成。

**优化**：将 iFind 调用分为3组并行执行（使用 Promise.all 风格，或在 prompt 中明确标注可并行）：

| 并行组 | 调用项 |
|--------|--------|
| 组A（基本同步） | 历史年报（IS/BS/CF）+ 股票信息 |
| 组B（财务数据） | 一致预期 + 估值指标 |
| 组C（补充数据） | 行业分类、风险指标、股东结构 |

**修改位置**：阶段一（1.1节）

### 4. 新增数据校验规则（阶段零/阶段一之间）

**新增步骤 0.5：数据校验**

在完成 iFind 数据获取后，增加以下校验逻辑：

```
IF 任意必需指标返回为空:
   → 记录缺失字段，标记 WARNING
   → 使用行业均值填充（参考 scoring_rubric 中的行业平均）

IF 历史数据年份 < 6年:
   → 从可用年份开始，降低预测年限（每少1年多预测1年）

IF 季度数据累计值差分后出现负值:
   → 检查 iFind 数据口径（可能不是累计值）
   → 记录警告，标注异常季度
```

**修改位置**：阶段一末尾（1.4节后）

### 5. Excel 结构优化：新增「数据来源」列

**现状**：`模型假设` Sheet 的 G 列为「说明/来源」，但未强制标注每个假设的数据来源。

**优化**：在 `模型假设` Sheet 的 H 列新增「数据来源」列，强制标注格式：
```
来源格式：[来源类型] 具体说明
  如：[iFind] 2020-2024 历史均值
       [一致预期] FY1E/West 预测值
       [行业] 申万行业均值
       [Research] 研报数据
       [插值] 线性外推
```

**修改位置**：`excel_template_structure.md` Sheet 2 部分

### 6. 季度数据处理强化

**现状**：季度差分逻辑写在 `quarterly_model.md` 但实际依赖 LLM 理解执行。

**优化**：
1. 在 `quarterly_model.md` 中提供可直接复用的 Python 代码片段
2. 新增对港股/H股公司半年报-only情况的降级处理（只有 H1 和年报可用）
3. 在 SKILL.md 中明确标注季度数据缺失时的处理方式

### 7. 三张表校验公式显性化

**现状**：阶段六（6.2节）提到用 `scripts/recalc.py` 检查 `#REF!` 等错误，但三张表自身的校验逻辑不够显式。

**优化**：在 `excel_template_structure.md` 中，为每个 Sheet 添加**校验行**（hidden row 或可见行）：

| Sheet | 校验公式 |
|-------|---------|
| 利润表 | Σ(历史4年)归母净利 + Σ(预测5年)归母净利 → 与现金流量表「净利润」合计比对 |
| 资产负债表 | `资产总计 = 负债合计 + 股东权益合计`（第29行已有），强化标注 |
| 现金流量表 | `期末货币资金` → 链接到资产负债表货币资金行（双向校验） |

### 8. 新增执行摘要自动化

**现状**：摘要 Sheet 依赖 LLM 手动填写所有内容。

**优化**：在 `SKILL.md` 阶段六中，要求 LLM 先调用一个伪代码/结构化输出模板，生成「摘要填充指令清单」，再按清单填充摘要 Sheet，确保无遗漏字段。

---

## 关键文件修改清单

| 文件 | 修改类型 | 主要内容 |
|------|---------|---------|
| `SKILL.md` | 大幅修改 | 路径修复、并行化标注、数据校验步骤、摘要自动化模板 |
| `references/excel_template_structure.md` | 中等修改 | 数据来源列、三张表校验行标注 |
| `references/quarterly_model.md` | 中等修改 | Python 差分代码片段、港股降级处理 |
| `references/scoring_rubric.md` | 小幅修改 | 行业均值填充规则说明 |
| `scripts/recalc.py` | 同步 | 确保复制到 plugin cache 版本 |

---

## 执行顺序

1. **Phase 1**：修复 SKILL.md 中的 `/mnt/Research/` → `~/Research/`
2. **Phase 2**：新增数据校验步骤（阶段0.5）
3. **Phase 3**：标注并行化机会，重构阶段一结构
4. **Phase 4**：更新 excel_template_structure.md（来源列、校验行）
5. **Phase 5**：强化 quarterly_model.md（Python 代码片段 + 港股处理）
6. **Phase 6**：新增执行摘要自动化模板
7. **Phase 7**：同步 recalc.py 到所有版本
8. **Phase 8**：重新打包 `.skill` 文件

---

## 验证方式

1. 用一个测试公司（如「宁德时代 300750」）实际执行一次完整流程
2. 验证 `/mnt/Research/` 路径错误已修复
3. 确认三张表资产负债表平衡（资产 = 负债 + 权益）
4. 确认季度加总 = 年度对应数字
5. 确认无 `#REF!`/`#DIV/0!` 错误（recalc.py 输出 clean）
6. 确认所有假设都有数据来源标注
