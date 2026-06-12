---
node_type: ExtensionPoint
scope: component
concept: 插件系统
targets: [ai-agent]
motivated_by: [ast-autodiscovery-decision]
sources:
  - gateway/hooks.py:9-19
  - gateway/hooks.py:34-80
extracted_from:
  - architecture
  - extension-points
---

# Event Hooks

生命周期事件系统：`gateway:startup`、`session:start`、`agent:step`、`agent:end` 等事件，hook 通过目录扫描自动加载（与工具自动发现同一哲学）。与 OpenClaw 28 个细粒度 hook 对比：Hermes 事件粒度更粗，覆盖面更窄。
^[gateway/hooks.py:9-19]

<!-- generated-wikilinks -->
## 关联

**设计原因**（motivates）：
- [[hermes-agent/nodes/design-decisions/ast-autodiscovery-decision]] — 该决策催生了此节点

**作用于**（targets）：
- [[hermes-agent/nodes/components/ai-agent]] — 改动会波及此组件

**同属「插件系统」的其他仓库实例：**
- [[hermes-agent/nodes/extension-points/platform-adapter]] — hermes-agent
- [[hermes-agent/nodes/components/tool-registry]] — hermes-agent
- [[openclaw/nodes/extension-points/agent-harness]] — openclaw
- [[openclaw/nodes/extension-points/channel-plugin]] — openclaw
- [[openclaw/nodes/extension-points/hook-system]] — openclaw
<!-- /generated -->
