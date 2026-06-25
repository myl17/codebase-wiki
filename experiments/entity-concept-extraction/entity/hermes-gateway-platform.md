# GatewayRunner + 平台适配器（Hermes Agent）

## 是什么 / 边界

GatewayRunner 是多平台消息网关控制器，管理所有平台适配器（22 个）的生命周期，负责消息路由进出 agent、会话查找与创建、记忆上下文注入，以及跨消息复用 AIAgent 实例（以维持 prompt cache）。

BasePlatformAdapter 是 20+ 消息平台的抽象基类，统一消息收发、会话管理、媒体处理接口。

不做：tool-calling 逻辑（由 AIAgent 处理）、安全审批（由 ApprovalSystem 处理）、记忆内容的实际存储（由 MemoryManager 处理）。

## 关键实现

- GatewayRunner：`gateway/run.py:538`
- Agent 实例缓存（跨消息复用）：`gateway/run.py:604-611`
- BasePlatformAdapter 抽象基类：`gateway/platforms/base.py:813-893`
- 会话管理：`gateway/session.py`（SQLite + FTS5，PII 哈希化）
- 运行时状态：`gateway/status.py`（PID 文件 + 状态 JSON）
- 消息路由：`gateway/delivery.py`，`DeliveryRouter`
- 新增平台 checklist：`gateway/platforms/ADDING_A_PLATFORM.md`（16 步）

已实现平台：Telegram、Discord、Slack、WhatsApp、Signal、Matrix、BlueBubbles（iMessage）、HomeAssistant、Email、SMS、Mattermost、DingTalk、Feishu、WeCom、Weixin、QQBot、Webhook、API Server 等 22 个。

## 设计选择记录

- **维度**：Architecture
- **选择**：GatewayRunner 跨消息缓存 AIAgent 实例，而非每条消息新建实例
- **替代方案**：每条消息创建新的 AIAgent 实例
- **为什么有这个选择**：复用实例可以保持 LLM API 层的 prompt cache prefix 在跨消息对话中持续有效，降低 input token 成本；每次新建实例会打断 cache prefix

---

- **维度**：Architecture
- **选择**：所有平台通过 BasePlatformAdapter 统一接口，新增平台需修改 16 处配置点
- **替代方案**：每个平台完全独立实现，不共享基类
- **为什么有这个选择**：统一接口确保 toolset、认证映射、cron delivery 等跨平台逻辑只写一次；16 处修改点是为了让所有集成点都感知新平台的存在，不遗漏

---

- **维度**：Architecture
- **选择**：Gateway 审批使用 FIFO 队列 + threading.Event，agent 线程阻塞等待用户 /approve 或 /deny
- **替代方案**：超时自动拒绝，不阻塞等待用户响应
- **为什么有这个选择**：消息平台场景下用户不在场的时间较长，自动超时拒绝会中断合法任务；阻塞等待保证用户有机会审批，代价是 agent 线程占用
