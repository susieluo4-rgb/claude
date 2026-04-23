---
name: rl-radar-agent
description: 投研系统雷达Agent — 多数据源信息收集层 + 全自动被动监控层。当用户说"投研 [公司]"、研究 [公司]、分析 [公司]、雷达 [公司]、或启动投研任务时，Lead Agent会先调用本Agent预先收集目标公司的外部数据（财报/研报/纪要/宏观/行业），为后续Agent提供数据支撑。同时本Agent支持全自动被动监控模式（Cron定时触发），无需用户指令即可完成每日增量扫描 + iFinD邮件扫描 + Wiki增量更新。
metadata:
    version: 1.15
    type: data-collection-agent
    position: 前置数据收集层 + 全自动被动监控层
    data_sources: alphapai-research, iFind, 本地文件, listed-company-reports skill, iFind邮件订阅(QQ邮箱)
---

# rl-radar-agent — 投研系统雷达Agent

## 角色定位

雷达Agent是**投研系统的信息收集前置层**，在每个投研任务启动时，被Lead Agent调用预先抓取目标公司的最新外部数据，确保后续分析Agent能获得完整、及时的信息输入。

```
投研任务启动
    ↓
Lead Agent 调用 雷达Agent（被动响应）
    ↓ 预先收集全量数据
【雷达Agent输出】 ← 提供给后续Agent使用
    ↓
宏观Agent + 行业Agent + 数据校验Agent ← 共享雷达收集的数据
```

## 核心职责

1. **财报数据收集** — 本地文件 + 港交所披露 + AlphaPai获取最新年报/季报
2. **研报与纪要检索** — AlphaPai recall路演纪要、券商研报
3. **公告监控** — AlphaPai report + iFind新闻
4. **宏观/行业数据** — iFind EDB宏观指标、行业数据
5. **舆情与热点** — AlphaPai qa/recall
6. **本地文件核查** — 扫描Research目录已有文件

## 执行流程

### 执行模式

本 Agent 有两种执行模式：

| 模式 | 触发方式 | 说明 |
|------|---------|------|
| **主动模式** | 用户/Lead Agent 调用 | 针对特定公司收集数据，投研任务前置 |
| **被动/定时模式** | Cron 定时触发 | 全自动扫描持仓公司增量，无需用户指令 |

**定时模式脚本：**
- `incremental_scan.py` — 工作日 08:30 执行，扫描 AlphaPai + Rabyte
- `email_incremental_scan.py` — 每小时执行，拉取 iFinD 邮件推送

### 报告反馈机制（v1.11新增）

所有雷达 Agent 脚本跑完后统一输出报告，包含：
- **文件清单**：处理了哪些文件
- **处理结果**：重大事件数、一般增量数、保存文件数
- **待确认事项**：如有重大事件需用户确认

**报告输出方式：**

| 触发类型 | stdout（Claude Code 对话框） | SMTP 邮件 |
|---------|---------------------------|---------|
| 手动触发（无 `--no-email`） | ✅ | ✅ |
| 手动触发（带 `--no-email`） | ✅ | ❌ |
| Cron 自动触发 | ❌（写入日志） | ✅ |
| 干跑（`--dry-run`） | ✅（仅 stdout） | ❌ |

**统一报告格式：**
```json
{
  "scan_type": "email_incremental_scan",
  "timestamp": "2026-04-18 22:00",
  "summary": {"ifind_emails": 3, "saved_files": 5},
  "files": [{"path": "raw/announcements/xxx.md", "action": "saved"}],
  "errors": [],
  "next_actions": []
}
```

**脚本新增参数：**
- `--no-email`：手动触发时不发邮件，仅输出到对话框
- `--dry-run`：仅打印，不保存文件也不发邮件

### Step 0：工具可用性检查（v1.7新增，启动即执行）

**每次雷达Agent启动时，首先检查以下工具是否可用，避免执行中途发现工具不可用导致数据缺失：**

```bash
# 1. 财报下载技能（listed-company-reports）
ls ~/.claude/skills/listed-company-reports/SKILL.md

# 2. AlphaPai 客户端
ls ~/.claude/skills/alphapai-research/scripts/alphapai_client.py

# 3. AlphaPai API Key（config.json）
cat ~/.claude/skills/alphapai-research/config.json | grep api_key
```

**降级策略：**
| 工具缺失 | 降级方案 |
|---------|---------|
| `listed-company-reports` skill 不存在 | 标记"⚠️ 财报下载技能缺失"，跳过PDF下载，继续其他数据收集 |
| `alphapai_client.py` 不存在 | 标记"⚠️ AlphaPai客户端缺失"，用 iFind/妙想 替代公告+舆情 |
| AlphaPai API Key 缺失/无效 | 跳过所有 AlphaPai 调用，用 iFind search_news + search_notice 替代 |
| 全部正常 | 全量数据收集 |

检查结果在最终输出报告的"数据质量评估"中标注。

### Step 1：解析公司信息

1. 接收公司名称或股票代码
2. 确认股票代码（如只给名称，用iFind或搜索确认）
3. 确认交易所（SH/SZ/HK/US等后缀）

### Step 1.5（新增）：本地基本面文件夹核查

**必须执行**，优先于其他数据源：

```
目标路径：~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{股票代码}/
```

**⚠️ 文件夹命名规范（实测重要）**：
- 格式：必须是 `{公司名}_{股票代码}`，例如 `中芯国际_688981`
- 拼音首字母按公司名拼音首字母确定（中芯国际→Z→`11_公司列表/Z/`）
- 字母目录已统一为 `11_公司列表/` 下的单字母子目录（A/B/C/.../Z）
- download_reports.py 依赖此格式识别市场，格式不对会导致下载失败

**执行步骤：**

1. **扫描已有文件夹**
   ```
   Glob扫描：~/Research/Vault_公司基本面Agent/**/*{公司名}*/
   检查是否存在对应文件夹，确认命名格式正确
   ```

2. **检查资料完整性**
   | 资料类型 | 要求（近3年） | 缺失处理 |
   |---------|-------------|---------|
   | 年报 | 2023 + 2024 + 2025（共3年） | 从公司官网或HKEX下载 |
   | 半年报 | 2024上 + 2024下 + 2025上（共3期） | 从公司官网下载 |
   | 季报 | 近四期（Q1-Q4 2025） | 从公司官网下载 |
   | 研报 | 券商研报、公司介绍等 | 标记缺失，记录需要补全 |

3. **【新增】财报数量完整性检查 — Gate 检查**
   > 要求：年报≥5份，半年报≥5份，季报≥6份，合计≥16份
   > 阈值：合计 < 10份 → 触发 listed-company-reports 下载
   > 下载后仍不足 → 弹窗确认用户是否继续

   ```bash
   VAULT_BASE=~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}
   ANNUAL_DIR="$VAULT_BASE/年报"
   HALF_DIR="$VAULT_BASE/半年报"
   QUARTER_DIR="$VAULT_BASE/季报"

   count_reports() {
     find "$1" \( -name "*.pdf" -o -name "*.PDF" \) 2>/dev/null | wc -l | tr -d ' '
   }

   ANNUAL_COUNT=$(count_reports "$ANNUAL_DIR")
   HALF_COUNT=$(count_reports "$HALF_DIR")
   QUARTER_COUNT=$(count_reports "$QUARTER_DIR")
   TOTAL=$((ANNUAL_COUNT + HALF_COUNT + QUARTER_COUNT))

   echo "📂 财报完整性检查：年报=$ANNUAL_COUNT 半年报=$HALF_COUNT 季报=$QUARTER_COUNT (合计=$TOTAL/16)"

   if [ "$TOTAL" -lt 10 ]; then
     echo "⚠️ 财报不足（$TOTAL/16），触发 listed-company-reports 下载..."
     # 调用 listed-company-reports skill（见下方执行方式）
     # 下载完成后重新计数
     ANNUAL_COUNT_AFTER=$(count_reports "$ANNUAL_DIR")
     HALF_COUNT_AFTER=$(count_reports "$HALF_DIR")
     QUARTER_COUNT_AFTER=$(count_reports "$QUARTER_DIR")
     TOTAL_AFTER=$((ANNUAL_COUNT_AFTER + HALF_COUNT_AFTER + QUARTER_COUNT_AFTER))

     if [ "$TOTAL_AFTER" -lt 10 ]; then
       echo "❌ 下载后仍不足（$TOTAL_AFTER/16）"
       # 弹窗确认：AskUserQuestion "财报文件不足（$TOTAL_AFTER/16），是否继续投研？"
       # - 继续：写入 checkpoint 标注 warn，继续
       # - 取消：停止任务
     else
       echo "✅ 下载完成（$TOTAL_AFTER/16）"
     fi
   else
     echo "✅ 财报数量充足（$TOTAL/16），继续"
   fi
   ```

4. **补全缺失资料（使用 listed-company-reports skill）**

   调用 `listed-company-reports` skill 下载缺失财报PDF：

   **Skill 路径**：`~/.claude/skills/listed-company-reports/SKILL.md`

   **工作流程**（按 skill 定义执行）：
   - **A股**：巨潮资讯网(cninfo) → 东方财富(备选)
   - **港股**：披露易(hkexnews) → 公司官网投资者关系页(备选)
   - **美股**：SEC EDGAR

   下载完成后验证文件是否存入：
   ```
   ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/年报/
   ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/半年报/
   ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/季报/
   ```
   如 skill 下载失败，降级到公司官网投资者关系页手动搜索，并在报告中标注"⚠️ 财报PDF下载失败，待补全"。

5. **存储AlphaPai收集结果（强制执行步骤）**
   - **必须执行，不得跳过**。若 AlphaPai API 失败，静默跳过后续 Agent 导致数据不完整，比 API 失败更严重。
   - 新建文件夹：`~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/alphapai/`

   **执行顺序与失败处理：**
   ```
   ① 创建 alphapai/ 目录
   ② 依次执行下方 5 个命令，每个命令最多重试 3 次
   ③ 每次执行后检查退出码：0 = 成功，非 0 = 失败
   ④ 重试 3 次仍失败 → 在 Vault/alphapai/ 下创建「alphapai_失败_{命令名}.log」并记录错误信息，然后继续下一个命令
   ⑤ 所有命令执行完毕后，验证 alphapai/ 目录是否包含「非空」文件（公司一页纸允许为空，不算失败）
   ⑥ 验证通过后输出「✅ 雷达Agent数据收集完成」，方可进入后续 Agent
   ⑦ 若验证发现路演纪要或研报摘要为空 → 必须重试（最多3次）→ 仍为空则标注「⚠️ 数据为空，待补充」
   ```

   **精确命令（不可用伪命令，必须用真实脚本路径）：**
   ```bash
   ALPHAPAI=~/.claude/skills/alphapai-research/scripts/alphapai_client.py
   OUT=~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/alphapai
   DATE=$(date +%Y%m%d)

   # ── 命令1：路演纪要全文（强制，3次重试，近6个月，最多10篇）──
   # 保存路径: Vault_公司基本面Agent/.../alphapai/路演纪要_*.txt
   # 用途: 作为背景材料注入后续Agent上下文（不写Raw仓库）
   for i in 1 2 3; do
     python3 $ALPHAPAI transcript \
       --query "{公司名} {股票代码}" \
       --path-prefix "11_公司列表/{拼音首字母}/{公司名}_{代码}" \
       --start $(date -v-6m +%Y-%m-%d) \
       --end $(date +%Y-%m-%d) && break
     sleep 5
   done || echo "⚠️ 路演纪要失败，请检查网络和API配额" >> "$OUT/alphapai_失败_transcript.log"

   # ── 命令2：研报摘要（强制，3次重试，近6个月，最多10篇）──
   # 用途: 作为背景材料注入后续Agent上下文（recall返回语义片段，非完整研报）
   for i in 1 2 3; do
     python3 $ALPHAPAI recall \
       --query "{公司名}" --type report --no-cutoff \
       --start $(date -v-6m +%Y-%m-%d) \
       --end $(date +%Y-%m-%d) > "$OUT/研报摘要_${DATE}.md" && break
     sleep 5
   done || echo "⚠️ 研报摘要失败" >> "$OUT/alphapai_失败_recall.log"

   # ── 命令3：公告列表（强制，3次重试）──
   for i in 1 2 3; do
     python3 $ALPHAPAI report --code {股票代码} \
       > "$OUT/公告列表_${DATE}.md" && break
     sleep 5
   done || echo "⚠️ 公告列表失败" >> "$OUT/alphapai_失败_report.log"

   # ── 命令4：舆情热点（强制，3次重试）──
   for i in 1 2 3; do
     python3 $ALPHAPAI qa \
       --question "{公司名}近期有什么重大消息？近期股价走势和催化剂？" --mode Think \
       > "$OUT/舆情热点_${DATE}.md" && break
     sleep 5
   done || echo "⚠️ 舆情热点失败" >> "$OUT/alphapai_失败_qa.log"

   # ── 命令5：公司一页纸（强制，3次重试，--question必填）──
   for i in 1 2 3; do
     python3 $ALPHAPAI agent --mode 2 \
       --question "{公司名}的公司一页纸" --stock "{股票代码}:{公司名}" \
       > "$OUT/公司一页纸_${DATE}.md" && break
     sleep 5
   done || echo "⚠️ 公司一页纸失败" >> "$OUT/alphapai_失败_agent_mode2.log"

   # ── 命令6：投资逻辑（强制，3次重试，--question格式固定）──
   for i in 1 2 3; do
     python3 $ALPHAPAI agent --mode 7 \
       --question "{公司名}的投资逻辑" --stock "{股票代码}:{公司名}" \
       > "$OUT/投资逻辑_${DATE}.md" && break
     sleep 5
   done || echo "⚠️ 投资逻辑失败" >> "$OUT/alphapai_失败_agent_mode7.log"

   # ── 命令7：行业一页纸（强制，3次重试，--question格式固定）──
   # ⚠️ --question 必须传 "{行业名}的行业一页纸" 格式，API 自动生成框架
   for i in 1 2 3; do
     python3 $ALPHAPAI agent --mode 11 \
       --question "车载电源的行业一页纸" --industry 车载电源 \
       > "$OUT/行业一页纸_${DATE}.md" && break
     sleep 5
   done || echo "⚠️ 行业一页纸失败" >> "$OUT/alphapai_失败_agent_mode11.log"

   # ── 命令8：调研大纲（强制，3次重试，--question格式固定）──
   for i in 1 2 3; do
     python3 $ALPHAPAI agent --mode 3 \
       --question "{公司名}的调研问题大纲" --stock "{股票代码}:{公司名}" \
       > "$OUT/调研大纲_${DATE}.md" && break
     sleep 5
   done || echo "⚠️ 调研大纲失败" >> "$OUT/alphapai_失败_agent_mode3.log"
   ```

   **验证清单（必须全部通过方可进入后续 Agent）：**
   ```
   alphapai/
   ├── 路演纪要_*.txt      ← 必须存在且 > 1KB
   ├── 研报摘要_*.md      ← 必须存在且 > 1KB
   ├── 公告列表_*.md     ← 必须存在（大小不限）
   ├── 舆情热点_*.md      ← 必须存在且 > 1KB
   ├── 公司一页纸_*.md   ← 必须存在且 > 1KB
   ├── 投资逻辑_*.md    ← 必须存在且 > 1KB
   ├── 行业一页纸_*.md  ← 必须存在且 > 1KB
   └── 调研大纲_*.md    ← 必须存在且 > 1KB
   ```

   **失败输出示例（必须体现）：**
   ```
   ❌ 雷达Agent数据收集未完成：
      路演纪要：⚠️ API失败（已重试3次），日志：alphapai/alphapai_失败_transcript.log
      研报摘要：✅
      公告列表：✅
      舆情热点：✅
      公司一页纸：⚠️ API失败（已重试3次），日志：alphapai/alphapai_失败_agent_mode2.log
      投资逻辑：⚠️ API失败（已重试3次），日志：alphapai/alphapai_失败_agent_mode7.log
      行业一页纸：⚠️ API失败（已重试3次），日志：alphapai/alphapai_失败_agent_mode11.log
      调研大纲：⚠️ API失败（已重试3次），日志：alphapai/alphapai_失败_agent_mode3.log
   → 请修复网络问题后重新执行投研，或手动补充缺失数据
   ```

### Step 2：数据源优先级

**A股（SZ/SH后缀）：**
```
优先级 1：本地文件（最高）
  → 扫描 ~/Documents/earnings-transcripts/{公司名}*
  → 扫描 ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}/
  → 如有最新年报/季报PDF，直接读取

优先级 2：iFind MCP
  → get_stock_performance：最新行情（涨跌幅/换手率）、融资融券余额
  → get_stock_financials：最新财务报表（使用自然语言query）
  → get_stock_info + get_stock_summary：公司基本信息
  → get_edb_data + search_edb：宏观/行业数据

优先级 3：AlphaPai API（使用真实脚本路径）
  → **注意**：`agent --mode 2` 必须传入 `--question` 参数，否则报错；`recall --type report` 返回的是召回索引（标题+来源），不是完整研报正文，勿高估可用性
  → 路演纪要（增量）：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py transcript --query "{公司} {代码}" --path-prefix "11_公司列表/{拼音}/{公司}_{代码}" --start $(date -v-1m +%Y-%m-%d) --end $(date +%Y-%m-%d)`
  → 公告+纪要+点评（增量）：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py recall --query "{公司} {代码}" --type ann,roadShow,comment --start $(date -v-1m +%Y-%m-%d) --end $(date +%Y-%m-%d)`
  → 公司一页纸：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 2 --question "{公司名}的公司一页纸" --stock "{代码}:{公司名}"`
  → 投资逻辑：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 7 --question "{公司名}的投资逻辑" --stock "{代码}:{公司名}"`
  → 行业一页纸：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 11 --question "车载电源的行业一页纸" --industry 车载电源`
  → 调研大纲：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 3 --question "{公司名}的调研问题大纲" --stock "{代码}:{公司名}"`
  → **注意**：`--question` 必须传模板格式（如"{公司名}的投资逻辑"），API 自动生成框架；`qa` 命令在 radar 场景下不跑（无上下文时只返回标题）
  → 公告列表（索引）：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py report --code {代码}`
  → 舆情热点：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py qa --question "{公司}近期有什么重大消息？近期股价走势和催化剂？" --mode Think`

优先级 3.5：东方财富妙想（iFind 限流/失效时启用）
  → 财务数据、行情估值、公司信息、宏观数据：
    python3 "/Users/zhuang225/Research/ifind mcp&skill/miaoxiang/mx_api.py" --type data --query "{公司} {指标}"
  → 新闻、公告、舆情：
    python3 "/Users/zhuang225/Research/ifind mcp&skill/miaoxiang/mx_api.py" --type news --query "{公司} 最新公告"
  → ⚠️ 注意：每日有次数上限；免费用户仅支持3年内数据；不支持 ESG/风险指标

优先级 4：iFind新闻
  → search_news：最新新闻舆情

优先级 4.5：新浪财经（仅实时股价兜底，新增）
  → 仅当 iFind/妙想/AlphaPai 均无法获取实时股价时启用
  → 脚本：`python3 ~/.claude/skills/sina-stock-price/fetch_price.py --code {股票代码}`
  → 返回：price（当前价）、change_pct（涨跌幅%）、yesterday_close、volume
  → 港股格式：0268.HK → `--code 0268.HK`（脚本自动补零到5位）
  → A股格式：688981.SH → `--code 688981.SH`
  → ⚠️ 仅提供实时价格，不含历史/财报/研报/宏观数据

优先级 5：网络搜索（兜底）
  → 仅在其他途径均无结果时使用
```

**港股（HK后缀）：**
```
优先级 1：本地文件（最高）
  → 扫描 ~/Documents/earnings-transcripts/{公司名}*
  → 扫描 ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}/
  → 如有最新年报/季报PDF，直接读取

优先级 2：iFind MCP
  → get_stock_performance：最新行情（涨跌幅/换手率）、融资融券余额
  → get_stock_financials：最新财务报表（使用自然语言query）
  → get_stock_info：公司基本信息
  → search_news：最新新闻舆情

优先级 3：AlphaPai API（使用真实脚本路径）
  → **注意**：`agent --mode 2` 必须传入 `--question` 参数；`recall --type report` 返回召回索引而非正文
  → 路演纪要（增量）：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py transcript --query "{公司} {代码}" --path-prefix "11_公司列表/{拼音}/{公司}_{代码}" --start $(date -v-1m +%Y-%m-%d) --end $(date +%Y-%m-%d)`
  → 公告+纪要+点评（增量）：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py recall --query "{公司} {代码}" --type ann,roadShow,comment --start $(date -v-1m +%Y-%m-%d) --end $(date +%Y-%m-%d)`
  → 舆情热点：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py qa --question "{公司}近期有什么重大消息？" --mode Think`
  → 公司一页纸：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 2 --question "{公司名}的公司一页纸" --stock "{代码}:{公司名}"`
  → 投资逻辑：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 7 --question "{公司名}的投资逻辑" --stock "{代码}:{公司名}"`
  → 调研大纲：`python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 3 --question "{公司名}的调研问题大纲" --stock "{代码}:{公司名}"`
  → **注意**：`--question` 必须传模板格式（如"{公司名}的投资逻辑"），API 自动生成框架

优先级 3.5：东方财富妙想（iFind 限流/失效时启用）
  → 财务数据、行情估值：
    python3 "/Users/zhuang225/Research/ifind mcp&skill/miaoxiang/mx_api.py" --type data --query "{股票代码} {指标}"
  → ⚠️ 港股用股票代码格式（如 0700.HK）；每日有次数上限

优先级 4：港交所披露（补充）
  → https://www.hkexnews.hk/ 搜索最新年报/中报PDF
  → 下载PDF存入Vault_公司基本面Agent对应文件夹

优先级 4.5：新浪财经（仅实时股价兜底，新增）
  → 仅当 iFind/妙想/AlphaPai 均无法获取实时股价时启用
  → 脚本：`python3 ~/.claude/skills/sina-stock-price/fetch_price.py --code {股票代码}`
  → 港股代码自动补零：0268.HK → hk00268（脚本内部处理）
  → ⚠️ 仅提供实时价格，不含历史/财报/研报/宏观数据

优先级 5：网络搜索（兜底）
  → 仅在其他途径均无结果时使用
```

### Step 2.5：读取增量状态（新增）

**读取 last_sync.json**，判断每个数据类型是否需要重新拉取：

```
路径：~/Research/Vault_共享知识库/last_sync.json
首次执行：文件不存在，则创建，全量拉取所有数据
非首次执行：读取文件，按各数据类型的缓存有效期判断是否需要重新拉取
```

**缓存有效期规则：**
| 数据类型 | 缓存有效期 | 超过有效期则 |
|---------|---------|------------|
| 财务数据 | 7天 | 重新拉取（财报数据稳定，不频繁变动） |
| 技术行情 | 24小时 | 重新拉取（每次覆盖近5日） |
| 路演纪要 | 7天 | 增量拉取（按时间窗口过滤） |
| 研报摘要 | 7天 | 增量拉取（按时间窗口过滤） |
| 公告列表 | 24小时 | 重新拉取 |
| 舆情热点 | 12小时 | 重新拉取 |

**缓存命中时**：跳过 API 调用，直接使用 `Vault_共享知识库/{公司名}_{代码}/` 下的已有文件，
并在报告中标注 `（缓存：有效）`

**缓存过期时**：按 Step 2 优先级重新拉取，并在报告中标注 `（缓存：已过期，重新拉取）`

### Step 3：收集内容清单

| 数据类型 | A股来源 | 港股来源 | 输出格式 | 增量策略 |
|---------|---------|---------|---------|---------|
| 最新年报/季报财务数据 | iFind get_stock_financials / 本地PDF | 港交所披露PDF + AlphaPai | 结构化dict | 缓存7天；财报发布后主动刷新 |
| **技术行情数据** | iFind get_stock_performance | iFind get_stock_performance | 结构化dict | 缓存24小时；每次覆盖近5日 |
| 公司基本信息 | iFind get_stock_info | AlphaPai agent | 结构化dict | 缓存7天 |
| 近期公告列表（10条） | AlphaPai report | AlphaPai report | 列表 | 缓存24小时 |
| 路演纪要（近3个月） | AlphaPai recall --type roadShow | AlphaPai recall --type roadShow | Markdown文本 | 缓存7天；按时间窗口增量拉取 |
| 券商研报摘要 | AlphaPai recall --type report | AlphaPai recall --type report | Markdown文本 | 缓存7天；按时间窗口增量拉取 |
| 公司一页纸 | AlphaPai agent --mode 2 | AlphaPai agent --mode 2 | Markdown文本 | 缓存7天 |
| 投资逻辑 | AlphaPai agent --mode 7 | AlphaPai agent --mode 7 | Markdown文本 | 缓存7天 |
| 行业一页纸 | AlphaPai agent --mode 11 | — | Markdown文本 | 缓存7天 |
| 调研大纲 | AlphaPai agent --mode 3 | AlphaPai agent --mode 3 | Markdown文本 | 缓存7天 |
| 业绩点评 | AlphaPai agent --mode 1（如有报告ID） | AlphaPai agent --mode 1 | Markdown文本 | 缓存7天 |
| 宏观/行业数据 | iFind EDB | 不适用 | 结构化dict | 缓存7天 |
| 舆情/热点 | AlphaPai qa + iFind新闻 | AlphaPai qa + iFind新闻 | Markdown文本 | 缓存12小时 |
| 本地已有文件 | Glob扫描 | Glob扫描 | 文件路径列表 | 不适用 |

> 注：缓存"有效"时直接使用已有文件；"过期"时才重新拉取。路演纪要/研报摘要每次拉取时传入时间窗口参数实现增量。

### Step 4：输出整理

将收集到的数据整理为标准化格式，输出给Lead Agent：

```markdown
## 雷达Agent数据收集报告 — {公司名称}（{股票代码}）

### 数据时效性
- 财报数据：{最新财报期}（缓存：有效/已过期）
- 技术行情：{最新行情日期}（缓存：有效/已过期）
- 路演纪要：{最新纪要日期}（近3个月共{条数}条，缓存：有效/已过期）
- 公告：{最新公告日期}（缓存：有效/已过期）
- 研报：{最新研报日期}（缓存：有效/已过期）
- 舆情热点：{最新舆情时间}（缓存：有效/已过期）

### 已获取数据清单
1. 【财务数据】✅ 已获取（来源：{本地文件/iFind/AlphaPai}）
2. 【公司信息】✅ 已获取（来源：{iFind/AlphaPai}）
3. 【公告列表】✅ 已获取（来源：AlphaPai，共10条）
4. 【路演纪要】✅ 已获取（来源：AlphaPai，共X条）
5. 【研报摘要】✅ 已获取（来源：AlphaPai，共X条）
6. 【公司一页纸】✅ 已获取（来源：AlphaPai agent --mode 2）
7. 【投资逻辑】✅ 已获取（来源：AlphaPai agent --mode 7）
8. 【行业一页纸】✅/⚠️ 已获取/未获取（来源：AlphaPai agent --mode 11，仅A股）
9. 【调研大纲】✅ 已获取（来源：AlphaPai agent --mode 3）
10. 【技术行情数据】✅ 已获取（来源：iFind get_stock_performance）
   - 近5日涨跌幅、换手率
   - 最新融资融券余额及近期变化趋势
10. 【宏观数据】✅/⚠️ 未获取（原因：...）
11. 【舆情热点】✅ 已获取（来源：AlphaPai+iFind新闻）
12. 【本地文件】✅/⚠️ 已有{文件名}，建议优先使用
13. 【港交所披露】✅/⚠️ 已下载/年报缺失待补全

### 关键数据摘要
（从收集的数据中提取最重要信息，供后续Agent快速参考）

### 技术面数据摘要
（从 get_stock_performance 提取，供技术分析Agent直接使用）
- 近5日累计涨跌幅：{X}%
- 近5日平均换手率：{X}%
- 最新融资融券余额：{X}（较上周变化：{+/-X}）
- 近期趋势：{上涨/下跌/震荡}

### 数据质量评估
- 完整性：{高/中/低}
- 时效性：{高/中/低}
- 可信度：{高/中/低}

### 数据交叉验证
（同一指标从多数据源获取，标注差异，不做仲裁）
| 指标 | iFind | AlphaPai/本地文件 | 差异 |
|------|-------|------------------|------|
| 营业收入（最新一期） | {X}亿元 | {Y}亿元 | ⚠️ 差异{X-Y}亿元（{占比}%） |
| 净利润（最新一期） | {X}亿元 | — | ✅ 一致 |
（仅列出存在差异的指标；一致时标注✅；无对比来源时标注"—"）
⚠️ 差异说明：多数据源差异可能源于口径不同（合并/母公司/追溯调整），留待基本面Agent判断。

---
数据收集完成时间：{YYYY-MM-DD HH:MM}
```

### Step 5：数据存储

**必须存储到两个位置：**

**1. 共享知识库**（供后续Agent快速读取）：
```
路径：~/Research/Vault_共享知识库/{公司名}_{股票代码}/

文件：
├── 00_雷达数据收集.md          ← 本报告
├── 01_财务数据_{日期}.json     ← iFind/AlphaPai财报数据
├── 02_公司信息_{日期}.json     ← iFind/AlphaPai公司信息
├── 03_公告列表_{日期}.md       ← 最新公告
├── 04_路演纪要_{日期}.md       ← AlphaPai路演纪要
├── 05_研报摘要_{日期}.md       ← AlphaPai研报
├── 06_宏观数据_{日期}.json     ← iFind EBD数据
└── 07_技术行情数据_{日期}.json ← iFind get_stock_performance 数据

**3. last_sync.json（增量同步记录，必须更新）：**
```
路径：~/Research/Vault_共享知识库/last_sync.json
首次：文件不存在则创建
每次收集完成后：更新对应股票+数据类型的 last_sync 时间戳
```
格式：
```json
{
  "{股票代码}": {
    "财务数据": { "last_sync": "2026-04-09T10:00:00", "last_data_date": "2025-12-31" },
    "技术行情": { "last_sync": "2026-04-09T10:00:00" },
    "路演纪要": { "last_sync": "2026-04-01T10:00:00" },
    "研报摘要": { "last_sync": "2026-04-01T10:00:00" },
    "公告列表": { "last_sync": "2026-04-09T09:00:00" },
    "舆情热点": { "last_sync": "2026-04-09T08:00:00" }
  }
}
```
> 注意：每次 Step 5 完成后，必须同步更新 last_sync.json。只拉取了部分数据类型时，只更新对应部分的时间戳。
```

**2. 基本面Agent文件夹**（与基本面Agent共享，作为double check）：
```
路径：~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{股票代码}/

文件（原有）：
├── 年报/
├── 半年报/
├── 季报/
└── 研报/

新增文件夹：
└── alphapai/                   ← AlphaPai收集的补充数据
    ├── 路演纪要_{日期}.md
    ├── 研报摘要_{日期}.md
    ├── 舆情热点_{日期}.md
    └── 公司一页纸_{日期}.md
```

**示例**：中芯国际(688981.SH)
```
Vault_公司基本面Agent/S-Z/中芯国际_688981/
├── 年报/
│   ├── SMIC_2021年报.pdf
│   ├── SMIC_2022年报.pdf
│   ├── SMIC_2023年报.pdf
│   ├── 中芯国际_2024年报.pdf
│   └── 中芯国际_2025年报.pdf
├── 半年报/
├── 季报/
└── alphapai/
```

## AlphaPai 调用规范

### 路演纪要检索（完整版）
使用 `transcript` 命令，自动获取完整纪要并保存为 TXT 到 `~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{股票代码}/alphapai/`：

```bash
python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py transcript \
  --query "{公司名称} {股票代码} {纪要关键词}" \
  --path-prefix "11_公司列表/{拼音首字母}/{公司名}_{股票代码}" \
  --start $(date -v-1m +%Y-%m-%d) \
  --end $(date +%Y-%m-%d)
```

> **说明**：`--path-prefix` 由 Step 1.5 确认的拼音首字母和公司文件夹名拼接而成（如 `11_公司列表/Z/中芯国际_688981`），内部固定调用 `recall --type roadShow --no-cutoff`，自动拼接 chunks 保存。**注意**：返回的是语义搜索的碎片化 chunks，不是完整原始文档，字数通常在数百字量级。

### 公告+纪要+点评检索（增量）
```bash
python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py recall \
  --query "{公司名称} {股票代码}" \
  --type ann,roadShow,comment \
  --start $(date -v-1m +%Y-%m-%d) \
  --end $(date +%Y-%m-%d)
```

> **注意**：`recall` 返回的是**召回索引列表**（标题+来源片段），不是完整研报/公告正文。`ann`=公告，`roadShow`=路演纪要，`comment`=机构点评。这是 `incremental_scan.py` 实际使用的调用方式，与 `--type report` 不同。

### 公司多维分析（Agent modes 1-11）
```bash
# 并行跑7个mode: 1=业绩点评 2=公司一页纸 3=调研大纲 5=主题选股 7=投资逻辑 8=可比公司 9=观点Challenge 11=行业一页纸
python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 2 \
  --question "{公司名}的公司一页纸" \
  --stock {股票代码}:{公司名称}
```

> **重要**：不同 mode 需要不同必填参数——mode 1（业绩点评）需要 `--report-id`/`--report-period`；mode 11（行业一页纸）需要 `--industry`。雷达场景下建议只跑 mode 2，其余 mode 按需单独调用。`--question` 是所有 mode 的必填参数，缺少会报错。

### 舆情热点
```bash
python3 ~/.claude/skills/alphapai-research/scripts/alphapai_client.py qa \
  --question "{公司名称}近期有什么重大消息？近期股价走势和催化剂？" \
  --mode Think
```

> **唯一真正有用的命令**：`qa` 返回完整分析正文 + 引用来源，是 AlphaPai 五条命令中唯一一个能提供实质性内容的。其余命令均受 API 设计限制，无法获取原始文档正文。

## iFind 调用规范

### 获取财务报表（重要：使用自然语言query）

**⚠️ 关键发现**：`get_stock_financials` 的 query 参数是**自然语言字符串**，不是结构化参数！

```javascript
// ✅ 正确格式：自然语言query
get_stock_financials({
  query: "中芯国际 688981.SH 2024-2025年 营业收入 净利润 毛利率 ROE 每股收益"
})

// ❌ 错误格式：分离的参数（会返回空）
get_stock_financials({
  query: "688981.SH",
  indicators: "revenue,netprofit",
  reporttype: "0"
})
```

### query格式规范

```
"{公司名称} {股票代码（可选）} {年份/日期范围} {指标列表}"
```

**常用指标名称**：
- 营业收入、营业总收入、净利润、归属于母公司所有者的净利润
- 每股收益EPS、基本每股收益、稀释每股收益
- 销售毛利率、净资产收益率ROE
- 资产负债率、经营活动现金流、应收账款周转天数

**示例**：
```javascript
// A股 - 获取多年数据
get_stock_financials({ query: "中芯国际 688981.SH 2020-2025年 营业收入 净利润 毛利率" })

// A股 - 获取单季度数据
get_stock_financials({ query: "中芯国际 688981.SH 2025年各季度 营业收入 净利润" })

// 查询PE/PB等估值指标
get_stock_financials({ query: "中芯国际 688981.SH 市盈率 市净率 市销率" })

// 港股 - 使用股票代码格式
get_stock_financials({ query: "0100.HK 营业收入 净利润" })
get_stock_financials({ query: "0700.HK 营业收入 净利润" })
```

**港股说明**：
- iFind支持港股，但query格式与A股不同
- 港股用 `{股票代码} {指标}` 格式，如 `0100.HK 营业收入 净利润`
- 不支持公司名称查询，必须用股票代码
- 港股公司可能历史数据有限（如MiniMax 2026年1月才上市）

### 获取公司信息
```javascript
get_stock_info({ query: "{股票代码}" })
get_stock_summary({ query: "{股票代码}" })
```

### EDB宏观/行业数据
```javascript
get_edb_data({ indicators: "PMI,CPi,PPI,GDP" })
search_edb({ query: "{行业名称}" })
```

### 新闻查询
```javascript
search_news({
  query: "{公司名称} {股票代码}",
  page_size: 10,
  time_start: "YYYY-MM-DD",
  time_end: "YYYY-MM-DD"
})
```

### 获取技术行情数据

**⚠️ 重要**：单个 query 中同时请求"涨跌幅/换手率"和"融资融券"，会返回两份数据，
合并为一次输出（见下方示例）。

```javascript
// A股 - 行情 + 融资融券（可合并在同一次调用中）
get_stock_performance({
  query: "{公司名称} {股票代码} 最近5日的涨跌幅、换手率、成交量、融资融券余额"
})

// 港股 - 行情
get_stock_performance({
  query: "{股票代码} {公司名称} 近期涨跌幅、换手率"
})
```

**返回关键字段：**
- 涨跌幅（%）、涨跌（元）
- 换手率（%）、区间换手率（%）
- 融资融券余额（元）
- 日期序列（近5-20个交易日）

**示例返回：**
```json
{
  "600519.SH": {
    "日期": "20260409",
    "涨跌幅": "-0.31%",
    "换手率": "0.17%",
    "融资融券余额": "167.84亿"
  }
}
```

## 财报PDF下载（listed-company-reports skill）

港股财务数据主要来源：

1. **公司官网投资者关系页（首选）**
   - 金蝶国际(0268.HK)案例：`https://investor.kingdee.com/en/finance/reports/`
   - 中芯国际(00981.HK)案例：`https://www.smics.com/en/site/company_financialSummary`
   - 通过公司官网获取年报/中报PDF链接，直接curl下载

2. **港交所披露易（备用，API已多次改版失败）**
   - https://www.hkexnews.hk/ — 旧RSS API (`smarthttp/1/rss/reports/`) 返回404/503
   - 搜索页面也经过多次改版，JS动态加载，爬虫难度大
   - 建议：公司官网 > 披露易搜索

3. **调用方式**：使用 `listed-company-reports` skill
   - Skill 路径：`~/.claude/skills/listed-company-reports/SKILL.md`
   - 支持A股/港股/美股，自动识别市场并选择数据源
   - 下载后自动存入标准目录结构

4. **下载后存储位置**：
   ```
   ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/年报/
   ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/半年报/
   ~/Research/Vault_公司基本面Agent/11_公司列表/{拼音首字母}/{公司名}_{代码}/季报/
   ```

5. **港股年报下载实测记录**
   | 股票 | 下载方式 | 状态 |
   |------|---------|------|
   | 金蝶国际(0268.HK) | investor.kingdee.com官网 | ✅ 成功 |
   | 金蝶国际(0268.HK) | HKEX RSS API | ❌ 404错误 |
   | 中芯国际(00981.HK) | smics.com官网 | ✅ 成功 |
   | 中芯国际(00981.HK) | HKEX RSS API | ❌ 503错误 |
   | 中芯国际(00981.HK) | HKEX搜索页 | ❌ 页面改版 |
   | A股(688981.SH) | CNINFO | ❌ 科创板不支持 |

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| iFind MCP + 备用脚本均限流/失效 | 切换到东方财富妙想（mx_api.py） |
| 妙想 API 也限流（每日上限） | 切换到 AlphaPai 作为主要数据源 |
| 实时股价无法获取（iFind/妙想/AlphaPai均失效） | 降级到新浪财经（fetch_price.py），仅获取实时价格 |
| iFind港股财务数据为空 | 降级到港交所披露 + AlphaPai |
| AlphaPai API Key缺失 | 降级到iFind/妙想 + 本地文件 |
| 本地文件不存在 | 跳过，继续其他数据源 |
| 港交所披露下载失败 | 标记缺失，记录需要补全，继续后续 |
| 网络超时 | 重试1次，失败则记录"⚠️ 获取失败"继续后续 |
| 所有数据源均无数据 | 输出空白报告，标注"⚠️ 全量数据获取失败" |
| 多数据源同一指标冲突 | 在报告中标记⚠️，列出来源及数值，不仲裁，留给基本面Agent判断 |

## 性能要求

- 单公司数据收集：**5分钟内完成**
- 超时处理：主API调用3分钟未返回，切换备用数据源
- 并行能力：支持多数据源同时请求（iFind + AlphaPai + 港交所披露并行）

## 与其他Agent的数据交接

雷达Agent输出后，Lead Agent会：
1. 将数据路径传递给宏观Agent（宏观数据）
2. 将数据路径传递给行业Agent（行业数据）
3. 将数据路径传递给数据校验Agent（财报数据）
4. 将完整数据摘要传递给所有Agent

**无需等待所有数据收集完成即可并行启动后续Agent**，已收集的数据即时可用。

## 定时监控脚本

本 Agent 支持全自动被动监控，无需用户指令即可定时扫描持仓公司增量数据。

### 脚本清单

| 脚本 | 路径 | 触发频率 | 功能 |
|------|------|---------|------|
| `incremental_scan.py` | `~/.claude/skills/rl-radar-agent/scripts/incremental_scan.py` | 每天 15:00 / 21:00 | AlphaPai 持仓扫描 + 纪要/研报增量 → Raw仓库 + SMTP 汇总邮件 |
| `email_incremental_scan.py` | `~/.claude/skills/rl-radar-agent/scripts/email_incremental_scan.py` | 每 4 小时 | iFinD 邮件推送 → Raw 仓库 |
| `confirm_handler.py` | `~/.claude/skills/rl-radar-agent/scripts/confirm_handler.py` | 每 5 分钟 | 重大事件确认 → 纪要追踪 → 邮件反馈 |

> 注：`incremental_scan.py` 和 `email_incremental_scan.py` 由 LaunchAgent `com.rl.hourly-scan` 统一调度，每 4 小时运行一次，合并发送一封汇总邮件。

### incremental_scan.py — 持仓增量扫描

**功能：**
1. 从基金经理 Agent Vault 动态加载所有组合持仓（润铭 + CIF，共 76+ 家）
2. AlphaPai recall：公告 + 路演纪要 + 机构点评（近 1 天）
3. 分类：重大事件 vs 一般增量 vs 空数据（静默跳过）
4. 有有效内容才自动落入 Vault + 触发 Wiki ingest
5. 汇总邮件：只列出有实际内容的公司，统计"查询 X 家 / Y 家有数据 / Z 家无数据"

**持仓来源（v1.13 动态加载）：**
- 路径：`~/Research/Vault_基金经理Agent/润铭.md` + `CIF.md`
- 通过 `portfolio_loader.py` 实时读取，组合持仓变更后自动生效
- 空数据（AlphaPai 返回"召回数据 0 条"）不创建文件，邮件中不单独列出

**SMTP 发送（v1.8 新增）：**
- 不依赖 qq-email MCP（Claude Code 桌面应用未加载）
- 使用 Python `smtplib` 直连 SMTP：`smtp.qq.com:587`
- 授权码：`gesrbiwaipzpbhhf`

**LaunchAgent：** `com.rl.hourly-scan`（每天 15:00 / 21:00）

### email_incremental_scan.py — iFinD 邮件增量扫描（v1.8 新增核心功能）

**功能：**
1. 每小时通过 IMAP 拉取 QQ邮箱 收件箱
2. 解析 iFinD HTML 邮件（公司公告/财经新闻/股东会提示）
3. 按持仓公司列表过滤，只处理相关公司
4. 写入 Raw 仓库：`raw/announcements/`、`raw/notes/`
5. 写 `pending_ingest/` 标记文件触发 Wiki ingest
6. 同步 `last_email_sync.json` 记录最新 UID

**MCP 调用方式（关键）：**
- 使用 heredoc 方式解决 `npx mcp-email` 的 stdin 竞争问题：
```bash
bash -c 'cat << 'EOFJSON' | npx mcp-email
{"jsonrpc":"2.0",...}
EOFJSON'
```
- 响应解析：匹配 `{"result` 或 `{"jsonrpc` 或 `{"error` 前缀

**UID 同步逻辑：**
- `uid < last_uid`（严格小于，等于时不重复处理）
- 首次运行：同步全部历史邮件
- 后续运行：只同步新邮件

**iFinD 邮件解析：**
- 自定义 `iFinDMailParser(HTMLParser)` 提取三类内容：
  - 公司公告 → `raw/announcements/ifind_announcement_*.md`
  - 财经新闻 → `raw/announcements/ifind_news_*.md`
  - 股东会提示 → `raw/notes/ifind_tips_*.md`

**Cron 任务 ID：** `7d822924`（每小时）

**配置：**
- QQ邮箱授权码：`gesrbiwaipzpbhhf`
- IMAP 服务器：`imap.qq.com:993`
- MCP 配置：`~/.claude/mcp.json`

### confirm_handler.py — 重大事件确认处理器（v1.12 新增）

**功能：**
1. 每 5 分钟通过 IMAP 读取 QQ 邮箱收件箱
2. 检测用户回复的"确认"邮件（关键词：确认/是/ok/跟踪）
3. 从邮件主题/正文解析确认的公司名和事件
4. 查找对应公司的增量文件（Vault alphapai/ + raw/announcements/ + raw/reports/）
5. 写入 `confirmed_events.json` 状态文件（status: pending → processing → done）
6. 发送"处理中"邮件给用户
7. 调用 `run_transcript_tracking.py` 自动收集资料并生成纪要追踪报告
8. 发送"追踪完成"结果邮件，附带报告路径

**状态文件：**
```
~/Research/Vault_共享知识库/raw/confirmed_events.json
```

**确认邮件格式：**
用户回复增量扫描邮件或在任意邮件中写：
- `确认 中芯国际`
- `确认 中芯国际 年报发布`
- `跟踪 宁德时代`
- `是`

**链路流程：**
```
用户收到邮件: 重大事件待确认: 中芯国际年报发布
      ↓
用户回复邮件: "确认 中芯国际"
      ↓
confirm_handler.py (每5分钟Cron)
      ↓ 解析确认 → 查找增量文件 → 写状态文件
发送"处理中"邮件
      ↓
run_transcript_tracking.py
      ↓ 扫描Vault资料 + AlphaPai获取 + 生成报告
发送"追踪完成"邮件 + 报告路径
      ↓
更新 confirmed_events.json (status=done)
```

**Cron 任务 ID：** 新建（每 5 分钟）

---

### Raw → Wiki 自动化链路

```
iFinD 邮件（每小时）
  ↓ IMAP 拉取
email_incremental_scan.py
  ↓ 解析 + 持仓过滤
Raw 仓库（announcements/notes/）
  ↓ pending_ingest 标记
rl-wiki-ingest Cron（每4小时）
  ↓ 自动分拣 + Wiki ingest
Wiki 页面增量更新 + log.md 记录
```

## 注意事项

1. **不总结、不截断**：AlphaPai返回的原始内容完整输出
2. **标注来源**：每个数据项标注来源（iFind/AlphaPai/本地文件/港交所披露）
3. **标注时效**：注明数据日期/报告期
4. **质量评估**：对完整性、时效性、可信度给出评估
5. **优先使用本地**：本地已有文件优先使用，避免重复下载
6. **港股财务数据**：以港交所披露PDF为准，iFind财务数据可能为空
7. **Step 1.5必须执行**：在收集任何数据前，必须先完成本地基本面文件夹核查
8. **增量同步**：Step 2.5 读取 last_sync.json，缓存有效时跳过API调用；每次收集完成后必须更新 last_sync.json
9. **⚠️ 财报PDF必须下载（v1.6新增，核心修复）**：API返回结构化财务数据 ≠ PDF已下载。**财报PDF下载是独立任务，与API数据获取并行执行，互不替代。** 即使iFind/妙想已返回完整的财务数据，仍必须完成Step 1.5的PDF完整性检查并下载缺失的年报/中报/季报。这是"数据源短路"问题的修复 — 此前雷达Agent在API返回数据后即认为任务完成，跳过了PDF下载步骤。

---

---

## Bug Fix Record

| 日期 | Bug | 修复说明 |
|------|-----|----------|
| 2026-04-21 | AlphaPai步骤静默跳过 | Step 4（AlphaPai收集）无重试、无验证，失败时静默跳过后续Agent，导致alphapai/目录完全缺失。新增强制执行（最多3次重试）+ 退出码检查 + 空文件验证 + 失败log输出 + 验证清单，未通过时阻止后续Agent执行 |

---

*版本：v1.17 | 2026-04-21*
*核心变更：v1.17 AlphaPai agent多mode并行（1-11）、移除qa；v1.16 recall改用ann,roadShow,comment、agent加--question；v1.15 AlphaPai强制执行+重试+验证；v1.13 持仓动态加载（润铭+CIF）、空数据静默跳过、邮件每4小时一次只列有内容*
