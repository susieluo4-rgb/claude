---
name: RL-投研团队进度分析
description: 扫描投研Vault，生成投研团队整体进度报告。输出Markdown总览表 + 交互式HTML可视化页面，包含公司覆盖度、Agent产出统计、财务模型清单、本周活跃度等量化数据。
metadata:
  version: "1.0"
  last_updated: "2026-04-11"
---

# RL-投研团队进度分析 Skill v1.0

扫描 `Vault_公司基本面Agent` 目录，统计所有公司的研究进度，生成量化报告。

## 触发关键词

- "投研进度"
- "团队进度"
- "进度分析"
- "RL进度"
- "覆盖情况"
- "研究统计"

## 工作目录

从任意目录触发均可，Vault 路径固定。

## 执行流程

### Step 1: 扫描公司目录

扫描以下路径：
```
/Users/zhuang225/Research/Vault_公司基本面Agent/
```

需要分析的目录：
- `11_公司列表/` — 所有监控公司（含空目录）
- `01_公司研究/` — 已完成的 Level 1 研究报告
- `02_行业研究/` — 行业研究报告
- `04_日志/` — 每日研究日志

### Step 2: 运行分析脚本

```bash
cd /Users/zhuang225/Research/Vault_公司基本面Agent

python3 << 'PYEOF'
import os, re, json, subprocess

vault = "11_公司列表"
company_dirs = []

for root, dirs, files in os.walk(vault):
    basename = os.path.basename(root)
    if '_' in basename:
        parts = basename.split('_')
        if len(parts) >= 2 and len(parts[1]) > 0:
            company_dirs.append(root)

results = []
for cdir in company_dirs:
    r = subprocess.run(['find', cdir, '-type', 'f'], capture_output=True, text=True)
    files = [f.strip() for f in r.stdout.strip().split('\n') if f.strip()]
    total_files = len(files)

    if total_files == 0:
        continue

    md_files = [f for f in files if f.endswith('.md')]
    pdf_files = [f for f in files if f.endswith('.pdf')]
    docx_files = [f for f in files if f.endswith('.docx')]
    xlsx_files = [f for f in files if f.endswith(('.xlsx', '.xls'))]

    has_company_md = any('公司_' in os.path.basename(f) for f in md_files)
    has_alphapai = any('alphapai' in f for f in files)
    has_announcement = any('公告' in f.lower() for f in files)
    has_jiyao = any('纪要' in f.lower() for f in files) or any('纪要对比' in os.path.dirname(f) for f in files)
    has_model = len(xlsx_files) > 0

    dates = []
    for f in files:
        bname = os.path.basename(f)
        m = re.search(r'(20\d{2})[-_]?(\d{2})[-_]?(\d{2})', bname)
        if m:
            dates.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
        else:
            m = re.search(r'(20\d{2})[-_]?(\d{2})', bname)
            if m:
                dates.append(f"{m.group(1)}-{m.group(2)}")

    latest = max(dates) if dates else '未知'

    basename = os.path.basename(cdir)
    parts = basename.split('_')
    comp_name = parts[0]
    code = parts[1] if len(parts) > 1 else '?'

    alphapai_count = len([f for f in files if 'alphapai' in f])

    results.append({
        'name': comp_name,
        'code': code,
        'total': total_files,
        'md': len(md_files),
        'pdf': len(pdf_files),
        'docx': len(docx_files),
        'xlsx': len(xlsx_files),
        'latest': latest,
        'alphapai': alphapai_count,
        'has_model': has_model,
        'has_company_md': has_company_md,
        'has_jiyao': has_jiyao,
        'has_announcement': has_announcement,
    })

results.sort(key=lambda x: x['total'], reverse=True)
print(json.dumps(results, ensure_ascii=False))
PYEOF
```

### Step 3: 检查 01_公司研究/ 独立报告

```bash
ls -la "/Users/zhuang225/Research/Vault_公司基本面Agent/01_公司研究/" 2>/dev/null
```

对比 `01_公司研究/` 中的报告与 `11_公司列表/` 中的公司，找出：
- 有报告但无监控目录的公司
- 有报告但监控目录为空的公司

### Step 4: 生成 Markdown 报告

输出到：
- `/Users/zhuang225/LLM播客/research/投研系统进度报告.md`

报告结构：
1. KPI 总览卡片
2. 全部公司进度总表（按深度分 Tier 1-4）
3. 仅完成 Level 1 报告的公司列表
4. Agent 产出汇总
5. 本周活跃更新

### Step 5: 生成 HTML 报告

输出到：
- `/Users/zhuang225/LLM播客/research/投研系统进度报告.html`

HTML 要求：
- Apple 风格简洁设计
- KPI 卡片行
- 可滚动表格（overflow-x: auto）
- 彩色标签区分内容类型（模型/α派/纪要/报告/PDF/公告）
- Tier 分隔行（绿/橙/紫/灰）
- 本周活跃公司高亮
- Agent 产出卡片网格
- 响应式布局

### Step 6: 打开报告

```bash
open "/Users/zhuang225/LLM播客/research/投研系统进度报告.html"
```

## 统计口径

### Tier 分级

| Tier | 文件数 | 说明 |
|------|--------|------|
| Tier 1 | 10+ | 深度研究（含模型/多源数据） |
| Tier 2 | 5-9 | 中度研究（有模型或研报） |
| Tier 3 | 2-4 | 初步研究（少量文件） |
| Tier 4 | 1 | 单文件（仅公告或单篇研究） |

### 内容标签

| 标签 | 判定条件 |
|------|----------|
| 财务模型 | 目录下有 .xlsx/.xls 文件 |
| α派研报 | 存在 alphapai 子目录及文件 |
| 纪要对比 | 文件名或路径含"纪要" |
| Level1报告 | 存在 `公司_*.md` 文件 |
| 公告监控 | 存在"公告"相关文件 |
| PDF/DOCX | 对应格式文件数量 |

### "完整投研"定义

同时满足以下至少 2 项：
1. 有 Level 1 公司研究报告（`公司_*.md` 或 `01_公司研究/` 中有对应文件）
2. 有财务模型（Excel 文件）
3. 有 α派研报（≥2 篇）
4. 有纪要对比分析

## 输出路径

| 文件 | 路径 |
|------|------|
| Markdown 报告 | `/Users/zhuang225/LLM播客/research/投研系统进度报告.md` |
| HTML 报告 | `/Users/zhuang225/LLM播客/research/投研系统进度报告.html` |
