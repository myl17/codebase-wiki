# nanobot 设计选择轴定位

> 将 nanobot 的 25 条设计选择在种子库（openclaw + hermes-agent，44 条）中做轴定位。
> 生成日期：2026-06-19

---

## 概览统计

| 类型 | 数量 | 说明 |
|------|------|------|
| A 新位置 | 8 | 种子库轴线仅有 1 个仓库，nanobot 首次带来第 2 个位置 |
| B 已有位置 | 5 | 种子库轴线已有 2+ 仓库，nanobot 增加第 3+ 个位置 |
| C 已有轴首次出现分歧 | 3 | 种子库轴线已有多仓库位置，但 nanobot 从根本上重新解释轴线定义 |
| 新轴 | 9 | 种子库不存在此问题域的全新轴线 |
| **合计** | **25** | |

反向检查：种子库 32 条「待观察」条目中，nanobot 面对 **8** 条，已在对应轴线定位中补充。

---

## Architecture 维度（8 条）

---

## A1. 子系统集中组装：构造函数 Hub vs 中央编排器

**对齐种子库**：hermes #1「如何编排多轮 agent 对话的单一切入点」
**定位类型**：**新轴**

**标准化问题陈述**：一个由 10+ 子系统组成的 agent 框架，如何将所有子系统的初始化、依赖注入和生命周期管理集中在一个位置——是通过中央编排器吸收所有执行路径，还是通过构造函数在单个 Hub 中显式组装所有子系统？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 所有执行路径必须经过同一编排逻辑，改动才能一致生效 | hermes |
| 中央编排器的规模会随功能增长膨胀（hermes 11510 行单文件） | hermes |
| 无替换机制意味着中央编排器的任何错误阻断所有入口 | hermes |
| 可发现性——所有连线逻辑集中在一个文件的单个函数中，读一个构造函数就能完整理解系统组成 | nanobot |
| 可测试性牺牲——集中式组装意味着无法对单个子系统做独立单元测试 | nanobot |
| 启动耦合——所有子系统在启动时一次性初始化，无法按需延迟加载 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| hermes-agent | **AIAgent 中央编排器**：11510 行单文件吸收所有执行路径（CLI/Gateway/Cron/ACP），无替换机制 | 所有路径统一编排，改动一致生效；代价：单文件巨大，错误阻断所有入口 |
| nanobot | **单体 Hub 集中组装**：AgentLoop.\_\_init\_\_() 作为唯一架构入口，在一个方法中实例化并注入所有子系统 | 可发现性极高，读构造函数即理解全貌；代价：无法独立单元测试子系统，启动时全部初始化 |
| openclaw | 不面对此问题——openclaw 基于 plugin SDK 的分散式架构，无集中式子系统组装概念 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| hermes-agent | [[hermes-agent/nodes/components/hermes-agent-ai-agent]] → `run_agent.py:535-560`, `run_agent.py:8130-8189` |
| nanobot | nanobot-architecture.md:1. AgentLoop → `agent/loop.py:115-228` |

> **说明**：虽然两者都采用集中式架构模式，但核心问题不同——hermes 关注的是「多入口路由到同一编排循环」，nanobot 关注的是「构造函数中显式 DI 组装」。当前是两个独立轴线，未来可考虑合并为「Agent 系统集中式集线器模式」的父轴。

---

## A2. 执行引擎的产品层分离

**对齐种子库**：无直接匹配
**定位类型**：**新轴**

**标准化问题陈述**：如何让同一套 tool-calling 循环引擎同时服务主 agent、子 agent 和后台记忆处理，而不让引擎依赖任何产品层概念（channel、session、cron）？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 引擎复用——AgentRunner 不 import channel、session、cron 等产品层模块，只关心「收消息 -> 调 LLM -> 执行工具」 | nanobot |
| 上下文盲区——AgentRunner 不知道自己在为主 agent 还是子 agent 服务，无法根据上下文调整行为 | nanobot |
| 职责分离——所有产品层逻辑在 AgentLoop 层处理，AgentRunner 只管纯粹的 LLM 交互循环 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **产品层无关的纯执行引擎**：AgentRunner 接受 AgentRunSpec 纯数据配置，与产品层零耦合，同时驱动主 agent、子 agent、Dream Phase 2 | 引擎高度复用，一次编写三处受益；代价：引擎对上下文盲，无法针对不同场景优化行为 |
| openclaw | 未显式分离——编排逻辑与执行逻辑耦合在 agent harness 中 | — |
| hermes-agent | 未显式分离——AIAgent 中央编排器同时包含编排逻辑和执行逻辑 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-architecture.md:2. AgentRunner → `agent/runner.py:83-97`; `agent/loop.py:300-355`; `agent/subagent.py:140-150`; `agent/memory.py:519+` |

> **种子库待收录**：openclaw 和 hermes-agent 均未将「执行引擎与产品层分离」作为显式设计选择。此轴线为 nanobot 带来，待未来轮次观察另外两仓库是否隐含面对此问题。

---

## A3. Channel 层与 Agent 核心的解耦机制

**对齐种子库**：无直接匹配（种子库有「消息平台适配：接口分解粒度」但那是适配器接口粒度问题，非通信解耦机制）
**定位类型**：**新轴**

**标准化问题陈述**：如何让不同的 IM Channel 与 Agent 核心完全解耦，使新增 Channel 不需要修改 AgentLoop 的任何代码——是通过异步队列、同步回调、还是事件总线？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 接口统一——Channel 只操作 publish_inbound()/consume_outbound()，AgentLoop 只操作 consume_inbound()/publish_outbound() | nanobot |
| 异步解耦——使用 asyncio.Queue 而非同步调用，Channel 和 AgentLoop 各自独立运行，生产消费速率解耦 | nanobot |
| 排队语义——队列引入消息缓冲和潜在延迟，不适合需要同步响应的场景 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **MessageBus 异步队列解耦**：asyncio.Queue 将 Channel 层与 Agent 核心完全解耦，双方只操作统一的消息队列接口 | Channel 与 Agent 完全解耦，新增 Channel 零修改 Agent 核心；代价：队列引入延迟，不适合同步响应 |
| openclaw | Channel Plugin 通过 Adapter 接口直接与核心交互，非队列解耦 | — |
| hermes-agent | BasePlatformAdapter 直接调用，Gateway 层同步处理 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-architecture.md:3. MessageBus → `bus/queue.py:8-35` |

> **种子库待收录**：openclaw 和 hermes-agent 均未将 Channel-Agent 通信解耦机制作为显式设计选择突出。

---

## A4. 非消息事件的入站路径：统一注入 vs 独立通道

**对齐种子库**：openclaw「如何在消息驱动的 AI 助手中创建主动触发路径」
**定位类型**：**A 新位置**（种子库仅有 openclaw 1 个仓库，nanobot 首次带来第 2 个位置）

**标准化问题陈述**：子 agent 完成结果、Cron 触发消息、Heartbeat 唤醒消息等非用户 IM 消息事件，如何进入主 agent 的处理流程——应该走独立路径（隔离 session）还是复用现有入站消息路径（统一注入）？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 主动触发路径不应破坏消息驱动模型的清晰性——两条路径共存需要明确的边界 | openclaw |
| 定时触发的执行结果必须可投递回消息通道——主动触发的结果需要消息通道作为出口 | openclaw |
| 每次定时触发应使用独立的 agent session，不与用户对话 session 混淆 | openclaw |
| 处理统一性——子 agent 结果通过 bus.publish_inbound() 注入入站队列，与 IM 消息走完全相同的消费路径，AgentLoop 不需要区分消息来源 | nanobot |
| 语义丢失——子 agent 结果和 IM 消息在系统中没有任何语义区别，无法对不同来源的消息做差异化路由或优先级 | nanobot |
| 架构简化——统一入站路径避免了多条处理管线的维护成本 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| openclaw | **Cron 作为唯一无消息主动触发入口**：CronScheduler 创建独立 isolated-agent session，CronDeliveryPlan 决定结果投递目标（channel/thread/announce/webhook），与消息驱动的 agent 运行隔离 | 两条路径边界清晰，session 不混淆；代价：多套处理管线 |
| nanobot | **统一 bus 注入：子 agent 结果等同于 IM 消息**：子 agent、Cron、Heartbeat 的所有触发消息统一通过 bus.publish_inbound() 注入，复用 AgentLoop 的主消费路径 | 架构简化，单套处理逻辑维护成本低；代价：所有来源的消息无差别对待，无法做差异化路由 |
| hermes-agent | Cron 只是又一个入口通向同一编排循环，不区分「消息驱动」和「主动触发」路径——不面对此问题 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| openclaw | [[openclaw/nodes/components/openclaw-cron-scheduler]] → `src/cron/delivery-plan.ts:10-19`; `src/tasks/task-executor.ts:85-112` |
| nanobot | nanobot-architecture.md:数据流 → `agent/subagent.py:202-209`; `agent/loop.py:363-556` |

---

## A5. 系统 Prompt 的组装方式

**对齐种子库**：部分相关 hermes「如何在系统 prompt 中内建自学习驱动」，但核心问题不同
**定位类型**：**新轴**

**标准化问题陈述**：系统 prompt 由多个独立来源组成（identity、bootstrap files、memory、skills、history），如何组装这些内容使得每层可以独立修改和测试——是纯数据到文本的拼接，还是嵌入驱动性指令？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 可测试性——ContextBuilder 不持有 AgentLoop 引用、不调用 LLM、不管理工具，是纯数据到文本的转换层，可以独立单元测试 | nanobot |
| 层次独立——六层内容依次拼接，每层用 `---` 分隔，修改一层不影响其他层 | nanobot |
| 运行时效率——skills 摘要支持渐进式加载（always skills 全文注入 + 其他仅在摘要中列出），避免所有技能内容塞满 system prompt | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **ContextBuilder 纯数据到文本的六层拼接**：六层独立内容依次拼接为 system prompt，ContextBuilder 是无副作用的纯转换层 | 层次独立可测试，渐进式加载节省 token；代价：无自学习驱动能力 |
| hermes-agent | **三段自驱动 system prompt**：MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE 嵌入 system prompt，驱动 LLM 自主改进 | LLM 可自主积累知识；代价：虚假记忆风险 |
| openclaw | Context Engine 组装阶段注入记忆和技能内容 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-architecture.md:4. ContextBuilder → `agent/context.py:17-63` |
| hermes-agent | [[hermes-agent/nodes/design-decisions/hermes-agent-self-learning-loop-decision]] → `agent/prompt_builder.py:145-171` |

---

## A6. 记忆存储：纯文件 vs 外部数据库

**对齐种子库**：无直接匹配（种子库有记忆检索时机和记忆 provider 共存，但无存储后端选择轴）
**定位类型**：**新轴**

**标准化问题陈述**：如何实现 agent 的长期记忆——包括用户档案、对话历史压缩和记忆更新——是使用纯文件 I/O（零外部依赖）还是引入嵌入式数据库或向量检索？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 零外部依赖——MemoryStore 是纯文件 I/O（读/写 MEMORY.md、history.jsonl），无嵌入式数据库，无向量检索 | nanobot |
| 检索质量取舍——文件级记忆无法做语义检索，只能线性读取整个 MEMORY.md 内容放入 system prompt，记忆量受 context window 限制 | nanobot |
| 三级处理栈——MemoryStore（持久化）-> Consolidator（后台压缩）-> Dream（两阶段 LLM 驱动更新），每层职责明确 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **纯文件 I/O 三层记忆栈（无向量检索）**：MemoryStore 文件读写 + Consolidator 异步压缩 + Dream 两阶段 LLM 处理，全部基于文件系统 | 零外部依赖，部署简单；代价：无法语义检索，记忆量受 context window 限制 |
| hermes-agent | 支持 7 种外部记忆后端（Honcho/Mem0/Supermemory 等），加性叠加 builtin 存储 | 可扩展性强，支持语义检索；代价：引入外部依赖 |
| openclaw | 可插拔 MemoryCapability 接口，支持外部记忆后端注册 | 可扩展；代价：需要外部依赖 |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-architecture.md:8. MemoryStore → `agent/memory.py:27-228,346+,519+` |

---

## A7. 会话状态持久化机制

**对齐种子库**：无直接匹配
**定位类型**：**新轴**

**标准化问题陈述**：多轮对话的会话状态应该如何持久化——在文件级存储、内存缓存和惰性加载之间如何权衡？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 无外部 DB——会话以 JSONL 文件存储，无需数据库 | nanobot |
| 内存效率——内存缓存 + 惰性加载，不将所有会话长驻内存 | nanobot |
| 边界对齐——get_history() 或 retain_recent_legal_suffix() 在每轮开始时裁剪历史到合法边界，防止 LLM 看到不完整的 tool-call 对 | nanobot |
| 单一天地入口——get_or_create() 是唯一入口函数 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **JSONL 文件存储 + 内存缓存 + 惰性加载 + 合法边界裁剪** | 无外部 DB 依赖，合法边界裁剪防止上下文损坏；代价：文件级存储，无查询能力 |
| hermes-agent | Gateway session 管理，PII 哈希化存储 | — |
| openclaw | 会话通过 agent session 管理 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-architecture.md:7. SessionManager → `session/manager.py:50-94,119-204` |

> **种子库待收录**：hermes-agent 和 openclaw 均未将会话持久化机制作为显式设计选择条目。

---

## A8. 定时任务调度与 Agent 唤醒

**对齐种子库**：与 A4 共享同一 openclaw 种子条目「如何在消息驱动的 AI 助手中创建主动触发路径」，但聚焦调度机制本身
**定位类型**：**B 已有位置**（与 A4 共同扩展 openclaw 主动触发轴线的调度侧）

**标准化问题陈述**：如何实现 agent 的定时任务调度——是使用传统 cron 机制、定时器轮询、还是 LLM 驱动的智能唤醒？多种调度模式如何共存？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 三种调度模式共存——at（一次性）、every（间隔）、cron（cron 表达式），满足从精确时刻到周期循环的所有场景 | nanobot |
| 多进程安全——CronStore 使用 FileLock 做持久化，防止多进程环境下的重复执行 | nanobot |
| LLM 驱动唤醒的可靠性——Heartbeat 使用专用单工具 LLM 调用做定期唤醒，agent 自主判断是否需要执行任务——依赖 LLM 的判断准确性，可能漏判或误判 | nanobot |
| Cron 作为唯一无消息主动触发入口，每次创建独立 session | openclaw |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **Cron 三模式调度 + Heartbeat LLM 自主唤醒**：Cron（at/every/cron）+ Heartbeat（LLM 通过 heartbeat tool 判断是否执行），统一通过 bus 注入 | 覆盖所有调度场景，LLM 自主判断提供灵活性；代价：LLM 判断可能不准确 |
| openclaw | **CronScheduler 唯一主动触发入口**：每次 cron 触发创建独立 isolated-agent session | 边界清晰；代价：仅支持 cron 表达式，无 LLM 驱动唤醒 |
| hermes-agent | Cron 作为编排循环的又一个入口 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-architecture.md:11. 调度系统 → `cron/service.py:1-50`; `heartbeat/service.py:14-40` |
| openclaw | [[openclaw/nodes/components/openclaw-cron-scheduler]] → `src/cron/delivery-plan.ts:10-19` |

---

## Performance Tradeoffs 维度（4 条）

---

## P1. 上下文治理：透明预处理 vs 显式压缩管线

**对齐种子库**：「上下文窗口溢出防护：触发策略」（concept/context-window-overflow-guard）+「上下文压缩：资源分配策略」（concept/compression-resource-allocation）
**定位类型**：**C 已有轴首次出现分歧**

**标准化问题陈述**：如何在每次 LLM 调用前自动治理上下文窗口——修复不完整数据、压缩旧内容、截断超长结果、裁剪超预算历史——同时所有治理操作对 LLM 完全透明（LLM 不知道上下文被裁剪过）？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 压缩阈值的选择——太早触发浪费 token，太晚触发有截断丢失风险 | openclaw / hermes-agent |
| 压缩后摘要必须保留足够信息使 agent 可恢复任务执行 | openclaw |
| 用户通知不能注入 LLM——避免模型因感知到上下文压力而提前放弃 | hermes-agent |
| **对 LLM 透明**——四层治理全部在 AgentRunner 内部完成，LLM 不知道上下文被裁剪过、不知道某些 tool result 已被替换为摘要，避免了 LLM 提前放弃任务 | nanobot |
| **LLM 策略盲区**——LLM 无法主动调整自己的对话策略来适应有限的上下文，因为它不知道上下文已被压缩 | nanobot |
| **关键路径性能**——四步治理在每次 LLM 调用的关键路径上自动运行（Backfill -> Microcompact -> Budget -> Snip），任何一步出错都可能导致 LLM 看到损坏的上下文 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **四步透明上下文治理**：Backfill（修复孤立 tool_use）+ Microcompact（压缩 10 轮前的 tool result）+ Tool Result Budget（截断超长结果）+ Snip History（按 token 预算从尾部裁剪），全部对 LLM 透明 | LLM 不知道上下文压力，不会提前放弃任务；代价：LLM 无法主动调整策略适应有限上下文，关键路径任何一步出错导致损坏上下文 |
| openclaw | **可恢复性优先压缩**：摘要指令优先保留活跃任务状态，SAFETY_MARGIN=1.2 补偿 token 估算误差 | 任务可恢复性高；代价：牺牲历史细节完整性 |
| hermes-agent | **20% 摘要预算 + 600s 冷却**：摘要预算为压缩内容的 20%，上限 12,000 tokens；用户通知分层但不注入 LLM | 成本可控，冷却期防止重试风暴；代价：高压缩率损失细节 |

**轴线重新解释**：nanobot 将「上下文治理」从「何时触发压缩 + 如何分配预算」重新定义为「透明预处理管线」——核心差异不在压缩策略，而在 LLM 是否知情。这迫使轴线考虑一个新维度：**LLM 感知 vs LLM 透明**的治理哲学。

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-performance-tradeoffs.md:1. Context Governance → `agent/runner.py:552-697` |
| openclaw | [[openclaw/nodes/design-decisions/openclaw-compaction-recoverability-priority]] → `src/agents/compaction.ts:19-40` |
| hermes-agent | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/context_compressor.py:51-60` |

---

## P2. Prompt Cache 稳定化：工具排序 vs 内容边界

**对齐种子库**：「Prompt 缓存边界：划分策略」（concept/prompt-cache-boundary）
**定位类型**：**B 已有位置**（种子库已有 openclaw + hermes-agent 两个位置，nanobot 增加第三个）

**标准化问题陈述**：如何确保每次请求中 LLM prompt cache 的前缀部分稳定不变，使动态内容（如 MCP 工具的增删）不破坏已缓存的内容——是通过内容边界标记、消息分层缓存、还是工具定义排序？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 尽可能多的 token 命中缓存以减少每轮 API 费用 | openclaw / hermes-agent |
| 动态内容必须放在缓存边界之后，不能混入缓存区 | openclaw |
| cache breakpoint 数量受限于 provider（Anthropic 上限 4 个） | openclaw |
| 跨消息复用 agent 实例才能保持 cache prefix 有效 | hermes-agent |
| **缓存稳定性**——builtins 按名称排序放在前面作为稳定前缀，MCP 工具放后面，只要 MCP 工具不变缓存就不会被破坏 | nanobot |
| **缓存命中率**——排序策略直接决定 Anthropic prompt cache 的命中率，进而影响每次 LLM 调用的成本和延迟 | nanobot |
| **工具数量敏感**——如果 builtins 数量过多，缓存前缀本身就会很大，留给 MCP 工具和消息的缓存空间会减少 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **工具定义排序：builtins 前缀 + MCP 后缀**：get_definitions() 按名称排序 builtins 在前、MCP 工具在后，构成 Anthropic prompt cache 的稳定前缀 | 简单直接，不依赖内容标记；代价：工具数量大时缓存前缀本身很大 |
| openclaw | **稳定前缀 + 动态后缀分离**：system prompt 中插入 CACHE_BOUNDARY 标记，stable prefix 打上 cache_control 标记，动态后缀在 boundary 后插入 | 内容级精确控制；代价：依赖 provider 的 cache_control API |
| hermes-agent | **system_and_3 缓存策略**：4 个 cache breakpoints（system prompt 占 1 个 + 最后 3 条非 system 消息占 3 个），跨消息缓存 AIAgent 实例 | 滚动窗口适应对话动态性；代价：breakpoint 数量固定，灵活性受限 |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-performance-tradeoffs.md:3. Prompt Cache → `agent/tools/registry.py:45-63` |
| openclaw | [[openclaw/nodes/components/openclaw-context-engine]] → `src/agents/system-prompt-cache-boundary.ts:3-47` |
| hermes-agent | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/prompt_caching.py:1-73` |

---

## P3. 记忆压缩的非阻塞执行

**对齐种子库**：部分相关「记忆检索与注入时机」（concept/memory-retrieval-timing），但关注不同阶段
**定位类型**：**新轴**

**标准化问题陈述**：记忆压缩需要调用 LLM 进行历史总结，如何在不阻塞主 agent 对话的前提下完成压缩，且压缩失败不影响正在进行的对话？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| Provider 实例隔离——Consolidator 使用独立的 LLM provider 实例，不共享主 agent 的 provider 状态（如速率限制计数器），压缩和对话互相不干扰 | nanobot |
| 异步解耦——在 asyncio.create_task() 中后台运行，主 agent 在压缩运行期间不受影响 | nanobot |
| 结果延迟生效——压缩结果在下一轮 context 组装时才生效，本轮对话使用压缩前的内容，失败不中断对话 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **Consolidator 独立 Provider 实例 + 异步后台任务**：独立的 LLM provider 实例 + asyncio.create_task() 后台运行，主循环不阻塞 | 压缩和对话互不干扰；代价：多一个 provider 实例的资源开销 |
| openclaw | Prompt 组装阶段批量注入记忆，非实时查询 | — |
| hermes-agent | 后台预取 + 不阻塞关键路径 | 记忆检索不阻塞 API 调用；代价：记忆可能不是最新状态 |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-performance-tradeoffs.md:4. Consolidator → `agent/loop.py:210-219,572`; `agent/memory.py:346+` |

> **种子库待收录**：此轴线关注的是「记忆压缩的非阻塞执行」，与种子库的「记忆检索时机」关注不同阶段（压缩 vs 检索）。未来可合并为「记忆操作的异步策略」父轴。

---

## P4. LLM API 错误处理与重试策略

**对齐种子库**：无直接匹配
**定位类型**：**新轴**

**标准化问题陈述**：如何设计 LLM API 调用的重试策略，使其能区分临时性错误（可重试）和永久性错误（不可重试），并在速率限制和配额耗尽的处理上做出不同响应？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 错误分类粒度——429 错误按语义分类：配额耗尽类（非重试）vs 速率限制类（重试 + 等待 Retry-After） | nanobot |
| 重试策略分级——standard 模式 3 次指数退避 vs persistent 模式无限制但相同错误超过 10 次停止 | nanobot |
| 内容降级——图片内容导致的 API 错误自动降级为纯文本重试 | nanobot |
| 维护复杂度——三级重试逻辑在基类统一实现，但错误分类依赖各 provider 的 error code 规范 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **三级重试：standard 3 次退避 + persistent 无限制限停 + 429 语义分类**：基类统一实现，区分临时/永久错误，429 分类为配额 vs 限速，图片错误自动降纯文本 | 错误分类精细，重试策略灵活；代价：维护复杂度高，依赖 provider error code 规范 |
| hermes-agent | fill_first + 被动追踪 12 个 x-ratelimit-* header，收到 429 后才切换 fallback | 充分利用每个 key 的配额；代价：偶尔浪费一次请求 |
| openclaw | 未将 LLM 重试策略作为显式设计选择突出 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-performance-tradeoffs.md:5. LLM Provider 重试 → `providers/base.py:629-698` |

---

## Extension Points 维度（8 条）

---

## E1. 工具注册与发现：显式注册 vs AST 扫描

**对齐种子库**：hermes「如何发现和注册工具（AST 扫描）」
**定位类型**：**A 新位置**（种子库仅有 hermes-agent 1 个仓库，nanobot 首次带来第 2 个位置，且为相反立场）

**标准化问题陈述**：工具应该被自动发现（装饰器/AST 扫描）还是显式注册——如何权衡发现便利性和注册确定性？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 自动发现机制要求注册调用必须是静态可发现的顶层调用，限制了动态注册的灵活性 | hermes-agent |
| AST 扫描引入启动开销，工具越多解析越慢 | hermes-agent |
| 同样的自动发现哲学是否应一致应用于 hooks、skills 等其他扩展 | hermes-agent |
| 注册确定性——显式 register() 不做 AST 扫描、不做装饰器发现，每个工具必须在 _register_default_tools() 中点名，不存在隐式工具被发现或遗漏 | nanobot |
| 扩展成本——每个新工具需要两步操作：创建 Tool 子类 + 在 register 处点名，相比装饰器自动发现多了一步手工操作 | nanobot |
| 调试可见性——所有已注册工具可通过 get_definitions() 一次性获取完整列表，工具清单是明确的而非推断的 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **显式 register() 注册，零自动发现**：所有工具通过显式 tool_registry.register() 调用注册，不做 AST 扫描或装饰器发现 | 注册确定性强，调试可见性高；代价：每个新工具多一步手工操作 |
| hermes-agent | **AST 扫描自动发现**：进程启动时通过 AST 扫描所有 registry.register() 顶层调用自动发现工具，新增工具只需写注册调用无需手动接线 | 零额外接线，新增工具摩擦小；代价：启动开销，限制动态注册灵活性 |
| openclaw | 未面对此问题——工具通过 plugin harness 注册 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-extension-points.md:1. ToolRegistry → `agent/tools/registry.py:8-99`; `agent/loop.py:229-255` |
| hermes-agent | [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]] → `tools/registry.py:28-73` |

---

## E2. Channel 插件发现：自扫描 vs 显式注册

**对齐种子库**：无直接匹配（种子库有 Channel 适配器接口粒度轴，但那是接口设计问题，非发现机制）
**定位类型**：**新轴**

**标准化问题陈述**：如何让内置 Channel 和外部第三方 Channel 都能被自动发现，同时确保外部插件无法覆盖内置实现？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 双层发现——内置 Channel 通过 pkgutil.iter_modules() 自动扫描，外部 Channel 通过 Python entry_points 机制注册 | nanobot |
| 安全边界——内置 Channel 优先级高于外部插件，外部插件不能 shadow 同名内置 Channel | nanobot |
| 无需注册文件——内置 Channel 不需要维护显式注册表，新增模块文件即注册 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **pkgutil 自发现 + entry_points 外部插件，内置优先**：内置 Channel 通过 pkgutil 自动发现，外部插件通过 entry_points 注册，内置实现不受外部插件覆盖 | 内置无需维护注册表，外部可扩展，安全边界清晰；代价：pkgutil 扫描有启动开销 |
| openclaw | defineBundledChannelEntry 统一注册入口，Channel extension 独立 package | 注册入口统一；代价：非自动发现 |
| hermes-agent | 22 个平台通过 BasePlatformAdapter 继承，16 步 checklist 注册 | 统一接口；代价：新增平台需手动 checklist |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-extension-points.md:2. Channel Plugin → `channels/registry.py:17-72` |

---

## E3. LLM Provider 注册：数据驱动 vs 代码驱动

**对齐种子库**：部分相关 openclaw「如何选择 LLM Provider 的实现」和 hermes「如何选择核心 API SDK 的架构锁定」，但核心问题不同
**定位类型**：**新轴**

**标准化问题陈述**：如何支持 20+ LLM provider 而无需为每个 provider 编写大量适配代码——如何让新增 provider 成为纯数据操作而非代码修改？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 数据驱动注册——新增 provider 只需在 PROVIDERS 元组中加一行 ProviderSpec 数据，所有匹配、检测、状态展示逻辑都从元组派生 | nanobot |
| 统一接口——LLMProvider 抽象基类定义统一的 chat()/chat_stream() 接口，子类只需实现其中一个方法，重试逻辑在基类中统一实现 | nanobot |
| 覆盖范围有限——仅支持 5 种 backend 风格，非标准 API 风格的 provider 需要新 backend | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **数据驱动 ProviderSpec 注册表**：Provider 元数据集中在 PROVIDERS 元组中，5 种 backend 风格覆盖 20+ provider，新增 provider 是纯数据操作 | 新增 provider 成本极低；代价：backend 风格有限，非标准 provider 需新 backend |
| openclaw | 优先级排序 + 能力匹配选择 harness | 运行时灵活选择；代价：新增 harness 需代码实现 |
| hermes-agent | OpenAI SDK 统一路由，20+ provider 通过 openai SDK 通信 | 代码简单；代价：架构锁定 OpenAI SDK |

> **说明**：此轴线关注「provider 注册表的数据驱动设计」，与 hermes 的「SDK 架构锁定」（Dependency Strategy 维度）和 openclaw 的「运行时 harness 选择」（Extension Points 维度）属于 LLM provider 管理的不同子问题。

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-extension-points.md:3. Provider Registry → `providers/registry.py:1-376` |

---

## E4. 生命周期 Hook：组合策略分化 vs 统一粗/细粒度

**对齐种子库**：「生命周期 Hook：拦截粒度」（concept/lifecycle-hook-granularity）
**定位类型**：**B 已有位置**（种子库已有 openclaw + hermes-agent 两个位置，nanobot 增加第三个）

**标准化问题陈述**：如何提供一套生命周期钩子机制，使外部插件能够在 agent 循环的关键时刻注入自定义行为，同时不同钩子的组合策略应该适配各自的语义（内容变换 vs 事件通知）？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| Hook handler 可能修改核心数据——需明确区分可修改和只读的 hook | openclaw |
| 事件粒度的权衡——过细增加 hook 实现者负担，过粗限制精确拦截能力 | openclaw / hermes-agent |
| 多 handler 执行顺序和失败处理需可预测 | openclaw / hermes-agent |
| 组合策略分化——finalize_content 采用纯函数管线（管道串联，前一 hook 输出是后一 hook 输入），其余五个方法采用扇出（每个 hook 独立执行，一个异常不阻塞其他） | nanobot |
| 语义适配——finalize_content 是内容变换，适合管道逐步加工；其余方法是事件通知，适合扇出避免单点阻塞 | nanobot |
| 运行时注入——AgentLoop 维护 _extra_hooks 列表，外部插件可在运行时添加钩子而不修改核心代码，但多个插件的 hook 执行顺序依赖注入顺序 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **CompositeHook：内容变换用管道，事件通知用扇出**：六个生命周期拦截点中，finalize_content 是纯函数管线，其余五法是独立并行的扇出模式 | 组合策略按语义分化，适配精确；代价：两种执行模式的复杂度，注入顺序依赖 |
| openclaw | **28 个细粒度命名 Hook**：29 个命名生命周期 hook，覆盖完整链路，同 hook 多 handler 按 priority 降序执行 | 覆盖全面，拦截精确；代价：实现者负担重 |
| hermes-agent | **8 个粗粒度事件 + 目录扫描加载**：8 个生命周期事件，hook 通过目录扫描自动加载，错误隔离不阻塞主 pipeline | 简单易用；代价：拦截粒度粗 |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-extension-points.md:4. AgentHook → `agent/hook.py:29-103`; `agent/loop.py:180` |
| openclaw | [[openclaw/nodes/extension-points/openclaw-hook-system]] → `src/plugins/hook-types.ts:55-84,128-133` |
| hermes-agent | [[hermes-agent/nodes/extension-points/hermes-agent-event-hooks]] → `gateway/hooks.py:9-19,34-80` |

---

## E5. 声明式 Markdown 技能扩展：渐进式加载 vs 全文注入

**对齐种子库**：openclaw「如何在无代码情况下扩展 Agent 行为」
**定位类型**：**A 新位置**（种子库仅有 openclaw 1 个仓库，nanobot 首次带来第 2 个位置）

**标准化问题陈述**：如何让用户和开发者通过创建 Markdown 文件来扩展 agent 能力——哪些技能应该始终可用（全文注入），哪些应该按需加载（渐进式），如何声明工具的运行时依赖？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 零代码门槛——用户只需编辑文本文件即可定制 agent 行为 | openclaw |
| 扩展内容需注入到 agent 的 system prompt 以影响 LLM 行为 | openclaw |
| 与 plugin 系统互补不冲突——同一系统内两种扩展机制共存 | openclaw |
| 渐进式加载——always skills 全文注入 system prompt；其他技能仅以 XML 摘要形式出现，agent 需要时通过 read_file 工具按需读取 | nanobot |
| 上下文经济——所有技能全文注入会耗尽 context window，渐进式加载按需取用，节省 token | nanobot |
| 依赖自声明——frontmatter 中的 requires.bins 和 requires.env 声明工具依赖，不满足条件的技能自动标记为不可用 | nanobot |
| 用户覆盖——workspace/skills/ 中的用户自定义技能可以覆盖内建同名技能 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **Skills Markdown 渐进式加载**：always skills 全文注入 + 其他技能 XML 摘要 + 按需 read_file，依赖自声明，用户可覆盖内建技能 | Token 经济，按需取用，依赖自声明防止调用不可执行技能；代价：需要额外 read_file 轮次 |
| openclaw | **Markdown 技能文件作为第三层扩展**：用户在工作区放置 Markdown 技能文件，内容注入 agent system prompt，命令 spec 注册为可用命令 | 零代码，即时生效；代价：全部内容注入 system prompt，无渐进式加载 |
| hermes-agent | 基于 agentskills.io 代码标准，skill 是代码文件需要安装和扫描 | 互操作性好；代价：非零代码 |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-extension-points.md:5. Skills → `agent/skills.py:52-205` |
| openclaw | [[openclaw/nodes/extension-points/openclaw-skills-extension]] → `src/agents/skills.ts:8-39` |

---

## E6. 子 Agent 能力边界隔离

**对齐种子库**：部分相关 hermes「如何限制 agent 的单次任务计算预算」，但核心关注工具隔离
**定位类型**：**新轴**

**标准化问题陈述**：如何让主 agent 可以 spawn 子 agent 处理独立任务，同时防止子 agent 递归创建更多子 agent、发送消息给用户、或调度新任务——通过工具白名单还是仅通过预算限制？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 预算耗尽后处理——立即终止还是给一次 grace call | hermes-agent |
| 某些工具调用是否应退款（不计入预算） | hermes-agent |
| 工具白名单限制——子 agent 拥有独立的 ToolRegistry，不包含 message/spawn/cron 工具，从工具层面杜绝递归创建子 agent 的可能 | nanobot |
| 错误即终止——子 agent 的 tool error 为 fatal 级别，因为子 agent 没有用户交互通道来恢复 | nanobot |
| 资源限制——每个子 agent 拥有 15 轮 iteration budget，超限自动终止 | nanobot |
| 引擎复用——共享 AgentRunner 引擎获得所有上下文治理能力 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **子 agent 受限 ToolRegistry（无 message/spawn/cron）+ 共享执行引擎**：独立受限工具集 + 共享 AgentRunner + fatal error 模式 + 15 轮预算 | 工具层面杜绝权限逃逸，共享引擎复用上下文治理；代价：子 agent 功能受限 |
| hermes-agent | **线程安全迭代预算 + 不注入 LLM**：父 agent 90 轮、子 agent 50 轮独立预算，耗尽后一次 grace call，execute_code 可退款 | 预算管理精细，支持退款；代价：仅预算限制，无工具级隔离 |
| openclaw | 未将子 agent 作为显式设计选择 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-extension-points.md:6. Subagent → `agent/subagent.py:70-209` |
| hermes-agent | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `run_agent.py:170-199,815-821` |

> **种子库待收录**：hermes 有迭代预算但无工具白名单隔离。此轴线关注「能力边界隔离机制」，与 hermes 的「计算预算限制」可能是同一父轴的两个子维度。

---

## E7. MCP 外部工具集成

**对齐种子库**：hermes「如何集成外部工具服务（MCP 协议）」
**定位类型**：**A 新位置**（种子库仅有 hermes-agent 1 个仓库，nanobot 首次带来第 2 个位置）

**标准化问题陈述**：如何支持 MCP（Model Context Protocol）工具服务器的懒加载连接、工具动态注册和生命周期清理？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 外部工具的可用性不确定性——断连后是否需要自动重连 | hermes-agent |
| 双向通信——外部 MCP server 可能发起 LLM 采样请求 | hermes-agent |
| 凭据安全——外部 server 返回的错误消息可能泄露 API key | hermes-agent |
| 惰性连接——MCP server 通过 _connect_mcp() 在 AgentLoop 初始化时惰性连接，避免阻塞启动 | nanobot |
| 命名空间隔离——MCP 工具以 mcp_ 前缀动态注册到 ToolRegistry，与 builtins 工具命名空间不冲突 | nanobot |
| 生命周期管理——所有 MCP server 通过 AsyncExitStack 管理，AgentLoop 关闭时自动清理所有连接 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **MCP 惰性连接 + mcp_ 前缀命名空间 + AsyncExitStack 生命周期**：MCP server 懒加载连接，工具以 mcp_ 前缀注册，通过 AsyncExitStack 自动清理 | 惰性连接不阻塞启动，命名空间隔离清晰，自动清理无泄漏；代价：mcp_ 前缀限制工具命名 |
| hermes-agent | **MCP 协议集成**：通过 config.yaml 的 mcp_servers 配置自动发现和注入，支持 Stdio（指数退避自动重连）和 HTTP/StreamableHTTP，支持 MCP Sampling，错误消息凭据自动脱敏 | 协议覆盖完整，自动重连，凭据安全；代价：配置驱动，启动时连接 |
| openclaw | 未将 MCP 集成作为显式设计选择 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-extension-points.md:7. MCP → `agent/loop.py:256-276`; `agent/tools/mcp.py` |
| hermes-agent | [[hermes-agent/dimensions/hermes-agent-extension-points]] → `tools/mcp_tool.py:15-43` |

---

## E8. Channel 适配器粒度：队列解耦 vs 接口分解

**对齐种子库**：部分相关「消息平台适配：接口分解粒度」（concept/im-platform-adapter-granularity），但关注通信机制而非接口粒度
**定位类型**：此条已作为 A3（Architecture 维度）覆盖——Channel 与 Agent 核心的解耦机制。在 Extension Points 维度中，nanobot 的 Channel 插件发现（E2）和 MCP 工具集成（E7）已分别覆盖相关扩展点。

> E8 跳过——nanobot 的 Channel 架构选择已在 Architecture A3 中覆盖。

---

## Dependency Strategy 维度（4 条）

---

## D1. LLM API SDK 依赖：多原生 SDK vs 单 SDK 统一路由

**对齐种子库**：hermes「如何选择核心 API SDK 的架构锁定」
**定位类型**：**A 新位置**（种子库仅有 hermes-agent 1 个仓库，nanobot 首次带来第 2 个位置，且为相反立场）

**标准化问题陈述**：如何在支持 20+ LLM provider 的前提下，决定核心 API SDK 的依赖策略——是使用单一 SDK 统一路由（架构锁定但代码简单），还是使用多个原生 SDK 直接调用（行为可控但维护成本高）？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 单 SDK 路由简化代码但形成架构锁定——如果 OpenAI SDK 出现破坏性变更或不再满足需求，替换成本极高 | hermes-agent |
| 多 SDK 策略分散维护但降低锁定风险——每个 provider 的原生 SDK 各有特点 | hermes-agent |
| OpenAI-compatible 协议的生态覆盖足够广，但 Anthropic 原生 API 需要单独 SDK | hermes-agent |
| 行为可控性——移除 litellm 后用原生 openai + anthropic SDK 直接调用，适配层复杂性从第三方库转移到自有代码（3719 行 providers/），但完全掌控行为 | nanobot |
| 零间接供应商依赖——所有 LLM API 调用都经过自有代码，不依赖任何中间转发层的正确性 | nanobot |
| 维护成本转移——放弃 litellm 开箱即用的 30+ provider 支持，需自己维护每个 provider 的 API 兼容细节 | nanobot |
| 版本风险隔离——不再受 litellm 版本升级节奏的影响，各 SDK 版本独立管理 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **移除 litellm，使用原生 openai + anthropic SDK**：替换 LLM 转发层为原生 SDK 直接调用，适配逻辑内化到自有 providers/ 代码中 | 行为完全可控，零间接供应商依赖，版本风险隔离；代价：维护 3719 行自有适配代码 |
| hermes-agent | **OpenAI SDK 统一路由**：20+ provider 都通过 openai SDK 路由（OpenAI-compatible 协议），Anthropic 额外使用原生 SDK 但可通过 api_mode 切换 | 代码简洁，单 SDK 维护成本低；代价：架构锁定 OpenAI SDK，替换成本高 |
| openclaw | 深度绑定 @mariozechner 私有包族 | 快速复用经过验证的引擎；代价：几乎无法切换引擎 |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-dependency-strategy.md:1. 替换 litellm → `README.md:21`; `providers/registry.py` 整体 |
| hermes-agent | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:15-37` |

---

## D2. 可选依赖安装分层：pip extras 按平台分组

**对齐种子库**：「可选依赖分层：统一降级还是按安装成本分层？」（concept/optional-dependency-layering）
**定位类型**：**B 已有位置**（种子库已有 openclaw + hermes-agent 两个位置，nanobot 增加第三个）

**标准化问题陈述**：如何让用户只安装所需 IM 平台的 SDK，而不是强制安装所有 14+ 平台的依赖——是通过 pip extras、peer dependencies、还是 ImportError 降级？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 默认安装不应拉入 GB 级二进制或复杂原生模块 | openclaw |
| ImportError 检查点需要遍布所有使用可选依赖的代码路径 | hermes-agent |
| 降级行为需要明确告知用户 | hermes-agent |
| 安装体积最小化——IM 平台 SDK 标记为 pip extras 可选依赖，核心运行时只有 ~20 个包 | nanobot |
| 用户体验成本——用户需要知道自己用哪些平台然后选择性安装，不像全量安装那样零配置 | nanobot |
| 版本约束集中——平台 SDK 的版本锁定在 pyproject.toml 主依赖中而非可选组中 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **pip extras 可选依赖分组：按平台按需安装**：IM 平台 SDK 标记为 pip extras，用户按需选择，核心安装只有 ~20 个包 | 核心极轻，按需安装；代价：用户需知道要装什么 |
| openclaw | **Peer + Optional 依赖分层**：Peer dependencies 用户显式安装，Optional dependencies 缺失时自动降级 | 默认轻量，分层清晰；代价：GB 级 peer dep 用户需手动安装 |
| hermes-agent | **ImportError -> 降级/跳过 + 20+ extras 分组**：所有可选依赖遵循 ImportError 捕获后优雅降级，pyproject.toml 通过 20+ extras 拆分 | 绝不因缺少可选包启动失败；代价：ImportError 检查点遍布 |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-dependency-strategy.md:2. 可选依赖 → `pyproject.toml:20-78` |
| openclaw | [[openclaw/dimensions/openclaw-dependency-strategy]] → `package.json: peerDependencies, optionalDependencies` |
| hermes-agent | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:39-115` |

---

## D3. Channel SDK 依赖隔离：零交叉 import vs 独立 Package 声明

**对齐种子库**：openclaw「如何隔离 Channel SDK 故障域」
**定位类型**：**A 新位置**（种子库仅有 openclaw 1 个仓库，nanobot 首次带来第 2 个位置）

**标准化问题陈述**：不同的 IM 平台 SDK 之间存在潜在的版本冲突和命名空间污染——如何确保一个 Channel 的 SDK 不会影响其他 Channel？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 单个 channel SDK 的故障不能影响核心运行时 | openclaw |
| 用户只需安装自己使用的 channel | openclaw |
| 跨 channel 共享的 plugin 基础设施需要一致接口 | openclaw |
| 零交叉依赖——每个内置 Channel 是独立的 Python 模块，只 import 自己需要的 SDK，Channel 之间无相互依赖 | nanobot |
| 版本统一约束——平台 SDK 的版本锁定在 pyproject.toml 主依赖中，不在可选组中分别锁定 | nanobot |
| 添加新 Channel 安全——新增 Channel 只增加自己的模块文件和依赖声明，不可能打破已有 Channel 的依赖隔离 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **Channel 模块独立：零交叉 import**：每个 Channel 模块只 import 自己的 SDK，Channel 之间无相互依赖（单体仓库内模块隔离） | 隔离简单有效，新增 Channel 安全；代价：版本锁定在主依赖中，全局统一 |
| openclaw | **Channel SDK 独立声明 + 故障域隔离**：每个 channel extension 在自身 package.json 中独立声明 SDK 依赖，不在 root package 聚合（monorepo 独立包隔离） | 故障域完全隔离，独立版本管理；代价：跨包协调复杂度高 |
| hermes-agent | 单体仓库，所有依赖在同一个 pyproject.toml 中通过 extras 分组声明 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-dependency-strategy.md:3. Channel 依赖隔离 → `channels/` 目录结构; `pyproject.toml:35-42` |
| openclaw | [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] → `extensions/slack/package.json:1-15` |

---

## D4. 跨语言生态桥接

**对齐种子库**：无匹配
**定位类型**：**新轴**

**标准化问题陈述**：当 Python 生态中不存在某些所需能力而这些能力在 Node.js 生态中可用时，如何以最小代价获取这些能力？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 进程隔离——TypeScript bridge 通过 HTTP 与 Python 核心通信，不共享进程空间，bridge 崩溃不影响 Python 主进程 | nanobot |
| 主语言纯净——Python 核心不需要引入 Node.js 运行时作为依赖，bridge 是可选的独立组件 | nanobot |
| 额外成本——跨语言桥接引入了额外的网络通信延迟和部署复杂度（需要同时管理 Python 和 Node.js 两个运行时） | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **独立进程 TypeScript HTTP bridge**：bridge/ 目录独立 Node.js/TypeScript 模块，通过 HTTP 通信，不共享进程空间 | 进程隔离安全，主语言纯净；代价：额外网络延迟，双运行时部署复杂度 |
| openclaw | 本身是 Node.js/TypeScript 项目，不面对跨语言桥接 | — |
| hermes-agent | Python 单体项目，不面对跨语言桥接 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-dependency-strategy.md:4. Bridge → `bridge/src/index.ts` |

---

## Testing Philosophy 维度（2 条）

---

## T1. 测试资源分配策略：风险驱动 vs 行为驱动

**对齐种子库**：部分相关 hermes「如何选择测试的抽象层级」，但关注资源分配而非测试层级
**定位类型**：**新轴**

**标准化问题陈述**：测试资源有限（虽然 26,048 行测试代码是核心运行时的 5.7 倍），如何决定哪些模块值得最密集的测试覆盖——是按风险优先级分配、按模块均衡覆盖、还是按行为接口测试？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 测试行为接口——重构时测试不需要改动但对复杂内部逻辑的覆盖不足 | hermes-agent |
| 安全优先——SSRF 防护、exec 沙箱、workspace 隔离是 agent 框架最不可出错的方面，安全测试的投入远超其他模块 | nanobot |
| 跨平台一致性——Windows/macOS/Linux 的 exec 行为差异在跨平台测试矩阵中覆盖 | nanobot |
| 覆盖率不均衡——安全测试比重最大，意味着其他功能域的测试覆盖相对薄弱 | nanobot |
| 集成优于单元——测试集中在集成和关键路径，而非每个内部函数的单元测试 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **风险驱动测试分配：安全 + 跨平台 + Channel 交互优先**：测试投入集中在安全边界、跨平台兼容和 Channel 交互，覆盖率不追求模块间均衡 | 安全领域覆盖率极高，关键路径有保障；代价：其他功能域测试薄弱 |
| hermes-agent | **行为驱动测试**：测试公共 API 表面，对错误路径和边界值有专门测试，不测试私有实现细节 | 重构友好，测试不因内部改动失效；代价：复杂内部逻辑覆盖不足 |
| openclaw | 架构边界 CI lint + 性能预算 CI 门控 | — |

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-testing-philosophy.md:1. 测试覆盖重点 → `tests/` 目录; `test_exec_security.py`; `test_sandbox.py` |

> **种子库待收录**：hermes 和 openclaw 均未将「测试资源分配策略」作为显式设计选择。此轴线关注的是分配优先级（而非测试层级或 CI 机制），与 hermes 的「测试抽象层级」属测试策略的不同维度。

---

## T2. 安全防护边界：基础设施隔离 vs 审批门控

**对齐种子库**：「工具执行安全门控：统一管道还是分层可调节？」（concept/tool-security-gating）
**定位类型**：**C 已有轴首次出现分歧**

**标准化问题陈述**：agent 框架中安全漏洞的后果远大于功能 bug，如何在架构层面定义并测试安全边界——是通过审批/门控机制（在执行前拦截危险操作），还是通过基础设施级隔离（在操作系统/网络/文件系统层面限制破坏能力）？

**综合核心关切**：

| 关切 | 来源 |
|------|------|
| 不同部署场景的安全需求差异巨大 | openclaw |
| 安全门控延迟不应影响正常的消息处理吞吐 | openclaw |
| 高风险工具需要额外用户确认回路 | openclaw / hermes-agent |
| 审批状态的持久化粒度影响安全性和便利性的平衡 | hermes-agent |
| **多层防护**——SSRF 防护（10 个 CIDR 私有网络块拦截）+ exec 沙箱（隔离 workspace）+ workspace 隔离（限制文件系统访问范围），三层独立互不依赖 | nanobot |
| **可配置白名单**——支持通过 configure_ssrf_whitelist() 自定义白名单，平衡安全性和灵活性 | nanobot |
| **测试隔离**——安全测试使用 pytest tmp_path fixture 和临时 workspace 目录 | nanobot |

**三仓库权衡位置表**：

| 仓库 | 选择 | 权衡 |
|------|------|------|
| nanobot | **三层安全防护：SSRF CIDR 拦截 + exec 沙箱 + workspace 隔离**：网络出口、命令执行、文件系统三个维度独立防护，支持白名单配置 | 基础设施级隔离，不依赖审批决策的准确性，防护纵深；代价：无法针对具体操作做精细控制 |
| openclaw | **同步串行 Pipeline**：5 层 allowlist/denylist 过滤，exec 类额外阻塞等待 owner 审批 | 逐操作精细控制；代价：审批延迟影响吞吐 |
| hermes-agent | **三层渐进式审批**：Layer 0 快速路径 + Layer 1 Smart（辅助 LLM 评估）+ Layer 2 Manual（tirith + 25+ 危险模式正则），三级持久化 | 按风险分级审批，灵活性高；代价：审批系统复杂度高 |

**轴线重新解释**：nanobot 从不同于 openclaw/hermes-agent 的维度切入安全问题——前者关注「基础设施级隔离」（在操作系统层面限制破坏能力），后者关注「操作审批门控」（在执行前判断是否允许）。这是同一安全轴线的两个互补维度，而非对立选择。未来 Concept 页需扩展以容纳这两种安全哲学。

**溯源表**：

| 仓库 | 溯源 |
|------|------|
| nanobot | nanobot-testing-philosophy.md:1. 测试覆盖重点 → `security/network.py`; `test_exec_security.py`; `test_sandbox.py` |
| openclaw | [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]] → `src/agents/tool-policy-pipeline.ts:56-90` |
| hermes-agent | [[hermes-agent/nodes/design-decisions/hermes-agent-layered-approval-decision]] → `tools/approval.py:586-922` |

---

## 反向检查：种子库「待观察」条目 × nanobot

以下逐一检查种子库中标记为「仅 X—待观察」的 32 条条目，确认 nanobot 是否面对同一问题。

### openclaw 待观察条目（11 条）

| # | 种子条目 | nanobot 是否面对 | 补充 |
|---|---------|-----------------|------|
| 1 | 如何在消息驱动的 AI 助手中创建主动触发路径 | **是** | 已纳入 A4（入站路径）+ A8（调度机制），nanobot 选择统一 bus 注入而非独立 session |
| 2 | 如何选择 LLM Provider 的实现 | **部分** | E3（Provider 注册表）和 D1（SDK 依赖）分别从不同角度触及，但 nanobot 的核心问题是「数据驱动注册」而非「运行时选择」 |
| 3 | 如何在无代码情况下扩展 Agent 行为 | **是** | 已纳入 E5（Markdown 技能渐进式加载），nanobot 增加依赖自声明和用户覆盖能力 |
| 4 | 如何提供 Plugin SDK 的双入口模式 | 否 | nanobot 没有统一的 plugin SDK，扩展通过 entry_points + pkgutil 实现 |
| 5 | 如何保证 Plugin 接口稳定性 | 否 | nanobot 没有统一的 plugin 系统 |
| 6 | 如何优化冷启动速度 | 否 | nanobot 未将冷启动优化作为显式设计选择 |
| 7 | 如何管理消息入站的突发流 | 否 | nanobot 使用 asyncio.Queue 天然缓冲，但未将防抖作为显式设计选择 |
| 8 | 如何选择 AI 引擎依赖策略 | 否 | nanobot 是自建引擎（类似 hermes），不面对「自建 vs 绑定外部引擎」的决策 |
| 9 | 如何隔离 Channel SDK 故障域 | **是** | 已纳入 D3（Channel 模块独立），nanobot 使用零交叉 import 而非独立 package |
| 10 | 如何将架构边界约束从文档变为可执行检查 | 否 | nanobot 无架构边界 CI lint |
| 11 | 如何将性能预算纳入 CI 门控 | 否 | nanobot 无性能预算 CI 检查 |

### hermes-agent 待观察条目（21 条）

| # | 种子条目 | nanobot 是否面对 | 补充 |
|---|---------|-----------------|------|
| 1 | 如何编排多轮 agent 对话的单一切入点 | **部分** | 已纳入 A1（子系统集中组装），但核心问题不同：hermes 关注多入口路由，nanobot 关注构造函数 DI 组装 |
| 2 | 如何在系统 prompt 中内建自学习驱动 | **部分** | 已纳入 A5（系统 Prompt 组装），nanobot 采用纯数据拼接，hermes 嵌入自学习指令——在「Prompt 组装方式」轴的不同位置 |
| 3 | 如何管理外部 skill 的安全信任 | 否 | nanobot 有用户 skill 覆盖机制（workspace/skills/ 覆盖内建），但无安全扫描 |
| 4 | 如何分离关注点防止单层膨胀 | 否 | nanobot 有自然分层（AgentLoop/Runner/ContextBuilder/Bus）但未形式化 |
| 5 | 如何管理日志的安全性和可追溯性 | 否 | nanobot 未将日志脱敏作为显式设计选择 |
| 6 | 如何管理后台进程的生命周期 | 否 | nanobot 无 terminal 后台进程管理 |
| 7 | 如何发现和注册工具（AST 扫描） | **是** | 已纳入 E1（工具注册与发现），nanobot 选择相反的显式注册路径 |
| 8 | 如何组织工具为可组合的能力组 | 否 | nanobot 有 MCP vs builtins 区分但无 toolset 分组机制 |
| 9 | 如何集成外部工具服务（MCP 协议） | **是** | 已纳入 E7（MCP 集成），nanobot 使用惰性连接 + 命名空间隔离 |
| 10 | 如何管理可安装技能的互操作性 | 否 | nanobot 使用自有 Skills Markdown 格式，不基于 agentskills.io |
| 11 | 如何分类管理工具的并行执行 | 否 | nanobot 未将工具并行执行作为显式设计选择 |
| 12 | 如何为不同复杂度查询路由模型 | 否 | nanobot 无模型路由机制 |
| 13 | 如何管理 API 多凭证的速率限制 | 否 | nanobot 的重试策略（P4）处理速率限制，但无多凭证轮换 |
| 14 | 如何限制 agent 的单次任务计算预算 | **是** | 已纳入 E6（子 agent 能力边界），nanobot 子 agent 15 轮 budget vs hermes 子 agent 50 轮 |
| 15 | 如何为特定场景精简 agent 的工具面 | **部分** | E6 中 nanobot 子 agent 的受限 ToolRegistry 实质上是场景化工具精简 |
| 16 | 如何缓存模型元数据加速启动 | 否 | nanobot 未将模型元数据缓存作为显式设计选择 |
| 17 | 如何隔离测试环境以确保零残留 | 否 | nanobot 使用 pytest tmp_path 但未显式文档化隔离策略 |
| 18 | 如何选择测试的抽象层级 | **部分** | T1（测试资源分配）触及测试策略但侧重资源分配而非抽象层级 |
| 19 | 如何在 CI 中防范供给链攻击 | 否 | nanobot 无供给链审计 workflow |
| 20 | 如何在运行时选择多种后端实现 | **部分** | E3（Provider 注册表）实现了数据驱动多 provider 选择 |
| 21 | 如何选择核心 API SDK 的架构锁定 | **是** | 已纳入 D1（SDK 依赖策略），nanobot 选择多原生 SDK vs hermes 单 SDK 统一路由 |

---

## 综合统计

### 轴定位分布

| 定位类型 | 数量 | nanobot 条目 |
|---------|------|-------------|
| A 新位置（种子 1 仓 -> 2 仓） | 8 | A4（入站路径）、E1（工具注册）、E5（Markdown 技能）、E7（MCP 集成）、D1（SDK 依赖）、D3（Channel 隔离）、T2（安全边界，与 seed 不同角度但同轴）、A8（调度机制） |
| B 已有位置（种子 2+ 仓 -> 3+ 仓） | 5 | P1（上下文治理）、P2（Prompt Cache）、E4（生命周期 Hook）、D2（可选依赖分层）、A8+P1 综合 |
| C 已有轴首次出现分歧 | 3 | P1（透明治理重塑压缩轴）、T2（基础设施隔离重塑安全轴）、E1 的反向立场也可视作分歧 |
| 新轴 | 9 | A1（集中组装-Hub）、A2（执行引擎分离）、A3（Channel 解耦机制）、A5（Prompt 组装方式）、A6（记忆存储后端）、A7（会话持久化）、P3（非阻塞记忆压缩）、P4（LLM 错误重试）、E3（Provider 注册表）、E6（子 agent 隔离）、D4（跨语言桥接）、T1（测试资源分配） |

### 反向检查统计

| 种子库来源 | 待观察条目 | nanobot 面对 | 占比 |
|-----------|-----------|-------------|------|
| openclaw | 11 | 3（确定）+ 1（部分） | 27%-36% |
| hermes-agent | 21 | 5（确定）+ 5（部分） | 24%-48% |
| **合计** | **32** | **8（确定）+ 6（部分）** | **25%-44%** |

### 种子库轴线升级建议

nanobot 的加入使以下轴线从「单仓库待观察」升级为「双仓库可升级 Concept」：

1. **工具发现机制**（E1）：hermes AST 扫描 vs nanobot 显式注册 —— 轴线成熟度达标
2. **非消息事件入站路径**（A4）：openclaw 独立 session vs nanobot 统一注入 —— 轴线成熟度达标
3. **声明式 Markdown 技能扩展**（E5）：openclaw 第三层扩展 vs nanobot 渐进式加载 —— 轴线成熟度达标
4. **MCP 工具集成**（E7）：hermes config 驱动 vs nanobot 惰性连接 —— 轴线成熟度达标
5. **LLM API SDK 依赖策略**（D1）：hermes 单 SDK 统一路由 vs nanobot 多原生 SDK —— 轴线成熟度达标
6. **Channel SDK 依赖隔离**（D3）：openclaw monorepo 独立包 vs nanobot 单体零交叉 import —— 轴线成熟度达标
7. **安全防护哲学**（T2）：审批门控（openclaw/hermes）vs 基础设施隔离（nanobot）—— 轴线上已有三个仓库，但 nanobot 带来的是轴线重新解释而非简单增加位置
8. **上下文治理透明度**（P1）：LLM 感知 vs LLM 透明 —— 三个仓库各有不同治理策略，nanobot 引入透明预处理维度

---

## 附录：nanobot 25 条设计选择完整索引

| # | 简称 | 维度 | 轴定位 | 类型 |
|---|------|------|--------|------|
| 1 | 子系统集中组装 | Architecture | A1 | 新轴 |
| 2 | 执行引擎产品层分离 | Architecture | A2 | 新轴 |
| 3 | 四步透明上下文治理 | Performance | P1 | C 分歧 |
| 4 | MessageBus 队列解耦 | Architecture | A3 | 新轴 |
| 5 | 统一 bus 注入 | Architecture | A4 | A 新位置 |
| 6 | ContextBuilder 六层拼接 | Architecture | A5 | 新轴 |
| 7 | 显式工具注册 | Extension | E1 | A 新位置 |
| 8 | 工具排序稳定缓存 | Performance | P2 | B 已有位置 |
| 9 | Channel 插件双层发现 | Extension | E2 | 新轴 |
| 10 | 数据驱动 Provider 注册 | Extension | E3 | 新轴 |
| 11 | CompositeHook 组合策略分化 | Extension | E4 | B 已有位置 |
| 12 | Skills Markdown 渐进式加载 | Extension | E5 | A 新位置 |
| 13 | 子 agent 受限 ToolRegistry | Extension | E6 | 新轴 |
| 14 | MCP 惰性连接 + 命名空间 | Extension | E7 | A 新位置 |
| 15 | 纯文件 I/O 三层记忆栈 | Architecture | A6 | 新轴 |
| 16 | Consolidator 异步非阻塞 | Performance | P3 | 新轴 |
| 17 | 三级 LLM 错误重试 | Performance | P4 | 新轴 |
| 18 | JSONL 会话持久化 | Architecture | A7 | 新轴 |
| 19 | 移除 litellm 原生 SDK | Dependency | D1 | A 新位置 |
| 20 | pip extras 按平台安装 | Dependency | D2 | B 已有位置 |
| 21 | Channel 模块零交叉 import | Dependency | D3 | A 新位置 |
| 22 | TypeScript HTTP bridge | Dependency | D4 | 新轴 |
| 23 | Cron 三模式 + Heartbeat | Architecture | A8 | B 已有位置 |
| 24 | 风险驱动测试分配 | Testing | T1 | 新轴 |
| 25 | 三层安全防护 | Testing | T2 | C 分歧 |
