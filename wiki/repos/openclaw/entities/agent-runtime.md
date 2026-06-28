---
type: entity
repo: openclaw
slug: agent-runtime
problem: "如何实现一个与模型 provider 无关、支持流式输出、自动压缩和故障切换的 AI agent 执行循环？"
generated: 2026-06-25
source_files:
  - src/agents/
---

# Agent Runtime (PI Embedded)

**代码位置**：`src/agents/`
**这个模块解决什么问题**：
- 实现层：通过 `runEmbeddedPiAgent` 函数实现完整的 agent 执行循环：模型选择→认证→系统提示构建→工具组装→流式订阅→错误处理→压缩→故障切换
- 问题层：如何实现一个与模型 provider 无关、支持流式输出、自动压缩和故障切换的 AI agent 执行循环？
**对外暴露什么**：
- `runEmbeddedPiAgent(params)` — 执行 agent 主循环 ^[src/agents/pi-embedded-runner/run.ts:162]
- `queueEmbeddedPiMessage(sessionId, text)` — 向运行中的 agent 注入消息 ^[src/agents/pi-embedded-runner/runs.ts:99]
- `abortEmbeddedPiRun(sessionId)` — 终止运行 ^[src/agents/pi-embedded-runner/runs.ts]
- `compactEmbeddedPiSession(params)` — 触发会话压缩 ^[src/agents/pi-embedded-runner/compact.queued.ts]
- `subscribeEmbeddedPiSession(params)` — 流式订阅事件处理 ^[src/agents/pi-embedded-subscribe.ts:69]
- `buildAgentSystemPrompt(params)` — 构建完整系统提示 ^[src/agents/system-prompt.ts:380]
- `runWithModelFallback(params)` — 模型故障切换链 ^[src/agents/model-fallback.ts:626]
**它和谁交互**：
- 依赖 [[entities/model-configuration]]（provider/模型选择、认证）
- 依赖 [[entities/tool-system]]（工具组装、策略过滤）
- 依赖 [[entities/session-system]]（会话历史、转录）
- 依赖 [[entities/sandbox]]（沙箱上下文）
- 依赖 [[entities/skills]]（技能提示注入）
- 依赖 [[entities/hooks-system]]（生命周期钩子）
- 被 [[entities/gateway]] 调度执行
- 被 [[entities/subagent-system]] 孵化子 agent
**为什么它是可分离的**：完整的 agent 生命周期（初始化→循环→清理）封装在 `runEmbeddedPiAgent` 中，通过参数注入所有外部依赖

**关键机制**（源码可见）：
- Agent 主循环：`while(true)` 内完成模型调用→流式订阅→结果分析→错误处理→压缩重试→计划检测→不完整回合处理 ^[src/agents/pi-embedded-runner/run.ts:569]
- 流式订阅状态机：追踪 assistantTexts、toolMetas、delta buffer、thinking tags、重复检测、压缩协调 ^[src/agents/pi-embedded-subscribe.ts:74-127]
- 系统提示组装：27 个按序排列的节（Identity→Tooling→Skills→Memory→Workspace→Sandbox→Voice→Context Files→Runtime） ^[src/agents/system-prompt.ts:631-920]
- Lane 并发控制：先加入 session lane，再加入 global lane，防止并发访问 ^[src/agents/pi-embedded-runner/run.ts:176-210]
- 压缩协调：高 token 用量超时触发自动压缩，最多 3 次重试 ^[src/agents/pi-embedded-runner/run.ts:817-933]
- 运行状态全局单例：`Symbol.for("openclaw.embeddedRunState")` 跨模块边界追踪所有活跃运行 ^[src/agents/pi-embedded-runner/runs.ts]

**源码证据**：
- 入口文件：src/agents/pi-embedded.ts
- 运行器实现：src/agents/pi-embedded-runner/run.ts
- 流式订阅：src/agents/pi-embedded-subscribe.ts
- 压缩逻辑：src/agents/pi-embedded-runner/compact.queued.ts
- 运行状态管理：src/agents/pi-embedded-runner/runs.ts
- 核心类型：EmbeddedPiRunResult、EmbeddedPiRunMeta（src/agents/pi-embedded-runner/types.ts）

**关联 Concept**：
- [[concepts/system-prompt-assembly]]
- [[concepts/agent-loop-orchestration]]
- [[concepts/context-compression-strategy]]
