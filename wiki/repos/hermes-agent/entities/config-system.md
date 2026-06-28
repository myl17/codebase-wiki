---
type: entity
repo: hermes-agent
slug: config-system
problem: 如何管理分布式配置（config.yaml + 环境变量），支持命令行、环境和 YAML 三层覆盖，以及 profile 隔离
generated: 2026-06-25
source_files:
  - gateway/config.py
  - hermes_cli/config.py
  - hermes_constants.py
  - hermes_time.py
---

# 配置系统

**代码位置**：`gateway/config.py`、`hermes_cli/config.py`、`hermes_constants.py`、`hermes_time.py`
**这个模块解决什么问题**：
- 实现层：GatewayConfig 定义 gateway 的平台配置、会话重置策略和流式设置；CLI config 提供 `config.yaml` 读写和 env var 覆盖；`hermes_constants.py` 提供配置路径解析和平台检测；`hermes_time.py` 提供时区管理
- 问题层：如何管理分布式配置（config.yaml + 环境变量），支持命令行、环境和 YAML 三层覆盖，以及 profile 隔离
**对外暴露什么**：`GatewayConfig` dataclass（gateway/config.py:222）、`Platform` enum（gateway/config.py:48）、`SessionResetPolicy`（gateway/config.py:101）、`load_config()` / `get_config()`（hermes_cli/config.py）、`get_hermes_home()`（hermes_constants.py:11）、`now()`（hermes_time.py:91）
**它和谁交互**：
- 被 [[entities/gateway-runner]] 调用（GatewayConfig 驱动平台适配器连接和会话策略）
- 被 [[entities/session-manager]] 调用（SessionResetPolicy）
- 被 [[entities/cli-system]] 调用（所有 CLI 命令读取配置）
- 被 [[entities/web-server]] 调用（API 读写配置）
- 被 [[entities/agent-core]] 调用（获取 provider/model/base_url 回退值）
- 被 [[entities/memory-system]] 调用（`memory.provider` 选择）
- 被 [[entities/plugin-system]] 调用（`context.engine` 选择）
- 被 [[entities/logging-system]] 调用（`logging.*` 配置）
- 被 [[entities/security-sandbox]] 调用（`security.*` 和 `command_allowlist`）
- 被 [[entities/terminal-execution]] 调用（`TERMINAL_ENV` 选择后端）
**为什么它是可分离的**：配置通过 `config.yaml` 文件 + 环境变量分层管理，各子系统仅读取自身关心的键

**关键机制**（源码可见）：
- 二十三层配置优先级：环境变量 > config.yaml > 代码默认值，`_expand_env_vars()` 在 YAML 加载后展开 `${VAR}` 引用 ^[hermes_cli/config.py]
- HERMES_HOME Profile 隔离：`get_hermes_home()` 返回 `Path(os.getenv("HERMES_HOME", ~/.hermes))`，Profile 模式下指向 `~/.hermes/profiles/<name>/` 实现完全独立配置 ^[hermes_constants.py:11-18]
- Subprocess HOME 隔离：`get_subprocess_home()` 返回 profile-scoped `home/` 目录作为子进程 HOME，隔离 git/ssh/gh 等工具配置 ^[hermes_constants.py:114-137]
- 时区管理：`hermes_time.now()` 按优先级 `HERMES_TIMEZONE env > config.yaml timezone > 服务器 local` 解析，缓存 ZoneInfo 避免重复 I/O ^[hermes_time.py:37-104]
- 18 种平台枚举：`Platform` enum 定义所有支持的 messaging 平台 ^[gateway/config.py:48-70]
- 三层重置策略：`SessionResetPolicy` 支持 `none/idle/daily/both` 四种模式和 per-platform/per-type 覆盖 ^[gateway/config.py:101-137, 319-350]
- 平台认证检测：`get_connected_platforms()` 根据平台类型检查不同的验证条件（token、http_url、api_key 等）^[gateway/config.py:261-317]
- 扩展配置：`PlatformConfig.extra` 字典允许平台自定义字段（如 QQ app_id、Webhook 回调 URL）^[gateway/config.py:144-190]
- 流式配置：`StreamingConfig` 控制编辑间隔（默认 1s）、缓冲区阈值（40 字符）和光标样式 ^[gateway/config.py:191-220]
- IPv4 偏好：`apply_ipv4_preference()` 通过 monkey-patch `socket.getaddrinfo` 解决 IPv6 不可达超时问题 ^[hermes_constants.py:249-288]

**源码证据**：
- 入口文件：gateway/config.py、hermes_cli/config.py、hermes_constants.py
- 核心类型：`@dataclass class GatewayConfig` ^[gateway/config.py:222]、`class Platform(enum.Enum)` ^[gateway/config.py:48]

**关联 Concept**：
- [[concepts/configuration-management]]
