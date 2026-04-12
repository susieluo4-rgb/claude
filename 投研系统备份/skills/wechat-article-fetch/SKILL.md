---
name: wechat-article-fetch
description: 微信公众号文章抓取工具。当用户提供微信公众号文章链接（mp.weixin.qq.com）且需要读取文章内容时使用。支持自动打开 Chrome 浏览器窗口、手动验证、正文提取、Markdown 保存。输出保存至 ~/Research/Vault_共享知识库/ 目录。
metadata:
    version: 1.0
    type: data-source
    dependency: playwright (已安装)
    cost: 免费
---

# WeChat-Article-Fetch — 微信公众号文章抓取

## 核心定位

微信公众号文章的反爬机制（环境异常验证）导致直接 HTTP 抓取或 WebFetch 工具无法获取内容。本 skill 通过 Playwright 启动真实 Chrome 窗口，用户手动完成验证后自动提取正文并保存为 Markdown。

## 使用方式

### 何时触发

- 用户提供 `mp.weixin.qq.com` 链接并要求读取内容
- 投研雷达Agent收集到微信文章链接需要解析
- 用户说"帮我读下这篇微信文章"、"解析这个链接"等

### 执行步骤

```bash
# 关键：必须设置 NODE_PATH，否则找不到全局安装的 playwright
NODE_PATH=~/.nvm/versions/node/v24.13.0/lib/node_modules node ~/.claude/skills/wechat-article-fetch/fetch_article.js "https://mp.weixin.qq.com/s/xxxxx"
```

> **环境问题排查**：如果报错 `Cannot find module 'playwright'`，是因为 Bash 工具未加载 nvm 环境变量。解决方案：显式设置 `NODE_PATH=~/.nvm/versions/node/v24.13.0/lib/node_modules`

### 输出位置

默认保存到：`~/Research/Vault_共享知识库/微信文章抓取.md`

可通过第二个参数自定义输出路径。

## 工作流程

1. **启动 Chrome** — 使用 Playwright 打开独立 Chrome 窗口（临时 profile，不影响正在运行的 Chrome）
2. **导航到文章** — 加载微信文章 URL
3. **检测验证** — 自动检测是否需要完成人机验证
4. **等待用户操作** — 如需验证，终端提示用户手动完成，输入 "done" 继续
5. **提取正文** — 自动提取标题、作者、发布时间、正文纯文本、图片链接
6. **保存 Markdown** — 生成带 frontmatter 的 Markdown 文件

## 交互流程

```
用户: 帮我读下这篇微信文章 https://mp.weixin.qq.com/s/xxx
Agent: 正在启动浏览器抓取...
      → 弹出 Chrome 窗口
      → 如需验证: "请在弹出的窗口中完成验证，完成后输入 done"
      → 用户输入 done
      → 自动提取并保存
      → "文章已保存到 ~/Research/Vault_共享知识库/微信文章抓取.md"
```

## 技术细节

### 依赖

- Node.js (v24+)
- Playwright (已全局安装 v1.59.1)
- Google Chrome (macOS: `/Applications/Google Chrome.app`)

### 提取选择器

| 元素 | 优先级选择器 |
|------|------------|
| 标题 | `#activity-name` → `.rich_media_title` → `document.title` |
| 作者 | `#js_name` → `.rich_media_meta_nickname` |
| 发布时间 | `#publish_time` → `.rich_media_meta_text` |
| 正文 | `#js_content` → `.rich_media_content` |
| 图片 | `img[data-src]` → `img[src]` |

### 输出格式

```markdown
---
title: "文章标题"
author: "作者"
publish_time: "2026年4月10日 20:31"
source_url: "原文链接"
captured_at: "2026-04-11T13:26:56"
tags: [微信文章, 投研]
---

# 文章标题

**作者**: xxx
**发布时间**: xxx
**原文链接**: xxx

---

正文内容...

## 图片来源 (N 张)
- ![图片 1](url)
```

## 限制

- 需要用户手动完成验证（微信反爬机制无法自动化绕过）
- 音频/视频内容无法提取，仅保留占位文本
- 部分微信特有的排版元素（如 SVG 动画）可能丢失
- 每次抓取使用临时 Chrome profile，无法复用登录态（为避免与正在运行的 Chrome 冲突）

## 文件

| 文件 | 说明 |
|------|------|
| `fetch_article.js` | 核心脚本，支持 CLI 调用 |
| `SKILL.md` | 本文件 |
