---
name: RL-alphapai
description: RL投研包 — 基于Alpha派API，专门针对RL自选股（189只）提供一键投研问答、纪要检索、业绩点评、公告监控等批量分析能力。当用户提到RL自选股、RL分组、我的自选股查询、批量检索RL股票、RL监控、或要求对自选股进行投研分析时使用本skill。
metadata:
    version: 1.0
    parent: alphapai-research
    watchlist_group: RL
    watchlist_count: 63
---

# RL-AlphaPai 投研技能包

基于 Alpha派 API，专为 **RL 自选股分组**（63只，2026-04-07更新）提供投研分析封装。

## 核心定位

本 skill 是 `alphapai-research` 的 RL 自选股专用封装层，所有底层调用均委托 `alphapai-research/scripts/alphapai_client.py` 执行。**无需额外配置 API Key**（复用 alphapai-research 的配置）。

## RL 自选股列表

RL 分组共 **63 只**股票，覆盖以下核心方向：

| 方向 | 代表股票 |
|------|---------|
| 半导体/GPU | 寒武纪(688256.SH)、中芯国际(688981.SH)、沐曦股份(688802.SH) |
| 机器人/汽车电子 | 科博达(603786.SH)、耐世特(01316.HK)、舜宇光学(02382.HK) |
| 卫星测控 | 星图测控(920116.BJ)、航天宏图(688066.SH) |
| 军工/高端制造 | 航宇科技(688239.SH)、盟升电子(688311.SH)、华力创通(300045.SZ) |
| 医疗/生物科技 | 海尔生物(688139.SH)、心脉医疗(688016.SH)、中熔电气(301031.SZ) |
| 新能源汽车 | 比亚迪电子(00285.HK)、欣旺达(300207.SZ)、通合科技(300491.SZ) |
| 港股/美股 | 美团(03690.HK)、联想集团(00992.HK)、拼多多(PDD.US) |

> 完整列表请用 `watchlist` 命令实时查询。

## 使用方式

所有命令通过 `alphapai-research` 的 CLI 执行，无需重复安装依赖。

### 一键查询 RL 自选股公告

```bash
# 查询 RL 分组中某只股票的最近公告
python ~/.claude/skills/alphapai-research/scripts/alphapai_client.py report --code <股票代码>
```

### 批量检索 RL 股票纪要

```bash
# 检索 RL 分组中某只股票的路演纪要（近3个月）
python ~/.claude/skills/alphapai-research/scripts/alphapai_client.py recall \
  --query "<关键词>" \
  --type roadShow \
  --start 2026-01-01 --end 2026-04-07
```

### RL 个股 Agent 分析

```bash
# 公司一页纸
python ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 2 \
  --stock <代码:名称>

# 投资逻辑
python ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 7 \
  --stock <代码:名称>

# 业绩点评（需先查公告ID）
python ~/.claude/skills/alphapai-research/scripts/alphapai_client.py report --code <代码>
```

### RL 主题选股

```bash
# 按主题筛选相关股票
python ~/.claude/skills/alphapai-research/scripts/alphapai_client.py agent --mode 5 \
  --question "<主题>" --template-text "<主题>"
```

## 输出原则

与母 skill `alphapai-research` 一致：
- **不总结、不压缩、不截断**：完整输出原始内容
- **保留原始格式**：Markdown、表格、引用块原样呈现
- **引用来源随正文输出**

## 配置说明

- **API Key**：复用 `~/.claude/skills/alphapai-research/config.json`，无需单独配置
- **base_url**：`https://open-api.rabyte.cn`
- **自选股同步**：在 Alpha派 电脑端添加/删除 RL 分组股票，下次调用自动同步

## 典型工作流

### 工作流1：监控 RL 分组新纪要

```
1. recall --query "<行业/主题词>" --type roadShow --start 2026-04-01
2. 从返回结果中筛选 RL 分组股票
3. 对感兴趣的股票调用 agent --mode 2/7 深读
```

### 工作流2：批量业绩跟踪

```
1. 对 RL 分组重点股票批量调用 report --code <代码>
2. 筛选出近期有财报发布的股票
3. 调用 agent --mode 1 做业绩点评
```

### 工作流3：主题机会挖掘

```
1. agent --mode 5 --template-text "<热点主题>"
2. 对筛出的股票与 RL 分组取交集
3. 对重叠股票调用 agent --mode 8 找可比公司
```

## 更新日志

### v1.0 (2026-04-07)
- 初始化 RL 分组封装
- RL 分组：63只股票，覆盖半导体/机器人/军工/医疗/新能源
