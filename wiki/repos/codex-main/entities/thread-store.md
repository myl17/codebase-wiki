---
type: entity
repo: codex-main
slug: thread-store
problem: 如何抽象跨存储后端的对话持久化
generated: 2026-06-28
source_files:
  - codex-rs/thread-store/src/lib.rs
  - codex-rs/core/src/codex_thread.rs
---

# Thread Store

**代码位置**：codex-rs/thread-store/
**这个模块解决什么问题**：
- 实现层：通过 `ThreadStore` trait 抽象 + `LocalThreadStore` 本地文件实现，提供线程（对话）的创建、读取、恢复、元数据管理等持久化操作
- 问题层：如何抽象跨存储后端的对话持久化
**对外暴露什么**：
- `ThreadStore`：线程存储 trait ^[codex-rs/thread-store/src/lib.rs]
- `LocalThreadStore`：本地文件系统线程存储实现 ^[codex-rs/thread-store/src/lib.rs]
- `StoredThread`：持久化的线程数据 ^[codex-rs/thread-store/src/lib.rs]
- `LiveThread`：活跃（正在运行）的线程句柄 ^[codex-rs/thread-store/src/lib.rs]
- `ThreadMetadataPatch`：线程元数据补丁 ^[codex-rs/thread-store/src/lib.rs]
- `CreateThreadParams`：创建线程参数 ^[codex-rs/thread-store/src/lib.rs]
- `ReadThreadParams`：读取线程参数 ^[codex-rs/thread-store/src/lib.rs]
- `ResumeThreadParams`：恢复线程参数 ^[codex-rs/thread-store/src/lib.rs]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（`CodexThread` 使用 `thread_store` 持久化线程状态）
- 被 [[entities/rollout]] 使用（rollout 文件存储与线程存储协作）
- 被 [[entities/app-server]] 使用（列出和管理线程）
**为什么它是可分离的**：独立的 crate，通过 trait 抽象存储后端，可以替换为 SQLite/远程等实现

**关键机制**（源码可见）：
- **Trait 抽象**：`ThreadStore` trait 定义了统一的线程 CRUD 接口，`LocalThreadStore` 是默认的文件系统实现 ^[codex-rs/thread-store/src/lib.rs]
- **活跃线程与持久化分离**：`LiveThread` 和 `StoredThread` 分离了运行时状态和持久化数据，避免锁竞争 ^[codex-rs/thread-store/src/lib.rs]
- **元数据管理**：`ThreadMetadataPatch` 支持对线程元数据的部分更新，避免全量覆写 ^[codex-rs/thread-store/src/lib.rs]
- **线程恢复**：`ResumeThreadParams` 支持从中断的线程恢复执行，保留上下文和配置 ^[codex-rs/thread-store/src/lib.rs]

**源码证据**：
- 入口文件：codex-rs/thread-store/src/lib.rs
- 线程创建参数：codex-rs/core/src/codex_thread.rs:143-144
