# 实验：Source Code vs DeepWiki — 维度提取质量对比

> 日期：2026-06-14 | 分支：feat/experiment-deepwiki-vs-src | 仓库：openclaw / hermes-agent / codex | 维度：Architecture

---

## 一、实验动机

codebase-wiki 的 `/analyze` 流程是 LLM 直接读源码 → 写维度页。我们想验证：

1. 如果输入源换成 DeepWiki（已预解析的代码知识），产出的维度页质量会不会更高？
2. DeepWiki 是否值得作为 codebase-wiki 的固定输入层？

---

## 二、实验设计

### 控制变量（完全相同）

- 同一个维度指南：`schema/dimensions.md` Dimension 1 (Architecture)
- 同一个输出格式：中文 Markdown + `^[文件:行号-行号]` provenance + 结构（核心抽象 → 分层 → 数据流 → 关注点分离 → 关联）
- 同一种探索自由度：agent 自己决定读什么，不限定具体文件/页面列表
- 同一个 LLM：Claude general-purpose subagent，独立上下文窗口

### 唯一变量

| Path | 输入源 | 提示 |
|------|--------|------|
| **A (Source)** | 源码目录（`/Users/yuanlimiao/Work/agent_harness/<repo>/`） | 「自己决定读哪些文件，广泛探索直到全面理解」 |
| **B (DeepWiki)** | DeepWiki MCP 预解析内容（65-79 页，800K-1MB） | 「自己决定读哪些页面，广泛探索直到全面理解」 |

### 两种提示的核心差异

```
Source: 先列出目录 → 读入口文件 → 跟踪 import → 搜索关键词 → 读任何相关文件
DeepWiki: grep "# Page:" 列出页面 → 选择与 Architecture 相关的 → 分段读取
```

**没有给 Source agent 指定文件列表。** 修正了第一轮实验的错误（人为限定 9 个文件）。

### 参与实验的版本

| 对比组 | 说明 |
|--------|------|
| Wiki 现有版 | `/analyze` 完整流程（LLM 读源码 → 草稿 → 人工确认 → 写入），**仅供参考，不是实验组** |
| Source 实验版 | subagent 独立上下文，一次性穷尽可能，无人交互 |
| DeepWiki 实验版 | subagent 独立上下文，一次性穷尽可能，无人交互 |

---

## 三、实验结果

### 3.1 OpenClaw（TypeScript monorepo，100+ 扩展包，多平台客户端）

| 版本 | 大小 | 行数 | provenance | 抽象数 |
|------|------|------|-----------|--------|
| Wiki 现有 | 7.0K | 97 | 13 | 9 |
| Source 实验 | 20.6K | 261 | 48 | 10（12 层） |
| DeepWiki 实验 | 33.8K | 343 | 133 | 8（5 层） |

**Source 优于 DeepWiki**：
- 架构边界规则（CLAUDE.md/AGENTS.md 中的设计约束：禁止硬编码扩展 ID、Plugin SDK 唯一公共契约）
- 分层更细（12 层 vs 5 层），每层有明确源码位置
- Plugin SDK 作为独立抽象（70+ 细粒度子路径导出）

**DeepWiki 优于 Source**：
- 设备节点层（iOS/Android NodeRuntime、TalkMode）
- 沙箱层（Docker/OpenShell/Crabbox 隔离）
- 协议层（Gateway Protocol v4、代码自动生成）
- 原生客户端（macOS/iOS/Android apps）
- 子 Agent 编排流、原生节点调用流
- 跨仓库对比关联（Gpt-Corpuse、DataMaid、CosyVoice）

**Source 遗漏的原因**：这些内容在 `apps/`、`scripts/` 目录中，与 `src/` 核心没有 import 连接。单 agent turn 的探索半径无法覆盖。

### 3.2 Hermes Agent（Python 项目，根目录核心）

| 版本 | 大小 | 行数 | provenance | 抽象数 |
|------|------|------|-----------|--------|
| Wiki 现有 | 15.9K | 269 | 33 | 14 |
| Source 实验 | 18.0K | 321 | 29 | 9 |
| DeepWiki 实验 | 18.7K | 252 | 75 | 8 |

**DeepWiki 的边际提升仅 4%。** 三者差距不大。

**Wiki 独有（人工参与价值）**：
- 自学习闭环（MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE 三条驱动指令）
- 与 OpenClaw 的关键差异分析
- 设计模式显式命名（适配器、策略、单例、Observer）

**DeepWiki 独有**：
- BaseEnvironment 抽象（6 种后端：local/docker/ssh/modal/daytona/singularity）
- 跨框架定位（vs LangChain、vs CrewAI/AutoGen）
- 渐进式技能披露（Tier 0/1/2）

**关键发现**：两个实验 agent **都没有捕捉到自学习闭环**。DeepWiki 有 Memory and Sessions、Skills System 页面包含此信息，但 DeepWiki agent 没有选择读这些页面——在它的判断里 Memory 和 Skills 不是"架构"相关页面。**Agent 的页面选择决定了能否捕捉到关键洞察。**

### 3.3 Codex（Rust + TypeScript monorepo，120+ crate）

| 版本 | 大小 | 行数 | provenance | 抽象数 |
|------|------|------|-----------|--------|
| Source 实验 | 22.2K | 332 | 61 | 7 |
| DeepWiki 实验 | 17.8K | 280 | 30 | 10 |

**Source 反而更大（+25%）。** 这是唯一 Source > DeepWiki 的仓库。

**Source 优于 DeepWiki**：
- 10 种 Extension Contributor trait 完整列表
- core 瘦身原则（AGENTS.md 中的架构纪律：抵制向 core 添加新代码）
- ContextManager 的 8 种 contextual fragment 注入

**DeepWiki 优于 Source**：
- SessionTask trait 多态（RegularTask/ReviewTask/CompactTask/UserShellCommandTask）
- ThreadManager 生命周期（spawn/resume/fork）
- SQLite 四库分离持久化（state_5/logs_2/goals_1/memories_1）
- 多 Agent 树形架构（AgentControl + AgentRoleConfig）
- ModelsManager TTL + ETag 缓存

---

## 四、综合分析

### 4.1 DeepWiki 的真实价值

**不是「产出的质量更高」，而是「读到的内容半径更大」。**

单 agent turn 的探索半径有天然上限——一个 agent 不管怎么自由探索，都不会发现：
- `apps/android/` 里有 NodeRuntime 和 TalkMode（没有 import 线索指向它）
- 120 个 crate 中 SessionTask trait 的多态分布在 `tasks/mod.rs`、`tasks/regular.rs`、`tasks/review.rs`、`tasks/compact.rs` 四个文件里

DeepWiki 的预解析已经完成了**全仓库扫描**这一单 agent turn 不可能完成的工作。

### 4.2 DeepWiki 的盲区

**DeepWiki 是描述性的，不是分析性的。** 它的盲区：

1. **架构纪律**（CLAUDE.md/AGENTS.md 中的设计约束）：Codex 的「抵制向 core 添加新代码」、OpenClaw 的「禁止硬编码扩展 ID」
2. **设计意图**：为什么 Plugin SDK 要 70+ 子路径？为什么 ContextManager 有 8 种 fragment？
3. **接口级细节**：Contributor trait 的完整列表、AgentHarness.supports() 的优先级竞争

这些必须从源码注释、AGENTS.md、CLAUDE.md 中读取。DeepWiki 的描述性文档里没有。

### 4.3 对 Concept 提取的影响

Wiki 现有版虽然最小，但最利于 Concept 提取——它包含：
- 设计模式显式命名
- 与另一个仓库的关键差异
- 仓库最独特的架构特征

实验版本更详细，但缺少这种「结构感」。

### 4.4 实验局限性

1. **没有人工交互**。真正的 `/analyze` 流程有「草稿 → 用户确认 → 深化」的反馈回路。实验 agent 只是一次性穷尽可能。
2. **只测了 Architecture 维度**。Extension Points 和 Performance Tradeoffs 维度可能对 DeepWiki 的依赖程度不同。
3. **agent 页面选择偏差**。Hermes 实验证明 agent 的页面选择决定了能否捕捉到关键洞察。如果把维度指南改成「必须探索 Memory、Skills、Hooks 等非传统架构页面」，DeepWiki 的实验结果可能会不同。
4. **只测了 3 个仓库**。样本太小，无法得出统计结论。

---

## 五、结论与建议

### 引入 DeepWiki 的决策矩阵

| 仓库特征 | 是否启用 DeepWiki | 原因 |
|---------|------------------|------|
| 复杂 monorepo（多目录、多包、扩展目录与核心无 import 连接） | **启用** | 单 agent turn 无法完成全局探索。DeepWiki 是唯一能在一个 turn 里给出全貌的方法 |
| 简洁项目（单一语言、核心在根目录、模块边界明确） | **不启用** | Hermes 证明了 Source 自己就能覆盖到位。边际提升 < 5% |
| DeepWiki 未索引的仓库 | **不可用** | 只有被访问过的仓库才有内容 |

### 优化优先级

1. **P0：改 `/analyze` prompt。** 从「草稿→确认即停」改成「穷尽探索→人选 2-3 点深挖→agent 定向深入」。Source 实验对 OpenClaw (+195%) 的提升证明了单独改 prompt 就有显著收益。不改 prompt 就引入 DeepWiki 是本末倒置。
2. **P1：对复杂 monorepo 启用 DeepWiki 预扫描。** 作为 `/analyze` 的可选 Step 1.5，无成本（公开仓库 MCP 免费）。
3. **不要纯用 DeepWiki 替代 Source。** Codex 证明了 DeepWiki 会漏掉架构纪律和接口级细节。两者互补，不是替代。
4. **不要对所有仓库统一启用。** 简洁项目的边际收益可忽略。
