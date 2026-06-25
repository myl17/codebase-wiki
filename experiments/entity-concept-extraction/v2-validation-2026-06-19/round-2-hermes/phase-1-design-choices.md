# Hermes Agent — 设计选择草稿

> 独立提取自 hermes-agent 的 5 个维度叙事页和 12 个节点页。
> 日期：2026-06-19

---

## 1. 如何编排多轮 agent 对话的单一切入点

**维度**：Architecture
**问题陈述**：一个多平台、多入口（CLI/Gateway/Cron/ACP）的 agent 系统，如何保证所有执行路径共享同一套对话循环、工具调用和安全护栏，避免分叉维护？
**核心关切**：
- 关切 1：所有执行路径必须经过同一编排逻辑，改动才能一致生效
- 关切 2：中央编排器的规模会随功能增长膨胀（11510 行单文件）
- 关切 3：无替换机制意味着中央编排器的任何错误阻断所有入口

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | AIAgent 中央编排器 | 11510 行单文件 AIAgent 是所有执行路径的唯一入口，无替换机制 | [[hermes-agent/nodes/components/hermes-agent-ai-agent]] → `run_agent.py:535-560`, `run_agent.py:8130-8189` |

**层级**：层 3 架构决策

---

## 2. 如何在系统 prompt 中内建自学习驱动

**维度**：Architecture
**问题陈述**：agent 系统如何让 LLM 在无人干预下自主积累知识、改进技能、回忆历史，而非依赖人类在每次会话中重新提供上下文？
**核心关切**：
- 关切 1：自驱动指令必须足够强以触发 LLM 主动行为，但不能产生虚假记忆
- 关切 2：三个时间尺度（实时/跨会话/代际）的改进需要不同的工具和持久化路径
- 关切 3：自学习的安全边界——agent 自建技能必须经过安全扫描才能落盘

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 三段自驱动 system prompt | 在 system prompt 中嵌入 MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE 三套指令，驱动 LLM 在实时、跨会话、代际三个时间尺度自主改进 | [[hermes-agent/nodes/design-decisions/hermes-agent-self-learning-loop-decision]] → `agent/prompt_builder.py:145-171` |

**层级**：层 3 架构决策

---

## 3. 如何平衡命令执行的安全性与流畅性

**维度**：Architecture
**问题陈述**：agent 执行任意 shell 命令时，如何在"完全不检查（流畅但危险）"和"全部人工审批（安全但繁琐）"之间找到可调节的平衡点？
**核心关切**：
- 关切 1：不同部署场景的安全需求差异巨大（个人开发机 vs 生产容器 vs 共享服务器）
- 关切 2：审批决策本身需要成本——辅助 LLM 评估引入额外 token 开销和延迟
- 关切 3：审批状态的持久化粒度（once/session/always）影响安全性和便利性的平衡

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 三层渐进式审批 | Layer 0 快速路径（YOLO/容器/off）+ Layer 1 Smart（辅助 LLM 自动评估）+ Layer 2 Manual（tirith + 25+ 危险模式正则 → 用户交互审批），审批级别 once/session/always 三级持久化 | [[hermes-agent/nodes/design-decisions/hermes-agent-layered-approval-decision]] → `tools/approval.py:586-922` |

**层级**：层 3 架构决策

---

## 4. 如何发现和注册工具

**维度**：Architecture / Extension Points
**问题陈述**：在工具数量不断增长的 agent 系统中，如何让新增工具零额外接线即可被系统发现，同时避免手动维护工具清单的遗漏和冲突？
**核心关切**：
- 关切 1：自动发现机制要求注册调用必须是静态可发现的顶层调用，限制了动态注册的灵活性
- 关切 2：AST 扫描引入启动开销，工具越多解析越慢
- 关切 3：同样的自动发现哲学是否应一致应用于 hooks、skills 等其他扩展

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | AST 扫描自动发现 | 进程启动时通过 AST 扫描所有 `registry.register()` 顶层调用自动发现工具，新增工具只需写注册调用无需手动接线；同一哲学延伸至 hooks（目录扫描）和 skills（双同步） | [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]] → `tools/registry.py:28-73` |

**层级**：层 3 架构决策

---

## 5. 如何抽象多消息平台的统一接口

**维度**：Architecture / Extension Points
**问题陈述**：面对 20+ 消息平台（Telegram/Discord/Slack/WhatsApp/Signal/Matrix/iMessage 等），如何设计统一抽象使得新增平台只需实现最小接口，同时不限制平台特有能力的发挥？
**核心关切**：
- 关切 1：单一抽象基类继承 vs 多接口组合——前者强制统一但可能过度约束，后者灵活但分散
- 关切 2：新增平台需要修改 16 处代码（adapter/enum/factory/auth/session/toolset/cron/docs 等），扩展成本高
- 关切 3：抽象基类需要覆盖消息收发、会话管理、媒体处理、打字指示等异构能力

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 单一抽象基类继承 | 通过 `BasePlatformAdapter` ABC 定义统一接口（connect/disconnect/send/send_typing/send_image/get_chat_info），22 个平台通过继承实现；代价是新增平台需按 16 步 checklist 修改多处 | [[hermes-agent/nodes/extension-points/hermes-agent-platform-adapter]] → `gateway/platforms/base.py:813-893` |

**层级**：层 3 架构决策

---

## 6. 如何管理外部记忆后端的集成约束

**维度**：Extension Points
**问题陈述**：当系统同时有内置记忆和外部记忆插件时，如何设计集成约束——外部记忆是替代内置存储还是叠加其上？允许多个外部 provider 同时运行还是限制为一个？
**核心关切**：
- 关切 1：加性叠加保证基础功能永不丢失但可能产生冗余存储
- 关切 2：替换式更简洁但可能丢失内置存储的稳定性
- 关切 3：provider 数量约束（最多 1 个）简化编排但限制了组合使用场景

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 加性叠加 + 最多 1 个外部 provider | BuiltinMemoryProvider 始终启用不可移除，外部 provider（Honcho/Mem0/Supermemory 等 7 选 1）是加性的——不替代内置存储。与 OpenClaw 的 exclusive 替换式槽位形成对比 | [[hermes-agent/nodes/extension-points/hermes-agent-memory-provider]] → `agent/memory_manager.py:1-27` |

**层级**：层 3 架构决策

---

## 7. 如何组织工具为可组合的能力组

**维度**：Extension Points
**问题陈述**：当 agent 拥有数十个工具时，如何让不同使用场景（CLI 全功能 vs Gateway 聊天 vs ACP 编码）只暴露相关工具子集，而非全量工具 schema 每次都注入 system prompt？
**核心关切**：
- 关切 1：工具分组的组合粒度——太细管理复杂，太粗无法精准控制
- 关切 2：递归 include 链的去重和循环检测
- 关切 3：核心工具的修改如何自动传播到所有继承它的 toolset

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 可组合 Toolset 分组 | 每个 toolset 是工具名列表 + `includes` 引用其他 toolsets，`resolve_toolset()` 递归解析带去重和循环检测；`_HERMES_CORE_TOOLS` 作为共享核心清单编辑一次即可更新所有平台 | [[hermes-agent/nodes/extension-points/hermes-agent-toolset-system]] → `tools/toolsets.py:1-30`, `tools/toolsets.py:447-497` |

**层级**：层 3 架构决策

---

## 8. 如何管理对话上下文超出模型窗口时的压缩策略

**维度**：Extension Points / Performance Tradeoffs
**问题陈述**：当对话历史持续增长超出模型 context window 时，如何选择压缩策略（摘要/DAG/其他），且允许策略可插拔替换？
**核心关切**：
- 关切 1：压缩阈值的选择——太早触发浪费 token（无需压缩时压缩），太晚触发有丢失风险
- 关切 2：摘要的保真度——辅助 LLM 摘要必然丢失信息，关键上下文可能被省略
- 关切 3：压缩失败后的退避策略——防止重试风暴

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 策略模式可插拔压缩 | `ContextEngine` ABC 定义压缩接口（阈值 75% context window），内置 Compressor/LCM 两种实现，第三方放入 `plugins/context_engine/<name>/`；同一时间只有一个 engine 激活 | [[hermes-agent/nodes/extension-points/hermes-agent-context-engine]] → `agent/context_engine.py:32-60` |

**层级**：层 3 架构决策

---

## 9. 如何集成外部工具服务（MCP 协议）

**维度**：Extension Points
**问题陈述**：当 agent 需要调用外部独立的工具服务时，如何通过标准协议集成，使外部工具与内置工具在调度层面无差别？
**核心关切**：
- 关切 1：外部工具的可用性不确定性——断连后是否需要自动重连
- 关切 2：双向通信——外部 MCP server 可能发起 LLM 采样请求
- 关切 3：凭据安全——外部 server 返回的错误消息可能泄露 API key

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | MCP 协议集成 | 通过 `~/.hermes/config.yaml` 的 `mcp_servers` 配置自动发现和注入外部工具，支持 Stdio（子进程+指数退避自动重连）和 HTTP/StreamableHTTP 两种传输，支持 MCP Sampling（server 可发起 LLM 请求），错误消息中凭据自动脱敏 | [[hermes-agent/dimensions/hermes-agent-extension-points]] → `tools/mcp_tool.py:15-43` |

**层级**：层 3 架构决策

---

## 10. 如何管理 agent 生命周期事件的扩展点

**维度**：Extension Points
**问题陈述**：agent 系统需要允许外部代码在关键生命周期节点（启动/会话开始/每轮对话/结束）注入自定义逻辑，如何设计事件粒度和加载机制？
**核心关切**：
- 关切 1：事件粒度——过细增加 hook 实现者的负担，过粗限制扩展能力
- 关切 2：hook 中的错误不能阻塞主 pipeline
- 关切 3：hook 的自动发现机制与工具的自动发现是否一致

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 粗粒度生命周期事件 + 目录扫描加载 | 8 个生命周期事件（gateway:startup / session:start / session:end / session:reset / agent:start / agent:step / agent:end / command:*），hook 通过 `~/.hermes/hooks/<name>/HOOK.yaml` + `handler.py` 目录扫描自动加载，错误隔离不阻塞主 pipeline | [[hermes-agent/nodes/extension-points/hermes-agent-event-hooks]] → `gateway/hooks.py:9-19`, `gateway/hooks.py:34-80` |

**层级**：层 3 架构决策

---

## 11. 如何管理可安装技能的互操作性

**维度**：Extension Points
**问题陈述**：agent 的 Skill 系统如何设计才能在多个 agent 框架（Claude Code / Codex CLI / Hermes）之间互操作，避免技能被锁定在单一生态？
**核心关切**：
- 关切 1：开放标准 vs 专有格式——前者互操作但可能约束表达能力
- 关切 2：外部 skill 的安全风险——下载后安装前必须经过扫描
- 关切 3：skill 的自我改进——agent 在使用中如何更新过时或不完善的 skill

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | agentskills.io 开放标准 | 采用 agentskills.io 开放标准实现与 Claude Code / Codex CLI 的 skill 互操作；外部 skill 下载后经 `skills_guard.py` 100+ 威胁模式扫描方可安装；agent 可通过 `skill_manage` 工具自主改进 skill | [[hermes-agent/dimensions/hermes-agent-extension-points]] → `tools/skills_tool.py`, `tools/skills_hub.py` |

**层级**：层 3 架构决策

---

## 12. 如何管理外部 skill 的安全信任

**维度**：Architecture / Extension Points
**问题陈述**：当 agent 可以从社区和第三方安装 skill 时，如何在"完全信任（危险）"和"一律拒绝（封闭）"之间按来源和风险等级实施差异化的安全策略？
**核心关切**：
- 关切 1：信任分级需要覆盖不同来源（内置/官方/社区/自建）和不同风险等级（safe/caution/dangerous）
- 关切 2：威胁模式的覆盖面——12 类别 100+ 模式覆盖 exfiltration/injection/destructive/persistence/network/obfuscation/execution/traversal/mining/supply_chain/privilege_escalation/credential_exposure
- 关切 3：agent 自建 skill 的安全处理——最可能出问题但也最有价值的来源

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 三级信任策略 × 三级风险等级 | 信任级别（builtin/trusted/community/agent-created）与风险等级（Safe/Caution/Dangerous）交叉形成差异化策略：builtin 全放行、trusted 仅 block dangerous、community block caution+dangerous、agent-created ask dangerous | [[hermes-agent/nodes/components/hermes-agent-skills-guard]] → `tools/skills_guard.py:39-48`, `tools/skills_guard.py:82-484` |

**层级**：层 3 架构决策

---

## 13. 如何在多轮对话中降低 token 成本

**维度**：Performance Tradeoffs
**问题陈述**：多轮对话中 system prompt 和早期 messages 在每轮都重复发送，如何利用 LLM 的 prompt caching 机制大幅降低 input token 成本，同时不破坏消息结构？
**核心关切**：
- 关切 1：cache breakpoint 数量受限于 provider（Anthropic 上限 4 个），需权衡 system prompt 占用几个、历史消息占用几个
- 关切 2：cache TTL 默认 5 分钟——太短命中率低，太长写入成本高（1.25x）
- 关切 3：跨消息复用 agent 实例才能保持 cache prefix 有效

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | system_and_3 缓存策略 | 4 个 cache breakpoints：system prompt 占 1 个（跨 turn 稳定），最后 3 条非 system 消息占 3 个（滚动窗口）；GatewayRunner 跨消息缓存 AIAgent 实例以保持 cache prefix 有效 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/prompt_caching.py:1-73`, `gateway/run.py:604-611` |

**层级**：层 3 架构决策

---

## 14. 如何分类管理工具的并行执行

**维度**：Performance Tradeoffs
**问题陈述**：当 LLM 在一次响应中发起多个工具调用时，哪些可以并行执行以降低延迟，哪些必须串行以保证安全或正确性？
**核心关切**：
- 关切 1：只读工具天然可并行，但文件路径有重叠的读写工具存在隐式依赖
- 关切 2：破坏性命令（rm/mv/sed -i 等）的识别依赖正则匹配，可能漏检
- 关切 3：交互式工具（clarify）必须阻塞等待用户输入，并行无意义

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 四分类并行策略 | 永不并行（clarify 交互式）/ 安全并行（web_search 等 11 个只读工具）/ 路径范围并行（read_file/write_file/patch 当目标路径不同时可并行）/ 破坏性串行（terminal 命令中含危险模式标记串行执行），最大 8 workers | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `run_agent.py:214-311` |

**层级**：层 3 架构决策

---

## 15. 如何为不同复杂度的查询路由模型

**维度**：Performance Tradeoffs
**问题陈述**：日常简单对话（"你好""今天天气怎么样"）不需要大模型处理，如何在不牺牲复杂任务质量的前提下，将简单查询路由到便宜模型降低成本？
**核心关切**：
- 关切 1：误判代价——复杂任务被路由到弱模型导致质量下降，比简单任务走强模型多花一点钱更严重
- 关切 2：分类特征的完备性——字符数/词数/代码块/URL/关键词黑名单的准确率有限
- 关切 3：保守策略的倾向——宁可多用强模型也不能漏判复杂任务

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 保守的智能路由 | 仅 < 160 字符、< 28 词、无代码块、无 URL、无 45 个复杂关键词（debug/implement/refactor/analyze/architecture 等）的消息才路由到便宜模型；任一条件不满足则回主模型 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/smart_model_routing.py:62-118` |

**层级**：层 3 架构决策

---

## 16. 如何管理 API 多凭证的速率限制

**维度**：Performance Tradeoffs
**问题陈述**：单个 API key 有严格的 rate limit，如何用多个 key 提升可用性——是随机轮换、按剩余配额分配、还是先用完再切？
**核心关切**：
- 关切 1：轮换策略影响配额利用率——随机轮换可能浪费低配额 key，fill_first 更高效但加重首个 key 负担
- 关切 2：被动追踪（等 429 再切）vs 主动限流（提前切换）——前者充分利用配额但偶尔浪费一次请求
- 关切 3：多 key 管理增加配置和监控复杂度

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | fill_first + 被动追踪 | 先用第一个 key 耗尽再切下一个（fill_first）；被动追踪 12 个 x-ratelimit-* header，收到 429 后才切换 fallback，不做主动预限流以充分利用每个 key 的配额 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/credential_pool.py:60`, `agent/rate_limit_tracker.py:1-51` |

**层级**：层 3 架构决策

---

## 17. 如何限制 agent 的单次任务计算预算

**维度**：Performance Tradeoffs
**问题陈述**：agent 在执行复杂任务时可能陷入无限循环或过度探索，如何在保证任务完成度的同时设置计算成本的上限？
**核心关切**：
- 关切 1：预算耗尽后的处理——是立即终止还是给一次 grace call 生成最终响应
- 关切 2：某些工具调用（execute_code）是否应退款——代码执行本身不是 agent 的决策性轮次
- 关切 3：预算告警是否应注入 LLM——提前告警可能导致模型过早放弃，不告警则可能在耗尽时突然中断

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 线程安全迭代预算 + 不注入 LLM | 父 agent 90 轮、子 agent 50 轮独立预算；耗尽后允许一次 grace call 尽力生成文本响应；`execute_code` 调用可退款（不计入预算）；预算耗尽不提前通知 LLM（之前做法导致模型过早放弃） | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `run_agent.py:170-199`, `run_agent.py:815-821` |

**层级**：层 3 架构决策

---

## 18. 如何管理可选依赖的优雅降级

**维度**：Dependency Strategy
**问题陈述**：一个功能丰富的 agent 系统有 20+ 可选依赖（消息/记忆/语音/浏览器/搜索/容器运行时等），如何在缺失时优雅降级而非崩溃，让用户按需安装所需功能？
**核心关切**：
- 关切 1：ImportError 检查点需要遍布所有使用可选依赖的代码路径
- 关切 2：降级行为需要明确告知用户（哪些功能因缺失依赖而不可用）
- 关切 3：条件依赖（特定 OS 或 Python 版本才可用）需要在包管理层面表达

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | ImportError → 降级/跳过 | 所有可选依赖遵循 ImportError 捕获后优雅降级模式，绝不因缺少可选包而启动失败；pyproject.toml 通过 20+ extras 将单体重安装拆分为按需安装（如 `hermes-agent[messaging]`）；条件依赖（matrix 仅 Linux、yc-bench 仅 Python>=3.12）在包层面约束 | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:39-115` |

**层级**：层 3 架构决策

---

## 19. 如何选择核心 API SDK 的架构锁定

**维度**：Dependency Strategy
**问题陈述**：agent 系统需要与 20+ 模型 provider 通信，是每个 provider 使用其原生 SDK，还是选择一个通用 SDK 作为统一路由层？
**核心关切**：
- 关切 1：单 SDK 路由简化代码但形成架构锁定——如果 OpenAI SDK 出现破坏性变更或不再满足需求，替换成本极高
- 关切 2：多 SDK 策略分散维护但降低锁定风险——每个 provider 的原生 SDK 各有特点
- 关切 3：OpenAI-compatible 协议的生态覆盖足够广（20+ provider），但 Anthropic 的原生 API 需要单独 SDK

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | OpenAI SDK 统一路由 | 20+ provider 都通过 `openai` SDK 路由（OpenAI-compatible 协议），Anthropic 额外使用原生 SDK 但可通过 `api_mode` 切换回 OpenAI-compatible 路径；核心依赖清单中 openai SDK 替换成本标注为"高——无官方替代" | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:15-37` |

**层级**：层 3 架构决策

---

## 20. 如何实现依赖的可重复构建

**维度**：Dependency Strategy
**问题陈述**：一个依赖 200+ 传递包的系统，如何确保在不同时间、不同机器上的安装结果完全一致？
**核心关切**：
- 关切 1：版本范围的宽松程度——太松可重复性差，太紧更新成本高
- 关切 2：容器层的可重复性——Docker 基础镜像也需固定
- 关切 3：不内嵌第三方源码（no vendor）——完全依赖包管理器的 lockfile

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 三层版本锁定 | 范围锁（所有核心依赖 `>=lower,<upper` 双边界定）+ 精确锁（`uv.lock` 5512 行覆盖全依赖树 hash 锁定）+ Docker 层（基础镜像 SHA256 固定 + COPY . 后再 uv pip install）；无 vendor/bundle 策略，所有依赖通过 PyPI + lockfile 管理 | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `pyproject.toml:15-37`, `uv.lock`, `Dockerfile:1-3,38-39` |

**层级**：层 3 架构决策

---

## 21. 如何在运行时选择多种后端实现

**维度**：Dependency Strategy / Extension Points
**问题陈述**：对于终端执行、Web 搜索、TTS 引擎、记忆存储、上下文压缩等子系统，如何在多个后端实现之间切换而不修改代码？
**核心关切**：
- 关切 1：后端的发现机制——通过 API key 存在性自动发现 vs 显式配置选择
- 关切 2：后端的替换粒度——是整个子系统替换还是允许混合使用
- 关切 3：后端的降级优先级——多个后端可用时的选择策略

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 配置驱动的多后端选择 | 终端 6 种后端（local/docker/ssh/daytona/singularity/modal）、搜索 4 种（Exa/Firecrawl/Tavily/Parallel-Web）、TTS 3 种、记忆 7 选 1、压缩 2+ 种——均通过 `config.yaml` 选择；搜索后端通过 API key 存在性自动发现和回退 | [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] → `config.yaml`, `tools/web_tools.py:1925-1947` |

**层级**：层 3 架构决策

---

## 22. 如何隔离测试环境以确保零残留

**维度**：Testing Philosophy
**问题陈述**：一个读写 `~/.hermes/` 目录、调用真实 API、使用单例模式的 agent 系统，如何在测试中完全隔离以避免污染用户数据和产生费用？
**核心关切**：
- 关切 1：单例模式的跨测试泄漏——`plugin_manager` 等单例必须在测试间重置
- 关切 2：敏感 API key 的误用——测试中需清除环境变量防止意外调用真实 API
- 关切 3：失控测试的保护——单个测试卡死不应拖垮整个 CI

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 自动隔离 fixture + 30s 硬超时 | `_isolate_hermes_home` autouse fixture 将 `HERMES_HOME` 重定向到 `tmp_path/hermes_test/`，清除 `OPENROUTER_API_KEY` 等关键 env var，重置 `plugin_manager` 单例；30 秒 `SIGALRM` 硬超时 kill 任何卡死测试 | [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] → `tests/conftest.py:20-42`, `tests/conftest.py:77-118` |

**层级**：层 3 架构决策

---

## 23. 如何选择测试的抽象层级

**维度**：Testing Philosophy
**问题陈述**：在测试覆盖的深度和重构友好性之间，是测试行为接口还是测试内部实现？
**核心关切**：
- 关切 1：测试行为接口——重构时测试不需要改动但对复杂内部逻辑的覆盖不足
- 关切 2：测试实现细节——覆盖更全面但重构时测试大面积失效
- 关切 3：Mock 的边界——只在外部边界（API/文件系统/环境）使用 mock，内部模块直接测试

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 行为驱动测试 | 测试公共 API 表面（函数签名、返回格式、边界条件）；对错误路径和边界值有专门测试（空 model fallback、SQL injection 等）；不测试私有实现细节；不对 mock 对象的内部调用做过度断言 | [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] → `tests/` |

**层级**：层 3 架构决策

---

## 24. 如何在 CI 中防范供给链攻击

**维度**：Testing Philosophy / Dependency Strategy
**问题陈述**：开源 agent 项目的 CI pipeline 中，如何检测 PR 中是否包含恶意代码注入（如 litellm-style supply chain attack）、新增不安全的预构建 wheel、或 credential-stealing 载荷？
**核心关切**：
- 关切 1：检测时机——在 PR 阶段阻断而非合并后发现
- 关切 2：检测模式的覆盖面——`.pth` 文件注入、base64+exec/eval 组合、新增预构建 wheel、不安全的 PYTHONPATH
- 关切 3：与 CI 流程的集成——作为独立 workflow 在每次 PR 上运行

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | PR 级供给链审计 workflow | Supply Chain Audit workflow 在每次 PR 上运行：检测 `.pth` 文件（阻止 litellm-style 攻击）、base64+exec/eval 组合（credential-stealing 载荷）、新增预构建 wheel、新增 pip install 命令、不安全的 PYTHONPATH 修改 | [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] → `.github/workflows/supply-chain-audit.yml:1-60` |

**层级**：层 3 架构决策

---

## 25. 如何为特定场景精简 agent 的工具面

**维度**：Performance Tradeoffs / Extension Points
**问题陈述**：当 agent 被嵌入编辑器（通过 ACP 协议）而非作为独立聊天应用时，如何裁剪工具集以移除不相关的功能（消息/音频/交互式 UI），从而减少 token 开销和避免模型误用？
**核心关切**：
- 关切 1：裁剪的工具集需独立维护 vs 从核心工具集派生（继承核心再移除）
- 关切 2：裁剪后功能不完整——编辑器场景无法使用消息发送、TTS 等功能
- 关切 3：不同场景的 toolset 定义应该由谁维护（平台开发者 vs 核心团队）

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | ACP 专用精简 toolset | `hermes-acp` toolset 移除 messaging/audio/clarify UI 工具，仅保留编码相关工具；更小的工具 schema → 更低的 token 开销和更精确的上下文，但牺牲编辑器中的完整 Hermes 功能 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `toolsets.py:226-243` |

**层级**：层 3 架构决策

---

## 26. 如何在 Gateway 模式下实现阻塞式审批

**维度**：Architecture
**问题陈述**：在多平台 Gateway 模式下，命令审批需要用户通过聊天界面回复 `/approve` 或 `/deny`。agent 线程如何在等待审批时不占用 CPU，同时支持多个并行子 agent 各自的审批等待？
**核心关切**：
- 关切 1：阻塞等待的机制——轮询浪费 CPU，事件通知需要线程安全
- 关切 2：多审批并发——不同子 agent 的审批请求需要独立队列和独立等待
- 关切 3：审批超时——用户长时间不响应时 agent 线程如何处理

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | FIFO 队列 + threading.Event 阻塞审批 | Gateway 模式下审批请求进入 FIFO 队列，agent 线程通过 `threading.Event` 阻塞挂起等待用户 `/approve` / `/deny`；并行子 agent 并发等待各自审批（独立 Event） | [[hermes-agent/nodes/components/hermes-agent-approval-system]] → `tools/approval.py:219-284` |

**层级**：层 3 架构决策

---

## 27. 如何分离关注点防止单层膨胀

**维度**：Architecture
**问题陈述**：一个包含配置管理、会话持久化、安全边界、资源隔离的大型 agent 系统，如何划分层次使得各层独立演化、避免循环依赖？
**核心关切**：
- 关切 1：配置层必须在所有模块导入之前加载，CLI 和 Gateway 独立加载
- 关切 2：会话层的 PII 保护——敏感信息需哈希化存储
- 关切 3：资源隔离——不同 agent 实例的终端 VM 按 task_id 隔离，防止相互干扰

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 六层分离架构 | 用户界面层 → 编排层 → 安全层 → 插件层 → 工具层 → 基础设施层 + 可观测性层（横切）；配置层在启动时独立加载避免循环依赖；`_SafeWriter` 包装 stdout/stderr 防止管道破裂；终端 VM 按 task_id 隔离 | [[hermes-agent/dimensions/hermes-agent-architecture]] → `run_agent.py:113-167`, `gateway/run.py:88-218`, `gateway/session.py:1-60` |

**层级**：层 3 架构决策

---

## 28. 如何管理日志的安全性和可追溯性

**维度**：Architecture
**问题陈述**：agent 系统的日志中可能包含 API key、用户私密对话等敏感信息，如何在保留调试信息的同时确保密钥永不写入磁盘？
**核心关切**：
- 关切 1：脱敏的覆盖面——40+ 种 API key 前缀模式需持续更新
- 关切 2：脱敏的时机——在日志写入前截获，不能依赖事后清理
- 关切 3：多组件日志的路由——gateway/agent/tools/cli/cron 的日志需分开存储便于排查

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 密文脱敏 + 组件路由 + session 注入 | 40+ 种 API key 前缀模式自动脱敏（OpenAI/Anthropic/GitHub/Slack/Google/AWS/Stripe 等）；三日志分文件（agent.log/errors.log/gateway.log）；`[session_id]` 标签注入 LogRecord 支持按会话过滤；Managed Mode 下 chmod 0660 保证多用户共享 | [[hermes-agent/dimensions/hermes-agent-architecture]] → `agent/redact.py:1-60`, `hermes_logging.py:1-391` |

**层级**：层 3 架构决策

---

## 29. 如何管理后台进程的生命周期

**维度**：Architecture
**问题陈述**：agent 可能在后台启动长时间运行的进程（terminal background=true），如何在 agent 崩溃重启后恢复对这些进程的跟踪，同时限制内存占用？
**核心关切**：
- 关切 1：进程状态的持久化——JSON checkpoint 文件支持崩溃恢复
- 关切 2：输出缓冲的容量——200KB 滚动缓冲区平衡内存占用和可追溯性
- 关切 3：并发进程数的上限——64 个进程 LRU 淘汰防止资源耗尽

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 进程注册表 + JSON checkpoint | 管理所有后台进程：200KB 滚动输出缓冲区、已完成进程保留 30min、最大并发跟踪 64 个进程（LRU 淘汰）、JSON checkpoint 文件支持网关崩溃恢复 | [[hermes-agent/dimensions/hermes-agent-architecture]] → `tools/process_registry.py:1-60` |

**层级**：层 3 架构决策

---

## 30. 如何记忆上下文跨 turn 预取

**维度**：Performance Tradeoffs
**问题陈述**：在每轮对话开始前需要从记忆后端检索相关历史，这个检索操作是否应阻塞 API 调用前的关键路径？
**核心关切**：
- 关切 1：同步预取会增加用户感知延迟（等待记忆检索完成后才能调用 LLM）
- 关切 2：异步预取返回上一轮的结果——可能已过时（上一轮后又写入新记忆）
- 关切 3：预取触发时机——在当前 turn 完成后后台触发，下一轮 prefetch() 返回缓存结果

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 后台预取 + 不阻塞关键路径 | `queue_prefetch()` 在当前 turn 完成后后台线程触发记忆检索，下一轮 `prefetch()` 返回缓存结果；优势是不阻塞 API 调用前的关键路径，代价是记忆可能不是最新状态 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/memory_provider.py:92-112` |

**层级**：层 2 技术选型

---

## 31. 如何选择上下文压缩的摘要预算

**维度**：Performance Tradeoffs
**问题陈述**：对对话历史进行摘要压缩时，摘要本身也消耗 token。如何分配摘要的 token 预算使其既能覆盖关键信息又不过度膨胀？
**核心关切**：
- 关切 1：摘要预算比例——太大浪费 token（压缩失去意义），太小丢失信息
- 关切 2：压缩失败后的冷却期——防止摘要失败触发重试风暴
- 关切 3：用户通知不能注入 LLM——避免模型因感知到上下文压力而提前放弃

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 20% 摘要预算 + 600s 冷却 | 摘要预算为压缩内容的 20%，上限 12,000 tokens；摘要失败后冷却 600 秒防止重试风暴；用户通知分层（85%/95% 阈值）但不注入 LLM | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `agent/context_compressor.py:51-53`, `agent/context_compressor.py:60` |

**层级**：层 2 技术选型

---

## 32. 如何缓存模型元数据加速启动

**维度**：Performance Tradeoffs
**问题陈述**：agent 启动时需要查询 API provider 获取模型列表和元数据，这个网络请求是否应阻塞启动过程？
**核心关切**：
- 关切 1：缓存过期后的信息不准确——新模型可能未被发现
- 关切 2：后台线程预热——在 agent 初始化时启动 daemon 线程获取元数据，不阻塞启动
- 关切 3：缓存 TTL 的选择——1 小时平衡新鲜度和启动速度

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes-agent | 1h TTL 缓存 + daemon 线程预热 | 模型元数据缓存 1 小时避免每次启动阻塞 API 调用；后台 `threading.Thread(target=..., daemon=True)` 在 agent 初始化时启动预热 | [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] → `run_agent.py:747-748`, `agent/model_metadata.py` |

**层级**：层 2 技术选型

---

## 设计选择总览

| # | 问题 | 维度 | 层级 |
|---|------|------|------|
| 1 | 如何编排多轮 agent 对话的单一切入点 | Architecture | 层 3 |
| 2 | 如何在系统 prompt 中内建自学习驱动 | Architecture | 层 3 |
| 3 | 如何平衡命令执行的安全性与流畅性 | Architecture | 层 3 |
| 4 | 如何发现和注册工具 | Architecture / Extension Points | 层 3 |
| 5 | 如何抽象多消息平台的统一接口 | Architecture / Extension Points | 层 3 |
| 6 | 如何管理外部记忆后端的集成约束 | Extension Points | 层 3 |
| 7 | 如何组织工具为可组合的能力组 | Extension Points | 层 3 |
| 8 | 如何管理对话上下文超出模型窗口时的压缩策略 | Extension Points / Performance Tradeoffs | 层 3 |
| 9 | 如何集成外部工具服务（MCP 协议） | Extension Points | 层 3 |
| 10 | 如何管理 agent 生命周期事件的扩展点 | Extension Points | 层 3 |
| 11 | 如何管理可安装技能的互操作性 | Extension Points | 层 3 |
| 12 | 如何管理外部 skill 的安全信任 | Architecture / Extension Points | 层 3 |
| 13 | 如何在多轮对话中降低 token 成本 | Performance Tradeoffs | 层 3 |
| 14 | 如何分类管理工具的并行执行 | Performance Tradeoffs | 层 3 |
| 15 | 如何为不同复杂度的查询路由模型 | Performance Tradeoffs | 层 3 |
| 16 | 如何管理 API 多凭证的速率限制 | Performance Tradeoffs | 层 3 |
| 17 | 如何限制 agent 的单次任务计算预算 | Performance Tradeoffs | 层 3 |
| 18 | 如何管理可选依赖的优雅降级 | Dependency Strategy | 层 3 |
| 19 | 如何选择核心 API SDK 的架构锁定 | Dependency Strategy | 层 3 |
| 20 | 如何实现依赖的可重复构建 | Dependency Strategy | 层 3 |
| 21 | 如何在运行时选择多种后端实现 | Dependency Strategy / Extension Points | 层 3 |
| 22 | 如何隔离测试环境以确保零残留 | Testing Philosophy | 层 3 |
| 23 | 如何选择测试的抽象层级 | Testing Philosophy | 层 3 |
| 24 | 如何在 CI 中防范供给链攻击 | Testing Philosophy / Dependency Strategy | 层 3 |
| 25 | 如何为特定场景精简 agent 的工具面 | Performance Tradeoffs / Extension Points | 层 3 |
| 26 | 如何在 Gateway 模式下实现阻塞式审批 | Architecture | 层 3 |
| 27 | 如何分离关注点防止单层膨胀 | Architecture | 层 3 |
| 28 | 如何管理日志的安全性和可追溯性 | Architecture | 层 3 |
| 29 | 如何管理后台进程的生命周期 | Architecture | 层 3 |
| 30 | 如何记忆上下文跨 turn 预取 | Performance Tradeoffs | 层 2 |
| 31 | 如何选择上下文压缩的摘要预算 | Performance Tradeoffs | 层 2 |
| 32 | 如何缓存模型元数据加速启动 | Performance Tradeoffs | 层 2 |

共提取 32 条设计选择：29 条层 3 架构决策 + 3 条层 2 技术选型。
