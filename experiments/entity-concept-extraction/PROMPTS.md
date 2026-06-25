# 实验提示词存证

> 实验：Entity + Concept 增量提取新方案  
> 日期：2026-06-16（Phase 1-5）/ 2026-06-17（Concept 增量验证）  
> 分支：feat/experiment-deepwiki-vs-src

---

## 背景与核心假设

**Entity 定义**：有明确边界、架构师或二开工程师会独立查看、独立讨论的单元。两层粒度：仓库级表征（整体是什么）+ 子系统级（内部可定位单元）。Entity 独立提取，无需参考系。

**Concept 定义**：同一设计问题在不同仓库中给出了不同答案。Concept 名称是问题，不是答案（「插件扩展点的契约方式」而非「接口契约式插件」）。

**参考系**：五个维度（Architecture / Extension Points / Performance Tradeoffs / Dependency Strategy / Testing Philosophy）是 Concept 提取的参考系——保证两个仓库都被同一组问题问过，使「同一设计问题」的判断有依据。

**增量逻辑**：种子库持久化积累，每个新仓库进来，对比已有种子库（而非只对比上一个仓库），实现真正的累积增长。

---

## Phase 1 提示词：openclaw Entity 提取

```
你是一个代码仓库知识提取专家。你的任务是从 OpenClaw 代码仓库中提取 Entity（实体）信息。

## 什么是 Entity

Entity 是有明确边界、可以独立讨论的系统单元。判断标准：「一个架构师或二开工程师会为了理解或修改这个单元，而单独查看它吗？」满足这个标准的，才算 Entity。

Entity 有两个层次：
1. **仓库级表征**：这个系统整体是什么，边界在哪里（每个仓库一个）
2. **子系统 Entity**：系统内部满足上述标准的可定位单元（数量不限，按实际情况来）

## 你的输入

主要素材（优先读）：
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/openclaw-overview.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/openclaw-architecture.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/openclaw-extension-points.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/openclaw-performance-tradeoffs.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/openclaw-dependency-strategy.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/openclaw-testing-philosophy.md

补充素材（叙事页信息不足时读）：
- 源码路径：/Users/yuanlimiao/Work/agent_harness/openclaw/

## 你的输出

### 1. 仓库级表征页
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/entity/openclaw-entity.md

格式：
```markdown
# OpenClaw — 系统表征

## 这个系统是什么
（1-2 句话，非专业人士也能理解）

## 核心子系统
- 子系统名：一句话说它做什么 + 边界（不做什么）

## 关键机制
（2-4 个最有辨识度的设计选择，每个 3-5 句话）

## 明确不做什么
（系统边界的反面）
```

### 2. 子系统 Entity 页（每个满足标准的子系统一个文件）
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/entity/openclaw-<subsystem-slug>.md

格式：
```markdown
# <子系统名>（OpenClaw）

## 是什么 / 边界
（这个单元做什么，明确不做什么）

## 关键实现
（核心逻辑、入口文件、关键接口）

## 设计选择记录
- **维度**：<Architecture / Extension Points / Performance Tradeoffs / Dependency Strategy / Testing Philosophy>
- **选择**：<这里实际做的选择，一句话>
- **替代方案**：<没有选择的另一个方向，一句话>
- **为什么有这个选择**：<简要说明，不确定可以标「待确认」>
```
（一个子系统可以有多条设计选择记录）

### 3. 种子库初始化
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/design-seeds.md

把所有子系统页的「设计选择记录」汇总到种子库，每条状态为「仅 openclaw—待观察」。

格式：
```markdown
# 设计选择种子库

> 最后更新：openclaw ingest 完成

---

## <设计问题名>

**维度**：<维度名>  
**问题陈述**：如何...（一句话）

| 仓库 | 选择 | 简述 |
|------|------|------|
| openclaw | <方案名> | <一句话> |

**Concept 状态**：仅 openclaw—待观察
```

## 核心约束

1. **Entity 判断标准是「会独立查看吗」**，不是功能分类或目录结构
2. **设计选择必须是真正的选择**（有替代方案）。「用了 TypeScript」不是选择，「工具权限在消息处理路径上做同步门控而非事后审计」才是选择
3. **每个设计选择必须锚定到五维度之一**
4. **叙事页优先**，源码是补充。如果叙事页已经说清楚，不需要再读源码
```

---

## Phase 2 提示词：hermes Entity 提取

```
你是一个代码仓库知识提取专家。你的任务是从 Hermes Agent 代码仓库中提取 Entity（实体）信息。

## 什么是 Entity

Entity 是有明确边界、可以独立讨论的系统单元。判断标准：「一个架构师或二开工程师会为了理解或修改这个单元，而单独查看它吗？」满足这个标准的，才算 Entity。

Entity 有两个层次：
1. **仓库级表征**：这个系统整体是什么，边界在哪里（每个仓库一个）
2. **子系统 Entity**：系统内部满足上述标准的可定位单元（数量不限，按实际情况来）

## 你的输入

主要素材（优先读）：
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/hermes-agent/hermes-agent-overview.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/hermes-agent/dimensions/hermes-agent-architecture.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/hermes-agent/dimensions/hermes-agent-extension-points.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/hermes-agent/dimensions/hermes-agent-performance-tradeoffs.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/hermes-agent/dimensions/hermes-agent-dependency-strategy.md
- /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/hermes-agent/dimensions/hermes-agent-testing-philosophy.md

补充素材（叙事页信息不足时读）：
- 源码路径：/Users/yuanlimiao/Work/agent_harness/hermes-agent/

## 你的输出

### 1. 仓库级表征页
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/entity/hermes-entity.md

格式（与 openclaw 相同）：
```markdown
# Hermes Agent — 系统表征

## 这个系统是什么
## 核心子系统
## 关键机制
## 明确不做什么
```

### 2. 子系统 Entity 页
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/entity/hermes-<subsystem-slug>.md

格式（与 openclaw 相同，包含「设计选择记录」节）

### 3. 临时设计选择文件（不写入种子库，等 Phase 3 处理）
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/hermes-design-seeds-draft.md

把所有 hermes 子系统的「设计选择记录」汇总到这个临时文件。格式与种子库相同，但不更新种子库本身。

## 核心约束（与 Phase 1 相同）

1. Entity 判断标准是「会独立查看吗」，不是功能分类
2. 设计选择必须是真正的选择（有替代方案）
3. 每个设计选择必须锚定到五维度之一
4. **不要读 openclaw 的任何结果**，独立提取
5. 叙事页优先，源码是补充
```

---

## Phase 3 提示词：种子库合并 + Concept 涌现

```
你是一个跨仓库知识整合专家。你的任务是把两个仓库的设计选择对齐，找出真正的 Concept（跨仓库同一设计问题的不同答案）。

## 你的输入

1. openclaw 种子库：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/design-seeds.md
2. hermes 临时设计选择文件：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/hermes-design-seeds-draft.md
3. 所有 Entity 页（需要时参考细节）：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/entity/

## 什么是 Concept

Concept = 同一设计问题在不同仓库中给出了不同答案。

关键判断：
- **问题陈述相同**：同一维度下，能用一句相同的「如何...」表述
- **答案不同**：两个仓库的选择方向不一样（不只是实现细节不同）
- **都必须面对**：这个问题对这类系统（AI Agent 框架）是普遍的，不是某个仓库特有的

**不是 Concept 的情况**：
- 两个仓库都用了同一个方案（技术共性，不是对比）
- 只有一个仓库面对这个问题（另一个仓库根本没有这个维度）
- 只是实现语言/框架不同，设计选择层面是一样的

## 你的任务

### 第一步：按维度对齐

把 hermes 临时文件里的每个设计选择条目，与 openclaw 种子库里同维度的条目逐一比对：

对于每对候选：
1. 问题陈述是否可以用同一句「如何...」表述？（是 → 继续；否 → 各自是独立条目）
2. 两个仓库的选择方向是否不同？（是 → 候选 Concept；否 → 追加实例）

### 第二步：升级 Concept

对每个候选 Concept，写一个独立的 Concept 页：
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/concept/<concept-slug>.md

格式：
```markdown
# <Concept 名>
（命名为问题形式，如「工具权限的执行时机」，不是答案形式）

## 问题陈述
（这类 AI Agent 框架为什么必须面对这个问题，1-3 句话）

## 已知答案图谱

### 方案 A：<名称>
- 特征：
- 优势：
- 劣势：

### 方案 B：<名称>
- 特征：
- 优势：
- 劣势：

## 跨仓库对比

| | OpenClaw | Hermes Agent |
|---|---|---|
| 选择的方案 | | |
| 具体实现 | | |
| 付出的代价 | | |

## 设计权衡
（什么约束下选 A 更合理，什么约束下选 B 更合理）
```

### 第三步：更新种子库

把 hermes 的所有条目合并进 design-seeds.md：
- 候选 Concept → 标注「已升级」，附 Concept 页链接
- 答案相同 → 追加 hermes 的实例行，状态保持「待观察」
- hermes 独有 → 新增条目，标「仅 hermes—待观察」

## 核心约束

1. Concept 名称是**问题**，不是答案
2. 「两个仓库都用向量检索」不是 Concept；「一个用向量另一个用关键词」才是
3. 必须能说清楚「为什么会有不同选择」——不能只是技术描述的罗列
4. 对比的是设计决策层面，不是实现细节层面
```

---

## Phase 3.5 提示词：交叉审查 + 补充 Concept

```
你是一个跨仓库知识整合审计师。Phase 3 的 Concept 涌现遗漏了重要的跨仓库设计对比（如「工具注册与发现方式」），因为两个仓库的 Entity 提取 subagent 各自覆盖了同一设计问题的不同侧面。

你的任务：用交叉审查的方法，找出所有遗漏的 Concept。

## 你的输入

1. 两个仓库的全部 Entity 页：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/entity/
   - openclaw：entity.md + 9 个子系统页
   - hermes：entity.md + 8 个子系统页
2. 两个仓库的原始维度叙事页：
   - /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/openclaw/dimensions/*.md
   - /Users/yuanlimiao/Work/codebase-wiki/wiki/repos/hermes-agent/dimensions/*.md
3. 当前种子库：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/design-seeds.md
4. hermes 草稿：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/hermes-design-seeds-draft.md
5. 已有 Concept 页：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/concept/

## 交叉审查逻辑

### 第一步：识别共享子系统

找出两个仓库都有的同概念子系统（命名可能不同）。例如：
- openclaw 的「Tool Policy + Channel Plugin 系统」↔ hermes 的「ToolRegistry + ApprovalSystem」
- openclaw 的「Memory 系统」↔ hermes 的「MemoryManager + MemoryProvider」
- openclaw 的「Agent Harness」（LLM 抽象层）↔ hermes 的「AIAgent」（中央编排器）
- openclaw 的「Plugin/Hook 系统」↔ hermes 的「自学习闭环 + SkillsGuard」
- openclaw 的「Context Engine」↔ hermes 的「ContextEngine」

对每个共享子系统，阅读两个仓库的对应 Entity 页和维度叙事页，理解两边的实现方式。

### 第二步：逐子系统比对设计选择

对每个共享子系统，问三个问题：

**问题 1：A 的种子库里有但 B 没有的条目，B 是真的没有面对这个问题，还是面对了但漏提取？**

如果 B 也面对了（不用相同的答案，只要面对了同样的问题），就在 B 这边补充一条设计选择记录。

**问题 2：两个仓库都有的条目，问题陈述是否真的是同一个问题？**
如果不精准对齐，是否有更好的问题陈述可以把两边都套进去？

**问题 3：这个共享子系统是否引入了全新的设计选择，两边都有但都没提取？**
回到维度叙事页重新审视——维度页里是否有隐含的设计选择没有被识别出来。

### 第三步：汇总候选 Concept

对每个补充/修正后形成「同一问题 + 不同答案」的条目对，识别为候选 Concept。

## 特别关注方向

深入检查以下已知遗漏方向（但不限于这些）：

1. **工具注册与发现**：openclaw 有显式 registerTool + channel 插件的注册机制，hermes 有 ToolRegistry + AST 扫描自动发现。这是「工具如何被发现和注册」这一问题的两种不同答案。
2. **工具的使用方式/模型**：两者的工具调用模式有什么异同？以 function-calling 的形式传给 LLM 还是通过其他方式？
3. **技能/扩展的管理**：openclaw 的 Skills Markdown 层 vs hermes 的自学习 skill_manage，这是「如何让用户扩展 agent 能力」的问题。已有 Concept 提到了部分但可能不完整。
4. **扩展点的粒度**：Channel Plugin 的接口粒度（每个 platform 独立实现）vs BasePlatformAdapter（统一 ABC），这是「如何定义平台适配接口」的问题。
5. **消息与 Agent 的绑定方式**：openclaw 的 session binding 方式 vs hermes 的消息聚合去重方式。

## 你的输出

### 1. 新的 Concept 页

对每个新涌现的候选 Concept，按以下格式写入独立文件：
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/concept/<concept-slug>.md

格式（与 Phase 3 相同）：
```markdown
# <Concept 名>（问题形式命名）

## 问题陈述
## 已知答案图谱
### 方案 A：<名称>
特征 / 优势 / 劣势
### 方案 B：<名称>
（同上）
## 跨仓库对比
| | OpenClaw | Hermes Agent |
|---|---|---|
| 选择的方案 | | |
| 具体实现 | | |
| 付出的代价 | | |
## 设计权衡
```

### 2. 更新后的种子库

把交叉审查补充的条目合并进 design-seeds.md。格式与已有条目一致。
路径：/Users/yuanlimiao/Work/codebase-wiki/experiments/entity-concept-extraction/design-seeds.md

### 3. 交叉审查报告

在输出末尾，列明：
- 识别了几个共享子系统
- 每个共享子系统补充了多少条设计选择
- 最终新增了几个 Concept 页
- 哪些已有种子条目的问题陈述被修正了

## 核心约束

1. **双向审查**：A 有的问题问 B 是否也有，B 有的问题也问 A 是否也有
2. **不强行配对**：如果经过审查确认 B 确实没面对这个问题，不要强行补充
3. **回到原素材验证**：每次补充条目必须回到维度叙事页确认有实际内容支撑，不能凭空推断
4. **Concept 名称是问题，不是答案**
5. 如果需要读源码补充细节，源码路径：/Users/yuanlimiao/Work/agent_harness/openclaw/ 和 /Users/yuanlimiao/Work/agent_harness/hermes-agent/
```

---

## Concept 增量验证（2026-06-17）

### 实验设计

- **方法**：备份旧产物 → 清空 concept/ 和 design-seeds.md → 三轮增量模拟
- **Round 1**：openclaw 第一个进入 → 种子库初始化（无 Concept）
- **Round 2**：hermes 第二个进入 → 交叉审查 → per-Concept 写作（含源码验证）→ 独立验证 → 修复 → 种子库更新
- **Round 3**：nanobot 第三个进入 → 同上 + 已有 Concept 更新
- **关键改进**：per-Concept 独立 agent（完整上下文窗口）+ Phase 3b 源码验证 + 种子库溯源列

### Round 1 Phase 1 提示词：openclaw 种子库初始化

```
[见计划文件 Phase 1-R1]
```

### Round 2 Phase 1 提示词：hermes 设计选择草稿

```
[见计划文件 Phase 1-R2]
```

### Round 2 Phase 2 提示词：交叉审查

```
[见计划文件 Phase 2-R2]
```

### Round 2 Phase 3a 提示词：per-Concept 深度写作

```
[见计划文件 Phase 3a-R2]
```

### Round 2 Phase 3b 提示词：Concept 验证

```
[见计划文件 Phase 3b-R2]
```

### Round 2 Phase 3c 提示词：修复

```
[见计划文件 Phase 3c-R2]
```

### Round 2 Phase 3d 提示词：种子库更新

```
[见计划文件 Phase 3d-R2]
```

### Round 3 提示词

```
Round 3 各 Phase 与 Round 2 相同，差异：
- Phase 2 输入包含已有 Concept 页（需要检查追加方案 C）
- Phase 3a 包含两类任务：新 Concept 写作 + 已有 Concept 追加 nanobot 列
```
完整提示词见计划文件 `/Users/yuanlimiao/.claude/plans/functional-tickling-scroll.md`。
