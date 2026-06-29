---
type: entity
repo: deepagents
slug: backend-protocol
problem: 如何为 AI Agent 的文件存储和命令执行定义统一的、可替换的后端接口
generated: 2026-06-28
source_files:
  - deepagents/backends/protocol.py
---

# Backend Protocol

**代码位置**：`deepagents/backends/protocol.py`
**这个模块解决什么问题**：
- 实现层：定义 `BackendProtocol`（文件操作：ls/read/write/edit/grep/glob/upload/download）和 `SandboxBackendProtocol`（扩展了 execute 命令执行）两个抽象协议，以及配套的结果类型（ReadResult、WriteResult、EditResult、LsResult、GrepResult、GlobResult、ExecuteResponse、FileData、FileDownloadResponse、FileUploadResponse）
- 问题层：如何让 Agent 中间件不依赖特定的存储实现（内存 state、磁盘文件系统、数据库、远程沙箱），而是通过统一的协议接口与任何兼容后端交互

**对外暴露什么**：
- `BackendProtocol` 抽象基类 -- `deepagents/backends/protocol.py:301`
- `SandboxBackendProtocol` 抽象基类 -- `deepagents/backends/protocol.py:730`
- `BackendFactory` 类型别名 -- `deepagents/backends/protocol.py:810`
- `BACKEND_TYPES` 类型别名 -- `deepagents/backends/protocol.py:811`
- 结果类型：`ReadResult`、`WriteResult`、`EditResult`、`LsResult`、`GrepResult`、`GlobResult`、`ExecuteResponse`
- 数据类型：`FileData`、`FileInfo`、`GrepMatch`、`FileDownloadResponse`、`FileUploadResponse`
- `FileOperationError` 字面量类型 -- `deepagents/backends/protocol.py:33`
- `execute_accepts_timeout(cls)` 工具函数 -- `deepagents/backends/protocol.py:788`

**它和谁交互**：
- 被 [[entities/filesystem-middleware]] 实现所有文件操作
- 被 [[entities/summarization-middleware]] 用于持久化对话历史
- 被 [[entities/memory-middleware]] 用于下载记忆文件
- 被 [[entities/skills-middleware]] 用于发现和下载技能文件
- 被 [[entities/state-backend]]、[[entities/composite-backend]] 等具体 backend 实现

**为什么它是可分离的**：`BackendProtocol` 是纯粹的接口定义——不包含任何实现逻辑。所有 async 方法默认通过 `asyncio.to_thread` 委托给 sync 版本。具体 backend 实现各自独立。

**关键机制**（源码可见）：
- 统一文件数据格式 v2：content 为 str（UTF-8 文本或 base64 编码的二进制），encoding 字段区分格式 ^[deepagents/backends/protocol.py:148-158]
- 标准化错误码：`file_not_found`、`permission_denied`、`is_directory`、`invalid_path` 四种可恢复错误的字面量，方便 LLM 理解和处理 ^[deepagents/backends/protocol.py:33-48]
- async 默认实现：所有 `a*` 方法默认通过 `asyncio.to_thread` 调用同步版本 ^[deepagents/backends/protocol.py:341-343]
- 旧 API 兼容层：`ls_info`、`glob_info`、`grep_raw` 等已弃用方法自动桥接到新 API 并发出 DeprecationWarning ^[deepagents/backends/protocol.py:593-707]
- execute timeout 检测：`execute_accepts_timeout` 通过 inspect.signature 缓存检查后端类是否接受 timeout 参数 ^[deepagents/backends/protocol.py:788-807]

**源码证据**：
- 入口文件：`deepagents/backends/protocol.py`
- 核心协议定义：`deepagents/backends/protocol.py:301`

**关联 Concept**：
- [[concepts/execution-isolation]]
