---
node_type: ExtensionPoint
scope: component
concept: 插件系统
targets: [ai-agent]
motivated_by: [ast-autodiscovery-decision]
sources:
  - gateway/hooks.py:9-19
  - gateway/hooks.py:34-80
---

# Event Hooks

生命周期事件系统：`gateway:startup`、`session:start`、`agent:step`、`agent:end` 等事件，hook 通过目录扫描自动加载（与工具自动发现同一哲学）。与 OpenClaw 28 个细粒度 hook 对比：Hermes 事件粒度更粗，覆盖面更窄。
^[gateway/hooks.py:9-19]
