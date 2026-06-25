# AgentRunner（nanobot）

## 是什么 / 边界
nanobot 的共享执行引擎——一个纯 tool-calling 循环，从 AgentLoop 中提取出来实现产品层零耦合。接受 `AgentRunSpec` 纯数据配置，不 import channel、session、cron 等任何产品层模块。只做一件事：接收 messages → 调用 LLM → 执行 tool_calls → 循环或返回。

**边界**：AgentRunner 不拥有任何产品层上下文（不知道 channel 类型、不知道会话状态、不知道自己在为主 agent 还是子 agent 还是 Dream 服务）。所有产品层逻辑在 AgentLoop 层处理完毕后才将 messages 传入。

## 关键实现
- **`run(spec)` 循环**：`for iteration in range(spec.max_iterations)`，每次迭代执行四步上下文治理 → LLM 调用 → tool 执行
- **四层上下文治理**（在调用 LLM 前自动执行）：
  1. `_backfill_missing_tool_results()` — 扫描孤立 tool_use，插入合成错误结果
  2. `_microcompact()` — 10 轮次前的 tool result 替换为 `[tool result omitted from context]`
  3. `_apply_tool_result_budget()` — 单结果截断至 `max_tool_result_chars`，超限内容持久化到文件
  4. `_snip_history()` — 按 token 预算从尾部裁剪，边界对齐到 user-turn
- **三类使用场景**：主 agent（AgentLoop._run_agent_loop()）→ 子 agent（SubagentManager._run_subagent()）→ Dream Phase 2 记忆处理
- **tool error 策略**：默认 non-fatal（记录错误继续），子 agent 中为 fatal（立即终止）

## 设计选择记录
- **维度**：Architecture
- **选择**：AgentRunner 完全产品层无关——不持有 channel/session/cron 引用，只接受 messages 和 tool_registry 作为纯数据输入
- **替代方案**：执行引擎感知产品层上下文（如 openclaw 的 gateway-aware runner），允许根据 channel 类型或 session 状态调整行为
- **为什么有这个选择**：牺牲产品层感知能力，换取引擎的零修改复用——同一个 AgentRunner 实例同时服务于主 agent、子 agent、Dream 三种场景。上下文治理也因此可以统一实现，不因场景不同而需要分支逻辑
