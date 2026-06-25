# OpenClaw 架构维度

## 核心抽象

### Gateway（网关控制平面）

Gateway 是 OpenClaw 的中央控制平面，一个基于 Node.js 的多路复用服务进程，协调所有客户端、通道、Agent 和工具之间的通信。它是配置、会话和多平台消息的唯一真实来源 (single source of truth)。^[src/gateway/server.impl.ts:165-166]

Gateway 的核心职责包括：
- **协议连接**：WebSocket 客户端通过 Gateway 进行 RPC 调用和事件订阅。^[src/gateway/server.impl.ts:112-112]
- **通道路由**：来自 Telegram、Discord 等平台的消息被标准化并路由到 Agent。^[src/gateway/server.impl.ts:4-9]
- **Agent 编排**：Gateway 调用 Agent 运行并流式返回结果，管理整个执行流水线。^[src/gateway/server.impl.ts:3-4]
- **配置管理**：运行时配置被加载、验证并支持热重载。^[src/gateway/server.impl.ts:12-19]
- **模型认证预热**：启动时预取模型提供商的认证状态，减少首次 Agent 执行的延迟。^[src/gateway/server-startup-post-attach.ts:188-191]

Gateway 对外暴露 RPC 方法族，按域组织并通过 `createGatewayMethodRegistry` 注册，同时允许插件扩展方法集。^[src/gateway/methods/registry.ts:65-69]

### Agent（智能体运行时）

Agent 是由执行流水线驱动的隔离运行时上下文。每个 Agent 管理自己的工作区、模型提供商和工具执行逻辑。^[docs/gateway/config-agents.md:14-17]

Agent 隔离模型的关键资源：
- **工作区**：`~/.openclaw/workspace-<agentId>`，为工具和本地技能提供文件系统上下文。^[src/gateway/server-methods/agent.test.ts:122-133]
- **Agent 目录**：`~/.openclaw/agents/<agentId>/`，包含 `auth-profiles.json` 和 `models.json` 等 Agent 专属配置。^[src/gateway/server-methods/agent.ts:120-125]
- **会话存储**：每个 Agent 维护独立的会话元数据和 JSONL 转录文件。^[src/gateway/server-methods/sessions.ts:50-58]

Agent 配置采用分层结构：`agents.defaults` 提供共享默认值（工作区、模型、内存），`agents.list[]` 定义个体覆盖。^[docs/gateway/config-agents.md:46-56]

### Session（会话）

Session 是对话状态的边界。OpenClaw 使用灵活的会话作用域模型，Session 通过唯一 Key 标识，并持久化为 JSONL 转录文件。^[src/config/sessions/store.ts:42-46]

支持的会话作用域模式：
- **`main`**：单个全局会话，所有通道共享。^[src/routing/session-key.ts:25-25]
- **`agent`**：作用域限定到特定 Agent 实例。
- **`subagent`**：为任务委派生成的特殊会话。

Session Key 编码了路由信息，典型格式为 `agent:<agentId>:<channel>:<kind>:<id>`。^[src/routing/session-key.js:72-73] 系统通过 `parseAgentSessionKey` 解析和分类 Session Key，区分持久用户会话和合成运行时会话（如 `cron`、`subagent`、`acp`）。^[src/routing/session-key.js:86-91]

会话存储采用双层结构：`sessions.json` 作为元数据索引（映射 sessionKey 到 UUID、更新时间戳、会话文件路径），而每个会话的完整对话历史存储在 `.jsonl` 附加日志文件中。^[src/config/sessions/transcript.ts:62-75] ^[src/config/sessions/types.ts:33-34] 为优化性能，系统实现了多层缓存，包括序列化字符串缓存和 DeepReadonly 快照缓存，大字符串（如技能提示）被驻留以减少内存压力。^[src/config/sessions/store-cache.ts:14-39] ^[src/config/sessions/store-cache.ts:111-125]

### Channel（通道）

Channel 是连接 Gateway 的消息传递表面。每个 Channel 负责维护与各自平台的实时连接、将入站事件标准化为统一的中间表示、管理多账户配置并执行安全策略。平台元数据被抽象到 `ChannelMeta` 中。^[src/infra/outbound/message-action-runner.ts:88-90]

Channel 遵循 Provider Monitor 模式，每个消息平台集成作为一个长期运行进程监控平台的消息流。例如，Telegram 使用 grammY，Discord 使用 discord.js，WhatsApp 使用 Baileys。^[package.json:89-122] 核心抽象是 `ChannelPlugin` 接口，细分为多个职责域：

- **ChannelMeta**：元数据包括通道 id 和标签
- **ChannelMessaging**：提供目标标准化（`normalizeTarget`）、聊天类型推断（`inferTargetChatType`）和会话路由（`resolveOutboundSessionRoute`）^[src/infra/outbound/message-action-runner.ts:88-90]
- **ChannelOutbound**：定义消息分块（`chunker`）、媒体发送（`sendMedia`）和负载投递（`sendPayload`），尊重平台限制 ^[src/plugin-sdk/reply-payload.ts:187-195]
- **ChannelActions**：将平台特定能力（如投票、消息置顶）暴露为 AI Agent 的工具 ^[src/agents/tools/message-tool.ts:11-21]

### Tool（工具）

Tool 使 Agent 能够超越文本生成，执行结构化类型化函数。工具通过插件系统注册 (`api.registerTool`)，并被 Agent 动态发现。^[src/agents/openclaw-tools.ts:37-66]

工具类别包括：
- **编码工具**：通过 `createOpenClawCodingTools` 创建，支持文件操作和 Shell 执行 ^[src/agents/embedded-agent-runner/run/attempt.ts:97-97]
- **浏览器自动化**：基于 CDP 的标签页控制和 Web 导航
- **内存工具**：混合搜索，从会话历史中召回信息 ^[docs/gateway/config-agents.md:192-194]
- **媒体工具**：图像理解、媒体生成（音乐/图像/视频）和媒体处理
- **消息工具**：跨通道发送消息，通过 `isMessagingToolSendAction` 检测 ^[src/auto-reply/reply/agent-runner-execution.ts:39-39]

工具生命周期包括四个阶段：Inventory Resolution（基于策略和配置文件确定可见工具集）、Schema Normalization（适配模型提供商要求，使用 TypeBox 进行严格类型处理）、Execution Handling（路由到内部处理器）、Result Processing（捕获输出并返回结构化数据）。^[src/agents/tools/music-generate-tool.ts:2-2] ^[src/agents/tool-schema-projection.ts:27-30]

### Plugin（插件）

Plugin 是 OpenClaw 的模块化扩展单元，基于 manifest 优先的架构。每个原生插件必须包含 `openclaw.plugin.json` 清单文件，声明 id、名称、描述、configSchema、支持的提供商列表、所属通道和激活触发器（`onStartup`、`onProviders`、`onChannels`）。^[src/plugins/manifest.ts:61-63] ^[src/plugins/loader.test.ts:177-179]

插件通过 `register(api)` 方法注册五种能力：
- `api.registerProvider()`：模型提供商（文本推理、语音 TTS/STT、图像生成）^[src/plugins/registry.ts:124-125]
- `api.registerChannel()`：消息通道（Telegram、Slack 等）^[src/plugins/loader-channel-setup.ts:79-81]
- `api.registerTool()`：Agent 工具 ^[src/plugins/registry.ts:151-155]
- `api.registerHook()`：生命周期事件钩子（如 `before_prompt_build`）^[src/plugins/registry.ts:32-33]
- `api.registerMemoryCapability()`：内存后端和补充 ^[src/plugins/loader.ts:169-174]

系统通过 Activation Planner 根据清单中的触发条件决定何时加载插件。插件发现按四级优先级扫描：显式配置路径 → Workspace `extensions/` → 全局安装 → 内置捆绑。^[src/plugins/loader.ts:46-57] ^[pnpm-workspace.yaml:5-5]

关键独占插槽（同一时间只有一个插件可激活）包括 `memory`（长期记忆和向量存储实现）和 `context-engine`（专用上下文管理逻辑）。^[src/plugins/loader.ts:50-53]

### Sub-Agent（子智能体）与 ACP（Agent Control Protocol）

Sub-Agent 是由父会话启动的隔离 Agent 会话。每个 Sub-Agent 在自己的 Session Key 空间中运行，通常通过 Key 中的 `subagent` 段标识。^[src/agents/subagent-registry.test.ts:189-192]

ACP 是一个专用于多会话编排的运行时框架，支持与外部 AI CLI 工具（Codex、Claude Code、Gemini CLI、Cursor）集成，扩展了 Sub-Agent 模型，支持会话恢复、流式输出路由和高级配置。^[src/acp/control-plane/manager.core.ts:1-28]

`SubagentRegistry` 跟踪活动运行，维护 `runId`、`childSessionKey` 和 `requesterSessionKey`（父会话）之间的映射。^[src/agents/subagent-registry.ts:52-78] 运行可以以 `SUBAGENT_ENDED_REASON_COMPLETE`、`ERROR` 或 `KILLED` 结束。^[src/agents/subagent-registry.ts:32-37] 清理时触发关联浏览器自动化实例的终止，并根据 `cleanup` 模式决定是否清除会话产物。^[src/agents/subagent-registry-lifecycle.ts:73-77] ^[src/agents/subagent-registry-run-manager.ts:45-47]

---

## 分层架构

OpenClaw 采用 **Hub-and-Spoke（中心辐射型）** 架构，中央 Gateway 协调 Agent 执行、消息通道和原生设备节点。^[docs/gateway/protocol.md:15-26]

### 协议 / 客户端层

最外层包含与 Gateway 通信的各类客户端：
- **CLI**：`openclaw` 命令行工具，用于直接调用、配置管理和守护进程控制 ^[src/cli/main.ts]
- **Control UI (WebChat)**：基于浏览器的管理仪表板和聊天界面，通过 Hono HTTP 服务器提供 ^[ui/src/ui/views/config-quick.ts]
- **iOS/macOS 原生应用**：通过共享的 OpenClawKit 与 Gateway 通信，使用共享的协议模型 ^[apps/shared/OpenClawKit]
- **Android 原生应用**：实现了 `NodeRuntime` 协调硬件处理器（CameraHandler、LocationHandler、SmsHandler）和 A2UI Canvas 渲染 ^[apps/android/app/src/main/java/ai/openclaw/app/NodeRuntime.kt:78-188]

通信协议采用 WebSocket 上的 JSON-RPC。当前使用 Protocol v4，包含标准化的 `RequestFrame`（含 id 追踪异步操作）、`ResponseFrame` 和 `EventFrame`。错误处理通过集中式 `ErrorCode` 枚举定义平台范围错误状态如 `AGENT_TIMEOUT` 和 `NOT_PAIRED`。^[apps/shared/OpenClawKit/Sources/OpenClawProtocol/GatewayModels.swift:5-256]

### Gateway 控制平面层

Gateway 内部包含多个子系统，共同实现了 `startGatewayServer()` 的完整服务能力：

- **WebSocket 处理器**：通过 `attachGatewayWsHandlers` 管理初始连接状态和 `ConnectParams`，处理握手和连接生命周期 ^[src/gateway/server.impl.ts:112-112]
- **方法分发**：通过 `handleGatewayRequest` 将 RPC 请求路由到注册的处理器，方法处理器由 `createGatewayMethodRegistry` 注册并可由插件扩展 ^[src/gateway/methods/registry.ts:65-69]
- **事件广播**：通过 `enqueueSystemEvent` 推送异步通知（如 `GATEWAY_EVENT_UPDATE_AVAILABLE`）到所有连接的客户端 ^[src/gateway/server-startup-post-attach.ts:20-22]
- **配置 I/O**：`getRuntimeConfig()` 加载并验证 Zod 校验的 JSON 配置，支持增量迁移和热重载 ^[src/config/io.ts]
- **会话管理器**：`resolveMainSessionKey()` 维护会话状态和持久化，协调并发访问 ^[src/gateway/server.impl.ts:22-22] ^[src/gateway/server-startup-post-attach.ts:36-36]
- **认证系统**：`resolveGatewayAuth()` 处理令牌/密码/无认证三种模式的作用域授权，ADMIN_SCOPE 限制高权限操作 ^[src/gateway/server.impl.ts:57-57]
- **模型认证预热**：`warmCurrentProviderAuthStateOffMainThread` 探测外部 CLI 和插件以缓存可用凭证，在热重载时清除并重新预热 ^[src/gateway/server-startup-post-attach.ts:188-191] ^[src/gateway/server-reload-handlers.ts:93-97]
- **Channel 监控**：`listLoadedChannelPlugins` 管理已加载通道插件的状态和生命周期 ^[src/gateway/server.impl.ts:85-85]
- **Cron 调度器**：`createLazyGatewayCronState` 延迟初始化定时任务服务 ^[src/cron/service.ts]

RPC 方法按操作域组织为三个作用域：`operator.read`（状态、健康检查、日志和列表方法）、`operator.write`（修改状态或发送消息的动作）、`operator.admin`（高权限配置变更，受 `ADMIN_SCOPE` 限制）。^[src/gateway/methods/core-descriptors.ts:20-50]

### Agent 运行时层

执行引擎将高层 Agent 逻辑与底层模型提供商和本地系统工具桥接，使用基于 Lane 的执行模型管理并发，`CommandLane` 用于优先处理不同类型的任务。^[src/auto-reply/reply/agent-runner-execution.ts:67-67]

运行时包含多个互联子系统：
- **执行流水线**：通过 `runAgentTurnWithFallback` 编排整个交互生命周期，包括多模型回退 ^[src/auto-reply/reply/agent-runner-execution.ts:71-71]
- **系统提示构建**：`buildReplyPromptEnvelope` 动态合并模块化部分并添加环境和 Agent 能力上下文 ^[src/auto-reply/reply/get-reply-run.ts:84-84]
- **入站元数据**：`buildInboundMetaSystemPrompt` 添加消息来源信息（发送者信息、通道类型）^[src/auto-reply/reply/get-reply-run.ts:78-78]
- **群组上下文**：`buildGroupChatContext` 和 `buildGroupIntro` 处理群聊的特定逻辑 ^[src/auto-reply/reply/get-reply-run.ts:72-73]
- **技能注入**：`resolveSkillsPromptForRun` 在运行时将技能提示注入系统提示 ^[src/agents/embedded-agent-runner/run/attempt.ts:61-61]
- **内存与压缩**：`runPreflightCompactionIfNeeded` 在上下文窗口溢出前触发压缩或截断 ^[src/auto-reply/reply/agent-runner-memory.ts:43-43]
- **模型选择与回退**：`resolveModelRefFromString` 选择模型，`resolveModelFallbackOptions` 管理回退链，`resolveRunAuthProfile` 处理认证配置文件映射 ^[src/auto-reply/reply/agent-runner-execution.ts:48-50] ^[src/auto-reply/reply/agent-runner-execution.ts:88-88]
- **状态管理**：`updateSessionStoreAfterAgentRun` 在执行后持久化模型使用、令牌消耗和会话元数据 ^[src/agents/command/session-store.ts:55-76]

### 通道 / 插件层

通道实现了 `ChannelPlugin` 接口，每个消息平台通过 `defineChannelPluginEntry` 或 `createChatChannelPlugin` 注册。^[src/plugin-sdk/entrypoints.ts:27] ^[docs/plugins/sdk-subpaths.md:27]

插件通过 `openclaw.plugin.json` 清单声明能力。清单驱动的发现机制使系统能够在不执行插件代码的情况下验证配置和确定能力。^[src/plugins/loader.ts:98-101] 插件发现按四级优先级扫描：显式配置路径 → Workspace 下的 `extensions/` 目录 → 全局安装 → 内置捆绑。^[pnpm-workspace.yaml:5-5] ^[src/plugins/loader.test.ts:203-204]

插件加载由 `loadOpenClawPlugins` 管理，根据 Activation Planner 评估的触发条件（`onStartup`、`onProviders`、`onChannels`）动态导入插件入口点并调用 `register(api)`。^[src/plugins/loader.ts:53-57] ^[src/plugins/loader.ts:28-30]

关键独占插槽通过 slot 声明防止冲突：
- **`memory`**：长期记忆和向量存储实现 ^[src/plugins/loader.ts:50-53]
- **`context-engine`**：专用上下文管理逻辑 ^[src/plugins/loader.test.ts:11-11]

### 基础设施层

底层支持包括：
- **会话存储**：双层存储（JSON 索引 + JSONL 转录），带多级缓存、写锁保护（`runWithOwnedSessionTranscriptWriteLock`）和磁盘预算强制（`enforceSessionDiskBudget`）^[src/config/sessions/store-cache.ts:14-39] ^[src/config/sessions/transcript.ts:25-25] ^[src/config/sessions/store.ts:17-17]
- **构建系统**：使用 `tsdown` 打包 Node.js 核心和共享包，自动检测并注入打包钩子 ^[tsdown.config.ts:3-12]
- **跨平台原生代码生成**：从 TypeScript 协议 schema 自动生成 Swift/Kotlin 模型，确保客户端与 Gateway 保持同步 ^[scripts/protocol-gen-swift.ts:1-9]
- **守护进程管理**：集成 macOS `launchd`（通过 `installLaunchAgent`、`repairLaunchAgentBootstrap`）、Linux `systemd` 和 Windows `schtasks`，支持受控重启和回退分离重启 ^[src/daemon/launchd.ts:26-26]
- **诊断与自动修复**：`openclaw doctor` 命令执行健康检查（配置验证、认证配置文件修复、插件验证）和自动修复（`--fix` 模式）^[src/flows/doctor-health-contributions.ts:48-53]

---

## 数据流

### 入站消息处理流

入站消息从外部平台到 Agent 响应的完整数据流方向是**单向的入站→处理→出站**管道：

```
外部平台（Telegram/Discord/WhatsApp）
  → Provider Monitor（平台特定监听器，如 dispatchTelegramMessage、processDiscordMessage）
    → Message Normalization（标准化为统一格式）
      → Deduplication（setGatewayDedupeEntry 防止重复处理）^[src/gateway/server-methods/chat.ts:153-153]
        → Policy Layer（DM 策略 pairing/allowlist/open/disabled，群组策略 allowlist/open/disabled，提及门控 requireMention）^[docs/gateway/config-channels.md:25-30]
          → Session Key Resolution（parseAgentSessionKey 解析路由信息）^[src/routing/session-key.js:90-90]
            → Agent Runtime（runEmbeddedPiAgent 执行，runAgentTurnWithFallback 编排）^[src/auto-reply/reply/agent-runner-execution.ts:71-71]
              → Reply Delivery（Build reply payloads → Block reply pipeline → Outbound adapter → Platform send）
```

^[extensions/telegram/src/bot-message-dispatch.ts:170-171], ^[extensions/discord/src/monitor/message-handler.process.ts:154-157], ^[extensions/telegram/src/sequential-key.ts:100-155]

### 出站投递流

Agent 生成响应后的出站投递流水线采用**管道模式**，从意图到平台特定实现层层解析：

1. **Action Initiation**：Agent 或命令通过 `runInboundMessageDispatch` 调用出站消息动作 ^[src/gateway/server-methods/chat.ts:42-42]
2. **Target Resolution**：`resolveOutboundChannelPlugin` 将人类友好标识符转换为具体的通道-账户-消息目标 ^[src/infra/outbound/message-action-runner.ts:51-51] ^[src/infra/outbound/message-action-runner.ts:88-90]
3. **Session Routing**：`parseAgentSessionKey` 计算或确认适当的 Session Key 维持对话连续性 ^[src/routing/session-key.ts:25-30]
4. **Payload Normalization**：`normalizeOutboundReplyPayload` 处理文本分块和媒体附件规则 ^[src/plugin-sdk/reply-payload.ts:84-88]
5. **Chunking**：`sendPayloadWithChunkedTextAndMedia` 拆分长消息同时保留格式 ^[src/plugin-sdk/reply-payload.ts:187-195]
6. **Action Execution**：`executeSendAction` 将负载交给通道特定的出站适配器完成最终投递 ^[src/infra/outbound/outbound-send-service.ts:11-11]

出站投递支持多种流式传输模式：`partial`（流式文本逐字传输）、`block`（发送完整段落）、`progress`（显示工具执行状态）。^[src/plugin-sdk/channel-streaming.test.ts:36-49]

### Agent 执行流水线

执行流水线采用**分层责任链模式**，将入站消息转换为模型响应：

| 层级 | 名称 | 入口函数 | 职责 |
|---|---|---|---|
| L1 | Reply Orchestration | `runAgentTurnWithFallback` | 顶层入口，处理完整的多模型回退策略 ^[src/auto-reply/reply/agent-runner-execution.ts:71-71] |
| L2 | Turn Management | `runWithModelFallback` | 管理候选模型序列（如果主模型失败）^[src/auto-reply/reply/agent-runner-execution.ts:44-44] |
| L3 | Execution Core | `runEmbeddedAgent` | 与底层模型提供商的单次尝试直接接口 ^[src/auto-reply/reply/agent-runner-execution.ts:40-40] |
| L4 | Followup Handling | `createFollowupRunner` | 编排二次运行（承诺、提醒、子 Agent）^[src/auto-reply/reply/followup-runner.ts:29-30] |

错误分类系统 (`classifyProviderRequestError`) 将原始提供商错误映射到内部恢复策略：^[src/auto-reply/reply/agent-runner-execution.ts:107-109]
- **Context Overflow** → `isContextOverflowError` / `isLikelyContextOverflowError` → 触发压缩 ^[src/auto-reply/reply/agent-runner-execution.ts:31-33]
- **Billing** → `isBillingErrorMessage` → 报告计费问题 ^[src/auto-reply/reply/agent-runner-execution.ts:32-32]
- **Rate Limit** → `isRateLimitErrorMessage` → 通过 `resolveRunAuthProfile` 轮换 API 密钥 ^[src/auto-reply/reply/agent-runner-execution.ts:35-35] ^[src/auto-reply/reply/agent-runner-execution.ts:88-88]
- **Overloaded** → `isOverloadedErrorMessage` → 触发模型回退 ^[src/auto-reply/reply/agent-runner-execution.ts:34-34]
- **Live Model Switch** → `LiveSessionModelSwitchError` → 最多 `MAX_LIVE_SWITCH_RETRIES` (2) 次重试 ^[src/auto-reply/reply/agent-runner-execution.ts:43-43] ^[src/auto-reply/reply/agent-runner-execution.ts:122-122]

### 子 Agent 编排流

子 Agent 编排采用**事件驱动的异步生成-完成模式**：

```
Parent Session: sessions-send-tool → startAgentRun
  → SubagentRegistry: 注册 child run（runId → childSessionKey → requesterSessionKey）^[src/agents/subagent-registry.ts:52-78]
    → persistSubagentRunsToDisk: 将内存注册表刷入持久存储 ^[src/agents/subagent-registry.ts:73-74]
      → AcpSessionManager（如果为 ACP 会话）: initializeSession → runTurn → 完成 ^[src/acp/control-plane/manager.core.ts:145-168]
        → Delivery Dispatch: 通过 agent.wait RPC 轮询完成，withSubagentOutcomeTiming 跟踪指标 ^[src/agents/subagent-registry-run-manager.ts:11-13]
          → Idempotency: 幂等键防止重复完成通知 ^[src/agents/subagent-registry-lifecycle.ts:21-24]
            → Announcement: deliverSubagentAnnouncement 将结果投递给父 Agent ^[src/agents/subagent-announce-delivery.ts:204-213]
```

### 原生节点调用流

当 Agent 需要访问设备硬件时，请求通过 Gateway 的 RPC 层流向原生客户端：

```
Agent Runtime (Node.js)
  → GatewayServer: 请求工具调用（如 camera、location、sms）
    → GatewayModels: 序列化 RequestFrame（含 id 追踪异步操作）^[apps/shared/OpenClawKit/Sources/OpenClawProtocol/GatewayModels.swift:153-155]
      → NodeRuntime (Android/iOS): WebSocket 传输
        → CameraHandler.takePhoto() / LocationHandler / SmsHandler ^[apps/android/app/src/main/java/ai/openclaw/app/NodeRuntime.kt:110-180]
          → ResponseFrame 序列化返回 ^[apps/shared/OpenClawKit/Sources/OpenClawProtocol/GatewayModels.swift:179]
```

所有平台使用相同的 `GatewayModels` schema 确保二进制兼容的 JSON 序列化。请求通过 `RequestFrame` 中的 `id` 字段追踪，实现非阻塞硬件操作。^[apps/shared/OpenClawKit/Sources/OpenClawProtocol/GatewayModels.swift:1-10]

---

## 关注点分离

### 配置与运行时的分离

系统配置通过 Zod 校验的 JSON 文件加载（`openclaw.json`、`models.json`、`auth-profiles.json`），并与运行时执行严格分离。配置支持增量迁移——配置格式随时间演进而无需破坏旧格式。Gateway 在配置变更时通过 `getRuntimeConfig()` 自动热重载，并清除缓存和重新预热模型认证状态。^[src/gateway/server-reload-handlers.ts:93-97]

### Agent 隔离

每个 Agent 是独立的逻辑实体，拥有独立的文件系统资源，确保工具、内存和凭证不泄露：

| 资源 | 路径模式 | 用途 |
|---|---|---|
| Workspace | `~/.openclaw/workspace-<agentId>` | 文件系统上下文，供工具和本地技能使用 ^[src/gateway/server-methods/agent.test.ts:122-133] |
| Agent 目录 | `~/.openclaw/agents/<agentId>/` | Agent 专属配置文件（`auth-profiles.json`、`models.json`）^[src/gateway/server-methods/agent.ts:120-125] |
| Session Store | `~/.openclaw/agents/<agentId>/sessions/store.json` | 该 Agent 所有对话的元数据索引 ^[src/gateway/server-methods/sessions.ts:50-58] |
| Session Transcripts | `~/.openclaw/agents/<agentId>/sessions/<uuid>.jsonl` | 附加型对话历史（JSONL）^[src/gateway/server-methods/sessions.ts:54-55] |

Agent ID 通过 `resolveAgentIdFromSessionKey` 从 Session Key 中提取，工作区路径通过 `resolveAgentWorkspaceDir` 计算。认证配置文件按 Agent 作用域管理——即使两个 Agent 使用相同的模型提供商，也可以使用存储在各自 `auth-profiles.json` 中的不同 API 密钥。^[src/gateway/server-methods/agent.ts:39-39]

### 消息标准化与通道抽象

每个消息平台的具体 API 差异被封装在 `ChannelPlugin` 实现中，遵循统一的接口契约。入站消息被标准化为通用格式供 Agent 运行时处理——平台特定标识符（电话号码、用户 ID、频道 ID）通过 `resolveChannelTarget` 标准化为内部格式。^[src/infra/outbound/message-action-runner.ts:90-90]

出站消息通过 `message` 工具抽象平台特定 API。Agent 通过 `listChannelSupportedActions` 发现可在特定平台上执行的操作，并可通过 `broadcast` 操作在多个通道上同时广播消息。^[src/agents/tools/message-tool.ts:51-51] ^[src/infra/outbound/message-action-runner.ts:148-162]

### 工具策略管道

工具可见性和执行受多层策略管道控制，确保安全和上下文的适当性：

1. **Effective Policy Resolution**：`resolveEffectiveToolPolicy` 基于全局、Agent 和配置文件设置计算最终允许的工具集 ^[src/agents/embedded-agent-runner/run/attempt.ts:102-102] ^[src/flows/doctor-core-checks.runtime.ts:14-14]
2. **Explicit Allowlist**：`collectExplicitAllowlist` 提取被授予执行权限的特定工具名称 ^[src/flows/doctor-core-checks.runtime.ts:26-26]
3. **Schema Normalization**：工具定义被适配到特定模型提供商的要求，使用 TypeBox 进行严格的 JSON Schema 类型处理 ^[src/agents/tool-schema-projection.ts:27-30]
4. **Inventory Assembly**：`createOpenClawTools` 基于 Agent 配置、活动插件和可用技能构建工具的完整清单 ^[src/agents/openclaw-tools.ts:80-143]

### 插件边界强制

插件架构包含严格的边界强制机制，维护主机完整性和安全性：
- **安全扫描**：安装时运行静态分析（`scanBundleInstallSource`、`scanPackageInstallSource`）检测危险操作 ^[src/plugins/install.test.ts:38-43]
- **完整性校验**：NPM 插件完整性哈希与注册表元数据匹配 ^[src/plugins/install.ts:13-14]
- **受控 NPM 根**：插件安装在管理的根目录下（`_openclaw-managed-npm`），与 Gateway 主机建立对等依赖链接 ^[src/plugins/install.ts:27-27]
- **版本兼容性**：检查 `minHostVersion` 和 `pluginApi` 范围，防止不兼容的插件加载 ^[src/plugins/install.ts:112-116] ^[src/plugins/install.ts:150-165]
- **SDK 别名**：加载器通过虚拟别名系统确保插件导入正确的 SDK 版本，根据环境映射到 `src/` 或 `dist/` ^[src/plugins/sdk-alias.ts:12-21] ^[src/plugins/sdk-alias.ts:150-165]
- **Slot 隔离**：Slot 声明防止多个插件占据独占角色（如内存后端），通过 `resolveMemorySlotDecision` 解决冲突 ^[src/plugins/loader.ts:163-163] ^[src/plugins/loader.ts:50-50]
- **能力过滤**：只有 `InstalledPluginIndex` 中已启用的插件才能在运行时参与。插件在 `openclaw.plugin.json` 中声明能力，使系统能够在执行代码前进行推理。^[src/plugins/loader.ts:66-67] ^[src/plugins/loader.ts:98-101]

### 会话维护与可靠性

会话层通过以下机制保证数据一致性和系统健康：
- **写锁保护**：所有转录写入由 `acquireSessionWriteLock` 保护，防止并发 Agent 轮次导致损坏 ^[src/agents/command/attempt-execution.ts:41-41]
- **磁盘预算**：`enforceSessionDiskBudget` 执行扫描确保会话文件不超过分配空间 ^[src/config/sessions/store.ts:17-17]
- **过期条目修剪**：`pruneStaleEntries` 移除超过阈值未更新的会话元数据 ^[src/config/sessions/store.ts:53-53]
- **缓存失效**：`invalidateSessionStoreCache` 确保多进程操作期间内存会话元数据与磁盘保持同步 ^[src/config/sessions/store.ts:33-33]
- **故障分类**：如果会话损坏或执行失败，系统使用 `FailoverError` 分类原因并决定是否清除重用的 CLI 会话 ^[src/agents/command/attempt-execution.ts:59-64]

### 信任边界

OpenClaw 采用**个人助手安全模型**，每个 Gateway 实例有单一可信操作员边界。它不是为不可信或对抗性用户共享一个 Gateway 配置或 Agent 运行时而设计的多租户对抗性隔离系统。

| 边界 | 信任级别 | 说明 |
|---|---|---|
| Gateway 配置和状态 | **可信** | 任何能修改 `openclaw.json` 或 Gateway 状态文件的人有效控制整个系统和所有 Agent |
| Gateway 认证调用者 | **可信** | Gateway 认证授予操作员级权限；OpenClaw 不提供单实例内的每用户隔离 |
| Session Key | **仅路由上下文** | Session Key 路由消息和上下文，但不独立授予授权 |
| 通道消息 | **不可信输入** | 来自第三方的消息可能包含代码注入或社会工程负载，在 Gateway 内被视为不可信 |
| 插件和扩展 | **可信代码** | 插件在 Gateway 进程内以完整操作员权限运行 |
| 模型提供商 | **可信外部服务** | 网络请求受 SSRF 守卫和网络控制的约束 |

所有出站网络请求经过 SSRF 防护系统处理：`readBoundedGitHubApiJson` 包装 API 请求并施加安全策略（大小限制、超时守卫）、私有/本地网络的请求在 Agent 执行期间被限制，所有网络响应通过有界读取器消费以防止内存 DoS 攻击。^[scripts/github/real-behavior-proof-policy.mjs:122-133] ^[scripts/check-memory-fd-repro.mjs:32-44]

---

## 关联

### 关键子系统关联

OpenClaw 的架构可以理解为一组相互关联的子系统，它们通过明确定义的接口协作：

- **Gateway** 是所有通信的中央枢纽。它通过 WebSocket 协议 (v4) 与所有客户端（CLI、Control UI、原生应用）通信，并通过 Provider Monitor 模式连接外部消息平台。Gateway 作为唯一真实来源维护三种核心状态：配置状态、会话状态和连接状态。^[src/gateway/server.impl.ts:112-112]

- **Multi-Agent Router** 将通道消息映射到特定的 Agent 实例，使用 Session Key 作为路由标识符。Session Key 格式 `agent:<agentId>:<channel>:<kind>:<id>` 编码了从通道到 Agent 的完整路由路径，`resolveAgentIdFromSessionKey` 提取目标 Agent。^[src/routing/session-key.ts:30-40] 系统支持 per-session 模型覆盖（`resolveSessionModelRef`）以在运行时切换模型。^[src/gateway/server-methods/sessions.ts:113-113]

- **Plugin System** 是扩展性的核心机制，通过 manifest 优先的发现机制（`openclaw.plugin.json`）在不执行插件代码的情况下验证配置和确定能力。提供五种注册接口（Provider、Channel、Tool、Hook、Memory），通过 Activation Planner 根据清单中的 `onStartup`、`onProviders`、`onChannels` 触发条件按需加载。^[src/plugins/loader.ts:98-101] ^[src/plugins/loader.ts:46-51]

- **ACP (Agent Control Protocol)** 提供了多会话编排框架，`AcpSessionManager` 作为 ACP 的中央控制平面，处理会话初始化、状态转换、持久化和可观测性（活动轮次快照、队列深度、平均延迟）。将 Sub-Agent 与外部 AI CLI 工具（Codex、Claude Code、Gemini CLI、Cursor）集成，支持会话恢复和流式输出路由。^[src/acp/control-plane/manager.core.ts:62-260]

- **Execution Pipeline** 连接 Agent Runtime 和模型提供商，通过 `runAgentTurnWithFallback` 实现四层回退（L1 编排 → L2 轮次管理 → L3 核心执行 → L4 后续处理）。错误分类系统将原始提供商错误映射到恢复策略，实现自动化的上下文压缩、认证轮换和模型回退。^[src/auto-reply/reply/agent-runner-execution.ts:40-122]

- **Context Compaction** 与 Execution Pipeline 紧密配合，在每次运行前通过 `runPreflightCompactionIfNeeded` 检查上下文窗口使用量，比较估计会话令牌数 (`resolveContextTokensForModel`) 与模型限制，并在必要时触发压缩或截断。压缩后读取 `readPostCompactionContext` 确保下一轮使用新鲜的压缩状态。^[src/auto-reply/reply/agent-runner-execution.ts:26-26] ^[src/auto-reply/reply/agent-runner.ts:78-96]

- **Service Lifecycle** 管理 Gateway 进程的完整生命周期，包括启动序列（CLI 路径确保 → 启动配置快照 → 追踪初始化 → 早期运行时 → 模型目录 → 插件引导 → 侧车服务）、信号处理（SIGTERM/SIGINT/SIGUSR1）、优雅关闭（`waitForActiveTasks`、`waitForActiveEmbeddedRuns` 排空活跃任务）、重启恢复（`resumeGatewayRestartTraceFromHandoff` 跨进程边界保持诊断连续性）和自动修复（`openclaw doctor --fix` 执行配置验证、认证修复和插件重装）。^[src/gateway/server.impl.ts:34-119] ^[src/cli/gateway-cli/run-loop.ts:19-21] ^[src/gateway/server.impl.ts:81-81]

- **Message Delivery Pipeline** 将 Agent 意图（出站消息动作）与平台特定实现解耦。从 `runMessageAction` 入口，经过 `normalizeMessageActionInput` 参数清理和媒体引用解析，到 `resolveOutboundChannelPlugin` 通道识别，最终由 `executeSendAction` 完成平台特定投递。整个管道支持进度草稿（`createStatusReactionController`）和实时预览（`createDiscordDraftStream`）以改善长时间运行任务的用户体验。^[src/infra/outbound/message-action-runner.ts:51-111] ^[extensions/discord/src/monitor/message-handler.draft-preview.ts:58-60]

### 仓库结构

OpenClaw 组织为 pnpm workspace 管理的 monorepo，各部分职责明确分离：
- `src/`：核心 TypeScript Gateway 运行时，包含 Agent 逻辑、基础设施和会话管理
- `apps/`：原生客户端应用 (iOS/macOS/Android)，集成 Swabble 唤醒词守护进程和 A2UI 标准
- `extensions/*`：40+ 独立插件包，每个拥有自己的 `package.json`，实现通道适配器（WhatsApp、Discord、Slack）和模型提供商
- `packages/*`：共享 TypeScript 包——`@openclaw/sdk`（Gateway 编程接口）、`@openclaw/fs-safe`（安全文件操作）、`@openclaw/proxyline`（网络代理）
- `skills/`：内置 Skill 库（Markdown 格式的 `SKILL.md` 文档集合）
- `qa/`：质量保证场景包和对话测试套件
- `.pi/`：开发者工具辅助工具集

^[pnpm-workspace.yaml:1-6], ^[package.json:1-146], ^[pnpm-lock.yaml:83-88]
