---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [context-engine]
motivated_by: [mariozechner-core-dependency]
sources:
  - src/agents/harness/types.ts:30-44
---

# AgentHarness

`AgentHarness` 接口：`supports(ctx)` 做优先级选择，`runAttempt(params)` 执行 LLM 调用，`compact?(params)` 压缩上下文，`reset?(params)` 重置 session。`selectAgentHarness()` 按 priority 排序选择实现。`extensions/` 下各 provider（anthropic/openai/ollama/deepseek）各自注册，对 core 透明。compact 操作委托给 ContextEngine。
^[src/agents/harness/types.ts:30-44]
