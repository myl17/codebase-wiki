---
node_type: Component
scope: system
motivated_by: [self-learning-loop-decision]
sources:
  - run_agent.py:535-560
  - run_agent.py:8130-8189
extracted_from:
  - architecture
---

# AIAgent

中央编排器（11510 行单文件）：对话循环、工具调用、模型 API 交互、fallback 路由、子 agent 委派。`run_conversation()` 是所有执行路径（CLI / Gateway / Cron）的必经入口，无替换机制——改动波及一切。IterationBudget 提供线程安全的父子 agent 独立迭代预算。
^[run_agent.py:8130-8189]

<!-- generated-wikilinks -->
## 关联

**设计原因**（motivates）：
- [[hermes-agent/nodes/design-decisions/self-learning-loop-decision]] — 该决策催生了此节点

**被以下扩展点作用于**（被 targets）：
- [[hermes-agent/nodes/extension-points/context-engine]]
- [[hermes-agent/nodes/extension-points/event-hooks]]
- [[hermes-agent/nodes/extension-points/memory-provider]]
- [[hermes-agent/nodes/extension-points/platform-adapter]]
<!-- /generated -->
