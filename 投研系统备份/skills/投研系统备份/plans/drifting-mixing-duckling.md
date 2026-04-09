# 实时股价监控页面实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建一套实时股价监控工具，包括 Node.js 后端服务（调用 ifind MCP）和原生 HTML 前端页面，用户可管理自选股列表并实时查看股价/涨跌幅。

**Architecture:**
- **后端**：Express.js 提供 REST API，代理 ifind MCP 调用
- **前端**：单页 HTML 应用，localStorage 存储自选股列表，定时轮询后端 API
- **刷新机制**：前端每 30 秒自动刷新一次数据

**Tech Stack:** Node.js, Express, 原生 HTML/CSS/JS

---

## 文件结构

```
stock-monitor/
├── server.js              # Express 服务器，API 端点
├── package.json            # 依赖管理
├── public/
│   └── index.html          # 前端页面（单文件包含 CSS/JS）
└── README.md               # 使用说明
```

---

## Task 1: 项目初始化

**Files:**
- Create: `stock-monitor/package.json`
- Create: `stock-monitor/server.js`
- Create: `stock-monitor/public/index.html`
- Create: `stock-monitor/README.md`

- [ ] **Step 1: 创建项目目录结构**

```bash
mkdir -p stock-monitor/public
cd stock-monitor
npm init -y
```

- [ ] **Step 2: 安装依赖**

```bash
npm install express cors
```

- [ ] **Step 3: 创建 package.json**

```json
{
  "name": "stock-monitor",
  "version": "1.0.0",
  "description": "实时股价监控工具",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5"
  }
}
```

---

## Task 2: 后端服务器实现

**Files:**
- Create: `stock-monitor/server.js`

- [ ] **Step 1: 创建 server.js（调用 ifind MCP HTTP API）**

```javascript
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 3000;
const IFIND_API = 'http://localhost:3001'; // ifind MCP HTTP API 地址

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// 获取股价数据
app.post('/api/stocks', async (req, res) => {
  const { stocks } = req.body; // stocks = ['600519.SH', '000858.SZ', ...]

  if (!stocks || !Array.isArray(stocks)) {
    return res.status(400).json({ error: 'Invalid stock list' });
  }

  try {
    const results = await Promise.all(
      stocks.map(async (stockCode) => {
        try {
          // 调用 ifind MCP HTTP API
          const response = await fetch(`${IFIND_API}/mcp/tools/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              tool: 'get_stock_performance',
              parameters: {
                query: `${stockCode} 最新价 涨跌幅`
              }
            })
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          const data = await response.json();
          return {
            code: stockCode,
            success: true,
            data: data
          };
        } catch (err) {
          return {
            code: stockCode,
            success: false,
            error: err.message
          };
        }
      })
    );

    res.json({ success: true, data: results });
  } catch (error) {
    console.error('Error fetching stock data:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Stock Monitor running at http://localhost:${PORT}`);
  console.log(`Ifind MCP API: ${IFIND_API}`);
});
```

---

## Task 3: 前端页面实现

**Files:**
- Create: `stock-monitor/public/index.html`

- [ ] **Step 1: 创建 index.html（完整单文件应用）**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>自选股监控</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #1a1a2e;
      color: #eee;
      min-height: 100vh;
      padding: 20px;
    }

    .container { max-width: 900px; margin: 0 auto; }

    h1 {
      text-align: center;
      margin-bottom: 30px;
      color: #00d4ff;
    }

    /* 添加股票区域 */
    .add-stock {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
      background: #16213e;
      padding: 15px;
      border-radius: 8px;
    }

    .add-stock input {
      flex: 1;
      padding: 10px;
      border: 1px solid #0f3460;
      border-radius: 4px;
      background: #1a1a2e;
      color: #eee;
      font-size: 14px;
    }

    .add-stock button {
      padding: 10px 20px;
      background: #00d4ff;
      color: #1a1a2e;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
    }

    .add-stock button:hover { background: #00a8cc; }

    /* 股票表格 */
    .stock-table {
      width: 100%;
      border-collapse: collapse;
      background: #16213e;
      border-radius: 8px;
      overflow: hidden;
    }

    .stock-table th, .stock-table td {
      padding: 12px 15px;
      text-align: left;
      border-bottom: 1px solid #0f3460;
    }

    .stock-table th {
      background: #0f3460;
      color: #00d4ff;
      font-weight: 600;
    }

    .stock-table tr:last-child td { border-bottom: none; }
    .stock-table tr:hover { background: #1f2b47; }

    .stock-code { color: #888; font-size: 13px; }

    .price { font-size: 18px; font-weight: bold; }

    .change-up { color: #ff4757; }
    .change-down { color: #2ed573; }
    .change-flat { color: #888; }

    .delete-btn {
      background: transparent;
      border: 1px solid #ff4757;
      color: #ff4757;
      padding: 5px 10px;
      border-radius: 4px;
      cursor: pointer;
    }

    .delete-btn:hover { background: #ff4757; color: #fff; }

    /* 刷新按钮 */
    .refresh-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
    }

    .refresh-btn {
      padding: 8px 16px;
      background: #0f3460;
      color: #00d4ff;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }

    .refresh-btn:hover { background: #1a4a7a; }

    .last-update { color: #666; font-size: 13px; }

    .loading { text-align: center; padding: 20px; color: #00d4ff; }

    .empty-state {
      text-align: center;
      padding: 40px;
      color: #666;
    }

    /* 错误提示 */
    .error-msg {
      background: rgba(255, 71, 87, 0.2);
      border: 1px solid #ff4757;
      color: #ff4757;
      padding: 10px;
      border-radius: 4px;
      margin-bottom: 15px;
    }

    /* 闪烁动画 */
    @keyframes flash {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    .loading { animation: flash 1s infinite; }
  </style>
</head>
<body>
  <div class="container">
    <h1>自选股监控</h1>

    <!-- 错误提示 -->
    <div id="error-msg" class="error-msg" style="display:none;"></div>

    <!-- 添加股票 -->
    <div class="add-stock">
      <input type="text" id="stock-input" placeholder="输入股票代码，如：600519.SH (茅台)" />
      <button onclick="addStock()">添加</button>
    </div>

    <!-- 刷新栏 -->
    <div class="refresh-bar">
      <button class="refresh-btn" onclick="fetchStockData()">刷新数据</button>
      <span id="last-update" class="last-update"></span>
    </div>

    <!-- 股票列表 -->
    <div id="content">
      <div class="empty-state">暂无自选股，请添加股票代码</div>
    </div>
  </div>

  <script>
    const API_URL = 'http://localhost:3000/api/stocks';
    let watchlist = JSON.parse(localStorage.getItem('watchlist') || '[]');
    let updateTimer = null;

    // 初始化
    document.addEventListener('DOMContentLoaded', () => {
      renderWatchlist();
      if (watchlist.length > 0) {
        fetchStockData();
        startAutoUpdate();
      }

      // 回车添加
      document.getElementById('stock-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addStock();
      });
    });

    // 添加股票
    function addStock() {
      const input = document.getElementById('stock-input');
      const code = input.value.trim().toUpperCase();

      if (!code) return alert('请输入股票代码');

      // 格式校验
      const validFormat = /^[0-9]{6}\.(SH|SZ|BJ|HK)$/.test(code);
      if (!validFormat) {
        return alert('格式错误，示例：600519.SH、000858.SZ、920116.BJ、01316.HK');
      }

      if (watchlist.includes(code)) {
        return alert('该股票已在列表中');
      }

      watchlist.push(code);
      saveWatchlist();
      input.value = '';
      renderWatchlist();
      fetchStockData();
      startAutoUpdate();
    }

    // 删除股票
    function removeStock(code) {
      watchlist = watchlist.filter(s => s !== code);
      saveWatchlist();
      renderWatchlist();
      if (watchlist.length === 0) {
        stopAutoUpdate();
        document.getElementById('content').innerHTML = '<div class="empty-state">暂无自选股，请添加股票代码</div>';
      }
    }

    // 保存自选股列表
    function saveWatchlist() {
      localStorage.setItem('watchlist', JSON.stringify(watchlist));
    }

    // 渲染自选股列表
    function renderWatchlist() {
      const container = document.getElementById('content');

      if (watchlist.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无自选股，请添加股票代码</div>';
        return;
      }

      const rows = watchlist.map(code => `
        <tr id="row-${code}">
          <td>
            <strong>${getStockName(code)}</strong>
            <div class="stock-code">${code}</div>
          </td>
          <td class="price" id="price-${code}">--</td>
          <td id="change-${code}" class="change-flat">--</td>
          <td><button class="delete-btn" onclick="removeStock('${code}')">删除</button></td>
        </tr>
      `).join('');

      container.innerHTML = `
        <table class="stock-table">
          <thead>
            <tr>
              <th>股票</th>
              <th>最新价</th>
              <th>涨跌幅</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }

    // 股票代码映射（示例，可扩展）
    const stockNames = {
      '600519.SH': '贵州茅台',
      '000858.SZ': '五粮液',
      '920116.BJ': '星图测控',
      '01316.HK': '耐世特',
      '002594.SZ': '比亚迪',
      '300750.SZ': '宁德时代',
      '603786.SH': '科博达',
      '601799.SH': '星宇股份'
    };

    function getStockName(code) {
      return stockNames[code] || code;
    }

    // 获取股价数据
    async function fetchStockData() {
      if (watchlist.length === 0) return;

      const errorDiv = document.getElementById('error-msg');
      errorDiv.style.display = 'none';

      // 显示加载状态
      document.getElementById('content').innerHTML = `
        <table class="stock-table">
          <thead>
            <tr><th>股票</th><th>最新价</th><th>涨跌幅</th><th>操作</th></tr>
          </thead>
          <tbody>
            ${watchlist.map(code => `
              <tr id="row-${code}">
                <td><strong>${getStockName(code)}</strong><div class="stock-code">${code}</div></td>
                <td class="price" id="price-${code}"><span class="loading">加载中...</span></td>
                <td id="change-${code}" class="change-flat">--</td>
                <td><button class="delete-btn" onclick="removeStock('${code}')">删除</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;

      try {
        const response = await fetch(API_URL, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ stocks: watchlist })
        });

        const result = await response.json();

        if (!result.success) {
          throw new Error(result.error || '获取数据失败');
        }

        // 更新表格数据
        result.data.forEach(item => {
          if (item.success && item.data) {
            updateStockRow(item.code, item.data);
          } else {
            document.getElementById(`price-${item.code}`).textContent = '获取失败';
          }
        });

        document.getElementById('last-update').textContent =
          `最后更新: ${new Date().toLocaleTimeString('zh-CN')}`;

      } catch (error) {
        console.error('Fetch error:', error);
        errorDiv.textContent = `连接失败: ${error.message}（请确保后端服务已启动）`;
        errorDiv.style.display = 'block';
        renderWatchlist();
      }
    }

    // 更新单只股票行
    function updateStockRow(code, data) {
      const priceEl = document.getElementById(`price-${code}`);
      const changeEl = document.getElementById(`change-${code}`);

      if (!priceEl || !changeEl) return;

      const price = data.price || data.最新价 || '--';
      const change = data.change || data.涨跌幅 || data.涨跌额 || '--';

      priceEl.textContent = price;

      // 格式化涨跌幅
      if (change !== '--') {
        const changeNum = parseFloat(change);
        const changeStr = changeNum >= 0 ? `+${changeNum.toFixed(2)}%` : `${changeNum.toFixed(2)}%`;

        changeEl.textContent = changeStr;
        changeEl.className = changeNum > 0 ? 'change-up' :
                             changeNum < 0 ? 'change-down' : 'change-flat';
      } else {
        changeEl.textContent = '--';
        changeEl.className = 'change-flat';
      }
    }

    // 自动更新（每30秒）
    function startAutoUpdate() {
      stopAutoUpdate();
      updateTimer = setInterval(fetchStockData, 30000);
    }

    function stopAutoUpdate() {
      if (updateTimer) {
        clearInterval(updateTimer);
        updateTimer = null;
      }
    }
  </script>
</body>
</html>
```

---

## Task 4: ifind MCP 集成

**Files:**
- Modify: `stock-monitor/server.js`

- [ ] **Step 1: 更新 server.js 以调用 ifind MCP**

ifind MCP 提供的是 Node.js 工具调用能力，需通过 MCP 协议交互。由于 MCP 运行在独立的 Claude Code 进程中，server.js 需要通过 HTTP 调用已运行的 MCP 服务器。

**方案 A：使用 MCP HTTP 接口（如果 ifind MCP 提供）**
**方案 B：直接使用 ifind 备用脚本**

```javascript
// 在 server.js 中添加通过 Node.js 调用 ifind 的能力
const { call } = require('./call-node.js');

// 替换 fetchStockData 中的调用逻辑
async function getStockDataFromIfind(stockCode) {
  try {
    const result = await call('stock', 'get_stock_performance', {
      query: `${stockCode} 最新价 涨跌幅 成交量`
    });
    return result;
  } catch (err) {
    console.error(`Failed to fetch ${stockCode}:`, err.message);
    return null;
  }
}
```

---

## Task 5: 测试验证

- [ ] **Step 1: 安装依赖并启动服务**

```bash
cd stock-monitor
npm install
node server.js
```

- [ ] **Step 2: 打开浏览器访问**

```
http://localhost:3000
```

- [ ] **Step 3: 添加测试股票**

尝试添加 `600519.SH`、`000858.SZ` 等

- [ ] **Step 4: 验证数据刷新**

点击"刷新数据"按钮，观察是否获取到最新股价

---

## 验证清单

- [ ] 页面可正常加载，无 JS 错误
- [ ] 可添加股票到自选列表
- [ ] 可删除股票
- [ ] 自选股列表在刷新后保持（localStorage）
- [ ] 股价数据正确显示（最新价、涨跌幅）
- [ ] 涨跌幅颜色正确（红涨绿跌）
- [ ] 错误处理正常（后端未启动时提示）
- [ ] 自动刷新功能正常（30秒间隔）
