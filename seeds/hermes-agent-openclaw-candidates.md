# hermes-agent + openclaw — 候选 Concept 清单

> 生成日期：2026-06-25
> 跨仓库问题空间匹配：nanobot（种子库 15 条）+ hermes-agent（14 条问题空间）+ openclaw（18 条问题空间）

---

## A 类：追加到已有 Concept 页（0 条）

无。wiki/concepts/ 当前为空，无已有 Concept 页可供追加。

---

## B 类：新建 Concept 页（15 条）

### 1. agent-loop-orchestration — 如何编排 Agent 的主循环

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot 采用 AgentLoop + AgentRunner 双层分离（loop 管理会话路由，runner 管理 LLM 迭代）；hermes-agent 采用 AIAgent 单体 `while` 循环 + `api_mode` 自动检测 + `IterationBudget` 预算共享；openclaw 采用 `runEmbeddedPiAgent` 函数 + 流式订阅状态机 + lane 并发控制。三种风格迥异。
- **② 独立设计空间**：评价维度是控制流组织（单体 vs 分层）、错误恢复策略、并发模型，不与"上下文压缩"或"工具管理"共享评价维度。
- **③ 持续 Trade-off**：单体循环（hermes-agent）简单直接但职责混乱；分层分离（nanobot）职责清晰但增加模块间通信成本；函数式+状态机（openclaw）灵活但理解门槛高。
- **来源 Entity**：nanobot/agent-loop + agent-runner, hermes-agent/agent-core, openclaw/agent-runtime

### 2. context-compression-strategy — 如何管理对话上下文窗口

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot 采用启发式微压缩（`_microcompact` + `_snip_history` 快照裁剪）无需额外 LLM 调用；hermes-agent 采用三阶段 LLM 辅助压缩（工具裁剪→11 字段结构化摘要→组装）使用便宜模型；openclaw 采用自动压缩重试（最多 3 次）集成在 agent 主循环中。三种方案在"是否调用 LLM 做压缩"这一根本决策上不同。
- **② 独立设计空间**：评价维度是压缩保真度 vs 压缩成本、触发策略、对 prompt caching 的影响。
- **③ 持续 Trade-off**：LLM 辅助压缩保真度高但消耗 token 和延迟；启发式压缩零 token 成本但可能丢失语义；压缩频率 vs 信息保留是永恒张力。
- **来源 Entity**：nanobot/agent-runner（微压缩+裁剪），hermes-agent/context-compressor，openclaw/agent-runtime（压缩重试）

### 3. channel-abstraction-pattern — 如何抽象异构消息平台的接口差异

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot 12 个 channel 适配器各实现独立接口；hermes-agent `BasePlatformAdapter` ABC + 18 个具体适配器，工厂创建，`GatewayStreamConsumer` 统一流式输出；openclaw `ChannelPlugin` 类型 + 30+ 可选 adapter + manifest-first ID 体系 + 注册表懒加载。
- **② 独立设计空间**：评价维度是接口抽象粒度（thin vs thick）、平台特有能力的暴露程度、第三方扩展的便利性。
- **③ 持续 Trade-off**：薄接口（nanobot）简单但无法利用平台特有功能；厚接口+ABC（hermes-agent）覆盖全面但适配器实现成本高；类型系统+manifest（openclaw）最灵活但注册体系增加了复杂度。
- **来源 Entity**：nanobot/channel-system, hermes-agent/platform-adapters + gateway-runner, openclaw/channel-system

### 4. session-lifecycle-management — 如何管理会话身份识别与持久化生命周期

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot 使用 `unified_session` 模式 + JSON 存储 + 简单键；hermes-agent 使用确定性 `agent:main:<platform>:<type>:<id>` 键 + 三层重置策略（none/idle/daily/both）+ SQLite WAL + FTS5 搜索；openclaw 使用结构化键 `agent:{id}:{channel}:{account}:{peer}` + 四种 DM scope 模式 + 写锁保护 + 磁盘预算强制执行 + HTML 转录归档。
- **② 独立设计空间**：评价维度是会话键的确定性/灵活性、并发安全策略、存储格式可演化性、跨会话搜索能力。
- **③ 持续 Trade-off**：简单键（nanobot）容易实现但灵活性低；分层键+多模式（openclaw）灵活但复杂；SQLite+搜索（hermes-agent）功能强但引入数据库依赖。
- **来源 Entity**：nanobot/session-manager, hermes-agent/session-manager + state-database, openclaw/session-system + routing-system

### 5. system-prompt-assembly — 如何组装 Agent 的系统提示词

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot `context_builder` 分层组装（SOUL → memory → context files）；hermes-agent `prompt_builder` 纯函数多层组装 + prompt injection 扫描（10+ 模式）+ 模型特定执行纪律；openclaw `buildAgentSystemPrompt` 27 个按序排列的节 + `<available_skills>` XML 注入 + 运行时上下文注入。
- **② 独立设计空间**：评价维度是层的可组合性、prompt caching 友好度、注入安全、模型适配。
- **③ 持续 Trade-off**：多独立层（hermes-agent）模块化但增加 prompt 碎片化风险；固定顺序节（openclaw）结构清晰但灵活性受限；安全扫描增加延迟但防止注入攻击。
- **来源 Entity**：nanobot/context-builder, hermes-agent/prompt-builder, openclaw/agent-runtime（system-prompt 组件）

### 6. memory-management-architecture — 如何管理 Agent 的长期记忆

- **覆盖仓库**：nanobot, hermes-agent（openclaw 以嵌入式工具形式存在）
- **① 多方案**：nanobot 三层架构（MemoryStore 文件 I/O → Consolidator token 预算驱动压缩 → Dream 两阶段深度反思编辑 + git 提交）；hermes-agent 内置 MEMORY.md/USER.md + 8 种外部 provider 后端（Honcho/Holographic/mem0 等）+ 冻结快照保证 cache 效率 + MemoryProvider ABC 插件体系。
- **② 独立设计空间**：评价维度是存储后端多样性、缓存一致性策略、自主演化能力。
- **③ 持续 Trade-off**：纯文件存储（nanobot）简单可靠但无外部集成；多后端插件（hermes-agent）功能丰富但增加复杂度；冻结快照保证 cache 效率但牺牲即时一致性。
- **来源 Entity**：nanobot/memory-system, hermes-agent/memory-system

### 7. tool-lifecycle-management — 如何管理工具注册、发现与策略过滤

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot `ToolRegistry` 单例 + 自动发现 + 并发安全分组；hermes-agent `ToolRegistry` 单例 + AST 扫描发现 + 遮蔽保护 + MCP 动态刷新 + 外部进程注册；openclaw 工具组装管道 + 9 层策略管道（profile→provider→global→agent→group→sandbox→subagent）+ 4 profiles（minimal/coding/messaging/full）+ provider schema 归一化。
- **② 独立设计空间**：评价维度是工具发现机制、策略复杂度的收益/成本比、工具安全性。
- **③ 持续 Trade-off**：简单注册（nanobot）易维护但缺乏细粒度控制；AST 扫描+遮蔽保护（hermes-agent）自动化但增加启动成本；9 层策略管道（openclaw）控制粒度最细但调试和理解困难。
- **来源 Entity**：nanobot/tool-registry, hermes-agent/tool-registry + mcp-integration, openclaw/tool-system

### 8. provider-abstraction-pattern — 如何抽象多 LLM Provider 的差异

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot `LLMProvider` ABC + 自动匹配 + OpenAI-compatible API 优先；hermes-agent 函数式适配器模块（非类继承）+ `api_mode` 枚举（chat_completions/anthropic_messages/bedrock_converse/codex_responses）+ `CredentialPool` 多 key 轮换；openclaw 四种认证模式（api-key/oauth/token/aws-sdk）+ `AuthProfileStore` 磁盘持久化（含冷却追踪）+ 冷却感知故障切换链。
- **② 独立设计空间**：评价维度是适配器设计模式（ABC vs 函数式 vs 枚举）、认证管理复杂度、故障切换策略。
- **③ 持续 Trade-off**：ABC 继承（nanobot）类型安全但每个 provider 建类；函数式适配（hermes-agent）灵活但不强制接口契约；冷却感知切换（openclaw）智能但持久化状态增加复杂度。
- **来源 Entity**：nanobot/provider-system, hermes-agent/model-adapters + provider-registry, openclaw/model-configuration

### 9. subagent-orchestration — 如何编排子 Agent 的委托与生命周期

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot `SubagentManager` 后台异步任务 + 独立 session + 限制工具集；hermes-agent `delegate_task` 通过 `ThreadPoolExecutor` 并行创建独立 `AIAgent` 实例 + 共享 `IterationBudget` + 最大深度 2 + `DELEGATE_BLOCKED_TOOLS` 禁止递归/用户交互；openclaw `SubagentRegistry` DI 构造 + 内存/磁盘双层存储 + 定期清扫器 + 孤儿恢复 + 指数退避 announce 重试。
- **② 独立设计空间**：评价维度是并行模式、资源隔离、故障恢复、预算控制。
- **③ 持续 Trade-off**：线程池并行（hermes-agent）简单高效但 Python GIL 限制；异步任务（nanobot）适合 I/O 密集但缺乏精细生命周期；DI+双存储（openclaw）最健壮但架构最重。
- **来源 Entity**：nanobot/subagent-manager, hermes-agent/delegate-subagent, openclaw/subagent-system

### 10. security-architecture — 如何构建多层安全防御体系

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot SSRF 防护 + 网络安全（URL 过滤 + IP 限制）；hermes-agent Tirith 二进制扫描（homograph/pipe/注入）+ 40+ 危险模式检测 + LLM 辅助智能审批 + DM 配对码；openclaw 四维审计（gateway bind/auth/rate-limit + 外部内容标记 + DM 四级策略 + HTTP 工具限制）+ 可插拔安全审计收集器。
- **② 独立设计空间**：评价维度是防御深度 vs 复杂度、误报率控制、不同平台的安全模型。
- **③ 持续 Trade-off**：深度防御（openclaw）最安全但用户摩擦最大；扫描+智能降级（hermes-agent）平衡安全与体验但 LLM 辅助审批有成本；简单过滤（nanobot）最轻量但覆盖面窄。
- **来源 Entity**：nanobot/security-system, hermes-agent/security-sandbox, openclaw/security-system

### 11. execution-approval-pattern — 如何在 Agent 高风险操作前插入人类审批

- **覆盖仓库**：hermes-agent, openclaw（nanobot 无独立审批机制）
- **① 多方案**：hermes-agent 三级审批（session/permanent/YOLO）+ DM 配对加密随机码授权 + 仅需首次审批后记住；openclaw 异步创建-注册分离（create 同步返回 requestId，register 返回 Promise）+ `setTimeout` 超时 15s 宽限期后自动拒绝 + 反重放元数据 + iOS 推送通知集成。
- **② 独立设计空间**：评价维度是审批的同步/异步模式、记忆/超时策略、多平台审批体验。
- **③ 持续 Trade-off**：同步审批（hermes-agent 首次后记忆）简单但首次阻塞；异步审批（openclaw）非阻塞但增加状态管理复杂度；记忆审批减少摩擦但可能降低安全意识。
- **来源 Entity**：hermes-agent/security-sandbox, openclaw/approval-system

### 12. skills-extension-mechanism — 如何管理 Agent 的可插拔能力模块

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot `skills-loader` 可插拔模块管理 + 按需加载；hermes-agent 技能 CRUD（创建/查看/编辑/删除/补丁）+ 8 源联邦市场搜索 + Quarantine 隔离安装 + 三级信任策略（builtin/trusted/community/agent-created）+ 渐进式信息披露（Tier 1→2→3）；openclaw 多源加载（bundled/plugin/clawhub/workspace）+ YAML frontmatter 解析 + 平台/agent 过滤 + 五种安装策略（brew/node/go/uv/download）+ `<available_skills>` XML 提示注入。
- **② 独立设计空间**：评价维度是技能来源多样性、安全扫描深度、安装自动化程度、上下文注入方式。
- **③ 持续 Trade-off**：社区市场（hermes-agent）技能来源最广但安全风险最高；多源加载+过滤（openclaw）灵活但用户需理解安装策略；简单加载（nanobot）最简单但扩展性最低。
- **来源 Entity**：nanobot/skills-loader, hermes-agent/skills-system, openclaw/skills

### 13. autonomous-scheduling — 如何实现 Agent 定时自主任务

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot 分离 cron-service（定时触发）+ heartbeat-service（空闲自主检查）；hermes-agent cron/scheduler.py 每 60s tick + 文件锁（fcntl）防多进程并发 + `[SILENT]` 静默抑制 + 自然语言关键词解析（"tomorrow 9am"）；openclaw Cron 表达式 → 网关 cron 服务 → 心跳系统提示注入 → agent 通过 cron 工具管理。
- **② 独立设计空间**：评价维度是调度表达方式、防重复执行机制、agent 对调度的感知方式。
- **③ 持续 Trade-off**：cron+heartbeat 分离（nanobot）职责清晰但管理两个系统；自然语言解析（hermes-agent）用户友好但解析不可靠；提示注入感知（openclaw）让 agent 了解调度但占用上下文。
- **来源 Entity**：nanobot/cron-service + heartbeat-service, hermes-agent/cron-scheduler, openclaw/cron-system

### 14. configuration-management — 如何管理运行时配置与多 Profile

- **覆盖仓库**：nanobot, hermes-agent, openclaw
- **① 多方案**：nanobot 多维运行时配置（env + CLI + config file）；hermes-agent `HERMES_HOME` profile 目录 + 每 profile 独立 `home/`（git/ssh/gh 隔离）+ `hermes profile` CLI 全生命周期管理；openclaw JSON5 + `$include` 模块化（10 层限制+循环检测）+ `${ENV}` 动态替换 + 固定顺序 `materializeRuntimeConfig` + Zod schema 分层验证。
- **② 独立设计空间**：评价维度是配置源的可组合性、多环境/profile 隔离强度、schema 验证与演化。
- **③ 持续 Trade-off**：Profile 隔离（hermes-agent）最强隔离但配置文件重复；模块化 include（openclaw）最灵活但可能产生复杂的包含链；简单多维（nanobot）最易上手但不适合复杂多环境场景。
- **来源 Entity**：nanobot/config-system, hermes-agent/config-system, openclaw/config-system

### 15. execution-isolation — 如何为 Agent 工具提供隔离的执行环境

- **覆盖仓库**：hermes-agent, openclaw（nanobot 仅 SSRF 防护，无执行环境隔离）
- **① 多方案**：hermes-agent `BaseEnvironment` ABC + 6 种后端（local/docker/modal/singularity/ssh/slurm）+ spawn-per-call 模型 + CWD 持久化（temp file/in-band marker）+ 300s 自动清理；openclaw 可插拔后端注册表（`registerSandboxBackend`）+ `SandboxFsBridge` 文件系统透明翻译 + session/agent/shared 三级作用域 + Docker/SSH 后端。
- **② 独立设计空间**：评价维度是后端可插拔性、文件系统透明性、环境生命周期管理。
- **③ 持续 Trade-off**：多后端（hermes-agent 6 种）覆盖面最广但每个后端维护成本高；FS Bridge（openclaw）文件透明但对 agent 有"魔法"感；spawn-per-call（hermes-agent）简单但冷启动延迟；持久容器（openclaw session scope）无冷启动但占用资源。
- **来源 Entity**：hermes-agent/terminal-execution, openclaw/sandbox

---

## C 类：待观察（6 条）

| # | 问题名 | 来源 | 层级 | 原因 |
|---|--------|------|------|------|
| 1 | 如何定义 core↔plugin 公共契约边界 | openclaw/plugin-sdk | 架构决策 | 仅 openclaw 有独立 Plugin SDK 三层入口体系；hermes-agent 的插件机制是基础设施，nanobot 无此抽象 |
| 2 | 如何安全处理多媒体文件上传 | openclaw/media-pipeline | 技术选型 | 仅 openclaw 有完整媒体管道（sharp/sips 双后端 + HEIC 转换 + SSRF 保护）；hermes-agent 和 nanobot 媒体处理较基础 |
| 3 | 如何实现跨平台后台服务管理 | openclaw/daemon | 技术选型 | 仅 openclaw 有统一 `GatewayService` 接口 + launchd/systemd/schtasks 三平台支持 |
| 4 | 如何设计 CLI 的双层路由架构 | openclaw/cli-system | 技术选型 | openclaw 有独特的快速路由+完整 Commander 双层设计；hermes-agent 和 nanobot 的 CLI 均为标准实现 |
| 5 | 如何持久化会话并支持全文跨会话检索 | hermes-agent/state-database | 架构决策 | 仅 hermes-agent 有 SQLite FTS5 + jitter 重试 + LLM 摘要的完整检索方案；此为 session-lifecycle-management 的子维度 |
| 6 | 如何让 Agent 从经验中程序性学习 | hermes-agent/agent-learning | 架构决策 | 与 skills-extension-mechanism 和 memory-management-architecture 高度重叠，可作为两者的交叉讨论维度 |

---

## D 类：演化信号（2 条）

已在 `/docs/evolve-signals/2026-06-25-hermes-agent-openclaw.md` 中记录：

| # | 问题 | 相关 Concept | 信号类型 | 理由 |
|---|------|-------------|----------|------|
| 1 | 事件驱动的 Agent 生命周期扩展点 | — | 粒度不匹配 | openclaw 有完整 hooks-system（4 源+3 级过滤+通配符），hermes-agent 有 gateway hooks，nanobot 有 AgentHook。三者处于不同成熟度——openclaw 是独立子系统，另外两个是轻量回调。未来若 hooks 成熟为跨仓库通用模式，可独立建 Concept |
| 2 | Channel↔Agent Core 消息传输层解耦 | — | 粒度不匹配 | nanobot 有独立 message-bus entity（异步解耦消息总线），hermes-agent 的 gateway-runner 内嵌消息流，openclaw 的 gateway 统一处理。消息总线作为独立层仅在 nanobot 存在，另两个将其融入 gateway。可能作为 session-lifecycle-management 的子维度 |

---

## 能力域覆盖表

| 能力域 | nanobot | hermes-agent | openclaw |
|--------|---------|-------------|----------|
| Agent 主循环编排 | agent-loop + agent-runner | agent-core | agent-runtime |
| 上下文窗口压缩 | agent-runner（微压缩+裁剪） | context-compressor | agent-runtime（压缩重试） |
| 多平台 Channel 抽象 | channel-system | platform-adapters + gateway-runner | channel-system |
| 会话身份与持久化 | session-manager | session-manager + state-database | session-system + routing-system |
| 系统提示词组装 | context-builder | prompt-builder | agent-runtime（system-prompt） |
| 长期记忆管理 | memory-system | memory-system | （嵌入式工具） |
| 工具注册与策略 | tool-registry | tool-registry + mcp-integration | tool-system |
| LLM Provider 抽象 | provider-system | model-adapters + provider-registry | model-configuration |
| 子 Agent 委托 | subagent-manager | delegate-subagent | subagent-system |
| 安全防御体系 | security-system | security-sandbox | security-system + approval-system |
| 执行审批 | — | security-sandbox（三级审批） | approval-system |
| 可插拔能力/Skills | skills-loader | skills-system | skills |
| 定时自主任务 | cron-service + heartbeat-service | cron-scheduler | cron-system |
| 配置与 Profile | config-system | config-system | config-system |
| 执行环境隔离 | — | terminal-execution（6 后端） | sandbox（Docker/SSH） |
| 插件公共契约 | — | — | plugin-sdk |
| 媒体管道 | — | — | media-pipeline |
| 跨平台后台服务 | — | — | daemon |
| 事件钩子扩展 | AgentHook（轻量） | gateway/hooks（轻量） | hooks-system（完整） |
| 消息总线/传输 | message-bus | （嵌入 gateway） | （嵌入 gateway） |
