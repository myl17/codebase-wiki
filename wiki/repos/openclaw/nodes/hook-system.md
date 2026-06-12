---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [context-engine, tool-policy]
sources:
  - src/plugins/hook-types.ts:55-84
  - src/plugins/hook-types.ts:128-133
---

# Hook System

28 个生命周期 hook（`before_prompt_build`、`llm_input`、`llm_output`、`before_tool_call`、`session_start` 等），通过 `registerHook(events, handler)` 注册。Prompt 注入类 hook（`before_prompt_build`、`before_agent_start`）允许 plugin 在 LLM 调用前修改 system prompt——是 active-memory 和记忆注入的入口。二开拦截任意生命周期阶段的首选切入点。
^[src/plugins/hook-types.ts:55-84]

<!-- generated-wikilinks -->
## 关联

**作用于**（targets）：
- [[openclaw/nodes/context-engine]] — 改动会波及此组件
- [[openclaw/nodes/tool-policy]] — 改动会波及此组件

**同属「插件系统」的其他仓库实例：**
- [[hermes-agent/nodes/event-hooks]] — hermes-agent
- [[hermes-agent/nodes/platform-adapter]] — hermes-agent
- [[hermes-agent/nodes/tool-registry]] — hermes-agent
- [[openclaw/nodes/agent-harness]] — openclaw
- [[openclaw/nodes/channel-plugin]] — openclaw
<!-- /generated -->
