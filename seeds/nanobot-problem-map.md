# nanobot Problem Space Map

从 nanobot 的 20 个 Structural Entity 中提取，面向 Framework Builder 翻译为问题空间条目。

---

## 如何编排 Agent 的主循环

**问题陈述**：构建 Agent 框架的人必须定义消息如何从入口进入、经过哪些处理阶段、最终如何返回响应——这是框架的"心跳"
**核心关切**：
- 关切 1：消息从不同 channel 进入时如何保证会话顺序
- 关切 2：如何在单实例中平衡并发和串行处理
- 关切 3：长时间运行的 tool call 中断后如何恢复状态
**nanobot 的解法**：异步消息总线 + 会话级串行锁 + 运行时检查点持久化，channel 通过总线推送消息，agent 从总线消费
**源码证据**：nanobot/agent/loop.py:115-361
**来源 Entity**：agent-loop
**层级**：架构决策

---

## 如何实现与产品逻辑解耦的通用 tool-use LLM 执行循环

**问题陈述**：所有 Agent 框架都需要一个 LLM 调用循环来交替执行"思考"和"行动"，问题在于这个循环是否应该与 channel、session、CLI 等产品层逻辑耦合
**核心关切**：
- 关切 1：上下文窗口管理（何时裁剪、如何裁剪、裁剪多少）
- 关切 2：错误恢复策略（空响应、长度截断、工具错误如何处理）
- 关切 3：并发工具执行的安全性和效率
**nanobot 的解法**：纯 runner 只处理 messages + tools + provider 循环，上下文治理通过快照裁剪、微压缩和预算管理三层管道实现
**源码证据**：nanobot/agent/runner.py:83-723
**来源 Entity**：agent-runner
**层级**：架构决策

---

## 如何组装 Agent 的系统提示词

**问题陈述**：每个 Agent 框架都要决定系统提示词的结构——身份、记忆、技能、历史如何分层注入，以及如何避免上下文膨胀
**核心关切**：
- 关切 1：上下文预算有限时，哪些信息必须进入系统提示词、哪些按需加载
- 关切 2：运行时动态信息（时间、channel）如何注入而不污染消息语义
- 关切 3：多模态输入（图片）如何与文本上下文融合
**nanobot 的解法**：分层系统提示词（身份 > 引导文件 > 长期记忆 > always skills > 技能摘要 > 最近历史），运行时上下文以元数据标签注入 user 消息前缀
**源码证据**：nanobot/agent/context.py:17-195
**来源 Entity**：context-builder
**层级**：架构决策

---

## 如何管理 Agent 的长期记忆

**问题陈述**：Agent 框架需要持久化对话历史和长期记忆，问题在于用多少层处理——是简单的文件追加，还是需要 LLM 驱动的主动整理和反思
**核心关切**：
- 关切 1：上下文窗口有限，旧消息如何压缩而不丢失关键信息
- 关切 2：记忆整理的触发时机——passive（token 预算触发）vs active（定时调度）
- 关切 3：记忆的存储格式和可迁移性
**nanobot 的解法**：三层架构——MemoryStore（文件 I/O，被动）-> Consolidator（token 预算触发压缩，主动）-> Dream（定时深度反思 + 文件编辑，重量级）
**源码证据**：nanobot/agent/memory.py:31-675
**来源 Entity**：memory-system
**层级**：架构决策

---

## 如何管理 Agent 工具的生命周期

**问题陈述**：Agent 框架需要工具注册、发现、参数校验和执行的标准机制，还要支持内建工具和外部扩展（如 MCP）的统一管理
**核心关切**：
- 关切 1：工具定义排序对 LLM prompt cache 的影响
- 关切 2：参数类型转换和验证应该在哪里做（注册时还是执行时）
- 关切 3：扩展工具（MCP）与内建工具的命名空间冲突
**nanobot 的解法**：Tool 抽象基类 + ToolRegistry 字典注册，MCP 工具以 `mcp_` 前缀区分，工具定义稳定排序优化缓存
**源码证据**：nanobot/agent/tools/registry.py:8-111
**来源 Entity**：tool-registry
**层级**：架构决策

---

## 如何解耦 Channel 和 Agent Core 的消息传递

**问题陈述**：当 Agent 同时接入多个聊天平台时，框架需要一种通信机制，使平台适配器和 Agent 核心可以独立演化
**核心关切**：
- 关切 1：异步解耦——平台和 Agent 谁都不应该阻塞对方
- 关切 2：流式消息的传递方式——delta 粒度、合并策略
- 关切 3：会话标识的传递——channel 信息如何映射到 session
**nanobot 的解法**：基于 asyncio.Queue 的双向事件总线，InboundMessage 携带 `channel:chat_id` 作为 session key，OutboundMessage 通过 metadata 传递流式控制信号
**源码证据**：nanobot/bus/events.py:9-36, nanobot/bus/queue.py:8-45
**来源 Entity**：message-bus
**层级**：架构决策

---

## 如何让 Agent 同时支持多个聊天平台

**问题陈述**：Agent 框架面临的一个核心问题是平台适配层的设计——应该为每个平台写独立集成，还是提供统一抽象让平台插件化
**核心关切**：
- 关切 1：平台多样性——不同平台的 API 差异巨大（消息格式、流式支持、媒体处理）
- 关切 2：平台发现和启用——如何让用户轻松添加新平台
- 关切 3：发送可靠性——不同平台的失败模式和重试策略
**nanobot 的解法**：BaseChannel 统一接口（start/stop/send/send_delta）+ discover_all() 自动发现 + 指数退避重试
**源码证据**：nanobot/channels/base.py:15-182, nanobot/channels/manager.py:20-296
**来源 Entity**：channel-system
**层级**：架构决策

---

## 如何抽象 LLM 提供商的差异

**问题陈述**：Agent 框架需要支持多种 LLM API（Anthropic/OpenAI/Azure/本地等），问题在于统一的接口粒度——是只抽象 chat 调用，还是把重试、错误分类、提供商选择也纳入抽象
**核心关切**：
- 关切 1：错误分类粒度——哪些错误应该重试、哪些不应该
- 关切 2：提供商自动匹配——用户给出 model 名，框架如何选择正确的 API 端点
- 关切 3：多提供商之间的 API 差异（消息格式、工具调用格式、流式协议）
**nanobot 的解法**：LLMProvider 抽象类封装 chat + retry + 错误分类，provider registry 按 model 关键词 + prefix 自动匹配，标准化 ToolCallRequest/LLMResponse 类型
**源码证据**：nanobot/providers/base.py:80-703
**来源 Entity**：provider-system
**层级**：架构决策

---

## 如何在 Agent 对话流中嵌入内置命令

**问题陈述**：Agent 框架需要处理用户发出的控制命令（如 /stop、/status），问题在于这些命令应该在进入 LLM 之前拦截，还是让 LLM 自己识别和处理
**核心关切**：
- 关切 1：优先级命令（如 /stop）需要即时响应，不应等待 LLM 处理
- 关切 2：常规命令（如 /status）在 LLM 有上下文时可能处理得更好
- 关切 3：插件 channel 如何注册自己的命令
**nanobot 的解法**：两级命令路由——优先级命令在主循环直接 dispatch，常规命令在消息处理流程中 dispatch，channel 可通过注册扩展
**源码证据**：nanobot/command/router.py, nanobot/agent/loop.py:385-389,529-531
**来源 Entity**：command-router
**层级**：架构决策

---

## 如何为 Agent 提供定时任务调度

**问题陈述**：Agent 框架如果支持用户设置定时任务（如"每天早上 9 点提醒我"），需要内置调度器——问题在于调度器的持久化、多实例协调和调度表达力
**核心关切**：
- 关切 1：调度表达力——简单间隔 vs Cron 表达式 vs 一次性
- 关切 2：多实例协调——多个 nanobot 进程如何避免重复执行同一任务
- 关切 3：任务的持久化可靠性
**nanobot 的解法**：at/every/cron 三种调度方式，文件持久化 + action.jsonl 实现多实例协调
**源码证据**：nanobot/cron/service.py:65-495
**来源 Entity**：cron-service
**层级**：架构决策

---

## 如何让 Agent 具备自主唤醒能力

**问题陈述**：Agent 框架如果允许 Agent 在空闲时自主检查待办任务并主动执行（而不依赖用户输入触发），需要一个轻量级的决策机制
**核心关切**：
- 关切 1：决策成本——每次检查不应该消耗完整 agent loop 的 token
- 关切 2：决策可靠性——如何避免自由文本解析的不可靠性
- 关切 3：执行触发——决策后如何衔接实际的 agent 执行
**nanobot 的解法**：两阶段心跳——Phase 1 用虚拟 tool call（heartbeat tool）做结构化 skip/run 决策，Phase 2 仅当需要时才启动完整 agent loop
**源码证据**：nanobot/heartbeat/service.py:14-50
**来源 Entity**：heartbeat-service
**层级**：架构决策

---

## 如何持久化管理 Agent 的多会话对话历史

**问题陈述**：Agent 框架需要持久化多用户的对话历史，问题在于存储格式的选择——纯文本、JSONL、数据库——以及如何在读写效率和格式复杂度间权衡
**核心关切**：
- 关切 1：读写性能——每次 LLM 调用都需要读历史，格式必须高效
- 关切 2：消息完整性——跨会话的消息序列必须从合法的 user turn 开始
- 关切 3：数据迁移——用户升级框架时旧格式的兼容性
**nanobot 的解法**：JSONL 格式（一行一消息 + 首行元数据），内存缓存 + 合法消息边界裁剪，支持旧版路径自动迁移
**源码证据**：nanobot/session/manager.py:17-237
**来源 Entity**：session-manager
**层级**：架构决策

---

## 如何管理 Agent 的可插拔能力模块

**问题陈述**：Agent 框架需要支持通过 skill 文件扩展 Agent 能力，问题在于 skill 的发现、加载时机、需求检查和版本管理
**核心关切**：
- 关切 1：加载时机——全部预加载 vs 渐进式按需加载
- 关切 2：需求检查——skill 依赖的 CLI 工具或环境变量不可用时如何处理
- 关切 3：工作区覆盖——用户自定义 skill 如何覆盖内置 skill
**nanobot 的解法**：双层发现（workspace 优先覆盖 built-in），渐进式加载（系统提示词含摘要 XML，完整内容按需 read_file），需求检查前置
**源码证据**：nanobot/agent/skills.py:23-229
**来源 Entity**：skills-loader
**层级**：架构决策

---

## 如何让主 Agent 委托后台子 Agent 执行复杂任务

**问题陈述**：Agent 框架如果需要支持后台任务（Agent 说"帮我在后台做 X"然后继续对话），需要子 Agent 机制——问题在于子 Agent 的工具集如何限制、结果如何回传
**核心关切**：
- 关切 1：递归安全——子 Agent 不应该能再 spawn 子 Agent
- 关切 2：结果通知——子 Agent 完成后如何在正确的会话中通知用户
- 关切 3：取消支持——用户取消主任务时子 Agent 是否同步取消
**nanobot 的解法**：子 Agent 使用精简工具集（无 message/spawn 工具），通过 system 消息注入结果，按 session 跟踪支持批量取消
**源码证据**：nanobot/agent/subagent.py:42-255
**来源 Entity**：subagent-manager
**层级**：架构决策

---

## 如何保护 Agent 的 Web/Shell 工具安全

**问题陈述**：Agent 框架的 Web Fetch 工具可能被利用进行 SSRF 攻击，Shell 工具可能访问敏感文件——框架需要内置安全防护
**核心关切**：
- 关切 1：SSRF 检测的准确性和性能
- 关切 2：白名单配置的灵活性——用户可能需要访问某些内网服务
- 关切 3：工具隔离——哪些工具需要安全检查
**nanobot 的解法**：三层 SSRF 检测（URL 正则 + DNS 解析 + IP 黑名单），可配置白名单，workspace 限制和沙箱支持
**源码证据**：nanobot/security/network.py:10-50
**来源 Entity**：security-system
**层级**：架构决策

---

## 跳过的 Entity（属于实现细节）

- **nanobot-facade**：纯 facade 层，仅是依赖组装和接口简化，不涉及设计选择
- **bridge-gateway**：特定平台的适配实现（WhatsApp Node.js 桥接），不是框架级设计问题
- **cli-system**：CLI 是框架的消费者而非框架本身的设计决策，交互式 Shell 的实现方式不影响框架架构
- **api-server**：OpenAI-compatible API 是标准协议适配，不涉及独立设计空间
- **config-system**：配置管理本质是实现细节——JSON + env override 是 Python 生态的常规做法，provider 匹配逻辑虽精巧但属于实现
