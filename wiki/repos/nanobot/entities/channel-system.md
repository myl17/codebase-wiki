---
type: entity
repo: nanobot
slug: channel-system
problem: 如何让一个 Agent 核心同时支持多个聊天平台（Telegram/Discord/Slack 等）的接入
generated: 2026-06-25
source_files:
  - nanobot/channels/base.py
  - nanobot/channels/manager.py
  - nanobot/channels/registry.py
---

# Channel System

**代码位置**：`nanobot/channels/`
**这个模块解决什么问题**：
- 实现层：BaseChannel 定义统一接口（start/stop/send），ChannelManager 通过 pkgutil + entry_points 自动发现并管理所有启用的 Channel，协调消息路由和流式送达
- 问题层：如何让一个 Agent 核心同时支持多个聊天平台的接入
**对外暴露什么**：`BaseChannel` 抽象基类（nanobot/channels/base.py:15）、`ChannelManager` 类（nanobot/channels/manager.py:20）
**它和谁交互**：
- 依赖 [[entities/message-bus]]（消费 outbound 消息，发布 inbound 消息）
- 被 [[entities/agent-loop]] 调用（启动时通过 ChannelManager 初始化所有 channel）
- 依赖各平台 Channel 实现（telegram、discord、slack、whatsapp、feishu、wecom、weixin、dingtalk、qq、matrix、email、mochat）
**为什么它是可分离的**：通过 `discover_all()` 自动发现和 BaseChannel 接口实现 plugin 架构，添加新平台只需创建新 channel 子类

**关键机制**（源码可见）：
- Channel 自动发现：`discover_all()` 扫描 `nanobot.channels` 包的子模块 + entry_points 注册的 `nanobot.channels` 组，收集所有 `BaseChannel` 子类 ^[nanobot/channels/registry.py]
- 流式 Delta 合并：`_coalesce_stream_deltas()` 在 outbound 分发时将同一 (channel, chat_id) 的连续 `_stream_delta` 消息合并，减少 API 调用次数 ^[nanobot/channels/manager.py:198-246]
- 重试策略：发送失败时指数退避重试（1s, 2s, 4s），最大尝试次数由 `send_max_retries` 配置 ^[nanobot/channels/manager.py:17, 248-276]
- 访问控制：`BaseChannel.is_allowed()` 检查 `allow_from` 列表，空列表拒绝所有人，`"*"` 允许所有人 ^[nanobot/channels/base.py:117-125]
- 流式支持检测：`supports_streaming` property 同时检查配置 `streaming: true` 和子类是否覆盖了 `send_delta` 方法 ^[nanobot/channels/base.py:110-115]

**源码证据**：
- 入口文件：nanobot/channels/base.py、nanobot/channels/manager.py
- 核心类型/接口定义：`class BaseChannel` ^[nanobot/channels/base.py:15]、`class ChannelManager` ^[nanobot/channels/manager.py:20]

**关联 Concept**：
- [[concepts/channel-abstraction-pattern]]
