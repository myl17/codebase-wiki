---
type: entity
repo: codex-main
slug: connectors
problem: 如何发现和缓存外部应用连接器目录
generated: 2026-06-28
source_files:
  - codex-rs/connectors/src/lib.rs
  - codex-rs/connectors/src/directory_cache.rs
  - codex-rs/connectors/src/metadata.rs
---

# Connectors

**代码位置**：codex-rs/connectors/
**这个模块解决什么问题**：
- 实现层：通过 `ConnectorDirectoryCacheContext` + 带 TTL 的内存缓存 + 从后端 API 拉取 `AppInfo` 列表，为 Agent 提供可用的外部应用连接器目录
- 问题层：如何发现和缓存外部应用连接器目录
**对外暴露什么**：
- `ConnectorDirectoryCacheContext`：连接器目录缓存上下文 ^[codex-rs/connectors/src/directory_cache.rs:20]
- `ConnectorDirectoryCacheKey`：缓存键（含 base_url, account_id, user_id） ^[codex-rs/connectors/src/lib.rs:25-30]
- `CONNECTORS_CACHE_TTL`：缓存 TTL（3600 秒） ^[codex-rs/connectors/src/lib.rs:22]
- `AppInfo`：应用信息（来自 protocol） ^[codex-rs/connectors/src/lib.rs:10]
- `AppMetadata`：应用元数据 ^[codex-rs/connectors/src/lib.rs:11]
- `AppBranding`：应用品牌信息 ^[codex-rs/connectors/src/lib.rs:9]
- `DirectoryListResponse`：目录列表响应 ^[codex-rs/connectors/src/lib.rs:59]
- `filter` 模块：连接器过滤逻辑 ^[codex-rs/connectors/src/filter.rs]
- `merge` 模块：多源连接器合并 ^[codex-rs/connectors/src/merge.rs]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 通过 connectors 模块发现可用的外部应用）
- 与 [[entities/plugin-system]] 配合（插件的 AppDeclaration 连接器 ID 通过 connectors 解析为具体的 AppInfo）
**为什么它是可分离的**：独立的 crate，纯外部服务目录的发现和缓存层

**关键机制**（源码可见）：
- **带 TTL 的内存缓存**：`CONNECTOR_DIRECTORY_CACHE` 是 `LazyLock<StdMutex<Option<CachedConnectorDirectory>>>`，TTL 为 1 小时 ^[codex-rs/connectors/src/lib.rs:22,55-56]
- **多账户缓存键**：`ConnectorDirectoryCacheKey` 按 `chatgpt_base_url + account_id + user_id` 组合区分不同账户的目录 ^[codex-rs/connectors/src/lib.rs:25-30]
- **目录序列化**：`DirectoryListResponse` 从后端 API JSON 反序列化，包含 app 列表 ^[codex-rs/connectors/src/lib.rs:58-60]
- **过滤与合并**：`filter` 模块支持按条件筛选连接器，`merge` 模块处理多源连接器的合并去重 ^[codex-rs/connectors/src/filter.rs:14-16]
- **可访问性检查**：`accessible` 模块验证连接器对当前用户是否可用 ^[codex-rs/connectors/src/accessible.rs]

**源码证据**：
- 入口文件：codex-rs/connectors/src/lib.rs
- 缓存定义：codex-rs/connectors/src/lib.rs:22,55-56
- 缓存键：codex-rs/connectors/src/lib.rs:25-30
