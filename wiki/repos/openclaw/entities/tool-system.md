---
type: entity
repo: openclaw
slug: tool-system
problem: "如何管理 agent 可用工具的目录、策略和交付，支持多层 allow/deny 过滤并适配不同模型和渠道？"
generated: 2026-06-25
source_files:
  - src/agents/pi-tools.ts
  - src/agents/tool-catalog.ts
  - src/agents/tool-policy.ts
  - src/agents/bash-tools.ts
---

# Tool System

**代码位置**：`src/agents/pi-tools.ts`、`src/agents/tool-catalog.ts`、`src/agents/tool-policy.ts`
**这个模块解决什么问题**：
- 实现层：按需组装工具列表 → 通过多层策略管道过滤 → 按 model/provider 归一化 schema → 包装生命周期钩子 → 交付给 agent
- 问题层：如何管理 agent 可用工具的目录、策略和交付，支持多层 allow/deny 过滤并适配不同模型和渠道？
**对外暴露什么**：
- `createOpenClawCodingTools(options)` — 组装完整工具列表的主工厂函数 ^[src/agents/pi-tools.ts]
- `CoreToolDefinition` — 工具元数据（id, label, description, profiles, openclawGroup） ^[src/agents/tool-catalog.ts]
- `ToolPolicyLike` — 策略类型（`{ allow?: string[]; deny?: string[] }`） ^[src/agents/tool-policy.ts]
- `applyToolPolicyPipeline(params)` — 多层策略管道执行 ^[src/agents/tool-policy-pipeline.ts]
- `createExecTool(options)` — 进程执行工具 ^[src/agents/bash-tools.exec.ts]
- `createProcessTool(options)` — 交互式进程工具 ^[src/agents/bash-tools.process.ts]
- `AnyAgentTool` — 通用工具接口（参数泛型 + optional ownerOnly + displaySummary） ^[src/agents/pi-tools.ts]
**它和谁交互**：
- 依赖 [[entities/agent-runtime]]（工具被注入到 agent 执行循环）
- 依赖 [[entities/sandbox]]（沙箱上下文决定 exec/file 工具是否路由到容器）
- 依赖 [[entities/channel-system]]（渠道 agent 工具注册）
- 依赖 [[entities/model-configuration]]（provider 特定 schema 归一化）
- 依赖 [[entities/hooks-system]]（before-tool-call 钩子、循环检测）
- 被 [[entities/plugin-sdk]] 暴露的 `AnyAgentTool` 类型引用
**为什么它是可分离的**：工具组装是纯函数管道，输入配置+上下文→输出工具数组，无内部状态

**关键机制**（源码可见）：
- 工具组装管道（有序）：基础工具替换（read/write/edit）→ 添加 exec/process → 添加渠道工具 → 添加 openclaw 工具 → 策略过滤 → schema 归一化 → 钩子包装 → 超时包装 ^[src/agents/pi-tools.ts]
- 9 层策略管道（优先级）：profile → provider-profile → global → global-provider → agent → agent-provider → group → sandbox → subagent ^[src/agents/tool-policy-pipeline.ts]
- 工具目录分 4 个 profiles：minimal / coding / messaging / full ^[src/agents/tool-catalog.ts]
- 工具按领域分节：Files (read,write,edit,apply_patch), Runtime (exec,process), Web (web_search,web_fetch), Memory, Sessions, UI (browser,canvas), Messaging, Automation (cron,gateway), Nodes, Agents, Media ^[src/agents/tool-catalog.ts]
- Owner-only 授权：`cron`, `gateway`, `nodes`, `whatsapp_login` 等 control-plane 工具仅 owner 可用 ^[src/agents/tool-policy.ts]
- 内存刷新模式：trigger="memory" 时仅保留 read/write，write 包装为 append-only ^[src/agents/pi-tools.ts]

**源码证据**：
- 工具工厂：src/agents/pi-tools.ts
- 工具目录：src/agents/tool-catalog.ts
- 策略引擎：src/agents/tool-policy.ts
- 策略管道：src/agents/tool-policy-pipeline.ts
- 执行工具：src/agents/bash-tools.exec.ts
- 进程工具：src/agents/bash-tools.process.ts
- OpenClaw 工具：src/agents/openclaw-tools.ts

**关联 Concept**：
- [[concepts/memory-management-architecture]]
- [[concepts/tool-lifecycle-management]]
