---
type: entity
repo: openclaw
slug: session-system
problem: "如何在本地文件系统中管理 agent 会话的存储、转录、压缩检查点和磁盘预算？"
generated: 2026-06-25
source_files:
  - src/config/sessions/
---

# Session System

**代码位置**：`src/config/sessions/`
**这个模块解决什么问题**：
- 实现层：通过文件系统存储 + 写锁 + 内存缓存 + 磁盘预算强制执行实现会话全生命周期管理
- 问题层：如何在本地文件系统中管理 agent 会话的存储、转录、压缩检查点和磁盘预算？
**对外暴露什么**：
- `updateSessionStore()` / `loadSessionStore()` — 会话持久化读写 ^[src/config/sessions/store.ts]
- `SessionEntry` 类型 — 会话条目（key, metadata, origin, context, delivery info） ^[src/config/sessions/types.ts]
- `SessionScope` — `"per-sender" | "global"` ^[src/config/sessions/types.ts]
- `acquireSessionWriteLock()` — 写锁获取 ^[src/config/sessions/store.ts]
- `enforceSessionDiskBudget()` — 磁盘预算检查 ^[src/config/sessions/disk-budget.ts]
- `archiveSessionTranscripts()` — 转录归档 ^[src/gateway/session-utils.ts]
- `resolveSessionKey()` — 会话键解析（agent:{agentId}:{channel}:{account}:{peer} 格式） ^[src/routing/session-key.ts]
**它和谁交互**：
- 依赖 [[entities/routing-system]]（会话键构造）
- 依赖 [[entities/config-system]]（会话路径配置）
- 被 [[entities/gateway]] 用于会话列表/历史/归档
- 被 [[entities/agent-runtime]] 用于会话历史读取
- 被 [[entities/subagent-system]] 用于子 agent 会话
**为什么它是可分离的**：文件系统存储 + 缓存 + 锁的封装，通过函数接口暴露

**关键机制**（源码可见）：
- 会话键格式：`agent:{normalizedAgentId}:{channel}:{accountId}:{peerKind}:{peerId}` 或 `agent:{agentId}:main` ^[src/routing/session-key.ts]
- DM 范围模式：`main`（全局单会话）| `per-peer`（每人独立）| `per-channel-peer` | `per-account-channel-peer` ^[src/routing/session-key.ts]
- 写锁保护：`acquireSessionWriteLock` 防止并发写入冲突 ^[src/config/sessions/store.ts]
- 磁盘预算监控：限制每会话磁盘使用总量，自动轮转旧文件 ^[src/config/sessions/disk-budget.ts]
- 转录管理：HTML 转录文件 → 归档 → 磁盘维护 ^[src/config/sessions/transcript.ts]
- 缓存层：`store-cache.ts` 内存缓存序列化的 session store，减少磁盘 I/O ^[src/config/sessions/store-cache.ts]
- 压缩检查点：`SessionCompactionCheckpointReason` 追踪压缩触发原因 ^[src/config/sessions/types.ts]

**源码证据**：
- 入口文件：src/config/sessions.ts
- 存储引擎：src/config/sessions/store.ts
- 类型定义：src/config/sessions/types.ts
- 会话键：src/routing/session-key.ts
- 转录管理：src/config/sessions/transcript.ts
- 磁盘预算：src/config/sessions/disk-budget.ts
- 网关侧工具：src/gateway/session-utils.ts

**关联 Concept**：
- [[concepts/session-lifecycle-management]]
