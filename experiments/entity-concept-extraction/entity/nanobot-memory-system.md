# Memory System（nanobot）

## 是什么 / 边界
nanobot 的三层记忆架构——MemoryStore（纯文件 I/O）+ Consolidator（异步压缩）+ Dream（两阶段记忆处理）。无嵌入式数据库、无向量检索、无 embedding。

**边界**：Memory System 负责长期记忆的存储、压缩和处理。不做实时上下文管理（那是 AgentRunner 的职责）、不做会话持久化（SessionManager）。

## 关键实现
- **MemoryStore**：纯文件 I/O——读/写 `MEMORY.md`、`history.jsonl`，通过 `GitStore` 版本控制 `SOUL.md`/`USER.md`/`MEMORY.md`
- **Consolidator**：独立 `asyncio.create_task()` 运行，使用独立的 LLM provider 实例（不共享 provider 状态）以避免阻塞主 agent。将历史消息压缩为按会话存储的文件级摘要（`agent/memory/prompt/`）。压缩失败不影响正在进行的对话，结果在下一轮 context 组装时生效
- **Dream**：两阶段记忆处理器——Phase 1 用纯 LLM 分析历史提取 insight；Phase 2 用只读文件/编辑文件的 AgentRunner 执行针对性写入
- **GitStore 版本控制**：SOUL.md、USER.md、MEMORY.md 的变更通过 git 追踪

## 设计选择记录
- **维度**：Architecture
- **选择**：Consolidator 使用独立 LLM provider 实例，在 `asyncio.create_task()` 中异步运行，压缩失败不阻塞主循环
- **替代方案**：同步压缩（压缩期间主 agent 不可用），或共享 provider 实例复用连接池
- **为什么有这个选择**：避免记忆压缩成为主 agent 的可用性瓶颈。独立 provider 实例保证压缩任务和对话任务的 API 调用互不干扰。代价是额外的 provider 实例开销，但 nanobot 的单进程模型下这个开销可忽略
