# Codebase-Wiki 后续执行方案

> 2026-06-13 | 基于 Karpathy 原文重读 + 认知模型对齐 + 当前实现状态

---

## 〇、核心共识

### Karpathy 的人机分工（不是可靠性分级）

> The LLM owns this layer entirely. You read it; the LLM writes it.
> The human's job is to curate sources, direct the analysis, ask good questions, and think about what it all means. The LLM's job is everything else.

| | 人 | LLM |
|------|-----|-----|
| **角色** | 策展来源、引导方向、提出好问题、思考意义 | 写一切：总结、提取、分类、交叉引用、标记冲突 |
| **动作** | 「这部分再展开」「我想比较 A 和 B」「这个方向值得深挖」 | 自主完成一轮工作，告诉人做了什么、发现了什么、建议下一步 |

**不是**人批准 LLM 的每一步产出。**是** LLM 写、人读、人给方向、LLM 继续。

### 管线结构

```
Source
  │
  ▼
Summary  ←── 必须第一步：维度提取，理解仓库
  │
  ▼
Entity + Concept  ←── 依赖 Summary，提取对象 + 归并抽象
  │
  ▼
Insights  ←── 按需触发：Comparison / Overview / Synthesis
              共享同一套生成机制，只是触发条件不同
```

前半段是顺序依赖（没理解仓库就没法提取），后半段是按需触发（不是管道里的固定下一站）。

### 五个维度的意义

不是「产出维度页给人读」，而是**同一组问题问每个仓库，保证每个仓库被同样深度的目光看过**。这样后续做任何跨仓库操作，素材在源头上就是可比的。

---

## 一、当前状态

```
✅ Source → Summary（/analyze 的维度提取）
✅ Summary → Entity（Component + ExtensionPoint 节点提取）
✅ Entity → Concept（embodies 边 + _index.md 索引表）

⚠️ Concept 页内容只有定义+实例列表，知识没有真正整合进去
⚠️ Entity 间对比（/compare 做了基本版，维度矩阵）

❌ Concept 间对比（如 Pipeline门控 vs 异步审计）
❌ Overview（领域全景）
❌ Synthesis（推导性结论）
❌ 自动化归一化管线
❌ 增量维护

需要回退：
  🗑 DesignDecision 节点类型 — 不是 Karpathy 的原型，是我们自建的梯子，
     内容应留在维度叙事中，被 Concept 页消费时自然引用
```

---

## 二、Entity 节点类型：只保留两种

### Component — 「这是什么」

系统中可定位的结构单元。有明确的代码边界（目录/文件/类）。

- 提取方式：代码结构扫描（目录、类层次、import）
- 例子：Gateway、ContextEngine、ToolPolicy、MemoryProvider
- 受众问题：「改这里会波及什么？」

### ExtensionPoint — 「怎么改/怎么扩展」

二开可操作的定制入口。存在明确的接口、注册机制、配置项或钩子。

- 提取方式：模式匹配（interface + 多实现、register* 方法、hook 签名）出候选，人工确认
- 例子：ChannelPlugin、ExecApprovalRequest、AgentHarness 接口
- 受众问题：「这里怎么扩展？」

### DesignDecision：不再作为独立节点类型

「选 X 不选 Y 因为 Z」在我们的认知模型里不是 Entity——它没有可指代的对象边界。它是理解代码仓库过程中的**梯子**——帮我们从代码事实爬上设计意图。梯子用完，内容已经在了：
- 维度叙事中记录了因果链
- Concept 页面写「实现范式」和「设计权衡」时自然会引用

这些内容不消失，只是不再以独立节点页的形式存在。现有 DesignDecision 节点页的内容回流到对应维度页，或在 Concept 升级时作为素材消费。

---

## 三、Concept 页面：知识整合的主战场

### 当前状态 vs 目标状态

**当前**（存根）：
```markdown
# 插件系统
定义：允许通过注册机制扩展系统功能
实例：openclaw:channel-plugin, hermes-agent:tool-registry
```

**目标**（知识页）：
```markdown
# 插件系统

## 为什么存在
...

## 实现范式
### 接口契约式
特征 / 优势 / 劣势 / 实例：OpenClaw ChannelPlugin、Hermes ToolRegistry

### 约定目录式
特征 / 优势 / 劣势 / 实例：（暂无）

## 实例对比
| | OpenClaw | Hermes Agent |
|---|---|---|
| 注册方式 | PluginApi.register*() 25个方法 | ToolRegistry 静态注册 |
| 生命周期Hook | 28个 | 0个 |
...

## 设计权衡
- 接口契约式：类型安全但灵活性受限
- 约定目录式：灵活但缺编译期检查
```

### Concept、Comparison、Synthesis 是深度光谱，不是三种页面类型

```
薄 ──────────────────────────────────→ 厚

Concept 页的对比表    Comparison 分析     Synthesis 推导
「它们哪里不同」      「为什么会有这种不同」 「所以这意味着什么规律」
事实聚合              有论点               有推论
LLM 自主更新           LLM 提案+人引导方向   人主导思考
```

一个页面往往三层混在一起。不需要在实现层面强行分开——它们共享同一套生成机制：LLM 从 Entity + Concept 素材中按需生成叙事页面。

### 触发方式

- **自动**：ingest 新 repo 后，涉及 Concept 的实例列表和对比表自动更新
- **人引导**：人在 Obsidian 中读到某 Concept 页，说「这里值得对比一下」「这个方向深挖」
- **LLM 建议**：完成一轮工作后告诉人发现了什么、建议下一步（「Concept X 下已有 3 个实例且差异显著，建议对比」）

---

## 四、Insight 生成：统一的知识组织机制

Comparison、Overview、Synthesis 共享同一套生成方式：

```
触发（人提问 / LLM 建议 / 自动检测）
  → LLM 读相关素材（Entity 页 + Concept 页 + 维度叙事）
  → 生成叙事页面
  → 存到 wiki/insights/，用 frontmatter type 标注偏向
```

| type | 触发条件 | 核心问题 |
|------|---------|---------|
| `comparison` | 人：「比较 X 和 Y」；Concept ≥ 3 实例且差异显著 | 「它们哪里不同、为什么」 |
| `overview` | category ≥ 3 repo；人：「这个领域全景怎么样」 | 「这个领域有什么、缺什么」 |
| `synthesis` | 人主导：「为什么 X」「这意味着什么」 | 「所以真正重要的规律是什么」 |

不是三个独立 skill，是一个 `/insight` 操作，`type` 只是标注偏向。

---

## 五、执行路线图

### 第 1 步：回退 DesignDecision

- 现有 DesignDecision 节点页内容回流到对应维度页，或在 Concept 升级时作为素材引用
- graph.py 的 node_type 从三种改为两种（Component、ExtensionPoint）
- graph-schema.md、lint.py 中相关规则同步修改

### 第 2 步：Concept 页面补全（知识整合）

- 为 4 个已注册 Concept 写完整知识页（为什么存在 / 实现范式 / 实例对比 / 设计权衡）
- `/analyze` 完成后自动更新涉及 Concept 页的实例列表和对比表
- 设计 Concept 页面的 generated section 机制（自动更新部分不覆盖手写内容）
- `/concept --deepen` 做深化归纳（LLM 提案，人引导方向）

### 第 3 步：Insight 生成机制

- 新建 `/insight` 操作：统一 Comparison / Overview / Synthesis 的生成流程
- `/analyze` 收尾加入触发检测：category ≥ 3 repo → 建议 Overview；Concept ≥ 3 实例且差异显著 → 建议 Comparison
- 复用现有 `wiki/insights/` 目录和 insight 页面机制

### 第 4 步：自动化归一化 + 增量维护

- matchers.yaml 规则匹配
- Embedding 索引 + ANN 检索（节点量级小，JSON + 暴力 cosine 即可）
- LLM 终判 + 低置信度升级人
- Delta → 边失效检测
- 新 Concept 回溯存量 repo

---

## 六、怎么开始

1. **回退 DesignDecision**（最小改动，清理认知模型）
2. **选一个 Concept 手写黄金标准**（「插件系统」实例最多），然后让 LLM 按模板补全其余 3 个
3. **跑通一次完整的知识整合流程**：读维度叙事 + Entity 节点 → 写 Concept 知识页 → 人读、给方向 → LLM 继续深化
