---
node_type: Component
scope: subsystem
concept: 插件系统
motivated_by: [ast-autodiscovery-decision]
sources:
  - tools/registry.py:100-159
---

# ToolRegistry

单例工具注册中心（RLock 线程安全），收集工具 schema + handler，支持 MCP 动态刷新。所有工具调用经 `model_tools.handle_function_call()` → `ToolRegistry.dispatch()` 分发。
^[tools/registry.py:100-159]
