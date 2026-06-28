---
type: overview
repo: codex-main
generated: 2026-06-28
---

# Codex CLI

OpenAI Codex CLI 是一个用 Rust 实现的 AI 编码 Agent 框架，采用 monorepo 结构（`codex-rs/` 下 ~107 个 crate）。它提供完整的 Agent 能力栈：从回合制交互循环、多传输层 JSON-RPC 后端、MCP 协议集成、插件/技能扩展系统、多层沙箱安全体系，到 LLM Provider 抽象和模型管理。同时提供了 CLI 和 TUI 两种交互界面。

## 核心子系统

- [[repos/codex-main/entities/core-agent-loop]] — Agent 的回合制交互循环，管理会话生命周期和线程状态
- [[repos/codex-main/entities/exec-server]] — 跨本地/远程/沙箱环境的统一命令执行抽象
- [[repos/codex-main/entities/execpolicy]] — Shell 命令执行的前缀规则策略引擎
- [[repos/codex-main/entities/sandbox-abstraction]] — 跨平台文件系统沙箱（Landlock/Bubblewrap/Seatbelt）
- [[repos/codex-main/entities/shell-escalation]] — 特权 shell 命令的安全提升执行
- [[repos/codex-main/entities/tool-system]] — 工具的定义、发现、执行和 Responses API 适配
- [[repos/codex-main/entities/hook-system]] — Agent 生命周期 10 个事件点的钩子拦截
- [[repos/codex-main/entities/skills-system]] — 用户定义的声明式技能文件扩展
- [[repos/codex-main/entities/model-provider]] — 多 LLM 后端统一抽象（OpenAI/Bedrock/ChatGPT）
- [[repos/codex-main/entities/models-manager]] — 模型目录、预设和动态刷新管理
- [[repos/codex-main/entities/config-management]] — 文件/云端/CLI 多层配置合并与验证
- [[repos/codex-main/entities/mcp-server]] — 将 Codex 工具暴露为 MCP JSON-RPC 服务
- [[repos/codex-main/entities/codex-mcp-integration]] — MCP 服务器连接、目录、OAuth 管理
- [[repos/codex-main/entities/app-server]] — 多传输层 JSON-RPC 后端，管理 Agent 会话
- [[repos/codex-main/entities/rollout]] — Agent 会话转录的持久化、浏览和全文搜索
- [[repos/codex-main/entities/thread-store]] — 跨存储后端的对话持久化抽象
- [[repos/codex-main/entities/message-history]] — 并发安全的全局用户消息历史
- [[repos/codex-main/entities/plugin-system]] — 插件包的标识、能力和钩子元数据模型
- [[repos/codex-main/entities/plugin-management]] — 插件商城、安装、升级和卸载管理
- [[repos/codex-main/entities/extension-api]] — 贡献者注册表式的 Agent 行为扩展接口
- [[repos/codex-main/entities/headless-exec]] — 命令行非交互式 Agent 执行
- [[repos/codex-main/entities/connectors]] — 外部应用连接器的发现和缓存

## 明确不做什么

- 不提供多 Agent 间的高层协作协议（如任务分解、Agent 间直接通信）——colab-mode-templates 只处理协作模式模板
- 不对消息平台作通用抽象（不像 nanobot/OpenClaw 有 channel system）——核心是编码场景的 Agent，交互主要通过 CLI/TUI/IDE 插件
- 不提供社区市场/技能市场（不像 HermesAgent 的 community marketplace）——商城限于 openai-curated 和 openai-bundled
- 内存管理非独立子系统——由核心循环中的 compact 和 message-history 协同处理
