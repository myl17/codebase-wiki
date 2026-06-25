# OpenClaw — Structural Entity & Ontology 候选提取

从 `/Users/yuanlimiao/Work/agent_harness/openclaw/` 源码直接提取。

---

# 第一步：Structural Entity

## Entity: Plugin SDK（公共扩展合约）

**代码位置**：`src/plugin-sdk/` + `packages/plugin-sdk/`

**这个模块解决什么问题**：定义所有扩展（bundled + third-party）可导入的唯一公共合约表面，确保 core 与 extension 之间的边界清晰。

**对外暴露什么**：
- `definePluginEntry()` 工厂函数 ^[src/plugin-sdk/plugin-entry.ts:1]
- `defineSingleProviderPluginEntry()` 单模型供应商快速注册 ^[src/plugin-sdk/provider-entry.ts:100]
- `OpenClawPluginApi` 完整注册接口（registerProvider, registerChannel, registerTool, registerCommand, registerHook, 等 30+ 方法）^[src/plugins/types.ts:1867]
- `OpenClawPluginDefinition` 模块级插件定义类型 ^[src/plugins/types.ts:1829]
- `ProviderPlugin` 文本推理供应商合约 ^[src/plugins/types.ts:1051]
- `ChannelPlugin` 消息通道合约 ^[src/channels/plugins/types.plugin.ts:53]
- `AgentHarness` Agent 运行时嵌入合约 ^[src/agents/harness/types.ts:30]
- `SpeechProviderPlugin` 语音合成合约 ^[src/plugins/types.ts:1570]
- `ImageGenerationProviderPlugin` 图片生成合约 ^[src/plugins/types.ts:1628]
- `VideoGenerationProviderPlugin` 视频生成合约 ^[src/plugins/types.ts:1629]
- `MediaUnderstandingProviderPlugin` 媒体理解合约 ^[src/plugins/types.ts:1627]
- `WebSearchProviderPlugin` / `WebFetchProviderPlugin` 网络搜索/抓取合约 ^[src/plugins/types.ts:118]
- `RealtimeTranscriptionProviderPlugin` 实时转录合约 ^[src/plugins/types.ts:1596]
- `RealtimeVoiceProviderPlugin` 实时语音合约 ^[src/plugins/types.ts:1613]

**它和谁交互**：被所有扩展（extensions/ 目录下 ~110 个包）import；依赖 `src/plugins/types.ts`、`src/channels/plugins/types.plugin.ts` 等内部类型定义文件。

**为什么它是可分离的**：独立的 npm 包（`packages/plugin-sdk`），有独立的 `package.json` ^[packages/plugin-sdk/package.json]，有独立的 tsconfig ^[packages/plugin-sdk/tsconfig.json]，通过 `openclaw/plugin-sdk/*` 子路径导出。

**关键机制**（源码可见）：
- 入口点注册（entrypoints.ts）强制枚举所有合法子路径，防止扩展访问内部模块 ^[src/plugin-sdk/entrypoints.ts]
- API 基线清单（api-baseline.ts）跟踪所有公开导出，通过 CI 检测非预期变更 ^[src/plugin-sdk/api-baseline.ts]
- 窄子路径设计：prefer `import { X } from "openclaw/plugin-sdk/agent-runtime"` 而非 `"openclaw/plugin-sdk"` 全量 barrels ^[src/plugin-sdk/AGENTS.md:25]
- Provider 工厂辅助函数（`provider-catalog-shared.ts`、`provider-model-shared.ts`）标准化供应商注册 ^[src/plugin-sdk/provider-catalog-shared.ts]

**源码证据**：
- 入口文件：`src/plugin-sdk/plugin-entry.ts`
- 核心类型定义：`src/plugins/types.ts:1867`（OpenClawPluginApi）
- 公共合约索引：`src/plugin-sdk/core.ts:32`

---

## Entity: Plugin System（插件发现/加载/注册器）

**代码位置**：`src/plugins/`

**这个模块解决什么问题**：负责所有插件的发现（扫描 workspace + npm 安装）、manifest 验证、运行时加载和注册表组装。

**对外暴露什么**：
- Plugin loader：从文件系统加载 `openclaw.plugin.json` + 入口 JS ^[src/plugins/loader.ts]
- Plugin registry：维护所有已注册的 Provider、Channel、Tool、Command ^[src/plugins/contracts/registry.ts]
- Manifest 验证：`openclaw.plugin.json` schema 校验 ^[src/plugins/manifest-types.ts:88]
- Config schema 处理：`OpenClawPluginConfigSchema` ^[src/plugins/types.ts:205]
- Plugin activation 管线：`register()` and `activate()` lifecycle ^[src/plugins/types.ts:1840]
- Hook 类型系统：`PluginHookHandlerMap`, `PluginHookName` ^[src/plugins/hook-types.ts]

**它和谁交互**：依赖 `src/plugin-sdk/`（类型定义）、`src/config/`（配置）、被 `src/gateway/server-plugins.ts` 调用（启动时加载）、被所有扩展消费。

**为什么它是可分离的**：独立目录（`src/plugins/`），职责明确（discovery/validation/loading/registry），有独立的 AGENTS.md 边界规则文档。

**关键机制**（源码可见）：
- `OpenClawPluginDefinition` 是模块级入口定义的类型（id, kind, configSchema, register, activate）^[src/plugins/types.ts:1829]
- `PluginKind` 枚举当前只有 `"memory"` 和 `"context-engine"` ^[src/plugins/plugin-kind.types.ts:1]
- `PluginRegistrationMode` 分 "full"、"setup-only"、"setup-runtime"、"cli-metadata" 四个级别 ^[src/plugins/types.ts:1847]
- `PluginOrigin` 区分 bundled vs third-party vs npm ^[src/plugins/plugin-origin.types.ts]
- 合约测试确保 bundled 和 third-party 插件走相同路径 ^[src/plugins/contracts/registry.ts]

**源码证据**：
- 入口文件：`src/plugins/index.ts`
- 核心类型定义：`src/plugins/types.ts:1829`（OpenClawPluginDefinition）
- Registry：`src/plugins/contracts/registry.ts`

---

## Entity: Gateway Server（控制平面）

**代码位置**：`src/gateway/`

**这个模块解决什么问题**：OpenClaw 的后端服务器——处理 WebSocket 连接、HTTP API、多节点协调、客户端认证和会话管理。

**对外暴露什么**：
- Gateway Server 启动/关闭 ^[src/gateway/server.ts]
- HTTP endpoint 路由（control UI, API, webhooks）^[src/gateway/server-http.ts]
- WebSocket 实时传输（Gateway Protocol over WS）^[src/gateway/server-ws-runtime.ts]
- Client/Node 认证与授权 ^[src/gateway/auth.ts]
- Channel 运行时管理（启动/停止/健康检查）^[src/gateway/server-channels.ts]
- Session 生命周期管理（创建/删除/压缩/历史）^[src/gateway/session-utils.ts]
- Config 热重载 ^[src/gateway/config-reload.ts]
- Node 注册表（多设备/多节点拓扑）^[src/gateway/node-registry.ts]
- Cron 调度器 HTTP API ^[src/gateway/server-cron.ts]
- Exec 审批流（operator approvals）^[src/gateway/exec-approval-manager.ts]
- MCP HTTP 桥接 ^[src/gateway/mcp-http.ts]
- 运维审批系统 ^[src/gateway/operator-approvals-client.ts]

**它和谁交互**：依赖 `src/gateway/protocol/`（协议 schema）、`src/channels/`（通道运行时）、`src/plugins/`（插件系统）、`src/agents/`（Agent 执行）、`src/config/`（配置）；被 `openclaw gateway run` CLI 命令启动 ^[src/entry.ts:204]。

**为什么它是可分离的**：独立目录（`src/gateway/`），是整个平台的中央控制平面，WS + HTTP 服务独立可部署。

**关键机制**（源码可见）：
- Gateway 启动管线：早期启动 -> 插件加载 -> Channel 启动 -> HTTP 监听 ^[src/gateway/server-startup.ts]
- 多阶段启动：`server-startup-early` -> `server-startup-config` -> `server-startup-plugins` -> `server-startup-post-attach` ^[src/gateway/server-startup-early.ts]
- Session compaction：自动压缩长会话为摘要 ^[src/gateway/session-compaction-checkpoints.ts]
- Node 事件系统：订阅制跨节点事件总线 ^[src/gateway/server-node-events.ts]
- 设备配对审批流 ^[src/gateway/server-mobile-nodes.ts]
- 方法表罗列所有 Gateway RPC 方法 ^[src/gateway/server-methods-list.ts]

**源码证据**：
- 入口文件：`src/gateway/server.ts`
- 实现：`src/gateway/server.impl.ts`
- 启动：`src/gateway/server-startup.ts`

---

## Entity: Gateway Protocol（有线协议 schema）

**代码位置**：`src/gateway/protocol/`

**这个模块解决什么问题**：定义 Gateway 与所有客户端（CLI、Control UI、移动端）之间的类型安全有线协议——所有请求/响应/事件的 JSON Schema 合约。

**对外暴露什么**：
- RequestFrame / ResponseFrame / EventFrame 协议帧类型 ^[src/gateway/protocol/index.ts:197-201]
- Agent 相关 schema（create, update, delete, list, files）^[src/gateway/protocol/schema.ts:1]
- Session 相关 schema（create, send, abort, patch, reset, compact）^[src/gateway/protocol/schema.ts:17]
- Config 相关 schema（get, set, apply, patch）^[src/gateway/protocol/schema.ts:9]
- Channel 相关 schema（status, logout）^[src/gateway/protocol/schema.ts:3]
- Cron 相关 schema（add, update, remove, list, run）^[src/gateway/protocol/schema.ts:6]
- Wizard 相关 schema（start, next, cancel, status）^[src/gateway/protocol/schema.ts:18]
- Node 相关 schema（pair, invoke, event, pending）^[src/gateway/protocol/schema.ts:12]
- Device/Exec-Approval schema ^[src/gateway/protocol/schema.ts:8]
- Talk/Speech schema ^[src/gateway/protocol/schema.ts]
- Secrets resolve schema ^[src/gateway/protocol/schema.ts:15]
- AJV 编译的验证函数（validateConnectParams, validateRequestFrame 等）^[src/gateway/protocol/index.ts:305-510]
- 错误码枚举 `ErrorCodes` ^[src/gateway/protocol/index.ts:140]

**它和谁交互**：被 `src/gateway/server*.ts` 系列使用（请求验证、响应构造）；被 `src/cli/`（CLI client）、`ui/`（Web Control UI）、`apps/`（移动端）消费。

**为什么它是可分离的**：独立目录（`src/gateway/protocol/`），schema 文件按域拆分到 `schema/` 子目录，是有线协议的单一真相来源，不依赖运行时。

**关键机制**（源码可见）：
- Schema 编码：TypeScript type → ajv compile → validator function 三重结构 ^[src/gateway/protocol/index.ts:299-510]
- `PROTOCOL_VERSION` 版本标记 ^[src/gateway/protocol/index.ts:190]
- 按域拆分的 schema 文件（agents-models-skills, channels, config, cron, exec-approvals, nodes, sessions, push, secrets, devices, frames, logs-chat, snapshot, wizard, protocol-schemas）^[src/gateway/protocol/schema.ts:1-20]
- `formatValidationErrors` 统一错误格式化 ^[src/gateway/protocol/index.ts:512]

**源码证据**：
- 入口文件：`src/gateway/protocol/index.ts`
- Schema manifest：`src/gateway/protocol/schema.ts:1`

---

## Entity: Agent System（嵌入式 Pi 执行引擎）

**代码位置**：`src/agents/`

**这个模块解决什么问题**：以嵌入式方式运行 Pi Agent（mariozechner/pi-agent-core）——处理模型选择、流式推理、工具调用、上下文管理、系统提示组装。

**对外暴露什么**：
- `runEmbeddedPiAgent()` 嵌入式 Agent 运行 ^[src/agents/pi-embedded.ts]
- `AgentHarness` 接口（可替换的 Agent 运行时）^[src/agents/harness/types.ts:30]
- 模型选择逻辑（defaults, thinking levels）^[src/agents/model-selection.js]
- 系统提示组装 ^[src/agents/system-prompt.ts]
- Agent scope/workspace 管理 ^[src/agents/agent-scope.ts]
- Auth profile 管理（credential rotation, cooldown）^[src/agents/auth-profiles/]
- Anthropic 专用传输流（standard + vertex）^[src/agents/anthropic-transport-stream.ts]
- 模型目录（ModelCatalogEntry）^[src/agents/model-catalog.types.ts]
- Failover 机制 ^[src/agents/pi-embedded-helpers/types.js:14]

**它和谁交互**：依赖 `src/plugins/types.ts`（ProviderPlugin）、`src/config/`（模型配置）；被 `src/gateway/server-chat.ts` 调用（Gateway 聊天会话）、被 `src/cli/`（CLI agent 命令）调用。

**为什么它是可分离的**：独立目录（`src/agents/`），通过 AgentHarness 接口实现可替换性，支持多种 Agent 运行时嵌入。

**关键机制**（源码可见）：
- `AgentHarness` 定义了标准的 `supports()`, `runAttempt()`, `compact()`, `reset()`, `dispose()` 接口 ^[src/agents/harness/types.ts:30-38]
- 嵌入式 Pi runner 处理完整的 tool-calling 循环 + 压缩 ^[src/agents/pi-embedded-runner/]
- Provider auth profiles 支持 cooldown + round-robin + 自动故障转移 ^[src/agents/auth-profiles/]
- Anthropic 提示缓存日志（调试 payload 大小/结构）^[src/agents/anthropic-payload-log.ts]
- API key rotation 支持 ^[src/agents/api-key-rotation.ts]

**源码证据**：
- 入口文件：`src/agents/pi-embedded.ts`
- Harness 接口：`src/agents/harness/types.ts:30`

---

## Entity: Channel System（消息通道）

**代码位置**：`src/channels/`

**这个模块解决什么问题**：处理所有消息通道的入站/出站适配——轮询、安全策略、账户绑定、线程管理、媒体消息。

**对外暴露什么**：
- `ChannelPlugin` 接口（含 30+ 适配器插槽）^[src/channels/plugins/types.plugin.ts:53]
- `ChannelMessagingAdapter` 消息收发适配器 ^[src/channels/plugins/types.core.ts]
- `ChannelOutboundAdapter` 出站投递 ^[src/channels/plugins/outbound.types.ts]
- `ChannelSecurityAdapter` 安全/DM 策略 ^[src/channels/plugins/types.adapters.ts]
- `ChannelPairingAdapter` 配对适配器 ^[src/channels/plugins/pairing.types.ts]
- `ChannelThreadingAdapter` 线程适配器 ^[src/channels/plugins/types.core.ts]
- `ChannelSetupAdapter` 安装向导 ^[src/channels/plugins/types.adapters.ts]
- `ChannelLifecycleAdapter` 生命周期管理 ^[src/channels/plugins/types.adapters.ts]
- `ChannelConfigAdapter` 配置适配器 ^[src/channels/plugins/types.adapters.ts]
- `ChannelStatusAdapter` 健康状态适配器 ^[src/channels/plugins/types.adapters.ts]
- `ChannelAgentToolFactory` Channel 专用的 Agent 工具 ^[src/channels/plugins/types.core.ts:31]

**它和谁交互**：被 `src/gateway/server-channels.ts` 驱动（启动/停止/健康检查）；Channel 实现分布在 `src/`（telegram, discord, slack, signal, imessage, whatsapp）和 `extensions/`（matrix, zalo, irc, msteams, etc.）。

**为什么它是可分离的**：独立目录（`src/channels/`），适配器模式高度解耦，每个 Channel 是新实现，通过 `ChannelPlugin<ResolvedAccount>` 泛型接口注册。

**关键机制**（源码可见）：
- Channel 适配器分为 30+ 个可插拔 slot，每个 Channel 只实现需要的 ^[src/channels/plugins/types.plugin.ts:53-96]
- `ChannelMeta` 提供 UI/文档用的元数据（label, docsPath, blurb, aliases, showInSetup）^[src/channels/plugins/types.core.ts:142-164]
- `ChannelAccountSnapshot` 统一所有 Channel 的状态快照字段 ^[src/channels/plugins/types.core.ts:167-229]
- Channel 健康监控（`channel-health-monitor.ts`）^[src/gateway/channel-health-monitor.ts]
- 出站路由通过 `buildOutboundBaseSessionKey` 确定目标会话 ^[src/infra/outbound/base-session-key.ts]

**源码证据**：
- 核心接口：`src/channels/plugins/types.plugin.ts:53`
- 适配器类型：`src/channels/plugins/types.adapters.ts`
- 核心类型：`src/channels/plugins/types.core.ts`

---

## Entity: CLI（命令行接口）

**代码位置**：`src/cli/` + `src/commands/`

**这个模块解决什么问题**：提供完整功能的 CLI（基于 Commander.js），包括 `openclaw gateway run`、`openclaw agent`、`openclaw config`、`openclaw models` 等命令。

**对外暴露什么**：
- Commander program 构建 ^[src/cli/program/]
- `runCli()` 入口 ^[src/cli/run-main.ts]
- Profile 系统（dev/prod 环境切换）^[src/cli/profile.js]
- Container target 路由（Docker 命令转发）^[src/cli/container-target.js]
- Root help 预计算（快速 help 输出）^[src/cli/root-help-metadata.ts]
- 各类子命令：agent, config, models, channels, cron, sessions, secrets, wizard, talk, update, doctor, status, skills, memory

**它和谁交互**：依赖 Commander、`src/gateway/`（Gateway client）、`src/config/`（配置读写）、`src/plugins/`（插件 CLI 注册）；被 `src/entry.ts:204` 启动。

**为什么它是可分离的**：独立目录（`src/cli/` + `src/commands/`），通过 Commander 命令注册模式与 Core 解耦。

**关键机制**（源码可见）：
- Profile/Container 参数提前解析（在 Commander 之前剥离）^[src/entry.ts:128-155]
- CLI respawn 机制（`buildCliRespawnPlan`）处理运行时版本切换 ^[src/entry.respawn.ts]
- Docker container target 路由透明转发 CLI 命令到容器 ^[src/cli/container-target.js]
- Root help 预计算缓存避免每次 `--help` 加载所有命令 ^[src/cli/root-help-metadata.ts]

**源码证据**：
- 入口文件：`src/cli/run-main.ts`
- 命令目录：`src/commands/`
- 启动入口：`src/entry.ts:200`

---

## Entity: Config System（配置管理）

**代码位置**：`src/config/`

**这个模块解决什么问题**：管理 OpenClaw 的全量配置——加载、验证、合并默认值、迁移、热重载、schema 生成。

**对外暴露什么**：
- `OpenClawConfig` 完整配置类型 ^[src/config/types.openclaw.ts]
- `loadConfig()` 配置加载器 ^[src/config/config.ts]
- Zod schema + JSON Schema 生成（用于 Control UI 表单验证）^[src/config/schema.ts]
- Config 迁移（legacy -> 现代格式）^[src/config/legacy/]
- Config defaults 合并 ^[src/config/defaults.ts]
- `ModelProviderConfig` 模型供应商配置类型 ^[src/config/types.ts:23]
- 配置热重载计划 ^[src/config/reload.ts]

**它和谁交互**：被所有模块依赖（全局配置源）；被 Gateway（热重载）、CLI（读写）、Control UI（表单渲染）、plugins（provider defaults）消费。

**为什么它是可分离的**：独立目录（`src/config/`），类型定义是模块间的主要数据合约。

**关键机制**（源码可见）：
- 分为 `types.openclaw.ts`（全局配置）和 `types.ts`（子类型）^[src/config/types.openclaw.ts, src/config/types.ts]
- Zod schema 同时用于运行时验证和 JSON Schema 生成 ^[src/config/schema.ts]
- Legacy migration 路径显式定义在 `legacy.migrations.*` ^[src/config/legacy/]
- Config 基线文件（`.json`）通过 SHA-256 哈希检测漂移 ^[src/config/baseline/]

**源码证据**：
- 入口文件：`src/config/config.ts`
- 核心类型：`src/config/types.openclaw.ts`

---

## Entity: Memory Core（记忆核心插件）

**代码位置**：`extensions/memory-core/`

**这个模块解决什么问题**：提供文件级记忆系统——AI Agent 可以 search（语义搜索）、get（读取）、主动 dreaming（后台整理记忆）。

**对外暴露什么**：
- `memory_search` Agent Tool ^[extensions/memory-core/src/tools.ts]
- `memory_get` Agent Tool（读取记忆文件）^[extensions/memory-core/src/tools.ts]
- Dreaming 管线（light/REM/deep 三阶段）^[extensions/memory-core/src/dreaming.ts]
- Memory flush plan（压缩前记忆冲刷）^[extensions/memory-core/src/flush-plan.ts]
- Prompt section builder（构建记忆注入到 system prompt）^[extensions/memory-core/src/prompt-section.ts]
- CLI `memory` 命令（search, inspect, reindex）^[extensions/memory-core/src/cli.ts]
- `MemoryPluginCapability` 注册（通过 `api.registerMemoryCapability()`）^[extensions/memory-core/index.ts:33]
- 记忆证据追踪（rem-evidence.ts）^[extensions/memory-core/src/rem-evidence.ts]
- 短期记忆提升（short-term-promotion.ts）^[extensions/memory-core/src/short-term-promotion.ts]

**它和谁交互**：通过 `api.registerMemoryCapability()` 注册为独占 memory slot ^[extensions/memory-core/index.ts:33]；通过 `api.registerMemoryEmbeddingProvider()` 注册多种嵌入供应商 ^[extensions/memory-core/src/memory/provider-adapters.js]；被 Gateway 启动时加载。

**为什么它是可分离的**：独立的 workspace extension 包（`extensions/memory-core/`），有独立的 `package.json`、`tsconfig.json`、`openclaw.plugin.json` manifest ^[extensions/memory-core/openclaw.plugin.json:1]。

**关键机制**（源码可见）：
- Plugin manifest 声明 `kind: "memory"` ^[extensions/memory-core/openclaw.plugin.json:3]
- Dreaming 三个阶段：Light（recency dedup）、REM（pattern synthesis）、Deep（记忆评分）^[extensions/memory-core/openclaw.plugin.json:55-133]
- 可配置的 dreaming cron schedule 和 storage mode ^[extensions/memory-core/openclaw.plugin.json:18-49]
- 嵌入供应商适配器允许切换底层嵌入模型（OpenAI、Mistral、Gemini、Voyage、Ollama）^[packages/memory-host-sdk/src/host/embeddings.ts]

**源码证据**：
- 入口文件：`extensions/memory-core/index.ts`
- Plugin manifest：`extensions/memory-core/openclaw.plugin.json`
- 核心 Tool：`extensions/memory-core/src/tools.ts`

---

## Entity: Memory Host SDK（记忆引擎合约）

**代码位置**：`packages/memory-host-sdk/`

**这个模块解决什么问题**：定义记忆引擎的 host 端合约——嵌入、存储、查询、批量处理、schema 迁移。

**对外暴露什么**：
- `EmbeddingProvider` 接口（embedQuery, embedBatch）^[packages/memory-host-sdk/src/engine-embeddings.ts]
- 存储引擎抽象 ^[packages/memory-host-sdk/src/engine-storage.ts]
- QMD（Queryable Markdown）引擎 ^[packages/memory-host-sdk/src/engine-qmd.ts]
- 基础引擎合约 ^[packages/memory-host-sdk/src/engine-foundation.ts]
- 多供应商嵌入实现（OpenAI, Mistral, Gemini, Voyage, Ollama, Bedrock）^[packages/memory-host-sdk/src/host/embeddings-*.ts]
- SQLite-vec 向量扩展 ^[packages/memory-host-sdk/src/host/sqlite-vec.ts]
- 批量处理工具（batch-openai, batch-voyage）^[packages/memory-host-sdk/src/host/batch-*.ts]
- Query expansion ^[packages/memory-host-sdk/src/host/query-expansion.ts]
- 运行时 CLI/文件接口 ^[packages/memory-host-sdk/src/runtime.ts, runtime-cli.ts, runtime-files.ts]

**它和谁交互**：被 `extensions/memory-core/`、`extensions/memory-lancedb/`、`extensions/memory-wiki/` 等多个记忆后端消费。

**为什么它是可分离的**：独立的 npm 包（`packages/memory-host-sdk/`），有独立的 `package.json`，通过接口定义实现多个存储后端。

**关键机制**（源码可见）：
- 引擎聚合 barrel：`engine.ts` 重导出四个子引擎合约 ^[packages/memory-host-sdk/src/engine.ts]
- 嵌入维度信息（embedding-model-limits, embedding-chunk-limits, embedding-input-limits）^[packages/memory-host-sdk/src/host/]
- Node-llama 本地模型支持 ^[packages/memory-host-sdk/src/host/node-llama.ts]
- Memory schema 迁移管理 ^[packages/memory-host-sdk/src/host/memory-schema.ts]

**源码证据**：
- 入口文件：`packages/memory-host-sdk/src/engine.ts`
- 嵌入实现示例：`packages/memory-host-sdk/src/host/embeddings-openai.ts`

---

## Entity: Browser Extension（浏览器自动化）

**代码位置**：`extensions/browser/`

**这个模块解决什么问题**：通过 CDP（Chrome DevTools Protocol）提供浏览器自动化能力，允许 Agent 浏览网页、截图、执行 JS。

**对外暴露什么**：
- Browser CDP 连接管理 ^[extensions/browser/browser-cdp.ts]
- Browser profiles 管理 ^[extensions/browser/browser-profiles.ts]
- Browser control auth（授权控制）^[extensions/browser/browser-control-auth.ts]
- Browser doctor（诊断修复）^[extensions/browser/browser-doctor.ts]
- Browser maintenance ^[extensions/browser/browser-maintenance.ts]
- Plugin registration（register agent tools）^[extensions/browser/plugin-registration.ts]
- Browser bridge（与宿主浏览器进程通信）^[extensions/browser/browser-bridge.ts]

**它和谁交互**：依赖 `src/plugin-sdk/browser-*.ts`（browser 专用 SDK 表面）、CDP 协议；被 Agent 在推理时通过 browser tool 调用。

**为什么它是可分离的**：独立的 workspace extension 包（`extensions/browser/`），通过 `enabledByDefault: true` 默认开启 ^[extensions/browser/openclaw.plugin.json:3]。

**关键机制**（源码可见）：
- CDP 协议操作（Page.navigate, Runtime.evaluate, etc.）^[extensions/browser/browser-cdp.ts]
- Browser host inspection 检测可用的浏览器安装 ^[extensions/browser/browser-host-inspection.ts]
- Browser profiles 支持多浏览器配置 ^[extensions/browser/browser-profiles.ts]
- 安全审计集成 ^[extensions/browser/src/security-audit.ts]

**源码证据**：
- 入口文件：`extensions/browser/index.ts`
- Plugin manifest：`extensions/browser/openclaw.plugin.json`
- CDP 实现：`extensions/browser/browser-cdp.ts`

---

## Entity: Speech Core（语音核心）

**代码位置**：`extensions/speech-core/`

**这个模块解决什么问题**：提供 TTS（文字转语音）/ STT（语音转文字）统一抽象层，抹平 ElevenLabs、Deepgram、Sherpa-ONNX 等后端差异。

**对外暴露什么**：
- Universal `synthesize()` TTS 接口 ^[extensions/speech-core/src/tts.ts]
- Speech synthesis routing（自动选择已配置的 providers）^[extensions/speech-core/src/tts.ts]
- Runtime API ^[extensions/speech-core/runtime-api.ts]
- Plugin API ^[extensions/speech-core/api.ts]

**它和谁交互**：通过 `api.registerSpeechProvider()` 接收多个 TTS 实现（elevenlabs, deepgram, sherpa-onnx-tts skill 等）；被 Agent 的 `talk` 命令调用。

**为什么它是可分离的**：独立的 workspace extension 包（`extensions/speech-core/`），有独立的 `package.json`。

**关键机制**（源码可见）：
- `synthesize()` 统一接口：接受 `SpeechSynthesisRequest` → 返回 `SpeechSynthesisResult` ^[extensions/speech-core/src/tts.ts]
- 多 Provider 自动选择（`autoSelectOrder`）^[extensions/speech-core/src/tts.ts]
- Telephony 语音合成特殊路径（8kHz mu-law）^[src/plugins/types.ts:1585-1587]

**源码证据**：
- 入口文件：`extensions/speech-core/src/tts.ts`
- SDK 类型：`src/plugins/types.ts:1570-1589`（SpeechProviderPlugin）

---

## Entity: Image Generation Core（图片生成核心）

**代码位置**：`extensions/image-generation-core/`

**这个模块解决什么问题**：统一图片生成抽象——Agent 请求一张图片，系统路由到已配置的生成后端。

**对外暴露什么**：
- Image generation runtime ^[extensions/image-generation-core/src/runtime.ts]
- Runtime API ^[extensions/image-generation-core/runtime-api.ts]
- Plugin API ^[extensions/image-generation-core/api.ts]

**它和谁交互**：通过 `api.registerImageGenerationProvider()` 接收多个后端（fal, comfy, runway 等）；ImageGenerationProvider 接口定义在 `src/image-generation/types.ts` ^[src/image-generation/types.ts]。

**为什么它是可分离的**：独立的 workspace extension 包（`extensions/image-generation-core/`），有独立的 `package.json`。

**关键机制**（源码可见）：
- `ImageGenerationProvider` 合约 ^[src/image-generation/types.ts]

**源码证据**：
- 入口文件：`extensions/image-generation-core/src/runtime.ts`
- Provider 类型：`src/image-generation/types.ts`

---

## Entity: Video Generation Core / Media Understanding Core / Music Generation Core

**代码位置**：`extensions/video-generation-core/`、`extensions/media-understanding-core/`、`src/music-generation/`

**这些模块解决什么问题**：分别提供视频生成、媒体理解（视觉分析）、音乐生成的统一抽象。

**对外暴露什么**：
- `VideoGenerationProvider` 接口 ^[src/video-generation/types.ts]
- `MediaUnderstandingProvider` 接口 ^[src/media-understanding/types.ts]
- `MusicGenerationProvider` 接口 ^[src/music-generation/types.ts]

**它和谁交互**：分别通过 `api.registerVideoGenerationProvider()`、`api.registerMediaUnderstandingProvider()`、`api.registerMusicGenerationProvider()` 注册多个后端实现。

**为什么它们是可分离的**：独立的 contracts 定义在 `src/<domain>/types.ts` 中，各自有独立目录，通过统一的 api.register* 模式注册。

**关键机制**（源码可见）：
- 三者都遵循 `api.registerXxxProvider()` 统一注册模式 ^[src/plugins/types.ts:1944-1951]

**源码证据**：
- Video：`src/video-generation/types.ts`
- Media Understanding：`src/media-understanding/types.ts`
- Music：`src/music-generation/types.ts`

---

## Entity: Web Search & Web Fetch Providers

**代码位置**：厂商在 `extensions/` 中各自独立目录（`brave/`, `tavily/`, `searxng/`, `duckduckgo/`, `firecrawl/`, `exa/`）

**这个模块解决什么问题**：分别为 Agent 提供网络搜索和网页抓取能力，通过统一接口让 Agent 无需关心后端差异。

**对外暴露什么**：
- `WebSearchProviderPlugin` 接口 ^[src/plugins/types.ts:118]（来自 `src/plugins/web-provider-types.ts`）
- `WebFetchProviderPlugin` 接口 ^[src/plugins/types.ts:118]
- Tool definition（description + parameters + execute）^[src/plugins/web-provider-types.ts:13-23]

**它和谁交互**：通过 `api.registerWebSearchProvider()` 和 `api.registerWebFetchProvider()` 注册 ^[src/plugins/types.ts:1953-1954]；被 Agent 在 tool-calling 时自动调用。

**为什么它们是可分离的**：各自是独立的 extension 包，有独立的 `openclaw.plugin.json` manifest 和 `package.json`。

**关键机制**（源码可见）：
- WebSearch provider 定义包括 credential resolution source（config/secretRef/env/missing）^[src/plugins/web-provider-types.ts:37]
- WebFetch provider 同样有 credential resolution ^[src/plugins/web-provider-types.ts:58]
- Runtime metadata 注入允许 provider 覆盖全局配置 ^[src/plugins/web-provider-types.ts:28-35]

**源码证据**：
- SDK 类型：`src/plugins/web-provider-types.ts:10-23`
- 示例实现：`extensions/brave/`、`extensions/tavily/`、`extensions/firecrawl/`、`extensions/exa/`

---

## Entity: Voice Call（语音通话）

**代码位置**：`extensions/voice-call/`

**这个模块解决什么问题**：提供电话语音通话能力——通过 Telnyx API 接听/拨打电话，集成 TTS/STT 实现 AI 语音对话。

**对外暴露什么**：
- Voice Call Channel Plugin ^[extensions/voice-call/]
- Telnyx 集成（SIP trunking）^[extensions/voice-call/openclaw.plugin.json]
- Talk voice skill ^[extensions/talk-voice/]

**它和谁交互**：依赖 `extensions/speech-core/`（TTS）、`extensions/deepgram/`（STT）；作为 Channel Plugin 注册到系统。

**为什么它是可分离的**：独立的 workspace extension 包，有 `openclaw.plugin.json` manifest 和 `channelEnvVars` 配置。

**关键机制**（源码可见）：
- `channelEnvVars` 声明 `TELNYX_API_KEY` 等环境变量 ^[extensions/voice-call/openclaw.plugin.json:3-6]

**源码证据**：
- manifest：`extensions/voice-call/openclaw.plugin.json`

---

## Entity: Node Host（节点端执行环境）

**代码位置**：`src/node-host/`

**这个模块解决什么问题**：提供节点端（如移动端设备、远程机器）上的命令执行、文件操作、凭据管理。

**对外暴露什么**：
- Node host runner ^[src/node-host/runner.ts]
- System run invocation ^[src/node-host/invoke-system-run.ts]
- Exec policy 控制 ^[src/node-host/exec-policy.ts]
- Plugin node host 桥接 ^[src/node-host/plugin-node-host.ts]
- Node host config ^[src/node-host/config.ts]
- SSH credentials 管理 ^[src/node-host/runner.credentials.ts]

**它和谁交互**：被 Gateway 通过 Node Event/Invoke 协议调用 ^[src/gateway/server-node-events.ts]；依赖 Gateway Protocol。

**为什么它是可分离的**：独立目录（`src/node-host/`），Node 是独立可部署的运行时单元。

**关键机制**（源码可见）：
- System run plan（构建要执行的命令序列）^[src/node-host/invoke-system-run-plan.ts]
- Exec policy 沙箱化（允许/禁止特定命令）^[src/node-host/exec-policy.ts]
- Timeout 保护（`with-timeout.ts`）^[src/node-host/with-timeout.ts]

**源码证据**：
- 入口文件：`src/node-host/runner.ts`
- 执行：`src/node-host/invoke.ts`

---

## Entity: Skills System（Agent 技能库）

**代码位置**：`skills/`（~52 个独立技能目录）

**这个模块解决什么问题**：提供 Agent 可动态加载的领域技能——每个 Skill 是一个独立的 markdown 指令文件，告诉 Agent 如何完成特定任务。

**对外暴露什么**：
- 每个 Skill 目录包含 `SKILL.md`（Agent 指令）和可选的辅助文件
- 技能包括：github, coding-agent, canvas, weather, 1password, apple-notes, notion, obsidian, spotify-player, trello, discord, slack, taskflow, voice-call, home automation, etc.

**它和谁交互**：被 Agent 在 tool-calling 时通过 skill tool 动态加载和引用；通过 Gateway 的 skills API manage。

**为什么它是可分离的**：独立顶层目录（`skills/`），每个 Skill 是自包含的 markdown + 可选脚本包，不依赖 TypeScript 编译。

**关键机制**（源码可见）：
- Skills 管理通过 Gateway protocol 暴露（SkillsBins, SkillsSearch, SkillsInstall, SkillsUpdate, SkillsDetail）^[src/gateway/protocol/schema.ts:14]
- 每个 Skill 在 `SKILL.md` 中声明自己的 capabilities 和使用说明 ^[skills/*/SKILL.md]

**源码证据**：
- 入口：`skills/` 目录
- Gateway API：`src/gateway/protocol/schema.ts` (skills* schemas)

---

## Entity: TUI（终端 UI）/ Control UI（Web 控制面板）

**代码位置**：`src/tui/` + `ui/`

**这个模块解决什么问题**：TUI 提供终端内的交互式用户界面（rich tables, progress bars）；Control UI 提供 Web 管理面板（React/Vite）。

**对外暴露什么**：
- TUI 组件：table, status display, progress spinners ^[src/tui/]
- Terminal palette（颜色常量）^[src/terminal/palette.ts]
- Control UI：Web 控制面板（Svelte/React 构建）^[ui/]
- i18n 本地化框架 ^[ui/src/i18n/]

**它和谁交互**：TUI 被 CLI 命令使用；Control UI 通过 Gateway HTTP API 与后端通信。

**为什么它们是可分离的**：TUI 是独立目录（`src/tui/`）；Control UI 是独立顶层前端项目（`ui/`），有自己的构建管线。

**关键机制**（源码可见）：
- CLI progress 使用 `osc-progress` + `@clack/prompts` ^[src/cli/progress.ts]
- ANSI 安全的表格渲染（`src/terminal/table.ts`）^[src/terminal/table.ts]

**源码证据**：
- TUI：`src/tui/`
- Control UI：`ui/`

---

## Entity: Secrets & Security（凭据管理与安全审计）

**代码位置**：`src/secrets/` + `src/security/`

**这个模块解决什么问题**：统一管理所有凭据——API keys、tokens、OAuth tokens——支持 env、文件、密钥存储等多种来源；安全审计扫描配置中的潜在问题。

**对外暴露什么**：
- Secret resolver（多来源优先级：env > profile > config）^[src/secrets/]
- Secret target registry（哪些 provider/channel 需要哪些 secret）^[src/secrets/target-registry-types.ts]
- Runtime web tools secrets ^[src/secrets/runtime-web-tools.types.ts]
- Security audit engine（扫描配置中的安全问题）^[src/security/audit.ts]
- Security audit findings 类型 ^[src/security/audit.types.ts]

**它和谁交互**：被 Gateway 启动时加载（auth resolution）、被 Plugin SDK（`resolveSyntheticAuth`）、被 Provider plugins（auth methods）。

**为什么它们是可分离的**：两个独立目录（`src/secrets/`、`src/security/`），职责明确。

**关键机制**（源码可见）：
- 多来源凭据解析优先级显式定义 ^[src/plugins/types.ts:1500-1529]
- SecretRef 支持（引用外部密钥管理器而不暴露明文）^[src/plugins/types.ts:1506-1521]
- `PluginSecurityAuditCollector` 允许插件贡献自己的安全检查 ^[src/plugins/types.ts:1805]
- Auth doctor hint 帮助用户诊断/修复凭据问题 ^[src/plugins/types.ts:1496-1498]

**源码证据**：
- Secrets：`src/secrets/`
- Security：`src/security/audit.types.ts`

---

## Entity: Cron System（定时任务调度）

**代码位置**：`src/cron/`

**这个模块解决什么问题**：提供 cron 式定时任务调度——自动运行 agent 对话、memory dreaming、周期性检查。

**对外暴露什么**：
- Cron job 添加/更新/删除 ^[src/cron/]
- Cron 调度器 ^[src/cron/scheduler.ts]
- 支持标准 5-field cron 表达式 ^[extensions/memory-core/openclaw.plugin.json:18]

**它和谁交互**：被 Gateway 管理（通过 cron HTTP API）；被 memory-core dreaming 使用。

**为什么它是可分离的**：独立目录（`src/cron/`）。

**源码证据**：
- Cron 入口：`src/cron/`

---

## Entity: Session Management（会话管理）

**代码位置**：`src/sessions/` + `src/gateway/session-*.ts`

**这个模块解决什么问题**：管理 AI Agent 的会话生命周期——创建、压缩、分支、历史、文件存储。

**对外暴露什么**：
- Session create/reset/delete ^[src/gateway/session-utils.ts]
- Session compaction（自动压缩长对话为摘要）^[src/gateway/session-compaction-checkpoints.ts]
- Session history state ^[src/gateway/session-history-state.ts]
- Session preview ^[src/gateway/session-preview.test-helpers.ts]
- Session transcript files (JSONL) ^[src/gateway/session-transcript-files.fs.ts]
- Session archive runtime ^[src/gateway/session-archive.runtime.ts]
- Sub-agent session 管理 ^[src/gateway/session-subagent-reactivation.ts]

**它和谁交互**：被 Gateway 所有聊天/session API 使用；被 Agent System 在运行前后读/写。

**为什么它是可分离的**：独立目录（`src/sessions/`）加 Gateway 中的 session-*.ts 文件。

**关键机制**（源码可见）：
- Session compaction 自动触发（基于 token 预算）^[src/gateway/session-compaction-checkpoints.ts]
- Compaction 支持 branching（分支）和 restore ^[src/gateway/protocol/schema.ts:210-228]
- Session transcript 按 `<agentId>/sessions/*.jsonl` 存储 ^[src/gateway/session-transcript-files.fs.ts]

**源码证据**：
- 核心文件：`src/gateway/session-utils.ts`

---

## Entity: App Platforms（原生应用）

**代码位置**：`apps/`（macOS, iOS, Android, shared）

**这个模块解决什么问题**：提供各平台的原生应用——macOS 菜单栏应用、iOS/Android 移动端应用。

**对外暴露什么**：
- macOS app（Sparkle 自动更新, menu bar, control panel）^[apps/macos/]
- iOS app（SwiftUI）^[apps/ios/]
- Android app（Kotlin, Jetpack Compose）^[apps/android/]
- 共享 Swift 代码 ^[apps/shared/]
- Swabble 子项目（Swift 词法/语法工具）^[Swabble/]

**它和谁交互**：通过 Gateway WebSocket 协议与 backend 通信；独立构建管线。

**为什么它们是可分离的**：独立顶层目录，各自有独立的构建系统（Xcode, Gradle），与 TypeScript 后端完全解耦。

**源码证据**：
- macOS：`apps/macos/`
- iOS：`apps/ios/`
- Android：`apps/android/`

---

## Entity: Hooks System（生命周期钩子系统）

**代码位置**：`src/hooks/`

**这个模块解决什么问题**：提供可扩展的生命周期钩子——插件可以在特定事件点（消息发送前/后、agent 启动前/后）执行自定义逻辑。

**对外暴露什么**：
- `PluginHookHandlerMap` 所有钩子类型映射 ^[src/plugins/hook-types.ts]
- `PluginHookReplyDispatch` 回复分发钩子 ^[src/plugins/types.ts:96]
- `InternalHookHandler` 内部钩子处理 ^[src/hooks/internal-hook-types.ts]
- Hook 注册 API（`api.registerHook()`）^[src/plugins/types.ts:1889]

**它和谁交互**：被 plugins 通过 `api.registerHook()` 注册；被 Gateway 和 Agent 在各个生命周期点调用。

**为什么它是可分离的**：独立目录（`src/hooks/`），事件驱动架构。

**源码证据**：
- 核心类型：`src/plugins/hook-types.ts`
- 运行时：`src/hooks/`

---

## Entity: ACP（Agent Communication Protocol）绑定

**代码位置**：`src/acp/`

**这个模块解决什么问题**：实现 ACP 协议（Agent Communication Protocol）——Agent 之间的标准化通信、spawning sub-agents。

**对外暴露什么**：
- ACP spawning（parent -> child agent）^[src/agents/acp-spawn.ts]
- ACP binding architecture ^[src/agents/acp-binding-architecture.guardrail.test.ts]
- ACP 运行时 ^[src/plugin-sdk/acp-runtime.ts]

**它和谁交互**：被 Agent System 用于创建 sub-agent；被 Plugin SDK 暴露给扩展。

**为什么它是可分离的**：独立目录（`src/acp/`），协议级抽象。

**源码证据**：
- Spawn：`src/agents/acp-spawn.ts`
- SDK：`src/plugin-sdk/acp-runtime.ts`

---

## Entity: MCP（Model Context Protocol）集成

**代码位置**：`src/mcp/`

**这个模块解决什么问题**：集成 Anthropic 的 MCP 协议——让 Agent 可以发现和调用外部 MCP servers 提供的 tools。

**对外暴露什么**：
- MCP HTTP handlers ^[src/gateway/mcp-http.handlers.ts]
- MCP HTTP protocol bridge ^[src/gateway/mcp-http.protocol.ts]
- MCP server 注册与路由 ^[src/mcp/]

**它和谁交互**：被 Gateway 通过 `mcp-http.ts` 集成；对外暴露 MCP-compatible HTTP endpoint。

**为什么它是可分离的**：独立目录（`src/mcp/`）。

**源码证据**：
- Gateway integration：`src/gateway/mcp-http.ts`

---

## Entity: Auto-Reply System（自动回复引擎）

**代码位置**：`src/auto-reply/`

**这个模块解决什么问题**：处理 Agent 回复的分发——将 LLM 输出按格式转换并路由到正确的 Channel target。

**对外暴露什么**：
- `ReplyPayload` 类型 ^[src/auto-reply/reply-payload.ts]
- 回复分发逻辑 ^[src/auto-reply/]
- Templating（`MsgContext`）^[src/auto-reply/templating.js]
- Thinking level 管理 ^[src/auto-reply/thinking.shared.js]

**它和谁交互**：被 Agent System 在推理完成后调用；被 Channel outbound adapters 消费。

**为什么它是可分离的**：独立目录（`src/auto-reply/`）。

**源码证据**：
- Payload：`src/auto-reply/reply-payload.ts`

---

## Entity: Device Pairing（设备配对）

**代码位置**：`src/pairing/` + `extensions/device-pair/`

**这个模块解决什么问题**：管理移动设备/客户端与 Gateway 的安全配对流程——包括配对请求、审批、token 管理。

**对外暴露什么**：
- Pairing workflow ^[src/pairing/]
- Device pair approve/reject/remove API ^[src/gateway/protocol/schema.ts:8]
- Device token rotate/revoke ^[src/gateway/protocol/schema.ts:8]

**它和谁交互**：被 Gateway 的设备配对审批流调用 ^[src/gateway/server-mobile-nodes.ts]。

**为什么它是可分离的**：独立目录（`src/pairing/`）加独立 extension（`extensions/device-pair/`）。

**源码证据**：
- Pairing：`src/pairing/`
- Extension：`extensions/device-pair/`

---

## Entity: Infrastructure Utilities（基础设施工具）

**代码位置**：`src/infra/`

**这个模块解决什么问题**：提供底层工具——环境变量处理、错误格式化、进程管理、HTTP helpers。

**对外暴露什么**：
- Env normalization ^[src/infra/env.js]
- 错误格式化 ^[src/infra/errors.js]
- Process warning filter ^[src/infra/warning-filter.js]
- Outbound delivery ^[src/infra/outbound/deliver.js]
- Provider usage snapshots ^[src/infra/provider-usage.types.ts]

**它和谁交互**：被几乎所有其他模块依赖。

**为什么它是可分离的**：独立目录（`src/infra/`），纯工具函数无业务逻辑。

**源码证据**：
- 入口：`src/infra/`

---

# 第二步：候选 Ontology 节点

## Ontology 候选: Model Provider（LLM 文本推理）

**信号类型**：接口+多实现 + 注册机制 + 配置可替换

**源码证据**：
- Interface: `ProviderPlugin` 定义在 ^[src/plugins/types.ts:1051-1567]
- 注册 API: `api.registerProvider(provider: ProviderPlugin)` ^[src/plugins/types.ts:1937]
- 配置可替换: `models.providers.<id>` 在 `OpenClawConfig` 中 ^[src/config/types.ts:23]
- 多实现（≥30）:
  - `extensions/openai/` ^[extensions/openai/openclaw.plugin.json]
  - `extensions/anthropic/` ^[extensions/anthropic/]
  - `extensions/google/` ^[extensions/google/]
  - `extensions/groq/` ^[extensions/groq/]
  - `extensions/deepseek/` ^[extensions/deepseek/]
  - `extensions/mistral/` ^[extensions/mistral/]
  - `extensions/ollama/` ^[extensions/ollama/]
  - `extensions/openrouter/` ^[extensions/openrouter/]
  - `extensions/amazon-bedrock/` ^[extensions/amazon-bedrock/]
  - `extensions/github-copilot/` ^[extensions/github-copilot/]
  - `extensions/xai/` ^[extensions/xai/]
  - `extensions/perplexity/` ^[extensions/perplexity/]
  - `extensions/together/` ^[extensions/together/]
  - `extensions/fireworks/` ^[extensions/fireworks/]
  - `extensions/huggingface/` ^[extensions/huggingface/]
  - `extensions/alibaba/` ^[extensions/alibaba/]
  - `extensions/minimax/` ^[extensions/minimax/]
  - `extensions/moonshot/` ^[extensions/moonshot/]
  - `extensions/qwen/` ^[extensions/qwen/]
  - `extensions/qianfan/` ^[extensions/qianfan/]
  - `extensions/nvidia/` ^[extensions/nvidia/]
  - `extensions/vllm/` ^[extensions/vllm/]
  - `extensions/sglang/` ^[extensions/sglang/]
  - `extensions/volcengine/` ^[extensions/volcengine/]
  - `extensions/stepfun/` ^[extensions/stepfun/]
  - `extensions/zai/` ^[extensions/zai/]
  - `extensions/chutes/` ^[extensions/chutes/]
  - `extensions/byteplus/` ^[extensions/byteplus/]
  - `extensions/litellm/` ^[extensions/litellm/]
  - `extensions/cloudflare-ai-gateway/` ^[extensions/cloudflare-ai-gateway/]
  - `extensions/vercel-ai-gateway/` ^[extensions/vercel-ai-gateway/]
  - `extensions/microsoft/` ^[extensions/microsoft/]
  - `extensions/microsoft-foundry/` ^[extensions/microsoft-foundry/]
  - `extensions/venice/` ^[extensions/venice/]
  - `extensions/vydra/` ^[extensions/vydra/]
  - `extensions/arcee/` ^[extensions/arcee/]
  - `extensions/lobster/` ^[extensions/lobster/]
  - `extensions/synthetic/` ^[extensions/synthetic/]
  - `extensions/tlon/` ^[extensions/tlon/]

**下属 Entity**：Plugin System, Agent System, Config System, Secrets & Security

**判断置信度**：高（≥30 个 ProviderPlugin 实现，大量的 provider-specific hooks）

---

## Ontology 候选: Messaging Channel（消息通道）

**信号类型**：接口+多实现 + 注册机制 + 配置可替换

**源码证据**：
- Interface: `ChannelPlugin<ResolvedAccount>` ^[src/channels/plugins/types.plugin.ts:53]
- 注册 API: `api.registerChannel(registration: ChannelPlugin)` ^[src/plugins/types.ts:1896]
- 配置可替换: 每个 Channel 独立 `channels.<id>` 配置段
- 多实现（≥20）:
  - Core channels（in `src/`）: telegram, discord, slack, signal, imessage, whatsapp ^[AGENTS.md:20]
  - Extension channels: `extensions/matrix/`、`extensions/zalo/`、`extensions/zalouser/`、`extensions/irc/`、`extensions/msteams/`、`extensions/telegram/`（bundled）、`extensions/nostr/`、`extensions/nextcloud-talk/`、`extensions/synology-chat/`、`extensions/qqbot/`、`extensions/feishu/`、`extensions/line/`、`extensions/mattermost/`、`extensions/googlechat/`、`extensions/twitch/`、`extensions/xiaomi/`、`extensions/webhooks/`、`extensions/bluebubbles/`、`extensions/whatsapp/`（bundled）

**下属 Entity**：Channel System, Auto-Reply System, Gateway Server

**判断置信度**：高（≥20 个 ChannelPlugin 实现，30+ 适配器插槽）

---

## Ontology 候选: Memory / Knowledge Storage（记忆/知识存储）

**信号类型**：接口+多实现 + 注册机制 + 配置可替换

**源码证据**：
- Interface: `MemoryPluginCapability` ^[src/plugins/memory-state.ts]（通过 `api.registerMemoryCapability()` 独占 slot）
- Embedding Provider interface: `PluginEmbeddingProvider` ^[src/plugins/types.ts:798-806]
- Memory Engine interface: `engine.ts` 聚合导出 ^[packages/memory-host-sdk/src/engine.ts]
- 注册 API:
  - `api.registerMemoryCapability()` ^[src/plugins/types.ts:1978]
  - `api.registerMemoryEmbeddingProvider()` ^[src/plugins/types.ts:2007]
- 多实现:
  - 存储后端（≥3）: `extensions/memory-core/`（文件系统 + QMD）^[extensions/memory-core/openclaw.plugin.json:3]、`extensions/memory-lancedb/`（向量数据库）、`extensions/memory-wiki/`（wiki 标记文件）
  - 嵌入供应商（≥6）: OpenAI embeddings ^[packages/memory-host-sdk/src/host/embeddings-openai.ts]、Mistral ^[packages/memory-host-sdk/src/host/embeddings-mistral.ts]、Gemini ^[packages/memory-host-sdk/src/host/embeddings-gemini.test.ts]、Voyage ^[packages/memory-host-sdk/src/host/embeddings-voyage.ts]、Ollama ^[packages/memory-host-sdk/src/host/embeddings-ollama.ts]、Bedrock ^[packages/memory-host-sdk/src/host/embeddings-bedrock.test.ts]

**下属 Entity**：Memory Core, Memory Host SDK, memory-lancedb, memory-wiki

**判断置信度**：高（3 个存储后端 + 6+ 嵌入供应商，独立的 Memory Host SDK 包）

---

## Ontology 候选: Speech / Voice Synthesis（语音合成）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `SpeechProviderPlugin` ^[src/plugins/types.ts:1570-1589]
- 注册 API: `api.registerSpeechProvider()` ^[src/plugins/types.ts:1939]
- 多实现（≥3）:
  - `extensions/elevenlabs/`（ElevenLabs TTS）
  - `extensions/deepgram/`（Deepgram TTS）
  - `skills/openai-whisper/`、`skills/openai-whisper-api/`（Whisper STT）
  - `skills/sherpa-onnx-tts/`（本地 ONNX TTS）
- 配置驱动选择：`autoSelectOrder` 自动选择已配置的 provider ^[src/plugins/types.ts:1574]

**下属 Entity**：Speech Core

**判断置信度**：高（≥3 个 provider 实现，明确的统一接口）

---

## Ontology 候选: Image Generation（图片生成）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `ImageGenerationProvider` ^[src/image-generation/types.ts]
- 注册 API: `api.registerImageGenerationProvider()` ^[src/plugins/types.ts:1947]
- Core abstraction: `extensions/image-generation-core/` ^[extensions/image-generation-core/]
- 多实现（≥3）:
  - `extensions/fal/`（Fal.ai）
  - `extensions/comfy/`（ComfyUI）
  - `extensions/runway/`（RunwayML）

**下属 Entity**：Image Generation Core

**判断置信度**：中（≥3 个实现，独立 core 包）

---

## Ontology 候选: Video Generation（视频生成）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `VideoGenerationProvider` ^[src/video-generation/types.ts]
- 注册 API: `api.registerVideoGenerationProvider()` ^[src/plugins/types.ts:1949]
- Core abstraction: `extensions/video-generation-core/`
- 多实现（≥2）:
  - `extensions/runway/`
  - `extensions/fal/`

**下属 Entity**：Video Generation Core

**判断置信度**：中（≥2 个实现）

---

## Ontology 候选: Media Understanding（媒体理解/视觉分析）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `MediaUnderstandingProvider` ^[src/media-understanding/types.ts]
- 注册 API: `api.registerMediaUnderstandingProvider()` ^[src/plugins/types.ts:1945]
- Core abstraction: `extensions/media-understanding-core/`
- 多实现（≥2）: Google Gemini Vision, OpenAI Vision 等

**下属 Entity**：Media Understanding Core

**判断置信度**：中（独立接口 + 注册机制，2+ 实现）

---

## Ontology 候选: Web Search（网页搜索）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `WebSearchProviderPlugin` ^[src/plugins/web-provider-types.ts:10]
- 注册 API: `api.registerWebSearchProvider()` ^[src/plugins/types.ts:1954]
- 多实现（≥4）:
  - `extensions/brave/`（Brave Search）
  - `extensions/tavily/`（Tavily）
  - `extensions/searxng/`（SearXNG）
  - `extensions/duckduckgo/`（DuckDuckGo）

**下属 Entity**：Web Search Providers

**判断置信度**：高（≥4 个实现，独立接口）

---

## Ontology 候选: Web Fetch（网页抓取）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `WebFetchProviderPlugin` ^[src/plugins/web-provider-types.ts:10]
- 注册 API: `api.registerWebFetchProvider()` ^[src/plugins/types.ts:1953]
- 多实现（≥2）:
  - `extensions/firecrawl/`（Firecrawl）
  - `extensions/exa/`（Exa）

**下属 Entity**：Web Fetch Providers

**判断置信度**：中（≥2 个实现）

---

## Ontology 候选: Agent Harness / Runtime（Agent 运行时嵌入）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `AgentHarness` ^[src/agents/harness/types.ts:30-38]
- 注册 API: `api.registerAgentHarness(harness: AgentHarness)` ^[src/plugins/types.ts:1976]
- 多实现（≥3）:
  - Embedded Pi Agent（默认运行时）^[src/agents/pi-embedded.ts]
  - `extensions/kilocode/`（Kilo Code agent）
  - `extensions/opencode/`（OpenCode agent）
  - `extensions/opencode-go/`（OpenCode Go）
  - `extensions/openshell/`（OpenShell agent）
  - `extensions/codex/`（Codex agent）
  - `extensions/kimi-coding/`（Kimi Coding agent）
  - `extensions/copilot-proxy/`（GitHub Copilot proxy）

**下属 Entity**：Agent System

**判断置信度**：高（≥8 个 harness 实现，标准化接口 supports/runAttempt/compact/reset/dispose）

---

## Ontology 候选: Realtime Transcription（实时语音转文字）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `RealtimeTranscriptionProviderPlugin` ^[src/plugins/types.ts:1596-1606]
- 注册 API: `api.registerRealtimeTranscriptionProvider()` ^[src/plugins/types.ts:1941]
- 多实现（≥2）: `extensions/deepgram/`（默认）、其他 STT providers

**下属 Entity**：（目前无独立 core 包，直接注册）

**判断置信度**：低（接口定义清晰但仅 1-2 个实现）

---

## Ontology 候选: Realtime Voice（实时语音对话）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `RealtimeVoiceProviderPlugin` ^[src/plugins/types.ts:1613-1625]
- 注册 API: `api.registerRealtimeVoiceProvider()` ^[src/plugins/types.ts:1943]

**下属 Entity**：（目前无独立 core 包，直接注册）

**判断置信度**：低（接口清晰但实现较少）

---

## Ontology 候选: Context Engine（上下文引擎）

**信号类型**：接口 + 注册机制（独占 slot）

**源码证据**：
- Interface: `ContextEngineFactory` ^[src/context-engine/registry.js]
- 注册 API: `api.registerContextEngine(id, factory)` ^[src/plugins/types.ts:1967]（独占 slot）
- PluginKind includes `"context-engine"` ^[src/plugins/plugin-kind.types.ts:1]

**下属 Entity**：Context Engine

**判断置信度**：低（独占 slot，仅 1 个活跃实现，但接口定义清晰）

---

## Ontology 候选: Gateway Protocol（控制平面协议）

**信号类型**：独立包/目录 + 对外类型导出

**源码证据**：
- 独立目录：`src/gateway/protocol/` ^[src/gateway/protocol/]
- Schema 按域拆分：agent, channels, config, cron, devices, exec-approvals, nodes, sessions, push, secrets, snapshot, wizard, protocol-schemas ^[src/gateway/protocol/schema.ts:1-20]
- 双版本（类型 + AJV 验证器）^[src/gateway/protocol/index.ts:299-510]
- `PROTOCOL_VERSION` 标记有线格式版本 ^[src/gateway/protocol/index.ts:190]
- 被所有客户端消费（CLI, Control UI, iOS, Android, macOS）

**下属 Entity**：Gateway Server, Gateway Protocol, CLI, App Platforms

**判断置信度**：高（独立目录，30+ 类型 schema，所有客户端共享的单一有线合约）

---

## Ontology 候选: Plugin Extension Contract（插件扩展合约）

**信号类型**：独立包导出 + 注册机制

**源码证据**：
- 独立 npm 包：`packages/plugin-sdk/` ^[packages/plugin-sdk/package.json]
- 独立 npm 包：`packages/plugin-package-contract/` ^[packages/plugin-package-contract/src/index.ts]
- 公共合约文件：`scripts/lib/plugin-sdk-entrypoints.json`（枚举所有合法子路径）^[scripts/lib/plugin-sdk-entrypoints.json]
- `OpenClawPluginApi` 提供 30+ 标准注册方法 ^[src/plugins/types.ts:1867-2017]

**下属 Entity**：Plugin SDK, Plugin System

**判断置信度**：高（独立 npm 包，明确的 public surface 策略，被 ~110 个扩展消费）

---

## Ontology 候选: Memory Engine（记忆引擎）

**信号类型**：独立包/目录 + 接口 + 多实现

**源码证据**：
- 独立 npm 包：`packages/memory-host-sdk/` ^[packages/memory-host-sdk/package.json]
- Interface: engine.ts 聚合重导出四个子引擎 ^[packages/memory-host-sdk/src/engine.ts]
- 多存储后端：memory-core（文件系统）^[extensions/memory-core/openclaw.plugin.json]、memory-lancedb、memory-wiki
- 多嵌入供应商：OpenAI, Mistral, Gemini, Voyage, Ollama, Bedrock ^[packages/memory-host-sdk/src/host/embeddings-*.ts]

**下属 Entity**：Memory Host SDK

**判断置信度**：高（独立包，标准接口，3+ 存储后端，6+ 嵌入后端）

---

## Ontology 候选: Browser Automation（浏览器自动化）

**信号类型**：独立包/目录 + 注册机制

**源码证据**：
- 独立 extension：`extensions/browser/` ^[extensions/browser/index.ts]
- 默认启用：`"enabledByDefault": true` ^[extensions/browser/openclaw.plugin.json:3]
- 专用 SDK 表面：`src/plugin-sdk/browser-*.ts`（browser-bridge, browser-cdp, browser-config, browser-control-auth, browser-maintenance, etc.）
- CDP 协议实现：^[extensions/browser/browser-cdp.ts]

**下属 Entity**：Browser Extension

**判断置信度**：高（独立包 + 专用 SDK 表面 + CDP 协议集成）

---

## Ontology 候选: Skills / Agent Capability Registry（技能/能力注册表）

**信号类型**：独立目录 + 注册机制

**源码证据**：
- 独立顶层目录：`skills/`（~52 个独立技能）
- Gateway 管理 API：SkillsBins, SkillsSearch, SkillsInstall, SkillsUpdate, SkillsDetail ^[src/gateway/protocol/schema.ts:14]
- 每个 Skill 是自包含的 markdown 指令文件 ^[skills/*/SKILL.md]

**下属 Entity**：Skills System

**判断置信度**：高（独立顶层目录，52+ 技能实例，完整的 Gateway API 管理面）

---

## Ontology 候选: Cron / Scheduled Automation（定时自动化）

**信号类型**：独立目录 + 注册机制

**源码证据**：
- 独立目录：`src/cron/`
- Gateway API：CronAdd, CronUpdate, CronRemove, CronList, CronRun, CronStatus ^[src/gateway/protocol/schema.ts:6]
- 配置驱动（cron 表达式字符串）^[extensions/memory-core/openclaw.plugin.json:18]
- 插件可以注册 cron 触发的行为（如 memory dreaming）^[extensions/memory-core/openclaw.plugin.json:14]

**下属 Entity**：Cron System

**判断置信度**：中（独立目录 + 完整的 Gateway API）

---

## Ontology 候选: Compaction / Conversation Compression（对话压缩）

**信号类型**：接口 + 注册机制

**源码证据**：
- Interface: `CompactionProvider` ^[src/plugins/compaction-provider.js]
- 注册 API: `api.registerCompactionProvider()` ^[src/plugins/types.ts:1972]
- Session compaction 基础设施：checkpoints, branching, restore ^[src/gateway/session-compaction-checkpoints.ts]
- Session life cycle state (compact, reset, delete, branch) ^[src/gateway/session-lifecycle-state.ts]

**下属 Entity**：Session Management

**判断置信度**：低（接口 + 注册机制定义清晰，但实现数较少）

---

## Ontology 候选: Cross-platform App（跨平台应用）

**信号类型**：独立目录

**源码证据**：
- 独立顶层目录：`apps/`（macOS, iOS, Android, shared）^[apps/]
- macOS：Sparkle 自动更新, Menu Bar, SwiftUI ^[apps/macos/]
- iOS：SwiftUI + Observation framework ^[apps/ios/]
- Android：Kotlin + Jetpack Compose + Gradle ^[apps/android/]

**下属 Entity**：App Platforms

**判断置信度**：高（3 个完全独立的原生应用，共享 Gateway Protocol）

---

## Ontology 候选: Device Pairing / Auth（设备配对与认证）

**信号类型**：独立目录 + 注册机制

**源码证据**：
- 独立目录：`src/pairing/`、独立 extension：`extensions/device-pair/`
- Gateway 协议：DevicePairList, DevicePairApprove, DevicePairReject, DevicePairRemove, DeviceTokenRotate, DeviceTokenRevoke ^[src/gateway/protocol/schema.ts:8]
- Node 配对协议：NodePairRequest, NodePairList, NodePairApprove, NodePairReject, NodePairVerify ^[src/gateway/protocol/index.ts:332-344]
- Mobile nodes 管理 ^[src/gateway/server-mobile-nodes.ts]

**下属 Entity**：Device Pairing

**判断置信度**：高（独立 extension + 12+ 协议 schema + 完整的审批流程）

---

## Ontology 候选: Music Generation（音乐生成）

**信号类型**：接口+多实现 + 注册机制

**源码证据**：
- Interface: `MusicGenerationProvider` ^[src/music-generation/types.ts]
- 注册 API: `api.registerMusicGenerationProvider()` ^[src/plugins/types.ts:1951]
- Core abstraction: `src/music-generation/`

**下属 Entity**：Music Generation（in src/）

**判断置信度**：低（接口 + 注册机制定义清晰，但实现较少）

---

## Ontology 候选: CLI Backend（命令行后端）

**信号类型**：接口 + 注册机制

**源码证据**：
- Interface: `CliBackendPlugin` ^[src/plugins/cli-backend.types.ts]
- 注册 API: `api.registerCliBackend()` ^[src/plugins/types.ts:1929]
- 多实现：内建 CLI 后端 + extension 可注册自定义后端

**下属 Entity**：CLI

**判断置信度**：低（接口定义存在但实现数较少）

---

## 孤立 Entity（未找到 Ontology 归属）

- **Config System**：全局基础设施，所有模块依赖但不属于单个能力域。没有可替换策略、没有多个实现、不属于任何注册接口的多态模式。

- **Infrastructure Utilities（`src/infra/`）**：纯工具函数集合，不属于接口驱动的能力域。

- **Secrets & Security**：安全审计基础设施，与所有 Ontology 节点都有交互但不属于单一能力域。Secret management 虽然可替换（env/file/secretRef）但没有抽象为独立接口+多实现模式。

- **Hooks System**：事件分发基础设施，是跨 Ontology 节点的横切关注点而非独立能力域。

- **Auto-Reply System**：Agent 回复分发逻辑，紧耦合于 Channel System，不独立形成能力域。

- **TUI / Control UI**：前端展示层，不属于后端能力域分类。

- **ACPs（Agent Communication Protocol）**：Spawning/sub-agent 通信协议。虽然独立但缺少多实现——目前只有一个内建实现。

- **MCP Integration**：Model Context Protocol 集成。虽然独立但缺少多实现——目前只有 HTTP bridge 一种集成方式。

---

## 同时匹配多个 Ontology 节点的 Entity

- **Speech Core**：同时属于 Speech Synthesis 和 Realtime Voice（因为 TTS 在两种场景共用）
- **Voice Call**：同时属于 Messaging Channel 和 Speech Synthesis（既是 channel 又消费 TTS/STT）
- **Memory Core**：同时属于 Memory/Knowledge Storage 和 Cron（因为 dreaming 依赖 cron scheduling）
- **Plugin SDK**：同时属于 Plugin Extension Contract（作为公共表面）和所有其他注册式 Ontology 节点（作为注册 API 的提供者）
- **Gateway Server**：同时属于 Gateway Protocol（消费协议）和 Device Pairing/Auth（作为配对审批的后端）以及几乎所有运行时 Ontology 节点（作为宿主进程）
