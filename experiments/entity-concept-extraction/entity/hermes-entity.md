# Hermes Agent — 系统表征

## 这个系统是什么

Hermes Agent 是 Nous Research 构建的自学习 AI Agent 框架——它是一个能通过完成任务自动创建技能、跨会话持久化记忆、并从历史经验中主动改进自身的 agent 运行时。用户通过 Telegram、Discord 等 20+ 消息平台或命令行与之交互，agent 在 $5 VPS 到 GPU 集群的任何环境上运行。

## 核心子系统

- **AIAgent（中央编排器）**：管理完整的 tool-calling 对话循环，处理模型 API 调用、failover 路由和子 agent 委派；不负责消息收发和平台适配。
- **GatewayRunner + 平台适配器**：将 agent 连接到 20+ 消息平台，管理适配器生命周期、会话路由和跨消息 agent 实例缓存；不做 tool-calling 逻辑。
- **自学习闭环（Prompt + 三工具）**：系统 prompt 中的三段驱动指令（MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE）+ 对应三个工具（memory / session_search / skill_manage），让 agent 在完成任务后自主创建技能、记忆用户偏好、跨会话回溯历史；不负责实际工具执行。
- **三层审批系统（ApprovalSystem）**：在命令执行前介入，按 YOLO → Smart（aux LLM）→ Manual（tirith + 正则匹配）三级审批；不负责工具结果处理。
- **Skill 安全扫描（SkillsGuard）**：外部技能安装前用 100+ 威胁模式做静态扫描，按 builtin/trusted/community/agent-created 四级信任策略决定放行或阻止；只在安装阶段介入，不干预运行时。
- **工具注册中心（ToolRegistry）**：通过 AST 扫描自动发现工具注册调用，作为单例管理所有工具 schema 和 handler，支持 MCP 动态刷新；不执行工具，只调度。
- **MemoryManager + MemoryProvider**：编排内置记忆存储和最多一个外部记忆插件（Honcho / Mem0 等 7 种），在每次 API 调用前预取相关记忆并注入 system prompt；不做 skill 管理。
- **ContextEngine（上下文压缩）**：当对话达到 75% context window 时触发，用辅助 LLM 摘要中间轮次以延长对话寿命；不感知工具执行结果的业务语义。
- **可观测性层**：覆盖三路旋转日志（含 40+ API key 自动脱敏）、后台进程注册表、per-session 成本追踪；是横切所有子系统的独立关注点。

## 关键机制

**系统 prompt 驱动的自学习闭环**：Hermes 的核心差异化不是某个工具，而是写入 system prompt 的三段驱动指令。这些指令让 LLM 主动触发 memory 写入、session_search 回溯和 skill_manage 创建——不需要人类触发，agent 在完成复杂任务后会自驱地积累经验。这与普通 agent 框架的本质区别在于：技能和记忆的产生是 agent 行为的自然副产品，而不是需要人工维护的外部配置。

**三层时间尺度的持久化**：Hermes 在三个不同时间尺度上积累状态——实时层（每轮后 memory 写入 MEMORY.md，同一会话后续立即生效）、跨会话层（FTS5 全文搜索历史会话，用户无需重复信息）、代际层（skill_manage 创建 SKILL.md，每次 CLI 启动自动注入 system prompt）。三层协同让 agent 越用越好，而不是每次重置。

**插件总线式扩展架构**：工具注册（AST 自动发现）、记忆后端（MemoryProvider ABC，最多 1 个外部）、上下文压缩（ContextEngine ABC）、平台适配（BasePlatformAdapter ABC）、事件 hooks（目录扫描加载）——五条扩展轴各自独立，都通过统一接口接入，不修改核心编排器即可扩展。

**多层安全护栏内嵌于执行路径**：审批系统（命令执行前）和技能扫描（安装前）都是硬路径拦截，不是可绕过的建议。三层审批的中间层（Smart Approval）用辅助 LLM 做风险评估，避免人在每条命令上都要手动确认，同时防止高危操作悄悄通过。

## 明确不做什么

- 不是 RAG 框架，不索引代码库或文档做语义检索（session_search 是会话历史 FTS，不是通用知识库）
- 不是 workflow 编排工具，没有 DAG 定义层，tool-calling 循环由 LLM 自主决策
- 不提供模型训练或微调能力（RL 环境集成是可选 extra，不是核心功能）
- 不自带 LLM，依赖 20+ 外部 provider 提供模型能力（OpenAI-compatible API）
- 不做端到端加密，安全边界在于审批拦截和日志脱敏，不在于传输层
