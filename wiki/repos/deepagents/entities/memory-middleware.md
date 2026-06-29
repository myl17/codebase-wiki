---
type: entity
repo: deepagents
slug: memory-middleware
problem: 如何在 Agent 启动时从文件系统加载持久化的项目上下文和用户偏好
generated: 2026-06-28
source_files:
  - deepagents/middleware/memory.py
---

# Memory Middleware

**代码位置**：`deepagents/middleware/memory.py`
**这个模块解决什么问题**：
- 实现层：通过 `MemoryMiddleware` 在 Agent 启动前从配置的 source 路径加载 AGENTS.md 文件内容，注入到系统提示词的 `<agent_memory>` 标签中；同时通过系统提示词中的指南引导 Agent 利用 `edit_file` 工具自主更新记忆
- 问题层：如何让 AI Agent 跨会话记住项目约定、用户偏好和学到的经验，同时让 Agent 能自主决定何时更新记忆（学习新信息 → 立即写入）

**对外暴露什么**：
- `MemoryMiddleware` 类 -- `deepagents/middleware/memory.py:159`
- `MemoryState` 状态类 -- `deepagents/middleware/memory.py:80`
- `MEMORY_SYSTEM_PROMPT` 常量 -- `deepagents/middleware/memory.py:97`

**它和谁交互**：
- 依赖 [[entities/backend-protocol]]（通过 backend.download_files 加载记忆文件）
- 被 [[entities/agent-graph-assembly]] 组装进中间件堆栈（在 AnthropicPromptCachingMiddleware 之后，确保缓存不因记忆更新而失效）
- 与 [[entities/filesystem-middleware]] 配合：Agent 使用 edit_file 工具更新记忆文件

**为什么它是可分离的**：`MemoryMiddleware` 是独立的 AgentMiddleware 子类，有自己的 State Schema 和生命周期钩子。记忆加载和注入逻辑完全自包含，通过 backend 抽象与存储解耦。

**关键机制**（源码可见）：
- 懒加载：`before_agent` 钩子在 `memory_contents` 已存在时跳过加载，支持从 checkpoint 恢复 ^[deepagents/middleware/memory.py:253-254]
- 多源拼接：按配置的 sources 顺序加载多个 AGENTS.md 文件，拼接为 `path + content` 格式 ^[deepagents/middleware/memory.py:230-236]
- 文件缺失容错：`file_not_found` 错误被静默跳过，不阻塞 Agent 启动 ^[deepagents/middleware/memory.py:262-263]
- 系统提示词注入指南：通过 `<memory_guidelines>` 标签指导 Agent 何时更新记忆、何时不更新 ^[deepagents/middleware/memory.py:97-155]
- 隐私状态：`memory_contents` 使用 `PrivateStateAttr` 标记，不包含在最终 Agent 状态中 ^[deepagents/middleware/memory.py:88]

**源码证据**：
- 入口文件：`deepagents/middleware/memory.py`
- 核心类定义：`deepagents/middleware/memory.py:159`

**关联 Concept**：
- [[concepts/memory-management-architecture]]
