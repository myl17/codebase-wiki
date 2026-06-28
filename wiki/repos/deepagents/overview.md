# Deep Agents

**仓库**：`deepagents`  
**描述**：Deep Agents 是一个基于 LangChain/LangGraph 的 AI Agent 框架，通过中间件堆栈模式为 Agent 提供文件系统、子代理委派、对话压缩、技能系统、记忆管理等能力。核心设计哲学是"中间件优于扁平工具"——中间件可以拦截每次 LLM 请求以修改系统提示词、动态过滤工具列表、管理跨轮次状态，而普通工具函数只能被 LLM 调用。

**核心子系统**：

### Agent 组装
- [[repos/deepagents/entities/agent-graph-assembly]]：`create_deep_agent()` 入口函数，按固定顺序组装中间件堆栈

### 中间件层
- [[repos/deepagents/entities/filesystem-middleware]]：提供 ls、read_file、write_file、edit_file、glob、grep、execute 工具，自动驱逐超大结果
- [[repos/deepagents/entities/subagent-middleware]]：通过 task 工具同步启动短期子代理，隔离上下文执行复杂任务
- [[repos/deepagents/entities/async-subagent-middleware]]：通过 LangGraph SDK 连接远程 Agent Protocol 服务器，启动/监控/更新后台异步子代理
- [[repos/deepagents/entities/summarization-middleware]]：自动发送 LLM 摘要压缩长对话，持久化完整历史到 backend
- [[repos/deepagents/entities/memory-middleware]]：加载 AGENTS.md 文件注入系统提示词，引导 Agent 自主更新记忆
- [[repos/deepagents/entities/skills-middleware]]：遵循 Agent Skills 规范，渐进披露技能元数据，按需加载完整技能
- [[repos/deepagents/entities/tool-call-patching]]：修复中断导致的悬空工具调用，保持消息历史一致性

### 后端层
- [[repos/deepagents/entities/backend-protocol]]：定义 BackendProtocol 和 SandboxBackendProtocol 两个统一后端接口
- [[repos/deepagents/entities/state-backend]]：基于 LangGraph 状态的短暂存储（默认）
- [[repos/deepagents/entities/composite-backend]]：按路径前缀路由到不同后端，实现混合存储策略

### 基础设施
- [[repos/deepagents/entities/model-resolution]]：统一解析 provider:model 字符串、BaseChatModel 实例，处理 OpenAI/OpenRouter 特例

**明确不做什么**：
- 不实现自己的 LLM 客户端——依赖 `langchain-core` 和 `langchain-anthropic`
- 不提供 UI 或 Web 界面——纯 SDK 库
- 不管理 Agent 部署或编排——异步子代理通过与 Agent Protocol 服务器交互实现，但部署由外部平台（如 LangSmith）管理
