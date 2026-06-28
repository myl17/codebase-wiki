---
type: concept
concept: tool-lifecycle-management
problem: 如何管理 Agent 工具的注册、发现、策略过滤和生命周期
concerns: [工具发现机制, 策略复杂度收益/成本比, 工具安全性]
repos: [nanobot, hermes-agent, openclaw, codex-main]
generated: 2026-06-25
---

# 工具生命周期管理

## 核心问题

Agent 的工具集不是静态的——它随 MCP 服务器的动态加入而增长、随策略规则按场景裁剪、随插件系统的扩展而变化。因此工具管理必须回答三个连续的问题：**工具从哪里来（发现）、谁可以用什么（策略）、如何防止冲突和注入（安全）。**

工具发现的本质是"自动化程度 vs 可审计性"的取舍。最简单的方案是手工注册（每个工具显式 `register()`），最激进的方案是 AST 扫描（解析源码找注册调用，连 import 都不需要）。自动化越高，维护负担越低（加工具只需新建文件），但隐式行为越多（你不知道哪些文件会被发现）。

策略过滤的核心张力是"粒度的收益是否超过复杂度的成本"。单层 allow/deny 列表易于理解和调试，但无法处理"渠道 A 允许 process 工具但渠道 B 禁止"的场景。多层管道（profile → global → agent → channel → sandbox → subagent）可以精确控制，但策略冲突的调试、合并语义的定义、优先级规则的沟通都随层数指数增长。openclaw 的 9 层管道是极端案例——它的收益是"为每个部署场景精确裁剪工具集"，成本是"维护者必须理解 9 级优先级才能排查工具缺失问题"。

工具安全是一个被低估的关切。工具名冲突可能导致插件工具覆盖内建工具（shadow attack）；MCP 工具在独立进程中运行，可能注入恶意 schema；control-plane 工具（如 cron、gateway）如果对非 owner 暴露，可能导致权限提升。

## 关切

- **工具发现机制**：手工注册、AST 扫描还是配置驱动？MCP 工具的发现和动态刷新如何处理？发现失败时的降级路径？
- **策略复杂度收益/成本比**：过滤层数、合并语义、调试工具缺失的难度。9 层管道是否过度工程化？
- **工具安全性**：工具名冲突保护、MCP 工具 schema 信任、control-plane 工具的 owner-only 授权、参数注入防护。

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/tool-registry]]
**解法**：ToolRegistry 单例 + 手工注册 + 稳定排序 + concurrency_safe 分组。
**实现**：Tool 基类定义工具接口（name/description/parameters schema/execute/cast_params/validate_params）。ToolRegistry 管理注册和查找，`get_definitions()` 按内建工具字母序 → MCP 工具字母序稳定排序以优化 prompt cache。`prepare_call()` 做参数类型转换 + 验证，返回 (tool, params, error) 三元组。concurrency_safe 分组：safe 工具并行执行，unsafe 串行。^[nanobot/agent/tools/registry.py:8-83; nanobot/agent/tools/base.py]
**权衡**：最简洁——手工注册透明可控，稳定排序对 prompt cache 友好。但无自动发现（新工具需显式注册），无策略过滤（所有注册工具对所有场景可用），安全仅依赖 concurrency_safe 分组，无工具名冲突保护。

### hermes-agent
来源：[[repos/hermes-agent/entities/tool-registry]]、[[repos/hermes-agent/entities/mcp-integration]]
**解法**：ToolRegistry 单例 + AST 扫描自动发现 + 工具遮蔽保护 + MCP 动态刷新 + 工具集组合系统。
**实现**：`discover_builtin_tools()` 扫描 `tools/*.py`，AST 检测包含 `registry.register()` 的文件并导入触发自注册。工具遮蔽保护：非 MCP 工具名冲突时拒绝注册（REJECTED），MCP-to-MCP 允许覆盖。MCP 集成：双传输（stdio + HTTP/StreamableHTTP），后台 daemon 线程运行 event loop，自动重连（指数退避最多 5 次），支持 `notifications/tools/list_changed` 动态刷新。工具集组合：`resolve_toolset()` 递归解析 includes，支持 all/* 通配符和菱形依赖去重。参数类型纠正：`coerce_tool_args()` 根据 JSON Schema 纠正 LLM 类型错误。^[tools/registry.py:41-74, 190-213, 112-115; toolsets.py:447-498; model_tools.py:334; tools/mcp_tool.py:774-841, 890-966, 1170-1185]
**权衡**：自动发现最成熟——AST 扫描实现隐式注册，新工具只需新建 .py 文件。工具遮蔽保护是唯一有冲突防护的方案。但策略过滤弱——工具集组合是静态配置（非管道式策略），MCP schema 信任无校验。

### openclaw
来源：[[repos/openclaw/entities/tool-system]]
**解法**：8 步工具组装管道 + 9 层策略管道 + 4 工具 profiles + owner-only 控制面授权。
**实现**：组装管道有序执行：基础工具替换 → 添加 exec/process → 添加渠道工具 → 添加 openclaw 工具 → 策略过滤 → schema 归一化 → 钩子包装 → 超时包装。策略管道 9 层优先级：profile → provider-profile → global → global-provider → agent → agent-provider → group → sandbox → subagent。4 个工具 profiles（minimal/coding/messaging/full）定义不同场景的默认工具集。Owner-only 授权：cron/gateway/nodes/whatsapp_login 等 control-plane 工具仅 owner 可用。Memory refresh mode 限制为仅 read/write。^[src/agents/pi-tools.ts; src/agents/tool-policy-pipeline.ts; src/agents/tool-catalog.ts; src/agents/tool-policy.ts]
**权衡**：策略粒度最细——9 层管道 + 4 profiles 可实现任意场景的精确工具裁剪。但复杂度最高——策略合并语义和优先级调试不透明；自动发现弱（工具在 pi-tools.ts 中显式组装）；工具遮蔽无保护；无 MCP 工具发现机制。

### codex-main

来源：[[repos/codex-main/entities/tool-system]]
**解法**：`ToolDefinition` 统一元数据 + 多源工具解析（内置/MCP/动态）+ `TurnItemEmitter` 流式输出 + Responses API 适配。
**实现**：
- `ToolDefinition` 是所有工具的统一定义格式（名称、描述、输入/输出 JSON Schema），`defer_loading` 支持延迟加载 ^[codex-rs/tools/src/tool_definition.rs:6-13]
- 多源解析：内置工具（tool_definition）、MCP 工具（`parse_mcp_tool` 转为内部格式）、动态工具（`parse_dynamic_tool`） ^[codex-rs/tools/src/mcp_tool.rs:41]
- `ResponsesApiTool` 和 `FreeformTool` 将内部工具定义适配为 OpenAI Responses API 格式，`LoadableToolSpec` 支持延迟发送 ^[codex-rs/tools/src/responses_api.rs:53-64]
- `TurnItemEmitter` trait 支持工具执行过程中流式发射中间结果，`NoopTurnItemEmitter` 提供空实现降级 ^[codex-rs/tools/src/tool_call.rs:66-72]
- `JsonSchema` 类型支持 `AdditionalProperties` 控制，`parse_tool_input_schema` 处理 schema 的压缩与展开 ^[codex-rs/tools/src/json_schema.rs:35-40]
- `ToolConfig` 配置 Shell 后端类型、用户 Shell 类型、ZshForkConfig 等执行参数 ^[codex-rs/tools/src/tool_config.rs:72-80]
**权衡**：`ToolDefinition` 的统一格式设计使 MCP/内置/动态三种工具源通过同一解析管道接入，实现简洁。但无自动发现机制（工具在组装管道中显式列出），无策略过滤（工具定义和策略检查分离到 execpolicy 层）。流式执行反馈通过 trait 实现，调用了方无需感知底层是流式还是批量。

## 对比
| 框架 | 工具发现机制 | 策略复杂度收益/成本比 | 工具安全性 |
|------|------|------|------|
| nanobot | 手工注册，无自动发现 | 无策略过滤，所有工具全局可用 | 仅 concurrency_safe 分组 |
| hermes-agent | AST 扫描自动发现 + MCP 动态刷新 | 静态工具集组合，非管道式过滤 | 工具遮蔽保护 + MCP 凭证脱敏 |
| openclaw | 显式组装管道，无自动发现 | 9 层管道 + 4 profiles，粒度最细 | Owner-only 授权 + 超时包装 |
| codex-main | ToolDefinition 统一元数据 + MCP/内置/动态三源解析；无自动发现 | 无策略过滤层（策略在 execpolicy 层单独处理） | MCP tool result output schema 校验 + JsonSchema 控制 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 codex-main（ToolDefinition 统一元数据 + 三源解析 + Responses API 适配）
