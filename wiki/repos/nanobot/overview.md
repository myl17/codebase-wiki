# nanobot — Ultra-Lightweight Personal AI Agent

nanobot 是一个超轻量级个人 AI Agent 框架，受 OpenClaw 启发，用 **99% 更少的代码行数** 提供核心 Agent 功能。它不是一个单一用途的工具——它是一个可扩展的 Agent 运行时，支持多 LLM 提供方、多聊天平台、工具调用、内存管理和定时任务。用 Python >=3.11 编写，以 pip 包分发（`nanobot-ai`）。

核心设计哲学：**最小化代码量，最大化可理解性**。面向研究者和开发者，代码干净可读，易于理解和修改。

## 核心子系统

- [[repos/nanobot/entities/agent-loop]] — Agent 主循环，编排消息接收、上下文构建、LLM 调用、工具执行和响应发送
- [[repos/nanobot/entities/agent-runner]] — 通用 tool-use LLM 执行循环，不耦合产品逻辑
- [[repos/nanobot/entities/context-builder]] — 系统提示词和上下文消息组装
- [[repos/nanobot/entities/memory-system]] — 三层内存架构：文件 I/O + token 预算整理 + 深度反思编辑
- [[repos/nanobot/entities/tool-registry]] — 工具注册、发现和执行引擎
- [[repos/nanobot/entities/message-bus]] — Channel-Agent 之间的异步解耦消息总线
- [[repos/nanobot/entities/channel-system]] — 多聊天平台接入框架（12 个 channel）
- [[repos/nanobot/entities/provider-system]] — 多 LLM 提供商抽象和自动匹配
- [[repos/nanobot/entities/config-system]] — 多维运行时配置管理
- [[repos/nanobot/entities/cli-system]] — 交互式命令行界面
- [[repos/nanobot/entities/command-router]] — 内建 in-chat 命令路由
- [[repos/nanobot/entities/cron-service]] — 定时任务调度
- [[repos/nanobot/entities/heartbeat-service]] — 空闲时自主任务检查
- [[repos/nanobot/entities/session-manager]] — 多会话持久化
- [[repos/nanobot/entities/api-server]] — OpenAI-compatible HTTP API
- [[repos/nanobot/entities/security-system]] — SSRF 防护和网络安全
- [[repos/nanobot/entities/subagent-manager]] — 后台子 Agent 异步任务
- [[repos/nanobot/entities/skills-loader]] — 可插拔能力模块管理
- [[repos/nanobot/entities/nanobot-facade]] — Python SDK 简洁接口
- [[repos/nanobot/entities/bridge-gateway]] — Node.js 跨语言网关（WhatsApp 桥接）

## 明确不做什么

- **不提供有类型系统的知识图谱** — 这是 Agent 运行时，不是知识管理工具
- **不做 Crypto/Token 相关功能** — README 明确声明与此无关
- **不做 Web UI** — 交互通过 CLI、Chat Apps 或 API
- **非生产级分布式系统** — 设计目标是单用户/小团队的个人 Agent，不处理多租户和高可用
