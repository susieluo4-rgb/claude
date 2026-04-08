# 计划：修复模块选择相关 Bug

## 背景
代码审查发现 `selectedModules` 选词逻辑有 2 个 bug，需要修复。

---

## Bug 1：`getReviewWords()` 忽略模块选择

**位置**：`js/app.js` 第 340-345 行

**问题**：`btn-review` 调用 `getReviewWords()` 返回**所有模块**的错词，不受用户模块选择限制

**修复**：修改 `getReviewWords()` 加入 `selectedModules` 过滤
```js
getReviewWords() {
  const mods = this.state.selectedModules;
  return WORDS.filter(w => {
    if (mods.length > 0 && !mods.includes(w.unit)) return false;
    const p = this.state.progress[w.word];
    return p && p.errors > 0;
  });
}
```

---

## Bug 2：`selectedModules` 不持久化

**位置**：`js/app.js` 状态初始化 + `loadProgress()`

**问题**：`selectedModules` 只存在内存，刷新页面后丢失，重置为"全部词汇"

**修复**：
1. 新增 `saveSelectedModules()` 保存到 `localStorage`（key: `vocab-modules-v1`）
2. 新增 `loadSelectedModules()` 在 `init()` 时读取恢复
3. 在 `_addModule` / `_removeModule` / `_toggleModule` 末尾调用 `saveSelectedModules()`
4. 抽屉关闭时（`ms-start` 点击）也触发保存

**localStorage 键**：`vocab-modules-v1`

```js
// 保存
saveSelectedModules() {
  try {
    localStorage.setItem('vocab-modules-v1', JSON.stringify(this.state.selectedModules));
  } catch (_) {}
}

// 加载（在 init() 中调用）
loadSelectedModules() {
  try {
    const s = localStorage.getItem('vocab-modules-v1');
    if (s) this.state.selectedModules = JSON.parse(s);
  } catch (_) {
    this.state.selectedModules = [];
  }
}
```

---

## 实现步骤

1. **`js/app.js`**
   - 修改 `getReviewWords()` 加入模块过滤
   - 新增 `saveSelectedModules()` / `loadSelectedModules()`
   - 在 `_addModule` / `_removeModule` / `_closeModuleSelector` 中调用 `saveSelectedModules()`
   - 在 `init()` 中调用 `loadSelectedModules()`
2. 验证 GitHub 推送

---

## 验证

1. 选择特定模块（如"四上 M1" + "四下 M2"）
2. 刷新页面 → 模块选择保持（不重置）
3. 点击错题本 → 只显示所选模块内的错词
4. 其他模式（闪卡/四选一/拼写/连连看）均使用所选模块的词
