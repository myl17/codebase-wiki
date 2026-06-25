# MemoryManager + MemoryProvider — 记忆系统（Hermes Agent）

## 是什么 / 边界

MemoryManager 是记忆提供者的编排器，管理内置记忆存储（BuiltinMemoryProvider，始终启用）和最多一个外部记忆插件（Honcho/Mem0/Supermemory 等 7 种）。它在每次 API 调用前预取相关记忆并注入 system prompt，在每轮对话后同步新事实到存储。

它的边界：只做记忆的存储、检索和注入，不做技能管理（skill_manage 工具和 prompt_builder 负责），不做会话历史搜索（session_search 工具负责）。外部 provider 是加性的（additive），不会禁用内置存储。

## 关键实现

- 编排器：`agent/memory_manager.py`
- Provider 抽象基类：`agent/memory_provider.py:42-232`，定义完整生命周期接口
- 后台预取：`queue_prefetch()`（`agent/memory_provider.py:106-112`），当前 turn 完成后触发，下一轮调用 `prefetch()` 返回缓存结果
- 已捆绑 7 种 provider：`plugins/memory/{honcho, mem0, supermemory, hindsight, holographic, byterover, retaindb}`
- 激活方式：`config.yaml` 中 `memory.provider: "honcho"`
- 约束：最多 1 个外部 provider，BuiltinMemoryProvider 不可移除

MemoryProvider ABC 关键方法：
- `prefetch(query)` — 每次 API 调用前回溯相关记忆
- `sync_turn(user, asst)` — 每轮后持久化
- `system_prompt_block()` — 静态 prompt 注入
- `on_pre_compress(messages)` — 上下文压缩前提取重要信息（防压缩丢失）
- `on_delegation(task, result)` — 子 agent 完成时观察

## 设计选择记录

- **维度**：Architecture
- **选择**：内置记忆（BuiltinMemoryProvider）始终启用且不可移除，外部 provider 是加性扩展
- **替代方案**：外部 provider 完全替换内置记忆，用户只需选一个记忆后端
- **为什么有这个选择**：内置记忆保证基础功能始终可用，不依赖外部服务配置；外部 provider 提供增强（如向量搜索），但不能造成基础功能空白

---

- **维度**：Performance Tradeoffs
- **选择**：记忆预取在后台异步执行（queue_prefetch），下一轮使用上一轮完成后的缓存结果
- **替代方案**：每轮 API 调用前同步阻塞等待记忆预取完成
- **为什么有这个选择**：记忆检索（尤其是外部 provider）可能有网络延迟，异步预取不阻塞 LLM API 调用的关键路径；代价是记忆可能落后一轮（上一轮新写入在当前轮不可见）

---

- **维度**：Extension Points
- **选择**：MemoryProvider ABC 暴露 15+ 生命周期回调（on_pre_compress / on_delegation / on_memory_write 等）
- **替代方案**：只提供 prefetch / sync_turn 两个核心方法，不支持生命周期 hooks
- **为什么有这个选择**：外部记忆系统需要观察更多时机才能准确存储，如 on_pre_compress 在压缩前提取重要信息防丢失，on_delegation 观察子 agent 的输出；只提供核心方法会让外部 provider 无法感知关键状态变化
