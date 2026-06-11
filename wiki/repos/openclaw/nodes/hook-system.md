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
