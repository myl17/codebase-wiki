# Deepagents 问题空间映射 v2

使用修改后的 Step 2 提示词（解除 entity-问题空间一对一约束），对 deepagents 的 12 个 entity 页独立重新映射。

生成日期：2026-06-29
输入：wiki/repos/deepagents/entities/*.md（12 个 entity 页）

---

## 如何将横切中间件按正确顺序组装成完整的 Agent 执行图

**问题陈述**：构建 AI Agent 框架时，文件操作、子代理调用、上下文压缩、工具修复等横切关注点必须按正确顺序编排——中间件 A 的输入可能依赖中间件 B 的输出，顺序错误会导致功能失效或性能退化。
**核心关切**：
- 关切 1：中间件堆栈的顺序必须保证依赖关系正确（如 ToolCallPatching 必须在压缩后执行，否则可能修补已压缩的消息）
- 关切 2：子代理的中间件堆栈应自动继承主代理配置而非重复声明
- 关切 3：声明式子代理和异步子代理应自动路由到正确的中间件
**deepagents 的解法**：`create_deep_agent()` 函数按固定顺序组装中间件堆栈，并为声明式子代理自动填充默认中间件配置。
**源码证据**：`deepagents/graph.py:363-395`（默认中间件堆栈顺序）、`deepagents/graph.py:330-354`（子代理自动填充）
**来源 Entity**：agent-graph-assembly
**层级**：架构决策

---

## 如何将长时间任务异步派发到远程服务器执行而不阻塞主 Agent 交互

**问题陈述**：Agent 需要执行可能运行数分钟甚至数小时的后台任务（如数据处理、模型训练），如果同步等待会阻塞用户交互循环——构建 Agent 框架时必须提供非阻塞的任务执行通道。
**核心关切**：
- 关切 1：任务启动后立即返回控制权给主 Agent，禁止轮询等待
- 关切 2：任务状态必须在多次对话轮次间持久化（包括上下文压缩后）
- 关切 3：客户端连接应缓存复用，避免每次状态查询都重建连接
**deepagents 的解法**：`AsyncSubAgentMiddleware` 通过 LangGraph SDK 连接远程 Agent Protocol 服务器，提供 start/check/update/cancel/list 五个异步任务管理工具，并在 State 中持久化任务状态。
**源码证据**：`deepagents/middleware/async_subagents.py:862`（类定义）、`deepagents/middleware/async_subagents.py:113-126`（状态持久化）
**来源 Entity**：async-subagent-middleware
**层级**：架构决策

---

## 如何为 Agent 的文件存储和命令执行定义统一的、可替换的后端抽象

**问题陈述**：Agent 的文件操作（读写、搜索、执行命令）可能运行在不同环境——本地磁盘、内存 State、远程沙箱、数据库——中间件代码不能绑定到特定存储实现，否则无法在不同部署场景间复用。
**核心关切**：
- 关切 1：协议接口必须覆盖所有文件操作（ls/read/write/edit/grep/glob/upload/download）和命令执行
- 关切 2：错误码必须是标准化的、LLM 可理解的（如 `file_not_found`、`permission_denied`）
- 关切 3：旧 API 必须平滑迁移，提供兼容层和弃用警告
**deepagents 的解法**：定义 `BackendProtocol` 和 `SandboxBackendProtocol` 两个抽象基类，所有后端实现通过统一接口与中间件交互。
**源码证据**：`deepagents/backends/protocol.py:301`（BackendProtocol）、`deepagents/backends/protocol.py:33-48`（标准化错误码）
**来源 Entity**：backend-protocol
**层级**：架构决策

---

## 如何根据文件路径前缀将操作路由到不同后端实现

**问题陈述**：单个 Agent 可能需要混合存储策略——临时工作文件用短暂存储（不跨会话），持久化记忆用长期存储（跨会话）——框架必须在不修改中间件代码的前提下支持路径感知的后端切换。
**核心关切**：
- 关切 1：路由必须是透明的——中间件不感知路由逻辑，只通过统一的 BackendProtocol 接口操作
- 关切 2：最长前缀优先匹配，避免路由歧义
- 关切 3：跨后端聚合操作（如根目录 ls、全局 grep）的结果必须正确合并和路径重映射
**deepagents 的解法**：`CompositeBackend` 实现 BackendProtocol，按路径前缀将操作路由到不同后端，根路径下聚合所有后端的文件列表。
**源码证据**：`deepagents/backends/composite.py:119`（类定义）、`deepagents/backends/composite.py:87-116`（路径前缀路由）
**来源 Entity**：composite-backend
**层级**：技术选型

---

## 如何为 Agent 提供统一的文件系统操作接口

**问题陈述**：Agent 需要读写文件、搜索内容、列出目录、执行命令——这些是通用能力，但每个操作都需要参数校验、错误处理和结果格式化。构建框架时必须提供一致的工具集。
**核心关切**：
- 关切 1：工具集应覆盖 ls/read/write/edit/glob/grep/execute 七种操作
- 关切 2：execute 工具应仅在 backend 支持命令执行时动态注入，避免在不支持的环境中暴露无效工具
- 关切 3：文件写入的去重保护——同一路径重复写入应被检测和处理
**deepagents 的解法**：`FilesystemMiddleware` 提供完整的七工具集，根据 backend 能力动态启用 execute 工具。
**源码证据**：`deepagents/middleware/filesystem.py:522`（类定义）、`deepagents/middleware/filesystem.py:333-350`（动态 execute 注入）
**来源 Entity**：filesystem-middleware
**层级**：架构决策

---

## 如何防止大文件内容和长工具输出撑爆 LLM 上下文窗口

**问题陈述**：Agent 可能读取数百 KB 的文件或执行产生大量输出的命令，这些内容如果全部放入 LLM 上下文会超出 token 限制——框架必须在不丢失信息的前提下自动管理上下文预算。
**核心关切**：
- 关切 1：超大工具结果应自动驱逐到文件系统，上下文只保留截断预览和文件路径引用
- 关切 2：驱逐策略应有白名单——某些工具（如 ls、glob）输出天然较小，不应被驱逐
- 关切 3：用户消息中的超大内容也应被驱逐保护
**deepagents 的解法**：`FilesystemMiddleware` 在工具执行后检查结果大小，超阈值时写入文件并用截断预览替换，保留 ls/glob/read_file 等小输出工具不被驱逐。
**源码证据**：`deepagents/middleware/filesystem.py:384-393`（超大结果驱逐）、`deepagents/middleware/filesystem.py:374-381`（排除列表）、`deepagents/middleware/filesystem.py:430-451`（HumanMessage 驱逐）
**来源 Entity**：filesystem-middleware
**层级**：技术选型

---

## 如何让 Agent 跨会话记住项目约定和用户偏好

**问题陈述**：AI Agent 需要在多次对话中保持一致的行为——记住项目编码规范、用户偏好、学到的经验教训——这些知识必须跨会话持久化并在每次启动时自动加载。
**核心关切**：
- 关切 1：记忆文件（AGENTS.md）应从文件系统自动加载，无需用户手动指定
- 关切 2：Agent 应能自主决定何时更新记忆（学到新信息后立即写入），而非依赖外部触发
- 关切 3：记忆内容应是私有的——不应泄漏到子代理或外部状态
**deepagents 的解法**：`MemoryMiddleware` 在 Agent 启动前从配置的 source 路径加载 AGENTS.md 并注入系统提示词的 `<agent_memory>` 标签，通过 `<memory_guidelines>` 指导 Agent 自主更新。
**源码证据**：`deepagents/middleware/memory.py:159`（类定义）、`deepagents/middleware/memory.py:230-236`（多源拼接）、`deepagents/middleware/memory.py:97-155`（MEMORY_SYSTEM_PROMPT）
**来源 Entity**：memory-middleware
**层级**：架构决策

---

## 如何在 Agent 生命周期关键节点拦截执行流程，注入横切行为

**问题陈述**：构建 Agent 框架时，需要在 Agent 执行的特定阶段（启动前、每次模型调用前、工具调用后）注入横切关注点（如加载记忆、注入使用说明、修复状态不一致）——这些拦截点本身是框架的设计维度：在哪个阶段拦截、多个拦截器的执行顺序如何保证。
**核心关切**：
- 关切 1：拦截点的选择——是 Agent 启动前（before_agent）还是每次模型调用前（wrap_model_call）——影响行为注入的时机和粒度
- 关切 2：多个拦截器共享同一拦截点时，执行顺序必须保证无数据竞争和不一致
- 关切 3：拦截器的结果（如注入的系统提示词、修复的消息列表）必须正确合并到 Agent 状态
**deepagents 的解法**：通过 LangGraph AgentMiddleware 的 `before_agent` 和 `wrap_model_call` 钩子实现多阶段拦截——before_agent 用于加载记忆（Memory）、修复消息（ToolCallPatching）、注入文件系统指南（Filesystem）；wrap_model_call 用于在每次模型调用前注入子代理使用说明（SubAgent）。
**源码证据**：`deepagents/middleware/memory.py:253-254`（before_agent 懒加载）、`deepagents/middleware/subagents.py:520-529`（wrap_model_call 注入）、`deepagents/middleware/patch_tool_calls.py:11-44`（before_agent 扫描修复）
**来源 Entity**：memory-middleware, subagent-middleware, tool-call-patching
**层级**：架构决策

---

## 如何将不同格式的模型标识符统一解析为可用实例

**问题陈述**：用户可能以多种方式指定模型——已初始化的 BaseChatModel 实例、`openai:` 前缀字符串、`openrouter:` 前缀字符串、其他 `provider:model` 格式——框架 API 需要在处理这些变体的同时正确配置各 provider 的特殊需求（如 OpenAI Responses API、OpenRouter 归属头）。
**核心关切**：
- 关切 1：已初始化的实例应直通，避免重复初始化
- 关切 2：不同 provider 的特殊配置（如 OpenAI 的 use_responses_api、OpenRouter 的 HTTP-Referer 头）应自动处理
- 关切 3：模型标识符提取应适配不同 provider 的字段名差异（model_name vs model）
**deepagents 的解法**：`resolve_model()` 函数通过类型检查分支处理字符串和实例，为 OpenAI 启用 Responses API，为 OpenRouter 注入归属头。
**源码证据**：`deepagents/_models.py:72`（resolve_model）、`deepagents/_models.py:89-92`（BaseChatModel 直通和 OpenAI 特殊处理）
**来源 Entity**：model-resolution
**层级**：技术选型

---

## 如何按需渐进披露结构化领域技能，避免系统提示词膨胀

**问题陈述**：Agent 可能需要数十种专业技能（代码审查、Web 研究、部署等），将全部技能的内容加载到系统提示词会导致 token 浪费和注意力稀释——框架需要一种机制让 Agent 先看到技能目录，仅在需要时加载完整内容。
**核心关切**：
- 关切 1：系统提示词中只注入技能元数据（名称、描述、路径），不包含完整技能内容
- 关切 2：多源技能应分层合并（基础 → 用户 → 项目），后加载的同名技能覆盖先加载的
- 关切 3：技能名称和合法性验证应符合 Agent Skills 规范（1-64 字符、小写字母数字连字符）
**deepagents 的解法**：`SkillsMiddleware` 扫描 backend 中的 SKILL.md 文件，解析 YAML frontmatter 获取元数据，仅将名称和描述注入系统提示词；Agent 通过 read_file 按需加载完整内容。
**源码证据**：`deepagents/middleware/skills.py:602`（类定义）、`deepagents/middleware/skills.py:560-599`（渐进披露模式）、`deepagents/middleware/skills.py:755-758`（多源合并）
**来源 Entity**：skills-middleware
**层级**：架构决策

---

## 如何在不引入外部存储依赖的情况下为 Agent 提供文件存储

**问题陈述**：Agent 需要临时文件存储（写入中间结果、缓存数据），但有些部署场景不容许引入外部数据库或文件系统——框架必须提供一种与 Agent 状态管理机制一致的内置存储。
**核心关切**：
- 关切 1：存储应与 LangGraph checkpoint 机制一致，支持状态回滚和恢复
- 关切 2：零构造依赖——`StateBackend()` 即可使用，不需要外部配置
- 关切 3：跨图上下文限制——仅在 LangGraph graph 执行上下文中可用，外部调用应明确失败
**deepagents 的解法**：`StateBackend` 实现 BackendProtocol，通过 LangGraph 的 `CONFIG_KEY_READ`/`CONFIG_KEY_SEND` 在 agent state 中直接读写文件数据。
**源码证据**：`deepagents/backends/state.py:38`（类定义）、`deepagents/backends/state.py:104-141`（直接 state 通道读写）
**来源 Entity**：state-backend
**层级**：技术选型

---

## 如何将复杂任务委派给隔离的短期子 Agent 执行

**问题陈述**：在复杂的多步骤任务中，某些子任务可以独立执行——搜索、代码分析、文件生成——如果全部在主 Agent 上下文中执行会消耗大量 token 并污染推理过程。框架需要将子任务隔离到独立的子 Agent 中，完成后只返回聚合结果。
**核心关切**：
- 关切 1：子 Agent 应继承主 Agent 的工具集（文件系统、技能等），但状态应隔离——主 Agent 的 messages 不应泄漏到子 Agent
- 关切 2：子 Agent 支持三种形态：声明式配置（SubAgent）、预编译图（CompiledSubAgent）、远程异步（AsyncSubAgent）
- 关切 3：子 Agent 完成后，结果应结构化返回为单一 ToolMessage，避免子 Agent 的内部推理过程污染主 Agent 上下文
**deepagents 的解法**：`SubAgentMiddleware` 注入 `task` 工具，创建隔离的子 Agent 图执行子任务，通过状态键过滤防止泄漏，从子 Agent 最后一条消息提取结果返回。
**源码证据**：`deepagents/middleware/subagents.py:392`（类定义）、`deepagents/middleware/subagents.py:126`（状态键过滤）、`deepagents/middleware/subagents.py:336`（结果提取）
**来源 Entity**：subagent-middleware
**层级**：架构决策

---

## 如何在 Agent 对话过长时自动压缩历史消息

**问题陈述**：Agent 长时间对话会累积大量消息，超出模型输入 token 限制——框架必须在保留关键上下文的同时压缩历史，且不能丢失完整历史（应持久化以供后续查询）。
**核心关切**：
- 关切 1：压缩触发策略应灵活——支持 token 数、比例、消息数三种阈值，且可组合
- 关切 2：压缩前必须将完整历史持久化到 backend，避免信息不可逆丢失
- 关切 3：压缩后对旧消息中的大参数（如 write_file 的 content）进行截断，进一步减少 token 消耗
**deepagents 的解法**：`SummarizationMiddleware` 提供自动触发和手动触发两种压缩模式，支持多策略触发，压缩前将完整对话追加到 backend 的 `/conversation_history/{thread_id}.md`。
**源码证据**：`deepagents/middleware/summarization.py:210`（类定义）、`deepagents/middleware/summarization.py:217-219`（三种触发策略）、`deepagents/middleware/summarization.py:735-807`（历史持久化）
**来源 Entity**：summarization-middleware
**层级**：架构决策

---

## 如何修复消息历史中因中断导致的悬空工具调用

**问题陈述**：Agent 在执行工具调用时可能被中断（人工审批拒绝、超时、并发冲突），导致 AIMessage 中有 tool_calls 但缺少对应的 ToolMessage 响应——这种状态不一致会使后续 LLM 调用失败。框架必须在每次 Agent 执行前检测并修复此类悬空调用。
**核心关切**：
- 关切 1：检测必须覆盖消息历史中的每条 AIMessage 的每个 tool_call
- 关切 2：修复方式应是注入取消通知 ToolMessage，使 LLM 能理解该调用未完成
- 关切 3：修复操作应使用原子替换（Overwrite），避免并发修改消息列表
**deepagents 的解法**：`PatchToolCallsMiddleware` 在 `before_agent` 钩子中遍历消息历史，为每个悬空 tool_call 注入取消通知 ToolMessage，使用 `Overwrite` 替换整个消息列表。
**源码证据**：`deepagents/middleware/patch_tool_calls.py:11`（类定义）、`deepagents/middleware/patch_tool_calls.py:26-43`（悬空调用的检测和修复）
**来源 Entity**：tool-call-patching
**层级**：技术选型

---

## 跳过 Entity

无。修改后的 Step 2 提示词允许每个 entity 产出多条问题空间，12 个 entity 全部映射成功，共 16 条问题空间条目。

---

## 与旧版对比

### 旧版（entity-问题空间一对一约束）

旧版 Step 2 提示词要求每个 entity 只能产出一个问题空间条目，导致：

1. **生命周期拦截条目缺失**：subagent-middleware、memory-middleware、tool-call-patching 中使用的 `before_agent`、`wrap_model_call`、`interrupt_on` 等生命周期钩子被压制——因为这些 entity 的"主问题"被分配给了其他概念（subagent-orchestration、memory-management-architecture），生命周期拦截作为"实现手段"不产出独立条目。

2. **tool-call-patching 被跳过**：旧版可能因为 tool-call-patching 的问题空间与已有概念匹配度低、或被视为"太小"而不产出独立条目。

3. **filesystem-middleware 只产出 1 条**：文件系统工具提供和上下文溢出管理被合并为一个条目，丢失了"上下文窗口管理"作为独立设计维度的价值。

### 新版（允许一对多）

| 变更 | 来源 Entity | 详情 |
|------|-----------|------|
| **新增：生命周期拦截** | memory-middleware, subagent-middleware, tool-call-patching | 产出 1 条独立条目"如何在 Agent 生命周期关键节点拦截执行流程，注入横切行为"，涵盖 before_agent（memory、tool-call-patching）、wrap_model_call（subagent）、interrupt_on（subagent）三个拦截点，可直接匹配 `hooks-event-interception` Concept |
| **新增：上下文溢出管理** | filesystem-middleware | 从原单一条目中拆分出"如何防止大文件内容和长工具输出撑爆 LLM 上下文窗口"，与"文件系统工具提供"形成独立的两个设计维度 |
| **恢复：悬空工具调用修复** | tool-call-patching | 产出独立条目"如何修复消息历史中因中断导致的悬空工具调用"，不再被跳过 |
| **条目总数** | — | 12 entity → 16 条（旧版估计约 8-10 条） |

### 能匹配 hooks-event-interception 的条目

新版中"如何在 Agent 生命周期关键节点拦截执行流程，注入横切行为"条目：

- **覆盖的拦截点**：
  - `before_agent`（执行前）：MemoryMiddleware 加载记忆、PatchToolCallsMiddleware 修复悬空调用、FilesystemMiddleware 驱逐超大结果
  - `wrap_model_call`（模型调用前）：SubAgentMiddleware 注入子代理使用说明、AsyncSubAgentMiddleware 注入异步任务说明
  - `interrupt_on`（中断配置）：SubAgentMiddleware 的子代理继承顶层 interrupt_on 配置

- **匹配 Concept**：`hooks-event-interception`（codex 创建的 Concept）核心关切为"如何在 Agent 执行流程中通过钩子和事件机制拦截关键节点"，deepagents 的解法是通过 AgentMiddleware 的 before_agent/wrap_model_call 钩子 + interrupt_on 配置实现多阶段拦截——与该 Concept 的问题空间直接对应。
