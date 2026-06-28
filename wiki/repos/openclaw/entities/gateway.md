---
type: entity
repo: openclaw
slug: gateway
problem: "如何在单进程中同时服务 HTTP REST、WebSocket 双向通信、控制界面和 OpenAI 兼容 API？"
generated: 2026-06-25
source_files:
  - src/gateway/
---

# Gateway 服务器

**代码位置**：`src/gateway/`
**这个模块解决什么问题**：
- 实现层：通过单端口 HTTP 服务器同时承载 JSON-over-WebSocket 控制协议、REST API、OpenAI 兼容端点和控制界面 SPA
- 问题层：如何在单进程中同时服务 HTTP REST、WebSocket 双向通信、控制界面和 OpenAI 兼容 API？
**对外暴露什么**：
- `startGatewayServer(port, opts)` — 启动网关主入口 ^[src/gateway/server.ts:7-12]
- `GatewayServer` 类型（close 方法）^[src/gateway/server.impl.ts:142-144]
- `GatewayServerOptions` — 绑定地址、认证、Tailscale、控制界面等配置 ^[src/gateway/server.impl.ts:146-199]
**它和谁交互**：
- 依赖 [[entities/plugin-system]]（插件注册表、引导）
- 依赖 [[entities/agent-runtime]]（agent 会话执行）
- 依赖 [[entities/session-system]]（会话存储、转录）
- 依赖 [[entities/channel-system]]（渠道管理、健康监控）
- 依赖 [[entities/cron-system]]（定时任务调度）
- 依赖 [[entities/config-system]]（配置加载、运行时覆盖）
- 依赖 [[entities/hooks-system]]（webhook 处理、生命周期事件）
- 被 [[entities/cli-system]] 调用（`openclaw gateway` 命令）
- 被 [[entities/daemon]] 管理（launchd/systemd 生命周期）
**为什么它是可分离的**：独立模块，通过明确的 `GatewayServer` 接口对外暴露，可独立启动/关闭，所有子系统通过 DI 模式注入

**关键机制**（源码可见）：
- JSON-over-WebSocket 协议：三帧类型（req/res/event），TypeBox schema + AJV 验证 ^[src/gateway/protocol/schema/frames.ts:139-174]
- HTTP 请求分阶段管道：hooks → OpenAI 兼容 → 工具调用 → 会话 → 画布 → 插件 → 控制界面 → 探针 ^[src/gateway/server-http.ts:873]
- 方法分发引擎：~30 个领域（agents, sessions, config, channels, nodes, cron, skills, tools 等），基于角色的授权 ^[src/gateway/server-methods.ts:69-100]
- 启动生命周期：早期运行时（MCP 回环、发现、维护）→ 配置加载 → 插件引导 → HTTP/WS 启动 → 后期附加（模型预热、ACP、Tailscale） ^[src/gateway/server-startup.ts:1-6]
- 客户端认证：支持 token/password/trusted-proxy/none 四种模式，含速率限制 ^[src/gateway/auth.ts]
- 协议版本管理：`PROTOCOL_VERSION = 3`，向前兼容的增量演化 ^[src/gateway/protocol/schema/protocol-schemas.ts:367]

**源码证据**：
- 入口文件：src/gateway/server.ts
- 核心实现：src/gateway/server.impl.ts（~250 行主要引导逻辑）
- HTTP/WS 传输层：src/gateway/server-http.ts
- 方法分发：src/gateway/server-methods.ts
- 协议定义：src/gateway/protocol/schema/
- 核心类型：GatewayServer（line 142）、GatewayServerOptions（line 146）、startGatewayServer（line 201）
