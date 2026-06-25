# Tasks + Cron 调度系统（OpenClaw）

## 是什么 / 边界

Tasks + Cron 是 OpenClaw 的任务状态机和定时触发层：Tasks 管理多步骤任务的状态流转（queued → running → completed / failed），Cron 提供定时触发机制，是系统中唯一可以在没有 IM 消息的情况下主动发起 agent 运行的入口。不直接执行 AI 调用（由 Agent Harness 负责），不管理对话上下文（由 Context Engine 负责）。

## 关键实现

- TaskFlow 状态机：`src/tasks/task-executor.ts`（`createQueuedTaskRun` → `startTaskRunByRunId` → `completeTaskRunByRunId` / `failTaskRunByRunId`）
- 状态持久化：`src/tasks/task-flow-registry.store.sqlite.ts`（SQLite 持久化）
- 支持能力：flow 内多 task 级联、cancel 传播、block retry、owner 访问控制
- Cron 调度器：`src/cron/`
- 投递计划：`src/cron/delivery-plan.ts`（`CronDeliveryPlan`：channel / thread / announce / webhook 四种投递目标）
- Isolated-agent 模式：每次 cron 触发创建独立 agent session，互不干扰

## 设计选择记录

- **维度**：Architecture
- **选择**：Cron 是唯一一个无 IM 消息触发 agent 运行的入口，使用 isolated-agent 模式（每次触发创建独立 session）
- **替代方案**：Cron 触发复用已有的 IM channel session 来运行 agent
- **为什么有这个选择**：Cron 触发的任务通常是无状态的周期性任务（如每日报告、定期检查），独立 session 避免污染用户的对话历史；复用已有 session 会导致 cron 输出混入对话 context

---

- **维度**：Architecture
- **选择**：TaskFlow 状态持久化到 SQLite，支持 cancel 传播和 block retry
- **替代方案**：任务状态只在内存中维护，进程重启后丢失
- **为什么有这个选择**：agent 执行的任务可能是跨多轮对话的长任务，内存状态在进程重启（或 respawn）后会丢失，持久化到 SQLite 确保任务状态在进程重启后可恢复

---

- **维度**：Performance Tradeoffs
- **选择**：长时间无输出的命令轮询使用指数退避（`5s → 10s → 30s → 60s`），有新输出时立即重置为 5s
- **替代方案**：固定频率轮询（如每 5 秒）
- **为什么有这个选择**：长时间运行的命令（如编译、测试）在中间阶段不会有输出，固定频率轮询浪费 CPU；指数退避在最坏情况下引入 60s 延迟，但大幅减少空轮询开销
