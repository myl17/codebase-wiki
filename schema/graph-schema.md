# Graph Schema

**Version:** v0.1
**Evolution policy:** First 20 repos — add only, never remove or rename. New edge types require a real query use case. Scope field has an explicit exit condition (see Scope section).

---

## Node Types

每个节点页（`wiki/repos/<name>/nodes/<slug>.md`）的 `node_type` 必须是以下三种之一：

| type | 含义 | 对应受众问题 |
|------|------|-------------|
| `Component` | 系统中可定位的结构单元（子系统/核心抽象/数据结构） | 改这里会波及什么? |
| `ExtensionPoint` | 二开可操作的定制入口（接口/注册机制/钩子/配置项） | 这里怎么扩展? |
| `DesignDecision` | 存在明确因果链的架构选择，影响后续设计 | 为什么这样设计? |

**不入图的类型**（保持叙事文本即可）：
- 函数名、类名、文件路径（实现细节）
- 教科书模式（单例、懒加载、退避——任何仓库都有，汇合无信息量）
- 工具/库名（Vitest、pytest——package.json 可见事实）

---

## 节点的提取与验证（两步分离）

提取宽松、验证收紧。只有通过验证的候选才写入节点页。

### 提取标准（候选阶段，宽松）

- 在维度页中有具名的代码边界（目录/接口/函数）
- 具备三种 node_type 之一的典型结构特征：
  - Component：独立目录 + 入口文件 + 独立职责
  - ExtensionPoint：interface + 多实现 / register* 方法 / hook 签名 / 配置 schema
  - DesignDecision：文档或注释中存在 "选 X 不选 Y 因为 Z" 因果链

### 验证标准（写入节点页前，必须全部通过）

1. **连通性测试**：节点必须有至少一条边（`concept` / `targets` / `motivated_by` 任一非空）。
   孤立节点在图中没有遍历价值，等同于复述维度页内容。
   若一个候选声称自己很重要却找不到任何边，这个矛盾本身提示它不该是节点
   （例：一个"API 总目录"式候选——它是其他 ExtensionPoint 的容器，不是图中节点）。
2. **受众问题测试**：节点必须能直接回答一个具体的受众问题——
   "改这里波及什么？"（Component）/ "这里怎么扩展？"（ExtensionPoint）/ "为什么这样设计？"（DesignDecision）。
   问不出来 = 对图谱无贡献。
3. **去重测试**：节点不能是另一节点的属性。
   （例：某组件的"独占注册槽位"是该 Component 的属性，不是独立 ExtensionPoint。）

---

## Scope

`scope` 描述节点的**替换爆炸半径**，用于 compare 矩阵排序和影响分析输出优先级。不参与连边合法性。

### 核心测试

> **假设把这个节点代表的东西删除或彻底替换，最小重写单元是什么？**

按顺序判定，首个命中即停：

**① `system` —— 满足以下任一条：**
- 位于主数据流的**必经路径**上（每个请求/消息都经过它）
- 约束**某类操作的全部实例**（"所有工具调用"、"所有插件"、"所有模块加载"）
- 是**无法通过接口替换**的依赖（替换 = 重写一层）

**② `subsystem` —— 节点自身是一个有边界的能力单元，同时满足：**
- 有独立目录/包 + 入口文件
- 有注册机制或配置开关控制其启用/替换
- 其他代码只通过接口依赖它
- 删除它 = 失去一项完整能力，但其余能力照常运行

**③ `component` —— 以上都不满足（能力单元内部的一个机制）：**
- 实现局限在单个文件/类
- 删除它 = 某项能力的某个行为退化，能力本身仍在

### 能力单元的定义

判据是代码结构性的，不依赖 repo 文档的自我描述：
能用"这个 repo 能做 X"描述、且在代码里有接口边界（目录 + 入口 + 接口）的单元。

### 常见误判提醒

**"调用了其他子系统"不等于爆炸半径。** 一个调度器调用了任务系统、agent、消息通道，
但删除它只需要重写它自己（其余能力照常）→ 它是 `subsystem`，不是 `system`。
判定问的是"删掉它要重写什么"，不是"它碰到了什么"。

### scope 的价值假设与退出条件

价值假设：(a) 影响分析按 scope 排序输出更有用；(b) 同一 Concept 下不同 repo 实例的
scope 差异是有判别力的对比发现（"这个模式各家做到多深"）。

**退出条件**：到第 5 个仓库回顾时，若 scope 既没有在任何 compare 中产生 scope 差异型发现、
也没有在影响分析排序中体现价值，则删除该字段（派生图架构下删除零成本）。

---

## Edge Types（起步集）

边存储在源节点页的 frontmatter 字段中。`graph.py build` 读取后构建图。

| 边 | frontmatter 字段 | 方向 | 合法源类型 | 合法目标类型 |
|----|-----------------|------|-----------|------------|
| `embodies` | `concept:` | 实例 → Concept | Component, ExtensionPoint | wiki/entities/_index.md 中的 Concept |
| `targets` | `targets:` (list of slugs) | ExtensionPoint → Component | ExtensionPoint | Component |
| `motivates` | `motivated_by:` (list of slugs) | DesignDecision → 节点 | Component, ExtensionPoint | DesignDecision |

**reserved（未来）**：`constrains`（待影响发现查询验证后引入）；`alternative_to`（待有完整 ADR 仓库后引入）。

---

## Concept 准入三问

候选概念须**同时通过**三问才能入 `wiki/entities/_index.md`：

1. **问题测试**：它直接回答某个二开/架构师问题吗？（"怎么扩展？""为什么这样设计？""选型差异在哪？"）
2. **判别测试**：在此锚点上跨仓库汇合，能得出**有差异的结论**吗？还是任何仓库都"有"？
3. **沉淀测试**：其知识需读代码才能获得吗？还是 package.json/README 一眼可见？

ingest 时 LLM 只能在节点页标 `concept_candidate: <名>`，正式入索引须过三问。

---

## 节点页模板

```yaml
---
node_type: ExtensionPoint          # Component | ExtensionPoint | DesignDecision
scope: subsystem                   # system | subsystem | component（替换爆炸半径判定）
concept: 插件系统                   # 省略则该节点无跨仓库对应（仓库特有）
concept_candidate: ""              # 候选 Concept 名（待过三问后正式入索引）
targets:                           # list of node slugs in same repo
  - tool-policy
motivated_by:                      # list of DesignDecision slugs in same repo
  - sync-gating-decision
sources:
  - src/channels/plugins/types.plugin.ts:53-94
---

# <节点名>

一段人话描述：这是什么、怎么用、二开时从哪里切入。
^[src/channels/plugins/types.plugin.ts:53-94]
```

**字段说明**：
- `targets` / `motivated_by` 填同 repo `nodes/` 目录下的文件名（不含 `.md`）
- `concept` 填 `wiki/entities/_index.md` 中已有的 Concept 名，未注册不得填
- `sources` 格式：`<repo 内相对路径>:<起始行>-<结束行>`
