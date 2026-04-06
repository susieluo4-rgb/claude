# RL Sync to GitHub

将多Agent投研系统的所有配置文件同步推送到 GitHub 仓库。

---

## 使用方式

```
/sync-skills
/sync-agent-system
```

---

## 备份范围

| 路径 | 说明 | 重要性 |
|------|------|--------|
| `~/.claude/skills/` | 所有Skill触发器（含投研团队Skill） | ⭐⭐⭐ |
| `~/.claude/settings.json` | Claude Code全局设置 | ⭐⭐⭐ |
| `~/Research/Vault_公司基本面Agent/03_配置/` | 基本面Agent人设 | ⭐⭐⭐ |
| `~/Research/Vault_*/` | 所有Agent Vault（9个） | ⭐⭐⭐ |
| `~/0.Agent 投研总监/reports/` | 生成的报告 | ⭐⭐ |
| `~/.claude/projects/-Users-zhuang225-0-Agent-----/memory/` | 记忆文件 | ⭐⭐ |
| `~/.claude/plans/` | 计划文件 | ⭐ |

**已排除（敏感信息）：**
- `~/.mcp.json` — 包含API密钥，**请勿上传GitHub**
- `~/.claude/settings.json` 中的个人token

---

## 执行步骤

### 1. 定位备份根目录
```bash
cd ~
```

### 2. 检查git状态
```bash
git status
```

若还没有初始化过git，执行初始化：
```bash
git init
git remote add origin https://github.com/susieluo4-rgb/claude.git
git config user.email "claude@research.ai"
git config user.name "Claude Research"
```

### 3. 克隆仓库到本地（如首次）
```bash
git clone https://github.com/susieluo4-rgb/claude.git ~/backup_temp
```

### 4. 同步文件到本地备份目录

```bash
# 创建备份目录结构
mkdir -p ~/backup_temp/投研系统备份

# 同步skills
rsync -av ~/.claude/skills/ ~/backup_temp/投研系统备份/skills/

# 同步settings.json
cp ~/.claude/settings.json ~/backup_temp/投研系统备份/

# 同步所有Vault
rsync -av ~/Research/Vault_*/ ~/backup_temp/投研系统备份/Vaults/

# 同步报告
rsync -av ~/0.Agent\ 投研总监/reports/ ~/backup_temp/投研系统备份/reports/

# 同步记忆文件
rsync -av ~/.claude/projects/-Users-zhuang225-0-Agent-----/memory/ ~/backup_temp/投研系统备份/memory/

# 同步计划文件
rsync -av ~/.claude/plans/*.md ~/backup_temp/投研系统备份/plans/
```

### 5. 提交推送
```bash
cd ~/backup_temp
git add .
git commit -m "Update 投研系统 - $(date '+%Y-%m-%d %H:%M')"
git push origin main
```

---

## 一键备份命令

```bash
# 创建临时备份目录
git clone https://github.com/susieluo4-rgb/claude.git ~/backup_temp --depth 1

# 同步所有文件
mkdir -p ~/backup_temp/投研系统备份
rsync -av ~/.claude/skills/ ~/backup_temp/投研系统备份/skills/
cp ~/.claude/settings.json ~/backup_temp/投研系统备份/
rsync -av ~/Research/Vault_*/ ~/backup_temp/投研系统备份/Vaults/
rsync -av ~/0.Agent\ 投研总监/reports/ ~/backup_temp/投研系统备份/reports/
rsync -av ~/.claude/projects/-Users-zhuang225-0-Agent-----/memory/ ~/backup_temp/投研系统备份/memory/
rsync -av ~/.claude/plans/*.md ~/backup_temp/投研系统备份/plans/

# 提交推送
cd ~/backup_temp
git add .
git commit -m "Update 投研系统 - $(date '+%Y-%m-%d %H:%M')"
git push origin main

# 清理临时目录
rm -rf ~/backup_temp
```

---

## 从GitHub恢复

```bash
# 克隆仓库
git clone https://github.com/susieluo4-rgb/claude.git ~/restore_temp

# 恢复skills
rsync -av ~/restore_temp/投研系统备份/skills/ ~/.claude/skills/

# 恢复settings.json
cp ~/restore_temp/投研系统备份/settings.json ~/.claude/

# 恢复Vaults
rsync -av ~/restore_temp/投研系统备份/Vaults/ ~/Research/

# 恢复报告
rsync -av ~/restore_temp/投研系统备份/reports/ ~/0.Agent\ 投研总监/

# 恢复记忆
rsync -av ~/restore_temp/投研系统备份/memory/ ~/.claude/projects/-Users-zhuang225-0-Agent-----/memory/

# 清理
rm -rf ~/restore_temp
```

---

## GitHub 仓库

| 项目 | 值 |
|------|-----|
| 仓库地址 | https://github.com/susieluo4-rgb/claude |
| 远程协议 | HTTPS |

---

## 注意事项

1. **敏感文件不推送**：`~/.mcp.json` 包含API密钥，**禁止上传GitHub**
2. **定期备份**：建议每次对skill或配置有实质更新后执行
3. **恢复前先pull**：从另一设备恢复前，先 `git pull` 同步最新
4. **Vaults体积较大**：如Vaults文件很多，可先压缩再同步
