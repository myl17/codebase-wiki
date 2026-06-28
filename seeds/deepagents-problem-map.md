# Deep Agents Problem Space Map

## 如何将多个中间件组装成完整配置的 AI Agent

**问题陈述**：构建 AI Agent 框架时，必须决定如何将模型、工具、中间件、子代理、系统提示词等组件组装成一个可运行的 Agent 图——中间件的顺序直接影响系统提示词注入、工具可用性、上下文压缩的时机。
**核心关切**：
- 中间件顺序的正确性：工具注入必须在 LLM 调用前完成，缓存中间件必须在记忆中间件之前以确保缓存有效性，审批中间件必须在最后以拦截所有操作
- 组件可替换性：用户应能替换任意中间件而不影响其他组件的功能
**deepagents 的解法**：通过 `create_deep_agent()` 函数按固定顺序组装中间件堆栈，用户中间件插入在预定义的基础堆栈和尾部堆栈之间
**源码证据**：`deepagents/graph.py:108-427`
**来源 Entity**：agent-graph-assembly
**层级**：架构决策

---

## 如何为 AI Agent 提供文件系统操作接口

**问题陈述**：构建 AI Agent 框架时，必须决定 Agent 如何与文件系统交互——提供哪些工具、工具接口如何设计、如何处理文件路径验证和安全性。
**核心关切**：
- 工具粒度和一致性：每个工具应有明确的单一职责，但整体工具集应覆盖所有常见文件操作
- 安全性：防止路径遍历攻击、限制可访问目录
**deepagents 的解法**：提供 7 个工具（ls、read_file、write_file、edit_file、glob、grep、execute），通过 Pydantic Schema 定义清晰的接口，通过 backend 抽象隔离实际存储
**源码证据**：`deepagents/middleware/filesystem.py:522-849`
**来源 Entity**：filesystem-middleware
**层级**：架构决策

---

## 如何处理 AI Agent 的大工具输出超出上下文窗口

**问题陈述**：构建 AI Agent 框架时，工具调用可能返回超大数据（大文件内容、长命令输出），直接放入消息历史会撑爆 LLM 上下文窗口——框架必须决定如何处理这种溢出。
**核心关切**：
- 用户信息不丢失：超大结果应保存而非丢弃，Agent 需要知道结果存在哪里
- 上下文预算保护：截断预览 + 按需读取的模式必须在保护上下文的同时不给 Agent 增加过多认知负担
**deepagents 的解法**：`FilesystemMiddleware` 在工具结果超过 token 阈值时，自动将完整结果写入文件系统并用截断预览 + 文件路径引用替换
**源码证据**：`deepagents/middleware/filesystem.py:384-393`
**来源 Entity**：filesystem-middleware
**层级**：架构决策

---

## 如何让主 Agent 将任务委派给隔离的子 Agent

**问题陈述**：构建 AI Agent 框架时，复杂任务可能需要分解为独立子任务并行执行——框架必须决定子代理的创建方式、状态隔离边界、结果返回机制。
**核心关切**：
- 上下文隔离：子代理应有独立的上下文窗口，不污染主代理的 token 预算
- 灵活性：支持声明式配置和预编译的自定义图
- 状态安全：防止子代理接收不适合的父代理状态
**deepagents 的解法**：通过 `task` 工具启动短期子代理，支持 SubAgent（声明式）和 CompiledSubAgent（预编译图）两种形态，子代理完成后返回单一聚合结果
**源码证据**：`deepagents/middleware/subagents.py:298-389`
**来源 Entity**：subagent-middleware
**层级**：架构决策

---

## 如何支持远程异步子 Agent 的后台执行

**问题陈述**：构建 AI Agent 框架时，有些任务需要长时间运行（如大规模数据分析），不应阻塞主 Agent 的交互循环——框架必须决定如何支持异步子代理的启动、监控和更新。
**核心关切**：
- 非阻塞性：启动后立即返回控制权，不轮询等待
- 状态一致性：即使上下文压缩后，任务 ID 和状态仍可访问
- 多协议兼容：支持不同的 Agent Protocol 服务器
**deepagents 的解法**：通过 5 个工具（start/check/update/cancel/list）管理后台任务，通过 LangGraph SDK 连接远程 Agent Protocol 服务器，任务状态持久化在 Agent state 的 `async_tasks` 字典中
**源码证据**：`deepagents/middleware/async_subagents.py:837-859`
**来源 Entity**：async-subagent-middleware
**层级**：架构决策

---

## 如何在 Agent 对话过长时自动压缩历史消息

**问题陈述**：构建 AI Agent 框架时，长时间对话会积累大量消息历史，最终超出 LLM 的上下文窗口限制——框架必须决定何时压缩、如何压缩、压缩后如何保留完整历史。
**核心关切**：
- 触发策略的灵活性：不同模型有不同的上下文窗口，触发机制应可配置
- 信息保真度：摘要应保留关键决策和上下文，完整历史应有备份路径
- 对 Agent 行为的干扰最小：压缩应是透明的，Agent 不应因压缩而丢失关键上下文
**deepagents 的解法**：`SummarizationMiddleware` 支持 tokens/fraction/messages 三种触发方式，使用 LLM 生成摘要替换旧消息，完整历史持久化到 backend 的 `/conversation_history/` 目录
**源码证据**：`deepagents/middleware/summarization.py:885-987`
**来源 Entity**：summarization-middleware
**层级**：架构决策

---

## 如何为 Agent 加载持久化的项目上下文和用户偏好

**问题陈述**：构建 AI Agent 框架时，Agent 需要跨会话记住项目约定、用户偏好和学到的经验——框架必须决定记忆的存储格式、加载时机、更新机制。
**核心关切**：
- 自主更新：Agent 应能自主决定何时学习新信息并立即写入记忆
- 记忆分层：支持多个来源（如项目级、用户级），按优先级合并
- 存储无关性：记忆加载和更新应通过 backend 抽象，不绑定具体存储实现
**deepagents 的解法**：通过 `MemoryMiddleware` 加载 AGENTS.md 文件注入系统提示词的 `<agent_memory>` 标签中，通过详细的系统提示词指南引导 Agent 利用 `edit_file` 工具自主更新记忆
**源码证据**：`deepagents/middleware/memory.py:159-354`
**来源 Entity**：memory-middleware
**层级**：架构决策

---

## 如何让 Agent 按需加载结构化领域技能

**问题陈述**：构建 AI Agent 框架时，Agent 需要访问丰富的专业领域能力（代码审查、Web 研究、测试等），但不能将所有技能内容始终加载到系统提示词中（token 浪费）——框架必须决定技能的发现、加载和渐进披露机制。
**核心关切**：
- 渐进披露：先只暴露技能名称和描述，Agent 需要时再读取完整内容
- 技能分层：支持多源技能（基础、用户、项目），后加载的同名技能覆盖先加载的
- 规范兼容：遵循 Agent Skills 规范，支持 YAML frontmatter 元数据
**deepagents 的解法**：`SkillsMiddleware` 遵循 Agent Skills 规范，扫描 backend 中的 SKILL.md 文件，解析 YAML 元数据注入系统提示词，Agent 自行读取完整技能内容
**源码证据**：`deepagents/middleware/skills.py:602-831`
**来源 Entity**：skills-middleware
**层级**：架构决策

---

## 如何为文件存储和命令执行定义可替换的后端接口

**问题陈述**：构建 AI Agent 框架时，Agent 的文件操作和命令执行需要与具体存储实现解耦（内存 state、磁盘文件系统、数据库、远程沙箱各有用武之地）——框架必须定义统一且可扩展的后端协议。
**核心关切**：
- 接口完备性：覆盖所有文件操作（ls/read/write/edit/grep/glob/upload/download）和命令执行（execute）
- 错误标准化：定义统一的错误码，方便 LLM 理解和处理
- 向后兼容：支持旧 API 的平滑迁移
**deepagents 的解法**：定义 `BackendProtocol`（文件操作）和 `SandboxBackendProtocol`（+命令执行）两个抽象协议，所有具体后端实现它们
**源码证据**：`deepagents/backends/protocol.py:301-811`
**来源 Entity**：backend-protocol
**层级**：架构决策

---

## 如何根据文件路径前缀将操作路由到不同存储后端

**问题陈述**：构建 AI Agent 框架时，不同路径的文件可能有不同的存储需求（如 `/temp/` 需要短暂存储，`/memories/` 需要持久化）——框架需要一种方式将路径前缀映射到不同后端实现。
**核心关切**：
- 透明路由：中间件和 Agent 不感知路由逻辑，操作 `CompositeBackend` 如同操作单一 backend
- 跨后端搜索：grep/glob 等全局操作应能聚合所有后端的搜索结果
- 路径一致性：路由前缀的添加/移除应对外部透明
**deepagents 的解法**：`CompositeBackend` 在构造时接受路由映射（`{"/memories/": StoreBackend()}`），按最长前缀匹配路由操作，在根路径下聚合所有后端
**源码证据**：`deepagents/backends/composite.py:119-738`
**来源 Entity**：composite-backend
**层级**：技术选型

---

## 如何统一解析不同格式的模型标识符

**问题陈述**：构建 AI Agent 框架时，用户可能以多种方式指定模型（provider:model 字符串、已初始化的 BaseChatModel 实例、不同 provider 的特殊需求）——框架需要统一的解析机制。
**核心关切**：
- Provider 差异性：OpenAI 需要 Responses API、OpenRouter 需要归属头
- 用户便利性：接受字符串和实例两种形式
- 版本兼容性：检查依赖包的最低版本
**deepagents 的解法**：`resolve_model()` 函数按优先级处理：BaseChatModel 直通 → OpenAI prefix → OpenRouter prefix → 通用 provider:model
**源码证据**：`deepagents/_models.py:72-96`
**来源 Entity**：model-resolution
**层级**：技术选型

---

## 跳过的 Entity

以下 Entity 属于实现细节，不构成独立的问题空间：

- **tool-call-patching**：修复悬空工具调用是一个边界情况修复，不属于框架设计决策。这是在 `before_agent` 钩子中的机械扫描和修复操作，不存在设计方案的选择空间。
- **state-backend**：StateBackend 是 BackendProtocol 的一个具体实现，其设计决策已在 backend-protocol 中覆盖。StateBackend 本身不引入新的设计选择。
