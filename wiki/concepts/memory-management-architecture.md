---
type: concept
concept: memory-management-architecture
problem: 如何管理 Agent 的长期记忆，在跨会话间持久化知识和用户画像
concerns: [存储后端多样性, 缓存一致性, 自主演化能力]
repos: [nanobot, hermes-agent, openclaw, deepagents]
generated: 2026-06-25
---

# 记忆管理架构

## 核心问题

Agent 的长期记忆不像数据库查询那样可以按需检索——它必须在每次 LLM 调用时作为系统提示词的一部分注入，但又不能像会话历史那样无限膨胀。这个约束催生了一个根本性的架构张力：**记忆需要既是活的（可被 Agent 自主写入和演化），又是冻结的（保持 LLM prefix cache 有效性）。** 写入越频繁，快照越容易过时；快照越冻结，Agent 越看不到自己的最新变化。

第二个张力来自**存储后端的多样性**。跨会话持久化最简单的方案是本地文件（MEMORY.md / USER.md），但一旦用户需要跨设备同步或多租户隔离，就必须引入外部 provider（向量数据库、图数据库、专用记忆服务）。如何在保持简单本地方案的同时，架构上不排斥外部后端——决定了记忆系统能否从 CLI 单用户工具扩展到平台级服务。

第三个张力是**自主演化**的深度。最简单的记忆系统只是被动读写文件；最激进的则是 Agent 在后台（cron）自主分析自己的历史、编辑自己的记忆文件、甚至 git commit。自主性越高，错误修正的成本越低（Agent 自己改），但失控风险越大（Agent 可能覆盖人工编辑的内容）。

## 关切

- **存储后端多样性**：是纯文件还是支持外部 provider？外部 provider 如何发现和注册？多 provider 如何编排？
- **缓存一致性**：写入是否立即更新 LLM 可见快照？冻结快照模式如何平衡 freshness 和 prefix cache？读写锁机制如何防止 race？
- **自主演化能力**：Agent 能否自主压缩、整理、编辑自己的记忆？演化是实时触发（token 预算驱动）还是后台 cron？有多段回退机制？

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/memory-system]]
**解法**：三层递进架构——被动文件 I/O → token 预算触发压缩 → cron 驱动深度整理，每层增加自主性。
**实现**：MemoryStore 管理 MEMORY.md + history.jsonl + SOUL.md + USER.md 的文件读写；Consolidator 在 token 超预算时触发，LLM 摘要旧消息追加到 history.jsonl，降级时 raw dump；Dream 两阶段 cron job——Phase 1 分析 history.jsonl 生成摘要，Phase 2 委托 AgentRunner 用 read_file/edit_file 增量编辑、最后 git commit。.dream_cursor 追踪已处理条目避免重复。^[nanobot/agent/memory.py:27-29, 346-512, 519-675, 304-313]
**权衡**：自主演化最深——Dream 是唯一能用 LLM 自主编辑自己记忆文件的方案，三层递进满足不同紧迫度。但无外部 provider 支持，纯本地文件；无冻结快照机制，每次写入后必须重读文件，cache 友好度低；无进程锁保护，多实例并发写入不安全。

### hermes-agent
来源：[[repos/hermes-agent/entities/memory-system]]
**解法**：内置文件存储 + 可选外部 provider 插件，通过 MemoryManager 统一编排，冻结快照模式保护 cache。
**实现**：内置 MEMORY.md/USER.md 以 § 分隔条目，原子写入（tempfile + os.replace）+ fcntl 文件锁保护并发。冻结快照模式在 load 时捕获 entries 快照，会话中写入立即落盘但不更新快照。MemoryProvider ABC 定义 5 个生命周期钩子（on_turn_start/on_session_end/on_pre_compress/on_delegation/on_memory_write）。8 种外部后端可插拔（Honcho、Holographic 等）。内容安全扫描在写入前检测提示注入和数据外泄。^[agent/memory_manager.py:83-356, 124-135; tools/memory_tool.py:53-57, 116-118, 65-101, 432-460, 142-150]
**权衡**：存储后端最丰富——单一接口下 8 种外部 backend，且内置方案的并发安全性最完善（文件锁 + 原子写入）。冻结快照直接为 prompt caching 优化。但自主演化最弱——无 consolidation 机制，无 cron 驱动整理，Agent 只能被动读写，不能自主压缩或编辑记忆。

### deepagents
来源：[[repos/deepagents/entities/memory-middleware]]
**解法**：AGENTS.md 规范驱动——加载 AGENTS.md 文件注入系统提示词 `<agent_memory>` 标签，通过详细指南引导 Agent 利用 `edit_file` 工具自主更新记忆，多源拼接加载。
**实现**：MemoryMiddleware 在 `before_agent` 钩子中通过 backend.download_files 从配置的 sources 路径批量加载 AGENTS.md 文件。文件缺失（`file_not_found`）静默跳过不阻塞 Agent 启动。多源按顺序拼接为 `path + content` 格式。系统提示词中的 `<memory_guidelines>` 标签提供详细的更新时机指南（何时更新：用户明确要求、角色定义、反馈纠正、工具使用信息；何时不更新：临时信息、一次性任务、闲聊、凭据）。`memory_contents` 使用 PrivateStateAttr 标记，不包含在最终 Agent 状态中。懒加载机制：state 中已有 `memory_contents` 时跳过重复加载，支持从 checkpoint 恢复。记忆更新方式依赖 Agent 通过 `edit_file` 工具直接编辑 AGENTS.md 文件——无专门的 memory write API。 ^[deepagents/middleware/memory.py:159-354, 230-236, 262-263, 88, 253-254, 97-155]
**权衡**：设计最简洁——AGENTS.md 规范驱动 + 文件系统原生操作，无额外 API 层。自主更新机制依赖 Agent 遵循提示词指南（而非程序化强制执行），灵活性高但一致性取决于 Agent 对指南的遵循程度。懒加载 + PrivateStateAttr 对 checkpoint 和上下文保护友好。但无 consolidation 机制、无外部 provider 支持、无并发保护——与 nanobot 相似，纯本地文件方案。记忆更新使用通用 `edit_file` 工具，无专门的写入验证或内容安全扫描。

## 对比
| 框架 | 存储后端多样性 | 缓存一致性 | 自主演化能力 |
|------|------|------|------|
| nanobot | 纯本地文件，无外部 provider | 无冻结快照，每次写入后重读 | 最深——Dream cron 自主编辑 + git commit |
| hermes-agent | 最丰富——8 种外部 backend + 内置文件 | 冻结快照模式，显式 prompt cache 优化 | 弱——无压缩或整理机制 |
| openclaw | 嵌入式工具域，无独立 entity | 不适用 | 几乎为零——append-only write |
| deepagents | 纯本地文件（AGENTS.md），无外部 provider | 懒加载 + PrivateStateAttr；无冻结快照 | 中——Agent 遵循指南自主用 edit_file 更新，无程序化限制 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 deepagents（AGENTS.md 规范驱动 + Agent 自主 edit_file 更新）
