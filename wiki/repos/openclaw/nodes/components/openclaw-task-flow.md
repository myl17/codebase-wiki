---
node_type: Component
scope: subsystem
concept_candidate: 任务编排
sources:
  - src/tasks/task-executor.ts:85-112
extracted_from:
  - architecture
---

# TaskFlow

任务状态机：`createQueuedTaskRun` → `startTaskRunByRunId` → `completeTaskRunByRunId` / `failTaskRunByRunId`，状态持久化到 SQLite。支持 flow 内多 task 级联、cancel 传播、block retry、owner 访问控制。CronScheduler 触发的执行落到这里。
^[src/tasks/task-executor.ts:85-112]
