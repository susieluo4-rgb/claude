# Portfolio Monitor Skill — 实现计划

## Context

用户（基金经理）需要一个持仓监控 Skill，核心价值是**告警编排层**而非数据查询（数据查询已由 ifind MCP 覆盖）。

**设计决策（已确认）**：
1. 持仓配置存在 Obsidian vault（与研究笔记一起）
2. 不设止损价，只做常规预警
3. 每类数据源独立告警，不做多条件组合
4. 支持查询历史告警记录

---

## 架构

```
持仓配置 (Obsidian)
     ↓
┌─────────────────────────────────────────┐
│         portfolio_monitor.py            │
│  (Orchestrator: 配置加载 + 并发查询 +    │
│   独立告警判定 + 历史记录 + 飞书推送)     │
└─────────────────────────────────────────┘
     ↓
ifind MCP (数据源) → 飞书 (推送)
alert_history.json (持久化)
```

---

## 文件结构

```
~/.claude/skills/RL-portfolio-monitor/
├── SKILL.md                    # Skill 入口说明
├── portfolio_monitor.py        # 主脚本（核心编排逻辑）
├── portfolio_loader.py         # 从 Obsidian 加载持仓配置
├── alert_history.py            # 告警历史读写（SQLite）
├── feishu_formatter.py         # 飞书消息格式化
└── requirements.txt
```

**持仓配置文件位置**：`~/Documents/Research/基金经理agen- 持仓 -- 润铭/portfolio.md`
（Obsidian frontmatter 格式，放在你指定的 Research 目录下）

---

## 核心模块

### 1. 持仓配置 — Obsidian frontmatter

```yaml
---
holdings:
  - code: "300750.SZ"
    name: "宁德时代"
    cost: 185.0
    position_pct: 8.5
    alerts:
      price_drop_pct: 5      # 跌幅 >5%  告警
      price_rise_pct: 15    # 涨幅 >15% 告警
      volume_spike: 2.0      # 成交量放大超过平日 X 倍
      negative_news: true    # 负面新闻即告警
      esg_downgrade: true    # ESG 评级下调告警
      analyst_downgrade: true # 券商下调评级告警
      large_shareholder_reduce: true  # 大股东减持告警

  - code: "01801.HK"
    name: "信达生物"
    cost: 32.0
    alerts:
      price_drop_pct: 7      # 港股波动大，阈值放宽
      ...
---
```

### 2. 独立告警类型（与配置一一对应）

| 告警类型 | 数据源 | 触发条件 |
|---------|--------|---------|
| `PRICE_DROP` | `get_stock_performance` | 跌幅 > 阈值 |
| `PRICE_RISE` | `get_stock_performance` | 涨幅 > 阈值 |
| `VOLUME_SPIKE` | `get_stock_performance` | 成交量 > 平日 X 倍 |
| `NEGATIVE_NEWS` | `search_news` | 负面关键词命中 |
| `ESG_DOWNGRADE` | `get_esg_data` | ESG 评级下降 |
| `ANALYST_DOWNGRADE` | `get_stock_events` | 券商下调评级事件 |
| `LARGE_SHAREHOLDER_REDUCE` | `get_stock_shareholders` | 大股东减持变动 |

**每个类型独立判断，互不组合。满足即告警。**

### 3. 告警历史 — SQLite

```sql
CREATE TABLE alert_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT,
  name TEXT,
  alert_type TEXT,          -- PRICE_DROP / NEGATIVE_NEWS / etc.
  trigger_value REAL,       -- 实际触发值（如跌幅 -6.5%）
  threshold_value REAL,      -- 阈值（如 5%）
  headline TEXT,             -- 新闻标题 / 事件摘要
  source TEXT,               -- ifind / alphapai
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  sent_to_feishu BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_code ON alert_history(code);
CREATE INDEX idx_created ON alert_history(created_at);
CREATE INDEX idx_alert_type ON alert_history(alert_type);
```

**历史查询能力**：
- `portfolio-monitor history --days 7` — 过去7天告警汇总
- `portfolio-monitor history --stock 300750` — 单只股票告警历史
- `portfolio-monitor history --type PRICE_DROP --days 30` — 某类型历史

### 4. 飞书消息格式

**独立告警（实时推送，每条单独发）**：
```
🔔 【持仓预警】宁德时代 300750.SZ
━━━━━━━━━━━━━━━━━━━━━━━
类型：价格下跌
触发：当前价 172.3元（较昨日 -5.8%）
阈值：跌幅 > 5% 即告警
时间：2026-04-09 09:32
```

**日度汇总（每日 08:30 自动推送 + 手动 `/portfolio-monitor summary`）**：
```
📊 【持仓监控日报】2026-04-09
━━━━━━━━━━━━━━━━━━━━━━━
今日告警 5 条：
  🔴 宁德时代 — 跌幅 5.8%（PRICE_DROP）
  🟡 信达生物 — 负面新闻 1 条（NEGATIVE_NEWS）
  🟡 药明康德 — 大股东减持（LARGE_SHAREHOLDER_REDUCE）
  🟢 比亚迪 — 成交量放大 2.3 倍（VOLUME_SPIKE）
  🟢 耐世特 — 券商下调目标价（ANALYST_DOWNGRADE）
━━━━━━━━━━━━━━━━━━━━━━━
过去 7 天告警趋势：宁德时代 3次 / 信达生物 2次
```

### 5. 执行方式

| 命令 | 说明 |
|------|------|
| `/portfolio-monitor` | 全量持仓扫描，独立判断，即时推送 |
| `/portfolio-monitor 300750` | 单标的扫描 |
| `/portfolio-monitor history` | 今日告警历史 |
| `/portfolio-monitor history --days 7` | 过去7天告警 |
| `/portfolio-monitor summary` | 手动查今日告警汇总 |
| `/portfolio-monitor loop 60m` | 定时每小时执行（交易时段 9:30-15:00）|
| 日度汇总 | 每日 08:30 自动推送前一日告警汇总到飞书 |

---

## 关键文件修改/创建

| 文件 | 操作 |
|------|------|
| `~/.claude/skills/RL-portfolio-monitor/SKILL.md` | 新建 |
| `~/.claude/skills/RL-portfolio-monitor/portfolio_monitor.py` | 新建（核心）|
| `~/.claude/skills/RL-portfolio-monitor/portfolio_loader.py` | 新建 |
| `~/.claude/skills/RL-portfolio-monitor/alert_history.py` | 新建 |
| `~/.claude/skills/RL-portfolio-monitor/feishu_formatter.py` | 新建 |
| `~/Documents/Research/基金经理agen- 持仓 -- 润铭/portfolio.md` | 用户自建（配置模板由 skill 提供）|

---

## 复用现有资产

- **ifind MCP**：所有数据查询（无需额外脚本）
- **OpenClaw**：飞书推送（已有 session-id）
- **公告情感监控框架**：`RL-alphapai/scripts/daily_announcement_monitor.py` 的并发框架参考
- **Python SQLite**：`alert_history.py` 使用标准库 `sqlite3`

---

## 验证计划

1. **单元测试**：加载 Obsidian 配置，验证解析正确
2. **单标的测试**：`/portfolio-monitor 300750`，确认各类型独立告警触发
3. **飞书推送验证**：确认消息格式正确到达飞书
4. **历史查询测试**：`/portfolio-monitor history --days 7`
5. **并发安全**：多标的并发查询不触发速率限制
