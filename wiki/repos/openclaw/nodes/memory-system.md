---
node_type: Component
scope: subsystem
concept_candidate: 可替换记忆后端
sources:
  - src/memory-host-sdk/host/types.ts:1-30
---

# Memory System

`MemorySearchManager` 接口封装向量搜索与语义检索，支持两种 backend：`builtin`（SQLite + sqlite-vec）和 `qmd`（外部引擎）。extensions 层 4 个可选实现（memory-core / memory-lancedb / memory-wiki / active-memory）。记忆在 prompt 组装阶段注入，非实时查询。`registerMemoryCapability` 是 exclusive 槽位，全局只能有一个活跃实现。
^[src/memory-host-sdk/host/types.ts:1-30]
