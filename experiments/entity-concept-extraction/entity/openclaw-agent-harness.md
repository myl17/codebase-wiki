# Agent Harness（OpenClaw）

## 是什么 / 边界

Agent Harness 是 OpenClaw 的 LLM 提供商抽象层：统一包装不同 LLM provider 的调用接口，通过 `selectAgentHarness()` 按优先级选择最合适的实现来处理每次调用。不管理对话上下文（由 Context Engine 负责），不做工具权限判断（由 Tool Policy 负责），不持有会话状态。

## 关键实现

- 接口定义：`src/agents/harness/types.ts`（`AgentHarness` 接口：`supports(ctx)` + `runAttempt(params)` + 可选的 `compact?(params)` + `reset?(params)`）
- 选择逻辑：`selectAgentHarness()` 按 priority 排序，选第一个 `supports()` 返回 true 的实现
- Provider 实现：`extensions/anthropic/`、`extensions/openai/`、`extensions/ollama/`、`extensions/deepseek/` 等各自注册 harness
- 注册入口：`OpenClawPluginApi.registerAgentHarness`
- 核心依赖：`@mariozechner/pi-ai`（176 次 import）、`@mariozechner/pi-agent-core`（164 次 import）、`@mariozechner/pi-coding-agent`（77 次 import）

## 设计选择记录

- **维度**：Dependency Strategy
- **选择**：agent 层深度依赖 `@mariozechner/*` 私有包族（442 处 import，精确锁定 `0.66.1`）
- **替代方案**：自研 LLM transport 和 agent 消息类型，不依赖外部私有包
- **为什么有这个选择**：快速复用成熟 AI agent 引擎，避免重新实现 LLM transport、stream 解析、session 管理等底层能力；代价是替换成本极高，受上游版本节奏约束

---

- **维度**：Extension Points
- **选择**：harness 通过 `supports(ctx)` + priority 排序的策略模式选择实现，而非硬编码 if-else
- **替代方案**：用配置字段明确指定使用哪个 provider
- **为什么有这个选择**：策略模式允许 plugin 自主声明适用场景（特定模型前缀、特定 endpoint 等），core 不需要了解每个 provider 的选择条件；新增 provider 无需修改 core

---

- **维度**：Architecture
- **选择**：`compact?` 和 `reset?` 设计为可选方法，非必须实现
- **替代方案**：所有 harness 实现必须提供完整接口包含压缩和重置
- **为什么有这个选择**：并非每个 LLM provider 都有等价的压缩能力，可选设计让轻量 provider 也能接入而不需要实现完整协议
