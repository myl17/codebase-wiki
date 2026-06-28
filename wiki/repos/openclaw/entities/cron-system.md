---
type: entity
repo: openclaw
slug: cron-system
problem: "如何在 agent 上下文中调度定时任务，使 agent 能在指定时间自动触发对话？"
generated: 2026-06-25
source_files:
  - src/cron/
  - src/gateway/server-cron.ts
---

# Cron System

**代码位置**：`src/cron/`、`src/gateway/server-cron.ts`
**这个模块解决什么问题**：
- 实现层：cron 表达式 → 定时器 → 心跳系统提示 → agent 自动执行，支持多种时区和调度模式
- 问题层：如何在 agent 上下文中调度定时任务，使 agent 能在指定时间自动触发对话？
**对外暴露什么**：
- `buildGatewayCronService(opts)` — 构建 cron 服务 ^[src/gateway/server-cron.ts]
- `CronJob` 类型 — 定时任务定义（schedule, timezone, agent, message, sessionKey） ^[src/config/types.cron.ts]
- `cron` 工具 — agent 可用的 cron 管理工具 ^[src/agents/tool-catalog.ts]
- 心跳系统提示段：将下一个 cron 触发时间注入系统提示，使 agent 知道何时会被唤醒 ^[src/agents/system-prompt.ts]
**它和谁交互**：
- 依赖 [[entities/gateway]]（作为网关的一项服务运行）
- 依赖 [[entities/agent-runtime]]（触发 agent 执行）
- 依赖 [[entities/session-system]]（使用会话键定位目标会话）
- 依赖 [[entities/config-system]]（cron 配置段）
- 被 [[entities/tool-system]]（cron 工具暴露给 agent）
**为什么它是可分离的**：独立的定时调度模块，通过 cron 表达式和 agent 触发接口工作

**关键机制**（源码可见）：
- Cron 表达式解析：支持标准 cron 字段 + 时区 ^[src/gateway/server-cron.ts]
- Agent 触发：指定时间到达 → 自动向目标会话发送心跳消息 → agent 回复 ^[src/gateway/server-cron.ts]
- 心跳提示：`buildHeartbeatSection` 在系统提示中告知 agent 当前的 cron 调度状态 ^[src/agents/system-prompt.ts:122]
- `cron` 工具：agent 可通过工具管理自己的 cron 计划 ^[src/agents/tool-catalog.ts]
- 网关集成：`buildGatewayCronService` 创建 cron 服务实例，与网关生命周期绑定 ^[src/gateway/server-cron.ts]

**源码证据**：
- Cron 服务：src/gateway/server-cron.ts
- Cron 类型：src/config/types.cron.ts
- 心跳提示：src/agents/system-prompt.ts
- Cron CLI：src/cli/cron-cli.ts

**关联 Concept**：
- [[concepts/autonomous-scheduling]]
