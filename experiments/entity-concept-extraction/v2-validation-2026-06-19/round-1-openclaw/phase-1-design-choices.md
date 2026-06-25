# OpenClaw — 设计选择草稿 (Phase 1)

> 独立提取自 openclaw 的 5 维度叙事页 + 17 节点页。未参考任何其他仓库。

---

## 如何门控工具权限

**维度**：Architecture
**问题陈述**：在 AI 助手运行时中，如何在工具执行前可靠地阻止未授权调用，而不依赖事后审计日志？
**核心关切**：
- 安全边界可被代码静态验证——不依赖运行时日志的可审计性
- 门控延迟不影响正常的消息处理吞吐
- 多来源配置（profile/provider/global/agent/group）的叠加规则不产生不可预测的交互
- Exec 类高风险工具需要额外的用户确认回路，但不应阻塞低风险工具

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 5层同步串行Pipeline | 所有工具调用在执行前串行经过5层 allowlist/denylist 过滤，exec 类额外阻塞等待 owner 审批。权限决策在消息处理关键路径上同步完成，不依赖事后审计 | [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]] → `src/agents/tool-policy-pipeline.ts:56-90`；[[openclaw/nodes/components/openclaw-tool-policy]] → `src/agents/tool-policy.ts:19-55` |

**层级**：层 3 架构决策

---

## 如何平衡 Context 压缩的可恢复性与压缩率

**维度**：Performance Tradeoffs
**问题陈述**：AI 助手上下文窗口有限时，如何在压缩历史对话时既减少 token 消耗，又保证 agent 恢复执行时能接续之前的工作状态？
**核心关切**：
- 压缩后的摘要必须保留足够信息以使 agent 可恢复任务执行
- 压缩率需足够高以控制 LLM token 成本
- 工具输出（如 `tool_result.details`）通常冗长但对后续决策价值低，需特殊处理
- Token 估算误差会导致截断——压缩参数需包含安全余量

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 可恢复性优先压缩 | 摘要指令优先保留活跃任务状态、批处理进度、最后一次用户请求；`tool_result.details` 在压缩前 strip；参数用 `SAFETY_MARGIN = 1.2`（20% 缓冲补偿 token 估算误差）。牺牲历史细节完整性换取可恢复性 | [[openclaw/nodes/design-decisions/openclaw-compaction-recoverability-priority]] → `src/agents/compaction.ts:19-40`；[[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27` |

**层级**：层 3 架构决策

---

## 如何优化冷启动速度

**维度**：Performance Tradeoffs
**问题陈述**：用户期望 CLI 助手即时响应，但 Node.js 运行时初始化、模块解析和依赖加载都有固定开销——如何在不显著增加运行时内存占用的前提下最小化冷启动延迟？
**核心关切**：
- 用户感知的首次可用时间（time-to-first-response）尽可能短
- 内存中同时持有多个缓存对象不能导致 OOM
- 新增模块的加载方式必须遵守同一套延迟约束，否则逐次退化
- 启动失败（如 compile cache 损坏）必须静默降级，不能阻塞进程

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 启动速度优先于内存占用 | compile cache（V8 字节码磁盘缓存）+ `createLazyRuntimeModule`（Promise 缓存包装动态 import）+ channel entry 按需懒加载 + NODE_OPTIONS respawn 策略。冷启动被当作一等公民优化，所有重型运行时模块必须走 lazy 加载路径。代价：内存中多个 Promise cache，冷启动多一次 spawn() | [[openclaw/nodes/design-decisions/openclaw-startup-over-memory-tradeoff]] → `src/shared/lazy-runtime.ts:1-44`, `src/entry.ts:52-58`；[[openclaw/nodes/components/openclaw-process-supervisor]] → `src/process/supervisor/index.ts:1-12` |

**层级**：层 3 架构决策

---

## 如何选择 AI 引擎依赖策略

**维度**：Dependency Strategy
**问题陈述**：构建 AI 助手时，核心 agent 引擎（LLM transport、消息类型、session 管理）是自研还是深度绑定一个已有的成熟引擎——如何在开发速度和长期可控性之间取舍？
**核心关切**：
- 快速复用经过验证的 agent 引擎，避免从零实现复杂的 LLM 交互协议
- agent 层是整个产品的核心——替换引擎等价于重写系统
- 上游引擎的版本节奏和 breaking change 直接影响产品迭代计划
- 引擎包之间的版本耦合必须被精确管理，防止隐式不兼容

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 深度绑定 @mariozechner 私有包族 | 442 处 import 完全依赖 `@mariozechner/*` 四件套（pi-ai / pi-agent-core / pi-coding-agent / pi-tui），四个包精确锁定同一版本。代价：agent 层几乎无法在不重写的情况下切换引擎，受上游版本节奏约束 | [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] → `package.json:1-50`；[[openclaw/nodes/extension-points/openclaw-agent-harness]] → `src/agents/harness/types.ts:30-44` |

**层级**：层 3 架构决策

---

## 如何隔离 Channel SDK 故障域

**维度**：Dependency Strategy
**问题陈述**：多平台 IM 助手需要集成 20+ 个第三方 SDK，如何在 monorepo 中防止任意一个 channel SDK 的依赖问题（安全漏洞、breaking change、安装失败）影响其他 channel 或核心运行时？
**核心关切**：
- 单个 channel SDK 的故障（安全漏洞、版本冲突、安装失败）不能影响核心运行时
- 用户只需安装自己使用的 channel，不被迫拉入所有 SDK
- 跨 channel 共享的 plugin 基础设施需要一致接口，但实现完全独立

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Channel SDK 独立声明 + 故障域隔离 | 每个 channel extension 在自身 package.json 中独立声明 SDK 依赖（Slack 用 @slack/bolt、Telegram 用 grammy 等），不在 root package 聚合，通过 `workspace:*` 引用内部 plugin-sdk。核心运行时不因任何单个 channel SDK 变动受影响 | [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] → `extensions/slack/package.json:1-15`；[[openclaw/nodes/extension-points/openclaw-channel-plugin]] → `src/channels/plugins/types.plugin.ts:53-94` |

**层级**：层 3 架构决策

---

## 如何选择 LLM Provider 的实现

**维度**：Extension Points
**问题陈述**：多 provider 环境中，如何在运行时从多个已注册的 LLM harness 实现中选出最合适的一个，而不在 core 中硬编码 provider 优先级？
**核心关切**：
- Core 不感知具体 provider 的存在——新增 provider 不需要修改核心代码
- 同一模型如果被多个 harness 声明支持，需要确定性的选择规则
- 不同 harness 的能力集不同（如是否支持 compact）——选择时必须考虑能力匹配

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 优先级排序 + 能力匹配选择 | `AgentHarness` 接口包含 `supports(ctx)` 方法返回优先级分数，`selectAgentHarness()` 按 priority 排序选最优实现。各 provider（anthropic/openai/ollama/deepseek）在 extensions/ 下独立注册 harness，对 core 完全透明 | [[openclaw/nodes/extension-points/openclaw-agent-harness]] → `src/agents/harness/types.ts:30-44` |

**层级**：层 3 架构决策

---

## 如何管理上下文引擎和记忆能力的全局唯一性

**维度**：Extension Points
**问题陈述**：当多个 plugin 都想提供 context engine 或 memory 实现时，系统如何保证全局只有一个活跃实现，同时允许 plugin 在启动时竞争注册？
**核心关切**：
- Context engine 决定所有 LLM 交互的 prompt 组装方式——同时存在多个必然冲突
- Plugin 应能自由注册自己的实现，但运行时只能激活一个
- 注册顺序应可预测——后注册者覆盖前者

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Exclusive 槽位覆盖注册 | `registerContextEngine` 和 `registerMemoryCapability` 被设计为 exclusive 槽位——全局只能有一个活跃实现，后注册者覆盖前者。这与 `registerHook`（多个 handler 共存）和 `registerChannel`（多个实现并存）的设计截然不同 | [[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27`；[[openclaw/nodes/extension-points/openclaw-compaction-provider]] → `src/plugins/types.ts:1867-1990`；[[openclaw/nodes/components/openclaw-memory-system]] → `src/memory-host-sdk/host/types.ts:1-30` |

**层级**：层 3 架构决策

---

## 如何设计 Prompt 缓存边界

**维度**：Performance Tradeoffs
**问题陈述**：LLM API 的 Prompt Caching 只能缓存连续前缀——如何在 system prompt 中插入缓存边界标记，使得稳定内容（技能定义、人格）命中缓存的同时，动态内容（记忆注入、实时上下文）不破坏缓存连续性？
**核心关切**：
- 尽可能多的 token 命中缓存以减少每轮 API 费用
- 动态内容（记忆、当前上下文）必须放在缓存边界之后，不能混入缓存区
- 不同 LLM 平台的缓存 TTL 策略不同——边界设计需兼容多平台

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 稳定前缀 + 动态后缀分离 | 在 system prompt 中插入 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记，stable prefix 打上 Anthropic `cache_control: { type: "ephemeral" }` 标记。根据不同 API endpoint 决定缓存 TTL（`api.anthropic.com` 支持 `ttl: "1h"` 长缓存，其他端点的缓存时间更短）。动态后缀（记忆注入、实时上下文）在 boundary 后插入，不影响缓存命中 | [[openclaw/nodes/components/openclaw-context-engine]]（维度叙事页） → `src/agents/system-prompt-cache-boundary.ts:3-47`, `src/agents/anthropic-payload-policy.ts:37-65` |

**层级**：层 3 架构决策

---

## 如何在消息驱动的 AI 助手中创建主动触发路径

**维度**：Architecture
**问题陈述**：AI 助手运行时的主体逻辑由 IM 消息驱动（用户发消息 → agent 响应），但定时任务和主动通知需要一条不依赖消息的 agent 运行路径——如何在保持消息驱动为主模型的同时，为定时触发开辟受控的并行路径？
**核心关切**：
- 主动触发路径不应破坏消息驱动模型的清晰性
- 定时触发的执行结果必须可投递回消息通道（channel/thread/announce/webhook）
- 每次定时触发应使用独立的 agent session，不与用户对话 session 混淆

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Cron 作为唯一无消息主动触发入口 | CronScheduler 是唯一可以在无 IM 消息触发的情况下主动发起 agent 运行的入口。每次 cron 触发创建独立 isolated-agent session，`CronDeliveryPlan` 决定结果投递目标（channel/thread/announce/webhook）。所有其他 agent 运行都是消息驱动的 | [[openclaw/nodes/components/openclaw-cron-scheduler]] → `src/cron/delivery-plan.ts:10-19`；[[openclaw/nodes/components/openclaw-task-flow]] → `src/tasks/task-executor.ts:85-112` |

**层级**：层 3 架构决策

---

## 如何设计 Exec 类工具的审批流程

**维度**：Architecture
**问题陈述**：AI 助手执行 shell 命令等高风险工具时，如何既保证用户在命令执行前有机会审核和拒绝，又不因为等待用户响应而阻塞其他 agent 操作？
**核心关切**：
- 审批必须是同步阻塞的——不能在命令执行后才通知用户
- 阻塞等待不应死锁 agent 进程——需要超时和取消机制
- 审批可通过多种路径到达用户（host CLI / gateway HTTP），路径选择应对 core 透明
- 审批失败或超时不应导致 agent session 永久卡死

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 异步阻塞双路径审批 | `ExecApprovalRequest` 注册后 `waitForExecApprovalDecision` 阻塞等待 owner 决策，支持 host/gateway 双路径审批通道。审批在 ToolPolicy 同步门控 pipeline 内部触发，但等待机制是异步的可中断等待，不占用事件循环 | [[openclaw/nodes/extension-points/openclaw-exec-approval-request]] → `src/agents/bash-tools.exec-approval-request.ts:89-126`；[[openclaw/nodes/components/openclaw-tool-policy]] → `src/agents/tool-policy.ts:19-55` |

**层级**：层 3 架构决策

---

## 如何注入记忆到 LLM 上下文

**维度**：Architecture
**问题陈述**：AI 助手需要在对话中注入历史记忆以保持上下文连续性——但记忆检索有延迟（向量搜索），记忆库随时可能写入新内容——是在每次 LLM 调用前实时检索，还是在 prompt 组装的特定阶段一次性注入？
**核心关切**：
- 记忆内容的新鲜度——实时检索可获取最新记忆，但增加延迟
- Prompt 组装阶段的确定性——如果记忆内容在 prompt 构建后变化，可能导致行为不一致
- 多个记忆后端并存（builtin SQLite + qmd 外部引擎 + LanceDB + wiki-style）

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Prompt 组装阶段批量注入 | 记忆在 Context Engine 的 `assemble` 阶段注入，非实时查询。记忆注入通过生命周期 hook（`before_prompt_build`、`before_agent_start`）实现，由 `active-memory` 等扩展负责。代价：同一次 LLM 调用期间新增的记忆在当前轮不可见 | [[openclaw/nodes/components/openclaw-memory-system]] → `src/memory-host-sdk/host/types.ts:1-30`；[[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27` |

**层级**：层 3 架构决策

---

## 如何在无代码情况下扩展 Agent 行为

**维度**：Extension Points
**问题陈述**：plugin 系统需要写 TypeScript 代码并注册到 OpenClawPluginApi——但对于只想定制 agent 行为但不写代码的最终用户，如何在完全不写代码的情况下让 agent 获得新的技能和行为模式？
**核心关切**：
- 零代码门槛——用户只需编辑文本文件
- 扩展内容需注入到 agent 的 system prompt，影响 LLM 行为
- 扩展内容可作为 agent 可调用的命令暴露，不仅是被动的 prompt 指令
- 与 plugin 系统互补，不冲突——同一系统内两种扩展机制共存

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Markdown 技能文件作为第三层扩展 | 用户在工作区放置 Markdown 技能文件，`buildWorkspaceSkillsPrompt` 将内容注入 agent system prompt，`buildWorkspaceSkillCommandSpecs` 将技能文件中的命令 spec 注册为可用命令。不需要代码，纯 Markdown 即可定制 agent 行为。与声明式 plugin manifest（`openclaw.plugin.json`）和命令式 plugin API 构成三层扩展体系 | [[openclaw/nodes/extension-points/openclaw-skills-extension]] → `src/agents/skills.ts:8-39` |

**层级**：层 3 架构决策

---

## 如何将架构边界约束从文档变为可执行检查

**维度**：Testing Philosophy
**问题陈述**：当系统有明确的层级架构（core/extensions/plugins），如何防止开发者——特别是外部 contributor——无意中违反层间依赖规则，只能依赖代码 review 来发现架构违规？
**核心关切**：
- 架构边界的规则必须是 CI 可自动检查的，不能仅依赖人的纪律
- 规则描述需精确到文件路径级别的 import 检测
- 新增的架构约束应能低成本添加新的 lint 脚本
- 检查必须是白名单式（禁止某些 import 模式），而非黑名单式

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 20+ 专项 lint 脚本守护架构边界 | `lint:extensions:no-src-outside-plugin-sdk` 禁止 extensions 直接 import `src/` 内部模块；`lint:plugins:no-extension-imports` 禁止 plugin 反向 import extension；`lint:plugins:no-monolithic-plugin-sdk-entry-imports` 禁止 import plugin-sdk 单体入口；`lint:webhook:no-low-level-body-read` 强制 webhook 走正确 body 解析顺序。架构约束从文档变为可执行的 CI gate | [[openclaw/dimensions/openclaw-testing-philosophy]] → `package.json: lint:* scripts`, `scripts/check-ts-max-loc.ts:1-30` |

**层级**：层 3 架构决策

---

## 如何保证 Plugin 接口稳定性

**维度**：Testing Philosophy
**问题陈述**：当系统定义了标准接口契约（ChannelPlugin、AgentHarness 等），新增的 plugin 实现如何自动验证其符合契约，而不依赖开发者手写测试或人工检查？
**核心关切**：
- 新 plugin 注册后应自动被现有契约覆盖，零额外测试成本
- 契约测试需验证接口行为而不仅是类型签名
- 不同 plugin 的契约测试应能复用同一套 test suite

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 共享 test suite 自动覆盖新注册 plugin | 契约测试以 `installChannelActionsContractSuite(...)` 等共享 test suite 定义，新 channel 注册到 registry 后自动被契约测试覆盖。运行时用 `forks` pool + `isolate: false` 共享注册表状态，不需为每个新 plugin 手写测试 | [[openclaw/dimensions/openclaw-testing-philosophy]] → `src/channels/plugins/contracts/actions.registry-backed.contract.test.ts:1-12` |

**层级**：层 3 架构决策

---

## 如何区分版本锁定策略

**维度**：Dependency Strategy
**问题陈述**：monorepo 中的依赖有不同的变更风险和兼容性保证——有 native addon 的包、协议 SDK、工具类库——如何根据依赖的类型和风险级别采用不同的版本锁定策略，既防止不兼容变更又不过度限制正常升级？
**核心关切**：
- 协议 SDK（如 MCP、ACP）的不兼容变更直接导致功能故障——必须精确锁定
- 有 native addon 的包版本敏感——native 编译失败难以排查
- 核心 AI 引擎的 breaking change 影响全局——必须精确锁定
- 工具类库（chalk、commander、uuid）的 patch 变更不影响行为——用范围版本降低维护负担

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 精确定位协议/native/核心包，范围版本工具库 | 70 个 runtime deps 中 29 个精确锁定：所有 `@mariozechner/*`、协议 SDK（`@modelcontextprotocol/sdk`、`@agentclientprotocol/sdk`）、有 native addon 的包（`sqlite-vec`、`playwright-core`、`node-pty`）、HTTP 框架 `hono`。41 个范围版本用于工具类库 | [[openclaw/dimensions/openclaw-dependency-strategy]] → `package.json: dependencies` |

**层级**：层 2 技术选型

---

## 如何管理重型可选依赖

**维度**：Dependency Strategy
**问题陈述**：系统需要支持可选功能（如本地 LLM 推理、Canvas 渲染、Discord 语音、Matrix E2E 加密），但这些功能的依赖体积巨大（GB 级本地 LLM）或有复杂的原生编译需求——如何在默认安装不拉入重型依赖的同时，让需要它们的用户能按需安装？
**核心关切**：
- 默认安装不应拉入 GB 级二进制（本地 LLM 推理）或复杂原生模块
- 需要这些功能的用户清楚知道需要额外安装步骤
- 缺失时系统应优雅降级而非崩溃

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Peer 依赖 + Optional 依赖分层 | Peer dependencies（`@napi-rs/canvas`、`node-llama-cpp`）由用户显式安装，不默认拉入；optional dependencies（`@discordjs/opus`、`@matrix-org/matrix-sdk-crypto-nodejs`）缺失时自动降级不崩溃。`node-llama-cpp` 安装体积达 GB 级，故设为 peer 而非 optional——用户必须有意识地安装 | [[openclaw/dimensions/openclaw-dependency-strategy]] → `package.json: peerDependencies, optionalDependencies` |

**层级**：层 2 技术选型

---

## 如何防止 Context Window 不足导致截断失败

**维度**：Performance Tradeoffs
**问题陈述**：不同 LLM 模型的 context window 大小差异巨大（16K 到 200K+），运行时的实际 token 消耗受 prompt 组装、工具输出、历史对话共同影响——如何在没有精确 token 计数的前提下，安全地防止上下文超出窗口导致请求失败或静默截断？
**核心关切**：
- 必须在多个来源（modelsConfig / model 自报 / agentContextTokens）中选最保守值——宁可过早触发压缩
- Token 估算误差不可避免（尤其是工具输出的实际大小）——需留安全余量
- 压缩触发线如果设得太低，不必要的压缩浪费 LLM 调用成本

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 硬限制 + 软警告 + 多源保守选择 | 硬下限 `CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000`，软警告线 `CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000`，在 modelsConfig、model 自报、agentContextTokens 之间按优先级选最保守值。实际压缩触发由 `BASE_CHUNK_RATIO = 0.4` 和 `SAFETY_MARGIN = 1.2` 共同决定 | [[openclaw/dimensions/openclaw-performance-tradeoffs]] → `src/agents/context-window-guard.ts:4-81`, `src/agents/compaction.ts:19-40` |

**层级**：层 2 技术选型

---

## 如何分解 Channel Plugin 的适配器接口

**维度**：Extension Points
**问题陈述**：一个 IM 平台插件涉及消息收发、生命周期管理、认证、环境配置等多种职责——如何将一个复杂 channel plugin 的接口设计拆分为可独立实现的适配器，让平台开发者能按需实现而不必全部覆盖？
**核心关切**：
- 不同 IM 平台的能力差异巨大——不是所有平台都支持所有操作
- 核心对 channel 的调用路径（入站解析、出站发送、生命周期）需要统一的接口约定
- 新增平台的工作量应与所需能力成正比——简单平台不应被迫实现复杂接口

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 13+ Adapter 分解 | `ChannelPlugin<ResolvedAccount>` 接口拆分为 13+ Adapter：`ChannelMessagingAdapter`、`ChannelOutboundAdapter`、`ChannelLifecycleAdapter`、`ChannelAuthAdapter`、`ChannelSetupAdapter` 等。每个 adapter 是可选的——平台只实现自己支持的维度。通过 `defineBundledChannelEntry` 统一注册入口 | [[openclaw/nodes/extension-points/openclaw-channel-plugin]] → `src/channels/plugins/types.plugin.ts:53-94`；[[openclaw/dimensions/openclaw-extension-points]] → `src/plugin-sdk/channel-entry-contract.ts:31-60` |

**层级**：层 3 架构决策

---

## 如何提供 Plugin SDK 的双入口模式

**维度**：Extension Points
**问题陈述**：plugin 系统的使用者分为两类——provider/tool 类插件相对轻量，希望简单注册；channel 类插件包含大量平台 SDK 代码，需要在未使用时避免加载——如何用不同的注册入口满足两类场景？
**核心关切**：
- Provider/tool 插件应有一个简单的注册入口，无需关心加载优化
- Channel 插件包含重量级 SDK（如 `@slack/bolt`），必须懒加载以避免未配置的 channel 拖慢启动
- 两种入口应共享同一套底层 plugin API，避免分裂

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `definePluginEntry` + `defineBundledChannelEntry` 双入口 | `definePluginEntry` 用于 provider/tool/command/service/memory/context-engine 类插件——简单的 register 回调；`defineBundledChannelEntry` 用于 channel 类插件——接受 `{ plugin, secrets, runtime, registerFull }` 四个模块引用，channel 代码通过 `loadBundledEntryExportSync` 按需懒加载。两种入口最终都通过 `OpenClawPluginApi` 注册 | [[openclaw/dimensions/openclaw-extension-points]] → `src/plugin-sdk/plugin-entry.ts:181-206`, `src/plugin-sdk/channel-entry-contract.ts:31-60` |

**层级**：层 3 架构决策

---

## 如何将生命周期 Hook 设计为扩展拦截面

**维度**：Extension Points
**问题陈述**：AI 助手的运行生命周期有多个关键节点（LLM 调用前后、消息收发、session 开始结束、工具调用），如何设计一个 hook 系统让 plugin 能在任意节点拦截和修改行为，同时保证 hook 的注入不影响核心路径的稳定性？
**核心关切**：
- Hook handler 可能修改核心数据（如 system prompt）——需明确区分可修改和只读的 hook
- Hook 数量需要覆盖主要生命周期节点，但不应无限膨胀
- 每个 hook 可注册多个 handler，执行顺序和失败处理需可预测
- Prompt 注入类 hook 是记忆等系统的唯一入口——稳定性和性能要求极高

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 28 个命名生命周期 Hook | `registerHook(events, handler)` 支持 28 个生命周期 hook 名，覆盖从 `before_model_resolve` 到 `agent_end` 的完整链路。Prompt 注入类 hook（`before_prompt_build`、`before_agent_start`）允许 plugin 在 LLM 调用前修改 system prompt——是 active-memory 和记忆注入的唯一入口。同一 hook 支持多个 handler 共存 | [[openclaw/nodes/extension-points/openclaw-hook-system]] → `src/plugins/hook-types.ts:55-84`, `src/plugins/hook-types.ts:128-133` |

**层级**：层 3 架构决策

---

## 如何将性能预算纳入 CI 门控

**维度**：Testing Philosophy
**问题陈述**：启动速度是用户感知的关键质量指标，但其退化通常是渐进的（每次改动增加几十 ms，累积后显著变慢）——如何在 CI 中自动检测启动性能回归，而不依赖人工基准测试？
**核心关切**：
- 启动时间的退化是渐进的、容易被忽视的质量问题
- CI 需要可重复的基准测量环境——Docker 或固定配置的 runner
- 预算值必须存储在可版本控制的文件中，随代码一起演进

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | CLI 冷启动时间对比基线 fixture | `test:startup:bench:check` 测量 CLI 冷启动时间，对比 `test/fixtures/cli-startup-bench.json` 中的基线值，超出预算即 CI 失败。启动性能作为一等公民有专用 fixture 文件和独立 CI 检查 | [[openclaw/dimensions/openclaw-testing-philosophy]] → `scripts/test-cli-startup-bench-budget.mjs:1-40`, `test/fixtures/cli-startup-bench.json` |

**层级**：层 2 技术选型

---

## 如何管理消息入站的突发流

**维度**：Performance Tradeoffs
**问题陈述**：用户经常分多条消息发送一个问题（"帮我看看这个bug" + 粘贴 stack trace + "是什么原因"），如果每条消息都立即触发 agent 处理，会产生多次冗余的 LLM 调用——如何在不过度延迟用户感知响应时间的前提下合并关联消息？
**核心关切**：
- 合并窗口太长——用户感觉助手响应慢
- 合并窗口太短——仍会产生多余的 LLM 调用
- 不同 channel 的消息到达模式不同——合并策略需可配置

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Inbound 消息防抖合并 | 消息入站时做防抖，合并短时间内连续到达的多条消息再交给 agent 处理。防抖窗口由 channel plugin 的 `defaults.queue.debounceMs` 配置，不同 channel 可设置不同窗口。开销：引入最大 debounce 延迟 | [[openclaw/dimensions/openclaw-performance-tradeoffs]] → `src/channels/inbound-debounce-policy.ts:11-51` |

**层级**：层 2 技术选型

---

## 设计选择覆盖总览

| # | 设计问题 | 维度 | 层级 |
|---|---------|------|------|
| 1 | 如何门控工具权限 | Architecture | 3 |
| 2 | 如何平衡压缩可恢复性与压缩率 | Performance Tradeoffs | 3 |
| 3 | 如何优化冷启动速度 | Performance Tradeoffs | 3 |
| 4 | 如何选择 AI 引擎依赖策略 | Dependency Strategy | 3 |
| 5 | 如何隔离 Channel SDK 故障域 | Dependency Strategy | 3 |
| 6 | 如何选择 LLM Provider 实现 | Extension Points | 3 |
| 7 | 如何管理引擎全局唯一性 | Extension Points | 3 |
| 8 | 如何设计 Prompt 缓存边界 | Performance Tradeoffs | 3 |
| 9 | 如何创建主动触发路径 | Architecture | 3 |
| 10 | 如何设计 Exec 审批流程 | Architecture | 3 |
| 11 | 如何注入记忆到 LLM 上下文 | Architecture | 3 |
| 12 | 如何无代码扩展 Agent 行为 | Extension Points | 3 |
| 13 | 如何守护架构边界 | Testing Philosophy | 3 |
| 14 | 如何保证 Plugin 接口稳定性 | Testing Philosophy | 3 |
| 15 | 如何区分版本锁定策略 | Dependency Strategy | 2 |
| 16 | 如何管理重型可选依赖 | Dependency Strategy | 2 |
| 17 | 如何防止 Context Window 截断 | Performance Tradeoffs | 2 |
| 18 | 如何分解 Channel Plugin 适配器 | Extension Points | 3 |
| 19 | 如何提供 Plugin SDK 双入口 | Extension Points | 3 |
| 20 | 如何设计生命周期 Hook 体系 | Extension Points | 3 |
| 21 | 如何将性能预算纳入 CI | Testing Philosophy | 2 |
| 22 | 如何管理消息入站突发流 | Performance Tradeoffs | 2 |
