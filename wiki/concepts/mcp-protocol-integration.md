---
type: concept
concept: mcp-protocol-integration
problem: 如何将 MCP（Model Context Protocol）集成到 Agent 框架中，既作为客户端消费外部工具资源，也作为服务端暴露自身能力
concerns: [协议兼容性深度, 多服务器连接与目录管理, OAuth 认证与安全]
repos: [codex-main, hermes-agent]
generated: 2026-06-28
---

# MCP 协议集成

## 核心问题

MCP（Model Context Protocol）正在成为 AI Agent 工具互操作的事实标准。一个 Agent 框架必须决定：以什么深度集成 MCP——是简单地包装 MCP 工具为内部格式，还是实现完整的连接管理、目录构建、OAuth 认证和冲突解决？更进一步：Agent 自身是否也应作为 MCP Server 向外部暴露工具？

这两个方向构成 MCP 集成的完整设计空间：Client 端（消费外部工具的深度）和 Server 端（暴露自身工具的广度）。框架在这两个维度的选择直接决定了其可接入的 MCP 生态范围。

## 关切

- **协议兼容性深度**：MCP 实现是薄封装（最小协议功能）还是深度集成（完整资源管理、Elicitation、Sandbox 状态传递）。薄封装开发快但功能受限；深度集成能力完整但维护成本高。
- **多服务器连接与目录管理**：同时连接多个 MCP 服务器时的连接池管理、工具目录聚合、重名冲突解决策略。集中式目录简化实现但丧失每个服务器的独立配置灵活性。
- **OAuth 认证与安全**：MCP 服务器的 OAuth 认证流程（scope 协商、降级重试、token 刷新）和权限自动审批。完整 OAuth 支持提高安全性但增加认证流程复杂度。

## 各框架的解法

### codex-main

来源：[[repos/codex-main/entities/codex-mcp-integration]]、[[repos/codex-main/entities/mcp-server]]
**解法**：Client 端深度集成（连接池 + 目录构建 + OAuth）+ Server 端暴露（MCP JSON-RPC 服务）
**实现**：
- Client 端：`McpConnectionManager` 管理多 MCP 服务器连接池，支持断线重连 ^[codex-rs/codex-mcp/src/connection_manager.rs]
- 目录构建：`McpCatalogBuilder` 从配置、插件等多源收集服务器，`McpServerConflict` 处理工具名冲突 ^[codex-rs/codex-mcp/src/catalog.rs:15-19]
- OAuth 认证：`oauth_login_support` 和 `resolve_oauth_scopes` 管理完整的 OAuth 流程，`should_retry_without_scopes` 支持 scope 降级重试 ^[codex-rs/codex-mcp/src/lib.rs:56-64]
- 权限审批：`mcp_permission_prompt_is_auto_approved` 和 `McpPermissionPromptAutoApproveContext` 实现 MCP 权限自动审批 ^[codex-rs/codex-mcp/src/lib.rs:66-68]
- 沙箱状态传递：`SandboxState` 通过 MCP 协议在客户端和服务器间传递沙箱策略 ^[codex-rs/codex-mcp/src/runtime.rs:18]
- Server 端：基于 `rmcp` crate 实现标准 MCP JSON-RPC 服务端 ^[codex-rs/mcp-server/src/lib.rs:57-59]
- `MessageProcessor` 处理 JSON-RPC 请求路由 ^[codex-rs/mcp-server/src/message_processor.rs:38]
- `codex_tool_runner` 将 MCP 工具调用路由到 Codex 内部工具执行管线 ^[codex-rs/mcp-server/src/codex_tool_runner.rs]
- 审批集成：`exec_approval` 和 `patch_approval` 模块将 MCP Elicitation 机制用于执行和补丁审批 ^[codex-rs/mcp-server/src/exec_approval.rs]
**权衡**：
- 深度集成满足协议兼容性（完整 OAuth + 冲突解决 + 沙箱状态），代价是实现复杂度高
- 满足多服务器管理（连接池 + 目录构建），代价是增加了框架启动时的连接初始化开销
- Server 模式扩展了 MCP 生态影响力，代价是维护独立的 MCP Server 进程

### hermes-agent

来源：[[repos/hermes-agent/entities/mcp-integration]]
**解法**：MCP 工具通过 ToolRegistry 的统一注册接口接入，支持 stdio/HTTP 双传输、自动重连和 OAuth 2.1 PKCE
**实现**：
- `register_mcp_servers()` 连接配置的 MCP 服务器，发现工具并注册到中央 ToolRegistry ^[tools/mcp_tool.py:1959]
- `discover_mcp_tools()` 动态发现 MCP 工具，前缀格式 `server_name/tool_name`，toolset 为 `mcp-{server_name}` ^[tools/mcp_tool.py:2036]
- `shutdown_mcp_servers()` 优雅关闭所有 MCP 连接 ^[tools/mcp_tool.py:2191]
- 双传输支持：stdio（command + args 启动子进程）和 HTTP/StreamableHTTP（url 连接） ^[tools/mcp_tool.py:890-966]
- 专用后台 daemon 线程运行 `asyncio` event loop，每个 MCP 服务器作为长生命周期 Task ^[tools/mcp_tool.py:1170-1185]
- 自动重连：指数退避最多 5 次重试，支持 `notifications/tools/list_changed` 动态刷新 ^[tools/mcp_tool.py:774-841]
- OAuth 2.1 PKCE：`mcp_oauth` 模块支持 MCP 授权服务器的 PKCE 流程 ^[tools/mcp_oauth.py]
- 恶意包检测：`osv_check.check_package_for_malware()` 启动前检查 OSV 数据库 ^[tools/mcp_tool.py:tools/osv_check.py]
**权衡**：集成简单（MCP 只是 tool-registry 的一个工具源），但缺少独立连接池管理、目录构建和冲突解决；OAuth 支持有 PKCE 但无 scope 降级重试策略

## 对比

| 框架 | 协议兼容性深度 | 多服务器管理 | OAuth 认证 | Server 模式 |
|------|---------------|-------------|-----------|------------|
| codex-main | 深（完整 MCP JSON-RPC + 沙箱状态 + Elicitation） | 高（连接池 + 目录构建 + 冲突解决） | 完整（scope 协商 + 降级重试 + token 刷新） | 是（独立 MCP Server 进程） |
| hermes-agent | 浅（MCP 工具转为内部格式） | 低（作为工具源接入） | 基础 | 否 |

## 演化记录

- 2026-06-28：初建，包含 codex-main、hermes-agent
