---
type: entity
repo: nanobot
slug: agent-loop
problem: 如何编排 Agent 的主循环，协调消息接收、上下文构建、LLM 调用、工具执行和响应发送
generated: 2026-06-25
source_files:
  - nanobot/agent/loop.py
---

# Agent 主循环

**代码位置**：`nanobot/agent/loop.py`
**这个模块解决什么问题**：
- 实现层：通过 MessageBus 接收消息、构建上下文、调用 LLM、执行工具、管理会话和内存，驱动 AI Agent 的完整交互循环
- 问题层：如何编排 Agent 的主循环，协调消息接收、上下文构建、LLM 调用、工具执行和响应发送
**对外暴露什么**：`AgentLoop` 类（nanobot/agent/loop.py:115）
**它和谁交互**：
- 依赖 [[entities/message-bus]]（接收 inbound 消息，发布 outbound 响应）
- 依赖 [[entities/context-builder]]（构建系统提示词和消息列表）
- 依赖 [[entities/agent-runner]]（执行 tool-aware LLM 循环）
- 依赖 [[entities/tool-registry]]（注册和管理可用工具集）
- 依赖 [[entities/session-manager]]（管理会话历史和状态）
- 依赖 [[entities/memory-system]]（Consolidator 和 Dream 内存处理）
- 依赖 [[entities/subagent-manager]]（管理后台子 agent 执行）
- 依赖 [[entities/command-router]]（处理优先级命令如 /stop）
- 依赖 AgentHook（nanobot/agent/hook.py，生命周期回调）
- 被 [[entities/nanobot-facade]] 调用（SDK 层包装）
- 被 [[entities/cli-system]] 调用（CLI 模式启动）
**为什么它是可分离的**：`AgentLoop` 是独立类，接收 `MessageBus`、`LLMProvider`、`ToolRegistry` 等依赖注入，可在不同上下文中替换使用

**关键机制**（源码可见）：
- 统一会话模式：当 `unified_session` 启用时，所有 channel 共享同一会话 key `"unified:default"`，支持单用户多设备 ^[nanobot/agent/loop.py:44]
- 运行时检查点恢复：在长任务中断时通过 `_RUNTIME_CHECKPOINT_KEY` 持久化进行中的 turn 状态，重建时恢复未完成的 tool call ^[nanobot/agent/loop.py:127]
- 流式输出管道：通过 `_wants_stream` metadata 触发流式响应，按 stream segment 分段发送 delta，支持 tool call 前后的流式生命周期 ^[nanobot/agent/loop.py:407-436]
- MCP 惰性连接：首次消息到达时才连接 MCP 服务器，失败时重试，不阻塞启动 ^[nanobot/agent/loop.py:256-276]
- 并发控制：通过 `NANOBOT_MAX_CONCURRENT_REQUESTS` 环境变量（默认 3）限制并发会话数，使用 `asyncio.Semaphore` ^[nanobot/agent/loop.py:205-209]
- 会话级串行锁：每个 session_key 维护独立的 `asyncio.Lock`，保证同会话消息顺序处理 ^[nanobot/agent/loop.py:204]

**源码证据**：
- 入口文件：nanobot/agent/loop.py
- 核心类型/接口定义：`class AgentLoop` ^[nanobot/agent/loop.py:115]

**关联 Concept**：
- [[concepts/agent-loop-orchestration]]
