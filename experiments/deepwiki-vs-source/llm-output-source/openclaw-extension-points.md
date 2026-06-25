---
repo: openclaw
dimension: extension-points
dimensions_version: v1.0
generated: 2026-06-14
---

# OpenClaw 扩展点 (Extension Points) 维度知识

---

## 1. 插件系统 (Plugin System) -- 核心扩展机制

### 1.1 插件入口与导出契约

OpenClaw 的插件系统定义了统一的模块导出契约，通过 `OpenClawPluginModule` 类型约束插件模块可以导出 `OpenClawPluginDefinition` 对象或接收 `OpenClawPluginApi` 的注册函数。`OpenClawPluginDefinition` 是主合约，包含 `id`、`name`、`description`、`configSchema`、`register(api)` 和可选的 `activate(api)` 生命周期方法。^[src/plugins/types.ts:1829-1841]

插件提供标准入口辅助函数 `definePluginEntry()`（来自 `openclaw/plugin-sdk/plugin-entry`），非 Channel 类插件统一使用此函数包装。Channel 插件另有专用入口 `defineChannelPluginEntry()`（来自 `openclaw/plugin-sdk/core`）。Provider 类插件可使用更高阶的 `defineSingleProviderPluginEntry()`（来自 `openclaw/plugin-sdk/provider-entry`）。^[src/plugin-sdk/plugin-entry.ts:149-200] ^[src/plugin-sdk/provider-entry.ts:100-168]

插件模块可以是以下任一形式：^[src/plugins/types.ts:1843-1845]

- 导出 `OpenClawPluginDefinition` 对象（包含 `id`、`name`、`register` 等字段）
- 导出函数 `(api: OpenClawPluginApi) => void | Promise<void>`

### 1.2 OpenClawPluginApi -- 插件注册 API 全景

`OpenClawPluginApi` 是注入到每个插件 `register()` 方法的中央注册接口，提供约 40 个注册方法，覆盖全部扩展能力：^[src/plugins/types.ts:1867-2017]

**文本推理与渠道**：
- `registerProvider(provider: ProviderPlugin)` -- 注册模型供应商 ^[src/plugins/types.ts:1937]
- `registerChannel(registration)` -- 注册消息渠道 ^[src/plugins/types.ts:1896]
- `registerCliBackend(backend: CliBackendPlugin)` -- 注册 CLI 推理后端 ^[src/plugins/types.ts:1929]
- `registerAgentHarness(harness: AgentHarness)` -- 注册 Agent 执行容器 ^[src/plugins/types.ts:1976]

**钩子系统**：
- `registerHook(events, handler, opts)` -- 注册内部钩子处理器 ^[src/plugins/types.ts:1889-1893]
- `on(hookName, handler, opts)` -- 注册插件生命周期钩子（29 个精细粒度钩子）^[src/plugins/types.ts:2012-2016]

**工具与命令**：
- `registerTool(tool, opts)` -- 注册 Agent 工具 ^[src/plugins/types.ts:1885-1888]
- `registerCommand(command)` -- 注册自定义命令（绕过 LLM，优先于内置命令）^[src/plugins/types.ts:1965]
- `registerCli(registrar, opts)` -- 注册 CLI 命令扩展树 ^[src/plugins/types.ts:1909-1923]

**能力供应商**：
- `registerSpeechProvider(provider)` -- 语音合成供应商 ^[src/plugins/types.ts:1939]
- `registerRealtimeTranscriptionProvider(provider)` -- 实时转录供应商 ^[src/plugins/types.ts:1941]
- `registerRealtimeVoiceProvider(provider)` -- 实时语音供应商 ^[src/plugins/types.ts:1943]
- `registerMediaUnderstandingProvider(provider)` -- 媒体理解供应商 ^[src/plugins/types.ts:1945]
- `registerImageGenerationProvider(provider)` -- 图像生成供应商 ^[src/plugins/types.ts:1947]
- `registerVideoGenerationProvider(provider)` -- 视频生成供应商 ^[src/plugins/types.ts:1949]
- `registerMusicGenerationProvider(provider)` -- 音乐生成供应商 ^[src/plugins/types.ts:1951]
- `registerWebFetchProvider(provider)` -- 网页抓取供应商 ^[src/plugins/types.ts:1953]
- `registerWebSearchProvider(provider)` -- 网页搜索供应商 ^[src/plugins/types.ts:1955]

**记忆系统** (Memory)：^[src/plugins/types.ts:1978-2009]
- `registerMemoryCapability(capability)` -- 记忆核心能力（独占槽位，aggregates promptBuilder/flushPlanResolver/runtime）
- `registerMemoryPromptSection(builder)` -- 记忆提示段落构建器（独占槽位，deprecated，合并入 registerMemoryCapability）
- `registerMemoryPromptSupplement(builder)` -- 附加记忆提示段落（非独占，多个插件可共存）
- `registerMemoryCorpusSupplement(supplement)` -- 附加记忆语料源（非独占）
- `registerMemoryFlushPlan(resolver)` -- 记忆刷新计划解析器（独占，deprecated）
- `registerMemoryRuntime(runtime)` -- 记忆运行时适配器（独占，deprecated）
- `registerMemoryEmbeddingProvider(adapter)` -- 记忆嵌入向量供应商（非独占）

**上下文引擎** (Context Engine)：^[src/plugins/types.ts:1967-1970]
- `registerContextEngine(id, factory)` -- 注册上下文引擎（独占槽位，替换默认上下文管理策略）

**HTTP 与 Gateway**：^[src/plugins/types.ts:1894-1908]
- `registerHttpRoute(params)` -- 注册 HTTP 路由端点
- `registerGatewayMethod(method, handler, opts)` -- 注册 Gateway RPC 方法

**基础设施与配置**：^[src/plugins/types.ts:1924-1935]
- `registerService(service)` -- 注册后台服务（start/stop 生命周期）
- `registerReload(registration)` -- 注册配置热重载监听
- `registerConfigMigration(migrate)` -- 注册配置迁移（可在插件运行时加载前执行）
- `registerAutoEnableProbe(probe)` -- 注册自动启用探测
- `registerTextTransforms(transforms)` -- 注册文本替换（input/output 双向）
- `registerNodeHostCommand(command)` -- 注册节点宿主机命令
- `registerSecurityAuditCollector(collector)` -- 注册安全审计收集器

**交互**：^[src/plugins/types.ts:1956-1959]
- `registerInteractiveHandler(registration)` -- 注册交互式消息处理器
- `onConversationBindingResolved(handler)` -- 注册会话绑定解析回调

API 还提供 `runtime: PluginRuntime`（受信任的进程内运行时，包含 subagent 操作和 channel 操作）和 `logger: PluginLogger` 等上下文属性。^[src/plugins/types.ts:1872-1884]

### 1.3 插件发现与加载

插件发现通过 `discoverOpenClawPlugins()` 函数实现，扫描以下来源的 `openclaw.plugin.json` 清单文件：^[src/plugins/discovery.ts:24-54]

1. **工作空间路径** (`workspaceDir`) -- 用户级插件
2. **配置的额外路径** (`extraPaths`) -- 显式声明路径
3. **extensions 目录** -- 内置捆绑插件目录 ^[extensions/AGENTS.md:1-3]
4. **node_modules** -- npm 安装的第三方插件包

发现结果缓存在短期缓存中（默认 1000ms），可通过 `OPENCLAW_PLUGIN_DISCOVERY_CACHE_MS` 调整或 `OPENCLAW_DISABLE_PLUGIN_DISCOVERY_CACHE=1` 禁用。^[src/plugins/discovery.ts:61-91]

每个扫描到的候选插件包含 `idHint`、`source`（入口文件路径）、`rootDir`、`origin`（来源标识）、`format`（`"openclaw"` 或 `"bundle"`）、`packageName` 等信息。^[src/plugins/discovery.ts:38-54]

插件加载通过 `loadBundledPlugins()` 主函数进行，支持多种加载模式：^[src/plugins/loader.ts:90-114]

- `"full"` -- 完整加载，运行 register/activate，注册所有能力
- `"validate"` -- 仅校验清单而不执行插件代码
- `"setup-only"` -- 仅加载 setup 表面（轻量）
- `"cli-metadata"` -- 仅加载 CLI 元数据

加载使用 `jiti` 作为即时编译（JIT）加载器，支持 TypeScript 和 ESM/CJS 插件模块。插件模块通过 SDK 别名机制从 `openclaw/plugin-sdk/*` 子路径导入，边界规则强制插件不得直接导入 `src/**` 核心内部代码。^[extensions/AGENTS.md:26-50]

`PluginLoadFailureError` 和 `PluginLoadReentryError` 分别处理加载失败和重入检测异常。^[src/plugins/loader.ts:123-147]

### 1.4 插件清单 (Plugin Manifest)

每个插件目录根需要一个 `openclaw.plugin.json` 清单文件，完整清单类型包含以下字段：^[src/plugins/manifest.ts:134-190]

| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | `string` | 唯一插件标识 |
| `configSchema` | `Record<string, unknown>` | 插件配置 JSON Schema |
| `enabledByDefault` | `boolean?` | 默认启用 |
| `legacyPluginIds` | `string[]?` | 旧版插件 ID 映射 |
| `autoEnableWhenConfiguredProviders` | `string[]?` | 当这些供应商被引用时自动启用此插件 |
| `kind` | `PluginKind \| PluginKind[]?` | 插件类型：`"memory"` \| `"context-engine"` ^[src/plugins/plugin-kind.types.ts:1] |
| `providers` | `string[]?` | 拥有的模型供应商 ID 列表 |
| `channels` | `string[]?` | 拥有的渠道 ID 列表 |
| `modelSupport` | `{ modelPrefixes?, modelPatterns? }?` | 模型前缀/正则匹配（用于快捷模型引用如 `claude-`） |
| `cliBackends` | `string[]?` | CLI 推理后端 ID 列表 |
| `providerAuthEnvVars` | `Record<string, string[]>?` | 供应商认证环境变量映射 |
| `providerAuthAliases` | `Record<string, string>?` | 供应商认证别名 |
| `providerAuthChoices` | `PluginManifestProviderAuthChoice[]?` | 认证选择器元数据（浮现在 CLI/UI 上） |
| `channelEnvVars` | `Record<string, string[]>?` | 渠道环境变量映射 |
| `contracts` | `PluginManifestContracts?` | 静态能力拥有权快照（内存嵌入/语音/媒体理解等） |
| `activation` | `PluginManifestActivation?` | 激活触发器（onProviders/onCommands/onChannels/onRoutes/onCapabilities） |
| `setup` | `PluginManifestSetup?` | 安装/配置元数据（providers/cliBackends/configMigrations） |
| `skills` | `string[]?` | 拥有的技能 ID 列表 |
| `name` | `string?` | 插件显示名称 |
| `description` | `string?` | 插件描述 |
| `version` | `string?` | 插件版本 |
| `uiHints` | `Record<string, PluginConfigUiHint>?` | 配置 UI 提示 |
| `configContracts` | `PluginManifestConfigContracts?` | 配置合约（dangerousFlags/secretInputs/compatibilityMigrationPaths） |
| `channelConfigs` | `Record<string, PluginManifestChannelConfig>?` | 渠道配置 Schema |

`PluginManifestContracts` 包含 10 种能力供应商的静态拥有权声明：^[src/plugins/manifest.ts:192-204]

- `memoryEmbeddingProviders` -- 记忆嵌入供应商 ID
- `speechProviders` -- 语音合成供应商 ID
- `realtimeTranscriptionProviders` -- 实时转录供应商 ID
- `realtimeVoiceProviders` -- 实时语音供应商 ID
- `mediaUnderstandingProviders` -- 媒体理解供应商 ID
- `imageGenerationProviders` -- 图像生成供应商 ID
- `videoGenerationProviders` -- 视频生成供应商 ID
- `musicGenerationProviders` -- 音乐生成供应商 ID
- `webFetchProviders` -- 网页抓取供应商 ID
- `webSearchProviders` -- 网页搜索供应商 ID
- `tools` -- 工具 ID 列表

以 Anthropic 插件清单为例：^[extensions/anthropic/openclaw.plugin.json:1-47]

```json
{
  "id": "anthropic",
  "enabledByDefault": true,
  "providers": ["anthropic"],
  "modelSupport": { "modelPrefixes": ["claude-"] },
  "cliBackends": ["claude-cli"],
  "providerAuthEnvVars": { "anthropic": ["ANTHROPIC_OAUTH_TOKEN", "ANTHROPIC_API_KEY"] },
  "providerAuthChoices": [
    { "provider": "anthropic", "method": "cli", "choiceId": "anthropic-cli", ... },
    { "provider": "anthropic", "method": "api-key", "choiceId": "apiKey", ... }
  ],
  "contracts": { "mediaUnderstandingProviders": ["anthropic"] },
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```

### 1.5 注册中心 (Plugin Registry)

插件注册中心 `PluginRegistry` 维护所有已加载插件的状态，包含：^[src/plugins/registry.ts:1-68]

- `plugins: PluginRecord[]` -- 插件记录列表（ID、状态、错误、根源等）
- 全局单例管理（`getActivePluginRegistry()` / `setActivePluginRegistry()`）^[src/plugins/runtime.ts:63-68]
- 插件注册通过 `buildPluginApi()` 创建 API 实例，然后调用各注册 handler 注入到全局注册表中 ^[src/plugins/api-builder.ts:1-61]

注册类型包括 `PluginToolRegistration`、`PluginProviderRegistration`、`PluginChannelRegistration`、`PluginHookRegistration`、`PluginHttpRouteRegistration`、`PluginCliRegistration`、`PluginSpeechProviderRegistration` 等 20+ 种注册记录类型。^[src/plugins/registry-types.ts:48-150]

### 1.6 独占槽位 (Exclusive Slots)

系统通过槽位（slots）机制管理互斥的插件能力。当前有两种插件类型对应独占槽位：^[src/plugins/slots.ts:12-15]

- `kind: "memory"` -- 槽位键 `"memory"`（默认值: `"memory-core"`）
- `kind: "context-engine"` -- 槽位键 `"contextEngine"`（默认值: `"legacy"`）

选择独占插件时，`applyExclusiveSlotSelection()` 自动禁用之前拥有该槽位的其他插件，并生成变更警告。^[src/plugins/slots.ts:76-159]

---

## 2. 钩子系统 (Hook System) -- 生命周期拦截

### 2.1 双轨钩子架构

OpenClaw 有两套平行的钩子系统：

**内部钩子 (Internal Hooks)** -- 传统事件驱动系统，支持类型化事件 (`command` / `session` / `agent` / `gateway` / `message`)，每个事件包含 `type`、`action`、`sessionKey`、`context` (Record<string, unknown>)、`timestamp` 以及 `messages` (返回消息数组)。^[src/hooks/internal-hook-types.ts:1-18]

钩子加载通过 `loadInternalHooks()` 函数进行：^[src/hooks/loader.ts:79-101]

1. 钩子默认启用（除非 `cfg.hooks.internal.enabled === false`）
2. 从工作空间目录发现钩子条目（`loadWorkspaceHookEntries()`）
3. 从 managed hooks 目录加载
4. 从 bundled hooks 目录加载（`boot-md`、`bootstrap-extra-files`、`command-logger`、`session-memory`）^[src/hooks/bundled/]
5. 加载旧版配置 handler（向后兼容）
6. 对工作空间和管理钩子发出信任警告

**插件钩子 (Plugin Hooks)** -- 新一代精细粒度钩子，通过 `api.on(hookName, handler)` 注册，共 29 个钩子名称，通过 `PluginHookHandlerMap` 提供类型安全的 handler 签名。^[src/plugins/hook-types.ts:55-116] ^[src/plugins/hook-types.ts:568-685]

### 2.2 全部 29 个插件钩子

钩子按生命周期阶段分组：

**Agent 模型与提示阶段**：^[src/plugins/hook-types.ts:55-61]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `before_model_resolve` | modelOverride / providerOverride | `PluginHookAgentContext` | LLM 模型选择覆盖 ^[src/plugins/hook-before-agent-start.types.ts:6-12] |
| `before_prompt_build` | systemPrompt / prependContext / appendSystemContext | `PluginHookAgentContext` | System Prompt 注入与修改 ^[src/plugins/hook-before-agent-start.types.ts:15-34] |
| `before_agent_start` | 模型+提示双覆盖（兼容旧版） | `PluginHookAgentContext` | 组合 before_model_resolve + before_prompt_build ^[src/plugins/hook-before-agent-start.types.ts:53-60] |

**Agent 回复阶段**：^[src/plugins/hook-types.ts:61-62]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `before_agent_reply` | handled / reply / reason | `PluginHookAgentContext` | 回复前拦截/替换（如个性化改写）^[src/plugins/hook-types.ts:153-161] |

**LLM 调用阶段**：^[src/plugins/hook-types.ts:63-65]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `llm_input` | 无（纯观察） | `PluginHookAgentContext` | 观察请求内容（system prompt、messages、images）^[src/plugins/hook-types.ts:163-172] |
| `llm_output` | 无（纯观察） | `PluginHookAgentContext` | 观察响应内容（assistant texts、usage）^[src/plugins/hook-types.ts:174-188] |

**Agent 生命周期阶段**：^[src/plugins/hook-types.ts:65-67]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `agent_end` | 无（纯观察） | `PluginHookAgentContext` | Agent 运行结束（messages、success、error、durationMs）^[src/plugins/hook-types.ts:190-195] |

**压缩与重置阶段**：^[src/plugins/hook-types.ts:67-69]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `before_compaction` | 无（纯观察） | `PluginHookAgentContext` | 压缩前观察（messageCount、tokenCount）^[src/plugins/hook-types.ts:197-203] |
| `after_compaction` | 无（纯观察） | `PluginHookAgentContext` | 压缩后观察（compactedCount）^[src/plugins/hook-types.ts:211-216] |
| `before_reset` | 无（纯观察） | `PluginHookAgentContext` | 会话重置前观察 ^[src/plugins/hook-types.ts:205-209] |

**入站与分发阶段**：^[src/plugins/hook-types.ts:69-74]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `inbound_claim` | handled: boolean | `PluginHookInboundClaimContext` | 入站消息认领（插件可声明处理权）^[src/plugins/hook-types.ts:218-220] |
| `before_dispatch` | handled / text | `PluginHookBeforeDispatchContext` | 消息分发前修改/拦截 ^[src/plugins/hook-types.ts:222-243] |
| `reply_dispatch` | handled / queuedFinal / counts | `PluginHookReplyDispatchContext` | 回复分发控制 ^[src/plugins/hook-types.ts:245-280] |

**消息阶段**：^[src/plugins/hook-types.ts:74-77]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `message_received` | 无（纯观察） | `PluginHookMessageContext` | 消息接收观察 |
| `message_sending` | 修改/阻止发送 | `PluginHookMessageContext` | 消息发送前修改 |
| `message_sent` | 无（纯观察） | `PluginHookMessageContext` | 消息发送后观察 |

**工具调用阶段**：^[src/plugins/hook-types.ts:77-80]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `before_tool_call` | 参数修改/阻止/审批 | `PluginHookToolContext` | 工具调用前拦截（可修改参数或审批）^[src/plugins/hook-types.ts:291-298+] |
| `after_tool_call` | 无（纯观察） | `PluginHookToolContext` | 工具调用后观察 |
| `tool_result_persist` | 持久化修改（同步钩子） | `PluginHookToolResultPersistContext` | 工具结果持久化前修改 |
| `before_message_write` | 消息过滤（同步钩子） | 最小上下文 | 消息写入前过滤 ^[src/plugins/hook-types.ts:642-645] |

**会话阶段**：^[src/plugins/hook-types.ts:80-82]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `session_start` | 无（纯观察） | `PluginHookSessionContext` | 会话开始 |
| `session_end` | 无（纯观察） | `PluginHookSessionContext` | 会话结束 |

**子 Agent 阶段**：^[src/plugins/hook-types.ts:82-86]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `subagent_spawning` | 阻止/修改 | `PluginHookSubagentContext` | 子 Agent 派生前 |
| `subagent_delivery_target` | 目标覆盖 | `PluginHookSubagentContext` | 子 Agent 交付目标选择 |
| `subagent_spawned` | 无（纯观察） | `PluginHookSubagentContext` | 子 Agent 已派生 |
| `subagent_ended` | 无（纯观察） | `PluginHookSubagentContext` | 子 Agent 结束 |

**Gateway 阶段**：^[src/plugins/hook-types.ts:86-88]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `gateway_start` | 无（纯观察） | `PluginHookGatewayContext` | Gateway 启动 |
| `gateway_stop` | 无（纯观察） | `PluginHookGatewayContext` | Gateway 停止 |

**安装阶段**：^[src/plugins/hook-types.ts:88-89]
| 钩子名称 | 可修改 | 上下文 | 用途 |
|---|---|---|---|
| `before_install` | 安装修改/阻止 | `PluginHookBeforeInstallContext` | 插件安装前拦截 |

`PLUGIN_HOOK_NAMES` 常量包含所有 29 个钩子名称，`isPluginHookName()` 提供运行时类型守卫。^[src/plugins/hook-types.ts:86-126]

Hook 注册类型：^[src/plugins/hook-types.ts:687-693]

```typescript
type PluginHookRegistration<K extends PluginHookName> = {
  pluginId: string;
  hookName: K;
  handler: PluginHookHandlerMap[K];
  priority?: number;  // 数字越大越先执行
  source: string;
};
```

### 2.3 钩子执行模型

钩子按优先级降序排列后执行：^[src/plugins/hooks.ts:186-193]

- **修改型钩子**（如 `before_prompt_build`、`before_agent_start`）支持 `mergeResults` 累积和 `shouldStop` 提前终止。系统提示注入的四个字段 (`systemPrompt` / `prependContext` / `prependSystemContext` / `appendSystemContext`) 通过 `PLUGIN_PROMPT_MUTATION_RESULT_FIELDS` 常量定义。^[src/plugins/hook-before-agent-start.types.ts:36-41]
- **拦截型钩子**（如 `before_agent_reply`、`inbound_claim`、`before_dispatch`）返回 `handled: true` 可阻止后续处理链。
- **同步钩子**（`tool_result_persist`、`before_message_write`）必须同步执行，不支持异步返回。^[src/plugins/hooks.ts:177-181]
- 钩子错误默认 "fail-open"（容错，捕获并记录错误后继续执行后续钩子），可通过 `failurePolicyByHook` 为特定钩子配置 "fail-closed"（遇错即停）。^[src/plugins/hooks.ts:134-145]

全局钩子运行器 `GlobalHookRunnerRegistry` 和 `HookRunnerRegistry` 通过 `initializeGlobalHookRunner()` 初始化，`getHooksForName()` 和 `getHooksForNameAndPlugin()` 提供按钩子名和插件 ID 的查询。^[src/plugins/hooks.ts:186-199]

---

## 3. Provider 插件 -- 模型供应商扩展

### 3.1 ProviderPlugin 接口全景

`ProviderPlugin` 是文本推理能力供应商的完整接口，包含 40+ 个可选钩子方法，分组如下：

**认证 (Auth)**：^[src/plugins/types.ts:1051-1567]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `auth` | `ProviderAuthMethod[]` | 认证方法列表（oauth/api_key/token/device_code/custom） |
| `prepareRuntimeAuth` | `(ctx) => Promise<ProviderPreparedRuntimeAuth>` | 运行时凭证交换（如 GitHub token -> 短期 API key） |
| `resolveUsageAuth` | `(ctx) => ProviderResolvedUsageAuth` | 用量配额认证解析 |
| `resolveSyntheticAuth` | `(ctx) => ProviderSyntheticAuthResult` | 无密钥认证（自托管/本地场景） |
| `resolveExternalAuthProfiles` | `(ctx) => ProviderExternalAuthProfile[]` | 外部工具管理的凭证发现 |
| `refreshOAuth` | `(cred) => Promise<OAuthCredential>` | OAuth 令牌刷新 |
| `formatApiKey` | `(cred) => string` | 凭证格式化（如提取 bearer token） |
| `resolveConfigApiKey` | `(ctx) => string` | 从配置解析 API key（AWS/GCP marker 场景） |
| `buildMissingAuthMessage` | `(ctx) => string` | 自定义缺失认证提示 |
| `buildAuthDoctorHint` | `(ctx) => string` | 认证修复建议 |
| `deprecatedProfileIds` | `string[]` | 旧版 Profile ID（用于 doctor 迁移） |
| `oauthProfileIdRepairs` | `ProviderOAuthProfileIdRepair[]` | OAuth Profile ID 迁移 |

**模型目录 (Catalog)**：^[src/plugins/types.ts:1077-1138]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `catalog.run` | `(ctx) => ProviderCatalogResult` | 返回模型供应商配置 |
| `resolveDynamicModel` | `(ctx) => ProviderRuntimeModel` | 动态模型 ID 解析（同步，廉价） |
| `prepareDynamicModel` | `(ctx) => Promise<void>` | 动态模型预取（异步，可联网） |
| `augmentModelCatalog` | `(ctx) => ModelCatalogEntry[]` | 最终目录增强（追加行） |
| `suppressBuiltInModel` | `(ctx) => { suppress, errorMessage }` | 隐藏过期/不支持的模型 |
| `normalizeModelId` | `(ctx) => string` | 模型 ID 标准化（provider-owned alias cleanup） |
| `normalizeResolvedModel` | `(ctx) => ProviderRuntimeModel` | 模型解析后标准化（API ID 替换、base URL 修复、compat flags） |
| `contributesResolvedModelCompat` | `(ctx) => Partial<ModelCompatConfig>` | 跨传输模型兼容性贡献 |
| `preferRuntimeResolvedModel` | `(ctx) => boolean` | 是否偏好运行时解析的模型 |

**配置标准化**：^[src/plugins/types.ts:1146-1172]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `normalizeConfig` | `(ctx) => ModelProviderConfig` | 供应商配置标准化（baseUrl/model-id cleanup） |
| `normalizeTransport` | `(ctx) => { api, baseUrl }` | 传输族标准化 |
| `applyNativeStreamingUsageCompat` | `(ctx) => ModelProviderConfig` | 原生流式用量兼容 |
| `applyConfigDefaults` | `(ctx) => OpenClawConfig` | 全局配置默认值注入 |

**传输 (Transport)**：^[src/plugins/types.ts:1241-1278]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `createStreamFn` | `(ctx) => StreamFn` | 完全自定义传输实现 |
| `wrapStreamFn` | `(ctx) => StreamFn` | Stream 包装器（provider-specific payload/header mutations） |
| `prepareExtraParams` | `(ctx) => Record<string, unknown>` | 额外请求参数准备 |
| `resolveTransportTurnState` | `(ctx) => ProviderTransportTurnState` | 传输回合状态（headers/metadata per turn） |
| `resolveWebSocketSessionPolicy` | `(ctx) => ProviderWebSocketSessionPolicy` | WebSocket 会话策略（headers + cooldown） |

**重放/压缩 (Replay/Compaction)**：^[src/plugins/types.ts:1185-1223]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `buildReplayPolicy` | `(ctx) => ProviderReplayPolicy` | 重放策略（sanitizeMode/toolCallIdMode/dropThinking/validateTurns 等） |
| `sanitizeReplayHistory` | `(ctx) => AgentMessage[]` | 重放历史清洗（provider-specific rewrites） |
| `validateReplayTurns` | `(ctx) => AgentMessage[]` | 最终重放回合校验 |
| `normalizeToolSchemas` | `(ctx) => AnyAgentTool[]` | 工具 Schema 标准化（transport-family keyword cleanup） |
| `inspectToolSchemas` | `(ctx) => ProviderToolSchemaDiagnostic[]` | 工具 Schema 诊断 |

**推理行为 (Inference)**：^[src/plugins/types.ts:1230-1429]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `resolveReasoningOutputMode` | `(ctx) => "native" \| "tagged"` | 推理输出模式 |
| `resolveDefaultThinkingLevel` | `(ctx) => "off" \| "minimal" \| ... \| "adaptive"` | 默认思考级别 |
| `isBinaryThinking` | `(ctx) => boolean` | 二进制思考切换 |
| `supportsXHighThinking` | `(ctx) => boolean` | xhigh 思考支持 |
| `resolveSystemPromptContribution` | `(ctx) => ProviderSystemPromptContribution` | System Prompt 贡献 |
| `transformSystemPrompt` | `(ctx) => string` | System Prompt 最终转换（compatibility rewrites） |
| `textTransforms` | `PluginTextTransforms` | 双向文本替换（input: prompt/message, output: assistant text） |

**故障转移与诊断**：^[src/plugins/types.ts:1334-1389]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `classifyFailoverReason` | `(ctx) => FailoverReason` | 故障转移错误分类 |
| `matchesContextOverflowError` | `(ctx) => boolean` | 上下文溢出匹配 |
| `isCacheTtlEligible` | `(ctx) => boolean` | 缓存 TTL 资格判断 |
| `buildUnknownModelHint` | `(ctx) => string` | 未知模型提示 |
| `isModernModelRef` | `(ctx) => boolean` | 现代模型判断（for live profile/smoke filters） |

**用量与嵌入**：^[src/plugins/types.ts:1325-1327] ^[src/plugins/types.ts:1285-1291]
| 钩子 | 签名 | 用途 |
|---|---|---|
| `fetchUsageSnapshot` | `(ctx) => ProviderUsageSnapshot` | 用量快照 |
| `createEmbeddingProvider` | `(ctx) => PluginEmbeddingProvider` | 嵌入式向量供应商 |

认证方法类型 `ProviderAuthMethod` 包含 `id`、`label`、`kind`（oauth/api_key/token/device_code/custom）、`run(ctx)`（交互式认证）、`runNonInteractive(ctx)`（非交互式认证）和 `wizard`（向导元数据）。^[src/plugins/types.ts:316-333]

### 3.2 简化 Provider 注册

对于标准 API-key 型供应商，`defineSingleProviderPluginEntry()` 提供高度简化的注册入口：^[src/plugin-sdk/provider-entry.ts:41-168]

```typescript
// 示例：extensions/brave/index.ts 使用 definePluginEntry
import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

export default definePluginEntry({
  id: "brave",
  name: "Brave Plugin",
  description: "Bundled Brave plugin",
  register(api) {
    api.registerWebSearchProvider(createBraveWebSearchProvider());
  },
});
```

Provider 入口还导出了 `emptyPluginConfigSchema`、`buildPluginConfigSchema`、`createProviderApiKeyAuthMethod` 等辅助函数。^[src/plugin-sdk/provider-entry.ts:1-9]

### 3.3 内置扩展目录

`extensions/` 目录下包含 30+ 捆绑插件，涵盖：^[extensions/]

- **模型供应商**：Anthropic、OpenAI、Google、Groq、DeepSeek、Amazon Bedrock、Fireworks、GitHub Copilot、Ollama、OpenRouter、Cloudflare AI Gateway、HuggingFace、xAI、MiniMax、Arcee、BytePlus、Chutes、Codex 等
- **消息渠道**：Discord、Telegram、Slack、WhatsApp (via BlueBubbles)、iMessage、IRC、Matrix、Google Chat、Microsoft Teams、Feishu、Signal、Nostr、Nextcloud Talk、Twitch、Tlon、Xiaomi、Zalo、Synology Chat 等
- **工具/搜索**：Brave、DuckDuckGo、Exa、Firecrawl、Comfy、Diffs 等
- **媒体**：ElevenLabs、Deepgram、Fal 等
- **基础设施**：Diagnostics-OTel、Active Memory、Device Pair 等

每个插件目录遵循标准结构：`index.ts`（入口）、`api.ts`（公共 API 导出）、`openclaw.plugin.json`（清单）、`package.json`（包信息）。^[extensions/anthropic/]

---

## 4. Channel 插件 -- 消息渠道扩展

### 4.1 ChannelPlugin 接口

`ChannelPlugin` 是消息渠道能力的完整规范，包含约 25 个适配器接口字段：^[src/channels/plugins/types.plugin.ts:53-96]

**基本信息**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `id` | `ChannelId` | 唯一渠道标识 |
| `meta` | `ChannelMeta` | 渠道元数据（名称、描述、标签等） |
| `capabilities` | `ChannelCapabilities` | 渠道能力声明（streaming/threading/groups/mentions/directMessaging 等） |

**配置**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `config` | `ChannelConfigAdapter<ResolvedAccount>` | 配置解析与标准化（必需） |
| `configSchema` | `ChannelConfigSchema?` | 配置 JSON Schema（含 uiHints） |
| `setup` | `ChannelSetupAdapter?` | 设置/配置向导 |
| `setupWizard` | `ChannelSetupWizard \| ChannelSetupWizardAdapter?` | 交互式设置向导 |
| `reload` | `{ configPrefixes, noopPrefixes }?` | 触发热重载的配置前缀 |

**生命周期**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `lifecycle` | `ChannelLifecycleAdapter?` | 生命周期管理（启动/停止/健康检查） |
| `heartbeat` | `ChannelHeartbeatAdapter?` | 心跳检测 |

**通信**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `outbound` | `ChannelOutboundAdapter?` | 出站消息发送 |
| `streaming` | `ChannelStreamingAdapter?` | 流式发送支持 |
| `threading` | `ChannelThreadingAdapter?` | 线程/对话管理 |
| `messaging` | `ChannelMessagingAdapter?` | 消息收发底层 |

**安全与认证**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `security` | `ChannelSecurityAdapter<ResolvedAccount>?` | DM 策略、身份验证 |
| `auth` | `ChannelAuthAdapter?` | 渠道认证（登录/登出） |
| `pairing` | `ChannelPairingAdapter?` | 设备配对流程 |
| `secrets` | `ChannelSecretsAdapter?` | 密钥管理 |
| `allowlist` | `ChannelAllowlistAdapter?` | 允许列表 |

**审批**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `approvalCapability` | `ChannelApprovalCapability?` | 审批能力（审批消息原生支持） |
| `elevated` | `ChannelElevatedAdapter?` | 提权操作 |

**群组与交互**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `groups` | `ChannelGroupAdapter?` | 群组管理 |
| `mentions` | `ChannelMentionAdapter?` | @提及处理 |
| `actions` | `ChannelMessageActionAdapter?` | 消息操作（按钮/交互） |
| `agentPrompt` | `ChannelAgentPromptAdapter?` | Agent 提示定制 |

**Gateway 与诊断**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `gateway` | `ChannelGatewayAdapter<ResolvedAccount>?` | Gateway 集成 |
| `gatewayMethods` | `string[]?` | 暴露的 Gateway 方法名 |
| `status` | `ChannelStatusAdapter<ResolvedAccount, Probe, Audit>?` | 状态探测与审计 |
| `doctor` | `ChannelDoctorAdapter?` | 诊断 |
| `commands` | `ChannelCommandAdapter?` | 渠道自有命令 |

**高级**：
| 字段 | 类型 | 用途 |
|---|---|---|
| `bindings` | `ChannelConfiguredBindingProvider?` | 配置绑定（会话绑定到渠道） |
| `conversationBindings` | `ChannelConversationBindingSupport?` | 会话绑定支持 |
| `directory` | `ChannelDirectoryAdapter?` | 目录服务 |
| `resolver` | `ChannelResolverAdapter?` | 实体解析 |
| `agentTools` | `ChannelAgentToolFactory \| ChannelAgentTool[]?` | 渠道自有的 Agent 工具 |
| `defaults` | `{ queue?: { debounceMs? } }?` | 渠道默认配置 |

---

## 5. 能力供应商扩展 (Capability Providers)

插件系统为以下 9 种能力提供了专用注册接口：^[src/plugins/types.ts:1938-1955]

| 能力 | 注册方法 | Provider 接口 | 核心职责 |
|---|---|---|---|
| 语音合成 (TTS) | `registerSpeechProvider()` | `SpeechProviderPlugin` ^[src/plugins/types.ts:1569-1589] | synthesize, listVoices, resolveConfig, parseDirectiveToken, configure/synthesizeTelephony |
| 实时转录 (STT) | `registerRealtimeTranscriptionProvider()` | `RealtimeTranscriptionProviderPlugin` ^[src/plugins/types.ts:1595-1599+] | createSession, resolveConfig, isConfigured |
| 实时语音 | `registerRealtimeVoiceProvider()` | `RealtimeVoiceProviderPlugin` ^[src/realtime-voice/provider-types.ts:42-48] | 双向语音桥接（createBridge） |
| 媒体理解 | `registerMediaUnderstandingProvider()` | `MediaUnderstandingProviderPlugin` | 图像/视频/音频内容理解 |
| 图像生成 | `registerImageGenerationProvider()` | `ImageGenerationProviderPlugin` | 图像生成请求处理 |
| 视频生成 | `registerVideoGenerationProvider()` | `VideoGenerationProviderPlugin` | 视频生成请求处理 |
| 音乐生成 | `registerMusicGenerationProvider()` | `MusicGenerationProviderPlugin` | 音乐生成请求处理 |
| 网页抓取 | `registerWebFetchProvider()` | `WebFetchProviderPlugin` ^[src/plugins/types.ts:175-191] | 网页内容获取、凭据解析 |
| 网页搜索 | `registerWebSearchProvider()` | `WebSearchProviderPlugin` ^[src/plugins/types.ts:175-191] | 搜索结果获取、凭据解析 |

所有能力供应商的拥有权在 `PluginManifestContracts` 中声明（`speechProviders`、`realtimeTranscriptionProviders`、`mediaUnderstandingProviders` 等），允许在插件运行时加载前进行静态能力发现。^[src/plugins/manifest.ts:192-204]

---

## 6. Context Engine -- 上下文引擎扩展

Context Engine 是独占槽位类型的扩展点（`kind: "context-engine"`），用于替换默认的会话上下文管理策略。

注册方式：`api.registerContextEngine(id, factory)`，其中 `factory` 是 `() => ContextEngine | Promise<ContextEngine>`。^[src/context-engine/registry.ts:10-11]

`ContextEngine` 接口包含以下核心方法：^[src/plugin-sdk/index.ts:96-112]

- `bootstrap(sessionKey)` -- 会话初始化
- `maintain(sessionKey)` -- 上下文维护（清理、修剪旧消息）
- `ingest(params)` -- 单条消息消化
- `ingestBatch(params)` -- 批量消息消化
- `afterTurn(params)` -- 每轮交互后处理
- `assemble(params)` -- 上下文组装（构建发送给 LLM 的完整上下文）
- `compact(params)` -- 上下文压缩

注册引擎时通过 `registerContextEngineForOwner()` 函数管理所有权，支持 `allowSameOwnerRefresh` 参数允许同一所有者刷新注册。Context Engine 的槽位默认值为 `"legacy"`。^[src/plugins/slots.ts:15]

SDK 还导出了 `registerContextEngine()` 函数和 `buildMemorySystemPromptAddition()` / `delegateCompactionToRuntime()` 辅助函数用于快速集成。^[src/plugin-sdk/index.ts:115-120]

---

## 7. Memory 插件 -- 记忆系统扩展

### 7.1 Memory Capability（独占槽位）

通过 `api.registerMemoryCapability(capability)` 注册，`kind: "memory"` 类型的插件拥有此槽位。`MemoryPluginCapability` 聚合了以下子能力（这些在旧的独立注册方法中各自是独占的）：^[src/plugins/types.ts:1978-2004]

- `promptBuilder` -- 构建记忆系统提示段落的函数
- `flushPlanResolver` -- 决定压缩前是否刷新记忆的策略
- `runtime` -- 运行时记忆适配（执行实际的记忆读写操作）

旧版独立注册方法（均已 deprecated，推荐使用聚合的 `registerMemoryCapability`）：
- `registerMemoryPromptSection(builder)` -- 独占
- `registerMemoryFlushPlan(resolver)` -- 独占
- `registerMemoryRuntime(runtime)` -- 独占

### 7.2 Memory 非独占扩展

以下注册接口可被多个插件同时使用：^[src/plugins/types.ts:1988-2008]

- `registerMemoryPromptSupplement(builder)` -- 附加记忆提示段落（多个插件的输出会拼接在一起）
- `registerMemoryCorpusSupplement(supplement)` -- 附加记忆语料源（提供额外的搜索结果/文档内容）
- `registerMemoryEmbeddingProvider(adapter)` -- 记忆嵌入向量供应商（支持多供应商共存）

`MemoryEmbeddingProviderAdapter`（即 `PluginEmbeddingProvider`）提供 `embedQuery(text)` 和 `embedBatch(texts)` 方法用于将文本转换为向量。^[src/plugins/types.ts:798-806]

---

## 8. CLI Backend 与 Agent Harness

### 8.1 CLI Backend 插件

通过 `api.registerCliBackend(backend)` 注册 CLI 推理后端。类型为 `CliBackendPlugin`（来自 `src/plugins/cli-backend.types.ts`），用于注册本地命令行推理程序。^[src/plugins/types.ts:1928-1929]

清单中的 `cliBackends` 字段声明 CLI 后端所有权（如 Anthropic 的 `["claude-cli"]`），在插件运行时加载前即可识别。^[extensions/anthropic/openclaw.plugin.json:8]

### 8.2 Agent Harness

通过 `api.registerAgentHarness(harness)` 注册 Agent 执行容器。类型为 `AgentHarness`（来自 `src/agents/harness/types.ts`），用于替换或增强 Agent 的核心执行逻辑。SDK 通过 `openclaw/plugin-sdk/agent-harness` 子路径暴露相关类型。^[src/plugins/types.ts:1975-1976]

---

## 9. 自定义命令与 CLI 扩展

### 9.1 自定义命令 (Commands)

通过 `api.registerCommand(command)` 注册绕过 LLM 的直接命令。插件命令在内置命令之前、Agent 调用之前处理，适合简单的状态切换或状态查询命令。^[src/plugins/types.ts:1960-1965]

命令名称约束：必须以字母开头，只能包含字母、数字、连字符和下划线（`/^[a-z][a-z0-9_-]*$/`）。内置保留命令名不可覆盖。^[src/plugins/command-registration.ts:31-40]

命令注册结果 `CommandRegistrationResult` 包含 `{ ok: boolean; error?: string }`。^[src/plugins/command-registration.ts:26-29]

### 9.2 CLI 注册器

通过 `api.registerCli(registrar, opts)` 注册 CLI 命令扩展树，支持：^[src/plugins/types.ts:1909-1923]

- `commands` -- 显式的顶层命令根列表
- `descriptors` -- 解析时命令描述符（允许延迟加载，避免启动时导入全部 CLI 代码）

清单中的 `commandAliases` 字段静态声明命令别名所有权。^[src/plugins/manifest.ts:161]

---

## 10. HTTP 路由与 Gateway 方法扩展

### 10.1 HTTP 路由

通过 `api.registerHttpRoute(params)` 注册自定义 HTTP 端点：^[src/plugins/registry-types.ts:68-76]

- `path` -- 路由路径
- `handler` -- 请求处理器（`OpenClawPluginHttpRouteHandler`）
- `auth` -- 认证策略（`OpenClawPluginHttpRouteAuth`）
- `match` -- 路由匹配规则（`OpenClawPluginHttpRouteMatch`）
- `gatewayRuntimeScopeSurface` -- Gateway 运行时作用域（如 `"operator"` / `"admin"`）

路由重叠检测由 `findOverlappingPluginHttpRoute()` 负责。^[src/plugins/registry.ts:33]

### 10.2 Gateway RPC 方法

通过 `api.registerGatewayMethod(method, handler, opts)` 注册 Gateway RPC 方法。核心管理命名空间（`config.*`、`exec.approvals.*`、`wizard.*`、`update.*`）自动规范化为 `operator.admin`，即使请求了更窄的作用域。^[src/plugins/types.ts:1897-1908]

---

## 11. 其他扩展点

### 11.1 Compaction Provider

通过 `api.registerCompactionProvider(provider)` 注册可插拔的会话压缩/摘要后端。多个供应商可以注册并存，核心通过 `getRegisteredCompactionProvider()` 和 `listRegisteredCompactionProviders()` 查询。^[src/plugins/types.ts:1971-1973]

### 11.2 Interactive Handler

通过 `api.registerInteractiveHandler(registration)` 注册交互式消息处理器，用于处理按钮点击、表单提交等用户交互事件。^[src/plugins/types.ts:1956]

### 11.3 文本转换 (Text Transforms)

通过 `api.registerTextTransforms(transforms)` 注册插件拥有的 `PluginTextTransforms`，包含双向替换规则：^[src/plugins/types.ts:1931]

- `input` 方向 -- 应用于发送给 LLM 的系统提示和消息文本之前
- `output` 方向 -- 应用于 LLM 响应文本到达后、渠道分发前

### 11.4 配置迁移 (Config Migration)

通过 `api.registerConfigMigration(migrate)` 注册轻量级配置迁移函数，可在插件运行时加载前执行。函数签名：`(config: OpenClawConfig) => { config, changes } | null | undefined`。^[src/plugins/types.ts:1932-1933]

### 11.5 背景服务 (Services)

通过 `api.registerService(service)` 注册后台服务，包含 `start()` 和 `stop()` 生命周期方法（类型 `OpenClawPluginService`）。^[src/plugins/types.ts:1927]

### 11.6 节点主机命令 (Node Host Commands)

通过 `api.registerNodeHostCommand(command)` 注册可在宿主机进程执行的命令。系统级命令包括 `NODE_SYSTEM_RUN_COMMANDS`、`NODE_SYSTEM_NOTIFY_COMMAND`、`NODE_EXEC_APPROVALS_COMMANDS` 等。^[src/plugins/types.ts:1925]

### 11.7 安全审计收集器

通过 `api.registerSecurityAuditCollector(collector)` 注册安全审计收集器，用于收集和报告安全扫描发现。^[src/plugins/types.ts:1926]

### 11.8 自动启用探测 (Auto-Enable Probe)

通过 `api.registerAutoEnableProbe(probe)` 注册轻量级配置探测函数，返回应为此插件自动启用的供应商/渠道 ID 列表。函数签名：`(ctx: { config, env }) => string | string[] | null | undefined`。^[src/plugins/types.ts:1935]

### 11.9 热重载 (Reload Registration)

通过 `api.registerReload(registration)` 注册配置热重载监听器。Channel 插件也可通过 `reload.configPrefixes` 声明触发重载的配置路径前缀。^[src/plugins/types.ts:1924] ^[src/channels/plugins/types.plugin.ts:63]

### 11.10 会话绑定解析 (Conversation Binding)

通过 `api.onConversationBindingResolved(handler)` 注册会话绑定解析回调，处理 `PluginConversationBindingResolvedEvent` 事件。^[src/plugins/types.ts:1957-1959]

---

## 12. Plugin SDK 子路径体系

扩展代码通过 `openclaw/plugin-sdk/<subpath>` 导入 SDK 类型和工具。官方 SDK 入口包含约 80 个标准化子路径，来自 `scripts/lib/plugin-sdk-entrypoints.json`：

**核心入口**：`index`, `core`, `plugin-entry`, `provider-entry`, `provider-setup`, `self-hosted-provider-setup`

**运行时**：`runtime`, `runtime-env`, `runtime-doctor`, `runtime-secret-resolution`, `runtime-config-snapshot`, `runtime-group-policy`, `plugin-runtime`, `lazy-runtime`

**渠道 (Channel)**：`channel-setup`, `channel-streaming`, `channel-runtime`, `channel-runtime-context`, `channel-reply-pipeline`, `channel-secret-runtime`, `channel-secret-basic-runtime`, `channel-secret-tts-runtime`

**审批 (Approval)**：`approval-auth-runtime`, `approval-client-runtime`, `approval-delivery-runtime`, `approval-gateway-runtime`, `approval-handler-adapter-runtime`, `approval-handler-runtime`, `approval-native-runtime`, `approval-reply-runtime`, `approval-runtime`

**回复 (Reply)**：`reply-runtime`, `reply-dispatch-runtime`, `reply-reference`, `reply-chunking`, `reply-payload`, `inbound-reply-dispatch`, `inbound-envelope`

**媒体 (Media)**：`media-runtime`, `media-mime`, `media-generation-runtime`, `agent-media-payload`, `outbound-media`, `speech-core`

**安全 (Security)**：`security-runtime`, `ssrf-policy`, `ssrf-runtime`, `secret-ref-runtime`

**基础设施**：`infra-runtime`, `gateway-runtime`, `config-runtime`, `config-schema`, `setup`, `setup-runtime`, `setup-adapter-runtime`, `setup-tools`, `temp-path`, `testing`, `sandbox`, `logging-core`, `markdown-table-runtime`

**代理**：`agent-runtime`, `agent-harness`, `agent-config-primitives`, `simple-completion-runtime`, `hook-runtime`, `host-runtime`, `process-runtime`, `windows-spawn`, `acp-runtime`, `acp-binding-runtime`

**对话与绑定**：`conversation-binding-runtime`, `conversation-runtime`, `thread-bindings-runtime`, `text-runtime`, `text-chunking`

**浏览器**：`browser-cdp`, `browser-config`, `browser-config-runtime`, `browser-config-support`, `browser-control-auth`, `browser-node-runtime`, `browser-profiles`

**账户与渠道配置**：`account-helpers`, `account-core`, `account-id`, `account-resolution`, `allow-from`, `allowlist-config-edit`, `bluebubbles`, `bluebubbles-policy`

**路由与矩阵**：`routing`, `proxy-capture`, `matrix-runtime-heavy`, `matrix-runtime-shared`

**GitHub Copilot**：`github-copilot-login`, `github-copilot-token`

**CLI**：`cli-runtime`, `cli-backend`

**SDK 模块解析**：插件加载器中的 `buildPluginLoaderAliasMap()` 和 `resolvePluginSdkAliasCandidateOrder()` 确保插件模块能正确解析 `openclaw/plugin-sdk/*` 导入。三种解析模式（`prefer-sdk`、`prefer-core`、`prefer-module`）通过 `pluginSdkResolution` 选项控制。^[src/plugins/loader.ts:72-84]

---

## 13. 扩展边界与安全规则

`extensions/AGENTS.md` 定义了严格的边界规则：^[extensions/AGENTS.md:26-50]

1. **导入限制**：扩展代码只能从 `openclaw/plugin-sdk/*` 和自身本地 barrel（如 `./api.ts`、`./runtime-api.ts`）导入。禁止导入核心内部（`src/**`）、其他扩展的内部代码。
2. **清单完整性**：保持 `openclaw.plugin.json` 和 `package.json` 的 `openclaw` 块准确，以便发现和设置工作无需执行插件代码。
3. **公共 API 隔离**：将内部实现文件（如 `src/**`、`onboard.ts`）视为私有，除非通过 `api.ts` 和 `src/plugin-sdk/<id>.ts` facade 显式提升为公共。
4. **Provider 本地化**：将认证、onboarding、目录选择和供应商特有产品行为保留在插件本地。不要因为两个供应商看似相似就将供应商特定逻辑移到核心。
5. **共享工具优先**：在添加新的 Provider 本地 helper 之前，检查是否已通过 `openclaw/plugin-sdk/*` 存在相同的共享工具。
6. **向后兼容**：新插件面对接缝必须保持向后兼容和版本化。第三方插件消费此表面。

测试边界通过 `test/extension-import-boundaries.test.ts`、`test/extension-package-tsc-boundary.test.ts`、`test/plugin-extension-import-boundary.test.ts` 和 `scripts/check-no-extension-src-imports.ts` 等文件强制实施。

---

## 14. 扩展难度梯度

| 难度 | 扩展类型 | 入口 | 所需知识 |
|---|---|---|---|
| **极低** | Provider (API-key 型) | `defineSingleProviderPluginEntry()` | API endpoint、认证方式 |
| **极低** | Web Search / Web Fetch Provider | `registerWebSearchProvider()` / `registerWebFetchProvider()` | 实现 fetch/search 标准接口 |
| **低** | 自定义命令 | `registerCommand()` | 命令名 + 简单处理器 |
| **低** | 观察型钩子 | `api.on("llm_input", handler)` | 事件负载结构 |
| **低** | 配置迁移 | `registerConfigMigration()` | OpenClawConfig 结构 |
| **中低** | 修改型钩子 | `api.on("before_prompt_build", handler)` | System Prompt 注入位置和字段 |
| **中低** | 文本转换 | `registerTextTransforms()` | input/output 方向替换规则 |
| **中** | Provider (复杂型) | `definePluginEntry()` + `registerProvider()` | 传输层、重放策略、OAuth 认证流、动态模型解析 |
| **中** | Speech / TTS Provider | `registerSpeechProvider()` | synthesize、listVoices、resolveConfig 等标准方法 |
| **中高** | Channel 插件 (简单渠道) | `defineChannelPluginEntry()` + `registerChannel()` | ChannelPlugin 配置和生命周期适配器 |
| **高** | Channel 插件 (复杂渠道) | `defineChannelPluginEntry()` + 全套适配器 | pairing、security、streaming、gateway、groups、mentions 等 |
| **高** | Context Engine | `registerContextEngine()` (独占槽位) | bootstrap/maintain/ingest/assemble/compact 完整上下文管理逻辑 |
| **高** | Memory 插件 | `registerMemoryCapability()` (独占槽位) | 记忆存储、检索、嵌入向量、刷新计划 |
| **极高** | Agent Harness | `registerAgentHarness()` | 替换完整 Agent 核心执行容器 |

---

## 15. 关联总结

```
openclaw.plugin.json (Manifest) --> 静态能力声明（contracts/activation/setup/modelSupport）
         |
         v
discoverOpenClawPlugins() --> 候选插件列表（idHint/source/rootDir/origin/format）
         |
         v
loadBundledPlugins() --> PluginRegistry (已加载插件 + 诊断)
         |
         v
definePluginEntry() / defineSingleProviderPluginEntry() / defineChannelPluginEntry()
         |
         v
OpenClawPluginApi.register*() / .on() --> 注册到各全局注册表
         |
    +----+----+----+----+----+----+----+----+
    |    |    |    |    |    |    |    |    |
    v    v    v    v    v    v    v    v    v
  Provider Channel Tool Hook Command HTTP Gateway ContextEngine Memory ...
  (40+     (25     (Any (29  (Custom (REST  (RPC   (exclusive  (exclusive
   hooks)  adapters) Tool) hooks) cmd)    route) method) slot)      slot)

Plugin SDK 子路径 (80+ subpaths) -> 类型安全 + 边界强制 + 向后兼容
Extensibility boundary: extensions/AGENTS.md + test/extension-*-boundary.test.ts
```
