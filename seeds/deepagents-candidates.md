# Deep Agents Candidate List

## A 类 — 追加到已有 Concept 页

### A1: 同步子代理委派 → subagent-orchestration
- **问题名**：如何让主 Agent 将任务委派给隔离的子 Agent
- **目标 slug**：subagent-orchestration
- **理由**：deepagents 通过 `task` 工具启动短期同步子代理，支持 SubAgent（声明式配置）和 CompiledSubAgent（预编译图）两种形态。与已有 repos（nanobot 的 subagent-manager、openclaw 的 subagent-system、hermes-agent 的 delegate-subagent）面对同一核心问题——如何隔离执行复杂子任务。deepagents 的独特贡献：声明式 vs 编译式双形态、状态键过滤防止父状态泄漏。

### A2: 远程异步子代理 → subagent-orchestration
- **问题名**：如何支持远程异步子 Agent 的后台执行
- **目标 slug**：subagent-orchestration
- **理由**：deepagents 的 `AsyncSubAgentMiddleware` 是 subagent-orchestration 的异步/远程变体——通过 LangGraph SDK 连接远程 Agent Protocol 服务器，提供 start/check/update/cancel/list 五工具套件。与同步子代理互补，共享同一核心问题。独特贡献：后台任务的非阻塞模型、任务状态跨压缩持久化。

### A3: 对话自动摘要压缩 → context-compression-strategy
- **问题名**：如何在 Agent 对话过长时自动压缩历史消息
- **目标 slug**：context-compression-strategy
- **理由**：deepagents 的 `SummarizationMiddleware` 使用 LLM 生成摘要替换旧消息，完整历史持久化到 backend。支持 tokens/fraction/messages 三种触发策略。与已有 repos（nanobot 的 context-builder、openclaw 的压缩机制、hermes-agent 的 context-compressor）面对同一核心问题。独特贡献：model-aware 默认阈值、工具参数预截断、链式摘要事件管理。

### A4: 大工具结果驱逐 → context-compression-strategy
- **问题名**：如何处理 AI Agent 的大工具输出超出上下文窗口
- **目标 slug**：context-compression-strategy
- **理由**：deepagents 的 `FilesystemMiddleware` 在工具结果超过 token 阈值时自动驱逐到文件系统。这是 context-compression-strategy 的一个具体机制（结果级压缩，而非对话级摘要）。独特贡献：工具级驱逐粒度、排除列表（ls/grep/glob 不驱逐）。

### A5: 记忆加载与自主更新 → memory-management-architecture
- **问题名**：如何为 Agent 加载持久化的项目上下文和用户偏好
- **目标 slug**：memory-management-architecture
- **理由**：deepagents 的 `MemoryMiddleware` 加载 AGENTS.md 文件注入系统提示词，通过详细指南引导 Agent 自主更新记忆。与已有 repos（nanobot 的 memory-system、hermes-agent 的 memory-system）面对同一核心问题。独特贡献：AGENTS.md 规范遵循、自主更新机制（Agent 学习新信息 → 立即写入）。

### A6: 技能渐进披露 → skills-extension-mechanism
- **问题名**：如何让 Agent 按需加载结构化领域技能
- **目标 slug**：skills-extension-mechanism
- **理由**：deepagents 的 `SkillsMiddleware` 遵循 Agent Skills 规范，扫描 backend 中的 SKILL.md 文件，解析 YAML 元数据实现渐进披露。与已有 repos（nanobot 的 skills-loader、openclaw 的 skills、hermes-agent 的 skills-system）面对同一核心问题。独特贡献：Agent Skills 规范遵循、多源合并（last one wins）、隐私状态标记。

### A7: 后端协议定义 → execution-isolation
- **问题名**：如何为文件存储和命令执行定义可替换的后端接口
- **目标 slug**：execution-isolation
- **理由**：deepagents 的 `BackendProtocol` 和 `SandboxBackendProtocol` 定义了统一的后端接口契约。与已有 repos（openclaw 的 sandbox、hermes-agent 的 terminal-execution）面对同一核心问题——如何抽象执行环境。独特贡献：标准化的协议接口设计（而非具体实现）、标准化错误码供 LLM 理解、文件格式版本管理。

### A8: 多后端路由 → execution-isolation
- **问题名**：如何根据文件路径前缀将操作路由到不同存储后端
- **目标 slug**：execution-isolation
- **理由**：deepagents 的 `CompositeBackend` 按路径前缀将操作路由到不同后端（如 `/temp/` → StateBackend、`/memories/` → StoreBackend）。是 execution-isolation 的存储路由层面。独特贡献：透明路由（中间件不感知）、跨后端全局搜索聚合。

### A9: 模型标识符解析 → provider-abstraction-pattern
- **问题名**：如何统一解析不同格式的模型标识符
- **目标 slug**：provider-abstraction-pattern
- **理由**：deepagents 的 `resolve_model()` 统一解析 provider:model 字符串和 BaseChatModel 实例，处理 OpenAI Responses API 和 OpenRouter 归属头等特例。与已有 repos（nanobot 的 provider-system、openclaw 的 model-configuration、hermes-agent 的 model-adapters）面对同一核心问题。独特贡献：多种输入格式的统一入口、provider 特例的集中处理。

## B 类 — 新建 Concept 页

### B1: middleware-composition-pattern（中间件组合模式）
- **问题名**：如何将多个中间件按正确顺序组装成完整配置的 AI Agent 图
- **新建 slug**：middleware-composition-pattern
- **判断理由**：
  ① **多方案**：nanobot 用一次性的 context-builder 模式组装 pipeline，openclaw 用运行时 hook 管道，hermes-agent 用事件驱动的 prompt-builder，deepagents 用固定顺序的中间件堆栈。四个仓库用明显不同的方式解决组件组装问题。✅
  ② **独立设计空间**：中间件顺序决定"工具何时可用""系统提示词何时注入""缓存是否有效""审批何时拦截"，其评价维度（可预测性、可替换性、扩展点灵活性）独立于"提示词文本内容"（system-prompt-assembly）和"运行时循环"（agent-loop-orchestration）。✅
  ③ **持续 Trade-off**：固定顺序（deepagents）提供可预测性和正确性保证，但用户无法自由调整顺序；可配置顺序提供灵活性，但引入排序错误的可能性。这是真正的设计权衡，无银弹。✅
  ④ **可持续扩展**：随着 Agent 框架继续演化，中间件/插件/钩子的组合方式仍会是一个活跃的设计空间。✅

## C 类 — 待观察

（无）

## D 类 — 演化信号

### D1: 文件系统工具接口设计
- **问题**：如何为 AI Agent 提供文件系统操作接口
- **相关 Concept**：tool-lifecycle-management
- **信号类型**：粒度不匹配
- **理由**：deepagents 的文件系统工具设计（7 个工具、Pydantic Schema、backend 抽象解耦）是 tool-lifecycle-management 的子维度——它关注的是"工具应该设计成什么样"而非"工具如何注册/发现/过滤"。建议在 tool-lifecycle-management 中新增"工具设计模式"小节。详见 evolve-signals/2026-06-28-deepagents.md。

---

## 能力域覆盖表

| 能力域 | nanobot | hermes-agent | openclaw | deepagents |
|--------|---------|-------------|----------|------------|
| Agent 主循环编排 | ✅ | ✅ | ✅ | — |
| 中间件组合模式 | ✅ (context-builder) | ✅ (prompt-builder) | ✅ (hook pipeline) | ✅ (middleware stack) |
| 上下文压缩 | ✅ | ✅ | ✅ | ✅ |
| 子代理编排 | ✅ | ✅ | ✅ | ✅ |
| 记忆管理 | ✅ | ✅ | — | ✅ |
| 技能扩展 | ✅ | ✅ | ✅ | ✅ |
| 工具生命周期 | ✅ | ✅ | ✅ | ✅ |
| Provider 抽象 | ✅ | ✅ | ✅ | ✅ |
| 执行隔离 | — | ✅ | ✅ | ✅ |
| 系统提示词组装 | ✅ | ✅ | — | — |
| 会话生命周期 | ✅ | ✅ | ✅ | — |
| 安全架构 | ✅ | ✅ | ✅ | — |
| 渠道抽象 | ✅ | ✅ | ✅ | — |
| 配置管理 | — | ✅ | ✅ | — |
| 执行审批 | — | ✅ | ✅ | — |
| 自主调度 | ✅ | ✅ | ✅ | — |
