# Hermes-Agent Performance Tradeoffs 维度知识

> 来源：/Users/yuanlimiao/Work/agent_harness/hermes-agent/ 源码
> 提取日期：2026-06-14
> 方法：逐个子系统深读源码，识别设计权衡

---

## 1. AIAgent — 中央编排器

### 1.1 并行工具执行：读安全 + 路径隔离并发

- **优化目标**：减少多工具调用轮次的端到端延迟
- **手段**：当模型在一次回复中发出多个工具调用时，对只读工具和路径不相交的文件操作进行并发执行（`ThreadPoolExecutor`，最多 8 个工作线程）
- **牺牲**：
  - 需要路径碰撞检测逻辑（`_paths_overlap`、`_extract_parallel_scope_path`），增加复杂度
  - 交互类工具（`clarify`）永远不能并发，要求维护 `_NEVER_PARALLEL_TOOLS` 黑名单
  - 文件工具（`read_file`/`write_file`/`patch`）仅在目标路径不重叠时才允许并发，需要额外解析和比对
- **理由**：大部分多工具调用是独立的只读操作（web_search + web_extract，read_file x3），并发可以显著减少等待时间；安全验证的 CPU 开销可忽略
- **源码证据**：`run_agent.py:216-308`（`_NEVER_PARALLEL_TOOLS`、`_PARALLEL_SAFE_TOOLS`、`_PATH_SCOPED_TOOLS`、`_should_parallelize_tool_batch`）^[run_agent.py:216-308]

### 1.2 上下文压缩：有损 LLM 摘要 vs 保留完整历史

- **优化目标**：控制上下文窗口增长，防止超出模型的 token 限制
- **手段**：使用辅助（便宜/快速）LLM 对对话中间轮次进行结构化摘要，丢弃原始消息，仅保留摘要文本；默认在 50% 上下文窗口时触发
- **牺牲**：
  - 信息损失：工具调用参数和输出的细节被压缩为 1 行摘要
  - 额外的 LLM 调用成本：摘要本身消耗 token（预算为压缩内容的 20%，上限为上下文长度的 5%）
  - 摘要失败时有降级策略（丢弃中间轮次但不注入摘要），导致上下文彻底丢失
- **理由**：一个被压缩但仍能继续的对话，优于一个因超出 token 限制而崩溃的对话。辅助模型的成本远低于重复发送完整上下文的成本
- **源码证据**：`agent/context_compressor.py:185-194`（算法描述），`agent/context_compressor.py:48-58`（token 预算常量 `_SUMMARY_RATIO=0.20`、`_SUMMARY_TOKENS_CEILING=12_000`），`agent/context_compressor.py:927-1091`（`compress()` 主入口）^[agent/context_compressor.py:185-1091]

### 1.3 工具结果裁剪：廉价预通行（无 LLM 调用）优先

- **优化目标**：在 LLM 摘要之前尽可能多地回收上下文空间，不消耗额外 API 成本
- **手段**：压缩前先执行 3 通行纯本地处理：① 去重相同的工具结果（MD5 哈希）② 将旧工具结果替换为 1 行摘要 ③ 截断 assistant 消息中的大型 tool_call 参数
- **牺牲**：去重和摘要使用基于字符串的启发式方法，可能丢失细微差异；MD5 哈希碰撞理论风险（实际可忽略）
- **理由**：本地 CPU 处理几乎免费，能在 LLM 摘要前回收大量 token，降低摘要调用的成本和延迟
- **源码证据**：`agent/context_compressor.py:333-465`（`_prune_old_tool_results` 方法，含去重通行、替换通行、截断通行）^[agent/context_compressor.py:333-465]

### 1.4 迭代预算：静默耗尽，无渐进式警告

- **优化目标**：防止模型因预算压力而提前放弃复杂任务
- **手段**：仅在迭代预算真正耗尽时注入一条消息并允许最后一次 API 调用；不发送渐进式的"还剩 X 轮"警告
- **牺牲**：用户和模型没有任何提前警告信号——任务可能突然停止且无中间通知
- **理由**：渐进式压力警告导致模型在复杂任务上提前"放弃"（#7915），产出不完整的解决方案。耗尽时的单次通知更可靠
- **源码证据**：`run_agent.py:815-821`（注释明确说明："No intermediate pressure warnings — they caused models to 'give up' prematurely on complex tasks (#7915)"）^[run_agent.py:815-821]

### 1.5 代理实例缓存：保持 Anthropic 前缀缓存有效

- **优化目标**：跨消息保持 Anthropic 提示前缀缓存，降低 API 成本 ~75%（在支持缓存的提供商上）
- **手段**：GatewayRunner 按 session_key 缓存 AIAgent 实例，复用 system prompt 和上下文；system prompt 仅在首次构建，压缩后才重建
- **牺牲**：
  - 内存消耗：长期运行的网关会持有多个代理实例（每个活跃 session 一个）
  - 状态管理复杂度：需要缓存失效、逐出和 signature 检查逻辑
  - 旧代理状态可能过期，需要跟踪何时重建
- **理由**：每消息创建新代理会重建 system prompt（包括 memory），破坏 Anthropic 前缀缓存，成本飙升 ~10x
- **源码证据**：`gateway/run.py:604-611`（`_agent_cache` 注释："Without this, a new AIAgent is created per message, rebuilding the system prompt (including memory) every turn — breaking prefix cache and costing ~10x more"），`run_agent.py:8287-8313`（system prompt 缓存策略）^[gateway/run.py:604-611][run_agent.py:8287-8313]

### 1.6 智能模型路由：保守的简单/复杂消息分类

- **优化目标**：对简单查询使用便宜模型，保留强大模型用于复杂任务，降低 API 成本
- **手段**：基于关键词黑名单（`_COMPLEX_KEYWORDS`：debug、implement、refactor 等）、长度（<160 字符、<28 词）、格式检测（代码块、URL）判断消息复杂度
- **牺牲**：
  - 保守策略：任何存疑的消息都走主模型，意味着部分简单消息仍被路由到昂贵模型
  - 关键词黑名单不能覆盖所有复杂场景
  - 仅按启发式分类，不进行语义理解
- **理由**：错误的降级（复杂任务发到便宜模型导致失败重试）成本远高于漏掉的优化机会。保守策略确保安全
- **源码证据**：`agent/smart_model_routing.py:11-102`（`_COMPLEX_KEYWORDS` 集合和 `choose_cheap_model_route` 函数，包含多项保守判断）^[agent/smart_model_routing.py:11-102]

---

## 2. ToolRegistry — 工具注册中心

### 2.1 读取快照模式：不一致性换取吞吐

- **优化目标**：支持高并发读取（多线程 MCP 刷新 + 多 session 查询），不阻塞工具模式查询
- **手段**：使用 `threading.RLock()` 保护写操作，但读取路径通过 `_snapshot_entries()` 返回工具条目的稳定副本——在锁内快速复制列表，锁外进行迭代和过滤
- **牺牲**：读取者可能看到略微过时的快照（如果在快照后注册了新工具）；这被文档明确接受
- **理由**：工具注册是低频操作（启动时 + MCP 刷新），而工具查询是高频操作（每个 API 调用前）。短暂的快照不一致性在功能上是无害的（最坏情况是一次调用错过新工具，下一次调用仍会包含）
- **源码证据**：`tools/registry.py:100-115`（`ToolRegistry.__init__` 注释："MCP dynamic refresh can mutate the registry while other threads are reading tool metadata, so keep mutations serialized and readers on stable snapshots"），`tools/registry.py:117-123`（`_snapshot_entries()` 和 `_snapshot_state()` 方法）^[tools/registry.py:100-123]

### 2.2 注册冲突检测：防止静默覆盖

- **优化目标**：防止插件/MCP 无意中覆盖内置工具（安全优先于便利）
- **手段**：同名工具注册时检测 `existing.toolset != toolset`，仅允许 MCP 到 MCP 的覆盖（服务器刷新），拒绝内置覆盖
- **牺牲**：有意的覆盖需要先注销再注册，增加了操作步骤；MCP 工具名冲突时仅记录警告
- **理由**：静默的覆盖可能将关键工具（terminal、write_file）替换为恶意或破损的版本，这是安全风险，值得接受更高的操作摩擦
- **源码证据**：`tools/registry.py:190-228`（`register()` 方法中的冲突检测逻辑，包含 `both_mcp` 允许和 `REJECTED` 拒绝分支）^[tools/registry.py:190-228]

---

## 3. Toolset — 工具集组合器

### 3.1 静态字典 + 延迟解析：编译时组合，零运行时开销

- **优化目标**：工具集解析速度——每个 API 调用前都会查询
- **手段**：工具集定义为模块级 `TOOLSETS` 字典，递归解析仅在需要时执行（`resolve_toolset`），结果缓存在调用方的 set 中
- **牺牲**：不支持条件性包含（所有工具集定义在代码中，无法按环境动态切换工具集内容）
- **理由**：工具集查询是热路径。静态定义确保 O(n) 解析速度，无需数据库或文件 I/O
- **源码证据**：`toolsets.py:68-397`（模块级 `TOOLSETS` 字典），`toolsets.py:447-497`（`resolve_toolset` 递归解析含循环检测）^[toolsets.py:68-497]

### 3.2 钻石依赖自动去重：避免重复工具

- **优化目标**：工具集组合的语义正确性，同时保持解析效率
- **手段**：使用 `visited` set 追踪已解析的工具集，钻石依赖（A includes B and C, both include D）静默去重
- **牺牲**：真正的循环依赖也被静默跳过（返回空列表），不如报错提示开发者修复
- **理由**：工具重复会浪费上下文 token（每工具 schema ~500-2000 tokens）。静默处理钻石依赖是正确行为；循环依赖在实际使用中不会出现
- **源码证据**：`toolsets.py:474-478`（钻石/循环检测："Silently return [] — either this is a diamond (not a bug, tools already collected via another path) or a genuine cycle (safe to skip)"）^[toolsets.py:474-478]

---

## 4. GatewayRunner — 消息网关控制器

### 4.1 代理缓存 vs 新鲜实例：缓存一致性取舍

- **优化目标**：跨网关消息保持 Anthropic 提示前缀缓存
- **手段**：按 session_key 缓存 AIAgent 实例（`_agent_cache`），检查 config signature 以检测需要重建的配置变更
- **牺牲**：
  - 内存：每个活跃对话持有一个完整的 AIAgent 对象图
  - 状态过期风险：缓存的 agent 可能反映旧的 memory 状态或工具注册
- **理由**：前缀缓存带来的成本节省（~75% 输入 token 成本）远超缓存维护的复杂度
- **源码证据**：`gateway/run.py:604-611`（agent cache 声明和注释），`gateway/run.py:2062-2078`（缓存 agent 的 memory provider shutdown 和 cleanup）^[gateway/run.py:604-2078]

### 4.2 后台平台重连：部分可用优于全不可用

- **优化目标**：单个平台故障不拖垮整个网关
- **手段**：平台适配器启动失败时加入 `_failed_platforms` 队列，由 `_platform_reconnect_watcher` 后台重试，而非让网关整体退出
- **牺牲**：故障平台暂时不可用，用户可能在重连期间错过消息
- **理由**：20+ 平台中部分不可用，远优于所有 20+ 平台全部不可用。网关的架构价值在于并发服务多平台
- **源码证据**：`gateway/run.py:620-622`（`_failed_platforms` 字典），`gateway/run.py:2006`（`_platform_reconnect_watcher` 作为后台任务启动）^[gateway/run.py:620-622]

---

## 5. Platform Adapter — 平台适配器抽象

### 5.1 消息截断：UTF-16 感知的二进制搜索

- **优化目标**：符合平台特定的消息长度限制（Telegram 4096 UTF-16 code units），不丢失信息
- **手段**：使用 UTF-16 code unit 计数（而非 Python codepoint 计数）配合二分搜索找到最长的安全前缀，避免切分代理对（emoji 等）
- **牺牲**：二分搜索需要 O(log n) 次 UTF-16 编码调用，比简单的 `s[:4096]` 慢
- **理由**：不正确截断代理对会导致无效的 UTF-16 序列和消息发送失败。O(log n) 的代价在消息长度（通常 <10000 字符）范围内可忽略
- **源码证据**：`gateway/platforms/base.py:24-55`（`utf16_len` 和 `_prefix_within_utf16_limit` 函数，含代理对处理注释）^[gateway/platforms/base.py:24-55]

---

## 6. SessionDB — 会话持久化存储

### 6.1 WAL 模式 + 应用级抖动重试：打破 SQLite 的 convoy 模式

- **优化目标**：多进程（网关 + CLI + worktree agent）共享 state.db 时的高并发写入
- **手段**：
  - WAL 模式：并发读者 + 单一写者
  - `BEGIN IMMEDIATE`：写锁在事务开始时获取（而非提交时），使锁竞争立即可见
  - 短 SQLite 超时（1s）+ 应用级随机抖动重试（20-150ms，最多 15 次）：替代 SQLite 内置的确定性退避（会导致 convoy 效应）
- **牺牲**：
  - 复杂度：需要应用层重试循环 + 随机抖动生成
  - WAL 文件需要定期 checkpoint（每 50 次写入执行 PASSIVE checkpoint）
- **理由**：SQLite 的内置 busy handler 使用确定性退避，在 3+ 并发写入者时产生 convoy 效应（所有写入者在同一时间唤醒、竞争、再全部睡眠）。随机抖动自然地错开写入者，消除 convoy
- **源码证据**：`hermes_state.py:123-156`（注释："SQLite's built-in busy handler uses a deterministic sleep schedule that causes convoy effects under high concurrency" 和 `_WRITE_MAX_RETRIES=15`、`_WRITE_RETRY_MIN_S=0.020`），`hermes_state.py:164-214`（`_execute_write` 含 `BEGIN IMMEDIATE` + 随机抖动重试）^[hermes_state.py:123-214]

### 6.2 FTS5 全文搜索：触发器维护 vs 搜索速度

- **优化目标**：跨所有会话消息的毫秒级全文搜索
- **手段**：FTS5 虚拟表（`messages_fts`）通过 INSERT/UPDATE/DELETE 触发器与 `messages` 表保持同步；content 同步模式使 FTS 表不单独存储内容
- **牺牲**：每次消息写入触发额外的 FTS 索引更新，增加写延迟；触发器维护增加 schema 复杂度
- **理由**：session_search 工具需要在数万条消息中实现亚秒级搜索。FTS5 的写入惩罚（~10-20%）远小于无索引全表扫描的读取惩罚（~100x）
- **源码证据**：`hermes_state.py:93-112`（`FTS_SQL` 含 FTS5 虚拟表和三个触发器的创建语句）^[hermes_state.py:93-112]

---

## 7. MemoryProvider — 可插拔记忆后端

### 7.1 单外部提供者限制：防膨胀 vs 多后端能力

- **优化目标**：防止工具 schema 膨胀和冲突记忆后端
- **手段**：`MemoryManager` 强制仅允许一个外部（非内置）memory provider；第二个注册尝试被拒绝并记录警告
- **牺牲**：无法同时使用多个外部记忆后端（如同时 Honcho + Mem0）
- **理由**：每个外部 provider 可以向模型暴露工具 schema。多个 provider 的工具 schema 累积会占用大量上下文 token，且可能产生冲突（两个后端同时写入相同内容的场景）。单 provider 保证 schema 简洁且行为可预测
- **源码证据**：`agent/memory_manager.py:83-119`（`MemoryManager.add_provider` 含 `_has_external` 检查和拒绝逻辑），`agent/memory_provider.py:7-10`（文档："Only one external provider runs at a time to prevent tool schema bloat and conflicting memory backends"）^[agent/memory_manager.py:83-119][agent/memory_provider.py:7-10]

### 7.2 异步写入：非阻塞持久化

- **优化目标**：不阻塞对话轮次的响应时间
- **手段**：`sync_turn()` 应非阻塞——调用方期望 provider 在内部排队后台处理
- **牺牲**：系统崩溃可能丢失尚未持久化的最近 1-2 轮记忆
- **理由**：记忆持久化的延迟远高于对话响应时间约束（网络 RTT 50-500ms）；排队写入消除这 50-500ms 的用户感知延迟
- **源码证据**：`agent/memory_provider.py:114-119`（`sync_turn` 文档："Should be non-blocking — queue for background processing if the backend has latency"）^[agent/memory_provider.py:114-119]

---

## 8. ContextCompressor — 上下文压缩器

### 8.1 辅助模型摘要：速度/成本 vs 保真度

- **优化目标**：最小化压缩的 token 成本
- **手段**：使用可配置的辅助/摘要模型（`summary_model_override`，通常比主模型更便宜/更快）进行压缩；摘要预算为压缩内容的 20%（上限为上下文长度的 5%）
- **牺牲**：
  - 辅助模型产生的摘要质量低于主模型
  - 摘要模型不可用时需要回退到主模型（自动 fallback）或完全降级
- **理由**：压缩是一个元任务（总结已完成的工作），不需要推理能力。便宜模型在摘要任务上的性能与昂贵模型相当，但成本低 10-50x
- **源码证据**：`agent/context_compressor.py:50-58`（`_SUMMARY_RATIO=0.20`、`_SUMMARY_TOKENS_CEILING=12_000`），`agent/context_compressor.py:671-733`（`_generate_summary` 使用 `call_llm(task="compression")`，含摘要模型回退逻辑）^[agent/context_compressor.py:50-733]

### 8.2 反抖动保护：防止无限压缩循环

- **优化目标**：防止反复无效压缩（每次仅释放 1-2 条消息的死循环）
- **手段**：跟踪 `_last_compression_savings_pct`；连续 2 次压缩节省 <10% 时，跳过后续压缩，建议用户使用 `/new` 或 `/compress <topic>`
- **牺牲**：上下文持续增长，可能最终耗尽 token 限制，触发 API 错误
- **理由**：反复无效压缩消耗 API 成本（每次 LLM 摘要调用）但不释放有意义的空间。用户干预（/new）是更好的恢复路径
- **源码证据**：`agent/context_compressor.py:307-327`（`should_compress()` 含 `_ineffective_compression_count >= 2` 检查），`agent/context_compressor.py:1074-1079`（保存百分比的逻辑）^[agent/context_compressor.py:307-327][agent/context_compressor.py:1074-1079]

---

## 9. IterationBudget — 迭代预算

### 9.1 线程安全计数器：锁保护 vs 无锁原子操作

- **优化目标**：跨主代理和子代理的安全迭代预算共享
- **手段**：使用 `threading.Lock()` 保护 `_used` 计数器；`consume()` 和 `refund()` 在锁内原子化操作
- **牺牲**：每次预算操作获取锁的微秒级开销；在高竞争场景下（多个子代理同时 consuming）可能产生锁竞争
- **理由**：迭代预算操作频率低（每 LLM 调用一次，每秒最多 1-2 次），锁开销可忽略。Python 的 GIL 不保证 `+= 1` 的原子性，因此线程安全需要显式锁
- **源码证据**：`run_agent.py:170-211`（`IterationBudget` 类含 `_lock = threading.Lock()`，`consume()`、`refund()` 和 `remaining` 属性均在锁内操作）^[run_agent.py:170-211]

---

## 10. 插件系统 — PluginManager

### 10.1 三层发现：用户/项目/pip — 灵活性与安全性的权衡

- **优化目标**：最大化插件来源的灵活性，同时保护用户不受恶意插件影响
- **手段**：
  - 用户插件（`~/.hermes/plugins/`）：始终加载
  - 项目插件（`./.hermes/plugins/`）：需通过 `HERMES_ENABLE_PROJECT_PLUGINS` 环境变量显式 opt-in
  - Pip 插件（`hermes_agent.plugins` entry-point 组）：通过包管理器安装
- **牺牲**：项目插件默认不加载，增加了配置步骤；三个不同来源增加了发现逻辑的复杂度
- **理由**：项目插件是最大的安全风险（`git clone` 后自动执行代码）。opt-in 模型防止供应链攻击，同时保持用户和 pip 插件的便利性
- **源码证据**：`hermes_cli/plugins.py:1-14`（顶部文档："Project plugins — ./plugins/ (opt-in via HERMES_ENABLE_PROJECT_PLUGINS)"）^[hermes_cli/plugins.py:1-14]

---

## 11. 工具注册 — 自注册模式

### 11.1 AST 自发现 vs 显式注册表：零样板 vs 隐式依赖

- **优化目标**：工具开发者零注册样板——在模块顶层调用 `registry.register()` 即可
- **手段**：`discover_builtin_tools()` 使用 AST 解析（而非导入）扫描工具文件中的顶层 `registry.register(...)` 调用，确认后才导入模块
- **牺牲**：
  - AST 解析增加了代码复杂度（`_is_registry_register_call`、`_module_registers_tools`）
  - 工具文件的导入顺序和副作用变得隐式——看到 `importlib.import_module()` 的开发者可能不清楚背后发生了什么
- **理由**：手动维护工具列表容易出错（新增工具忘记注册）。AST 预扫描在不执行任何代码的情况下安全地发现工具，避免导入时的副作用
- **源码证据**：`tools/registry.py:28-73`（`_is_registry_register_call` AST 检查，`_module_registers_tools` 源码级扫描，`discover_builtin_tools` 导入编排）^[tools/registry.py:28-73]

---

## 12. MCP 集成 — stdio/HTTP transport

### 12.1 后台事件循环 + 守护线程：连接保活 vs 线程安全复杂度

- **优化目标**：跨多次工具调用的 MCP 服务器连接复用，避免每调用重复建立连接
- **手段**：专用后台事件循环（`_mcp_loop`）运行在守护线程上；每个 MCP 服务器作为长期存在的 asyncio Task 保持其 transport 上下文活跃；工具调用通过 `run_coroutine_threadsafe()` 调度到该循环
- **牺牲**：
  - 线程安全：`_servers` 和 `_mcp_loop` 被主线程和 MCP 线程同时访问，需要 `_lock` 保护所有变异
  - 关闭复杂性：每个服务器 Task 需要信号来退出其 `async with` 块，确保 anyio cancel-scope 清理在同一个 Task 中发生
- **理由**：stdio 连接建立需要启动子进程（npx/node），延迟 1-5 秒。复用连接使后续工具调用在 <100ms 内完成。线程安全开销由锁粒度最小化控制
- **源码证据**：`tools/mcp_tool.py:55-70`（架构文档："A dedicated background event loop (_mcp_loop) runs in a daemon thread. Each MCP server runs as a long-lived asyncio Task"），`tools/mcp_tool.py:65-69`（线程安全注释："All mutations are protected by _lock so the code is safe regardless of GIL presence"）^[tools/mcp_tool.py:55-70]

### 12.2 指数退避重连：可用性 vs 延迟

- **优化目标**：MCP 服务器短暂不可用后自动恢复
- **手段**：首次连接最多重试 3 次，已建立连接后的断连最多重试 5 次，指数退避（上限 60 秒）
- **牺牲**：退避期间工具不可用；在总故障时间（服务器完全宕机）的情况下，重试浪费资源
- **理由**：MCP 服务器是外部进程，可能因资源限制或网络抖动而暂时不可用。有上限的指数退避平衡了恢复速度和资源保护
- **源码证据**：`tools/mcp_tool.py:165-167`（`_MAX_RECONNECT_RETRIES=5`、`_MAX_INITIAL_CONNECT_RETRIES=3`、`_MAX_BACKOFF_SECONDS=60`）^[tools/mcp_tool.py:165-167]

---

## 13. 技能系统 — SKILL.md 渐进式披露

- **未发现显式设计权衡**：技能系统的主要设计是文件系统约定（SKILL.md 元数据 + 目录结构），没有在源码中表现出显著的性能权衡。技能的加载和发现是手工过程（用户创建文件），不涉及自动化的性能敏感操作。

---

## 14. 上下文引擎 — ContextEngine ABC

### 14.1 可插拔替换：抽象代价 vs 灵活性

- **优化目标**：允许第三方实现完全替换上下文管理策略（如 LCM 的 DAG 方法替代摘要方法）
- **手段**：`ContextEngine` ABC 定义了 `compress()`、`should_compress()`、`update_from_response()` 等核心接口；`ContextCompressor` 是默认的内置实现
- **牺牲**：
  - ABC 需要 `last_prompt_tokens`、`last_completion_tokens`、`threshold_tokens` 等属性——每个实现必须维护这些状态
  - `run_agent.py` 直接读取这些属性（而非通过 getter），破坏封装
- **理由**：不同引擎有不同的压缩策略（摘要 vs. DAG 构建 vs. 完全不同的方法）。ABC 开销（几个属性维护）远小于锁定单一策略的代价
- **源码证据**：`agent/context_engine.py:32-129`（`ContextEngine` ABC 定义，含 `@abstractmethod` 标记和属性文档）^[agent/context_engine.py:32-129]

---

## 15. 执行环境 — BaseEnvironment ABC

### 15.1 统一 spawn-per-call 模型：隔离性 vs 状态维护

- **优化目标**：跨 6 种后端（local、Docker、Singularity、Modal、Daytona、SSH）的统一命令执行接口
- **手段**：每次命令调用 spawn 新的 `bash -c` 进程；session snapshot（环境变量、函数、别名）在 init 时捕获并在每次命令前重新 source；CWD 通过 stdout 带内标记（远程）或临时文件（本地）持久化
- **牺牲**：
  - 每次命令调用都需要 fork/spawn 新进程，而非复用 shell（增加 ~50-200ms）
  - CWD 持久化通过 stdout 标记实现，增加了输出解析的复杂度
- **理由**：进程隔离防止命令之间的状态污染（`cd` 等副作用不会影响后续命令）。200ms 的 spawn 开销在秒级工具执行时间面前可接受
- **源码证据**：`tools/environments/base.py:1-7`（文档："Unified spawn-per-call model: every command spawns a fresh bash -c process. A session snapshot is captured once at init and re-sourced before each command"）^[tools/environments/base.py:1-7]

---

## 16. 网关事件钩子 — 8 种事件类型

### 16.1 同步文件系统发现：简单性 vs 启动延迟

- **优化目标**：在网关启动时加载所有钩子，确保事件处理无遗漏
- **手段**：`HookRegistry.discover_and_load()` 在启动时同步扫描 `~/.hermes/hooks/` 目录，解析每个 `HOOK.yaml` 并导入 `handler.py`
- **牺牲**：钩子数量多时会增加网关启动时间（每个钩子需要 YAML 解析 + Python 模块导入）；钩子目录必须在启动时存在
- **理由**：钩子是用户配置的扩展点，数量通常很少（<10）。同步加载确保网关在接受消息前已完全就绪，避免首次事件触发时的冷启动延迟
- **源码证据**：`gateway/hooks.py:69-100`（`discover_and_load` 方法依次扫描目录、加载 YAML 和 handler.py）^[gateway/hooks.py:69-100]

---

## 权衡汇总表

| 子系统 | 优化了什么 | 牺牲了什么 | 关键文件 |
|--------|-----------|-----------|---------|
| AIAgent — 并行工具执行 | 多工具调用的端到端延迟 | 路径碰撞检测复杂度，交互工具黑名单维护 | `run_agent.py:216-308` |
| AIAgent — 上下文压缩 | 上下文窗口增长控制 | 信息损失，额外 LLM 调用成本 | `agent/context_compressor.py:185-1091` |
| AIAgent — 工具结果裁剪 | 零 LLM 成本的上下文回收 | 启发式方法的细节丢失 | `agent/context_compressor.py:333-465` |
| AIAgent — 迭代预算 | 防止模型提前放弃 | 无提前警告信号 | `run_agent.py:815-821` |
| AIAgent — 代理缓存 | API 成本 ~75%，前缀缓存保持 | 内存消耗，状态管理复杂度 | `gateway/run.py:604-611` `run_agent.py:8287-8313` |
| AIAgent — 智能模型路由 | 简单查询的 API 成本 | 分类精度（保守启发式） | `agent/smart_model_routing.py:11-102` |
| ToolRegistry — 快照模式 | 高并发读取吞吐 | 短暂的快照不一致性 | `tools/registry.py:100-123` |
| ToolRegistry — 冲突检测 | 防止工具被静默覆盖 | 有意覆盖的操作摩擦 | `tools/registry.py:190-228` |
| Toolset — 静态组合 | 运行时解析速度 | 无动态条件性包含 | `toolsets.py:68-497` |
| Toolset — 钻石去重 | 语义正确，token 节省 | 真实循环被静默跳过 | `toolsets.py:474-478` |
| GatewayRunner — 代理缓存 | 跨消息前缀缓存 | 内存，状态过期风险 | `gateway/run.py:604-2078` |
| GatewayRunner — 后台重连 | 多平台可用性 | 单平台暂时不可用 | `gateway/run.py:620-622` |
| Platform Adapter — 消息截断 | 符合平台限制，字符完整性 | O(log n) 二分搜索开销 | `gateway/platforms/base.py:24-55` |
| SessionDB — WAL + 抖动重试 | 多进程并发写入 | 应用层重试复杂度，WAL 维护 | `hermes_state.py:123-214` |
| SessionDB — FTS5 索引 | 亚秒级全文搜索 | 写入延迟增加 ~10-20% | `hermes_state.py:93-112` |
| MemoryProvider — 单外部限制 | 防 schema 膨胀 | 无法同时使用多后端 | `agent/memory_manager.py:83-119` |
| MemoryProvider — 异步写入 | 对话响应时间 | 崩溃数据丢失风险 | `agent/memory_provider.py:114-119` |
| ContextCompressor — 辅助模型 | 压缩 token 成本 | 摘要质量低于主模型 | `agent/context_compressor.py:50-733` |
| ContextCompressor — 反抖动 | 防止无限压缩循环 | 上下文持续增长风险 | `agent/context_compressor.py:307-327` |
| IterationBudget — 锁保护 | 线程安全 | 微秒级锁开销 | `run_agent.py:170-211` |
| 插件系统 — 三层发现 | 灵活性 + 安全性 | opt-in 配置步骤 | `hermes_cli/plugins.py:1-14` |
| 工具注册 — AST 自发现 | 零注册样板 | AST 解析复杂度 | `tools/registry.py:28-73` |
| MCP 集成 — 后台循环 | 连接复用（1-5s -> <100ms） | 线程安全复杂度 | `tools/mcp_tool.py:55-70` |
| MCP 集成 — 指数退避 | 自动恢复 | 重试期间不可用 | `tools/mcp_tool.py:165-167` |
| ContextEngine — ABC | 策略可替换 | 封装破坏（属性直接访问） | `agent/context_engine.py:32-129` |
| 执行环境 — spawn-per-call | 隔离性 | 每命令 fork 开销 ~50-200ms | `tools/environments/base.py:1-7` |
| 网关钩子 — 同步发现 | 简单性，无遗漏 | 启动延迟（钩子数量多时） | `gateway/hooks.py:69-100` |
