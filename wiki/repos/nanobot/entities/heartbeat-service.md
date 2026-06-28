---
type: entity
repo: nanobot
slug: heartbeat-service
problem: 如何让 Agent 在空闲时自主检查待办任务并主动执行，而不依赖用户输入触发
generated: 2026-06-25
source_files:
  - nanobot/heartbeat/service.py
---

# Heartbeat Service

**代码位置**：`nanobot/heartbeat/service.py`
**这个模块解决什么问题**：
- 实现层：两阶段心跳机制——Phase 1 通过虚拟 tool call 让 LLM 判断是否有活跃任务（skip/run），Phase 2 仅当 Phase 1 返回 `run` 时才执行任务
- 问题层：如何让 Agent 在空闲时自主检查待办任务并主动执行，而不依赖用户输入触发
**对外暴露什么**：`HeartbeatService` 类（nanobot/heartbeat/service.py:40）
**它和谁交互**：
- 依赖 `LLMProvider`（Phase 1 决策用轻量 LLM 调用）
- 通过回调 `on_execute` 与 [[entities/agent-loop]] 交互（Phase 2 执行实际任务）
- 被 Agent Loop 启动
**为什么它是可分离的**：独立服务，通过回调与 Agent 核心通信，可禁用

**关键机制**（源码可见）：
- 虚拟工具决策：Phase 1 使用一个专用的 `heartbeat` 工具定义（仅 `action: skip/run` + `tasks` 字段），通过强制 tool_choice 让 LLM 输出结构化的决策，避免解析自由文本 ^[nanobot/heartbeat/service.py:14-37]
- 两阶段解耦：决策和执行分离，避免每次 heartbeat 都启动完整的 agent loop 造成 token 浪费 ^[nanobot/heartbeat/service.py:40-50]
- HEARTBEAT.md 上下文：检查 workspace 中的 HEARTBEAT.md 文件内容作为决策上下文 ^[nanobot/heartbeat/service.py]

**源码证据**：
- 入口文件：nanobot/heartbeat/service.py
- 核心类型/接口定义：`class HeartbeatService` ^[nanobot/heartbeat/service.py:40]

**关联 Concept**：
- [[concepts/autonomous-scheduling]]
