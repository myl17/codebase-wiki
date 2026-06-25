# 平台适配接口粒度

## 问题陈述

当一个 AI Agent 框架需要支持 20+ 种消息平台（WhatsApp、Telegram、Slack、Discord、Signal、iMessage、LINE、Feishu 等）时，核心问题是：如何为这些平台定义适配接口——按功能维度拆分为多个细粒度接口让平台按需实现，还是提供一个统一的抽象基类要求所有平台实现全部方法？这个选择直接影响新平台的接入成本、接口演进的灵活性，以及跨平台功能的复用程度。

## 已知答案图谱

### 方案 A：细粒度 Adapter 接口
- 特征：将平台适配拆分为 13+ 个独立的 Adapter 接口（`ChannelMessagingAdapter`、`ChannelOutboundAdapter`、`ChannelLifecycleAdapter`、`ChannelAuthAdapter`、`ChannelSetupAdapter` 等），每个接口聚焦单一职责；平台可以选择性实现自己需要的接口，不需要的接口完全不感知
- 优势：接口职责清晰，每个 Adapter 的方法集内聚；新平台只需实现最小必要接口子集即可运行，接入门槛低；各接口独立演进，修改一个不影响其他；按需加载时只加载实际使用的 Adapter 代码
- 劣势：接口数量多，新开发者需要理解各 Adapter 的分工才能正确选择；跨平台的通用逻辑需要在多个 Adapter 之间协调；可能出现不同平台实现了不同 Adapter 子集导致能力不一致

### 方案 B：统一抽象基类 + Checklist
- 特征：定义一个 `BasePlatformAdapter` 抽象基类，所有平台必须继承并实现全部抽象方法；新增平台时遵循标准化的 16 步 checklist，确保所有集成点（toolset、认证映射、cron delivery、消息路由等）都感知到新平台的存在
- 优势：统一接口确保跨平台逻辑只写一次——toolset 分配、认证映射、cron delivery 等对所有平台一致生效；16 步 checklist 作为新增平台的标准操作手册，防止遗漏集成点；所有平台能力一致，不存在接口子集差异
- 劣势：新增平台的成本固定（16 处修改点），即使简单平台也需要完成全部步骤；基类变更影响所有平台，修改成本高；某些平台可能被迫实现不需要的方法

### 方案 B 轻量变体：ABC + 自发现 + 无 Checklist
- 特征：保留方案 B 的统一抽象基类（`BaseChannel` ABC），但消除 Checklist——内置 channel 通过 `pkgutil.iter_modules()` 自动扫描发现，新增 Python 文件即自动可用，无需修改任何注册文件；外部 channel 通过 entry_points 插件机制接入；内置覆盖外部同名插件的优先级保护
- 优势：兼具统一接口的低耦合（所有 channel 继承同一 ABC）和自发现的零摩擦（新增文件即生效）；无 Checklist 消除了方案 B 的最大代价——新增平台不需要修改 16 处配置点；内置优先覆盖策略防止第三方插件 shadow 内置功能
- 劣势：自发现依赖文件系统扫描，有一定启动开销；pkgutil 扫描机制是隐式约定，新开发者可能不知道「创建文件即注册」的规则；没有 checklist 意味着集成点的完整性由代码结构保证而非流程文档保证

## 跨仓库对比

| | OpenClaw | Hermes Agent | nanobot |
|---|---|---|---|---|
| 选择的方案 | 方案 A：细粒度 Adapter 接口 | 方案 B：统一抽象基类 + Checklist | 方案 B 轻量变体：ABC + 自发现 + 无 Checklist |
| 具体实现 | `ChannelPlugin<ResolvedAccount>` 组合 13+ Adapter 接口：`ChannelMessagingAdapter`（消息收发）、`ChannelOutboundAdapter`（出站路由）、`ChannelLifecycleAdapter`（启停生命周期）、`ChannelAuthAdapter`（认证）、`ChannelSetupAdapter`（初始化配置）等，每个是独立接口；各 channel 为独立 npm 包，按需懒加载 | `BasePlatformAdapter` 统一 ABC（813-893 行），22 个平台全部继承；`ADDING_A_PLATFORM.md` 提供 16 步 checklist 涵盖所有需要感知新平台的集成点；GatewayRunner 统一管理所有适配器生命周期 | `BaseChannel` ABC 统一接口；内置 14 个 channel 通过 `pkgutil.iter_modules()` 自动扫描 `channels/` 目录下 BaseChannel 子类，新增 Python 文件即自动可用；外部插件通过 entry_points 机制；内置覆盖外部同名插件；各平台 SDK 通过 pip extras 按需安装 |
| 付出的代价 | 13+ 接口增加了概念复杂度，新 channel 开发者需要理解接口分工；跨平台通用逻辑需要在各 Adapter 接口间协调 | 新增平台必须修改 16 处配置点，不能渐进式接入；基类修改会影响全部 22 个平台 | pkgutil 扫描有启动开销；自发现是隐式约定，新开发者可能不知情；无 checklist 意味着集成点完整性由代码结构而非流程文档保证 |

## 设计权衡

**选择细粒度 Adapter 接口（方案 A）更合理的场景**：
- 平台间差异大，不是所有平台都需要相同的能力集合
- 扩展生态开放，第三方开发者需要低门槛接入自定义平台
- 每个平台作为独立包发布，依赖隔离和按需加载是硬需求
- 接口本身需要频繁演进，细粒度拆分可以局部修改

**选择统一抽象基类 + Checklist（方案 B）更合理的场景**：
- 平台间协议差异已被基类充分抽象，大部分方法对所有平台都有意义
- 跨平台功能（toolset、认证、cron 等）的一致性比单平台接入速度更重要
- 平台适配由核心团队维护，不对外暴露扩展接口
- Checklist 作为流程规范在团队内部比接口灵活性更有价值

**关键取舍本质**：方案 A 用接口数量换灵活性——每个平台只承担自己需要的复杂度；方案 B 用统一性换一致性——所有平台承担相同的结构性成本，但换来跨平台行为的完全可预测。
