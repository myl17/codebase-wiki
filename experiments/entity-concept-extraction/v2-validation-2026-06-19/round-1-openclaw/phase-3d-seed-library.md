# 设计选择种子库

> 最后更新：openclaw（2026-06-19）
> 第一轮，种子库包含 22 条设计选择，全部为"仅 openclaw—待观察"

---

## Architecture

---

## 如何门控工具权限

**维度**：Architecture
**问题陈述**：如何在 AI 助手的工具调用关键路径上，决定工具权限的拦截策略——是同步阻塞验证还是事后审计？
**核心关切**：
- 关切 1：安全边界必须可被代码静态验证，不依赖运行时日志的可审计性
- 关切 2：权限门控延迟不应影响正常的消息处理吞吐——安全检查与性能是零和博弈
- 关切 3：多来源配置（profile/provider/global/agent/group）的叠加规则必须产生可预测的结果，而非隐式交互
- 关切 4：Exec 类高风险工具需要额外用户确认回路，但低风险工具不应被同等阻塞

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 同步串行 Pipeline | 所有工具调用在执行前串行经过5层 allowlist/denylist 过滤，exec 类额外阻塞等待 owner 审批。权限决策在消息处理关键路径上同步完成，不依赖事后审计 | [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]] → `src/agents/tool-policy-pipeline.ts:56-90`；[[openclaw/nodes/components/openclaw-tool-policy]] → `src/agents/tool-policy.ts:19-55` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何在消息驱动的 AI 助手中创建主动触发路径

**维度**：Architecture
**问题陈述**：在消息驱动的 AI 助手架构中，如何设计主动触发路径——是通过独立调度系统还是复用消息处理管道？
**核心关切**：
- 关切 1：主动触发路径不应破坏消息驱动模型的清晰性——两条路径共存需要明确的边界
- 关切 2：定时触发的执行结果必须可投递回消息通道（channel/thread/announce/webhook）——主动触发的结果需要消息通道作为出口
- 关切 3：每次定时触发应使用独立的 agent session，不与用户对话 session 混淆——session 隔离是正确性要求

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Cron 作为唯一无消息主动触发入口 | CronScheduler 是唯一可以在无 IM 消息触发的情况下主动发起 agent 运行的入口。每次 cron 触发创建独立 isolated-agent session，`CronDeliveryPlan` 决定结果投递目标（channel/thread/announce/webhook）。所有其他 agent 运行都是消息驱动的 | [[openclaw/nodes/components/openclaw-cron-scheduler]] → `src/cron/delivery-plan.ts:10-19`；[[openclaw/nodes/components/openclaw-task-flow]] → `src/tasks/task-executor.ts:85-112` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何设计 Exec 类工具的审批流程

**维度**：Architecture
**问题陈述**：在 AI 助手执行高风险 shell 命令时，如何设计审批流程的阻塞策略——是同步阻塞等待用户决策还是异步通知后继续执行？
**核心关切**：
- 关切 1：审批必须是同步阻塞的——不能在命令执行后才通知用户（安全性要求前置审批）
- 关切 2：阻塞等待不应死锁 agent 进程——需要超时和取消机制（活性要求）
- 关切 3：审批可通过多种路径到达用户（host CLI / gateway HTTP）——路径选择应对 core 透明
- 关切 4：审批失败或超时不应导致 agent session 永久卡死——容错性要求优雅降级

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 异步阻塞双路径审批 | `ExecApprovalRequest` 注册后 `waitForExecApprovalDecision` 阻塞等待 owner 决策，支持 host/gateway 双路径审批通道。审批在 ToolPolicy 同步门控 pipeline 内部触发，但等待机制是异步的可中断等待，不占用事件循环 | [[openclaw/nodes/extension-points/openclaw-exec-approval-request]] → `src/agents/bash-tools.exec-approval-request.ts:89-126`；[[openclaw/nodes/components/openclaw-tool-policy]] → `src/agents/tool-policy.ts:19-55` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何注入记忆到 LLM 上下文

**维度**：Architecture
**问题陈述**：在 AI 助手的 LLM 调用链路中，如何决定记忆注入的时机——是在每次 LLM 调用前实时检索还是在一个确定性的组装阶段批量注入？
**核心关切**：
- 关切 1：记忆内容的新鲜度——实时检索可获取最新记忆，避免使用过时信息
- 关切 2：Prompt 组装阶段的确定性——如果记忆内容在 prompt 构建后变化，可能导致行为不一致
- 关切 3：多个记忆后端（builtin SQLite + qdrant + LanceDB + wiki-style）并存——注入时机需兼容多种检索延迟

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Prompt 组装阶段批量注入 | 记忆在 Context Engine 的 `assemble` 阶段注入，非实时查询。记忆注入通过生命周期 hook（`before_prompt_build`、`before_agent_start`）实现，由 `active-memory` 等扩展负责。代价：同一次 LLM 调用期间新增的记忆在当前轮不可见 | [[openclaw/nodes/components/openclaw-memory-system]] → `src/memory-host-sdk/host/types.ts:1-30`；[[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27` |

**Concept 状态**：仅 openclaw—待观察

---

## Extension Points

---

## 如何选择 LLM Provider 的实现

**维度**：Extension Points
**问题陈述**：在多 LLM provider 环境中，如何在运行时决定最优 provider harness 的选择规则——是基于显式优先级排序还是基于能力自描述匹配？
**核心关切**：
- 关切 1：Core 不应感知具体 provider 的存在——新增 provider 不应修改核心代码（透明性）
- 关切 2：同一模型如果被多个 harness 声明支持，需要确定性的选择规则——优先级必须可预测
- 关切 3：不同 harness 的能力集不同（如是否支持 compact）——选择时必须考虑能力匹配，而非仅看优先级

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 优先级排序 + 能力匹配选择 | `AgentHarness` 接口包含 `supports(ctx)` 方法返回优先级分数，`selectAgentHarness()` 按 priority 排序选最优实现。各 provider（anthropic/openai/ollama/deepseek）在 extensions/ 下独立注册 harness，对 core 完全透明 | [[openclaw/nodes/extension-points/openclaw-agent-harness]] → `src/agents/harness/types.ts:30-44` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何管理上下文引擎和记忆能力的全局唯一性

**维度**：Extension Points
**问题陈述**：当多个 plugin 都想提供同一类全局能力（如 context engine）时，如何决定注册策略——是允许多个实现共存还是强制全局唯一？
**核心关切**：
- 关切 1：Context engine 决定所有 LLM 交互的 prompt 组装方式——同时存在多个必然产生冲突（正确性要求唯一性）
- 关切 2：Plugin 应能自由注册自己的实现——开放性要求允许多个 plugin 竞争注册
- 关切 3：注册顺序应可预测——后注册者覆盖前者的规则必须明确且一致

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Exclusive 槽位覆盖注册 | `registerContextEngine` 和 `registerMemoryCapability` 被设计为 exclusive 槽位——全局只能有一个活跃实现，后注册者覆盖前者。这与 `registerHook`（多个 handler 共存）和 `registerChannel`（多个实现并存）的设计截然不同 | [[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27`；[[openclaw/nodes/extension-points/openclaw-compaction-provider]] → `src/plugins/types.ts:1867-1990`；[[openclaw/nodes/components/openclaw-memory-system]] → `src/memory-host-sdk/host/types.ts:1-30` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何在无代码情况下扩展 Agent 行为

**维度**：Extension Points
**问题陈述**：在为 AI 助手设计扩展机制时，如何决定最低门槛的扩展方式——是要求写代码注册 API 还是允许纯文本文件声明扩展？
**核心关切**：
- 关切 1：零代码门槛——用户只需编辑文本文件即可定制 agent 行为
- 关切 2：扩展内容需注入到 agent 的 system prompt 以影响 LLM 行为——文本扩展必须被正确组装进 prompt
- 关切 3：扩展内容可作为 agent 可调用的命令暴露，不仅是被动的 prompt 指令——文本格式需同时支持声明式指令和可执行命令
- 关切 4：与 plugin 系统互补不冲突——同一系统内两种扩展机制共存，不能互相破坏

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Markdown 技能文件作为第三层扩展 | 用户在工作区放置 Markdown 技能文件，`buildWorkspaceSkillsPrompt` 将内容注入 agent system prompt，`buildWorkspaceSkillCommandSpecs` 将技能文件中的命令 spec 注册为可用命令。不需要代码，纯 Markdown 即可定制 agent 行为。与声明式 plugin manifest（`openclaw.plugin.json`）和命令式 plugin API 构成三层扩展体系 | [[openclaw/nodes/extension-points/openclaw-skills-extension]] → `src/agents/skills.ts:8-39` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何分解 Channel Plugin 的适配器接口

**维度**：Extension Points
**问题陈述**：在为多平台 IM 系统设计 channel plugin 接口时，如何决定适配器接口的拆分粒度——是一个大而全的接口还是多个可选的小接口？
**核心关切**：
- 关切 1：不同 IM 平台的能力差异巨大——不是所有平台都支持所有操作，大而全的接口会迫使简单平台实现空方法
- 关切 2：核心对 channel 的调用路径（入站解析、出站发送、生命周期）需要统一的接口约定——拆分过细会破坏调用的一致性
- 关切 3：新增平台的工作量应与所需能力成正比——简单平台不应被迫实现复杂接口

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 13+ Adapter 分解 | `ChannelPlugin<ResolvedAccount>` 接口拆分为 13+ Adapter：`ChannelMessagingAdapter`、`ChannelOutboundAdapter`、`ChannelLifecycleAdapter`、`ChannelAuthAdapter`、`ChannelSetupAdapter` 等。每个 adapter 是可选的——平台只实现自己支持的维度。通过 `defineBundledChannelEntry` 统一注册入口 | [[openclaw/nodes/extension-points/openclaw-channel-plugin]] → `src/channels/plugins/types.plugin.ts:53-94`；[[openclaw/dimensions/openclaw-extension-points]] → `src/plugin-sdk/channel-entry-contract.ts:31-60` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何提供 Plugin SDK 的双入口模式

**维度**：Extension Points
**问题陈述**：在 plugin SDK 中，如何决定对不同类型插件的注册入口设计——是统一入口还是按插件重量级提供多个入口？
**核心关切**：
- 关切 1：Provider/tool 类插件相对轻量，应有一个简单的注册入口，无需关心加载优化
- 关切 2：Channel 插件包含重量级 SDK（如 `@slack/bolt`），必须懒加载以避免未配置的 channel 拖慢启动
- 关切 3：两种入口应共享同一套底层 plugin API——避免分裂导致维护两份文档和行为不一致

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `definePluginEntry` + `defineBundledChannelEntry` 双入口 | `definePluginEntry` 用于 provider/tool/command/service/memory/context-engine 类插件——简单的 register 回调；`defineBundledChannelEntry` 用于 channel 类插件——接受 `{ plugin, secrets, runtime, registerFull }` 四个模块引用，channel 代码通过 `loadBundledEntryExportSync` 按需懒加载。两种入口最终都通过 `OpenClawPluginApi` 注册 | [[openclaw/dimensions/openclaw-extension-points]] → `src/plugin-sdk/plugin-entry.ts:181-206`, `src/plugin-sdk/channel-entry-contract.ts:31-60` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何将生命周期 Hook 设计为扩展拦截面

**维度**：Extension Points
**问题陈述**：在 AI 助手运行生命周期中，如何设计 hook 系统的拦截粒度——是少数关键节点还是密集覆盖全生命周期？
**核心关切**：
- 关切 1：Hook handler 可能修改核心数据（如 system prompt）——需明确区分可修改和只读的 hook，权限模型不能过于粗糙
- 关切 2：Hook 数量需要覆盖主要生命周期节点，但不应无限膨胀——每个新 hook 增加系统复杂度
- 关切 3：每个 hook 可注册多个 handler，执行顺序和失败处理需可预测——多 handler 场景下行为确定性至关重要
- 关切 4：Prompt 注入类 hook 是记忆等关键系统的唯一入口——稳定性和性能要求极高

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 28 个命名生命周期 Hook | `registerHook(events, handler)` 支持 28 个生命周期 hook 名，覆盖从 `before_model_resolve` 到 `agent_end` 的完整链路。Prompt 注入类 hook（`before_prompt_build`、`before_agent_start`）允许 plugin 在 LLM 调用前修改 system prompt——是 active-memory 和记忆注入的唯一入口。同一 hook 支持多个 handler 共存 | [[openclaw/nodes/extension-points/openclaw-hook-system]] → `src/plugins/hook-types.ts:55-84`, `src/plugins/hook-types.ts:128-133` |

**Concept 状态**：仅 openclaw—待观察

---

## Performance Tradeoffs

---

## 如何平衡 Context 压缩的可恢复性与压缩率

**维度**：Performance Tradeoffs
**问题陈述**：在 AI 助手上下文窗口有限的情况下，如何决定历史对话压缩的优先目标——是可恢复性（agent 能接续任务）还是压缩率（最小化 token 消耗）？
**核心关切**：
- 关切 1：压缩后摘要必须保留足够信息使 agent 可恢复任务执行——信息保留与 token 削减直接冲突
- 关切 2：压缩率需足够高以控制 LLM token 成本——高压缩率必然损失细节
- 关切 3：工具输出（如 `tool_result.details`）通常冗长但对后续决策价值低，需特殊处理策略
- 关切 4：Token 估算存在固有误差——压缩参数需包含安全余量，但余量过大会削弱压缩效果

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 可恢复性优先压缩 | 摘要指令优先保留活跃任务状态、批处理进度、最后一次用户请求；`tool_result.details` 在压缩前 strip；参数用 `SAFETY_MARGIN = 1.2`（20% 缓冲补偿 token 估算误差）。牺牲历史细节完整性换取可恢复性 | [[openclaw/nodes/design-decisions/openclaw-compaction-recoverability-priority]] → `src/agents/compaction.ts:19-40`；[[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何优化冷启动速度

**维度**：Performance Tradeoffs
**问题陈述**：在 Node.js CLI 助手启动时，如何决定冷启动优化的权衡方向——是极限压缩首次响应时间，还是控制运行时内存占用？
**核心关切**：
- 关切 1：用户感知的首次可用时间（time-to-first-response）尽可能短——这是用户留存的关键质量指标
- 关切 2：内存中同时持有多个缓存对象不能导致 OOM——缓存与内存占用的零和关系
- 关切 3：新增模块的加载方式必须遵守同一套延迟约束，否则每次新增模块都会逐次退化启动性能
- 关切 4：启动失败（如 compile cache 损坏）必须静默降级，不能阻塞进程——可靠性不能为性能牺牲

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 启动速度优先于内存占用 | compile cache（V8 字节码磁盘缓存）+ `createLazyRuntimeModule`（Promise 缓存包装动态 import）+ channel entry 按需懒加载 + NODE_OPTIONS respawn 策略。冷启动被当作一等公民优化，所有重型运行时模块必须走 lazy 加载路径。代价：内存中多个 Promise cache，冷启动多一次 spawn() | [[openclaw/nodes/design-decisions/openclaw-startup-over-memory-tradeoff]] → `src/shared/lazy-runtime.ts:1-44`, `src/entry.ts:52-58`；[[openclaw/nodes/components/openclaw-process-supervisor]] → `src/process/supervisor/index.ts:1-12` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何设计 Prompt 缓存边界

**维度**：Performance Tradeoffs
**问题陈述**：在使用 LLM Prompt Caching 时，如何决定 system prompt 中缓存边界的位置——是将尽可能多的内容推入缓存区还是严格隔离动态内容？
**核心关切**：
- 关切 1：尽可能多的 token 命中缓存以减少每轮 API 费用——缓存区越大越好
- 关切 2：动态内容（记忆注入、实时上下文）必须放在缓存边界之后，不能混入缓存区——动态内容的存在限制了缓存区上限
- 关切 3：不同 LLM 平台的缓存 TTL 策略不同——边界设计需兼容多平台，不能只针对单一 provider 优化

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 稳定前缀 + 动态后缀分离 | 在 system prompt 中插入 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记，stable prefix 打上 Anthropic `cache_control: { type: "ephemeral" }` 标记。根据不同 API endpoint 决定缓存 TTL（`api.anthropic.com` 支持 `ttl: "1h"` 长缓存，其他端点的缓存时间更短）。动态后缀（记忆注入、实时上下文）在 boundary 后插入，不影响缓存命中 | [[openclaw/nodes/components/openclaw-context-engine]]（维度叙事页） → `src/agents/system-prompt-cache-boundary.ts:3-47`, `src/agents/anthropic-payload-policy.ts:37-65` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何防止 Context Window 不足导致截断失败

**维度**：Performance Tradeoffs
**问题陈述**：在无精确 token 计数的前提下，如何决定上下文窗口溢出的防护策略——是保守地提前触发压缩还是信任 token 估算尽量延迟压缩？
**核心关切**：
- 关切 1：必须在多个来源（modelsConfig / model 自报 / agentContextTokens）中选最保守值——宁可过早触发压缩也不能溢出
- 关切 2：Token 估算误差不可避免（尤其是工具输出的实际大小）——需留安全余量，但余量过大会过早触发压缩
- 关切 3：压缩触发线如果设得太低，不必要的压缩浪费 LLM 调用成本——过早压缩的经济代价

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 硬限制 + 软警告 + 多源保守选择 | 硬下限 `CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000`，软警告线 `CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000`，在 modelsConfig、model 自报、agentContextTokens 之间按优先级选最保守值。实际压缩触发由 `BASE_CHUNK_RATIO = 0.4` 和 `SAFETY_MARGIN = 1.2` 共同决定 | [[openclaw/dimensions/openclaw-performance-tradeoffs]] → `src/agents/context-window-guard.ts:4-81`, `src/agents/compaction.ts:19-40` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何管理消息入站的突发流

**维度**：Performance Tradeoffs
**问题陈述**：在 IM 助手的消息入站处理中，如何决定消息合并的防抖策略——是每条消息立即处理还是在时间窗口内合并后批量处理？
**核心关切**：
- 关切 1：合并窗口太长会导致用户感觉助手响应慢——用户体验要求低延迟
- 关切 2：合并窗口太短仍会产生多余的 LLM 调用，浪费 token 成本——成本控制要求足够的合并窗口
- 关切 3：不同 channel 的消息到达模式不同（如 Slack 的消息分段 vs Telegram 的长消息）——合并策略需按 channel 可配置

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Inbound 消息防抖合并 | 消息入站时做防抖，合并短时间内连续到达的多条消息再交给 agent 处理。防抖窗口由 channel plugin 的 `defaults.queue.debounceMs` 配置，不同 channel 可设置不同窗口。开销：引入最大 debounce 延迟 | [[openclaw/dimensions/openclaw-performance-tradeoffs]] → `src/channels/inbound-debounce-policy.ts:11-51` |

**Concept 状态**：仅 openclaw—待观察

---

## Dependency Strategy

---

## 如何选择 AI 引擎依赖策略

**维度**：Dependency Strategy
**问题陈述**：在构建 AI 助手时，如何决定核心 agent 引擎的依赖策略——是深度绑定一个成熟引擎还是保持引擎可替换性？
**核心关切**：
- 关切 1：快速复用经过验证的 agent 引擎，避免从零实现复杂的 LLM 交互协议——开发速度要求深度集成
- 关切 2：agent 层是整个产品的核心——替换引擎等价于重写系统，深度绑定意味着长期锁定
- 关切 3：上游引擎的版本节奏和 breaking change 直接影响产品迭代计划——外部节奏控制内部节奏
- 关切 4：引擎包之间的版本耦合必须被精确管理，防止隐式不兼容——版本矩阵的维护成本随包数量增长

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 深度绑定 `@mariozechner` 私有包族 | 442 处 import 完全依赖 `@mariozechner/*` 四件套（pi-ai / pi-agent-core / pi-coding-agent / pi-tui），四个包精确锁定同一版本。代价：agent 层几乎无法在不重写的情况下切换引擎，受上游版本节奏约束 | [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] → `package.json:1-50`；[[openclaw/nodes/extension-points/openclaw-agent-harness]] → `src/agents/harness/types.ts:30-44` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何隔离 Channel SDK 故障域

**维度**：Dependency Strategy
**问题陈述**：在多平台 IM 助手的 monorepo 中，如何决定第三方 Channel SDK 的依赖隔离策略——是集中管理依赖还是每个 Channel 独立声明？
**核心关切**：
- 关切 1：单个 channel SDK 的故障（安全漏洞、版本冲突、安装失败）不能影响核心运行时——隔离性要求独立声明
- 关切 2：用户只需安装自己使用的 channel，不被迫拉入所有 SDK——按需加载要求独立声明
- 关切 3：跨 channel 共享的 plugin 基础设施需要一致接口——共享层要求一定程度的集中约定

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Channel SDK 独立声明 + 故障域隔离 | 每个 channel extension 在自身 package.json 中独立声明 SDK 依赖（Slack 用 @slack/bolt、Telegram 用 grammy 等），不在 root package 聚合，通过 `workspace:*` 引用内部 plugin-sdk。核心运行时不因任何单个 channel SDK 变动受影响 | [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] → `extensions/slack/package.json:1-15`；[[openclaw/nodes/extension-points/openclaw-channel-plugin]] → `src/channels/plugins/types.plugin.ts:53-94` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何区分版本锁定策略

**维度**：Dependency Strategy
**问题陈述**：在 monorepo 中管理异构依赖时，如何决定版本锁定粒度——是对所有依赖统一精确锁定、统一范围版本，还是按依赖风险级别分类锁定？
**核心关切**：
- 关切 1：协议 SDK（如 MCP、ACP）的不兼容变更直接导致功能故障——高风险依赖必须精确锁定
- 关切 2：有 native addon 的包（如 `sqlite-vec`、`node-pty`）版本敏感——native 编译失败难以排查，精确锁定降低风险
- 关切 3：核心 AI 引擎的 breaking change 影响全局——必须精确锁定
- 关切 4：工具类库（如 chalk、commander、uuid）的 patch 变更不影响行为——用范围版本可降低维护负担，但需接受偶尔的不兼容风险

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 精确定位协议/native/核心包，范围版本工具库 | 70 个 runtime deps 中 29 个精确锁定：所有 `@mariozechner/*`、协议 SDK（`@modelcontextprotocol/sdk`、`@agentclientprotocol/sdk`）、有 native addon 的包（`sqlite-vec`、`playwright-core`、`node-pty`）、HTTP 框架 `hono`。41 个范围版本用于工具类库 | [[openclaw/dimensions/openclaw-dependency-strategy]] → `package.json: dependencies` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何管理重型可选依赖

**维度**：Dependency Strategy
**问题陈述**：当系统需要支持可选的重型功能（如本地 LLM 推理 GB 级二进制）时，如何决定可选依赖的分层策略——是全部默认安装、全部可选，还是按安装成本分层管理？
**核心关切**：
- 关切 1：默认安装不应拉入 GB 级二进制（本地 LLM 推理）或复杂原生模块——默认体验的轻量性是用户留存的基础
- 关切 2：需要这些功能的用户必须清楚知道需要额外安装步骤——可发现性与轻量默认之间的张力
- 关切 3：可选依赖缺失时系统应优雅降级而非崩溃——健壮性要求在依赖缺失时不出现硬错误

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Peer 依赖 + Optional 依赖分层 | Peer dependencies（`@napi-rs/canvas`、`node-llama-cpp`）由用户显式安装，不默认拉入；optional dependencies（`@discordjs/opus`、`@matrix-org/matrix-sdk-crypto-nodejs`）缺失时自动降级不崩溃。`node-llama-cpp` 安装体积达 GB 级，故设为 peer 而非 optional——用户必须有意识地安装 | [[openclaw/dimensions/openclaw-dependency-strategy]] → `package.json: peerDependencies, optionalDependencies` |

**Concept 状态**：仅 openclaw—待观察

---

## Testing Philosophy

---

## 如何将架构边界约束从文档变为可执行检查

**维度**：Testing Philosophy
**问题陈述**：在分层架构系统中，如何决定架构边界约束的执行方式——是依赖文档和代码 review 还是将约束编码为 CI 自动检查？
**核心关切**：
- 关切 1：架构边界的规则必须是 CI 可自动检查的，不能仅依赖人的纪律——人的 review 不可靠且不持续
- 关切 2：规则描述需精确到文件路径级别的 import 检测——粒度越细，误报风险越高
- 关切 3：新增架构约束应能低成本添加新的 lint 脚本——检查框架的扩展性决定其长期价值
- 关切 4：检查必须是白名单式（禁止某些 import 模式）而非黑名单式——白名单更安全但更严格，可能阻碍合理的例外

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 20+ 专项 lint 脚本守护架构边界 | `lint:extensions:no-src-outside-plugin-sdk` 禁止 extensions 直接 import `src/` 内部模块；`lint:plugins:no-extension-imports` 禁止 plugin 反向 import extension；`lint:plugins:no-monolithic-plugin-sdk-entry-imports` 禁止 import plugin-sdk 单体入口；`lint:webhook:no-low-level-body-read` 强制 webhook 走正确 body 解析顺序。架构约束从文档变为可执行的 CI gate | [[openclaw/dimensions/openclaw-testing-philosophy]] → `package.json: lint:* scripts`, `scripts/check-ts-max-loc.ts:1-30` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何保证 Plugin 接口稳定性

**维度**：Testing Philosophy
**问题陈述**：在 plugin 系统中，如何决定接口契约的验证策略——是依赖开发者手写测试还是让契约测试自动覆盖所有注册实现？
**核心关切**：
- 关切 1：新 plugin 注册后应自动被现有契约覆盖，零额外测试成本——自动化程度越高，对新 plugin 的约束越强
- 关切 2：契约测试需验证接口行为而不仅是类型签名——行为验证比类型检查更深入但更脆弱
- 关切 3：不同 plugin 的契约测试应能复用同一套 test suite——复用降低维护成本但需测试套件设计足够通用

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 共享 test suite 自动覆盖新注册 plugin | 契约测试以 `installChannelActionsContractSuite(...)` 等共享 test suite 定义，新 channel 注册到 registry 后自动被契约测试覆盖。运行时用 `forks` pool + `isolate: false` 共享注册表状态，不需为每个新 plugin 手写测试 | [[openclaw/dimensions/openclaw-testing-philosophy]] → `src/channels/plugins/contracts/actions.registry-backed.contract.test.ts:1-12` |

**Concept 状态**：仅 openclaw—待观察

---

## 如何将性能预算纳入 CI 门控

**维度**：Testing Philosophy
**问题陈述**：在 CI 管线中，如何决定性能回归的检测策略——是将性能预算编码为 CI 检查还是依赖人工基准测试？
**核心关切**：
- 关切 1：启动时间的退化是渐进的、容易被忽视的质量问题——自动化检测比人工更有持续保障
- 关切 2：CI 需要可重复的基准测量环境（Docker 或固定配置的 runner）——环境差异会导致误报，但锁定环境增加 CI 复杂度
- 关切 3：预算值必须存储在可版本控制的文件中，随代码一起演进——预算值本身需要被治理，过时或过紧的预算同样有害

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | CLI 冷启动时间对比基线 fixture | `test:startup:bench:check` 测量 CLI 冷启动时间，对比 `test/fixtures/cli-startup-bench.json` 中的基线值，超出预算即 CI 失败。启动性能作为一等公民有专用 fixture 文件和独立 CI 检查 | [[openclaw/dimensions/openclaw-testing-philosophy]] → `scripts/test-cli-startup-bench-budget.mjs:1-40`, `test/fixtures/cli-startup-bench.json` |

**Concept 状态**：仅 openclaw—待观察
