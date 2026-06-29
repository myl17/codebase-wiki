---
type: concept
concept: autonomous-scheduling
problem: 如何让 Agent 具备定时自主执行任务的能力，支持调度表达、防重复触发和静默交付
concerns: [调度表达方式, 防重复执行, Agent 对调度的感知程度]
repos: [nanobot, hermes-agent, openclaw]
generated: 2026-06-25
---

# Autonomous Scheduling

## 核心问题

Agent 真正的自主性不是"用户发指令它执行"，而是"没有用户干预时它也能在正确的时间做正确的事"。定时调度是实现这一自主性的基础机制——让 Agent 每天早上 9 点汇总新闻、每周五生成周报、或监控某个事件源并在条件满足时主动通知。但定时触发只是表面需求，深层张力在于三个维度：调度表达的灵活度（cron 表达式 vs 自然语言）、防重复执行的可靠性（多进程/多实例部署时如何确保同一任务不执行两次）、以及 Agent 对自身调度的感知程度（Agent 是否知道自己有个 schedule，还是被盲触发）。

调度表达方式决定用户的使用门槛。cron 表达式精确但难写，"每天早上 9 点"这种自然语言直观但解析有歧义。两者的覆盖面和边界情况不同——cron 表达式能表达"每个月最后一个周五"，自然语言关键词更擅长"明天上午"这种相对时间。理想方案是两者共存，让用户可以选择精确或直观。

防重复执行是多实例部署的核心难题。如果 Agent 在 3 台服务器上各跑一个 gateway 实例，每 60 秒的 tick 会被触发 3 次——需要分布式锁或文件锁防止同一任务重复执行。更隐蔽的问题是时间窗口：如果任务执行本身耗时超过 tick 间隔（如一个 cron 任务执行了 90 秒，而 tick 是 60 秒），预提前调度（在执行前就标记下次运行时间）比执行后标记更安全。

Agent 对调度的感知程度是最被低估的设计差异。盲触发模式（到时间就推一条消息给 Agent）简单但 Agent 不知道自己在 schedule 中——它无法主动管理自己的调度（如调整频率、跳过下一次）。感知模式（将调度信息注入系统提示）让 Agent 知道自己何时会被唤醒，可以用 cron 工具管理自己的调度计划。后者让调度从"外部定时触发器"升级为"Agent 的时间感知能力"。

## 关切

- **调度表达方式**：cron 表达式精确但陡峭，自然语言直观但有歧义。两者的覆盖面和解析可靠性如何？是否支持时区和一次性任务？
- **防重复执行**：多实例部署时同一 tick 被触发多次如何防止？任务执行时间超过 tick 间隔时如何避免重复调度？预提前调度 vs 执行后标记的策略差异是什么？
- **Agent 对调度的感知程度**：Agent 是被盲触发还是知道自己的调度？能否主动管理调度（增删改查）？调度信息是否在系统提示中可见？

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/cron-service]]、[[repos/nanobot/entities/heartbeat-service]]
**解法**：两个独立的调度引擎——CronService 管理定时任务调度，HeartbeatService 在 Agent 空闲时触发自主行为决策。
**实现**：CronService 支持 at（一次性）、every（间隔毫秒）、cron（标准 5 段表达式+时区）三种调度方式；action.jsonl 实现多实例间的任务变更协调；自适应 timer 根据最早到期任务计算唤醒间隔（最长休眠 5 分钟）；Heartbeat 通过虚拟 tool call 让 LLM 输出 skip/run 决策，Phase 1 决策与 Phase 2 执行解耦避免浪费 token。 ^[nanobot/cron/types.py, nanobot/cron/service.py:135-169, 259-287, nanobot/heartbeat/service.py:14-37, 40-50]
**权衡**：双服务拆分让定时调度和空闲自主行为各司其职——适合需要两种自主触发模式并存的场景。但 cron-service 的防重复依赖 action log 合并而非严格锁，多实例场景下边缘情况可能遗漏。

### hermes-agent
来源：[[repos/hermes-agent/entities/cron-scheduler]]
**解法**：60s tick + fcntl 文件锁 + 自然语言关键词解析 + [SILENT] 静默抑制 + 26+ 平台交付。
**实现**：`~/.hermes/cron/.tick.lock` 使用 fcntl 文件锁严格防止多进程并发 tick；`parse_schedule()` 支持 cron 表达式 + 间隔 + 自然语言关键词（"tomorrow 9am"）；预提前调度在执行前就写入下次运行时间，防止崩溃后重复执行；`[SILENT]` 标签让 Agent 响应为空时不推送通知但结果仍存档；11 种注入/外泄模式检测 cron 提示词安全。 ^[cron/scheduler.py:921-935, cron/jobs.py:117-160, cron/scheduler.py:636, 55-58, tools/cronjob_tools.py:41-115]
**权衡**：防重复机制最可靠（文件锁+预提前调度），调度表达最丰富（自然语言+cron+间隔），交付最广泛（26+ 平台）。但 Agent 对自身调度无感知——触发是由外部时机驱动的盲触发模式。

### openclaw
来源：[[repos/openclaw/entities/cron-system]]
**解法**：Cron 表达式解析 → gateway cron 服务 → 心跳系统提示注入调度信息 → Agent 通过 cron 工具自主管理调度。
**实现**：`buildGatewayCronService` 集成到 gateway 生命周期；`buildHeartbeatSection` 在系统提示中注入下一个 cron 触发时间和调度状态，让 Agent 知道何时会被唤醒；Agent 可通过 `cron` 工具增删改查自己的调度计划；支持多种时区指定。 ^[src/gateway/server-cron.ts, src/agents/system-prompt.ts:122, src/agents/tool-catalog.ts]
**权衡**：唯一实现"Agent 感知调度"的框架——Agent 知道自己的 schedule 并可用工具管理。但防重复机制细节不明确，调度表达仅支持标准 cron 表达式（无自然语言），交付渠道不如 hermes-agent 丰富。

## 对比
| 框架 | 调度表达方式 | 防重复执行 | Agent 对调度的感知程度 |
|------|------|------|------|
| nanobot | cron 表达式 + at + every 三种，无自然语言 | action.jsonl 多实例协调（非严格锁） | 盲触发，但 HeartbeatService 提供空闲时自主决策 |
| hermes-agent | cron + 间隔 + 自然语言关键词（"tomorrow 9am"） | fcntl 文件锁 + 预提前调度（最强） | 盲触发，无系统提示注入 |
| openclaw | 标准 cron 表达式 + 时区，无自然语言 | 网关集成但细节不明确 | Agent 通过心跳提示感知调度，可用 cron 工具自主管理 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
