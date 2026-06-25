# Channel Plugin 系统（OpenClaw）

## 是什么 / 边界

Channel Plugin 系统是 OpenClaw 的 IM 平台适配层：将 20+ 种 IM 平台（WhatsApp、Telegram、Slack、Discord、Signal、iMessage、Feishu、LINE 等）的消息协议统一抽象为标准接口，向上游提供一致的入站/出站消息流。不决定 AI 如何响应，不持有对话状态，不做工具调用权限判断。

## 关键实现

- 插件接口定义：`src/channels/plugins/types.plugin.ts`（`ChannelPlugin<ResolvedAccount>` + 13+ Adapter 接口）
- 主要 Adapter：`ChannelMessagingAdapter`、`ChannelOutboundAdapter`、`ChannelLifecycleAdapter`、`ChannelAuthAdapter`、`ChannelSetupAdapter`
- 各 channel 实现：`extensions/<channel-name>/`（每个为独立 npm 包）
- 入口格式：每个 channel package 的 `index.ts` 导出 `defineBundledChannelEntry(...)` 的返回值
- 按需加载机制：`src/plugin-sdk/channel-entry-contract.ts`（`loadBundledEntryExportSync`）
- 入站防抖：`src/channels/inbound-debounce-policy.ts`

## 设计选择记录

- **维度**：Dependency Strategy
- **选择**：每个 channel 是独立 npm 包，只声明自己需要的 SDK，通过 `workspace:*` 引用内部 plugin-sdk
- **替代方案**：所有 channel SDK 统一安装在 root package，共享一套依赖
- **为什么有这个选择**：故障域完全隔离——任何单个 channel SDK 变动不影响核心运行时；用户按需安装 channel，不拉入无关 SDK

---

- **维度**：Performance Tradeoffs
- **选择**：`defineBundledChannelEntry` 让 channel 代码只在该 channel 被实际使用时才加载（懒加载）
- **替代方案**：启动时加载所有已安装 channel 的代码
- **为什么有这个选择**：多数用户只配置少数 channel，提前加载所有 channel 代码会拖慢启动速度并浪费内存

---

- **维度**：Performance Tradeoffs
- **选择**：入站消息做防抖（`inbound-debounce-policy`），合并短时间内连续到达的多条消息再触发 LLM 调用
- **替代方案**：每条消息独立触发一次 LLM 调用
- **为什么有这个选择**：用户习惯分多条消息表达一个完整意图，防抖可以减少因此触发的多余 LLM 调用；代价是引入最大 debounce 延迟
