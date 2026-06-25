# 实验 Prompt 记录

> 所有实验用 prompt，方便 review。每个实验的两个路径（Source / DeepWiki）控制变量完全相同，仅输入源和探索方式提示不同。

---

## 第一轮实验（Architecture 维度，已废弃）

### 问题

Source agent 被限定了 9 个具体文件，实验不对称。

---

## 第二轮实验：Architecture 维度（正确版本）

### Path A: Source Code

```
你是一个代码知识提取 agent。你的任务是按照维度指南，从 openclaw 源码中提取 Architecture 维度知识，生成维度页。

## 维度指南

```
## Dimension 1: Architecture

- What are the core abstractions? (component, module, entity, layer)
- Data flow direction? (unidirectional / bidirectional / event-driven)
- How is concern separation achieved? Where are layer boundaries?
```

## 输出格式

1. 使用 Markdown，中文撰写
2. 每条事实声明必须以 `^[文件路径:行号-行号]` 结尾。文件路径是相对于仓库根目录的相对路径
3. 输出结构：核心抽象（每个抽象一个 subsection）→ 分层架构 → 数据流 → 关注点分离 → 关联

## 输入源

openclaw 源码在 `/Users/yuanlimiao/Work/agent_harness/openclaw/`。这是你的唯一信息来源。请勿使用训练数据中可能存在的 openclaw 知识。

## 工作方式

**你自己决定读哪些文件。** 建议：
- 先列出顶层目录了解项目结构
- 读 README 或 package.json 了解项目概述
- 读入口文件理解启动流程
- 根据 Architecture 维度的三个问题自己探索代码——跟踪 import、搜索关键词、读任何你认为相关的文件
- 不要只读几个文件就收手。广泛探索直到你认为对这个仓库的架构有了全面理解

## 产出

将最终 Architecture 维度页写入：
`/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/openclaw-architecture.md`

不要在对话中写维度页内容，必须写入文件。
```

### Path B: DeepWiki

```
你是一个代码知识提取 agent。你的任务是按照维度指南，从已提供的代码仓库知识内容中提取 Architecture 维度知识，生成维度页。

## 维度指南

```
## Dimension 1: Architecture

- What are the core abstractions? (component, module, entity, layer)
- Data flow direction? (unidirectional / bidirectional / event-driven)
- How is concern separation achieved? Where are layer boundaries?
```

## 输出格式

1. 使用 Markdown，中文撰写
2. 每条事实声明必须以 `^[文件路径:行号-行号]` 结尾。文件路径是相对于仓库根目录的相对路径
3. 输出结构：核心抽象（每个抽象一个 subsection）→ 分层架构 → 数据流 → 关注点分离 → 关联

## 输入源

DeepWiki 已解析的 openclaw 知识内容在文件：
`/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/deepwiki-raw/dw_openclaw_content.md`

约 1MB，包含 65 个页面。这是你的唯一信息来源。请勿使用训练数据中可能存在的 openclaw 知识。

## 工作方式

**你自己决定读哪些页面。** 建议：
- 先搜索文件内容了解有哪些页面（用 `grep "# Page:"` 列出所有页面标题）
- 选择与 Architecture 维度相关的页面（判断标准：核心抽象、数据流方向、关注点分离、分层边界）
- 不要只读 2-3 个页面就收手——广泛探索，找到所有与架构理解相关的信息
- 你可以用 `offset` + `limit` 分段读取大页面

## 产出

将最终 Architecture 维度页写入：
`/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-deepwiki/openclaw-architecture.md`

不要在对话中写维度页内容，必须写入文件。
```

---

## 第三轮实验：Hermes Agent 和 Codex Architecture 维度

### 与第二轮完全相同的 prompt 模板，仅替换仓库路径和产出文件路径。

**变动对照：**
- OpenClaw → Hermes/Codex
- 源码路径 → 对应仓库路径
- DeepWiki 内容文件 → 对应 dw_*_content.md
- 产出文件名 → 对应仓库名

### Codex DeepWiki 提示额外改动了什么

因为在 Hermes 实验中发现 DeepWiki agent 跳过了 Memory、Skills 等包含自学习信息的页面，Codex 的 DeepWiki prompt 中加入了提醒：

```
- **重要：不只读 Architecture Overview 和 Core Concepts。** 一个仓库的独特架构特征往往隐藏在 Memory、Skills、Hooks、Thread Management、MCP、Plugins 等页面中。广泛探索。
```

这是**唯一一次修改了实验变量**（给 DeepWiki agent 加了额外引导）。但在 Architecture 维度结束后，这条引导被统一纳入了所有后续实验的 prompt。

---

## 第四轮实验：Performance Tradeoffs 维度

### 设计差异

Performance Tradeoffs 维度与 Architecture 不同——权衡信息往往不在单独的 "Performance" 页面中，而是隐藏在众多子系统页面里。两条 prompt 都对此做了提示。

### Path A: Source Code（一次性处理三个仓库）

```
你是一个代码知识提取 agent。按照维度指南，从源码中提取 Performance Tradeoffs 维度知识，为一个仓库生成维度页。

## 维度指南

```
## Dimension 3: Performance Tradeoffs

- What has been optimized? (startup time / runtime perf / memory)
- What has been sacrificed? What is the rationale for that tradeoff?
- Where in the code is the tradeoff visible? (specific file and lines)
```

## 输出格式

1. 使用 Markdown，中文撰写
2. 每条事实声明必须以 `^[文件路径:行号-行号]` 结尾
3. 输出结构：每项权衡一个 subsection，包含优化目标、手段、牺牲、源码证据。最后加上权衡汇总表

## 输入源

### 仓库 1: openclaw
源码在 `/Users/yuanlimiao/Work/agent_harness/openclaw/`
产出写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/openclaw-performance-tradeoffs.md`

### 仓库 2: hermes-agent
源码在 `/Users/yuanlimiao/Work/agent_harness/hermes-agent/`
产出写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/hermes-agent-performance-tradeoffs.md`

### 仓库 3: codex
源码在 `/Users/yuanlimiao/Work/agent_harness/codex-main/`（Rust workspace 在 codex-rs/ 下）
产出写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/codex-performance-tradeoffs.md`

## 工作方式

对每个仓库，自己决定读哪些文件。关键是寻找**设计取舍的证据**：
- 是否有 "chose X over Y"、"tradeoff"、"牺牲" 出现在注释或文档中？
- `prompt_caching`、`compaction`、`compression`、`cache`、`lazy`、`debounce`、`throttle` 关键词
- 启动优化、内存优化、token 成本优化的相关代码
- benchmark 文件和性能配置

广泛探索直到全面理解每个仓库的取舍，然后分别写入三个文件。
```

### Path B: DeepWiki（一次性处理三个仓库）

```
你是一个代码知识提取 agent。按照维度指南，从 DeepWiki 预解析内容中提取 Performance Tradeoffs 维度知识，为三个仓库生成维度页。

## 维度指南

```
## Dimension 3: Performance Tradeoffs

- What has been optimized? (startup time / runtime perf / memory)
- What has been sacrificed? What is the rationale for that tradeoff?
- Where in the code is the tradeoff visible? (specific file and lines)
```

## 输出格式

1. 使用 Markdown，中文撰写
2. 每条事实声明必须以 `^[文件路径:行号-行号]` 结尾
3. 输出结构：每项权衡一个 subsection，包含优化目标、手段、牺牲、源码证据。最后加上权衡汇总表

## 输入源

### 仓库 1: openclaw
预解析内容: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/deepwiki-raw/dw_openclaw_content.md`
产出写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-deepwiki/openclaw-performance-tradeoffs.md`

### 仓库 2: hermes-agent
预解析内容: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/deepwiki-raw/dw_hermes_content.md`
产出写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-deepwiki/hermes-agent-performance-tradeoffs.md`

### 仓库 3: codex
预解析内容: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/deepwiki-raw/dw_codex_content.md`
产出写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-deepwiki/codex-performance-tradeoffs.md`

## 工作方式

对每个仓库：
1. 用 `grep "# Page:"` 列出所有页面标题
2. 选择与 Performance Tradeoffs 相关的页面。注意：性能权衡信息往往不在单独的 "Performance" 页面中，而是隐藏在 Context Compression、Prompt Caching、Model Selection、Startup、Compaction、Sandboxing、Approval 等页面里。广泛阅读。
3. 关键是寻找**设计取舍的证据**——优化了什么、牺牲了什么、为什么做这个取舍。如果 DeepWiki 页面只描述了机制但没有说明取舍理由，诚实记录「该页面描述了机制但未说明取舍理由」
4. 对每个仓库分别写入

不要在对话中写维度页内容，必须写入文件。
```

---

## 第五轮实验：Extension Points 维度

### 设计原则

1. **纯通用提示词。** 不硬编码 AI agent 领域关键词
2. **每个仓库单独 subagent。** 不是一次性处理三个仓库
3. **每个仓库两条路径各一个 agent。** 共 6 个 subagent，独立上下文

### Path A: Source Code（通用模板，以 openclaw 为例）

```
你是代码知识提取 agent。按维度指南提取 Extension Points 维度知识。

## 维度指南

```
## Dimension 2: Extension Points

- Does a plugin system exist? Where is the entry file?
- Where are hooks / middleware / interceptors designed?
- Which layer is the easiest entry point for framework customization?
- Is there an official extension protocol (interfaces / types / conventions)?
```

## 输出格式

1. 中文 Markdown
2. 每条事实 `^[文件路径:行号-行号]` 结尾
3. 结构：每个扩展点一个 subsection → 扩展难度梯度 → 关联

## 输入源

openclaw 源码: `/Users/yuanlimiao/Work/agent_harness/openclaw/`
唯一信息来源，不用训练数据。

## 工作方式

自行决定读哪些文件。广泛探索直到全面理解扩展机制。

## 产出

写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/openclaw-extension-points.md`
必须写入文件。
```

### Path B: DeepWiki（通用模板，以 openclaw 为例）

```
你是代码知识提取 agent。按维度指南提取 Extension Points 维度知识。

## 维度指南

```
## Dimension 2: Extension Points

- Does a plugin system exist? Where is the entry file?
- Where are hooks / middleware / interceptors designed?
- Which layer is the easiest entry point for framework customization?
- Is there an official extension protocol (interfaces / types / conventions)?
```

## 输出格式

1. 中文 Markdown
2. 每条事实 `^[文件路径:行号-行号]` 结尾
3. 结构：每个扩展点一个 subsection → 扩展难度梯度 → 关联

## 输入源

DeepWiki 预解析内容: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/deepwiki-raw/dw_openclaw_content.md`
唯一信息来源，不用训练数据。

## 工作方式

`grep "# Page:"` 列出页面 → 选择与扩展机制相关的页面 → 分段读取。广泛探索。

## 产出

写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-deepwiki/openclaw-extension-points.md`
必须写入文件。
```

### 变体

**hermes-agent**: 源码路径 → `/Users/yuanlimiao/Work/agent_harness/hermes-agent/`，DeepWiki 内容 → `dw_hermes_content.md`

**codex**: 源码路径 → `/Users/yuanlimiao/Work/agent_harness/codex-main/`（补充 "Rust workspace 在 codex-rs/ 下"），DeepWiki 内容 → `dw_codex_content.md`

### 特点

- **真正纯通用：** 没有任何 "plugin"、"MCP"、"skill" 等 AI agent 领域关键词
- **极简 prompt：** 比 Architecture 和 Performance Tradeoffs 实验的 prompt 更短
- **维度指南 + 输出格式 + 工作方式 + 产出路径，四段式固定结构**

---

## 第六轮实验：Performance Tradeoffs v2（架构清单驱动）

### 设计原则

1. **复用 Architecture + Extension Points 产出作为子系统清单。** 不再让 agent 自己定义「什么算性能权衡」
2. **只测 Hermes。** 验证方法论是否让两个路径收敛
3. **Source 和 DeepWiki 使用相同的子系统清单**——但清单内容来自各自路径的 Architecture + Extension Points 产出

### Path A: Source Code

```
你是代码知识提取 agent。从源码中提取 Performance Tradeoffs 维度知识。

## 维度指南

对于以下核心抽象/子系统，**逐个检查**是否存在设计权衡：

### 来自 Architecture 维度的子系统清单

1. AIAgent（中央编排器）— 对话循环、API 调用管理、工具执行分发、上下文管理
2. ToolRegistry（工具注册中心）— 单例注册、AST 自发现、线程安全
3. Toolset（工具集组合器）— 按场景分组、组合继承
4. GatewayRunner（消息网关控制器）— 平台适配器生命周期、代理缓存、并发守护
5. Platform Adapter（平台适配器抽象）— 20+ 消息平台统一接口
6. SessionDB（会话持久化存储）— SQLite + FTS5、WAL 模式
7. MemoryProvider（可插拔记忆后端）— 内置+外部、生命周期接口
8. ContextCompressor（上下文压缩器）— LLM 摘要、自动触发
9. IterationBudget（迭代预算）— 线程安全计数器

### 来自 Extension Points 维度的扩展点

10. 插件系统 — PluginManager、注册生命周期钩子、中间件
11. 工具注册 — 自注册模式、动态发现
12. MCP 集成 — stdio/HTTP transport、外部工具发现
13. 技能系统 — SKILL.md、渐进式披露
14. 上下文引擎 — ContextEngine ABC、可插拔替换
15. 执行环境 — BaseEnvironment ABC、6 种后端
16. 网关事件钩子 — 8 种事件类型

### 检查标准

每个子系统，回答：
1. 是否存在设计权衡？（判断标准：代码中有 "chose X over Y" 类似表述，或功能描述中隐含了取舍）
2. 如果存在：优化了什么？牺牲了什么？为什么这个取舍是可接受的？源码证据在哪里？
3. 如果不存在：标注「未发现」并跳过

## 输出格式

1. 中文 Markdown
2. 每条事实 `^[文件路径:行号-行号]` 结尾
3. 每项权衡一个 subsection，含：优化目标、手段、牺牲、理由、源码证据
4. 最后：权衡汇总表（列：子系统、优化了什么、牺牲了什么、关键文件）

## 输入源

hermes-agent 源码: `/Users/yuanlimiao/Work/agent_harness/hermes-agent/`
唯一信息来源，不用训练数据。

## 工作方式

逐个子系统深读源码。不要在没读代码的情况下标注「未发现」。

## 产出

写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/hermes-agent-performance-tradeoffs-v2.md`
必须写入文件。
```

### Path B: DeepWiki

```
你是代码知识提取 agent。从 DeepWiki 预解析内容中提取 Performance Tradeoffs 维度知识。

## 维度指南

对于以下核心抽象/子系统，**逐个检查**是否存在设计权衡：

### 来自 Architecture 维度的子系统清单

1. AIAgent（中央编排器）— LLM 通信、工具编排、上下文管理、会话状态与记忆、迭代预算控制
2. ToolRegistry（工具注册表单例）— 自注册模式、线程安全、异步桥接
3. BaseEnvironment（执行环境抽象）— spawn-per-call 模型、6 种后端、ProcessHandle 协议
4. GatewayRunner（网关运行器）— LRU 代理缓存、并发守护、瞬态错误处理
5. BasePlatformAdapter（平台适配器基类）— 消息收发、媒体处理
6. IterationBudget（迭代预算）— 步数限制、子代理共享分配
7. Toolset（工具集）— 组合模式、嵌套 includes
8. Skill（技能）— 渐进式披露 Tier 0/1/2、安全扫描

### 来自 Extension Points 维度的扩展点

9. 插件系统 — PluginManager、config.yaml 启用、plugin.yaml 清单
10. 生命周期钩子 — on_session_start/end、pre/post_llm_call、pre/post_tool_call
11. 工具注册 — registry.register()、AST 自动发现
12. MCP 集成 — stdio/HTTP transport、工具名规范化
13. 技能系统 — SKILL.md、Skill Hub、安全扫描
14. 上下文引擎 — ContextEngine ABC、压缩阈值、可插拔替换
15. 执行环境 — 6 种后端、工厂模式
16. 内存提供者 — MemoryProvider ABC、7 个内置实现

### 检查标准

每个子系统，回答：
1. 是否存在设计权衡？（判断标准：DeepWiki 描述中是否提到了取舍、牺牲、或 "chose X over Y" 的决策）
2. 如果存在：优化了什么？牺牲了什么？为什么这个取舍是可接受的？源码证据在哪里？
3. 如果不存在：标注「未发现」并跳过
4. 如果 DeepWiki 只描述了机制但没有取舍理由，这样写：「机制已知，取舍理由未在 DeepWiki 中说明」

## 输出格式

1. 中文 Markdown
2. 每条事实 `^[文件路径:行号-行号]` 结尾
3. 每项权衡一个 subsection，含：优化目标、手段、牺牲、理由、源码证据
4. 最后：权衡汇总表（列：子系统、优化了什么、牺牲了什么、关键文件）

## 输入源

DeepWiki 预解析内容: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/deepwiki-raw/dw_hermes_content.md`
唯一信息来源，不用训练数据。

## 工作方式

逐个子系统，grep 定位相关页面，分段读取。不要在没读的情况下标注「未发现」。

## 产出

写入: `/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-deepwiki/hermes-agent-performance-tradeoffs-v2.md`
必须写入文件。
```

### 关键设计决策

1. **两个路径的子系统清单不同。** Source 路径的清单来自 Source agent 的 Architecture 产出，DeepWiki 路径的清单来自 DeepWiki agent 的 Architecture 产出。这模拟了真实场景——每个路径用自己的 Architecture 产出做索引。
2. **清单长度相等（各 16 项）。** 保证公平。
3. **检查标准完全对称。** 唯一的差异是 DeepWiki 路径多了一条「如果 DeepWiki 只描述了机制但没有取舍理由，标注已读但缺理由」。

---

## 全部实验方法总结

| 实验 | 维度 | 控制变量 | 唯一变量 | 是否公平 |
|------|------|---------|---------|---------|
| Architecture Round 1 | Architecture | — | Source 限定 9 个文件 | ❌ 不公平 |
| Architecture Round 2 | Architecture | 相同维度指南、输出格式、探索自由度 | 输入源 (源码 vs DeepWiki) | ✅ 公平 |
| Architecture × 3 repos | Architecture | 同上 | 同上（Hermes 额外测试） | ✅ 公平 |
| Performance Tradeoffs v1 | Perf | 相同维度指南、输出格式 | 输入源（三个仓库一次提取） | ✅ 公平 |
| Extension Points × 3 repos | Ext | 相同维度指南、输出格式、纯通用 prompt、每个仓库单独 agent | 输入源 | ✅ 公平 |
| Performance Tradeoffs v2 | Perf | 架构清单驱动、逐个检查、相同输出格式、只测 Hermes | 输入源 + 各自的架构清单 | ✅ 公平 |

---

---

## 第七轮实验：过程约束验证（三步流程 vs 单次提取）

### 设计原则

不改变维度指南内容和输出格式。只改变提取流程——在写入前插入两个检查关卡。

### Step 0: Baseline（对 v1 产出做对抗式评审）

```
你是事实核查员。对以下 Performance Tradeoffs 维度页进行反向验证。

## 被评审内容

文件：`/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/hermes-agent-performance-tradeoffs.md`

这是另一个 agent 从 Hermes Agent 源码中提取的性能权衡维度页。请先读取这个文件的全部内容。

## 你的任务

### A. 随机抽取验证（5 条）

从文件中随机选 5 条权衡声明。对每条，回 Hermes Agent 源码（`/Users/yuanlimiao/Work/agent_harness/hermes-agent/`）中标注的文件和行号，验证：

- ✅ 行号正确、代码确实实现了描述的逻辑
- ⚠️ 行号偏移、代码只有部分相关
- ❌ 找不到对应的逻辑（虚构）

### B. 已知盲区检查

从 Hermes Agent 源码目录中，分别检查以下目录是否包含了该维度页完全遗漏的性能权衡：

1. `agent/context_compressor.py`
2. `cron/`
3. `tools/approval.py`
4. `skills/` 或 `tools/skills_guard.py`
5. `agent/prompt_caching.py`

对每个盲区：如果有遗漏，列出遗漏的具体权衡（优化了什么、牺牲了什么）。

### C. 整体评估

- 事实准确性：A 部分验证结果统计
- 覆盖完整性：B 部分发现的遗漏统计
- 总体评分

## 产出

写入：`/tmp/step0-v1-review.md`
必须写入文件。
```

### Step 1: 候选清单 + 自审

```
你是代码知识提取 agent。从 Hermes Agent 源码中提取 Performance Tradeoffs 维度知识。

## 维度指南

```

## Dimension 3: Performance Tradeoffs

- What has been optimized? (startup time / runtime perf / memory)
- What has been sacrificed? What is the rationale for that tradeoff?
- Where in the code is the tradeoff visible? (specific file and lines)

```

## 工作方式

1. 探索 Hermes Agent 源码目录：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/`
2. 检查以下每个子目录，确保没有遗漏：`agent/`、`tools/`、`gateway/`、`cron/`、`skills/`、`hermes_cli/`、`plugins/`
3. 对每个子系统，判断是否存在设计权衡。如果不存在，标注「未发现」。不允许在没有读代码的情况下做出「未发现」判断

## 输出（两步）

### 第一步：候选权衡清单

每项格式：
```

序号. 子系统 - 权衡名称
  优化了什么：[一句话]
  牺牲了什么：[一句话]  
  源码证据：^[文件路径:行号-行号]

```

### 第二步：自审

在候选清单之后，附上自审结果：

```

□ 是否检查了所有子目录？（agent/, tools/, gateway/, cron/, skills/, hermes_cli/, plugins/）
□ 是否有遗漏的子目录？
□ 每条是否有明确的牺牲声明（不只是「使用了XX机制」的描述）？
□ 所有 provenance 行号是否在已读源码范围内（不是猜测的）？

```

## 产出

写入：`/tmp/step1-candidates.md`
必须写入文件。
```

### Step 2: 对抗式评审（独立 subagent）

```
你是事实核查员。对以下候选权衡清单进行反向验证。

## 被评审内容

文件：`/tmp/step1-candidates.md`

另一个 agent 从 Hermes Agent 源码中提取了候选性能权衡清单。请先读取该文件全部内容。

## A. 随机抽取验证（5 条）

从候选清单中随机选 5 条权衡声明。对每条，回 Hermes Agent 源码（`/Users/yuanlimiao/Work/agent_harness/hermes-agent/`）中标注的文件和行号验证：

- ✅ 行号正确、代码确实实现了描述的逻辑
- ⚠️ 行号偏移、代码只有部分相关
- ❌ 找不到对应的逻辑（虚构）

## B. 已知盲区检查

检查 Hermes Agent 源码中的以下位置是否包含了候选清单完全遗漏的权衡：

1. `tools/approval.py`
2. `agent/context_compressor.py`
3. `cron/`
4. `tools/skills_guard.py`
5. `agent/prompt_caching.py`

对每个盲区：如果发现遗漏，列出遗漏的具体权衡。

## C. 自审检查

候选清单后面的自审 checklist 是否诚实？
- agent 自审声称检查了所有子目录，是否真的全部覆盖了？
- agent 是否真的读了代码而不是猜测？

## 产出

写入：`/tmp/step2-review.md`
必须写入文件。
```

### Step 3: 修复 → 最终产出

```
你收到了事实核查员对你候选权衡清单的评审结果。请基于评审反馈修复问题，然后生成最终维度页。

## 你的候选清单

文件：`/tmp/step1-candidates.md`（请先读取回顾）

## 评审结果

文件：`/tmp/step2-review.md`（请先读取）

## 你需要修复的问题

根据评审结果：

1. 第 10 条：修正不精确的行号
2. 第 15 条：修正不精确的行号
3. hermes_cli/ 目录零覆盖：补充遗漏
4. cron/ 浅覆盖：补充遗漏
5. Smart Approval：补充遗漏
6. skills_guard.py：补充遗漏
7. context_compressor.py：补充遗漏细节
8. prompt_caching.py：补充遗漏细节

## 修复标准

- 每条修复必须有实际源码行号证据
- 如果某个被评审指出的遗漏实际不存在（读代码后确认不是遗漏），说明原因

## 产出

写入：`/Users/yuanlimiao/Work/codebase-wiki/experiments/deepwiki-vs-source/llm-output-source/hermes-agent-performance-tradeoffs-v3.md`

格式：中文 Markdown、每条事实 `^[文件路径:行号-行号]` 结尾、每项权衡含优化目标/手段/牺牲/源码证据、末尾权衡汇总表。

必须写入文件。
```

### 实际执行方式（重要）

**不是「给一个 agent 一段包含三步骤的提示词让它自己分步执行」。** 三步是分别在 4 个独立 subagent 中执行的，每个有独立上下文，互不知晓。对抗式评审之所以有效，正是因为 Step 2 的评审 agent 完全没有被 Step 1 的思路污染——它独立读源码验证。

详细执行追踪见 `evaluation/execution-trace.md`。中间产物位于 `evaluation/step0-v1-review.md`、`step1-candidates.md`、`step2-review.md`。

### 评估指标设计

**不评估绝对质量（没有 ground truth）。** 评估流程是否有能力发现和修复错误：

1. **错误发现率**：对抗式评审发现多少 ❌/⚠️。v1 baseline 10/10 → v3 修复后应更低
2. **遗漏发现数**：对抗式评审发现候选清单遗漏了多少个应该覆盖的子系统/目录
3. **修复闭环率**：Step 3 中 ⚠️/❌ 成功修复的比例

### 评估结果

| 指标 | v1 | v3 |
|------|-----|-----|
| 事实准确性 | 10/10 | 3→5/5 修复后全对 |
| 覆盖完整性 | 7/10（11 遗漏） | 补全全部 11 遗漏 + 额外发现 hermes_cli 5 条 |
| 自审诚实度 | N/A（无自审） | 不诚实（声称全检查但 hermes_cli 零覆盖） |
| 修复闭环率 | N/A | 100%（8 类问题全部修复） |
| 最终权衡数 | 10 | 30 |

**核心发现**：三步流程有效，但 agent 自审不可靠，必须加独立评审。

---

---

## 第八轮实验：新 `/analyze` 完整流程验证

### 设计

使用修改后的 `schema/dimensions.md` v1.1 + `skills/code-ingest/SKILL.md`。
完整执行 Phase 1（Architecture → Extension Points）→ Phase 2（Performance Tradeoffs + 对抗式评审）。

### 执行方式

5 个独立 subagent 串行执行：

**Phase 1 — Architecture（56 tool uses）**

```
你是代码知识提取 agent。按维度指南提取 Architecture 维度知识。

## 维度指南

维度 1: Architecture。这个维度做什么：描述这个仓库自身的结构——有什么核心抽象、怎么分层的、数据怎么流动。只描述结构，不跨仓库对比，不回答「为什么这样设计」。

提取方式：自己决定读哪些文件形成系统全局理解。列出顶层目录、读入口文件和核心抽象定义、跟踪 import 关系。

## 输出格式
- 中文 Markdown，每条事实 ^[文件路径:行号-行号] 结尾
- 结构：核心抽象逐个 → 分层架构 → 数据流 → 关注点分离
- 不跨仓库对比。不回答「为什么这样设计」。只描述结构。
- 末尾：核心抽象列表（方便后续维度使用）

## 输入源
hermes-agent 源码: /Users/yuanlimiao/Work/agent_harness/hermes-agent/

产出: /tmp/experiment-arch-hermes.md
```

**Phase 1 — Extension Points（45 tool uses）**

```
你是代码知识提取 agent。按维度指南提取 Extension Points 维度知识。

## 维度指南

维度 2: Extension Points。对照 Architecture 产出的核心抽象列表，逐个检查每个子系统是否有扩展机制。只描述扩展机制本身，不评价设计好坏。

提取方式：从 Architecture 核心抽象列表中逐个检查。对每个子系统，寻找接口定义、多实现、注册方法、配置入口。

## Architecture 产出的子系统清单
先读取 /tmp/experiment-arch-hermes.md 获取完整列表，逐个子系统检查。

## 输出格式
- 中文 Markdown，每条事实 ^[文件路径:行号-行号]
- 每个扩展点一个 subsection → 扩展难度梯度
- 只描述扩展机制本身。不评价设计好坏。
- 末尾：扩展点列表（方便后续维度使用）

## 输入源
hermes-agent 源码: /Users/yuanlimiao/Work/agent_harness/hermes-agent/

产出: /tmp/experiment-ext-hermes.md
```

**Phase 2 — 3a 候选清单（41 tool uses）**

```
你是代码知识提取 agent。按维度指南提取 Performance Tradeoffs 维度知识。

## 维度指南
维度 3: Performance Tradeoffs。对照子系统清单，逐个检查是否存在设计权衡。对每项权衡回答：这个子系统的设计与最常规的做法有什么不同？优化了什么？牺牲了什么？为什么这个取舍是可接受的？

## Phase 1 产出（子系统清单来源）
先读取 /tmp/experiment-arch-hermes.md 和 /tmp/experiment-ext-hermes.md，提取完整的子系统清单，逐个子系统检查。

## 输出（两步）
第一步：候选清单。每项格式：序号. 子系统 - 权衡名称 \n 与常规做法的不同/优化了什么/牺牲了什么/证据
第二步：自审。□ 逐个子系统检查了？实际读过的文件：[列出] □ 源码目录未被覆盖？□ 每条有「与常规做法不同」和「牺牲了什么」？□ 所有行号来自实际读取？

## 输入源
hermes-agent 源码: /Users/yuanlimiao/Work/agent_harness/hermes-agent/

产出: /tmp/experiment-perf-candidates.md
```

**Phase 2 — 3b 对抗式评审（60 tool uses）**

```
你是事实核查员。验证以下候选性能权衡清单。

## 被评审内容
文件：/tmp/experiment-perf-candidates.md。先读取全部内容。

## A. provenance 验证
对候选清单中的每一条（不是抽样，全部），回源码验证：
- ✅ 行号正确
- ⚠️ 行号偏移
- ❌ 找不到对应逻辑

## B. 覆盖完整性
从 Architecture + Extension Points 子系统清单中，逐个子系统检查是否被候选清单覆盖。特别注意：hermes_cli/、cron/、tools/approval.py、tools/skills_guard.py、agent/prompt_caching.py

## C. 自审验证
自审 checklist 是否诚实？agent 声称读过的文件路径是否真实？覆盖率宣称是否属实？

产出: /tmp/experiment-perf-review.md
```

**Phase 2 — 3c 修复+写入（16 tool uses）**

```
你收到了事实核查员的评审结果。基于反馈修复问题。

## 你的候选清单: /tmp/experiment-perf-candidates.md
## 评审结果: /tmp/experiment-perf-review.md

根据评审：
1. Provenance 全部正确（22/22 ✅）——不需要修复
2. 补充遗漏：Smart Approval、Skills Guard、Prompt Caching、Tirith Security
3. 诚实标注未覆盖的子系统

产出: experiments/deepwiki-vs-source/llm-output-source/hermes-agent-performance-tradeoffs-final.md
格式：中文、^[文件:行号]、每项含"与常规做法不同"、末尾汇总表
```

### 结果

| 指标 | v1（单次提取） | 新流程 |
|------|--------------|--------|
| 权衡数 | 10 | 26 |
| provenance 准确性 | 10/10 (抽查) | 22/22 (全量) |
| 遗漏 | 11 | 4（全部修复） |
| 每条有「与常规做法不同」 | ❌ | ✅ |
| subagent 数 | 1 | 5 |

### 结论

新流程有效。Architecture + Extension Points 提供覆盖度保证；「与最常规做法不同」提供因果推理引导；对抗式评审提供准确性验证。

---

## 已知的问题

1. **每个 agent 是一个 LLM turn，不存在真正的多次交互。** 真正的 `/analyze` 流程有用户确认和方向引导。实验抹掉了这个回路。
2. **Architecture 维度指南过于开放。** 「What are the core abstractions?」没有告诉 agent 去哪里找。Hermes 实验证明 agent 的页面选择直接决定了能否捕捉到关键洞察（例如跳过了 Memory and Sessions 页面导致漏掉自学习闭环）。
3. **Performance Tradeoffs 维度指南同样过于开放。** 「What has been sacrificed?」没有告诉 agent 应该按子系统逐个检查。三个实验版本发现了几乎完全不重叠的权衡——这不是信息源的问题，是 agent 对「什么算性能权衡」的定义不一致。
