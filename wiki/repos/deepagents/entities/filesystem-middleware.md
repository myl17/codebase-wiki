---
type: entity
repo: deepagents
slug: filesystem-middleware
problem: 如何为 AI Agent 提供统一的文件系统操作接口，同时自动管理上下文窗口溢出
generated: 2026-06-28
source_files:
  - deepagents/middleware/filesystem.py
---

# Filesystem Middleware

**代码位置**：`deepagents/middleware/filesystem.py`
**这个模块解决什么问题**：
- 实现层：通过 `FilesystemMiddleware` 提供 ls、read_file、write_file、edit_file、glob、grep 工具，并根据 backend 能力动态添加 execute 工具；自动将超大工具结果驱逐到文件系统以避免上下文窗口溢出
- 问题层：如何在为 Agent 提供灵活的文件系统访问能力的同时，防止大文件内容和长工具输出撑爆 LLM 上下文窗口

**对外暴露什么**：
- `FilesystemMiddleware` 类 -- `deepagents/middleware/filesystem.py:522`
- `FilesystemState` 状态类 -- `deepagents/middleware/filesystem.py:114`
- 工具 Schema：`LsSchema`、`ReadFileSchema`、`WriteFileSchema`、`EditFileSchema`、`GlobSchema`、`GrepSchema`、`ExecuteSchema`

**它和谁交互**：
- 依赖 [[entities/backend-protocol]]（通过 BackendProtocol 接口读写文件）
- 被 [[entities/agent-graph-assembly]] 组装进中间件堆栈
- 被 [[entities/subagent-middleware]] 的子代理继承
- 使用 `_utils.append_to_system_message` 注入文件系统使用说明

**为什么它是可分离的**：`FilesystemMiddleware` 是独立的 AgentMiddleware 子类，有自己的 State Schema、工具集和系统提示词模板。它通过 BackendProtocol 与后端解耦，可插入任何兼容 backend 的 Agent。

**关键机制**（源码可见）：
- 动态 execute 工具：仅在 backend 实现 `SandboxBackendProtocol` 时注入 execute 工具 ^[deepagents/middleware/filesystem.py:333-350]
- 超大结果驱逐：当工具结果超过 token 阈值时，将完整结果写入文件系统并用截断预览 + 文件路径引用替换，避免上下文膨胀 ^[deepagents/middleware/filesystem.py:384-393]
- 排除列表：ls、glob、grep、read_file、edit_file、write_file 工具从不驱逐——它们有自己的截断机制或输出很小 ^[deepagents/middleware/filesystem.py:374-381]
- 文件合并 reducer：`_file_data_reducer` 支持通过 `None` 值标记文件删除 ^[deepagents/middleware/filesystem.py:78-111]
- HumanMessage 驱逐：超大的用户消息内容也可驱逐到文件系统 ^[deepagents/middleware/filesystem.py:430-451]
- 双后端解析：支持直接实例和工厂可调用两种 backend 传入方式 ^[deepagents/middleware/filesystem.py:632-650]

**源码证据**：
- 入口文件：`deepagents/middleware/filesystem.py`
- 核心类定义：`deepagents/middleware/filesystem.py:522`
- 工具创建方法：`deepagents/middleware/filesystem.py:652-849`

**关联 Concept**：
- [[concepts/context-compression-strategy]]（工具结果驱逐机制）
