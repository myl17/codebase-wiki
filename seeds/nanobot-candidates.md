# nanobot Candidate List

## 匹配结果

所有问题空间条目均为 **C 类（待观察）**——当前仅 nanobot 一个仓库被 ingest，无法满足 Concept 创建的硬门槛 ①（至少两个不同仓库以明显不同的方式解决同一问题）。

无 A 类（追加）、无 B 类（新建 Concept）、无 D 类（演化信号）。

| # | 问题名 | 情况 | 判断理由 |
|---|--------|------|----------|
| 1 | 如何编排 Agent 的主循环 | C | 仅 nanobot，无其他仓库对比 |
| 2 | 如何实现与产品逻辑解耦的通用 tool-use LLM 执行循环 | C | 仅 nanobot，无其他仓库对比 |
| 3 | 如何组装 Agent 的系统提示词 | C | 仅 nanobot，无其他仓库对比 |
| 4 | 如何管理 Agent 的长期记忆 | C | 仅 nanobot，无其他仓库对比 |
| 5 | 如何管理 Agent 工具的生命周期 | C | 仅 nanobot，无其他仓库对比 |
| 6 | 如何解耦 Channel 和 Agent Core 的消息传递 | C | 仅 nanobot，无其他仓库对比 |
| 7 | 如何让 Agent 同时支持多个聊天平台 | C | 仅 nanobot，无其他仓库对比 |
| 8 | 如何抽象 LLM 提供商的差异 | C | 仅 nanobot，无其他仓库对比 |
| 9 | 如何在 Agent 对话流中嵌入内置命令 | C | 仅 nanobot，无其他仓库对比 |
| 10 | 如何为 Agent 提供定时任务调度 | C | 仅 nanobot，无其他仓库对比 |
| 11 | 如何让 Agent 具备自主唤醒能力 | C | 仅 nanobot，无其他仓库对比 |
| 12 | 如何持久化管理 Agent 的多会话对话历史 | C | 仅 nanobot，无其他仓库对比 |
| 13 | 如何管理 Agent 的可插拔能力模块 | C | 仅 nanobot，无其他仓库对比 |
| 14 | 如何让主 Agent 委托后台子 Agent 执行复杂任务 | C | 仅 nanobot，无其他仓库对比 |
| 15 | 如何保护 Agent 的 Web/Shell 工具安全 | C | 仅 nanobot，无其他仓库对比 |

## 能力域覆盖表

仅 nanobot 一个仓库，覆盖表留空。等待其他 Agent 框架仓库（如 OpenClaw、Cognee、CrewAI 等）ingest 后填充。

| 能力域 | nanobot |
|--------|---------|
| Agent 主循环编排 | ✅ |
| LLM 调用循环与上下文治理 | ✅ |
| 系统提示词组装 | ✅ |
| 长期记忆与内存管理 | ✅ |
| 工具系统 | ✅ |
| 消息总线与解耦 | ✅ |
| 多平台 Channel 接入 | ✅ |
| LLM 提供商抽象 | ✅ |
| 内建命令系统 | ✅ |
| 定时任务调度 | ✅ |
| 自主唤醒/心跳 | ✅ |
| 会话管理 | ✅ |
| 技能/插件系统 | ✅ |
| 子 Agent/后台任务 | ✅ |
| 安全防护 | ✅ |
