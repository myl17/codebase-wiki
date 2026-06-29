---
type: entity
repo: nanobot
slug: session-manager
problem: 如何持久化管理 Agent 的多会话对话历史，支持高效读写和内存缓存
generated: 2026-06-25
source_files:
  - nanobot/session/manager.py
---

# Session Manager

**代码位置**：`nanobot/session/manager.py`
**这个模块解决什么问题**：
- 实现层：基于 JSONL 文件的会话持久化，内存缓存会话对象，按 `channel:chat_id` 键隔离会话，支持旧版路径迁移、legal message boundary 裁剪
- 问题层：如何持久化管理 Agent 的多会话对话历史，支持高效读写和内存缓存
**对外暴露什么**：`Session` dataclass（nanobot/session/manager.py:17）、`SessionManager` 类（nanobot/session/manager.py:96）
**它和谁交互**：
- 被 [[entities/agent-loop]] 调用（获取/保存会话、恢复 checkpoint）
- 被 [[entities/memory-system]] 调用（Consolidator 读取会话消息做压缩）
**为什么它是可分离的**：独立管理器，仅依赖文件系统，可替换为数据库后端

**关键机制**（源码可见）：
- JSONL 格式：第一行是 `_type: "metadata"` 的元数据记录（包含 key、created_at、last_consolidated），后续行是消息条目，每行一个 JSON 对象 ^[nanobot/session/manager.py:189-201]
- 合法消息边界：`get_history()` 确保返回的消息序列从 user 消息开始，不包含孤立的 tool 结果，保证 LLM 接收的消息序列格式正确 ^[nanobot/session/manager.py:38-61]
- 旧版迁移：自动将 `~/.nanobot/sessions/` 下的旧版 session 文件迁移到 workspace 的 `sessions/` 目录 ^[nanobot/session/manager.py:142-150]
- 内存缓存：`_cache: dict[str, Session]` 避免每次访问都读文件，save 时同步更新缓存 ^[nanobot/session/manager.py:107, 203]

**源码证据**：
- 入口文件：nanobot/session/manager.py
- 核心类型/接口定义：`@dataclass class Session` ^[nanobot/session/manager.py:17]、`class SessionManager` ^[nanobot/session/manager.py:96]

**关联 Concept**：
- [[concepts/session-lifecycle-management]]
