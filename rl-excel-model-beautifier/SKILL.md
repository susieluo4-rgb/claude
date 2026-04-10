---
name: rl-excel-model-beautifier
description: 将基础财务模型 Excel 转换为专业投行风格的格式化文档。自动识别增速/利润率/金额等数据类型并应用对应配色，高亮分析师手动输入区，统一表头样式和 Sheet 标签。支持独立工具和 build 脚本集成两种模式。
trigger: "美化模型", "beautify model", "format the Excel", "美化这个Excel", "apply styling", "模型美化", "style the model", "professional formatting", "优化Excel格式"
---

# Excel 财务模型美化器

## 概述

将功能完整但样式简陋的财务研究 Excel 模型，一键转换为专业投行风格的格式化文档。

**核心保证：**
- 只改格式（font/fill/alignment/border/number_format），**绝不修改任何 cell.value**
- 所有公式完整保留
- 幂等安全（多次运行结果一致）
- 通用（支持任意符合标准 Sheet 结构的模型）

---

## 适用文件

投研系统生成的标准财务模型（通常包含以下 Sheet）：
- `摘要` / `业务拆分` / `模型假设` / `利润表` / `资产负债表` / `现金流量表` / `基本面研究` / `估值分析`

列结构：A列为标签列，B-L列为年份（2020A-2025A 历史 + 2026E-2030E 预测）

---

## 配色方案

### 表头与标题

| 元素 | 颜色 | 说明 |
|------|------|------|
| 大标题行背景 | `#1F3864` 深蓝 | 公司名+代码 行，14px 白粗体 |
| 历史期表头 | `#2E75B6` 表头蓝 | 2020A-2025A |
| 预测期表头 | `#375623` 深绿 | 2026E-2030E |
| 表头文字 | `#FFFFFF` 白色 | 10px Bold |

### 数据字体颜色

| 数据类型 | 颜色 | 数字格式 | 检测关键词 |
|----------|------|----------|-----------|
| **增速/增长率** | `#CC0000` 红色 | `0.0%` | `增速` `增长率` `YoY` `QoQ` `同比` `环比` |
| **利润率** | `#0070C0` 蓝色 | `0.0%` | `毛利率` `净利率` `营业利润率` `EBITDA率` |
| 跨表引用 | `#008000` 绿色 | 按原格式 | 以 `=` 开头的公式 |
| 金额/普通 | `#000000` 黑色 | `#,##0.0` | 默认 |
| EPS/单价 | `#000000` 黑色 | `0.00` | 标签含 `EPS` 或 `股价` |

### 单元格背景

| 类型 | 背景色 | 适用范围 |
|------|--------|---------|
| **分析师手动输入** | `#FFF2CC` 浅黄 | 模型假设（全部）+ 业务拆分（预测期增速/毛利率） |
| 偶数行交替 | `#F2F2F2` 浅灰 | 数据区偶数行 |
| 公式行 | `#EAF2E8` 浅绿 | 含公式的整行（可选） |

### Sheet 标签颜色

| Sheet | 颜色 | 说明 |
|-------|------|------|
| 摘要 | `#4472C4` 蓝 | 概览 |
| 业务拆分 | `#70AD47` 绿 | 核心假设输入 |
| 模型假设 | `#FFC000` 琥珀 | 参数配置 |
| 利润表/资产负债表/现金流量表 | `#4472C4` 蓝 | 三表 |
| 基本面研究 | `#BF8F00` 金 | 质量评分 |
| 估值分析 | `#C00000` 红 | 估值 |

---

## 手动输入区判定规则

**模型假设 Sheet：**
- 所有**非公式**数据单元格 → 黄色背景
- 公式单元格（以 `=` 开头，通常是跨表引用）→ 保持绿色字体，不标黄
- 分节标题行（`▌A. 收入假设` 等）→ 不标黄

**业务拆分 Sheet：**
- 预测列（2026E+）中，行标签含 `增速` 或 `毛利率` 的单元格 → 黄色背景
- 历史数据列 → 不标黄
- 公式联动的收入/毛利额 → 不标黄

---

## 使用方式

### 方式 1：独立工具（对已有文件运行）

```bash
python3 /path/to/beautify_model.py "敏实集团_财务模型.xlsx"
# 输出: 敏实集团_财务模型_beautified.xlsx
```

或在 Python 中调用：

```python
from openpyxl import load_workbook
import sys
sys.path.insert(0, '/Users/zhuang225/.claude/skills/rl-excel-model-beautifier/scripts')
from beautify_model import beautify_financial_model

wb = load_workbook('敏实集团_财务模型.xlsx')
beautify_financial_model(wb, company_name='敏实集团', verbose=True)
wb.save('敏实集团_财务模型_beautified.xlsx')
```

### 方式 2：集成到 build 脚本

在 build_minshi_model.py 的 `wb.save()` 之前添加：

```python
sys.path.insert(0, '/Users/zhuang225/.claude/skills/rl-excel-model-beautifier/scripts')
from beautify_model import beautify_financial_model

beautify_financial_model(wb, company_name='敏实集团', verbose=False)
wb.save(output_path)
```

---

## 处理流程（6 Pass）

```
Pass 1  ── 表头识别      扫描含年份(20XXA/E)的行，美化标题和表头
Pass 2  ── 列宽优化      A列26px，数据列13px，特殊Sheet自定义
Pass 3  ── 类型格式化    检测增速/利润率/金额，应用对应颜色+格式
Pass 4  ── 手动输入高亮  业务拆分+模型假设的可改参数标黄
Pass 5  ── Sheet标签     按类型着色
Pass 6  ── 边框+冻结     全框thin border，冻结表头行+B列
```

---

## 依赖

- Python 3.8+
- `openpyxl` (`pip install openpyxl`)

无其他第三方依赖。

---

## 边缘情况

| 场景 | 处理方式 |
|------|---------|
| 缺少某些标准 Sheet | 跳过缺失的 Sheet，不报错 |
| 没有数据单元格 | 跳过该 Sheet，不报错 |
| 已美化过（重复运行） | 幂等安全，单元格内容完全一致 |
| 年份标签格式异常 | 回退到正则扫描 `\d{4}[AE]` |
| 合并单元格 | 只格式化左上角单元格 |
| 超大模型（500+行） | 仍 <3 秒完成 |
| 公式单元格在增速/利润率行 | 保留公式值，应用对应 `number_format`（如 `0.0%`），确保百分比公式正确显示 |
