# 设计选择种子库

> 最后更新：openclaw + hermes + nanobot（2026-06-17）

---

## 如何让 LLM provider 的接口粒度恰到好处？

**维度**：Architecture
**问题陈述**：如何让不同能力的 LLM provider 都能接入 agent 框架，而不强制所有 provider 实现完整的接口契约？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `compact?` 和 `reset?` 设计为可选方法 | 可选方法让轻量 provider 无需实现完整协议即可接入 | entity/openclaw-agent-harness.md → src/agents/harness/types.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何让子系统被框架发现和自动选择？

**维度**：Extension Points
**问题陈述**：如何让多个同类型子系统（如 LLM provider）被框架自动发现并按优先级选择，而不在 core 中硬编码选择逻辑？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `supports(ctx)` + priority 排序的策略模式 | plugin 自主声明适用场景，core 按 priority 选第一个匹配的 harness | entity/openclaw-agent-harness.md → src/agents/harness/types.ts |
| hermes | AST 扫描自动发现 `registry.register()` 顶层调用 | 新工具只需在文件顶层调用 registry.register()，不需要修改任何现有文件；代价是依赖静态分析约定（只扫描顶层调用） | entity/hermes-tool-registry.md → tools/registry.py:28-73 |
| nanobot | pkgutil + entry_points 双层 Channel 发现，内置包优先覆盖第三方 | 内置 pkgutil 扫描 channels/ 自动发现，entry_points 支持 pip 可安装第三方插件，内置优先防止同名劫持 | entity/nanobot-channel-system.md → channels/registry.py:23, channels/registry.py:42-55 |
| nanobot | 显式 `register()`——不做 AST 扫描、装饰器发现、模块自省 | 每个工具在 `_register_default_tools()` 中点名注册，builtins 按名称排序保证 prompt cache 稳定前缀 | entity/nanobot-tool-registry.md → agent/tools/registry.py:8-18, agent/loop.py:225-229 |

**Concept 状态**：已升级 → [[concept/plugin-subsystem-auto-discovery]]

---

## 如何组织所有子系统的实例化和连线以最大化可发现性？

**维度**：Architecture
**问题陈述**：如何组织所有子系统的实例化和连线，使系统的整体构成具有最大可发现性？单体 hub 构造函数、依赖注入容器、分散初始化，还是 plugin registry + 懒加载？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 单体 Hub 集中式组装 | 所有子系统在一个构造函数中实例化和连线，读一个函数即知全貌 | entity/nanobot-agent-loop.md → agent/loop.py:115-228 |
| openclaw | Plugin Manifest Registry + 按 scope 懒加载 + 运行时动态选择 | 双层 registry（manifest registry + harness registry），插件按需加载，新增 provider 需 manifest + 接口实现 | entity/openclaw-agent-harness.md → src/plugins/manifest-registry.ts, src/agents/harness/registry.ts |
| hermes | 构造函数集中式顺序组装（~1072 行 `__init__()`） | AIAgent 构造函数内完成所有子系统实例化，顺序明确但耦合度高 | entity/hermes-ai-agent.md → run_agent.py |

**Concept 状态**：已升级 → [[concept/subsystem-assembly-visibility]]

---

## 如何管理对外部私有核心库的深度依赖？

**维度**：Dependency Strategy
**问题陈述**：如何复用成熟的第三方 AI agent 引擎，同时控制替换成本和上游版本耦合风险？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | agent 层深度依赖 `@mariozechner/*` 私有包族（442 处 import，锁定 0.66.1） | 快速复用成熟引擎，代价是替换成本极高 | entity/openclaw-agent-harness.md → src/agents/harness/types.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何适配多 LLM 供应商而不引入第三方转发层？

**维度**：Dependency Strategy
**问题陈述**：如何适配 20+ LLM 供应商的 API 差异，同时避免第三方转发层（如 litellm）的不可控风险？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 移除 litellm，自行维护原生 SDK 适配层 | 使用 openai + anthropic 原生 SDK，Provider 适配代码 3,719 行全部自控，5 种 backend 覆盖 20+ 供应商，零间接供应商依赖 | entity/nanobot-llm-provider.md → providers/base.py, providers/registry.py |

**Concept 状态**：仅 nanobot—待观察（候选 Concept「LLM Provider Integration Strategy」）

---

## 如何隔离 plugin 依赖的故障域？

**维度**：Dependency Strategy
**问题陈述**：如何让多个 channel plugin 的依赖互相隔离，避免单个 channel 的 SDK 变动影响核心运行时？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 每个 channel 是独立 npm 包，通过 `workspace:*` 引用内部 plugin-sdk | 故障域完全隔离，用户按需安装 channel | entity/openclaw-channel-plugin.md → src/channels/plugins/types.plugin.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何避免启动时加载所有 plugin 代码？

**维度**：Performance Tradeoffs
**问题陈述**：如何在多 channel 场景下避免启动时加载全部 channel 代码，从而减少冷启动延迟和内存占用？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `defineBundledChannelEntry` 懒加载，channel 代码仅在首次使用时加载 | 多数用户只配少数 channel，懒加载避免浪费 | entity/openclaw-channel-plugin.md → src/plugin-sdk/channel-entry-contract.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何处理用户分条发送消息导致的重复 LLM 调用？

**维度**：Performance Tradeoffs
**问题陈述**：如何合并短时间内连续到达的多条消息，减少因此触发的多余 LLM 调用？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 入站消息防抖（`inbound-debounce-policy`），合并短时间内的多条消息 | 减少碎片化消息导致的重复 LLM 调用，代价是引入 debounce 延迟 | entity/openclaw-channel-plugin.md → src/channels/inbound-debounce-policy.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何在压缩对话历史时保留关键任务状态？

**维度**：Performance Tradeoffs
**问题陈述**：如何在 LLM context window 接近上限压缩历史时，保留关键的任务状态和进度，使长任务不因压缩而中断？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 压缩时优先保留活跃任务状态、批处理进度、最后一次用户请求 | 可恢复性优先于最大化压缩率，避免任务中断需用户重新说明 | entity/openclaw-context-engine.md → src/agents/compaction.ts |
| hermes | 结构化摘要模板 + token-budget tail 保护 | 摘要模板确保关键信息不丢失，token-budget tail 保留最近对话的语义连续性 | entity/hermes-context-engine.md → agent/context_compressor.py:1-60 |
| nanobot | 四层透明治理（Backfill → Microcompact → Budget → Snip），对 LLM 完全透明 | 纯规则压缩，不使用 LLM 生成摘要；Backfill 修复孤立 tool_use 后裁剪，Microcompact 压缩旧 tool result，Budget 截断单结果，Snip 从尾部按 token 预算裁剪 | entity/nanobot-agent-runner.md → agent/runner.py:102-107, agent/runner.py:553-640 |

**Concept 状态**：已升级 → [[concept/context-compression-quality]]

---

## 如何降低 LLM system prompt 的 token 输入成本？

**维度**：Performance Tradeoffs
**问题陈述**：如何在每次对话轮次中复用 system prompt 的稳定部分，减少重复传输相同内容的 token 开销？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `OPENCLAW_CACHE_BOUNDARY` 标记切分稳定前缀和动态后缀，命中 Anthropic Prompt Caching | 稳定内容跨轮次不变时命中缓存，大幅降低输入成本 | entity/openclaw-context-engine.md → src/agents/system-prompt-cache-boundary.ts |
| hermes | 跨消息缓存 AIAgent 实例，非每条消息新建 | 复用实例保持 LLM API 层的 prompt cache prefix 在跨消息对话中持续有效，降低 input token 成本 | entity/hermes-gateway-platform.md → gateway/run.py:604-611 |
| nanobot | 六层固定顺序纯函数式 ContextBuilder，以构造纪律替代显式边界标记 | identity → bootstrap → memory → always skills → skills summary → recent history 固定顺序，不依赖运行时状态，保证 prompt cache 稳定前缀 | entity/nanobot-context-builder.md → agent/context.py:17, agent/context.py:30-63 |

**Concept 状态**：已升级 → [[concept/llm-input-token-cost-reduction]]

---

## 如何避免多个 context engine 实现并存的状态冲突？

**维度**：Extension Points
**问题陈述**：如何为控制全局对话状态的子系统提供扩展点，同时防止多个实现并存导致状态冲突？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `registerContextEngine` 为独占槽位，全局只能有一个活跃实现 | 独占设计强制明确选择，避免多个实现隐式竞争对话状态 | entity/openclaw-context-engine.md → src/context-engine/index.ts |
| hermes | ContextEngine ABC 接口，第三方实现放入 `plugins/context_engine/` | 不同场景需求不同（代码场景需保留代码块、对话场景重语义连续性）；插件化允许外部开发者实验不同压缩算法 | entity/hermes-context-engine.md → agent/context_engine.py:32-60 |

**Concept 状态**：已升级 → [[concept/context-engine-singleton-vs-pluggable]]

---

## 如何减少压缩摘要中的噪声？

**维度**：Architecture
**问题陈述**：如何防止冗长的工具输出污染对话压缩摘要，从而提高摘要质量并减少摘要本身的 token 消耗？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `tool_result.details` 在压缩前被 strip，不参与摘要生成 | 长文件读取等冗长工具输出不适合作为摘要素材，去除后显著提高摘要质量 | entity/openclaw-context-engine.md → src/agents/compaction.ts |
| hermes | 工具输出修剪（先剪后摘要） | 在摘要生成前先裁剪冗长工具输出，减少噪声注入摘要 | entity/hermes-context-engine.md → agent/context_compressor.py:1-60 |
| nanobot | Microcompact + Budget 纯规则裁剪，不使用 LLM 生成摘要 | Microcompact 压缩 10 轮前 tool result 为一行，Budget 截断超大单结果；无 LLM 调用，零摘要噪声 | entity/nanobot-agent-runner.md → agent/runner.py:553-640 |

**Concept 状态**：已升级 → [[concept/context-compression-quality]]

---

## 如何让控制平面和 AI 执行层解耦？

**维度**：Architecture
**问题陈述**：如何将网络边界层的路由/认证职责与 AI 执行层的模型调用职责分离，使两者可独立扩展和替换？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Gateway 是纯 HTTP 路由层，不包含 AI 调用逻辑 | 控制平面与 AI 执行层分离，各自独立扩展 | entity/openclaw-gateway.md → src/gateway/ |

**Concept 状态**：仅 openclaw—待观察

---

## 如何让执行引擎不耦合到产品层逻辑以跨场景复用？

**维度**：Architecture
**问题陈述**：如何让 LLM 执行引擎在不同使用场景（主 agent / 子 agent / 记忆处理 / Cron 定时任务）间复用，而不耦合 channel、session 等产品层概念？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | AgentRunner 纯数据接口，完全不持有 channel/session/cron 引用 | 只接受 messages 和 tool_registry 纯数据输入，产品层桥接由 AgentLoop 完成 | entity/nanobot-agent-runner.md → agent/runner.py:83-89 |
| openclaw | pi-agent-core 委托，channel/gateway 信息作为参数透传 | 核心执行委托给第三方库 `@mariozechner/pi-agent-core`，但外层透传 40+ channel 字段 | entity/openclaw-agent-harness.md → src/agents/pi-embedded-runner/ |
| hermes | AIAgent 耦合编排器，同时处理编排和平台适配 | `run_agent.py` 同时包含 LLM 循环编排和 session/gateway 适配逻辑 | entity/hermes-ai-agent.md → run_agent.py |

**Concept 状态**：已升级 → [[concept/execution-engine-decoupling]]

---

## 如何让 plugin 向控制平面注入自定义 API？

**维度**：Extension Points
**问题陈述**：如何让 channel plugin 能与 gateway 直接通信，而不必绕道事件/hook 系统？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `registerGatewayMethod` 允许 plugin 向 Gateway 注入 RPC 方法 | channel plugin 的审批协议等场景需与 gateway 直接通信，开放此路径比绕道 hook 更直接 | entity/openclaw-gateway.md → src/gateway/ |

**Concept 状态**：仅 openclaw—待观察

---

## 不同来源的消息如何统一进入处理管线？

**维度**：Architecture
**问题陈述**：如何让不同来源的消息（IM / 子 agent / Cron / Heartbeat）统一进入 AgentLoop 处理，而不区分为不同路径？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | asyncio.Queue 极简事件总线（两个单向队列 inbound/outbound） | Channel 和 AgentLoop 完全解耦，入站不区分来源，所有消息无差别进入同一队列 | entity/nanobot-message-bus.md → bus/queue.py:8-20 |

**Concept 状态**：仅 nanobot—待观察（候选 Concept「Message Bus Architecture」）

---

## 如何在正确的时机注入记忆？

**维度**：Architecture
**问题陈述**：如何确定记忆注入 LLM context 的最佳时机——是 prompt 组装阶段一次性注入，还是每轮对话动态检索？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 记忆在 prompt 组装阶段注入，而非每次 LLM 输出后实时查询 | 确保记忆在 LLM 调用前稳定存在，避免记忆检索消耗额外 LLM 调用 | entity/openclaw-memory-system.md → src/memory-host-sdk/host/types.ts |
| hermes | 后台异步预取（queue_prefetch），下一轮使用上一轮完成后的缓存结果 | 记忆检索不在 LLM API 调用关键路径上阻塞；代价是记忆可能落后一轮 | entity/hermes-memory-manager.md → agent/memory_provider.py:106-112 |
| nanobot | Consolidator 独立 provider + asyncio.create_task 异步后台压缩 | 不共享主 agent provider 实例，压缩失败不影响正在进行对话，结果下一轮 context 组装时生效 | entity/nanobot-memory-system.md → agent/memory.py:346-365, agent/loop.py:470-474 |

**Concept 状态**：已升级 → [[concept/memory-retrieval-timing]]

---

## 如何让向量存储后端可替换？

**维度**：Extension Points
**问题陈述**：如何在不同部署环境中灵活选择记忆后端，同时保持默认方案开箱即用？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | `registerMemoryCapability` 为独占槽位，底层实现（SQLite-vec、LanceDB 等）完全可替换 | 高级用户可接入专业向量数据库，默认内置方案开箱即用 | entity/openclaw-memory-system.md → src/memory-host-sdk/host/types.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何选择本地向量搜索的后端技术？

**维度**：Dependency Strategy
**问题陈述**：如何在本地部署场景下选择向量搜索后端，平衡性能、依赖复杂度和兼容性？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 内置 backend 使用 `sqlite-vec`（SQLite 向量扩展，native addon，精确版本锁定） | 复用已有 SQLite 基础设施，native addon 性能优，精确锁定避免编译版本不兼容 | entity/openclaw-memory-system.md → src/memory-host-sdk/host/types.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何让 plugin 扩展协议同时支持静态声明和动态注册？

**维度**：Extension Points
**问题陈述**：如何为 plugin 提供扩展协议，使静态元数据和运行时动态注册各得其所？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 两层扩展协议并存——声明式 manifest（静态元数据）+ 命令式 API（运行时注册） | manifest 适合描述 provider 名、认证变量等静态信息，命令式 API 适合运行时动态注册工具/hook/服务 | entity/openclaw-plugin-hook-system.md → src/plugins/types.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何降低 agent 能力扩展的门槛？

**维度**：Extension Points
**问题陈述**：如何让非开发者也能定制 agent 的行为，而不必编写 TypeScript plugin 代码？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 提供纯 Markdown Skills 文件作为最轻量的第三层扩展，无需任何代码 | agent 行为定制本质上是 prompt 工程，用 Markdown 表达比写代码更自然 | entity/openclaw-plugin-hook-system.md → src/agents/skills.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何细分生命周期 hook 以支持不同 plugin 的介入时机？

**维度**：Extension Points
**问题陈述**：如何让不同 plugin 在各自需要的粒度上介入生命周期，而不在单一通用 hook 内部再做过滤？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 28 个生命周期 hook 覆盖从消息入站到 agent 结束的完整链路 | 细粒度 hook 使每个 plugin 只订阅自己需要的节点 | entity/openclaw-plugin-hook-system.md → src/plugins/hook-types.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何让内容变换钩子和事件通知钩子采用不同组合策略？

**维度**：Extension Points
**问题陈述**：如何让内容变换钩子和事件通知钩子采用不同的组合策略，以适应它们各自的语义？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | finalize_content 管道串联 + 其余方法扇出 | 内容变换适合逐步加工（一个 hook 输出是下一个输入），事件通知适合互不阻塞（所有 hook 独立并行触发） | entity/nanobot-agent-hook.md → agent/hook.py:57 |

**Concept 状态**：仅 nanobot—待观察（候选 Concept「Hook Composition Strategy: Pipeline vs Fan-out」）

---

## 如何确保所有 plugin 的接口兼容性？

**维度**：Testing Philosophy
**问题陈述**：如何让新 plugin 无需手写测试即可验证其接口兼容性，同时保证所有已注册 plugin 的一致性？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 契约测试（`installChannelActionsContractSuite`）自动覆盖所有注册到 registry 的 channel/plugin | 共享 test suite + 自动覆盖确保接口一致性，新 plugin 零测试门槛 | entity/openclaw-plugin-hook-system.md → src/plugins/types.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何加速 CLI 工具的冷启动？

**维度**：Performance Tradeoffs
**问题陈述**：如何减少 Node.js CLI 工具的冷启动延迟，特别是对频繁启动的个人工具？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 启动时第一步调用 `enableCompileCache()`，将 V8 字节码缓存到磁盘，失败时静默降级 | 跳过重复 JS 解析加速冷启动，静默降级保证兼容性 | entity/openclaw-process-supervisor.md → src/entry.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何在需要时安全地修改 Node.js 进程运行参数？

**维度**：Performance Tradeoffs
**问题陈述**：如何在运行时需要修改 NODE_OPTIONS 等环境变量时，安全地重启进程而不进入循环？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 通过 respawn 重启进程（`buildCliRespawnPlan`），`OPENCLAW_NODE_OPTIONS_READY=1` 防循环 | NODE_OPTIONS 必须在进程启动时设置，respawn 是唯一安全途径 | entity/openclaw-process-supervisor.md → src/entry.respawn.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何管理子进程的生命周期？

**维度**：Architecture
**问题陈述**：如何在多个子系统需要管理子进程时，统一生命周期观测和协调，避免分散管理导致的不可见性？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Process Supervisor 以单例模式暴露（`getProcessSupervisor()`），全局统一管理子进程 | 集中管理使 respawn 策略、状态机和日志追踪可统一处理 | entity/openclaw-process-supervisor.md → src/process/supervisor/ |

**Concept 状态**：仅 openclaw—待观察

---

## 如何让定时任务不污染用户对话历史？

**维度**：Architecture
**问题陈述**：如何让无 IM 消息触发的定时任务独立运行，而不将任务输出混入用户的即时消息对话 context？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Cron 使用 isolated-agent 模式，每次触发创建独立 agent session | 周期性任务互不干扰，不会污染用户对话历史 | entity/openclaw-task-cron.md → src/cron/ |

**Concept 状态**：仅 openclaw—待观察

---

## 如何让定期唤醒兼具确定性和 LLM 主动性？

**维度**：Architecture
**问题陈述**：如何让定期唤醒机制兼具确定性调度和 LLM 基于上下文的主动判断？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | Heartbeat 单工具 LLM 调用 + Cron 确定性调度 | Heartbeat 用仅含 skip/run 的虚拟 tool 让 LLM 基于上下文判断是否需要执行；Cron 覆盖确定的 at/every/cron 时间触发 | entity/nanobot-cron-heartbeat.md → heartbeat/service.py:25-30, heartbeat/service.py:88-111; cron/service.py:65 |

**Concept 状态**：仅 nanobot—待观察（候选 Concept「Scheduled Wake-up: Deterministic vs LLM-Judged」）

---

## 如何保证长任务状态在进程重启后可恢复？

**维度**：Architecture
**问题陈述**：如何在多步骤长任务跨多轮对话执行时，确保任务状态在进程重启（或 respawn）后不丢失？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | TaskFlow 状态持久化到 SQLite，支持 cancel 传播和 block retry | SQLite 持久化确保任务状态在进程重启后可恢复 | entity/openclaw-task-cron.md → src/tasks/task-flow-registry.store.sqlite.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 会话数据如何存储以兼顾可读性和正确性？

**维度**：Architecture
**问题陈述**：如何存储和加载会话数据，使其追加友好、人类可读，且发给 LLM 的历史始终从合法边界开始？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | JSONL 文件 + 惰性加载 + 合法边界裁剪（对齐 user-turn） | JSONL 逐行追加无锁竞争，get_or_create 首次访问才加载，裁剪对齐到 user-turn 避免孤立的 tool 调用 | entity/nanobot-session-manager.md → session/manager.py:96, session/manager.py:69, session/manager.py:119 |

**Concept 状态**：仅 nanobot—待观察

---

## 如何减少长时间命令的轮询开销？

**维度**：Performance Tradeoffs
**问题陈述**：如何在监控长时间运行的命令时减少空轮询开销，同时不在有新输出时引入过大延迟？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 长时间无输出的命令轮询使用指数退避（5s → 10s → 30s → 60s），有新输出时立即重置为 5s | 最坏情况 60s 延迟，大幅减少空轮询 CPU 开销 | entity/openclaw-task-cron.md → src/tasks/task-executor.ts |

**Concept 状态**：仅 openclaw—待观察

---

## 如何在关键路径上做工具权限控制？

**维度**：Architecture
**问题陈述**：如何在 LLM 看到可用工具之前就完成权限过滤，从根本上阻止未授权工具的调用？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 权限决策在消息处理关键路径上做同步门控，工具集在进入 LLM 之前已过滤完毕 | 事前门控阻止未授权工具进入 function-calling 视野，预防而非补救 | entity/openclaw-tool-policy.md → src/agents/tool-policy-pipeline.ts |
| hermes | 25+ 危险模式正则作为主防线，LLM 判断作为补充 | 正则确定性匹配（rm/chmod/curl\|sh/kill/systemctl/git reset --hard 等），不受 LLM 幻觉影响，与 tirith 结果合并审批 | entity/hermes-approval-system.md → tools/approval.py:75-138 |

**Concept 状态**：已升级 → [[concept/dangerous-operation-prevention]]

---

## 如何安全地授权高风险工具执行？

**维度**：Architecture
**问题陈述**：如何让 exec 类高风险工具在执行前获得人工确认，而不依赖 LLM 自身的判断？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | exec 类工具走异步审批协议，阻塞等待 owner 决策后才执行（支持 host/gateway 双路径审批） | 高风险工具需人类在循环中确认，允许助手「请求许可」而非「请求原谅」 | entity/openclaw-tool-policy.md → src/agents/bash-tools.exec-approval-request.ts |
| hermes | 三层审批（YOLO → Smart → Manual） | 便宜辅助 LLM 自动处理明显安全/危险的命令，模糊情况才升级到人工审批，降低用户疲劳 | entity/hermes-approval-system.md → tools/approval.py:586-922（主入口）、tools/approval.py:534-583（Smart 层） |

**Concept 状态**：已升级 → [[concept/tool-execution-safety-approval]]

---

## 如何实现多粒度的工具权限策略？

**维度**：Extension Points
**问题陈述**：如何在 profile、provider、agent 等不同粒度上独立配置工具权限，而不耦合各层策略？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | tool policy 通过 5 层 pipeline 叠加（profile / provider / global / agent / group），每层独立配置 allowlist/denylist | pipeline 架构使各层策略正交，不互相耦合 | entity/openclaw-tool-policy.md → src/agents/tool-policy-pipeline.ts |

**Concept 状态**：仅 openclaw—待观察

---

## Agent 编排模型

**维度**：Architecture
**问题陈述**：如何在多工具系统中管理 LLM 交互循环，同时支持 failover 路由、子 agent 委派和资源预算控制？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 单一中央编排器 | AIAgent 作为唯一编排点管理完整 tool-calling 循环，避免各工具模块重复处理 LLM 协议差异 | entity/hermes-ai-agent.md → run_agent.py:535（入口）、run_agent.py:8130-8189（对话循环入口） |

**Concept 状态**：仅 hermes—待后续仓库

---

## 子 agent 如何复用主 agent 能力同时限制权限？

**维度**：Architecture
**问题陈述**：如何让子 agent 复用主 agent 的执行能力，同时安全地限制其权限范围？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 共享 AgentRunner 引擎 + 独立受限 ToolRegistry + 结果经 bus 注入 | 子 agent 无 message/spawn/cron 工具防止递归，结果通过 bus.publish_inbound 走与 IM 消息完全相同的处理路径 | entity/nanobot-subagent.md → agent/subagent.py:70-85, agent/subagent.py:102-129 |

**Concept 状态**：仅 nanobot—待观察（候选 Concept「Sub-agent Sandboxing」）

---

## 工具执行并发策略

**维度**：Performance Tradeoffs
**问题陈述**：如何在保证安全的前提下最大化工具执行的并发度？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 并行执行（8 线程），破坏性命令强制串行 | 只读工具无共享状态可并行降低延迟；含 rm/mv/sed -i 等破坏性命令必须串行执行防并发冲突 | entity/hermes-ai-agent.md → run_agent.py:214-311 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 对话轮次预算控制

**维度**：Performance Tradeoffs
**问题陈述**：如何防止 agent 陷入无限循环消耗 token，又避免预算警告导致模型过早放弃任务？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 硬上限 + 一次 grace call，预算信息不注入 LLM | 父 agent 90 轮、子 agent 50 轮硬上限；耗尽时给一次完成机会；不向 LLM 注入预算警告（之前注入导致模型过早放弃） | entity/hermes-ai-agent.md → run_agent.py:170-199 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 审批结果持久化策略

**维度**：Performance Tradeoffs
**问题陈述**：如何在减少重复审批和保持安全审查之间取得平衡？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 三级持久化（once/session/always），always 写入 config.yaml allowlist | 常用命令一次审批永久生效；allowlist 需人工维护审查，但消除重复审批摩擦 | entity/hermes-approval-system.md → tools/approval.py:299-303（session）、tools/approval.py:376-402（always） |

**Concept 状态**：仅 hermes—待后续仓库

---

## 上下文压力通知策略

**维度**：Performance Tradeoffs
**问题陈述**：如何通知上下文耗尽风险而不干扰 agent 完成任务？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 85%/95% 阈值各通知一次用户，不注入 LLM | 用户需要知道压缩发生，但 LLM 不应感受压力（实验发现向 LLM 发送 context 警告会导致提前放弃未完成任务） | entity/hermes-context-engine.md → agent/context_engine.py:59 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 多平台适配架构

**维度**：Architecture
**问题陈述**：如何为 20+ 消息平台提供统一的接入接口，同时确保所有集成点感知新平台的存在？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | BasePlatformAdapter 统一基类，新增平台需修改 16 处配置点 | 统一接口确保 toolset、认证映射、cron delivery 等跨平台逻辑只写一次；16 处修改点保证不遗漏集成点 | entity/hermes-gateway-platform.md → gateway/platforms/base.py:813-893 |

**Concept 状态**：仅 hermes—待后续仓库

---

## Gateway 环境下的审批等待策略

**维度**：Architecture
**问题陈述**：如何在异步消息平台环境下处理需要用户审批的等待——阻塞 vs 超时自动拒绝？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | FIFO 队列 + threading.Event 阻塞等待用户 /approve 或 /deny | 消息平台场景用户不在场时间长，自动超时拒绝会中断合法任务；阻塞等待保证审批机会，代价是 agent 线程占用 | entity/hermes-gateway-platform.md → tools/approval.py:219-284 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 记忆系统的可靠性保障

**维度**：Architecture
**问题陈述**：如何确保基础记忆功能不因外部服务配置错误而失效？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | BuiltinMemoryProvider 始终启用且不可移除，外部 provider 加性扩展 | 内置记忆保证基础功能始终可用；外部 provider（Honcho/Mem0 等 7 种）提供增强能力，但不能造成基础功能空白 | entity/hermes-memory-manager.md → agent/memory_provider.py:42-232 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 记忆系统的可扩展性

**维度**：Extension Points
**问题陈述**：如何让外部记忆系统感知 agent 的关键状态变化，而不仅仅限于读写操作？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | MemoryProvider ABC 暴露 15+ 生命周期回调 | on_pre_compress（压缩前提取重要信息防丢失）、on_delegation（观察子 agent 输出）等 hook 让外部 provider 精准感知状态变化 | entity/hermes-memory-manager.md → agent/memory_provider.py:42-232 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 日志安全脱敏

**维度**：Architecture
**问题陈述**：如何防止 API 密钥通过 agent 日志泄露，尤其是在日志记录所有工具调用参数的场景下？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 40+ API key 前缀模式写入时实时脱敏，密钥永不落盘 | 不依赖开发者手动脱敏；写入时脱敏消除"先写后脱敏"窗口期的泄露风险 | entity/hermes-observability.md → hermes_logging.py:1-391、agent/redact.py:1-60 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 日志文件组织策略

**维度**：Architecture
**问题陈述**：如何在多组件系统中高效定位问题，支持跨组件追踪单个用户会话的完整链路？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 三路日志（主日志/错误日志/网关日志）+ session_id 标签注入 | 按组件分离让错误排查直接看 errors.log，网关问题看 gateway.log；session_id 标签让跨组件追踪单个会话链路成为可能 | entity/hermes-observability.md → hermes_logging.py:72-119 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 后台进程输出管理

**维度**：Performance Tradeoffs
**问题陈述**：如何在内存可控的前提下提供后台进程输出的随时查询能力？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 200KB 滚动缓冲区 + LRU 淘汰（最大 64 进程）+ 已完成进程保留 30 分钟 | 200KB 足够看最近状态而不致内存问题；64 进程 LRU 防止无界增长；30 分钟保留让用户有时间查询已完成进程 | entity/hermes-observability.md → tools/process_registry.py:1-60 |

**Concept 状态**：仅 hermes—待后续仓库

---

## Agent 自学习触发机制

**维度**：Architecture
**问题陈述**：如何让 agent 在正确时机主动积累知识（创建技能、保存记忆、搜索历史），而不需要人类触发或独立后台进程？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | System prompt 驱动指令（三段 GUIDANCE），LLM 在完成任务过程中自发学习 | 将学习行为内嵌到 agent 决策流程，LLM 在刚完成复杂任务时主动创建技能，时机比后台批处理更准确；无需额外分析模块 | entity/hermes-self-learning-loop.md → agent/prompt_builder.py:145-171 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 技能注入策略

**维度**：Architecture
**问题陈述**：在技能数量较少的情况下，如何在简单性和检索精度之间选择技能注入方式？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | SKILL.md 文件全量注入 system prompt，每次会话启动时加载 | 技能数量通常较少，全量注入简单可靠，不依赖向量搜索基础设施；agent 能看到所有技能，不遗漏低频但关键的技能 | entity/hermes-self-learning-loop.md → agent/prompt_builder.py:449-453 |

**Concept 状态**：已升级 → [[concept/skill-injection-granularity]]

---

## 如何在技能数量增长时平衡可见性和 context 消耗？

**维度**：Extension Points
**问题陈述**：如何在技能数量增长时平衡 LLM 可见性和 context window 消耗——全量注入 vs 完全不注入 vs 分级注入？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | always 技能全文注入 + 其余 XML 摘要 + 按需 read_file | always 技能确保关键能力可见，其余以 XML 摘要呈现、agent 按需加载，兼顾可见性和预算 | entity/nanobot-skills.md → agent/skills.py:23-50, agent/skills.py:109-117 |
| openclaw | 三级预算退化（完整 XML → 紧凑 XML → 截断），技能正文从不注入 | 30,000 字符预算上限，预算不足时先降级格式再截断数量，LLM 始终需用 read_file 按需加载 | entity/openclaw-plugin-hook-system.md → src/agents/skills.ts |
| hermes | 紧凑索引 + 专用工具 skill_view 按需加载 | 分类组织 name+description 索引，LLM 先扫描索引再用 skill_view(name) 获取完整内容 | entity/hermes-self-learning-loop.md → agent/prompt_builder.py:583-808 |

**Concept 状态**：已升级 → [[concept/skill-injection-granularity]]

---

## 技能的自我维护能力

**维度**：Extension Points
**问题陈述**：如何防止技能因环境变化（工具版本升级、API 变更）而过时失效？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | skill_manage 支持 patch 操作，agent 在使用中发现技能过时可就地修复 | 避免无效技能积累；agent 发现即修复而非等到下次使用时才报错 | entity/hermes-self-learning-loop.md → tools/skill_manager_tool.py:1-30 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 外部技能安全分级

**维度**：Architecture
**问题陈述**：如何在安全性和开放生态之间，按技能来源的可信度做差异化的安全策略？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 100+ 威胁模式静态扫描 + 四级信任矩阵（builtin/trusted/community/agent-created） | builtin 直接放行（项目维护者保证），community 最严格（不可信第三方），agent-created 询问但默认信任 | entity/hermes-skills-guard.md → tools/skills_guard.py:595-639（入口）、tools/skills_guard.py:39-48（信任矩阵） |

**Concept 状态**：仅 hermes—待后续仓库

---

## 技能安装安全防护

**维度**：Dependency Strategy
**问题陈述**：如何在外部技能安装前，防止未经验证的代码在扫描期间被意外执行？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 隔离区（quarantine）暂存：Hub 下载 → quarantine/ → 扫描 → 通过后安装到 skills/<name>/ | 扫描失败直接删除隔离区文件，不影响已安装技能；确保未验证技能不会在扫描期间被意外执行 | entity/hermes-skills-guard.md → tools/skills_guard.py（隔离区流程） |

**Concept 状态**：仅 hermes—待后续仓库

---

## 安全模块的测试策略

**维度**：Testing Philosophy
**问题陈述**：如何确保安全扫描规则的覆盖度和有效性，特别是针对变体绕过场景？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 100+ 规则用于边界条件专项测试（如 test_sql_injection.py），规则本身是测试覆盖重点 | 安全规则覆盖的边界条件（变体绕过等）需专项测试才能发现；行为测试而非实现测试的哲学在安全模块中尤为重要 | entity/hermes-skills-guard.md → 专项测试文件（如 test_sql_injection.py） |

**Concept 状态**：仅 hermes—待后续仓库

---

## 测试资源如何分配以最大化安全效果？

**维度**：Testing Philosophy
**问题陈述**：如何在 agent 框架的测试策略中分配有限资源，最大化安全防护的投入产出比？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 测试投入集中安全（SSRF / exec 沙箱 / workspace 隔离） | 26,048 行测试代码中安全测试比重最大，因为 agent 框架中安全漏洞的后果远大于功能 bug | entity/nanobot-security.md → security/network.py; tests/tools/test_exec_security.py |

**Concept 状态**：仅 nanobot—待观察（候选 Concept「Testing Investment Prioritization」）

---

## 工具注册中心的生命周期

**维度**：Architecture
**问题陈述**：如何在单进程内管理工具注册的唯一性和线程安全同步？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 全局单例 + RLock 线程安全 | 工具集在进程内稳定，全局单例避免重复初始化；MCP 动态刷新需权威注册中心，分散实例难以同步 | entity/hermes-tool-registry.md → tools/registry.py:100-159 |

**Concept 状态**：仅 hermes—待后续仓库

---

## 工具集的组合与复用

**维度**：Extension Points
**问题陈述**：如何让不同平台共享核心工具的同时拥有专用工具，避免工具名称在各平台重复列举？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | Toolset includes 递归组合，平台专用 toolset 从 _HERMES_CORE_TOOLS 继承，带去重和循环检测 | 核心工具列表改一处所有平台自动获得；includes 组合避免重复列举；去重和循环检测确保组合安全 | entity/hermes-tool-registry.md → toolsets.py:68-397、toolsets.py:447-497（递归解析） |

**Concept 状态**：仅 hermes—待后续仓库
