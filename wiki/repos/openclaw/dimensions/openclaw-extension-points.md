---
repo: openclaw
dimension: extension-points
dimensions_version: v1.0
generated: 2026-06-09
---

# OpenClaw — Extension Points

OpenClaw 的插件系统分为两个层次：一套声明式 JSON manifest（`openclaw.plugin.json`）描述 plugin 元数据，一套命令式的 `OpenClawPluginApi` 提供运行时注册能力。两者共同构成 plugin 扩展协议；Skills 文件是第三层轻量扩展，无需代码。

## 扩展入口文件

每个扩展包的 `index.ts` 导出 `definePluginEntry(...)` 或 `defineBundledChannelEntry(...)` 的返回值作为 `default export`。^[src/plugin-sdk/plugin-entry.ts:181-206]


**`definePluginEntry`** — 用于 provider、tool、command、service、memory、context-engine 类插件：

```ts
export default definePluginEntry({
  id: "anthropic",
  name: "Anthropic Provider",
  description: "...",
  register(api) {
    registerAnthropicPlugin(api);
  },
});
```
^[extensions/anthropic/index.ts:1-10]


**`defineBundledChannelEntry`** — 用于 channel 类插件，接受 `{ plugin, secrets, runtime, registerFull }` 四个模块引用，channel 代码按需懒加载（`loadBundledEntryExportSync`），避免不使用的 channel 在启动时加载。^[src/plugin-sdk/channel-entry-contract.ts:31-60]


## OpenClawPluginApi — 注册 API 全面清单

`register(api: OpenClawPluginApi)` 是所有扩展点的入口。API 上共有以下注册方法：^[src/plugins/types.ts:1867-1990]

| 方法 | 能力 |
|---|---|
| `registerTool` | 注册 agent 工具 |
| `registerHook` | 注册生命周期 hook |
| `registerHttpRoute` | 注册 HTTP 路由 |
| `registerChannel` | 注册 IM channel 插件 |
| `registerGatewayMethod` | 注册 Gateway RPC 方法 |
| `registerCli` | 注册 CLI 命令 |
| `registerProvider` | 注册 LLM provider |
| `registerSpeechProvider` | 注册 TTS provider |
| `registerRealtimeTranscriptionProvider` | 注册 STT provider |
| `registerRealtimeVoiceProvider` | 注册双工语音 provider |
| `registerMediaUnderstandingProvider` | 注册多模态理解 provider |
| `registerImageGenerationProvider` | 注册图片生成 provider |
| `registerVideoGenerationProvider` | 注册视频生成 provider |
| `registerMusicGenerationProvider` | 注册音乐生成 provider |
| `registerWebFetchProvider` | 注册 web fetch provider |
| `registerWebSearchProvider` | 注册 web 搜索 provider |
| `registerCommand` | 注册绕过 LLM 的直接命令 |
| `registerContextEngine` | 注册上下文引擎实现（**exclusive**） |
| `registerCompactionProvider` | 注册压缩/摘要后端 |
| `registerAgentHarness` | 注册 LLM 调用 harness 实现 |
| `registerMemoryCapability` | 注册记忆能力（**exclusive**） |
| `registerService` | 注册常驻服务（lifecycle managed） |
| `registerTextTransforms` | 注册文本兼容转换 |
| `registerConfigMigration` | 注册轻量配置迁移函数 |
| `registerAutoEnableProbe` | 注册自动启用探针 |

**独占槽位**：`registerContextEngine` 和 `registerMemoryCapability` 全局只能有一个活跃实现，后注册者覆盖前者。

## 28 个生命周期 Hook

`registerHook(events, handler)` 支持以下 hook 名：^[src/plugins/hook-types.ts:55-84]


```
before_model_resolve      before_prompt_build       before_agent_start
before_agent_reply        llm_input                 llm_output
agent_end                 before_compaction         after_compaction
before_reset              inbound_claim             message_received
message_sending           message_sent              before_tool_call
after_tool_call           tool_result_persist       before_message_write
session_start             session_end               subagent_spawning
subagent_delivery_target  subagent_spawned          subagent_ended
gateway_start             gateway_stop              before_dispatch
reply_dispatch            before_install
```

**Prompt 注入 hook**（`before_prompt_build`、`before_agent_start`）允许 plugin 在 LLM 调用前修改 system prompt，是 `active-memory` 和记忆系统注入的入口。^[src/plugins/hook-types.ts:128-133]


## openclaw.plugin.json — 声明式 manifest

每个 extension 包还可以包含 `openclaw.plugin.json`，声明：

- `id`、`enabledByDefault`
- `providers`：声明拥有的 provider 名（用于路由）
- `modelSupport.modelPrefixes`：声明支持哪些 model id 前缀
- `cliBackends`：声明 CLI backend 名
- `providerAuthEnvVars`：声明认证环境变量名（用于 doctor / setup wizard 自动检测）
- `contracts`：声明实现了哪些 capability contract（如 `mediaUnderstandingProviders`）
- `configSchema`：JSON Schema 形式的插件配置 schema

^[extensions/anthropic/openclaw.plugin.json:1-50]


## Skills 扩展（最轻量）

`src/agents/skills/` 是独立于 plugin 系统的第三层扩展点——用户在工作区放置 Markdown 技能文件，通过 `buildWorkspaceSkillsPrompt` 注入到 agent system prompt；`buildWorkspaceSkillCommandSpecs` 将技能文件中的命令 spec 注册为可用命令。技能文件不需要代码，纯 Markdown 即可定制 agent 行为。^[src/agents/skills.ts:8-39]


## 关联

*(暂无同类仓库已分析，链接待补充)*

<!-- generated-dimension-links -->
**本维度提取的节点：**

- [[openclaw/nodes/extension-points/agent-harness]] — ExtensionPoint
- [[openclaw/nodes/extension-points/channel-plugin]] — ExtensionPoint
- [[openclaw/nodes/extension-points/compaction-provider]] — ExtensionPoint
- [[openclaw/nodes/components/context-engine]] — Component
- [[openclaw/nodes/extension-points/exec-approval-request]] — ExtensionPoint
- [[openclaw/nodes/extension-points/hook-system]] — ExtensionPoint
- [[openclaw/nodes/extension-points/skills-extension]] — ExtensionPoint
<!-- /generated-dimension-links -->
