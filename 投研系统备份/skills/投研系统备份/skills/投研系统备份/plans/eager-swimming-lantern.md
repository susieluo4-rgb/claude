# Plan: Fix Industry + QL Sections

## Context
The script currently runs at 70/76 (92%) match. The 6 mismatches are precision differences (0.071→0.07, 0.0293→0.03). The real gaps are **missing fills**: Porter Ind3-4 five forces and several QL metrics are never extracted.

## All Issues to Fix

### 1. Porter: Add bp3, bp4 blocks
`Portet Model.txt` has all 4 industries. Script only processes bp1 (Ind1) and bp2 (Ind2), missing Ind3 (光纤用四氯化锗) and Ind4 (红外系锗产品).

**Fix:** Add after the existing bp1/bp2 loop:
```python
bp3=blk(port,'云南锗业光纤用四氯化锗 竞争力分析报告',['云南锗业红外系锗产品','$$'])
bp4=blk(port,'云南锗业红外系锗产品 竞争力分析报告',['$$'])
for ind_idx,bp in [(3,bp3),(4,bp4)]:
    ...same extraction...
```

### 2. QL Visibility: Fix pattern
Current pattern `r'增长能见度评分.*?(\d+)/5分'` misses because the heading is `**增长能见度评分**` and the value is on the next line as `**评分：2/5分**`.

**Fix:** `r'\*\*评分\*\*[^\d]*(\d+)/5分'` — matches `**评分：2/5分**` directly.

### 3. QL Margin peers: Fix pattern (table format)
Peer margins are in a markdown table `| 驰宏锌锗 | 23.07 | 2023年年报 |` — no `%` after the number. Current pattern `[^*\n]*?(\d+(?:\.\d+)?)\s*%` never matches.

**Fix:** Remove `\s*%` from all 3 peer patterns:
```python
('margin_p1', r'驰宏锌锗[^*\n]*?(\d+(?:\.\d+)?)'),
('margin_p2', r'中金岭南[^*\n]*?(\d+(?:\.\d+)?)'),
('margin_p3', r'罗平锌电[^*\n]*?(\d+(?:\.\d+)?)'),
```

### 4. QL R&D personnel: Fix pattern + add computed ratio
- Current: `r'研发人员[为]?\s*(\d+)\s*人'` → pattern exists but fails because actual text is `研发人员数量为122人` (extra `数量` after `人员`). Also `[为]?` only handles single char, not `数量`.
- R&D personnel ratio (ref=0.11): not extracted at all.

**Fix:**
```python
m=re.search(r'研发人员[^\d]*?(\d+)\s*人',ql)
if m: ql_vals['rd_personnel']=float(m.group(1))
m=re.search(r'研发人员[^\d]*?\d+[^\d]*?(\d+)\s*人',ql)  # second number = total staff
if m:
    total=int(re.search(r'研发人员[^\d]*?\d+[^\d]*?(\d+)\s*人',ql).group(1))
    if ql_vals.get('rd_personnel'):
        ql_vals['rd_personnel_ratio']=round(ql_vals['rd_personnel']/total,2)
```

### 5. QL R&D ratio: Fix pattern
Current: `r'研发费用率[为]?\s*(\d+(?:\.\d+)?)\s*%'` → text is `研发费用率为5.80%` (no space before `%`). Pattern `\s*%` fails.

**Fix:** `r'研发费用率[^\d]*?(\d+(?:\.\d+)?)\s*%'`

### 6. QL Turnover peers: Fix pattern
Data is in table rows without `次` right after the number. Current pattern `驰宏锌锗[^*]*?存货周转率[^*]*?(\d+(?:\.\d+)?)\s*次` fails because there are `|` separators and the `次` is elsewhere.

**Fix:** Remove `\s*次` from all 3:
```python
('turnover_p1', r'驰宏锌锗[^*\n]*?(\d+(?:\.\d+)?)'),
('turnover_p2', r'中金岭南[^*\n]*?(\d+(?:\.\d+)?)'),
('turnover_p3', r'罗平锌电[^*\n]*?(\d+(?:\.\d+)?)'),
```

### 7. QL Leverage: Fix self + peers
- `leverage_self`: text is `资产负债率为34.60%**` — `%` is not immediately after number (there's `**`). Pattern `\s*%` fails.
- Peer leverage: in table rows with no `%` after number.

**Fix:**
```python
m=re.search(r'资产负债率[^\d]*?(\d+(?:\.\d+)?)\s*%',ql)
if m: ql_vals['leverage_self']=round(float(m.group(1))/100,4)
for lbl,pat in [
    ('leverage_p1', r'驰宏锌锗[^*\n]*?(\d+(?:\.\d+)?)'),
    ('leverage_p2', r'中金岭南[^*\n]*?(\d+(?:\.\d+)?)'),
    ('leverage_p3', r'罗平锌电[^*\n]*?(\d+(?:\.\d+)?)'),
]:
    m=re.search(pat,ql)
    if m: ql_vals[lbl]=round(float(m.group(1))/100,2)
```

### 8. QL fills: Fix duplicate `rd_ratio` key + add `rd_personnel_ratio`
```python
for qk,ep in [('rd_personnel','number of R&D personnel'),
              ('rd_personnel_ratio','R&D personnel ratio'),   # NEW
              ('rd_ratio','R&D expense ratio'),              # fixed
              ('patents','number of patents')]:
```

### 9. QL fills: Turnover vs. peers
Current pattern for turnover self: `存货周转率[）)]\s*[：:]\s*` — fails because text is `云南锗业**存货周转率**（2023年年报）： 2.05次`. Pattern `\s*[：:]\s*` needs to account for `**： 2.05次` format.

**Fix:** `r'存货周转率[^\d]*?(\d+(?:\.\d+)?)'` (remove unit constraint)

### 10. Marketing ratio: Rounding
Ref=0.03, script outputs 0.0293. Change to 2-decimal rounding:
```python
m=re.search(r'销售费用率[^\d]*?(\d+(?:\.\d+)?)\s*%',ql)
if m: ql_vals['marketing_ratio']=round(float(m.group(1))/100,2)
```

### 11. Market size float precision
Ind3 mkt_size = 459.9999999... instead of 460. Add `round()`:
```python
if m: ind_vals[(ind_idx,'mkt_size')]=round(float(m.group(1))*100)
```

## Files to Modify
- `/Users/zhuang225/Research/自动化 测试/auto_fill_score.py`

## Verification
Run `python3 auto_fill_score.py` and confirm:
1. Porter Ind3-4 Competition/Supplier/Customer/Entry Barrier/Substitution scores appear in fills
2. QL rows 139-146, 154-157, 165 show correct values
3. All Industry rows for Ind1-4 filled correctly
4. Match rate improves from 70/76
