---
type: entity
repo: codex-main
slug: plugin-management
problem: 如何管理插件商城、安装、升级和卸载
generated: 2026-06-28
source_files:
  - codex-rs/core-plugins/src/lib.rs
  - codex-rs/core-plugins/src/manager.rs
  - codex-rs/core-plugins/src/marketplace.rs
  - codex-rs/core-plugins/src/loader.rs
---

# Plugin Management

**代码位置**：codex-rs/core-plugins/
**这个模块解决什么问题**：
- 实现层：通过 `PluginsManager` 统一管理插件的安装、卸载、升级 + `ConfiguredMarketplace` 管理商城源（openai-curated、openai-bundled） + 启动时同步远程商城
- 问题层：如何管理插件商城、安装、升级和卸载
**对外暴露什么**：
- `PluginsManager`：插件管理器核心（安装、卸载、读取、列表） ^[codex-rs/core-plugins/src/manager.rs:42]
- `PluginInstallRequest`：插件安装请求 ^[codex-rs/core-plugins/src/manager.rs:37]
- `PluginInstallOutcome`：插件安装结果 ^[codex-rs/core-plugins/src/manager.rs:36]
- `PluginUninstallError`：卸载错误类型 ^[codex-rs/core-plugins/src/manager.rs:41]
- `ConfiguredMarketplace`：已配置的商城（名称、URL、认证） ^[codex-rs/core-plugins/src/manager.rs:30]
- `ConfiguredMarketplacePlugin`：商城中的插件条目 ^[codex-rs/core-plugins/src/manager.rs:32]
- `PluginDetail`：插件详情 ^[codex-rs/core-plugins/src/manager.rs:33]
- `PluginMarketplaceUpgradeOutcome`：商城升级结果 ^[codex-rs/core-plugins/src/marketplace_upgrade.rs:45]
- `startup_sync` 模块：启动时同步远程商城列表 ^[codex-rs/core-plugins/src/startup_sync.rs]
- `ExecutorPluginProvider`：执行器插件 Provider ^[codex-rs/core-plugins/src/provider.rs:46]
- `OPENAI_CURATED_MARKETPLACE_NAME` / `OPENAI_BUNDLED_MARKETPLACE_NAME`：预置商城名 ^[codex-rs/core-plugins/src/lib.rs:21-22]
**它和谁交互**：
- 依赖 [[entities/plugin-system]]（使用 PluginId、LoadedPlugin 等类型）
- 被 [[entities/core-agent-loop]] 调用（Agent 加载插件能力）
- 与 [[entities/config-management]] 配合（插件配置来自 config 层）
- 与 [[entities/hook-system]] 配合（插件的钩子通过 PluginHookLoadOutcome 加载）
**为什么它是可分离的**：独立的 crate，插件生命周期管理逻辑与核心 Agent 解耦

**关键机制**（源码可见）：
- **双商城源**：openai-curated（OpenAI 官方维护的精选商城）和 openai-bundled（内置商城），均通过 ConfiguredMarketplace 抽象 ^[codex-rs/core-plugins/src/lib.rs:21-22]
- **启动同步**：`startup_sync` 模块在 Agent 启动时异步拉取远程商城的最新插件列表 ^[codex-rs/core-plugins/src/startup_sync.rs]
- **远程资源获取**：`remote_bundle` 和 `remote_legacy` 模块处理插件远程下载和本地缓存 ^[codex-rs/core-plugins/src/remote_bundle.rs]
- **插件存储**：`store` 模块管理插件本地安装目录（`CODEX_HOME/plugins/`）的文件布局 ^[codex-rs/core-plugins/src/store.rs]
- **发现与推荐**：`discoverable` 模块实现工具建议驱动的插件发现（ToolSuggestDiscoverablePlugin） ^[codex-rs/core-plugins/src/discoverable.rs:27-28]

**源码证据**：
- 入口文件：codex-rs/core-plugins/src/lib.rs
- 商城管理：codex-rs/core-plugins/src/marketplace.rs
- 启动同步：codex-rs/core-plugins/src/startup_sync.rs
