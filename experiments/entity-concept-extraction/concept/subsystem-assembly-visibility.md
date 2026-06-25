# Subsystem Assembly Visibility

## 问题陈述

当一个 agent 框架由多个子系统组成（LLM provider、session 管理、tool registry、context compressor、memory manager、skill injector 等），如何组织所有这些子系统的实例化和连线，使系统的整体构成具有最大可发现性？单体 hub 构造函数、依赖注入容器、分散初始化、还是 plugin registry + 懒加载？

三种策略的核心权衡：**可见性**（能不能一眼看到完整构成）、**可扩展性**（加一个子系统改多少代码）、**耦合度**（子系统之间的依赖有多直接）、**启动成本**（是一次性全加载还是按需加载）。

## 实例

### openclaw: Plugin Manifest Registry + 懒加载 + 运行时动态选择

**所属仓库**: [[openclaw-agent-harness|Agent Harness (OpenClaw)]]
**维度**: Architecture
**机制类型**: 双层 registry（manifest registry + harness registry）+ 按 scope 懒加载

**机制**

openclaw 的子系统组装分为两层，分别用不同的 registry 机制：

**上层 — Plugin Manifest Registry（静态发现）**

`src/plugins/manifest-registry.ts` 维护一个 `PluginManifestRegistry`，包含所有已发现插件的 manifest 记录（`PluginManifestRecord[]`）和诊断信息。插件通过文件系统扫描发现（`discoverOpenClawPlugins()`），每个插件有 manifest 文件声明其 id、providers、channels、hooks、skills、config schema 等元数据。Manifest registry 是启动时构建的静态索引——它不加载插件代码，只记录"存在哪些插件"。

**下层 — Runtime Registry（按需加载）**

`src/plugins/runtime/runtime-registry-loader.ts` 中的 `ensurePluginRegistryLoaded()` 实现 scoped loading：

1. `"none"` → `"configured-channels"` → `"channels"` → `"all"`：四个 scope 级别，每次请求检查当前 registry 是否满足所需 scope 级别
2. 如果已加载的 registry 满足 scope（例如已加载 `"channels"` 级别的 registry 能响应 `"configured-channels"` 级别的请求），跳过重复加载
3. 通过 `resolveChannelPluginIds()` 或 `resolveConfiguredChannelPluginIds()` 计算出需要的插件 ID 列表
4. 调用 `loadOpenClawPlugins()` 实际加载插件代码

Gateway 启动时（`src/gateway/server-startup-plugins.ts:24-80`）：`createEmptyPluginRegistry()` → `loadGatewayStartupPlugins()` → 按 scope 懒加载。插件只在需要时才被初始化，不是启动时全量加载。

**AgentHarness 层 — 全局 Registry Map + 运行时策略选择**

`src/agents/harness/registry.ts` 使用 `globalThis[Symbol.for("openclaw.agentHarnessRegistryState")]` 存储一个 `Map<string, RegisteredAgentHarness>`。`registerAgentHarness()` 将 harness 实例注册到全局 Map，`selectAgentHarness()`（`src/agents/harness/selection.ts`）每次请求时遍历所有已注册 harness，调用 `supports(ctx)` 过滤 + 按 `priority` 降序排序，选择最优匹配。

**注册方式**：Plugin 通过文件系统 manifest 声明存在性，通过 `registerAgentHarness()` 显式注册到运行时 Map。新增一个 provider harness 需要：创建 manifest + 实现 harness 接口 + 调用 `registerAgentHarness()`。不需要修改选择逻辑、引导代码或任何配置文件。

**调用时机**：Plugin manifest registry 在启动时构建。Runtime registry 按 scope 懒加载——首先加载 channel 所需的插件，然后按需加载更多。Harness 选择在每次请求时动态执行。

**关键源码**：
- `src/plugins/manifest-registry.ts:115-118` — `PluginManifestRegistry` 类型定义
- `src/plugins/runtime/runtime-registry-loader.ts:57-100` — `ensurePluginRegistryLoaded()` scoped loading
- `src/gateway/server-startup-plugins.ts:24-80` — Gateway 启动时的 plugin bootstrap 流程
- `src/agents/harness/registry.ts:11-18` — 全局 `Map<string, RegisteredAgentHarness>` 基于 `globalThis[Symbol]`
- `src/agents/harness/registry.ts:21-34` — `registerAgentHarness()` 注册函数

---

### hermes: 单体 Hub 构造函数（~1072 行 `__init__()`）

**所属仓库**: [[hermes-agent|Hermes Agent]]
**维度**: Architecture
**机制类型**: 构造函数内集中式顺序组装

**机制**

`AIAgent` 类（`run_agent.py:535`）的 `__init__()` 方法从第 559 行到第 1631 行，共约 1072 行。所有子系统的实例化和配置都在这个单一方法中完成，按顺序排列为 `self.xxx = ...` 的平铺属性赋值：

- **Provider 客户端**（`:895-1070`）：约 175 行处理 API mode 检测（chat_completions / codex_responses / anthropic_messages / bedrock_converse），`self.client` 通过 `_create_openai_client()` 创建（`:1058`），`self._anthropic_client` 通过 Anthropic SDK 构建（`:909/929`）
- **Tool 定义**（`:1098-1121`）：`self.tools = get_tool_definitions(enabled_toolsets=..., disabled_toolsets=...)`，工具 schema 作为 dict list 存入 `self.tools`
- **Checkpoint 管理**（`:1165-1168`）：`self._checkpoint_mgr = CheckpointManager(enabled=..., max_snapshots=...)`
- **内存存储**（`:1212-1234`）：`self._memory_store = MemoryStore(memory_char_limit=..., user_char_limit=...)`，从磁盘加载 MEMORY.md
- **Memory Provider 插件**（`:1240-1315`）：`self._memory_manager = MemoryManager()`，通过配置驱动的插件加载，支持 honcho 等外部 provider。这是一个 plugin 模式，但 plugin 选择和初始化逻辑内联在 `__init__()` 中
- **Context Compressor**（`:1357-1504`）：~150 行处理压缩配置、context engine 选择、回退到内置 `ContextCompressor`。`self.context_compressor` 可以是插件引擎（`:1471`）或内置 `ContextCompressor(...)`（`:1491`）
- **其他**：`self._todo_store = TodoStore()`（`:1202`）、`self._session_db = session_db`（`:1172`）、`self._subdirectory_hints = SubdirectoryHintTracker(...)`（`:1544`）、`self.iteration_budget = IterationBudget(...)`（`:663`）、Ollama num_ctx 检测（`:1563-1588`）、API 配置（`:1055-1094`）、session 日志（`:1142-1159`）

**创建方式**：所有子系统通过直接构造函数调用创建，或通过工厂函数（如 `get_tool_definitions()`）创建。没有任何 DI 容器、服务定位器或 registry 抽象层。子系统的生命周期与 `AIAgent` 实例完全绑定——构造函数返回时所有子系统已初始化完毕。

**Plugin 化尝试**：hermes 在 context engine（`:1432-1471`）和 memory provider（`:1240-1315`）两处使用了 plugin 模式，但 plugin 的发现、加载、选择逻辑完全内联在 `__init__()` 中，没有独立的 registry 或 loader 模块。这更像是在单体构造函数中嵌入的条件分支，而非独立的插件系统。

**可发现性**：读 `__init__()` 源文件就能看到所有子系统及其创建顺序——如果愿意读 1072 行代码的话。没有独立 manifest、没有 registry 索引、没有配置驱动的子系统列表。系统的"完整构成"等于构造函数体的文本本身。

**关键源码**：
- `run_agent.py:559-1631` — `AIAgent.__init__()` 完整构造函数
- `run_agent.py:1098` — `self.tools = get_tool_definitions(...)` 工具加载
- `run_agent.py:1273` — `self._memory_manager = MemoryManager()` 内存插件初始化
- `run_agent.py:1471/1491` — `self.context_compressor` plugin engine 或 `ContextCompressor` 分支

---

### nanobot: 紧凑构造函数 + 接口级依赖注入

**所属仓库**: [[nanobot|nanobot]]
**维度**: Architecture
**机制类型**: 构造函数集中组装 + 关键接口可注入

**机制**

`AgentLoop.__init__()`（`nanobot/agent/loop.py:129-228`）约 100 行，所有子系统在构造函数中直接实例化：

```python
self.context = ContextBuilder(workspace, timezone=timezone)          # :182
self.sessions = session_manager or SessionManager(workspace)         # :183
self.tools = ToolRegistry()                                          # :184
self.runner = AgentRunner(provider)                                  # :185
self.subagents = SubagentManager(provider=provider, workspace=..., bus=bus, ...)  # :186
self.consolidator = Consolidator(store=..., provider=..., ...)       # :210
self.dream = Dream(store=..., provider=..., model=...)               # :220
self.commands = CommandRouter()                                      # :226
```

随后调用 `self._register_default_tools()`（`:225`），在 `_register_default_tools()`（`:229-249`）中逐行显式注册所有内置工具——`ReadFileTool`、`WriteFileTool`、`EditFileTool`、`ListDirTool`、`GlobTool`、`GrepTool`、条件注册 `ExecTool`、`WebSearchTool`、`WebFetchTool`、`MessageTool`。每个工具在注册时完成参数化（workspace、allowed_dir、timeout、sandbox 等）。

**与 hermes 的关键差异 — 接口级 DI**：

nanobot 的构造函数参数中有 5 个是可注入的外部依赖：

| 参数 | 类型 | 注入语义 |
|------|------|---------|
| `bus` | `MessageBus` | 消息总线 — 外部协调层提供，不可为空 |
| `provider` | `LLMProvider` | LLM provider — 外部提供，不可为空 |
| `session_manager` | `SessionManager \| None` | 可选覆盖 — 如果未提供则构造函数内创建默认实例 |
| `cron_service` | `CronService \| None` | 可选外部 cron 服务 |
| `hooks` | `list[AgentHook] \| None` | 可选外部 hook 列表 |

`bus` 和 `provider` 是**必须**由外部提供的核心依赖——`AgentLoop` 不自己创建它们，也不依赖全局单例。`session_manager` 和 `cron_service` 是可选的——外部可以注入自己的实现，如果不注入则在构造函数内创建默认实例。`hooks` 允许外部附加行为而不修改 `AgentLoop` 代码。

这是"接口级 DI"而非"容器级 DI"：没有 DI 框架、没有服务容器、没有自动装配。依赖通过构造函数参数显式传递，类型系统（Python type hints）是唯一的契约。

**与 hermes 的相似之处**：两个仓库都在构造函数中集中创建所有子系统——没有延迟初始化、没有 registry 中介、没有按需加载。差异在于 hermes 的构造函数是 nanobot 的约 10 倍长、且没有任何接口级 DI 抽象。

**关键源码**：
- `nanobot/agent/loop.py:129-228` — `AgentLoop.__init__()` 完整构造函数
- `nanobot/agent/loop.py:229-249` — `_register_default_tools()` 显式工具注册
- `nanobot/agent/loop.py:183` — `session_manager or SessionManager(workspace)` DI 默认值模式
- `nanobot/agent/tools/registry.py:8-20` — `ToolRegistry` 类

---

## 对比分析

三个仓库覆盖了子系统组装光谱上的三个关键点位：完全集中（hermes 单体构造函数）、接口分离（nanobot 紧凑构造 + DI）、完全分布（openclaw plugin registry + 懒加载）。

| 维度 | openclaw Plugin Registry | hermes 单体构造函数 | nanobot 紧凑构造 + DI |
|------|------|------|------|
| **组装位置** | 分散：manifest 声明 + registry 加载 + 运行时选择 | 集中在 `AIAgent.__init__()` 一个方法 | 集中在 `AgentLoop.__init__()` 一个方法 |
| **代码量** | 每个插件独立模块 + registry/loader 基础设施 | ~1072 行单一方法 | ~100 行构造函数 |
| **子系统创建方式** | 插件自行管理（manifest + loader） | 构造函数内直接 `new` / 工厂调用 | 构造函数内直接实例化 / 参数注入 |
| **可发现性** | 需跨文件追踪：manifest → loader → registry → 运行时 | 单文件单方法可读全貌（如果愿意读 1072 行） | 单方法可读全貌（~100 行，易读） |
| **新增子系统成本** | 低：创建 manifest + 实现 + 注册，不改现有文件 | 中：在 `__init__()` 中插入代码块，有合并冲突风险 | 低：加一行 `self.xxx = Yyy()` + 可选参数 |
| **子系统间解耦** | 高：插件之间无直接依赖，通过 registry 接口通信 | 低：所有子系统在同一个作用域内直接引用 | 中：外部依赖通过参数传入，内部子系统直接引用 |
| **外部可替换性** | 高：更换 plugin 实现只需不同的 manifest/harness | 极低：需要修改 `__init__()` 内部代码或 monkey-patch | 中：5 个可注入参数允许外部替换核心依赖 |
| **启动成本** | 按需：scope 懒加载，不使用的插件不加载 | 全量：构造函数返回时所有子系统已初始化 | 全量：构造函数返回时所有子系统已初始化 |
| **适合规模** | O(100) 子系统，多团队贡献 | O(10-20) 子系统，单团队快速迭代 | O(10) 子系统，需要明确的外部协调边界 |

## 设计权衡

### 集中 vs 分布是规模函数

三个仓库的组装策略直接反映其规模和历史阶段：

- **hermes** 的 1072 行构造函数是**增量演化的结果**——每个时期加一个子系统，代码累积在 `__init__()` 中，没有得到重构。plugin 化尝试（context engine、memory provider）已经出现在构造函数中，但 plugin 的选择/加载逻辑仍然内联，没有提取成独立抽象。这是"有机增长"的典型产物：系统复杂到需要 plugin，但 plugin 基础设施还没独立出来。

- **nanobot** 的 100 行构造函数是**从零设计的结果**——子系统数量有限（7 个核心子系统 + 外部接口），每个子系统职责清晰，构造函数简洁到可以快速把握全貌。接口级 DI 是刻意的架构选择：`bus` 和 `provider` 强制外部注入，使得 `AgentLoop` 不依赖任何全局状态或单例。这不是"缺乏 plugin 系统"——这是规模下的正确选择。

- **openclaw** 的 plugin registry 是**明确的多插件架构**——从一开始就设计为支持 50+ 插件、多 channel/provider、多贡献者并行开发的系统。Manifest registry + runtime registry 双层结构、scope-based 懒加载、动态 harness 选择——这些都是平台级基础设施，不是"先用单体再重构"。

### 构造函数的"可读性密度"

hermes 的构造函数虽然 1072 行，但其中大量代码是配置解析（压缩配置 ~100 行、API mode 检测 ~175 行、Ollama 检测 ~25 行）、错误处理、日志打印。真正的子系统创建语句占比不高。而 nanobot 的 100 行几乎全是子系统实例化（~8 个 `self.xxx = Yyy()` 语句），"可读性密度"极高。

但 hermes 的问题不（仅仅）是行数——是**混合了多层次关注点**：API mode 检测、provider 路由、tool 加载、memory plugin 选择、context engine 选择、session 日志、checkpoint 设置全在同一个作用域。这些本应是独立模块的职责，但因为所有决策都在构造函数中完成，模块边界永远不会形成。

### DI 不一定要有容器

nanobot 证明了 DI 不必然需要 DI 容器或框架。5 个构造函数参数形成的"注入接口"已经足够让外部协调层（`AgentLoop` 的上层调用者）控制关键依赖。`session_manager or SessionManager(workspace)` 这种"注入或用默认值"的模式是 DI 最轻量的实现——比 Spring-style XML、NestJS-style decorator、或手动服务定位器都简单，但提供了同样重要的**控制反转**。

hermes 的 `AIAgent.__init__()` 接受 50+ 个参数，几乎所有都是配置值（string、bool、int、可选的 dict），而非接口依赖。参数多是配置而非注入——调用了 `AIAgent(model="...", max_iterations=90, ...)` 不能替换内部的 `CheckpointManager` 或 `ContextCompressor` 实现。

### 懒加载的取舍

openclaw 的 scope-based 懒加载有明确好处——不使用的插件不消耗启动时间或内存。但代价是**可发现性下降**：要理解"完整系统由哪些部分组成"，不能只看一个文件，需要追踪 manifest registry、runtime registry、loader、bootstrap 等多层抽象。

hermes/nanobot 的 eager 初始化则相反：构造函数返回时系统全貌已定，但启动成本是 O(N)，N 是子系统数量。对于 hermes 的 10+ 子系统和 nanobot 的 7 个子系统，这个成本可忽略；对于 openclaw 的 50+ 插件，懒加载是必要优化。

### 适合什么场景

- **用 openclaw 模式**（plugin registry + 懒加载）：子系统多（O(100)）、有多团队/多贡献者、不同部署场景需要不同的子系统组合、启动性能敏感。代价是实现和维护 registry 基础设施的复杂度。
- **用 hermes 模式**（单体构造函数）：子系统少到中等（O(10-20)）、单团队、快速迭代、不需要外部替换子系统实现。在系统规模超过临界点之前——即构造函数开始让新成员难以定位子系统在哪里创建——这是最直接的方案。
- **用 nanobot 模式**（紧凑构造 + 接口 DI）：子系统少（O(10)）、但需要明确的外部协调边界（bus + provider 强制外部注入）、需要在测试中用 mock 替换核心依赖。100 行的构造函数是"读代码即读架构"的理想尺寸。

三个方案不是排他的演进阶段——nanobot 不需要"成长"成 openclaw 来证明成熟度。hermes 的 1072 行构造函数已经到了需要拆分的地步，但不是因为它应该有 plugin registry——而是因为它混合了太多关注点。拆分的第一步可能是提取"配置解析 → 子系统创建"的子步骤为独立方法，而不是引入 plugin 架构。

## 关联概念

- **Plugin Auto-Discovery**：openclaw 的 manifest 扫描和 hermes 的 AST 扫描都是在"找到需要组装的子系统"，但这里讨论的是"找到之后如何把它们拼在一起"——发现 vs 组装的关注点是正交的。
- **Context Compression Quality**：hermes 的 context compressor 是其单体构造函数中最复杂的一段（~150 行），但压缩器本身是独立模块。构造函数中做的是"选择哪个压缩器"——这是一个典型的"组装决策"。
- **Tool Execution Safety**：nanobot 的工具注册在 `_register_default_tools()` 中完成参数化（sandbox、timeout 等），组装时就把安全边界决定好了——安不安全取决于组装时传了什么参数。
- **Strategy Pattern**：openclaw 的 harness selection 是策略模式，nanobot 的 DI 是依赖反转——两种不同的解耦技法，但服务于同一个目标：让系统构成不是写死的。
