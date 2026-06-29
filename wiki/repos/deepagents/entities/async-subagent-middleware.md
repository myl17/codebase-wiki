---
type: entity
repo: deepagents
slug: async-subagent-middleware
problem: 如何让主 Agent 在远程服务器上启动、监控和更新后台异步子 Agent 任务
generated: 2026-06-28
source_files:
  - deepagents/middleware/async_subagents.py
---

# Async SubAgent Middleware

**代码位置**：`deepagents/middleware/async_subagents.py`
**这个模块解决什么问题**：
- 实现层：通过 `AsyncSubAgentMiddleware` 提供 start_async_task、check_async_task、update_async_task、cancel_async_task、list_async_tasks 五个工具，通过 LangGraph SDK 连接远程 Agent Protocol 服务器执行后台子代理
- 问题层：如何在 Agent 需要执行长时间运行的任务时，不阻塞主 Agent 的交互循环，而是将任务异步派发到远程服务器并在需要时查询状态和结果

**对外暴露什么**：
- `AsyncSubAgentMiddleware` 类 -- `deepagents/middleware/async_subagents.py:862`
- `AsyncSubAgent` TypedDict -- `deepagents/middleware/async_subagents.py:34`
- `AsyncSubAgentState` 状态类 -- `deepagents/middleware/async_subagents.py:123`

**它和谁交互**：
- 依赖 `langgraph_sdk`（外部库，Agent Protocol 客户端）
- 被 [[entities/agent-graph-assembly]] 组装进中间件堆栈
- 与 [[entities/subagent-middleware]] 互补：同步子代理 vs 异步远程子代理

**为什么它是可分离的**：`AsyncSubAgentMiddleware` 是独立的 AgentMiddleware 子类，有自己的 State Schema 和完整的五工具套件。它通过 LangGraph SDK 连接外部服务，与同步 `SubAgentMiddleware` 完全独立。

**关键机制**（源码可见）：
- 任务状态持久化：通过 `async_tasks` 状态字典 + 自定义 reducer 在 Agent 状态中跟踪所有异步任务，即使上下文压缩后仍可访问 ^[deepagents/middleware/async_subagents.py:113-126]
- 客户端缓存：`_ClientCache` 按 (url, headers) 键缓存 LangGraph 客户端，避免重复创建 ^[deepagents/middleware/async_subagents.py:227-262]
- 实时状态获取：`list_async_tasks` 并发获取所有任务的最新状态，终态（success/error/cancelled）跳过网络请求 ^[deepagents/middleware/async_subagents.py:683-722]
- 多任务策略：`update_async_task` 使用 `multitask_strategy="interrupt"` 中断当前 run 并发送新指令 ^[deepagents/middleware/async_subagents.py:527]
- 认证头注入：默认添加 `x-auth-scheme: langsmith`，可通过 headers 字段覆盖 ^[deepagents/middleware/async_subagents.py:214-224]
- 系统提示词规则：强调启动后立即返回控制权，禁止轮询；任务状态在上次工具结果中总是过时的 ^[deepagents/middleware/async_subagents.py:176-211]

**源码证据**：
- 入口文件：`deepagents/middleware/async_subagents.py`
- 核心类定义：`deepagents/middleware/async_subagents.py:862`

**关联 Concept**：
- [[concepts/subagent-orchestration]]
