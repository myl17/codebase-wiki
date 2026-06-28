---
type: entity
repo: hermes-agent
slug: process-registry
problem: 如何跟踪和管理 Agent 通过终端工具在后台启动的进程，提供状态轮询、输出缓冲、中断、崩溃恢复和会话感知
generated: 2026-06-25
source_files:
  - tools/process_registry.py
  - tools/checkpoint_manager.py
---

# 进程注册表

**代码位置**：`tools/process_registry.py`
**这个模块解决什么问题**：
- 实现层：`ProcessRegistry` 内存单例跟踪通过 `terminal(background=true)` 启动的后台进程，提供 200KB 滚动输出缓冲、状态轮询、阻塞等待（带中断支持）、进程终止和 JSON 崩溃恢复
- 问题层：如何跟踪和管理 Agent 通过终端工具在后台启动的进程，提供状态轮询、输出缓冲、中断、崩溃恢复和会话感知
**对外暴露什么**：单例 `process_registry`（tools/process_registry.py）、`ProcessSession` dataclass（line 68）、`ProcessRegistry` 类（line 106）
**它和谁交互**：
- 依赖 [[entities/terminal-execution]]（后台进程通过 `process_registry.spawn()` 或 `spawn_via_env()` 注册）
- 依赖 [[entities/agent-core]]（中断事件传播到后台进程；agent 轮询 `is_interrupted()`）
- 被 [[entities/gateway-runner]] 调用（会话重置前检查 `has_active_for_session()` 阻止重置）
- 被 [[entities/session-manager]] 调用（`has_active_processes_fn` 回调）
- 被 checkpoint-manager 互补（文件系统的文件版本控制 vs 进程级的进程管理）
**为什么它是可分离的**：独立单例注册表，通过 PID 和环境引用跟踪进程，不与任何特定工具耦合

**关键机制**（源码可见）：
- 双 spawn 模式：`spawn_local()` 通过 PTY（ptyprocess）或 pipe（subprocess.Popen）本地创建 ^[tools/process_registry.py:298-408]；`spawn_via_env()` 通过环境接口（Docker/Singularity/Modal/Daytona/SSH）创建 ^[tools/process_registry.py:410-518]
- 200KB 滚动缓冲：`MAX_OUTPUT_CHARS = 200_000`，进程输出通过 deque 循环缓冲，保持最新数据 ^[tools/process_registry.py:57, 68-106]
- 会话感知：`session_key` 字段关联进程到 gateway 会话，`has_active_for_session()` 检查活跃进程阻止重置 ^[tools/process_registry.py:68]
- 崩溃恢复：`CHECKPOINT_PATH = ~/.hermes/processes.json`，gateway 启动时通过 `recover_from_checkpoint()` 恢复未完成的进程状态 ^[tools/process_registry.py:54, 1014]
- 中断感知等待：`wait()` 方法轮询 `is_interrupted()` 事件，收到中断信号立即 `kill_process()` 并返回 ^[tools/process_registry.py:700-770]
- 容量限制：`MAX_PROCESSES = 64`，超出时 LRU 修剪最旧的已完成进程；已完成进程保留 `FINISHED_TTL_SECONDS = 1800`（30 分钟）^[tools/process_registry.py:58-59]
- 进程终止：`kill_process()` 先 SIGTERM，超时后 SIGKILL，兼容 Windows 的 `taskkill` ^[tools/process_registry.py:773-831]
- stdin 交互：`write_stdin()` / `submit_stdin()` / `close_stdin()` 支持向运行中的后台进程发送输入 ^[tools/process_registry.py:833-880]
- 磁盘使用警告：`_get_total_sandbox_size_used_gb()` 监控 sandbox 磁盘使用，超过 500GB 时通过 activity callback 警告 ^[tools/process_registry.py:520-559]

**源码证据**：
- 入口文件：tools/process_registry.py
- 核心类型：`class ProcessRegistry` ^[tools/process_registry.py:106]、`@dataclass class ProcessSession` ^[tools/process_registry.py:68]
