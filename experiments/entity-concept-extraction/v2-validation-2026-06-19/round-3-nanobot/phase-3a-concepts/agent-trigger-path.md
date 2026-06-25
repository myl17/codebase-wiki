---
concept: agent-trigger-path
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - nanobot
  - hermes-agent
---

# 非用户消息事件如何进入 Agent 处理流程——独立触发路径还是统一消息注入？

## 标准化问题陈述

子 agent 完成结果、Cron 定时触发、Heartbeat 唤醒消息等非用户 IM 消息事件，如何进入主 agent 的处理流程——应该走独立的隔离 session 路径还是复用现有入站消息队列统一注入？这两条路径代表了两种架构哲学：独立路径隔离了主动触发的副作用但不保证处理逻辑一致，统一注入保证了所有来源走同一套处理管线但埋没了消息的语义区分。

## 核心关切

1. **处理统一性**——所有来源走同一消费路径，无需维护多条处理管线。新增事件源无需额外的基础设施投入，保证处理逻辑的单一真相来源
2. **语义区分**——不同来源的消息在统一队列中无区别，无法做差异化路由、优先级或工具集裁剪。子 agent 返回结果和 IM 用户消息在系统中完全等同，失去了「这条消息从哪来」的元信息
3. **Session 隔离**——主动触发（Cron、Heartbeat）不应污染用户对话 session。如果 Cron 任务在用户的 session 上下文中执行，会产生意外的消息副作用（即使用户没在对话也会看到 agent 的响应）
4. **架构简化**——单一路径降低维护成本，多路径增加灵活性但提升复杂度。每增加一条独立路径都意味着新的调度器、新的生命周期管理、新的错误处理边界

## 实例矩阵

| 仓库 | 路径选择 | 机制 | 核心权衡 |
|------|---------|------|--------|
| openclaw | Cron 独立主动触发路径 | 创建 isolated-agent session，CronDeliveryPlan 决定结果投递目标 | Session 隔离 + 语义区分 > 架构复杂度 |
| nanobot | 混合路径：子 agent 走 bus + Cron/Heartbeat 直通 `process_direct()` | 子 agent 通过 `bus.publish_inbound()` 注入队列走完整消费路径；Cron/Heartbeat 通过 `process_direct()` 绕过队列和 `_dispatch()`，直通 `_process_message()` | 子 agent 走统一路径保证处理一致性；Cron/Heartbeat 直通避免队列排队延迟 |
| hermes-agent | Cron 作为同一编排循环的入口 | Cron 调度器直接调用 `AIAgent.run_conversation()`，不面对路径选择问题 | 自然统一（单体架构下 Cron 天然是 AIAgent 的另一个调用方，不存在独立的路径分歧） |

## openclaw — Cron 独立主动触发路径

### 机制概述

openclaw 的数据流分为两条互不交叉的路径（`openclaw-architecture.md` 第 64-78 行）：

```
用户消息路径：
  IM 平台 → Channel Plugin → Tool Policy Pipeline → Session Binding
  → Context Engine → Agent Harness → Channel Plugin → IM 平台

并行触发路径（无消息驱动）：
  Cron Scheduler → isolated-agent → Agent Harness
```

`src/cron/delivery-plan.ts:10-19` 定义了 `CronDeliveryPlan` 投递计划的数据类型——Cron 触发后，不经过 Channel Plugin 和 Session Binding。实际创建 isolated-agent session 的逻辑位于 `src/cron/isolated-agent/session.ts:12-89` 的 `resolveCronSession()` 和 `src/cron/isolated-agent/run-executor.ts`。需注意 Cron 支持四种 `sessionTarget`：`"main" | "isolated" | "current" | session:*`，并非所有 cron 任务都使用完全隔离的 session——`"current"` 和 `"session:*"` 会复用已有 session。Cron 是唯一一个可以在无 IM 消息触发的情况下主动发起 agent 运行的入口。

### CronDeliveryPlan 决定结果投递目标

Cron 任务完成后，`CronDeliveryPlan` 决定结果投递到哪个 channel、哪个 thread、是否通过 announce 通知、或走 webhook 回调。这意味着 Cron 的执行上下文和结果投递是解耦的——执行发生在隔离 session，结果按需投递到指定的通信目标。

`src/tasks/task-executor.ts:85-217` 的 TaskFlow 独立状态转换函数负责 Cron 触发的任务生命周期管理：`createQueuedTaskRun`(85) → `startTaskRunByRunId`(150) → `completeTaskRunByRunId`(173) / `failTaskRunByRunId`(196)，状态持久化到 SQLite。TaskFlow 支持 flow 内多 task 级联(488-580)、cancel 传播(632-712)、block retry(265-374)、owner 访问控制(582-630)——这构成了独立触发路径的完整生命周期保障。

### Session 隔离的核心价值

isolated-agent session 意味着：
- Cron 执行过程中产生的消息不会出现在任何用户的对话历史中
- Cron 的 tool calls、中间结果、错误重试都在隔离沙箱中进行
- 只有最终结果（通过 `CronDeliveryPlan` 指定）才会投递到目标 channel

这个设计的选择是：**宁可维护两条独立的处理路径（IM 消息路径 + Cron 触发路径），也不让 Cron 的内部执行细节泄漏到用户对话中**。代价是两条路径的处理逻辑可能存在不一致——IM 路径的 Tool Policy Pipeline、Context Engine 组装、Hook 注入等逻辑在 Cron 路径上是否完全等价，需要额外的契约保证。

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| Session 隔离（Cron 执行在 isolated-agent session 中，不污染任何用户对话；中间状态和错误重试不在用户可见范围内） | 架构复杂度（维护两条独立路径——IM 消息路径和 Cron 触发路径——每条有自己的调度器、生命周期管理、错误处理边界） |
| 语义区分（Cron 触发可识别为特殊消息类型——通过 isolated-agent 标记可做差异化路由、工具集裁剪、优先级控制） | 处理不一致风险（IM 路径的 Tool Policy Pipeline、Context Engine 组装、Hook 注入等逻辑在 Cron 路径上可能需要不同的配置，两条路径的处理逻辑可能产生分歧） |

## nanobot — 混合路径：子 agent 走 bus 队列 + Cron/Heartbeat 直通 `process_direct()`

### 机制概述

nanobot 的 `MessageBus` 用 `asyncio.Queue` 将 Channel 层与 Agent 核心解耦（`bus/queue.py:8-35`）。但并非所有非用户消息都走 bus 队列——实际情况是**混合路径**：

- **子 agent**：完成后通过 `bus.publish_inbound()` 注入入站队列，经 `_dispatch()` 走完整消费路径
- **Cron 和 Heartbeat**：通过 `agent.process_direct()`（`agent/loop.py:734-750`）直接调用 `_process_message()`，**绕过** `bus.inbound` 队列和 `_dispatch()`（包括其 session-lock、CommandRouter、concurrency gate）

`process_direct()` 创建 `InboundMessage` 后直通核心处理逻辑，不与 `AgentLoop.run()` 的队列消费循环交互。数据流：

```
IM 消息路径：
  IM 平台 → Channel (BaseChannel) → MessageBus.inbound
  → AgentLoop.run() → consume_inbound() → _dispatch() → _process_message()

子 agent 结果注入路径：
  SubagentManager.spawn() → AgentRunner.run() → 完成后
  → bus.publish_inbound() → 复用主 agent 的消费路径

Cron 触发路径（绕过 bus.inbound 队列）：
  CronService._execute_job(service.py:313-314) → on_cron_job 回调(cli/commands.py:689-742)
  → agent.process_direct()(commands.py:715) → _process_message()(loop.py:481)

Heartbeat 唤醒路径（绕过 bus.inbound 队列）：
  HeartbeatService._tick(service.py:145-177) → on_execute 回调(cli/commands.py:766-787)
  → agent.process_direct()(commands.py:773) → _process_message()(loop.py:481)
```

### 子 agent 结果统一注入

`agent/subagent.py:202-209` 是子 agent 结果注入的关键位置——子 agent 完成后，结果通过 `bus.publish_inbound(msg)` 注入入站队列。子 agent 消息使用 `channel="system"` 和 `sender_id="subagent"`，在 `_process_message()` 中（`loop.py:491-502`）触发专门处理分支：检查 `msg.channel == "system"`、根据 `sender_id == "subagent"` 设置 `current_role = "assistant"`（而非默认的 `"user"`）。因此在处理层面系统能识别子 agent 消息并设置正确的角色，但在优先级和路由层面不做区分——主 agent 在消费队列时无法为子 agent 消息做差异化路由。

子 agent 共享 `AgentRunner` 引擎但拥有独立的受限 `ToolRegistry`（`agent/subagent.py:114-132`）：文件工具 + 可选的 exec/web 工具，**不包含** message/spawn/cron 工具——防止递归创建子 agent。15 轮 iteration budget，tool error 为 fatal 级别立即终止。

### 混合路径的本质

nanobot 的实际架构并非所有来源统一注入 bus 队列，而是**混合路径**——`_process_message()` 是所有消息的汇聚点，但注入方式因来源而异：

1. **核心处理逻辑统一**——所有来源（IM、子 agent、Cron、Heartbeat）最终都在 `_process_message()` → `_run_agent_loop()` 汇合，共享同一套 ContextBuilder 和 AgentRunner。处理逻辑的一致性是真实的。
2. **注入路径分叉**——子 agent 走 bus 队列 + `_dispatch()` 完整路径（含 session-lock、CommandRouter、concurrency gate）；Cron 和 Heartbeat 走 `process_direct()` 捷径（绕过队列和 `_dispatch()`，直通 `_process_message()`）。
3. **独立 session 但共享处理管线**——Cron 和 Heartbeat 通过 `process_direct()` 传入自定义 `session_key`（如 `"cron:{job.id}"`、`"heartbeat"`），拥有独立 session 上下文但复用同一处理管线。调度器本身（CronService/HeartbeatService）也是独立的，但管理开销低于 openclaw 的完整 isolated-agent 生命周期。

代价是内部复杂度：两条注入路径（bus 队列路径 vs `process_direct()` 直通路径）的预处理逻辑不共享——`_dispatch()` 中的 session-lock、CommandRouter、concurrency gate 对 Cron/Heartbeat 不生效。这意味着这两类来源的消息不经过并发控制、不需要通过路由鉴权、不参与 session 锁竞争。此外子 agent 消息虽有 `channel="system"` 和 `sender_id="subagent"` 的基础语义标记（在 `_process_message()` 中触发专门处理分支，设置 `current_role="assistant"`），但 Cron/Heartbeat 消息的 `sender_id` 固定为 `"user"`，来源元信息在进入核心处理管线前即消失。

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 核心处理逻辑统一（所有来源在 `_process_message()` → `_run_agent_loop()` 汇合，ContextBuilder 和 AgentRunner 对所有来源共享——不存在核心处理逻辑分歧的风险） | 预处理路径不统一（子 agent 走 `bus.inbound → _dispatch()` 含 session-lock + CommandRouter + concurrency gate；Cron/Heartbeat 走 `process_direct()` 绕过这些预处理——两条路径的预处理能力不等价） |
| 语义基础标记保留（子 agent 消息通过 `channel="system"` 和 `sender_id="subagent"` 在 `_process_message()` 中触发专门分支；Cron/Heartbeat 通过独立 `session_key` 拥有 session 隔离） | 来源元信息丢失（Cron/Heartbeat 的 `sender_id` 固定为 `"user"`，与 IM 消息混同；无法在优先级或路由层面做差异化处理） |

## hermes-agent — Cron 作为同一编排循环的自然入口

### 机制概述

hermes-agent 的 Cron 调度器实际执行逻辑位于 `cron/scheduler.py:580-883` 的 `run_job()` 函数——它直接 `from run_agent import AIAgent`（587 行）、实例化 `AIAgent(...)`（736 行）、调用 `agent.run_conversation(prompt)`（778 行），不经过 Gateway 的消息路由层。Cron 位于基础设施层，直接调用编排层的 AIAgent——与 CLI TUI 和 Gateway 平台适配器并列，都是 `AIAgent` 的调用方。但需注意 Cron 创建的 AIAgent 实例使用了裁剪配置：`disabled_toolsets=["cronjob", "messaging", "clarify"]`, `quiet_mode=True`, `skip_context_files=True`, `skip_memory=True`——并非与 CLI/Gateway 使用完全相同的 AIAgent 配置。

hermes-agent 不面对「独立路径 vs 统一注入」的选择问题，因为其单体架构下 Cron 天然是 AIAgent 的另一个调用方（位于基础设施层，直接调用编排层）：CLI、Gateway、Cron 三个入口直接调用同一个 `AIAgent.run_conversation()`，不存在需要统合的分散路径。数据流方向是单向的——基础设施层（Cron）→ 编排层 → 安全层 → 工具层——Cron 只是在这个方向上多了一个调用方，不需要额外的路径架构决策。

### 与 openclaw/nanobot 的本质区别

| 维度 | hermes-agent | openclaw | nanobot |
|------|-------------|----------|---------|
| Cron 的架构位置 | 基础设施层中直接调用编排层的定时入口（与 CLI、Gateway 并列作为 AIAgent 的调用方） | 独立的并行触发路径（与 IM 消息路径分离） | 混合路径：子 agent 走 bus 队列（与 Channel 并列作为 bus 生产者）；Cron/Heartbeat 走 `process_direct()` 直通（绕过 bus 队列） |
| 是否需要路径选择 | 否——单体架构下所有入口天然统一 | 是——两条路径需要显式的架构决策 | 是——混合路径是刻意的架构选择：子 agent 统一注入保证一致性，Cron/Heartbeat 直通保证时效性 |
| 隔离策略 | Cron 直接调用 `AIAgent.run_conversation()`，但启用裁剪配置（禁用 cronjob/messaging/clarify 工具集，跳过 context files 和 memory） | 创建 isolated-agent session，结果通过 CronDeliveryPlan 投递 | 部分隔离——Cron/Heartbeat 通过 `process_direct()` 使用独立 `session_key`（如 `"cron:{id}"`, `"heartbeat"`），不与 IM 消息共享 session 上下文，但共享核心处理管线 |

## 权衡对比

| 维度 | openclaw | nanobot | hermes-agent |
|------|----------|---------|-------------|
| **路径数量** | 2 条（IM 消息路径 + Cron 独立路径） | 2 条注入路径但 1 条处理路径（子 agent 走 bus 队列 + `_dispatch()`；Cron/Heartbeat 走 `process_direct()` 直通；均在 `_process_message()` 汇合） | 多条入口但 1 条编排路径（CLI、Gateway、Cron 都调用同一 `run_conversation()`） |
| **Cron 隔离程度** | 完全隔离（isolated-agent session，不绑定任何用户；但也支持 main/current/session:* 三种非完全隔离模式） | 部分隔离（Cron/Heartbeat 通过 `process_direct()` 使用独立 `session_key`，与 IM 消息 session 分离；但共享核心处理管线） | 自然隔离（Cron 调用独立的 `AIAgent` 实例，不与 Gateway session 共享） |
| **结果投递** | CronDeliveryPlan 解耦执行和投递（channel / thread / announce / webhook） | Cron/Heartbeat 结果通过 `process_direct()` 返回值由上层回调处理；通知通过 `bus.publish_outbound()` 投递 | Cron 结果通过 `AIAgent` 的返回路径，与调用方约定 |
| **语义区分能力** | 高（isolated-agent 标记使 Cron 消息可识别、可差异化路由） | 低（子 agent 有 `channel="system"` / `sender_id="subagent"` 语义标记；Cron/Heartbeat 的 `sender_id` 固定为 `"user"`，来源元信息在进入处理管线前消失） | 中（Cron 作为独立调用方，调用上下文已知，但 `AIAgent` 内部不区分调用来源） |
| **新增事件源成本** | 高（每条新路径需要独立 session 管理、生命周期、错误恢复） | 中低（bus 路径新增只需 `publish_inbound()` 一行；`process_direct()` 路径需要上层回调注册 + 自定义 `session_key` 管理） | 低（新增入口直接调用 `AIAgent.run_conversation()`） |
| **处理逻辑一致性** | 需显式保证——两条路径可能产生分歧 | 核心处理逻辑统一（`_process_message()` → `_run_agent_loop()` 共享），但预处理路径不共享（`_dispatch()` 的 session-lock / CommandRouter / concurrency gate 对 Cron/Heartbeat 不生效） | 天然保证——所有入口走同一 `run_conversation()` |
| **调试复杂度** | 高（两条路径的 bug 可能仅在其中一条触发） | 中（核心处理统一在 `_process_message()`，但注入入口需分别排查 bus 路径的 `run()` 循环和 `process_direct()` 的上层回调） | 低（所有入口 trace 在同一 `run_conversation()`） |
| **适合规模** | 大（Cron 需要独立的工具策略、上下文管理、审批流程时，独立路径的灵活性是必须的） | 小-中（Cron 和子 agent 只是主对话的附属功能，混合路径以适度复杂度换取处理灵活性和时效性） | 中-大（单体架构下入口多样但核心统一，不需要路径层面的架构决策） |
| **核心取舍** | 宁可增加路径维护成本也不让 Cron 内部执行泄漏到用户可见范围 | 混合路径：子 agent 走完整 bus 路径保证处理一致性；Cron/Heartbeat 直通 `process_direct()` 避免队列排队延迟，但牺牲了统一预处理（无 session-lock / CommandRouter / concurrency gate） | 自然统一——单体架构下这不是一个需要决策的问题 |

## 选择指南

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| **Cron 需要独立工具策略和审批流程** | 独立路径（openclaw 模式） | 当 Cron 执行需要不同于 IM 对话的工具集、安全策略或审批逻辑时，混合路径因缺少 `_dispatch()` 层面的语义区分和路由能力而难以实现 |
| **Cron 执行过程需要对用户透明** | 独立路径（openclaw 模式） | 当 Cron 的中间步骤（tool calls、错误重试）不应出现在用户对话历史中时，isolated-agent session 是强制要求 |
| **代码量极简、事件源都是主对话的附属功能** | 混合路径（nanobot 模式） | 当 Cron 和子 agent 只是主 agent 的简单附属（如每日摘要、文件整理），核心处理逻辑共享已足够，`process_direct()` 直通避免了队列排队延迟 |
| **需要频繁新增事件源类型** | 混合路径（nanobot 模式） | bus 路径新增只需 `publish_inbound()`；`process_direct()` 路径需要上层回调注册但提供更直接的 session 控制 |
| **单体架构、编排层统一** | 自然统一（hermes-agent 模式） | 当系统本质上是单体且所有入口直接调用同一编排函数时，刻意引入路径分离或统一注入都是过度工程化 |
| **需要消息来源元信息但不想要独立路径** | 在混合路径的基础上增加消息 envelope | 在 bus 消息和 `process_direct()` 的 `InboundMessage` 中增加 `source_type` 字段（`im` / `subagent` / `cron` / `heartbeat`），在 `_process_message()` 中根据 `source_type` 做差异化路由和工具集裁剪——这是 nanobot 模式的自然演进，在不增加新路径的前提下恢复语义区分能力 |

## 关键源码引用

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/cron/delivery-plan.ts` | 10-19, 29-86 | `CronDeliveryPlan` 类型定义（10-19）+ `resolveCronDeliveryPlan()` 函数（29-86）：根据 `job.delivery.mode` 解析投递目标（announce/webhook/none），决定 isolated-agent session 的产出如何到达用户。实际创建 isolated session 的逻辑位于 `src/cron/isolated-agent/` 子目录 |
| openclaw | `src/tasks/task-executor.ts` | 85-217 | TaskFlow 独立状态转换函数：`createQueuedTaskRun`(85) → `startTaskRunByRunId`(150) → `completeTaskRunByRunId`(173) / `failTaskRunByRunId`(196)，状态持久化到 SQLite；支持 flow 内多 task 级联(488-580)、cancel 传播(632-712)、block retry(265-374)、owner 访问控制(582-630) |
| openclaw | `openclaw-architecture.md` | 64-78 | 数据流完整描述：IM 消息路径（同步门控 → session 绑定 → context assemble → agent harness）与 Cron 并行路径（Cron Scheduler → isolated-agent → Agent Harness） |
| nanobot | `bus/queue.py` | 8-35 | MessageBus 定义：`asyncio.Queue` inbound/outbound 两个单向队列，将 Channel 层与 Agent 核心解耦。IM 和子 agent 消息经此队列，但 Cron/Heartbeat 通过 `process_direct()` 绕过 |
| nanobot | `agent/loop.py` | 363-396 | `AgentLoop.run()`：从 `bus.consume_inbound()` 取消息（371）→ `_dispatch()` session-lock(402) + concurrency gate(403) + CommandRouter(410) → `_process_message()`(438) |
| nanobot | `agent/loop.py` | 734-750 | `AgentLoop.process_direct()`：Cron/Heartbeat 的注入入口——创建 `InboundMessage` 后直接调用 `_process_message()`(481)，绕过 `bus.inbound` 队列和 `_dispatch()`（含 session-lock、CommandRouter、concurrency gate） |
| nanobot | `agent/loop.py` | 481-578 | `_process_message()`：所有来源的汇聚点——IM/子 agent/Cron/Heartbeat 均在此汇合。子 agent 消息通过 `channel="system"` + `sender_id="subagent"` 走专门分支(491-517)设置 `current_role="assistant"`；IM 消息有 SlashCommand 检查(527-538)；通用路径走 ContextBuilder → `_run_agent_loop()` → AgentRunner |
| nanobot | `agent/subagent.py` | 202-209 | 子 agent 结果注入：完成后通过 `bus.publish_inbound(msg)` 注入入站队列（`channel="system"`, `sender_id="subagent"`），在优先级/路由层面与 IM 消息不做区分 |
| nanobot | `agent/subagent.py` | 114-132 | 子 agent 受限 ToolRegistry：文件工具 + 可选 exec/web，无 message/spawn/cron 工具——防止递归 |
| nanobot | `cron/service.py` | 22-48, 313-314 | CronService：三种调度类型（at/every/cron）计算(22-48)；`FileLock`(77) 保护 action.jsonl 并发写入；触发通过 `on_job` 回调(313-314) → `commands.py:689-742` → `agent.process_direct()`(715)，**不使用** `bus.publish_inbound()` |
| nanobot | `cli/commands.py` | 689-742 | `on_cron_job` 回调：Cron 的实际触发入口——接收 `CronJob` → 构造 `InboundMessage`(698) → `agent.process_direct()`(715) 绕过 bus 队列直通 `_process_message()` |
| nanobot | `heartbeat/service.py` | 14-37, 145-177 | HeartbeatService：单工具 LLM 调用（heartbeat tool，枚举 skip/run）做定期唤醒(14-37)；`_tick()`(145-177) → `on_execute` 回调 → `commands.py:766-787` → `agent.process_direct()`(773)，**不使用** `bus.publish_inbound()` |
| nanobot | `cli/commands.py` | 766-787 | `on_heartbeat_execute` 回调：Heartbeat 的实际触发入口——接收 tasks → `agent.process_direct()`(773) 绕过 bus 队列直通 `_process_message()` |
| hermes-agent | `cron/scheduler.py` | 580-883 | `run_job()` 函数：实际执行 cron 的代码——`from run_agent import AIAgent`(587) → `agent = AIAgent(...)`(736, 裁剪配置：禁用 cronjob/messaging/clarify 工具集，quiet_mode，跳过 context files 和 memory) → `agent.run_conversation(prompt)`(778) |
| hermes-agent | `run_agent.py` | 8130-8189 | `AIAgent.run_conversation()`：CLI、Gateway、Cron 三个入口统一的编排入口 |

## 关联

- [[消息注入模式]]
- [[openclaw/nodes/components/openclaw-cron-scheduler]]
- [[openclaw/nodes/components/openclaw-task-flow]]
- [[nanobot/dimensions/nanobot-architecture]]
- [[hermes-agent/dimensions/hermes-agent-architecture]]
- [[hermes-agent/nodes/components/hermes-agent-ai-agent]]

---

## 修复记录
- 2026-06-19 Phase 3b → 3c 修复（第一轮）：
  - 修正 hermes-agent Cron 层归属：从"编排层的一部分"修正为"基础设施层，直接调用编排层的 AIAgent"（wiki 架构图将 Cron 置于基础设施层）
  - 同步修正在实例矩阵对比表中的同一层归属错误
- 2026-06-19 Phase 3b → 3c 修复（真实源码验证）：
  - ❌ Cron/Heartbeat 并非走 `bus.publish_inbound()`：实际使用 `process_direct()` 绕过 `bus.inbound` 队列和 `_dispatch()`。修正为混合路径描述——子 agent 走 bus 队列 + `_dispatch()` 完整路径；Cron/Heartbeat 走 `process_direct()` 直通 `_process_message()`
  - 修正纳米机器人节标题：从"统一注入"改为"混合路径"
  - 更新数据流图：Cron 路径改为 `CronService._execute_job(service.py:313-314) → on_cron_job 回调(commands.py:689-742) → agent.process_direct()(715) → _process_message()(481)`；Heartbeat 路径改为 `HeartbeatService._tick(service.py:145-177) → on_execute 回调(commands.py:766-787) → agent.process_direct()(773) → _process_message()(481)`
  - 重写"架构简化最大化"节为"混合路径的本质"：反映 `_process_message()` 是汇聚点但注入路径分叉的现实
  - 更新设计取向表：预处理路径不统一 + 来源元信息丢失
  - 更新对比表中 nanobot 列全部 9 行：路径数量、隔离程度、结果投递、语义区分、新增成本、处理一致性、调试复杂度、适合规模、核心取舍
  - 新增 `agent/loop.py:734-750` process_direct() 溯源引用；新增 `cli/commands.py:689-742` 和 `766-787` 两个回调溯源
  - 修正 cron/service.py 和 heartbeat/service.py 溯源：移除错误的 `bus.publish_inbound()` 描述，标注实际回调路径
  - 修正子 agent 注入描述：从"没有任何语义区别"改为反映 `channel="system"` + `sender_id="subagent"` 的基础语义标记
  - 修正 hermes-agent Cron 引用：`cron/__init__.py` → `cron/scheduler.py:580-883 run_job()`；补充 Cron AIAgent 的裁剪配置说明
  - 修正 openclaw task-executor 行号：85-112 → 85-217；补充 CronDeliveryPlan 实际创建 session 的逻辑位置
