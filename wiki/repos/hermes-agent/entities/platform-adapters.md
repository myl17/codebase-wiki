---
type: entity
repo: hermes-agent
slug: platform-adapters
problem: 如何通过统一接口对接 18 个通讯平台，实现消息接收、格式化回复和平台特有功能
generated: 2026-06-25
source_files:
  - gateway/platforms/base.py
  - gateway/platforms/telegram.py
  - gateway/platforms/discord.py
  - gateway/platforms/slack.py
  - gateway/platforms/whatsapp.py
  - gateway/platforms/signal.py
  - gateway/platforms/matrix.py
  - gateway/platforms/mattermost.py
  - gateway/platforms/feishu.py
  - gateway/platforms/weixin.py
  - gateway/platforms/wecom.py
  - gateway/platforms/wecom_callback.py
  - gateway/platforms/dingtalk.py
  - gateway/platforms/qqbot.py
  - gateway/platforms/bluebubbles.py
  - gateway/platforms/email.py
  - gateway/platforms/sms.py
  - gateway/platforms/homeassistant.py
  - gateway/platforms/webhook.py
  - gateway/platforms/api_server.py
  - gateway/platforms/helpers.py
---

# 平台适配器

**代码位置**：`gateway/platforms/` 目录（20+ 文件）
**这个模块解决什么问题**：
- 实现层：18 个平台适配器实现统一的 `BasePlatformAdapter` 抽象接口（connect → handle message → send response），每个适配器封装平台 SDK 的认证、消息格式化和媒体处理
- 问题层：如何通过统一接口对接 18 个通讯平台，实现消息接收、格式化回复和平台特有功能
**对外暴露什么**：`BasePlatformAdapter` ABC（gateway/platforms/base.py:813）、`MessageEvent` dataclass（base.py:655）、`SendResult` dataclass（base.py:723）、18 个具体适配器类
**它和谁交互**：
- 依赖 [[entities/gateway-runner]]（GatewayRunner 通过 `_create_adapter()` 工厂创建、连接和管理所有适配器）
- 依赖 [[entities/session-manager]]（适配器通过 `MessageEvent.source` 传入 SessionSource 用于会话标识）
- 依赖 [[entities/config-system]]（PlatformConfig 驱动平台认证和配置）
- 依赖 [[entities/security-sandbox]]（PairingStore 用于 DM 配对授权）
- 被 [[entities/gateway-runner]] 调用（GatewayRunner 将适配器存储在 `self.adapters` 字典中）
- 被 [[entities/cron-scheduler]] 调用（定时任务通过 adapter.send() 交付结果）
**为什么它是可分离的**：所有适配器继承同一 ABC，通过 Platform enum 选择实例；添加新平台只需实现 ABC 并注册到工厂

**关键机制**（源码可见）：
- 统一 ABC 接口：`connect()`（连接平台）、`disconnect()`（断开）、`send(chat_id, content, reply_to, metadata) → SendResult`（发送消息）、`edit_message(chat_id, message_id, text)`（编辑消息，用于流式溢出）^[gateway/platforms/base.py:813-996]
- 18 个平台适配器：Telegram、Discord、Slack、WhatsApp、Signal、Matrix、Mattermost、Feishu/Lark、WeChat、WeCom、WeCom Callback、DingTalk、QQ、BlueBubbles（iMessage）、Email、SMS、Home Assistant、Webhook + API Server（gateway 内部 API）^[gateway/platforms/]
- 消息事件归一化：`MessageEvent` 将各平台的原生消息格式统一为 `text`、`message_type`、`source`（SessionSource）、`media_urls`、`media_types`、`reply_to_text`、`auto_skill` ^[gateway/platforms/base.py:655-720]
- 平台认证保护：`get_connected_platforms()` 按平台类型检查不同条件（token、http_url、enabled flag 等）^[gateway/config.py:261-317]
- Telegram 适配器：使用 `python-telegram-bot`，支持命令处理、CallbackQuery、消息线程、链接预览和 inline keyboard ^[gateway/platforms/telegram.py]
- Discord 适配器：使用 `discord.py` Bot + Intents，支持服务器频道、线程、DM 和 channel-level prompt ^[gateway/platforms/discord.py]
- Slack 适配器：使用 `slack-bolt` Socket Mode + AsyncWebClient，支持通道、线程和 block kit 消息 ^[gateway/platforms/slack.py]
- Feishu 适配器：最大单个适配器文件（165KB），支持 Lark/Feishu 完整的消息、卡片、审批流和回调 ^[gateway/platforms/feishu.py]
- 微信适配器：`weixin.py`（公众号）+ `wecom.py`（企业微信）+ `wecom_callback.py`（企业微信回调）+ `wecom_crypto.py`（加解密工具）^[gateway/platforms/weixin.py, wecom.py]
- QQ 适配器：通过 `aiohttp`/`httpx` 对接 QQ Bot API，需要 `app_id` 和 `client_secret` ^[gateway/platforms/qqbot.py]
- 添加新平台指南：`ADDING_A_PLATFORM.md` 提供了完整的步骤模板（ABC 实现 → 注册 Platform enum → 工厂注册 → 配置文档）^[gateway/platforms/ADDING_A_PLATFORM.md]

**源码证据**：
- 入口文件：gateway/platforms/base.py
- 核心类型：`class BasePlatformAdapter(ABC)` ^[gateway/platforms/base.py:813]、`@dataclass class MessageEvent` ^[gateway/platforms/base.py:655]

**关联 Concept**：
- [[concepts/channel-abstraction-pattern]]
