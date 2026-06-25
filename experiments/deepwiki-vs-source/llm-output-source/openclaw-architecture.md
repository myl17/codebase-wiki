# Architecture 维度：openclaw

openclaw 是一个自托管的个人 AI 助手网关，采用分层插件架构，TypeScript ESM monorepo。Gateway 是中央控制面，插件系统通过 Plugin SDK 公共契约与核心交互。

## 核心抽象

### Gateway（网关控制面）

Gateway 是 openclaw 的中央控制面，是一个长期运行的 Node.js HTTP+WebSocket 服务器，负责协调所有通道、AI 代理和操作者客户端。Gateway 通过文件锁防止多实例并发启动，绑定到配置的 host:port 后持续运行 ^[src/gateway/server/http-listen.ts:18-60]。它对外暴露统一的 WebSocket+HTTP 协议供 CLI、WebChat、移动应用等操作者客户端连接，并通过服务端广播将状态变更推送到所有已连接客户端 ^[src/gateway/protocol/schema.ts:1-21]。

Gateway 在启动时执行 BOOT.md 工作区引导脚本，用于通道连通性检查、健康验证等一次性启动任务 ^[src/gateway/boot.ts:38-55]。Gateway 的生命周期还包括 exec approval、plugin approval、secrets 等辅助处理管线 ^[src/gateway/server-aux-handlers.ts:28-60]。

### Channel（通道）

Channel 是对消息平台集成的核心抽象，被定义为一个 `ChannelPlugin<ResolvedAccount, Probe, Audit>` 对象。每个通道包含一组类型化的适配器契约，覆盖通道全生命周期的所有关注点 ^[src/channels/plugins/types.plugin.ts:53-94]。

适配器体系包括：
- **消息收发**（`ChannelMessagingAdapter`）：处理消息的接收、格式化和规范化 ^[src/channels/plugins/types.core.ts:1-80]
- **安全策略**（`ChannelSecurityAdapter`）：控制 DM 安全策略、允许列表匹配 ^[src/channels/plugins/types.adapters.ts:36-38]
- **出站投递**（`ChannelOutboundAdapter`）：将 AI 回复 Payload 转换为通道原生消息格式并投递 ^[src/plugin-sdk/channel-contract.ts:28-37]
- **配置管理**（`ChannelConfigAdapter`）：处理通道账户配置的解析、验证与写入 ^[src/channels/plugins/types.adapters.ts:76-100]
- **配对绑定**（`ChannelPairingAdapter`）：管理通道与 Agent 的绑定关系
- **状态探测**（`ChannelStatusAdapter`）：通道健康检查和状态诊断
- **审批流**（`ChannelApprovalCapability`）：通道级别的执行审批发起能力
- **生命周期**（`ChannelLifecycleAdapter`）：通道启动/停止/重启钩子
- **分组管理**（`ChannelGroupAdapter`）：群聊/Guild 上下文的成员和角色解析

### Plugin（插件）

Plugin 是 openclaw 的扩展机制，支持通道、模型供应商、工具、命令、钩子处理器、服务等多种扩展类型。插件系统由 `src/plugins/` 管理，负责插件发现、清单验证、加载、注册表组装和契约执行 ^[src/plugins/AGENTS.md:1-62]。

核心类型 `OpenClawPluginDefinition` 定义了插件的完整契约，包括 `id`、`name`、`register(api: OpenClawPluginApi)` 注册函数，以及可选的 `channels`、`providers`、`tools`、`commands`、`hooks`、`services` 等能力声明 ^[src/plugin-sdk/plugin-entry.ts:1-73]。

插件边界规则严格：核心必须保持扩展无关，插件只能通过 `openclaw/plugin-sdk/*` 导入核心能力，不能导入 `src/**` 内部模块。核心代码和测试也不应深度导入内置插件的内部模块（如插件的 `src/**` 文件）^[CLAUDE.md:41-48]。

### Plugin SDK（插件 SDK 公共契约）

`src/plugin-sdk/` 是插件与核心之间的唯一公共 API 边界。它在 `package.json` 中定义了 70+ 个细粒度的导出子路径（如 `openclaw/plugin-sdk/core`、`openclaw/plugin-sdk/channel-contract`、`openclaw/plugin-sdk/provider-entry`），每个子路径封装一组紧密相关的类型和辅助函数 ^[src/plugin-sdk/AGENTS.md:1-81]。

SDK 设计原则：优先使用窄而专注的子路径，避免宽泛的"便利重导出"；公共入口点在模块加载时保持轻量（避免静态导入仅在异步路径上需要的重量级模块）；使用 `*.runtime` 后缀的专用子路径承载仅在运行时需要的重量级表面 ^[src/plugin-sdk/AGENTS.md:25-33]。

### Agent（AI 代理）

Agent 代表一个 AI 代理实例，绑定到特定的模型供应商、会话存储路径和通道。每个 Agent 由唯一 `agentId` 标识，通过 `resolveAgentRoute()` 从入站消息的 channel + account + peer 上下文中解析目标 Agent 和 sessionKey ^[src/routing/resolve-route.ts:27-61]。

Agent 的行为由以下要素共同决定：System Prompt（核心 + Provider 贡献）、可用工具集（核心工具 + 插件工具）、会话历史（Pi 编码代理格式）、模型选择（通过 `resolveAgentConfig` 解析）和超时/并发策略。

路由支持多层匹配优先级：`binding.peer` > `binding.peer.parent` > `binding.peer.wildcard` > `binding.guild+roles` > `binding.guild` > `binding.team` > `binding.account` > `binding.channel` > `default` ^[src/routing/resolve-route.ts:51-61]。

### AgentHarness（代理执行器）

AgentHarness 是对 AI 推理执行的抽象接口。每个 Harness 必须实现 `supports(ctx)`（判断是否支持某 provider/model 组合，返回支持优先级）、`runAttempt(params)`（执行一次完整的推理尝试），以及可选的 `compact`（会话压缩）、`reset`（会话重置）、`dispose`（资源释放）方法 ^[src/agents/harness/types.ts:30-39]。

Harness 由插件通过 `api.registerAgentHarness()` 注册，核心通过 `selectAgentHarness()` 按优先级排序选择最合适的实现。内置的 Pi 嵌入式运行时是默认的 Harness 实现 ^[src/agents/harness/registry.ts:1-end]。

### Provider（模型供应商）

Provider 是对 LLM 供应商（Anthropic、OpenAI、Google 等）的抽象，通过 `ProviderPlugin` hook 体系定义。每个 Provider 提供一组类型化的 hook 函数覆盖推理链路的各个阶段 ^[src/plugin-sdk/plugin-entry.ts:1-73]：

- **认证**：`resolveAuth`、`prepareRuntimeAuth`、`resolveUsageAuth`
- **模型目录**：`augmentModelCatalog`、`resolveDynamicModel`
- **工具 Schema 标准化**：`normalizeToolSchemas`
- **流包装**：`wrapStream`、`resolveTransportTurnState`
- **重放策略**：`getReplayPolicy`、`sanitizeReplayHistory`、`validateReplayTurns`
- **思考策略**：`getDefaultThinkingPolicy`、`resolveReasoningOutputMode`

核心拥有通用推理循环；Provider 通过注册和类型化 hook 拥有供应商特定行为。禁止从无关核心代码中临时读取 `plugins.entries.<id>.config` ^[CLAUDE.md:54-58]。

### Config（配置系统）

`OpenClawConfig` 是全局配置的顶层类型，聚合了所有子系统的配置节：`auth`、`acp`、`channels`、`agents`、`models`、`tools`、`hooks`、`gateway`、`session`、`logging`、`diagnostics`、`plugins`、`cron`、`secrets`、`skills`、`memory`、`browser`、`commands`、`messages` 等 ^[src/config/types.openclaw.ts:32-80]。配置通过 `loadConfig()` 从 YAML/TOML 文件加载，支持环境变量覆盖和 CLI 设置。

### Session（会话）

会话基于 Pi 编码代理框架的 `SessionManager`，以 JSONL 文件持久化存储。每个会话由 `sessionKey` 唯一标识，其格式为 `channel:account:agent:peer`，通过 `routing/session-key.ts` 实现 sessionKey 的构建和解析 ^[src/routing/session-key.ts:1-19]。会话存储路径由 `resolveStorePath()` 解析，支持按 agentId 隔离 ^[src/gateway/boot.ts:82]。

### Gateway Protocol（网关协议）

网关协议定义操作者客户端与 Gateway 之间的类型化通信契约。协议通过 `src/gateway/protocol/schema.ts` 聚合所有子 Schema：`agent`、`channels`、`config`、`cron`、`sessions`、`push`、`secrets`、`exec-approvals`、`wizard`、`nodes`、`plugin-approvals`、`commands` 等 ^[src/gateway/protocol/schema.ts:1-21]。协议变更需遵循加法演进原则，不兼容变更需显式版本管理和客户端跟进 ^[src/gateway/protocol/AGENTS.md:17-28]。

---

## 分层架构

openclaw 采用清晰的分层架构，从上到下依次为：

### 1. 入口层

负责 Node.js 版本检查（最低 v22.12）、编译缓存启用、gaxios fetch compat 安装、进程标题设置、环境标准化和 CLI 重生逻辑。入口文件 `openclaw.mjs` 在加载编译后的 `dist/entry.js` 之前完成最小化引导 ^[openclaw.mjs:1-180]。`entry.ts` 处理 CLI 参数解析、Profile 环境注入、`--container` 目标解析、版本快速路径和主 CLI 启动 ^[src/entry.ts:1-213]。

### 2. CLI 层

基于 Commander.js 的命令行界面。CLI 通过 `CommandDescriptor` 系统实现命令的可插拔注册：核心命令来自 `getCoreCliCommandDescriptors()`，插件命令来自 `getPluginCliCommandDescriptors()`，子 CLI 来自 `getSubCliEntries()` ^[src/cli/program/root-help.ts:19-40]。命令注册表支持命令组和延迟加载 ^[src/cli/program/command-registry.ts:1-end]。

### 3. Gateway 服务层

HTTP+WebSocket 服务器，位于 `src/gateway/server/`。核心组件包括 HTTP 监听（绑定端口并处理 EADDRINUSE 重试）^[src/gateway/server/http-listen.ts:1-60]、WebSocket 连接管理（握手认证、消息路由、未授权洪泛防护）和插件 HTTP 路由（插件注册的自定义 HTTP 端点如 webhook 接收）^[src/gateway/server/plugins-http/route-match.ts:1-end]。

### 4. 协议层

类型化的 Gateway 通信契约定义，位于 `src/gateway/protocol/`。Schema 定义与运行时验证器、文档、测试和生成的客户端工件同步 ^[src/gateway/protocol/AGENTS.md:1-29]。

### 5. 服务方法层

协议中各 RPC 方法的实现，位于 `src/gateway/server-methods/`。包括代理管理（`agent.ts`）、聊天消息处理（`chat.ts`）、配置读写（`config.ts`）、通道状态（`channels.ts`）、定时任务（`cron.ts`）、客户端连接（`connect.ts`）、exec 审批（`exec-approval.ts`）、设备管理（`devices.ts`）等 ^[src/gateway/server-methods/chat.ts:1-60]。

### 6. 推理调度层

位于 `src/auto-reply/`，实现从入站消息到 AI 回复的完整调度流程。`dispatch.ts` 是入口调度器，接收 `MsgContext` 和配置，委托给 `dispatchReplyFromConfig` 执行完整管线 ^[src/auto-reply/dispatch.ts:20-39]。`reply/dispatch-from-config.ts` 包含核心调度逻辑：解析 Agent 配置、加载会话、触发内部钩子和插件钩子（`inboundClaim`、`messageReceived`）、调用 Agent Harness、处理回复 ^[src/auto-reply/reply/dispatch-from-config.ts:1-60]。`reply/reply-dispatcher.ts` 管理打字指示器、部分回复和流式输出。

### 7. 代理层

位于 `src/agents/`，管理 AI 代理的完整生命周期：Agent 作用域解析（`agent-scope.ts`）、命令执行（`agent-command.ts`）、模型选择（`model-selection.ts`）、Harness 注册表和选择（`harness/`）、Pi 嵌入式运行时（`pi-embedded-runner/`）、认证配置文件管理（`auth-profiles/`）、工具注册和组装（`tools/`）、工具策略管线（`tool-policy-pipeline.ts`）和超时管理。

### 8. 通道层

位于 `src/channels/`。包含 `ChannelPlugin` 类型定义（`plugins/types.plugin.ts`）、核心类型（`plugins/types.core.ts`）、适配器接口（`plugins/types.adapters.ts`）和内置通道实现（`src/telegram/`、`src/discord/`、`src/slack/`、`src/signal/`、`src/imessage/`、`src/web/`）。通道层是核心实现，插件通道应通过 Plugin SDK 契约接入而非直接导入通道内部模块 ^[src/channels/AGENTS.md:1-44]。

### 9. 插件管理层

位于 `src/plugins/`，管理插件生态系统：加载器（`loader.ts`）、类型定义（`types.ts`）、注册表（`contracts/registry.ts`）、内置源（`bundled-sources.ts`）和契约验证。插件发现优先于清单元数据，配置验证和设置在插件运行时执行之前就应能工作 ^[src/plugins/AGENTS.md:19-24]。

### 10. Plugin SDK 层

位于 `src/plugin-sdk/`，插件与核心之间的唯一公共 API 表面。包含 70+ 个细粒度导出子路径，覆盖通道契约、Provider 类型、运行时辅助、回复管线、安全策略、媒体处理等 ^[src/plugin-sdk/AGENTS.md:1-81]。

### 11. 基础设施层

位于 `src/infra/`，提供跨切面工具：环境变量规范化、错误格式化、Gateway 文件锁、进程管理、审批处理、Secret 引用解析、诊断事件、代理事件上下文等。

### 12. 扩展层

位于 `extensions/`，以 workspace 包形式存在的 100+ 内置扩展：通道（Matrix、Zalo、BlueBubbles 等）、模型供应商（Anthropic、OpenAI、Amazon Bedrock、Google Vertex 等）、工具（Brave Search、Browser 等）、语音、媒体理解、可观测性等 ^[CLAUDE.md:13-21]。

---

## 数据流

### 入站消息处理流（事件驱动、单向管道）

```
外部消息源 (Webhook / Polling / WebSocket)
    │
    ▼
通道适配器 (ChannelMessagingAdapter) ── 原始消息 → 规范化 MsgContext
    │
    ▼
路由解析 (resolveAgentRoute) ── channel+account+peer → agentId+sessionKey
    │
    ▼
会话加载 (loadSessionStore) ── sessionKey → SessionEntry (Pi 会话)
    │
    ▼
钩子触发 ── 内部钩子 (messageReceived) + 插件钩子 (inboundClaim)
    │
    ▼
Agent 配置解析 (resolveAgentConfig) ── 模型选择、System Prompt 组装、工具注册
    │
    ▼
工具策略管线 (Tool Policy Pipeline) ── 5 层过滤: profile → provider → global → agent → group
    │
    ▼
AgentHarness.runAttempt() ── Pi 嵌入式运行时执行
    │
    ▼
Provider 管线 ── auth → normalizeToolSchemas → wrapStream → replay → LLM API
    │
    ▼
LLM 流式响应 ── streaming tokens
    │
    ▼
Reply Pipeline (ReplyDispatcher) ── chunking、media processing、formatting
    │
    ▼
出站适配器 (ChannelOutboundAdapter) ── ReplyPayload → 通道原生消息格式
    │
    ▼
外部消息平台 ── 消息投递至用户
```

入站调度的入口是 `dispatchInboundMessage()` ^[src/auto-reply/dispatch.ts:20-39]，核心调度在 `dispatchReplyFromConfig()` ^[src/auto-reply/reply/dispatch-from-config.ts:1-60]。

### Gateway 客户端通信流

```
操作者客户端 (CLI / WebChat / Mobile App)
    │
    ▼
WebSocket 连接 (ws://gateway:port) ── handshake + client auth + capability negotiation
    │
    ▼
协议方法路由 ── 类型化 RPC: chat.send、agent.run、config.get、channels.status 等
    │
    ▼
Gateway Server Methods ── 处理 RPC 调用，操作内部状态
    │
    ▼
Server Broadcast ── 状态变更推送至所有已连接客户端
```

### 插件数据流

插件通过以下阶段参与核心流程：

1. **注册阶段**：插件 `register(api)` 通过 `OpenClawPluginApi` 注册 channels、providers、tools、commands、hooks、services
2. **配置阶段**：核心加载配置后调用 Provider 的 `normalizeConfig`、`resolveAuth`、`augmentModelCatalog` 等 hook
3. **推理阶段**：Provider hook 在推理链路各节点介入（auth、tools、stream、replay、thinking）
4. **回复阶段**：Channel reply pipeline 和 hook 的 `replyDispatch` 事件处理回复投递前后的逻辑

插件不能直接导入核心内部模块（`src/**`），只能通过 `openclaw/plugin-sdk/*` 与核心交互 ^[CLAUDE.md:43]。

---

## 关注点分离

### 核心-插件边界

openclaw 最重要的架构边界是核心与插件之间的严格分离：

- **核心**（`src/`）保持扩展无关：添加新的扩展不应要求修改核心代码来"认识"该扩展。核心通过清单元数据、注册表、能力声明和通用契约来发现和使用插件 ^[CLAUDE.md:41-42]。
- **插件**（`extensions/` + 外部包）通过 `openclaw/plugin-sdk/*` 访问核心能力，不能导入 `src/**` 内部模块 ^[CLAUDE.md:43]。
- **Plugin SDK**（`src/plugin-sdk/`）是两者之间的唯一公共契约表面。核心不得对特定扩展做硬编码特判（禁止硬编码扩展/Provider/通道 ID 列表、映射或命名特殊案例），应通过清单、能力声明或注册表表达相同行为 ^[CLAUDE.md:44]。
- 扩展拥有的兼容性行为属于该扩展。核心可以编排通用的 doctor/config 流程，但扩展特定的遗留修复、检测规则、onboarding、auth 检测和 Provider 默认值应留在插件拥有的契约中 ^[CLAUDE.md:45]。
- 供应商拥有的工具和设置属于该供应商插件。不要将供应商特定的工具配置、secret 收集或运行时启用添加到核心 `tools.*` 表面，除非该工具有意由核心拥有 ^[CLAUDE.md:58]。

### 通道边界

`src/channels/` 是核心通道实现。通道插件通过 `openclaw/plugin-sdk/channel-contract` 和 `openclaw/plugin-sdk/core` 中的公共类型与核心交互，不能直接导入 `src/channels/**` ^[src/channels/AGENTS.md:21-23]。ChannelPlugin 的适配器体系将不同关注点分离为独立接口（消息、安全、出站、配置、配对等各由单独的适配器负责）^[src/channels/plugins/types.adapters.ts:1-100]。

### 供应商边界

核心拥有通用推理循环；供应商插件通过注册和类型化 hooks 拥有供应商特定行为。避免从无关核心代码中临时读取 `plugins.entries.<id>.config`；如果核心需要插件拥有的行为，应添加或使用通用 seam（如 `resolveSyntheticAuth`、公共 SDK/helper facade、清单元数据、插件自动启用 hook）^[CLAUDE.md:57-58]。Provider hook 的精细分层（认证、目录、工具 Schema、流包装、重放策略、思考策略）确保每个供应商的特定行为被隔离在各自的 hook 实现中 ^[src/plugin-sdk/plugin-entry.ts:1-73]。

### Gateway 协议边界

网关协议定义在 `src/gateway/protocol/schema/` 中，与运行时验证器、文档、测试和生成的客户端工件保持同步。协议变更优先加法演进；不兼容变更需显式版本管理、文档和客户端/代码生成跟进 ^[src/gateway/protocol/AGENTS.md:17-28]。

### 配置契约边界

公共配置存在于导出的配置类型、zod/schema 表面、Schema help/label、生成的配置元数据、配置基线和用户面向的 Gateway/config 负载中。当旧配置键从公共契约退役时，向后兼容性仅通过原始配置迁移/doctor seam 处理，而非通过重新引入已移除的遗留别名到公共类型/schema/help/基线 ^[CLAUDE.md:64-68]。

### CLI 命令分离

CLI 命令通过 `CommandDescriptor` 系统清晰分层：核心命令、插件命令和子 CLI 通过统一的 `collectUniqueCommandDescriptors` 机制组合。CommandRegistry 支持命令组的延迟加载，避免启动时加载全部命令 ^[src/cli/program/root-help.ts:19-40]。

### Session 与 Agent 的分离

会话（Session）和代理（Agent）是两个正交概念：Session 是持久化的对话历史记录（Pi JSONL 文件），Agent 是 AI 代理配置（模型、系统提示、工具、超时）。`routing/resolve-route.ts` 将入站消息路由到正确的 Agent+Session 组合 ^[src/routing/resolve-route.ts:27-61]。`sessionKey` 格式为 `channel:account:agent:peer`，由 `routing/session-key.ts` 管理构建和解析 ^[src/routing/session-key.ts:1-19]。

---

## 关联

- **Channel** 通过 `ChannelPlugin` 类型定义在 `src/channels/plugins/types.plugin.ts:53`，由插件在 `register()` 时通过 `api.registerChannel()` 注册到核心。
- **Provider** 通过 `ProviderPlugin` hook 类型定义在 `src/plugins/types.ts`，其认证、工具、流包装 hook 在推理链路中被核心按序调用。
- **Agent** 的 `sessionKey` 由 `routing/session-key.ts` 生成，通过 `resolveAgentRoute()` 从入站消息上下文解析 ^[src/routing/resolve-route.ts:27-61]。
- **Gateway Protocol** 的 Schema 定义在 `src/gateway/protocol/schema/`，被 `server-methods/` 和客户端 SDK 共同消费。
- **Config** 的 `OpenClawConfig` 聚合所有子配置，被 `loadConfig()` 加载后注入到所有子系统 ^[src/config/types.openclaw.ts:32-80]。
- **Plugin SDK** 作为核心-插件之间的唯一桥梁，禁止插件直接导入核心内部模块，也禁止核心对特定插件做硬编码特判 ^[src/plugin-sdk/AGENTS.md:1-81]。
- **Harness** 由插件通过 `api.registerAgentHarness()` 注册，核心通过 `selectAgentHarness()` 按优先级选择 ^[src/agents/harness/types.ts:30-39]。
- **Tools** 通过工具策略管线的 5 层过滤（profile/provider/global/agent/group）控制可见性，exec 类工具通过异步审批协议进行权限门控。
