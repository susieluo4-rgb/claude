# 计划：新闻摘要工作流增强

## Context
当前工作流只显示新闻标题，没有摘要、来源、时间或影响分析。用户希望升级为：
- 每条新闻加入来源、发布时间
- 生成主要结论摘要（一句话）
- 分析对经济/上市公司的影响
- DOCX 输出格式化美化

---

## 现状问题

| 问题 | 现状 |
|------|------|
| news-api-bridge.js | mock 数据只有标题，无来源/时间/摘要 |
| Build Message 节点 | 只读取 `资讯标题` 字段 |
| DOCX 导出 | 写原始 XML，不是真正的 .docx，已损坏 |
| 输出格式 | 纯文本列表，无格式 |

---

## 改进方案（4个步骤）

### 步骤 1：扩展 news-api-bridge.js mock 数据
**文件**: `/Users/zhuang225/Desktop/news-api-bridge.js`

每条新闻添加字段：
```json
{
  "资讯标题": "...",
  "资讯来源": "Reuters",
  "发布时间": "2026-04-04 08:30",
  "摘要": "一句话结论...",
  "经济影响": "对全球通胀预期产生压制...",
  "上市公司影响": ["金融股", "银行板块", "债券ETF"]
}
```

### 步骤 2：重写 n8n Build Message 节点
**位置**: n8n 工作流 `Daily-News-Digest-Report.json` 中 `build-message` 节点

每条新闻输出格式：
```
━━━━━━━━━━━━━━━━━━━━━━
📌 标题：美联储宣布维持利率不变
📝 摘要：利率维持5.25-5.5%区间，符合市场预期，美元小幅走强
⏰ 时间：2026-04-04 08:30 | 来源：Reuters
📈 经济影响：利率不变，短期内降息预期减弱，美元指数受支撑
🏢 相关上市公司：金融股（JPM、BAC）、债券ETF（TLT）
━━━━━━━━━━━━━━━━━━━━━━
```

### 步骤 3：重写 news-export-bridge.js（DOCX 格式化）
**文件**: `/Users/zhuang225/Desktop/news-export-bridge.js`

安装 `docx` npm 包，生成真正可用的 Word 文档：
- 标题：居中大字体，加粗
- 章节标题（国际新闻 Top10 / 金融新闻 Top10）：蓝色粗体
- 每条新闻：
  - 新闻标题：加粗
  - 摘要、来源、时间：正文
  - 经济影响：斜体灰色
  - 上市公司：绿色文字

### 步骤 4：修改 n8n Save Word 节点
**文件**: `Daily-News-Digest-Report.json` 中 `save-word` 节点

当前只传 `message` 字符串，需改为传结构化数据：
```json
{
  "message": "...",
  "globalNews": [...],
  "financeNews": [...],
  "timestamp": "...",
  "format": "docx"
}
```

---

## 关键文件路径

- `~/Desktop/news-api-bridge.js` — 新闻 API bridge（需扩展字段）
- `~/Desktop/news-export-bridge.js` — DOCX 导出（需重写）
- `~/Desktop/Daily-News-Digest-Report.json` — n8n 工作流（需更新2个节点）
- `~/.n8n/database.sqlite` — n8n 数据库（用 python3 更新工作流）

---

## 步骤 3（详细）：Claude AI 分析节点

**在 n8n 工作流中加入 AI 分析节点**（位于 Combine News Data 和 Build Message 之间）

新增节点：`AI Analyze News`（Code 节点，调用 Claude API）

```
Combine News Data
    → AI Analyze News   ← 新增
        → Build Message
```

调用 `claude-haiku-4-5-20251001` 对每条新闻生成：
```json
{
  "资讯标题": "美联储宣布维持利率不变",
  "资讯来源": "Reuters",
  "发布时间": "2026-04-04 08:30",
  "摘要": "符合市场预期，美元小幅走强",
  "经济影响": "降息预期减弱，债券收益率上行",
  "上市公司影响": ["金融股受益", "REITs承压", "债券ETF(TLT)下跌"]
}
```

API Prompt 设计（每次处理所有 20 条新闻，一次调用）：
> "以下是20条新闻标题，请对每条用JSON格式输出：摘要（15字内）、经济影响（20字内）、相关A股/港股板块（2-3个）"

---

## 步骤 4（详细）：DOCX 格式化

**安装**：`npm install docx` 在 Desktop 目录

**文档结构**：
```
┌────────────────────────────────┐
│    📰 每日新闻摘要报告           │  ← 居中大标题，深蓝色
│    2026-04-04 08:00            │  ← 居中副标题，灰色
└────────────────────────────────┘

【国际新闻 Top 10】                 ← 章节标题，蓝色加粗
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 美联储宣布维持利率不变           ← 加粗
   来源: Reuters | 时间: 08:30     ← 小字灰色
   摘要: 符合市场预期，美元走强      ← 正常字体
   经济影响: 降息预期减弱...        ← 斜体
   相关板块: 金融股、债券ETF        ← 蓝色标签

【金融新闻 Top 10】                 ← 章节标题
...
```

---

## 最终工作流结构

```
Schedule Trigger (每6小时)
    → Fetch Global News
        → Fetch Finance News
            → Combine News Data
                → AI Analyze News    ← 新增节点（调用Claude API）
                    → Build Message
                        → Report Output
                        → Save TXT
                        → Save Word（格式化DOCX）
```

---

## 关键文件路径

- `~/Desktop/news-api-bridge.js` — 扩展 mock 字段（来源、时间）
- `~/Desktop/news-export-bridge.js` — 重写 DOCX 导出（用 docx 库）
- `~/Desktop/Daily-News-Digest-Report.json` — 新增 AI 节点，更新 Build Message
- `~/.n8n/database.sqlite` — 用 python3 更新工作流

---

## 验证步骤

1. `cd ~/Desktop && npm install docx` 安装依赖
2. 重启 news-api-bridge.js 和 news-export-bridge.js
3. 触发 n8n 工作流，检查 AI Analyze News 输出是否包含分析字段
4. 检查生成的 .docx 文件能否被 Word/Pages 正常打开
5. 确认标题加粗、章节标题蓝色、来源/时间显示正确
