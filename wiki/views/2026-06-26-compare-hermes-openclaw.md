---
type: view
repos: [hermes-agent, openclaw]
concepts: [skills-extension-mechanism, memory-management-architecture, context-compression-strategy, channel-abstraction-pattern, agent-loop-orchestration, execution-isolation, security-architecture, subagent-orchestration, autonomous-scheduling, provider-abstraction-pattern, system-prompt-assembly, tool-lifecycle-management, configuration-management, execution-approval-pattern, session-lifecycle-management]
generated: 2026-06-26
source_level: Concept + 源码（compaction.ts）
sources: ["wiki/concepts/skills-extension-mechanism.md", "wiki/concepts/memory-management-architecture.md", "wiki/concepts/context-compression-strategy.md", "wiki/concepts/channel-abstraction-pattern.md", "wiki/concepts/agent-loop-orchestration.md", "wiki/concepts/execution-isolation.md", "wiki/concepts/security-architecture.md", "wiki/concepts/subagent-orchestration.md", "wiki/concepts/autonomous-scheduling.md", "src/agents/compaction.ts"]
---

# hermes-agent vs openclaw — 核心差异对比

## 跨维度根本张力

**hermes-agent 把 Agent 当作一个会学习的生命体**——它能创造 Skill、整理记忆、多阶段压缩保留决策链、在 6 种环境中执行、用 Tirith 二进制做深度安全扫描。代价是系统复杂度高、组件耦合紧、单文件巨大（run_agent.py 持续增长）。

**openclaw 把 Agent 当作一个可插拔的运行时平台**——插件 SDK 定义契约边界、渠道 30+ adapter 渐进式实现、SandboxFsBridge 透明路径翻译、记忆只是工具目录中的一行。代价是每个子系统偏轻量、部分能力（记忆自主演化、主动上下文压缩、深度命令安全扫描）依赖外部插件补全。

## 五个最显著的差异维度

### 1. Skills 哲学：自我进化的程序性记忆 vs 静态配置模块

| | hermes-agent | openclaw |
|---|---|---|
| 来源 | `skills-extension-mechanism` | `skills-extension-mechanism` |
| 解法 | Agent 可自主创建/编辑/删除 Skill，8 源联邦市场搜索，Quarantine 隔离安装，三级信任策略 | 三源本地加载（bundled/plugin/workspace），5 种安装策略自动处理依赖，7 层工具过滤管道 |
| 取舍 | 功能最完整——Skills 是 Agent 的程序性记忆。代价是复杂度最高 | 安装自动化最强——但 Skills 是静态手工制品，Agent 是消费者而非创造者 |

**核心差异**：hermes-agent 把 Skill 当作 Agent 自己的记忆——能创造、改进、从社区获取。openclaw 把 Skill 当作插件配置——精细的工具过滤和安装自动化，但 Agent 不能从经验中创建 Skill。

### 2. 记忆架构：独立记忆系统 vs 嵌入式工具域

| | hermes-agent | openclaw |
|---|---|---|
| 来源 | `memory-management-architecture` | `memory-management-architecture` |
| 解法 | MemoryManager 独立系统，8 种外部 backend + 文件，冻结快照 + fcntl 锁 + 原子写入 | 记忆归入工具目录 Memory 节，append-only write，与其他工具共享生命周期 |
| 取舍 | 存储后端最丰富、并发安全性最完善。但无自主演化 | 最轻量——但无 consolidation、无自主编辑、连修正已有记忆都做不到 |

**核心差异**：hermes-agent 的记忆是完整的子系统——8 种后端、并发安全、prompt cache 优化。openclaw 的记忆是工具目录中的一行——轻量但 append-only。

### 3. 上下文压缩：硬编码 11 字段结构化摘要 vs 迭代摘要链 + prose 质量指令

| | hermes-agent | openclaw |
|---|---|---|
| 来源 | `context-compression-strategy` | `context-compression-strategy` + `src/agents/compaction.ts` |
| 解法 | 三阶段管线：工具结果裁剪 → token 边界确定 → 辅模型生成 11 字段结构化摘要（Goal、Completed Actions、Active State、In Progress、Blocked、Key Decisions、Relevant Files、Critical Context 等） | 迭代摘要链：chunk → `generateSummary(chunk, previousSummary)` 逐步累积 + N 段并行摘要 → MERGE_INSTRUCTIONS 合并（prose 指令保留活跃任务、决策、TODO、承诺等） |
| 取舍 | 保真度最高——11 字段完整记录决策路径。但每次压缩一次 LLM 调用+延迟 | 迭代链避免单次超大 prompt，prose 指令使摘要长度自适应。但输出纪律依赖 LLM——可能漏维度，不如字段模板可靠 |

**核心差异**：hermes-agent 用结构保证完整性（11 个确定性字段），openclaw 用流程保证完整性（迭代累积 + 多层降级）。前者牺牲灵活性换可预测性，后者牺牲可预测性换灵活性。

### 4. Channel 抽象粒度：厚统一接口 vs 极细粒度分解

| | hermes-agent | openclaw |
|---|---|---|
| 来源 | `channel-abstraction-pattern` | `channel-abstraction-pattern` |
| 解法 | 厚 ABC（send/edit/react），18 个平台适配器，流式编辑桥接平台原生 API | 30+ 可选 adapter 极细粒度分解，ChannelCapabilities 声明式能力查询，插件化注册 |
| 取舍 | Agent 可利用平台高级特性（inline keyboard、block kit、审批流），但 Feishu 适配器 165KB | 第三方扩展便利性最强——插件化注册不修改框架源码，但 30+ adapter 碎片化 |

**核心差异**：hermes-agent 追求 Agent 的交互表现力（厚接口保留平台原生体验），openclaw 追求生态扩展性（极细粒度分解让第三方渐进式实现）。

### 5. Agent Loop 编排：单类 + 多级错误恢复 vs 函数式 + lane 双锁

| | hermes-agent | openclaw |
|---|---|---|
| 来源 | `agent-loop-orchestration` | `agent-loop-orchestration` |
| 解法 | AIAgent 单一类承载完整循环，6 类 API 错误分类 + 模型 fallback + 异步探活 | `runEmbeddedPiAgent` 函数式 while(true)，session lane + global lane 双锁，全局单例追踪 |
| 取舍 | 错误恢复最丰富——分类+fallback+探活提供高可用。但 AIAgent 单文件持续增长 | lane 双锁提供最细粒度并发控制。但 while(true) 中深度耦合压缩重试、超时恢复、溢出判定 |

**核心差异**：hermes-agent 偏向高可用（多级错误恢复），openclaw 偏向并发安全（lane 双锁 + 全局单例追踪）。

## 完整对比矩阵

| 维度 | hermes-agent | openclaw | 根本张力 |
|------|-------------|----------|---------|
| Agent Loop | 单类 AIAgent + 6 类错误分类 + 模型 fallback | 函数式 while(true) + lane 双锁 | 高可用 vs 并发安全 |
| Skills | Agent 自主创建 + 8 源市场 + Quarantine | 三源本地 + 5 种安装策略 + 7 层过滤 | 自主进化 vs 静态配置 |
| Memory | 8 种 backend + 冻结快照 + fcntl 锁 | 嵌入式工具域 + append-only | 独立系统 vs 轻量嵌入 |
| Context Compression | 11 字段结构化摘要 + 反震荡保护 | 迭代摘要链 + prose MERGE 指令 + 渐进降级 | 结构保证 vs 流程保证 |
| Channel | 厚 ABC + 18 平台 + 原生交互保留 | 30+ adapter + 插件化注册 | 交互表现力 vs 生态扩展性 |
| Execution Isolation | 6 种后端 spawn-per-call + CWD 持久化 | SandboxFsBridge 透明路径翻译 + 三种作用域 | 广度覆盖 vs 透明隔离 |
| Security | Tirith + 40+ 模式 + LLM 智能审批 + 配对码 | 4D 审计框架 + 四档 DM 策略 + 可插拔收集器 | 深度防御 vs 柔性伸缩 |
| Subagent | ThreadPoolExecutor + 共享 IterationBudget | Gateway 调度 + 双层持久化 + 孤儿恢复 | 并行执行 vs 故障恢复 |
| Scheduling | fcntl 锁 + 自然语言 + [SILENT] 静默 | 心跳提示注入 + Agent 用 cron 工具自主管理 | 防重复 vs Agent 感知 |
| Provider | 20+ Provider + API 模式自动检测 | 模型/Provider 配置 + 故障切换链 | 覆盖广度 vs 切换优雅 |
| System Prompt | 多层组装 + 模型特定执行纪律 | 27 个按序节 + 渠道提示 + 心跳注入 | 模型适配 vs 渠道适配 |
| Tool Lifecycle | 自动发现 + toolset 组合 | Tool catalog + 7 层策略过滤管道 | 灵活性 vs 可控性 |
| Configuration | Profile 隔离 + 时区感知 | JSON5 + $include + ${ENV} | 运行时隔离 vs 声明式组合 |
| Approval | Tirith + LLM 智能审批 + DM 配对码 | 审批工作流 + 超时决策 | 多层验证 vs 简洁流程 |
| Session | 跨平台会话 + 确定性 session key | 会话存储 + 转录 + 磁盘预算 | 跨平台连续性 vs 存储治理 |
