# hermes-agent — 一个自我进化的 AI Agent 框架

hermes-agent（由 Nous Research 构建）是一个具有闭环学习能力的 AI Agent 框架：它从经验中创建技能、在使用中自我改进、通过定时任务自主运行、跨会话持久化记忆、在 18+ 通讯平台上运行，并支持 20+ AI Provider。它可在 $5 VPS、GPU 集群或 serverless 基础设施上运行。

核心设计哲学：**Agent 应该从每次交互中学习并持续改进**。不同于单次查询-响应模型，hermes-agent 内建了"经验→技能→改进→记忆→检索"的完整学习回路。它不是绑定在笔记本上的聊天机器人——你在 Telegram 上和它对话，它同时在云端 VM 上工作。

**核心架构特征**：
- **闭环学习回路**：Agent 创建技能（程序性记忆）→ 技能自我改进 → 定期记忆整理提醒 → FTS5 跨会话搜索 → Honcho 辩证式用户建模
- **多平台部署**：Telegram、Discord、Slack、WhatsApp、Signal、Matrix、Feishu、微信、QQ 等 18 个平台，单一 gateway 进程管理
- **Provider 无关**：20+ AI Provider（OpenRouter、Anthropic、OpenAI Codex、Bedrock、Nous Portal、Xiaomi、Gemini、DeepSeek、xAI 等），切换无需代码变更
- **六种执行环境**：本地、Docker、Singularity、Modal、Daytona、SSH——从笔记本到 GPU 集群
- **研究就绪**：批量轨迹生成、Atropos RL 环境、轨迹压缩用于训练下一代 tool-calling 模型

## 核心子系统

- [[repos/hermes-agent/entities/agent-core]] — AIAgent 主循环，协调 LLM 调用、工具执行和流式响应
- [[repos/hermes-agent/entities/gateway-runner]] — 多平台消息网关，管理 18+ 平台适配器生命周期
- [[repos/hermes-agent/entities/session-manager]] — 跨平台会话管理，确定性 session key 和自动重置策略
- [[repos/hermes-agent/entities/tool-registry]] — 工具自动发现、注册和分发，支持 toolset 组合
- [[repos/hermes-agent/entities/delegate-subagent]] — 并行子 Agent 委派，隔离上下文和迭代预算共享
- [[repos/hermes-agent/entities/terminal-execution]] — 六种执行环境后端的统一命令执行接口
- [[repos/hermes-agent/entities/mcp-integration]] — MCP 服务器集成，动态工具发现和 OAuth PKCE
- [[repos/hermes-agent/entities/skills-system]] — 程序性记忆系统：技能创建、自我改进、社区市场和安全管理
- [[repos/hermes-agent/entities/memory-system]] — 持久记忆和用户画像，支持 8 种可插拔后端
- [[repos/hermes-agent/entities/context-compressor]] — 上下文窗口治理，三阶段压缩算法和反震荡保护
- [[repos/hermes-agent/entities/prompt-builder]] — 多层系统提示词组装，模型特定执行纪律
- [[repos/hermes-agent/entities/cron-scheduler]] — 自然语言定时任务，支持多平台交付
- [[repos/hermes-agent/entities/state-database]] — SQLite/FTS5 会话状态持久化和跨会话搜索
- [[repos/hermes-agent/entities/cli-system]] — 24+ 子命令的交互式命令行界面
- [[repos/hermes-agent/entities/web-server]] — Web 仪表板，远程管理配置和会话
- [[repos/hermes-agent/entities/config-system]] — 配置管理，profile 隔离和时区感知
- [[repos/hermes-agent/entities/plugin-system]] — Memory Provider 和 Context Engine 双类型插件架构
- [[repos/hermes-agent/entities/model-adapters]] — Anthropic、Bedrock、Codex 原生 API 适配
- [[repos/hermes-agent/entities/provider-registry]] — 20+ Provider 注册、认证和模型发现
- [[repos/hermes-agent/entities/security-sandbox]] — 执行前多层安全（Tirith、危险模式、审批、配对）
- [[repos/hermes-agent/entities/process-registry]] — 后台进程跟踪、崩溃恢复和会话感知
- [[repos/hermes-agent/entities/platform-adapters]] — 18 个通讯平台适配器统一接口
- [[repos/hermes-agent/entities/batch-trajectory]] — 批量轨迹生成和训练数据压缩
- [[repos/hermes-agent/entities/logging-system]] — 组件感知日志、会话关联和密文脱敏

## 明确不做什么

- 不是单次查询-响应模型：核心价值在于跨会话的持续学习和改进
- 不限制于特定 Provider：无供应商锁定，Provider 切换零代码
- 不绑定笔记本：gateway 架构使 Agent 在云端运行，用户通过任意平台访问
- 不假设特定部署环境：本地/Docker/Modal/Daytona/SSH 六种后端覆盖所有场景
- 不将训练数据和研究工具与运行时代码耦合：batch_runner 和 trajectory_compressor 独立运行
