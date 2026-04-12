#!/usr/bin/env node
/**
 * 微信公众号文章抓取工具
 *
 * 用法:
 *   node fetch_article.js <url> [output_path]
 *
 * 示例:
 *   node fetch_article.js "https://mp.weixin.qq.com/s/xxxxx"
 *   node fetch_article.js "https://mp.weixin.qq.com/s/xxxxx" ~/Desktop/article.md
 *
 * 依赖: playwright (npm install playwright)
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const os = require('os');

// --- 参数解析 ---
const articleUrl = process.argv[2];
if (!articleUrl) {
  console.error('用法: node fetch_article.js <wechat-article-url> [output_path]');
  console.error('示例: node fetch_article.js "https://mp.weixin.qq.com/s/xxxxx"');
  process.exit(1);
}

const homeDir = os.homedir();
const defaultOutput = path.join(homeDir, 'Research/Vault_共享知识库/微信文章抓取.md');
const outputPath = process.argv[3] ? path.resolve(process.argv[3]) : defaultOutput;

// 确保输出目录存在
const outputDir = path.dirname(outputPath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// 使用临时目录作为 Chrome profile
const userDataDir = path.join(os.tmpdir(), 'wechat-article-fetch-' + Date.now());
fs.mkdirSync(userDataDir, { recursive: true });

// --- 终端交互辅助函数 ---
function waitForUser(prompt) {
  return new Promise((resolve) => {
    const rl = require('readline').createInterface({ input: process.stdin, output: process.stdout });
    rl.question(prompt, (answer) => { rl.close(); resolve(answer.trim().toLowerCase()); });
  });
}

// --- 主流程 ---
(async () => {
  console.log('=== 微信公众号文章抓取工具 ===');
  console.log(`📎 链接: ${articleUrl}`);
  console.log('📂 输出: ' + outputPath);
  console.log('正在启动 Chrome 窗口...\n');

  const browser = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    viewport: { width: 1280, height: 900 },
    locale: 'zh-CN',
    userAgent:
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  });

  const page = await browser.pages()[0];

  // ---- Step 1: 打开文章 ----
  console.log('📌 Step 1/3: 正在加载文章页面...');
  await page.goto(articleUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(3000);

  // ---- Step 2: 检测验证 ----
  let needsVerification = await page.evaluate(() => {
    const text = document.body.innerText;
    return text.includes('环境异常') || text.includes('验证码') || text.includes('captcha');
  });

  let attempts = 0;
  const maxAttempts = 3;

  while (needsVerification && attempts < maxAttempts) {
    attempts++;
    console.log(`\n⚠️  需要验证 (尝试 ${attempts}/${maxAttempts})`);
    console.log('   请在弹出的浏览器窗口中完成验证');

    await waitForUser('   完成后输入 "done" 继续 (或 "quit" 退出): ');
    console.log('\n📌 等待页面加载...');
    await page.waitForTimeout(5000);

    needsVerification = await page.evaluate(() => {
      return document.body.innerText.includes('环境异常');
    });
  }

  if (needsVerification) {
    console.log('\n❌ 验证失败次数过多，请手动复制链接到浏览器打开');
    await browser.close();
    cleanup();
    process.exit(1);
  }

  if (attempts > 0) {
    console.log('✅ 验证通过！');
  } else {
    console.log('✅ 页面加载成功，无需验证');
  }

  // ---- Step 3: 提取内容 ----
  console.log('\n📌 Step 2/3: 正在提取文章内容...');

  const content = await extractContent(page);

  // 如果提取失败，提供重试
  if (!content.bodyText) {
    console.log('❌ 未找到文章正文容器');
    console.log(`   当前页面标题: ${content.title}`);

    const answer = await waitForUser('   确认页面正确后输入 "done" 重试，或 "quit" 退出: ');
    if (answer === 'quit') {
      await browser.close();
      cleanup();
      process.exit(0);
    }

    await page.waitForTimeout(3000);
    const retry = await extractContent(page);
    if (retry.bodyText) {
      Object.assign(content, retry);
    } else {
      console.log('\n❌ 仍无法提取正文，建议手动复制内容');
      await browser.close();
      cleanup();
      process.exit(1);
    }
  }

  // ---- 保存 ----
  console.log('\n📌 Step 3/3: 正在保存...');
  console.log(`📝 标题: ${content.title}`);
  console.log(`👤 作者: ${content.author || '未知'}`);
  console.log(`📅 时间: ${content.publishTime || '未知'}`);
  console.log(`📄 字数: ${content.bodyText.length} 字`);
  if (content.images.length > 0) {
    console.log(`🖼️ 图片: ${content.images.length} 张`);
  }

  const markdown = buildMarkdown(content, articleUrl);
  fs.writeFileSync(outputPath, markdown, 'utf-8');

  console.log(`\n💾 已保存: ${outputPath}`);
  console.log('\n--- 前 500 字预览 ---');
  console.log(content.bodyText.substring(0, 500) + '...\n');

  await browser.close();
  cleanup();
  console.log('✅ 全部完成！');
})();

// --- 提取函数 ---
async function extractContent(page) {
  return page.evaluate(() => {
    const title =
      document.querySelector('#activity-name')?.innerText?.trim() ||
      document.querySelector('.rich_media_title')?.innerText?.trim() ||
      document.title?.trim() || '';

    const author =
      document.querySelector('#js_name')?.innerText?.trim() ||
      document.querySelector('.rich_media_meta_nickname')?.innerText?.trim() ||
      '';

    const publishTime =
      document.querySelector('#publish_time')?.innerText?.trim() ||
      document.querySelector('.rich_media_meta_text')?.innerText?.trim() ||
      '';

    const bodyEl =
      document.querySelector('#js_content') ||
      document.querySelector('.rich_media_content');

    if (!bodyEl) {
      return { title, author, publishTime, bodyText: null, images: [], url: window.location.href };
    }

    const bodyText = bodyEl.innerText;

    const images = [];
    bodyEl.querySelectorAll('img').forEach((img) => {
      const src = img.getAttribute('data-src') || img.getAttribute('src');
      if (src && !images.includes(src)) images.push(src);
    });

    return { title, author, publishTime, bodyText, images, url: window.location.href };
  });
}

// --- Markdown 生成 ---
function buildMarkdown(content, sourceUrl) {
  const now = new Date().toISOString().slice(0, 19);

  let md = `---
title: "${content.title || '微信文章'}"
author: "${content.author || '未知'}"
publish_time: "${content.publishTime || '未知'}"
source_url: "${content.url || sourceUrl}"
captured_at: "${now}"
tags: [微信文章, 投研]
---

# ${content.title}

**作者**: ${content.author || '未知'}
**发布时间**: ${content.publishTime || '未知'}
**原文链接**: ${content.url || sourceUrl}

---

${content.bodyText}
`;

  if (content.images.length > 0) {
    md += `\n## 图片来源 (${content.images.length} 张)\n`;
    content.images.forEach((url, i) => {
      md += `- ![图片 ${i + 1}](${url})\n`;
    });
  }

  return md;
}

// --- 清理临时目录 ---
function cleanup() {
  try {
    fs.rmSync(userDataDir, { recursive: true, force: true });
  } catch (e) {
    // ignore
  }
}
