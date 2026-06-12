---
node_type: Component
scope: subsystem
concept: Context 压缩
motivated_by: [compaction-recoverability-priority]
sources:
  - src/context-engine/index.ts:1-27
extracted_from:
  - architecture
  - extension-points
---

# ContextEngine

管理 prompt 生命周期的四个操作：`assemble`（组装）/ `ingest`（摄入）/ `compact`（压缩）/ `transcriptRewrite`（重写）。支持可注册的 `ContextEngineFactory`（exclusive 槽位，全局只能有一个活跃实现），通过 `LegacyContextEngine` 向后兼容。二开替换上下文策略时实现 factory 并注册即可，不改 core。
^[src/context-engine/index.ts:1-27]

<!-- generated-wikilinks -->
## 关联

**设计原因**（motivates）：
- [[openclaw/nodes/compaction-recoverability-priority]] — 该决策催生了此节点

**被以下扩展点作用于**（被 targets）：
- [[openclaw/nodes/agent-harness]]
- [[openclaw/nodes/channel-plugin]]
- [[openclaw/nodes/compaction-provider]]
- [[openclaw/nodes/hook-system]]
- [[openclaw/nodes/skills-extension]]

**同属「Context 压缩」的其他仓库实例：**
- [[hermes-agent/nodes/context-engine]] — hermes-agent
- [[openclaw/nodes/compaction-provider]] — openclaw
<!-- /generated -->
