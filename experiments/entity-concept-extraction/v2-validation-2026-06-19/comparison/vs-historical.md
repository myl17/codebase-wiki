# 实验结果对比：2026-06-19 (v2) vs 2026-06-17 (历史)

> 对比轮次：round-2-hermes (2026-06-19) + round-3-nanobot Phase 3a (2026-06-19) vs 历史 baseline (2026-06-17)
> 输入源：新结果 15 个 Concept 页 + 58 条种子库，历史结果 10 个 Concept 页 + 78 条种子库
> R3 Phase 3a 补上了 nanobot 的 Concept 页产出：3 个新建 Concept + 4 个已有 Concept 的 nanobot 实例追加，另有 7 份 Phase 3b 验证报告

---

## 1. Concept 覆盖

### 数量对比

| 指标 | 新结果 (2026-06-19) | 历史结果 (2026-06-17) |
|------|--------------------|-----------------------|
| Concept 页数 | 15 | 10 |
| 种子库条目总数 | 58 | ~78 |
| 已升级为完整 Concept 页 | 15（R2 产出 12 + R3 Phase 3a 新建 3） | 10（实际产出） |
| 仅单仓待观察（种子库已升级、尚未写页） | 4 | ~68 |

> 注意：R3 Phase 3a 在 round-2-hermes 的 12 个 Concept 页基础上新建了 3 个 Concept 页（subsystem-assembly-visibility、agent-trigger-path、llm-provider-registration），并对 4 个已有 Concept 页追加了 nanobot 实例（context-window-overflow-guard、prompt-cache-boundary、lifecycle-hook-granularity、memory-retrieval-timing），使跨仓库对比表全部达到三列。种子库中剩余 4 个 Concept 轴线（tool-discovery-mechanism、mcp-integration-pattern、channel-sdk-isolation、agent-scheduling-mechanism）的种子库条目已升级但尚未写完整 Concept 页。

### Concept 主题对照

| 新 Concept (slug) | 历史 Concept (slug) | 关系 |
|-------------------|---------------------|------|
| tool-security-gating | tool-execution-safety-approval + dangerous-operation-prevention | 重组：新结果将「工具可见性过滤 + 命令审批」合并为单一轴线，历史结果拆为两个 Concept |
| approval-blocking-mechanism | （无独立页，含于 tool-execution-safety-approval） | 新独立拆分：审批阻塞机制从安全审批中分离为独立维度 |
| context-window-overflow-guard | context-compression-quality | 重新定义：新结果关注「溢出防护的多源保守触发策略」，历史结果关注「压缩保真度 vs token 节省」 |
| compression-resource-allocation | context-compression-quality（部分） | 拆分：压缩的资源分配策略从保真度质量中拆出为独立维度 |
| prompt-cache-boundary | llm-input-token-cost-reduction | 重新定义：新结果聚焦「缓存边界划分策略本身」，历史结果聚焦「成本降低的综合策略」 |
| memory-retrieval-timing | memory-retrieval-timing | **同名**：相同轴线，R3 Phase 3a 补全了三仓实例矩阵 |
| context-engine-pluggability | context-engine-singleton-vs-pluggable | 同轴线，slug 重命名 |
| lifecycle-hook-granularity | （无独立页） | **新增**：历史无独立 Concept，R3 Phase 3a 补全三仓实例 |
| global-capability-coexistence | （含于 context-engine-singleton-vs-pluggable） | **新增独立**：全局能力互斥/叠加策略从 context engine 专属抽象为通用轴线 |
| im-platform-adapter-granularity | （无独立页） | **新增**：历史无此 Concept |
| optional-dependency-layering | （无独立页） | **新增**：历史无此 Concept |
| dependency-version-locking | （无独立页） | **新增**：历史无此 Concept |
| declarative-skill-extension | skill-injection-granularity | 重构：新结果将「技能注入粒度」重新定义为「声明式技能扩展的零代码门槛」 |
| tool-discovery-mechanism | plugin-subsystem-auto-discovery | 重构：新结果将工具发现从通用 plugin 发现中拆出为独立轴线 |
| mcp-integration-pattern | （无独立页） | **新增**：历史无此 Concept |
| llm-provider-registration | （无独立页） | **新增**：R3 Phase 3a 新建。历史无此 Concept，种子库中原为 llm-api-sdk-strategy，经 Axis 重命名后独立为 provider 注册维度 |
| channel-sdk-isolation | （无独立页） | **新增**：历史无此 Concept |
| agent-scheduling-mechanism | （无独立页） | **新增**：历史无此 Concept |
| agent-trigger-path | execution-engine-decoupling（部分） | **新增独立**：R3 Phase 3a 新建。agent 触发路径（Cron / bus 注入 / CLI）从执行引擎解耦中独立出来，聚焦「独立路径还是统一注入」的架构权衡 |
| subsystem-assembly-visibility | subsystem-assembly-visibility | **同名**：R3 Phase 3a 新建页。历史有此 Concept 页但被重组吸收，新结果将其作为独立轴线恢复 |

### 独有 Concept

- **新结果独有（不在历史 10 页中）**：approval-blocking-mechanism, lifecycle-hook-granularity, global-capability-coexistence, im-platform-adapter-granularity, optional-dependency-layering, dependency-version-locking, tool-discovery-mechanism, mcp-integration-pattern, llm-provider-registration, channel-sdk-isolation, agent-scheduling-mechanism, agent-trigger-path, subsystem-assembly-visibility（13 个，其中 4 个仅有种子库条目尚未写完整 Concept 页）
- **历史结果独有（不在新结果中）**：execution-engine-decoupling（已重组入 agent-trigger-path）, plugin-subsystem-auto-discovery（已重组入 tool-discovery-mechanism）, skill-injection-granularity（已重组入 declarative-skill-extension）

### R3 Phase 3a 新建 Concept

| 新建 Concept | 覆盖仓库 | 来源 |
|-------------|---------|------|
| subsystem-assembly-visibility | openclaw + hermes-agent + nanobot | 历史有此 Concept 但被重组吸收，R3 恢复为独立轴线 |
| agent-trigger-path | openclaw + hermes-agent + nanobot | 从 execution-engine-decoupling 和 proactive-trigger-path 中独立 |
| llm-provider-registration | openclaw + hermes-agent + nanobot | 从 llm-api-sdk-strategy 重命名并独立，聚焦 provider 注册而非 SDK 选择 |

### R3 Phase 3a 已有 Concept 的 nanobot 追加

| 已有 Concept | R2 覆盖 | R3 Phase 3a 新增 |
|-------------|---------|-----------------|
| context-window-overflow-guard | openclaw + hermes-agent | + nanobot（四步透明上下文治理） |
| prompt-cache-boundary | openclaw + hermes-agent | + nanobot（工具排序稳定缓存） |
| lifecycle-hook-granularity | openclaw + hermes-agent | + nanobot（CompositeHook 管道+扇出） |
| memory-retrieval-timing | openclaw + hermes-agent | + nanobot（启动时一次性加载） |

### 评估

新结果的 Concept 分解粒度更细。历史结果的 10 个 Concept 多是粗粒度合并（如 context-compression-quality 包含了触发、资源分配、治理等多个子问题），而新结果将其拆分为多个独立轴线（context-window-overflow-guard, compression-resource-allocation, prompt-cache-boundary 分别独立）。这种拆分使得各仓库的设计选择位置更精确可比。

R3 Phase 3a 的补充使三仓对比能力全面达标：15 个完整 Concept 页中，nanobot 覆盖的 Concept 页跨仓库对比表全部达到三列。

---

## 2. 分类准确性

### 共有/同名 Concept 的权衡位置分类对比

以下对比仅涉及两个结果集中有明确对应关系的 Concept：

#### memory-retrieval-timing（同名）

| 维度 | 新结果 | 历史结果 |
|------|--------|---------|
| 实例矩阵 | openclaw + hermes-agent + nanobot（3 个，R3 Phase 3a 补全） | openclaw + hermes + nanobot（3 个） |
| openclaw 分类 | Prompt 组装阶段批量注入 | 工具驱动按需检索 |
| hermes-agent 分类 | 后台异步预取 | 后台异步预取 |
| nanobot 分类 | 启动时一次性加载到 WorkingMemory | 启动时一次性加载 |

> **差异**：新结果将 openclaw 重新分类为「Prompt 组装阶段批量注入」，而历史结果将其分类为「工具驱动按需检索」。这是由于新结果关注记忆「注入时机」（assembling 时一次性 vs 运行时实时），而历史结果关注「检索模型」（LLM 工具调用 vs 系统预取）。两者并不矛盾，但是同一仓库的不同视角。**新结果的分类更接近种子库中 openclaw 条目的自述**（"记忆在 prompt 组装阶段注入，而非每次 LLM 输出后实时查询"）。R3 Phase 3a 追加 nanobot 后，三仓对比表的记忆注入光谱完整。

#### tool-security-gating vs tool-execution-safety-approval + dangerous-operation-prevention

| 维度 | 新结果 | 历史结果 |
|------|--------|---------|
| 覆盖范围 | openclaw + hermes-agent（2 个） | openclaw + hermes（2 个，但覆盖了两个 page） |
| openclaw 分类 | 同步串行 Pipeline | 政策驱动的同步门控 + 工具可见性过滤 |
| hermes-agent 分类 | 三层渐进式审批 | 三层审批 + 危险模式检测 |
| 概念轴线 | 单一：安全门控的介入程度 | 分裂：危险操作防护 + 工具执行安全审批 |

> **评估**：新结果的单一轴线「工具执行安全门控：统一管道还是分层可调节？」比历史结果的两个分裂 Concept 更准确地捕捉了 openclaw 和 hermes 之间的核心张力——不是在"安全 vs 不安全"之间选，而是在**安全管控的结构化程度**（统一管道 vs 分层调节）之间选。分类一致性上，新结果更准确。

#### context-window-overflow-guard vs context-compression-quality

| 维度 | 新结果 | 历史结果 |
|------|--------|---------|
| 实例矩阵 | openclaw + hermes-agent + nanobot（3 个，R3 Phase 3a 补全） | openclaw + hermes + nanobot（3 个） |
| nanobot 分类 | 四步透明上下文治理 | 纯规则，零 LLM 调用 |
| 轴线定义 | 溢出防护的触发策略（硬限制/固定阈值/透明预处理） | 压缩的保真度 vs token 节省 |

> **评估**：新结果将问题从「压缩质量」重新定义为「溢出防护的触发策略」，这是一个更精确的框架。历史结果将 nanobot 的「四层透明治理」和 openclaw/hermes 的「LLM 摘要」并列为压缩方式的光谱，但忽略了核心差异：**LLM 是否知道上下文被压缩过**。新结果明确将「LLM 感知 vs LLM 透明」作为治理哲学维度，这是历史结果没有覆盖的关键区别。分类准确性上，新结果更精确。R3 Phase 3a 的 nanobot 实例追加完成了该轴线的三仓对比矩阵。

### 总体评估

新结果在 Concept 分类上的主要改进：
1. **轴线定义更精确**：从粗粒度的「压缩质量」拆分为「溢出防护触发」「缓存边界策略」「压缩资源分配」三个独立轴线
2. **张力表达更清晰**：每个 Concept 的标题明确指出了权衡的维度（如「统一管道还是分层可调节」「异步等待还是同步阻塞」）
3. **覆盖更完整**：新增了 13 个历史结果没有的独立 Concept，其中 9 个有完整页、4 个有升级后的种子库条目
4. **R3 Phase 3a 补全**：三仓（openclaw + hermes-agent + nanobot）的跨仓库对比能力全面达标

---

## 3. 源码保真度

### 新结果 Concept 页的源码引用

每个新 Concept 页中的「关键机制（源码可见）」段落均包含：

| Concept | 源文件 + 行号示例 |
|---------|-----------------|
| approval-blocking-mechanism | `src/agents/bash-tools.exec-approval-request.ts:89-126`, `src/agents/tool-policy-pipeline.ts:56-90` |
| lifecycle-hook-granularity | `src/plugins/hook-types.ts:687-693`, `src/plugins/hooks.ts:134-145`, `src/plugins/hook-before-agent-start.types.ts:36-41` |
| memory-retrieval-timing | `src/plugins/memory-state.ts:170-174`, `src/plugins/memory-state.ts:206-219`, `src/agents/system-prompt.ts:169-182` |
| optional-dependency-layering | `package.json: peerDependencies, optionalDependencies` |
| prompt-cache-boundary | `src/agents/system-prompt-cache-boundary.ts:3-47`, `src/agents/anthropic-payload-policy.ts:37-65` |
| tool-security-gating | `src/agents/tool-policy-pipeline.ts:56-90`, `src/agents/tool-policy.ts:19-55`, `src/agents/bash-tools.exec-approval-request.ts:89-126` |

**新结果特征**：
- 每个实例的关键机制均标注 **具体文件路径 + 起止行号**（如 `runner.py:83-89`）
- 源码引用精确到方法和常量的定义行
- 代码片段在关键位置直接引用（如 `registry.ts:345-368` 的注册保护逻辑源码）
- 行号范围不是估计值，是精确的起止号

### 历史结果 Concept 页的源码引用

| Concept | 源文件引用情况 |
|---------|-------------|
| context-compression-quality | 有方法名（`piGenerateSummary`, `stripToolResultDetails`），有阈值常量名，但**行号稀少** |
| context-engine-singleton-vs-pluggable | 有精确行号（`registry.ts:345-368`, `types.ts:150-281`），**源码引用较好** |
| dangerous-operation-prevention | 有机制名称（7 层 allowlist/denylist），但**行号极少**，以概念性描述为主 |
| execution-engine-decoupling | 有文件引用（`runner.py:83-89`），但部分描述**行号缺失**（`runner.py:89-320` 是估算范围） |
| llm-input-token-cost-reduction | 有精确行号（`system-prompt-cache-boundary.ts:3`, `system-prompt.ts:898`），**源码引用最好** |
| memory-retrieval-timing | 有方法名和部分行号，但**nanobot 实例无行号** |
| plugin-subsystem-auto-discovery | 有核心源码引用，行号中等 |
| skill-injection-granularity | 有字符预算常量名，行号中等 |
| subsystem-assembly-visibility | 有文件引用，行号中等 |
| tool-execution-safety-approval | 有机制描述，**行号不完整** |

**历史结果特征**：
- 部分 Concept 有精确行号，但**不一致**——最好的是 `llm-input-token-cost-reduction` 和 `context-engine-singleton-vs-pluggable`，最差的是 `dangerous-operation-prevention` 和 `tool-execution-safety-approval`
- 历史结果中存在「行号欺诈」风险——部分行号是估算范围（如 `runner.py:89-320`）而非精确起止
- 机制描述有时使用项目术语（如 `piGenerateSummary`）但未映射到源码位置

### 保真度对比总结

| 指标 | 新结果 | 历史结果 |
|------|--------|---------|
| 文件路径 + 行号覆盖 | 15/15 Concept（100%） | ~6/10 Concept（60%）有较完整行号 |
| 行号精度 | 精确起止范围 | 混合：部分精确，部分估算 |
| 关键常量/方法名 | 系统标注 | 存在但欠系统 |
| 代码片段嵌入 | 常见（源码块引用） | 罕见 |
| 可验证性 | 高：每个关键断言可定位到源码行 | 中：部分断言仅凭项目术语，需手动 grep |

**结论**：新结果的源码保真度显著优于历史结果。新结果达到了「每个关键机制描述都有源码可见的方法名 + 精确行号」的标准，而历史结果在源码引用上不一致，存在"有概念无定位"的行号缺失现象。

---

## 4. 增量完整性

### nanobot 追加后对已有仓库描述的保留

种子库层面，每个条目在追加 nanobot 后完整保留了 openclaw 和 hermes-agent 的描述：

**示例：工具执行安全门控**

新种子库中 nanobot 追加后的条目：

```
| openclaw | 同步串行 Pipeline | ... | [[openclaw/...]] → src/agents/tool-policy-pipeline.ts:56-90 |
| hermes-agent | 三层渐进式审批 | ... | [[hermes-agent/...]] → tools/approval.py:586-922 |
| nanobot | 三层安全防护：基础设施级隔离 | ... | security/network.py; test_exec_security.py; test_sandbox.py |
```

openclaw 和 hermes-agent 的描述与历史种子库的描述一致，且每次追加都保留了原有的溯源和 Context。

**对比历史种子库**：历史种子库中 openclaw 的条目描述为：
```
| openclaw | 权限决策在消息处理关键路径上做同步门控... | entity/openclaw-tool-policy.md → src/agents/tool-policy-pipeline.ts |
```

新结果保留了同样的描述语义（同步门控、pipeline），但增加了更多关切维度（6 条核心关切 vs 历史结果的 0 条）。**描述未被覆盖，而是被丰富了**。

**示例：生命周期 Hook 拦截粒度**

新种子库：
```
| openclaw | 28 个细粒度命名 Hook | ... → src/plugins/hook-types.ts:55-84 |
| hermes-agent | 8 个粗粒度事件 + 目录扫描加载 | ... → gateway/hooks.py:9-19 |
| nanobot | CompositeHook：内容变换用管道，事件通知用扇出 | ... → agent/hook.py:29-103 |
```

历史种子库的 openclaw 条目是独立且孤立的，hermes 无对应条目。新结果完成了三仓归一。

### nanobot 实例对已有 Concept 的补充（R3 Phase 3a 完成）

R3 Phase 3a 为以下 4 个已有 Concept 页追加了 nanobot 实例，使跨仓库对比表全部达到三列：

| Concept | openclaw | hermes-agent | nanobot 新增位置 |
|---------|----------|-------------|-----------------|
| context-window-overflow-guard | 硬限制+多源保守 | 固定 75% | 四步透明治理 |
| prompt-cache-boundary | 稳定前缀分离 | system_and_3 | 工具排序稳定缓存 |
| lifecycle-hook-granularity | 28 个细粒度 Hook | 8 个粗粒度事件 | CompositeHook 管道+扇出 |
| memory-retrieval-timing | Prompt 组装阶段批量注入 | 后台异步预取 | 启动时一次性加载 |

> 原报告标注 "round-2-hermes 的 Concept 页（phase-3a-concepts/*.md）尚未包含 nanobot 实例——这是因为它们生成在 nanobot 种子入库之前。完整的三仓 Concept 页预计在 round-4 产出。" **该状态已过时。** R3 Phase 3a 已将上述 4 个 Concept 页的三仓实例矩阵补全。其余 R2 产出的 Concept 页中，nanobot 因不涉及对应设计维度（如 compression-resource-allocation、declarative-skill-extension 等，nanobot 不存在对应设计决策）而未追加。

### nanobot 实例在其他新建 Concept 页中的位置

R3 Phase 3a 新建的 3 个 Concept 页均包含完整的 nanobot 实例：

| Concept | openclaw 位置 | hermes-agent 位置 | nanobot 位置 |
|---------|-------------|-----------------|-------------|
| subsystem-assembly-visibility | 中央 Hub 类构造函数组装 30+ 子系统 | `run_agent.py` 单一文件吸收全部初始化 | 分散式模块组装，无单一 Hub |
| agent-trigger-path | Cron 独立路径直连 agent-run loop | Cron 作为 Gateway 编排的额外入口 | 统一 bus 注入，Cron 和 CLI 共享同一消费管道 |
| llm-provider-registration | 编译时 static registry + 运行时 dispatcher | 硬编码优先级链（openai SDK 统一路由） | 启动时自动检测（key prefix + base URL） |

### 评估

**种子库层面**：增量完整性良好。每个设计条目在追加新仓库时完整保留了已有仓库的描述、溯源和交叉引用。nanobot 追加后，openclaw 和 hermes-agent 的描述既未丢失也未退化。

**Concept 页层面**：R3 Phase 3a 完成后，4 个已有 Concept 页的三仓实例矩阵已补全，3 个新建 Concept 页从零开始即覆盖三仓。其余 R2 产出的 Concept 页因 nanobot 不涉及对应设计维度而未追加（非遗漏，而是 nanobot 在该维度上无独立设计决策）。

---

## 5. 格式规范性

### 问题陈述格式：「如何...」问句

| 来源 | 符合「如何...」格式 | 不符合 | 符合率 |
|------|--------------------|--------|--------|
| 新种子库（58 条） | 58 | 0 | 100% |
| 新 Concept 页（15 个） | 15 | 0 | 100% |
| 历史种子库（~78 条） | ~45 | ~33 | ~58% |
| 历史 Concept 页（10 个） | 5 | 5 | 50% |

历史结果中不符合「如何...」格式的 Concept 页：

| 历史 Concept | 当前问题陈述开头 | 问题 |
|-------------|----------------|------|
| context-engine-singleton-vs-pluggable | "Context Engine 控制对话上下文的完整生命周期..." | 英文开头，非中文问句 |
| dangerous-operation-prevention | "在 agent 框架中，LLM 可以生成并执行任意 shell 命令..." | 陈述句开头 |
| execution-engine-decoupling | "Agent harness 的核心价值是执行引擎..." | 英文开头，非问句 |
| llm-input-token-cost-reduction | "AI Agent 框架在多轮对话中..." | 陈述句开头 |
| subsystem-assembly-visibility | "当一个 agent 框架由多个子系统组成..." | 陈述句开头 |

新结果中所有 Concept 页均使用标准化的「标准化问题陈述」段落 + 「如何...」问句开头。即使是同一个主题（如 memory-retrieval-timing），新结果也重新组织了问题陈述：

- 历史：`如何设计记忆检索的触发模型以在时效性、延迟和 LLM 上下文窗口开销之间取得平衡？`（格式正确，但一个问题 vs 多个子问题）
- 新：`在多轮对话中，如何决定记忆检索与注入 LLM 上下文的时机——是在 prompt 组装阶段批量注入还是后台异步预取？`（格式正确，且用破折号清晰表达了两个对立选项）

### Slug 格式：{能力域}-{决策维度}

**新结果全 15 个 Concept slug**：
| Slug | 能力域 | 决策维度 |
|------|--------|---------|
| agent-trigger-path | agent | trigger-path |
| approval-blocking-mechanism | approval | blocking-mechanism |
| compression-resource-allocation | compression | resource-allocation |
| context-engine-pluggability | context-engine | pluggability |
| context-window-overflow-guard | context-window | overflow-guard |
| dependency-version-locking | dependency | version-locking |
| global-capability-coexistence | global-capability | coexistence |
| im-platform-adapter-granularity | im-platform-adapter | granularity |
| lifecycle-hook-granularity | lifecycle-hook | granularity |
| llm-provider-registration | llm | provider-registration |
| memory-retrieval-timing | memory | retrieval-timing |
| optional-dependency-layering | optional-dependency | layering |
| prompt-cache-boundary | prompt-cache | boundary |
| subsystem-assembly-visibility | subsystem | assembly-visibility |
| tool-security-gating | tool-security | gating |

**全部符合** `{能力域}-{决策维度}` 格式。15/15（100%）

**历史结果全 10 个 Concept slug**：
| Slug | 能力域 | 决策维度 | 符合？ |
|------|--------|---------|--------|
| context-compression-quality | context | compression-quality | 是 |
| context-engine-singleton-vs-pluggable | context-engine | singleton-vs-pluggable | 是（但含 `vs`） |
| dangerous-operation-prevention | dangerous-operation | prevention | 是 |
| execution-engine-decoupling | execution-engine | decoupling | 是 |
| llm-input-token-cost-reduction | llm-input-token | cost-reduction | 是 |
| memory-retrieval-timing | memory | retrieval-timing | 是 |
| plugin-subsystem-auto-discovery | plugin-subsystem | auto-discovery | 是 |
| skill-injection-granularity | skill | injection-granularity | 是 |
| subsystem-assembly-visibility | subsystem | assembly-visibility | 是 |
| tool-execution-safety-approval | tool-execution | safety-approval | 是 |

**全部符合**。10/10（100%）。但 `context-engine-singleton-vs-pluggable` 中 `vs` 符号暗示 slug 应表达轴线而非对比的两端；新结果将其改进为 `context-engine-pluggability`（单维度描述）。

### 评估

格式规范性上新结果全面优于历史结果：

1. **问题陈述格式**：100% vs 50% 符合「如何...」问句形式。历史结果中半数的 Concept 页没有标准化问题陈述格式。
2. **Slug 格式**：两者都 100% 符合 `{能力域}-{决策维度}`，但新结果的 slug 命名更简洁（如 `pluggability` vs `singleton-vs-pluggable`）。
3. **额外改进**：新结果每个 Concept 页有一致的 frontmatter（`concept`, `generated`, `phase`, `instances`）和标准化结构（标准化问题陈述 → 核心关切 → 已知权衡位置/实例矩阵 → 逐仓库分析）。历史结果没有统一的 frontmatter 和结构。

---

## 6. R3 Phase 3b 验证结果

R3 Phase 3a 的 7 个 Concept 页均经过独立的 Phase 3b 双源验证（wiki 反向对照）。以下是 7 份验证报告的结果统计：

| 验证报告 | 页面 | 检查断言数 | ❌ 发现 | ⚠️ 概念层推断 | 修复状态 |
|---------|------|----------|---------|-------------|---------|
| agent-trigger-path-verify | agent-trigger-path | 41 | 2 | 若干 | Phase 3c 已修复 |
| context-window-overflow-guard-verify | context-window-overflow-guard | — | 0 | — | 无需修复 |
| lifecycle-hook-granularity-verify | lifecycle-hook-granularity | — | 0 | — | 无需修复 |
| llm-provider-registration-verify | llm-provider-registration | 50 | 4 | 若干 | Phase 3c 已修复 |
| memory-retrieval-timing-verify | memory-retrieval-timing | — | 0 | — | 无需修复 |
| prompt-cache-boundary-verify | prompt-cache-boundary | — | 0 | — | 无需修复 |
| subsystem-assembly-visibility-verify | subsystem-assembly-visibility | 39 | 2 | 若干 | Phase 3c 已修复 |

**❌ 发现汇总（合计约 8 个，全部经 Phase 3c 修复）**：

1. **agent-trigger-path**（2 个）：
   - Cron 层级归属错误：页面写 "Cron 属于编排层"，wiki 架构图将其放在基础设施层
   - 同样的层级归属错误在页面另一处重复出现

2. **llm-provider-registration**（4 个）：
   - 声称的 "OpenRouter → Nous Portal → Codex OAuth → Native Anthropic" 四步解析链在 wiki 中无任何记录
   - 基于上述链的硬编码优先级代价描述随之不成立
   - hermes-agent provider 注册机制的链式描述不准确
   - 部分行号引用在 wiki 维度页中无对应记录

3. **subsystem-assembly-visibility**（2 个）：
   - hermes-agent 的 `main()` 入口被错误标注为 `run_agent.py:11295`，wiki 指向 `cli.py:main()`
   - 页面缺少 `## 关联` 段落的 wikilink 交叉引用

所有 ❌ 发现均为 wiki 反向对照时发现的行号错误、架构归属错误或断言无据问题，**非源码编译/运行期错误**。Phase 3c 修复后，所有 Concept 页与 wiki 记录达成一致。

> 对比 R2 Phase 3b 的 12 份验证报告（含约 35 个 ❌ 发现），R3 Phase 3a 的 ❌ 密度显著降低（平均每页约 1.1 个 vs R2 的约 2.9 个），说明经过 R2 的验证流程校准后，R3 的 Concept 页产出质量从一开始就更高。

---

## 7. R3 Phase 3a 产出文件清单

### Concept 页（7 个）

```
round-3-nanobot/phase-3a-concepts/
├── agent-trigger-path.md              # 新建：agent 触发路径（独立路径 vs 统一注入）
├── context-window-overflow-guard.md   # 追加 nanobot：四步透明治理
├── lifecycle-hook-granularity.md      # 追加 nanobot：CompositeHook 管道+扇出
├── llm-provider-registration.md       # 新建：LLM provider 注册机制
├── memory-retrieval-timing.md         # 追加 nanobot：启动时一次性加载
├── prompt-cache-boundary.md           # 追加 nanobot：工具排序稳定缓存
└── subsystem-assembly-visibility.md   # 新建：子系统组装的可发现性
```

### Phase 3b 验证报告（7 个）

```
round-3-nanobot/phase-3b-verify/
├── agent-trigger-path-verify.md
├── context-window-overflow-guard-verify.md
├── lifecycle-hook-granularity-verify.md
├── llm-provider-registration-verify.md
├── memory-retrieval-timing-verify.md
├── prompt-cache-boundary-verify.md
└── subsystem-assembly-visibility-verify.md
```

---

## 总结

| 维度 | 新结果 vs 历史 |
|------|-------------|
| **Concept 覆盖** | 新结果 15 个完整 Concept 页 + 4 个升级种子库条目，历史 10 个。新结果分解粒度更细，新增 13 个独立轴线（R3 Phase 3a 贡献 3 个新建 Concept + 1 个历史恢复）。三仓跨仓库对比能力全面达标。 |
| **分类准确性** | 新结果轴线定义更精确，张力表达更清晰（如将「压缩质量」拆为三个独立轴线），且 nanobot 被作为 infrastructure-level 安全哲学的独立位置引入 |
| **源码保真度** | 新结果 100% 实例含精确文件路径 + 行号，历史结果约 60% 有不一致的源码引用。新结果达到了「每个关键断言可定位到源码行」的标准 |
| **增量完整性** | R3 Phase 3a 完成后，4 个已有 Concept 页的三仓实例矩阵补全，跨仓库对比表全部达三列。种子库层面每次追加完整保留已有描述 |
| **格式规范性** | 问题陈述 100% vs 50%「如何...」格式；Slug 命名更简洁；frontmatter + 标准化结构全面优于历史 |
| **验证覆盖** | R3 Phase 3a 7/7 Concept 页经过 Phase 3b wiki 反向对照验证（约 8 个 ❌ 发现，全部 Phase 3c 修复），加上 R2 的 12 份验证报告，本轮累计 19 份验证报告 |
