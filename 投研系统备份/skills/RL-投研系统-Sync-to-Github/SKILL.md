# RL-投研系统 Sync to GitHub v2

增量同步投研系统配置到 GitHub 仓库，**只提交有变更的文件**。

---

## 使用方式

```
/sync-skills
/RL-sync-agent-system
/sync-agent-system
"同步到GitHub"
"更新GitHub"
```

---

## 同步范围（仅 RL/投研 相关）

| 源路径 | GitHub 目标路径 | 说明 |
|--------|----------------|------|
| `~/.claude/skills/RL-*/` | `投研系统备份/skills/RL-*/` | 所有 RL 开头 skill |
| `~/.claude/skills/投研*/` | `投研系统备份/skills/投研*/` | 投研团队 skill |
| `~/投研系统/skills/` | `投研系统备份/skills/` | 投研系统 skills 副本 |
| `~/.claude/settings.json` | `投研系统备份/settings.json` | 全局配置 |
| `~/Research/Vault_公司基本面Agent/03_配置/` | `投研系统备份/Vaults/配置/` | Agent 人设 |
| `~/.claude/projects/-Users-zhuang225-LLM--/memory/` | `投研系统备份/memory/` | 记忆文件 |
| `~/.claude/plans/*.md` | `投研系统备份/plans/` | 计划文件 |

**排除项（不推送）：**
- `~/.mcp.json` — 含 API 密钥
- `__pycache__/` — Python 缓存
- `*.pyc`, `*.pyo` — 编译字节码
- `.DS_Store` — macOS 元数据
- `alert_history.db` — 本地数据库
- `skills/skills/` — 嵌套重复目录
- `投研系统备份/skills/投研系统备份/` — 自引用嵌套

---

## 执行流程

### Step 1: 确认仓库状态

```bash
cd ~
git status --short 2>/dev/null
```

若还没有初始化 git：
```bash
git init
git remote add origin https://github.com/susieluo4-rgb/claude.git
git config user.email "claude@research.ai"
git config user.name "Claude Research"
```

### Step 2: 清理嵌套冗余目录

```bash
cd ~
# 删除嵌套的 skills/skills/ 目录（rsync 误操作产物）
rm -rf "投研系统备份/skills/投研系统备份/skills/"
# 删除自引用嵌套
rm -rf "投研系统备份/skills/投研系统备份/skills/投研系统备份/"
```

### Step 3: 增量同步 Skills

**不使用 rsync --delete**，仅复制有变更的文件：

```bash
# 同步 .claude/skills/ 中的 RL-* 和 投研* 目录
cd ~
for skill in .claude/skills/RL-* .claude/skills/投研*; do
  [ -d "$skill" ] && rsync -av --exclude='__pycache__' --exclude='.DS_Store' --exclude='*.pyc' "$skill/" "投研系统备份/skills/$(basename $skill)/"
done
```

### Step 4: Stage 仅变更的文件

```bash
cd ~
# 只 stage 投研系统备份目录下的变更
git add "投研系统备份/skills/" 2>/dev/null
git add "投研系统备份/settings.json" 2>/dev/null
git add "投研系统备份/memory/" 2>/dev/null
git add "投研系统备份/plans/" 2>/dev/null

# 查看实际变更了哪些文件
git diff --cached --name-only
```

### Step 5: 判断是否需要提交

```bash
# 如果没有变更，跳过 commit
if [ -z "$(git diff --cached --name-only)" ]; then
  echo "✅ 无变更，已是最新"
  # 停止后续步骤
fi
```

### Step 6: 提交并推送

```bash
cd ~
# 生成变更摘要
CHANGED=$(git diff --cached --name-only | head -20)
COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')

git commit -m "feat: 同步投研系统 — ${COUNT} 个文件变更 ($(date '+%Y-%m-%d'))

变更文件:
${CHANGED}

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
"

# 先 pull 远程变更（如有）
git pull --rebase origin main 2>&1

# 推送
git push origin main 2>&1
```

### Step 7: 如果 pull/push 超时（网络问题）

如果 `git pull` 或 `git push` 超过 30 秒无响应：

1. 停止当前操作
2. 提示用户网络较慢，建议：
   - 切换网络环境后重试
   - 或在 GitHub 网页端手动上传变更
3. 变更已在本地 commit，不会丢失

---

## 完整执行脚本（一键版）

```bash
cd ~

# 1. 清理冗余嵌套
rm -rf "投研系统备份/skills/投研系统备份/skills/" 2>/dev/null
rm -rf "投研系统备份/skills/投研系统备份/skills/投研系统备份/" 2>/dev/null

# 2. 增量同步 RL 和 投研 skills
for skill in .claude/skills/RL-* .claude/skills/投研*; do
  [ -d "$skill" ] && rsync -av --exclude='__pycache__' --exclude='.DS_Store' --exclude='*.pyc' "$skill/" "投研系统备份/skills/$(basename $skill)/"
done

# 3. 同步 settings.json 和 memory
cp ~/.claude/settings.json "投研系统备份/" 2>/dev/null
rsync -av --exclude='.DS_Store' .claude/projects/-Users-zhuang225-LLM--/memory/ "投研系统备份/memory/" 2>/dev/null

# 4. Stage 变更
git add "投研系统备份/skills/" 2>/dev/null
git add "投研系统_backup/settings.json" 2>/dev/null
git add "投研系统备份/memory/" 2>/dev/null

# 5. 检查是否有变更
CHANGED_FILES=$(git diff --cached --name-only 2>/dev/null)
if [ -z "$CHANGED_FILES" ]; then
  echo "✅ 无变更，已是最新"
  exit 0
fi

# 6. 提交
FILE_COUNT=$(echo "$CHANGED_FILES" | wc -l | tr -d ' ')
git commit -m "feat: 同步投研系统 — ${FILE_COUNT} 个文件变更 ($(date '+%Y-%m-%d'))

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
"

# 7. 推送
git pull --rebase origin main 2>&1
git push origin main 2>&1
```

---

## GitHub 仓库

| 项目 | 值 |
|------|-----|
| 仓库地址 | https://github.com/susieluo4-rgb/claude |
| 远程协议 | HTTPS |
| 本地根目录 | `~` |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v2.0 | 2026-04-12 | 改为增量同步，排除冗余/缓存，自动检测变更 |
| v1.0 | - | 全量 rsync --delete 覆盖（已废弃） |

---

## 注意事项

1. **增量同步**：只同步 `RL-*` 和 `投研*` 开头的 skill，不碰 3rd party skills
2. **自动排重**：清理嵌套 `skills/skills/` 和 `__pycache__`
3. **无变更跳过**：如果没有任何文件变更，自动停止不提交
4. **网络超时保护**：push 超时不 force push，保留本地 commit 下次重试
5. **敏感文件不推送**：`~/.mcp.json` 绝不上 GitHub
