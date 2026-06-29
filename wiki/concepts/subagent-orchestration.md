---
type: concept
concept: subagent-orchestration
problem: 如何让主 Agent 委托后台子 Agent 执行复杂任务，管理其孵化、执行、完成和故障恢复
concerns: [并行模式与隔离, 故障恢复能力, 预算控制]
repos: [nanobot, hermes-agent, openclaw, deepagents]
generated: 2026-06-25
---

# Subagent Orchestration

## 核心问题

多 Agent 系统中，主 Agent 不可能在一个对话上下文中完成所有工作——有些任务需要并行加速（比如同时搜索多个信息源），有些任务需要上下文隔离（子任务不应污染主任务的工具调用历史），有些任务需要异步执行（主 Agent 不必等待子任务完成）。这三个需求——并行、隔离、异步——是所有 Agent 框架构建子 Agent 委派机制时必须回答的三元张力。

不同框架在这个三角上取了不同的平衡点。并行意味着要管理并发生命周期；隔离意味着要限制工具集和上下文传递方式；异步意味着要有结果的回传和故障恢复机制。三者互相制约：更强的隔离（如独立进程）会削弱并行效率；更激进的并行会提高故障恢复的复杂度；简单的同步等待模型牺牲了异步价值但极大简化了实现。

预算控制是第四个维度——当子 Agent 可以继续调用 LLM 时，如何防止一次委派耗尽所有 token 配额？这个问题的答案直接决定了子 Agent 的自主程度：是给一个固定的步数上限，还是共享全局预算，还是完全信任子 Agent 自行决策。

## 关切

- **并行模式与隔离**：子 Agent 是在同一进程内独立会话运行，还是跨进程/线程并行？工具集如何限制以避免递归委派和上下文污染？隔离越强，并行开销越大。
- **故障恢复能力**：子 Agent 崩溃后能否恢复？主 Agent 重启后能否找回孤儿子 Agent 的结果？这决定了系统在长时间运行任务中的可靠性。
- **预算控制**：子 Agent 的 LLM 调用如何计费？是继承父 Agent 的配额、独立限额、还是无限制？预算共享模式决定了子 Agent 的自主程度和父 Agent 的资源安全。

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/subagent-manager]]
**解法**：通过 MessageBus 以 system 消息注入结果的异步回调模式，子 Agent 使用完全独立的 AgentRunner 和精简工具集。
**实现**：回调通信通过 `_announce_result()` 将子任务结果以 markdown 格式通过 `bus.publish_inbound()` 注入主 Agent 上下文，避免轮询；子 Agent 工具集硬编码排除 `message` 和 `spawn` 工具以防递归；`_session_tasks` 字典支持按 session 批量取消子任务。 ^[nanobot/agent/subagent.py:181-209, 113-133, 247-255]
**权衡**：满足了隔离（独立 AgentRunner 实例，独立工具集）和异步（消息总线注入结果），但缺少显式的预算控制和故障恢复机制——子 Agent 崩溃后无孤儿恢复。

### hermes-agent
来源：[[repos/hermes-agent/entities/delegate-subagent]]
**解法**：通过 ThreadPoolExecutor 并行创建独立 AIAgent 子实例，共享父 Agent 的 IterationBudget 统一限制 LLM 调用总数。
**实现**：`DELEGATE_BLOCKED_TOOLS` 屏蔽 5 个工具（delegate_task/clarify/memory/send_message/execute_code）防递归和上下文污染；最大嵌套深度硬编码为 2 层；默认最多 3 个并发子 Agent；子 Agent 继承父的 `iteration_budget` 共享全局配额；支持单任务和批量两种模式。 ^[tools/delegate_tool.py:32-38, 53, 52-79, 238-284]
**权衡**：并行为强项（ThreadPoolExecutor + 进度回调），预算控制通过共享 IterationBudget 统一管理，但故障恢复较弱——子 Agent 的生命周期与父 Agent 绑定。

### openclaw
来源：[[repos/openclaw/entities/subagent-system]]
**解法**：通过 DI 构造的 SubagentRegistry 管理完整生命周期，内存+磁盘双层持久化保证故障恢复。
**实现**：内存 Map + 磁盘文件双层存储；定期 sweeper 处理孤立运行；`reconcileOrphanedRestoredRuns` 在 gateway 重启后恢复未完成的子 Agent；announce 重试使用指数退避，有最大重试次数限制；深度限制通过 `DEFAULT_SUBAGENT_MAX_SPAWN_DEPTH` 防止无限嵌套。 ^[src/agents/subagent-registry.ts:33-56, src/agents/subagent-registry-memory.ts, src/agents/subagent-registry-helpers.ts:23-25]
**权衡**：故障恢复是三个框架中最强的（持久化+孤立恢复+announce 重试），但并行模型不如 hermes-agent 的 ThreadPoolExecutor 直观——openclaw 通过 gateway 调度子 Agent，本质上走网络层。

### deepagents
来源：[[repos/deepagents/entities/subagent-middleware]]、[[repos/deepagents/entities/async-subagent-middleware]]
**解法**：双轨子代理——同步 `SubAgent`（声明式/编译式）通过 `task` 工具隔离执行；异步 `AsyncSubAgent` 通过 LangGraph SDK 连接远程 Agent Protocol 服务器，非阻塞后台执行，任务状态跨压缩持久化。
**实现**：同步子代理支持 SubAgent（声明式 name/description/system_prompt + 自动填充默认中间件堆栈）和 CompiledSubAgent（预编译 Runnable 图）两种形态，完成后从 messages 提取最后一条消息作为 ToolMessage 返回。状态键过滤排除 messages/todos/structured_response/skills_metadata/memory_contents 五类，防止父状态泄漏。异步子代理通过 5 个工具（start/check/update/cancel/list）管理后台任务，任务状态持久化在 `async_tasks` 字典中（含 status/thread_id/run_id/timestamps），即使上下文压缩后仍可访问。并发状态获取在 `list_async_tasks` 中通过 `asyncio.gather` 实现，终态跳过网络请求。`interrupt_on` 在声明式子代理中默认继承父配置。通用子代理自动注入：未提供 `general-purpose` 名称的子代理时，自动创建默认通用子代理。 ^[deepagents/middleware/subagents.py:298-389, 126, 336, 500-502; deepagents/middleware/async_subagents.py:837-859, 113-126, 683-722]
**权衡**：同步+异步双轨覆盖了短期隔离执行和长期后台执行两种场景，隔离性好（五类状态键过滤 + 独立中间件堆栈）。但同步子代理无持久化（ephemeral，结果仅通过 ToolMessage 返回），故障恢复弱于 openclaw。异步子代理依赖远程 Agent Protocol 服务器，offline 不可用。无显式预算控制——子代理的 LLM 调用不受限制。

## 对比
| 框架 | 并行模式与隔离 | 故障恢复能力 | 预算控制 |
|------|------|------|------|
| nanobot | 独立 AgentRunner + 回调式消息注入，工具集硬编码排除 message/spawn | 无持久化，无孤儿恢复 | 无显式预算控制 |
| hermes-agent | ThreadPoolExecutor 并行（默认 3 并发）+ 5 工具屏蔽清单 + 深度限制 2 | 子 Agent 生命周期随父进程 | 共享 IterationBudget，全局 LLM 调用计数 |
| openclaw | Gateway 调度 + DI 注册表隔离 + 深度限制 | 内存+磁盘双层持久化 + 孤立恢复 + 指数退避 announce 重试 | 无显式预算控制 |
| deepagents | 同步声明式/编译式 + 异步远程双轨；五类状态键过滤；通用子代理自动注入 | 同步子代理无持久化；异步子代理状态跨压缩持久化 | 无显式预算控制 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 deepagents（同步 SubAgent + 异步 AsyncSubAgent 双轨）
