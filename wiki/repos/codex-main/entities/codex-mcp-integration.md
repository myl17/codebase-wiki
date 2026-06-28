---
type: entity
repo: codex-main
slug: codex-mcp-integration
problem: 如何管理 MCP 服务器的连接、目录和认证
generated: 2026-06-28
source_files:
  - codex-rs/codex-mcp/src/lib.rs
  - codex-rs/codex-mcp/src/connection_manager.rs
  - codex-rs/codex-mcp/src/catalog.rs
  - codex-rs/codex-mcp/src/mcp.rs
---

# Codex MCP Integration

**代码位置**：codex-rs/codex-mcp/
**这个模块解决什么问题**：
- 实现层：通过 `McpConnectionManager` 管理 MCP 服务器连接池 + `ResolvedMcpCatalog` 维护工具目录 + OAuth 登录支持，将外部 MCP 服务器集成为 Agent 可用的工具源
- 问题层：如何管理 MCP 服务器的连接、目录和认证
**对外暴露什么**：
- `McpConnectionManager`：MCP 连接管理器，管理所有 MCP 服务器的生命周期 ^[codex-rs/codex-mcp/src/connection_manager.rs]
- `ResolvedMcpCatalog`：已解析的 MCP 服务器目录 ^[codex-rs/codex-mcp/src/catalog.rs:19]
- `McpServerRegistration`：MCP 服务器注册信息 ^[codex-rs/codex-mcp/src/catalog.rs:17]
- `McpServerSource`：服务器来源（配置/插件/动态） ^[codex-rs/codex-mcp/src/catalog.rs:18]
- `McpCatalogBuilder`：目录构建器，从配置和插件中组装目录 ^[codex-rs/codex-mcp/src/catalog.rs:15]
- `ToolInfo`：MCP 工具信息 ^[codex-rs/codex-mcp/src/tools.rs:22]
- `McpRuntimeContext`：MCP 运行时上下文 ^[codex-rs/codex-mcp/src/runtime.rs:17]
- `SandboxState`：MCP 沙箱状态 ^[codex-rs/codex-mcp/src/runtime.rs:18]
- `ElicitationReviewer`：MCP 消息交互审核器 ^[codex-rs/codex-mcp/src/elicitation.rs:19]
- OAuth 认证支持：`McpOAuthLoginSupport`、`McpOAuthScopesSource`、`oauth_login_support` ^[codex-rs/codex-mcp/src/lib.rs:56-64]
- `McpPermissionPromptAutoApproveContext`：MCP 权限提示自动审批上下文 ^[codex-rs/codex-mcp/src/lib.rs:66]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 通过 MCP 连接获取和调用外部工具）
- 被 [[entities/tool-system]] 使用（MCP 工具解析器将 MCP 工具转为内部 ToolDefinition）
- 依赖 `rmcp-client` crate 实现底层 MCP 协议通信 ^[codex-rs/codex-mcp/src/rmcp_client.rs]
- 与 [[entities/plugin-system]] 配合（插件可以声明 MCP 服务器）^[codex-rs/codex-mcp/src/plugin_config.rs]
- 与 [[entities/config-management]] 配合（MCP 服务器配置来自 config 层）
**为什么它是可分离的**：独立的 crate，封装了 MCP 协议客户端侧的完整生命周期管理

**关键机制**（源码可见）：
- **多服务器连接池**：`McpConnectionManager` 管理多个 MCP 服务器的并发连接，支持断线重连和健康检查 ^[codex-rs/codex-mcp/src/connection_manager.rs]
- **目录构建与冲突解决**：`McpCatalogBuilder` 从配置、插件等多源收集服务器，`McpServerConflict` 处理工具名冲突 ^[codex-rs/codex-mcp/src/catalog.rs:15-19]
- **OAuth 认证流程**：`oauth_login_support` 和 `resolve_oauth_scopes` 管理 MCP 服务器的 OAuth 授权流程，`should_retry_without_scopes` 处理 scope 降级 ^[codex-rs/codex-mcp/src/lib.rs:56-64]
- **权限自动审批**：`mcp_permission_prompt_is_auto_approved` 和 `McpPermissionPromptAutoApproveContext` 实现 MCP 权限提示的自动审批决策 ^[codex-rs/codex-mcp/src/lib.rs:66-68]
- **沙箱状态传递**：`SandboxState` 通过 MCP 协议在客户端和服务器间传递沙箱策略 ^[codex-rs/codex-mcp/src/runtime.rs:18]

**源码证据**：
- 入口文件：codex-rs/codex-mcp/src/lib.rs
- 连接管理：codex-rs/codex-mcp/src/connection_manager.rs
- 目录构建：codex-rs/codex-mcp/src/catalog.rs:15-19
- MCP 配置：codex-rs/codex-mcp/src/mcp.rs
