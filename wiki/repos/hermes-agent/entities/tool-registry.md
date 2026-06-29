---
type: entity
repo: hermes-agent
slug: tool-registry
problem: 如何实现工具的自动发现、注册、校验和分发，支持内建工具与 MCP/插件工具的共存
generated: 2026-06-25
source_files:
  - tools/registry.py
  - model_tools.py
  - toolsets.py
  - toolset_distributions.py
---

# 工具注册与编排

**代码位置**：`tools/registry.py`、`model_tools.py`、`toolsets.py`
**这个模块解决什么问题**：
- 实现层：单例 ToolRegistry 通过 AST 扫描自动发现内建工具模块，统一注册 schema + handler + check_fn；model_tools.py 提供工具定义获取和函数调用分发的编排层；toolsets.py 定义工具集组合与场景切换
- 问题层：如何实现工具的自动发现、注册、校验和分发，支持内建工具与 MCP/插件工具的共存
**对外暴露什么**：`ToolRegistry` 类（tools/registry.py:100）、单例 `registry`（tools/registry.py:437）、`get_tool_definitions()`（model_tools.py:196）、`handle_function_call()`（model_tools.py:421）、`resolve_toolset()`（toolsets.py:447）、`TOOLSETS` 字典（toolsets.py:68）
**它和谁交互**：
- 依赖 [[entities/mcp-integration]]（MCP 工具模块自注册到 registry）
- 依赖 [[entities/plugin-system]]（插件工具模块自注册）
- 依赖 [[entities/cli-system]]（CLI tools 配置 UI 消费工具列表）
- 被 [[entities/agent-core]] 调用（get_tool_definitions 提供 LLM schema，handle_function_call 执行工具）
- 被 [[entities/delegate-subagent]] 调用（子 agent 获取受限工具集）
- 被 [[entities/batch-trajectory]] 调用（批量生成使用分布采样）
- 被 [[entities/terminal-execution]] 消费（terminal 工具自注册）
- 被 [[entities/skills-system]] 消费（技能工具自注册）
- 被 [[entities/cron-scheduler]] 消费（cron 工具自注册）
**为什么它是可分离的**：Registry 是独立单例，所有工具模块通过 `registry.register()` 自注册，替换 registry 或添加新工具不修改调用方代码

**关键机制**（源码可见）：
- AST 自动发现：`discover_builtin_tools()` 扫描 `tools/*.py` 文件，通过 AST 检测是否包含 `registry.register()` 调用，导入含注册调用的模块触发自注册 ^[tools/registry.py:41-74]
- 工具遮蔽保护：非 MCP 工具名冲突时拒绝注册（`REJECTED` 日志），防止插件意外覆盖内建工具；MCP-to-MCP 覆盖允许 ^[tools/registry.py:190-213]
- 线程安全快照：`_snapshot_state()` 用 RLock 保护获取一致的 entries + toolset_checks 视图 ^[tools/registry.py:112-115]
- 工具集组合与解析：`resolve_toolset()` 递归解析 `includes`，支持菱形依赖（visited set 避免重复），支持 `all/*` 通配符 ^[toolsets.py:447-498]
- 参数类型纠正：`coerce_tool_args()` 根据 JSON Schema type 声明纠正 LLM 的类型错误（字符串 "42" -> int 42，字符串 "true" -> bool True）^[model_tools.py:334]
- 异步桥接：`_run_async()` 使用每线程持久 event loop 避免 "Event loop is closed" 错误，主线程和 worker 线程各有独立 loop ^[model_tools.py:44-125]
- 动态 Schema 注入：`execute_code` 工具根据当前启用的工具集动态注入可用沙箱工具列表；`browser_navigate` 在 web 工具不可用时剥离相关引用 ^[model_tools.py:196-330]
- 平台工具集：每个 messaging 平台有预定义工具集（`hermes-telegram`、`hermes-discord` 等），共享 `_HERMES_CORE_TOOLS` 核心列表 ^[toolsets.py:31-63]
- 工具集分布采样：`sample_toolsets_from_distribution()` 用于批量生成，按概率分布采样工具集组合 ^[toolset_distributions.py:247]

**源码证据**：
- 入口文件：tools/registry.py、model_tools.py、toolsets.py
- 核心类型/接口定义：`class ToolRegistry` ^[tools/registry.py:100]、`class ToolEntry` ^[tools/registry.py:76]

**关联 Concept**：
- [[concepts/tool-lifecycle-management]]
