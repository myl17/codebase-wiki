# 消息平台适配的接口分解粒度

**问题陈述**：在为多平台 IM 系统设计适配器接口时，如何决定接口的拆分粒度——是单一抽象基类还是多个可选小接口？

**核心关切**：
- 关切 1：不同 IM 平台的能力差异巨大——不是所有平台都支持所有操作，大而全的接口会迫使简单平台实现空方法
- 关切 2：核心对 channel 的调用路径（入站解析、出站发送、生命周期）需要统一的接口约定——拆分过细会破坏调用的一致性
- 关切 3：新增平台的工作量应与所需能力成正比——简单平台不应被迫实现复杂接口
- 关切 4：抽象基类需要覆盖消息收发、会话管理、媒体处理、打字指示等异构能力——覆盖面的广度与接口简洁性直接冲突
- 关切 5：新增平台需要修改的代码点数量直接影响扩展成本——hermes 16 步 checklist vs openclaw 注册入口

---

## 已知权衡位置

### 位置 A：13+ Adapter 分解

**优先满足的关切**：关切 1（能力差异兼容）、关切 3（工作量与能力成正比）、关切 5（最小化扩展改动的代码点）

**接受妥协的关切**：关切 2（接口一致性——不同平台 adapter 组合不同，调用路径的强制统一性较弱）

**特征**：
- 将平台适配拆分为 13+ 独立的小接口（Adapter），每个代表一个能力维度
- 每个 Adapter 是**可选的**——平台只实现自己支持的能力维度
- 新增平台只需实现相关的 Adapter 并通过统一入口注册，不改动 core
- 每个 channel 作为独立 npm 包存在，SDK 依赖完全隔离

**关键机制**（源码可见）：
- `ChannelPlugin<ResolvedAccount>` 接口将平台能力拆分为 13+ 独立 Adapter：`ChannelMessagingAdapter`、`ChannelOutboundAdapter`、`ChannelLifecycleAdapter`、`ChannelAuthAdapter`、`ChannelSetupAdapter` 等（`types.plugin.ts:53-94`）。每个 Adapter 是可选接口——平台只实现自己支持的能力维度，不支持的功能不声明对应 Adapter
- `defineBundledChannelEntry` 统一注册入口，接受 `{ plugin, secrets, runtime, registerFull }` 四个模块引用，channel 代码通过 `loadBundledEntryExportSync` 按需懒加载，避免未使用的 channel 拖慢启动（`channel-entry-contract.ts:31-60`）

**代价**：
- 调用方需要检查 Adapter 是否存在再调用（类型安全的可选链），相比于统一接口的遍历更繁琐
- 不同平台 Adapter 组合各不相同，无法通过单一接口签名保证所有平台的调用一致性
- Debug 时需要额外理解每个平台到底实现了哪些 Adapter——全貌不如单一 ABC 一目了然

**已知实例**：openclaw（20+ 平台）

---

### 位置 B：单一 ABC 继承

**优先满足的关切**：关切 2（接口统一——所有平台走同一抽象路径）、关切 4（覆盖面的广度——统一接口涵盖消息收发、会话管理、媒体处理、打字指示等）

**接受妥协的关切**：关切 1（能力差异兼容——简单平台被迫实现空方法或抛出 `NotImplementedError`）、关切 3（工作量与能力成正比——简单平台仍需实现完整接口的表面结构）、关切 5（扩展成本——新增平台需按 16 步 checklist 修改 16 处代码）

**特征**：
- 所有平台适配器继承自同一个抽象基类 `BasePlatformAdapter`
- 基类定义统一的必须实现方法和可选覆盖方法
- `GatewayRunner` 统一管理所有 adapter 生命周期，以相同的模式路由消息进出 AIAgent
- 调用方无需检查能力是否存在——所有平台都有一致的接口签名

**关键机制**（源码可见）：
- `BasePlatformAdapter` 抽象基类定义 4 个 @abstractmethod 方法：`connect()`、`disconnect()`、`send()`、`get_chat_info()`，以及 8-9 个可选覆盖方法：`send_typing()`、`send_image()`、`send_document()`、`send_voice()`、`send_video()`、`send_animation()`、`edit_message()`、`stop_typing()`、`send_image_file()` 等（`base.py:813-893`）。不支持可选方法的平台继承默认空实现即可，@abstractmethod 方法对所有平台强制一致
- `GatewayRunner` 通过统一的 adapter 生命周期管理所有平台：初始化时遍历所有启用的 adapter 调用 `connect()`，消息到达时查找对应 adapter 的 session 并路由到 `AIAgent.run_conversation()`，响应通过 `DeliveryRouter` 路由回对应平台（`gateway/run.py:538-617`）。所有 adapter 走完全相同的代码路径，无分支检查能力差异

**代价**：
- 简单平台（如 Webhook、SMS）仍需实现 4 个 @abstractmethod 方法，即使某些方法（如 `get_chat_info()`）对自己不自然也需要在代码中存在；但可选覆盖方法（如 `send_typing()`、`send_image()`）继承默认实现即可
- 新增平台需按照 `ADDING_A_PLATFORM.md` 的 16 步 checklist 修改 adapter 本身、enum、factory、auth maps、session source、system prompt hints、toolset、cron delivery、send_message tool、channel directory、status display、gateway setup wizard、redaction、docs、tests 共 16 处代码
- 基类修改（如新增 @abstractmethod 方法）会波及所有 22 个平台实现

**已知实例**：hermes-agent（22 平台）

---

## 跨仓库对比

| | openclaw | hermes-agent |
|---|---|---|
| 权衡位置 | 13+ Adapter 分解 | 单一 ABC 继承 |
| 具体实现 | `ChannelPlugin<ResolvedAccount>` 接口内含 13+ 可选 Adapter（`ChannelMessagingAdapter`、`ChannelOutboundAdapter` 等），每个平台按需实现相关 Adapter；通过 `defineBundledChannelEntry` 统一注册入口，channel 代码懒加载（`types.plugin.ts:53-94`，`channel-entry-contract.ts:31-60`） | `BasePlatformAdapter` 抽象基类统一 4 个 @abstractmethod 方法（`connect`/`disconnect`/`send`/`get_chat_info`）和 8-9 个可选覆盖方法（`send_typing`/`send_image`/`send_document`/`send_voice`/`send_video`/`send_animation`/`edit_message`/`stop_typing`/`send_image_file` 等），所有 22 个平台通过 `GatewayRunner` 以相同抽象路径管理（`base.py:813-893`，`gateway/run.py:538-617`） |
| 优先满足的关切 | 关切 1（能力差异兼容）——可选 Adapter 使不支持某能力的平台不声明该接口；关切 3（工作量成正比）——只需实现相关 Adapter；关切 5（扩展成本）——新增平台只需实现 Adapter + 注册入口，不改 core | 关切 2（接口统一）——所有平台通过同一 `BasePlatformAdapter` 路径调用；关切 4（覆盖面广度）——统一接口涵盖消息收发、会话管理、媒体处理、打字指示 |
| 接受妥协的关切 | 关切 2（接口一致性）——不同平台 Adapter 组合不同，调用方需检查 Adapter 是否存在再调用 | 关切 1（能力差异兼容）——简单平台被迫实现不支持的方法；关切 3（工作量成正比）——简单平台仍需承接完整接口结构；关切 5（扩展成本）——新增平台需修改 16 处代码 |
| 新增平台改动范围 | 实现相关 Adapter + `defineBundledChannelEntry` 注册 = 1 个新目录内的 1-2 个文件 | 16 步 checklist：adapter 本身 + enum + factory + auth maps + session source + system prompt hints + toolset + cron delivery + send_message tool + channel directory + status display + setup wizard + redaction + docs + tests = ~16 处修改 |
| 平台数量 | 20+ | 22 |
| 注册方式 | 每个 channel 作为独立 npm 包，通过 `defineBundledChannelEntry` 声明式注册 | 在 factory map / enum / auth maps 等多处分发式注册 |
| 依赖隔离 | Channel SDK 各自独立声明在自身 `package.json` 中，不聚合到 root | 所有平台适配器在统一 codebase 中，无 SDK 级隔离 |

---

## 选择指南

| 场景 | 倾向 |
|---|---|
| 平台间能力差异极大（如 SMS 只发文本 vs Telegram 支持富媒体/Inline Keyboard/Poll） | **13+ Adapter 分解**——能力弱的平台不受冗余接口拖累 |
| 平台数量持续增长，且新平台大多为简单通道 | **13+ Adapter 分解**——简单平台的扩展成本低（实现 1-2 个 Adapter 即完成） |
| 核心调用路径需要强一致性保证（如所有平台必须经过相同的审核逻辑） | **单一 ABC 继承**——统一接口保证没有平台绕过关键路径 |
| 团队规模小，需要快速验证新平台 | **13+ Adapter 分解**——改动范围可控，不触及核心代码 |
| 基类本身稳定，能力模型高度一致（如所有平台都支持消息收发和会话管理） | **单一 ABC 继承**——接口膨胀风险低，统一下调用简洁 |
| 需要在编译时或类型系统层面强制执行接口契约 | **单一 ABC 继承**——ABC 的 `@abstractmethod` 在实例化时即报错，不会遗漏 |
| 第三方扩展者需要独立于主仓库发布平台适配器 | **13+ Adapter 分解**——独立 npm 包 + SDK 隔离，不依赖主仓库版本 |

---

## 溯源

| 仓库 | 验证过的源码文件 | 关键行号 |
|------|----------------|---------|
| openclaw | `src/channels/plugins/types.plugin.ts` | `:53-94`（`ChannelPlugin<ResolvedAccount>` 接口定义，13+ Adapter 拆分） |
| openclaw | `src/plugin-sdk/channel-entry-contract.ts` | `:31-60`（`defineBundledChannelEntry` 统一注册入口，channel 按需懒加载） |
| hermes-agent | `gateway/platforms/base.py` | `:813-893`（`BasePlatformAdapter` 抽象基类，4 @abstractmethod 方法 + 8-9 可选覆盖方法） |
| hermes-agent | `gateway/platforms/ADDING_A_PLATFORM.md` | `:1-313`（新增平台 16 步 checklist，扩展成本量化） |
| hermes-agent | `gateway/run.py` | `:538-617`（`GatewayRunner` 统一 adapter 生命周期管理） |

> **注**：本次验证通过 wiki/repos/ 下的架构分析文档（维度页和节点页）交叉确认上述源码位置和机制描述。源码原始文件未在 wiki/repos/ 中存放，溯源行号来自维度提取阶段的标注，后续可通过直接读取原始仓库源码做二次验证。

---
## 修复记录

**2026-06-19（v2 验证修复）**：
- **方法计数错误（❌→✅）**：源码验证发现 `BasePlatformAdapter` 只有 4 个 `@abstractmethod` 方法（`connect`/`disconnect`/`send`/`get_chat_info`），而非原 Concept 页声称的 6 个。`send_typing` 和 `send_image` 在源码中有默认实现（`pass` 和 fallback 文本发送），属于可选覆盖方法。全局将「6 个必须实现方法」修正为「4 个 @abstractmethod 方法，另有 8-9 个可选覆盖方法」。
- **可选方法数量修正（⚠️→✅）**：原 Concept 页称 5 个可选覆盖方法，源码验证确认至少 8-9 个可选覆盖方法（增加 `edit_message`、`stop_typing`、`send_image_file` 等），已全局更新。
