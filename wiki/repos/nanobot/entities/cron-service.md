---
type: entity
repo: nanobot
slug: cron-service
problem: 如何调度和管理 Agent 的定时任务，支持一次性、间隔和 Cron 表达式三种调度方式
generated: 2026-06-25
source_files:
  - nanobot/cron/service.py
  - nanobot/cron/types.py
---

# Cron Service

**代码位置**：`nanobot/cron/`
**这个模块解决什么问题**：
- 实现层：基于文件持久化的任务调度器，支持 at（一次性）、every（间隔）、cron 三种调度方式，多实例间通过 action.jsonl 共享任务变更
- 问题层：如何调度和管理 Agent 的定时任务，支持多种调度方式和多实例协调
**对外暴露什么**：`CronService` 类（nanobot/cron/service.py:65）、`CronJob` dataclass（nanobot/cron/types.py）、`CronSchedule` dataclass
**它和谁交互**：
- 被 [[entities/agent-loop]] 调用（启动 cronservice，注册 CronTool 供 Agent 使用）
- 被 Agent Cron Tool 调用（通过 `add_job()` / `remove_job()` / `list_jobs()` API）
- 触发 [[entities/memory-system]]（Dream 作为系统 cron job 周期性运行）
- 依赖 `croniter` 库（解析 Cron 表达式）
**为什么它是可分离的**：独立服务，仅依赖文件系统持久化，通过回调 `on_job` 与 Agent 核心通信

**关键机制**（源码可见）：
- 三种调度方式：`at`（绝对时间一次性）、`every`（毫秒级间隔）、`cron`（标准 5 段 cron 表达式 + 时区）^[nanobot/cron/types.py]
- Action log 多实例协调：`action.jsonl` 记录跨实例的任务变更（add/update/del），每个 timer tick 时 `_merge_action()` 合并外部变更 ^[nanobot/cron/service.py:135-169]
- 自适应 timer：根据最早到期任务计算下次唤醒时间，无到期任务时最长休眠 5 分钟 ^[nanobot/cron/service.py:259-287]
- 一次性任务处理：`kind="at"` 的任务执行后根据 `delete_after_run` 标记决定删除还是禁用 ^[nanobot/cron/service.py:338-346]
- 保护系统任务：`payload.kind == "system_event"` 的任务不可通过 public API 删除 ^[nanobot/cron/service.py:419-442]

**源码证据**：
- 入口文件：nanobot/cron/service.py
- 核心类型/接口定义：`class CronService` ^[nanobot/cron/service.py:65]

**关联 Concept**：
- [[concepts/autonomous-scheduling]]
