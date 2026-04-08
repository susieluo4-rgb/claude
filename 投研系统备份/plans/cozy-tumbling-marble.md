# 计划：n8n 工作流自动生成 Excel 打分表

## Context

用户有两个 n8n 工作流，分别生成 4 类 AI 分析报告（TXT 格式）：
- **Porter & RF & ESG** (ID: `N4pl9SISnSX8vjn4`) → `ESG.txt` + `QL&RF.txt`
- **Industry & Porter** (ID: `gbenfpcR3yCR1371`) → `Industry.txt` + `Portet Model.txt`

目前这 4 个 TXT 仅存在于 n8n 内存，没有保存到磁盘，也没有自动触发 Excel 生成。

现有的 Python 脚本 `auto_fill_score.py` 已经能将 4 个 TXT 转换为 Excel 打分表（基于模板 `打分—新V 2.1.3.xlsx`），但路径是硬编码的。

**目标**：两个工作流运行完毕后，自动触发 Python 脚本，生成 `{公司名}--打分.xlsx` 到本地文件夹，用户只需做数据 lookup 完成填表。

---

## 关键文件

| 文件 | 路径 |
|------|------|
| Python 脚本 | `/Users/zhuang225/Research/自动化 测试/auto_fill_score.py` |
| Excel 模板 | `/Users/zhuang225/Research/自动化 测试/打分—新V 2.1.3.xlsx` |
| HTTP Bridge | `/Users/zhuang225/Desktop/n8n-workflow/ifind-api-bridge.js` |
| Python 路径 | `/opt/homebrew/bin/python3` |

---

## 实施步骤

### Step 1：修改 `auto_fill_score.py`（6 处改动，仅文件头）

用环境变量替换硬编码路径，保持向后兼容（不传环境变量时行为不变）：

```python
# 第6-8行：替换 BASE/TPLT/DONE
BASE = os.environ.get("SCORE_BASE", "/Users/zhuang225/Research/自动化 测试")
TPLT = os.environ.get("SCORE_TPLT", os.path.join(BASE, "打分—新V 2.1.3.xlsx"))
DONE = os.environ.get("SCORE_DONE", os.path.join(BASE, "打分—新V 2.1.3_自动填充.xlsx"))

# 第46行 ESG open() 改为：
with open(os.environ.get("SCORE_ESG", os.path.join(BASE,"ESG - 2026-03-04T091324.733.txt")), encoding="utf-8") as f:

# 第173行 Industry open() 改为：
with open(os.environ.get("SCORE_IND", os.path.join(BASE,"Industry - 2026-03-04T091340.034.txt")), encoding="utf-8") as f:

# 第223行 Porter open() 改为：
with open(os.environ.get("SCORE_PORT", os.path.join(BASE,"Portet Model - 2026-03-04T091336.268.txt")), encoding="utf-8") as f:

# 第356行 QL&RF open() 改为：
with open(os.environ.get("SCORE_QL", os.path.join(BASE,"QL&RF - 2026-03-04T091330.666.txt")), encoding="utf-8") as f:
```

并在脚本末尾（`wb.save(DONE)` 处）将 `DONE` 替换为 `os.environ.get("SCORE_OUT", DONE)`。

---

### Step 2：在 Bridge 添加新端点 `/api/txt-to-excel`

在 `/Users/zhuang225/Desktop/n8n-workflow/ifind-api-bridge.js` 第 113 行（`// 404` 之前）插入：

```javascript
// ─── /api/txt-to-excel ────────────────────────────────────────────────
if (pathname === '/api/txt-to-excel' && req.method === 'POST') {
  let body = '';
  req.on('data', chunk => { body += chunk.toString(); });
  req.on('end', () => {
    try {
      const { company, esg, industry, porter, qlrf } = JSON.parse(body);
      const { execFile } = require('child_process');
      const fs = require('fs');

      // ── 状态缓存（等待两个工作流都完成）
      if (!global._txtCache) global._txtCache = {};
      const key = (company || 'unknown').trim();
      if (!global._txtCache[key]) global._txtCache[key] = { arrivedAt: Date.now() };
      const cache = global._txtCache[key];
      if (esg)      cache.esg = esg;
      if (qlrf)     cache.qlrf = qlrf;
      if (industry) cache.industry = industry;
      if (porter)   cache.porter = porter;

      const ready = cache.esg && cache.qlrf && cache.industry && cache.porter;
      if (!ready) {
        const have = Object.keys(cache).filter(k => k !== 'arrivedAt');
        console.log(`[txt-to-excel] ${key}: 收到 ${have.join(',')}，等待剩余文件...`);
        res.writeHead(202);
        res.end(JSON.stringify({ success: true, status: 'waiting', have }));
        return;
      }

      // ── 四份全到：写 TXT 到磁盘
      const base = '/Users/zhuang225/Research/自动化 测试';
      const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const files = {
        esg:     `${base}/ESG_n8n_${ts}.txt`,
        ind:     `${base}/Industry_n8n_${ts}.txt`,
        porter:  `${base}/Portet Model_n8n_${ts}.txt`,
        qlrf:    `${base}/QL&RF_n8n_${ts}.txt`,
      };
      fs.writeFileSync(files.esg,    cache.esg,      'utf8');
      fs.writeFileSync(files.ind,    cache.industry, 'utf8');
      fs.writeFileSync(files.porter, cache.porter,   'utf8');
      fs.writeFileSync(files.qlrf,   cache.qlrf,     'utf8');
      delete global._txtCache[key];

      // ── 运行 Python 脚本
      const outPath = `${base}/${key}--打分.xlsx`;
      const env = {
        ...process.env,
        SCORE_ESG:  files.esg,
        SCORE_IND:  files.ind,
        SCORE_PORT: files.porter,
        SCORE_QL:   files.qlrf,
        SCORE_TPLT: `${base}/打分—新V 2.1.3.xlsx`,
        SCORE_OUT:  outPath,
      };
      execFile('/opt/homebrew/bin/python3',
        ['/Users/zhuang225/Research/自动化 测试/auto_fill_score.py'],
        { env, timeout: 120000 },
        (err, stdout, stderr) => {
          if (err) {
            console.error('[txt-to-excel] 错误:', stderr);
            res.writeHead(500);
            res.end(JSON.stringify({ success: false, error: err.message, stderr }));
            return;
          }
          console.log(`[txt-to-excel] Excel 已生成: ${outPath}`);
          res.writeHead(200);
          res.end(JSON.stringify({ success: true, outputPath: outPath }));
        });
    } catch (e) {
      res.writeHead(400);
      res.end(JSON.stringify({ success: false, error: e.message }));
    }
  });
  return;
}
```

并在 `server.listen()` 之后添加超时清理（防止孤儿缓存）：

```javascript
setInterval(() => {
  if (!global._txtCache) return;
  const now = Date.now();
  for (const [k, v] of Object.entries(global._txtCache)) {
    if (now - v.arrivedAt > 2 * 60 * 60 * 1000) {
      console.log(`[txt-to-excel] 清理超时缓存: ${k}`);
      delete global._txtCache[k];
    }
  }
}, 30 * 60 * 1000);
```

---

### Step 3：修改工作流 1（Porter & RF & ESG）

节点连接改动如下：

```
原来：
  Code in JavaScript5 → Convert to File2 (QL&RF)
  Code in JavaScript7 → Convert to File3 (ESG)

修改后：
  Code in JavaScript5 → Convert to File2 (QL&RF)
                      └──→ MergeForBridge[input 0]
  Code in JavaScript7 → Convert to File3 (ESG)
                      └──→ MergeForBridge[input 1]
                               ↓
                        HTTP Request → Bridge
```

**MergeForBridge 节点配置**：
- Type: `n8n-nodes-base.merge`
- mode: `combine`, combinationMode: `mergeByIndex`

**HTTP Request 节点配置**：
- Method: POST
- URL: `http://localhost:3001/api/txt-to-excel`
- Body (JSON):
```json
{
  "company": "={{ $('On form submission').first().json['Company'] }}",
  "qlrf": "={{ $input.all()[0].json.mergedText }}",
  "esg":  "={{ $input.all()[1].json.mergedText }}"
}
```
- Options → 勾选 "Continue On Fail"（202 响应不中断流程）

---

### Step 4：修改工作流 2（Industry & Porter）

```
原来：
  Code in JavaScript3 → Convert to File1 (Industry)
  Code in JavaScript2 → Convert to File4 (Portet Model)

修改后：
  Code in JavaScript3 → Convert to File1 (Industry)
                      └──→ MergeForBridge[input 0]
  Code in JavaScript2 → Convert to File4 (Portet Model)
                      └──→ MergeForBridge[input 1]
                               ↓
                        HTTP Request → Bridge
```

**HTTP Request Body**：
```json
{
  "company":  "={{ $('On form submission').first().json['Company'] }}",
  "industry": "={{ $input.all()[0].json.mergedText }}",
  "porter":   "={{ $input.all()[1].json.mergedText }}"
}
```

---

## 架构逻辑

```
工作流1 完成 → POST /api/txt-to-excel {esg, qlrf, company}
  Bridge 收到 → 缓存，返回 202 等待

工作流2 完成 → POST /api/txt-to-excel {industry, porter, company}
  Bridge 收到 → 四份齐全，写 TXT，运行 Python，返回 200 + Excel 路径

Excel 保存到 → /Users/zhuang225/Research/自动化 测试/{公司名}--打分.xlsx
```

两个工作流无论哪个先完成，最后完成的那个触发 Excel 生成。**公司名（Company 表单字段）** 作为配对 key，两个工作流输入相同公司名即可自动配对。

---

## 验证方式

1. 重启 Bridge：`cd /Users/zhuang225/Desktop/n8n-workflow && node ifind-api-bridge.js`
2. 用 curl 模拟两次请求（第一次返回 202，第二次返回 200 + Excel 路径）
3. 运行两个 n8n 工作流（同一公司名），检查 Excel 是否生成到 `自动化 测试/` 目录
4. 打开 Excel，验证各字段是否正确填入（ESG 评分、QL&RF 数值、Industry 数据、Porter 五力分）

---

## 注意事项

- Python 脚本中 `INDUSTRY_HEADERS` / `PORTER_HEADERS` 包含行业名称（如"云南锗业"），切换公司时可能需要手动更新，这部分不在本次范围内
- Bridge 的 `global._txtCache` 在进程重启后清空；两个工作流应在同一次 Bridge 会话内运行
