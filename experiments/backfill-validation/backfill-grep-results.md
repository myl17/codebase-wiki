# 向后传播 grep 实验

## 第 1 层：机械 grep

**搜索词来源**：原始 Concept (commit f46bbcd) 的 `concerns` 字段 `[事件覆盖完整性, 匹配器精度与过滤开销, 执行隔离与性能]` 拆分为独立词语。

| 搜索词 | 命中 entity | 计数 |
|--------|-----------|------|
| 事件 | summarization-middleware | 1 |
| 覆盖 | agent-graph-assembly, async-subagent-middleware, model-resolution, skills-middleware, state-backend, subagent-middleware | 6 |
| 匹配器 | (无) | 0 |
| 过滤 | state-backend, subagent-middleware | 2 |
| 执行 | backend-protocol, composite-backend, async-subagent-middleware, state-backend, tool-call-patching, subagent-middleware | 6 |
| 隔离 | subagent-middleware | 1 |
| 性能 | (无) | 0 |
| 完整性 | tool-call-patching | 1 |
| 精度 | (无) | 0 |
| 开销 | (无) | 0 |

**第 1 层合计命中（去重）**：10 个 entity

```
async-subagent-middleware
agent-graph-assembly
backend-protocol
composite-backend
model-resolution
skills-middleware
state-backend
subagent-middleware
summarization-middleware
tool-call-patching
```

**未命中**：filesystem-middleware, memory-middleware（共 2 个）

---

## 第 2 层：LLM 生成搜索词

**推理过程**：

从三方框架的实现中抽象模式：
- **codex-main**：10 个命名生命周期事件（PreToolUse/PostToolUse/PermissionRequest/PreCompact/PostCompact/SessionStart/UserPromptSubmit/SubagentStart/SubagentStop/Stop），8 个事件支持按工具名/触发源匹配器过滤，外部命令执行引擎——核心模式是**命名事件 + 匹配器 + 外部执行**。
- **openclaw**：插件钩子系统，钩子发现-过滤-隔离——核心模式是**插件式钩子 + 发现机制**。
- **nanobot**：中间件组合模式，中间件按顺序组成处理链，每个中间件可在处理前后插入逻辑——核心模式是**中间件管道 + 前后拦截**。

从这些模式中抽象出跨框架通用表达：
1. **中间件管道模式**（nanobot 的核心表达）→ 搜索词 `middleware`, `pipeline`
2. **钩子/扩展点模式**（codex + openclaw 共用）→ 搜索词 `hook`, `extension`
3. **前后处理拦截**（三个框架都有的 before/after 语义）→ 搜索词 `before_`, `wrap_`, `intercept`
4. **生命周期驱动**（codex 的显式事件 + nanobot 的隐式管道）→ 搜索词 `lifecycle`
5. **回调注册机制**（通用实现模式，任何一个框架都可能用 callback 实现钩子）→ 搜索词 `callback`

**搜索词列表**：`hook`, `middleware`, `lifecycle`, `wrap_`, `intercept`, `pipeline`, `callback`, `extension`

| 搜索词 | 命中 entity | 计数 |
|--------|-----------|------|
| hook | (无) | 0 |
| middleware | agent-graph-assembly, async-subagent-middleware, backend-protocol, composite-backend, memory-middleware, filesystem-middleware, subagent-middleware, skills-middleware, summarization-middleware, state-backend, tool-call-patching | 11 |
| lifecycle | (无) | 0 |
| wrap_ | subagent-middleware | 1 |
| intercept | (无) | 0 |
| pipeline | (无) | 0 |
| callback | (无) | 0 |
| extension | skills-middleware | 1 |

**第 2 层合计命中（去重）**：11 个 entity

```
agent-graph-assembly
async-subagent-middleware
backend-protocol
composite-backend
filesystem-middleware
memory-middleware
skills-middleware
state-backend
subagent-middleware
summarization-middleware
tool-call-patching
```

---

## 合并结果 vs 地面真值

地面真值：5 个 deepagents entity 包含生命周期拦截机制（hook/before_agent/wrap_model_call/interrupt_on）。

| Entity | 第 1 层命中 | 第 2 层命中 | 命中层 | head-10 problem 确认 |
|--------|-----------|-----------|--------|-------------|
| subagent-middleware | ✅ (覆盖/过滤/执行/隔离) | ✅ (middleware, wrap_) | L1+L2 | ✅ "委派给隔离的短期子 Agent 执行" -- 子Agent 生命周期拦截 |
| filesystem-middleware | ❌ | ✅ (middleware) | L2 only | ✅ "自动管理上下文窗口溢出" -- 上下文生命周期拦截 |
| memory-middleware | ❌ | ✅ (middleware) | L2 only | ✅ "Agent 启动时从文件系统加载" -- 会话启动钩子 |
| tool-call-patching | ✅ (执行/完整性) | ✅ (middleware) | L1+L2 | ✅ "修复消息历史中因中断或并发导致的悬空工具调用" -- before_agent 生命周期拦截 |
| agent-graph-assembly | ✅ (覆盖) | ✅ (middleware) | L1+L2 | ✅ "将多个中间件组合成一个完整配置的 AI Agent 图" -- 定义钩子执行顺序 |

**通过标准**：至少覆盖 >= 2 个地面真值 entity，假阳性 < 3

**结果**：覆盖 5/5 地面真值。假阳性 7 个（见下节分析）。

---

## 假阳性分析

| Entity | 被哪层捕获 | 捕获词 | 为何假阳性 |
|--------|-----------|--------|-----------|
| async-subagent-middleware | L1+L2 | 覆盖/执行 + middleware | problem 是关于异步子 Agent 任务管理，不属于生命周期拦截 |
| backend-protocol | L1+L2 | 执行 + middleware | problem 是关于后端接口协议定义，与钩子无关 |
| composite-backend | L1+L2 | 执行 + middleware | problem 是关于后端路由策略，与钩子无关 |
| model-resolution | L1 only | 覆盖 | problem 是模型标识符解析，完全无关；"覆盖"误中"覆盖不同格式" |
| skills-middleware | L1+L2 | 覆盖 + middleware/extension | problem 是技能按需加载，与生命周期拦截无关 |
| summarization-middleware | L1+L2 | 事件 + middleware | problem 是上下文压缩，**与 Concept "上下文压缩" 钩子语义相关**，但未在源码中实现 before_agent/wrap_model_call/interrupt_on 机制，故标记为假阳性 |
| state-backend | L1+L2 | 覆盖/过滤/执行 + middleware | problem 是状态管理存储，与生命周期钩子无关 |

**有效假阳性**：6 个（不含 summarization-middleware 的语义争议）

---

## 分析

### 1. 两层 grep 各自的优势区间

- **第 1 层（机械 grep）**：以 concerns 中文词为种子。优势是零 token 零推理，直接覆盖了 3/5 地面真值（agent-graph-assembly、tool-call-patching、subagent-middleware）。"覆盖"、"执行"、"过滤" 三个词贡献了绝大多数命中。局限：中文 concerns 词语与 entity 页正文的用词习惯不完全对齐——"事件" 只命中 summarization-middleware，而 5 个地面真值 entity 均未在正文中使用"事件"一词。filesystem-middleware 和 memory-middleware 完全漏检，因为它们的 entity 正文中不包含 concerns 拆分出的任何中文词。

- **第 2 层（LLM 搜索词）**：以跨框架抽象模式生成的英文搜索词。`middleware` 一词就覆盖了全部 12 个 entity 中的 11 个（deepagents 的 entity 命名和后缀基本都含 middleware）。这既是优势也是劣势——极高召回但几乎零精度。其余 7 个搜索词中 5 个零命中（hook/lifecycle/intercept/pipeline/callback），`wrap_` 精准命中 subagent-middleware（该 entity 源码使用 `wrap_model_call`），`extension` 命中 skills-middleware。filesystem-middleware 和 memory-middleware 仅靠 `middleware` 这个高召回低精度词被捕获。

### 2. 第 2 层的搜索词是否有框架特定术语泄露

搜索词生成时刻意避免了 codex 的 API 术语（PreToolUse、PostToolUse、SessionStart 等）。但有两点值得注意：

- **`wrap_` 属于通用模式但碰巧匹配了 deepagents 的 `wrap_model_call`**：wrap 模式在 codex 中体现为事件包裹（PreToolUse + PostToolUse 形成 wrap），在 nanobot 中体现为中间件包裹管道。`wrap_` 是抽象模式词而非框架特定词，但在 deepagents 中恰好对应了其具体 API 命名 `wrap_model_call`，命中 subagent-middleware。
- **`middleware` 命中过宽**：在 deepagents 这个特定仓库中，middleware 是 entity 命名后缀而非实现层特征信号。`middleware` 作为搜索词的行为更接近文件命名匹配而非内容语义匹配。

### 3. 假阳性的来源

假阳性主要来自三个渠道：

1. **中文通用词的语义歧义**（第 1 层）：
   - "覆盖"：在 Concept 中意为 "事件覆盖完整性"（coverage），但在 entity 页中可能意为 "覆盖不同格式/场景"。model-resolution 中使用了"覆盖"描述模型格式的多态处理，与生命周期拦截完全无关。
   - "执行"：在 Concept 中意为 "Hook 执行隔离"（execution），但在 entity 页中广泛用于描述后端命令执行、任务执行等通用操作。backend-protocol、composite-backend、async-subagent-middleware、state-backend 均因此误中。
   - "过滤"：在 Concept 中意为 "匹配器过滤"，但在 state-backend 中可能是数据过滤语义。

2. **`middleware` 搜索词在 deepagents 中的过度泛化**（第 2 层）：
   由于 deepagents 几乎所有扩展机制都定义为 middleware 类，`middleware` 词命中 11/12 entity，几乎丧失了区分度。这是搜索词在特定仓库语境下的退化现象。

3. **Entity 命名污染的假信号**：
   deepagents 的 entity 命名约定（*-middleware 后缀）使得 middleware 一词的行为类似文件命名匹配而非语义匹配。filesystem-middleware 和 memory-middleware 虽然确实是地面真值，但它们被 middleware 命中更像巧合（所有 middleware entity 都被命中），而非搜索词的语义选择性起作用。

### 4. 关键发现

- **filesystem-middleware 和 memory-middleware 仅靠 `middleware` 命中**。这个搜索词的命中率在 deepagents 仓库中为 11/12，也就是说在这个特定仓库中它的实际信息增益几乎为零——它命中了所有东西，包括与生命周期拦截无关的 entity。
- **如果去掉 `middleware`，第 2 层仅命中 1 个地面真值**（subagent-middleware 通过 `wrap_`）。这意味着在远离 middleware 命名约定的仓库中，第 2 层的有效性需要重新评估。
- **summarization-middleware 是一个有趣的边界案例**：它的语义确实属于 contexts-compression-strategy（Concept 核心问题明确提到"上下文压缩等"），但它在 deepagents 源码中未使用 before_agent/wrap_model_call/interrupt_on 机制来拦截生命周期。这提示搜索词需要区分"语义属于 Concept"和"实现机制属于 Concept"两个层次。
