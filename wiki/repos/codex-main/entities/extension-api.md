---
type: entity
repo: codex-main
slug: extension-api
problem: 如何通过贡献者注册表扩展 Agent 行为
generated: 2026-06-28
source_files:
  - codex-rs/ext/extension-api/src/lib.rs
---

# Extension API

**代码位置**：codex-rs/ext/extension-api/
**这个模块解决什么问题**：
- 实现层：通过 `ExtensionDataInit` + `PromptSlot` + `LoadedUserInstructions`，定义扩展向 Agent 注入上下文、指令和能力的标准化接口
- 问题层：如何通过贡献者注册表扩展 Agent 行为
**对外暴露什么**：
- `ExtensionDataInit`：扩展数据初始化接口 ^[codex-rs/ext/extension-api/src/lib.rs]
- `LoadedUserInstructions`：已加载的用户自定义指令 ^[codex-rs/ext/extension-api/src/lib.rs]
- `PromptSlot`：提示词槽位（扩展可以向系统提示词的特定位置注入内容） ^[codex-rs/ext/extension-api/src/lib.rs]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 通过 PromptSlot 将扩展注入的指令和上下文合并到系统提示词中）
- 与 [[entities/plugin-system]] 配合（插件的指令通过 Extension API 注入）
- 与内置扩展（goal, guardian, image-generation, memories, mcp, skills, web-search）有实现关系
**为什么它是可分离的**：独立的 crate，定义扩展契约而不依赖任何特定扩展实现

**关键机制**（源码可见）：
- **提示词槽位系统**：`PromptSlot` 将系统提示词划分为多个可插拔的槽位，每个扩展可以独立注入指令到指定槽位 ^[codex-rs/ext/extension-api/src/lib.rs]
- **扩展数据初始化**：`ExtensionDataInit` trait 定义了扩展在 Agent 启动时的初始化接口 ^[codex-rs/ext/extension-api/src/lib.rs]
- **用户指令加载**：`LoadedUserInstructions` 封装了从配置、文件、云端等多个来源加载的用户自定义指令 ^[codex-rs/ext/extension-api/src/lib.rs]
- **内置扩展族**：`ext/` 目录下有 7 个内置扩展（goal、guardian、image-generation、memories、mcp、skills、web-search），均实现 Extension API 的契约

**源码证据**：
- 入口文件：codex-rs/ext/extension-api/src/lib.rs
