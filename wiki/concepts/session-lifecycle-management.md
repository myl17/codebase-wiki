---
type: concept
concept: session-lifecycle-management
problem: 如何管理会话的身份识别、持久化存储和生命周期，在跨平台、多设备、长时间间隔场景下保证正确性和可用性
concerns: [会话键的确定性与灵活性, 并发安全, 存储可演化性与检索能力]
repos: [nanobot, hermes-agent, openclaw, codex-main]
generated: 2026-06-25
---

# 会话生命周期管理

## 核心问题

Agent 框架需要在两个时间尺度上管理会话状态：微观上，同一次 LLM 循环内的消息序列必须完整且格式正确；宏观上，同一个用户隔了几个小时、几天甚至换了设备/平台再回来，应该继续之前的对话还是开启新会话？如何在"保持连续性"和"避免上下文过长"之间做权衡？

根本张力在于**会话键的设计**。会话键决定了"谁"在同一会话里——用户、设备、平台、群组、频道、线程。键太粗（如所有消息一个全局会话），不同用户或不同平台的对话混在一起；键太细（如按 (平台, 设备, 聊天ID) 复合），则用户换设备或平台后看不到之前的对话，产生割裂感。三个框架都采用了确定性键生成方案，但复合维度和灵活性差异显著。

第二个张力是**并发安全与存储可演化性**。Agent 在多用户多平台场景下，同一会话可能被并发写入。文件系统存储（JSON/JSONL）简单但并发写不安全，数据库（SQLite）安全但引入依赖和迁移负担。三个框架在复杂度光谱上选择了不同位置。

## 关切

- **会话键的确定性与灵活性**：键格式决定了会话的跨平台/跨设备/跨时间连续性——粒度太粗产生混淆，粒度太细产生割裂
- **并发安全**：多用户多平台同时写入同一会话时的数据一致性保证
- **存储可演化性与检索能力**：存储格式的 schema 演进支持、跨会话搜索、历史审计等长期运维能力

## 各框架的解法

### nanobot

来源：[[repos/nanobot/entities/session-manager]]
**解法**：简单 JSONL 文件存储 + 内存缓存，`channel:chat_id` 简单键，`unified_session` 模式可选全局单一会话。
**实现**：
- 简单会话键：默认按 `channel:chat_id` 隔离，启用 `unified_session` 时所有 channel 共享 `"unified:default"` 单一键 ^[nanobot/agent/loop.py:44]
- JSONL 格式：首行 `_type: "metadata"` 元数据记录（key、created_at、last_consolidated），后续行每行一条消息 JSON 对象 ^[nanobot/session/manager.py:189-201]
- 合法边界保证：`get_history()` 确保返回序列从 user 消息开始，孤立 tool 结果被排除，保证 LLM 接收格式正确 ^[nanobot/session/manager.py:38-61]
- 内存缓存：`_cache: dict[str, Session]` 避免每次读磁盘，save 时同步更新缓存 ^[nanobot/session/manager.py:107, 203]
- 旧版迁移：自动将 `~/.nanobot/sessions/` 旧版文件迁移到 workspace 的 `sessions/` 目录 ^[nanobot/session/manager.py:142-150]
- 无自动重置：无会话超时或定期重置机制——由内存 Consolidator 定期读取并压缩，但会话本身不自动销毁
**权衡**：极简实现——单文件 ~200 行，零外部依赖。但无并发写入保护（多消息同时到达时 JSONL 追加可能产生交错），无跨会话搜索能力，无 schema 演进（修改消息格式需手动迁移旧文件），无自动重置机制（长会话持续膨胀依赖上层压缩）。

### hermes-agent

来源：[[repos/hermes-agent/entities/session-manager]]、[[repos/hermes-agent/entities/state-database]]
**解法**：确定性复合键 + 三层重置策略 + SQLite WAL 持久化 + FTS5 全文搜索 + jitter 重试并发保护。
**实现**：
- 确定性会话键：`build_session_key()` 生成 `agent:main:<platform>:<chat_type>:<chat_id>[:<thread_id>]` 格式，DM 按 chat_id 隔离，群组/频道可选按 user_id 隔离 ^[gateway/session.py:439-496]
- 三层重置策略：`none`（永不重置）、`idle`（空闲超时默认 24h）、`daily`（每日固定时间默认 4AM）、`both`（同时满足）；重置时自动通知用户 ^[gateway/session.py:620-684]
- SQLite WAL + FTS5：Write-Ahead Logging 支持多读者 + 单写者并发，FTS5 虚拟表 + 3 触发器自动同步全文索引 ^[hermes_state.py:157, 93-112]
- Jitter 重试：写入冲突时随机 sleep 20-150ms 后重试（最多 15 次），避免 SQLite 内置退避的 convoy effect ^[hermes_state.py:132-135, 180-210]
- WAL 检查点：每 50 次成功写入后尝试 PASSIVE checkpoint，防止 WAL 文件无限增长 ^[hermes_state.py:136, 216-235]
- 6 版本 Schema 迁移：从 v1 到 v6 逐步添加列（finish_reason、title、token 计数器、billing 字段、reasoning 列），向后兼容 ^[hermes_state.py:252-332]
- 跨会话搜索工具：`session_search()` 通过 FTS5 匹配 → 加载会话 → 截断至 ~100k chars → `asyncio.gather` 并行 Gemini Flash 摘要 → 返回结构化结果，Agent 可跨会话检索历史 ^[tools/session_search_tool.py:297-498]
- 压缩感知拆分：上下文压缩时旧消息移入子会话（`parent_session_id` 链），支持会话 lineage ^[hermes_state.py:48]
- PII 脱敏：WhatsApp/Signal/Telegram/BlueBubbles 的 sender_id 和 chat_id 通过 SHA-256 确定性哈希在系统提示词中脱敏 ^[gateway/session.py:34-54]
- 挂起机制：`/stop` 或异常关闭时设置 `suspended=True`，下次消息强制自动重置 ^[gateway/session.py:789-803]
**权衡**：功能最完善——自动重置、跨会话搜索、schema 演进、PII 脱敏、压缩感知拆分。但复杂度最高：SQLite + WAL + FTS5 + 6 版本迁移 + jitter 重试 + WAL 检查点 + Gemini Flash 辅助搜索摘要。三层重置策略提供灵活的连续性控制，但不同重置模式的语义差异可能让用户困惑。跨会话搜索依赖辅模型生成摘要，增加了延迟和成本。

### openclaw

来源：[[repos/openclaw/entities/session-system]]、[[repos/openclaw/entities/routing-system]]
**解法**：结构化复合键 `agent:{id}:{channel}:{account}:{peer}` + 4 DM 范围模式 + 写锁保护 JSON 文件 + 磁盘预算强制执行 + HTML 转录归档。
**实现**：
- 结构化会话键：`agent:{normalizedAgentId}:{channel}:{accountId}:{peerKind}:{peerId}` 或简化 `agent:{agentId}:main`，确定性生成 ^[src/routing/session-key.ts]
- 4 DM 范围模式：`main`（全局单会话）、`per-peer`（每人独立）、`per-channel-peer`（按渠道+人隔离）、`per-account-channel-peer`（最细粒度，按账户+渠道+人隔离）^[src/routing/session-key.ts]
- 写锁保护：`acquireSessionWriteLock` 防止并发写入冲突——多消息同时到达时串行化写入 ^[src/config/sessions/store.ts]
- 内存缓存层：`store-cache.ts` 序列化 session store 缓存，减少磁盘 I/O ^[src/config/sessions/store-cache.ts]
- 磁盘预算强制执行：`enforceSessionDiskBudget()` 限制每会话磁盘总量，自动轮转旧文件，防止单会话无限膨胀 ^[src/config/sessions/disk-budget.ts]
- HTML 转录归档：`archiveSessionTranscripts()` 将 HTML 转录归档，支持长期审计和 review ^[src/gateway/session-utils.ts]
- 9 级路由优先级与会话键联动：路由绑定 (`binding.peer` → `binding.guild+roles` → `binding.channel` → `default`) 决定使用哪个 agent 的会话键 ^[src/routing/resolve-route.ts]
- 路由缓存：`evaluatedBindingsCacheByCfg`（2000 条目）、`resolvedRouteCacheByCfg`（4000 条目），高性能多层缓存 ^[src/routing/resolve-route.ts]
**权衡**：4 DM 范围模式提供了最精细的会话隔离控制——从"所有对话一个会话"到"每个账户每个渠道每个人独立会话"全覆盖。磁盘预算强制执行 + HTML 转录归档适合长期运维和合规场景。但 JSON 文件 + 写锁的并发模型在高并发时可能成为瓶颈（单写者阻塞其他写入），且缺乏 SQL 级检索能力（无全文搜索，检索依赖文件扫描）。路由缓存解决了大量重复查询的性能问题，但增加了缓存一致性维护成本。

### codex-main

来源：[[repos/codex-main/entities/thread-store]]、[[repos/codex-main/entities/rollout]]、[[repos/codex-main/entities/message-history]]
**解法**：`ThreadStore` trait 存储抽象 + JSONL rollout 文件 + SQLite 搜索索引 + `history.jsonl` 全局消息历史。
**实现**：
- `ThreadStore` trait 抽象跨存储后端的线程 CRUD，`LocalThreadStore` 是默认文件系统实现 ^[codex-rs/thread-store/src/lib.rs]
- `LiveThread` 与 `StoredThread` 分离运行时状态和持久化数据，`ThreadMetadataPatch` 支持部分更新 ^[codex-rs/thread-store/src/lib.rs]
- JSONL rollout 文件持久化完整会话转录，`spawn_rollout_compression_worker` 后台异步压缩旧文件 ^[codex-rs/rollout/src/compression.rs:36-40]
- SQLite 搜索索引支持全文搜索历史会话，`StateDb` 提供键值对状态持久化 ^[codex-rs/rollout/src/state_db.rs]
- `history.jsonl` 全局消息历史：`O_APPEND` 原子追加 + 软上限 80% 裁剪 + Unix 权限 600 ^[codex-rs/message-history/src/lib.rs:46-53]
**权衡**：ThreadStore trait 提供后端可替换性，但当前仅本地文件实现。JSONL + SQLite 混合存储兼顾流式追加和搜索性能。全局消息历史的 POSIX 原子写入是并发安全的最简方案，但跨平台一致性依赖 OS 语义。

## 对比

| 框架 | 会话键的确定性与灵活性 | 并发安全 | 存储可演化性与检索能力 |
|------|------|------|------|
| nanobot | 低——简单 `channel:chat_id` 或全局 `unified:default`；无重置机制 | 无——JSONL 追加无锁保护，多消息并发有交错风险 | 极低——单文件 JSONL，无 schema 演进，无搜索，无审计 |
| hermes-agent | 高——`agent:main:<platform>:<type>:<id>[:<thread>]` 确定性复合键；3 层重置策略（idle/daily/both） | 高——SQLite WAL 多读者单写者 + jitter 重试（20-150ms，最多 15 次）+ WAL checkpoint | 高——SQLite FTS5 全文搜索 + 6 版本 schema 迁移 + 跨会话搜索工具 + 压缩感知 lineage + PII 脱敏 |
| openclaw | 最高——`agent:{id}:{channel}:{account}:{peer}` 结构化键 + 4 DM 范围模式；无自动重置但有磁盘预算强制轮转 | 中——写锁保护 JSON 文件 + 内存缓存；单写者可能在高并发下成为瓶颈 | 中——JSON 文件 + 磁盘预算 + HTML 转录归档；无全文搜索，检索依赖文件扫描；路由缓存提升性能但增加一致性担 |
| codex-main | 中——ThreadStore trait 抽象 + ThreadId 线程标识 | 中——LiveThread/StoredThread 分离 + ThreadMetadataPatch 部分更新；无显式写锁 | 中——JSONL rollout + SQLite 搜索索引混合存储；全局历史 JSONL 原子追加 |

## 演化记录

- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 codex-main（ThreadStore trait + JSONL rollout + SQLite 搜索 + 全局历史 JSONL）
