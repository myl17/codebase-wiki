# 交叉审查报告 R2：openclaw 种子库 vs hermes 设计草稿

> 审查日期：2026-06-17
> 输入：openclaw 种子库（28 条）+ hermes 设计草稿（28 条）

---

## 一、对齐成功：答案相同，追加 hermes 实例

以下条目中 hermes 和 openclaw 面对相同问题、给出相同或高度一致的答案，不升级为 Concept，仅需将 hermes 实例行追加到 openclaw 种子条目中。

### A1：压缩前裁剪工具输出以减少摘要噪声

- **openclaw 种子条目**：如何减少压缩摘要中的噪声？（Architecture）
  - 选择：`tool_result.details` 在压缩前被 strip
  - 溯源：entity/openclaw-context-engine.md → src/agents/compaction.ts
- **hermes 对应**：长对话上下文管理（#7，Performance Tradeoffs）
  - 选择：工具输出修剪（先剪后摘要）
  - 溯源：entity/hermes-context-engine.md → agent/context_compressor.py:1-60
- **一致性**：两者都在压缩前裁剪冗长工具输出。hermes 的「先剪后摘要」与 openclaw 的 strip `tool_result.details` 是同一策略的不同表述。
- **操作**：在 openclaw 种子条目 #10 中追加 hermes 实例行。

### A2：上下文压缩中的任务信息保留

- **openclaw 种子条目**：如何在压缩对话历史时保留关键任务状态？（Performance Tradeoffs）
  - 选择：可恢复性优先 — 保留活跃任务状态、批处理进度、最后一次用户请求
  - 溯源：entity/openclaw-context-engine.md → src/agents/compaction.ts
- **hermes 对应**：长对话上下文管理（#7，Performance Tradeoffs）
  - 选择：结构化摘要模板 + token-budget tail 保护，保留语义连续性
  - 溯源：entity/hermes-context-engine.md → agent/context_compressor.py:1-60
- **一致性**：两者都在压缩时优先保留关键信息（任务状态 vs 对话 tail）。hermes 的 token-budget tail 保护和 openclaw 的「最后用户请求保留」在意图上一致。
- **操作**：在 openclaw 种子条目 #7 中追加 hermes 实例行。

---

## 二、候选 Concept 清单

### 候选 Concept #1：如何降低多轮对话中 LLM 调用的 input token 成本？

- **维度**：Performance Tradeoffs
- **openclaw 种子条目**：如何降低 LLM system prompt 的 token 输入成本？（#8）
  - 选择：`OPENCLAW_CACHE_BOUNDARY` 标记切分稳定/动态前缀，命中 Anthropic Prompt Caching
  - 溯源：entity/openclaw-context-engine.md → src/agents/system-prompt-cache-boundary.ts
- **hermes 种子条目**：跨消息 Agent 实例复用（#10）
  - 选择：跨消息缓存 AIAgent 实例，维持 prompt cache prefix 持续有效
  - 溯源：entity/hermes-gateway-platform.md → gateway/run.py:604-611
- **异同**：同一目标（降低 input token 成本），不同层次 — openclaw 在 prompt 内容层面设计缓存边界，hermes 在进程实例层面复用 agent 对象。
- **状态**：新 Concept

### 候选 Concept #2：如何确定记忆检索的最佳时机？

- **维度**：Architecture / Performance Tradeoffs
- **openclaw 种子条目**：如何在正确的时机注入记忆？（#13）
  - 选择：记忆在 prompt 组装阶段注入，而非每轮 LLM 输出后实时查询
  - 溯源：entity/openclaw-memory-system.md → src/memory-host-sdk/host/types.ts
- **hermes 种子条目**：记忆检索的延迟优化（#14）
  - 选择：后台异步预取（queue_prefetch），下一轮使用上一轮完成后的缓存结果
  - 溯源：entity/hermes-memory-manager.md → agent/memory_provider.py:106-112
- **异同**：都关注记忆检索不阻塞 LLM 调用。openclaw 在 prompt 组装时一次性注入（静态时机），hermes 用异步预取以一轮延迟为代价换取非阻塞（动态时机）。
- **状态**：新 Concept

### 候选 Concept #3：如何在 agent 框架中防护危险工具操作？

- **维度**：Architecture
- **openclaw 种子条目**：如何在关键路径上做工具权限控制？（#26）
  - 选择：权限决策在消息处理关键路径上做同步门控，工具集在进入 LLM 之前已过滤完毕（事前门控）
  - 溯源：entity/openclaw-tool-policy.md → src/agents/tool-policy-pipeline.ts
- **hermes 种子条目**：危险命令检测机制（#6）
  - 选择：25+ 危险模式正则作为主防线，LLM 判断作为补充（执行前检测）
  - 溯源：entity/hermes-approval-system.md → tools/approval.py:75-138
- **异同**：同一目标（防止危险操作），不同层次。openclaw 在 LLM 视野层面过滤工具可见性（不让 LLM 看到危险工具），hermes 在命令内容层面用正则检测（LLM 可以生成命令但会被拦截）。两种方法互补 — 门控减少攻击面，扫描捕获漏网之鱼。
- **状态**：新 Concept

### 候选 Concept #4：如何设计工具执行的安全审批机制？

- **维度**：Architecture
- **openclaw 种子条目**：如何安全地授权高风险工具执行？（#27）
  - 选择：exec 类工具走异步审批协议，阻塞等待 owner 决策（支持 host/gateway 双路径审批）
  - 溯源：entity/openclaw-tool-policy.md → src/agents/bash-tools.exec-approval-request.ts
- **hermes 种子条目**：命令安全审批层级（#4）
  - 选择：三层审批（YOLO → Smart → Manual），便宜辅助 LLM 自动处理明显安全/危险的命令，模糊情况升级到人工审批
  - 溯源：entity/hermes-approval-system.md → tools/approval.py:586-922（主入口）、tools/approval.py:534-583（Smart 层）
- **异同**：同一领域（工具执行审批），不同模型。openclaw 采用异步协议 + 人类决策的单层模型，hermes 采用辅助 LLM 预筛选 + 人类确认的三层模型。核心分歧在于是否信任辅助 LLM 分担审批决策。
- **状态**：新 Concept

### 候选 Concept #5：如何让 plugin 子系统实现零配置自动发现？

- **维度**：Extension Points
- **openclaw 种子条目**：如何让子系统被框架发现和自动选择？（#2）
  - 选择：`supports(ctx)` + priority 排序的策略模式 — plugin 自主声明适用场景，core 按 priority 选第一个匹配的
  - 溯源：entity/openclaw-agent-harness.md → src/agents/harness/types.ts
- **hermes 种子条目**：工具注册的发现机制（#25）
  - 选择：AST 扫描自动发现 `registry.register()` 顶层调用，新工具无需修改任何现有文件
  - 溯源：entity/hermes-tool-registry.md → tools/registry.py:28-73
- **异同**：同样的自动发现目标，不同的发现机制。openclaw 用运行时策略匹配（声明式接口），hermes 用静态代码扫描（AST 约定）。两种机制适用于不同的注册模型：策略模式适合有选择逻辑的场景，AST 扫描适合无条件注册的场景。核心 Concept 是「自动发现」，不是具体机制。
- **状态**：新 Concept

### 候选 Concept #6：如何在上下文压缩中平衡信息保真度和 token 节省？

- **维度**：Performance Tradeoffs
- **openclaw 种子条目**：
  - 如何在压缩对话历史时保留关键任务状态？（#7）：可恢复性优先，保留活跃任务状态
  - 如何减少压缩摘要中的噪声？（#10）：压缩前 strip 工具输出
  - 溯源：entity/openclaw-context-engine.md → src/agents/compaction.ts
- **hermes 种子条目**：长对话上下文管理（#7）
  - 选择：辅助 LLM 摘要中间轮次 + 结构化摘要模板 + token-budget tail 保护 + 工具输出修剪
  - 溯源：entity/hermes-context-engine.md → agent/context_compressor.py:1-60
- **异同**：同一问题域（上下文压缩质量），多个优化子方向。openclaw 关注保留什么（任务状态）和移除什么（工具输出噪声），hermes 关注如何摘要（辅助 LLM + 结构化模板）和摘要预算控制。两者在工具输出裁剪上一致（见 A1）。
- **状态**：新 Concept（注：OC#7 和 OC#10 是两个独立种子条目，但在此 Concept 中合并为不同优化子方向）

### 候选 Concept #7：Context Engine 应是单例还是可插拔？

- **维度**：Extension Points / Architecture（设计张力）
- **openclaw 种子条目**：如何避免多个 context engine 实现并存的状态冲突？（#9）
  - 选择：`registerContextEngine` 为独占槽位，全局只能有一个活跃实现
  - 溯源：entity/openclaw-context-engine.md → src/context-engine/index.ts
- **hermes 种子条目**：上下文压缩策略的可扩展性（#9）
  - 选择：ContextEngine ABC 接口，第三方实现放入 `plugins/context_engine/`
  - 溯源：entity/hermes-context-engine.md → agent/context_engine.py:32-60
- **异同**：同一子系统（Context Engine）的相反设计选择。openclaw 强制执行单例以防止状态冲突（安全优先），hermes 提供 ABC 接口允许外部插件替换压缩策略（灵活优先）。这是经典的单例 vs 策略模式的张力，没有绝对优劣。
- **状态**：新 Concept

---

## 三、hermes 独有条目（openclaw 种子库中无对应）

以下条目在 openclaw 种子库中无对应，经回溯 openclaw Entity 页确认后判定为 hermes 独有或 openclaw 未覆盖。

| # | hermes 条目 | 维度 | 回溯 openclaw 结论 |
|---|------------|------|-------------------|
| H#3 | 对话轮次预算控制 | Performance Tradeoffs | openclaw 使用 token-based context window guard（硬限 16000、软警告 32000），而非轮次预算。不同防护维度 |
| H#8 | 上下文压力通知策略 | Performance Tradeoffs | openclaw context engine 有软警告阈值（32000 tokens），但通知策略（是否通知用户、是否注入 LLM）未在种子库中捕获。**建议补充 openclaw 条目** |
| H#12 | Gateway 环境下的审批等待策略 | Architecture | openclaw 使用异步审批协议，不阻塞线程；hermes 使用 FIFO + threading.Event 阻塞等待。openclaw 种子 #27 覆盖审批协议但不覆盖等待策略的具体实现 |
| H#16 | 日志安全脱敏 | Architecture | openclaw 无 observability Entity 页，API key 脱敏策略未被种子库覆盖。**建议补充 openclaw 条目（若存在脱敏机制）** |
| H#17 | 日志文件组织策略 | Architecture | 同上，openclaw 无 observability Entity。**可补充** |
| H#18 | 后台进程输出管理 | Performance Tradeoffs | openclaw 有 Process Supervisor（#22）但关注生命周期编排而非输出缓冲管理。不同关注点 |
| H#19 | Agent 自学习触发机制 | Architecture | openclaw 有 Skills 系统（Markdown 文件扩展）但无自学习触发，依赖人类创建技能。hermes 独有 |
| H#20 | 技能注入策略 | Architecture | openclaw 种子 #17 关注扩展格式（Markdown），不关注注入策略（全量 vs 向量检索）。hermes 补充了注入策略维度 |
| H#21 | 技能的自我维护能力 | Extension Points | openclaw 无对应。Skills 一旦创建由人类维护。hermes 独有 |
| H#22 | 外部技能安全分级 | Architecture | openclaw Skills 为 Markdown 文件，风险较低（仅 prompt 注入风险），无对应安全分级机制。hermes 独有 |
| H#23 | 技能安装安全防护 | Dependency Strategy | openclaw channel plugin 通过 npm 包隔离（#4），但安装过程不涉及 quarantine。不同防护模型 |
| H#24 | 安全模块的测试策略 | Testing Philosophy | openclaw 种子 #19 覆盖 plugin 接口契约测试，不覆盖安全规则边界测试。不同测试关注点 |
| H#27 | 工具集的组合与复用 | Extension Points | openclaw 用 tool policy pipeline 做权限过滤（#28），不做 toolset 组合复用。不同概念 |

---

## 四、openclaw 反向检查补充

以下 openclaw 种子条目经反向检查后，确认 hermes 草稿中漏提或可补充。

### 补充 1：openclaw 种子 #1 — LLM provider 接口粒度 → hermes 可能相关

- **openclaw 种子**：如何让 LLM provider 的接口粒度恰到好处？（Architecture）
  - 选择：`compact?` 和 `reset?` 设计为可选方法
  - 溯源：entity/openclaw-agent-harness.md → src/agents/harness/types.ts
- **hermes 回溯**：AIAgent 作为中央编排器直接处理 LLM 调用，但没有显式的 provider 抽象层。hermes 在实践中也支持多个 LLM provider（通过 litellm），但 provider 接口的粒度设计未被提取为设计选择。
- **建议**：若 hermes 通过 litellm 或其他中间层支持多 provider，应补充 hermes 条目说明其 provider 抽象策略。

### 补充 2：openclaw 种子 #11 — 控制平面与 AI 执行层分离 → hermes 实现相似

- **openclaw 种子**：如何让控制平面和 AI 执行层解耦？（Architecture）
  - 选择：Gateway 是纯 HTTP 路由层，不包含 AI 调用逻辑
  - 溯源：entity/openclaw-gateway.md → src/gateway/
- **hermes 回溯**：hermes 的 GatewayRunner + BasePlatformAdapter 负责平台消息路由，AIAgent 负责 AI 执行。两者在架构上实现了类似的控制/执行分离。
- **建议**：hermes 草稿 #11（多平台适配架构）侧重适配器统一接口，可补充一条独立种子聚焦「控制平面与 AI 执行层分离」的设计选择。

### 补充 3：openclaw 种子 #23 — Cron 任务隔离 → hermes 有 cron delivery 但未作为独立种子

- **openclaw 种子**：如何让定时任务不污染用户对话历史？（Architecture）
  - 选择：Cron 使用 isolated-agent 模式
  - 溯源：entity/openclaw-task-cron.md → src/cron/
- **hermes 回溯**：hermes gateway-platform Entity 页提及 BasePlatformAdapter 包含 cron delivery 功能。hermes 内部有 cron 支持但未被提取为设计选择种子。
- **建议**：补充 hermes 条目说明其 cron 任务的隔离策略。

### 补充 4：openclaw 种子 #28 — 多粒度工具权限 → hermes 审批持久化可作为对应

- **openclaw 种子**：如何实现多粒度的工具权限策略？（Extension Points）
  - 选择：5 层 pipeline 叠加（profile/provider/global/agent/group）
  - 溯源：entity/openclaw-tool-policy.md → src/agents/tool-policy-pipeline.ts
- **hermes 回溯**：hermes 草稿 #5（审批结果持久化策略）涉及 once/session/always 三级持久化，是工具权限策略的一个维度（时效性粒度），但不同于 openclaw 的配置层级粒度。
- **建议**：可考虑作为独立 Concept 候选（工具权限的多粒度配置），但两个仓库关注的粒度轴不同。

---

## 五、统计摘要

| 类别 | 数量 |
|------|------|
| openclaw 种子条目 | 28 |
| hermes 草稿条目 | 28 |
| 对齐成功（追加实例） | 2 |
| 候选 Concept | 7 |
| hermes 独有 | 13 |
| openclaw 独有 | 16 |
| openclaw 反向补充建议 | 4 |
