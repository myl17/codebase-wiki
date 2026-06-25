# 验证报告：im-platform-adapter-granularity

## 格式完整性
- [x] 问题陈述是"如何..."问题形式 — `在为多平台 IM 系统设计适配器接口时，如何决定接口的拆分粒度——是单一抽象基类还是多个可选小接口？`
- [x] 核心关切列表 >= 2 条 — 共 5 条
- [x] 每个权衡位置有"优先满足"和"接受妥协"两个字段 — 位置 A 和位置 B 均有
- [x] 跨仓库对比表列数 = 仓库数 — 2 列
- [x] 溯源表完整 — 有

---

## 逐仓库验证

### openclaw

**Claim 1**: "ChannelPlugin<ResolvedAccount> 接口将平台能力拆分为 13+ 独立 Adapter"（`types.plugin.ts:53-94`）

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/channels/plugins/types.plugin.ts:53-96`
代码摘要：`ChannelPlugin` 接口包含 28 个 adapter 槽位（config, setup, pairing, security, groups, mentions, outbound, status, gateway, auth, approvalCapability, elevated, commands, lifecycle, secrets, allowlist, doctor, bindings, conversationBindings, streaming, threading, messaging, agentPrompt, directory, resolver, actions, heartbeat, agentTools），每个均为可选字段。

判定：✅ 28 >= 13。每个 Adapter 是可选的（TypeScript 类型层面无强制必须实现），平台只实现自己支持的能力维度。

---

**Claim 2**: "defineBundledChannelEntry 统一注册入口，接受 { plugin, secrets, runtime, registerFull } 四个模块引用"（`channel-entry-contract.ts:31-60`）

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/plugin-sdk/channel-entry-contract.ts:31-60` — 此处定义的是 `DefineBundledChannelEntryOptions` 类型（line 31-42）和 `BundledChannelEntryContract` 类型（line 50-60）。
`channel-entry-contract.ts:327-380` — **实际函数 `defineBundledChannelEntry`** 位于此区间，接受 `{ id, name, description, importMetaUrl, plugin, secrets, configSchema, runtime, registerCliMetadata, registerFull }` 参数。

判定：⚠️ Concept 页标注行号 31-60 对应的是类型定义，不是函数实现。`defineBundledChannelEntry` 函数实现在第 327-380 行。功能描述正确（接受 plugin/secrets/runtime/registerFull 模块引用并通过 `loadBundledEntryExportSync` 懒加载），但溯源行号需修正为 `:327-380`。

---

**Claim 3**: "每个 channel 作为独立 npm 包存在，SDK 依赖完全隔离"

源码：`channel-entry-contract.ts:70-73` — `const nodeRequire = createRequire(import.meta.url)`，`jitiLoaders` 按模块路径缓存。`defineBundledChannelEntry` 接受 `importMetaUrl`（channel 自身目录的 URL），通过 `loadBundledEntryExportSync` 按需加载该 channel 的模块。`resolveBundledEntryModulePath` (line 208-261) 从多个候选路径（dist/extensions, source）搜索模块，支持独立 package 结构。

判定：✅ Channel 通过 `importMetaUrl` + `specifier` 独立加载模块，不聚合到 root package.json。独立 npm 包的架构得到源码支撑。

---

**Claim 4**: "Channel 代码通过 loadBundledEntryExportSync 按需懒加载，避免未使用的 channel 拖慢启动"

源码：`channel-entry-contract.ts:306-325` — `loadBundledEntryExportSync` 使用 Jiti 即时编译加载 TypeScript 模块。`defineBundledChannelEntry` 返回的 `loadChannelPlugin` 为惰性工厂函数（line 343），不在注册时立即执行。

判定：✅ 懒加载通过惰性工厂函数 (`() => loadBundledEntryExportSync(...)`) 实现，channel 插件在 `api.registerChannel()` 被调用前不会被实际加载。

---

### hermes-agent

**Claim 1**: "BasePlatformAdapter 抽象基类定义 6 个必须实现方法：connect()、disconnect()、send()、send_typing()、send_image()、get_chat_info()"（`base.py:813-893`）

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/platforms/base.py`

实际 `@abstractmethod` 装饰的方法（源码 grep 确认）：
1. `connect()` — line 981, `@abstractmethod`
2. `disconnect()` — line 990, `@abstractmethod`
3. `send()` — line 995, `@abstractmethod`
4. `get_chat_info()` — line 1981, `@abstractmethod`

共 **4 个** `@abstractmethod` 方法。

`send_typing()`（line 1030）— 没有 `@abstractmethod`，有默认空实现 `pass`
`send_image()`（line 1047）— 没有 `@abstractmethod`，有默认 fallback（转为文本发送）

判定：❌ Concept 页声称 6 个必须实现方法，但源码只有 4 个 `@abstractmethod`。`send_typing()` 和 `send_image()` 在源码中是**可选覆盖方法**（有默认实现），不应被归类为必须实现方法。

注：`gateway/platforms/ADDING_A_PLATFORM.md` 文档中将 `send_typing` 和 `send_image` 也列为 Required methods，与源码的实际约束不一致。这是文档与源码之间的不一致，Concept 页沿用了文档而非源码的实际约束。

修正建议：修正为「4 个必须实现方法（connect / disconnect / send / get_chat_info）+ 7 个可选覆盖方法（send_typing / send_image / send_document / send_voice / send_video / send_animation / edit_message 等）」。

---

**Claim 2**: "5 个可选覆盖方法：send_document()、send_voice()、send_video()、send_animation() 等"（`base.py:813-893`）

源码验证：可选覆盖方法的实际数量：
1. `edit_message()` — line 1017，默认返回 `SendResult(success=False)`
2. `send_typing()` — line 1030，默认 `pass`
3. `stop_typing()` — line 1039，默认 `pass`
4. `send_image()` — line 1047，默认 fallback 为 text send
5. `send_animation()` — line 1066，默认 fallback 为 send_image
6. `send_voice()` — line 1137
7. `send_video()` — line 1171
8. `send_document()` — line 1190
9. `send_image_file()` — line 1210（还有更多）

判定：⚠️ 可选方法实际数量远超 5 个。鉴于 `send_typing()` 和 `send_image()` 应从"必须实现"移至"可选"，可选方法总数修订后至少为 7+。

---

**Claim 3**: "GatewayRunner 通过统一的 adapter 生命周期管理所有平台"（`gateway/run.py:538-617`）

源码：`gateway/run.py:538` — `class GatewayRunner:` 类定义。Line 562 — `self.adapters: Dict[Platform, BasePlatformAdapter] = {}` 存储所有平台适配器。后续 `connect()` 遍历 `self.adapters` 统一管理生命周期。

判定：✅ GatewayRunner 管理所有 adapter 的架构模式与描述一致。但 538-617 行区间主要为 `__init__` 初始化和配置加载，adapter 生命周期管理的核心逻辑（connect/disconnect/路由）分布在文件后续区域，建议溯源引用范围扩展或调整为引用 GatewayRunner 类整体。

---

**Claim 4**: "新增平台需按照 ADDING_A_PLATFORM.md 的 16 步 checklist 修改 16 处代码"（`ADDING_A_PLATFORM.md:1-313`）

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/platforms/ADDING_A_PLATFORM.md`，共 313 行，16 个步骤：
1. Core Adapter
2. Platform Enum
3. Adapter Factory
4. Authorization Maps
5. Session Source
6. System Prompt Hints
7. Toolset
8. Cron Delivery
9. Send Message Tool
10. Cronjob Tool Schema
11. Channel Directory
12. Status Display
13. Gateway Setup Wizard
14. Phone/ID Redaction
15. Documentation
16. Tests

判定：✅ 16 步 checklist 与文档完全一致。

---

## 关切验证

| 关切 | 跨仓库对比表对应行 | 判定 |
|------|-------------------|------|
| 1. 能力差异兼容 | 「优先满足的关切」行中 openclaw 明确满足关切 1 | ✅ |
| 2. 接口统一 | 「优先满足的关切」行中 hermes-agent 明确满足关切 2 | ✅ |
| 3. 工作量成正比 | 「优先满足的关切」行中 openclaw 明确满足关切 3 | ✅ |
| 4. 覆盖面广度 | 「优先满足的关切」行中 hermes-agent 明确满足关切 4 | ✅ |
| 5. 扩展改动代码点 | 「新增平台改动范围」行显式对比 1-2 文件 vs 16 步 | ✅ |

所有 5 个关切均在对比表中直接或间接体现，无悬空关切。

---

## 追加完整性

- [x] openclaw 在各节均有提及 — 位置 A（13+ Adapter 分解）、对比表、选择指南、溯源表均包含
- [x] hermes-agent 在各节均有提及 — 位置 B（单一 ABC 继承）、对比表、选择指南、溯源表均包含

---

## 绝对化语言验证

| 绝对化表述 | 源码边界条件 | 判定 |
|-----------|------------|------|
| "所有平台适配器继承自同一个抽象基类 BasePlatformAdapter" | `gateway/run.py:562` — `self.adapters: Dict[Platform, BasePlatformAdapter]` 类型约束确认 | ✅ 准确 |
| "所有 adapter 走完全相同的代码路径，无分支检查能力差异" | GatewayRunner 以 `BasePlatformAdapter` 类型遍历 adapter，不检查各平台具体能力 | ✅ 准确 |
| "不支持可选方法的平台继承默认空实现即可" | `send_typing` (line 1030, `pass`), `send_image` (line 1047, fallback) 等均有默认实现 | ✅ 准确 |
| "基类修改会波及所有 22 个平台实现" | 所有 adapter 继承自同一基类，新增 `@abstractmethod` 会触发所有子类编译/启动失败 | ✅ 逻辑正确（如修改的是 @abstractmethod） |

---

## 汇总

总 claim 数：14 | ✅：11 | ⚠️：2 | ❌：1

关键发现：
1. **BasePlatformAdapter 必须实现方法数量错误（❌）**：源码只有 4 个 `@abstractmethod` 方法（connect / disconnect / send / get_chat_info），Concept 页声称 6 个（额外计入 send_typing 和 send_image，但这两者源码中有默认实现）。这是文档（ADDING_A_PLATFORM.md）与源码不一致的传导错误。
2. **可选方法数量被低估（⚠️）**：源码中至少有 8-9 个可选覆盖方法，Concept 页只列出了 5 个。
3. **defineBundledChannelEntry 行号偏差（⚠️）**：溯源行号 31-60 指向类型定义而非函数实现，函数在 327-380 行。
