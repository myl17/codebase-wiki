---
type: entity
repo: codex-main
slug: plugin-system
problem: 如何建模插件包的标识、能力和钩子元数据
generated: 2026-06-28
source_files:
  - codex-rs/plugin/src/lib.rs
  - codex-rs/plugin/src/plugin_id.rs
  - codex-rs/plugin/src/manifest.rs
  - codex-rs/plugin/src/provider.rs
---

# Plugin System

**代码位置**：codex-rs/plugin/
**这个模块解决什么问题**：
- 实现层：通过 `PluginId` 标识符 + `PluginManifest` 清单 + `PluginProvider` 来源抽象 + `PluginCapabilitySummary` 能力声明，为插件包提供统一的元数据模型
- 问题层：如何建模插件包的标识、能力和钩子元数据
**对外暴露什么**：
- `PluginId`：插件唯一标识符（name+owner 格式） ^[codex-rs/plugin/src/plugin_id.rs:15]
- `PluginManifest`：插件清单（声明技能、MCP 服务器、应用连接器） ^[codex-rs/plugin/src/manifest.rs]
- `PluginProvider`：插件来源 Provider trait ^[codex-rs/plugin/src/provider.rs:22]
- `ResolvedPlugin`：已解析的插件（位置 + Provider 信息） ^[codex-rs/plugin/src/provider.rs:24]
- `LoadedPlugin`：已加载的插件（清单 + 有效技能根目录） ^[codex-rs/plugin/src/load_outcome.rs:16]
- `PluginLoadOutcome`：插件加载结果 ^[codex-rs/plugin/src/load_outcome.rs:17]
- `PluginCapabilitySummary`：插件能力摘要（技能数、MCP 服务器名、App 连接器 ID） ^[codex-rs/plugin/src/lib.rs:51-59]
- `PluginHookSource`：插件的钩子源信息（钩子文件位置和内容） ^[codex-rs/plugin/src/lib.rs:61-69]
- `PluginTelemetryMetadata`：插件遥测元数据 ^[codex-rs/plugin/src/lib.rs:71-78]
- `AppDeclaration`：App 连接器声明（名称、类别） ^[codex-rs/plugin/src/lib.rs:31-36]
- `AppConnectorId`：App 连接器 ID ^[codex-rs/plugin/src/lib.rs:28-29]
**它和谁交互**：
- 被 [[entities/plugin-management]] 调用（core-plugins 使用 plugin 的类型定义进行安装/卸载/升级）
- 与 [[entities/hook-system]] 配合（插件的钩子通过 PluginHookSource 接入 Hook 引擎）
- 与 [[entities/codex-mcp-integration]] 配合（插件的 MCP 服务器配置通过 PluginMcpConfig 解析）
**为什么它是可分离的**：独立的 crate，纯数据模型层，定义插件生态的类型系统而不涉及具体管理逻辑

**关键机制**（源码可见）：
- **插件标识符规范**：`PluginId` 格式为 `<namespace>/<name>`，`validate_plugin_segment` 校验各段合法性 ^[codex-rs/plugin/src/plugin_id.rs:15-20]
- **多能力声明**：每个插件可同时声明技能（has_skills）、MCP 服务器（mcp_server_names）、App 连接器（app_connector_ids） ^[codex-rs/plugin/src/lib.rs:51-59]
- **来源抽象**：`PluginProvider` trait 统一了本地目录、远程 registry、内置 bundle 等不同插件来源 ^[codex-rs/plugin/src/provider.rs:22]
- **加载与验证**：`LoadedPlugin` 包含有效技能根目录的路径解析结果，在加载阶段完成路径验证 ^[codex-rs/plugin/src/load_outcome.rs:15-17]
- **钩子集成**：`PluginHookSource` 携带插件的钩子文件路径和解析后的 `HookEventsToml`，直接注入到 Hooks 引擎 ^[codex-rs/plugin/src/lib.rs:61-69]

**源码证据**：
- 入口文件：codex-rs/plugin/src/lib.rs
- 能力摘要：codex-rs/plugin/src/lib.rs:51-59
- 插件 ID：codex-rs/plugin/src/plugin_id.rs:15-20
- 来源抽象：codex-rs/plugin/src/provider.rs:22-25
