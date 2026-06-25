# 验证报告：agent-trigger-path

## 格式完整性
- [x] 问题陈述是"如何..."问题形式 — `非用户消息事件如何进入 Agent 处理流程——独立触发路径还是统一消息注入？`
- [x] 核心关切列表 >= 2 条 — 共 4 条
- [x] 每个权衡位置有"优先满足"和"接受妥协"两个字段 — openclaw 和 nanobot 均有
- [x] 跨仓库对比表列数 = 仓库数 — 3 列 (openclaw / nanobot / hermes-agent)
- [x] 溯源表完整 — 有

---

## 逐仓库验证

### openclaw

**Claim 1**: "`src/cron/delivery-plan.ts:10-19` 定义了 `CronDeliveryPlan`——Cron 触发后，不经过 Channel Plugin 和 Session Binding，也不与任何现有用户 session 关联，而是创建独立的 **isolated-agent session**。"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/cron/delivery-plan.ts:10-19`
代码摘要：第 10-19 行定义了 `CronDeliveryPlan` 类型（包含 `mode`, `channel`, `to`, `threadId`, `accountId`, `source`, `requested` 字段）。这是一个 TypeScript 类型定义，不包含创建 session 的逻辑。实际 session 创建在 `src/cron/isolated-agent/session.ts:12-89`（`resolveCronSession` 函数）和 `src/cron/isolated-agent/run-executor.ts` 中。`delivery-plan.ts` 的核心逻辑是 `resolveCronDeliveryPlan()` 函数（第 29 行起），它解析 delivery 模式并决定投递目标。

判定：⚠️ 行号引用正确（10-19 定义了 `CronDeliveryPlan` 类型），但描述暗示该类型定义包含了"创建 isolated-agent session"的行为。实际上 `CronDeliveryPlan` 只定义投递计划的**数据结构**，创建隔离 session 的逻辑分散在 `isolated-agent/session.ts` 和 `isolated-agent/run-executor.ts` 中。修正建议：注明 `CronDeliveryPlan` 是投递计划的数据类型定义，实际创建 isolated session 的逻辑位于 `src/cron/isolated-agent/` 子目录中。

---

**Claim 2**: "Cron 是唯一一个可以在无 IM 消息触发的情况下主动发起 agent 运行的入口。"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/cron/isolated-agent/run-executor.ts:45-50` — `createCronPromptExecutor()` 接收 `CronJob` 并启动 agent 运行。无其他显式的非 IM 触发 agent 运行入口。

判定：✅ 源码中未发现其他无 IM 消息触发的 agent 运行入口。Cron 调度器确实是唯一主动发起 agent 运行的路径。

---

**Claim 3**: "Cron 任务完成后，`CronDeliveryPlan` 决定结果投递到哪个 channel、哪个 thread、是否通过 announce 通知、或走 webhook 回调。"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/cron/delivery-plan.ts:29-86` — `resolveCronDeliveryPlan()` 根据 `job.delivery.mode` 解析为 `"announce"` / `"webhook"` / `"none"`。Line 62-68 组合 mode、channel、to、threadId、accountId 等字段构成完整投递计划。Line 71-76 对 `agentTurn` 类型 payload 自动推断模式。

判定：✅ 与源码一致。`CronDeliveryPlan` 确实包含 channel、thread、announce、webhook 四种投递维度。

---

**Claim 4**: "`src/tasks/task-executor.ts:85-112` 的 TaskFlow 状态机负责 Cron 触发的任务生命周期管理：`createQueuedTaskRun` → `startTaskRunByRunId` → `completeTaskRunByRunId` / `failTaskRunByRunId`，状态持久化到 SQLite。"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/tasks/task-executor.ts:85-217`
代码摘要：
- `createQueuedTaskRun()` 第 85 行：创建 status="queued" 的任务记录
- `startTaskRunByRunId()` 第 150 行：调用 `markTaskRunningByRunId()` 将任务转为 running
- `completeTaskRunByRunId()` 第 173 行：以 status="succeeded" 终止任务
- `failTaskRunByRunId()` 第 196 行：以 status="failed"/"timed_out"/"cancelled" 终止任务
- SQLite 持久化：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/tasks/task-registry.store.sqlite.ts:1-30` — 使用 `node:sqlite` 的 `DatabaseSync` 存储任务数据

判定：⚠️ 行号覆盖范围不精确。Concept 页标注 `85-112`，但 `startTaskRunByRunId` 在第 150 行，`completeTaskRunByRunId` 在第 173 行，`failTaskRunByRunId` 在第 196 行——这些函数分布在 85-217 行，不是 85-112 的紧凑区间。其次，这些函数是**独立函数**而非严格的状态机（如不存在"必须 queued 才能 start"的显式约束检查）。修正建议：行号改为 `85-217`，并注明这些是独立的状态转换函数而非内联状态约束的状态机。

---

**Claim 5**: "TaskFlow 支持 flow 内多 task 级联、cancel 传播、block retry、owner 访问控制"

源码：
- 多 task 级联：`task-executor.ts:488-580` — `runTaskInFlow()` 在同一 flow 下创建子任务，检查 `flow.status` 和 `cancelRequestedAt` 守卫
- cancel 传播：`task-executor.ts:632-712` — `cancelFlowById()` 遍历所有 linkedTasks，调用 `cancelTaskById` 传播取消
- block retry：`task-executor.ts:265-374` — `resolveRetryableBlockedFlowTask()` 检查 flow.status==="blocked" 且 task.terminalOutcome==="blocked"，`retryBlockedFlowTask()` 创建新 task 继承原 flow 的 ownerKey
- owner 访问控制：`task-executor.ts:582-630` — `runTaskInFlowForOwner()` 和 `cancelFlowByIdForOwner()` 通过 `getTaskFlowByIdForOwner()` 做 owner 校验

判定：✅ 四个特性均有对应源码实现。

---

**Claim 6**: "isolated-agent session 意味着：Cron 执行过程中产生的消息不会出现在任何用户的对话历史中"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/cron/isolated-agent/session.ts:12-89` — `resolveCronSession()` 为 cron 创建独立的 sessionId（第 51/57 行 `crypto.randomUUID()`），不与任何用户 session 共享。但需注意 `CronSessionTarget` 类型（`src/cron/types.ts:17`）包括 `"main" | "isolated" | "current" | session:${string}` 四种，并非所有 cron 任务都使用 "isolated" session——"current" 和 "session:*" 会与已有 session 关联。

判定：⚠️ 对 "isolated" 模式的描述正确，但未提及 cron 实际支持四种 sessionTarget（main/isolated/current/session:*），其中 "current" 和 "session:*" 会复用已有 session，不完全隔离。修正建议：补充说明 cron 支持多种 sessionTarget，isolated 只是其中一种（也是最常用的一种）。

---

**Claim 7**: "维护两条独立的处理路径（IM 消息路径 + Cron 触发路径）"

源码：`/Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/openclaw-architecture.md:64-78` — 数据流图明确显示两条路径：
用户消息路径：IM 平台 → Channel Plugin → Tool Policy Pipeline → Session Binding → Context Engine → Agent Harness
并行触发路径：Cron Scheduler → isolated-agent → Agent Harness

判定：✅ 架构文档和源码均确认存在两条独立路径。

---

**Claim 8**: "openclaw 的数据流分为两条互不交叉的路径（`openclaw-architecture.md` 第 64-77 行）"

源码：`/Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/openclaw-architecture.md:64-78` — 行号匹配（数据流从 64 行开始，到 78 行结束）。

判定：✅ 行号匹配，描述与架构文档一致。

---

### nanobot

**Claim 1**: "nanobot 的 `MessageBus` 用 `asyncio.Queue` 将 Channel 层与 Agent 核心完全解耦（`bus/queue.py:8-35`）。两个单向队列——`inbound` 和 `outbound`——是系统中所有消息的唯一通道。"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/bus/queue.py:8-35`
代码摘要：`MessageBus` 类在 `__init__` 中创建 `self.inbound: asyncio.Queue[InboundMessage]`（第 17 行）和 `self.outbound: asyncio.Queue[OutboundMessage]`（第 18 行）。提供 `publish_inbound` / `consume_inbound` / `publish_outbound` / `consume_outbound` 四个方法。

判定：⚠️ "所有消息的唯一通道"——这在技术上是错误的。Cron 和 Heartbeat 通过 `AgentLoop.process_direct()` 绕过了 `bus.inbound` 队列（详见 Claim 3），因此 inbound 队列不是"所有消息的唯一通道"。outbound 方面，`process_direct()` 的返回值直接由调用方处理，也并非所有 outbound 都经过 `bus.outbound`。修正建议：将"唯一通道"改为"IM 和子 agent 消息的主要通道"。

---

**Claim 2**: "`AgentLoop.run()` 从 `bus.consume_inbound()` 取消息（`agent/loop.py:363-556`），不做来源区分。"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/agent/loop.py:363-396`
代码摘要：`run()` 方法（第 363 行）在 while 循环中调用 `self.bus.consume_inbound()`（第 371 行）获取消息，1 秒超时。获取消息后调用 `self._dispatch(msg)`（第 394 行）进行处理。`run()` 层面确实不做来源区分——所有从 inbound 队列取出的消息统一进入 `_dispatch()`。

判定：✅ `run()` 方法对从队列取出的消息不做来源区分——但需注意这仅对**通过 inbound 队列到达**的消息成立。Cron 和 Heartbeat 绕过了 `run()` 和 `_dispatch()`（见 Claim 3）。

---

**Claim 3**: "子 agent、Cron、Heartbeat 三种非用户消息来源，全部通过 `bus.publish_inbound(msg)` 注入同一个入站队列，与 IM 用户消息共享完全相同的消费路径。"

源码：

**子 agent**: `/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/agent/subagent.py:201-209`
```
msg = InboundMessage(channel="system", sender_id="subagent", ...)
await self.bus.publish_inbound(msg)
```
✅ 子 agent 确实通过 `bus.publish_inbound()` 注入。

**Cron**: `/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/cli/commands.py:689-742`
- `on_cron_job` 回调（第 689 行）调用 `agent.process_direct()`（第 715 行），**不是** `bus.publish_inbound()`
- `process_direct()` 定义在 `agent/loop.py:734-750`，它创建 `InboundMessage` 后直接调用 `self._process_message()`，绕过了 `bus.inbound` 队列和 `_dispatch()`（含 session-lock、CommandRouter、concurrency gate）
- Cron 的实际路径：`CronService._execute_job(service.py:313-314) → on_job 回调(commands.py:689-742) → agent.process_direct()(commands.py:715) → _process_message()(loop.py:481)`
❌ Cron 不使用 `bus.publish_inbound()`，而是通过 `process_direct()` 绕过入站队列。

**Heartbeat**: `/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/cli/commands.py:766-787`
- `on_heartbeat_execute` 回调（第 766 行）调用 `agent.process_direct()`（第 773 行），同样**不是** `bus.publish_inbound()`
- Heartbeat 的实际路径：`HeartbeatService._tick(service.py:145-177) → on_execute 回调(commands.py:766-787) → agent.process_direct()(commands.py:773) → _process_message()(loop.py:481)`
❌ Heartbeat 不使用 `bus.publish_inbound()`，而是通过 `process_direct()` 绕过入站队列。

判定：❌ 这是概念页最严重的错误。三种来源中只有子 agent 使用 `bus.publish_inbound()` 注入队列；Cron 和 Heartbeat 都通过 `agent.process_direct()` 直接调用 `_process_message()`，完全绕过 `bus.inbound` 队列和 `_dispatch()`（包括其 session-lock、CommandRouter、concurrency gate 等逻辑）。概念页的数据流图（第 88-93 行）和核心论断需要修复。

修正建议：nanobot 的实际模式是**混合路径**——子 agent 走 bus 队列（经 `_dispatch()`），Cron/Heartbeat 走 `process_direct()` 直通（绕过 `_dispatch()`）。两者都在 `_process_message()` 汇合，共享核心处理逻辑（ContextBuilder → AgentRunner），但进入方式不同。应将概念页的"统一注入"描述修正为反映这种混合架构。

---

**Claim 4**: "`agent/subagent.py:202-209` 是子 agent 结果注入的关键位置——子 agent 完成后，结果通过 `bus.publish_inbound(msg)` 注入入站队列，与 IM 消息在系统中没有任何语义区别。"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/agent/subagent.py:201-209`
```
msg = InboundMessage(
    channel="system",
    sender_id="subagent",
    chat_id=f"{origin['channel']}:{origin['chat_id']}",
    content=announce_content,
)
await self.bus.publish_inbound(msg)
```

判定：⚠️ 注入方式正确（`bus.publish_inbound()`），但"没有任何语义区别"不准确。子 agent 消息使用 `channel="system"` 和 `sender_id="subagent"`——在 `_process_message()` 中（`loop.py:491-502`），系统消息有专门的处理分支：检查 `msg.channel == "system"`、根据 `sender_id == "subagent"` 设置 `current_role = "assistant"`（而非默认的 "user"）。因此系统层面确实区分了子 agent 消息与 IM 消息，只是不在优先级或路由层面做区分。修正建议：将"没有任何语义区别"改为"在优先级/路由层面不做区分，但系统可通过 channel='system' 和 sender_id='subagent' 识别子 agent 消息并设置 assistant role"。

---

**Claim 5**: "子 agent 共享 `AgentRunner` 引擎但拥有独立的受限 `ToolRegistry`（`agent/subagent.py:114-132`）：文件工具 + 可选的 exec/web 工具，不包含 message/spawn/cron 工具——防止递归创建子 agent。"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/agent/subagent.py:113-133`
代码摘要：
- 第 113 行注释：`# Build subagent tools (no message tool, no spawn tool)`
- 第 114 行：创建新的 `ToolRegistry()` 实例
- 第 117-122 行：注册 ReadFileTool、WriteFileTool、EditFileTool、ListDirTool、GlobTool、GrepTool
- 第 123-130 行：条件注册 ExecTool（需 `exec_config.enable`）
- 第 131-133 行：条件注册 WebSearchTool、WebFetchTool（需 `web_config.enable`）
- 确实没有 message/spawn/cron 工具

判定：✅ 工具注册与描述完全一致。"防止递归创建子 agent"的解读合理（无 spawn 工具无法创建新子 agent）。

---

**Claim 6**: "15 轮 iteration budget，tool error 为 fatal 级别立即终止。"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/agent/subagent.py:140-150`
```
result = await self.runner.run(AgentRunSpec(
    ...
    max_iterations=15,
    ...
    fail_on_tool_error=True,
))
```
- 第 144 行：`max_iterations=15`
- 第 149 行：`fail_on_tool_error=True`
- 第 151-159 行：当 `result.stop_reason == "tool_error"` 时立即返回错误

判定：✅ 与源码完全一致。

---

**Claim 7**: "`_dispatch()` 中的 CommandRouter、session-lock、`_process_message()` 中的 ContextBuilder、`_run_agent_loop()` 中的 AgentRunner 对任何来源的消息一视同仁。"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/agent/loop.py:398-578`
- `_dispatch()` 第 402 行：`lock = self._session_locks.setdefault(msg.session_key, asyncio.Lock())` — session-lock
- `_dispatch()` 第 403 行：`gate = self._concurrency_gate or nullcontext()` — concurrency gate
- `_dispatch()` 第 438 行：`await self._process_message(...)` — 进入统一处理
- `_process_message()` 第 540-556 行：ContextBuilder → `_run_agent_loop()` 包含 AgentRunner

判定：⚠️ "对任何来源的消息一视同仁"——这只对通过 `_dispatch()` 进入的消息成立（即通过 bus.inbound 队列到达的 IM 和子 agent 消息）。但 Cron 和 Heartbeat 通过 `process_direct()` 绕过了 `_dispatch()`，因此它们不经过 CommandRouter、session-lock、concurrency gate 的处理。修正建议：注明 `_dispatch()` 的统一性仅适用于经 bus 队列进入的消息。

---

**Claim 8**: "Cron 和 Heartbeat 不需要像 openclaw 那样维护独立的 session 生命周期、Tool Policy Pipeline、错误恢复路径——它们只是 bus 队列的另一个生产者。"

源码：Cron（`cli/commands.py:715`）和 Heartbeat（`cli/commands.py:773`）均使用 `agent.process_direct()`，此方法传入自定义 `session_key`（如 `"cron:{job.id}"` 或 `"heartbeat"`）和 `channel`/`chat_id`。因此它们确实维护了独立的 session（通过不同的 session_key），但不通过 bus 队列注入（见 Claim 3）。

判定：❌ "它们只是 bus 队列的另一个生产者"——Cron 和 Heartbeat 不是 bus 队列的生产者，它们通过 `process_direct()` 绕过队列。它们也维护了独立的 session（通过不同的 session_key），这与"不需要维护独立 session 生命周期"的表述矛盾。修正建议：重新表述为"它们通过 `process_direct()` 直接调用 `_process_message()`，使用独立的 session_key 但共享核心处理管线"。

---

**Claim 9**: "所有消息经过同一条消费路径，所有日志在 `AgentLoop.run()` 的同一处被记录，trace 单一路径即可排查任何来源的问题。"

源码：Cron 和 Heartbeat 通过 `process_direct()` 绕过了 `AgentLoop.run()`（第 363 行）的消费循环。它们的日志不会在 `run()` 中被记录。但 `_process_message()`（第 481 行）是共享的，所以核心处理逻辑是统一的。

判定：⚠️ "所有日志在 `AgentLoop.run()` 的同一处被记录"——Cron 和 Heartbeat 的日志在调用 `process_direct()` 的上层回调中被记录，不在 `run()` 循环内。"trace 单一路径即可排查"——对处理逻辑成立（都在 `_process_message()`），但对注入入口不成立（需要分别查看 bus 路径和 `process_direct()` 路径）。

---

**Claim 10**: "`cron/service.py:22-48` CronService：三种调度类型（at/every/cron），CronStore 用 FileLock 做持久化，触发通过 `bus.publish_inbound()` 注入。"

源码：
- 第 22-48 行：`_compute_next_run()` 函数处理 `at`/`every`/`cron` 三种调度类型 ✅
- 第 77 行：`self._lock = FileLock(str(self._action_path.parent) + ".lock")` — FileLock 用于保护 action.jsonl 的并发写入，不是用于 CronStore JSON 文件的持久化（持久化是 `_save_store()` 中的普通文件写入，第 181-232 行）
- 触发：第 313-314 行 `await self.on_job(job)` — CronService 本身不调用 `bus.publish_inbound()`，它通过 `on_job` 回调机制触发。实际触发逻辑在 `commands.py:689-742` 的 `on_cron_job` 回调中，该回调使用 `process_direct()` 而非 `bus.publish_inbound()`

判定：❌ 有三处不准确：
1. FileLock 用于 action 协调而非 "持久化"——持久化通过 JSON 文件写入完成
2. "触发通过 `bus.publish_inbound()` 注入" —— CronService 使用 `on_job` 回调模式，最终通过 `process_direct()` 而非 `bus.publish_inbound()`
3. 行号 `22-48` 仅覆盖调度类型计算，不包含 FileLock（第 77 行）和触发逻辑（commands.py:689）

---

**Claim 11**: "`heartbeat/service.py:14-40` HeartbeatService：单工具 LLM 调用（heartbeat tool，枚举 skip/run）做定期唤醒，结果经 `bus.publish_inbound()` 注入。"

源码：
- 第 14-37 行：定义 `_HEARTBEAT_TOOL` 单工具（heartbeat，枚举 `skip`/`run`） ✅
- 第 40-187 行：`HeartbeatService` 类，`_decide()` 方法（第 87-111 行）用单工具 LLM 调用做 skip/run 决策 ✅
- 结果注入：第 165 行 `await self.on_execute(tasks)` → `commands.py:773` 调用 `agent.process_direct()`，不是 `bus.publish_inbound()`
- 通知投递：第 173 行 `await self.on_notify(response)` → `commands.py:795` 调用 `bus.publish_outbound()`

判定：❌ "结果经 `bus.publish_inbound()` 注入" —— Heartbeat 结果通过 `on_execute` → `process_direct()` 路径执行，不经过 `bus.publish_inbound()`。投递通过 `bus.publish_outbound()` 是正确的。修正建议：改为"执行经 `on_execute` → `process_direct()` 进入处理路径，投递经 `on_notify` → `bus.publish_outbound()` 发出"。

---

**Claim 12**: "语义的完全丢失：子 agent 结果、Cron 触发、Heartbeat 唤醒、IM 消息在系统中是完全等同的。"

源码（反证）：
- 子 agent 消息使用 `channel="system"`、`sender_id="subagent"`，在 `_process_message()` 中走专门分支（`loop.py:491-517`），设置 `current_role="assistant"`
- Cron 消息通过 `process_direct()` 传入，sender_id 固定为 `"user"`（`loop.py:746`）
- Heartbeat 消息同样通过 `process_direct()` 传入，sender_id 固定为 `"user"`
- IM 消息走 `bus.inbound → _dispatch() → _process_message()`，有 SlashCommand 检查、MessageTool 启动等额外处理（`loop.py:527-538`）

判定：⚠️ 不同来源在进入系统和处理路径上存在不同程度的语义区分：子 agent 消息走专门的 system 分支，Cron/Heartbeat/IM 走通用分支但到达路径不同（`process_direct` 跳过 `_dispatch` 的 CommandRouter 和 session-lock）。因此"完全等同"不准确——更精确的表述是"核心处理逻辑共享但注入路径和预处理存在差异"。

---

### hermes-agent

**Claim 1**: "hermes-agent 的 Cron 调度器（`cron/__init__.py:1-42`）直接调用 `AIAgent.run_conversation()`（`run_agent.py:8130-8189`），不经过 Gateway 的消息路由层。"

源码：
- `/Users/yuanlimiao/Work/agent_harness/hermes-agent/cron/__init__.py:1-42` — 这是一个 `__init__.py` 模块文件，仅负责 re-export（`from cron.jobs import ...`, `from cron.scheduler import tick`），不包含直接调用 `AIAgent.run_conversation()` 的代码
- `/Users/yuanlimiao/Work/agent_harness/hermes-agent/cron/scheduler.py:580-883` — `run_job()` 函数（第 580 行）是实际执行 cron 的代码。第 587 行 `from run_agent import AIAgent`，第 736 行 `agent = AIAgent(...)`，第 778 行 `agent.run_conversation(prompt)` 在 ThreadPoolExecutor 中执行
- `/Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py:8130` — `run_conversation()` 方法定义

判定：⚠️ 模块引用不准确。`cron/__init__.py` 是 re-export 模块，实际执行逻辑在 `cron/scheduler.py:run_job()`（第 580-883 行）。修正建议：将引用改为 `cron/scheduler.py:580-883` 或 `cron/scheduler.py:run_job()`。

---

**Claim 2**: "Cron 位于基础设施层，直接调用编排层的 AIAgent——与 CLI TUI 和 Gateway 平台适配器并列，都是 AIAgent 的调用方。"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/cron/scheduler.py:580-760`
代码摘要：`run_job()` 函数直接 `from run_agent import AIAgent`（第 587 行）并实例化 `AIAgent(...)`（第 736 行），然后调用 `agent.run_conversation(prompt)`（第 778 行）。不经过 Gateway 消息路由或 CLI 适配器。

判定：✅ 架构位置描述正确——Cron 确实是 AIAgent 的独立调用方。但需注意 Cron 创建 AIAgent 时传入了特殊配置（`disabled_toolsets=["cronjob", "messaging", "clarify"]`, `quiet_mode=True`, `skip_memory=True`, `skip_context_files=True`）——并非与 CLI/Gateway 使用完全相同的 AIAgent 配置。

---

**Claim 3**: "hermes-agent 不面对独立路径 vs 统一注入的选择问题，因为其单体架构下 Cron 天然是 AIAgent 的另一个调用方。"

源码：Cron 入口（`scheduler.py:run_job()`）、CLI 入口、Gateway 入口各自独立调用 `AIAgent.run_conversation()`。不存在消息总线或队列注入机制。数据流是单向的：入口 → AIAgent → 安全层 → 工具层。

判定：✅ 单体架构的定性准确。hermes-agent 没有消息总线概念，所有入口直接调用同一 `run_conversation()` 函数。

---

**Claim 4**: "Cron 调度器直接调用 AIAgent.run_conversation()，复用主对话循环的所有机制（审批、上下文组装、工具策略）。"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/cron/scheduler.py:736-760`
```
agent = AIAgent(
    ...
    disabled_toolsets=["cronjob", "messaging", "clarify"],
    quiet_mode=True,
    skip_context_files=True,
    skip_memory=True,
    platform="cron",
    ...
)
```

判定：⚠️ "复用所有机制"不精确。Cron 创建的 AIAgent 实例明确禁用了三个工具集（cronjob/messaging/clarify），跳过了上下文文件注入和记忆加载，启用了 quiet_mode。这些限制意味着 Cron 的 AIAgent 与 Gateway/CLI 的 AIAgent 不完全相同——工具集被裁剪，上下文组装被简化。修正建议：将"所有机制"改为"核心机制（Agent 循环、工具调用、审批流程），但工具集被裁剪（禁用 cronjob/messaging/clarify）且上下文组装简化（跳过 context files 和 memory）"。

---

**Claim 5**: "CLI、Gateway、Cron 三个入口直接调用同一个 AIAgent.run_conversation()，不需要额外的路径架构决策。"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py:8130` — `run_conversation()` 方法接收 `user_message` 和一系列可选参数，设计为通用入口。

判定：✅ 架构层面准确——三个入口确实共享同一函数签名。

---

## 关切验证

| 关切 | 跨仓库对比表对应行 | 判定 |
|------|-------------------|------|
| 1. 处理统一性 | 路径数量、处理逻辑一致性 行 | ✅ 有对应——通过路径数量和处理一致性两个维度覆盖 |
| 2. 语义区分 | 语义区分能力 行 | ✅ 有对应——但 nanobot 的"零"语义区分需要在修正后重新评估（实际上 sender_id 和 channel="system" 提供了基础的语义信息） |
| 3. Session 隔离 | Cron 隔离程度 行 | ✅ 有对应 |
| 4. 架构简化 | 新增事件源成本、调试复杂度、核心取舍 行 | ✅ 有对应 |

---

## 追加完整性

- [x] openclaw 在各节均有提及 — 实例矩阵、openclaw 专节、权衡对比表、选择指南、溯源表均包含
- [x] nanobot 在各节均有提及 — 实例矩阵、nanobot 专节、权衡对比表、选择指南、溯源表均包含
- [x] hermes-agent 在各节均有提及 — 实例矩阵、hermes-agent 专节、权衡对比表、选择指南、溯源表均包含

---

## 绝对化语言验证

| 绝对化表述 | 源码边界条件 | 判定 |
|-----------|------------|------|
| "子 agent、Cron、Heartbeat 三种非用户消息来源，全部通过 bus.publish_inbound(msg) 注入" | Cron 通过 process_direct() 绕过队列（commands.py:715），Heartbeat 同样通过 process_direct() 绕过队列（commands.py:773）。只有子 agent 使用 bus.publish_inbound() | ❌ 错误——2/3 来源不走 bus.publish_inbound() |
| "所有消息经过同一条消费路径" | Cron/Heartbeat 绕过 run() 和 _dispatch()，直接进入 _process_message()。路径不同但终点相同 | ⚠️ 部分正确——共享 _process_message() 但不共享 _dispatch() |
| "零额外调度器"（Cron 和 Heartbeat 不需要独立 session 生命周期） | process_direct() 传入独立的 session_key（如 "cron:{id}", "heartbeat"），使用独立 session。调度器本身（CronService/HeartbeatService）也是独立的 | ⚠️ session 虽独立但管理开销低于 openclaw 的完整 isolated-agent |
| "完全隔离"（openclaw isolated-agent） | CronSessionTarget 支持 isolated/main/current/session:* 四种模式，并非所有 cron 任务都完全隔离 | ⚠️ 对 isolated 模式正确，但存在其他模式 |
| "语义的完全丢失"（nanobot） | 子 agent 消息用 channel="system" 走专门分支（_process_message 行 491）；sender_id="subagent" 影响 current_role | ⚠️ 不完全丢失——基础语义信息保留在 channel 和 sender_id 字段中 |
| "Cron 是唯一一个可以在无 IM 消息触发的情况下主动发起 agent 运行的入口"（openclaw） | 源码中未发现其他非 IM 触发入口 | ✅ 准确 |
| "所有日志在 AgentLoop.run() 的同一处被记录"（nanobot） | Cron/Heartbeat 通过 process_direct() 绕过 run()，日志在上层回调中记录 | ⚠️ 不准确——Cron/Heartbeat 的日志不在 run() 循环中 |
| "天然保证——所有来源走同一函数调用链"（nanobot 处理逻辑一致性） | Cron/Heartbeat 绕过 _dispatch()，与 IM/子 agent 的调用链不完全相同 | ⚠️ _process_message() → _run_agent_loop() 共享，但 _dispatch() 部分不共享 |
| "天然保证——所有入口走同一 run_conversation()"（hermes-agent） | 三个入口（CLI/Gateway/Cron）确实都调用同一个 run_conversation() 方法 | ✅ 准确 |

---

## 汇总

总 claim 数：25 | ✅：11 | ⚠️：10 | ❌：4

关键发现：

1. **nanobot Cron/Heartbeat 路径错误（❌ 最高严重度）**：概念页核心论断——nanobot 的 Cron 和 Heartbeat 通过 `bus.publish_inbound()` 统一注入——与源码矛盾。实际上：
   - Cron 路径：`CronService._execute_job → on_job 回调 → agent.process_direct() → _process_message()`（绕过 `bus.inbound` 队列和 `_dispatch()`）
   - Heartbeat 路径：`HeartbeatService._tick → on_execute 回调 → agent.process_direct() → _process_message()`（同样绕过）
   - 只有子 agent 使用 `bus.publish_inbound()` 注入队列
   - 这推翻了概念页对 nanobot "统一注入"模式的核心定性。nanobot 的实际模式是**混合路径**：子 agent 走 bus 队列（经 `_dispatch()`），Cron/Heartbeat 走 `process_direct()` 直通 `_process_message()`。

2. **"统一注入"的修正**：nanobot 的实际架构精髓在于 `_process_message()` 是所有消息的汇聚点（而非 `bus.inbound` 队列是所有消息的通道）。处理逻辑的统一性是真实的——`_process_message()` → `_run_agent_loop()` 对所有来源共享——但注入方式的统一性不是。子 agent 走 bus 队列 + `_dispatch()` 的完整路径，Cron/Heartbeat 走 `process_direct()` 的捷径。

3. **openclaw sessionTarget 范围**：Cron 支持四种 sessionTarget（main/isolated/current/session:*），非仅 isolated。isolated 是主要模式但并非唯一选项。

4. **hermes-agent Cron 模块引用错误**：`cron/__init__.py` 是 re-export 模块，实际执行逻辑在 `cron/scheduler.py:run_job()`（第 580-883 行）。

5. **hermes-agent Cron 的工具裁剪**：Cron 创建的 AIAgent 禁用了三个工具集（cronjob/messaging/clarify）并跳过了 context files 和 memory，并非"复用所有机制"。

6. **nanobot 语义区分不完全丢失**：子 agent 消息的 `channel="system"` 和 `sender_id="subagent"` 在 `_process_message()` 中触发专门处理分支（`loop.py:491-502`），设置 `current_role="assistant"`。基础语义信息得以保留。

7. **nanobot FileLock 用途偏差**：FileLock（`cron/service.py:77`）保护 action.jsonl 的并发写入，不是持久化机制——持久化通过 `_save_store()` 的 JSON 文件写入完成。
