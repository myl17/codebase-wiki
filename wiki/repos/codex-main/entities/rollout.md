---
type: entity
repo: codex-main
slug: rollout
problem: 如何持久化、发现和搜索 Agent 会话转录
generated: 2026-06-28
source_files:
  - codex-rs/rollout/src/lib.rs
  - codex-rs/rollout/src/recorder.rs
  - codex-rs/rollout/src/compression.rs
  - codex-rs/rollout/src/search.rs
  - codex-rs/rollout/src/state_db.rs
---

# Rollout

**代码位置**：codex-rs/rollout/
**这个模块解决什么问题**：
- 实现层：通过 rollout 文件（压缩的 JSONL 日志）+ SQLite 搜索索引 + `StateDb` 状态数据库，实现 Agent 会话的持久化、浏览和全文搜索
- 问题层：如何持久化、发现和搜索 Agent 会话转录
**对外暴露什么**：
- `RolloutConfig`：Rollout 配置（目录、压缩策略） ^[codex-rs/rollout/src/config.rs:42]
- `RolloutLineReader`：Rollout 文件行读取器 ^[codex-rs/rollout/src/compression.rs:36]
- `spawn_rollout_compression_worker`：启动压缩后台任务 ^[codex-rs/rollout/src/compression.rs:40]
- `get_threads`：列出所有会话 ^[codex-rs/rollout/src/list.rs:55]
- `ThreadItem`：会话列表条目 ^[codex-rs/rollout/src/list.rs:45]
- `ThreadListConfig`：会话列表配置（排序、过滤、分页） ^[codex-rs/rollout/src/list.rs:47]
- `Cursor`：分页游标 ^[codex-rs/rollout/src/list.rs:44]
- `read_session_meta_line`：读取会话元数据行 ^[codex-rs/rollout/src/list.rs:59]
- `StateDbHandle`：状态数据库句柄（SQLite） ^[codex-rs/rollout/src/state_db.rs]
- `RolloutLineReader`（压缩读取）、`interactive_session_sources`（交互式会话源列表） ^[codex-rs/rollout/src/lib.rs:25-33]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 将每个回合写入 rollout 文件）
- 被 [[entities/app-server]] 使用（列出和读取会话）
- 依赖 `thread-store` 进行线程持久化
- 与 [[entities/message-history]] 配合（消息历史也有独立的持久化层）
**为什么它是可分离的**：独立的 crate，纯持久化层，Session 文件的读写和搜索功能与 Agent 核心逻辑解耦

**关键机制**（源码可见）：
- **Sessions 目录结构**：rollout 文件存储在 `sessions/` 子目录，归档的放在 `archived_sessions/` ^[codex-rs/rollout/src/lib.rs:24-25]
- **压缩与解压**：`spawn_rollout_compression_worker` 后台异步压缩旧 rollout 文件，`RolloutLineReader` 透明读取压缩/未压缩文件 ^[codex-rs/rollout/src/compression.rs:36-40]
- **SQLite 搜索索引**：`sqlite_metrics` 和 `search` 模块建立全文搜索索引，支持快速查找历史会话 ^[codex-rs/rollout/src/search.rs]
- **StateDb**：`state_db` 模块提供键值对的状态持久化（如 Agent 记忆、配置状态），基于 SQLite ^[codex-rs/rollout/src/state_db.rs]
- **会话元数据**：`SessionMeta` 和 `read_session_meta_line` 支持快速读取会话的标题、时间、模型等元数据而不需解析全文 ^[codex-rs/rollout/src/list.rs:59]

**源码证据**：
- 入口文件：codex-rs/rollout/src/lib.rs
- 列表查询：codex-rs/rollout/src/list.rs:44-60
- 压缩管理：codex-rs/rollout/src/compression.rs:36-40
