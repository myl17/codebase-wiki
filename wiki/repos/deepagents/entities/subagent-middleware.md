---
type: entity
repo: deepagents
slug: subagent-middleware
problem: 如何让主 Agent 将复杂任务委派给隔离的短期子 Agent 执行
generated: 2026-06-28
source_files:
  - deepagents/middleware/subagents.py
---

# SubAgent Middleware

**代码位置**：`deepagents/middleware/subagents.py`
**这个模块解决什么问题**：
- 实现层：通过 `SubAgentMiddleware` 注入 `task` 工具，允许主 Agent 启动声明式或预编译的子 Agent 来隔离执行复杂任务，子 Agent 完成后返回单一聚合结果
- 问题层：如何在多步骤复杂任务中将独立子任务隔离执行，减少主 Agent 的上下文压力和 token 消耗，同时保持结果的结构化返回

**对外暴露什么**：
- `SubAgentMiddleware` 类 -- `deepagents/middleware/subagents.py:392`
- `SubAgent` TypedDict（声明式子代理规范） -- `deepagents/middleware/subagents.py:21`
- `CompiledSubAgent` TypedDict（预编译子代理规范） -- `deepagents/middleware/subagents.py:80`
- `GENERAL_PURPOSE_SUBAGENT` 常量 -- `deepagents/middleware/subagents.py:283`
- `TASK_SYSTEM_PROMPT` 常量 -- `deepagents/middleware/subagents.py:251`

**它和谁交互**：
- 依赖 [[entities/agent-graph-assembly]]（被组装进中间件堆栈）
- 依赖 [[entities/filesystem-middleware]]（子代理继承文件系统工具）
- 依赖 `create_agent`（外部库，创建子代理图）
- 依赖 `HumanInTheLoopMiddleware`（外部库，子代理人工审批）
- 使用 `_utils.append_to_system_message` 注入任务工具说明

**为什么它是可分离的**：`SubAgentMiddleware` 是独立的 AgentMiddleware 子类，通过构造子代理 Runnable 并包装为 `task` 工具来提供隔离执行能力。子代理的中间件堆栈可独立配置。

**关键机制**（源码可见）：
- 三种子代理形态：`SubAgent`（声明式配置） + `CompiledSubAgent`（预编译图） + `AsyncSubAgent`（远程异步）^[deepagents/middleware/subagents.py:21-109]
- 状态键过滤：`messages`、`todos`、`structured_response`、`skills_metadata`、`memory_contents` 被排除，防止子代理接收无关状态或主代理状态泄漏 ^[deepagents/middleware/subagents.py:126]
- 子代理结果提取：从子代理 `messages` 列表的最后一条消息提取文本作为 ToolMessage 返回 ^[deepagents/middleware/subagents.py:336]
- 系统提示词注入：通过 `wrap_model_call` 在每次 LLM 调用前将子代理使用说明注入系统消息 ^[deepagents/middleware/subagents.py:520-529]
- `interrupt_on` 继承：声明式 SubAgent 默认继承顶层 `interrupt_on` 配置，也可提供自己的配置覆盖 ^[deepagents/middleware/subagents.py:500-502]
- 通用子代理默认值：如果未提供名称为 `general-purpose` 的子代理，自动创建默认通用子代理 ^[deepagents/middleware/subagents.py:283-287]

**源码证据**：
- 入口文件：`deepagents/middleware/subagents.py`
- 核心类定义：`deepagents/middleware/subagents.py:392`
- Task 工具构建：`deepagents/middleware/subagents.py:298-389`

**关联 Concept**：
- [[concepts/subagent-orchestration]]
