---
type: entity
repo: hermes-agent
slug: terminal-execution
problem: 如何在统一的接口下支持多种执行环境（本地、Docker、Modal、SSH、Daytona、Singularity），实现命令执行、后台任务和安全管理
generated: 2026-06-25
source_files:
  - tools/terminal_tool.py
  - tools/environments/base.py
  - tools/environments/local.py
  - tools/environments/docker.py
  - tools/environments/modal.py
  - tools/environments/singularity.py
  - tools/environments/ssh.py
  - tools/environments/daytona.py
  - tools/environments/managed_modal.py
  - tools/environments/modal_utils.py
  - tools/environments/file_sync.py
---

# 终端执行与环境后端

**代码位置**：`tools/terminal_tool.py`、`tools/environments/`
**这个模块解决什么问题**：
- 实现层：`terminal_tool()` 提供统一命令执行接口，通过 `_create_environment()` 工厂路由到 6 种后端（local/docker/singularity/modal/daytona/ssh），支持前台/后台、PTY、超时、中断和资源清理
- 问题层：如何在统一的接口下支持多种执行环境（本地、Docker、Modal、SSH、Daytona、Singularity），实现命令执行、后台任务和安全管理
**对外暴露什么**：`terminal_tool()` 函数（tools/terminal_tool.py:1106，注册为工具 `terminal`）、`cleanup_vm()`、`get_active_env()`、`is_persistent_env()`、环境基类 `BaseEnvironment`（tools/environments/base.py:89）
**它和谁交互**：
- 依赖 [[entities/security-sandbox]]（执行前通过 `check_all_command_guards()` 进行 tirith 扫描和危险命令检测）
- 依赖 [[entities/process-registry]]（后台进程通过 `process_registry.spawn()` 注册）
- 依赖 [[entities/agent-core]]（通过 interrupt event 支持中断；agent 设置 activity callback）
- 依赖 [[entities/config-system]]（TERMINAL_ENV 选择后端，sandbox 路径配置）
- 被 [[entities/agent-core]] 调用（通过工具分发）
- 被 [[entities/delegate-subagent]] 调用（子 agent 继承环境）
**为什么它是可分离的**：环境后端通过 ABC 抽象 `BaseEnvironment.execute()`，添加新后端只需实现接口，不修改调用方

**关键机制**（源码可见）：
- 统一 spawn-per-call 模型：所有后端都通过 `bash -c` 执行命令，会话快照（env vars, functions, aliases）在 init 时捕获并在每次命令前 source ^[tools/environments/base.py:1-8]
- 六种后端：local（直接 Popen）、docker（容器内执行，支持持久 workspace）、singularity（容器，scratch dir）、modal（云端沙箱）、daytona（云端 workspace）、ssh（远程执行）^[tools/terminal_tool.py:686-760]
- CWD 持久化：local 模式使用 temp file 标记，remote 模式使用 in-band stdout marker；保证跨命令的工作目录连续性 ^[tools/environments/base.py:1-8]
- Modal 托管网关：`managed_modal` 通过 Nous Research 托管网关转发 Modal 请求，无需用户配置 Modal credentials ^[tools/environments/managed_modal.py]
- 自动清理：`_cleanup_inactive_envs()` 后台线程定期清理空闲环境（默认 lifetime 300s），防止资源泄漏 ^[tools/terminal_tool.py:815]
- 前台超时硬限制：`FOREGROUND_MAX_TIMEOUT = 600s`，可通过 `TERMINAL_MAX_FOREGROUND_TIMEOUT` 覆盖 ^[tools/terminal_tool.py:76]
- 磁盘使用警告：监控 sandbox 目录大小，超过阈值 `TERMINAL_DISK_WARNING_GB`（500GB）时警告 ^[tools/terminal_tool.py:79]
- 中断感知：通过 `is_interrupted()` 轮询，接收中断信号后立即 kill 子进程 ^[tools/terminal_tool.py:55-56]
- PTY 支持：`pty=True` 时使用 `ptyprocess` 提供伪终端，支持交互式程序 ^[tools/terminal_tool.py:1106]
- Sudo 密码回调：`set_sudo_password_callback()` 注册函数处理 sudo 密码输入 ^[tools/terminal_tool.py:123]
- 任务级环境覆盖：`register_task_env_overrides()` 允许不同 task_id 使用不同后端 ^[tools/terminal_tool.py:553]

**源码证据**：
- 入口文件：tools/terminal_tool.py
- 核心函数：`def terminal_tool(command, background=False, timeout=None, ...)` ^[tools/terminal_tool.py:1106]
- 基类：`class BaseEnvironment(ABC)` ^[tools/environments/base.py:89]

**关联 Concept**：
- [[concepts/execution-isolation]]
