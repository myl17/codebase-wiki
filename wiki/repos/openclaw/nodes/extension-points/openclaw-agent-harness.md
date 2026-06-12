---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [context-engine]
motivated_by: [mariozechner-core-dependency]
sources:
  - src/agents/harness/types.ts:30-44
extracted_from:
  - architecture
  - extension-points
---

# AgentHarness

`AgentHarness` 接口：`supports(ctx)` 做优先级选择，`runAttempt(params)` 执行 LLM 调用，`compact?(params)` 压缩上下文，`reset?(params)` 重置 session。`selectAgentHarness()` 按 priority 排序选择实现。`extensions/` 下各 provider（anthropic/openai/ollama/deepseek）各自注册，对 core 透明。compact 操作委托给 ContextEngine。
^[src/agents/harness/types.ts:30-44]

<!-- generated-wikilinks -->
## 关联

**所属概念：** [[插件系统]]

**设计原因**（motivates）：
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] — 该决策催生了此节点

**作用于**（targets）：
- [[openclaw/nodes/components/openclaw-context-engine]] — 改动会波及此组件

**同属「插件系统」的其他仓库实例：**
- [[hermes-agent/nodes/extension-points/hermes-agent-event-hooks]] — hermes-agent
- [[hermes-agent/nodes/extension-points/hermes-agent-platform-adapter]] — hermes-agent
- [[hermes-agent/nodes/components/hermes-agent-tool-registry]] — hermes-agent
- [[openclaw/nodes/extension-points/openclaw-channel-plugin]] — openclaw
- [[openclaw/nodes/extension-points/openclaw-hook-system]] — openclaw
<!-- /generated -->
