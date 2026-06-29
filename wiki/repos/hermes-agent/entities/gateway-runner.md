---
type: entity
repo: hermes-agent
slug: gateway-runner
problem: 如何管理多平台消息适配器的生命周期，将不同聊天平台的入站消息路由到统一的 Agent 并返回响应
generated: 2026-06-25
source_files:
  - gateway/run.py
  - gateway/stream_consumer.py
  - gateway/delivery.py
  - gateway/hooks.py
  - gateway/pairing.py
---

# Gateway 运行器

**代码位置**：`gateway/run.py`、`gateway/stream_consumer.py`、`gateway/delivery.py`、`gateway/hooks.py`
**这个模块解决什么问题**：
- 实现层：GatewayRunner 管理所有平台适配器的生命周期（连接、重连、关闭），将入站消息路由到 AIAgent 执行并流式返回响应，支持中断、agent 缓存、语音模式和优雅重启
- 问题层：如何管理多平台消息适配器的生命周期，将不同聊天平台的入站消息路由到统一的 Agent 并返回响应
**对外暴露什么**：`GatewayRunner` 类（gateway/run.py:538）、`start_gateway()` 函数（gateway/run.py:9537）、`GatewayStreamConsumer` 类（gateway/stream_consumer.py:48）、`DeliveryRouter` 类（gateway/delivery.py:107）、`HookRegistry` 类（gateway/hooks.py:34）
**它和谁交互**：
- 依赖 [[entities/platform-adapters]]（18 个平台适配器实例，通过 `_create_adapter()` 工厂创建）
- 依赖 [[entities/session-manager]]（会话创建、重置策略、上下文注入）
- 依赖 [[entities/agent-core]]（为每条入站消息创建/复用 AIAgent）
- 依赖 [[entities/security-sandbox]]（DM 配对授权、会话级命令审批）
- 依赖 [[entities/config-system]]（GatewayConfig 驱动的平台配置）
- 依赖 [[entities/state-database]]（SQLite 会话持久化）
- 依赖 [[entities/cron-scheduler]]（每 60s 调用 tick()）
- 依赖 [[entities/memory-system]]（Honcho 管理器跨消息持久化）
- 依赖 [[entities/process-registry]]（会话重置时检查活跃后台进程）
**为什么它是可分离的**：GatewayRunner 是独立控制器类，接收 GatewayConfig 和平台适配器注册表，不绑定任何单一平台或传输层

**关键机制**（源码可见）：
- Agent 缓存：`_agent_cache` 按 session_key 缓存 AIAgent 实例，保留 prompt caching 前缀，避免每消息重建系统提示词导致 ~10x 成本增加 ^[gateway/run.py:604-611]
- 中断支持：`_running_agents` 跟踪活跃会话的 AIAgent 引用，接收 `/stop` 或新消息时可通过 agent.set_interrupt() 中断 ^[gateway/run.py:597-602]
- 会话级模型覆盖：`_session_model_overrides` 支持 `/model` 命令在单会话内切换模型 ^[gateway/run.py:615]
- 平台重连观察者：`_failed_platforms` 记录首次连接失败的平台，后台定时器 `_platform_reconnect_watcher` 定期重试 ^[gateway/run.py:620-622, 2015]
- 流式编辑：`GatewayStreamConsumer` 将同步 agent delta 回调桥接到异步平台消息编辑（Telegram/Discord/Slack 支持 editMessageText），支持 think-block 过滤、防 flood 退避 ^[gateway/stream_consumer.py:48-170]
- 优雅重启：`_restart_requested` 标志触发 drain 模式，等待活跃会话完成后重启；`--replace` 标志先 kill 已有实例 ^[gateway/run.py:552-557]
- 进程注册保护：会话重置时检查 `process_registry.has_active_for_session()`，活跃进程的会话不重置 ^[gateway/run.py:577-581]
- Hook 事件系统：支持 `gateway:startup`、`session:start`、`agent:step`、`command:*` 等事件，用户可在 `~/.hermes/hooks/` 注册处理器 ^[gateway/hooks.py:34-169]
- DM 配对授权：PairingStore 用加密随机码（8 字符，1h 过期）实现用户授权，支持速率限制（10min/请求）和锁定（5 次失败锁定 1h）^[gateway/pairing.py:75-193]

**源码证据**：
- 入口文件：gateway/run.py
- 核心类型/接口定义：`class GatewayRunner` ^[gateway/run.py:538]、`async def start_gateway()` ^[gateway/run.py:9537]

**关联 Concept**：
- [[concepts/channel-abstraction-pattern]]
