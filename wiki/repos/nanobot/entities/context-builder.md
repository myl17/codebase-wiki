---
type: entity
repo: nanobot
slug: context-builder
problem: 如何组装 Agent 的系统提示词和上下文消息，整合身份、记忆、技能和历史
generated: 2026-06-25
source_files:
  - nanobot/agent/context.py
---

# Context Builder

**代码位置**：`nanobot/agent/context.py`
**这个模块解决什么问题**：
- 实现层：从身份模板、引导文件（AGENTS.md/SOUL.md/USER.md/TOOLS.md）、长期记忆、技能列表和最近历史组装完整的系统提示词和消息列表
- 问题层：如何组装 Agent 的系统提示词和上下文消息，整合身份、记忆、技能和历史
**对外暴露什么**：`ContextBuilder` 类（nanobot/agent/context.py:17）
**它和谁交互**：
- 依赖 [[entities/memory-system]]（MemoryStore，读 MEMORY.md、SOUL.md、USER.md、历史记录）
- 依赖 [[entities/skills-loader]]（获取 always skills 和技能摘要）
- 被 [[entities/agent-loop]] 调用（构建每次 LLM 调用的上下文）
**为什么它是可分离的**：独立类，仅依赖 workspace Path，可在不同 agent 场景中替换上下文构建策略

**关键机制**（源码可见）：
- 运行时上下文注入：在每条 user 消息前注入 `[Runtime Context]` 标记块，包含当前时间、channel、chat_id，元数据形式不污染消息内容 ^[nanobot/agent/context.py:21, 79-87]
- 渐进式技能加载：系统提示词中包含 always skills 的完整内容 + 所有技能的 XML 摘要，LLM 可按需 `read_file` 加载其他技能 ^[nanobot/agent/context.py:46-53]
- 引导文件分层：按 AGENTS.md > SOUL.md > USER.md > TOOLS.md 优先级加载，每个文件注入独立的 ## 标题节 ^[nanobot/agent/context.py:20, 103-113]
- 多模态图像处理：自动检测图片 MIME 类型（magic bytes），将 media paths 转换为基础64 inline 图像，失败时静默跳过 ^[nanobot/agent/context.py:147-172]
- 最近历史注入：将 Dream 游标之后未处理的 history.jsonl 条目（最多 50 条）追加到系统提示词 ^[nanobot/agent/context.py:56-61]

**源码证据**：
- 入口文件：nanobot/agent/context.py
- 核心类型/接口定义：`class ContextBuilder` ^[nanobot/agent/context.py:17]

**关联 Concept**：
- [[concepts/system-prompt-assembly]]
