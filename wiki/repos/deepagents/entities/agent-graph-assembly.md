---
type: entity
repo: deepagents
slug: agent-graph-assembly
problem: 如何将多个中间件组合成一个完整配置的 AI Agent 图
generated: 2026-06-28
source_files:
  - deepagents/graph.py
---

# Agent Graph Assembly

**代码位置**：`deepagents/graph.py`
**这个模块解决什么问题**：
- 实现层：通过 `create_deep_agent()` 函数将模型、工具、中间件、子代理、内存、技能等组件按固定顺序组装成 LangGraph StateGraph
- 问题层：如何在组装 AI Agent 时确保中间件堆栈的顺序正确，使得工具注入、系统提示词增强、上下文压缩、缓存等横切关注点正确协同工作

**对外暴露什么**：
- `create_deep_agent(model, tools, system_prompt, middleware, subagents, skills, memory, backend, interrupt_on, ...)` -- `deepagents/graph.py:108`
- `get_default_model()` -- `deepagents/graph.py:93`
- `BASE_AGENT_PROMPT` -- `deepagents/graph.py:43`

**它和谁交互**：
- 依赖 [[entities/filesystem-middleware]]（文件系统工具注入）
- 依赖 [[entities/subagent-middleware]]（同步子代理） 
- 依赖 [[entities/async-subagent-middleware]]（远程异步子代理）
- 依赖 [[entities/summarization-middleware]]（对话压缩）
- 依赖 [[entities/memory-middleware]]（AGENTS.md 上下文加载）
- 依赖 [[entities/skills-middleware]]（技能渐进披露）
- 依赖 [[entities/tool-call-patching]]（悬空工具调用修复）
- 依赖 [[entities/model-resolution]]（模型解析）
- 依赖 `HumanInTheLoopMiddleware`（外部库，人工审批中断）
- 依赖 `TodoListMiddleware`（外部库，任务列表管理）
- 依赖 `AnthropicPromptCachingMiddleware`（外部库，提示词缓存）

**为什么它是可分离的**：`create_deep_agent()` 是单一入口函数，其职责是协调组装——它本身不实现任何工具或中间件逻辑，只按固定顺序编排已有组件。所有实际功能由独立中间件和 backend 模块提供。

**关键机制**（源码可见）：
- 默认中间件堆栈：TodoListMiddleware -> SkillsMiddleware(可选) -> FilesystemMiddleware -> SubAgentMiddleware -> SummarizationMiddleware -> PatchToolCallsMiddleware -> AsyncSubAgentMiddleware(可选) -> 用户中间件 -> AnthropicPromptCachingMiddleware -> MemoryMiddleware(可选) -> HumanInTheLoopMiddleware(可选) ^[deepagents/graph.py:363-395]
- 通用子代理自动注入：如果用户未提供名为 `general-purpose` 的子代理，自动创建一个具有完整中间件堆栈的默认通用子代理 ^[deepagents/graph.py:358-360]
- 子代理规范预处理：`SubAgent` 类型的声明式子代理会自动填充默认中间件堆栈（TodoListMiddleware、FilesystemMiddleware、SummarizationMiddleware 等），并解析 `interrupt_on` 的继承/覆盖关系 ^[deepagents/graph.py:330-354]
- 异步子代理分离路由：带有 `graph_id` 字段的子代理规范被识别为 `AsyncSubAgent`，路由到 `AsyncSubAgentMiddleware` 而非 `SubAgentMiddleware` ^[deepagents/graph.py:317-321]
- 系统提示词组合：自定义 `system_prompt` 前置 + `BASE_AGENT_PROMPT` 后置 ^[deepagents/graph.py:398-404]
- 配置元数据注入：设置 `recursion_limit=9999` 和 `ls_integration="deepagents"` 元数据 ^[deepagents/graph.py:418-427]

**源码证据**：
- 入口文件：`deepagents/graph.py`
- 核心函数定义：`deepagents/graph.py:108-427`

**关联 Concept**：
- [[concepts/middleware-composition-pattern]]
