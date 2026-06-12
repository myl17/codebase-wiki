---
node_type: ExtensionPoint
scope: component
concept: Context 压缩
targets: [context-engine]
motivated_by: [compaction-recoverability-priority]
sources:
  - src/plugins/types.ts:1867-1990
extracted_from:
  - extension-points
---

# CompactionProvider

`registerCompactionProvider` 注册压缩/摘要后端，替换 Context 压缩的具体策略（摘要 LLM、chunk 策略）而无需重写 ContextEngine。二开调整压缩行为的最小切入点。
^[src/plugins/types.ts:1867-1990]

<!-- generated-wikilinks -->
## 关联

**设计原因**（motivates）：
- [[openclaw/nodes/design-decisions/compaction-recoverability-priority]] — 该决策催生了此节点

**作用于**（targets）：
- [[openclaw/nodes/components/context-engine]] — 改动会波及此组件

**同属「Context 压缩」的其他仓库实例：**
- [[hermes-agent/nodes/extension-points/context-engine]] — hermes-agent
- [[openclaw/nodes/components/context-engine]] — openclaw
<!-- /generated -->
