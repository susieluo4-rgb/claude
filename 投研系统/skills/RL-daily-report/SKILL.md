---
name: RL-daily-report
description: Daily Report - 每日日报
---

# Daily Report - 每日日报

description: 生成每日市场日报，包含11个内容板块：全球重要新闻、美伊战争、全球财经新闻、隔夜美股、贵金属、全球市场、A股盘前、宏观日历、行业热点、个股关注（48家持仓）、公告速递、业绩预告。触发条件：手动触发或定时任务调用。

## 公司列表

监控以下48家重点持仓公司（来源：Portfolio.xlsx）：

| 代码 | 名称 | 市场 |
|------|------|------|
| 9992.HK | 泡泡玛特 | 港股 |
| 601127.SH | 赛力斯 | A股 |
| 3696.HK | 英矽智能 | 港股 |
| 1810.HK | 小米集团-W | 港股 |
| 3690.HK | 美团-W | 港股 |
| 0268.HK | 金蝶国际 | 港股 |
| 2556.HK | 迈富时 | 港股 |
| 3738.HK | 阜博集团 | 港股 |
| 688139.SH | 海尔生物 | A股 |
| 9660.HK | 地平线机器人-W | 港股 |
| WRD.O | 文远知行 | 美股 |
| 1357.HK | 美图公司 | 港股 |
| 688333.SH | 铂力特 | A股 |
| 688072.SH | 拓荆科技 | A股 |
| PONY.O | 小马智行 | 美股 |
| 688617.SH | 惠泰医疗 | A股 |
| 300750.SZ | 宁德时代 | A股 |
| 6160.HK | 百济神州 | 港股 |
| 002920.SZ | 德赛西威 | A股 |
| 9988.HK | 阿里巴巴-W | 港股 |
| 300832.SZ | 新产业 | A股 |
| 002594.SZ | 比亚迪 | A股 |
| 688775.SH | 影石创新 | A股 |
| 301566.SZ | 达利凯普 | A股 |
| 9896.HK | 名创优品 | 港股 |
| 0700.HK | 腾讯控股 | 港股 |
| 688289.SH | 圣湘生物 | A股 |
| 300661.SZ | 圣邦股份 | A股 |
| 300866.SZ | 安克创新 | A股 |
| 688301.SH | 奕瑞科技 | A股 |
| 301031.SZ | 中熔电气 | A股 |
| 601689.SH | 拓普集团 | A股 |
| 300760.SZ | 迈瑞医疗 | A股 |
| 002595.SZ | 豪迈科技 | A股 |
| 002050.SZ | 三花智控 | A股 |
| 601021.SH | 春秋航空 | A股 |
| 2382.HK | 舜宇光学科技 | 港股 |
| 002352.SZ | 顺丰控股 | A股 |
| 603786.SH | 科博达 | A股 |
| 300347.SZ | 泰格医药 | A股 |
| 603939.SH | 益丰药房 | A股 |
| 600750.SH | 江中药业 | A股 |
| 000338.SZ | 潍柴动力 | A股 |
| 603337.SH | 杰克股份 | A股 |
| 920522.BJ | 纳克诺尔 | 北交所 |
| 002851.SZ | 麦格米特 | A股 |
| 300452.SZ | 山河药辅 | A股 |
| 2057.HK | 中通快递 | 港股 |
| 9626.HK | 哔哩哔哩-W | 港股 |

## 工作流程

### Step 1: 获取全球重要新闻

使用 WebSearch 搜索 Reuters、AP News 获取过去24小时全球重大政治/经济/社会事件：

- **数量要求**: 至少5条
- **来源**: Reuters、AP News
- **搜索关键词**: "site:reuters.com OR site:apnews.com + 重要事件"

### Step 2: 获取美伊战争最新情况

使用 WebSearch 搜索美伊战争/中东局势最新动态：

- **来源**: Reuters、AP News
- **搜索关键词**: "Iran US war Middle East latest"

### Step 3: 获取全球财经新闻

使用 WebSearch 搜索 Bloomberg、Financial Times 获取过去24小时全球财经重大事件：

- **数量要求**: 至少5条
- **来源**: Bloomberg、Financial Times
- **搜索关键词**: "site:bloomberg.com OR site:ft.com + finance/market"

### Step 4: 获取全球市场数据

使用 curl 调用 Yahoo Finance API 获取隔夜美股数据：

```bash
# 三大指数
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=1d&interval=1d"
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range=1d&interval=1d"
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/%5EDJI?range=1d&interval=1d"

# 恐慌指数
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range=1d&interval=1d"

# 贵金属
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/GC%3AF?range=1d&interval=1d"
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/SI%3AF?range=1d&interval=1d"

# 原油
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/CL%3AF?range=1d&interval=1d"
```

### Step 5: 获取宏观日历

使用 ifind MCP `get_edb_data` 查询今日重要宏观数据发布。

### Step 6: 获取行业热点

使用 ifind MCP `search_trending_news` 查询近24小时行业热点。

### Step 7: 获取个股新闻

使用 ifind MCP `search_news` 批量查询48家公司的最新新闻：

- 时间范围：24小时
- 每家公司查询1-2条最新新闻
- **只显示有新闻的公司，无新闻则跳过**
- **每条摘要限制在100字以内**

### Step 8: 获取公告速递

使用 ifind MCP `search_notice` 批量查询48家公司的最新公告：

- 时间范围：24小时
- **必须显示具体公告内容摘要**
- 显示所有重大公告（业绩预告、分红、重组、监管问询等）
- **不做条数限制**

### Step 9: 获取业绩预告

使用 ifind MCP `get_stock_events` 查询48家公司的业绩披露日期：

- 筛选条件：业绩披露日期 = 今日或明日
- 显示内容：公司名称、代码、业绩类型、关键数据摘要
- **如无符合条件的公司，则显示"今日/明日无业绩披露"**

### Step 10: 格式化日报

按以下格式输出 Markdown（共11个板块）：

```markdown
# 📊 每日市场日报
**日期**: YYYY-MM-DD (周X)
**发布时间**: 北京时间 HH:MM

---

## 🌍 全球重要新闻
*来源: Reuters + AP News + WebSearch*

| # | 标题 | 摘要 |
|---|------|------|
| 1 | [标题] | [摘要] |
| 2 | [标题] | [摘要] |
| 3 | [标题] | [摘要] |
| 4 | [标题] | [摘要] |
| 5 | [标题] | [摘要] |

---

## ⚔️ 美伊战争最新情况
*来源: Reuters + AP News + WebSearch*

[美伊战争/中东局势最新动态]

---

## 💹 全球财经新闻
*来源: Bloomberg + Financial Times + WebSearch*

| # | 标题 | 摘要 |
|---|------|------|
| 1 | [标题] | [摘要] |
| 2 | [标题] | [摘要] |
| 3 | [标题] | [摘要] |
| 4 | [标题] | [摘要] |
| 5 | [标题] | [摘要] |

---

## 📈 隔夜美股综述
| 指数 | 收盘价 | 涨跌幅 |
|------|--------|--------|
| 标普500 | X,XXX.XX | +X.XX% |
| 纳斯达克 | X,XXX.XX | +X.XX% |
| 道琼斯 | XX,XXX.XX | -X.XX% |
| VIX恐慌指数 | XX.XX | +X.XX% |

---

## 🥇🥈 贵金属与大宗商品
| 品种 | 最新价 | 涨跌幅 |
|------|--------|--------|
| 黄金 | $X,XXX.XX/盎司 | +X.XX% |
| 白银 | $XX.XX/盎司 | -X.XX% |
| WTI原油 | $XX.XX/桶 | -X.XX% |

---

## 📊 全球市场概览
[港股ADR、日经、欧股概览]

---

## 🌅 A股盘前参考
- 沪深300期货: X,XXX.X
- 上证50期货: X,XXX.X
- 富时中国A50: X,XXX

**市场情绪**: [描述]

---

## 📅 宏观日历
| 日期 | 数据 | 市场 |
|------|------|------|
| 今日 | [重要数据] | [相关市场] |

---

## 🔥 行业热点
*来源: ifind trending_news*

- [热点主题]: [描述]

---

## 📰 个股关注 (48家)
*有新闻才显示，每条摘要100字*

| 公司 (代码) | 新闻标题 | 摘要（100字） |
|-------------|----------|---------------|
| **腾讯控股** (00700.HK) | [标题] | [100字摘要...] |
| **宁德时代** (300750.SZ) | [标题] | [100字摘要...] |

---

## 📢 公告速递 (48家)
*显示具体公告内容摘要*

| 公司 (代码) | 公告标题 | 具体内容摘要 |
|-------------|----------|---------------|
| **宁德时代** (300750.SZ) | [公告标题] | [具体内容：分红金额/业绩数据等] |
| **比亚迪** (002594.SZ) | [公告标题] | [具体内容] |

---

## 📋 业绩预告
*筛选条件: 业绩披露日期 = 今日或明日*

| 公司 (代码) | 业绩类型 | 关键数据摘要 |
|-------------|----------|---------------|
| **公司名** (代码) | 业绩预告/正式财报 | [关键数据...] |

*如无符合条件的公司，显示"今日/明日无业绩披露"*

---

**📝 市场简评**: [1-2句当日要点总结]
```

### Step 11: 发送飞书

使用 openclaw 发送日报到飞书：

```bash
openclaw agent \
  --session-id "782328a8-8c4c-4be3-b18c-57ad4ad0ae89" \
  --channel feishu \
  --reply-to "ou_aae8836476a244334c897fb11b9efd1a" \
  --deliver \
  -m "<日报内容>" \
  --json
```

### Step 12: 保存到 Obsidian

将完整日报保存到 Obsidian 研究仓库的日志目录：

- **保存路径**: `/Users/zhuang225/Research/公司研究仓库/04_日志/`
- **文件名格式**: `YYYY-MM-DD_日报.md`
- **关联公司**: 从当日有个股新闻或公告的公司中提取，填入 frontmatter

## 触发条件

- 定时任务：每天北京时间 07:00
- 手动触发：说"生成日报"或"运行日报"
