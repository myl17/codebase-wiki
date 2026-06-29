---
type: entity
repo: hermes-agent
slug: cron-scheduler
problem: 如何用自然语言定义定时任务并在后台自动执行，支持多平台交付和静默抑制
generated: 2026-06-25
source_files:
  - cron/scheduler.py
  - cron/jobs.py
  - tools/cronjob_tools.py
---

# 定时调度器

**代码位置**：`cron/scheduler.py`、`cron/jobs.py`、`tools/cronjob_tools.py`
**这个模块解决什么问题**：
- 实现层：通过文件系统存储定时任务（JSON），每 60s 由 gateway 后台线程调用 `tick()` 检查到期任务，为每个到期任务创建 AIAgent 执行自然语言提示词并交付到指定平台；支持 cron 表达式、间隔和智能关键词
- 问题层：如何用自然语言定义定时任务并在后台自动执行，支持多平台交付和静默抑制
**对外暴露什么**：
- `tick()` - 主调度函数（cron/scheduler.py:906，由 gateway 每 60s 调用）
- `cronjob()` - Agent 工具（tools/cronjob_tools.py:221，注册为 `cronjob`）
- `create_job()` / `list_jobs()` / `update_job()` / `remove_job()` - 任务 CRUD（cron/jobs.py:368/479/487/575）
- `parse_schedule()` - 调度表达式解析（cron/jobs.py:117）
**它和谁交互**：
- 依赖 [[entities/agent-core]]（`run_job()` 为每个到期任务创建 AIAgent 实例执行提示词）
- 依赖 [[entities/platform-adapters]]（`_deliver_result()` 路由交付到目标聊天平台）
- 依赖 [[entities/tool-registry]]（cronjob 工具注册）
- 被 [[entities/gateway-runner]] 调用（后台线程每 60s 调用 `tick()`）
- 被 [[entities/cli-system]] 调用（`hermes cron` 子命令管理任务）
- 被 [[entities/web-server]] 调用（API 路由管理 cron 任务）
**为什么它是可分离的**：独立子目录 `cron/`，使用文件锁（`.tick.lock`）保证单实例运行，与 gateway 解耦

**关键机制**（源码可见）：
- 文件锁保护：`~/.hermes/cron/.tick.lock` 使用 fcntl/msvcrt 文件锁，防止多进程并发 tick ^[cron/scheduler.py:921-935]
- 调度表达式解析：`parse_schedule()` 支持 cron 表达式（需 `croniter`）、间隔（`"30m"`、`"2h"`）、一次性时间戳、智能关键词（`"tomorrow 9am"`）^[cron/jobs.py:117-160]
- 静默抑制：Agent 响应前缀为 `[SILENT]` 时跳过交付，结果仍存档本地审计 ^[cron/scheduler.py:55-58]
- 预提前调度：`advance_next_run()` 在执行前计算下次运行时间并写入，保证崩溃后不会重复执行 ^[cron/scheduler.py:636]
- 安全扫描：`_scan_cron_prompt()` 对 cron 提示词进行 11 种注入/外泄模式检测 + 不可见 Unicode 检测 ^[tools/cronjob_tools.py:41-115]
- 交付平台验证：`_KNOWN_DELIVERY_PLATFORMS` frozenset（26+ 平台名）验证交付目标，防止 env var 枚举 ^[cron/scheduler.py:45-50]
- 多平台交付：`_deliver_result()` 支持 26+ 平台（telegram, discord, slack, whatsapp, signal, matrix, mattermost, weixin, feishu, dingtalk 等）^[cron/scheduler.py:201-478]
- 任务持久化：`~/.hermes/cron/jobs.json` 存储所有任务，支持 pause/resume 状态切换 ^[cron/jobs.py:36, 526/539]

**源码证据**：
- 入口文件：cron/scheduler.py、cron/jobs.py
- 核心函数：`def tick()` ^[cron/scheduler.py:906]、`def cronjob(action, ...)` ^[tools/cronjob_tools.py:221]

**关联 Concept**：
- [[concepts/autonomous-scheduling]]
