---
node_type: DesignDecision
scope: subsystem
sources:
  - tools/registry.py:28-73
---

# AST 扫描自动发现工具

进程启动时通过 AST 扫描自动发现所有 `registry.register()` 调用，而非手动维护工具清单。新增工具只需在文件中写注册调用，零额外接线；代价是启动时 AST 解析开销，且注册必须是静态可发现的顶层调用。同样的自动发现哲学也用于 hooks（目录扫描）和 skills（双同步）。
^[tools/registry.py:28-73]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[hermes-agent/nodes/event-hooks]]
- [[hermes-agent/nodes/tool-registry]]
<!-- /generated -->
