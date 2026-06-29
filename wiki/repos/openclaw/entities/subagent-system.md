---
type: entity
repo: openclaw
slug: subagent-system
problem: "如何管理子 agent 的孵化、跟踪、完成和孤立恢复，支持嵌套执行和超时控制？"
generated: 2026-06-25
source_files:
  - src/agents/subagent-registry.ts
  - src/agents/subagent-spawn.ts
---

# Subagent System

**代码位置**：`src/agents/subagent-registry.ts`、`src/agents/subagent-spawn.ts`
**这个模块解决什么问题**：
- 实现层：通过子 agent 注册表（内存 + 磁盘持久化）管理完整的 spawn→track→complete→cleanup 生命周期，含孤立恢复和 announce 重试
- 问题层：如何管理子 agent 的孵化、跟踪、完成和孤立恢复，支持嵌套执行和超时控制？
**对外暴露什么**：
- `SubagentRunRecord` 类型 — 子 agent 运行记录（id, sessionKey, status, depth, model, timeout） ^[src/agents/subagent-registry.types.ts]
- `createSubagentRegistry(deps)` — 创建注册表（DI 模式） ^[src/agents/subagent-registry.ts]
- `SpawnSubagentMode` / `SpawnSubagentSandboxMode` — 孵化模式 ^[src/agents/subagent-spawn.ts]
- `resolveSubagentDepth()` — 深度控制，防止无限递归 ^[src/agents/subagent-depth.ts]
- `persistSubagentRunsToDisk()` / `restoreSubagentRunsFromDisk()` — 状态持久化 ^[src/agents/subagent-registry-state.ts]
- `reconcileOrphanedRestoredRuns()` — 孤立运行恢复 ^[src/agents/subagent-registry-helpers.ts]
**它和谁交互**：
- 依赖 [[entities/agent-runtime]]（子 agent 执行）
- 依赖 [[entities/session-system]]（子 agent 会话存储）
- 依赖 [[entities/model-configuration]]（孵化时的模型选择）
- 依赖 [[entities/gateway]]（通过 callGateway 与网关通信）
- 依赖 [[entities/hooks-system]]（子 agent 结束时触发生命周期钩子）
- 被 [[entities/tool-system]] 的 `sessions_spawn` 工具调用
**为什么它是可分离的**：通过 DI 构造的注册表模式，完整的 spawn→track→complete 生命周期独立管理

**关键机制**（源码可见）：
- 注册表 DI 构造：`SubagentRegistryDeps` 注入 callGateway、persistState、resolveTimeout 等依赖 ^[src/agents/subagent-registry.ts:33-56]
- 内存 + 磁盘双层存储：`subagentRuns` Map（内存）+ `persistSubagentRunsToDisk`（磁盘） ^[src/agents/subagent-registry-memory.ts]
- 定期清扫：`setInterval` sweeper 处理孤立运行和清理 ^[src/agents/subagent-registry.ts]
- 孤立恢复：`reconcileOrphanedRestoredRuns` 恢复未正常完成的子 agent ^[src/agents/subagent-registry-helpers.ts]
- Announce 重试：指数退避，`MAX_ANNOUNCE_RETRY_COUNT` 限制 ^[src/agents/subagent-registry-helpers.ts:23-25]
- 生命周期事件：`SUBAGENT_ENDED_REASON_COMPLETE | ERROR | KILLED` ^[src/agents/subagent-lifecycle-events.ts:17-19]
- 深度限制：`DEFAULT_SUBAGENT_MAX_SPAWN_DEPTH` 防止无限嵌套 ^[src/agents/subagent-depth.ts]

**源码证据**：
- 注册表：src/agents/subagent-registry.ts
- 孵化逻辑：src/agents/subagent-spawn.ts
- 类型定义：src/agents/subagent-registry.types.ts
- 状态持久化：src/agents/subagent-registry-state.ts
- 查询函数：src/agents/subagent-registry-queries.ts
- Announce 流程：src/agents/subagent-announce.ts

**关联 Concept**：
- [[concepts/subagent-orchestration]]
