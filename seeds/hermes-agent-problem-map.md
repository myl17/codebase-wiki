# hermes-agent — Problem Space Mapping

> 生成日期：2026-06-25
> 来源实体：24 个 entities
> 分类：架构决策 × 8 | 技术选型 × 6 | 实现细节（跳过）× 10

---

## 架构决策（8 个）

---
## 如何编排 Agent 的主循环

**问题陈述**：任何 AI agent 框架都必须决定如何组织 LLM 调用、工具执行和流式输出的控制流，包括错误恢复和迭代预算管理。
**核心关切**：
- 效率：最小化不必要的 LLM 往返，同时保证工具调用的完整性
- 容错：优雅处理 API 错误（限流、认证过期、上下文溢出），不丢失会话状态
- provider 无关：同一循环必须适配多种 API 格式（chat completions、anthropic messages、bedrock converse）
**hermes-agent 的解法**：AIAgent 类通过 while 循环驱动迭代，自动检测 API mode，使用 IterationBudget 统一限制父子 agent 调用次数，通过 classify_api_error() 实现结构化故障路由
**源码证据**：run_agent.py:535-535, run_agent.py:690-709, run_agent.py:8130
**来源 Entity**：agent-core
**层级**：架构决策

---
## 如何管理对话上下文窗口

**问题陈述**：LLM 的上下文窗口有限（32K-200K tokens），长期对话必然超限，必须自动压缩历史而不丢失关键状态。
**核心关切**：
- 保真度：压缩后的摘要必须保留决策、约束和进行中任务的完整上下文
- 成本：压缩本身消耗 token（需调用 LLM），压缩收益必须大于成本
- 连续性：压缩不应破坏工具调用配对或 todo 状态
**hermes-agent 的解法**：ContextCompressor 三阶段压缩（工具裁剪→结构化摘要→组装），使用便宜模型（Gemini Flash）通过 11 字段模板生成摘要，含反震荡保护和压缩感知会话拆分
**源码证据**：agent/context_compressor.py:185, agent/context_compressor.py:927
**来源 Entity**：context-compressor
**层级**：架构决策

---
## 如何将不同通讯平台的消息路由到统一 Agent

**问题陈述**：AI agent 需要在 Telegram、Discord、Slack、WhatsApp 等完全不同的 API 上提供一致体验，每个平台有独特的消息格式、速率限制和媒体类型。
**核心关切**：
- 归一化：将各平台的原生消息格式转换为统一的内部表示
- 流式体验：在支持消息编辑的平台（Telegram/Discord/Slack）上实现实时流式输出
- 会话持续：同一用户跨平台时应能访问同一对话（或适当隔离）
**hermes-agent 的解法**：BasePlatformAdapter ABC 定义统一接口，18 个具体适配器封装平台 SDK；GatewayRunner 通过工厂创建并管理生命周期；GatewayStreamConsumer 通过编辑消息实现流式输出
**源码证据**：gateway/platforms/base.py:813, gateway/run.py:538, gateway/stream_consumer.py:48
**来源 Entity**：platform-adapters, gateway-runner
**层级**：架构决策

---
## 如何实现跨会话的身份和状态管理

**问题陈述**：AI agent 需要在不同平台、不同时间识别同一用户，决定何时开始新会话、何时继续，同时保持 prompt caching 效率。
**核心关切**：
- 识别确定性：session_key 必须在跨网关重启后在相同条件下产生相同值
- 重置时机：空闲超时、每日重置、手动 /new——三者需共存且可配置
- 隐私：用户标识在 system prompt 中可能需要脱敏（WhatsApp/Signal 等隐私平台）
**hermes-agent 的解法**：SessionStore 通过确定性 `agent:main:<platform>:<type>:<id>` 格式生成 session_key；三层重置策略（none/idle/daily/both）按平台/类型可覆盖；PII 通过 SHA-256 哈希脱敏
**源码证据**：gateway/session.py:439, gateway/session.py:620, gateway/session.py:34
**来源 Entity**：session-manager
**层级**：架构决策

---
## 如何管理工具的安全执行

**问题陈述**：AI agent 执行系统命令可能造成不可逆的破坏（删除文件、修改系统配置、网络数据外泄），必须在执行前进行多层安全检查。
**核心关切**：
- 防御深度：不应依赖单层检查；需要内容扫描 + 模式匹配 + 用户审批的级联防护
- 误报处理：静态正则匹配容易误报（如无害的 `python -c "print('hello')"` 匹配 `python -c` 模式），需要智能降级
- 用户体验：审批流程不应繁琐到用户禁用安全检查
**hermes-agent 的解法**：check_all_command_guards() 流水线依次执行 Tirith 二进制扫描（homograph/pipe/注入）→ 40+ 危险模式检测 → LLM 辅助智能审批（降低误报）→ 会话/永久/YOLO 三级审批；DM 配对的加密随机码授权
**源码证据**：tools/approval.py:693, tools/tirith_security.py:614, tools/approval.py:534
**来源 Entity**：security-sandbox
**层级**：架构决策

---
## 如何持久化会话并支持跨会话检索

**问题陈述**：长期运行的 agent 需要记住过去的对话，用户可能问"我们上周讨论的那件事"——需要索引和检索历史会话的能力。
**核心关切**：
- 并发安全：多进程（gateway + CLI + subagent worktree agents）共享一个 state.db，必须处理 WAL 写入冲突
- 规模：数千个会话、数百万条消息的全文本搜索必须高效
- 智能检索：原始 FTS5 命中不够，需要用 LLM 摘要跨会话结果
**hermes-agent 的解法**：SessionDB 使用 SQLite WAL + FTS5，jitter 重试（20-150ms 随机退避）解决写入竞争；session_search 工具通过 FTS5 匹配→加载会话→截断→并行 Gemini Flash 摘要返回结构化结果
**源码证据**：hermes_state.py:115, hermes_state.py:180-210, tools/session_search_tool.py:297
**来源 Entity**：state-database
**层级**：架构决策

---
## 如何管理系统提示词的复杂性

**问题陈述**：AI agent 的系统提示词必须集成身份定义、平台提示、技能列表、记忆上下文、项目文件和执行纪律——这些组件的组合方式直接影响 token 成本和指令遵循。
**核心关切**：
- Prompt caching：对 Anthropic 等支持 prompt cache 的 provider，缓存断点位置显著影响成本
- 上下文污染：项目文件可能包含恶意的 prompt injection，必须扫描后才能注入
- 模型差异：不同模型的角色约定（GPT-5 用 developer role、Gemini 需要特定风格）和最佳提示方式不同
**hermes-agent 的解法**：纯函数 prompt_builder 组装多层提示词（SOUL.md→平台提示→记忆→技能→上下文文件），每层独立函数；注入前扫描 10+ 种 prompt injection 模式 + 不可见 Unicode；模型特定执行纪律（TOOL_USE_ENFORCEMENT、OPENAI_MODEL_EXECUTION、GOOGLE_MODEL_OPERATIONAL）
**源码证据**：agent/prompt_builder.py:134-258, agent/prompt_builder.py:36-49
**来源 Entity**：prompt-builder
**层级**：架构决策

---
## 如何让 Agent 从经验中学习

**问题陈述**：AI agent 在完成任务后应该有机制将学到的知识持久化——"下次做 X 时记住 Y"——这是从工具到智能体的关键跃迁。
**核心关切**：
- 程序性 vs 声明性：技能（如何做，narrow）和记忆（知道什么，broad）是互补的学习维度
- 信任与安全：从社区下载的技能必须经过多层安全扫描
- 渐进式加载：完整技能内容可能很长，需要按需披露以控制上下文膨胀
**hermes-agent 的解法**：双轨学习——技能系统（程序性记忆，skill_manage 工具 CRUD） + 记忆系统（声明性记忆，MEMORY.md/USER.md + 8 种外部 provider）；技能社区市场通过 8 个联邦源并行搜索；Skills Guard 对安装前技能进行正则模式 + 不可见 Unicode + 结构扫描
**源码证据**：tools/skill_manager_tool.py:616, tools/memory_tool.py:105, tools/skills_guard.py:595
**来源 Entity**：skills-system, memory-system
**层级**：架构决策

---

## 技术选型（6 个）

---
## 如何抽象多种 AI Provider

**问题陈述**：不同 AI provider（Anthropic、OpenAI、Bedrock、OpenRouter）有不同的原生 API 格式、认证方法和限制，需要统一但又不丢失 provider 特有功能。
**核心关切**：
- 格式转换保真度：将 Anthropic 的 thinking blocks 或 Bedrock 的 guardrails 正确映射回 OpenAI 兼容格式
- 认证多样性：API key、OAuth device code、OAuth external（PKCE）、AWS IAM、external process——五种认证方式
- 回退链路：主 provider 不可用时自动切换到备选 provider
**hermes-agent 的解法**：函数式适配器模块（非类继承），通过 `api_mode` 枚举选择适配路径；HermesOverlay 元数据定义每个 provider 的 transport/auth/url；CredentialPool 管理多 key 轮换
**源码证据**：agent/anthropic_adapter.py:243, agent/bedrock_adapter.py:61, hermes_cli/providers.py:33-149
**来源 Entity**：model-adapters, provider-registry
**层级**：技术选型

---
## 如何实现可扩展的远程执行环境

**问题陈述**：AI agent 需要执行命令，但用户希望它在隔离环境（Docker）、云端（Modal）、远程机器（SSH）或高性能环境（Singularity）中运行——需要一个统一接口切换后端。
**核心关切**：
- 环境持久化：切换环境后工作目录（CWD）和文件必须保持连续
- 资源管理：长期空闲的环境应自动清理，避免资源泄漏
- 用户体验：用户不应感知后端差异
**hermes-agent 的解法**：BaseEnvironment ABC + 6 个具体实现；统一 spawn-per-call 模型；CWD 通过 temp file（local）或 in-band marker（remote）持久化；300s 自动清理不活跃环境
**源码证据**：tools/environments/base.py:89, tools/terminal_tool.py:686-760, tools/terminal_tool.py:815
**来源 Entity**：terminal-execution
**层级**：技术选型

---
## 如何扩展 Agent 的功能

**问题陈述**：Agent 的能力应该通过工具和插件可扩展——用户应能添加自定义工具、集成外部服务（MCP）、安装社区技能。
**核心关切**：
- 注册安全：新工具不应能覆盖（shadow）内建工具
- 发现自动化：添加新工具模块不需手动注册
- 动态性：MCP 服务器可能随时上线/下线，工具列表可能动态变化
**hermes-agent 的解法**：ToolRegistry 单例 + AST 自动发现（扫描 `tools/*.py`）+ 工具遮蔽保护（非 MCP 工具冲突时拒绝）；MCP 通过后台 event loop 管理长生命周期连接，支持 `notifications/tools/list_changed` 动态刷新
**源码证据**：tools/registry.py:100, tools/registry.py:41-74, tools/mcp_tool.py:774
**来源 Entity**：tool-registry, mcp-integration
**层级**：技术选型

---
## 如何将多个子任务并行化

**问题陈述**：复杂任务可能需要同时进行多个独立工作流（如同时研究多个候选方案），需要并行委派机制来利用并发加速。
**核心关切**：
- 隔离性：子任务不应能互相干扰（独立上下文、限制工具集、独立终端会话）
- 预算控制：子任务的 LLM 调用应与父任务共享迭代预算，防止无限消耗
- 进度透明：父任务应知晓子任务进度，但不淹没在子任务细节中
**hermes-agent 的解法**：delegate_task 通过 ThreadPoolExecutor 并行创建独立 AIAgent 实例；DELEGATE_BLOCKED_TOOLS 禁止递归、用户交互和共享内存写入；iteration_budget 共享限制总调用数；最大深度 2 防止递归爆炸
**源码证据**：tools/delegate_tool.py:32-53, tools/delegate_tool.py:238-284
**来源 Entity**：delegate-subagent
**层级**：技术选型

---
## 如何管理配置和 Profile

**问题陈述**：用户可能需要多个独立的 Agent 配置（个人/工作/开发），每个有独立的 API key、记忆、技能和会话——需要一个 profile 系统。
**核心关切**：
- 完全隔离：profile 之间的 API key、记忆和会话不应泄漏
- 子进程隔离：git、ssh、gh 等工具在 profile 内应有独立配置
- 易用性：profile 创建/切换/删除应简单直观
**hermes-agent 的解法**：HERMES_HOME 环境变量指向 profile 目录（`~/.hermes/profiles/<name>/`）；每个 profile 有独立 `home/` 目录作为子进程 HOME（git/ssh/gh 隔离）；hermes profile CLI 命令管理全生命周期
**源码证据**：hermes_constants.py:11-18, hermes_constants.py:114-137, hermes_cli/profiles.py:335-508
**来源 Entity**：config-system
**层级**：技术选型

---
## 如何实现定时自主任务

**问题陈述**：AI agent 应能自主执行定时任务——用户在 Telegram 上说"每天早上 9 点给我发科技新闻摘要"——需要调度系统支持自然语言定义和自主执行。
**核心关切**：
- 可靠性：单个 gateway 进程的 tick 机制需要文件锁防止重复执行
- 安静模式：当任务无新内容时不应发送空消息（静默抑制）
- 交付灵活性：结果可交付到原始平台、指定平台或仅存档
**hermes-agent 的解法**：cron/scheduler.py 每 60s tick，文件锁（fcntl）防止多进程并发；[SILENT] 标记抑制空交付；支持 cron 表达式 + 自然语言关键词（"tomorrow 9am"）；交付到 26+ 平台
**源码证据**：cron/scheduler.py:906, cron/scheduler.py:55-58, cron/jobs.py:117
**来源 Entity**：cron-scheduler
**层级**：技术选型

---

## 实现细节（跳过）

以下 entity 解决的是 **hermes-agent 特有的实现问题**，不是任何同类框架构建者都必须面对的通用问题空间：

| Entity | 跳过原因 |
|--------|----------|
| **web-server** | Web 仪表板是特定部署方式的选择，核心 agent 功能不需要 Web UI |
| **cli-system** | CLI 是 hermes-agent 的用户入口方式之一（gateway 是另一种），不是 agent 框架的架构核心问题 |
| **plugin-system** | 插件机制是 Memory Manager 和 Context Engine 的加载基础设施，核心设计决策已在相关 entity 中体现 |
| **process-registry** | 后台进程跟踪是终端工具的实现细节，核心问题是执行环境而非进程管理 |
| **batch-trajectory** | 批量轨迹生成和压缩是研究工具链，服务于 RL 训练，不属于 agent 框架的运行时核心 |
| **logging-system** | 集中式日志是工程实践而非架构决策 |
