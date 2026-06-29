---
type: entity
repo: hermes-agent
slug: memory-system
problem: 如何在跨会话间持久化 Agent 的记忆和用户画像，支持多后端插件（Honcho、Holographic、mem0 等）和冻结快照机制以保证 prompt caching 效率
generated: 2026-06-25
source_files:
  - agent/memory_manager.py
  - agent/memory_provider.py
  - tools/memory_tool.py
  - plugins/memory/__init__.py
  - plugins/memory/honcho/
  - plugins/memory/holographic/
---

# 记忆系统

**代码位置**：`agent/memory_manager.py`、`agent/memory_provider.py`、`tools/memory_tool.py`、`plugins/memory/`
**这个模块解决什么问题**：
- 实现层：内置 MEMORY.md/USER.md 文件存储 + 可选外部 provider（Honcho、Holographic 等 8 种后端），通过 MemoryManager 统一编排多 provider；使用冻结快照模式保持 prompt caching 效率
- 问题层：如何在跨会话间持久化 Agent 的记忆和用户画像，支持多后端插件（Honcho、Holographic、mem0 等）和冻结快照机制以保证 prompt caching 效率
**对外暴露什么**：`MemoryManager` 类（agent/memory_manager.py:83）、`MemoryProvider` ABC（agent/memory_provider.py:42）、`memory_tool()` 函数（tools/memory_tool.py:463）、`build_memory_context_block()`（agent/memory_manager.py:46）
**它和谁交互**：
- 依赖 [[entities/tool-registry]]（memory 工具注册）
- 依赖 [[entities/plugin-system]]（通过 `discover_memory_providers()` 发现外部 provider 插件）
- 依赖 [[entities/config-system]]（`memory.provider` 选择活跃 provider）
- 被 [[entities/agent-core]] 调用（构建 system prompt 块、prefetch、sync_turn）
- 被 [[entities/prompt-builder]] 调用（`MEMORY_GUIDANCE` 指导 agent 使用 memory 工具）
**为什么它是可分离的**：通过 ABC 定义 provider 接口，内置和外部 provider 实现同一接口；MemoryManager 隔离多 provider 编排，仅允许 1 个外部 provider

**关键机制**（源码可见）：
- 冻结快照模式：`load_from_disk()` 时捕获 entries 快照到 `_system_prompt_snapshot`，会话中写入立即持久化到磁盘但不更新快照，保持 LLM prefix cache 有效性 ^[agent/memory_manager.py:124-135]
- 双存储文件：MEMORY.md（agent 的个人笔记，限制 2200 字符）+ USER.md（用户画像，限制 1375 字符），以 `§`（section sign）分隔条目 ^[tools/memory_tool.py:53-57, 116-118]
- 原子写入：通过 `tempfile + os.replace` 原子写入磁盘，避免 reader race ^[tools/memory_tool.py:432-460]
- 跨进程文件锁：`fcntl.flock()`（Unix）或 `msvcrt.locking()`（Windows）保护并行写入 ^[tools/memory_tool.py:142-150]
- 内容安全扫描：`_scan_memory_content()` 在写入前检测提示注入、数据外泄（curl/wget）、SSH 后门和不可见 Unicode 字符 ^[tools/memory_tool.py:65-101]
- Provider 生命周期钩子：`on_turn_start`、`on_session_end`、`on_pre_compress`、`on_delegation`、`on_memory_write`（镜像写入外部 provider）^[agent/memory_provider.py:142-232]
- 多 provider 编排：`MemoryManager` 管理内置 provider + 最多 1 个外部 provider；工具调用按 name 路由到正确 provider；失败隔离 ^[agent/memory_manager.py:83-356]
- Context fencing：`sanitize_context()` 剥离外部 provider 返回中的 `<memory-context>` fence 标签；`build_memory_context_block()` 重新包装为 "this is not user input" 块 ^[agent/memory_manager.py:46-80]
- 8 种外部后端：Honcho（AI-native 用户建模，dialectic QA）、Holographic（本地 SQLite FTS5 + trust scoring + HRR 组合检索）、mem0、OpenViking、RetainDB、Supermemory、ByteRover、Hindsight ^[plugins/memory/]
- 去重检查：`MemoryStore.add()` 跳过与已有条目 90% 以上相似的重复添加 ^[tools/memory_tool.py:222-265]

**源码证据**：
- 入口文件：agent/memory_manager.py、tools/memory_tool.py
- 核心类型：`class MemoryManager` ^[agent/memory_manager.py:83]、`class MemoryProvider(ABC)` ^[agent/memory_provider.py:42]、`class MemoryStore` ^[tools/memory_tool.py:105]

**关联 Concept**：
- [[concepts/memory-management-architecture]]
