---
type: entity
repo: deepagents
slug: skills-middleware
problem: 如何让 Agent 按需加载和使用结构化的领域技能，而不在系统提示词中始终包含全部技能内容
generated: 2026-06-28
source_files:
  - deepagents/middleware/skills.py
---

# Skills Middleware

**代码位置**：`deepagents/middleware/skills.py`
**这个模块解决什么问题**：
- 实现层：通过 `SkillsMiddleware` 扫描 backend 中配置的 source 路径下的 SKILL.md 文件，解析 YAML frontmatter 获取技能元数据，将技能名称和描述注入系统提示词（渐进披露：先只显示元数据，Agent 需要时再读取完整 SKILL.md）
- 问题层：如何在为 Agent 提供丰富的专业领域能力（如代码审查、Web 研究）的同时，不因将所有技能内容加载到系统提示词而导致 token 浪费——即实现按需加载

**对外暴露什么**：
- `SkillsMiddleware` 类 -- `deepagents/middleware/skills.py:602`
- `SkillsState` 状态类 -- `deepagents/middleware/skills.py:195`
- `SkillMetadata` TypedDict -- `deepagents/middleware/skills.py:135`

**它和谁交互**：
- 依赖 [[entities/backend-protocol]]（通过 backend.ls + backend.download_files 发现和加载技能）
- 被 [[entities/agent-graph-assembly]] 组装进中间件堆栈
- 被 [[entities/subagent-middleware]] 的子代理继承

**为什么它是可分离的**：`SkillsMiddleware` 是独立的 AgentMiddleware 子类，遵循 Agent Skills 规范，有自己的 State Schema、技能发现-解析-注入流程。技能内容的实际读写由 Agent 通过文件系统工具自主完成。

**关键机制**（源码可见）：
- 渐进披露模式：系统提示词中只注入技能元数据（名称、描述、路径），Agent 需要时通过 `read_file` 工具自行读取完整 SKILL.md ^[deepagents/middleware/skills.py:560-599]
- 多源合并：按 sources 顺序加载技能，后加载的同名技能覆盖先加载的（last one wins），实现基础→用户→项目的分层 ^[deepagents/middleware/skills.py:755-758]
- YAML frontmatter 解析：通过正则匹配 `---` 分隔的 YAML，使用 `yaml.safe_load` 解析，遵循 Agent Skills 规范 ^[deepagents/middleware/skills.py:250-352]
- 技能名称验证：1-64 字符，小写字母数字和连字符，不允许首位连字符、连续连字符，必须匹配目录名 ^[deepagents/middleware/skills.py:209-247]
- 懒加载：`skills_metadata` 已在 state 中时跳过重新加载，支持从 checkpoint 恢复 ^[deepagents/middleware/skills.py:746-747]
- 隐私状态：`skills_metadata` 使用 `PrivateStateAttr` 标记，不传播到父 Agent ^[deepagents/middleware/skills.py:198]

**源码证据**：
- 入口文件：`deepagents/middleware/skills.py`
- 核心类定义：`deepagents/middleware/skills.py:602`

**关联 Concept**：
- [[concepts/skills-extension-mechanism]]
