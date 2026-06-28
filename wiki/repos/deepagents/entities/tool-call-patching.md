---
type: entity
repo: deepagents
slug: tool-call-patching
problem: 如何修复消息历史中因中断或并发导致的悬空工具调用（有 AIMessage.tool_calls 但没有对应 ToolMessage 响应）
generated: 2026-06-28
source_files:
  - deepagents/middleware/patch_tool_calls.py
---

# Tool Call Patching

**代码位置**：`deepagents/middleware/patch_tool_calls.py`
**这个模块解决什么问题**：
- 实现层：通过 `PatchToolCallsMiddleware` 的 `before_agent` 钩子在每次 Agent 执行前扫描消息历史，对每个 AIMessage 的 tool_calls 检查是否有对应的 ToolMessage 响应；对缺失的悬空调用注入取消通知 ToolMessage
- 问题层：如何在 Agent 被中断（如人工审批拒绝、超时、并发冲突）后，确保消息历史的状态一致性——每个 tool_call 都有对应的 tool_result

**对外暴露什么**：
- `PatchToolCallsMiddleware` 类 -- `deepagents/middleware/patch_tool_calls.py:11`

**它和谁交互**：
- 被 [[entities/agent-graph-assembly]] 组装进中间件堆栈（在 SummarizationMiddleware 之后）
- 被 [[entities/subagent-middleware]] 的子代理继承

**为什么它是可分离的**：`PatchToolCallsMiddleware` 是独立的 AgentMiddleware 子类，职责单一——在每次 Agent 执行前做一次消息历史的完整性扫描和修复。它不注入工具、不修改系统提示词。

**关键机制**（源码可见）：
- 悬空调用的检测：遍历消息历史，对每个 AIMessage 的每个 tool_call，在后续消息中查找 tool_call_id 匹配的 ToolMessage ^[deepagents/middleware/async_subagents.py:26-43]
- 取消通知注入：对未找到对应 ToolMessage 的工具调用，注入内容为 "另一条消息在其完成前到达" 的取消 ToolMessage ^[deepagents/middleware/patch_tool_calls.py:33-42]
- Overwrite 替换：使用 LangGraph 的 `Overwrite` 机制替换整个 messages 列表 ^[deepagents/middleware/patch_tool_calls.py:44]

**源码证据**：
- 入口文件：`deepagents/middleware/patch_tool_calls.py`
- 核心类定义：`deepagents/middleware/patch_tool_calls.py:11`
