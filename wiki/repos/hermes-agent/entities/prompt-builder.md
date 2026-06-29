---
type: entity
repo: hermes-agent
slug: prompt-builder
problem: 如何组装 Agent 的多层系统提示词，集成身份定义、平台提示、技能索引、上下文文件和记忆上下文
generated: 2026-06-25
source_files:
  - agent/prompt_builder.py
  - agent/prompt_caching.py
---

# 提示词构建器

**代码位置**：`agent/prompt_builder.py`
**这个模块解决什么问题**：
- 实现层：无状态的纯函数集合，组装多层系统提示词：SOUL.md 身份 → 平台提示 → 记忆上下文 → 技能索引 → 上下文文件 → Anthropic prompt caching 标记，包含模型特定的执行纪律和上下文文件威胁检测
- 问题层：如何组装 Agent 的多层系统提示词，集成身份定义、平台提示、技能索引、上下文文件和记忆上下文
**对外暴露什么**：模块级函数 `build_skills_system_prompt()`（line 583）、`load_soul_md()`（line 893）、`build_context_files_prompt()`（line 1006）、`build_environment_hints()`（line 407）、`DEFAULT_AGENT_IDENTITY`（line 134）、`PLATFORM_HINTS`（line 285）、`TOOL_USE_ENFORCEMENT_GUIDANCE`（line 173）
**它和谁交互**：
- 依赖 [[entities/skills-system]]（`build_skills_system_prompt()` 扫描技能目录构建索引）
- 依赖 [[entities/memory-system]]（`MEMORY_GUIDANCE` 指导 agent 使用 memory 工具）
- 被 [[entities/agent-core]] 调用（`_build_system_prompt()` 组装完整提示词）
- 被 [[entities/gateway-runner]] 间接使用（通过 agent 的 system prompt 注入平台上下文）
**为什么它是可分离的**：纯函数模块，无状态，不依赖 agent 运行时状态

**关键机制**（源码可见）：
- 多层提示词组装：SOUL.md（身份）→ 平台提示（PLATFORM_HINTS）→ 记忆上下文 → 技能索引 → 上下文文件 → 时间戳。各层独立函数，按序拼接 ^[agent/prompt_builder.py]
- 模型特定执行纪律：
  - `TOOL_USE_ENFORCEMENT_GUIDANCE`：强制 tool-use 模型实际调用工具而非描述意图 ^[agent/prompt_builder.py:173]
  - `OPENAI_MODEL_EXECUTION_GUIDANCE`：GPT/Codex 模型的详细执行规范（绝对路径、先验证、逐个执行）^[agent/prompt_builder.py:196]
  - `GOOGLE_MODEL_OPERATIONAL_GUIDANCE`：Gemini/Gemma 模型的操作规则 ^[agent/prompt_builder.py:258]
  - `DEVELOPER_ROLE_MODELS`：GPT-5/Codex 使用 'developer' role 替代 'system' ^[agent/prompt_builder.py:283]
- 平台格式化提示：20+ 平台的 `PLATFORM_HINTS`（WhatsApp 无 Markdown、Telegram 支持格式、Discord 长度限制等）^[agent/prompt_builder.py:285]
- 上下文文件威胁检测：注入前扫描提示注入模式（ignore instructions、role hijack、HTML 注释注入、hidden div、translate_execute、exfil_curl、read_secrets）+ 不可见 Unicode 检测（ZWJ、ZWNJ、BOM 等）^[agent/prompt_builder.py:36-49]
- 两层技能缓存：in-process LRU + 磁盘快照，减少频繁扫描技能目录的 I/O ^[agent/prompt_builder.py:583]
- Anthropic prompt caching：`apply_anthropic_cache_control()` 对 system prompt 和工具定义块添加 cache_control 断点 ^[agent/prompt_caching.py]
- 技能索引格式：紧凑摘要（name + description + platforms），仅在 agent 启用技能时注入 ^[agent/prompt_builder.py:583-700]

**源码证据**：
- 入口文件：agent/prompt_builder.py
- 核心常量：`DEFAULT_AGENT_IDENTITY` ^[agent/prompt_builder.py:134]、`TOOL_USE_ENFORCEMENT_GUIDANCE` ^[agent/prompt_builder.py:173]

**关联 Concept**：
- [[concepts/system-prompt-assembly]]
