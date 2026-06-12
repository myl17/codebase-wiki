---
node_type: DesignDecision
scope: subsystem
sources:
  - src/agents/compaction.ts:19-40
extracted_from:
  - performance-tradeoffs
---

# 压缩优先保证可恢复性

Context 压缩时摘要指令优先保留活跃任务状态、批处理进度、最后一次用户请求——优先保证**可恢复性**而非压缩率。`tool_result.details` 在压缩前 strip，防止冗长工具输出污染摘要。代价是牺牲历史细节完整性。
^[src/agents/compaction.ts:19-40]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[openclaw/nodes/extension-points/openclaw-compaction-provider]]
- [[openclaw/nodes/components/openclaw-context-engine]]
<!-- /generated -->
