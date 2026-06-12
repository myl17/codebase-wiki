---
node_type: ExtensionPoint
scope: subsystem
concept_candidate: 可替换记忆后端
targets: [ai-agent]
sources:
  - agent/memory_manager.py:1-27
---

# MemoryProvider

记忆后端扩展点：实现 `MemoryProvider` ABC 放入 `plugins/memory/<name>/` 即可接入（Honcho/Mem0/Supermemory 等 7 种）。约束：最多 1 个外部 provider，BuiltinMemoryProvider 始终启用不可移除，外部 provider 是加性的不替代内置存储。与 OpenClaw 的 exclusive 槽位（替换式）形成对比。
^[agent/memory_manager.py:1-27]

<!-- generated-wikilinks -->
## 关联

**作用于**（targets）：
- [[hermes-agent/nodes/ai-agent]] — 改动会波及此组件
<!-- /generated -->
