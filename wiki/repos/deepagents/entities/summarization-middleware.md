---
type: entity
repo: deepagents
slug: summarization-middleware
problem: 如何在 Agent 对话过长时自动压缩历史消息，保持上下文窗口在模型限制内
generated: 2026-06-28
source_files:
  - deepagents/middleware/summarization.py
---

# Summarization Middleware

**代码位置**：`deepagents/middleware/summarization.py`
**这个模块解决什么问题**：
- 实现层：提供两个中间件——`SummarizationMiddleware` 在 token 超过阈值时自动触发 LLM 摘要压缩，`SummarizationToolMiddleware` 允许 Agent 通过 `compact_conversation` 工具手动触发压缩；压缩的完整历史被持久化到 backend
- 问题层：如何在 AI Agent 的长时间对话中，既保留关键上下文信息（通过摘要），又不丢失完整历史（通过后端持久化），同时避免超出模型输入 token 限制

**对外暴露什么**：
- `SummarizationMiddleware` 类（`_DeepAgentsSummarizationMiddleware`） -- `deepagents/middleware/summarization.py:210`
- `SummarizationToolMiddleware` 类 -- `deepagents/middleware/summarization.py:1017-1537`
- `create_summarization_tool_middleware(model, backend)` 工厂函数
- `compute_summarization_defaults(model)` -- `deepagents/middleware/summarization.py:170`
- `SummarizationState` 状态类 -- `deepagents/middleware/summarization.py:152`

**它和谁交互**：
- 依赖 [[entities/backend-protocol]]（持久化对话历史到 backend）
- 被 [[entities/agent-graph-assembly]] 组装进中间件堆栈
- 被 [[entities/subagent-middleware]] 的子代理继承

**为什么它是可分离的**：`SummarizationMiddleware` 是独立的 AgentMiddleware 子类，有自己的 State Schema、LLM 摘要引擎和 backend 持久化逻辑。可以通过配置不同的触发阈值和保留策略独立调节。

**关键机制**（源码可见）：
- 摘要触发策略：支持 `("tokens", N)`、`("fraction", 0.85)`、`("messages", N)` 三种触发方式，可组合多个触发条件 ^[deepagents/middleware/summarization.py:217-219]
- ContextOverflowError 回退：如果未触发摘要但模型调用因上下文溢出失败，自动回退到摘要路径 ^[deepagents/middleware/summarization.py:940-944]
- 工具调用参数截断：在摘要之前对旧消息中的 `write_file`/`edit_file` 大参数进行截断，减少 token 消耗 ^[deepagents/middleware/summarization.py:646-733]
- 对话历史持久化：摘要前将完整消息 append 到 backend 上的 `/conversation_history/{thread_id}.md` 文件 ^[deepagents/middleware/summarization.py:735-807]
- 摘要事件链式处理：通过 `_summarization_event` 私有状态字段追踪多次摘要，后续请求基于摘要 + 新消息重建有效消息列表 ^[deepagents/middleware/summarization.py:500-537]
- 模型感知默认值：根据模型 `profile.max_input_tokens` 自动计算触发和保留阈值 ^[deepagents/middleware/summarization.py:170-207]

**源码证据**：
- 入口文件：`deepagents/middleware/summarization.py`
- 核心类定义：`deepagents/middleware/summarization.py:210`

**关联 Concept**：
- [[concepts/context-compression-strategy]]
