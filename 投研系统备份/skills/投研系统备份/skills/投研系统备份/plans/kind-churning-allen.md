# Plan: A股财务模型自动生成系统

## Context

用户已有一张精心构建的宁德时代财务模型（8个Sheet，三表联动，业务拆分驱动，DCF估值），
希望将其固化为可复用的模版，实现「说一个公司名 → 自动生成完整财务模型」。

当前环境已具备：
- ifind MCP（历史财务数据 + 分析师共识预测）
- 25+ 家公司文件夹（`~/Documents/Research/{公司}_{股票代码}/`）
- CATL模型完整公式体系（可作为代码模版提取）
- Python + openpyxl 环境

---

## 总体架构

```
用户输入（公司名/股票代码）
        ↓
Claude 技能（SKILL.md）
  ① search_stocks → 确认股票代码
  ② get_stock_financials → 历史三表数据（6年）
  ③ get_stock_financials → 分析师共识预测（FY1-FY3）
  ④ get_stock_info + get_stock_summary → 公司简介
  ⑤ search_notice → 年报中业务分部信息
  ⑥ get_risk_indicators → Beta等风险指标
        ↓
  调用 Python 生成器（financial_model_generator.py）
        ↓
输出 Excel 模型（~/Documents/Research/{公司}_{代码}/{公司}_Financial_Model_{代码}.xlsx）
```

---

## 组件一：Python 生成器脚本

**路径：** `~/Documents/Research/financial_model_generator.py`

### 函数签名

```python
def generate_financial_model(
    stock_code: str,          # e.g. "300750"
    company_name: str,        # e.g. "宁德时代"
    output_dir: str,          # e.g. "~/Documents/Research/宁德时代_300750/"
    hist_data: dict,          # 历史财务数据（年份→指标字典）
    forecast_data: dict,      # ifind共识预测（FY1-FY3）
    segments: list[dict],     # 业务分部列表（名称+历史收入+历史毛利率）
    dcf_params: dict,         # Beta, WACC参数
) -> str:                     # 返回文件路径
```

### 生成的8个Sheet结构（完全沿用CATL模型）

| Sheet | 内容 | 关键变化 |
|-------|------|---------|
| 摘要 | 公司简介 + 关键指标速览 | 动态填入公司信息 |
| 模型假设 | 蓝色输入区 + 黄色公式区 | 营收增速/毛利率引用业务拆分 |
| 利润表 | 历史6年 + 预测4年（到2029E） | 公式驱动 |
| 资产负债表 | 同上 | 公式驱动，Cash为配平plug |
| 现金流量表 | 同上 | 经营/投资/筹资CF联动 |
| 业务拆分 | 各业务增速+毛利率输入区 → 汇总 | 段数量动态（支持2-6个分部） |
| DCF估值 | WACC参数 + FCFF折现 + 敏感性分析 | Beta从ifind获取 |
| 可比公司 | 留白模版（用户手填或后续完善） | 暂为静态模版 |

### 核心设计原则

1. **动态分部数量**：`segments` 列表驱动业务拆分页，支持2-6个业务分部
2. **公式不变**：所有Excel公式结构与CATL完全一致，只是数据不同
3. **历史年份自动对齐**：有几年数据填几年，不足处留白
4. **预测列规则**：
   - FY1-FY3：直接用 ifind 共识校准增速
   - FY4（2029E）：按 FY3 增速 × 0.75 递减外推

---

## 组件二：Claude 技能文件

**路径：** `~/.openclaw/skills/a-share-model/SKILL.md`

### 触发条件（用户说以下任意一种）
- "帮我建 XX 公司的财务模型"
- "给 XX 做一张三表模型"
- "XX 公司建模"
- `/model XX`

### SKILL.md 执行流程

```
Step 1: 解析公司名 → search_stocks 确认股票代码和全名
Step 2: get_stock_financials 获取历史数据（2019-2025A，6年）
        指标: 营收, 营业成本, 毛利率, 营业利润, 净利润, 归母净利润, EPS,
              货币资金, 应收账款, 存货, 固定资产, 总资产,
              应付账款, 短期借款, 长期借款, 总负债, 归母权益,
              经营现金流, 资本开支
Step 3: get_stock_financials 获取分析师共识预测（FY1-FY3）
        指标: 预测营收(FY1/FY2/FY3), 预测归母净利润, 预测EPS,
              预测营业利润, 预测EBITDA
Step 4: get_stock_info + get_stock_summary 获取公司描述/主营业务
Step 5: search_notice 搜索最新年报，提取业务分部收入数据
        （关键词: 主营业务构成 / 分部信息 / 业务板块）
Step 6: get_risk_indicators 获取 Beta 值
Step 7: 整理数据 → 调用 Python 生成器
Step 8: 创建文件夹 ~/Documents/Research/{公司}_{代码}/ 并保存模型
Step 9: 输出摘要：文件路径 + 关键假设总览 + ifind对比验证
```

---

## 数据映射细节

### 历史三表从 ifind 获取

```python
# get_stock_financials 查询示例
query = f"{company_name}{stock_code} 2019-2025年 营业收入 营业成本 归母净利润 EPS
          资产负债率 货币资金 应收账款 存货 固定资产 总资产
          应付账款 短期借款 长期借款 归母权益
          经营活动现金流 资本开支"
```

### 分析师共识

```python
# 直接从 get_stock_financials 获取 FY1/FY2/FY3 预测字段
# 用于计算各年默认增速假设
```

### 业务分部处理逻辑

```
① search_notice 找年报 → 搜索"主营业务构成"表格
② 如找到：解析分部名称 + 收入 + 毛利率（近2年）
③ 如未找到：使用2个默认分部（主营业务 + 其他），手动填入
④ 最多6个分部（超出合并为"其他"）
```

---

## 文件夹结构

```
~/Documents/Research/
├── financial_model_generator.py      ← 核心生成器（新建）
├── 宁德时代_300750/
│   └── CATL_Financial_Model_300750.xlsx   ← 已有
├── 贵州茅台_600519/                   ← 新建示例
│   └── 贵州茅台_Financial_Model_600519.xlsx
└── ...
```

---

## 关键技术细节

### 动态业务分部适配

CATL有4个分部（动力/储能/材料/其他），其他公司可能有2-6个。
生成器根据 `segments` 长度动态计算行偏移：

```python
BASE_ROW = 19  # 第一个分部起始行
ROWS_PER_SEGMENT = 6  # 每个分部占6行
seg_start = BASE_ROW + idx * ROWS_PER_SEGMENT
```

总计行（合计区）= `BASE_ROW + len(segments) * ROWS_PER_SEGMENT + 2`

### ifind数据对齐

```python
# FY1通常对应当前年份+1，从时间点反推
import datetime
current_year = datetime.date.today().year
fy1_year = current_year  # 如3月份当前年报还未发 → FY1=当年
```

### WACC 自动计算

```python
# 从 get_risk_indicators 获取 Beta
# Rf = 2.3%（中国10年国债，可配置）
# ERP = 6.0%（A股）
# 债务占比 = 25%（默认，可从BS计算实际比例）
wacc = rf + beta * erp  # 纯权益计算作为第一步，后续加权
```

---

## 落地步骤

1. **Step 1**（核心工作）：基于 /tmp/rebuild_catl*.py 提取通用化生成器
   → 创建 `financial_model_generator.py`

2. **Step 2**：创建 SKILL.md
   → `~/.openclaw/skills/a-share-model/SKILL.md`

3. **Step 3**：用一家新公司测试端到端（建议用茅台600519 或比亚迪002594）

4. **Step 4**：根据测试结果微调数据清洗逻辑（ifind字段格式差异）

---

## 验证方法

测试命令：`帮我建贵州茅台600519的财务模型`

验证项目：
- [ ] 文件生成在正确路径
- [ ] 8个Sheet均存在
- [ ] 历史数据与ifind一致（对比2024A关键指标）
- [ ] 模型假设中营收增速公式引用业务拆分
- [ ] 修改业务拆分增速 → 利润表收入自动变化
- [ ] DCF估值中WACC公式正确

---

## 局限性说明（用户需知）

| 项目 | 自动化程度 | 备注 |
|------|----------|------|
| 历史三表 | ✅ 全自动 | ifind质量高 |
| 分析师共识预测 | ✅ 全自动 | FY1-FY3 |
| FY4外推 | ⚠️ 自动但需审阅 | 简单递减规则 |
| 业务分部划分 | ⚠️ 半自动 | 依赖年报文字解析，复杂结构需人工确认 |
| 可比公司 | ❌ 暂不自动 | 留空模版 |
| 摘要页图表 | ❌ 暂不自动 | 保留静态模版 |
