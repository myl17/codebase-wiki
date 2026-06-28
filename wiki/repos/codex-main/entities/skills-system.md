---
type: entity
repo: codex-main
slug: skills-system
problem: 如何用用户定义的技能文件扩展 Agent 能力
generated: 2026-06-28
source_files:
  - codex-rs/skills/src/lib.rs
  - codex-rs/core-skills/src/lib.rs
---

# Skills System

**代码位置**：codex-rs/skills/ + codex-rs/core-skills/
**这个模块解决什么问题**：
- 实现层：通过 `CODEX_HOME/skills/` 目录下的 Markdown 技能文件 + 内嵌系统技能 + 技能元数据预算管理，让用户以声明式方式扩展 Agent 的行为知识
- 问题层：如何用用户定义的技能文件扩展 Agent 能力
**对外暴露什么**：
- `install_system_skills`：安装内嵌系统技能到 CODEX_HOME ^[codex-rs/skills/src/lib.rs:32]
- `system_cache_root_dir`：系统技能缓存目录路径 ^[codex-rs/skills/src/lib.rs:18-22]
- `SKILLS_DIR_NAME`：技能目录名称常量 ^[codex-rs/skills/src/lib.rs:13]
- `SYSTEM_SKILLS_DIR_NAME`：系统技能子目录名 ^[codex-rs/skills/src/lib.rs:12]
- `core-skills` crate：核心技能定义（如文件操作、Web 搜索、代码执行等内置技能）^[codex-rs/core-skills/src/lib.rs]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 启动时加载技能，运行时注入技能提示词）
- 与 [[entities/hook-system]] 配合（技能可以触发或响应钩子事件）
- 与 [[entities/plugin-system]] 配合（插件的技能根目录通过 `EffectiveSkillRoots` 暴露） ^[codex-rs/plugin/src/load_outcome.rs:15]
**为什么它是可分离的**：独立的 crate，文件系统驱动的声明式扩展机制，与 Agent 核心逻辑解耦

**关键机制**（源码可见）：
- **声明式技能文件**：技能以 Markdown 文件形式存放在 `CODEX_HOME/skills/` 目录，文件内容描述技能的触发条件、行为和示例 ^[codex-rs/skills/src/lib.rs:1-5]
- **系统技能嵌入**：`include_dir!` 宏在编译时将 `src/assets/samples` 目录嵌入二进制，运行时安装到 `skills/.system`，通过 marker 文件避免重复安装 ^[codex-rs/skills/src/lib.rs:10-56]
- **指纹校验**：系统技能的 marker 文件包含嵌入目录的哈希指纹，首次启动或哈希变化时重新安装 ^[codex-rs/skills/src/lib.rs:40-50]
- **元数据预算管理**：`default_skill_metadata_budget` 控制技能元数据在 prompt 中的 token 预算 ^[codex-rs/core/src/session/mod.rs:33]
- **技能加载输入**：`skills_load_input_from_config` 从配置层解析技能加载参数（技能根目录、过滤规则） ^[codex-rs/core/src/session/mod.rs:34]

**源码证据**：
- 入口文件：codex-rs/skills/src/lib.rs
- 系统技能安装：codex-rs/skills/src/lib.rs:32-56
- 核心技能：codex-rs/core-skills/src/lib.rs
