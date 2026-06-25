# AIAgent — 中央编排器（Hermes Agent）

## 是什么 / 边界

AIAgent 是 Hermes 的核心编排器，负责执行完整的 tool-calling 对话循环：接收用户消息、构建 system prompt、调用 LLM API、分发工具调用、处理 API 错误和 fallback、委派子 agent。

不做：平台消息收发（由 GatewayRunner + 适配器负责）、工具执行本身（由各工具模块实现）、安全审批决策（由 ApprovalSystem 负责）、记忆存储（由 MemoryManager 负责）。

## 关键实现

- 入口文件：`run_agent.py:535`（11510 行）
- 对话循环入口：`run_agent.py:8130-8189`，`run_conversation()`
- 迭代预算：`IterationBudget`（`run_agent.py:170-199`），线程安全，父/子 agent 独立预算
- 工具分发：`model_tools.handle_function_call()` → `ToolRegistry.dispatch()`
- 并行工具执行：`run_agent.py:214-311`，最大 8 worker 线程
- 管道保护：`_SafeWriter`（`run_agent.py:113-167`），包装 stdout/stderr 防管道破裂

## 设计选择记录

- **维度**：Architecture
- **选择**：AIAgent 作为单一中央编排器，管理完整 tool-calling 循环
- **替代方案**：分散式编排，每个工具模块自行管理 LLM 交互
- **为什么有这个选择**：集中编排使 failover 路由、子 agent 委派、iteration budget 可以在统一地方管理，避免各工具模块重复处理 LLM 协议差异

---

- **维度**：Performance Tradeoffs
- **选择**：并行工具执行（最多 8 线程），但破坏性命令和交互式工具强制串行
- **替代方案**：所有工具调用全部串行执行
- **为什么有这个选择**：只读工具（web_search、read_file 等 11 个）无共享状态，并行可大幅降低延迟；破坏性命令（含 rm/mv/sed -i 等）必须串行以防并发冲突

---

- **维度**：Performance Tradeoffs
- **选择**：Iteration Budget — 默认父 agent 90 轮、子 agent 50 轮硬上限；耗尽时一次 grace call，预算信息不注入 LLM
- **替代方案**：无硬上限，让 LLM 自行判断何时停止；或者在预算耗尽前向模型发出警告
- **为什么有这个选择**：之前注入警告导致模型在预算耗尽前过早放弃任务；无上限会导致复杂任务无限消耗 token
