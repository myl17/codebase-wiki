---
type: entity
repo: codex-main
slug: mcp-server
problem: 如何将 Codex Agent 工具暴露为 MCP 兼容的 JSON-RPC 服务
generated: 2026-06-28
source_files:
  - codex-rs/mcp-server/src/lib.rs
  - codex-rs/mcp-server/src/message_processor.rs
  - codex-rs/mcp-server/src/codex_tool_runner.rs
---

# MCP Server

**代码位置**：codex-rs/mcp-server/
**这个模块解决什么问题**：
- 实现层：通过实现 MCP 协议的 JSON-RPC 服务端，将 Codex 的工具和执行能力暴露为 MCP 兼容接口，允许外部 MCP 客户端调用 Codex 的工具
- 问题层：如何将 Codex Agent 工具暴露为 MCP 兼容的 JSON-RPC 服务
**对外暴露什么**：
- `run_main`：MCP Server 主入口函数 ^[codex-rs/mcp-server/src/lib.rs:59]
- `MessageProcessor`：JSON-RPC 消息处理核心 ^[codex-rs/mcp-server/src/message_processor.rs:38]
- `CodexToolCallParam`：Codex 工具调用参数 ^[codex-rs/mcp-server/src/codex_tool_config.rs:43]
- `CodexToolCallReplyParam`：Codex 工具调用回复参数 ^[codex-rs/mcp-server/src/codex_tool_config.rs:44]
- `ExecApprovalElicitRequestParams`：执行审批请求参数 ^[codex-rs/mcp-server/src/exec_approval.rs:45]
- `ExecApprovalResponse`：执行审批响应 ^[codex-rs/mcp-server/src/exec_approval.rs:46]
- `PatchApprovalElicitRequestParams`：补丁审批请求参数 ^[codex-rs/mcp-server/src/patch_approval.rs:47]
- `PatchApprovalResponse`：补丁审批响应 ^[codex-rs/mcp-server/src/patch_approval.rs:48]
- MCP 频道容量常量 `CHANNEL_CAPACITY = 128` ^[codex-rs/mcp-server/src/lib.rs:53]
**它和谁交互**：
- 使用与 [[entities/core-agent-loop]] 相同的核心能力（ConfigBuilder、EnvironmentManager 等） ^[codex-rs/mcp-server/src/lib.rs:9-14]
- 使用 [[entities/exec-server]] 的 EnvironmentManager ^[codex-rs/mcp-server/src/lib.rs:11]
- 依赖 `rmcp` 外部 crate 实现 MCP JSON-RPC 协议 ^[codex-rs/mcp-server/Cargo.toml]
**为什么它是可分离的**：独立的二进制/库 crate，MCP 标准协议接口，可以作为独立的 MCP Server 进程运行

**关键机制**（源码可见）：
- **标准 MCP 协议**：基于 `rmcp` crate 的 JSON-RPC 消息格式（`JsonRpcMessage<ClientRequest, Value, ClientNotification>`）实现标准 MCP 通信 ^[codex-rs/mcp-server/src/lib.rs:57]
- **异步消息处理**：`MessageProcessor` 使用有界通道（容量 128）处理并发的 JSON-RPC 请求和通知 ^[codex-rs/mcp-server/src/lib.rs:53]
- **工具调用路由**：`codex_tool_runner` 模块将 MCP 的工具调用请求路由到 Codex 的工具执行管线 ^[codex-rs/mcp-server/src/codex_tool_runner.rs]
- **审批集成**：`exec_approval` 和 `patch_approval` 模块将 MCP 的 Elicitation 机制用于执行和补丁的审批流程 ^[codex-rs/mcp-server/src/exec_approval.rs]

**源码证据**：
- 入口文件：codex-rs/mcp-server/src/lib.rs
- 消息处理：codex-rs/mcp-server/src/message_processor.rs:38
- 工具执行：codex-rs/mcp-server/src/codex_tool_runner.rs
