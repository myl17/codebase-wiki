---
type: entity
repo: nanobot
slug: agent-runner
problem: 如何实现一个不耦合产品逻辑的通用 tool-use LLM 执行循环
generated: 2026-06-25
source_files:
  - nanobot/agent/runner.py
---

# Agent Runner

**代码位置**：`nanobot/agent/runner.py`
**这个模块解决什么问题**：
- 实现层：提供无产品层偏见的工具调用 LLM 循环，处理消息历史管理、上下文窗口裁剪、工具结果截断、空响应重试和长度恢复
- 问题层：如何实现一个不耦合产品逻辑的通用 tool-use LLM 执行循环
**对外暴露什么**：`AgentRunner` 类（nanobot/agent/runner.py:83）、`AgentRunSpec` 配置 dataclass（nanobot/agent/runner.py:44）、`AgentRunResult` 结果 dataclass（nanobot/agent/runner.py:70）
**它和谁交互**：
- 依赖 `LLMProvider`（nanobot/providers/base.py，底层 LLM 调用）
- 依赖 [[entities/tool-registry]]（获取工具定义和执行工具）
- 依赖 AgentHook（nanobot/agent/hook.py，迭代生命周期）
- 被 [[entities/agent-loop]] 调用（主循环通过 runner 执行 LLM 迭代）
- 被 [[entities/subagent-manager]] 调用（子 agent 使用独立 runner 实例）
- 被 [[entities/memory-system]] 调用（Dream Phase 2 使用 runner 做文件编辑）
**为什么它是可分离的**：纯 runner 不感知 channel、session、CLI 等产品层概念，只处理 messages + tools + provider 的通用循环

**关键机制**（源码可见）：
- 上下文治理管道：每次迭代依次执行 `_backfill_missing_tool_results`（回填丢失的工具结果）、`_microcompact`（压缩旧工具结果）和 `_snip_history`（按 token 预算裁剪历史）^[nanobot/agent/runner.py:89-107]
- 快照式历史裁剪：从后向前累加消息直到 token 预算用尽，保证至少从一个 user 消息开始，不破坏工具调用配对 ^[nanobot/agent/runner.py:640-697]
- 微压缩：将超过 `_MICROCOMPACT_KEEP_RECENT`（最近 10 条）的可压缩工具结果替换为一句话摘要，减少上下文膨胀 ^[nanobot/agent/runner.py:593-617]
- 空响应重试：最多重试 `_MAX_EMPTY_RETRIES`（2 次），超出后发送最终化重试消息强制回复 ^[nanobot/agent/runner.py:33-35, 200-230]
- 长度恢复：当 `finish_reason == "length"` 时追加继续消息，最多 `_MAX_LENGTH_RECOVERIES`（3 次）^[nanobot/agent/runner.py:36, 232-251]
- 并发工具分批：工具调用按 `concurrency_safe` 属性分组，安全的可并行，不安全的串行 ^[nanobot/agent/runner.py:699-722]

**源码证据**：
- 入口文件：nanobot/agent/runner.py
- 核心类型/接口定义：`class AgentRunner` ^[nanobot/agent/runner.py:83]、`@dataclass class AgentRunSpec` ^[nanobot/agent/runner.py:44]

**关联 Concept**：
- [[concepts/agent-loop-orchestration]]
- [[concepts/context-compression-strategy]]
