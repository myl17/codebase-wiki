---
type: entity
repo: nanobot
slug: subagent-manager
problem: 如何让主 Agent 将复杂任务委托给后台子 Agent 异步执行，完成后通知结果
generated: 2026-06-25
source_files:
  - nanobot/agent/subagent.py
---

# Subagent Manager

**代码位置**：`nanobot/agent/subagent.py`
**这个模块解决什么问题**：
- 实现层：通过独立的 AgentRunner 实例在后台异步执行子任务，使用精简工具集（无 message/spawn 工具避免递归），完成后通过 MessageBus 以 system 消息注入结果
- 问题层：如何让主 Agent 将复杂任务委托给后台子 Agent 异步执行，完成后通知结果
**对外暴露什么**：`SubagentManager` 类（nanobot/agent/subagent.py:42）
**它和谁交互**：
- 依赖 [[entities/agent-runner]]（使用独立 runner 实例执行子任务）
- 依赖 [[entities/message-bus]]（注入子 agent 结果到主 agent）
- 被 [[entities/agent-loop]] 调用（作为 SpawnTool 的底层实现）
- 被 Spawn Tool 使用（`nanobot/agent/tools/spawn.py`）
**为什么它是可分离的**：独立管理器，通过 MessageBus 注入结果，工具集隔离避免递归

**关键机制**（源码可见）：
- 回调通信：子 agent 完成后调用 `_announce_result()` 构造 markdown 格式的通知，通过 `bus.publish_inbound()` 以 system 消息注入主 agent，不依赖轮询 ^[nanobot/agent/subagent.py:181-209]
- 隔离工具集：子 agent 有独立的精简工具注册（read_file、write_file、edit_file、list_dir、glob、grep、exec、web_search、web_fetch），**没有** message 和 spawn 工具，防止无限递归 ^[nanobot/agent/subagent.py:113-133]
- 会话关联：`_session_tasks` 字典记录每个 session 的子 agent，支持按 session 批量取消 ^[nanobot/agent/subagent.py:68, 247-255]
- 部分进度报告：工具错误导致终止时，`_format_partial_progress()` 从 `tool_events` 提取已完成步骤列表，提供有意义的错误上下文 ^[nanobot/agent/subagent.py:212-231]

**源码证据**：
- 入口文件：nanobot/agent/subagent.py
- 核心类型/接口定义：`class SubagentManager` ^[nanobot/agent/subagent.py:42]

**关联 Concept**：
- [[concepts/subagent-orchestration]]
