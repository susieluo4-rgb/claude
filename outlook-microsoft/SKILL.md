# outlook-microsoft — 世纪互联 Outlook 邮件 + 日历

> 仅支持世纪互联（21Vianet）版本 Microsoft 365。
> 使用 Microsoft Graph API，走中国区专用端点。

## 触发词

"读邮件"、"查看邮件"、"发送邮件"、"搜索邮件"、"Outlook"、"日历"、"日程"、"创建会议"

## 技术原理

- **Microsoft Graph API**：`microsoftgraph.chinacloudapi.cn`
- **认证**：OAuth 2.0 设备码授权（Device Code Flow）
- **依赖**：仅 `requests` 库

## 前置要求

### 1. Azure 世纪互联应用注册

在 [Azure 中国区门户](https://portal.azure.cn) 注册：

1. **Microsoft Entra ID** → **应用注册** → **新建注册**
   - 名称：`Claude Code Outlook`
   - 账户类型：**任何组织目录中的账户**
   - 重定向 URI：**公共客户端/移动&桌面**，填 `http://localhost`

2. **API 权限** → **添加权限** → **Microsoft Graph** → **委托的权限**：
   - `Mail.Read`、`Mail.ReadWrite`、`Mail.Send`
   - `Calendars.Read`、`Calendars.ReadWrite`
   - `User.Read`、`offline_access`、`openid`、`profile`

3. **证书和密码** → **新建客户端密码** → 复制密钥值

4. 复制以下三个值：
   - **应用程序(客户端) ID** → `OUTLOOK_CLIENT_ID`
   - **目录(租户) ID** → `OUTLOOK_TENANT_ID`
   - **客户端密码** → `OUTLOOK_CLIENT_SECRET`

### 2. 配置凭证

```bash
# 编辑脚本目录下的 .env 文件
OUTLOOK_CLIENT_ID=你的客户端ID
OUTLOOK_TENANT_ID=你的租户ID
OUTLOOK_CLIENT_SECRET=你的客户端密码
```

### 3. 完成 OAuth 授权

```bash
python3 ~/.claude/skills/outlook-microsoft/scripts/outlook_auth.py authorize
```

会显示设备码，复制到浏览器完成授权。

### 4. 验证连接

```bash
python3 ~/.claude/skills/outlook-microsoft/scripts/outlook_auth.py test
```

## 使用方式

### 邮件操作

```bash
# 读取收件箱（最新10封）
python3 outlook_mail.py inbox 10

# 按发件人筛选
python3 outlook_mail.py from "华泰证券"

# 搜索邮件
python3 outlook_mail.py search "润铭"

# 读取邮件详情
python3 outlook_mail.py read <邮件ID>

# 标记已读/未读
python3 outlook_mail.py mark-read <邮件ID>
python3 outlook_mail.py mark-unread <邮件ID>

# 发送邮件
python3 outlook_mail.py send "主题" "收件人@example.com" "正文"

# 回复邮件
python3 outlook_mail.py reply <邮件ID> "回复内容"
```

### 日历操作

```bash
# 今日日程
python3 outlook_calendar.py today

# 本周日程
python3 outlook_calendar.py week

# 创建日程
python3 outlook_calendar.py create "会议标题" "2026-04-26 14:00" "2026-04-26 15:00"

# 查询忙闲
python3 outlook_calendar.py freebusy "user@example.com" "2026-04-26 09:00" "2026-04-26 18:00"
```

### 认证管理

```bash
python3 outlook_auth.py status    # 查看 token 状态
python3 outlook_auth.py refresh   # 刷新 token
python3 outlook_auth.py revoke     # 撤销授权
```

## 文件结构

```
outlook-microsoft/
├── SKILL.md
└── scripts/
    ├── .env                      # 凭证配置（需手动创建）
    ├── outlook_auth.py           # OAuth 认证
    ├── outlook_mail.py           # 邮件操作
    └── outlook_calendar.py       # 日历操作
```

## 已知限制

- 仅支持世纪互联版 Microsoft 365
- Token 有效期约 2 小时，`outlook_auth.py refresh` 自动续期
- 附件内容读取需额外调用 `attachments` 命令
