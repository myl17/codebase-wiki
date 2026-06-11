---
node_type: ExtensionPoint
scope: subsystem
concept: Context 压缩
targets: [ai-agent]
sources:
  - agent/context_engine.py:32-60
---

# ContextEngine

上下文压缩策略扩展点：实现 `ContextEngine` ABC 放入 `plugins/context_engine/<name>/`（策略模式），决定何时以及如何压缩对话上下文。内置 Compressor / LCM 两种实现。
^[agent/context_engine.py:32-60]
