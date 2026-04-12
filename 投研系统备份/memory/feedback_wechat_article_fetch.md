---
name: wechat_article_fetch_success
description: 微信文章抓取方法 — 使用 wechat-article-fetch skill 的 Playwright 脚本绕过反爬
type: feedback
originSessionId: d6fa946f-9f57-47fc-b08b-14704f9d6a67
---
**规则**：微信文章链接（mp.weixin.qq.com）无法用 WebFetch 直接抓取（会返回"环境异常"验证页面）。必须使用 `wechat-article-fetch` skill 中的 `fetch_article.js` 脚本，通过 Playwright 启动真实 Chrome 窗口来抓取。

**Why**: 2026-04-12 首次尝试 WebFetch 抓微信文章失败，后改用 Playwright 成功抓取。WebFetch 无法通过微信反爬验证。

**How to apply**:
- 遇到微信文章链接时，**必须**使用：
  ```
  NODE_PATH=~/.nvm/versions/node/v24.13.0/lib/node_modules node ~/.claude/skills/wechat-article-fetch/fetch_article.js "URL" [输出路径]
  ```
- Playwright 安装在 nvm 全局模块中（`~/.nvm/versions/node/v24.13.0/lib/node_modules/playwright`）
- Bash 工具**不加载 nvm 环境变量**，所以必须显式设置 `NODE_PATH`，否则报 `Cannot find module 'playwright'`
- 如弹出验证窗口，需用户手动完成后输入 "done" 继续
- 该脚本可集成到 Raw 仓库自动分拣流程中，定时处理微信文章链接文件
