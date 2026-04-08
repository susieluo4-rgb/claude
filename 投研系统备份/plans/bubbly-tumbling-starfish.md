# n8n-nodes-claude-code-cli 插件分析

## 概述

这是一个 n8n 社区节点包，将 Claude Code CLI 集成到 n8n 工作流自动化平台中。

- **仓库**: https://github.com/ThomasTartrau/n8n-nodes-claude-code-cli
- **版本**: 1.8.0
- **许可证**: MIT
- **节点**: `n8n-nodes-base.claudeCode`
- **分类**: AI, Development / Agents, Tools

---

## 项目结构

```
n8n-nodes-claude-code-cli/
├── index.ts                          # 主入口，导出所有节点和凭证
├── credentials/                      # 凭证定义（5种连接模式）
│   ├── ClaudeCodeLocalApi.credentials.ts
│   ├── ClaudeCodeSshApi.credentials.ts
│   ├── ClaudeCodeDockerApi.credentials.ts
│   ├── ClaudeCodeK8sApi.credentials.ts
│   ├── ClaudeCodeK8sPersistentApi.credentials.ts
│   └── k8sSharedProperties.ts
├── nodes/ClaudeCode/
│   ├── ClaudeCode.node.ts            # 主节点实现
│   ├── ClaudeCode.node.json          # 节点元数据
│   ├── descriptions/                # UI字段定义
│   ├── interfaces/
│   │   └── ClaudeCodeTypes.ts
│   ├── transport/                   # 执行策略模式
│   │   ├── ExecutorFactory.ts        # 工厂模式创建执行器
│   │   ├── LocalExecutor.ts          # 本地 child_process 执行
│   │   ├── SshExecutor.ts            # SSH 远程执行
│   │   ├── DockerExecutor.ts         # Docker exec 执行
│   │   ├── K8sEphemeralExecutor.ts   # K8s 临时 Pod
│   │   ├── K8sPersistentExecutor.ts  # K8s 持久化 Worker Pod
│   │   └── k8s/
│   └── utils/
│       ├── commandBuilder.ts         # 构建 Claude CLI 命令
│       ├── outputParser.ts           # 解析 JSON/stream-json 输出
│       └── optionsBuilder.ts
└── tests/
```

---

## 核心架构

### 执行器模式（Transport/Executor Pattern）

```
ExecutorFactory.createExecutor(connectionMode)
    ├── LocalExecutor      → child_process.spawn 本地执行
    ├── SshExecutor         → ssh2 远程 SSH 执行
    ├── DockerExecutor      → docker exec 容器内执行
    ├── K8sEphemeralExecutor → 每次创建新 Pod，执行后删除
    └── K8sPersistentExecutor → 维护长运行 Pod，复用执行
```

### 执行流程

1. 用户在 n8n 中配置凭证（5种连接模式）
2. 用户添加 Claude Code 节点，配置操作和参数
3. `ClaudeCode.node.ts` 提取参数和凭证
4. `ExecutorFactory` 创建对应执行器
5. 执行器运行 Claude Code CLI
6. `outputParser` 解析输出并标准化返回

---

## 5 种连接模式

| 模式 | 说明 |
|------|------|
| **Local** | Claude Code 与 n8n 同机运行 |
| **SSH Remote** | 通过 SSH 在远程机器执行 |
| **Docker Exec** | 在另一个 Docker 容器内执行 |
| **K8s Ephemeral Pod** | 每次执行创建新 Pod，执行后删除 |
| **K8s Persistent Pod** | 维护长运行 Worker Pod，复用 |

---

## 4 种操作类型

| 操作 | 说明 |
|------|------|
| **Execute Prompt** | 发送提示词获取响应 |
| **Execute with Context** | 包含文件/目录作为上下文 |
| **Continue Session** | 继续最近的对话 |
| **Resume Session** | 恢复指定 ID 的会话 |

---

## 关键参数

- **Model**: Opus / Sonnet / Haiku 或指定版本
- **Output Format**: JSON / Text / Stream JSON
- **Timeout**: 最大执行时间（默认 300s，最大 3600s）
- **Permission Mode**: default, acceptEdits, plan, dontAsk, bypassPermissions, delegate
- **Tool Permissions**: 细粒度工具权限控制（如 `Bash(rm:*)`, `Read(.env)`）
- **Max Turns**: 对话轮次限制
- **Max Budget (USD)**: 成本控制
- **JSON Schema**: 结构化输出验证
- **Extended Context**: 启用 1M token 上下文窗口
- **Worktree Isolation**: Git worktree 隔离执行
- **Reasoning Effort**: low / medium / high
- **Subagents**: 自定义 Agent 定义用于委托
- **MCP Servers**: MCP 服务器配置（stdio 或 HTTP 传输）

---

## 输出格式

```json
{
  "success": true,
  "sessionId": "uuid",
  "output": "响应文本",
  "exitCode": 0,
  "duration": 15234,
  "cost": 0.0523,
  "numTurns": 3,
  "usage": { "inputTokens": 1250, "outputTokens": 890 }
}
```

---

## 依赖

| 依赖 | 用途 |
|------|------|
| `n8n-workflow` | peer dependency |
| `@kubernetes/client-node` | K8s 执行器 |
| `ssh2` | SSH 执行器（动态加载） |

---

## 应用场景

1. **自动化代码审查** - 将 Claude Code 集成到 CI/CD 流程
2. **工作流驱动的开发任务** - n8n 触发 Claude Code 执行任务
3. **跨环境执行** - 本地/SSH/Docker/K8s 多种部署方式
4. **成本追踪** - 每次执行记录 token 消耗和成本
5. **会话管理** - 多轮对话和会话恢复
