---
type: concept
concept: agent-loop-orchestration
problem: 如何编排 Agent 的主循环，协调消息接收、LLM 调用、工具执行和流式响应
concerns: [模块化与职责分离, 错误恢复能力, 并发模型]
repos: [nanobot, hermes-agent, openclaw]
generated: 2026-06-25
---

# Agent 主循环编排

## 核心问题

构建 AI Agent 框架时，每个框架都必须回答同一个问题：Agent 的主循环应该长什么样？这个循环需要协调消息接收、上下文构建、LLM 调用、工具执行和流式响应五个环节，但每个环节都有多种设计选择。

根本张力在于**循环的职责边界**：循环是只管"LLM 调工具、工具返回结果、再调 LLM"的纯执行，还是同时管消息路由、会话管理、流式管道等编排职责？拆得太细会增加协调成本和理解负担，拆得太粗会让单个类承担过多职责。三个框架给出了三种答案：nanobot 严格拆分为两个独立类，hermes-agent 合并为单一类，openclaw 用函数闭包替代类层次。

另一个张力在于**循环的并发策略**：多用户同时发消息时，是串行处理每条消息保证顺序，还是允许并发处理？如果是并发，如何隔离不同会话的状态？三个框架都选择了"会话内串行、会话间并发"的基本路线，但对并发上限、会话锁粒度和优雅退出各有不同实现。

## 关切

- **模块化与职责分离**：编排层（消息路由、流式管道、会话管理）与执行层（LLM-tool 循环）是分离还是合并，影响代码可测试性和复用性
- **错误恢复能力**：API 错误、空响应、长度截断、超时等异常的自动检测、分类和恢复，直接影响生产可用性
- **并发模型**：多会话并发处理的隔离策略和流控机制，决定扩展性上限

## 各框架的解法

### nanobot

来源：[[repos/nanobot/entities/agent-loop]]、[[repos/nanobot/entities/agent-runner]]
**解法**：严格分离编排层与执行层——AgentLoop 负责消息路由/会话管理/流式管道，AgentRunner 负责纯 LLM-tool 执行循环。
**实现**：
- 双层类分离：`AgentLoop` 持有 `AgentRunner` 实例，loop 从 MessageBus 消费消息后委托 runner 执行，runner 完全不感知 channel、session 等产品概念 ^[nanobot/agent/loop.py:115-186]
- 会话级串行锁 + 并发信号量：每个 session_key 独立的 `asyncio.Lock` 保证同会话有序，全局 `asyncio.Semaphore`（默认 3，通过 `NANOBOT_MAX_CONCURRENT_REQUESTS` 配置）限制并发会话数 ^[nanobot/agent/loop.py:204-209]
- 运行时检查点恢复：长任务中断时持久化进行中的 turn 状态（`_RUNTIME_CHECKPOINT_KEY`），重建时恢复未完成的 tool call ^[nanobot/agent/loop.py:127]
- 空响应重试：最多 2 次，超出后发送最终化重试消息；长度恢复最多 3 次 ^[nanobot/agent/runner.py:33-36]
**权衡**：强模块化使 runner 可在子 agent、Dream 内存处理等场景复用，但增加了跨类协调成本。并发信号量是粗粒度全局控制（按会话数而非 token 数限流），无错误分类机制。

### hermes-agent

来源：[[repos/hermes-agent/entities/agent-core]]
**解法**：`AIAgent` 单一类承载完整循环，内建 API 模式自动检测、错误分类、迭代预算共享和模型 fallback。
**实现**：
- 单一类主循环：`AIAgent.run_conversation()` 驱动完整 while 循环，包含消息构建、LLM 调用、工具执行、流式输出和错误恢复 ^[run_agent.py:8130]
- API 模式自动检测：根据 provider 名称和 base URL 自动选择 `chat_completions` / `anthropic_messages` / `bedrock_converse` / `codex_responses`，无需手动配置 ^[run_agent.py:690-709]
- IterationBudget 共享：父子 agent 间共享迭代预算对象，剩余预算为 0 时只有一步宽限，防止无界循环 ^[run_agent.py:170]
- 错误分类与路由：`classify_api_error()` 区分 `retryable`、`malformed_request`、`rate_limited`、`context_length`、`auth_error` 等类别，针对性处理 ^[agent/error_classifier.py]
- 模型 fallback 与异步探活：主模型失败后切换 fallback，后台异步探活主模型，成功自动切回 ^[run_agent.py:6013]
- 流式优先健康检查：优先使用流式路径，90s 超时检测僵死连接 ^[run_agent.py:8806]
**权衡**：丰富的错误恢复（分类 + fallback + 探活）提供高可用性，但单类承载全流程使 AIAgent 成为超大文件（run_agent.py 持续增长）。无显式并发控制在上层网关层（GatewayRunner 按 session 路由消息），回路层自身不感知并发。

### openclaw

来源：[[repos/openclaw/entities/agent-runtime]]
**解法**：`runEmbeddedPiAgent` 纯函数实现，`while(true)` 内完成模型调用、流式订阅、压缩重试、错误处理和故障切换。
**实现**：
- 函数式主循环：`while(true)` 内模型调用 → 流式订阅 → 结果分析 → 错误处理 → 压缩重试 → 计划检测 → 不完整回合处理 ^[src/agents/pi-embedded-runner/run.ts:569]
- 流式订阅状态机：追踪 `assistantTexts`、`toolMetas`、delta buffer、thinking tags、重复检测、压缩协调等 10+ 状态字段 ^[src/agents/pi-embedded-subscribe.ts:74-127]
- Lane 并发控制：先加入 session lane（会话级互斥），再加入 global lane（全局并发限制），双层锁防止并发访问 ^[src/agents/pi-embedded-runner/run.ts:176-210]
- 模型故障切换链：`runWithModelFallback` 提供完整的 provider/model 级故障切换策略 ^[src/agents/model-fallback.ts:626]
- 运行状态全局单例：`Symbol.for("openclaw.embeddedRunState")` 跨模块边界追踪所有活跃运行，支持外部中断和注入 ^[src/agents/pi-embedded-runner/runs.ts]
**权衡**：函数式设计避免了类的复杂性，lane 双锁机制提供细粒度并发控制。但 `while(true)` 循环逻辑与压缩重试、超时恢复、上下文溢出判定等深度耦合在同一函数体中，单函数体积极大。

## 对比

| 框架 | 模块化与职责分离 | 错误恢复能力 | 并发模型 |
|------|------|------|------|
| nanobot | AgentLoop + AgentRunner 两层严格分离；runner 零产品耦合，可在子 agent、Dream 等场景复用 | 空响应重试 2 次 + 长度恢复 3 次；无错误分类，无模型 fallback | 会话级 asyncio.Lock + 全局 Semaphore（默认 3 并发） |
| hermes-agent | AIAgent 单一类承载所有职责；IterationBudget 在父子间共享 | 6 类 API 错误分类 + 主/fallback 模型异步探活 + 流式超时检测 + 死连接清理 | 上层网关按 session_key 路由消息，循环层本身无并发感知 |
| openclaw | `runEmbeddedPiAgent` 单一函数；故障切换、压缩、流式订阅均在 while(true) 内 | 完整模型故障切换链 + 超时触发压缩 + 上下文溢出判定 + retry limit 达上限后 liveness block | session lane + global lane 双锁机制；全局单例追踪活跃运行 |

## 子维度观察

以下问题空间当前因跨仓库成熟度不足而未独立成 Concept，记录为父页面的子维度。若未来更多仓库将其演化为独立子系统，可通过 Split 操作升级。

### Agent 生命周期的可扩展钩子系统

- **来源信号**：2026-06-25 hermes-agent + openclaw 跨仓库对比（信号 1，粒度不匹配）
- **涉及仓库**：openclaw（hooks-system：四个来源目录 + 三级过滤 + 双层层事件匹配 + per-handler 错误隔离）、hermes-agent（gateway/hooks.py：轻量 gateway 级 hooks）、nanobot（AgentHook：生命周期回调）
- **当前判断**：openclaw 将 hooks 作为一等公民子系统（完整发现-过滤-隔离-安全管道），hermes-agent 和 nanobot 将其作为附属回调。成熟度差距过大，暂不独立建 Concept。
- **升级条件**：至少 2 个以上仓库将 hooks 演化为独立子系统（含发现/过滤/隔离/安全机制），且方案间存在可对比的 trade-off。

## 演化记录

- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-25：记录子维度观察「Agent 生命周期的可扩展钩子系统」[触发: evolve-signals]
