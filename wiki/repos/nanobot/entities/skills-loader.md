---
type: entity
repo: nanobot
slug: skills-loader
problem: 如何管理 Agent 的可插拔能力模块，支持按需加载和工作区覆盖
generated: 2026-06-25
source_files:
  - nanobot/agent/skills.py
---

# Skills Loader

**代码位置**：`nanobot/agent/skills.py`
**这个模块解决什么问题**：
- 实现层：从 built-in 和 workspace 两个来源加载 SKILL.md 定义的能力模块，支持需求检查（CLI 工具、环境变量）、渐进式加载（系统提示词含摘要，完整内容按需 read_file）和工作区覆盖
- 问题层：如何管理 Agent 的可插拔能力模块，支持按需加载和工作区覆盖
**对外暴露什么**：`SkillsLoader` 类（nanobot/agent/skills.py:23）、`BUILTIN_SKILLS_DIR` 常量（nanobot/agent/skills.py:10）
**它和谁交互**：
- 被 [[entities/context-builder]] 调用（获取 always skills 内容和技能摘要）
- 被 [[entities/subagent-manager]] 调用（为子 agent 构建技能摘要）
**为什么它是可分离的**：独立的加载器，仅依赖文件系统，可在不同上下文中使用不同的技能源

**关键机制**（源码可见）：
- 双层发现：workspace skills（`workspace/skills/`）优先，built-in skills 作为后备，同名时 workspace 覆盖 ^[nanobot/agent/skills.py:52-71]
- 需求检查：`_check_requirements()` 验证技能要求的 CLI 工具是否在 PATH 中、环境变量是否设置，不满足的标记为 unavailable ^[nanobot/agent/skills.py:181-188]
- YAML Frontmatter 解析：每个 SKILL.md 的 YAML frontmatter 可包含 `name`、`description`、`always`（是否始终注入）、`metadata`（JSON 格式的 nano-specific 配置）^[nanobot/agent/skills.py:144-229]
- Always Skills：标记 `always: true` 且需求满足的技能，其完整内容注入系统提示词 ^[nanobot/agent/skills.py:195-205]
- XML 摘要格式：`build_skills_summary()` 生成 `<skills>` XML 元素，包含每个技能的 name、description、location、availability，LLM 可通过 read_file 按需加载 ^[nanobot/agent/skills.py:109-142]
- 工作区覆盖：workspace 中的同名 skill 会覆盖 built-in 版本 ^[nanobot/agent/skills.py:63-68]

**源码证据**：
- 入口文件：nanobot/agent/skills.py
- 核心类型/接口定义：`class SkillsLoader` ^[nanobot/agent/skills.py:23]

**关联 Concept**：
- [[concepts/skills-extension-mechanism]]
