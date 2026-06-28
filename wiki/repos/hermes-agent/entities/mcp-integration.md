---
type: entity
repo: hermes-agent
slug: mcp-integration
problem: 如何将外部 MCP 服务器的工具动态集成到 Agent 工具注册表，支持 stdio/HTTP 传输、自动重连和工具刷新
generated: 2026-06-25
source_files:
  - tools/mcp_tool.py
  - tools/mcp_oauth.py
  - tools/osv_check.py
---

# MCP 集成

**代码位置**：`tools/mcp_tool.py`、`tools/mcp_oauth.py`
**这个模块解决什么问题**：
- 实现层：连接外部 MCP 服务器（stdio 或 HTTP/StreamableHTTP 传输）、发现工具并注册到中央 ToolRegistry、支持自动重连和动态工具刷新、OAuth 2.1 PKCE 授权和采样（server→client LLM 请求）
- 问题层：如何将外部 MCP 服务器的工具动态集成到 Agent 工具注册表，支持 stdio/HTTP 传输、自动重连和工具刷新
**对外暴露什么**：`register_mcp_servers()`（tools/mcp_tool.py:1959）、`discover_mcp_tools()`（tools/mcp_tool.py:2036）、`shutdown_mcp_servers()`（tools/mcp_tool.py:2191）、`get_mcp_status()`（tools/mcp_tool.py:2085）
**它和谁交互**：
- 依赖 [[entities/tool-registry]]（MCP 工具通过 `registry.register()` 注册到中央 registry，前缀格式 `server_name/tool_name`，toolset 为 `mcp-{server_name}`）
- 依赖 [[entities/config-system]]（从 `config.yaml` 的 `mcp_servers` 段读取服务器配置）
- 被 [[entities/agent-core]] 间接使用（通过 tool registry 分发）
**为什么它是可分离的**：独立模块，MCP 在专用后台线程的 event loop 上运行，工具注册通过标准 registry 接口，可插拔

**关键机制**（源码可见）：
- 双传输支持：stdio（command + args 启动子进程）和 HTTP/StreamableHTTP（url 连接），通过 `_run_stdio()` 和 `_run_http()` 分别处理 ^[tools/mcp_tool.py:890-966]
- 后台 event loop：专用 daemon 线程运行 `asyncio` event loop，每个 MCP 服务器作为长生命周期 Task 保持连接 ^[tools/mcp_tool.py:1170-1185]
- 自动重连：指数退避最多 5 次重试（`_MAX_RECONNECT_RETRIES = 5`），支持 `notifications/tools/list_changed` 动态刷新 ^[tools/mcp_tool.py:774-841]
- 工具注册：MCP 工具按 `server_name/tool_name` 格式注册，toolset 为 `mcp-{server_name}`，同时注册资源/提示工具（list_resources, read_resource, list_prompts, get_prompt）^[tools/mcp_tool.py:1351]
- 线程安全：`_servers` 和 `_mcp_loop` 通过 `threading.Lock` 保护，支持 Python 3.13+ free-threading ^[tools/mcp_tool.py:65-68]
- 采样支持：`SamplingHandler` 处理 MCP 服务器的 `sampling/createMessage` 请求，含滑动窗口速率限制（`max_rpm`，默认 10）和工具循环治理（`max_tool_rounds`，默认 5）^[tools/mcp_tool.py:403]
- 安全环境过滤：`_build_safe_env()` 过滤 stdio 子进程环境变量，仅透传安全变量 ^[tools/mcp_tool.py:194]
- 凭证脱敏：`_sanitize_error()` 在错误消息中脱敏 GitHub PAT、OpenAI key、Bearer token 等凭证 ^[tools/mcp_tool.py:175-213]
- OAuth 2.1 PKCE：`mcp_oauth` 模块支持 MCP 授权服务器的 PKCE 流程 ^[tools/mcp_oauth.py]
- 恶意包检测：`osv_check.check_package_for_malware()` 在启动 MCP 服务器前检查 OSV 恶意包数据库 ^[tools/mcp_tool.py:tools/osv_check.py]

**源码证据**：
- 入口文件：tools/mcp_tool.py
- 核心类：`class MCPServerTask` ^[tools/mcp_tool.py:774]、`class SamplingHandler` ^[tools/mcp_tool.py:403]

**关联 Concept**：
- [[concepts/tool-lifecycle-management]]
