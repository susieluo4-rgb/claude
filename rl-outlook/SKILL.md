# rl-outlook — ⚠️ 已迁移，请使用 outlook-microsoft

> **本 Skill 已废弃，请使用 `outlook-microsoft` Skill。**
>
> 新 Skill 基于 Microsoft Graph API，无需浏览器，稳定性更高，功能更强。

---

## 迁移指南

### 新 Skill：outlook-microsoft

```bash
# 读邮件
python3 ~/.claude/skills/outlook-microsoft/scripts/outlook_mail.py inbox 10
python3 ~/.claude/skills/outlook-microsoft/scripts/outlook_mail.py search "关键词"
python3 ~/.claude/skills/outlook-microsoft/scripts/outlook_mail.py from "发件人"

# 日历
python3 ~/.claude/skills/outlook-microsoft/scripts/outlook_calendar.py today

# Token 状态
python3 ~/.claude/skills/outlook-microsoft/scripts/outlook_auth.py status
```

详见：`~/.claude/skills/outlook-microsoft/SKILL.md`

---

## 保留的 Fallback

`scripts/outlook_client.py`（AppleScript → 本地 Outlook.app）作为网络故障时的紧急备用：

```bash
python3 ~/.claude/skills/rl-outlook/scripts/outlook_client.py
```

仅在 Graph API 完全不可用时使用。

---

## 已删除的旧实现

以下方式已废弃：
- `chrome_outlook_client.py`（依赖 Chrome + partner.outlook.cn）
- `outlook.applescript`（旧版 AppleScript）
- `read_mail.applescript`
- `search_mail.applescript`
- `read_emails.js`

---

*迁移时间：2026-04-25*
