# 单词大挑战 — 艾宾浩斯遗忘曲线复习系统

## Context

**现状**：现有系统按"错误率"排序复习，没有时间维度的调度。同一个词今天答对后，明天不会自动安排复习，全靠用户自己发现忘了。

**目标**：实现基于简化 SM-2 算法的遗忘曲线调度——根据每次答题结果计算下次复习时间，词按"该复习了"而非"错得多"来排序。

---

## 数据结构变更

### `vocab-progress-v1` 每词记录扩展

```js
// 旧结构
{ correct: 3, errors: 1 }

// 新结构（向后兼容：旧记录仍可读）
{
  correct: 3,
  errors: 1,
  lastReviewed: "2026-03-25",      // 上次复习日期（ISO string）
  nextReview: "2026-03-26",         // 下次应该复习的日期
  repetitions: 2,                    // 连续记忆成功次数（SM-2 中的 r）
  easeFactor: 2.5,                   // 难度因子，初始 2.5，最小 1.3
  lastCorrect: true                  // 上次答题是否正确（影响间隔计算）
}
```

### 迁移逻辑
读取旧记录时若无 `nextReview` 字段，默认 `nextReview = 今天`（立即可复习）。

---

## 核心算法（简化 SM-2）

每次 `saveProgress(word, correct)` 后执行：

```js
_updateSpacedRepetition(word, correct) {
  const p = this.state.progress[word];
  const today = new Date().toDateString();

  if (correct) {
    // 答对了：延长间隔
    if (p.repetitions === 0) {
      p.interval = 1;   // 首次成功：1天后
    } else if (p.repetitions === 1) {
      p.interval = 3;   // 第2次成功：3天后
    } else {
      p.interval = Math.round(p.interval * p.easeFactor);
    }
    p.repetitions++;
    // easeFactor 调整（SM-2 标准公式，简化版）
    p.easeFactor = Math.max(1.3, p.easeFactor + 0.1);
    p.lastCorrect = true;
  } else {
    // 答错了：缩短间隔，退回上一步
    p.repetitions = 0;
    p.interval = 1;
    p.easeFactor = Math.max(1.3, p.easeFactor - 0.2);
    p.lastCorrect = false;
  }

  const next = new Date();
  next.setDate(next.getDate() + p.interval);
  p.lastReviewed = today;
  p.nextReview = next.toDateString();
}
```

**复习优先级不再是错误率，而是"距离下次复习的天数"（负数= overdue，越 overdue 越优先）。**

---

## 代码修改

### Step 1: `app.js` — 扩展 `saveProgress()` + 新增遗忘曲线方法

**文件**：`js/app.js`

1. 新增 `_updateSpacedRepetition(word, correct)` 方法（插入在 `saveProgress` 之前）
2. 修改 `saveProgress`：末尾调用 `_updateSpacedRepetition(word, correct)`
3. 迁移兼容：读取 localStorage 后检查每条记录是否有 `nextReview`，无则补充

```js
// 新方法
_updateSpacedRepetition(word, correct) {
  const p = this.state.progress[word];
  if (!p) return;
  const today = new Date().toDateString();

  if (correct) {
    if (p.repetitions === 0) p.interval = 1;
    else if (p.repetitions === 1) p.interval = 3;
    else p.interval = Math.round((p.interval || 1) * (p.easeFactor || 2.5));
    p.repetitions = (p.repetitions || 0) + 1;
    p.easeFactor = Math.max(1.3, (p.easeFactor || 2.5) + 0.1);
    p.lastCorrect = true;
  } else {
    p.repetitions = 0;
    p.interval = 1;
    p.easeFactor = Math.max(1.3, (p.easeFactor || 2.5) - 0.2);
    p.lastCorrect = false;
  }

  const next = new Date();
  next.setDate(next.getDate() + (p.interval || 1));
  p.lastReviewed = today;
  p.nextReview = next.toDateString();
}
```

### Step 2: `app.js` — 新增 `getDueReviewWords()`

替换/增强现有的 `getReviewWords()`：

```js
// 获取今日应复习的词（遗忘曲线驱动）
getDueReviewWords() {
  const mods = this.state.selectedModules;
  const today = new Date().toDateString();
  return WORDS.filter(w => {
    if (mods.length > 0 && !mods.includes(w.unit)) return false;
    const p = this.state.progress[w.word];
    if (!p) return false;  // 从未学过的词不算复习
    // 无 nextReview 字段的旧记录：视为今天应复习
    if (!p.nextReview) return true;
    return p.nextReview <= today;
  }).sort((a, b) => {
    // 最优先：overdue 最久的（nextReview 越早越前面）
    const pa = this.state.progress[a.word]?.nextReview || '';
    const pb = this.state.progress[b.word]?.nextReview || '';
    return pa.localeCompare(pb);
  });
}
```

### Step 3: `app.js` — 修改 `getWordsSmartSorted()` 复习优先级

现有按错误率排序改为按遗忘紧急度：

```js
getUnfamiliarity(word) {
  const p = this.state.progress[word];
  if (!p || (p.correct + p.errors) === 0) return 1.0;  // 未学=最高优先
  // 遗忘紧急度：overdue 天数（负数说明还没到期）
  const today = new Date().toDateString();
  const next = p.nextReview || today;
  const overdue = (new Date(today) - new Date(next)) / 86400000; // 天数差
  // overdue > 0 表示该复习了，越大约优先
  // 无 nextReview 的旧词也视为需要复习
  if (!p.nextReview) return 999;  // 旧词优先复习
  return overdue;
}
```

### Step 4: 修改每日任务中的复习逻辑

**问题**：`getTaskWordPool()` 中调用的 `getReviewWords()` 需要改为 `getDueReviewWords()`。

但要注意：新词学习任务（闪卡）依然用 `isNewWordToday()` 筛选，不受影响。

```js
// _enterTaskMode() 中拼写和四选一的混合池
// 原来：getReviewWords()  → 改为 getDueReviewWords()
// 但 getTaskWordPool 内部用了 getReviewWords()
// 解决方案：给 getTaskWordPool 加参数选择用哪个
```

实际上，更简洁的做法是：
- 在 `getTaskWordPool` 中直接引用 `getDueReviewWords()` 替代原来的 `getReviewWords()`（因为错题本应该就是"该复习的词"）

### Step 5: 保留旧的"错题本"入口

首页"错题本"按钮（`btn-review`）改为显示**今日应复习词数**而非历史错题数：

```js
// updateHomeProgress() 中
const reviewCount = this.getDueReviewWords().length;
if (reviewBtn) {
  reviewBtn.textContent = `📖 复习 (${reviewCount} 词)`;
}
```

---

## 关键文件

| 文件 | 修改内容 |
|------|---------|
| `js/app.js` | `_updateSpacedRepetition()` 新增，`saveProgress()` 末尾调用它，`getDueReviewWords()` 新增，`getUnfamiliarity()` 改用 overdue 计算，`getTaskWordPool` 改用 `getDueReviewWords`，`updateHomeProgress()` 错题本按钮改为今日应复习数 |
| 无需修改 HTML/CSS（数据结构变化对 UI 无影响） |

---

## 验证方法

1. 清除 localStorage（`localStorage.clear()`）
2. 用四选一做 5 道题（全对）
3. 控制台查看 `localStorage['vocab-progress-v1']`，确认每词有 `nextReview` 和 `interval` 字段
4. 等第二天（mock 日期）或直接改 `nextReview` 为昨天，验证 overdue 词排在最前面
5. 确认首页"复习"按钮显示的词数和预期一致
