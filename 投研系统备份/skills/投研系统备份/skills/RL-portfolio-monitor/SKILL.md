---
name: RL-portfolio-monitor
description: 持仓监控告警编排层。当用户说"持仓监控"、"我的持仓告警"、"扫描持仓"时使用。核心功能：加载 Obsidian 持仓配置 → 并发查询 ifind API → 独立判断 7 类告警 → 写入 SQLite → 推送飞书。
metadata:
    version: 1.0
    type: portfolio-monitoring
    data_source: ifind API (via call-node.js)
    push_target: 飞书 (OpenClaw)
---

# RL-Portfolio-Monitor — 持仓监控

## 架构

```
持仓配置 (Obsidian frontmatter)
     ↓
portfolio_monitor.py   ← 主编排脚本（Python）
  ├─ portfolio_loader.py   ← 加载持仓配置
  ├─ alert_history.py      ← SQLite 持久化
  ├─ feishu_formatter.py   ← 飞书消息格式
  └─ call_ifind_api()      ← 通过 call-node.js 调用 ifind API
                                (不依赖 Claude Code MCP，
                                  直接 HTTP 请求 ifind)
     ↓
飞书推送 (OpenClaw)
```

## 持仓配置

持仓配置存放于 Obsidian vault：

```
~/Research/Vault_基金经理Agent/润铭.md
```

配置格式为 markdown 表格（第一列 Ticker=股票代码，第二列 Name=公司简称，第三列 润铭=组合占比 %）：

**配置示例**（直接使用现有的润铭.md 表格格式，无需改动）：

```markdown
| Ticker | Name | 润铭 |
| ------- | ------- | ------ |
| 300454.SZ | 深信服 | 6.20% |
| 688239.SH | 航宇科技 | 4.86% |
| 688981.SH | 中芯国际 | 0.45% |
```

告警阈值采用默认配置（见下方告警类型说明），如需自定义可修改 `portfolio_loader.py` 中的 `_default_alerts()`。

---

## 使用方式

### 主动查询

**全量扫描**（所有持仓）：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py scan
```

**单标的扫描**：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py scan 300750
```

**告警历史查询**：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py history
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py history --days 7
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py history --stock 300750
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py history --type PRICE_DROP --days 30
```

**今日汇总**（手动触发）：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py summary
```

**测试模式**（仅扫描不入库不推送）：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py scan --no-push
```

### 定时任务

**每小时轮询**（交易时段 9:30-15:00）：
```
/portfolio-monitor loop 60m
```
设置后每小时的交易时段内自动执行，发现告警立即推送飞书。

**日度汇总定时**：
每日 08:30 自动推送前一日告警汇总，使用 `/loop 60m` 定时任务 + `summary` 子命令实现。

---

## 告警类型

| 类型 | 数据源 API | 触发条件 |
|------|-----------|---------|
| `PRICE_DROP` | get_stock_performance | 跌幅 > 阈值 % |
| `PRICE_RISE` | get_stock_performance | 涨幅 > 阈值 % |
| `VOLUME_SPIKE` | get_stock_performance | 成交量 > 平日 X 倍 |
| `NEGATIVE_NEWS` | search_news | 命中负面关键词（监管/处罚/诉讼/减持等）|
| `ESG_DOWNGRADE` | get_esg_data | ESG 评级下降 |
| `ANALYST_DOWNGRADE` | get_stock_events | 券商下调评级事件 |
| `LARGE_SHAREHOLDER_REDUCE` | get_stock_shareholders | 大股东减持 |

**每类告警独立判断，互不组合。同类型告警当日不重复推送。**

---

## 告警负面关键词

`NEGATIVE_NEWS` 类型使用以下关键词判断：
```
违规、处罚、监管函、警示函、立案、调查、造假、欺诈、诉讼、仲裁、
减持、业绩亏损、下滑、不及预期、风险警示、ST、退市
```

---

## 数据文件

| 文件 | 说明 |
|------|------|
| `~/.claude/skills/RL-portfolio-monitor/alert_history.db` | SQLite 告警历史数据库 |
| `~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py` | 主脚本 |
| `~/.claude/skills/RL-portfolio-monitor/portfolio_loader.py` | 持仓配置加载器 |
| `~/.claude/skills/RL-portfolio-monitor/alert_history.py` | 告警历史读写 |
| `~/.claude/skills/RL-portfolio-monitor/feishu_formatter.py` | 飞书消息格式化 |

---

## 飞书推送配置

使用 OpenClaw，session 绑定飞书 channel：
- session-id: `782328a8-8c4c-4be3-b18c-57ad4ad0ae89`
- reply-to: `ou_aae8836476a244334c897fb11b9efd1a`

推送由 `portfolio_monitor.py` 内部通过 `openclaw agent` 命令调用，无需额外配置。
