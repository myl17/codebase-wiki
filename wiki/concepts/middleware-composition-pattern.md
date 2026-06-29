---
type: concept
concept: middleware-composition-pattern
problem: 如何将多个中间件按正确顺序组装成完整配置的 AI Agent 图
concerns: [顺序正确性与可靠性, 可替换性与扩展性, 子代理中间件继承]
repos: [nanobot, hermes-agent, openclaw, deepagents]
generated: 2026-06-28
---

# 中间件组合模式

## 核心问题

每个 Agent 框架都需要将多个横切关注点（文件系统工具、子代理委派、上下文压缩、记忆注入、人工审批）组合进 Agent 的执行管道中。这些关注点不是独立的——它们的顺序决定了哪些工具在何时可用、缓存是否有效、审批是否能拦截操作。如果中间件顺序错误，可能导致记忆在缓存之前注入（使缓存失效）或审批在工具执行之后才触发（失去安全保护）。

根本张力在于**可预测性与灵活性的权衡**。固定顺序（框架预定义中间件堆栈）提供了可预测性和正确性保证——每个中间件的位置是设计者有意选择的，理由可追溯。但用户无法自由调整顺序来满足特殊需求（如需要在审批中间件之前插入自定义日志中间件）。可配置顺序提供灵活性，但引入了排序错误的可能性——用户可能不知道"缓存中间件必须在记忆中间件之后"这类隐性约束。

第二个张力是**子代理中间件继承**。当主 Agent 委派任务给子代理时，子代理应该继承主 Agent 的哪些中间件？全部继承意味着子代理拥有与主代理相同的工具和约束，但可能导致递归委派和状态污染。选择性继承要求框架明确哪些中间件应该在子代理中重建、哪些应该排除、哪些可以自定义覆盖。

## 关切

- **顺序正确性与可靠性**：固定顺序 vs 可配置顺序。固定顺序保证正确性但限制灵活性；可配置顺序允许适配但引入隐性约束风险。
- **可替换性与扩展性**：用户能否替换框架内置中间件？替换后的协调责任在框架还是用户？自建中间件的插入点是否明确定义？
- **子代理中间件继承**：子代理继承全部中间件、选择性继承、还是独立配置？中间件复用 vs 上下文隔离的权衡。

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/context-builder]]
**解法**：一次性的 pipeline 阶段组装——在 Agent 启动时将 system sections、memory、skills、tools、MCP 等按固定顺序拼接为 context，运行时不再有中间件概念。
**实现**：`build_system_prompt()` 按固定顺序组装各部分（identity → agent_config → directive → personality → tool_prompt → user_context → memory → skills → mcp → examples → constraints）。tools 通过注册表注册，MCP 通过 `mcp_client_manager.start()` 异步连接。组装是一次性的——Agent 启动后 context 不再动态变化（除了 tool 调用历史）。 ^[nanobot/agent/context.py]
**权衡**：最简——组装是一次性的，运行时无中间件动态注入逻辑，调试简单。但无运行时动态性——不能在调用过程中根据上下文添加/移除工具，不能动态注入系统提示词片段。子代理使用独立 agent 实例，有自己的 context builder 调用，不继承父 context。

### hermes-agent
来源：[[repos/hermes-agent/entities/prompt-builder]]
**解法**：事件驱动的分层 prompt 构建——基础层 → 动态增量层，通过 plugin 钩子在不同时刻注入内容。
**实现**：`PromptBuilder` 分层构建系统提示词（基础指令 → identity → memory → skills → tools → constraints）。plugin 钩子系统在不同生命周期注入额外内容。工具管理通过 `tool_registry` 注册表+ `ConvenienceToolRegistry` 装饰器发现，MCP 通过连接管理器集成。分层结构允许每层独立控制是否注入当前会话。^[agent/prompt_builder.py]
**权衡**：分层构建 + plugin 钩子提供了比 nanobot 更多的动态性——不同层可在不同时机注入。但无中间件堆栈的概念——prompt 构建和工具管理是独立的两个维度，之间没有顺序约束。子代理继承父 agent 的部分配置（model、budget），但中间件/插件的继承规则不明确。

### openclaw
来源：[[repos/openclaw/entities/agent-runtime]]
**解法**：运行时 hook 管道——主循环中包含多个 hook 注入点，外部插件通过 hook 注册在特定阶段插入逻辑。
**实现**：Agent 主循环包含多个 hook 点（pre-model、post-model、pre-tool、post-tool、compaction 前后等）。内置 hook 按固定顺序执行。外部 hook 通过注册表注入。`ownsCompaction` 标志协调内建/插件压缩。工具通过 tool catalog 管理，按 category（Memory、Web、Message 等）分组。^[src/agents/pi-embedded-runner/run.ts]
**权衡**：hook 管道提供了比 nanobot 更多的运行时扩展点——外部插件可以在不修改核心代码的情况下注入行为。但 hook 的注册和排序机制较隐式——添加新 hook 时需要理解所有已有 hook 的依赖关系。工具目录按功能分组清晰但与 hook 管道的交互不透明。

### deepagents
来源：[[repos/deepagents/entities/agent-graph-assembly]]
**解法**：固定顺序中间件堆栈 + 用户中间件插入点 + 子代理中间件自动重建。
**实现**：`create_deep_agent()` 按以下固定顺序组装中间件：TodoListMiddleware → SkillsMiddleware(可选) → FilesystemMiddleware → SubAgentMiddleware → SummarizationMiddleware → PatchToolCallsMiddleware → AsyncSubAgentMiddleware(可选) → **用户中间件插入点** → AnthropicPromptCachingMiddleware → MemoryMiddleware(可选) → HumanInTheLoopMiddleware(可选)。用户中间件插入在基础堆栈（工具注入层）和尾部堆栈（缓存+记忆+审批层）之间——确保工具已可用、压缩已完成，但缓存和审批在用户逻辑之后。子代理的声明式 SubAgent 自动重建基础中间件堆栈（TodoListMiddleware → FilesystemMiddleware → SummarizationMiddleware → PatchToolCallsMiddleware → AnthropicPromptCachingMiddleware），然后附加自定义中间件。通用子代理自动注入：如果用户未提供名为 `general-purpose` 的子代理配置，自动创建一个具有完整中间件堆栈的默认通用子代理。系统提示词组合：自定义 prompt 前置 + BASE_AGENT_PROMPT 后置。^[deepagents/graph.py:108-427, 363-395, 330-360]
**权衡**：固定顺序 + 明确插入点提供了最强的可预测性——用户可以信任默认中间件堆栈的正确性，无需理解底层约束即可插入自定义中间件。子代理中间件自动重建确保隔离性（独立中间件实例）同时保持功能一致性。但固定顺序牺牲了灵活性——用户如果需要"在 FilesystemMiddleware 之前插入自定义工具"则无法实现。用户中间件插入点只有一个——如需在多个位置插入中间件，只能通过组件内部配置实现。尾部堆栈（缓存→记忆→审批）的顺序不可调整——这是有意为之，但限制了极端场景的自定义需求。

## 对比
| 框架 | 顺序正确性与可靠性 | 可替换性与扩展性 | 子代理中间件继承 |
|------|------|------|------|
| nanobot | 一次性静态组装，无动态注入 | 无替换机制——改代码 | 独立 agent 实例，不继承 |
| hermes-agent | 分层构建 + plugin 钩子注入 | plugin 钩子机制 | 继承 model/budget，中间件继承规则不明确 |
| openclaw | 固定 hook 点 + 注册表注入 | hook 注册表 + 压缩协调标志 | Gateway 调度，工具限制配置 |
| deepagents | 固定顺序中间件堆栈，插入点明确定义 | 用户中间件插入点 + backend 可替换 | 子代理自动重建基础堆栈，支持自定义中间件追加 |

## 演化记录
- 2026-06-28：初建，包含 nanobot, hermes-agent, openclaw, deepagents
