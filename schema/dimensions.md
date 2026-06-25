# Codebase Extraction Dimensions

**Version:** v1.1  
**Evolution policy:** First 20 repos — add only, never modify existing dimensions. New dimensions leave existing repos with `status: pending`.

---

## 维度依赖与执行顺序

维度提取按认知层级分为两阶段：

```
Phase 1（图示层 — 结构性事实，可客观提取）:
  1. Architecture → 2. Extension Points
  
Phase 2（图示→心智模型 — 因果推理，依赖 Phase 1 产出）:
  3. Performance Tradeoffs
  4. Dependency Strategy
  5. Testing Philosophy
```

**Architecture 必须第一个完成。Extension Points 必须第二个完成。** Phase 1 产出的核心抽象列表 + 扩展点列表 = 后续所有维度的子系统检查清单。

Phase 2 的三个维度可按任意顺序，但每个维度必须**逐个子系统检查** Phase 1 清单中的每个条目，不允许在没有读对应源码的情况下标注「未发现」。

---

## Phase 1: 图示层

### Dimension 1: Architecture

**这个维度做什么**：描述这个仓库自身的结构——有什么核心抽象、怎么分层的、数据怎么流动。**只描述结构，不跨仓库对比，不回答「为什么这样设计」。**

- What are the core abstractions? (component, module, entity, layer)
- Data flow direction? (unidirectional / bidirectional / event-driven)
- How is concern separation achieved? Where are layer boundaries?

**提取方式**：自己决定读哪些文件形成系统全局理解。列出顶层目录、读入口文件和核心抽象定义、跟踪 import 关系。

### Dimension 2: Extension Points

**这个维度做什么**：对照 Architecture 产出的核心抽象列表，逐个检查每个子系统是否有扩展机制。描述扩展接口、Hook 签名、注册协议、扩展难度梯度。**只描述扩展机制本身，不评价设计好坏。**

- Does a plugin system exist? Where is the entry file?
- Where are hooks / middleware / interceptors designed?
- Which layer is the easiest entry point for framework customization?
- Is there an official extension protocol (interfaces / types / conventions)?

**提取方式**：从 Architecture 核心抽象列表中逐个检查。对每个子系统，寻找接口定义、多实现、注册方法、配置入口。

---

## Phase 2: 图示 → 心智模型

Phase 2 的三个维度**共享同一个工作方式**：

1. 获取 Architecture + Extension Points 产出的子系统清单
2. 逐个子系统检查，读源码
3. 对每个子系统：不只描述机制，要问「这个设计与最常规/最显然的做法有什么不同？为什么做了这个选择？」

### Dimension 3: Performance Tradeoffs

- 对照子系统清单，逐个检查是否存在设计权衡
- 对每项权衡回答：这个子系统的设计与最常规的做法有什么不同？优化了什么？牺牲了什么？为什么这个取舍是可接受的？
- Where in the code is the tradeoff visible? (specific file and lines)

### Dimension 4: Dependency Strategy

- 对照 Architecture 产出的核心依赖列表，逐个检查替换成本和版本策略
- Attitude toward external dependencies? (minimize / embrace ecosystem / in-house)
- Replaceability of core dependencies? Is the replacement cost high?
- Are there peer dependency or optional dependency designs?

### Dimension 5: Testing Philosophy

- 对照 Architecture 产出的子系统目录结构，检查每个子系统的测试模式
- Ratio of unit / integration / e2e tests?
- Does testing target behavior or implementation details?
- Any specialized test tooling or test conventions?

---

## Adding New Dimensions

Add a new `## Dimension N: <Name>` section here. Bump `dimensions_version` in `.manifest.json` by minor version. For repos already analyzed, `manifest.py` will mark the new dimension as `pending`.
