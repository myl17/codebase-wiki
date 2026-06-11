---
node_type: ExtensionPoint
scope: component
concept: Context 压缩
targets: [context-engine]
motivated_by: [compaction-recoverability-priority]
sources:
  - src/plugins/types.ts:1867-1990
---

# CompactionProvider

`registerCompactionProvider` 注册压缩/摘要后端，替换 Context 压缩的具体策略（摘要 LLM、chunk 策略）而无需重写 ContextEngine。二开调整压缩行为的最小切入点。
^[src/plugins/types.ts:1867-1990]
