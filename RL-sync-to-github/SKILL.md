# RL Sync to GitHub

将 `~/.claude/skills/` 中的所有 RL skill 同步推送到 GitHub 仓库。

---

## 使用方式

```
/sync-skills
```

---

## 执行步骤

### 1. 定位 skills 目录
```
cd ~/.claude/skills/
```

### 2. 检查 git 状态
```
git status
```
- 若还没有初始化过 git，执行初始化：
  ```
  git init
  git remote add origin https://github.com/susieluo4-rgb/claude.git
  git config user.email "claude@research.ai"
  git config user.name "Claude Research"
  ```

### 3. 添加所有 RL skill 文件
```
git add RL-company-research-model/SKILL.md
git add RL-daily-report/SKILL.md
git add "RL-系统录入自动化/SKILL.md"
git add RL-sync-to-github/SKILL.md   # 本skill也一起同步
```

### 4. 检查变更
```
git status
```
确认文件列表是否正确。

### 5. 提交
```
git commit -m "Update RL skills - $(date '+%Y-%m-%d %H:%M')"
```

### 6. 推送
```
git push origin main
```

---

## 自动执行（无需确认）

若确认无误，可一次性执行完整流程：

```bash
cd ~/.claude/skills && \
git add . && \
git commit -m "Update RL skills - $(date '+%Y-%m-%d %H:%M')" && \
git push origin main
```

---

## GitHub 仓库

| 项目 | 值 |
|------|-----|
| 仓库地址 | https://github.com/susieluo4-rgb/claude |
| 远程协议 | HTTPS |

---

## 注意事项

- 每次推送前检查 `git status`，确保不会误提交敏感文件
- `git pull` 优先：若远程有更新，先 `git pull --rebase` 再 `git push`
- 建议在每次 skill 有实质更新后执行，不必频繁推送
