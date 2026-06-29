# Evolve Signals — deepagents (2026-06-28)

## D1: 文件系统工具接口设计

- **问题**：如何为 AI Agent 提供文件系统操作接口
- **相关 Concept**：tool-lifecycle-management
- **信号类型**：粒度不匹配
- **理由**：deepagents 的文件系统工具设计（7 个工具、Pydantic Schema、backend 抽象解耦）关注的是"每个工具应该设计成什么样"，而 tool-lifecycle-management 关注的是"工具如何注册/发现/过滤/生命周期管理"。当前 tool-lifecycle-management 中缺少"工具设计模式"维度。建议未来在 tool-lifecycle-management 中新增工具接口设计讨论小节，将 deepagents 的 Pydantic Schema 模式和 nanobot/openclaw/hermes-agent 的工具定义模式进行对比。
