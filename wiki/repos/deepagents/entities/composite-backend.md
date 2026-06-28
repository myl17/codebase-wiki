---
type: entity
repo: deepagents
slug: composite-backend
problem: 如何根据文件路径前缀将操作路由到不同的后端实现，实现混合存储策略
generated: 2026-06-28
source_files:
  - deepagents/backends/composite.py
---

# Composite Backend

**代码位置**：`deepagents/backends/composite.py`
**这个模块解决什么问题**：
- 实现层：`CompositeBackend` 实现 `BackendProtocol`，根据文件路径前缀将操作路由到不同的后端（如 `StateBackend` 用于临时文件，`StoreBackend` 用于持久化记忆）。路径匹配使用最长前缀优先
- 问题层：如何在单个 Agent 中使用不同特性的存储后端——比如临时工作文件用短暂存储，长期记忆用持久化存储——而不需要中间件感知路由逻辑

**对外暴露什么**：
- `CompositeBackend` 类 -- `deepagents/backends/composite.py:119`
- `artifacts_root` 属性 -- `deepagents/backends/composite.py:165`

**它和谁交互**：
- 实现 [[entities/backend-protocol]]
- 包装 [[entities/state-backend]] 和其他 backend
- 被 [[entities/filesystem-middleware]] 用于确定 `large_tool_results` 和 `conversation_history` 的存储路径
- 被 [[entities/summarization-middleware]] 用于确定对话历史持久化路径

**为什么它是可分离的**：`CompositeBackend` 是纯粹的代理/路由层——它不实现任何存储逻辑，只做路径匹配和转发。路由配置在构造时确定。

**关键机制**（源码可见）：
- 路径前缀路由：按 `sorted_routes`（前缀长度降序）匹配，最长前缀优先；未匹配路由的路径使用 default backend ^[deepagents/backends/composite.py:87-116]
- ls 聚合：在根路径 `/` 下聚合所有 backend 的目录列表，路由路径显示为虚拟目录 ^[deepagents/backends/composite.py:213-229]
- grep/glob 跨 backend 搜索：在 `/` 路径下的搜索会遍历所有 backend 并合并结果，自动为匹配结果添加路由前缀 ^[deepagents/backends/composite.py:307-363]
- upload/download 批量优化：按目标 backend 分组文件，每个 backend 调用一次批量 API ^[deepagents/backends/composite.py:600-738]
- execute 委托：命令执行总路由到 default backend，不支持按路径路由 ^[deepagents/backends/composite.py:538-598]
- 结果路径重映射：write/edit 成功后，将 backend 返回的内部路径替换为带路由前缀的原始路径 ^[deepagents/backends/composite.py:482-486]

**源码证据**：
- 入口文件：`deepagents/backends/composite.py`
- 核心类定义：`deepagents/backends/composite.py:119`

**关联 Concept**：
- [[concepts/execution-isolation]]
