# OpenClaw 扩展点 (Extension Points) 维度分析

> 基于 DeepWiki 预解析内容提取，覆盖插件系统、技能系统、生命周期钩子、通道架构、配置扩展和服务注册等全部可扩展接口。

---

## 一、扩展体系总览

OpenClaw 提供两类主要扩展机制：**插件 (Plugins)** 和 **技能 (Skills)**，分别面向代码级别和自然语言级别的扩展。^[9286-9344]

| 扩展类型 | 格式 | 用途 | 分发方式 |
|:---|:---|:---|:---|
| **Plugins** | TS/JS 模块或 bundle | 注册模型提供商、工具、钩子、通道等 | 内置 (`extensions/*`)、工作区 (`.openclaw/extensions`)、npm 包 ^[9354-9359] |
| **Skills** | Markdown 文件 (`SKILL.md`) | 通过自然语言指令定义 agent 能力 | ClawHub 社区集合、仓库内置 (`./skills`)、工作区安装 ^[9354-9359] |

---

## 二、Plugin SDK —— 核心扩展接口

### 2.1 SDK 架构

插件系统是"manifest 优先"的设计：系统先读取 `openclaw.plugin.json` 清单文件来校验配置和确定能力，再执行插件代码。^[9369-9369, 9639-9639]

核心组件：

| 组件 | 角色 | 关键代码实体 |
|:---|:---|:---|
| **PluginRegistry** | 持有活跃插件实例及其注册能力 | `PluginRegistry` [src/plugins/registry.ts:140-140] ^[9414-9414] |
| **Plugin Loader** | 管理插件的发现、加载和缓存 | `loadOpenClawPlugins` [src/plugins/loader.ts:58-58] ^[9414-9414] |
| **Plugin SDK API** | 传递给 `register(api)` 的能力注册接口 | `OpenClawPluginApi` [src/plugins/loader.ts:169-174] ^[9414-9416] |
| **PluginRuntime** | 提供核心助手 (agent, model 等) 的执行上下文 | `PluginRuntime` [src/plugins/loader.ts:149-149] ^[9414-9416] |

### 2.2 注册方法清单 —— 五种核心扩展能力

`OpenClawPluginApi` 提供的能力注册方法 [src/plugins/loader.ts:165-171]：^[9713-9721]

| 注册方法 | 注册能力 | 示例 |
|:---|:---|:---|
| `api.registerProvider()` | 模型提供商 (LLM 文本推理、语音 TTS/STT、图像生成、媒体理解) | OpenAI、Anthropic |
| `api.registerChannel()` | 消息通道 (Telegram、Discord、Slack 等) | `ChannelPlugin` [src/plugins/loader-channel-setup.ts:79-81] |
| `api.registerTool()` | Agent 工具 (通过工厂创建工具实例) | Web 搜索、PDF 处理器 |
| `api.registerHook()` | 生命周期事件钩子 | `before_prompt_build` 等 |
| `api.registerMemoryCapability()` | 记忆后端与补充能力 (向量数据库、prompt 增强) | 记忆核心实现 |

### 2.3 插件清单 —— `openclaw.plugin.json`

每个原生插件必须包含清单文件 ^[9741-9756]：

| 字段 | 说明 |
|:---|:---|
| `id` | 唯一插件标识符 |
| `name` | 人类可读的插件名称 |
| `description` | 简要描述 |
| `configSchema` | 校验插件配置的 JSON Schema (Zod 派生) |
| `providers` | 插件支持的 provider ID 列表 |
| `channels` | 插件拥有的消息通道 |
| `activation` | 加载触发器：`onStartup`、`onProviders`、`onChannels` |
| `slots` | 互斥插槽名称 (如 `memory`)，限制同时只能有一个活跃 |

清单用于发现、校验和计划加载激活，无需执行插件代码。^[9754-9754, 9756-9756]

### 2.4 插件发现与加载流水线

发现顺序按优先级排列 ^[9394-9402]：

1. **显式路径**：`plugins.load.paths` 配置的路径
2. **工作区扩展**：`.openclaw/extensions/` 目录 [src/plugins/loader.test.ts:208-212]
3. **全局安装**：全局用户目录
4. **内置插件**：`OPENCLAW_BUNDLED_PLUGINS_DIR` 环境变量指定 [src/plugins/loader.test.ts:203-204]

激活规划器 (Activation Planner) 根据清单中的 `activation` 提示决定何时加载插件 [src/plugins/loader.ts:46-51]：^[9683-9687]
- `onStartup`：Gateway 启动时加载
- `onProviders`：按需加载（请求特定 provider 时）
- `onChannels`：按需加载（通道活跃时）

### 2.5 加载与注册时序

```
Plugin Module (jiti) → loader.ts: 动态导入 → 构建 buildPluginApi(PluginRecord)
→ 调用 register(api) → api.registerProvider/registerTool/registerChannel/registerHook
→ 注册入 PluginRegistry
```
^[9426-9449]

### 2.6 SDK 子路径 (Subpaths)

SDK 采用模块化设计，避免 barrel import。关键子路径 [docs/plugins/sdk-subpaths.md:9-32]：^[9722-9728]

- `plugin-sdk/plugin-entry`：基础入口点定义
- `plugin-sdk/core`：通道和设置插件基元
- `plugin-sdk/config-schema`：根配置 schema
- `plugin-sdk/health`：诊断健康检查注册

---

## 三、互斥插槽 (Exclusive Slots)——替换式扩展

OpenClaw 将一些关键角色定义为互斥"插槽"，同一时间只能有一个插件活跃，防止核心子系统的行为冲突。^[9462-9472]

| 插槽 | 用途 | 配置路径 |
|:---|:---|:---|
| `memory` | 长期记忆和向量存储实现 | `plugins.slots.memory` [src/plugins/loader.ts:50-53] |
| `context-engine` | 专用上下文管理逻辑 | `plugins.slots.context-engine` [src/plugins/loader.test.ts:11-11] |

插槽决策在插件激活阶段通过 `resolveMemorySlotDecision` 解析。^[9471-9471]

---

## 四、生命周期钩子 (Lifecycle Hooks)

### 4.1 Hook 注册入口

插件的钩子系统通过 `api.registerHook()` 订阅生命周期事件。Hook 类型定义于 `src/plugins/hook-types.ts` [src/plugins/hook-types.ts:1-1]：^[9445-9455, 6652]

### 4.2 系统提示构建钩子

系统提示 (system prompt) 组装过程中会调用插件钩子，将模块化文本块注入最终 prompt 字符串 [src/auto-reply/reply/agent-runner-memory.ts:86-91]。这包括 `before_prompt_build` 类型钩子。^[4328-4338]

### 4.3 工具执行前钩子 (Before Tool Call Hooks)

工具在被执行前会经过钩子系统，可以否决、调整参数或要求人工审批：^[5406-5415]

- **Before Tool Call 检测**：`hasBeforeToolCallPolicy` [src/agents/agent-tools.before-tool-call.ts:175-178] 检查是否有活跃钩子或受信策略注册。
- **受信工具策略**：`runTrustedToolPolicies` [src/agents/agent-tools.before-tool-call.ts:32-32] 执行插件定义的安全策略，可以阻止执行。
- **人机协同 (HITL)**：若工具需要审批，创建 `DeferredPluginToolApproval` [src/agents/agent-tools.before-tool-call.ts:145-152]，暂停执行直到 Gateway 收到审批决议。
- **参数调整**：钩子可通过 `recordAdjustedParamsForToolCall` [src/agents/agent-tools.before-tool-call.ts:201-205] 修改工具参数，实现透明路径重映射或安全清理。

| 代码实体 | 角色 |
|:---|:---|
| `hasBeforeToolCallPolicy` | 检测是否有执行钩子活跃 [src/agents/agent-tools.before-tool-call.ts:175-175] |
| `BeforeToolCallBlockedError` | 当钩子否决工具调用时抛出的错误 [src/agents/agent-tools.before-tool-call.ts:194-194] |
| `runTrustedToolPolicies` | 执行插件安全策略 [src/agents/agent-tools.before-tool-call.ts:32-32] |
| `recordAdjustedParamsForToolCall` | 记录工具参数调整 [src/agents/agent-tools.before-tool-call.ts:201-205] |

### 4.4 上下文压缩前钩子 (Before Compaction Hooks)

在上下文压缩 (compaction) 执行前，系统调用 `runBeforeCompactionHooks` [src/agents/embedded-agent-runner/compact.hooks.harness.ts:1-1]，允许插件在会话历史被截断前执行自定义逻辑。^[7288-7299]

压缩流水线还通过 `context-engine` 插槽支持替换式上下文管理，允许插件完全接管压缩逻辑 (`contextEngine.compact`)。^[7289-7289]

### 4.5 交互处理器钩子

插件可注册交互处理器 (interactive handlers) 用于 UI 驱动的交互 [src/plugins/loader.ts:69-72]。^[9782-9788]

---

## 五、通道插件 (Channel Plugin) —— 消息平台扩展

### 5.1 ChannelPlugin 接口架构

OpenClaw 将消息平台抽象为 `ChannelPlugin` 接口，所有平台通过统一架构集成。每个通道实现标准接口的子组件：^[8440-8494]

```
ChannelPlugin {
    +string id
    +ChannelMeta meta          // 元数据：id、label
    +ChannelSetupAdapter setup // 设置适配器
    +ChannelConfigAdapter config // 配置适配器
    +ChannelSecurity security   // 安全策略
    +ChannelMessaging messaging // 消息规范化、目标推断、会话路由
    +ChannelOutbound outbound   // 消息分块、媒体发送、payload 分发
    +ChannelStatus status       // 状态监控
    +ChannelActions actions     // 平台特定动作 (投票、消息置顶等)
}
```

关键子接口：^[8486-8494]
- **ChannelMessaging**：提供 `normalizeTarget()`、`inferTargetChatType()`、`resolveOutboundSessionRoute()` [src/infra/outbound/message-action-runner.ts:88-90]
- **ChannelOutbound**：定义 `deliveryMode`、`chunker(text, limit)`、`sendText()`、`sendMedia()`、`sendPayload()` [src/plugin-sdk/reply-payload.ts:187-195]
- **ChannelActions**：暴露 `describeMessageTool()`、`dispatchMessageAction()`，将平台特有功能作为 AI agent 的工具 [src/agents/tools/message-tool.ts:11-21]

### 5.2 已支持的平台

| 平台 | 驱动库 | 协议 | 认证方式 | 实时模式 |
|:---|:---|:---|:---|:---|
| Telegram | grammY | Bot API | Bot Token | 长轮询 / Webhook |
| Discord | discord.js | Gateway API | Bot Token | WebSocket Gateway |
| Slack | @slack/bolt | Events API | Bot Token + App Token | Socket Mode / HTTP |
| WhatsApp | Baileys | WhatsApp Web | QR Code 配对 | WebSocket |
| Matrix | matrix-js-sdk | Client-Server API | Access Token | 同步循环 |

^[8751-8760]

### 5.3 通道扩展的实现要点

每个通道实现需要处理：^[10230-10259]

- **消息缓存**：持久化缓存用于重建回复链和提供 agent 上下文 [extensions/telegram/src/message-cache.ts:30-57]
- **交互式 UI**：动态键盘用于模型选择和 provider 切换 [extensions/telegram/src/model-buttons.ts:136-144]
- **入站防抖**：通过 `createInboundDebouncer` 将快速连续消息合并为单次 agent turn [extensions/telegram/src/bot-handlers.runtime.ts:11-14]
- **出站分发管道**：负载规范化 → 文本分块 → 媒体适配 → 平台 API 调用 [src/plugin-sdk/reply-payload.ts:84-195]
- **进度草稿与直播预览**：长时间任务中维护"思考中"状态指示器 [extensions/discord/src/monitor/message-handler.draft-preview.ts:58-60]

---

## 六、技能系统 (Skills System) —— 自然语言扩展

### 6.1 SKILL.md 格式

技能是遵循 **AgentSkills.io** 规范的目录化组织，每个技能目录包含一个 `SKILL.md` 文件，混合 YAML frontmatter 配置和 Markdown 指令。^[9918-9936]

YAML frontmatter 字段：^[9928-9936]

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `name` | string | 唯一标识符 [src/skills/workshop/service.test.ts:110-110] |
| `description` | string | 发现和 prompt 构建时使用的摘要 [src/skills/workshop/service.test.ts:110-110] |
| `user-invocable` | boolean | 是否可由用户手动触发 [src/skills/workshop/service.test.ts:142-142] |
| `metadata.openclaw.requires` | object | 门控规则：`bins` (PATH 检查)、`env` (变量)、`config` (openclaw.json 路径) [docs/tools/skills.md:119-120] |

### 6.2 需求评估

OpenClaw 在运行时验证技能是否可用，确保 agent 只尝试环境支持的技能：^[9937-9944]

- **二进制可用性**：所需工具必须在系统 PATH 中存在
- **配置路径**：特定功能 (如 API 密钥) 必须在 `openclaw.json` 中激活 [docs/tools/skills.md:119-120]
- **环境变量**：技能可要求执行上下文中存在特定变量 [src/skills/workshop/service.test.ts:142-142]

### 6.3 技能加载来源与优先级

按优先级从高到低 [docs/tools/skills.md:37-45]：^[9955-9964]

| # | 来源 | 路径 | 可见范围 |
|:---|:---|:---|:---|
| 1 | **工作区技能** | `<workspace>/skills` | 仅该 agent |
| 2 | **项目 Agent 技能** | `<workspace>/.agents/skills` | 工作区 agent |
| 3 | **个人 Agent 技能** | `~/.agents/skills` | 所有本地 agent |
| 4 | **托管技能** | `~/.openclaw/skills` | 所有本地 agent |
| 5 | **内置技能** | 仓库级 `./skills/` | 所有本地 agent |

安全控制：Agent 配置可通过 `openclaw.json` 中的 allowlist 限制可见技能。^[9965-9969]
插件技能：插件也可附带技能，以较低优先级加载。^[9969-9969]

### 6.4 技能工作坊 (Skill Workshop)

工作坊是一个基于提案的系统，允许 agent 建议新技能或更新现有技能，作为人工审核的暂存区。^[9998-10008]

- **提案创建**：通过 `proposeCreateSkill` 或 `proposeUpdateSkill` 创建提案 [src/skills/workshop/service.test.ts:49-53]
- **支持文件**：提案可包含辅助文件 (脚本、模板) [src/skills/workshop/store.ts:153-155]
- **提案应用**：`applySkillProposal` 将 `SKILL.md` 和支持文件写入目标工作区 [src/skills/workshop/service.test.ts:104-107]

管理服务：`SkillWorkshopService` [src/skills/workshop/service.ts:78-80]

### 6.5 运行时刷新

技能目录被监控变化，当技能被修改后 `bumpSkillsSnapshotVersion` 被调用，通知 agent 运行时刷新能力索引。^[10042-10042]

---

## 七、Provider 扩展 —— 模型提供商注册

### 7.1 Provider 认证 SDK

插件通过 `provider-auth` SDK 处理各种凭证类型 (API 密钥、OAuth Token) [src/plugin-sdk/provider-auth.ts:11-19]：^[10175-10186]

- **API Key 解析**：`resolveProviderAuthProfileApiKey` 从 `auth-profiles.json` 存储中查找凭证 [src/plugin-sdk/provider-auth.ts:11-19]
- **向导集成**：认证方法可在注册中定义 `wizard` 对象，为 Control UI 的引导表单提供元数据 [extensions/openai/openclaw.plugin.test.ts:81-92]
- **外部 CLI 发现**：部分 provider (如 OpenAI、Anthropic) 选择从本地 CLI 工具 (如 `gh`、`claude` CLI) 发现凭证 [src/plugin-sdk/provider-auth.ts:11-12]

### 7.2 Provider 类型

| Provider 类型 | 示例 | 关键接口 |
|:---|:---|:---|
| 文本推理 (Chat) | OpenAI、Anthropic | 标准 chat completion 接口 |
| 实时语音 (RealtimeVoice) | OpenAI Realtime | WebSocket 连接管理、打断处理、多音频格式 [extensions/openai/realtime-voice-provider.ts:20-24, 87-94, 153-176] |
| 音乐生成 (MusicGeneration) | OpenRouter | SSE 流处理、多模态输入、buffer 重组 [extensions/openrouter/music-generation-provider.ts:1-5, 80-85, 113-135, 178-185] |

### 7.3 通道级 Provider 路由

Provider 注册后通过 `normalizeRegisteredProvider()` 标准化，根据 agent 配置和运行时解析选择。Provider 认证支持后台预热 (`warmCurrentProviderAuthStateOffMainThread`) 以减少首次请求延迟 [src/gateway/server-startup-post-attach.ts:188-191]。^[9386-9390, 1182-1186]

---

## 八、工具扩展 (Tool Extension)

### 8.1 工具注册

插件通过 `api.registerTool()` 注册工具，提供 Zod/JSON schema 和执行处理器 [src/plugins/registry.ts:150-153]。^[9782-9788]

工具可标记为可选，通过 `src/plugins/tools.ts` 和 `src/plugins/tools.optional.test.ts` 管理可选工具和多重工具注册表。^[9516-9516]

### 8.2 工具策略管道 (Tool Policy Pipeline)

工具在到达 agent 之前经过多层过滤：^[5462-5472]

| 阶段 | 代码实体 | 功能 |
|:---|:---|:---|
| 策略合并 | `resolveEffectiveToolPolicy` [src/flows/doctor-core-checks.runtime.ts:14-14] | 合并全局和 agent 级工具配置 |
| 最终门控 | `applyFinalEffectiveToolPolicy` [src/flows/doctor-core-checks.runtime.ts:16-16] | 运行时的最终工具可用性裁决 |
| 前调用钩子 | `hasBeforeToolCallPolicy` [src/agents/agent-tools.before-tool-call.ts:175-175] | 检测是否有执行钩子活跃 |
| 名称规范化 | `normalizeToolName` [src/flows/doctor-core-checks.runtime.ts:26-26] | 防止通过名称绕过策略 |

### 8.3 MCP (Model Context Protocol) 集成

外部工具通过 MCP 协议集成：^[5453-5460]

- 运行时初始化：`createBundleMcpToolRuntime` [src/flows/doctor-core-checks.runtime.ts:4-4]
- 动态加载：`materializeBundleMcpToolsForRun` [src/agents/agent-bundle-mcp-tools.ts:11-11]
- Schema 校验：`createBundleMcpJsonSchemaValidator` [src/agents/agent-bundle-mcp-runtime.test.ts:6-6]

---

## 九、配置扩展 (Configuration Schema Extension)

### 9.1 插件提供的配置 Schema

各插件通过 `openclaw.plugin.json` 中的 `configSchema` 字段贡献 Zod schema，这些 schema 在运行时会合并到主配置的校验管道中。`validateConfigObjectWithPlugins` 负责合并后的校验 [src/config/io.ts:111-114]。^[2168-2179]

系统 Webhooks 作为配置的一级字段存在 (`hooks: System Webhooks`)，属于 `Automation & Extensions` 配置分组。^[2130-2162]

### 9.2 配置结构中的可扩展点

整个配置树中以下分组直接与扩展能力相关：^[2120-2162]

- `plugins: Manifest Extensions` — 插件清单配置
- `skills: SKILL.md Registry` — 技能注册表
- `hooks: System Webhooks` — 系统 Webhook 配置
- `mcp: Model Context Protocol` — MCP 协议配置
- `cron: Scheduled Jobs` — 定时任务配置
- `channels: Platform Config` — 通道平台配置

---

## 十、安全边界与合规 (Security Boundary)

### 10.1 插件安全扫描

安装时进行静态分析 (`scanBundleInstallSource`、`scanPackageInstallSource`) 检测危险操作 [src/plugins/install.test.ts:38-43]。^[9760-9777]

### 10.2 完整性校验

NPM 插件的完整性哈希与注册表元数据验证 [src/plugins/install.ts:13-14]。^[9760-9777]

### 10.3 托管 NPM Root

插件安装在受控的托管根目录 (`_openclaw-managed-npm`)，peer dependency 链接到 Gateway host [src/plugins/install.ts:27-27]。^[9760-9777]

### 10.4 版本兼容性检查

系统检查 `package.json` 中的 `minHostVersion` 和 `pluginApi` 范围 [src/plugins/install.ts:112-116, 150-165]。^[9769-9777]

### 10.5 SDK 别名强制

加载器通过虚拟别名系统确保插件导入正确版本的 SDK，将 `openclaw/plugin-sdk` 导入映射到源文件 (`src/`) 或分发文件 (`dist/`) [src/plugins/sdk-alias.ts:12-21, 150-165]。^[9771-9772]

### 10.6 能力边界强制

只有启用的插件才能参与运行时，插件必须在 `openclaw.plugin.json` 中声明能力，以便系统在执行代码前进行推理 [src/plugins/loader.ts:66-67, 98-101]。^[9731-9733]

---

## 十一、扩展难度梯度

| 难度 | 扩展方式 | 所需技能 | 典型场景 |
|:---|:---|:---|:---|
| **最低** | Skills (`SKILL.md`) | Markdown + YAML | 添加 agent 行为指令、环境集成说明 |
| **低** | Skill Workshop 提案 | 自然语言 | Agent 自主建议新能力，人工审核 |
| **中低** | 配置 Schema 扩展 | JSON Schema / Zod | 注册新配置段以支持插件行为 |
| **中** | Provider 插件 | TypeScript + OAuth/OAPI | 接入新模型提供商 (OpenAI 兼容、实时语音等) |
| **中** | Tool 注册 | TypeScript + Zod Schema | 添加新的 agent 工具能力 |
| **中高** | Channel 插件 | TypeScript + 消息平台 API | 集成新消息平台 (IM、社交网络等) |
| **高** | Slot 替换 | TypeScript + 深度架构理解 | 替换记忆后端或上下文引擎 |
| **高** | Hook 系统扩展 | TypeScript + 生命周期理解 | 拦截工具执行、prompt 构建、压缩等核心流水线 |

---

## 十二、扩展点关联图

```
配置层 (openclaw.json)
  ├── plugins: 插件清单 → PluginRegistry
  ├── skills: 技能注册表 → SkillWorkshopService
  ├── hooks: 系统 Webhooks → 外部 HTTP 回调
  ├── mcp: MCP 配置 → MCP Runtime
  ├── channels: 通道配置 → ChannelPlugin[]
  └── cron: 定时任务 → CronService

插件系统 (src/plugins/)
  ├── api.registerProvider() → Provider 标准化 → 认证预热 → Agent Runtime
  ├── api.registerChannel() → ChannelPlugin → 入站规范化 → 出站分发
  ├── api.registerTool() → Tool Policy 管道 → BeforeToolCall Hooks → MCP 桥接
  ├── api.registerHook() → 生命周期事件系统
  │     ├── before_prompt_build → System Prompt 组装
  │     ├── BeforeToolCallPolicy → 工具执行拦截/审批
  │     ├── runBeforeCompactionHooks → 压缩前逻辑
  │     └── Interactive Handlers → UI 交互处理
  ├── api.registerMemoryCapability() → 记忆/向量存储
  └── Slots (memory, context-engine) → 专有替换式扩展

技能系统 (src/skills/)
  ├── SKILL.md 解析 → 需求评估 (bins/env/config)
  ├── SkillWorkshopService → 提案创建/审核/应用
  └── 运行时刷新 → bumpSkillsSnapshotVersion → Agent 能力索引
```

---

## 十三、关键文件索引

| 维度 | 关键文件 | 说明 |
|:---|:---|:---|
| 插件注册表 | `src/plugins/registry.ts` | 核心 PluginRegistry 实现 |
| 插件加载器 | `src/plugins/loader.ts` | 发现、加载、缓存管理 |
| 插件 SDK API | `src/plugins/api-builder.ts` | `buildPluginApi` 构建 `OpenClawPluginApi` |
| 插件清单 | `src/plugins/manifest.ts` | 清单读取与校验 |
| 清单注册表 | `src/plugins/manifest-registry.ts` | 清单驱动的激活规划 |
| 插件安装 | `src/plugins/install.ts` | NPM 安装、安全扫描、完整性校验 |
| Hook 类型定义 | `src/plugins/hook-types.ts` | 钩子类型与接口 |
| 工具前调用策略 | `src/agents/agent-tools.before-tool-call.ts` | 工具执行前的钩子拦截 |
| 通道插件类型 | `src/channels/plugins/types.plugin.ts` | `ChannelPlugin` 接口定义 |
| Provider 认证 SDK | `src/plugin-sdk/provider-auth.ts` | 凭证解析与向导集成 |
| Provider 运行时 SDK | `src/plugin-sdk/realtime-voice.ts` | 实时语音 provider 接口 |
| 通道流式 SDK | `src/plugin-sdk/channel-streaming.ts` | 通道流式输出支持 |
| 回复 Payload SDK | `src/plugin-sdk/reply-payload.ts` | 出站回复规范化 |
| SDK 别名系统 | `src/plugins/sdk-alias.ts` | SDK 版本导入映射 |
| 技能工作坊服务 | `src/skills/workshop/service.ts` | 技能提案生命周期管理 |
| 技能发现状态 | `src/skills/discovery/status.ts` | 技能资格评估 |
