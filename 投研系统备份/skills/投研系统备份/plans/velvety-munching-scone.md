# 每日任务优化计划

## Context

用户希望为"单词大挑战"添加完整的每日任务打卡系统。目前代码中已有基础的每日任务框架（`DAILY_NEW_WORDS: 5`、`DAILY_REVIEW_GOAL: 10`、`recordNewWord()` 等），但缺少：任务入口页面、打卡流程引导、完成后金币奖励。

---

## 一、现有代码盘点

### 已有的基础设施（app.js）
| 元素 | 位置 |
|------|------|
| `DAILY_NEW_WORDS = 5`，`DAILY_REVIEW_GOAL = 10` | app.js L29-30 |
| `newWordsToday`、`reviewWordsToday` 计数器 | app.js L31-32 |
| `newWordsLearnedSet` 防重复 | app.js L33 |
| `recordNewWord()` / `recordReview()` | app.js L83-96 |
| `isDailyNewWordDone()` / `isDailyReviewDone()` | app.js L99-107 |
| `getDailyTaskStatus()` | app.js L110-120 |
| `updateDailyTasksUI()` | app.js L123-162（更新首页进度条） |
| `saveDailyTasks()` / `loadDailyTasks()` localStorage | app.js L42-66 |
| 进度条 DOM：`#task-new-bar`、`#task-review-bar` | index.html L36-48 |

### 缺口
1. **无每日任务主入口**：没有 `#screen-dailytask` 或类似屏幕
2. **无引导流程**：用户不知道要按顺序完成哪些模式
3. **无打卡奖励**：完成全部任务没有额外金币激励
4. **无打卡完成态**：首页面板没有"今日已完成"的状态显示

---

## 二、实现计划

### 步骤 1：新建每日任务屏幕 `#screen-dailytask`

**文件**: `index.html`

在 `#screen-home` 前插入新屏幕，包含：
- 顶部标题："每日任务"
- 两个任务卡片：
  - **新词学习**：图标 + 进度文字 + 进度条 + 状态标签（未开始/进行中/已完成）
  - **综合练习**：图标 + 进度文字 + 状态标签
- "领取奖励"按钮（任务全部完成后显示）
- 金币奖励动效区域

### 步骤 2：添加每日任务入口按钮

**文件**: `index.html`

在首页顶部（coin bar 下方）添加 "每日任务" 按钮，带有今日进度徽章。

### 步骤 3：实现任务流程逻辑

**文件**: `js/app.js`

新增 App 方法：

```
_startDailyTaskFlow()       // 点击每日任务入口，读取当前状态，显示引导
_nextTaskInFlow()           // 根据当前任务进度，决定下一个该做什么模式
_completeDailyTask()         // 全部完成后，发放金币奖励，更新打卡状态
_enterTaskMode(mode)        // 进入特定模式，但结束后回调 _onTaskModeComplete
_onTaskModeComplete(mode)   // 模式完成回调，判断是否继续引导或结束任务
```

**任务流程定义**：
```
顺序：闪卡(新词学习) → 四选一 → 连连看 → 拼写练习

每个任务有状态：
- pending（未开始）
- in_progress（进行中）
- completed（已完成）
```

**每个模式的具体目标**：
- **闪卡**：学习 `DAILY_NEW_WORDS = 5` 个新单词（`recordNewWord` 触发）→ 新词任务完成
- **四选一**：完成 10 道题，**新词+错题混合**（新词约7道，错题约3道）→ 综合练习任务完成
- **连连看**：完成 1 局（保持原有 ≥5 对最低词数限制，不够时提示选更多模块）
- **拼写练习**：完成 1 局（保持原有 ≥2 词最低词数限制）

### 步骤 4：任务完成奖励

**文件**: `js/app.js`

修改 `saveProgress()` 或新增 `completeDailyTask()` 方法：
- 完成全部 4 个任务 → 奖励 **+20 金币**
- 同时设置 `dailyTasksCompleted: true` 到 `vocab-daily-v1`
- 已完成打卡时，再次点击每日任务只显示完成状态，不重复奖励

### 步骤 5：结果页引导逻辑

**文件**: `js/app.js`

修改 `showResults()` 方法：
- 如果当前处于任务流程中（`_inTaskFlow = true`），结果显示后自动弹出"继续下一任务"按钮
- 如果是最后一个任务完成，显示"领取奖励"而不是"返回首页"

### 步骤 6：CSS 样式

**文件**: `css/style.css`

新增：
- `#screen-dailytask` 样式（居中卡片布局）
- `.task-card` 任务卡片样式（含图标、进度条）
- `.task-status` 状态标签（未开始/进行中/已完成 颜色区分）
- `.btn-claim` 领取奖励按钮样式
- 金币爆星动画 `.coin-burst`

---

## 三、关键文件修改清单

| 文件 | 修改内容 |
|------|---------|
| `index.html` | 新增 `#screen-dailytask` 屏幕 + 首页任务入口按钮 |
| `js/app.js` | 新增任务流程方法 + 修改 `showResults()` |
| `css/style.css` | 新增每日任务相关样式 |

---

## 四、验证方法

1. 清空 `localStorage`，刷新页面
2. 点击"每日任务"按钮 → 应显示 4 个任务（全部未开始）
3. 点击"新词学习" → 进入闪卡 → 认识 5 个新词 → 返回任务页 → 应看到新词任务完成
4. 按顺序完成四选一、连连看、拼写练习 → 最终显示领取奖励按钮
5. 点击领取 → 金币 +20，任务页显示"今日已完成 ✓"
6. 刷新页面 → 每日任务入口显示"已完成 ✓"，点击进入只有查看功能
7. 第二天（修改系统日期或清空 `vocab-daily-v1` 的 date）→ 任务重置
