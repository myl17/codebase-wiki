---
type: entity
repo: hermes-agent
slug: logging-system
problem: 如何提供组件感知的集中式日志系统，支持会话关联、密文脱敏和分级日志文件
generated: 2026-06-25
source_files:
  - hermes_logging.py
  - agent/redact.py
---

# 日志系统

**代码位置**：`hermes_logging.py`、`agent/redact.py`
**这个模块解决什么问题**：
- 实现层：`setup_logging()` 创建 RotatingFileHandler 驱动的日志文件（agent.log/errors.log/gateway.log），通过自定义 LogRecord factory 注入 thread-local 会话 ID，使用 `RedactingFormatter` 确保敏感信息不写入磁盘
- 问题层：如何提供组件感知的集中式日志系统，支持会话关联、密文脱敏和分级日志文件
**对外暴露什么**：`setup_logging()`（hermes_logging.py:156）、`setup_verbose_logging()`（hermes_logging.py:263）、`set_session_context()` / `clear_session_context()`（hermes_logging.py:72/81）、`RedactingFormatter`（agent/redact.py）
**它和谁交互**：
- 被 [[entities/agent-core]] 调用（agent 初始化时设定 session context）
- 被 [[entities/gateway-runner]] 调用（gateway 启动时以 `mode="gateway"` 初始化）
- 被 [[entities/cli-system]] 调用（`hermes logs` 查看日志）
- 被 [[entities/web-server]] 调用（`/api/logs` 路由）
- 被 [[entities/config-system]] 调用（读取 `logging.*` 配置）
- 全局生效：通过 `logging.setLogRecordFactory()` 注入 session_tag 到所有 log record
**为什么它是可分离的**：独立的 `hermes_logging.py` 模块，通过 Python logging 框架集成，不绑定特定子系统

**关键机制**（源码可见）：
- 三分级日志文件：
  - `agent.log`（INFO+，默认 5MB/3 备份）— 所有 agent/tool/session 活动 ^[hermes_logging.py:220-228]
  - `errors.log`（WARNING+，2MB/2 备份）— 快速分诊 ^[hermes_logging.py:230-238]
  - `gateway.log`（INFO+，5MB/3 备份）— 仅 gateway 组件记录（通过 `_ComponentFilter` 过滤 `gateway.*` logger）^[hermes_logging.py:240-250]
- Thread-local 会话关联：`set_session_context(session_id)` 设置线程局部变量，LogRecord factory 注入 `%(session_tag)s` 到每条日志 ^[hermes_logging.py:72-83, 90-118]
- 密文脱敏：`RedactingFormatter` 在日志写入前匹配并遮蔽 API key、token、密码等敏感模式 ^[agent/redact.py]
- 第三方日志静默：`_NOISY_LOGGERS` 包含 openai、httpx、httpcore、asyncio、grpc、urllib3、websockets 等，统一设为 WARNING 级别 ^[hermes_logging.py:50-65]
- 组件隔离：`COMPONENT_PREFIXES` 定义 5 个组件前缀（"gateway", "agent", "tools", "cli", "cron"），`_ComponentFilter` 按前缀路由日志到对应文件 ^[hermes_logging.py:143-149, 126-138]
- Managed mode 权限：`_ManagedRotatingFileHandler` 在 NixOS 部署模式下确保日志文件为 group-writable（chmod 0660）^[hermes_logging.py:299-329]
- 详细模式：`setup_verbose_logging()` 添加 DEBUG 级别 StreamHandler，使用短时间格式 `%H:%M:%S`，用于 `--verbose` 调试 ^[hermes_logging.py:263-292]
- 幂等性：`_logging_initialized` 哨兵确保 `setup_logging()` 第二次调用为 no-op（除非 `force=True`）^[hermes_logging.py:38, 197-201]
- 日志配置回退：`_read_logging_config()` 尝试从 `config.yaml` 读取 `logging.level`、`logging.max_size_mb`、`logging.backup_count`，失败时使用默认值 ^[hermes_logging.py:370-390]

**源码证据**：
- 入口文件：hermes_logging.py
- 核心函数：`def setup_logging(*, hermes_home=None, log_level=None, ...)` ^[hermes_logging.py:156]、`def set_session_context(session_id)` ^[hermes_logging.py:72]
