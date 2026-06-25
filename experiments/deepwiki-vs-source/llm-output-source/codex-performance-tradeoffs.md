# Codex Performance Tradeoffs

## 1. Remote Compaction -- 专用模型端点进行上下文压缩

**优化目标**：将上下文压缩从普通采样中分离，使用专用的 compact endpoint 避免污染正常的推理流。

**手段**：Codex 有两种 compaction 实现：`responses`（本地实现）和 `remote`（调用专用 compact endpoint）。当 provider 支持 `remote_compaction()` 时使用远程路径，将历史替换计算卸载到独立端点。Compaction 请求有独立的语义角色（`CompactionReason`、`CompactionPhase`、`CompactionTrigger`），完整的 analytics 追踪。

**源码证据**：

- `should_use_remote_compact_task()` 检查 provider 是否支持远程 compaction ^[codex-rs/core/src/compact.rs:68-70]
- Compaction 分为 `PreTurn`（预轮次）、`MidTurn`（轮次中）和 `StandaloneTurn`（独立轮次）三种阶段 ^[codex-rs/core/src/compact.rs:76-77]
- 触发方式分为 `Auto`（自动）和 `Manual`（用户触发）^[codex-rs/core/src/compact.rs:91-117]
- Compaction 原因：`UserRequested`、`ContextWindowNearlyFull` 等 ^[codex-rs/core/src/compact.rs:76]
- Remote compaction trace context 在 `codex-rs/rollout-trace/src/compaction.rs` 中实现 ^[codex-rs/rollout-trace/src/compaction.rs:1-7]
- `CompactionTraceContext` 支持重试——一个 compaction 可在安装 checkpoint 前多次重试 ^[codex-rs/rollout-trace/src/compaction.rs:30-33]
- `CompactionCheckpointTracePayload` 记录 `input_history` 和 `replacement_history` 两个完整快照 ^[codex-rs/rollout-trace/src/compaction.rs:78-87]

**牺牲**：Remote compaction 引入额外的网络往返。如果 provider 不支持远程 compaction，回退到本地 `run_inline_auto_compact_task()`，消解了性能优势。Compaction 摘要质量取决于辅助模型的性能。

---

## 2. Context Window Exceeded Recovery -- 渐进退避策略

**优化目标**：在 compaction 过程中遇到 context window exceeded 错误时，尽可能恢复而不是直接失败。

**手段**：当触发 `ContextWindowExceeded` 错误时，如果 history 长度 > 1，从开头移除最旧的一条 history item，然后重试整个 compaction 流程。这种方式保留了前缀缓存（prefix-based caching），并通过移除最旧项来释放空间。

**源码证据**：

- 错误处理分支明确："Trim from the beginning to preserve cache (prefix-based) and keep recent messages intact" ^[codex-rs/core/src/compact.rs:255-264]
- 仅在 `turn_input_len > 1` 时尝试 trim（如果 trim 后只剩 1 项则直接失败）^[codex-rs/core/src/compact.rs:256]
- Trim 后重置重试计数器（`retries = 0`），重新开始 compaction ^[codex-rs/core/src/compact.rs:262-263]
- 如果 trim 不可行，则设置 `total_tokens_full` 并报告错误事件 ^[codex-rs/core/src/compact.rs:265-269]
- 一般错误也支持重试（`max_retries`），使用指数退避 `backoff(retries)` ^[codex-rs/core/src/compact.rs:271-290]

**牺牲**：移除最旧 history item 会丢失早期对话上下文。丢失的上下文不会被总结而是直接丢弃，可能影响 compaction 摘要的完整性。多次 trim 可能导致信息持续丢失。

---

## 3. Initial Context Injection 策略 -- 按 compaction 阶段选择注入方式

**优化目标**：确保 compaction 后的对话上下文正确重建，同时尽量避免不必要的 token 消耗。

**手段**：根据 compaction 阶段选择不同的初始上下文注入策略。Pre-turn/manual compaction 使用 `DoNotInject`：完全替换 history 为摘要，清除 `reference_context_item`，让下一个常规轮次重新注入完整初始上下文。Mid-turn compaction 使用 `BeforeLastUserMessage`：在 replacement history 中最后一条真实用户消息之前注入初始上下文，因为模型训练时预期 mid-turn compaction 后 summary 作为 history 的最后一项。

**源码证据**：

- `InitialContextInjection` 枚举定义两种策略 ^[codex-rs/core/src/compact.rs:53-66]
- Pre-turn/manual 路径使用 `DoNotInject`，清除 reference context item ^[codex-rs/core/src/compact.rs:116-117]
- Mid-turn auto 路径使用 `BeforeLastUserMessage` ^[codex-rs/core/src/compact.rs:90-91]
- `insert_initial_context_before_last_real_user_or_summary()` 将初始上下文注入到指定位置 ^[codex-rs/core/src/compact.rs:306-309]

**牺牲**：`DoNotInject` 模式意味着下一个轮次需要完全重建初始上下文（增加单次 API 调用的 token 开销）。`BeforeLastUserMessage` 在 replacement history 中保留了更多 token，但保持了与模型训练格式的一致性。

---

## 4. BlockingLruCache -- 异步安全的 LRU 缓存 with Runtime Detection

**优化目标**：在异步运行时中提供线程安全的缓存，同时在不具备 Tokio runtime 的上下文中优雅降级为无缓存模式。

**手段**：`BlockingLruCache` 封装 `tokio::sync::Mutex<LruCache>`，使用 `block_in_place` 避免阻塞异步运行时。当不在 Tokio runtime 中时，所有操作变为 no-op（不 panic，不缓存）。支持容量配置、`get_or_insert_with` 延迟计算、`get_or_try_insert_with` 可失败工厂。

**源码证据**：

- `lock_if_runtime()` 尝试获取当前 Tokio runtime handle，失败时返回 None（调用方优雅降级） ^[codex-rs/utils/cache/src/lib.rs:122-128]
- `get_or_insert_with` 和 `get_or_try_insert_with` 在无 runtime 时直接调用 value factory 不缓存 ^[codex-rs/utils/cache/src/lib.rs:30-64]
- `try_with_capacity` 仅在 capacity > 0 时创建缓存，否则返回 None ^[codex-rs/utils/cache/src/lib.rs:67-70]
- 提供 `with_mut` 直接操作底层 `LruCache` 的方法 ^[codex-rs/utils/cache/src/lib.rs:107-114]
- 附带 `sha1_digest()` 工具函数用于基于内容的缓存键生成，避免仅路径键的陈旧性 ^[codex-rs/utils/cache/src/lib.rs:130-142]
- 测试覆盖了无 runtime 场景的 no-op 行为 ^[codex-rs/utils/cache/src/lib.rs:172-192]

**牺牲**：在无 runtime 上下文中缓存完全失效——无法减少重复计算。`block_in_place` 可能临时占用工作线程。LRU 淘汰策略是全局的，不考虑键的访问频率差异。

---

## 5. Rollout Trace -- Best-Effort 全链路追踪

**优化目标**：在不阻塞主执行路径的前提下记录完整的 agent rollout 事件（推理调用、工具调用、compaction 数据）。

**手段**：Rollout trace 的一切操作都是 best-effort：启动失败不阻塞 agent、写入失败只发出 warning。Trace writer 使用异步写入队列，payload 被序列化为 JSON 并持久化到磁盘。Compaction 追踪是其中唯一的 first-class checkpoint 模型。

**源码证据**：

- README 明确声明："Trace startup and writes are best-effort. Rollout tracing must never make a codex session less reliable" ^[codex-rs/rollout-trace/README.md:99-100]
- Thread trace 中 `invocation` 是 lazy 的："adapting core tool objects into trace-owned" ^[codex-rs/rollout-trace/src/thread.rs:336]
- 提供 `disabled()` 模式用于创建不记录任何内容的 no-op handle ^[codex-rs/rollout-trace/src/compaction.rs:91-95]
- `write_json_payload_best_effort` 包装写入操作忽略失败 ^[codex-rs/rollout-trace/src/compaction.rs:262-268]
- `append_with_context_best_effort` 同样忽略写入失败 ^[codex-rs/rollout-trace/src/compaction.rs:270-279]
- Compaction 请求 ID 使用 `AtomicU64` 原子递增（relaxed ordering），零锁开销 ^[codex-rs/rollout-trace/src/compaction.rs:28,257-260]
- `truncate_preview` 截断长输入以减少 trace 体积 ^[codex-rs/rollout-trace/src/tool_dispatch.rs:336]

**牺牲**：Best-effort 意味着 tracing 数据可能丢失（不保证完整）。`Relaxed` ordering 在极高并发下可能导致 ID 竞争。截断 preivew 丢失了工具调用的完整参数信息。

---

## 6. Compaction Analytics -- 全方位遥测跟踪

**优化目标**：收集 compaction 事件的全方位遥测数据，用于监控和调优。

**手段**：`CompactionAnalyticsAttempt` 记录 compaction 前后的 `active_context_tokens`、触发方式、原因、策略、状态、耗时（毫秒级）等维度。数据通过 `analytics_events_client.track_compaction()` 上报。

**源码证据**：

- `CompactionAnalyticsAttempt::begin()` 在 compaction 开始时记录 thread_id、turn_id、trigger、reason 和初始 token 使用量 ^[codex-rs/core/src/compact.rs:352-373]
- `track()` 方法在 compaction 结束时记录完整事件：前后 token 计数、保留图片数、摘要 token 数、缓存输入 token 数、耗时 ^[codex-rs/core/src/compact.rs:375-416]
- 策略固定为 `CompactionStrategy::Memento`（快照式历史替换） ^[codex-rs/core/src/compact.rs:400]
- `CompactionAnalyticsDetails` 结构体支持可选字段：`active_context_tokens_before`、`retained_image_count`、`compaction_summary_tokens`、`cached_input_tokens` ^[codex-rs/core/src/compact.rs:344-349]
- `compaction_status_from_result()` 将 `CodexResult` 映射为 `Completed`/`Interrupted`/`Failed` 状态 ^[codex-rs/core/src/compact.rs:419-425]

**牺牲**：Analytics 收集引入额外的内存分配（结构体构造）和异步调用开销。`Instant::elapsed()` 的时间精度受操作系统影响。

---

## 7. Cache-Friendly History Management -- 前缀保留的 Trim 策略

**优化目标**：在需要释放上下文空间时，优先保留近期消息以维持 cache 前缀一致性。

**手段**：当 compaction 过程中触发 context window exceeded 时，从 history 开头删除最旧项（"Trim from the beginning to preserve cache"），而非从末尾删除。这保持了 prefix-based caching 的有效性——因为末尾的消息是变化的而前缀是稳定的。

**源码证据**：

- Compaction 错误处理中的注释明确说明 trim 策略原因 ^[codex-rs/core/src/compact.rs:257-258]
- `history.remove_first_item()` 删除最旧的历史项 ^[codex-rs/core/src/compact.rs:261]
- Compaction 完成后调用 `sess.recompute_token_usage()` 更新 token 计数 ^[codex-rs/core/src/compact.rs:321]
- `COMPACT_USER_MESSAGE_MAX_TOKENS: usize = 20_000` 限制 compaction 中保留的用户消息 token 量 ^[codex-rs/core/src/compact.rs:51]

**牺牲**：丢弃早期上下文可能丢失初始指令或关键决策信息。Trim 策略不区分消息的重要性——同等对待所有消息。

---

## 8. Codex Thread Store -- Session 持久化的内存 vs 磁盘权衡

**优化目标**：提供线程（session）数据的持久化存储，同时支持内存缓存以提升访问速度。

**手段**：Thread store 提供 `Local`（文件系统）和 `InMemory`（内存）两种后端。`live_thread` 抽象支持活跃线程的实时读写。

**源码证据**：

- Thread store 文件结构：`local/` 下有 search、delete、unarchive 等操作 ^[codex-rs/thread-store/src/]
- `in_memory.rs` 提供零 I/O 延迟的纯内存实现 ^[codex-rs/thread-store/src/in_memory.rs]
- `live_thread.rs` 抽象活跃线程的实时状态管理 ^[codex-rs/thread-store/src/live_thread.rs]
- `codex_thread.rs` 中的 `get_total_token_usage()` 返回线程级 token 使用快照 ^[codex-rs/core/src/codex_thread.rs:422]

**牺牲**：内存后端在进程重启时丢失全部数据。文件系统后端涉及序列化开销。两种后端的切换需要不同的序列化策略。

---

## 性能权衡汇总

| 优化项 | 优化目标 | 手段 | 牺牲 | 关键文件 |
|--------|---------|------|------|---------|
| Remote Compaction | 压缩质量 / 推理隔离 | 专用 compact endpoint 分离压缩 | 额外网络往返、fallback 到本地 | `codex-rs/core/src/compact.rs:68-70` |
| Context Window Recovery | 压缩鲁棒性 | Trim 最旧 item + 重试 | 早期上下文丢失 | `codex-rs/core/src/compact.rs:255-264` |
| Initial Context Injection | Token 效率 / 格式一致性 | DoNotInject vs BeforeLastUserMessage | 下次轮次重建开销 vs 空间占用 | `codex-rs/core/src/compact.rs:53-66` |
| BlockingLruCache | 缓存可用性 | Runtime 检测 + 无 Runtime 降级 | 无 Runtime 时缓存失效 | `codex-rs/utils/cache/src/lib.rs:122-128` |
| Rollout Trace | 可观测性 | Best-effort 异步写入 | 数据可能丢失 | `codex-rs/rollout-trace/README.md:99-100` |
| Compaction Analytics | 监控调优 | 完整事件 + 毫秒级耗时 | 内存分配 + 异步调用开销 | `codex-rs/core/src/compact.rs:352-416` |
| Prefix-First Trim | Cache 命中率 | 删旧留新保持前缀稳定 | 早期信息丢失 | `codex-rs/core/src/compact.rs:257-261` |
| Thread Store Dual Backend | 访问速度 vs 持久化 | 内存 + 文件两套后端 | 进程重启数据丢失（内存模式） | `codex-rs/thread-store/src/` |
