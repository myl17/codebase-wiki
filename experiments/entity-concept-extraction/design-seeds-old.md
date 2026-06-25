# 设计选择种子库

> 最后更新：2026-06-16 — nanobot 交叉审查完成，10 个 Concept 涌现（+3：子系统组装与连线方式、上下文窗口治理策略、技能/知识注入的加载策略）。nanobot 15 条设计选择合并入库，6 条反向检查补充

---

## Architecture

### 控制平面与执行层分离

**维度**：Architecture
**问题陈述**：如何划分「网络入口层」和「AI 执行层」的职责边界？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | Gateway 纯路由，不执行 AI 调用 | Gateway 只处理 HTTP 路由、session 和认证，AI 调用完全在 Agent Harness 层发生 |

**Concept 状态**：仅 openclaw—待观察

---

### 工具权限门控时机

**维度**：Architecture
**问题陈述**：如何决定工具权限检查发生在执行前（同步门控）还是执行后（事后审计）？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 消息处理关键路径上做同步门控，工具在进入 LLM 前已过滤 | tool-policy-pipeline 在 LLM function-calling 之前过滤工具集，exec 类工具异步阻塞等待人工审批 |

**Concept 状态**：仅 openclaw—待观察

---

### 高风险操作的人机审批协议

**维度**：Architecture
**问题陈述**：如何处理 AI 请求执行高风险操作（如 shell 命令）时的人类授权？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 全量人工审批：exec 类工具注册异步审批协议，阻塞等待 owner 决策后才执行 | ExecApprovalRequest 阻塞 agent 执行，支持 host / gateway 双路径审批，实现「请求许可」而非「请求原谅」 |

**Concept 状态**：已升级 → [[concept/approval-grading-strategy|高风险操作审批的分级策略]]（openclaw 方案 A：全量人工审批 vs hermes 方案 B：三层智能分级）

---

### 命令审批架构

**维度**：Architecture
**问题陈述**：如何在命令执行前做风险评估和用户审批？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 三层审批（YOLO → Smart LLM → Manual） | 中间层用辅助 LLM 自动判断明显安全/危险，只有模糊情况升级到人工；降低用户审批疲劳 |

**Concept 状态**：已升级 → [[concept/approval-grading-strategy|高风险操作审批的分级策略]]（hermes 方案 B：三层智能分级 vs openclaw 方案 A：全量人工审批）

---

### Gateway 审批阻塞策略

**维度**：Architecture
**问题陈述**：消息平台场景下，危险命令需要用户审批时 agent 如何等待？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | agent 线程阻塞等待 | FIFO 队列 + threading.Event，agent 线程阻塞直到用户发送 /approve 或 /deny；不超时自动拒绝 |

**Concept 状态**：仅 hermes—待观察。参考 [[concept/approval-grading-strategy|高风险操作审批的分级策略]] 中 hermes 的审批架构

---

### 安全拦截实现方式

**维度**：Architecture
**问题陈述**：如何可靠地拦截高危操作？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 正则模式列表 + LLM 判断结合 | 25+ 危险模式正则（确定性拦截已知攻击向量）+ Smart Approval（LLM 判断上下文风险）；正则是主防线 |
| nanobot | 输入前过滤（最低侵入性） | 在消息进入 LLM 前做输入安全检查（敏感词过滤）；不修改 tool 执行流程；不实现审批机制 |

**Concept 状态**：hermes + nanobot 异向（hermes 多层防护 vs nanobot 轻量输入过滤）

---

### 记忆注入时机：组装时 vs 实时查询

**维度**：Architecture
**问题陈述**：记忆系统应在 prompt 组装阶段一次性注入，还是允许 agent 在对话中实时按需检索？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | prompt 组装阶段注入（`before_prompt_build` hook），非实时 | 记忆在 LLM 调用前稳定存在，避免消耗额外 LLM 调用；代价是无法在对话中途动态补充记忆 |
| hermes | prompt 组装阶段注入（异步预取，下一轮使用上一轮缓存） | 后台异步触发预取不阻塞 LLM API 调用；核心选择与 openclaw 一致（组装时注入而非实时检索），区别在于预取时机（同步 vs 异步） |
| nanobot | ContextBuilder 组装时注入（MEMORY.md 作为六层拼接的第三层） | 记忆在组装 system prompt 时固定注入，不在对话中动态检索；与 openclaw/hermes 同向：组装时注入而非实时查询 |

**Concept 状态**：待观察（三仓库同向：组装时注入）

---

### 记忆预取时机

**维度**：Performance Tradeoffs
**问题陈述**：何时触发记忆预取，同步还是异步？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 后台异步预取，下一轮使用上一轮缓存 | 当前 turn 完成后后台触发预取，下一轮 prefetch() 返回缓存结果；不阻塞 LLM API 调用，代价是记忆落后一轮 |
| nanobot | 独立 asyncio task 异步压缩，独立 provider 实例 | Consolidator 使用独立 LLM provider 实例（不共享主 agent 的连接），`asyncio.create_task()` 异步运行；压缩失败不阻塞主循环，结果在下一轮生效 |

**Concept 状态**：仅 hermes + nanobot—待观察

---

### 内置记忆与外部记忆关系

**维度**：Architecture
**问题陈述**：外部记忆插件是替换还是叠加内置记忆？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 加性叠加（最多 1 个外部 provider） | BuiltinMemoryProvider 始终启用不可移除，外部 provider 是额外增强；保证基础功能不依赖外部服务 |

**Concept 状态**：已升级 → [[concept/memory-backend-composition|记忆后端的替换与叠加策略]]（hermes 方案 B：加性叠加 vs openclaw 方案 A：独占可替换）

---

### 定时触发的 Agent Session 隔离

**维度**：Architecture
**问题陈述**：Cron 定时触发的 agent 运行应复用现有对话 session 还是创建独立 session？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | isolated-agent 模式：每次 cron 触发创建独立 agent session | 避免 cron 输出污染用户对话历史；代价是无法在 cron 触发中访问对话上下文 |

**Concept 状态**：仅 openclaw—待观察

---

### 自学习行为触发机制

**维度**：Architecture
**问题陈述**：如何让 agent 在完成任务后积累技能和记忆？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 人类编写，静态文件 | Skills 以纯 Markdown 文件由人类预先编写，通过 hook 注入 system prompt；agent 只能使用技能，不能创建或修改 |
| hermes | prompt 驱动指令 | 三段 system prompt 指令（MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE）让 LLM 在任务完成后自主触发工具调用，无需人类干预 |

**Concept 状态**：已升级 → [[concept/skill-source-and-lifecycle|技能来源与生命周期]]（openclaw 方案 A：人类编写静态文件 vs hermes 方案 B：Agent 自主创建与维护）

---

### 技能存储与注入方式

**维度**：Architecture
**问题陈述**：如何存储和注入 agent 积累的技能？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | markdown 文件全量注入 system prompt | 技能以 SKILL.md 文件存储，每次会话启动时全量注入 system prompt；不使用向量检索按相关性按需注入 |
| nanobot | 混合策略：always 全文 + 其余 XML 摘要 + 按需 read_file | always 标记的技能全文注入 ContextBuilder 第四层；其余技能以 XML 摘要注入第五层；agent 通过 read_file 工具按需加载；frontmatter requires 过滤不可用技能 |

**Concept 状态**：已升级 → [[concept/skill-injection-strategy|技能/知识注入的加载策略]]（openclaw 方案 A：全量注入 vs nanobot 方案 C：混合策略）。另见 [[concept/skill-source-and-lifecycle|技能来源与生命周期]]

---

### 中央编排器设计

**维度**：Architecture
**问题陈述**：如何设计 agent 的核心执行单元？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 单一中央编排器 AIAgent | 单个 AIAgent 类管理完整 tool-calling 循环，集中处理 failover、子 agent 委派、iteration budget |
| nanobot | 单体 Hub 构造函数 | AgentLoop.__init__() 在一个构造函数中实例化并注入所有子系统——极致的可发现性：「这个系统有什么」读一个函数即可 |

**Concept 状态**：已升级 → [[concept/subsystem-wiring-pattern|子系统组装与连线方式]]（openclaw 方案 A：Plugin API DI vs hermes 方案 B：中央编排器 vs nanobot 方案 C：单体 Hub 构造函数）

---

### 跨消息 Agent 实例复用

**维度**：Architecture
**问题陈述**：Gateway 场景下，每条消息是否需要新建 AIAgent 实例？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 实例缓存复用 | GatewayRunner 跨消息缓存 AIAgent 实例，以维持 LLM API 的 prompt cache prefix 跨消息有效 |

**Concept 状态**：已升级 → [[concept/prompt-cache-maintenance|Prompt Cache 维护策略]]（hermes 方案 B：会话复用 vs openclaw 方案 A：内容锚定）

---

### 平台适配器接口

**维度**：Architecture
**问题陈述**：如何支持 20+ 消息平台的接入？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 13+ 细粒度 Adapter 接口 | `ChannelPlugin<ResolvedAccount>` 组合 13+ 独立 Adapter 接口（Messaging/Outbound/Lifecycle/Auth/Setup 等），各 channel 按需实现子集，懒加载 |
| hermes | 统一 ABC + 16 步 checklist | 所有平台通过 BasePlatformAdapter ABC 统一接口；新增平台需修改 16 处配置点，确保所有集成点感知到新平台 |

**Concept 状态**：已升级 → [[concept/platform-adapter-interface-granularity|平台适配接口粒度]]（openclaw 方案 A：细粒度 Adapter 接口 vs hermes 方案 B：统一 ABC + Checklist）

---

### 工具自动发现机制

**维度**：Architecture
**问题陈述**：新工具如何被系统发现和注册？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 显式 API 注册 | `OpenClawPluginApi` 提供 25 个注册方法，plugin 在入口文件中命令式调用 API 手动注册每个工具和能力 |
| hermes | AST 扫描自动发现 | 扫描所有模块顶层的 registry.register() 调用，新工具只需创建文件并调用注册，无需修改任何现有文件 |

**Concept 状态**：已升级 → [[concept/tool-registration-discovery|工具注册与发现方式]]（openclaw 方案 A：显式 API 注册 vs hermes 方案 B：AST 自动发现）

---

### 工具注册中心单例

**维度**：Architecture
**问题陈述**：工具注册中心应该是全局单例还是每个 agent 实例独立？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 全局单例 + RLock | ToolRegistry 全局唯一，RLock 线程安全；MCP 动态刷新需要权威的单一注册中心 |
| nanobot | 单实例（AgentLoop 持有），非全局单例 | ToolRegistry 是 `dict[name, Tool]` 的薄封装，由 AgentLoop 构造并持有；不做 AST 扫描、不做装饰器收集、不做模块自省 |

**Concept 状态**：仅 hermes + nanobot—待观察。另见 [[concept/tool-registration-discovery|工具注册与发现方式]]

---

### 日志脱敏实现

**维度**：Architecture
**问题陈述**：如何防止 API key 被写入日志？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 写入时实时脱敏（40+ 前缀模式） | 日志写入时自动识别并脱敏 40+ 种 API key 前缀，密钥永不落盘；不依赖开发者手动避免记录敏感信息 |

**Concept 状态**：仅 hermes—待观察

---

### AgentRunner 产品层零耦合

**维度**：Architecture
**问题陈述**：执行引擎是否应该感知产品层上下文（channel 类型、会话状态、cron 触发源）？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | AgentRunner 完全产品层无关——不持有 channel/session/cron 引用，只接受 messages 和 tool_registry 作为纯数据输入 | 同一 AgentRunner 实例同时服务主 agent、子 agent、Dream 三种场景；代价是牺牲产品层感知能力，无法根据 channel 类型调整行为 |

**Concept 状态**：仅 nanobot—待观察。参见 [[concept/subsystem-wiring-pattern|子系统组装与连线方式]] 中 nanobot 的单体 Hub 模式

---

### ContextBuilder 纯数据转换层

**维度**：Architecture
**问题陈述**：系统 prompt 组装器应该与 agent 循环耦合还是设计为纯数据转换？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | ContextBuilder 是纯数据到文本的转换层——不调用 LLM、不管理工具、不持有运行时引用 | 六层固定拼接顺序使 system prompt 可独立于 AgentLoop 测试和调试；代价是无法根据运行时状态动态调整 prompt 结构 |

**Concept 状态**：仅 nanobot—待观察。六层拼接顺序也是 prompt cache 稳定性的支撑——见 [[concept/prompt-cache-maintenance|Prompt Cache 维护策略]]

---

### MCP 惰性连接 + 动态工具注入

**维度**：Architecture
**问题陈述**：MCP server 应在 agent 启动时连接还是惰性按需连接？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | AgentLoop.__init__() 结束前 `_connect_mcp()` 惰性连接，工具以 `mcp_` 前缀动态注入，AsyncExitStack 管理生命周期 | MCP 工具定义附加在 builtin 工具排序之后，保持 prompt cache 前缀稳定 |

**Concept 状态**：仅 nanobot—待观察

---

### Tool Error 策略：Non-Fatal vs Fatal

**维度**：Architecture
**问题陈述**：工具执行错误应该终止 agent 还是记录后继续？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | 默认 non-fatal（记录错误继续），子 agent 中为 fatal（立即终止） | 主 agent 容错优先——一个工具失败不应该终止整个会话；子 agent 中快速失败防止资源浪费 |

**Concept 状态**：仅 nanobot—待观察

---

## Performance Tradeoffs

### Context 压缩的优化目标

**维度**：Performance Tradeoffs
**问题陈述**：上下文压缩时，应优先最大化压缩率还是优先保留任务可恢复性？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 可恢复性优先：保留活跃任务状态、批处理进度、最后一次用户请求 | 代价是压缩后剩余 token 更多，换来 agent 在压缩后能无缝继续执行未完成任务 |
| nanobot | 四层透明治理：Backfill + Microcompact + Budget + Snip，每次 LLM 调用前自动执行 | 渐进式微清理代替一次性大压缩；治理对 LLM 透明；代价是四层逻辑复杂，Microcompact 丢失旧 tool result 完整内容 |

**Concept 状态**：已升级 → [[concept/context-window-governance|上下文窗口治理策略]]（openclaw 方案 A：单一压缩 vs nanobot 方案 C：四层透明治理）。另见 [[concept/context-compression-trigger|上下文压缩的触发机制]]

---

### Prompt Caching 的结构化支持

**维度**：Performance Tradeoffs
**问题陈述**：如何在 system prompt 设计中主动支持 LLM API 的 Prompt Caching 能力？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 在 system prompt 插入 CACHE_BOUNDARY 标记，切分稳定前缀（命中缓存）和动态后缀（不影响缓存） | 稳定部分打 `cache_control: ephemeral`，每轮 token 输入成本显著降低；代价是 system prompt 结构复杂度上升 |

**Concept 状态**：已升级 → [[concept/prompt-cache-maintenance|Prompt Cache 维护策略]]（openclaw 方案 A：内容锚定 vs hermes 方案 B：会话复用）

---

### 启动性能 vs 内存占用取舍

**维度**：Performance Tradeoffs
**问题陈述**：如何在启动速度和运行时内存占用之间取舍？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 优先冷启动速度：Compile Cache + Lazy Module + Channel 按需加载，代价是多个运行时 Promise 缓存占用内存 | 个人工具频繁启动，冷启动体验是一等公民；内存代价可接受 |

**Concept 状态**：仅 openclaw—待观察

---

### 并行工具执行策略

**维度**：Performance Tradeoffs
**问题陈述**：多个工具调用是否可以并行执行？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 条件并行（8 线程上限） | 只读工具并行，破坏性命令（rm/mv/sed -i 等）和交互式工具强制串行；路径不重叠的文件操作可并行 |

**Concept 状态**：仅 hermes—待观察

---

### Iteration Budget（迭代预算）

**维度**：Performance Tradeoffs
**问题陈述**：如何防止 agent 在复杂任务上无限循环消耗 token？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 硬上限 + 不向 LLM 注入警告 | 父 agent 90 轮、子 agent 50 轮硬上限；耗尽时一次 grace call；预算信息不注入 LLM 以防提前放弃 |
| nanobot | max_iterations 硬上限 + 不由 LLM 感知 | AgentRunner.run() 的 `for iteration in range(spec.max_iterations)`；上限在 AgentRunSpec 中由 AgentLoop 决定；上限耗尽直接退出循环，无 grace call |

**Concept 状态**：hermes + nanobot 同向：硬上限，不向 LLM 注入

---

### ContextBuilder 六层固定拼接顺序

**维度**：Performance Tradeoffs
**问题陈述**：system prompt 的拼接顺序应固定还是动态调整？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | 六层固定顺序：identity → bootstrap files → memory → always skills → skills summary → recent history | 固定顺序确保 prompt cache 前缀稳定——只要 bootstrap files 和 skills 不变，system prompt 前缀就不变；各层用 `---` 分隔 |

**Concept 状态**：仅 nanobot—待观察。另见 [[concept/prompt-cache-maintenance|Prompt Cache 维护策略]]

---

### Provider 三级重试 + 429 分类

**维度**：Performance Tradeoffs
**问题陈述**：LLM API 调用失败后应如何重试？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | standard 模式 3 次指数退避；persistent 模式无限制但相同错误超限停止；429 分类：配额耗尽（不重试）vs 速率限制（重试+等待） | 从 error type/code 和响应文本两个路径提取 429 分类信息，比仅依赖 HTTP status code 更可靠 |

**Concept 状态**：仅 nanobot—待观察

---

### 图片降级策略

**维度**：Performance Tradeoffs
**问题陈述**：图片内容导致 API 错误时如何处理？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | 自动降级为纯文本重试 | 图片内容导致的错误自动移除图片后重试，不丢失整轮内容；对 LLM 透明 |

**Concept 状态**：仅 nanobot—待观察

---

### 审批结果持久化

**维度**：Performance Tradeoffs
**问题陈述**：用户的审批决定是否应该跨会话生效？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 三级持久化（once/session/always） | always 级别写入 config.yaml allowlist，跨会话永久生效；代价是需要人工维护 allowlist |

**Concept 状态**：仅 hermes—待观察

---

### 上下文压缩触发机制

**维度**：Performance Tradeoffs
**问题陈述**：上下文压缩何时触发——按绝对 token 阈值还是按窗口百分比？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 硬 token 阈值（16000/32000） | hard limit 16000 tokens + soft warning 32000 tokens，固定常数，不随模型 context window 变化 |
| hermes | 动态窗口百分比（75%/85%/95%） | 75% 触发压缩，85%/95% 各通知用户一次；自动适配不同模型的 context window 大小；压缩失败退避冷却 600 秒 |

**Concept 状态**：已升级 → [[concept/context-compression-trigger|上下文压缩的触发机制]]（openclaw 方案 A：硬 token 阈值 vs hermes 方案 B：动态窗口百分比）

---

## Extension Points

### 可替换记忆后端设计

**维度**：Extension Points
**问题陈述**：记忆存储后端应内置固定，还是设计为可替换的独占槽位？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | `registerMemoryCapability` 独占槽位，支持 SQLite-vec（内置）/ LanceDB / 外部引擎替换 | 不同部署环境需求差异大，独占可替换保证默认开箱即用同时支持高级用户接入专业向量数据库 |

**Concept 状态**：已升级 → [[concept/memory-backend-composition|记忆后端的替换与叠加策略]]（openclaw 方案 A：独占可替换 vs hermes 方案 B：加性叠加）

---

### LLM Provider 选择机制

**维度**：Extension Points
**问题陈述**：系统应通过配置明确指定 LLM provider，还是通过策略模式让 provider 自主声明适用场景？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 策略模式：`supports(ctx)` + priority 排序，selectAgentHarness() 选第一个匹配的实现 | 新 provider 无需修改 core，只需实现 `supports()` 声明适用条件；代价是调试时 provider 选择逻辑不直观 |
| nanobot | ProviderSpec 数据表驱动 + 自动检测 | `PROVIDERS` 元组维护 20+ 供应商的 ProviderSpec（key 前缀、base URL 关键词、gateway/label 检测）；五种 backend（openai_compat/anthropic/azure_openai/openai_codex/github_copilot）；支持 `supports_prompt_caching` 标记 |

**Concept 状态**：openclaw + nanobot—待观察

---

### 独占 vs 多实现并存的扩展槽位设计

**维度**：Extension Points
**问题陈述**：Context Engine 和 Memory Capability 等核心扩展点应允许多实现并存还是设计为独占槽位？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 独占槽位：`registerContextEngine` 和 `registerMemoryCapability` 全局只能有一个活跃实现 | 避免多实现并存时的状态冲突，迫使使用者明确选择一个实现；代价是不支持运行时切换或组合 |

**Concept 状态**：仅 openclaw—待观察

---

### 零代码扩展层（Skills / Markdown）

**维度**：Extension Points
**问题陈述**：是否提供无需编写代码的 agent 行为定制机制？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 纯 Markdown Skills 文件，通过 hook 注入 system prompt，零代码即可定制 agent 行为 | 大幅降低普通用户扩展门槛；代价是能力上限受限（无法访问运行时 API） |
| hermes | markdown 文件全量注入 system prompt（实现方式相同） | 技能以 SKILL.md 文件存储，每次会话启动时全量注入；与 openclaw 的选择方向一致 |
| nanobot | Markdown 文件 + always/progressive 双策略 + requires 依赖过滤 | 内建 `nanobot/skills/` 和用户 `workspace/skills/` 双路径；`always: true` 全文注入，其余 XML 摘要 + 按需 read_file；`requires.bins/env` 自动过滤不可用技能 |

**Concept 状态**：三仓库同向（Markdown 注入）。细节差异已升级至 [[concept/skill-injection-strategy|技能/知识注入的加载策略]] 和 [[concept/skill-source-and-lifecycle|技能来源与生命周期]]

---

### 双路径技能存储与覆盖

**维度**：Extension Points
**问题陈述**：内建技能和用户自定义技能应如何共存？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | 双路径 + 用户覆盖内建：`nanobot/skills/`（内建）+ `workspace/skills/`（用户自定义，可覆盖同名内建技能） | 保证发行版自带技能不被用户删除，同时允许用户自定义覆盖 |

**Concept 状态**：仅 nanobot—待观察。另见 [[concept/skill-injection-strategy|技能/知识注入的加载策略]]

---

### Skills requires 依赖自动过滤

**维度**：Extension Points
**问题陈述**：环境不满足的技能是否应该注入 system prompt？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | frontmatter `requires.bins` 和 `requires.env` 自动过滤——不满足条件的技能标记为不可用，不出现在 XML 摘要中 | 防止 agent 尝试使用环境不支持的工具；代价是开发者需主动声明依赖 |

**Concept 状态**：仅 nanobot—待观察

---

### Tool Schema 专用类型 vs 泛用 JSON Schema

**维度**：Extension Points
**问题陈述**：工具参数 schema 应使用泛用 JSON Schema 库还是专用类型系统？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | 专用 Schema 类型：`StringSchema`/`IntegerSchema`/`ObjectSchema` 等子类，非泛用 JSON Schema 库 | 精确控制序列化格式，与 ToolRegistry 的 `prepare_call()` 验证深度集成；代价是失去 JSON Schema 生态的互操作性 |

**Concept 状态**：仅 nanobot—待观察

---

### 内置 Channel 优先覆盖外部插件

**维度**：Extension Points
**问题陈述**：内置 channel 和外部同名插件冲突时如何处理？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | 内置优先覆盖——外部插件不能 shadow 内置 channel 名称 | 保证内置 channel 的行为不被第三方篡改；代价是外部插件无法替换内置实现 |

**Concept 状态**：仅 nanobot—待观察

---

### LLM Provider 的 supports_prompt_caching 标记

**维度**：Extension Points
**问题陈述**：provider 的能力差异（如是否支持 prompt caching）如何在注册层表达？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | ProviderSpec 中包含 `supports_prompt_caching` 布尔标记（Anthropic/OpenRouter 为 true） | 让框架在运行时感知 provider 的缓存能力；另见 [[concept/prompt-cache-maintenance|Prompt Cache 维护策略]] 中 nanobot 的方案 C |

**Concept 状态**：仅 nanobot—待观察

---

### 技能生命周期管理

**维度**：Extension Points
**问题陈述**：技能过时后如何更新？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | agent 自主 patch | skill_manage 支持 patch 操作，agent 在使用中发现技能过时就立即就地修复，不依赖人类手动维护 |
| openclaw | 人类手动维护 | Skills 是静态 Markdown 文件，内容完全由人类控制，不存在 agent 自主修改技能的机制 |

**Concept 状态**：已升级 → [[concept/skill-source-and-lifecycle|技能来源与生命周期]]（hermes 方案 B：Agent 自主创建与维护 vs openclaw 方案 A：人类编写静态文件）

---

## Dependency Strategy

### Channel 依赖隔离策略

**维度**：Dependency Strategy
**问题陈述**：多 IM 平台的 SDK 应集中安装在 root 还是各自独立在子包中？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 每个 channel 是独立 npm 包，只声明自己需要的 SDK | 故障域完全隔离，任何单个 channel SDK 变动不影响核心运行时；代价是 monorepo 管理复杂度上升 |
| nanobot | 每个 channel 是独立 Python 模块（`channels/telegram.py` 等），SDK 通过 pip extras 按需安装 | 各模块只 import 自己需要的 SDK；pip extras 按需安装（`pip install nanobot-ai[telegram,discord]`）；代价是 extras 组合管理复杂度 |

**Concept 状态**：openclaw + nanobot 同向：独立模块 + 按需依赖

---

### 核心 AI 引擎的深度依赖取舍

**维度**：Dependency Strategy
**问题陈述**：AI agent 引擎层应自研还是深度依赖外部包族？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 深度依赖 `@mariozechner/*`（442 处 import，精确锁定 0.66.1） | 快速复用成熟引擎，代价是替换成本极高，受上游版本节奏约束 |
| nanobot | 移除 litellm 转发层，使用原生 `openai` + `anthropic` SDK（3,719 行自维护适配代码） | 换来完全的行为可控和零间接供应商依赖；代价是自行维护 20 个 provider 的适配代码，无法享受 litellm 的 30+ provider 开箱即用 |

**Concept 状态**：openclaw + nanobot 异向（openclaw 深度依赖外部引擎，nanobot 自维护）

---

### 外部技能安全扫描

**维度**：Dependency Strategy
**问题陈述**：如何防止外部来源的技能携带恶意代码？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 安装前静态扫描 + 四级信任策略 | 100+ 威胁模式覆盖 12 类风险，按 builtin/trusted/community/agent-created 信任级别区分审查严格度 |

**Concept 状态**：仅 hermes—待观察

---

### 技能安装隔离机制

**维度**：Dependency Strategy
**问题陈述**：外部技能在扫描期间是否需要隔离？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 隔离区暂存 | 技能下载到 quarantine/ 目录，扫描通过后才移出安装；扫描失败直接删除隔离区文件 |

**Concept 状态**：仅 hermes—待观察

---

### 依赖版本锁策略

**维度**：Dependency Strategy
**问题陈述**：如何确保可重复构建？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 三层版本锁（范围锁 + uv.lock + Docker SHA256） | pyproject.toml 范围锁 + uv.lock 全依赖树 hash 锁 + Docker 基础镜像 SHA256 固定；三层防护确保可重复 |

**Concept 状态**：仅 hermes—待观察

---

### 可选依赖降级策略

**维度**：Dependency Strategy
**问题陈述**：可选功能缺失时系统如何响应？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | ImportError → 优雅降级，绝不崩溃 | 所有 20+ 可选依赖缺失时自动跳过对应功能，不报错；web 搜索多后端回退、vision 忽略、MCP debug 日志 |

**Concept 状态**：仅 hermes—待观察

---

## Testing Philosophy

### 架构边界守护：Lint 脚本 vs 运行时检查

**维度**：Testing Philosophy
**问题陈述**：层间依赖边界约束应通过静态分析（lint）还是运行时检查来守护？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 20+ 个专项 lint 脚本将架构边界约束变成可执行代码，CI 失败即违规 | 静态分析在 CI 阶段捕获违规，不需要运行时开销；代价是 lint 脚本本身需要维护 |

**Concept 状态**：仅 openclaw—待观察

---

### 性能预算作为 CI 一等公民

**维度**：Testing Philosophy
**问题陈述**：启动性能应作为可量化指标纳入 CI 还是依赖人工感知？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 专用 fixture 基线 + `test:startup:bench:check` CI 检查，超出 budget 即失败 | 启动性能有明确量化约束，防止悄悄劣化；代价是需要维护基线 fixture 文件 |

**Concept 状态**：仅 openclaw—待观察

---

### Plugin 接口契约测试的自动化覆盖

**维度**：Testing Philosophy
**问题陈述**：plugin 接口兼容性测试应由 plugin 作者手写还是由 framework 自动覆盖？

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | 共享 test suite（`installChannelActionsContractSuite`）+ 自动注册，新 plugin 加入 registry 即自动被契约测试覆盖 | 保证接口一致性，降低新 plugin 测试门槛；代价是 test suite 本身是共享基础设施，需要稳定维护 |

**Concept 状态**：仅 openclaw—待观察

---

### 测试隔离机制

**维度**：Testing Philosophy
**问题陈述**：如何防止测试写入真实用户目录或调用真实 API？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | autouse fixture 强制隔离 + 30 秒硬超时 | _isolate_hermes_home 将 HERMES_HOME 重定向到 tmp_path，清除 API key 环境变量，重置单例；30 秒 SIGALRM 硬超时防测试挂起 |

**Concept 状态**：仅 hermes—待观察

---

### 集成测试比例

**维度**：Testing Philosophy
**问题陈述**：单元测试与集成测试应该如何分配？

| 仓库 | 选择 | 简述 |
|------|------|------|
| hermes | 重单元轻集成（1-2% 集成测试） | 578 文件单元测试为主，8 个集成测试文件 + 3 个 e2e 文件；默认 CI 排除集成/e2e，快速反馈优先 |

**Concept 状态**：仅 hermes—待观察

---

### 纯函数式组件的独立可测试性

**维度**：Testing Philosophy
**问题陈述**：核心组件是否应设计为可以脱离 AgentLoop 独立测试？

| 仓库 | 选择 | 简述 |
|------|------|------|
| nanobot | ContextBuilder 不依赖 AgentLoop 或任何运行时状态——可独立构造输入进行单元测试 | 纯数据到文本的转换层使 system prompt 组装逻辑可以独立验证，不需要启动完整 agent |

**Concept 状态**：仅 nanobot—待观察
