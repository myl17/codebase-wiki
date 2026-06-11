---
node_type: Component
scope: subsystem
concept_candidate: 无消息主动触发
sources:
  - src/cron/delivery-plan.ts:10-19
---

# CronScheduler

定时调度器，`CronDeliveryPlan` 决定结果投递目标（channel、thread、announce、webhook）。支持 isolated-agent 模式：每次 cron 触发创建独立 agent session。**唯一一个可以在无 IM 消息触发的情况下主动发起 agent 运行的入口**——其他所有 agent 运行都是消息驱动的。
^[src/cron/delivery-plan.ts:10-19]
