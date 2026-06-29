---
type: entity
repo: nanobot
slug: api-server
problem: 如何为外部应用提供 OpenAI-compatible API，使它们能像调用 ChatGPT 一样调用 nanobot Agent
generated: 2026-06-25
source_files:
  - nanobot/api/server.py
---

# API Server

**代码位置**：`nanobot/api/server.py`
**这个模块解决什么问题**：
- 实现层：基于 aiohttp 的 HTTP 服务器，提供 `/v1/chat/completions` 和 `/v1/models` 端点，所有请求路由到固定会话（`api:default`），返回 OpenAI 兼容的 SSE 流式响应
- 问题层：如何为外部应用提供 OpenAI-compatible API，使它们能像调用 ChatGPT 一样调用 nanobot Agent
**对外暴露什么**：`APIServer` 类（nanobot/api/server.py）、`API_SESSION_KEY` 常量
**它和谁交互**：
- 依赖 [[entities/agent-loop]]（通过 `process_direct()` 路由 API 请求到 Agent 会话）
- 被 CLI 启动时创建
**为什么它是可分离的**：独立的 HTTP 服务器，通过固定 session key 与 Agent Loop 通信，可独立启停

**关键机制**（源码可见）：
- 固定会话路由：所有 API 请求使用 `API_SESSION_KEY = "api:default"` 和固定 `chat_id = "default"`，保证对话连续性 ^[nanobot/api/server.py:19-20]
- SSE 流式输出：支持 `stream: true` 参数，通过 HTTP chunked transfer 逐段发送 `data: {...}\n\n` 格式的 SSE 事件 ^[nanobot/api/server.py]
- 超时控制：`ApiConfig.timeout`（默认 120s）限制单次请求的最长等待时间 ^[nanobot/config/schema.py:142]

**源码证据**：
- 入口文件：nanobot/api/server.py
- 核心类型/接口定义：`class APIServer` ^[nanobot/api/server.py]
