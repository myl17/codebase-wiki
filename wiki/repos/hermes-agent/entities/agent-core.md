---
type: entity
repo: hermes-agent
slug: agent-core
problem: 如何编排 AI Agent 的主循环，协调消息接收、上下文构建、LLM 调用、工具执行和流式响应
generated: 2026-06-25
source_files:
  - run_agent.py
  - agent/error_classifier.py
  - agent/model_metadata.py
  - agent/usage_pricing.py
---

# Agent 核心循环

**代码位置**：`run_agent.py`、`agent/` 包
**这个模块解决什么问题**：
- 实现层：AIAgent 类驱动完整的 tool-use LLM 循环，管理会话、上下文、工具执行、流式输出和错误恢复，并自动检测 API 模式（chat completions / anthropic messages / bedrock converse / codex responses）
- 问题层：如何编排 AI Agent 的主循环，协调消息接收、上下文构建、LLM 调用、工具执行和流式响应
**对外暴露什么**：`AIAgent` 类（run_agent.py:535）、`IterationBudget`（run_agent.py:170）、`classify_api_error()` / `FailoverReason`（agent/error_classifier.py）
**它和谁交互**：
- 依赖 [[entities/tool-registry]]（通过 model_tools.py 获取工具定义和执行工具调用）
- 依赖 [[entities/context-compressor]]（上下文压缩治理）
- 依赖 [[entities/prompt-builder]]（组装系统提示词）
- 依赖 [[entities/memory-system]]（持久内存和用户画像）
- 依赖 [[entities/model-adapters]]（多 provider API 调用路由，含 AnthropicAdapter、BedrockAdapter、AuxiliaryClient）
- 依赖 [[entities/session-manager]]（gateway 模式下的会话上下文）
- 依赖 [[entities/state-database]]（SQLite 会话持久化）
- 依赖 [[entities/security-sandbox]]（终端命令安全检查）
- 依赖 [[entities/process-registry]]（后台进程中断支持）
- 依赖 [[entities/logging-system]]（集中式日志和密文脱敏）
- 被 [[entities/gateway-runner]] 调用（多平台消息处理）
- 被 [[entities/cli-system]] 调用（CLI 模式启动）
- 被 [[entities/delegate-subagent]] 调用（子 agent 创建）
**为什么它是可分离的**：`AIAgent` 是独立类，接收 provider、tool registry、session db、memory manager 等依赖注入，不耦合特定平台或传输层

**关键机制**（源码可见）：
- API 模式自动检测：根据 provider 名称和 base URL 自动选择 `chat_completions` / `anthropic_messages` / `bedrock_converse` / `codex_responses`，无需手动配置 ^[run_agent.py:690-709]
- 迭代预算共享：`IterationBudget` 对象在父子 agent 间共享，统一限制 LLM 调用次数；剩余预算为 0 或有一步宽限 ^[run_agent.py:170]
- 压缩感知会话拆分：上下文压缩后将旧消息移入子会话（parent_session_id 链），系统提示词缓存自动失效后重建 ^[run_agent.py:7066]
- 流式优先健康检查：优先使用流式 API 路径，内建 90s 流超时检测防止僵死连接 ^[run_agent.py:8806]
- 模型 fallback 与恢复：fallback 模型失败后异步探活主模型，探活成功自动切换回主模型 ^[run_agent.py:6013]
- 错误分类与路由：`classify_api_error()` 区分 `retryable`、`malformed_request`、`rate_limited`、`context_length`、`auth_error` 等 ^[agent/error_classifier.py]
- Token 估算：`estimate_tokens_rough()` 使用启发式方法（每字符约 0.3 token）估算用量，`estimate_messages_tokens_rough()` 逐消息累加 ^[agent/model_metadata.py]
- 上下文压力去重：`_context_pressure_last_warned` 类级字典 {session_id: (warn_level, timestamp)}，同一会话 300s 内不重复警告 ^[run_agent.py:547-548]
- Todo 状态恢复：`_hydrate_todo_store()` 从对话历史恢复 todo 状态，使压缩后仍保持任务追踪 ^[run_agent.py:3264]
- 死连接清理：每轮开始前检测僵尸 TCP 连接并清理 ^[run_agent.py:4444]

**源码证据**：
- 入口文件：run_agent.py
- 核心类型/接口定义：`class AIAgent` ^[run_agent.py:535]、`class IterationBudget` ^[run_agent.py:170]
- 主循环入口：`AIAgent.run_conversation()` ^[run_agent.py:8130]

**关联 Concept**：
- [[concepts/agent-loop-orchestration]]
