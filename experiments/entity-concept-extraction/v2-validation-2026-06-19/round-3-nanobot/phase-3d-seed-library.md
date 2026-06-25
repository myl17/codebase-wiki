# 设计选择种子库

> 最后更新：openclaw + hermes-agent + nanobot（2026-06-19）
> 第三轮合并，种子库包含 58 条设计选择：19 条已升级为 Concept、8 条仅 openclaw—待观察、18 条仅 hermes-agent—待观察、13 条仅 nanobot—待观察

---

## Architecture

---

## 工具执行安全门控：统一管道还是分层可调节？

**维度**：Architecture
**问题陈述**：如何在工具执行的关键路径上决定安全检查的介入程度——是统一管道还是分层可调节？
**核心关切**：
- 关切 1：不同部署场景的安全需求差异巨大（个人开发机 vs 生产容器 vs 共享服务器）
- 关切 2：安全门控延迟不应影响正常的消息处理吞吐——安全检查与性能是零和博弈
- 关切 3：多来源配置的叠加规则必须产生可预测的结果，而非隐式交互
- 关切 4：高风险工具需要额外用户确认回路，但低风险工具不应被同等阻塞
- 关切 5：审批决策本身需要成本——辅助 LLM 评估引入额外 token 开销和延迟
- 关切 6：审批状态的持久化粒度（once/session/always）影响安全性和便利性的平衡

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 同步串行 Pipeline | 所有工具调用在执行前串行经过5层 allowlist/denylist 过滤，exec 类额外阻塞等待 owner 审批。权限决策在消息处理关键路径上同步完成，不依赖事后审计 | [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]] → `src/agents/tool-policy-pipeline.ts:56-90`；[[openclaw/nodes/components/openclaw-tool-policy]] → `src/agents/tool-policy.ts:19-55` |
| hermes-agent | 三层渐进式审批 | Layer 0 快速路径（YOLO/容器/off）+ Layer 1 Smart（辅助 LLM 自动评估）+ Layer 2 Manual（tirith + 25+ 危险模式正则 → 用户交互审批），审批级别 once/session/always 三级持久化 | [[hermes-agent/nodes/design-decisions/hermes-agent-layered-approval-decision]] → `tools/approval.py:586-922` |
| nanobot | 三层安全防护：基础设施级隔离 | SSRF 防护（10 个 CIDR 私有网络块拦截）+ exec 沙箱（隔离 workspace）+ workspace 隔离（限制文件系统访问范围），三层独立互不依赖，支持白名单配置。与 openclaw/hermes 的审批门控哲学不同——nanobot 在操作系统/网络/文件系统层面限制破坏能力，而非在执行前逐操作审批 | nanobot-testing-philosophy.md:1. 测试覆盖重点 → `security/network.py`; `test_exec_security.py`; `test_sandbox.py` |

**Concept 状态**：已升级 → [[concept/tool-security-gating]]
> nanobot 从「基础设施隔离」维度切入安全，与 openclaw/hermes 的「操作审批门控」形成互补。未来 Concept 页需扩展以容纳这两种安全哲学。

---

## 审批阻塞等待机制：异步 Promise 还是同步线程阻塞？

**维度**：Architecture
**问题陈述**：在高风险命令需要用户审批时，如何决定 agent 线程的阻塞等待机制——是异步 Promise 等待（不占事件循环）还是同步线程阻塞（线程挂起）？
**核心关切**：
- 关切 1：审批必须是同步阻塞的——不能在命令执行后才通知用户（安全性要求前置审批）
- 关切 2：阻塞等待不应死锁 agent 进程——需要超时、取消和多审批并发能力
- 关切 3：审批可通过多种路径到达用户（CLI / Gateway HTTP / chat reply）——路径选择应对 core 透明
- 关切 4：审批失败或超时不应导致 agent session 永久卡死——容错性要求优雅降级
- 关切 5：并行子 agent 的审批请求需要独立队列和独立等待

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 异步阻塞双路径审批 | `ExecApprovalRequest` 注册后 `waitForExecApprovalDecision` 阻塞等待 owner 决策，支持 host/gateway 双路径审批通道。审批在 ToolPolicy 同步门控 pipeline 内部触发，但等待机制是异步的可中断等待，不占用事件循环 | [[openclaw/nodes/extension-points/openclaw-exec-approval-request]] → `src/agents/bash-tools.exec-approval-request.ts:89-126`；[[openclaw/nodes/components/openclaw-tool-policy]] → `src/agents/tool-policy.ts:19-55` |
| hermes-agent | FIFO 队列 + threading.Event 阻塞审批 | Gateway 模式下审批请求进入 FIFO 队列，agent 线程通过 `threading.Event` 阻塞挂起等待用户 `/approve` / `/deny`；并行子 agent 并发等待各自审批（独立 Event） | [[hermes-agent/nodes/components/hermes-agent-approval-system]] → `tools/approval.py:219-284` |

**Concept 状态**：已升级 → [[concept/approval-blocking-mechanism]]

---

## 如何在消息驱动的 AI 助手中创建主动触发路径

**维度**：Architecture
**问题陈述**：在消息驱动的 AI 助手架构中，如何设计非用户消息事件（子 agent 结果、Cron 触发、Heartbeat 唤醒）的入站路径——是通过独立调度系统创建隔离 session 还是复用现有消息处理管道统一注入？
**核心关切**：
- 关切 1：主动触发路径不应破坏消息驱动模型的清晰性——两条路径共存需要明确的边界
- 关切 2：定时触发的执行结果必须可投递回消息通道（channel/thread/announce/webhook）——主动触发的结果需要消息通道作为出口
- 关切 3：每次定时触发应使用独立的 agent session，不与用户对话 session 混淆——session 隔离是正确性要求
- 关切 4：处理统一性——所有事件走同一入站路径避免多条处理管线的维护成本
- 关切 5：语义丢失——所有来源的消息无差别对待，无法做差异化路由或优先级

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Cron 作为唯一无消息主动触发入口 | CronScheduler 是唯一可以在无 IM 消息触发的情况下主动发起 agent 运行的入口。每次 cron 触发创建独立 isolated-agent session，`CronDeliveryPlan` 决定结果投递目标（channel/thread/announce/webhook）。所有其他 agent 运行都是消息驱动的 | [[openclaw/nodes/components/openclaw-cron-scheduler]] → `src/cron/delivery-plan.ts:10-19`；[[openclaw/nodes/components/openclaw-task-flow]] → `src/tasks/task-executor.ts:85-112` |
| nanobot | 统一 bus 注入：子 agent 结果等同于 IM 消息 | 子 agent、Cron、Heartbeat 的所有触发消息统一通过 `bus.publish_inbound()` 注入入站队列，与 Telegram/Discord 消息走完全相同的消费路径，AgentLoop 不需要区分消息来源。架构简化，单套处理逻辑维护成本低 | nanobot-architecture.md:数据流 → `agent/subagent.py:202-209`; `agent/loop.py:363-556` |

**Concept 状态**：已升级 → [[concept/proactive-trigger-path]]
> 反向检查：hermes 的中央 AIAgent 编排器架构中，Cron 只是又一个入口通向同一编排循环，不区分"消息驱动"和"主动触发"路径——不面对此问题。

---

## 如何调度定时任务和唤醒 agent

**维度**：Architecture
**问题陈述**：如何实现 agent 的定时任务调度——是使用传统 cron 机制、定时器轮询、还是 LLM 驱动的智能唤醒？多种调度模式如何共存？
**核心关切**：
- 关切 1：三种调度模式共存——at（一次性）、every（间隔）、cron（cron 表达式），满足从精确时刻到周期循环的所有场景
- 关切 2：多进程安全——CronStore 使用 FileLock 做持久化，防止多进程环境下的重复执行
- 关切 3：LLM 驱动唤醒的可靠性——Heartbeat 使用专用单工具 LLM 调用做定期唤醒，agent 自主判断是否需要执行任务——依赖 LLM 的判断准确性，可能漏判或误判
- 关切 4：Cron 作为唯一无消息主动触发入口，每次创建独立 session

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | CronScheduler 唯一主动触发入口 | 每次 cron 触发创建独立 isolated-agent session，CronDeliveryPlan 决定结果投递目标 | [[openclaw/nodes/components/openclaw-cron-scheduler]] → `src/cron/delivery-plan.ts:10-19` |
| nanobot | Cron 三模式调度 + Heartbeat LLM 自主唤醒 | Cron（at/every/cron）+ Heartbeat（LLM 通过 heartbeat tool 判断是否执行），统一通过 bus 注入入站路径 | nanobot-architecture.md:11. 调度系统 → `cron/service.py:1-50`; `heartbeat/service.py:14-40` |
| hermes-agent | Cron 作为编排循环的又一个入口 | — |

**Concept 状态**：已升级 → [[concept/agent-scheduling-mechanism]]

---

## 如何编排多轮 agent 对话的单一切入点

**维度**：Architecture
**问题陈述**：一个多平台、多入口（CLI/Gateway/Cron/ACP）的 agent 系统，如何保证所有执行路径共享同一套对话循环、工具调用和安全护栏，避免分叉维护？
**核心关切**：
- 关切 1：所有执行路径必须经过同一编排逻辑，改动才能一致生效
- 关切 2：中央编排器的规模会随功能增长膨胀（11510 行单文件）
- 关切 3：无替换机制意味着中央编排器的任何错误阻断所有入口

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | AIAgent 中央编排器 | 11510 行单文件 AIAgent 是所有执行路径的唯一入口，无替换机制 | [[hermes-agent/nodes/components/hermes-agent-ai-agent]] → `run_agent.py:535-560`, `run_agent.py:8130-8189` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何在系统 prompt 中内建自学习驱动

**维度**：Architecture
**问题陈述**：agent 系统如何让 LLM 在无人干预下自主积累知识、改进技能、回忆历史，而非依赖人类在每次会话中重新提供上下文？
**核心关切**：
- 关切 1：自驱动指令必须足够强以触发 LLM 主动行为，但不能产生虚假记忆
- 关切 2：三个时间尺度（实时/跨会话/代际）的改进需要不同的工具和持久化路径
- 关切 3：自学习的安全边界——agent 自建技能必须经过安全扫描才能落盘

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 三段自驱动 system prompt | 在 system prompt 中嵌入 MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE 三套指令，驱动 LLM 在实时、跨会话、代际三个时间尺度自主改进 | [[hermes-agent/nodes/design-decisions/hermes-agent-self-learning-loop-decision]] → `agent/prompt_builder.py:145-171` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何管理外部 skill 的安全信任

**维度**：Architecture
**问题陈述**：当 agent 可以从社区和第三方安装 skill 时，如何在"完全信任（危险）"和"一律拒绝（封闭）"之间按来源和风险等级实施差异化的安全策略？
**核心关切**：
- 关切 1：信任分级需要覆盖不同来源（内置/官方/社区/自建）和不同风险等级（safe/caution/dangerous）
- 关切 2：威胁模式的覆盖面——12 类别 100+ 模式覆盖 exfiltration/injection/destructive/persistence/network/obfuscation/execution/traversal/mining/supply_chain/privilege_escalation/credential_exposure
- 关切 3：agent 自建 skill 的安全处理——最可能出问题但也最有价值的来源

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 三级信任策略 x 三级风险等级 | 信任级别（builtin/trusted/community/agent-created）与风险等级（Safe/Caution/Dangerous）交叉形成差异化策略：builtin 全放行、trusted 仅 block dangerous、community block caution+dangerous、agent-created ask dangerous | [[hermes-agent/nodes/components/hermes-agent-skills-guard]] → `tools/skills_guard.py:39-48`, `tools/skills_guard.py:82-484` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何分离关注点防止单层膨胀

**维度**：Architecture
**问题陈述**：一个包含配置管理、会话持久化、安全边界、资源隔离的大型 agent 系统，如何划分层次使得各层独立演化、避免循环依赖？
**核心关切**：
- 关切 1：配置层必须在所有模块导入之前加载，CLI 和 Gateway 独立加载
- 关切 2：会话层的 PII 保护——敏感信息需哈希化存储
- 关切 3：资源隔离——不同 agent 实例的终端 VM 按 task_id 隔离，防止相互干扰

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 六层分离架构 | 用户界面层 → 编排层 → 安全层 → 插件层 → 工具层 → 基础设施层 + 可观测性层（横切）；配置层在启动时独立加载避免循环依赖；`_SafeWriter` 包装 stdout/stderr 防止管道破裂；终端 VM 按 task_id 隔离 | [[hermes-agent/dimensions/hermes-agent-architecture]] → `run_agent.py:113-167`, `gateway/run.py:88-218`, `gateway/session.py:1-60` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何管理日志的安全性和可追溯性

**维度**：Architecture
**问题陈述**：agent 系统的日志中可能包含 API key、用户私密对话等敏感信息，如何在保留调试信息的同时确保密钥永不写入磁盘？
**核心关切**：
- 关切 1：脱敏的覆盖面——40+ 种 API key 前缀模式需持续更新
- 关切 2：脱敏的时机——在日志写入前截获，不能依赖事后清理
- 关切 3：多组件日志的路由——gateway/agent/tools/cli/cron 的日志需分开存储便于排查

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 密文脱敏 + 组件路由 + session 注入 | 40+ 种 API key 前缀模式自动脱敏（OpenAI/Anthropic/GitHub/Slack/Google/AWS/Stripe 等）；三日志分文件（agent.log/errors.log/gateway.log）；`[session_id]` 标签注入 LogRecord 支持按会话过滤；Managed Mode 下 chmod 0660 保证多用户共享 | [[hermes-agent/dimensions/hermes-agent-architecture]] → `agent/redact.py:1-60`, `hermes_logging.py:1-391` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何管理后台进程的生命周期

**维度**：Architecture
**问题陈述**：agent 可能在后台启动长时间运行的进程（terminal background=true），如何在 agent 崩溃重启后恢复对这些进程的跟踪，同时限制内存占用？
**核心关切**：
- 关切 1：进程状态的持久化——JSON checkpoint 文件支持崩溃恢复
- 关切 2：输出缓冲的容量——200KB 滚动缓冲区平衡内存占用和可追溯性
- 关切 3：并发进程数的上限——64 个进程 LRU 淘汰防止资源耗尽

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 进程注册表 + JSON checkpoint | 管理所有后台进程：200KB 滚动输出缓冲区、已完成进程保留 30min、最大并发跟踪 64 个进程（LRU 淘汰）、JSON checkpoint 文件支持网关崩溃恢复 | [[hermes-agent/dimensions/hermes-agent-architecture]] → `tools/process_registry.py:1-60` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 子系统集中组装：构造函数 Hub vs 中央编排器

**维度**：Architecture
**问题陈述**：一个由 10+ 子系统组成的 agent 框架，如何将所有子系统的初始化、依赖注入和生命周期管理集中在一个位置——是通过中央编排器吸收所有执行路径，还是通过构造函数在单个 Hub 中显式组装所有子系统？
**核心关切**：
- 关切 1：可发现性——所有连线逻辑集中在一个文件的单个函数中，读一个构造函数就能完整理解系统组成
- 关切 2：可测试性牺牲——集中式组装意味着没有 DI 容器，无法对单个子系统做独立单元测试，AgentLoop 成为单一故障集中点
- 关切 3：启动耦合——所有子系统在启动时一次性初始化，无法按需延迟加载

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 单体 Hub 集中组装 | AgentLoop.__init__() 作为唯一架构入口，在一个方法中实例化并注入所有子系统（provider、bus、context、tools、runner、subagents、consolidator、dream、sessions、cron、heartbeat、MCP） | nanobot-architecture.md:1. AgentLoop → `agent/loop.py:115-228` |

**Concept 状态**：仅 nanobot—待观察
> 说明：hermes 的 AIAgent 中央编排器关注的是「多入口路由到同一编排循环」，nanobot 关注的是「构造函数中显式 DI 组装」。当前是两个独立轴线，未来可考虑合并为「Agent 系统集中式集线器模式」的父轴。

---

## 执行引擎的产品层分离

**维度**：Architecture
**问题陈述**：如何让同一套 tool-calling 循环引擎同时服务主 agent、子 agent 和后台记忆处理，而不让引擎依赖任何产品层概念（channel、session、cron）？
**核心关切**：
- 关切 1：引擎复用——AgentRunner 不 import channel、session、cron 等产品层模块，只关心「收消息 → 调 LLM → 执行工具」，实现一次编写三处复用
- 关切 2：上下文盲区——AgentRunner 不知道自己在为主 agent 还是子 agent 服务、不知道 channel 类型、不知道会话状态，无法根据上下文调整行为
- 关切 3：职责分离——所有产品层逻辑（session 管理、channel 路由、hook 注入、command 优先级）都在 AgentLoop 层处理，AgentRunner 只管纯粹的 LLM 交互循环

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 产品层无关的纯执行引擎 | AgentRunner 接受 AgentRunSpec 纯数据配置，与产品层零耦合，同时驱动主 agent、子 agent、Dream Phase 2 | nanobot-architecture.md:2. AgentRunner → `agent/runner.py:83-97`; `agent/loop.py:300-355`; `agent/subagent.py:140-150`; `agent/memory.py:519+` |

**Concept 状态**：仅 nanobot—待观察
> 种子库待收录：openclaw 和 hermes-agent 均未将「执行引擎与产品层分离」作为显式设计选择。此轴线为 nanobot 带来，待未来轮次观察另外两仓库是否隐含面对此问题。

---

## Channel 层与 Agent 核心的解耦机制

**维度**：Architecture
**问题陈述**：如何让不同的 IM Channel（Telegram、Discord、微信等 14+）与 Agent 核心完全解耦，使新增 Channel 不需要修改 AgentLoop 的任何代码——是通过异步队列、同步回调、还是事件总线？
**核心关切**：
- 关切 1：接口统一——Channel 只操作 `publish_inbound()`/`consume_outbound()`，AgentLoop 只操作 `consume_inbound()`/`publish_outbound()`，双方只通过队列交互
- 关切 2：异步解耦——使用 `asyncio.Queue` 而非同步调用，Channel 和 AgentLoop 各自独立运行，生产消费速率解耦
- 关切 3：排队语义——队列引入消息缓冲和潜在延迟，不适合需要同步响应的场景

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | MessageBus 异步队列解耦 | 使用 asyncio.Queue 将 Channel 层与 Agent 核心完全解耦，双方只操作统一的消息队列接口 | nanobot-architecture.md:3. MessageBus → `bus/queue.py:8-35` |

**Concept 状态**：仅 nanobot—待观察
> 种子库待收录：openclaw（Adapter 直接交互）和 hermes-agent（Gateway 层同步处理）均未将 Channel-Agent 通信解耦机制作为显式设计选择突出。

---

## 系统 Prompt 的组装方式

**维度**：Architecture
**问题陈述**：系统 prompt 由多个独立来源组成（identity、bootstrap files、memory、skills、history），如何组装这些内容使得每层可以独立修改和测试——是纯数据到文本的拼接，还是嵌入驱动性指令？
**核心关切**：
- 关切 1：可测试性——ContextBuilder 不持有 AgentLoop 引用、不调用 LLM、不管理工具，是纯数据到文本的转换层，可以独立于 AgentLoop 进行单元测试
- 关切 2：层次独立——六层内容（identity → bootstrap → memory → always skills → skills summary → recent history）依次拼接，每层用 `---` 分隔，修改一层不影响其他层
- 关切 3：运行时效率——skills 摘要支持渐进式加载（always skills 全文注入 + 其他仅在摘要中列出），避免所有技能内容塞满 system prompt

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | ContextBuilder 纯数据到文本的六层拼接 | 六层独立内容依次拼接为 system prompt，ContextBuilder 是无副作用的纯转换层 | nanobot-architecture.md:4. ContextBuilder → `agent/context.py:17-63` |

**Concept 状态**：仅 nanobot—待观察
> 说明：hermes 的「三段自驱动 system prompt」关注的是 system prompt 中嵌入指令驱动 LLM 行为，与 nanobot 的「纯数据拼接 + 层次独立」是 system prompt 组装维度的不同子问题。当前是两个独立轴线。

---

## 记忆存储：纯文件 vs 外部数据库

**维度**：Architecture
**问题陈述**：如何实现 agent 的长期记忆——包括用户档案、对话历史压缩和记忆更新——是使用纯文件 I/O（零外部依赖）还是引入嵌入式数据库或向量检索？
**核心关切**：
- 关切 1：零外部依赖——MemoryStore 是纯文件 I/O（读/写 `MEMORY.md`、`history.jsonl`），用 `GitStore` 版本控制 `SOUL.md`/`USER.md`/`MEMORY.md`，无嵌入式数据库，无向量检索
- 关切 2：检索质量取舍——文件级记忆无法做语义检索，只能线性读取整个 `MEMORY.md` 内容放入 system prompt，记忆量受 context window 限制
- 关切 3：三级处理栈——MemoryStore（持久化）→ Consolidator（后台压缩历史为文件级摘要）→ Dream（两阶段 LLM 驱动的记忆更新），每层职责明确

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 纯文件 I/O 三层记忆栈（无向量检索） | MemoryStore 文件读写 + Consolidator 异步压缩 + Dream 两阶段 LLM 处理，全部基于文件系统 | nanobot-architecture.md:8. MemoryStore → `agent/memory.py:27-228,346+,519+` |

**Concept 状态**：仅 nanobot—待观察
> 反向检查：hermes-agent 支持 7 种外部记忆后端（Honcho/Mem0/Supermemory 等），openclaw 有可插拔 MemoryCapability 接口——两者使用外部依赖路径，nanobot 选择纯文件路径。此轴线关注存储后端选择。

---

## 会话状态持久化机制

**维度**：Architecture
**问题陈述**：多轮对话的会话状态应该如何持久化——在文件级存储、内存缓存和惰性加载之间如何权衡？
**核心关切**：
- 关切 1：无外部 DB——会话以 JSONL 文件存储（第一行 `_type: metadata`），无需数据库，文件系统即持久层
- 关切 2：内存效率——内存缓存 + 惰性加载，不将所有会话长驻内存
- 关切 3：边界对齐——`get_history()` 或 `retain_recent_legal_suffix()` 在每轮开始时裁剪历史到合法边界，确保不会从孤立 tool result 中间开始（导致 LLM 看到不完整的 tool-call 对）
- 关切 4：单一天地入口——`get_or_create()` 是唯一入口函数，集中管理会话的创建和获取逻辑

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | JSONL 文件存储 + 内存缓存 + 惰性加载 + 合法边界裁剪 | 会话以 JSONL 持久化，内存缓存避免重复 I/O，裁剪到合法边界防止损坏的上下文 | nanobot-architecture.md:7. SessionManager → `session/manager.py:50-94,119-204` |

**Concept 状态**：仅 nanobot—待观察
> 种子库待收录：hermes-agent 和 openclaw 均未将会话持久化机制作为显式设计选择条目。

---

## Extension Points

---

## 消息平台适配：接口分解粒度

**维度**：Extension Points
**问题陈述**：在为多平台 IM 系统设计适配器接口时，如何决定接口的拆分粒度——是单一抽象基类还是多个可选小接口？
**核心关切**：
- 关切 1：不同 IM 平台的能力差异巨大——不是所有平台都支持所有操作，大而全的接口会迫使简单平台实现空方法
- 关切 2：核心对 channel 的调用路径（入站解析、出站发送、生命周期）需要统一的接口约定——拆分过细会破坏调用的一致性
- 关切 3：新增平台的工作量应与所需能力成正比——简单平台不应被迫实现复杂接口
- 关切 4：抽象基类需要覆盖消息收发、会话管理、媒体处理、打字指示等异构能力
- 关切 5：新增平台需要修改的代码点数量直接影响扩展成本（hermes 16 步 checklist vs openclaw 注册入口）

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 13+ Adapter 分解 | `ChannelPlugin<ResolvedAccount>` 接口拆分为 13+ Adapter：`ChannelMessagingAdapter`、`ChannelOutboundAdapter`、`ChannelLifecycleAdapter`、`ChannelAuthAdapter`、`ChannelSetupAdapter` 等。每个 adapter 是可选的——平台只实现自己支持的维度。通过 `defineBundledChannelEntry` 统一注册入口 | [[openclaw/nodes/extension-points/openclaw-channel-plugin]] → `src/channels/plugins/types.plugin.ts:53-94`；[[openclaw/dimensions/openclaw-extension-points]] → `src/plugin-sdk/channel-entry-contract.ts:31-60` |
| hermes-agent | 单一抽象基类继承 | 通过 `BasePlatformAdapter` ABC 定义统一接口（connect/disconnect/send/send_typing/send_image/get_chat_info），22 个平台通过继承实现；代价是新增平台需按 16 步 checklist 修改多处 | [[hermes-agent/nodes/extension-points/hermes-agent-platform-adapter]] → `gateway/platforms/base.py:813-893` |

**Concept 状态**：已升级 → [[concept/im-platform-adapter-granularity]]

---

## 全局能力共存策略：加性叠加还是替换式互斥？

**维度**：Extension Points
**问题陈述**：当多个实现竞争同一全局能力（上下文引擎/记忆后端）时，如何决定它们之间的共存关系——是加性叠加还是替换式互斥？
**核心关切**：
- 关切 1：Context engine 决定所有 LLM 交互的 prompt 组装方式——同时存在多个必然产生冲突（正确性要求唯一性）
- 关切 2：加性叠加保证基础功能永不丢失但可能产生冗余存储
- 关切 3：替换式更简洁但可能丢失内置存储的稳定性保障
- 关切 4：注册顺序应可预测——后注册者覆盖前者的规则必须明确且一致
- 关切 5：Plugin 应能自由注册自己的实现——开放性要求允许多个 plugin 竞争注册

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Exclusive 槽位覆盖注册 | `registerContextEngine` 和 `registerMemoryCapability` 被设计为 exclusive 槽位——全局只能有一个活跃实现，后注册者覆盖前者。这与 `registerHook`（多个 handler 共存）和 `registerChannel`（多个实现并存）的设计截然不同 | [[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27`；[[openclaw/nodes/extension-points/openclaw-compaction-provider]] → `src/plugins/types.ts:1867-1990`；[[openclaw/nodes/components/openclaw-memory-system]] → `src/memory-host-sdk/host/types.ts:1-30` |
| hermes-agent | 加性叠加 + 最多 1 个外部 provider | BuiltinMemoryProvider 始终启用不可移除，外部 provider（Honcho/Mem0/Supermemory 等 7 选 1）是加性的——不替代内置存储。与 openclaw 的 exclusive 替换式槽位形成对比 | [[hermes-agent/nodes/extension-points/hermes-agent-memory-provider]] → `agent/memory_manager.py:1-27` |

**Concept 状态**：已升级 → [[concept/global-capability-coexistence]]

---

## 上下文压缩引擎：可插拔架构

**维度**：Extension Points
**问题陈述**：当上下文压缩需要在不同场景使用不同策略时，如何决定压缩引擎的架构——是策略模式允许完全替换引擎实现，还是在共享基础设施内仅配置参数？
**核心关切**：
- 关切 1：第三方可扩展性——社区能否提供自己的压缩策略实现并即插即用
- 关切 2：同一时间只有一个 engine 激活——多个压缩策略同时运行必然冲突
- 关切 3：压缩引擎的注册机制——是通过配置显式选择还是通过注册 API 竞争覆盖
- 关切 4：引擎替换对核心代码的影响——新增引擎是否需修改 core

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Exclusive 槽位覆盖注册 | `ContextEngineFactory` 注册即可，不改 core；后注册覆盖前者，`LegacyContextEngine` 向后兼容；同一 ID 只能由一个 owner 持有，不同 owner 不可相互覆盖 | [[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27`；[[openclaw/nodes/extension-points/openclaw-compaction-provider]] → `src/plugins/types.ts:1867-1990` |
| hermes-agent | 策略模式 + 目录发现 | `ContextEngine` ABC 定义压缩接口，第三方放入 `plugins/context_engine/<name>/` 目录，config.yaml 指定激活哪个；目录扫描自动发现所有可用实现 | [[hermes-agent/nodes/extension-points/hermes-agent-context-engine]] → `agent/context_engine.py:32-60` |

**Concept 状态**：已升级 → [[concept/context-engine-pluggability]]

---

## 生命周期 Hook：拦截粒度

**维度**：Extension Points
**问题陈述**：在 agent 生命周期中设计 hook 系统的拦截粒度时，如何决定事件的拆分程度——是少数粗粒度事件还是密集覆盖全生命周期？同时如何决定不同 hook 的组合策略（管道串联 vs 扇出并行）？
**核心关切**：
- 关切 1：Hook handler 可能修改核心数据（如 system prompt）——需明确区分可修改和只读的 hook，防止误用
- 关切 2：事件粒度的权衡——过细增加 hook 实现者的负担，过粗限制精确拦截能力
- 关切 3：多 handler 执行顺序和失败处理需可预测——单个 handler 的异常不能阻塞主 pipeline
- 关切 4：Prompt 注入类 hook 是记忆等关键系统的唯一入口——稳定性和性能要求极高
- 关切 5：Hook 的发现机制（目录扫描 vs 显式注册）影响扩展的便利性和透明度
- 关切 6：组合策略分化——内容变换类 hook 适合管道串联（前一 hook 输出是后一 hook 输入），事件通知类 hook 适合扇出并行（每个 hook 独立执行）

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 28 个细粒度命名 Hook | `registerHook(events, handler)` 支持 29 个命名生命周期 hook，覆盖从 `before_model_resolve` 到 `agent_end` 的完整链路。Prompt 注入类 hook（`before_prompt_build`、`before_agent_start`）允许 plugin 在 LLM 调用前修改 system prompt。同 hook 多 handler 按 priority 降序执行 | [[openclaw/nodes/extension-points/openclaw-hook-system]] → `src/plugins/hook-types.ts:55-84`, `src/plugins/hook-types.ts:128-133` |
| hermes-agent | 8 个粗粒度事件 + 目录扫描加载 | 8 个生命周期事件（gateway:startup / session:start / session:end / session:reset / agent:start / agent:step / agent:end / command:*），hook 通过 `~/.hermes/hooks/<name>/HOOK.yaml` + `handler.py` 目录扫描自动加载，错误隔离不阻塞主 pipeline | [[hermes-agent/nodes/extension-points/hermes-agent-event-hooks]] → `gateway/hooks.py:9-19`, `gateway/hooks.py:34-80` |
| nanobot | CompositeHook：内容变换用管道，事件通知用扇出 | 六个生命周期拦截点中，`finalize_content` 是纯函数管线（管道串联，前一 hook 输出是后一 hook 输入），其余五个方法采用扇出（每个 hook 独立执行，一个异常不阻塞其他）。AgentLoop 维护 `_extra_hooks` 列表支持运行时注入 | nanobot-extension-points.md:4. AgentHook → `agent/hook.py:29-103`; `agent/loop.py:180` |

**Concept 状态**：已升级 → [[concept/lifecycle-hook-granularity]]

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
> 反向检查：hermes 的 OpenAI SDK 统一路由消除了多 harness 竞争的问题——所有 20+ provider 通过 openai SDK 通信，不存在运行时 harness 选择的场景。这是架构层面的不同前提。

---

## 如何在无代码情况下扩展 Agent 行为

**维度**：Extension Points
**问题陈述**：在为 AI 助手设计扩展机制时，如何决定最低门槛的扩展方式——是要求写代码注册 API 还是允许纯文本文件声明扩展？进一步地，如何在全文注入的便利性和按需加载的上下文经济性之间平衡？
**核心关切**：
- 关切 1：零代码门槛——用户只需编辑文本文件即可定制 agent 行为
- 关切 2：扩展内容需注入到 agent 的 system prompt 以影响 LLM 行为——文本扩展必须被正确组装进 prompt
- 关切 3：扩展内容可作为 agent 可调用的命令暴露，不仅是被动的 prompt 指令
- 关切 4：与 plugin 系统互补不冲突——同一系统内两种扩展机制共存，不能互相破坏
- 关切 5：渐进式加载——always skills 全文注入，其他技能仅以 XML 摘要形式出现，agent 需要时按需读取——节省 token
- 关切 6：依赖自声明——frontmatter 中的 `requires.bins` 和 `requires.env` 声明工具依赖，不满足条件的技能自动标记为不可用
- 关切 7：用户覆盖——workspace 用户自定义技能可以覆盖内建同名技能

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Markdown 技能文件作为第三层扩展 | 用户在工作区放置 Markdown 技能文件，`buildWorkspaceSkillsPrompt` 将内容注入 agent system prompt，`buildWorkspaceSkillCommandSpecs` 将技能文件中的命令 spec 注册为可用命令。不需要代码，纯 Markdown 即可定制 agent 行为。与声明式 plugin manifest（`openclaw.plugin.json`）和命令式 plugin API 构成三层扩展体系 | [[openclaw/nodes/extension-points/openclaw-skills-extension]] → `src/agents/skills.ts:8-39` |
| nanobot | Skills Markdown 渐进式加载 | always skills（`always: true`）全文注入 system prompt；其他技能仅以 XML 摘要形式出现（名称 + 描述 + 路径 + 可用性），agent 需要时通过 `read_file` 工具按需读取。frontmatter 的 `requires.bins` 和 `requires.env` 声明依赖，`workspace/skills/` 用户技能覆盖内建 | nanobot-extension-points.md:5. Skills → `agent/skills.py:52-205` |

**Concept 状态**：已升级 → [[concept/declarative-skill-extension]]
> 反向检查：hermes 的 skills 基于 agentskills.io 代码标准，skill 是代码文件需要安装和扫描，没有 markdown 文本文件的零代码扩展机制。

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
> 反向检查：hermes 没有统一的 plugin SDK 框架——扩展通过 hooks（目录扫描）、toolsets（配置定义）、skills（agentskills.io）和 tools（AST 扫描注册）实现，不面对轻量/重量级双入口设计问题。

---

## 如何保证 Plugin 接口稳定性

**维度**：Extension Points
**问题陈述**：在 plugin 系统中，如何决定接口契约的验证策略——是依赖开发者手写测试还是让契约测试自动覆盖所有注册实现？
**核心关切**：
- 关切 1：新 plugin 注册后应自动被现有契约覆盖，零额外测试成本——自动化程度越高，对新 plugin 的约束越强
- 关切 2：契约测试需验证接口行为而不仅是类型签名——行为验证比类型检查更深入但更脆弱
- 关切 3：不同 plugin 的契约测试应能复用同一套 test suite——复用降低维护成本但需测试套件设计足够通用

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 共享 test suite 自动覆盖新注册 plugin | 契约测试以 `installChannelActionsContractSuite(...)` 等共享 test suite 定义，新 channel 注册到 registry 后自动被契约测试覆盖。运行时用 `forks` pool + `isolate: false` 共享注册表状态，不需为每个新 plugin 手写测试 | [[openclaw/dimensions/openclaw-testing-philosophy]] → `src/channels/plugins/contracts/actions.registry-backed.contract.test.ts:1-12` |

**Concept 状态**：仅 openclaw—待观察
> 反向检查：hermes 没有统一的 plugin 系统——hooks/toolsets/skills/tools 各有一套独立的扩展机制，没有统一的契约测试框架。

---

## 如何发现和注册工具（AST 扫描）

**维度**：Extension Points
**问题陈述**：在工具数量不断增长的 agent 系统中，如何让新增工具零额外接线即可被系统发现——是通过 AST 扫描自动发现，还是通过显式注册确保确定性？如何权衡发现便利性和注册安全性？
**核心关切**：
- 关切 1：自动发现机制要求注册调用必须是静态可发现的顶层调用，限制了动态注册的灵活性
- 关切 2：AST 扫描引入启动开销，工具越多解析越慢
- 关切 3：同样的自动发现哲学是否应一致应用于 hooks、skills 等其他扩展
- 关切 4：注册确定性——显式 `register()` 不做 AST 扫描、不做装饰器发现，每个工具必须在注册函数中点名，不存在隐式工具被发现或遗漏
- 关切 5：扩展成本——每个新工具需要两步操作：创建 Tool 子类 + 在 register 处点名，相比装饰器自动发现多了一步手工操作
- 关切 6：调试可见性——所有已注册工具可通过 `get_definitions()` 一次性获取完整列表，工具清单是明确的而非推断的

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | AST 扫描自动发现 | 进程启动时通过 AST 扫描所有 `registry.register()` 顶层调用自动发现工具，新增工具只需写注册调用无需手动接线；同一哲学延伸至 hooks（目录扫描）和 skills（双同步） | [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]] → `tools/registry.py:28-73` |
| nanobot | 显式 register() 注册，零自动发现 | 所有工具通过显式 `tool_registry.register()` 调用注册，不做 AST 扫描或装饰器发现。每个工具必须在 `_register_default_tools()` 中点名，工具清单明确可查 | nanobot-extension-points.md:1. ToolRegistry → `agent/tools/registry.py:8-99`; `agent/loop.py:229-255` |

**Concept 状态**：已升级 → [[concept/tool-discovery-mechanism]]
> 反向检查：openclaw 工具通过 plugin harness 注册，未面对此问题。

---

## 如何组织工具为可组合的能力组

**维度**：Extension Points
**问题陈述**：当 agent 拥有数十个工具时，如何让不同使用场景（CLI 全功能 vs Gateway 聊天 vs ACP 编码）只暴露相关工具子集，而非全量工具 schema 每次都注入 system prompt？
**核心关切**：
- 关切 1：工具分组的组合粒度——太细管理复杂，太粗无法精准控制
- 关切 2：递归 include 链的去重和循环检测
- 关切 3：核心工具的修改如何自动传播到所有继承它的 toolset

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 可组合 Toolset 分组 | 每个 toolset 是工具名列表 + `includes` 引用其他 toolsets，`resolve_toolset()` 递归解析带去重和循环检测；`_HERMES_CORE_TOOLS` 作为共享核心清单编辑一次即可更新所有平台 | [[hermes-agent/nodes/extension-points/hermes-agent-toolset-system]] → `tools/toolsets.py:1-30`, `tools/toolsets.py:447-497` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何集成外部工具服务（MCP 协议）

**维度**：Extension Points
**问题陈述**：当 agent 需要调用外部独立的工具服务时，如何通过 MCP 标准协议集成——是启动时配置驱动连接还是惰性连接？工具如何动态注册和命名空间隔离？生命周期如何管理？
**核心关切**：
- 关切 1：外部工具的可用性不确定性——断连后是否需要自动重连
- 关切 2：双向通信——外部 MCP server 可能发起 LLM 采样请求
- 关切 3：凭据安全——外部 server 返回的错误消息可能泄露 API key
- 关切 4：惰性连接——MCP server 在 AgentLoop 初始化时惰性连接，避免阻塞启动
- 关切 5：命名空间隔离——MCP 工具以 `mcp_` 前缀动态注册，与 builtins 工具命名空间不冲突
- 关切 6：生命周期管理——所有 MCP server 通过 `AsyncExitStack` 管理，AgentLoop 关闭时自动清理

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | MCP 协议集成 | 通过 `~/.hermes/config.yaml` 的 `mcp_servers` 配置自动发现和注入外部工具，支持 Stdio（子进程+指数退避自动重连）和 HTTP/StreamableHTTP 两种传输，支持 MCP Sampling（server 可发起 LLM 请求），错误消息中凭据自动脱敏 | [[hermes-agent/dimensions/hermes-agent-extension-points]] → `tools/mcp_tool.py:15-43` |
| nanobot | MCP 惰性连接 + mcp_ 前缀命名空间 + AsyncExitStack 生命周期 | MCP server 懒加载连接，工具以 `mcp_` 前缀注册，通过 AsyncExitStack 自动清理所有连接，不阻塞启动 | nanobot-extension-points.md:7. MCP → `agent/loop.py:256-276`; `agent/tools/mcp.py` |

**Concept 状态**：已升级 → [[concept/mcp-integration-pattern]]
> 反向检查：openclaw 未将 MCP 集成作为显式设计选择突出。

---

## 如何管理可安装技能的互操作性

**维度**：Extension Points
**问题陈述**：agent 的 Skill 系统如何设计才能在多个 agent 框架（Claude Code / Codex CLI / Hermes）之间互操作，避免技能被锁定在单一生态？
**核心关切**：
- 关切 1：开放标准 vs 专有格式——前者互操作但可能约束表达能力
- 关切 2：外部 skill 的安全风险——下载后安装前必须经过扫描
- 关切 3：skill 的自我改进——agent 在使用中如何更新过时或不完善的 skill

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | agentskills.io 开放标准 | 采用 agentskills.io 开放标准实现与 Claude Code / Codex CLI 的 skill 互操作；外部 skill 下载后经 `skills_guard.py` 100+ 威胁模式扫描方可安装；agent 可通过 `skill_manage` 工具自主改进 skill | [[hermes-agent/dimensions/hermes-agent-extension-points]] → `tools/skills_tool.py`, `tools/skills_hub.py` |

**Concept 状态**：仅 hermes-agent—待观察

---

## Channel 插件发现：自扫描 vs 显式注册

**维度**：Extension Points
**问题陈述**：如何让内置 Channel 和外部第三方 Channel 都能被自动发现，同时确保外部插件无法覆盖内置实现？
**核心关切**：
- 关切 1：双层发现——内置 Channel 通过 `pkgutil.iter_modules()` 自动扫描（新增 Python 文件即自动可被发现），外部 Channel 通过 Python `entry_points` 机制注册（`nanobot.channels` 组），支持 pip 可安装的第三方插件
- 关切 2：安全边界——内置 Channel 优先级高于外部插件，外部插件不能 shadow 同名内置 Channel，防止恶意插件替换关键 Channel 实现
- 关切 3：无需注册文件——内置 Channel 不需要维护显式注册表，新增模块文件即注册，降低添加新 Channel 的摩擦

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | pkgutil 自发现 + entry_points 外部插件，内置优先 | 内置 Channel 通过 pkgutil 自动发现，外部插件通过 entry_points 注册，内置实现不受外部插件覆盖 | nanobot-extension-points.md:2. Channel Plugin → `channels/registry.py:17-72` |

**Concept 状态**：仅 nanobot—待观察
> 种子库待收录：openclaw（defineBundledChannelEntry 统一注册入口）和 hermes-agent（16 步 checklist 注册）均采用显式注册路径，nanobot 首次带来双层自动发现机制。

---

## LLM Provider 注册：数据驱动 vs 代码驱动

**维度**：Extension Points
**问题陈述**：如何支持 20+ LLM provider 而无需为每个 provider 编写大量适配代码——如何让新增 provider 成为纯数据操作而非代码修改？
**核心关切**：
- 关切 1：数据驱动注册——新增 provider 只需在 `PROVIDERS` 元组中加一行 `ProviderSpec` 数据 + 在 `config/schema.py` 中加一个配置字段，所有匹配、检测、状态展示逻辑都从元组派生
- 关切 2：统一接口——`LLMProvider` 抽象基类定义统一的 `chat()`/`chat_stream()` 接口，子类只需实现其中一个方法，重试逻辑在基类中统一实现
- 关切 3：覆盖范围有限——仅支持 5 种 backend 风格（openai_compat / anthropic / azure_openai / openai_codex / github_copilot），非标准 API 风格的 provider 需要新 backend

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 数据驱动 ProviderSpec 注册表 | Provider 元数据集中在 `PROVIDERS` 元组中，5 种 backend 风格覆盖 20+ provider，新增 provider 是纯数据操作 | nanobot-extension-points.md:3. Provider Registry → `providers/registry.py:1-376` |

**Concept 状态**：仅 nanobot—待观察
> 说明：此轴线关注「provider 注册表的数据驱动设计」，与 hermes 的「SDK 架构锁定」（Dependency Strategy 维度）和 openclaw 的「运行时 harness 选择」（Extension Points 维度）属于 LLM provider 管理的不同子问题。

---

## 子 Agent 能力边界隔离

**维度**：Extension Points
**问题陈述**：如何让主 agent 可以 spawn 子 agent 处理独立任务，同时防止子 agent 递归创建更多子 agent、发送消息给用户、或调度新任务——通过工具白名单还是仅通过预算限制？
**核心关切**：
- 关切 1：工具白名单限制——子 agent 拥有独立的 ToolRegistry，包含文件工具 + 可选的 exec/web 工具，**不包含** message/spawn/cron 工具，从工具层面杜绝递归创建子 agent 的可能
- 关切 2：错误即终止——子 agent 的 tool error 为 fatal 级别（出错立即终止），不像主 agent 的非致命错误继续，因为子 agent 没有用户交互通道来恢复
- 关切 3：资源限制——每个子 agent 拥有 15 轮 iteration budget，超限自动终止，防止单个子任务无限消耗资源
- 关切 4：引擎复用——共享 AgentRunner 引擎获得所有上下文治理能力（Backfill/Microcompact/Budget/Snip），无需重新实现

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 子 agent 受限 ToolRegistry（无 message/spawn/cron）+ 共享执行引擎 | 子 agent 拥有独立受限工具集 + 共享 AgentRunner + fatal error 模式 + 15 轮预算 | nanobot-extension-points.md:6. Subagent → `agent/subagent.py:70-209` |

**Concept 状态**：仅 nanobot—待观察
> 说明：hermes 有迭代预算限制（父 90 轮/子 50 轮）但无工具白名单隔离；openclaw 未将子 agent 作为显式设计选择。此轴线关注「能力边界隔离机制」，未来可与 hermes 的计算预算限制合并为父轴。

---

## Performance Tradeoffs

---

## 上下文窗口溢出防护：触发策略

**维度**：Performance Tradeoffs
**问题陈述**：在 token 计数不精确的前提下，如何决定上下文窗口溢出防护的压缩触发策略——是固定阈值还是多源保守选择？进一步地，如何在每次 LLM 调用前自动治理上下文（修复不完整数据、压缩旧内容、截断超长结果、裁剪超预算历史），同时所有治理操作对 LLM 完全透明？
**核心关切**：
- 关切 1：压缩阈值的选择——太早触发浪费 token（无需压缩时压缩），太晚触发有截断丢失风险
- 关切 2：Token 估算误差不可避免（尤其是工具输出的实际大小）——需留安全余量，但余量过大会过早触发压缩
- 关切 3：必须在多个来源中选最保守值——宁可过早触发压缩也不能溢出导致 API 调用失败
- 关切 4：不必要的压缩浪费 LLM 调用成本——过早压缩的经济代价
- 关切 5：对 LLM 透明——四层治理全部在 AgentRunner 内部完成，LLM 不知道上下文被裁剪过、不知道某些 tool result 已被替换为摘要，避免 LLM 提前放弃任务
- 关切 6：LLM 策略盲区——LLM 无法主动调整自己的对话策略来适应有限的上下文，因为它不知道上下文已被压缩
- 关切 7：关键路径性能——四步治理在每次 LLM 调用的关键路径上自动运行，任何一步出错都可能导致 LLM 看到损坏的上下文

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 硬限制 + 软警告 + 多源保守选择 | 硬下限 `CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000`，软警告线 `CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000`，在 modelsConfig、model 自报、agentContextTokens 之间按优先级选最保守值。实际压缩触发由 `BASE_CHUNK_RATIO = 0.4` 和 `SAFETY_MARGIN = 1.2` 共同决定 | [[openclaw/dimensions/openclaw-performance-tradeoffs]] → `src/agents/context-window-guard.ts:4-81`, `src/agents/compaction.ts:19-40` |
| hermes-agent | 固定 75% 阈值 | 当前上下文达到模型 context window 的 75% 时触发压缩，`ContextEngine` ABC 定义阈值参数；单一阈值规则易于理解和调优 | [[hermes-agent/nodes/extension-points/hermes-agent-context-engine]] → `agent/context_engine.py:32-60` |
| nanobot | 四步透明上下文治理 | Backfill（修复孤立 tool_use）+ Microcompact（压缩 10 轮前的 tool result）+ Tool Result Budget（截断超长结果）+ Snip History（按 token 预算从尾部裁剪），全部对 LLM 透明——LLM 不知道上下文被裁剪过 | nanobot-performance-tradeoffs.md:1. Context Governance → `agent/runner.py:552-697` |

**Concept 状态**：已升级 → [[concept/context-window-overflow-guard]]
> nanobot 将「上下文治理」从「何时触发压缩」重新定义为「透明预处理管线」——核心差异不在压缩策略，而在 LLM 是否知情。未来 Concept 页需扩展以容纳「LLM 感知 vs LLM 透明」的治理哲学维度。

---

## Prompt 缓存边界：划分策略

**维度**：Performance Tradeoffs
**问题陈述**：在利用 LLM prompt caching 机制时，如何决定缓存边界的划分策略——是按消息类型切分、按内容稳定性高低分离、还是按工具定义排序？
**核心关切**：
- 关切 1：尽可能多的 token 命中缓存以减少每轮 API 费用——缓存区越大越好
- 关切 2：动态内容（记忆注入、实时上下文）必须放在缓存边界之后，不能混入缓存区——动态内容的存在限制了缓存区上限
- 关切 3：cache breakpoint 数量受限于 provider（Anthropic 上限 4 个）——每个 breakpoint 的位置选择都是稀缺资源的分配问题
- 关切 4：不同 LLM 平台的缓存 TTL 策略不同——边界设计需兼容多平台
- 关切 5：跨消息复用 agent 实例才能保持 cache prefix 有效——否则缓存写入成本白白浪费
- 关切 6：缓存稳定性——builtins 按名称排序放在前面作为稳定前缀，MCP 工具（`mcp_` 前缀）放在后面，只要 MCP 工具不变缓存就不会被破坏
- 关切 7：缓存命中率——排序策略直接决定 Anthropic prompt cache 的命中率，进而影响每次 LLM 调用的成本和延迟
- 关切 8：工具数量敏感——如果 builtins 数量过多，缓存前缀本身就会很大，留给 MCP 工具和消息的缓存空间会减少

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 稳定前缀 + 动态后缀分离 | 在 system prompt 中插入 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记，stable prefix 打上 Anthropic `cache_control: { type: "ephemeral" }` 标记。根据不同 API endpoint 决定缓存 TTL（`api.anthropic.com` 支持 `ttl: "1h"` 长缓存，其他端点的缓存时间更短）。动态后缀（记忆注入、实时上下文）在 boundary 后插入，不影响缓存命中 | [[openclaw/nodes/components/openclaw-context-engine]]（维度叙事页） → `src/agents/system-prompt-cache-boundary.ts:3-47`, `src/agents/anthropic-payload-policy.ts:37-65` |
| hermes-agent | system_and_3 缓存策略 | 4 个 cache breakpoints：system prompt 占 1 个（跨 turn 稳定），最后 3 条非 system 消息占 3 个（滚动窗口）；GatewayRunner 跨消息缓存 AIAgent 实例以保持 cache prefix 有效 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/prompt_caching.py:1-73`, `gateway/run.py:604-611` |
| nanobot | 工具定义排序：builtins 前缀 + MCP 后缀 | `get_definitions()` 按名称排序 builtins 在前、MCP 工具在后，构成 Anthropic prompt cache 的稳定前缀。简单直接，不依赖内容标记 | nanobot-performance-tradeoffs.md:3. Prompt Cache → `agent/tools/registry.py:45-63` |

**Concept 状态**：已升级 → [[concept/prompt-cache-boundary]]

---

## 记忆检索与注入时机

**维度**：Performance Tradeoffs
**问题陈述**：在多轮对话中，如何决定记忆检索与注入 LLM 上下文的时机——是在 prompt 组装阶段批量注入还是后台异步预取？
**核心关切**：
- 关切 1：记忆内容的新鲜度——实时检索可获取最新记忆，预取返回上一轮结果可能已过时
- 关切 2：Prompt 组装阶段的确定性——同一轮内多次 API 调用期间记忆内容变化导致行为不一致
- 关切 3：同步检索增加用户感知延迟——多后端聚合时尤其明显
- 关切 4：多个记忆后端并存——注入时机需兼容多种检索延迟（毫秒到秒级）
- 关切 5：异步预取的过时问题——上一轮结束后入队的预取结果不含本轮上下文

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Prompt 组装阶段批量注入 | 记忆在 Context Engine 的 `assemble` 阶段注入，非实时查询。记忆注入通过生命周期 hook（`before_prompt_build`、`before_agent_start`）实现，由 `active-memory` 等扩展负责。代价：同一次 LLM 调用期间新增的记忆在当前轮不可见 | [[openclaw/nodes/components/openclaw-memory-system]] → `src/memory-host-sdk/host/types.ts:1-30`；[[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27` |
| hermes-agent | 后台预取 + 不阻塞关键路径 | `queue_prefetch()` 在当前 turn 完成后后台线程触发记忆检索，下一轮 `prefetch()` 返回缓存结果；优势是不阻塞 API 调用前的关键路径，代价是记忆可能不是最新状态 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/memory_provider.py:92-112` |

**Concept 状态**：已升级 → [[concept/memory-retrieval-timing]]

---

## 上下文压缩：资源分配策略

**维度**：Performance Tradeoffs
**问题陈述**：在对对话历史进行压缩时，如何决定压缩的资源分配策略——是优先保留任务可恢复性（让 agent 压缩后能继续执行未完成任务），还是用定量预算控制压缩成本？
**核心关切**：
- 关切 1：压缩后摘要必须保留足够信息使 agent 可恢复任务执行——信息保留与 token 削减直接冲突
- 关切 2：高压缩率必然损失细节——压缩率与保真度的零和关系
- 关切 3：工具输出通常冗长但对后续决策价值低，需特殊处理策略
- 关切 4：Token 估算存在固有误差——压缩参数需包含安全余量
- 关切 5：压缩失败后的冷却期——防止摘要失败触发重试风暴
- 关切 6：用户通知不能注入 LLM——避免模型因感知到上下文压力而提前放弃

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 可恢复性优先压缩 | 摘要指令优先保留活跃任务状态、批处理进度、最后一次用户请求；`tool_result.details` 在压缩前 strip；参数用 `SAFETY_MARGIN = 1.2`（20% 缓冲补偿 token 估算误差）。牺牲历史细节完整性换取可恢复性 | [[openclaw/nodes/design-decisions/openclaw-compaction-recoverability-priority]] → `src/agents/compaction.ts:19-40`；[[openclaw/nodes/components/openclaw-context-engine]] → `src/context-engine/index.ts:1-27` |
| hermes-agent | 20% 摘要预算 + 600s 冷却 | 摘要预算为压缩内容的 20%，上限 12,000 tokens；摘要失败后冷却 600 秒防止重试风暴；用户通知分层（85%/95% 阈值）但不注入 LLM | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/context_compressor.py:51-53`, `agent/context_compressor.py:60` |

**Concept 状态**：已升级 → [[concept/compression-resource-allocation]]

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
> 反向检查：hermes 是 Python 项目，启动优化手段不同（Python import 时间、字节码缓存 `.pyc`）。hermes #32（模型元数据缓存）解决的是启动时避免网络阻塞，而非冷启动速度本身的综合优化。两个问题的技术约束和优化手段不同，属不同轴。

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
> 反向检查：hermes Gateway 处理多平台 IM 消息入站，但未将消息防抖合并作为显式设计选择。可能 hermes 面对此问题但未将其提升为设计选择——当前证据不足，保持 openclaw 独有。

---

## 如何分类管理工具的并行执行

**维度**：Performance Tradeoffs
**问题陈述**：当 LLM 在一次响应中发起多个工具调用时，哪些可以并行执行以降低延迟，哪些必须串行以保证安全或正确性？
**核心关切**：
- 关切 1：只读工具天然可并行，但文件路径有重叠的读写工具存在隐式依赖
- 关切 2：破坏性命令（rm/mv/sed -i 等）的识别依赖正则匹配，可能漏检
- 关切 3：交互式工具（clarify）必须阻塞等待用户输入，并行无意义

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 四分类并行策略 | 永不并行（clarify 交互式）/ 安全并行（web_search 等 11 个只读工具）/ 路径范围并行（read_file/write_file/patch 当目标路径不同时可并行）/ 破坏性串行（terminal 命令中含危险模式标记串行执行），最大 8 workers | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `run_agent.py:214-311` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何为不同复杂度的查询路由模型

**维度**：Performance Tradeoffs
**问题陈述**：日常简单对话（"你好""今天天气怎么样"）不需要大模型处理，如何在不牺牲复杂任务质量的前提下，将简单查询路由到便宜模型降低成本？
**核心关切**：
- 关切 1：误判代价——复杂任务被路由到弱模型导致质量下降，比简单任务走强模型多花一点钱更严重
- 关切 2：分类特征的完备性——字符数/词数/代码块/URL/关键词黑名单的准确率有限
- 关切 3：保守策略的倾向——宁可多用强模型也不能漏判复杂任务

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 保守的智能路由 | 仅 < 160 字符、< 28 词、无代码块、无 URL、无 45 个复杂关键词（debug/implement/refactor/analyze/architecture 等）的消息才路由到便宜模型；任一条件不满足则回主模型 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/smart_model_routing.py:62-118` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何管理 API 多凭证的速率限制

**维度**：Performance Tradeoffs
**问题陈述**：单个 API key 有严格的 rate limit，如何用多个 key 提升可用性——是随机轮换、按剩余配额分配、还是先用完再切？
**核心关切**：
- 关切 1：轮换策略影响配额利用率——随机轮换可能浪费低配额 key，fill_first 更高效但加重首个 key 负担
- 关切 2：被动追踪（等 429 再切）vs 主动限流（提前切换）——前者充分利用配额但偶尔浪费一次请求
- 关切 3：多 key 管理增加配置和监控复杂度

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | fill_first + 被动追踪 | 先用第一个 key 耗尽再切下一个（fill_first）；被动追踪 12 个 x-ratelimit-* header，收到 429 后才切换 fallback，不做主动预限流以充分利用每个 key 的配额 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/credential_pool.py:60`, `agent/rate_limit_tracker.py:1-51` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何限制 agent 的单次任务计算预算

**维度**：Performance Tradeoffs
**问题陈述**：agent 在执行复杂任务时可能陷入无限循环或过度探索，如何在保证任务完成度的同时设置计算成本的上限？
**核心关切**：
- 关切 1：预算耗尽后的处理——是立即终止还是给一次 grace call 生成最终响应
- 关切 2：某些工具调用（execute_code）是否应退款——代码执行本身不是 agent 的决策性轮次
- 关切 3：预算告警是否应注入 LLM——提前告警可能导致模型过早放弃，不告警则可能在耗尽时突然中断

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 线程安全迭代预算 + 不注入 LLM | 父 agent 90 轮、子 agent 50 轮独立预算；耗尽后允许一次 grace call 尽力生成文本响应；`execute_code` 调用可退款（不计入预算）；预算耗尽不提前通知 LLM（之前做法导致模型过早放弃） | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `run_agent.py:170-199`, `run_agent.py:815-821` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何为特定场景精简 agent 的工具面

**维度**：Performance Tradeoffs
**问题陈述**：当 agent 被嵌入编辑器（通过 ACP 协议）而非作为独立聊天应用时，如何裁剪工具集以移除不相关的功能（消息/音频/交互式 UI），从而减少 token 开销和避免模型误用？
**核心关切**：
- 关切 1：裁剪的工具集需独立维护 vs 从核心工具集派生（继承核心再移除）
- 关切 2：裁剪后功能不完整——编辑器场景无法使用消息发送、TTS 等功能
- 关切 3：不同场景的 toolset 定义应该由谁维护（平台开发者 vs 核心团队）

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | ACP 专用精简 toolset | `hermes-acp` toolset 移除 messaging/audio/clarify UI 工具，仅保留编码相关工具；更小的工具 schema → 更低的 token 开销和更精确的上下文，但牺牲编辑器中的完整 Hermes 功能 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `toolsets.py:226-243` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何缓存模型元数据加速启动

**维度**：Performance Tradeoffs
**问题陈述**：agent 启动时需要查询 API provider 获取模型列表和元数据，这个网络请求是否应阻塞启动过程？
**核心关切**：
- 关切 1：缓存过期后的信息不准确——新模型可能未被发现
- 关切 2：后台线程预热——在 agent 初始化时启动 daemon 线程获取元数据，不阻塞启动
- 关切 3：缓存 TTL 的选择——1 小时平衡新鲜度和启动速度

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 1h TTL 缓存 + daemon 线程预热 | 模型元数据缓存 1 小时避免每次启动阻塞 API 调用；后台 `threading.Thread(target=..., daemon=True)` 在 agent 初始化时启动预热 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `run_agent.py:747-748`, `agent/model_metadata.py` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 记忆压缩的非阻塞执行

**维度**：Performance Tradeoffs
**问题陈述**：记忆压缩（Consolidator）需要调用 LLM 进行历史总结，如何在不阻塞主 agent 对话的前提下完成压缩，且压缩失败不影响正在进行的对话？
**核心关切**：
- 关切 1：Provider 实例隔离——Consolidator 使用独立的 LLM provider 实例，不共享主 agent 的 provider 状态（如速率限制计数器），压缩和对话互相不干扰
- 关切 2：异步解耦——在 `asyncio.create_task()` 中后台运行，主 agent 在压缩运行期间不受影响，也不会等待压缩完成
- 关切 3：结果延迟生效——压缩结果在下一轮 context 组装时才生效，本轮对话使用的仍是压缩前的内容，但失败的压缩不会中断对话

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | Consolidator 独立 Provider 实例 + 异步后台任务 | 独立的 LLM provider 实例 + asyncio.create_task() 后台运行，主循环不阻塞 | nanobot-performance-tradeoffs.md:4. Consolidator → `agent/loop.py:210-219,572`; `agent/memory.py:346+` |

**Concept 状态**：仅 nanobot—待观察
> 说明：此轴线关注「记忆压缩的非阻塞执行」，与种子库的「记忆检索时机」（concept/memory-retrieval-timing）关注不同阶段（压缩 vs 检索）。未来可合并为「记忆操作的异步策略」父轴。

---

## LLM API 错误处理与重试策略

**维度**：Performance Tradeoffs
**问题陈述**：如何设计 LLM API 调用的重试策略，使其能区分临时性错误（可重试）和永久性错误（不可重试），并在速率限制和配额耗尽的处理上做出不同响应？
**核心关切**：
- 关切 1：错误分类粒度——429 错误按语义分类：配额耗尽类（非重试，直接返回错误）vs 速率限制类（重试 + 等待 Retry-After），从响应 error type/code 和响应文本两个路径提取判断
- 关切 2：重试策略分级——standard 模式 3 次指数退避（适用于临时性故障）vs persistent 模式无限制但相同错误超过 10 次停止（适用于长任务）
- 关切 3：内容降级——图片内容导致的 API 错误自动降级为纯文本重试，不丢失整个请求
- 关切 4：维护复杂度——三级重试逻辑在基类 `_run_with_retry()` 中统一实现，但错误分类依赖各 provider 的 error code 规范，新 provider 的 error 行为可能不兼容

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 三级重试：standard 3 次退避 + persistent 无限制限停 + 429 语义分类 | 基类统一实现，区分临时/永久错误，429 分类为配额 vs 限速，图片错误自动降纯文本 | nanobot-performance-tradeoffs.md:5. LLM Provider 重试 → `providers/base.py:629-698` |

**Concept 状态**：仅 nanobot—待观察
> 种子库待收录：hermes-agent 有 fill_first + 被动追踪机制处理速率限制，openclaw 未将 LLM 重试策略作为显式设计选择。此轴线关注「错误分类和重试策略设计」的粒度。

---

## Dependency Strategy

---

## 可选依赖分层：统一降级还是按安装成本分层？

**维度**：Dependency Strategy
**问题陈述**：当系统需要支持可选功能（消息/记忆/语音/浏览器/搜索/容器运行时等）且对应依赖体积差异巨大时，如何决定可选依赖的分层策略——是统一降级还是按安装成本分层？
**核心关切**：
- 关切 1：默认安装不应拉入 GB 级二进制或复杂原生模块——默认体验的轻量性是用户留存的基础
- 关切 2：ImportError 检查点需要遍布所有使用可选依赖的代码路径，遗漏一处即崩溃
- 关切 3：降级行为需要明确告知用户（哪些功能因缺失依赖而不可用）
- 关切 4：条件依赖（特定 OS 或 Python 版本才可用）需要在包管理层面表达
- 关切 5：需要重型功能的用户必须清楚知道需要额外安装步骤——可发现性与轻量默认之间的张力

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Peer + Optional 依赖分层 | Peer dependencies（`@napi-rs/canvas`、`node-llama-cpp`）由用户显式安装，不默认拉入；optional dependencies（`@discordjs/opus`、`@matrix-org/matrix-sdk-crypto-nodejs`）缺失时自动降级不崩溃。`node-llama-cpp` 安装体积达 GB 级，故设为 peer 而非 optional——用户必须有意识地安装 | [[openclaw/dimensions/openclaw-dependency-strategy]] → `package.json: peerDependencies, optionalDependencies` |
| hermes-agent | ImportError → 降级/跳过 + 20+ extras 分组 | 所有可选依赖遵循 ImportError 捕获后优雅降级模式，绝不因缺少可选包而启动失败；pyproject.toml 通过 20+ extras 将单体重安装拆分为按需安装（如 `hermes-agent[messaging]`）；条件依赖（matrix 仅 Linux、yc-bench 仅 Python>=3.12）在包层面约束 | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:39-115` |
| nanobot | pip extras 可选依赖分组：按平台按需安装 | IM 平台 SDK 和辅助功能标记为 pip extras 可选依赖（`api`、`wecom`、`weixin`、`matrix`、`discord`、`langsmith`），核心运行时只有 ~20 个包。版本约束集中在 `pyproject.toml` 主依赖中而非可选组中 | nanobot-dependency-strategy.md:2. 可选依赖 → `pyproject.toml:20-78` |

**Concept 状态**：已升级 → [[concept/optional-dependency-layering]]

---

## 依赖版本锁定：按风险分级还是全量统一？

**维度**：Dependency Strategy
**问题陈述**：在管理项目依赖时，如何决定版本锁定的粒度——是全部精确锁定、全部范围版本，还是按风险级别分类锁定？
**核心关切**：
- 关切 1：协议 SDK 的不兼容变更直接导致功能故障——高风险依赖必须精确锁定
- 关切 2：有 native addon 的包版本敏感——编译失败难以排查，精确锁定降低风险
- 关切 3：核心引擎的 breaking change 影响全局——必须精确锁定
- 关切 4：工具类库的 patch 变更不影响行为——范围版本可降低维护负担
- 关切 5：版本范围的宽松程度——太松可重复性差，太紧更新成本高
- 关切 6：容器层的可重复性——Docker 基础镜像也需固定
- 关切 7：不内嵌第三方源码（no vendor）——完全依赖包管理器的 lockfile

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | 精确定位协议/native/核心包，范围版本工具库 | 70 个 runtime deps 中 29 个精确锁定：所有 `@mariozechner/*`、协议 SDK（`@modelcontextprotocol/sdk`、`@agentclientprotocol/sdk`）、有 native addon 的包（`sqlite-vec`、`playwright-core`、`node-pty`）、HTTP 框架 `hono`。41 个范围版本用于工具类库 | [[openclaw/dimensions/openclaw-dependency-strategy]] → `package.json: dependencies` |
| hermes-agent | 三层统一锁定 | 所有核心依赖 `>=lower,<upper` 双边界定 + `uv.lock` 5512 行覆盖全依赖树 hash 锁定 + Docker 层基础镜像 SHA256 固定；无 vendor/bundle 策略，所有依赖通过 PyPI + lockfile 管理 | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:15-37`, `uv.lock`, `Dockerfile:1-3,38-39` |

**Concept 状态**：已升级 → [[concept/dependency-version-locking]]

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
> 反向检查：hermes 自己就是 agent 引擎——AIAgent 是自建的编排器（11510 行单文件），不依赖外部 agent 引擎。"自建 vs 绑定"是更上层的架构选择，不构成同一轴的竞争位置。

---

## 如何隔离 Channel SDK 故障域

**维度**：Dependency Strategy
**问题陈述**：在多平台 IM 助手的项目中，如何确保一个 Channel 的 SDK 不会影响其他 Channel 或核心运行时——是通过独立 package 声明、模块内零交叉 import、还是统一依赖声明？
**核心关切**：
- 关切 1：单个 channel SDK 的故障（安全漏洞、版本冲突、安装失败）不能影响核心运行时——隔离性要求独立声明
- 关切 2：用户只需安装自己使用的 channel，不被迫拉入所有 SDK——按需加载要求独立声明
- 关切 3：跨 channel 共享的 plugin 基础设施需要一致接口——共享层要求一定程度的集中约定
- 关切 4：零交叉依赖——每个内置 Channel 是独立的 Python 模块，只 import 自己需要的 SDK
- 关切 5：添加新 Channel 安全——新增 Channel 只增加自己的模块文件，不可能打破已有 Channel 的依赖隔离

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| openclaw | Channel SDK 独立声明 + 故障域隔离 | 每个 channel extension 在自身 package.json 中独立声明 SDK 依赖（Slack 用 @slack/bolt、Telegram 用 grammy 等），不在 root package 聚合，通过 `workspace:*` 引用内部 plugin-sdk。核心运行时不因任何单个 channel SDK 变动受影响 | [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] → `extensions/slack/package.json:1-15`；[[openclaw/nodes/extension-points/openclaw-channel-plugin]] → `src/channels/plugins/types.plugin.ts:53-94` |
| nanobot | Channel 模块独立：零交叉 import | 每个内置 Channel 是独立的 Python 模块（`channels/telegram.py`、`channels/slack.py` 等），只 import 自己需要的 SDK，Channel 之间无相互依赖。版本统一约束在 `pyproject.toml` 主依赖中 | nanobot-dependency-strategy.md:3. Channel 依赖隔离 → `channels/` 目录结构; `pyproject.toml:35-42` |

**Concept 状态**：已升级 → [[concept/channel-sdk-isolation]]
> 反向检查：hermes 是单体仓库，所有依赖在同一个 pyproject.toml 中声明（通过 extras 分组而非独立包）。架构差异（monorepo vs monolith vs 模块内隔离）决定了不同的依赖管理策略。

---

## 如何选择核心 API SDK 的架构锁定

**维度**：Dependency Strategy
**问题陈述**：agent 系统需要与 20+ 模型 provider 通信，是每个 provider 使用其原生 SDK（行为可控但维护成本高），还是选择一个通用 SDK 作为统一路由层（代码简单但形成架构锁定）？
**核心关切**：
- 关切 1：单 SDK 路由简化代码但形成架构锁定——如果 OpenAI SDK 出现破坏性变更或不再满足需求，替换成本极高
- 关切 2：多 SDK 策略分散维护但降低锁定风险——每个 provider 的原生 SDK 各有特点
- 关切 3：OpenAI-compatible 协议的生态覆盖足够广（20+ provider），但 Anthropic 的原生 API 需要单独 SDK
- 关切 4：行为可控性——用原生 SDK 直接调用，provider 适配层的复杂性从第三方库转移到自有代码，但完全掌控行为
- 关切 5：零间接供应商依赖——所有 LLM API 调用都经过自有代码，不依赖任何中间转发层的正确性
- 关切 6：维护成本转移——放弃中间层开箱即用的 30+ provider 支持，需自己维护每个 provider 的 API 兼容细节
- 关切 7：版本风险隔离——不再受中间层版本升级节奏的影响，各 SDK 的版本独立管理

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | OpenAI SDK 统一路由 | 20+ provider 都通过 `openai` SDK 路由（OpenAI-compatible 协议），Anthropic 额外使用原生 SDK 但可通过 `api_mode` 切换回 OpenAI-compatible 路径；核心依赖清单中 openai SDK 替换成本标注为"高——无官方替代" | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:15-37` |
| nanobot | 移除 litellm，使用原生 openai + anthropic SDK | 替换 LLM 转发层为原生 SDK 直接调用，适配逻辑内化到自有 `providers/` 代码中（3,719 行）。行为完全可控，零间接供应商依赖，版本风险隔离 | nanobot-dependency-strategy.md:1. 替换 litellm → `README.md:21`; `providers/registry.py` 整体 |

**Concept 状态**：已升级 → [[concept/llm-api-sdk-strategy]]
> 反向检查：openclaw 深度绑定 `@mariozechner` 私有包族——是更上层的「引擎依赖」问题，不构成同一轴的竞争位置。

---

## 如何在运行时选择多种后端实现

**维度**：Dependency Strategy
**问题陈述**：对于终端执行、Web 搜索、TTS 引擎、记忆存储、上下文压缩等子系统，如何在多个后端实现之间切换而不修改代码？
**核心关切**：
- 关切 1：后端的发现机制——通过 API key 存在性自动发现 vs 显式配置选择
- 关切 2：后端的替换粒度——是整个子系统替换还是允许混合使用
- 关切 3：后端的降级优先级——多个后端可用时的选择策略

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 配置驱动的多后端选择 | 终端 6 种后端（local/docker/ssh/daytona/singularity/modal）、搜索 4 种（Exa/Firecrawl/Tavily/Parallel-Web）、TTS 3 种、记忆 7 选 1、压缩 2+ 种——均通过 `config.yaml` 选择；搜索后端通过 API key 存在性自动发现和回退 | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `config.yaml`, `tools/web_tools.py:1925-1947` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 跨语言生态桥接

**维度**：Dependency Strategy
**问题陈述**：当 Python 生态中不存在某些所需能力（如特定 API 适配）而这些能力在 Node.js 生态中可用时，如何以最小代价获取这些能力？
**核心关切**：
- 关切 1：进程隔离——TypeScript bridge 通过 HTTP 与 Python 核心通信，不共享进程空间，bridge 崩溃不影响 Python 主进程
- 关切 2：主语言纯净——Python 核心不需要引入 Node.js 运行时作为依赖，bridge 是可选的独立组件
- 关切 3：额外成本——跨语言桥接引入了额外的网络通信延迟和部署复杂度（需要同时管理 Python 和 Node.js 两个运行时）

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 独立进程 TypeScript HTTP bridge | `bridge/` 目录独立 Node.js/TypeScript 模块，通过 HTTP 通信，不共享进程空间 | nanobot-dependency-strategy.md:4. Bridge → `bridge/src/index.ts` |

**Concept 状态**：仅 nanobot—待观察
> 种子库待收录：openclaw 本身是 Node.js/TypeScript 项目，hermes-agent 是 Python 单体项目——两者均不面对跨语言桥接问题。

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
> 反向检查：hermes 是 Python 单体项目，没有显式的架构边界 lint 检查。hermes #24（CI 供给链审计）关注的是安全维度的恶意代码检测，而非架构边界约束。可能是未来补充项。

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
> 反向检查：hermes 没有显式的性能预算 CI 门控。可能是未来补充项。

---

## 如何隔离测试环境以确保零残留

**维度**：Testing Philosophy
**问题陈述**：一个读写 `~/.hermes/` 目录、调用真实 API、使用单例模式的 agent 系统，如何在测试中完全隔离以避免污染用户数据和产生费用？
**核心关切**：
- 关切 1：单例模式的跨测试泄漏——`plugin_manager` 等单例必须在测试间重置
- 关切 2：敏感 API key 的误用——测试中需清除环境变量防止意外调用真实 API
- 关切 3：失控测试的保护——单个测试卡死不应拖垮整个 CI

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 自动隔离 fixture + 30s 硬超时 | `_isolate_hermes_home` autouse fixture 将 `HERMES_HOME` 重定向到 `tmp_path/hermes_test/`，清除 `OPENROUTER_API_KEY` 等关键 env var，重置 `plugin_manager` 单例；30 秒 `SIGALRM` 硬超时 kill 任何卡死测试 | [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] → `tests/conftest.py:20-42`, `tests/conftest.py:77-118` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何选择测试的抽象层级

**维度**：Testing Philosophy
**问题陈述**：在测试覆盖的深度和重构友好性之间，是测试行为接口还是测试内部实现？
**核心关切**：
- 关切 1：测试行为接口——重构时测试不需要改动但对复杂内部逻辑的覆盖不足
- 关切 2：测试实现细节——覆盖更全面但重构时测试大面积失效
- 关切 3：Mock 的边界——只在外部边界（API/文件系统/环境）使用 mock，内部模块直接测试

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 行为驱动测试 | 测试公共 API 表面（函数签名、返回格式、边界条件）；对错误路径和边界值有专门测试（空 model fallback、SQL injection 等）；不测试私有实现细节；不对 mock 对象的内部调用做过度断言 | [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] → `tests/` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 如何在 CI 中防范供给链攻击

**维度**：Testing Philosophy
**问题陈述**：开源 agent 项目的 CI pipeline 中，如何检测 PR 中是否包含恶意代码注入（如 litellm-style supply chain attack）、新增不安全的预构建 wheel、或 credential-stealing 载荷？
**核心关切**：
- 关切 1：检测时机——在 PR 阶段阻断而非合并后发现
- 关切 2：检测模式的覆盖面——`.pth` 文件注入、base64+exec/eval 组合、新增预构建 wheel、不安全的 PYTHONPATH
- 关切 3：与 CI 流程的集成——作为独立 workflow 在每次 PR 上运行

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | PR 级供给链审计 workflow | Supply Chain Audit workflow 在每次 PR 上运行：检测 `.pth` 文件（阻止 litellm-style 攻击）、base64+exec/eval 组合（credential-stealing 载荷）、新增预构建 wheel、新增 pip install 命令、不安全的 PYTHONPATH 修改 | [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] → `.github/workflows/supply-chain-audit.yml:1-60` |

**Concept 状态**：仅 hermes-agent—待观察

---

## 测试资源分配策略：风险驱动 vs 行为驱动

**维度**：Testing Philosophy
**问题陈述**：测试资源有限（虽然 26,048 行测试代码是核心运行时的 5.7 倍），如何决定哪些模块值得最密集的测试覆盖——是按风险优先级分配、按模块均衡覆盖、还是按行为接口测试？
**核心关切**：
- 关切 1：安全优先——SSRF 防护、exec 沙箱、workspace 隔离是 agent 框架最不可出错的方面（一个 SSRF 漏洞可能让 agent 成为内网跳板），安全测试的投入远超其他模块
- 关切 2：跨平台一致性——Windows/macOS/Linux 的 exec 行为差异在跨平台测试矩阵（`ubuntu-latest`/`windows-latest`）中覆盖
- 关切 3：覆盖率不均衡——安全测试比重最大，意味着其他功能域（如 memory、cron、hook）的测试覆盖相对薄弱
- 关切 4：集成优于单元——测试集中在集成和关键路径（Channel 交互、工具行为、API 端点），而非每个内部函数的单元测试

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 风险驱动测试分配：安全 + 跨平台 + Channel 交互优先 | 测试投入集中在安全边界、跨平台兼容和 Channel 交互，覆盖率不追求模块间均衡 | nanobot-testing-philosophy.md:1. 测试覆盖重点 → `tests/` 目录; `test_exec_security.py`; `test_sandbox.py` |

**Concept 状态**：仅 nanobot—待观察
> 说明：此轴线关注「测试资源分配优先级」，与 hermes 的「测试抽象层级」和 openclaw 的「CI 架构边界/性能预算」属测试策略的不同维度。

---

## 条目对照清单

### nanobot 草稿 24 条处理情况

| nanobot # | 条目 | 处理 |
|-----------|------|------|
| 1 | 子系统集中组装 | 新条目：仅 nanobot—待观察（A1） |
| 2 | 执行引擎产品层分离 | 新条目：仅 nanobot—待观察（A2） |
| 3 | 四步透明上下文治理 | 合并至「上下文窗口溢出防护」→ 已升级 [[concept/context-window-overflow-guard]] |
| 4 | MessageBus 队列解耦 | 新条目：仅 nanobot—待观察（A3） |
| 5 | 统一 bus 注入 | 合并至「如何在消息驱动的 AI 助手中创建主动触发路径」→ 已升级 [[concept/proactive-trigger-path]] |
| 6 | ContextBuilder 六层拼接 | 新条目：仅 nanobot—待观察（A5） |
| 7 | 显式工具注册 | 合并至「如何发现和注册工具（AST 扫描）」→ 已升级 [[concept/tool-discovery-mechanism]] |
| 8 | 工具排序稳定缓存 | 合并至「Prompt 缓存边界」→ 已升级 [[concept/prompt-cache-boundary]] |
| 9 | Channel 插件双层发现 | 新条目：仅 nanobot—待观察（E2） |
| 10 | 数据驱动 Provider 注册 | 新条目：仅 nanobot—待观察（E3） |
| 11 | CompositeHook 组合策略分化 | 合并至「生命周期 Hook：拦截粒度」→ 已升级 [[concept/lifecycle-hook-granularity]] |
| 12 | Skills Markdown 渐进式加载 | 合并至「如何在无代码情况下扩展 Agent 行为」→ 已升级 [[concept/declarative-skill-extension]] |
| 13 | 子 agent 受限 ToolRegistry | 新条目：仅 nanobot—待观察（E6） |
| 14 | MCP 惰性连接 + 命名空间 | 合并至「如何集成外部工具服务（MCP 协议）」→ 已升级 [[concept/mcp-integration-pattern]] |
| 15 | 纯文件 I/O 三层记忆栈 | 新条目：仅 nanobot—待观察（A6） |
| 16 | Consolidator 异步非阻塞 | 新条目：仅 nanobot—待观察（P3） |
| 17 | 三级 LLM 错误重试 | 新条目：仅 nanobot—待观察（P4） |
| 18 | JSONL 会话持久化 | 新条目：仅 nanobot—待观察（A7） |
| 19 | 移除 litellm 原生 SDK | 合并至「如何选择核心 API SDK 的架构锁定」→ 已升级 [[concept/llm-api-sdk-strategy]] |
| 20 | pip extras 按平台安装 | 合并至「可选依赖分层」→ 已升级 [[concept/optional-dependency-layering]] |
| 21 | Channel 模块零交叉 import | 合并至「如何隔离 Channel SDK 故障域」→ 已升级 [[concept/channel-sdk-isolation]] |
| 22 | TypeScript HTTP bridge | 新条目：仅 nanobot—待观察（D4） |
| 23 | Cron 三模式 + Heartbeat | 合并至「如何调度定时任务和唤醒 agent」→ 已升级 [[concept/agent-scheduling-mechanism]] |
| 24 | 三层安全防护 | 合并至「工具执行安全门控」→ 已升级 [[concept/tool-security-gating]] |

### hermes 草稿 32 条处理情况

| hermes # | 条目 | 处理 |
|----------|------|------|
| 1 | 编排多轮 agent 对话的单一切入点 | 保持：仅 hermes-agent—待观察 |
| 2 | 系统 prompt 内建自学习驱动 | 保持：仅 hermes-agent—待观察 |
| 3 | 平衡命令执行的安全性与流畅性 | 合并至「工具执行安全门控」→ 已升级 [[concept/tool-security-gating]] |
| 4 | 发现和注册工具 (AST 扫描) | 与 nanobot 合并至「如何发现和注册工具（AST 扫描）」→ 已升级 [[concept/tool-discovery-mechanism]] |
| 5 | 抽象多消息平台的统一接口 | 合并至「消息平台适配」→ 已升级 [[concept/im-platform-adapter-granularity]] |
| 6 | 管理外部记忆后端的集成约束 | 合并至「全局能力共存策略」→ 已升级 [[concept/global-capability-coexistence]] |
| 7 | 组织工具为可组合的能力组 | 保持：仅 hermes-agent—待观察 |
| 8 | 管理对话上下文超出窗口时的压缩策略 | 合并至「上下文窗口溢出防护」→ 已升级 [[concept/context-window-overflow-guard]] |
| 9 | 集成外部工具服务（MCP 协议） | 与 nanobot 合并至「如何集成外部工具服务（MCP 协议）」→ 已升级 [[concept/mcp-integration-pattern]] |
| 10 | 管理 agent 生命周期事件的扩展点 | 合并至「生命周期 Hook 拦截粒度」→ 已升级 [[concept/lifecycle-hook-granularity]] |
| 11 | 管理可安装技能的互操作性 | 保持：仅 hermes-agent—待观察 |
| 12 | 管理外部 skill 的安全信任 | 保持：仅 hermes-agent—待观察 |
| 13 | 多轮对话中降低 token 成本 | 合并至「Prompt 缓存边界」→ 已升级 [[concept/prompt-cache-boundary]] |
| 14 | 分类管理工具的并行执行 | 保持：仅 hermes-agent—待观察 |
| 15 | 为不同复杂度查询路由模型 | 保持：仅 hermes-agent—待观察 |
| 16 | 管理 API 多凭证的速率限制 | 保持：仅 hermes-agent—待观察 |
| 17 | 限制 agent 单次任务计算预算 | 保持：仅 hermes-agent—待观察 |
| 18 | 管理可选依赖的优雅降级 | 合并至「可选依赖分层」→ 已升级 [[concept/optional-dependency-layering]] |
| 19 | 选择核心 API SDK 的架构锁定 | 与 nanobot 合并至「如何选择核心 API SDK 的架构锁定」→ 已升级 [[concept/llm-api-sdk-strategy]] |
| 20 | 实现依赖的可重复构建 | 合并至「依赖版本锁定」→ 已升级 [[concept/dependency-version-locking]] |
| 21 | 运行时选择多种后端实现 | 保持：仅 hermes-agent—待观察 |
| 22 | 隔离测试环境以确保零残留 | 保持：仅 hermes-agent—待观察 |
| 23 | 选择测试的抽象层级 | 保持：仅 hermes-agent—待观察 |
| 24 | CI 中防范供给链攻击 | 保持：仅 hermes-agent—待观察 |
| 25 | 为特定场景精简 agent 的工具面 | 保持：仅 hermes-agent—待观察 |
| 26 | Gateway 模式下实现阻塞式审批 | 合并至「审批阻塞等待机制」→ 已升级 [[concept/approval-blocking-mechanism]] |
| 27 | 分离关注点防止单层膨胀 | 保持：仅 hermes-agent—待观察 |
| 28 | 管理日志的安全性和可追溯性 | 保持：仅 hermes-agent—待观察 |
| 29 | 管理后台进程的生命周期 | 保持：仅 hermes-agent—待观察 |
| 30 | 记忆上下文跨 turn 预取 | 合并至「记忆检索与注入时机」→ 已升级 [[concept/memory-retrieval-timing]] |
| 31 | 选择上下文压缩的摘要预算 | 合并至「上下文压缩资源分配」→ 已升级 [[concept/compression-resource-allocation]] |
| 32 | 缓存模型元数据加速启动 | 保持：仅 hermes-agent—待观察 |

### openclaw 种子库 22 条处理情况

| openclaw # | 条目 | 处理 |
|-----------|------|------|
| 1 | 如何门控工具权限 | 合并至「工具执行安全门控」→ 已升级 [[concept/tool-security-gating]] |
| 2 | 如何在消息驱动架构中创建主动触发路径 | 与 nanobot 合并至「如何在消息驱动的 AI 助手中创建主动触发路径」→ 已升级 [[concept/proactive-trigger-path]] |
| 3 | 如何设计 Exec 类工具的审批流程 | 合并至「审批阻塞等待机制」→ 已升级 [[concept/approval-blocking-mechanism]] |
| 4 | 如何注入记忆到 LLM 上下文 | 合并至「记忆检索与注入时机」→ 已升级 [[concept/memory-retrieval-timing]] |
| 5 | 如何选择 LLM Provider 的实现 | 保持：仅 openclaw—待观察（反向检查：hermes OpenAI SDK 统一路由消除多 harness 问题） |
| 6 | 如何管理上下文引擎和记忆能力的全局唯一性 | 参与两条：合并至「全局能力共存策略」→ 已升级 [[concept/global-capability-coexistence]]；同时参与「上下文压缩引擎可插拔架构」→ 已升级 [[concept/context-engine-pluggability]] |
| 7 | 如何在无代码情况下扩展 Agent 行为 | 与 nanobot 合并至「如何在无代码情况下扩展 Agent 行为」→ 已升级 [[concept/declarative-skill-extension]] |
| 8 | 如何分解 Channel Plugin 的适配器接口 | 合并至「消息平台适配」→ 已升级 [[concept/im-platform-adapter-granularity]] |
| 9 | 如何提供 Plugin SDK 的双入口模式 | 保持：仅 openclaw—待观察（反向检查：hermes 无统一 plugin SDK） |
| 10 | 如何将生命周期 Hook 设计为扩展拦截面 | 合并至「生命周期 Hook 拦截粒度」→ 已升级 [[concept/lifecycle-hook-granularity]] |
| 11 | 如何平衡 Context 压缩的可恢复性与压缩率 | 合并至「上下文压缩资源分配」→ 已升级 [[concept/compression-resource-allocation]] |
| 12 | 如何优化冷启动速度 | 保持：仅 openclaw—待观察（反向检查：Node.js 特有优化 vs Python 不同技术栈） |
| 13 | 如何设计 Prompt 缓存边界 | 合并至「Prompt 缓存边界」→ 已升级 [[concept/prompt-cache-boundary]] |
| 14 | 如何防止 Context Window 不足导致截断失败 | 合并至「上下文窗口溢出防护」→ 已升级 [[concept/context-window-overflow-guard]] |
| 15 | 如何管理消息入站的突发流 | 保持：仅 openclaw—待观察（反向检查：hermes 未将消息防抖作为显式设计选择） |
| 16 | 如何选择 AI 引擎依赖策略 | 保持：仅 openclaw—待观察（反向检查：hermes 自建引擎，"自建 vs 绑定"是更上层选择） |
| 17 | 如何隔离 Channel SDK 故障域 | 与 nanobot 合并至「如何隔离 Channel SDK 故障域」→ 已升级 [[concept/channel-sdk-isolation]] |
| 18 | 如何区分版本锁定策略 | 合并至「依赖版本锁定」→ 已升级 [[concept/dependency-version-locking]] |
| 19 | 如何管理重型可选依赖 | 合并至「可选依赖分层」→ 已升级 [[concept/optional-dependency-layering]] |
| 20 | 如何将架构边界约束从文档变为可执行检查 | 保持：仅 openclaw—待观察（反向检查：hermes 无架构边界 CI lint） |
| 21 | 如何保证 Plugin 接口稳定性 | 保持：仅 openclaw—待观察（反向检查：hermes 无统一 plugin 系统） |
| 22 | 如何将性能预算纳入 CI 门控 | 保持：仅 openclaw—待观察（反向检查：hermes 无性能预算 CI 检查） |

---

## 统计

| 指标 | 数量 |
|------|------|
| 种子库总条目 | 58 |
| 已升级为 Concept | 19 |
| 仅 openclaw—待观察 | 8 |
| 仅 hermes-agent—待观察 | 18 |
| 仅 nanobot—待观察 | 13 |
| nanobot 草稿条目（已全部处理） | 24 |
| hermes 草稿条目（已全部处理） | 32 |
| openclaw 种子库条目（已全部处理） | 22 |
