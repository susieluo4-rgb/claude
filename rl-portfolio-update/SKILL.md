---
name: rl-portfolio-update
description: 组合持仓 + 净值自动同步 — 从数据源同步持仓和净值数据到本地 Wiki Markdown，支持 CIF / 润铭 两个组合
metadata:
  version: 2.0
  type: portfolio-maintenance
  input: --cif / --runming / --nav / --all
  output: 更新 CIF.md / 润铭.md / CIF_组合视图.md / 润铭_组合视图.md
---

# rl-portfolio-update — 组合持仓 + 净值自动同步

> 从数据源同步持仓数据和每日净值到本地 Wiki，支持多组合（CIF / 润铭）。

## 触发词

"更新持仓"、"同步组合"、"sync portfolio"、"更新净值"、"更新权重"

## 组件

| 组件 | 状态 | 数据源 | 目标文件 |
|------|------|--------|---------|
| CIF 持仓同步 | ✅ 完成 | Sunny Outlook → HFHC Sheet | CIF.md + CIF_组合视图.md |
| 润铭持仓同步 | ✅ 完成 | ZeJun Outlook → 润铭portfolio xlsx | 润铭.md + 润铭_组合视图.md |
| 净值拉取（润铭） | ✅ 完成 | ZeJun Outlook → 绝对收益净值表 xlsx | 润铭_组合视图.md（净值序列） |
| 净值拉取（CIF） | ✅ 完成 | Hereford Funds 官网 | CIF_组合视图.md（净值序列） |

### 净值数据源详情

| 组合 | 来源 | 方式 | 说明 |
|------|------|------|------|
| **润铭NAV** | Ma ZeJun <zejun.ma@binyuancapital.com> | Outlook 下载 xlsx 附件 | 绝对收益净值表 YYYYMMDD.xlsx → Sheet"净值" C列 |
| **CIF NAV** | https://herefordfunds.com/funds/bin-yuan-china-innovation-fund | 网页抓取 | FI USD share class NAV |

## 用法

```bash
# 统一入口
python3 scripts/portfolio_update.py --cif              # 仅更新 CIF 持仓
python3 scripts/portfolio_update.py --runming          # 仅更新润铭持仓
python3 scripts/portfolio_update.py --nav              # 更新两个组合的净值
python3 scripts/portfolio_update.py --all              # 更新全部（持仓+净值）

# 预览模式
python3 scripts/portfolio_update.py --cif --dry-run    # 预览 CIF 变更

# 净值回填（首次使用，拉取全量历史）
python3 scripts/portfolio_update.py --backfill-nav runming  # 回填润铭全量历史净值

# 直接调用净值脚本
python3 scripts/fetch_nav.py [runming|cif|both]        # 仅净值（增量）
python3 scripts/fetch_nav.py --backfill runming        # 仅净值（全量回填）
```

## 定时建议

| 任务 | 建议时间 | 说明 |
|------|---------|------|
| 持仓同步 | 工作日 10:00 | Sunny 通常在 9-10am 发送 Portfolio H 邮件 |
| 净值拉取 | 每日 15:00 | 收市后净值更新 |

## 文件结构

```
rl-portfolio-update/
├── SKILL.md
└── scripts/
    ├── portfolio_update.py       # 统一入口编排层
    ├── cif_update.py             # CIF 持仓同步（轻量包装）
    ├── runming_update.py         # 润铭持仓同步（完整实现）
    └── fetch_nav.py              # 净值拉取（润铭 Outlook xlsx + CIF 网页）
```

## 延伸阅读

- CIF 同步完整脚本：`~/.claude/skills/rl-portfolio-monitor/scripts/cif_portfolio_sync.py`
- Ticker 映射：`~/.claude/skills/rl-portfolio-monitor/cif_name_ticker_map.json`
- 净值对比 HTML 报告：`rl-portfolio-benchmark` skill
