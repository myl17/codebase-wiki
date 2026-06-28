---
type: entity
repo: codex-main
slug: tool-system
problem: 如何定义、发现和执行 Agent 工具
generated: 2026-06-28
source_files:
  - codex-rs/tools/src/lib.rs
  - codex-rs/tools/src/tool_definition.rs
  - codex-rs/tools/src/tool_discovery.rs
  - codex-rs/tools/src/tool_executor.rs
---

# Tool System

**代码位置**：codex-rs/tools/
**这个模块解决什么问题**：
- 实现层：通过 `ToolDefinition` 统一工具元数据 + `ToolCall` 抽象 + MCP 工具解析 + Responses API 适配，将不同来源的工具（内置、MCP、动态生成）统一为 Agent 可调用的接口
- 问题层：如何定义、发现和执行 Agent 工具
**对外暴露什么**：
- `ToolDefinition`：工具元数据（名称、描述、输入/输出 JSON Schema） ^[codex-rs/tools/src/tool_definition.rs:6-13]
- `ToolCall`：工具调用抽象 ^[codex-rs/tools/src/tool_call.rs:68]
- `ToolEnvironment`：工具执行环境上下文 ^[codex-rs/tools/src/tool_call.rs:69]
- `ToolConfig`：工具配置（Shell 后端、用户 Shell 类型等） ^[codex-rs/tools/src/tool_config.rs:72-80]
- `ResponsesApiTool`：OpenAI Responses API 格式的工具定义 ^[codex-rs/tools/src/responses_api.rs:55-58]
- `FreeformTool`：自由格式工具定义 ^[codex-rs/tools/src/responses_api.rs:53]
- `JsonSchema`：工具输入/输出 JSON Schema 类型 ^[codex-rs/tools/src/json_schema.rs:35-38]
- `TurnItemEmitter`：回合项目发射器 trait（工具执行结果流式输出） ^[codex-rs/tools/src/tool_call.rs:71]
- MCP 工具解析：`parse_mcp_tool` 将 MCP 工具转为内部表示 ^[codex-rs/tools/src/mcp_tool.rs:41]
- 工具搜索：`tool_search` 模块支持模糊搜索工具 ^[codex-rs/tools/src/tool_search.rs]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 通过工具系统执行 LLM 返回的 tool calls）
- 依赖 [[entities/codex-mcp-integration]]（解析和适配 MCP 工具）
- 与 [[entities/exec-server]] 配合（Shell 命令类工具委托给 exec-server 执行）
- 与 [[entities/hook-system]] 配合（工具使用前/后触发钩子）
**为什么它是可分离的**：独立的 Rust crate，可以脱离 `codex-core` 使用，定义了共享工具定义和 Responses API 原语

**关键机制**（源码可见）：
- **多源工具统一**：`ToolDefinition` 是统一的工具描述格式，内置工具、MCP 工具、动态工具均通过对应的解析器转换为该格式 ^[codex-rs/tools/src/tool_definition.rs:6-13]
- **Responses API 适配**：`ResponsesApiTool` 和 `FreeformTool` 将内部工具定义转换为 OpenAI Responses API 格式，支持 `LoadableToolSpec` 延迟加载 ^[codex-rs/tools/src/responses_api.rs:53-64]
- **流式执行结果**：`TurnItemEmitter` trait 支持工具执行时流式输出中间结果（如 shell 命令的 stdout/stderr） ^[codex-rs/tools/src/tool_call.rs:69-71]
- **工具搜索与发现**：`tool_discovery` 和 `tool_search` 模块支持从注册表查找工具、模糊匹配工具名 ^[codex-rs/tools/src/tool_discovery.rs]
- **Schema 演化和校验**：`JsonSchema` 类型支持 `AdditionalProperties` 控制，`parse_tool_input_schema` 处理输入 schema 的压缩与展开 ^[codex-rs/tools/src/json_schema.rs:35-40]

**源码证据**：
- 入口文件：codex-rs/tools/src/lib.rs
- 工具定义：codex-rs/tools/src/tool_definition.rs:6-13
- 工具调用：codex-rs/tools/src/tool_call.rs:68-71
