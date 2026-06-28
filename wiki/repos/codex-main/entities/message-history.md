---
type: entity
repo: codex-main
slug: message-history
problem: 如何以并发安全的方式持久化用户消息历史
generated: 2026-06-28
source_files:
  - codex-rs/message-history/src/lib.rs
---

# Message History

**代码位置**：codex-rs/message-history/
**这个模块解决什么问题**：
- 实现层：通过 `~/.codex/history.jsonl` 的追加写入 + POSIX `O_APPEND` 原子写入保证 + 软上限裁剪策略，持久化跨会话的用户消息历史
- 问题层：如何以并发安全的方式持久化用户消息历史
**对外暴露什么**：
- `HistoryEntry`：历史条目（session_id, ts, text） ^[codex-rs/message-history/src/lib.rs:55-60]
- `History`：历史配置类型 ^[codex-rs/message-history/src/lib.rs:38]
- `HistoryPersistence`：历史持久化策略 ^[codex-rs/message-history/src/lib.rs:39]
- `HISTORY_FILENAME`：历史文件名常量 `history.jsonl` ^[codex-rs/message-history/src/lib.rs:46]
- `HISTORY_READ_BUFFER_SIZE`：读取缓冲区大小 8192 字节 ^[codex-rs/message-history/src/lib.rs:47]
- `MAX_RETRIES`：最大重试次数 10 ^[codex-rs/message-history/src/lib.rs:52]
- `RETRY_SLEEP`：重试间隔 100ms ^[codex-rs/message-history/src/lib.rs:53]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 在用户输入时追加消息到历史）
- 与 [[entities/rollout]] 互补（rollout 存储完整会话转录，message-history 存储全局消息列表）
**为什么它是可分离的**：独立的 crate，纯文件 IO + 并发安全保证，功能单一

**关键机制**（源码可见）：
- **JSONL 格式**：每行一个 JSON 对象 `{"session_id":"<uuid>","ts":<unix_seconds>,"text":"<message>"}`，便于流式追加和标准工具解析 ^[codex-rs/message-history/src/lib.rs:7-9]
- **POSIX 原子写入**：利用 `O_APPEND` + 单次 `write(2)` 系统调用保证多进程并发追加时行不被交错（PIPE_BUF 限制内原子） ^[codex-rs/message-history/src/lib.rs:14-15]
- **软上限裁剪**：当文件超过 `max_bytes` 硬上限，裁剪到 80% 的软上限（HISTORY_SOFT_CAP_RATIO = 0.8）避免频繁裁剪 ^[codex-rs/message-history/src/lib.rs:50]
- **重试机制**：最多重试 10 次，每次间隔 100ms，处理文件锁竞争 ^[codex-rs/message-history/src/lib.rs:52-53]
- **Unix 权限**：在 Unix 上通过 `OpenOptionsExt` 设置文件权限 600，确保历史文件的私密性 ^[codex-rs/message-history/src/lib.rs:42-43]

**源码证据**：
- 入口文件：codex-rs/message-history/src/lib.rs
- 历史条目：codex-rs/message-history/src/lib.rs:55-60
- 原子写入说明：codex-rs/message-history/src/lib.rs:1-15
