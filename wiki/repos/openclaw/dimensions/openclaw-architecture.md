---
repo: openclaw
dimension: architecture
dimensions_version: v1.0
generated: 2026-06-09
---

# OpenClaw — Architecture

OpenClaw 是一个自托管个人 AI 助手运行时，采用**九大子系统**集成架构，[[TypeScript monorepo]]。Gateway 是纯控制平面，产品核心是助手本身。

## 1. Entry / Process Supervisor

`src/entry.ts` 是 CLI 入口，初始化 compile cache（`enableCompileCache()`）、gaxios fetch compat、进程标题（`process.title = "openclaw"`），并通过 `isMainModule` 防止作为依赖被 import 时重复启动。^[src/entry.ts:37-58]

`src/process/supervisor/` 是进程看门狗，管理 `ManagedRun` / `SpawnMode` / `RunState`，负责子进程生命周期和 respawn 策略。以[[单例模式]]暴露（`getProcessSupervisor()`）。^[src/process/supervisor/index.ts:1-12]

## 2. Gateway（控制平面）

`src/gateway/` 处理 HTTP 路由、shared session 生命周期、认证 secret ref 解析（token/password/gateway auth 三种形式）。Gateway 是纯路由层——不执行 AI 调用，不持有业务逻辑。^[src/gateway/auth-config-utils.ts:31-52]

## 3. Channel Plugin 系统

`src/channels/plugins/` 定义[[插件系统]]的 `ChannelPlugin<ResolvedAccount>` 接口，每个 IM 平台实现 13+ 个 Adapter：`ChannelMessagingAdapter`、`ChannelOutboundAdapter`、`ChannelLifecycleAdapter`、`ChannelAuthAdapter`、`ChannelSetupAdapter` 等。^[src/channels/plugins/types.plugin.ts:53-94]

`extensions/` 下每个目录是独立 npm 包，支持 20+ 平台（WhatsApp、Telegram、Slack、Discord、Signal、iMessage、BlueBubbles、IRC、Matrix、Feishu、LINE 等）。数据流单向：入站 → channel resolver → session binding → agent dispatch → outbound。

## 4. Tool Policy / 权限管理

`src/agents/tool-policy-pipeline.ts` 定义多级 pipeline 过滤工具可见性——包含 profile policy、provider policy、global policy、agent policy、group policy 共 5 层叠加，每层可配置 allowlist/denylist。权限决策是消息处理关键路径上的**同步门控**，不是事后审计。^[src/agents/tool-policy-pipeline.ts:56-90]

`src/agents/bash-tools.exec-approval-request.ts` 实现 exec 类工具的异步审批协议——注册 `ExecApprovalRequest`，阻塞等待 owner 决策（`waitForExecApprovalDecision`），支持 host/gateway 双路径审批。^[src/agents/bash-tools.exec-approval-request.ts:89-126]

`src/agents/tool-policy.ts` 的 `OwnerOnlyToolApprovalClass` 将工具分为三类：`control_plane`、`exec_capable`、`interactive`，`applyOwnerOnlyToolPolicy` 根据 sender 是否为 owner 动态过滤工具集。^[src/agents/tool-policy.ts:19-55]

## 5. Agent Harness（LLM 抽象层）

`src/agents/harness/types.ts` 定义 `AgentHarness` 接口：`supports(ctx: AgentHarnessSupportContext)` 用于优先级选择，`runAttempt(params)` 执行一次 LLM 调用，`compact?(params)` 压缩上下文，`reset?(params)` 重置 session。`selectAgentHarness()` 按 priority 排序选择最合适的实现。^[src/agents/harness/types.ts:30-44]

extensions/ 下各 provider（anthropic、openai、ollama、deepseek 等）各自注册 harness 实现，对 core 透明。

## 6. Context Engine（上下文生命周期）

`src/context-engine/` 管理四个生命周期操作：`assemble`（组装 prompt）、`ingest`（摄入新消息）、`compact`（[[Context 压缩]]历史）、`transcriptRewrite`（重写 transcript）。支持可注册的 `ContextEngineFactory`，通过 `LegacyContextEngine` 向后兼容。^[src/context-engine/index.ts:1-27]

## 7. 记忆系统（Memory）

`src/memory-host-sdk/` 定义 `MemorySearchManager` 接口，封装向量搜索（结果含 path/startLine/endLine/score/snippet/citation）和语义检索。底层支持两种 backend：`builtin`（SQLite + sqlite-vec 向量扩展）和 `qmd`（外部引擎），通过 `MemorySearchRuntimeDebug.backend` 区分。^[src/memory-host-sdk/host/types.ts:1-30]

extensions 层四个可选实现：`memory-core`（核心接口）、`memory-lancedb`（LanceDB 向量存储）、`memory-wiki`（wiki-style 记忆）、`active-memory`（主动记忆注入）。**记忆在 prompt 组装阶段注入，非实时查询**。

## 8. 任务调度系统（Tasks + Cron）

`src/tasks/` 实现 TaskFlow 状态机：`createQueuedTaskRun` → `startTaskRunByRunId` → `completeTaskRunByRunId` / `failTaskRunByRunId`，状态持久化到 SQLite（`task-flow-registry.store.sqlite.ts`）。支持 flow 内多 task 级联、cancel 传播、block retry、owner 访问控制。^[src/tasks/task-executor.ts:85-112]

`src/cron/` 是定时调度器，`CronDeliveryPlan` 决定结果投递目标（channel、thread、announce、webhook）。支持 isolated-agent 模式，每次 cron 触发创建独立 agent session。**Cron 是唯一一个可以在无 IM 消息触发的情况下主动发起 agent 运行的入口**。^[src/cron/delivery-plan.ts:10-19]

## 9. 可观测性（Observability）

`extensions/diagnostics-otel/` 实现完整 [[OpenTelemetry]] 集成：Traces（`OTLPTraceExporter`）、Metrics（`OTLPMetricExporter` + `PeriodicExportingMetricReader`）、Logs（`OTLPLogExporter` + `BatchLogRecordProcessor`）三路并行导出。采样率通过 `TraceIdRatioBasedSampler` 配置，敏感内容在上报前经 `redactSensitiveText` 处理。这是**可选 extension**，不在核心依赖路径，需显式安装。^[extensions/diagnostics-otel/src/service.ts:1-13]

## 数据流（完整）

```
用户消息 (IM 平台)
  → Channel Plugin (inbound adapter)
  → Tool Policy Pipeline (owner check + 5-layer allowlist filter)
  → Session Binding (thread → session mapping)
  → Context Engine (assemble: memory inject + history compact)
  → Agent Harness (selectAgentHarness → runAttempt)
      → ContextEngine (ingest new messages)
      → Tool calls → Tool Policy (exec approval gate, async)
  → Channel Plugin (outbound adapter)
  → 用户消息

并行触发路径（无消息驱动）：
  Cron Scheduler → isolated-agent → Agent Harness
```

## 关联

*(暂无同类仓库已分析，链接待补充)*
