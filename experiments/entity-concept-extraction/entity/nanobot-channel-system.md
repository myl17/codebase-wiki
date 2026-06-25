# Channel System（nanobot）

## 是什么 / 边界
nanobot 的 IM 平台插件架构——双层发现机制（内置 pkgutil 自发现 + 外部 entry_points 插件），所有 channel 继承 `BaseChannel` ABC，由 `ChannelManager` 统一编排。

**边界**：Channel System 负责 IM 平台的消息收发适配——接收平台消息转为 InboundMessage、接收 OutboundMessage 转为平台消息发送。不做消息编排（AgentLoop）、不做自然语言理解。

## 关键实现
- **内置 Channel 自发现**：`pkgutil.iter_modules()` 自动扫描 `channels/` 下所有模块，查找 `BaseChannel` 子类——新增 Python 文件即自动可被发现，无需注册
- **外部插件**：Python `entry_points` 机制（`nanobot.channels` 组），支持 pip 可安装的第三方 channel 插件
- **优先级保护**：内置 channel 覆盖外部同名插件——外部插件不能 shadow 内置 channel 名称
- **依赖隔离**：每个 Channel 是独立模块（`channels/telegram.py`、`channels/slack.py` 等），只 import 自己需要的 SDK，telegram.py 不会 import slack_sdk
- **可选安装**：各平台 SDK 通过 pip extras 按需安装（`pip install nanobot-ai[telegram,discord]`）
- **内置 14 个 channel**：Telegram、Slack、WhatsApp、Discord、微信、飞书、钉钉、QQ、Line、Matrix、iMessage、Email、Terminal、WebChat

## 设计选择记录
- **维度**：Extension Points
- **选择**：双层 Channel 发现——pkgutil.iter_modules() 内置自发现 + entry_points 外部插件
- **替代方案**：集中注册表（所有 channel 在一个配置文件中显式列出），或纯 entry_points（无内置自发现）
- **为什么有这个选择**：内置 channel 用 pkgutil 自发现消除了注册文件维护成本——新增 Python 文件即自动可用。entry_points 保留外部插件能力。内置优先覆盖策略防止第三方插件 shadow 内置功能
