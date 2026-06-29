---
type: entity
repo: nanobot
slug: command-router
problem: 如何在 Agent 对话流中嵌入内置命令（如 /stop、/status 等），区分优先级命令和常规命令
generated: 2026-06-25
source_files:
  - nanobot/command/router.py
  - nanobot/command/builtin.py
---

# Command Router

**代码位置**：`nanobot/command/`
**这个模块解决什么问题**：
- 实现层：基于匹配优先级的命令路由器——优先级命令（如 /stop）在消息入队前处理，常规命令（如 /dream、/status）在 Agent 循环内处理
- 问题层：如何在 Agent 对话流中嵌入内置命令，区分优先级命令和常规命令
**对外暴露什么**：`CommandRouter` 类（nanobot/command/router.py）、`CommandContext` dataclass、`register_builtin_commands()` 函数
**它和谁交互**：
- 被 [[entities/agent-loop]] 调用（注册内建命令，在消息处理时 dispatch 优先级/常规命令）
- 被 Channel 插件注册（各 channel 可注册自定义命令）
**为什么它是可分离的**：独立的路由器，命令通过注册模式添加，与 Agent 循环在产品层解耦

**关键机制**（源码可见）：
- 两级优先级：`is_priority()` 检查消息是否匹配高优先级命令（如 /stop），这些命令在主循环中直接执行不经过 LLM；常规命令在 `_process_message()` 中 dispatch ^[nanobot/agent/loop.py:385-389, 529-531]
- /stop 跨会话支持：`dispatch_priority()` 返回 `OutboundMessage`，/stop 能取消当前 running task 并在所有 session 中生效 ^[nanobot/command/builtin.py]
- 插件化扩展：各 Channel 可通过注册模式添加自定义 in-chat 命令 ^[nanobot/command/router.py]

**源码证据**：
- 入口文件：nanobot/command/router.py、nanobot/command/builtin.py
- 核心类型/接口定义：`class CommandRouter` ^[nanobot/command/router.py]
