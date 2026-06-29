---
type: entity
repo: nanobot
slug: bridge-gateway
problem: 如何为 Agent 提供与 WhatsApp 等平台的网关桥接，使 Node.js 生态的能力可接入 Python Agent
generated: 2026-06-25
source_files:
  - bridge/src/index.ts
  - bridge/src/server.ts
  - bridge/src/whatsapp.ts
---

# Bridge Gateway

**代码位置**：`bridge/`
**这个模块解决什么问题**：
- 实现层：基于 TypeScript 的独立 Node.js 网关，提供 WhatsApp Web.js 桥接和 HTTP 服务器，将 WhatsApp 消息转发到 Python Agent 核心
- 问题层：如何为 Agent 提供与 WhatsApp 等平台的网关桥接，使 Node.js 生态的能力可接入 Python Agent
**对外暴露什么**：TypeScript 入口 `bridge/src/index.ts`、HTTP 服务器 `bridge/src/server.ts`
**它和谁交互**：
- 依赖 [[entities/channel-system]]（Python 端的 WhatsApp channel 实现）
- 依赖 WhatsApp Web.js 库
**为什么它是可分离的**：独立的 Node.js 项目，通过 HTTP 与 Python 核心通信，可独立部署和扩展

**关键机制**（源码可见）：
- 跨语言桥接：Python agent 核心通过 HTTP API 与 Node.js 网关通信，解决 WhatsApp Web.js 等纯 Node.js 生态库的接入问题 ^[bridge/src/index.ts]
- HTTP 服务器模式：gateway 作为独立服务运行，接收 Python 端的请求并转发到 WhatsApp ^[bridge/src/server.ts]

**源码证据**：
- 入口文件：bridge/src/index.ts
- 核心文件：bridge/src/server.ts、bridge/src/whatsapp.ts
