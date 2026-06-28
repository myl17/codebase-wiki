# Deepagents Ingest 质量审计报告

> 日期：2026-06-28
> 审计人：第三方独立审计（Claude 以无利益关联审查者身份执行）
> 被审计对象：`/ingest --auto --repo deepagents` 的完整管线产出
> 审计方法：读取 transcript 行为 + 逐页审查 wiki 产出 + 交叉验证源码（subagents.py、graph.py、memory.py、protocol.py 等关键文件）

---

## 一、审计总评

| 维度 | 评级 | 说明 |
|------|------|------|
| Entity 提取质量 | **优秀** | 12 个 entity 边界清晰、职责明确，无遗漏重要模块 |
| 问题空间映射质量 | **良好** | 11 条目表述准确，2 个正确跳过 |
| Step 3 匹配正确性 | **优秀** | 9A+1B+1D 全部合理，无假阳性、无严重遗漏 |
| Concept 页修改质量 | **优秀** | 格式一致、数据准确、对比公正、演化记录完整 |
| 源码引用准确性 | **良好** | 行号引用准确，路径格式有轻微不统一 |
| 知识保鲜合规 | **通过** | Evolution records 完整、对比表更新、log.md 追加 |

**总评：这是一次高质量的 ingest。Product pipeline 在跨仓库知识累积上表现出了预期的成熟度。**

---

## 二、Entity 提取审计

### 2.1 提取清单

共 12 个 entity：

| # | Entity | Source | 独立性判断 |
|---|--------|--------|-----------|
| 1 | agent-graph-assembly | graph.py | ✅ 独立——协调组装，与任何中间件解耦 |
| 2 | backend-protocol | backends/protocol.py | ✅ 独立——接口定义，零实现依赖 |
| 3 | composite-backend | backends/composite.py | ✅ 独立——路径路由逻辑完整 |
| 4 | state-backend | backends/state.py | ✅ 独立——但设计决策被 backend-protocol 覆盖（已在 candidates 中正确处理） |
| 5 | filesystem-middleware | middleware/filesystem.py | ✅ 独立——7 工具提供 + 大结果驱逐 |
| 6 | subagent-middleware | middleware/subagents.py | ✅ 独立——完整子代理生命周期 |
| 7 | async-subagent-middleware | middleware/async_subagents.py | ✅ 独立——远程子代理独立设计空间 |
| 8 | summarization-middleware | middleware/summarization.py | ✅ 独立——LLM 摘要 + 三种触发策略 |
| 9 | memory-middleware | middleware/memory.py | ✅ 独立——AGENTS.md 规范驱动 |
| 10 | skills-middleware | middleware/skills.py | ✅ 独立——Agent Skills 规范实现 |
| 11 | tool-call-patching | middleware/patch_tool_calls.py | ⚠️ 被正确跳过（详见 2.3） |
| 12 | model-resolution | _models.py | ✅ 独立——provider 解析入口 |

### 2.2 Entity 页质量抽查

抽查了 3 个 entity 页（backend-protocol、subagent-middleware、agent-graph-assembly）：

- **Frontmatter 合规**：全部通过，type/repo/slug/problem/source_files 完整
- **源码行号准确性**：抽样验证了 `subagents.py:126`（状态键过滤）、`graph.py:108`（create_deep_agent）、`backends/protocol.py:301`（BackendProtocol）——全部精确匹配
- **交互关系描述**：wikilink 正确，上下游模块关系清晰
- **"为什么可分离"论证**：每页均有独立论证，逻辑自洽

### 2.3 跳过的 Entity

2 个 entity 被跳过不生成问题空间条目：

| Entity | 跳过理由 | 审计判断 |
|--------|---------|---------|
| tool-call-patching | 实现细节——边界情况修复，无设计方案选择空间 | ✅ 同意。`patch_tool_calls.py` 是机械扫描+替换操作，不构成独立设计决策 |
| state-backend | 设计决策已被 backend-protocol 覆盖 | ✅ 同意。StateBackend 是 BackendProtocol 的具体实现，无新增设计维度 |

---

## 三、问题空间映射审计

### 3.1 条目质量

11 个条目，每条检查了：问题陈述准确性、关切覆盖度、解法描述准确性、源码引用准确性。

**抽查结果**：

| 条目 | 问题陈述 | 关切覆盖 | 解法描述 | 源码引用 |
|------|---------|---------|---------|---------|
| 中间件组装 (→ B1) | ✅ "按固定顺序组装成完整配置的 AI Agent 图" | ✅ 顺序正确性 + 可替换性 | ✅ 固定顺序堆栈精确描述 | ✅ graph.py:108-427 |
| 文件系统操作 (→ D1) | ✅ "提供哪些工具、接口如何设计" | ✅ 粒度+安全性 | ✅ Pydantic Schema 正确 | ✅ filesystem.py:522-849 |
| 大工具输出 (→ A4) | ✅ "超出上下文窗口"精确 | ✅ 信息不丢失+预算保护 | ✅ 截断预览+文件路径引用 | ✅ filesystem.py:384-393 |
| 同步子代理 (→ A1) | ✅ "隔离的子 Agent"精确 | ✅ 上下文隔离+灵活性+状态安全 | ✅ SubAgent/CompiledSubAgent 正确 | ✅ subagents.py:298-389 |
| 异步子代理 (→ A2) | ✅ "后台执行"精确 | ✅ 非阻塞+状态一致+多协议 | ✅ 5 工具套件正确 | ✅ async_subagents.py:837-859 |
| 摘要压缩 (→ A3) | ✅ "自动压缩历史消息"精确 | ✅ 触发灵活性+保真度+干扰最小 | ✅ 三种触发策略正确 | ✅ summarization.py:885-987 |
| 记忆加载 (→ A5) | ✅ "跨会话记住"精确 | ✅ 自主更新+分层+存储无关 | ✅ AGENTS.md 正确 | ✅ memory.py:159-354 |
| 技能加载 (→ A6) | ✅ "按需加载"精确 | ✅ 渐进披露+分层+规范兼容 | ✅ Agent Skills 规范正确 | ✅ skills.py:602-831 |
| 后端协议 (→ A7) | ✅ "可替换的后端接口"精确 | ✅ 完备性+错误标准化+兼容 | ✅ BackendProtocol 正确 | ✅ protocol.py:301-811 |
| 多后端路由 (→ A8) | ✅ "路径前缀路由"精确 | ✅ 透明路由+跨后端搜索+一致性 | ✅ CompositeBackend 正确 | ✅ composite.py:119-738 |
| 模型解析 (→ A9) | ✅ "统一解析"精确 | ✅ Provider 差异+便利性+兼容 | ✅ resolve_model 正确 | ✅ _models.py:72-96 |

**无重大疏漏。**

### 3.2 一个值得关注的轻微问题

条目"大工具输出超出上下文窗口"被匹配到 `context-compression-strategy`（A 类）。这个分类**可以成立**——工具结果驱逐确实是压缩的一种形式，但与"对话级摘要压缩"在概念上属于不同层次。当前 context-compression-strategy 页将其作为 deepagents 的第二个压缩维度是正确的处理方式（区分了"对话压缩"和"结果驱逐"两个子维度），但将来如果多个仓库都实现了独立的工具结果驱逐机制，这块可能需要独立的子维度观察。

---

## 四、Step 3 匹配审计

### 4.1 A 类匹配（9 个）

逐条审查：

| # | 条目 → Concept | 合理性 | 审计意见 |
|---|---------------|--------|---------|
| A1 | 同步子代理 → subagent-orchestration | ✅ | 三个框架已有子代理委派机制，deepagents 的声明式/编译式双形态是独特的实现变体 |
| A2 | 异步子代理 → subagent-orchestration | ✅ | 远程异步子代理是同步子代理的自然延伸，共享核心问题空间 |
| A3 | 摘要压缩 → context-compression-strategy | ✅ | LLM 摘要 + 三种触发策略 + 链式摘要事件，是压缩策略光谱的重要补充 |
| A4 | 工具结果驱逐 → context-compression-strategy | ✅ | 虽粒度不同（结果级 vs 对话级），但在同一概念页内正确区分为两层 |
| A5 | 记忆加载 → memory-management-architecture | ✅ | AGENTS.md 规范驱动是第四种记忆管理方案，填补了"agent 自主 edit_file 更新"的模式 |
| A6 | 技能加载 → skills-extension-mechanism | ✅ | Agent Skills 规范遵循是重要的行业标准对齐 |
| A7 | 后端协议 → execution-isolation | ⚠️ | 详见 4.4 |
| A8 | 多后端路由 → execution-isolation | ⚠️ | 详见 4.4 |
| A9 | 模型解析 → provider-abstraction-pattern | ✅ | resolve_model 是 provider 抽象层的最简实现变体 |

### 4.2 B 类匹配（1 个）

**middleware-composition-pattern** —— 四条准则验证：

| 准则 | 判断 | 审计意见 |
|------|------|---------|
| ① 多方案 | ✅ nanobot context-builder + hermes prompt-builder + openclaw hook pipeline + deepagents middleware stack | 四个仓库确实有四种明显不同的组装方式 |
| ② 独立设计空间 | ✅ 中间件顺序决定"工具何时可用""缓存是否有效""审批何时拦截"，独立于 system-prompt-assembly 和 agent-loop-orchestration | 正确 |
| ③ 持续 Trade-off | ✅ 固定顺序（可预测性）vs 可配置顺序（灵活性），无银弹 | 正确的 trade-off 识别 |
| ④ 可持续扩展 | ✅ 中间件/插件/钩子组合方式仍然是活跃设计空间 | 正确 |

**审计意见：`middleware-composition-pattern` 符合 Concept 建立四条准则。这是一个有价值的跨仓库发现。**

### 4.3 D 类信号（1 个）

**文件系统工具接口设计 → tool-lifecycle-management 子维度**：

- 判断正确：deepagents 的工具设计关注的是"每个工具长什么样"（Pydantic Schema + 7 工具职责划分），而 tool-lifecycle-management 关注的是"工具如何注册/发现/过滤"
- 信号文件 `evolve-signals/2026-06-28-deepagents.md` 内容准确，建议合理

### 4.4 潜在问题：A7/A8 的归属

后端协议（BackendProtocol）和多后端路由（CompositeBackend）被匹配到 `execution-isolation`。这个归属有一个**语义张力**值得注意：

- `execution-isolation` 的核心问题是"代码在哪里执行、执行环境如何隔离"（Docker/SSH/本地沙箱）
- BackendProtocol 的核心问题是"文件操作和命令执行的接口抽象层"
- CompositeBackend 的核心问题是"按路径前缀的多后端存储路由"

BackendProtocol 既覆盖了文件操作（ls/read/write/edit）又覆盖了命令执行（execute），而 execution-isolation 主要关注后者。将 BackendProtocol 归类到 execution-isolation 意味着：
- 文件操作的后端抽象（StateBackend、StoreBackend）也被视为"执行隔离"的一部分
- 概念边界从"执行环境隔离"扩展为更广义的"后端抽象 + 执行隔离"

**这不构成错误**——Concept 页的 problem 字段本身已包含了"透明路由"，且 abstract backend protocol 是实现可插拔隔离的自然前提。但这是一个概念演变信号：execution-isolation 的概念边界正在从"安全沙箱"扩展到"存储/执行后端抽象"。如果未来 ingest 更多仓库后这个张力增大，可能需要 split。

### 4.5 遗漏检查

独立审查了是否应该匹配但未匹配的问题空间：

| 候选遗漏点 | 审计判断 |
|-----------|---------|
| deepagents 的 LangGraph 依赖（不用自己写循环） | 这不是 deepagents 自己的设计决策，是选择了 LangGraph 作为底层引擎。类似 hermes-agent 选择自研 AIAgent、openclaw 选择自研 runEmbeddedPiAgent——已在 agent-loop-orchestration 中覆盖 |
| deepagents 的 TodoListMiddleware（任务管理） | TodoListMiddleware 是外部库提供的，不是 deepagents 自身的设计。entity 提取正确跳过了它 |
| AnthropicPromptCachingMiddleware | 同上，外部库 |

**无遗漏。**

---

## 五、Concept 页修改审计

### 5.1 修改的 Concept 页（6 个）

逐页审查了 deepagents 新增段落的质量：

| Concept 页 | deepagents 段 | 格式一致性 | 数据准确性 | 对比公正性 | 演化记录 |
|-----------|-------------|-----------|-----------|-----------|---------|
| subagent-orchestration | ✅ 完整 | ✅ | ✅ 源码验证 | ✅ "无显式预算控制"诚实 | ✅ |
| execution-isolation | ✅ 完整 | ✅ | ✅ | ✅ "无 Docker/SSH 内置实现"诚实 | ✅ |
| context-compression-strategy | ✅ 双层架构 | ✅ | ✅ 三种触发验证 | ✅ "无反震荡保护"诚实 | ✅ |
| memory-management-architecture | ✅ AGENTS.md 规范 | ✅ | ✅ memory.py 验证 | ✅ "无 consolidation"诚实 | ✅ |
| skills-extension-mechanism | ✅ Agent Skills 规范 | ✅ | ✅ skills.py 验证 | ✅ "纯本地 backend"诚实 | ✅ |
| provider-abstraction-pattern | ✅ resolve_model | ✅ | ✅ _models.py 验证 | ✅ "功能最弱"诚实 | ✅ |

**格式一致性检查**：
- 全部使用 `### deepagents` 节标题（与已有 nanobot/hermes-agent/openclaw 的 `### nanobot` 等格式一致）
- 全部包含 `来源：[[repos/deepagents/entities/xxx]]` wikilink
- 全部包含 **解法** 一行摘要 + **实现** 详细段落 + **权衡** 客观评价
- 行号引用格式 `^[deepagents/xxx:line-line]` 与已有风格一致
- 对比表新增行格式与已有行一致

### 5.2 新建 Concept 页（1 个）

**`middleware-composition-pattern.md`**：

- Frontmatter 合规 ✅
- Problem 字段精确 ✅
- Concerns 三关切结构合理 ✅
- 四框架解法各具独立节 ✅
- 对比表覆盖三关切 ✅
- 演化记录完整 ✅
- 源码引用准确 ✅

**质量评价**：与已有的 15 个 Concept 页质量持平。nanobot 的 context-builder 归类为"一次性 pipeline 阶段组装"精准抓住了它的本质（运行时无动态注入）。hermes-agent 的"事件驱动分层 prompt 构建"正确识别了它与 middleware 堆栈的根本差异。

### 5.3 维护文件更新

- `wiki/index.md`：新增 deepagents 仓库行 + 更新 7 个 concept 的 repos 字段 ✅
- `wiki/hot.md`：16 concepts、1 pending signal、4 active repos ✅
- `wiki/log.md`：追加 ingest 日志 ✅

---

## 六、问题清单

### 6.1 轻微问题

| # | 严重度 | 描述 | 建议 |
|---|--------|------|------|
| 1 | 低 | 问题空间条目"大工具输出超出上下文窗口"（→ A4）和"对话自动摘要压缩"（→ A3）共享了同一个 entity（filesystem-middleware 和 summarization-middleware），但被映射到同一个 Concept（context-compression-strategy）。条目覆盖了两种不同粒度的压缩，Concept 页正确处理了这一点，但 candidates.md 中将其标记为两个独立的 A 类匹配（A3 和 A4），略显冗余 | 考虑在 candidates 中将 A3 和 A4 合并为一个条目（"双层压缩"），因为它们在 Step 4 Concept 写作时已经合并处理 |
| 2 | 低 | entity 页 `source_files` 使用 `deepagents/graph.py` 格式（相对于 repo 根），而 repo 实际结构是 `libs/deepagents/deepagents/graph.py`。这在当前 ingest 的 repo 路径配置下是正确的（repo 根被设为 `libs/deepagents/`），但与其他三个仓库的 source_file 路径风格不同 | 无需修改。这是 repo 路径配置的问题，不是 entity 提取的问题 |
| 3 | 低 | deepagents 的 `summarization-middleware` entity 页中提到 `SummarizationToolMiddleware`（允许 Agent 手动触发压缩），但在 concept 页的 deepagents 段中没有提到这个变体 | 可在 context-compression-strategy 页 deepagents 段补充一句"还支持 Agent 通过 compact_conversation 工具手动触发" |

### 6.2 值得关注的概念边界演变

| # | 描述 | 建议 |
|---|------|------|
| 1 | `execution-isolation` 的概念边界正在从"安全沙箱/执行隔离"扩展到"后端抽象 + 执行隔离"。BackendProtocol 的纳入使这个 Concept 同时覆盖了"文件存储后端"和"命令执行后端" | 这不是当前问题，但应在该 Concept 页的子维度观察中记录概念边界演变。如果未来 ingest 的仓库中出现了纯粹的"文件存储后端抽象"（不含执行隔离），可能需要 split |
| 2 | `context-compression-strategy` 现在包含了两层压缩：对话级摘要（SummarizationMiddleware）和结果级驱逐（FilesystemMiddleware 的 tool result eviction）。这两层在同一个 Concept 页内处理是正确的，但应注意其他仓库是否将工具结果驱逐作为独立机制设计 | 当前处理正确。如果未来至少 2 个仓库将工具结果驱逐作为独立子系统，应触发子维度观察或 split |

---

## 七、审计结论

### 量化评分

| 维度 | 得分 | 权重 | 加权 |
|------|------|------|------|
| Entity 提取完整性 | 9/10 | 20% | 1.8 |
| Entity 页质量 | 10/10 | 20% | 2.0 |
| 问题空间映射准确性 | 9/10 | 20% | 1.8 |
| Step 3 匹配正确性 | 9/10 | 25% | 2.25 |
| Concept 页修改质量 | 10/10 | 10% | 1.0 |
| 源码引用准确性 | 9/10 | 5% | 0.45 |
| **加权总分** | | | **9.30/10** |

### 定性结论

1. **Entity 提取成熟**：12 个 entity 的边界划分与 deepagents 的模块结构高度一致，skipped 的两个 entity 判断正确。与其他三个仓库的 entity 质量持平。

2. **问题空间映射准确**：11 个条目的问题陈述和关切维度准确反映了 deepagents 的设计决策。条目格式与已有 52 个条目一致。

3. **Step 3 匹配可靠**：9A+1B+1D 的匹配结果全部合理，无假阳性。`middleware-composition-pattern` 作为新 Concept 建立符合四条准则，是 ingest 中最有价值的跨仓库发现。

4. **Concept 页修改高质量**：6 个被修改的 Concept 页保持了格式一致性、数据准确性和评估公正性。对比表中对 deepagents 的弱项（"无显式预算控制""无 Docker/SSH 内置实现""无故障切换"）的描述诚实、客观。

5. **值得改进的方向**（非严重）：
   - 工具结果驱逐和对话摘要可以合并为一个"双层压缩"条目，减少 candidates 冗余
   - execution-isolation 的概念边界演变应记录为子维度观察

### 最终判定

**这是一次高质量的 ingest。Product pipeline（code-ingest skill）在当前 4 个仓库的规模下表现了预期的提取、映射、匹配和写作能力。审计发现的 3 个轻微问题和 2 个概念边界演变观察不影响 ingest 结果的可用性和准确性。**

---

## 第八章：Step 3 搜索行为还原

> 本节是 2026-06-28 基于用户追问补充的审计内容。用户问：ingest 在整合 Concept 时，具体是如何进行 agentic search 的？检索回了哪些问题空间和 Concept？

### 8.1 搜索策略：全量 frontmatter 扫描，不是关键词 grep

从 transcript 中提取的 Step 3 搜索流程如下：

**步骤 1：扫描全部 15 个 Concept 的 frontmatter**

```bash
for f in wiki/concepts/*.md; do 
  echo "=== $(basename $f) ===" 
  head -10 "$f"  # 读取每个 Concept 的 YAML frontmatter
done
```

这一步等效于"读取全部 15 个 Concept 的 problem 字段和 repos 字段"。不是关键词 grep——是批量全扫描。Transcript line 112。

**步骤 2：读取 master.md（种子状态表）**

```bash
cat seeds/master.md
```

确认已有三个仓库的条目状态（哪些已升级为 Concept、哪些是 C 类、哪些是 D 类）。Transcript line 108。

**步骤 3：选择性深读 6 个 Concept 页**

基于 frontmatter 扫描 + master.md 的结果，ingest subagent 在推理中自行判断了哪些 Concept 与 deepagents 的问题空间相关，然后深读了这 6 个页面的完整内容：

| # | 文件 | Transcript line | 被匹配的 deepagents 条目 |
|---|------|----------------|------------------------|
| 1 | `subagent-orchestration.md` | line 124 | 同步子代理 + 异步子代理 |
| 2 | `context-compression-strategy.md` | line 126 | 摘要压缩 + 工具结果驱逐 |
| 3 | `memory-management-architecture.md` | line 128 | AGENTS.md 记忆加载 |
| 4 | `skills-extension-mechanism.md` | line 131 | Agent Skills 规范技能加载 |
| 5 | `execution-isolation.md` | line 133 | BackendProtocol + CompositeBackend |
| 6 | `provider-abstraction-pattern.md` | line 135 | resolve_model 模型解析 |

**没有被深读的 9 个 Concept**：agent-loop-orchestration、channel-abstraction-pattern、autonomous-scheduling、security-architecture、session-lifecycle-management、system-prompt-assembly、configuration-management、execution-approval-pattern、tool-lifecycle-management。

### 8.2 匹配链路：frontmatter 语义路由 → 深读印证 → 分类

以"同步子代理委派"条目为例的完整匹配链：

```
1. deepagents 实体提取：subagent-middleware (问题: 如何让主Agent将任务委派给隔离的子Agent)

2. 前端扫描阶段：15 个 Concept frontmatter 全部入眼
   - agent-loop-orchestration → problem: "编排Agent主循环" → 不匹配（循环编排 ≠ 子代理委派）
   - subagent-orchestration → problem: "如何让主Agent委托后台子Agent执行复杂任务" → 语义高度匹配 ✓
   - execution-isolation → problem: "可插拔隔离环境" → 不匹配（环境隔离 ≠ 子代理管理）

3. 深读印证阶段：Read subagent-orchestration.md 全文
   - 验证核心问题段覆盖了"并行、隔离、异步三元张力"
   - 确认已有 nanobot/hermes-agent/openclaw 三个实例
   - 判断 deepagents 的 SubAgent/CompiledSubAgent 可作为第四实例追加
   - 识别独特贡献：声明式vs编译式双形态、状态键过滤

4. 分类决策：A 类 → 追加到 subagent-orchestration
```

### 8.3 Phase 5 实际搜索策略 vs Phase 1-4 实验策略

**这是本次审计最重要的方法论发现**：

| 维度 | Phase 1-4 实验 | Phase 5 ingest 实际 |
|------|---------------|-------------------|
| 搜索策略 | 关键词 grep → 只有命中文件才被读 | 全量 frontmatter 扫描 → 全部 Concept 入眼 |
| grep 次数 | 5-17 次/查询 | **0 次针对问题空间匹配的 grep** |
| frontmatter 读取 | 通过 Read 选读命中的 Concept | `head -10` 一次性读完 15 个 frontmatter |
| 匹配判断 | 基于 grep 命中的段落局部推理 | 基于全部 15 个 frontmatter 的全局对比 |
| Concept 深读 | 只读 grep 命中的 | 自行判断相关的 6 个，全读 |
| 遗漏风险 | 关键词没命中 → 整个 Concept 不可见 | frontmatter 全部可见 → 零遗漏 |

**关键洞察**：ingest subagent 在实际运行中**没有使用 Phase 1-4 测试的那种 keyword grep → selective read 策略**。它用了更简单粗暴但更可靠的"全量前端扫描 → 语义路由 → 选择性深读"——本质上是把 15 个 Concept 的 problem 字段当成了一个微型向量空间，用 LLM 的语义理解能力做了全局匹配。

这个差异**不否定 Phase 1-4 的结论**——Phase 1-4 证明了 keyword grep 在 22 条查询上能可靠找到正确匹配。但 Phase 5 的实际行为说明：**在当前规模（15 Concept + 52 条目）下，全量 frontmatter 扫描的 token 成本完全可承受，且比 keyword grep 更可靠（无关键词遗漏风险）。**

到 500 个 Concept 时，全量 frontmatter 扫描（`head -10` 500 个文件 ≈ 5000 行 frontmatter）仍然是可行的——500 个 YAML frontmatter 合计约 10000-15000 tokens，单次推理即可覆盖。真正的瓶颈不是 frontmatter 扫描，而是选择性深读的步数——当 500 个 Concept 中有 50 个与一个新仓库相关时，深读 50 个页面会产生显著的 token 成本。

### 8.4 检索回来的全部条目与匹配结果

实际检索链路中，每个 deepagents 问题空间条目与检索到的 Concept/Sed 的对应关系：

| # | deepagents 条目 | frontmatter 扫描触达 | 深读的 Concept | 最终匹配 | 分类 |
|---|----------------|---------------------|---------------|---------|------|
| 1 | 中间件组装 | 全部 15 个 frontmatter | 无直接命中 → 判为新概念 | (新建) middleware-composition-pattern | B |
| 2 | 文件系统操作接口 | 全部 15 个 | tool-lifecycle-management 未深读 | (信号) tool-lifecycle-management 子维度 | D |
| 3 | 大工具输出驱逐 | 全部 15 个 | context-compression-strategy | context-compression-strategy | A |
| 4 | 同步子代理 | 全部 15 个 | subagent-orchestration | subagent-orchestration | A |
| 5 | 异步子代理 | 全部 15 个 | subagent-orchestration | subagent-orchestration | A |
| 6 | 对话摘要压缩 | 全部 15 个 | context-compression-strategy | context-compression-strategy | A |
| 7 | 记忆加载 | 全部 15 个 | memory-management-architecture | memory-management-architecture | A |
| 8 | 技能加载 | 全部 15 个 | skills-extension-mechanism | skills-extension-mechanism | A |
| 9 | 后端协议 | 全部 15 个 | execution-isolation | execution-isolation | A |
| 10 | 多后端路由 | 全部 15 个 | execution-isolation | execution-isolation | A |
| 11 | 模型解析 | 全部 15 个 | provider-abstraction-pattern | provider-abstraction-pattern | A |

**核心特征**：每个条目都经过了"全部 15 个 frontmatter 入眼 → 语义判断 → 选择性深读"的完整链路。没有条目因为"关键词没命中"而被遗漏——因为全量扫描保证了每个 Concept 的 problem 字段都会被 LLM 读到。

**但这也意味着**：ingest subagent 没有用 grep 去做"在 problem-map 中匹配已有问题空间"这一步。它直接从 entity 提取到了 Concept 匹配——中间没有显式地在 seeds/problem-map 中做对照搜索。B1（middleware-composition-pattern）是个例外——agent 判断 15 个 Concept 中无匹配，然后独立判断四条准则成立，创建新 Concept。

### 8.5 方法论校准

Phase 1-4 实验的结论是：**agentic grep 在 keyword → file hit → deep read 模式下能可靠找到匹配**。这个结论仍然是正确的。

但 Phase 5 的实际行为表明：**ingest skill 当前使用的是更保守的"全量扫描"策略，未经 keyword grep 中间层**。这意味着：

1. 在规模较小（< 50 Concept）时，全量扫描是完全合理的——tokens 成本低、零遗漏
2. 当前实验验证的"agentic grep"策略是一种**可选的优化策略**，而非当前 ingest 实际使用的策略
3. 如果将来确实切换到 keyword grep 策略（500 Concept 时深读 50 页不可行），Phase 1-4 的实验数据证明了这个策略是可靠的
4. 建议：在 `/ingest` SKILL.md 的 Step 3 定义中，明确定义"全量 frontmatter 扫描"和"关键词 grep 预筛"两种策略的选择条件——按 Concept 数量阈值自动切换
