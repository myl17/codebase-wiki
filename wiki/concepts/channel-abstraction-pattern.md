---
type: concept
concept: channel-abstraction-pattern
problem: 如何用统一接口抽象 Telegram、Discord、WhatsApp 等异构消息平台，使 Agent 核心逻辑不感知平台差异
concerns: [接口抽象粒度（thin vs thick）, 平台特有能力的暴露程度, 第三方扩展便利性]
repos: [nanobot, hermes-agent, openclaw]
generated: 2026-06-25
---

# Channel 抽象模式

## 核心问题

一个 AI Agent 框架要成为用户的"无处不在的助手"，必须同时支持 Telegram、Discord、Slack、WhatsApp、微信、飞书等数十个通讯平台。但这些平台的 API 模型、消息格式、媒体处理、交互模式（DM vs 群组 vs 频道 vs 线程）完全不同。框架需要定义一套抽象接口，让 Agent 核心逻辑写一次就能对接所有平台。

根本张力在于**接口抽象粒度**：接口如果太薄（只有 `send(text)` 和 `receive()`），平台特有能力（如 Telegram 的 inline keyboard、Discord 的 embed、Slack 的 block kit）就无法被 Agent 利用，体验降级为"所有平台都是纯文本终端"。接口如果太厚（定义完整的富交互模型），每个新平台适配的成本急剧增加，且会产生"最小公分母"问题——某些平台不支持某些能力，导致适配器里充满空实现或模拟逻辑。

第二个张力是**扩展机制**：第三方如何添加新平台？是修改框架源码提交 PR，还是通过插件机制外部注册？三个框架都选择了某种形式的自动发现/注册机制，但发现方式和注册粒度的差异决定了生态扩展的便利性和安全性。

## 关切

- **接口抽象粒度（thin vs thick）**：接口定义了多少平台能力——仅消息收发，还是涵盖富交互、线程管理、目录服务等完整能力面
- **平台特有能力的暴露程度**：Agent 能否利用 Telegram 的 inline keyboard、Discord 的 slash command、Slack 的 block kit 等平台特有交互
- **第三方扩展便利性**：添加新平台需要修改框架源码还是可以外部注册；发现机制是扫描文件系统、entry_points 注册还是 manifest 声明

## 各框架的解法

### nanobot

来源：[[repos/nanobot/entities/channel-system]]
**解法**：`BaseChannel` ABC 定义薄接口（`start`/`stop`/`send`/`send_delta`），12 个内置适配器，通过 `pkgutil` 扫描子模块 + `entry_points` 注册实现自动发现。
**实现**：
- 薄 ABC 接口：`BaseChannel` 定义 `start()`、`stop()`、`send()`、`send_delta()` 四个核心方法 + `supports_streaming`/`is_allowed()` 辅助 property ^[nanobot/channels/base.py:15]
- 自动发现：`discover_all()` 扫描 `nanobot.channels` 包的子模块 + `entry_points` 组 `nanobot.channels`，收集所有 `BaseChannel` 子类 ^[nanobot/channels/registry.py]
- 流式 Delta 合并：`_coalesce_stream_deltas()` 在 outbound 分发时将同一 (channel, chat_id) 的连续 `_stream_delta` 消息合并，减少 API 调用次数 ^[nanobot/channels/manager.py:198-246]
- 重试与访问控制：发送失败指数退避重试（1s, 2s, 4s，最大次数可配置）；`is_allowed()` 检查 `allow_from` 白名单 ^[nanobot/channels/base.py:117-125]
- 12 个内置平台：Telegram、Discord、Slack、WhatsApp、Feishu、WeCom、Weixin、DingTalk、QQ、Matrix、Email、Mochat ^[nanobot/channels/]
**权衡**：薄接口使得适配器实现极简——每个新平台只需约 100-300 行代码。但平台特有交互能力几乎为零——所有平台都被降级为"收发文本+图片"的通用终端，Telegram 的 inline button、Discord 的 embed 等高级特性无法被 Agent 利用。entry_points 注册 + 源码扫描双通道提供了灵活的扩展方式。

### hermes-agent

来源：[[repos/hermes-agent/entities/platform-adapters]]、[[repos/hermes-agent/entities/gateway-runner]]
**解法**：`BasePlatformAdapter` ABC 定义厚接口（`connect`/`disconnect`/`send`/`edit_message`/`send_reaction` 等），18 个内置适配器，工厂函数创建，`GatewayStreamConsumer` 统一流式输出。
**实现**：
- 厚 ABC 接口：`connect()`、`disconnect()`、`send()` → `SendResult`、`edit_message()`（流式溢出）、`send_reaction()` 等，覆盖发送、编辑、交互能力 ^[gateway/platforms/base.py:813-996]
- 18 个平台适配器：Telegram（inline keyboard + 命令 + CallbackQuery）、Discord（Bot + Intents + 频道/线程/DM）、Slack（Socket Mode + block kit + 线程）、WhatsApp、Signal、Matrix、Mattermost、Feishu（最大单文件 165KB，含卡片/审批流/回调）、WeChat（公众号 + 企业微信 + 企业微信回调 + 加解密）、DingTalk、QQ、BlueBubbles（iMessage）、Email、SMS、Home Assistant、Webhook + API Server ^[gateway/platforms/]
- 消息归一化：`MessageEvent` 将各平台原生消息统一为 `text`、`message_type`、`source`、`media_urls`、`reply_to_text`、`auto_skill` 等字段 ^[gateway/platforms/base.py:655-720]
- 流式编辑：`GatewayStreamConsumer` 将 agent delta 回调桥接到平台 `edit_message`（Telegram/Discord/Slack 支持实时编辑消息文本），含 think-block 过滤和防 flood 退避 ^[gateway/stream_consumer.py:48-170]
- 扩展指南：`ADDING_A_PLATFORM.md` 提供完整步骤模板（ABC 实现 → 注册 Platform enum → 工厂注册 → 配置文档）^[gateway/platforms/ADDING_A_PLATFORM.md]
**权衡**：厚接口保留了平台特有交互——Agent 可以利用 inline keyboard、embed、thread 等高级特性（如 Telegram 适配器通过 CallbackQuery 实现交互式按钮）。但适配器实现较重——最大的 Feishu 适配器 165KB，各平台间实现复杂度差异大。工厂创建方式将平台注册与框架源码耦合——新平台需修改源码并注册到 Platform enum。

### openclaw

来源：[[repos/openclaw/entities/channel-system]]
**解法**：`ChannelPlugin` TypeScript 类型定义 30+ 功能 adapter，插件化的 manifest-first 注册，内置渠道 ID 枚举 + 懒加载注册表。
**实现**：
- 30+ adapter 分解：将渠道能力分解为 30+ 独立 adapter——`config`、`setup`、`pairing`、`security`、`gateway`、`outbound`、`status`、`messaging`、`threading`、`directory`、`lifecycle`、`doctor`、`streaming`、`agentPrompt`、`messageAction`、`allowlist`、`secrets`、`elevated`、`commands`、`resolver`、`heartbeat`、`agentTools`、`approvalCapability` 等——每个 adapter 可选实现 ^[src/channels/plugins/types.plugin.ts:53-97]
- 渠道能力标志：`ChannelCapabilities` 声明式描述平台能力（`chatTypes`、`polls`、`reactions`、`threads`、`media`），Agent 可查询可用能力 ^[src/channels/plugins/types.core.ts]
- 渠道 ID 双层体系：`ChatChannelId` 枚举（内置渠道）+ 插件注册的任意字符串 ID，manifest-first 的 ID 系统确保一致性 ^[src/channels/ids.ts]
- 懒加载注册表：从 `getActivePluginChannelRegistryFromState()` 获取，不直接导入渠道插件，避免拉入重型模块 ^[src/channels/registry.ts:28]
- 出站三模式：`direct`（渠道直发）、`gateway`（通过网关）、`hybrid`（混合），适配不同部署拓扑 ^[src/channels/plugins/types.adapters.ts]
- 渠道健康探针：每个渠道可选 `ChannelStatusAdapter` 提供连通性检测 ^[src/channels/plugins/types.core.ts]
**权衡**：30+ adapter 的细粒度分解使第三方可以渐进式实现——新渠道可以先实现 3-5 个核心 adapter 即可运行，后续逐步添加 `threading`、`reactions` 等高级能力。但 adapter 碎片化增加了理解和组合成本——需要了解 30+ adapter 各自的职责和交互才能完整对接一个平台。懒加载注册表 + manifest-first ID 提供了最强的第三方扩展便利性（不修改框架源码），但也引入了插件系统本身的复杂度。

## 对比

| 框架 | 接口抽象粒度 | 平台特有能力的暴露程度 | 第三方扩展便利性 |
|------|------|------|------|
| nanobot | 薄——4 个核心方法 + 2 个 property；所有平台降级为通用终端 | 极低——无 inline keyboard、embed、thread 等高级交互；纯文本+图片 | 高——entry_points 注册 + 源码扫描双通道；新平台只需实现 ~300 行子类 |
| hermes-agent | 厚——send/edit/react/connect 等完整方法；流式编辑桥接到平台原生编辑 API | 高——Agent 可利用 Telegram CallbackQuery、Slack block kit、Feishu 审批流 | 中——需修改源码（Platform enum + 工厂注册）；但有 `ADDING_A_PLATFORM.md` 完整指南 |
| openclaw | 极细粒度分解——30+ 可选 adapter；渐进式能力实现 | 最高——`ChannelCapabilities` 声明式能力查询，Agent 可感知平台差异 | 最高——插件化 manifest-first 注册，懒加载，不修改框架源码即可添加渠道 |

## 子维度观察

以下问题空间当前因跨仓库成熟度不足而未独立成 Concept，记录为父页面的子维度。若未来更多仓库将其演化为独立子系统，可通过 Split 操作升级。

### Channel-Agent Core 消息传输层解耦

- **来源信号**：2026-06-25 hermes-agent + openclaw 跨仓库对比（信号 2，粒度不匹配）
- **涉及仓库**：nanobot（message-bus：asyncio.Queue 实现 Channel↔Agent 异步解耦）、hermes-agent（消息流内嵌在 gateway-runner 中）、openclaw（消息流内嵌在 gateway 中）
- **当前判断**：仅 nanobot 将消息传输作为独立 entity（message-bus）。hermes-agent 和 openclaw 将消息流内嵌在 gateway 中，不将其作为独立层。可能说明"独立消息总线"不是此领域的普遍模式，gateway 统一处理消息流是主流做法。
- **升级条件**：至少 2 个以上仓库引入独立消息总线层解耦 Channel 和 Agent Core，且方案间存在可对比的 trade-off（如 Queue vs Pub/Sub vs Channel 模式）。

## 演化记录

- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-25：记录子维度观察「Channel-Agent Core 消息传输层解耦」[触发: evolve-signals]
