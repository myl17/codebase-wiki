---
concept: context-engine-pluggability
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# 上下文压缩引擎如何实现可插拔架构——程序化注册槽位还是文件系统发现？

## 标准化问题陈述

当上下文压缩需要在不同场景使用不同策略时，如何决定压缩引擎的架构——是策略模式允许完全替换引擎实现，还是在共享基础设施内仅配置参数？

## 核心关切

1. **第三方可扩展性**：社区能否提供自己的压缩策略实现并即插即用——扩展摩擦决定了生态能否自然生长
2. **同一时间只有一个 engine 激活**：多个压缩策略同时运行必然冲突——Context Engine 操作的是共享可变对话状态（prompt 组装、消息摄入、历史压缩、transcript 重写），让两个 engine 交替操作同一份对话历史等同于让两个进程同时写同一个文件
3. **压缩引擎的注册机制**：是通过配置显式选择还是通过注册 API 竞争覆盖——这决定了切换 engine 的操作成本和可审计性
4. **引擎替换对核心代码的影响**：新增引擎是否需修改 core——决定了第三方扩展是否需要 fork 框架才能引入新压缩策略

## 已知权衡位置

### 位置 A：openclaw — Exclusive 槽位覆盖注册

**优先满足的关切**：第三方扩展（`ContextEngineFactory` 注册即可，不改 core）；注册规则明确（后注册覆盖前者，`LegacyContextEngine` 向后兼容）

**接受妥协的关切**：显式选择（无法通过配置直接指定引擎——依赖注册顺序，行为可能因加载顺序不同而变化）

**核心特征**：Context Engine 通过程序化注册 API（`registerContextEngine`）接入，注册时即建立所有者身份和访问控制。全局 Map 中可以注册多个 factory，但同一时刻只有一个通过 `resolveContextEngine` 解析为活跃实现。Exclusive 槽位的"覆盖"是注册机制层面的设计——后注册者覆盖同一 ID 的前者——而非运行时动态切换。

**关键机制（源码可见）**：

1. **ContextEngine 完整生命周期接口**（`src/context-engine/index.ts:1-27`）：四个必选操作——`assemble`（组装 prompt）、`ingest`（摄入新消息）、`compact`（压缩历史）、`transcriptRewrite`（重写 transcript）。接口还涉及 subagent 状态管理和 prompt-cache 可观察性等生命周期能力[^1]。`ContextEngineFactory` 是创建 ContextEngine 实例的工厂函数。`LegacyContextEngine` 包装旧接口，保证向后兼容。

2. **Exclusive 注册槽位**（wiki node：`src/plugins/types.ts:1867-1990`）：`registerContextEngine` 声明为 exclusive，全局只能有一个活跃实现。与 `registerMemoryCapability` 共享同一设计模式——这两个都是"共享可变状态的排他性修改者"，不能叠加。`registerCompactionProvider` 则是 ContextEngine 内部的子策略替换点——更细粒度地替换压缩/摘要后端而不动整个 engine。

3. **三层保护的所有者访问控制**（`src/context-engine/registry.ts:309-395`）[^1]：默认槽位 ID（`"legacy"`）锁定给 core 所有者——第三方 SDK 无权覆盖核心默认实现。同一 ID 只能由一个 owner 持有——不同 owner 不可相互覆盖。同一 owner 刷新注册需显式声明 `allowSameOwnerRefresh`——防止无意覆盖。

4. **运行时解析机制**（`src/context-engine/registry.ts:411-427`）[^1]：`resolveContextEngine(config)` 先读 `config.plugins.slots.contextEngine`（显式覆盖），回退到默认槽位值 `"legacy"`。只有被选中的那一个 engine 被实例化和调用——Map 里可以注册多个，但同一时刻只有一个处于激活状态。

**已知代价**：
- 无法仅通过配置文件切换到未注册的 engine——切换 engine 需要先通过代码注册 factory，再通过配置 `config.plugins.slots.contextEngine` 选择已注册的 engine。与 hermes 仅靠改一行 YAML 即完成切换不同，openclaw 的两步流程（注册 + 选择）提高了切换操作成本
- 注册顺序敏感——如果多个 plugin 竞争注册同一 ID，先注册者被覆盖，行为可能因 plugin 加载顺序不同而变化
- 完整接口门槛高——ContextEngine 覆盖完整会话生命周期（含 subagent 状态管理），对简单压缩策略场景是过度工程
- 没有注册发现机制——用户无法"列出所有可用的 Context Engine"，必须先知道 ID 才能配置

**已知实例**：
- [[openclaw/nodes/components/openclaw-context-engine]]
- [[openclaw/nodes/extension-points/openclaw-compaction-provider]]
- [[openclaw/dimensions/openclaw-extension-points]]

---

### 位置 B：hermes-agent — 策略模式 + 目录发现

**优先满足的关切**：显式选择（`config.yaml` 指定激活引擎）；发现机制（目录扫描自动发现所有可用实现）

**接受妥协的关切**：扩展便利性（需创建目录结构 + 实现 `ContextEngine` ABC + 配置文件指定，比注册回调多步骤）

**核心特征**：Context Engine 通过文件系统目录发现 + 声明式配置切换。将实现放入 `plugins/context_engine/<name>/` 目录即可被自动发现，在 `config.yaml` 中写一行 `context.engine: "lcm"` 即可激活。目录即接口——目录结构和 ABC 实现共同构成第三方扩展的完整契约。

**关键机制（源码可见）**：

1. **ContextEngine 精简 ABC**（`agent/context_engine.py:32-60`）：必须实现的方法聚焦压缩核心——`name`（属性标识）、`update_from_response(usage)`（追踪 token 使用）、`should_compress()`（判断是否触发压缩）、`compress(messages, current_tokens)`（执行压缩）。可选扩展（8 个）：`should_compress_preflight`、`on_session_start/end/reset`（会话生命周期）、`get_tool_schemas` / `handle_tool_call`（暴露工具给 agent）、`get_status`、`update_model`[^2]。ABC 的焦点是"何时压缩 + 怎么压缩"——不是一个全栈生命周期管理器，而是一个可以附带额外能力的压缩策略。

2. **目录发现机制**（`plugins/context_engine/__init__.py:33-196`）[^2]：`discover_context_engines()` 扫描 `plugins/context_engine/` 目录——每个子目录（不以 `_` 或 `.` 开头）如果包含 `__init__.py` 即视为一个 engine 候选。支持两种加载模式：（a）`register(ctx)` 函数——模块导出注册函数，调用 `ctx.register_context_engine(engine)` 注册实例；（b）Fallback 扫描——直接查找 `ContextEngine` 子类并实例化。`plugin.yaml` 提供人类可读描述，`is_available()` 做轻量级前置检查。

3. **声明式激活 + 回退链**[^2]：`config.yaml` → `context.engine: "lcm"` → `load_context_engine("lcm")` → fallback to `hermes_cli.plugins.get_plugin_context_engine()` → fallback to built-in `"compressor"`。三层回退保证内置实现始终为最终兜底——即使第三方 engine 加载失败，系统仍能正常运行。

4. **压缩触发阈值**：固定 75% context window 触发压缩（`threshold_percent: float = 0.75`）。内置 `ContextCompressor`（summary-based 压缩）和 `LCM`（Low-Context-Mode）两种实现。

**已知代价**：
- 扩展步骤多——需创建目录 + `__init__.py` + 实现 ABC + `plugin.yaml` + 修改 `config.yaml`，总步骤多于单一注册回调
- ABC 接口非强制——`get_tool_schemas` 和会话生命周期都是可选的，如果 engine 选择不实现 `on_session_end`，会话结束时不会有任何清理
- 目录扫描是隐式的——不显式执行 `hermes plugins list` 时，用户不知道系统在加载哪些 engine；目录发现机制提供了可查询性但默认不可见
- 无所有者保护——任何第三方 engine 只要放在正确目录下即可与内置实现竞争激活位置
- ABC 不强制 `update_from_response` 必须正确更新 token 计数——依赖实现者自觉，如果实现有 bug 可能导致压缩触发时机错误

**已知实例**：
- [[hermes-agent/nodes/extension-points/hermes-agent-context-engine]]
- [[hermes-agent/dimensions/hermes-agent-extension-points]]

---

## 跨仓库对比

| 维度 | openclaw（Exclusive 槽位覆盖注册） | hermes-agent（策略模式 + 目录发现） |
|------|-------------------------------------|--------------------------------------|
| **注册方式** | 程序化 API（`registerContextEngine(factory)`） | 文件系统发现（目录扫描 `plugins/context_engine/<name>/`） |
| **激活方式** | `config.plugins.slots.contextEngine` 显式指定，回退 default slot | `config.yaml` → `context.engine` 显式指定，回退 built-in compressor |
| **接口广度** | 全栈生命周期：assemble/ingest/compact/transcriptRewrite + subagent 状态管理 + prompt-cache 可观察性[^1] | 聚焦压缩：should_compress/compress + 可选会话生命周期 + 可选工具暴露[^2] |
| **发现机制** | 无——需知道 ID 才能配置，无 "list all engines" 能力 | 有——目录扫描自动发现，`hermes plugins list` 可查看 |
| **状态安全** | 三层保护（默认槽位 core 锁定 + 跨 owner 拒绝 + 同 owner 刷新需 opt-in） | 配置选一 + 回退链兜底（无所有者概念，信任目录即授权） |
| **扩展摩擦** | 低（注册回调一步） | 中（创建目录 + `__init__.py` + ABC 实现 + `plugin.yaml` + 改配置） |
| **切换成本** | 中（改配置 + 注册新 engine，需知道 ID） | 低（改一行 YAML，engine 名即目录名） |
| **最小实现门槛** | 高（必须实现完整 ContextEngine 接口，含 subagent 生命周期） | 低（4 个抽象方法，其余可选[^2]——最小实现估计几十行代码） |
| **多实现并存** | Map 中可有多个注册，只有一个解析激活 | 目录中可有多个实现，只有一个被配置选中 |
| **引擎生命周期管理** | Factory 模式——每次会话初始化时创建新实例 | 策略模式——ABC 实例持久化，会话开始/结束 hook 可选 |
| **兜底机制** | `LegacyContextEngine` + core 锁定的默认槽位 | 回退链：engine 加载失败 → `hermes_cli.plugins` → built-in `compressor` |
| **核心取舍** | 宁可扩展摩擦高也要保证状态安全（编译时/注册时防线压倒操作便利性） | 宁可状态安全检查弱也要降低切换摩擦（声明式切换 + 目录发现压倒所有者访问控制） |

## 选择指南

| 场景 | 推荐偏向 | 理由 |
|------|---------|------|
| Context Engine 管理完整会话生命周期（DAG、subagent、transcript 重写） | openclaw 独占槽位 + 所有者访问控制 | 注册阶段就阻止冲突，比运行时发现更安全；覆盖操作是不可逆的，必须防止意外激活 |
| Context Engine 主要是压缩策略的替代实现（不同摘要算法、不同 token 预算） | hermes-agent 目录发现 + 声明式切换 | 降低第三方参与的摩擦比防止边缘情况的风险更有价值；简单 ABC 让社区快速实验 |
| 需要防止第三方无意覆盖核心实现 | openclaw 所有者机制 | 默认槽位锁定给 core，第三方 SDK 无权抢占；跨 owner 拒绝防止恶意/无意覆盖 |
| 希望用户可发现和浏览所有可用 engine | hermes-agent 目录扫描 | `hermes plugins list` 自动列出所有 engine，`plugin.yaml` 提供人类可读描述 |
| 需要运行时动态切换 engine | 两者均不支持 | 两者都在会话初始化时决定 engine，运行时不支持动态切换——这是"同一时间只有一个 engine 激活"约束的自然结果 |
| 最小第三方扩展开销 | hermes-agent 精简 ABC | 4 个必选方法即可运行，`get_tool_schemas` 等全是可选——比 openclaw 的完整生命周期接口门槛低 |
| 需要引擎正确性可被代码静态验证 | openclaw TypeScript 接口 + 注册 API | 接口强制所有方法返回明确类型，注册失败立即返回 `{ ok: false }`——不依赖实现者自觉 |
| 团队需要更换压缩策略但不想改代码 | hermes-agent YAML 切换 | 改一行 `context.engine: "new-engine"` 即可，不需要重新编译或理解插件注册 API |

## 溯源表

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/context-engine/index.ts` | 1-27 | ContextEngine 四大生命周期操作（assemble/ingest/compact/transcriptRewrite）+ ContextEngineFactory 注册点 + LegacyContextEngine 向后兼容 |
| openclaw | `src/plugins/types.ts` | 1867-1990 | OpenClawPluginApi：registerContextEngine（exclusive，全局唯一活跃实现）+ registerCompactionProvider（ContextEngine 内部子策略替换）+ registerMemoryCapability（exclusive） |
| openclaw | `src/context-engine/registry.ts` | 309-395 | registerContextEngineForOwner：三层保护（默认槽位 core 锁定 + 跨 owner 拒绝 + 同 owner 刷新需 allowSameOwnerRefresh opt-in） |
| openclaw | `src/context-engine/registry.ts` | 411-427 | resolveContextEngine：config.plugins.slots.contextEngine 显式覆盖 → 回退 default slot |
| hermes-agent | `agent/context_engine.py` | 32-60 | ContextEngine ABC：name/threshold_percent=0.75/protect_first_n=3 + update_from_response/should_compress/compress 四个必选方法 + on_session_start/end/reset/get_tool_schemas 等可选扩展 |
| hermes-agent | `agent/context_engine.py` | 5-17 | 同一时间只有一个 engine 激活的硬性约束 |
| hermes-agent | `plugins/context_engine/__init__.py` | 33-76 | discover_context_engines()：目录扫描发现 engine 候选 + plugin.yaml 描述 + is_available() 前置检查 |
| hermes-agent | `plugins/context_engine/__init__.py` | 100-196 | _load_engine_from_dir()：支持 register(ctx) 函数注册或 Fallback ABC 子类扫描两种加载模式 |

## 关联

- [[Context 压缩]] — 父级 concept（Context Engine 所属的概念维度）
- [[openclaw/nodes/components/openclaw-context-engine]] — openclaw ContextEngine 组件
- [[hermes-agent/nodes/extension-points/hermes-agent-context-engine]] — hermes-agent ContextEngine 扩展点
- [[openclaw/nodes/extension-points/openclaw-compaction-provider]] — openclaw CompactionProvider（ContextEngine 内部子策略替换）
- [[openclaw/dimensions/openclaw-extension-points]] — openclaw 扩展点系统（含 exclusive 注册机制全貌）
- [[hermes-agent/dimensions/hermes-agent-extension-points]] — hermes-agent 扩展点系统（含 Context Engine 目录发现机制）
- [[openclaw/nodes/design-decisions/openclaw-compaction-recoverability-priority]] — 催生了 ContextEngine 设计的设计决策
- [[openclaw/dimensions/openclaw-architecture]] — openclaw 架构（Context Engine 的子系统定位）
- [[hermes-agent/dimensions/hermes-agent-architecture]] — hermes-agent 架构（Context Engine 的子系统定位）
- [[global-capability-coexistence]] — 兄弟 concept（Context Engine 和 Memory 共享的全局能力唯一性约束）

[^1]: 标记来自直接源码阅读（`src/context-engine/registry.ts`、`src/context-engine/index.ts`）——三层保护、resolveContextEngine、subagent 状态管理、prompt-cache 可观察性等细节在 wiki 中无对应节点页，无法从 wiki 维度页二次验证。

[^2]: 标记来自直接源码阅读（`plugins/context_engine/__init__.py`、`agent/context_engine.py`）——`discover_context_engines()` 函数细节、register(ctx)/Fallback 两种加载模式、`plugin.yaml`/`is_available()`、三层回退链、ABC 必需方法 vs 可选扩展的区分——这些细节在 wiki 维度页中未展开，无法从 wiki 独立验证。

## 修复记录（2026-06-19 验证后修正）

| 判定 | 位置 | 修正内容 |
|------|------|---------|
| ⚠️ | hermes 已知代价 — "用户不知道" | 修正自相矛盾：line 77 "用户不知道系统在加载哪些 engine" 与 line 94 "hermes plugins list 可查看" 措辞冲突。改为 "不显式执行 `hermes plugins list` 时，用户不知道系统在加载哪些 engine；目录发现机制提供了可查询性但默认不可见"，统一两处表述 |
| ⚠️ | openclaw 已知代价 — "无法通过配置文件直接指定 engine" | 精确化措辞：原文 "无法通过配置文件直接指定" 与 `config.plugins.slots.contextEngine` 的显式覆盖能力矛盾。改为 "无法仅通过配置文件切换到未注册的 engine——切换 engine 需要先通过代码注册 factory，再通过配置选择"，区分注册和选择两步 |
| ⚠️ | openclaw 三层保护/resolveContextEngine | 添加行号引用 (`registry.ts:309-395, 411-427`) 和 [^1] 标注——这些细节来自直接源码阅读，wiki 中无对应节点页 |
| ⚠️ | hermes 目录发现/回退链/ABC 方法分类 | 添加行号引用 (`plugins/context_engine/__init__.py:33-196`) 和 [^2] 标注——`discover_context_engines()` 函数细节、两种加载模式、三层回退链、4 必需 vs 8 可选方法区分来自直接源码阅读 |
| ⚠️ | 对比表 — 接口广度行 (openclaw subagent/prompt-cache) | 添加 [^1] 标注——subagent 状态管理和 prompt-cache 可观察性未在 wiki 维度页中出现 |
| ⚠️ | 对比表 — 最小实现门槛 (hermes "几十行代码") | "最小实现可几十行代码" → "最小实现估计几十行代码"，标注为估算 |
| ⚠️ | 对比表 — 最小实现门槛 (hermes 4 必需方法) | 添加 [^2] 标注——ABC 必需 vs 可选方法区分来自源码细节 |
| ⚠️ | 溯源表 — registry.ts 行号 | `registry.ts:309-395, :411-427` 无对应 wiki 节点可交叉验证，已在正文中通过 [^1] 标注 |

**验证汇总**：本页无硬事实错误（0 处 ❌）。主要修正方向：（1）消除自相矛盾措辞；（2）精确化模糊表述以免产生误解；（3）标注直接源码阅读细节与 wiki 覆盖范围的边界。Concept 页对两个 ContextEngine 接口的描述深度超出 wiki 维度页覆盖范围（openclaw 的 registry.ts 内部机制、hermes 的函数级加载细节），这些细节通过 [^1]/[^2] 脚注标注来源。
