# Codebase Wiki

## Repos

- [[nanobot/overview]] — Ultra-Lightweight Personal AI Agent, 多 LLM 提供商、多聊天平台、工具调用、内存管理 — topics: ai-agent, python, multi-channel, llm — last ingest: 2026-06-25
- [[hermes-agent/overview]] — Full-Featured Python AI Agent, 26+ 平台支持、多 Provider、可插拔执行环境、技能系统、社区市场 — topics: ai-agent, python, multi-channel, skills-marketplace, remote-execution — last ingest: 2026-06-25
- [[openclaw/overview]] — TypeScript AI Agent 框架, 插件化架构、100+ 插件、25+ 消息平台、沙箱执行 — topics: ai-agent, typescript, plugin-architecture, multi-channel, sandbox — last ingest: 2026-06-26
- [[deepagents/overview]] — Python AI Agent SDK, 中间件堆栈架构、子代理双轨、双层压缩、Agent Skills 规范 — topics: ai-agent, python, middleware, sdk, agent-skills — last ingest: 2026-06-28

## Concepts

| 问题 | 页面 | 覆盖仓库 |
|------|------|----------|
| 如何编排 Agent 的主循环 | [[concepts/agent-loop-orchestration]] | nanobot, hermes-agent, openclaw |
| 如何在上下文窗口限制下压缩对话历史 | [[concepts/context-compression-strategy]] | nanobot, hermes-agent, openclaw, deepagents |
| 如何抽象多个异构消息平台的接口差异 | [[concepts/channel-abstraction-pattern]] | nanobot, hermes-agent, openclaw |
| 如何管理会话身份识别与持久化生命周期 | [[concepts/session-lifecycle-management]] | nanobot, hermes-agent, openclaw |
| 如何组装 Agent 的系统提示词 | [[concepts/system-prompt-assembly]] | nanobot, hermes-agent, openclaw |
| 如何管理 Agent 的长期记忆架构 | [[concepts/memory-management-architecture]] | nanobot, hermes-agent, deepagents |
| 如何管理工具注册、发现与策略过滤 | [[concepts/tool-lifecycle-management]] | nanobot, hermes-agent, openclaw |
| 如何抽象多 LLM Provider 的差异 | [[concepts/provider-abstraction-pattern]] | nanobot, hermes-agent, openclaw, deepagents |
| 如何编排子 Agent 的委托与生命周期 | [[concepts/subagent-orchestration]] | nanobot, hermes-agent, openclaw, deepagents |
| 如何构建多层安全防御体系 | [[concepts/security-architecture]] | nanobot, hermes-agent, openclaw |
| 如何在高风险操作前插入人类审批 | [[concepts/execution-approval-pattern]] | hermes-agent, openclaw |
| 如何管理 Agent 的可插拔能力模块 | [[concepts/skills-extension-mechanism]] | nanobot, hermes-agent, openclaw, deepagents |
| 如何实现定时自主任务调度 | [[concepts/autonomous-scheduling]] | nanobot, hermes-agent, openclaw |
| 如何管理运行时配置与多 Profile | [[concepts/configuration-management]] | nanobot, hermes-agent, openclaw |
| 如何为工具提供隔离的执行环境 | [[concepts/execution-isolation]] | hermes-agent, openclaw, deepagents |
| 如何组合中间件构建 Agent 图 | [[concepts/middleware-composition-pattern]] | nanobot, hermes-agent, openclaw, deepagents |

## Views

- [[views/2026-06-26-compare-hermes-openclaw]] — hermes-agent vs openclaw 核心差异 — 2026-06-26

## Insights

*(no insights yet)*
