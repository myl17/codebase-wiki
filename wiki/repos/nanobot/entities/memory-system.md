---
type: entity
repo: nanobot
slug: memory-system
problem: 如何在本地文件系统上管理 Agent 的长期记忆、会话历史和内存整理
generated: 2026-06-25
source_files:
  - nanobot/agent/memory.py
---

# Memory System

**代码位置**：`nanobot/agent/memory.py`
**这个模块解决什么问题**：
- 实现层：三层内存架构——MemoryStore（纯文件 I/O，管理 MEMORY.md/history.jsonl/SOUL.md/USER.md）、Consolidator（轻量 token 预算触发的会话压缩）、Dream（重量 cron 驱动的两阶段内存整理）
- 问题层：如何在本地文件系统上管理 Agent 的长期记忆、会话历史和内存整理
**对外暴露什么**：`MemoryStore` 类（nanobot/agent/memory.py:31）、`Consolidator` 类（nanobot/agent/memory.py:346）、`Dream` 类（nanobot/agent/memory.py:519）
**它和谁交互**：
- 被 [[entities/context-builder]] 调用（读记忆文件、最近历史）
- 被 [[entities/agent-loop]] 调用（Consolidator 在每次 turn 后触发）
- 被 [[entities/cron-service]] 调用（Dream 作为 cron job 周期性触发）
- 依赖 `LLMProvider`（Consolidator 和 Dream 使用 LLM 做摘要和编辑）
- 依赖 [[entities/agent-runner]]（Dream Phase 2 使用 runner 做文件编辑）
- 依赖 `GitStore`（nanobot/utils/gitstore.py，Dream 编辑后自动 git commit）
**为什么它是可分离的**：MemoryStore 是纯文件 I/O 层，Consolidator 和 Dream 是独立处理器，可替换或禁用

**关键机制**（源码可见）：
- 三层内存架构：MemoryStore（被动文件 I/O）-> Consolidator（主动 token 预算管理）-> Dream（深度反思和文件编辑），逐层递进 ^[nanobot/agent/memory.py:27-29]
- Consolidator 的 token 预算驱动：比较 `estimated > context_window_tokens`，超标时找 user-turn 边界做存档，目标降到 budget 的 50%，最多 5 轮 ^[nanobot/agent/memory.py:346-512]
- Consolidator 归档：将旧的会话消息通过 LLM 摘要后追加到 history.jsonl，失败时降级为 raw dump ^[nanobot/agent/memory.py:419-449]
- Dream 两阶段处理：Phase 1 分析 history.jsonl 生成摘要；Phase 2 委托 AgentRunner 用 read_file/edit_file 工具做增量文件编辑，而非整文件替换 ^[nanobot/agent/memory.py:519-675]
- Dream 游标机制：使用 `.dream_cursor` 文件追踪已处理的 history 条目，避免重复处理 Phase 1 ^[nanobot/agent/memory.py:304-313]
- Git 自动提交：Dream 编辑文件后，如果 memory workspace 更新且 git 已初始化，自动创建增量提交 ^[nanobot/agent/memory.py:669-674]
- 旧版历史迁移：在首次启动时自动将旧版 HISTORY.md 迁移为 history.jsonl 格式，best-effort 解析 ^[nanobot/agent/memory.py:70-107]

**源码证据**：
- 入口文件：nanobot/agent/memory.py
- 核心类型/接口定义：`class MemoryStore` ^[nanobot/agent/memory.py:31]、`class Consolidator` ^[nanobot/agent/memory.py:346]、`class Dream` ^[nanobot/agent/memory.py:519]

**关联 Concept**：
- [[concepts/memory-management-architecture]]
