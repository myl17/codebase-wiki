# 子系统组装的可发现性

**问题陈述**：一个由 10+ 子系统组成的 agent 框架，如何将所有子系统的初始化、依赖注入和生命周期管理集中在一个位置——是通过中央编排器吸收所有执行路径，还是通过构造函数在单个 Hub 中显式组装所有子系统？

**核心关切**：
- **可发现性**：所有连线逻辑集中在一个文件中，读一个函数就能完整理解系统组成
- **可测试性**：集中式组装无法对单个子系统做独立单元测试，组件成为单一故障集中点
- **扩展成本**：新增子系统时需要修改核心 hub/编排器 vs 仅注册不修改 core
- **规模膨胀**：中央编排器会随功能增长膨胀（hermes 11510 行单文件 vs nanobot 114 行紧凑构造函数）

---

## 已知权衡位置

### 位置 A：中央编排器（Central Orchestrator）

**优先满足的关切**：所有执行路径统一编排，改动一致生效；provider 路由、工具过滤、回退链、上下文压缩等横切关注点在一次初始化中全部设置

**接受妥协的关切**：可发现性差（单文件 11510 行，__init__ 横跨 1072 行）；可测试性差（单一类承载全部状态，无法对子系统做隔离测试）；规模膨胀不受控

**特征**：
- 单个类吸收 CLI、Gateway、Cron、ACP 全部执行路径的初始化逻辑
- __init__ 方法按顺序逐一切换 provider 分支（anthropic_messages / bedrock_converse / chat_completions / codex_responses），每分支独立构建 client、解析 auth、设置 headers
- 配置读取、工具加载、session 管理、memory/skills/compression 插件全部内联在同一个 __init__ 中
- 入口函数 `main()` 和 `run_conversation()` 共享同一个 `AIAgent` 实例的全部状态

**关键机制**（源码可见）：
- `AIAgent.__init__()` at `run_agent.py:559-1631`：在同一个方法中依次完成 LLM client 初始化（559-1070 行，含 4 条 provider 分支）、工具定义加载（1097-1118 行）、session 日志与 SQLite 持久化（1141-1198 行）、memory store 与外部 memory provider 插件激活（1211-1315 行）、context compressor/engine 选择与配置（1354-1540 行）、Ollama num_ctx 检测（1563-1588 行）、主运行时快照保存（1602-1630 行）
- `AIAgent.run_conversation()` at `run_agent.py:8130`：单一入口被 CLI (`main()` at 11295)、Gateway (`gateway/run.py`)、Cron scheduler、ACP runtime 四类消费者共享
- 外部 memory provider 插件（Honcho 等）在 `run_agent.py:1238-1315` 处通过 `_memory_manager.initialize_all()` 热插拔激活，无需修改 AIAgent 类签名

**代价**：
- 单文件 11510 行，__init__ 自身 1072 行，任何子系统初始化失败都会阻断所有入口
- 无法替换编排器——所有路径硬绑定到同一个 `AIAgent` 类
- 新增子系统意味着在 __init__ 中部追加又一个初始化块，没有结构化边界
- provider 分支的 if/elif 链（anthropic_messages / bedrock_converse / 其他）在 __init__ 中展开为数百行，阅读者必须理解全部四条路径才能掌握完整初始化逻辑

**已知实例**：hermes-agent

---

### 位置 B：单体 Hub 集中组装（Monolithic Hub Assembly）

**优先满足的关切**：可发现性极高——构造函数签名即系统架构图，读一遍 `__init__` 就能完整理解系统组成；代码量极简（~114 行）使得维护和理解成本趋近于零

**接受妥协的关切**：无法对单个子系统做独立单元测试——所有子系统在构造时全部初始化，没有懒加载；启动时必须提供全部依赖，无法按需延迟实例化

**特征**：
- 所有子系统通过构造函数参数显式注入（`bus: MessageBus`, `provider: LLMProvider`, `workspace: Path`, ...），类型注解即文档
- 构造函数中按固定顺序组装——先存储简单参数 → 构建 ContextBuilder → SessionManager → ToolRegistry → AgentRunner → SubagentManager → Consolidator → Dream → CommandRouter
- 工具注册（`_register_default_tools()`）和命令注册（`register_builtin_commands()`）在函数末尾集中调用，形成清晰的"扩展注册区"
- 无 provider 分支展开——多 provider 支持通过 `LLMProvider` 抽象和多态实现，不在构造函数中展开条件逻辑

**关键机制**（源码可见）：
- `AgentLoop.__init__()` at `agent/loop.py:115-228`：构造函数共接收 20 个参数（含 17 个可选参数），按"存储简单字段 → 构建复合子系统 → 注册扩展"三阶段顺序组装，总计约 99 行有效代码
- `ContextBuilder(workspace, timezone=timezone)` at `agent/loop.py:182`：上下文构建器在构造函数早期创建，后续的 Consolidator 和 Dream 通过 `self.context.memory` 和 `self.context.build_messages` 引用其内部组件，形成清晰的依赖图
- `SubagentManager(provider=..., workspace=..., bus=..., ...)` at `agent/loop.py:186-195`：子 agent 管理器通过构造函数接收共享的 provider、workspace、bus 引用，不创建额外实例，整个系统只有一个 provider 实例贯穿全部子系统
- `self._register_default_tools()` at `agent/loop.py:225`：工具注册从构造函数末尾抽离为独立方法，新增工具类型只需在该方法（`agent/loop.py:229-254`）添加 `self.tools.register(XxxTool())` 一行，不碰构造函数签名

**代价**：
- 所有子系统在构造时全部实例化，无法按需懒加载（如 cron_service 可能在纯 CLI 模式下不需要）
- 构造函数 20 个参数对调用方有认知负担，虽然前 3 个（bus, provider, workspace）是必需核心，其余均有默认值
- 无法替换 Hub——`AgentLoop` 是唯一的编排中心，如果需要完全不同的组装方式，必须写一个新的编排类

**已知实例**：nanobot

---

## 跨仓库对比

| | hermes-agent | nanobot |
|---|---|---|
| **权衡位置** | 中央编排器（Central Orchestrator） | 单体 Hub 集中组装（Monolithic Hub Assembly） |
| **组装文件** | `run_agent.py`（11510 行单文件） | `agent/loop.py`（核心构造函数 ~99 行） |
| **__init__ 规模** | ~1072 行（559-1631） | ~99 行（115-228） |
| **具体实现** | `AIAgent.__init__()` 内联全部 provider 路由分支（anthropic/bedrock/chat_completions/codex_responses 四条路径各有独立 client 构建逻辑，`run_agent.py:898-1070`）、context compressor 插件加载（`run_agent.py:1432-1504`）、memory provider 热插拔（`run_agent.py:1238-1315`），所有初始化在同一方法中无边界展开 | `AgentLoop.__init__()` 通过构造函数参数显式注入全部依赖（`agent/loop.py:129-150`），按三阶段顺序组装：存储简单字段 → 构建复合子系统（ContextBuilder/ToolRegistry/AgentRunner/SubagentManager/Consolidator/Dream）→ 注册扩展（tools + commands），每步一行 |
| **入口路径** | 单一 `AIAgent` 类吸收 CLI (`cli.py:main()`)、Gateway (`gateway/run.py`)、Cron、ACP 四条执行路径 | AgentLoop 作为编排 Hub，被 Channel 层（`channels/` 目录下各平台适配器）通过 MessageBus 异步队列驱动 |
| **Provider 路由** | if/elif 分支链在 __init__ 中部展开为 ~170 行（898-1070），每个 provider 有独立的 auth 解析、header 构造、client 实例化逻辑 | 通过 `LLMProvider` 多态抽象在构造函数外解决（`provider.py` 中的 ProviderRegistry 数据驱动注册表），构造函数仅接收 `provider: LLMProvider` 参数 |
| **新增子系统成本** | 需在 __init__ 中部追加初始化块 + 必要时修改方法签名 + 确保不影响已有 provider 分支 | 在 `_register_default_tools()` 加一行 `self.tools.register(XxxTool())`，或在构造函数参数列表增加一个带默认值的新参数 |

---

## 选择指南

| 场景 | 推荐模式 |
|---|---|
| 框架需要同时服务 CLI、Gateway、Cron 等多条执行路径，且每条路径的初始化逻辑高度相似 | 中央编排器（hermes-agent 模式）：一次写清所有初始化，四条路径共享同一份逻辑 |
| 框架规模较小（< 5000 行），追求代码可读性和快速上手 | 单体 Hub 集中组装（nanobot 模式）：构造函数即文档，新人读一遍 `__init__` 就能理解全貌 |
| 框架规模持续增长，初始化逻辑已超过 500 行 | 考虑从中央编排器拆分为 Builder 模式或分阶段初始化，避免单方法膨胀 |
| 子系统需要独立单元测试 | 两种模式都不理想——考虑依赖注入容器或工厂模式，使子系统可独立构造 |
| 需要插件式扩展（第三方贡献子系统） | 注册表模式（如 nanobot 的 ToolRegistry）优于内联初始化块——新增子系统不需修改核心构造函数 |

### 模式选择的根本问题

两种模式的差异并非"好设计 vs 烂设计"，而是对"什么更重要"的不同回答：

- **hermes-agent 选择"正确性 > 简洁性"**：provider 路由的复杂性（4 条路径、20+ provider、auth 解析、header 定制、OAuth vs API key、Bedrock 特殊路径）必须在一个地方完整表达，拆开反而容易遗漏边界 case。代价是单文件膨胀到 11510 行。
- **nanobot 选择"简洁性 > 完备性"**：通过 LLMProvider 多态把 provider 差异推到构造函数之外，通过 ToolRegistry 把工具注册从构造函数抽离。代价是去除了 litellm（30+ provider 开箱即用），保持核心的 provider 抽象足够简单以支撑构造函数内联。

**本质权衡**：是把复杂性吸收进一个单一位置（牺牲可读性换取完备性），还是把复杂性推到边界之外（牺牲完备性换取可读性）。选择取决于框架的成熟度阶段——hermes-agent 作为生产级框架必须以完备性优先，nanobot 作为轻量实验框架必须以简洁性优先。

---

## 溯源

| 仓库 | 源码文件 | 关键行号 |
|---|---|---|
| hermes-agent | `run_agent.py` | `AIAgent.__init__()`: 559-1631；provider 路由分支: 898-1070；context compressor 加载: 1432-1504；memory provider 插件: 1238-1315 |
| nanobot | `agent/loop.py` | `AgentLoop.__init__()`: 115-228；`_register_default_tools()`: 229-254；SubagentManager 组装: 186-195；Consolidator 组装: 210-219 |

---

## 关联

- [[hermes-agent/nodes/components/hermes-agent-ai-agent]] — hermes-agent AIAgent 中央编排器（Position A 实例）
- [[hermes-agent/dimensions/hermes-agent-architecture]] — hermes-agent 架构维度
- [[nanobot/dimensions/nanobot-architecture]] — nanobot 架构维度（Position B 实例）
- [[单体架构模式]]

---

## 修复记录
- 2026-06-19 Phase 3b → 3c 修复：
  - 修正 `main()` 归属：`run_agent.py:11295` → `cli.py:main()`（wiki 架构页一致将 CLI 入口归于 `cli.py`）
  - 补充缺失的 `## 关联` wikilink 节
- 2026-06-19 Phase 3b 验证修复（`_register_default_tools` 行号 + `__init__` 起点统一）：
  - 修正 `_register_default_tools()` 行号范围：`229-281` → `229-254`。原范围错误地将 `_connect_mcp()` (256-276) 和 `_set_tool_context()` (278-282) 纳入该方法；实际方法体结束于 line 254。同步修正溯源表行号
  - 统一 `AgentLoop.__init__()` 起点行号：`129-228` → `115-228`。115-128 为类定义和文档字符串，与 wiki 记录保持一致。同步修正对比表和溯源表行号
