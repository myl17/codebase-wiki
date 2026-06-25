# 候选 Concept 详细清单 R2

> 生成日期：2026-06-17
> 用途：Phase 3a — Concept 页创建的输入模板
> 共 7 个候选 Concept

---

## 候选 Concept #1: llm-input-token-cost-reduction

**问题陈述**：如何降低多轮对话中 LLM 调用的 input token 成本？

**维度**：Performance Tradeoffs

**涉及的 openclaw 种子条目**：如何降低 LLM system prompt 的 token 输入成本？（#8）

**涉及的 hermes 种子条目**：跨消息 Agent 实例复用（#10）

**openclaw 选择**：`OPENCLAW_CACHE_BOUNDARY` 标记切分稳定前缀和动态后缀，稳定部分命中 Anthropic Prompt Caching。在 prompt 内容层面设计缓存边界。

**hermes 选择**：跨消息缓存 AIAgent 实例（非每条消息新建），使 LLM API 层的 prompt cache prefix 在跨消息对话中持续有效。在进程实例层面维持缓存。

**openclaw 溯源**：
- Entity 页：entity/openclaw-context-engine.md
- 源码路径：src/agents/system-prompt-cache-boundary.ts

**hermes 溯源**：
- Entity 页：entity/hermes-gateway-platform.md
- 源码路径：gateway/run.py:604-611

**差异分析**：同一目标（降低 input token 成本），不同干预层次。openclaw 在 prompt 内容结构上动手（标记静态/动态边界让 LLM 服务端缓存），hermes 在客户端对象生命周期上动手（复用 agent 实例保持连接级缓存）。两种策略互补而非互斥 — openclaw 的策略依赖服务端缓存行为（Anthropic-specific），hermes 的策略更通用但粒度更粗。

**状态**：新 Concept

---

## 候选 Concept #2: memory-retrieval-timing

**问题陈述**：如何确定记忆检索的最佳时机以最小化对 LLM 调用的延迟影响？

**维度**：Architecture / Performance Tradeoffs

**涉及的 openclaw 种子条目**：如何在正确的时机注入记忆？（#13）

**涉及的 hermes 种子条目**：记忆检索的延迟优化（#14）

**openclaw 选择**：记忆在 prompt 组装阶段注入（`before_prompt_build` / `before_agent_start` hook），不在每次 LLM 输出后实时查询。确保记忆在 LLM 调用前稳定存在，不消耗额外 LLM 调用。代价是注入时机固定，无法在对话中途动态补充。

**hermes 选择**：后台异步预取（`queue_prefetch`），当前 turn 完成后触发，下一轮调用时返回上一轮的缓存结果。记忆检索不在 LLM API 调用关键路径上阻塞。代价是记忆可能落后一轮（上一轮新写入在当前轮不可见）。

**openclaw 溯源**：
- Entity 页：entity/openclaw-memory-system.md
- 源码路径：src/memory-host-sdk/host/types.ts

**hermes 溯源**：
- Entity 页：entity/hermes-memory-manager.md
- 源码路径：agent/memory_provider.py:106-112

**差异分析**：都解决「记忆检索不能阻塞 LLM 调用」的问题。openclaw 选择在 prompt 组装时一次性注入（静态、确定性），hermes 选择异步流水线化（动态、非阻塞但有 staleness 窗口）。核心分歧在于是否接受 staleness：openclaw 选择无 staleness 但时机固定，hermes 选择低延迟但一轮 staleness。

**状态**：新 Concept

---

## 候选 Concept #3: dangerous-operation-prevention

**问题陈述**：如何在 agent 框架中可靠地防止危险操作执行？

**维度**：Architecture

**涉及的 openclaw 种子条目**：如何在关键路径上做工具权限控制？（#26）

**涉及的 hermes 种子条目**：危险命令检测机制（#6）

**openclaw 选择**：权限决策在消息处理关键路径上做同步门控。工具集在进入 LLM 的 function-calling 视野之前已按 allowlist/denylist 过滤完毕（事前门控）。根本防止 LLM 看到并尝试调用无权限工具。

**hermes 选择**：25+ 危险模式正则（rm/chmod/mkfs/kill/systemctl/curl|sh/git reset --hard 等）作为主防线，LLM 判断作为补充。正则确定性匹配，不受 LLM 幻觉影响。与 tirith 安全扫描结果合并后审批。

**openclaw 溯源**：
- Entity 页：entity/openclaw-tool-policy.md
- 源码路径：src/agents/tool-policy-pipeline.ts

**hermes 溯源**：
- Entity 页：entity/hermes-approval-system.md
- 源码路径：tools/approval.py:75-138

**差异分析**：同一目标（防止危险操作），不同防御层。openclaw 在工具可见性层面做门控（LLM 看不到危险工具就不可能调用），hermes 在命令执行前做内容扫描（LLM 可以生成危险命令但会被拦截）。两者互补 — 门控减少攻击面，扫描捕获漏网之鱼（如合法工具被滥用于危险目的）。

**状态**：新 Concept

---

## 候选 Concept #4: tool-execution-safety-approval

**问题陈述**：如何为高风险工具执行设计安全审批机制？

**维度**：Architecture

**涉及的 openclaw 种子条目**：如何安全地授权高风险工具执行？（#27）

**涉及的 hermes 种子条目**：命令安全审批层级（#4）

**openclaw 选择**：exec 类工具走异步审批协议。注册 `ExecApprovalRequest`，阻塞等待 owner 的 approve/deny 决策。支持 host 和 gateway 双路径审批通道。允许助手「请求许可」而非「请求原谅」。

**hermes 选择**：三层审批架构 — Layer 0 为 YOLO 模式全放行；Layer 1（Smart）用便宜辅助 LLM 自动评估，明显安全/危险的自动处理；Layer 2（Manual）模糊情况升级到用户交互式审批 [o/s/a/d]。目的是用辅助 LLM 分担人工审批决策，降低用户疲劳。

**openclaw 溯源**：
- Entity 页：entity/openclaw-tool-policy.md
- 源码路径：src/agents/bash-tools.exec-approval-request.ts

**hermes 溯源**：
- Entity 页：entity/hermes-approval-system.md
- 源码路径：tools/approval.py:586-922（主入口）、tools/approval.py:534-583（Smart 层）

**差异分析**：同一领域（审批流程），不同信任模型。openclaw 将审批决策完全交给人类（单层人工），hermes 引入辅助 LLM 预筛选（多层 AI+人工）。核心分歧在于是否信任辅助 LLM 做安全判断 — openclaw 倾向保守（不引入额外 AI 判断链路），hermes 倾向自动化（辅助 LLM 处理大部分减少人工疲劳）。

**状态**：新 Concept

---

## 候选 Concept #5: plugin-subsystem-auto-discovery

**问题陈述**：如何让 plugin 子系统无需手动配置即可被框架发现和使用？

**维度**：Extension Points

**涉及的 openclaw 种子条目**：如何让子系统被框架发现和自动选择？（#2）

**涉及的 hermes 种子条目**：工具注册的发现机制（#25）

**openclaw 选择**：`supports(ctx)` + priority 排序的策略模式。每个 harness plugin 实现 `supports()` 声明适用场景（模型前缀、endpoint 等），core 按 priority 排序选第一个返回 true 的实现。plugin 自主声明，core 不需要了解每个 provider 的选择条件。

**hermes 选择**：AST 扫描自动发现 `registry.register()` 顶层调用。新工具只需在文件顶层调用 `registry.register()`，不需要修改任何现有文件。依赖静态分析约定（只扫描顶层调用），有一定的隐式假设。

**openclaw 溯源**：
- Entity 页：entity/openclaw-agent-harness.md
- 源码路径：src/agents/harness/types.ts

**hermes 溯源**：
- Entity 页：entity/hermes-tool-registry.md
- 源码路径：tools/registry.py:28-73

**差异分析**：同样的「零配置自动发现」目标，不同的实现策略。openclaw 适用运行时策略匹配（适合有选择逻辑的 scenario — 多个 provider 竞争一个槽位），hermes 适用静态代码扫描（适合无条件注册的 scenario — 每个工具独立注册）。策略模式适合支持条件选择，AST 扫描摩擦最低但不适合有复杂选择逻辑的场景。

**状态**：新 Concept

---

## 候选 Concept #6: context-compression-quality

**问题陈述**：如何在上下文压缩中平衡信息保真度和 token 节省？

**维度**：Performance Tradeoffs

**涉及的 openclaw 种子条目**：
1. 如何在压缩对话历史时保留关键任务状态？（#7）
2. 如何减少压缩摘要中的噪声？（#10）

**涉及的 hermes 种子条目**：长对话上下文管理（#7）

**openclaw 选择**：
- 任务状态保留：压缩时优先保留活跃任务状态、批处理进度、最后一次用户请求（可恢复性优先于最大化压缩率）
- 噪声减少：`tool_result.details` 在压缩前被 strip，不参与摘要生成

**hermes 选择**：
- 辅助（便宜）LLM 摘要中间轮次，牺牲信息保真度换取无限长对话
- 结构化摘要模板确保关键信息不丢失
- token-budget tail 保护：为最后 N 轮对话保留下限 token
- 工具输出修剪：先裁剪冗长输出再摘要（与 openclaw #10 一致）
- Summary budget：压缩内容的 20%，上限 12,000 tokens
- 失败退避：摘要失败冷却 600 秒防重试风暴

**openclaw 溯源**：
- Entity 页：entity/openclaw-context-engine.md
- 源码路径：src/agents/compaction.ts

**hermes 溯源**：
- Entity 页：entity/hermes-context-engine.md
- 源码路径：agent/context_compressor.py:1-60、agent/context_compressor.py:51-53（budget）、agent/context_compressor.py:60（冷却）

**差异分析**：同一问题域，多个优化子方向。openclaw 的优化集中在「保留什么」（任务状态）和「移除什么」（工具输出），hermes 的优化更系统化（触发、方法、模板、预算、容错）。两者在工具输出裁剪上一致（对齐 A1）。hermes 额外引入辅助 LLM 做摘要（与自身 LLM 分离），而 openclaw 的压缩方法未引入额外 LLM。

**状态**：新 Concept（注：openclaw 种子 #7 和 #10 是两个独立条目，在此 Concept 中作为不同优化维度）

---

## 候选 Concept #7: context-engine-singleton-vs-pluggable

**问题陈述**：Context Engine 应如何在状态安全和扩展灵活性之间权衡？

**维度**：Extension Points / Architecture（设计张力）

**涉及的 openclaw 种子条目**：如何避免多个 context engine 实现并存的状态冲突？（#9）

**涉及的 hermes 种子条目**：上下文压缩策略的可扩展性（#9）

**openclaw 选择**：`registerContextEngine` 为独占槽位，全局只能有一个活跃实现。独占设计强制使用者明确选择一个实现，避免多个实现隐式竞争对话状态导致冲突。

**hermes 选择**：ContextEngine ABC 接口提供标准压缩协议（`should_compress()` / `compress()` / `update_from_response()` / `get_tools()`），第三方实现放入 `plugins/context_engine/<name>/` 目录，通过 `config.yaml` 切换激活。同一时间只有一个 engine 激活，但可随时切换。

**openclaw 溯源**：
- Entity 页：entity/openclaw-context-engine.md
- 源码路径：src/context-engine/index.ts

**hermes 溯源**：
- Entity 页：entity/hermes-context-engine.md
- 源码路径：agent/context_engine.py:32-60

**差异分析**：同一子系统（Context Engine）的相反设计哲学。openclaw 把「安全」放在首位 — 单例强制确保没有状态竞争；hermes 把「灵活」放在首位 — ABC 接口允许外部实验不同压缩策略。两者的共识是同一时间只能有一个 engine 激活，但开放程度不同：openclaw 用硬编码独占槽位，hermes 用接口抽象 + 配置切换。openclaw 需要代码级修改才能替换，hermes 只需改配置 + 放入 plugin 文件。

**状态**：新 Concept

---
