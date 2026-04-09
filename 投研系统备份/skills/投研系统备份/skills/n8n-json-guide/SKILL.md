# n8n JSON 最佳实践指南

解决 n8n 工作流无法显示连线或节点不连接的问题。

## 🎯 最常见的错误

### 错误1：connections中使用了错误的字段

**症状**：工作流导入后，节点在画布上但互不相连，看不到连线

**原因**：你指向节点用的是 `id` 或 `type`，而不是 `name`

```json
❌ 错误
{
  "nodes": [
    {"id": "schedule-1", "name": "Schedule Trigger", ...},
    {"id": "http-1", "name": "Fetch News", ...}
  ],
  "connections": {
    "Schedule Trigger": {
      "main": [[
        {"node": "http-1", ...}  ← ❌ 用的是id
      ]]
    }
  }
}

✅ 正确
{
  "connections": {
    "Schedule Trigger": {        ← 源节点的name
      "main": [[
        {"node": "Fetch News", ...}  ← ✅ 目标节点的name
      ]]
    }
  }
}
```

**规则**：connections中的node字段 = 目标节点的name属性

### 错误2：HTTP Request参数结构错误

**症状**：HTTP节点无法发送查询参数

**原因**：HTTP Request的queryParameters结构在不同版本差异大

```json
❌ typeVersion 3 不能用这个结构
{
  "queryParameters": {
    "values": [      ← ❌ values是v4+的
      {"name": "q", "value": "test"}
    ]
  }
}

✅ typeVersion 3 要用这个
{
  "queryParameters": {
    "parameters": [   ← ✅ v3用parameters
      {"name": "q", "value": "test"}
    ]
  }
}
```

**版本对应表**：
- HTTP v2：`parameters: []`
- HTTP v3：`parameters: { parameters: [] }`
- HTTP v4+：`values: []`

### 错误3：大小写或空格不匹配

**症状**：连线仍然失效，看起来一切都正确

**原因**：节点名字大小写或空格不一样

```json
❌ 不匹配
"Schedule Trigger"  vs  "schedule trigger"  (大小写)
"Fetch News"        vs  "Fetch News "       (多了空格)

✅ 必须完全一致
节点定义: "name": "Fetch Finance News"
connections: "node": "Fetch Finance News"  (完全相同)
```

## 🔧 快速修复清单

导入工作流失败，按这个顺序检查：

1. **检查connections中的node字段**
   ```bash
   在JSON中搜索 "connections"
   确保每个"node"值都等于某个节点的"name"值
   ```

2. **检查node值的大小写和空格**
   ```bash
   逐字对比：
   - 节点定义中的 "name" 值
   - connections中的 "node" 值
   必须完全一样
   ```

3. **检查HTTP节点的queryParameters**
   ```bash
   如果是 typeVersion 3：
   用 "parameters": { "parameters": [...] }
   
   如果是 typeVersion 4+：
   用 "values": [...]
   ```

4. **检查JSON格式**
   ```bash
   粘贴到 https://jsonlint.com 验证
   确保没有语法错误
   ```

## 📋 n8n JSON connections 正确写法

### 基础结构

```json
{
  "connections": {
    "节点A的name": {
      "main": [[
        {
          "node": "节点B的name",
          "type": "main",
          "index": 0
        }
      ]]
    },
    "节点B的name": {
      "main": [[
        {
          "node": "节点C的name",
          "type": "main",
          "index": 0
        }
      ]]
    }
  }
}
```

### 完整例子

```json
{
  "name": "Example Workflow",
  "nodes": [
    {
      "id": "trigger-123",
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      ...
    },
    {
      "id": "http-456",
      "name": "Get Data",
      "type": "n8n-nodes-base.httpRequest",
      ...
    },
    {
      "id": "set-789",
      "name": "Format",
      "type": "n8n-nodes-base.set",
      ...
    }
  ],
  "connections": {
    "Schedule Trigger": {          ← 节点1的name
      "main": [[
        {"node": "Get Data", "type": "main", "index": 0}  ← 指向节点2
      ]]
    },
    "Get Data": {                  ← 节点2的name
      "main": [[
        {"node": "Format", "type": "main", "index": 0}    ← 指向节点3
      ]]
    }
  }
}
```

## 💡 记住这3条规则

1. **connections的键 = 源节点的name**
2. **"node"字段 = 目标节点的name**
3. **必须精确匹配（大小写、空格都要对）**

不要用：id、type、position或其他属性

## 🆘 还是不行？

1. 使用JSON验证工具检查格式
2. 复制一个已知正常的工作流JSON，对比你的
3. 在n8n UI中手动创建一个简单工作流，导出JSON看格式
4. 搜索 n8n-json-guide skill 查看最新版本

## 参考资源

- n8n官方文档：https://docs.n8n.io/
- 本skill最后更新：2026-04-04
- 相关memory：feedback_n8n_json_connections.md
