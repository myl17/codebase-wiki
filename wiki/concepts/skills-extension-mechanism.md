---
type: concept
concept: skills-extension-mechanism
problem: 如何管理 Agent 的可插拔能力模块（Skills），支持从经验中自主创建、社区共享和安全安装
concerns: [技能来源多样性与安全风险, 安装自动化程度, 上下文注入效率]
repos: [nanobot, hermes-agent, openclaw, deepagents]
generated: 2026-06-25
---

# Skills Extension Mechanism

## 核心问题

Skills 是 Agent 能力的可插拔扩展单元——一个 Skill 通常是一个包含 SKILL.md 指令文件的目录，告诉 Agent 在特定场景下如何行为。但 Skills 不是简单的"加载文件到提示词"——它需要回答三个层层递进的问题：Skills 从哪里来（来源多样性）、如何安全地安装（安全风险）、如何高效地注入上下文（注入效率）。这三个问题的答案构成框架的 Skills 管理体系，也决定了生态系统的开放程度。

来源多样性与安全风险是一体两面。来源越多（内置、工作区、插件、社区市场），Agent 能掌握的能力越丰富，但恶意 Skill 入侵的风险也越大。如果只是加载本地文件，安全不是问题；一旦支持从 GitHub 或社区市场下载 Skill，就需要隔离安装（Quarantine 模式）、信任分级（谁发布的？）、内容扫描（包含危险命令吗？）。这个博弈直接决定安装自动化程度——安全校验越严格，自动化安装越可行。

上下文注入效率是第三个维度。每个 Skill 的完整内容可能长达数千字——如果全部注入系统提示，500 个 Skill 会撑爆上下文窗口。解决策略有两种：渐进式信息披露（Tier 1 摘要 → Tier 2 完整内容 → Tier 3 链接文件，Agent 按需通过 read_file 加载）和按需注入（仅注入标记为 always 的 Skill 或匹配当前任务的 Skill）。两者可组合使用。

## 关切

- **技能来源多样性与安全风险**：来源越多（内置、工作区、插件、社区市场），能力越丰富但攻击面越大。Quarantine 隔离、信任分级、内容扫描是必要的防御层，但每层都增加安装延迟。
- **安装自动化程度**：用户通过 CLI 安装 vs Agent 自主搜索安装 vs 完全手动复制文件。自动化越高，对安全扫描准确性的要求越高——因为不再有人类审查这一关。
- **上下文注入效率**：全量注入 vs 渐进式加载 vs 按需注入。全量注入浪费上下文但响应快；渐进式加载节约上下文但每个 Skill 首次调用需额外 read_file 往返。

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/skills-loader]]
**解法**：双层发现（workspace 优先覆盖 built-in）+ YAML frontmatter 解析 + always skills 全量注入 + 摘要 XML 供 LLM 按需加载。
**实现**：workspace 同名 Skill 覆盖 built-in 版本；`_check_requirements()` 验证 CLI 工具和环境变量可用性；标记 `always: true` 的 Skill 完整内容注入系统提示词，其余以 `<skills>` XML 摘要形式注入（含 name/description/location/availability），LLM 通过 read_file 按需加载。 ^[nanobot/agent/skills.py:52-71, 181-188, 195-205, 109-142]
**权衡**：最简洁的设计——双层发现 + 按需加载，无社区市场和安装自动化。上下文注入效率好（always vs summary 二分），但技能来源仅限于本地，不支持社区共享。

### hermes-agent
来源：[[repos/hermes-agent/entities/skills-system]]
**解法**：完整的 Skills 生命周期管理——CRUD + 8 源联邦市场搜索 + Quarantine 隔离安装 + 三级信任策略 + 渐进式信息披露。
**实现**：Agent 可通过工具自主创建/编辑/删除 Skill（含原子写入和补丁式改进）；`unified_search()` 并行搜索 8 个社区源（GitHub/agentskills.io/skills.sh/ClawHub/Claude Marketplace/LobeHub/Hermes Index），每源 30s 超时；下载的 Skill 先进入 `.hub/quarantine/` 扫描通过后才移入 `skills/`；三级信任（builtin/trusted/community/agent-created）决定不同来源的容忍度；渐进披露分 Tier 1 元数据 → Tier 2 完整 SKILL.md → Tier 3 链接文件。 ^[tools/skill_manager_tool.py:304-359, 397-487, tools/skills_hub.py:2917-3033, 2522-2608, tools/skills_guard.py:39-47, tools/skills_tool.py:647-883]
**权衡**：功能最完整——唯一支持 Agent 自主创建 Skill 和社区市场安装的框架。但复杂度最高，Quarantine 扫描和信任分级增加了安装延迟。

### deepagents
来源：[[repos/deepagents/entities/skills-middleware]]
**解法**：Agent Skills 规范遵循 + 多源合并（last one wins）+ 纯渐进披露（元数据 → Agent 自行 read_file 加载）。
**实现**：SkillsMiddleware 遵循 Agent Skills 规范（https://agentskills.io/specification），扫描 backend source 路径下含 SKILL.md 的子目录。YAML frontmatter 解析 name/description/license/compatibility/allowed_tools/metadata 元数据。技能名称验证 1-64 字符小写字母数字+连字符，必须匹配目录名。多源按顺序加载，后加载的同名技能覆盖先加载的（last one wins），实现基础→用户→项目分层。系统提示词中仅注入技能元数据（名称、描述、路径、allowed_tools），Agent 需要时自行 `read_file` 加载完整 SKILL.md。`skills_metadata` 使用 PrivateStateAttr 标记，不传播到父 Agent。懒加载机制支持从 checkpoint 恢复。 ^[deepagents/middleware/skills.py:602-831, 755-758, 209-247, 250-352]
**权衡**：最纯的渐进披露设计——元数据注入 + Agent 自主 read_file，无框架层面的安装自动化或安全扫描。多源合并机制简洁有效（last one wins）。但无社区市场搜索、无 Quarantine 隔离、无安装自动化——技能来源仅限于本地 backend 中的文件。适合将技能视为项目配置的一部分而非独立生态系统的设计哲学。

## 对比
| 框架 | 技能来源多样性与安全风险 | 安装自动化程度 | 上下文注入效率 |
|------|------|------|------|
| nanobot | 两层本地（workspace > built-in），无社区市场，无安全风险 | 无安装自动化，手动放置文件 | always full-inject + summary XML 按需，二分策略简洁高效 |
| hermes-agent | 8 源联邦社区市场 + Quarantine 隔离 + 三级信任策略 | Agent 可自主搜索安装 + 原子写入 + 锁定文件溯源 | 三级渐进披露（元数据→完整→链接），按需加载 |
| openclaw | 三源本地（bundled/plugin/workspace），无社区市场搜索 | 5 种安装策略自动处理依赖（brew/node/go/uv/download） | 全量 XML 注入 `<available_skills>` 块 |
| deepagents | 纯本地 backend source 路径，遵循 Agent Skills 规范 | 无安装自动化——手动放置文件到 backend | 纯渐进披露——元数据注入 + Agent read_file 按需加载 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 deepagents（Agent Skills 规范 + 纯渐进披露 + 多源合并）
