---
type: entity
repo: hermes-agent
slug: web-server
problem: 如何提供一个 Web 仪表板来远程管理 Agent 的配置、会话、定时任务和查看使用分析
generated: 2026-06-25
source_files:
  - hermes_cli/web_server.py
---

# Web 服务器

**代码位置**：`hermes_cli/web_server.py`
**这个模块解决什么问题**：
- 实现层：FastAPI 应用 + Vite/React SPA 前端，通过 bearer token 认证提供 30+ API 路由（配置读写、会话管理、cron 管理、技能管理、日志查看、Provider OAuth 流），严格限制本地访问
- 问题层：如何提供一个 Web 仪表板来远程管理 Agent 的配置、会话、定时任务和查看使用分析
**对外暴露什么**：FastAPI `app` 对象（hermes_cli/web_server.py:64）、`mount_spa()` 静态前端挂载（line 2025）
**它和谁交互**：
- 依赖 [[entities/config-system]]（`/api/config` 读写配置）
- 依赖 [[entities/state-database]]（`/api/sessions/*` 管理会话和消息）
- 依赖 [[entities/cron-scheduler]]（`/api/cron/*` 管理定时任务）
- 依赖 [[entities/skills-system]]（`/api/skills` 列出和切换技能）
- 依赖 [[entities/provider-registry]]（`/api/providers/oauth/*` OAuth 流程）
- 依赖 [[entities/tool-registry]]（`/api/tools/toolsets` 可用工具集列表）
- 依赖 [[entities/logging-system]]（`/api/logs` 查看 agent 日志）
- 被 [[entities/cli-system]] 调用（`hermes dashboard` 启动）
- 被 [[entities/gateway-runner]] 调用（gateway 内嵌 API server adapter）
**为什么它是可分离的**：独立 FastAPI 应用，通过 REST API 与后端组件交互，可替换前端 SPA

**关键机制**（源码可见）：
- Bearer token 认证：每次启动生成随机 `_SESSION_TOKEN`，注入前端 SPA 的 `window.__HERMES_SESSION_TOKEN__` 全局变量；API 中间件验证 `Authorization: Bearer <token>` 头 ^[hermes_cli/web_server.py:71-135]
- 公开端点白名单：`/api/status`、`/api/config/defaults`、`/api/config/schema`、`/api/model/info` 无需认证 ^[hermes_cli/web_server.py:94]
- 严格 CORS：仅允许 `localhost` 和 `127.0.0.1`，无通配符 ^[hermes_cli/web_server.py:82]
- 密钥揭示保护：`/api/env/reveal` 需要额外 `reveal_token` 参数（非 session token），且速率限制 ^[hermes_cli/web_server.py:765]
- 30+ API 路由：配置 CRUD（`/api/config`、`/api/env`）、会话管理（`/api/sessions`、搜索、消息、删除）、cron 管理（`/api/cron/jobs` 含 pause/resume/trigger）、Provider OAuth（start/submit/delete）、工具集（`/api/tools/toolsets`）、日志（`/api/logs`）、使用分析（`/api/analytics/usage`）^[hermes_cli/web_server.py:363-1977]
- 静态 SPA 挂载：`mount_spa()` 构建 Vite/React 前端 `web_dist/`，fallback 到 `index.html` 支持客户端路由 ^[hermes_cli/web_server.py:2025]
- 默认端口：`http://127.0.0.1:9119` ^[hermes_cli/web_server.py]

**源码证据**：
- 入口文件：hermes_cli/web_server.py
- 核心对象：`app = FastAPI(title="Hermes Agent")` ^[hermes_cli/web_server.py:64]
