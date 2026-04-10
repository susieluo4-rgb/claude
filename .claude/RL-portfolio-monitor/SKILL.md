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

**HTML 报告**（扫描后生成可浏览器打开的 HTML 文件）：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py scan --html
# 报告路径：~/.claude/skills/RL-portfolio-monitor/reports/portfolio_report_YYYY-MM-DD.html
```

### 交互式服务（带刷新按钮）

**启动本地 HTTP 服务**：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py --serve
```
默认端口 8765，访问 `http://127.0.0.1:8765` 打开交互式页面。

**自定义端口**：
```
python3 ~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py --serve --port 9000
```

页面上有三个按钮：
- **📈 股价刷新**：仅刷新涨跌幅数据（快，3-5 分钟）
- **🔔 预警刷新**：全量扫描所有告警类型（慢，10-15 分钟）
- **📋 公告刷新**：扫描所有持仓近48h公告并做情感分析（中，5-8 分钟）

交互页面表格新增"最新公告"列，显示情感标签 badge（+++ / ++ / = / -- / ---），点击按钮可独立刷新。

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
| `~/.claude/skills/RL-portfolio-monitor/reports/` | HTML 报告输出目录 |
| `~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py` | 主脚本 |
| `~/.claude/skills/RL-portfolio-monitor/portfolio_server.py` | 交互式 HTTP 服务器 |
| `~/.claude/skills/RL-portfolio-monitor/portfolio_loader.py` | 持仓配置加载器 |
| `~/.claude/skills/RL-portfolio-monitor/alert_history.py` | 告警历史读写 |
| `~/.claude/skills/RL-portfolio-monitor/feishu_formatter.py` | 飞书消息格式化 |

---

## ifind API 注意事项

### 涨跌幅 query 必须用"今日"

`get_stock_performance` 的 query 参数中：
- **正确**：`"{code} 今日涨跌幅、最新价"` → 返回最新交易日数据（交易日期=最新）
- **错误**：`"{code} 昨日涨跌幅、收盘价"` → 返回前一交易日数据（交易日期=前一交易日）

API 文档中标注"交易日期：前一交易日"表示取最近一个已完成的交易日。在非交易时段或盘前，"最新"和"昨日"可能等价；但在交易时段，"最新"才是盘中实时数据。

解析多行返回结果时，API 按日期**倒序**返回（最新日期在第一行），取 `data_rows[0]` 即可。

---

## Token 配置

ifind API Token 存放在 `~/Research/ifind mcp&skill/mcp_config.json`。

**已配置多 Token 自动轮换**（`call-node.js` 内置重试机制）：
- Token 0：主账号（首次触发限速后自动切换到备用）
- Token 1：备用账号（用户提供的第二个账号）

格式为 `auth_tokens` 数组：
```json
{
  "auth_tokens": ["<token0>", "<token1>"]
}
```

当某个 Token 返回 `"用户使用工具已超限"` 时，`call-node.js` 自动尝试下一个 Token，无需手动切换。
如需新增 Token，在 `mcp_config.json` 的 `auth_tokens` 数组中添加即可。

---

## 飞书推送配置

使用 OpenClaw，session 绑定飞书 channel：
- session-id: `782328a8-8c4c-4be3-b18c-57ad4ad0ae89`
- reply-to: `ou_aae8836476a244334c897fb11b9efd1a`

推送由 `portfolio_monitor.py` 内部通过 `openclaw agent` 命令调用，无需额外配置。
