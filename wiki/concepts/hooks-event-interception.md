---
type: concept
concept: hooks-event-interception
problem: 如何在 Agent 生命周期的关键节点（工具调用前后、会话启动、上下文压缩等）插入可编程的行为拦截
concerns: [事件覆盖完整性, 匹配器精度与过滤开销, 执行隔离与性能]
repos: [codex-main]
generated: 2026-06-28
---

# Hook 事件拦截

## 核心问题

任何 AI Agent 框架都需要在 Agent 行为的固定时间点提供扩展介入能力。用户或插件可能需要在工具调用前验证参数、在工具调用后修改结果、在会话启动时注入上下文——这些需求无法被静态的系统提示词或工具定义覆盖。Hook 系统回答的核心问题是：在 Agent 生命周期的哪些节点、以什么粒度、通过什么方式安全地允许外部代码介入。

不同框架在这三个维度上的选择构成了一个明确的设计空间：事件覆盖的完整性决定扩展能力的天花板，匹配器精度决定扩展的可用性和性能开销，执行隔离决定扩展的安全性。

## 关切

- **事件覆盖完整性**：Hook 事件覆盖的范围。覆盖越多节点，扩展能力越强，但 API 表面积越大、维护成本越高。代码式框架通常提供 5-15 个事件；配置式框架可能只提供 3-5 个。
- **匹配器精度**：Hook 触发时是否按工具名、触发源等维度过滤。高精度匹配减少无关执行但增加配置复杂度；无匹配器则简单但浪费计算资源。
- **执行隔离**：Hook 脚本的执行方式。外部命令执行（通用但启动开销大）；内置脚本引擎（高效但表达能力受限）；WebAssembly（安全但生态不成熟）。Hook 执行失败的处理策略也属于此关切。

## 各框架的解法

### codex-main

来源：[[repos/codex-main/entities/hook-system]]
**解法**：10 个命名生命周期事件 + 8 个支持匹配器过滤 + 外部命令执行引擎
**实现**：
- 10 个事件覆盖从 UserPromptSubmit 到 Stop 的完整生命周期：PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, SessionStart, UserPromptSubmit, SubagentStart, SubagentStop, Stop ^[codex-rs/hooks/src/lib.rs:19-30]
- 8 个事件（PreToolUse 到 SubagentStop）支持按工具名、压缩触发器等维度匹配器过滤；Stop 和 UserPromptSubmit 无匹配器 ^[codex-rs/hooks/src/lib.rs:37-46]
- Hook 通过外部命令执行，`engine` 模块管理 HookListEntry 优先级列表 ^[codex-rs/hooks/src/engine.rs:17]
- `HooksConfig` 从配置层解析钩子状态，支持多源合并 ^[codex-rs/hooks/src/config_rules.rs:13]
- 每个事件有独立的请求/响应类型组（PreToolUseRequest/Outcome, PostToolUseOutcome, PermissionRequestDecision 等） ^[codex-rs/hooks/src/lib.rs:48-67]
- 插件通过 `PluginHookDeclaration` 声明钩子，`PluginHookSource` 携带钩子文件路径和解析后配置 ^[codex-rs/plugin/src/lib.rs:61-69]
**权衡**：
- 满足事件覆盖完整性（10 个事件覆盖全生命周期），代价是 API 表面积大
- 满足匹配器精度（8 个事件支持精确匹配），代价是用户需要理解匹配器规则
- 外部命令执行满足通用性，代价是每次 Hook 触发有进程启动开销

### openclaw

来源：种子库 hooks-system（D 类演化信号）
**解法**：事件驱动扩展点 + 钩子发现-过滤-隔离
**实现**：OpenClaw 通过插件钩子系统提供扩展点，支持钩子发现、过滤和执行隔离
**权衡**：钩子粒度较 codex-main 粗（种子库中标记为"粒度不匹配"），但执行隔离更明确

### nanobot

来源：种子库中间件机制
**解法**：通过中间件组合模式在 Agent 处理管道中插入拦截逻辑
**实现**：中间件按顺序组成处理链，每个中间件可在处理前后插入逻辑
**权衡**：中间件模式灵活但与 Agent 循环耦合更紧，不如独立 Hook 系统解耦

## 对比

| 框架 | 事件覆盖完整性 | 匹配器精度 | 执行隔离 |
|------|---------------|-----------|---------|
| codex-main | 高（10 个命名事件） | 高（8 个事件支持匹配器，按工具名/触发源过滤） | 中（外部命令隔离，进程启动开销） |
| openclaw | 中（插件扩展点，粒度较粗） | 中（发现-过滤机制） | 高（明确的执行隔离） |
| nanobot | 低（中间件组合，非专用 Hook） | 低（中间件顺序，无事件级匹配） | 高（中间件在进程内执行） |

## 演化记录

- 2026-06-28：初建，包含 codex-main、openclaw、nanobot
