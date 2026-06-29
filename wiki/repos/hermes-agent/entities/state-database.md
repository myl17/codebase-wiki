---
type: entity
repo: hermes-agent
slug: state-database
problem: 如何持久化会话状态并支持跨会话全文搜索，处理多进程并发写入和 schema 演进
generated: 2026-06-25
source_files:
  - hermes_state.py
  - tools/session_search_tool.py
---

# 状态数据库

**代码位置**：`hermes_state.py`、`tools/session_search_tool.py`
**这个模块解决什么问题**：
- 实现层：SQLite WAL 模式会话存储（sessions + messages 表），内建 FTS5 全文搜索、6 版本 schema 迁移、jitter 重试写入和 session_search 工具供 agent 跨会话检索
- 问题层：如何持久化会话状态并支持跨会话全文搜索，处理多进程并发写入和 schema 演进
**对外暴露什么**：`SessionDB` 类（hermes_state.py:115）、`session_search()` 工具（tools/session_search_tool.py:297）
**它和谁交互**：
- 依赖 [[entities/model-adapters]]（session_search 通过 Gemini Flash 辅助模型并行摘要搜索结果）
- 被 [[entities/agent-core]] 调用（`_flush_messages_to_session_db()` 持久化消息；`update_token_counts()` 更新计数）
- 被 [[entities/gateway-runner]] 调用（GateWayRunner 初始化 SessionDB 实例）
- 被 [[entities/session-manager]] 调用（SessionStore 通过 SessionDB 持久化会话）
- 被 [[entities/cli-system]] 调用（session list/subcommands）
- 被 [[entities/web-server]] 调用（API 路由查询/删除会话）
- 被 insights-system 调用（InsightsEngine 使用 SessionDB 查询统计数据）
**为什么它是可分离的**：独立 SQLite 数据库，通过 Path 参数化路径，不绑定 agent 或 gateway 运行时

**关键机制**（源码可见）：
- WAL 模式：Write-Ahead Logging 支持多读者 + 单写者并发（gateway 多平台场景）^[hermes_state.py:157]
- Jitter 重试：写入冲突时随机 sleep 20-150ms 后重试（最多 15 次），避免 SQLite 内置确定性退避造成的 convoy effect ^[hermes_state.py:132-135, 180-210]
- WAL 检查点：每 50 次成功写入后尝试 PASSIVE checkpoint，防止 WAL 文件无限增长 ^[hermes_state.py:136, 216-235]
- FTS5 全文搜索：`messages_fts` 虚拟表 + 3 个触发器（insert/delete/update 自动同步），通过 `search_messages()` 查询 ^[hermes_state.py:93-112, 990-1040]
- 压缩感知会话拆分：上下文压缩时旧消息移入子会话（`parent_session_id` 引用父），支持会话 lineage 链 ^[hermes_state.py:48]
- 6 版本 Schema 迁移：从 v1 到 v6 逐步添加列（finish_reason, title, token 计数器, billing 字段, reasoning 列等），向后兼容 ^[hermes_state.py:252-332]
- 跨会话搜索工具：`session_search()` 使用 FTS5 找到匹配 → 加载会话 → 截断至 ~100k chars → `asyncio.gather` 并行 Gemini Flash 摘要 → 返回结构化结果 ^[tools/session_search_tool.py:297-498]
- 会话标题 lineage：支持 `title` → `title #2` → `title #3` 的自动递增命名，`get_next_title_in_lineage()` 查找最高编号 ^[hermes_state.py:682-715]
- 费用追踪：`update_token_counts()` 支持增量（CLI）和绝对值（gateway）两种模式，记录 billing_provider、estimated_cost_usd、actual_cost_usd 等 ^[hermes_state.py:412-500]
- 去重：`set_session_title()` 通过 WHERE 子句检查标题唯一性；`resolve_session_id()` 支持前缀匹配 ^[hermes_state.py:606-633, 532-557]
- 隐私：`_sanitize_fts5_query()` 清理 FTS5 查询中的特殊字符，防止 SQL 语法错误 ^[hermes_state.py:938-1021]

**源码证据**：
- 入口文件：hermes_state.py
- 核心类型：`class SessionDB` ^[hermes_state.py:115]
- 搜索工具：`def session_search(query, role_filter, limit, db)` ^[tools/session_search_tool.py:297]

**关联 Concept**：
- [[concepts/session-lifecycle-management]]
