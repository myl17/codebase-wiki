---
type: entity
repo: hermes-agent
slug: skills-system
problem: 如何实现 Agent 的程序性记忆系统，支持从经验中自主创建技能、运行时自我改进、社区技能市场同步和安全扫描
generated: 2026-06-25
source_files:
  - tools/skills_tool.py
  - tools/skill_manager_tool.py
  - tools/skills_hub.py
  - tools/skills_guard.py
  - tools/skills_sync.py
  - agent/skill_commands.py
  - agent/skill_utils.py
---

# 技能系统

**代码位置**：`tools/skills_tool.py`、`tools/skill_manager_tool.py`、`tools/skills_hub.py`、`tools/skills_guard.py`
**这个模块解决什么问题**：
- 实现层：技能是包含 SKILL.md 的目录，Agent 可列出/查看/创建/编辑/删除技能；Skills Hub 从多个社区源（GitHub、agentskills.io、skills.sh 等）下载技能；Skills Guard 在安装前扫描技能的安全风险
- 问题层：如何实现 Agent 的程序性记忆系统，支持从经验中自主创建技能、运行时自我改进、社区技能市场同步和安全扫描
**对外暴露什么**：
- `skills_list()` / `skill_view()` - Agent 工具，列出和查看技能（tools/skills_tool.py:647/804）
- `skill_manage()` - Agent 工具，CRUD 技能（tools/skill_manager_tool.py:616）
- `unified_search()` - 跨源搜索技能（tools/skills_hub.py:3033）
- `scan_skill()` / `should_allow_install()` - 安全扫描（tools/skills_guard.py:595/642）
- `check_skills_requirements()` - 环境检查（tools/skills_tool.py:428）
**它和谁交互**：
- 依赖 [[entities/tool-registry]]（通过 registry.register 注册 skills_list/skill_view/skill_manage 工具）
- 依赖 [[entities/prompt-builder]]（`build_skills_system_prompt()` 构建技能索引注入系统提示词；写入后通过 `clear_skills_system_prompt_cache()` 失效缓存）
- 依赖 [[entities/config-system]]（disabled_skills 列表、taps.json）
- 被 [[entities/agent-core]] 调用（通过工具分发）
- 被 [[entities/cli-system]] 调用（`hermes skills` 配置 UI）
**为什么它是可分离的**：技能系统是独立的文件系统层，技能目录即文件，安全扫描独立于安装流程

**关键机制**（源码可见）：
- 渐进式信息披露：技能元数据（Tier 1）→ 完整 SKILL.md（Tier 2）→ 链接文件如 references/ templates/（Tier 3），按需加载避免上下文膨胀 ^[tools/skills_tool.py:647-883]
- 技能创建：Agent 通过 `skill_manage(action="create", ...)` 创建新技能，内容通过 `_atomic_write_text()` 原子写入，创建后立即扫描 ^[tools/skill_manager_tool.py:304-359]
- 补丁式改进：`action="patch"` 通过 find-and-replace 修改 SKILL.md 或支持文件，支持增量改进而非全文重写 ^[tools/skill_manager_tool.py:397-487]
- 多源联邦搜索：`parallel_search_sources()` 并行搜索所有注册源（GitHub、agentskills.io、skills.sh、ClawHub、Claude Marketplace、LobeHub、可选技能、Hermes Index），每源 30s 超时 ^[tools/skills_hub.py:2917-3033]
- Hermes Index 智能优化：当 Index 覆盖某源时跳过外部 API 查询，减少网络消耗 ^[tools/skills_hub.py:2953-2994]
- 三级信任策略：builtin（永信）> trusted（openai/skills + anthropics/skills，允许 caution）> community（任何 finding = block）> agent-created（dangerous 时询问）^[tools/skills_guard.py:39-47]
- 安全扫描维度：正则模式匹配（数据外泄、提示注入、破坏性命令、持久化、网络调用、混淆）+ 不可见 Unicode 检测 + 结构检查（文件数 >500、总大小 >50MB、二进制文件、符号链接、.git 目录）^[tools/skills_guard.py:80-594, 734-785]
- 锁定文件溯源：`HubLockFile` 管理 `.hub/lock.json`，记录每技能的 source/identifier/trust_level/scan_verdict/content_hash，支持更新检查 ^[tools/skills_hub.py:2378-2645]
- 审计日志：所有安装/卸载操作追加到 `.hub/audit.log` ^[tools/skills_hub.py:2489]
- Quarantine 模式：下载的技能先写入 `.hub/quarantine/`，扫描通过后才移入 `skills/` ^[tools/skills_hub.py:2522-2608]

**源码证据**：
- 入口文件：tools/skills_tool.py、tools/skill_manager_tool.py、tools/skills_hub.py、tools/skills_guard.py
- 核心函数：`def skills_list(category=None)` ^[tools/skills_tool.py:647]、`def skill_manage(action, name, ...)` ^[tools/skill_manager_tool.py:616]

**关联 Concept**：
- [[concepts/skills-extension-mechanism]]
