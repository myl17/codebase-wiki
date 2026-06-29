---
type: entity
repo: deepagents
slug: state-backend
problem: 如何为 Agent 提供基于 LangGraph 状态管理的短暂文件存储
generated: 2026-06-28
source_files:
  - deepagents/backends/state.py
---

# State Backend

**代码位置**：`deepagents/backends/state.py`
**这个模块解决什么问题**：
- 实现层：`StateBackend` 实现 `BackendProtocol`，将文件数据存储在 LangGraph 的 agent state 中。文件在对话线程内持久化，但不跨线程。通过 `CONFIG_KEY_READ`/`CONFIG_KEY_SEND` 直接读写 state channel，实现与其他 state 更新一致的 checkpoint 语义
- 问题层：如何在不引入外部存储依赖的情况下，为 Agent 的文件操作提供与 LangGraph checkpoint 机制一致的短暂存储

**对外暴露什么**：
- `StateBackend` 类 -- `deepagents/backends/state.py:38`

**它和谁交互**：
- 实现 [[entities/backend-protocol]]
- 被 [[entities/agent-graph-assembly]] 用作默认 backend（当 `create_deep_agent` 未指定 backend 时）
- 被 [[entities/filesystem-middleware]] 通过 BackendProtocol 接口使用
- 依赖 LangGraph's `CONFIG_KEY_READ`/`CONFIG_KEY_SEND` 机制

**为什么它是可分离的**：`StateBackend` 是 `BackendProtocol` 的一个具体实现，通过 LangGraph 内部机制管理存储。可以替换为 `StoreBackend`、`FilesystemBackend` 等其他实现而不影响上层中间件。

**关键机制**（源码可见）：
- 无构造依赖：`StateBackend()` 即可使用，已弃用的 `runtime` 参数被忽略；通过 `get_config()` 在运行时获取 graph context ^[deepagents/backends/state.py:50-74]
- 直接 state 通道读写：通过 `CONFIG_KEY_READ(files, fresh=False)` 读取，`CONFIG_KEY_SEND` 写入，不返回 `files_update` 字典 ^[deepagents/backends/state.py:104-141]
- 文件格式版本：支持 `v2`（默认，content 为 str）和 `v1`（legacy，content 为 list[str]）^[deepagents/backends/state.py:50-74]
- ls 实现：通过路径前缀匹配过滤 state files 字典，自动识别子目录 ^[deepagents/backends/state.py:152-201]
- write 去重保护：写入前检查文件是否已存在，防止覆盖 ^[deepagents/backends/state.py:242-258]
- 跨图上下文限制：`StateBackend` 必须在 LangGraph graph 执行上下文中使用，外部调用会抛出 RuntimeError ^[deepagents/backends/state.py:80-102]

**源码证据**：
- 入口文件：`deepagents/backends/state.py`
- 核心类定义：`deepagents/backends/state.py:38`

**关联 Concept**：
- [[concepts/execution-isolation]]
