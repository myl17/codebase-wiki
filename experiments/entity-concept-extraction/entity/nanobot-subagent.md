# Subagent（nanobot）

## 是什么 / 边界
nanobot 的隔离代理生成器——`SubagentManager.spawn(task, label)` 在后台启动独立 agent，共享 AgentRunner 引擎但拥有独立的 ToolRegistry。结果通过 bus 注入主 agent 入站队列，与 IM 消息复用同一消费路径。

**边界**：Subagent 只负责独立任务的隔离执行。它不管理主 agent 状态、不直接与用户交互、不维护会话。

## 关键实现
- **共享引擎 + 独立工具集**：使用同一 `AgentRunner.run()` 引擎，但构建独立的 `ToolRegistry`——包含文件工具 + 可选的 exec/web 工具，**不包含** message/spawn/cron 工具（防止递归创建子 agent）
- **结果注入**：`bus.publish_inbound(msg)` 将子 agent 完成结果注入主 agent 的入站队列——与 Telegram/Discord 消息的处理路径完全相同
- **约束**：15 轮 iteration budget，tool error 为 fatal 级别（出错立即终止，不像主 agent 的非致命错误继续）
- **命名**：子 agent 的 label 用于追踪和日志区分

## 设计选择记录
- **维度**：Architecture
- **选择**：子 agent 共享 AgentRunner 引擎，但拥有独立的受限 ToolRegistry（无 message/spawn/cron），结果通过 bus.publish_inbound() 注入主 agent 入站队列
- **替代方案**：子 agent 拥有独立的执行引擎和独立的消息处理路径，结果通过专门的 callback 或 future 返回
- **为什么有这个选择**：共享引擎复用 AgentRunner 的所有上下文治理能力（Backfill/Microcompact/Budget/Snip），无需重新实现。独立受限 ToolRegistry 是防止递归创建子 agent 的安全边界。通过 bus 注入结果统一了入站处理路径——AgentLoop 不需要区分「这是 Telegram 消息还是子 agent 结果」
