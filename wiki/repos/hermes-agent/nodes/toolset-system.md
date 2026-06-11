---
node_type: ExtensionPoint
scope: component
targets: [tool-registry]
sources:
  - tools/toolsets.py:1-30
---

# Toolset System

将工具按功能分组为可组合 Toolset，按需启用/禁用整组工具（如 ACP Adapter 专用 toolset 牺牲功能完备度换专注）。二开通过定义新 Toolset 控制 agent 能力面，独立于单个工具定义。
^[tools/toolsets.py:1-30]
