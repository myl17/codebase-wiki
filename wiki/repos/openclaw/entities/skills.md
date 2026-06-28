---
type: entity
repo: openclaw
slug: skills
problem: "如何管理可安装的 agent 技能（markdown 指令文件），从发现、过滤、安装到系统提示注入？"
generated: 2026-06-25
source_files:
  - src/agents/skills/
---

# Skills

**代码位置**：`src/agents/skills/`
**这个模块解决什么问题**：
- 实现层：从 bundled/clawhub/workspace 三个来源加载 skill markdown 文件 → 按 agent 过滤和平台检查 → 渲染为 `<available_skills>` XML 块注入系统提示
- 问题层：如何管理可安装的 agent 技能（markdown 指令文件），从发现、过滤、安装到系统提示注入？
**对外暴露什么**：
- `loadWorkspaceSkillEntries()` — 从所有来源加载技能条目 ^[src/agents/skills/workspace.ts]
- `filterWorkspaceSkillEntries(entries, options)` — 按 agent 过滤 + 平台检查 ^[src/agents/skills/workspace.ts]
- `buildWorkspaceSkillsPrompt(params)` — 渲染技能为提示块 ^[src/agents/skills/workspace.ts]
- `resolveSkillsPromptForRun(params)` — 解析当前运行的技能提示 ^[src/agents/skills/workspace.ts]
- `syncSkillsToWorkspace(src, dest)` — 同步技能到沙箱工作区 ^[src/agents/skills/workspace.ts]
- `SkillEntry` 类型 — 技能条目（Skill + parsed frontmatter + metadata + invocation policy） ^[src/agents/skills/types.ts]
- `SkillInstallSpec` — 安装规格（kind: brew/node/go/uv/download + source details） ^[src/agents/skills/types.ts]
- `isBundledSkillAllowed(name)` — 检查 bundled skill 是否在白名单 ^[src/agents/skills/config.ts]
**它和谁交互**：
- 依赖 [[entities/sandbox]]（技能同步到沙箱工作区）
- 依赖 [[entities/config-system]]（技能过滤器配置）
- 被 [[entities/agent-runtime]] 用于系统提示注入 / 被 [[entities/cli-system]] 用于 skills 管理命令
- 被 [[entities/plugin-system]]（插件提供的技能）
**为什么它是可分离的**：技能是独立的 markdown 文件，加载和注入逻辑独立于 agent 循环

**关键机制**（源码可见）：
- 三个技能来源：`bundled/`（随 OpenClaw 发布）+ plugin 目录 + workspace `.claude/skills/` ^[src/agents/skills/workspace.ts]
- YAML frontmatter 解析：提取 name, description, metadata（always, emoji, os, requires, install） ^[src/agents/skills/frontmatter.ts]
- 工具过滤管道：memory-flush → message-provider → model-provider → owner-only → 策略管道（profile→agent→group→sandbox→subagent）→ schema 归一化 → 钩子包装 ^[src/agents/skills/workspace.ts]
- 平台检查：`requires.bins`（检查二进制可用性）、`requires.env`（检查环境变量）、`requires.config`（检查配置路径） ^[src/agents/skills/config.ts]
- 安装支持：brew（Homebrew）、node（npm/pnpm/yarn/bun）、go、uv（Python）、download（tar 解压） ^[src/agents/skills/types.ts]
- 提示渲染：`<available_skills>` XML 块 → 每个技能列出名称、描述和调用方式（通常通过 `read` 工具加载 markdown） ^[src/agents/skills/skill-contract.ts]

**源码证据**：
- 入口文件：src/agents/skills.ts
- 工作区管理：src/agents/skills/workspace.ts
- 配置解析：src/agents/skills/config.ts
- 类型定义：src/agents/skills/types.ts
- 安装逻辑：src/agents/skills/install.ts
- 前端元数据：src/agents/skills/frontmatter.ts

**关联 Concept**：
- [[concepts/skills-extension-mechanism]]
