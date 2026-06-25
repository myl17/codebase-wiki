# OpenClaw — 系统表征

## 这个系统是什么

OpenClaw 是一个自托管的个人 AI 助手运行时：你在自己的设备上运行它，通过你已在用的 IM 平台（WhatsApp、Telegram、Slack 等 20+ 种）与它对话，由此获得一个私有的、可扩展的 AI 助手。

## 核心子系统

- **Process Supervisor**：CLI 入口 + 进程看门狗，管理子进程生命周期和 respawn 策略；不负责 AI 调用或业务逻辑
- **Gateway**：纯 HTTP 控制平面，处理路由、会话和认证；不持有任何 AI 调用逻辑
- **Channel Plugin 系统**：20+ IM 平台适配层，标准化入站/出站消息；不决定 AI 如何响应
- **Tool Policy / 权限管理**：多层工具可见性过滤 + exec 异步审批协议；不执行工具本身
- **Agent Harness**：LLM 提供商抽象层，统一调用接口；不管理对话上下文
- **Context Engine**：对话上下文生命周期管理（组装、摄入、压缩、重写）；不直接调用 LLM
- **Memory 系统**：向量化记忆存储与检索；不决定何时注入记忆（由 hook 系统驱动）
- **Tasks + Cron 调度**：TaskFlow 状态机 + 定时触发；Cron 是唯一无消息触发 agent 的入口
- **OTel 可观测性**：可选的 OpenTelemetry 三路并行导出；不在核心依赖路径上

## 关键机制

**插件系统三层架构**：`definePluginEntry` / `defineBundledChannelEntry` 入口文件 + `OpenClawPluginApi`（25 个注册方法）+ 28 个生命周期 hook，外加纯 Markdown 的 Skills 文件作为零代码第三层。这套设计使得 LLM provider、IM channel、记忆后端、上下文引擎实现等全部通过统一插件协议接入，core 对这些实现透明。

**工具权限同步门控**：权限决策发生在消息处理的关键路径上（非事后审计）。`tool-policy-pipeline` 在 LLM 调用前对工具集做 5 层叠加过滤（profile / provider / global / agent / group），exec 类工具还需经过异步审批协议（阻塞等待 owner 确认），两者合力构成一个「先授权后执行」的安全模型。

**Prompt Cache Boundary**：system prompt 通过 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记切分为稳定前缀和动态后缀，稳定部分打上 Anthropic `cache_control: ephemeral` 标记，在 API 层命中 Prompt Caching，将每轮的 token 输入成本降到最低；动态内容（记忆注入、实时上下文）插在边界后不影响缓存命中。

**Context 压缩可恢复性优先**：上下文接近窗口上限时，摘要指令优先保留活跃任务状态、批处理进度和最后一次用户请求，而非追求最高压缩率。代价是摘要后可能保留更多 token，换来的是 agent 在压缩后仍能无缝继续执行未完成任务。

## 明确不做什么

- 不是云服务：无托管后端，不在用户设备之外持有数据
- Gateway 不执行 AI 调用，只是路由层
- 不直接管理 IM SDK 集成：每个 channel 是独立 npm 包，独立依赖，故障域完全隔离
- 不强制单一 LLM 提供商：provider 通过 `registerAgentHarness` 插件化接入
- OTel 可观测性不在默认安装中：需显式安装 `diagnostics-otel` 扩展
