---
node_type: Component
scope: subsystem
concept: 插件系统
motivated_by: [ast-autodiscovery-decision]
sources:
  - tools/registry.py:100-159
extracted_from:
  - architecture
  - extension-points
---

# ToolRegistry

单例工具注册中心（RLock 线程安全），收集工具 schema + handler，支持 MCP 动态刷新。所有工具调用经 `model_tools.handle_function_call()` → `ToolRegistry.dispatch()` 分发。
^[tools/registry.py:100-159]

<!-- generated-wikilinks -->
## 关联

**设计原因**（motivates）：
- [[hermes-agent/nodes/ast-autodiscovery-decision]] — 该决策催生了此节点

**被以下扩展点作用于**（被 targets）：
- [[hermes-agent/nodes/toolset-system]]

**同属「插件系统」的其他仓库实例：**
- [[hermes-agent/nodes/event-hooks]] — hermes-agent
- [[hermes-agent/nodes/platform-adapter]] — hermes-agent
- [[openclaw/nodes/agent-harness]] — openclaw
- [[openclaw/nodes/channel-plugin]] — openclaw
- [[openclaw/nodes/hook-system]] — openclaw
<!-- /generated -->
