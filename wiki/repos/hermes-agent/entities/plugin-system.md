---
type: entity
repo: hermes-agent
slug: plugin-system
problem: 如何通过插件架构扩展 Agent 的能力，支持可插拔的记忆后端和上下文引擎
generated: 2026-06-25
source_files:
  - plugins/__init__.py
  - plugins/memory/__init__.py
  - plugins/context_engine/__init__.py
  - plugins/memory/honcho/
  - plugins/memory/holographic/
  - plugins/memory/mem0/
  - plugins/memory/byterover/
  - plugins/memory/hindsight/
  - plugins/memory/openviking/
  - plugins/memory/retaindb/
  - plugins/memory/supermemory/
---

# 插件系统

**代码位置**：`plugins/` 目录
**这个模块解决什么问题**：
- 实现层：双插件类型架构（Memory Provider + Context Engine），每种类型有独立的发现/加载机制；Memory Provider 通过 `register(ctx)` 模式或 ABC 子类发现注册，Context Engine 通过 `register_context_engine()` 注册；仅 1 个外部 provider/engine 可同时激活
- 问题层：如何通过插件架构扩展 Agent 的能力，支持可插拔的记忆后端和上下文引擎
**对外暴露什么**：`discover_memory_providers()`（plugins/memory/__init__.py:122）、`load_memory_provider()`（plugins/memory/__init__.py:159）、`discover_context_engines()`（plugins/context_engine/__init__.py:33）、`load_context_engine()`（plugins/context_engine/__init__.py:79）
**它和谁交互**：
- 依赖 [[entities/memory-system]]（Memory Provider 通过 memory_provider.py 的 ABC 接口工作）
- 依赖 [[entities/context-compressor]]（Context Engine 通过 context_engine.py 的 ABC 接口替换默认压缩器）
- 依赖 [[entities/config-system]]（`memory.provider` 和 `context.engine` 选择活跃插件）
- 被 [[entities/cli-system]] 调用（`hermes plugins` 命令管理）
**为什么它是可分离的**：插件以独立子目录存在（`plugins/<type>/<name>/`），通过 `plugin.yaml` 声明元数据，加载器通过发现机制动态加载

**关键机制**（源码可见）：
- 双类型架构：`plugins/memory/`（8 个后端：Honcho、Holographic、mem0、ByteRover、Hindsight、OpenViking、RetainDB、Supermemory）和 `plugins/context_engine/`（当前仅有内置 compressor 作为默认）^[plugins/memory/__init__.py, plugins/context_engine/__init__.py]
- 插件发现：`discover_memory_providers()` 扫描打包目录（`plugins/memory/<name>/`）和用户目录（`$HERMES_HOME/plugins/<name>/`），检查 `plugin.yaml` 和 `__init__.py` ^[plugins/memory/__init__.py:122-158]
- 两种加载模式：`register(ctx)` 模式（插件在导入时通过 context 对象注册自己）+ ABC 子类发现模式（`_ProviderCollector` 遍历模块查找 MemoryProvider 子类）^[plugins/memory/__init__.py:184-325]
- 单激活约束：Memory Manager 仅接受 1 个内置 provider + 1 个外部 provider；额外注册被警告拒绝 ^[agent/memory_manager.py:97-113]
- Provider 生命周期钩子：`is_available()`、`initialize()`、`system_prompt_block()`、`prefetch()`、`sync_turn()`、`handle_tool_call()`、`shutdown()`、`on_session_end()`、`on_pre_compress()`、`on_delegation()`、`on_memory_write()` ^[agent/memory_provider.py:42-232]
- Honcho 集成：AI-native 用户建模，dialectic QA + 语义搜索 + 持久化结论；有 `on_session_end` 钩子和专用的 CLI 命令 ^[plugins/memory/honcho/]
- Holographic 集成：本地 SQLite FTS5 事实存储 + 信任评分 + HRR（Holographic Reduced Representation）组合检索；有 `on_session_end` 钩子 ^[plugins/memory/holographic/]
- Context Engine 接口：`on_session_start()`、`update_from_response()`、`should_compress()`、`compress()`、`on_session_end()`，可通过 `context.engine` 配置替换默认 `compressor` ^[agent/context_engine.py:32-80, plugins/context_engine/__init__.py]
- CLI 发现：`discover_plugin_cli_commands()` 返回活跃 memory 插件的 CLI 子命令 ^[plugins/memory/__init__.py:322-332]

**源码证据**：
- 入口文件：plugins/memory/__init__.py、plugins/context_engine/__init__.py
- 核心函数：`def discover_memory_providers()` ^[plugins/memory/__init__.py:122]、`def load_memory_provider(name)` ^[plugins/memory/__init__.py:159]
