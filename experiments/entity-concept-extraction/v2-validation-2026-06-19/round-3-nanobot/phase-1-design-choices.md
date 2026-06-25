# nanobot 架构级设计选择

> 从 nanobot 的 5 个维度叙事页独立提取。未参考任何其他仓库的分析结果。

---

## 如何组装所有子系统？

**维度**：Architecture
**问题陈述**：如何在单个构造函数中集中组装 10+ 子系统（provider、bus、context、tools、runner、subagents、consolidator、dream、sessions、cron、heartbeat、MCP），同时保持代码可理解？
**核心关切**：
- 关切 1：**可发现性**——所有连线逻辑集中在一个文件的单个函数中，读一个构造函数就能完整理解系统组成
- 关切 2：**可测试性牺牲**——集中式组装意味着没有 DI 容器，无法对单个子系统做独立单元测试，AgentLoop 成为单一故障集中点
- 关切 3：**启动耦合**——所有子系统在启动时一次性初始化，无法按需延迟加载

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **单体 Hub 集中组装** | AgentLoop.__init__() 作为唯一架构入口，在一个方法中实例化并注入所有子系统 | nanobot-architecture.md:1. AgentLoop → agent/loop.py:115-228 |

**层级**：层 3 架构决策

---

## 如何在不同 agent 上下文中复用执行引擎？

**维度**：Architecture
**问题陈述**：如何让同一套 tool-calling 循环引擎同时服务主 agent、子 agent 和 Dream 记忆处理，而不让引擎依赖任何产品层概念？
**核心关切**：
- 关切 1：**引擎复用**——AgentRunner 不 import channel、session、cron 等产品层模块，只关心「收消息 → 调 LLM → 执行工具」，实现一次编写三处复用
- 关切 2：**上下文盲区**——AgentRunner 不知道自己在为主 agent 还是子 agent 服务、不知道 channel 类型、不知道会话状态，无法根据上下文调整行为
- 关切 3：**职责分离**——所有产品层逻辑（session 管理、channel 路由、hook 注入、command 优先级）都在 AgentLoop 层处理，AgentRunner 只管纯粹的 LLM 交互循环

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **产品层无关的纯执行引擎** | AgentRunner 接受 AgentRunSpec 纯数据配置，与产品层零耦合，同时驱动主 agent、子 agent、Dream Phase 2 | nanobot-architecture.md:2. AgentRunner → agent/runner.py:83-97; agent/loop.py:300-355; agent/subagent.py:140-150; agent/memory.py:519+ |

**层级**：层 3 架构决策

---

## 如何在 AgentRunner 内管理 LLM 上下文窗口？

**维度**：Performance Tradeoffs
**问题陈述**：如何在不依赖 LLM 自身能力的前提下，在每次 LLM 调用前自动治理上下文——修复不完整数据、压缩旧内容、截断超长结果、裁剪超预算历史——同时不告知 LLM 这些操作的发生？
**核心关切**：
- 关切 1：**对 LLM 透明**——四层治理全部在 AgentRunner 内部完成，LLM 不知道上下文被裁剪过、不知道某些 tool result 已被替换为摘要，避免了 LLM 提前放弃任务
- 关切 2：**LLM 策略盲区**——LLM 无法主动调整自己的对话策略来适应有限的上下文，因为它不知道上下文已被压缩
- 关切 3：**关键路径性能**——四步治理在每次 LLM 调用的关键路径上自动运行（Backfill → Microcompact → Budget → Snip），任何一步出错都可能导致 LLM 看到损坏的上下文

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **四步透明上下文治理** | Backfill（修复孤立 tool_use）+ Microcompact（压缩 10 轮前的 tool result）+ Tool Result Budget（截断超长结果）+ Snip History（按 token 预算从尾部裁剪），全部对 LLM 透明 | nanobot-performance-tradeoffs.md:1. Context Governance → agent/runner.py:552-697 |

**层级**：层 3 架构决策

---

## 如何解耦 Channel 层与 Agent 核心？

**维度**：Architecture
**问题陈述**：如何让不同的 IM Channel（Telegram、Discord、微信等 14+）与 Agent 核心完全解耦，使新增 Channel 不需要修改 AgentLoop 的任何代码？
**核心关切**：
- 关切 1：**接口统一**——Channel 只操作 `publish_inbound()`/`consume_outbound()`，AgentLoop 只操作 `consume_inbound()`/`publish_outbound()`，双方只通过队列交互
- 关切 2：**异步解耦**——使用 `asyncio.Queue` 而非同步调用，Channel 和 AgentLoop 各自独立运行，生产消费速率解耦
- 关切 3：**排队语义**——队列引入消息缓冲和潜在延迟，不适合需要同步响应的场景

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **MessageBus 异步队列解耦** | 使用 asyncio.Queue 将 Channel 层与 Agent 核心完全解耦，双方只操作统一的消息队列接口 | nanobot-architecture.md:3. MessageBus → bus/queue.py:8-35 |

**层级**：层 3 架构决策

---

## 如何将子 agent 和调度事件的结果注入主 agent 处理流？

**维度**：Architecture
**问题陈述**：子 agent 完成结果、Cron 触发消息、Heartbeat 唤醒消息如何进入主 agent 的处理流程——应该走独立路径还是复用现有路径？
**核心关切**：
- 关切 1：**处理统一性**——子 agent 结果通过 `bus.publish_inbound()` 注入入站队列，与 Telegram/Discord 消息走完全相同的消费路径，AgentLoop 不需要区分消息来源
- 关切 2：**语义丢失**——子 agent 结果和 IM 消息在系统中没有任何语义区别，无法对不同来源的消息做差异化路由或优先级
- 关切 3：**架构简化**——统一入站路径避免了多条处理管线的维护成本，所有入站事件的消费逻辑只有一套

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **统一 bus 注入：子 agent 结果等同于 IM 消息** | 子 agent、Cron、Heartbeat 的所有触发消息统一通过 bus.publish_inbound() 注入，复用 AgentLoop 的主消费路径 | nanobot-architecture.md:数据流 → agent/subagent.py:202-209; agent/loop.py:363-556 |

**层级**：层 3 架构决策

---

## 如何组装系统 prompt？

**维度**：Architecture
**问题陈述**：系统 prompt 由多个独立来源组成（identity、bootstrap files、memory、skills、history），如何组装这些内容使得每层可以独立修改和测试？
**核心关切**：
- 关切 1：**可测试性**——ContextBuilder 不持有 AgentLoop 引用、不调用 LLM、不管理工具，是纯数据到文本的转换层，可以独立于 AgentLoop 进行单元测试
- 关切 2：**层次独立**——六层内容（identity → bootstrap → memory → always skills → skills summary → recent history）依次拼接，每层用 `---` 分隔，修改一层不影响其他层
- 关切 3：**运行时效率**——skills 摘要支持渐进式加载（always skills 全文注入 + 其他仅在摘要中列出），避免所有技能内容塞满 system prompt

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **ContextBuilder 纯数据到文本的六层拼接** | 六层独立内容依次拼接为 system prompt，ContextBuilder 是无副作用的纯转换层 | nanobot-architecture.md:4. ContextBuilder → agent/context.py:17-63 |

**层级**：层 3 架构决策

---

## 如何注册和发现工具？

**维度**：Extension Points
**问题陈述**：工具应该被自动发现（装饰器/AST 扫描）还是显式注册——如何权衡发现便利性和注册确定性？
**核心关切**：
- 关切 1：**注册确定性**——显式 `register()` 不做 AST 扫描、不做装饰器发现，每个工具必须在 `_register_default_tools()` 中点名，不存在隐式工具被发现或遗漏
- 关切 2：**扩展成本**——每个新工具需要两步操作：创建 Tool 子类 + 在 register 处点名，相比装饰器自动发现多了一步手工操作
- 关切 3：**调试可见性**——所有已注册工具可通过 `get_definitions()` 一次性获取完整列表，工具清单是明确的而非推断的

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **显式 register() 注册，零自动发现** | 所有工具通过显式 `tool_registry.register()` 调用注册，不做 AST 扫描或装饰器发现 | nanobot-extension-points.md:1. ToolRegistry → agent/tools/registry.py:8-99; agent/loop.py:229-255 |

**层级**：层 3 架构决策

---

## 如何稳定 prompt cache 使其不被工具列表变化破坏？

**维度**：Performance Tradeoffs
**问题陈述**：Anthropic prompt cache 对 tool 定义顺序敏感——如何确保每次请求中 tool 定义的前缀部分稳定不变，使 MCP 工具的动态增删不破坏已缓存的内容？
**核心关切**：
- 关切 1：**缓存稳定性**——builtins 按名称排序放在前面作为稳定前缀，MCP 工具（`mcp_` 前缀）放在后面，只要 MCP 工具不变缓存就不会被破坏
- 关切 2：**缓存命中率**——排序策略直接决定 Anthropic prompt cache 的命中率，进而影响每次 LLM 调用的成本和延迟
- 关切 3：**工具数量敏感**——如果 builtins 数量过多，缓存前缀本身就会很大，留给 MCP 工具和消息的缓存空间会减少

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **工具定义排序：builtins 前缀 + MCP 后缀** | get_definitions() 按名称排序 builtins 在前、MCP 工具在后，构成 Anthropic prompt cache 的稳定前缀 | nanobot-performance-tradeoffs.md:3. Prompt Cache → agent/tools/registry.py:45-63 |

**层级**：层 2 技术选型

---

## 如何发现和加载 Channel 插件？

**维度**：Extension Points
**问题陈述**：如何让内置 Channel 和外部第三方 Channel 都能被自动发现，同时确保外部插件无法覆盖内置实现？
**核心关切**：
- 关切 1：**双层发现**——内置 Channel 通过 `pkgutil.iter_modules()` 自动扫描（新增 Python 文件即自动可被发现），外部 Channel 通过 Python `entry_points` 机制注册（`nanobot.channels` 组），支持 pip 可安装的第三方插件
- 关切 2：**安全边界**——内置 Channel 优先级高于外部插件，外部插件不能 shadow 同名内置 Channel，防止恶意插件替换关键 Channel 实现
- 关切 3：**无需注册文件**——内置 Channel 不需要维护显式注册表，新增模块文件即注册，降低添加新 Channel 的摩擦

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **pkgutil 自发现 + entry_points 外部插件，内置优先** | 内置 Channel 通过 pkgutil 自动发现，外部插件通过 entry_points 注册，内置实现不受外部插件覆盖 | nanobot-extension-points.md:2. Channel Plugin → channels/registry.py:17-72 |

**层级**：层 3 架构决策

---

## 如何抽象和注册 LLM provider？

**维度**：Extension Points
**问题陈述**：如何支持 20+ LLM provider 而无需为每个 provider 编写大量适配代码——如何让新增 provider 成为纯数据操作而非代码修改？
**核心关切**：
- 关切 1：**数据驱动注册**——新增 provider 只需在 `PROVIDERS` 元组中加一行 `ProviderSpec` 数据 + 在 `config/schema.py` 中加一个配置字段，所有匹配、检测、状态展示逻辑都从元组派生
- 关切 2：**统一接口**——`LLMProvider` 抽象基类定义统一的 `chat()`/`chat_stream()` 接口，子类只需实现其中一个方法，重试逻辑在基类中统一实现
- 关切 3：**覆盖范围有限**——仅支持 5 种 backend 风格（openai_compat / anthropic / azure_openai / openai_codex / github_copilot），非标准 API 风格的 provider 需要新 backend

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **数据驱动 ProviderSpec 注册表** | Provider 元数据集中在 PROVIDERS 元组中，5 种 backend 风格覆盖 20+ provider，新增 provider 是纯数据操作 | nanobot-extension-points.md:3. Provider Registry → providers/registry.py:1-376 |

**层级**：层 3 架构决策

---

## 如何让外部插件拦截 agent 生命周期的关键节点？

**维度**：Extension Points
**问题陈述**：如何提供一套生命周期钩子机制，使外部插件能够在 agent 循环的关键时刻注入自定义行为，同时不同钩子的组合策略应该适配各自的语义（内容变换 vs 事件通知）？
**核心关切**：
- 关切 1：**组合策略分化**——`finalize_content` 采用纯函数管线（管道串联，前一 hook 输出是后一 hook 输入），其余五个方法采用扇出（每个 hook 独立执行，一个异常不阻塞其他）
- 关切 2：**语义适配**——`finalize_content` 是内容变换，适合管道逐步加工；其余方法是事件通知，适合扇出避免单点阻塞
- 关切 3：**运行时注入**——AgentLoop 维护 `_extra_hooks` 列表，外部插件可在运行时添加钩子而不修改核心代码，但多个插件的 hook 执行顺序依赖注入顺序

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **CompositeHook：内容变换用管道，事件通知用扇出** | 六个生命周期拦截点中，finalize_content 是纯函数管线，其余五法是独立并行的扇出模式 | nanobot-extension-points.md:4. AgentHook → agent/hook.py:29-103; agent/loop.py:180 |

**层级**：层 3 架构决策

---

## 如何以声明式 Markdown 文件扩展 agent 能力？

**维度**：Extension Points
**问题陈述**：如何让用户和开发者通过创建 Markdown 文件来扩展 agent 能力——哪些技能应该始终可用（全文注入），哪些应该按需加载（渐进式），如何声明工具的运行时依赖？
**核心关切**：
- 关切 1：**渐进式加载**——always skills（`always: true`）全文注入 system prompt；其他技能仅以 XML 摘要形式出现（名称 + 描述 + 路径 + 可用性），agent 需要时通过 `read_file` 工具按需读取
- 关切 2：**上下文经济**——所有技能全文注入会耗尽 context window，渐进式加载按需取用，节省 token
- 关切 3：**依赖自声明**——frontmatter 中的 `requires.bins` 和 `requires.env` 声明工具依赖，不满足条件的技能自动标记为不可用，agent 不会尝试调用无法执行的技能
- 关切 4：**用户覆盖**——`workspace/skills/` 中的用户自定义技能可以覆盖 `nanobot/skills/` 中的同名内建技能

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **Skills Markdown 渐进式加载** | always skills 全文注入 + 其他技能 XML 摘要 + 按需 read_file，依赖自声明，用户可覆盖内建技能 | nanobot-extension-points.md:5. Skills → agent/skills.py:52-205 |

**层级**：层 3 架构决策

---

## 如何隔离子 agent 的能力边界？

**维度**：Extension Points
**问题陈述**：如何让主 agent 可以 spawn 子 agent 处理独立任务，同时防止子 agent 递归创建更多子 agent、发送消息给用户、或调度新任务？
**核心关切**：
- 关切 1：**工具白名单限制**——子 agent 拥有独立的 ToolRegistry，包含文件工具 + 可选的 exec/web 工具，**不包含** message/spawn/cron 工具，从工具层面杜绝递归创建子 agent 的可能
- 关切 2：**错误即终止**——子 agent 的 tool error 为 fatal 级别（出错立即终止），不像主 agent 的非致命错误继续，因为子 agent 没有用户交互通道来恢复
- 关切 3：**资源限制**——每个子 agent 拥有 15 轮 iteration budget，超限自动终止，防止单个子任务无限消耗资源
- 关切 4：**引擎复用**——共享 AgentRunner 引擎获得所有上下文治理能力（Backfill/Microcompact/Budget/Snip），无需重新实现

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **子 agent 受限 ToolRegistry（无 message/spawn/cron）+ 共享执行引擎** | 子 agent 拥有独立受限工具集 + 共享 AgentRunner + fatal error 模式 + 15 轮预算 | nanobot-extension-points.md:6. Subagent → agent/subagent.py:70-209 |

**层级**：层 3 架构决策

---

## 如何集成 MCP 外部工具服务器？

**维度**：Extension Points
**问题陈述**：如何支持 MCP（Model Context Protocol）工具服务器的懒加载连接、工具动态注册和生命周期清理？
**核心关切**：
- 关切 1：**惰性连接**——MCP server 通过 `_connect_mcp()` 在 AgentLoop 初始化时惰性连接，避免阻塞启动
- 关切 2：**命名空间隔离**——MCP 工具以 `mcp_` 前缀动态注册到 ToolRegistry，与 builtins 工具命名空间不冲突
- 关切 3：**生命周期管理**——所有 MCP server 通过 `AsyncExitStack` 管理，AgentLoop 关闭时自动清理所有连接，无需手动管理
- 关切 4：**动态注册**——MCP 工具在连接后动态注入 ToolRegistry，工具数量取决于连接的 MCP server 数量

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **MCP 惰性连接 + mcp_ 前缀命名空间 + AsyncExitStack 生命周期** | MCP server 懒加载连接，工具以 mcp_ 前缀注册，通过 AsyncExitStack 自动清理 | nanobot-extension-points.md:7. MCP → agent/loop.py:256-276; agent/tools/mcp.py |

**层级**：层 3 架构决策

---

## 如何在不使用向量数据库的前提下实现记忆？

**维度**：Architecture
**问题陈述**：如何实现 agent 的长期记忆——包括用户档案、对话历史压缩和记忆更新——而不引入嵌入式数据库或向量检索？
**核心关切**：
- 关切 1：**零外部依赖**——MemoryStore 是纯文件 I/O（读/写 `MEMORY.md`、`history.jsonl`），用 `GitStore` 版本控制 `SOUL.md`/`USER.md`/`MEMORY.md`，无嵌入式数据库，无向量检索
- 关切 2：**检索质量取舍**——文件级记忆无法做语义检索，只能线性读取整个 `MEMORY.md` 内容放入 system prompt，记忆量受 context window 限制
- 关切 3：**三级处理栈**——MemoryStore（持久化）→ Consolidator（后台压缩历史为文件级摘要）→ Dream（两阶段 LLM 驱动的记忆更新），每层职责明确

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **纯文件 I/O 三层记忆栈（无向量检索）** | MemoryStore 文件读写 + Consolidator 异步压缩 + Dream 两阶段 LLM 处理，全部基于文件系统 | nanobot-architecture.md:8. MemoryStore → agent/memory.py:27-228,346+,519+ |

**层级**：层 3 架构决策

---

## 如何让记忆压缩不阻塞主 agent 对话？

**维度**：Performance Tradeoffs
**问题陈述**：记忆压缩（Consolidator）需要调用 LLM 进行历史总结，如何在不阻塞主 agent 对话的前提下完成压缩，且压缩失败不影响正在进行的对话？
**核心关切**：
- 关切 1：**Provider 实例隔离**——Consolidator 使用独立的 LLM provider 实例，不共享主 agent 的 provider 状态（如速率限制计数器），压缩和对话互相不干扰
- 关切 2：**异步解耦**——在 `asyncio.create_task()` 中后台运行，主 agent 在压缩运行期间不受影响，也不会等待压缩完成
- 关切 3：**结果延迟生效**——压缩结果在下一轮 context 组装时才生效，本轮对话使用的仍是压缩前的内容，但失败的压缩不会中断对话

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **Consolidator 独立 Provider 实例 + 异步后台任务** | 独立的 LLM provider 实例 + asyncio.create_task() 后台运行，主循环不阻塞 | nanobot-performance-tradeoffs.md:4. Consolidator → agent/loop.py:210-219,572; agent/memory.py:346+ |

**层级**：层 3 架构决策

---

## 如何处理 LLM API 调用的各类错误？

**维度**：Performance Tradeoffs
**问题陈述**：如何设计重试策略，使其能区分临时性错误（可重试）和永久性错误（不可重试），并在速率限制和配额耗尽的处理上做出不同响应？
**核心关切**：
- 关切 1：**错误分类粒度**——429 错误按语义分类：配额耗尽类（非重试，直接返回错误）vs 速率限制类（重试 + 等待 Retry-After），从响应 error type/code 和响应文本两个路径提取判断
- 关切 2：**重试策略分级**——standard 模式 3 次指数退避（适用于临时性故障）vs persistent 模式无限制但相同错误超过 10 次停止（适用于长任务）
- 关切 3：**内容降级**——图片内容导致的 API 错误自动降级为纯文本重试，不丢失整个请求
- 关切 4：**维护复杂度**——三级重试逻辑在基类 `_run_with_retry()` 中统一实现，但错误分类依赖各 provider 的 error code 规范，新 provider 的 error 行为可能不兼容

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **三级重试：standard 3 次退避 + persistent 无限制限停 + 429 语义分类** | 基类统一实现，区分临时/永久错误，429 分类为配额 vs 限速，图片错误自动降纯文本 | nanobot-performance-tradeoffs.md:5. LLM Provider 重试 → providers/base.py:629-698 |

**层级**：层 3 架构决策

---

## 如何持久化会话状态？

**维度**：Architecture
**问题陈述**：多轮对话的会话状态应该如何持久化——在文件级存储、内存缓存和惰性加载之间如何权衡？
**核心关切**：
- 关切 1：**无外部 DB**——会话以 JSONL 文件存储（第一行 `_type: metadata`），无需数据库，文件系统即持久层
- 关切 2：**内存效率**——内存缓存 + 惰性加载，不将所有会话长驻内存
- 关切 3：**边界对齐**——`get_history()` 或 `retain_recent_legal_suffix()` 在每轮开始时裁剪历史到合法边界，确保不会从孤立 tool result 中间开始（导致 LLM 看到不完整的 tool-call 对）
- 关切 4：**单一天地入口**——`get_or_create()` 是唯一入口函数，集中管理会话的创建和获取逻辑

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **JSONL 文件存储 + 内存缓存 + 惰性加载 + 合法边界裁剪** | 会话以 JSONL 持久化，内存缓存避免重复 I/O，裁剪到合法边界防止损坏的上下文 | nanobot-architecture.md:7. SessionManager → session/manager.py:50-94,119-204 |

**层级**：层 3 架构决策

---

## 如何管理和调度 LLM 依赖？

**维度**：Dependency Strategy
**问题陈述**：如何在支持 20+ LLM provider 的前提下，消除间接依赖层（如 litellm）引入的不可控风险——token 计数不一致、模型名称映射错误、不可控版本升级？
**核心关切**：
- 关切 1：**行为可控性**——移除 `litellm` 后用原生 `openai` + `anthropic` SDK 直接调用，provider 适配层的复杂性从第三方库转移到自有代码（3,719 行 `providers/`），但完全掌控行为
- 关切 2：**零间接供应商依赖**——所有 LLM API 调用都经过自有代码，不依赖任何中间转发层的正确性
- 关切 3：**维护成本转移**——放弃 litellm 开箱即用的 30+ provider 支持，需要自己维护每个 provider 的 API 兼容细节，但 nanobot 只支持 20 个最常用 provider，维护成本可控
- 关切 4：**版本风险隔离**——不再受 litellm 版本升级节奏的影响，各 SDK 的版本独立管理

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **移除 litellm，使用原生 openai + anthropic SDK** | 替换 LLM 转发层为原生 SDK 直接调用，适配逻辑内化到自有 providers/ 代码中 | nanobot-dependency-strategy.md:1. 替换 litellm → README.md:21; providers/registry.py 整体 |

**层级**：层 3 架构决策

---

## 如何处理不同 IM 平台 SDK 的依赖安装？

**维度**：Dependency Strategy
**问题陈述**：如何让用户只安装所需 IM 平台的 SDK，而不是强制安装所有 14+ 平台的依赖？
**核心关切**：
- 关切 1：**安装体积最小化**——IM 平台 SDK 和辅助功能标记为 pip extras 可选依赖（`api`、`wecom`、`weixin`、`matrix`、`discord`、`langsmith`），核心运行时只有 ~20 个包
- 关切 2：**用户体验成本**——用户需要知道自己用哪些平台然后选择性安装（`pip install nanobot-ai[telegram,discord]`），不像全量安装那样零配置
- 关切 3：**版本约束集中**——平台 SDK 的版本锁定在 `pyproject.toml` 主依赖中而非可选组中，保证所有 channel 在同一版本约束下运行

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **pip extras 可选依赖分组：按平台按需安装** | IM 平台 SDK 标记为 pip extras，用户按需选择，核心安装只有 ~20 个包 | nanobot-dependency-strategy.md:2. 可选依赖 → pyproject.toml:20-78 |

**层级**：层 3 架构决策

---

## 如何隔离不同 Channel 的平台 SDK 依赖？

**维度**：Dependency Strategy
**问题陈述**：不同的 IM 平台 SDK 之间存在潜在的版本冲突和命名空间污染——如何确保一个 Channel 的 SDK 不会影响其他 Channel？
**核心关切**：
- 关切 1：**零交叉依赖**——每个内置 Channel 是独立的 Python 模块（`channels/telegram.py`、`channels/slack.py` 等），只 import 自己需要的 SDK，Channel 之间无相互依赖
- 关切 2：**版本统一约束**——平台 SDK 的版本锁定在 `pyproject.toml` 主依赖中，不在可选组中分别锁定，保证全局版本一致
- 关切 3：**添加新 Channel 安全**——新增 Channel 只增加自己的模块文件和依赖声明，不可能打破已有 Channel 的依赖隔离

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **Channel 模块独立：零交叉 import** | 每个 Channel 模块只 import 自己的 SDK，Channel 之间无相互依赖 | nanobot-dependency-strategy.md:3. Channel 依赖隔离 → channels/ 目录结构; pyproject.toml:35-42 |

**层级**：层 3 架构决策

---

## 如何桥接 Python 生态与 Node.js 生态的能力？

**维度**：Dependency Strategy
**问题陈述**：当 Python 生态中不存在某些所需能力（如特定 API 适配）而这些能力在 Node.js 生态中可用时，如何以最小代价获取这些能力？
**核心关切**：
- 关切 1：**进程隔离**——TypeScript bridge 通过 HTTP 与 Python 核心通信，不共享进程空间，bridge 崩溃不影响 Python 主进程
- 关切 2：**主语言纯净**——Python 核心不需要引入 Node.js 运行时作为依赖，bridge 是可选的独立组件
- 关切 3：**额外成本**——跨语言桥接引入了额外的网络通信延迟和部署复杂度（需要同时管理 Python 和 Node.js 两个运行时）

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **独立进程 TypeScript HTTP bridge** | bridge/ 目录独立 Node.js/TypeScript 模块，通过 HTTP 通信，不共享进程空间 | nanobot-dependency-strategy.md:4. Bridge → bridge/src/index.ts |

**层级**：层 3 架构决策

---

## 如何调度定时任务和唤醒 agent？

**维度**：Architecture
**问题陈述**：如何实现定时任务调度——是使用传统 cron 机制、定时器轮询、还是 LLM 驱动的智能唤醒？
**核心关切**：
- 关切 1：**三种调度模式共存**——`at`（一次性）、`every`（间隔）、`cron`（cron 表达式），满足从精确时刻到周期循环的所有场景
- 关切 2：**多进程安全**——`CronStore` 使用 `FileLock` 做持久化，防止多进程环境下的重复执行
- 关切 3：**LLM 驱动唤醒的可靠性**——Heartbeat 使用专用单工具 LLM 调用（`heartbeat` tool，枚举 `skip`/`run`）做定期唤醒，agent 自主判断是否需要执行任务——依赖 LLM 的判断准确性，可能漏判或误判
- 关切 4：**统一入站路径**——Cron 触发消息和 Heartbeat 唤醒结果都通过 `bus.publish_inbound()` 注入，与 IM 消息共享同一处理路径

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **Cron 三模式调度 + Heartbeat LLM 自主唤醒** | Cron（at/every/cron）+ Heartbeat（LLM 通过 heartbeat tool 判断是否执行），统一通过 bus 注入 | nanobot-architecture.md:11. 调度系统 → cron/service.py:1-50; heartbeat/service.py:14-40 |

**层级**：层 3 架构决策

---

## 如何分配测试资源的优先级？

**维度**：Testing Philosophy
**问题陈述**：测试资源有限（虽然 26,048 行测试代码是核心运行时的 5.7 倍），如何决定哪些模块值得最密集的测试覆盖？
**核心关切**：
- 关切 1：**安全优先**——SSRF 防护、exec 沙箱、workspace 隔离是 agent 框架最不可出错的方面（一个 SSRF 漏洞可能让 agent 成为内网跳板），安全测试的投入远超其他模块
- 关切 2：**跨平台一致性**——Windows/macOS/Linux 的 exec 行为差异在跨平台测试矩阵（`ubuntu-latest`/`windows-latest`）中覆盖
- 关切 3：**覆盖率不均衡**——安全测试比重最大，意味着其他功能域（如 memory、cron、hook）的测试覆盖相对薄弱
- 关切 4：**集成优于单元**——测试集中在集成和关键路径（Channel 交互、工具行为、API 端点），而非每个内部函数的单元测试

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **风险驱动测试分配：安全 + 跨平台 + Channel 交互优先** | 测试投入集中在安全边界、跨平台兼容和 Channel 交互，覆盖率不追求模块间均衡 | nanobot-testing-philosophy.md:1. 测试覆盖重点 → tests/ 目录; test_exec_security.py; test_sandbox.py |

**层级**：层 3 架构决策

---

## 如何保证安全防护的边界？

**维度**：Testing Philosophy（设计选择体现在测试架构中）
**问题陈述**：agent 框架中安全漏洞的后果远大于功能 bug，如何在架构层面定义并测试安全边界——SSRF、命令执行、文件系统？
**核心关切**：
- 关切 1：**多层防护**——SSRF 防护（10 个 CIDR 私有网络块拦截，`security/network.py`）+ exec 沙箱（隔离 workspace）+ workspace 隔离（限制文件系统访问范围），三层独立互不依赖
- 关切 2：**可配置白名单**——支持通过 `configure_ssrf_whitelist()` 自定义白名单，平衡安全性和灵活性
- 关切 3：**测试隔离**——安全测试使用 pytest `tmp_path` fixture 和临时 workspace 目录，防止测试中的 shell 命令影响真实文件系统

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | **三层安全防护：SSRF CIDR 拦截 + exec 沙箱 + workspace 隔离** | 网络出口、命令执行、文件系统三个维度独立防护，支持白名单配置 | nanobot-testing-philosophy.md:1. 测试覆盖重点 → security/network.py; test_exec_security.py; test_sandbox.py |

**层级**：层 3 架构决策
