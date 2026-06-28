---
type: entity
repo: hermes-agent
slug: session-manager
problem: 如何管理跨平台的会话身份、上下文注入和自动重置策略，保证用户在不同平台和间隔时间上的连续或不连续体验
generated: 2026-06-25
source_files:
  - gateway/session.py
  - gateway/channel_directory.py
  - gateway/session_context.py
---

# 会话管理器

**代码位置**：`gateway/session.py`、`gateway/channel_directory.py`
**这个模块解决什么问题**：
- 实现层：SessionStore 管理会话的生命周期（创建、检索、重置、挂起），通过确定性 session_key 实现跨平台会话识别，支持三种重置策略（idle/daily/both）和断点续传；SessionContext 注入平台上下文到 agent 系统提示词
- 问题层：如何管理跨平台的会话身份、上下文注入和自动重置策略，保证用户在不同平台和间隔时间上的连续或不连续体验
**对外暴露什么**：`SessionStore` 类（gateway/session.py:498）、`SessionEntry` dataclass（gateway/session.py:332）、`SessionContext` dataclass（gateway/session.py:142）、`SessionSource` dataclass（gateway/session.py:66）、`build_session_key()`（gateway/session.py:439）、`build_session_context_prompt()`（gateway/session.py:186）
**它和谁交互**：
- 依赖 [[entities/config-system]]（SessionResetPolicy 配置、GatewayConfig）
- 依赖 [[entities/state-database]]（SQLite 会话持久化和计数）
- 依赖 [[entities/process-registry]]（检查活跃进程阻止重置）
- 被 [[entities/gateway-runner]] 调用（消息处理前后）
- 被 [[entities/agent-core]] 调用（获取会话上下文注入系统提示词）
**为什么它是可分离的**：SessionStore 是独立存储层，接收 config + session_db + process_check callback，不绑定特定平台或 agent 实现

**关键机制**（源码可见）：
- 确定性 session_key：`build_session_key()` 使用 `agent:main:<platform>:<chat_type>:<chat_id>[:<thread_id>]` 格式，DM 按 chat_id 隔离，群组/频道可选按 user_id 隔离 ^[gateway/session.py:439-496]
- 三层重置策略：支持 `none`（永不重置）、`idle`（空闲超时，默认 24h）、`daily`（每日固定时间，默认 4 AM）、`both`（同时满足）^[gateway/session.py:620-684]
- 重置通知: 自动重置时向用户发送通知（含重置原因），`notify_exclude_platforms` 可排除 webhook/api_server 等非用户平台 ^[gateway/config.py:101-137]
- 挂起机制：`/stop` 或异常关闭时设置 `suspended=True`，下次消息到达时强制自动重置 ^[gateway/session.py:789-803]
- PII 脱敏：WhatsApp/Signal/Telegram/BlueBubbles 平台的 sender_id 和 chat_id 在 system prompt 中通过 SHA-256 确定性哈希脱敏 ^[gateway/session.py:34-54]
- 会话上下文注入：`build_session_context_prompt()` 生成 "Session Context" 块，告知 agent 当前来源、已连接平台、home channel 和发送选项 ^[gateway/session.py:186-330]
- Channel 目录：`ChannelDirectory` 管理 group/channel 的注册和配置，支持 channel-level prompt 和 `sethome` 命令 ^[gateway/channel_directory.py]

**源码证据**：
- 入口文件：gateway/session.py
- 核心类型/接口定义：`class SessionStore` ^[gateway/session.py:498]、`@dataclass class SessionEntry` ^[gateway/session.py:332]

**关联 Concept**：
- [[concepts/session-lifecycle-management]]
