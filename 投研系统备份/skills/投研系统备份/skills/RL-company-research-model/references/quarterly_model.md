# 季度模型结构参考

## 季度数据获取

### iFind 季度财务数据
使用 financial_report 接口，通过不传 reporttype 或使用宽日期范围获取全部披露期别。

```python
# 获取所有期别的利润表数据（年报+半年报+季报）
payload = {
    "codes": "300750.SZ",
    "indicators": "revenue,operprofit,netprofit,parentnetprofit,grossmargin,netmargin,eps_basic",
    "startdate": "2021-01-01",
    "enddate": "2026-03-31",
    "reporttype": ""  # 空字符串=获取所有期别
}
```

**注意**：iFinD 返回的季度数据通常是**累计值**（如Q3=前3季度累计），需要做差分还原单季度值：
- Q1 单季 = Q1累计值
- Q2 单季 = H1累计值 - Q1值
- Q3 单季 = Q3累计值 - H1值
- Q4 单季 = 年报全年值 - Q3累计值

### 差分处理代码逻辑
```python
def calc_single_quarter(df):
    """
    df: DataFrame with columns = [period, indicator]
    period格式: '2023-03-31'(Q1), '2023-06-30'(H1), '2023-09-30'(Q3), '2023-12-31'(Annual)
    """
    quarters = {}
    for year in range(2021, 2027):
        q1 = df.get(f"{year}-03-31", None)
        h1 = df.get(f"{year}-06-30", None)
        q3 = df.get(f"{year}-09-30", None)
        ann = df.get(f"{year}-12-31", None)

        quarters[f"{year}Q1"] = q1
        quarters[f"{year}Q2"] = (h1 - q1) if h1 and q1 else None
        quarters[f"{year}Q3"] = (q3 - h1) if q3 and h1 else None
        quarters[f"{year}Q4"] = (ann - q3) if ann and q3 else None

    return quarters
```

---

## 季节性分析

### 计算季节性占比
```python
# 计算近2-3年每季度的收入/利润占全年比例
def calc_seasonality(quarterly_data, annual_data, metric, years=3):
    """返回 {Q1: 0.20, Q2: 0.25, Q3: 0.27, Q4: 0.28} 格式"""
    ratios = {1: [], 2: [], 3: [], 4: []}

    for year in recent_years(years):
        annual_val = annual_data.get(year, {}).get(metric)
        if not annual_val:
            continue
        for q in [1, 2, 3, 4]:
            qval = quarterly_data.get(f"{year}Q{q}", {}).get(metric)
            if qval and annual_val:
                ratios[q].append(qval / annual_val)

    return {q: sum(v)/len(v) if v else 0.25 for q, v in ratios.items()}
```

---

## 季度预测方法

### 利润表季度预测（仅I/S）

预测方式：季节性分拆法（Seasonal Decomposition）

**第一步：确定全年预测基准**
- 来自年度利润表的 FY1E 预测值（通过公式引用）
- 主要预测项：营收、毛利润、营业利润、归母净利润

**第二步：应用季节性比例**
- 各季度预测值 = 全年预测值 × 该季度历史占比均值
- 对于新业务占比变化明显的公司，可调整季节性权重

**第三步：验证加总等于全年**
在 Excel 中：
```
=ROUND(全年预测值 × Q1占比, 1)  → Q1E
=ROUND(全年预测值 × Q2占比, 1)  → Q2E
=ROUND(全年预测值 × Q3占比, 1)  → Q3E
=年度利润表!FY1E - SUM(Q1E:Q3E)  → Q4E（保证加总吻合）
```

---

## Sheet 设计要点

### 列布局（利润表_季度）

| 列 | 内容 |
|----|------|
| A | 科目名称 |
| B-E | 2022年4个季度（2022Q1~2022Q4） |
| F-I | 2023年4个季度 |
| J-M | 2024年4个季度 |
| N-Q | 2025年4个季度（部分可能未披露） |
| R-U | 2026年4个季度预测（标注E） |

### 颜色约定
- 历史实际数据：黑色文字
- 预测数据：蓝色文字
- 计算的季节性比例：绿色

### 关键辅助行
在数据区下方添加：
- YoY（同比增速）行：`=(本期-同期)/ABS(同期)*100`
- QoQ（环比增速）行：`=(本期-上期)/ABS(上期)*100`
- 季节性占比参考行（从哪里引用全年值）

---

## 注意事项

1. **数据缺失处理**：若某季度iFinD未能返回数据（如最新季度尚未披露），用 "N/A" 填充，不影响预测部分
2. **异常季度**：若某季度因资产减值/一次性损益导致利润异常，在注释中标注，季节性计算时可剔除该异常年份
3. **港股公司**：港股公司通常只有中报和年报，季度数据不完整，此时只做2个季度预测（H1E和H2E = FY - H1E）
4. **北交所/科创板**：数据可用性与A股主板相同
