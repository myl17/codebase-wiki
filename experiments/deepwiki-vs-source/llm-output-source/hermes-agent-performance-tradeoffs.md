# Hermes Agent Performance Tradeoffs

## 1. Anthropic Prompt Caching -- 输入 Token 成本降低约 75%

**优化目标**：降低多轮对话中的输入 token 成本（运行时成本）。

**手段**：对 Claude 模型自动启用 Anthropic prompt caching 的 "system_and_3" 策略。在 system prompt 和最近 3 条非系统消息上注入 4 个 `cache_control` 断点（Anthropic API 最大数量），让前缀被缓存复用。默认使用 5 分钟 ephemeral TTL。

**源码证据**：

- 自动检测：基于 OpenRouter + Claude 模型或原生 Anthropic API 判断启用条件 ^[run_agent.py:806-812]
- 默认 5 分钟 TTL（注释标注 "1.25x write cost"）^[run_agent.py:813]
- `apply_anthropic_cache_control()` 纯函数，注入 4 个断点（system + 最后 3 条非 system 消息），deep copy 避免篡改原始消息 ^[agent/prompt_caching.py:41-72]
- `_apply_cache_marker()` 处理多种内容格式：tool 角色、空内容、字符串内容、列表内容 ^[agent/prompt_caching.py:15-38]
- 在每次 API 调用前注入，标记为 "ephemeral" 类型 ^[run_agent.py:8627-8632]
- 缓存读/写 token 计数在 session 统计中跟踪 ^[run_agent.py:1556-1557]
- 启动日志显示："Prompt caching: ENABLED (source, TTL)" ^[run_agent.py:1137-1139]

**牺牲**：缓存写入成本是标准输入的 1.25x。ephemeral TTL 意味着超过 5 分钟未命中的缓存将失效。cache_control 断点计数限制为 4 个，超出部分的上下文无法被缓存。

---

## 2. Context Compression -- 上下文自动压缩至 50% 阈值

**优化目标**：在长对话中避免触及模型上下文窗口上限，通过牺牲历史细节换取会话连续性（运行时/内存）。

**手段**：`ContextCompressor` 使用廉价辅助模型对中间轮次进行摘要压缩。当 `prompt_tokens >= threshold_tokens`（默认上下文的 50%）时触发。压缩算法分为五步：修剪旧工具输出、保护头部消息、按 token 预算保护尾部消息、用结构化 LLM 提示总结中间轮次、迭代更新先前摘要。

**源码证据**：

- `ContextCompressor` 继承 `ContextEngine`，阈值默认 50%，压缩目标 20%（tail_token_budget） ^[agent/context_compressor.py:185-301]
- 阈值底线为 `MINIMUM_CONTEXT_LENGTH = 64_000` tokens，防止大上下文模型过早压缩 ^[agent/context_compressor.py:262-268]
- 压缩前先执行 Pre-compression memory flush（在上下文被丢弃前保存记忆） ^[run_agent.py:7084-7085]
- 压缩后通知外部 memory provider ^[run_agent.py:7088-7092]
- 压缩触发 session split（SQLite 中创建新 session，旧 session 标记为 "compression"） ^[run_agent.py:7104-7136]
- 压缩后更新 token 估算并清除 file-read dedup 缓存 ^[run_agent.py:7147-7177]
- 压缩启动时用户看到：`n messages -> m messages` ^[run_agent.py:7180-7183]
- 支持 `focus_topic` 参数进行定向压缩 ^[run_agent.py:7066-7072]
- 支持插件化的 context engine（通过 `plugins/context_engine/` 或通用插件系统） ^[run_agent.py:1432-1468]

**牺牲**：压缩是损失性操作——中间历史细节被 LLM 摘要替代，摘要质量取决于辅助模型。重复压缩会导致精度下降（连续 2 次以上会发出警告）^[run_agent.py:7138-7145]。session split 导致日志切换，可能丢失连续性信息。

---

## 3. Anti-Thrashing -- 压缩防抖/反震荡

**优化目标**：防止无效压缩循环——连续压缩但每次只节省极少 token 的死亡螺旋。

**手段**：跟踪最近两次压缩的节省百分比。如果每次节省 <10%，停止自动压缩以避免无限循环。

**源码证据**：

- `_ineffective_compression_count` 计数器跟踪连续低效压缩 ^[agent/context_compressor.py:207,298-299]
- `should_compress()` 在 `_ineffective_compression_count >= 2` 时跳过压缩 ^[agent/context_compressor.py:307-319]
- 后压缩 token 评估：如果压缩后 token 仍然 >= 阈值的 85%，保留压力警告状态以避免重复警告 ^[run_agent.py:7156-7168]
- RELEASE v0.7.0 明确记录了压缩死亡螺旋的修复（API 断开时停止循环） ^[RELEASE_v0.7.0.md:57,210]

**牺牲**：反震荡可能在少数合法场景中阻止了确实需要的压缩。需要依赖用户手动 `/compress` 或 `/new` 来恢复。

---

## 4. 确定性 call_id 落回策略

**优化目标**：保持 prompt caching 的跨请求一致性，提高缓存命中率。

**手段**：使用确定性 UUID 替代随机 UUID 作为 call_id 的 fallback 值，确保相同上下文产生相同的缓存键。

**源码证据**：

- v0.7.0 release 记录了确定性 call_id fallback 替代随机 UUID 的变更 ^[RELEASE_v0.7.0.md:62]

**牺牲**：确定性 ID 可能在极端并发场景下产生冲突（概率极低）。牺牲了随机 UUID 的绝对唯一性保证。

---

## 5. External Memory Prefetch -- 每轮一次而非每次工具调用

**优化目标**：减少外部 memory provider 的延迟和 API 调用成本。

**手段**：将 memory prefetch 从每次工具调用改为每轮开始时执行一次。如果每个工具调用都触发 memory provider API 调用（10 次工具调用 = 10x 延迟 + 成本）。

**源码证据**：

- 注释明确说明："Must happen BEFORE prefetch_all() so providers know which turn it is" ^[run_agent.py:8470]
- `prefetch_all()` 调用放在工具循环外部，避免每次工具调用时重复 ^[run_agent.py:8479-8484]
- prefetch 结果通过 `_ext_prefetch_cache` 缓存，在 API 消息构建时注入 ^[run_agent.py:8562-8569]
- 每轮结束时通过 `queue_prefetch_all()` 为下一轮预热 ^[run_agent.py:11233-11239]

**牺牲**：如果对话中用户消息在多轮工具调用之间剧烈变化主题，prefetch 的 memory 上下文可能不够精准。牺牲了实时性换取延迟和成本节省。

---

## 6. Lazy Imports for Update Safety

**优化目标**：防止 `hermes update` 过程中因模块引用新函数导致的 ImportError 链式失败。

**手段**：将关键模块的导入延迟到实际使用时，避免在更新期间因陈旧 .pyc 字节码导致的崩溃。

**源码证据**：

- v0.6.0 release 记录了 lazy `display_hermes_home` 导入防止更新时的 ImportError ^[RELEASE_v0.6.0.md:55,196]
- `hermes_logging.py` 中使用 lazy import 避免循环导入 ^[hermes_logging.py:214]
- OpenRouter 模型元数据缓存在后台线程预热："fetch_model_metadata() is cached for 1 hour; this avoids a blocking call" ^[run_agent.py:747-748]
- AsyncOpenAI client 在 compressor 中懒加载，绑定到当前事件循环 ^[trajectory_compressor.py:394-408]

**牺牲**：延迟导入意味着错误在运行时才暴露，而非启动时早期发现。后台线程预热增加了启动期的并发复杂度。

---

## 7. Context Pressure Warnings -- 分层通知而非 LLM 注入

**优化目标**：避免 LLM 因提前获知迭代预算/上下文压力而"过早放弃"复杂任务。

**手段**：将上下文压力警告改为纯信息性通知（显示在 CLI 输出和 gateway 状态回调中），不再注入到 LLM 消息流中。分层触发：85% 和 95% 的压缩阈值各发一次。

**源码证据**：

- 注释明确记录："No intermediate pressure warnings -- they caused models to 'give up' prematurely on complex tasks (#7915)" ^[run_agent.py:819-821]
- 分层警告："Tiered: fires at 85% and again at 95% of compaction threshold" ^[run_agent.py:827]
- `_context_pressure_warned_at` 跟踪已发出的最高警告级别 ^[run_agent.py:828]
- `_emit_context_pressure` 计算 `compaction_progress`（0.0-1.0）并仅在超过已警告级别时发出 ^[run_agent.py:7940-7971]

**牺牲**：用户可能错过上下文即将溢出的警告（如果不在看 CLI 输出）。LLM 无法根据上下文压力自行调整行为（如减少冗余输出）。

---

## 8. Trajectory Compression -- 离线训练数据压缩

**优化目标**：将完整的 agent 交互轨迹压缩到目标 token 预算内，同时保留训练信号质量。

**手段**：后处理 `TrajectoryCompressor` 使用单独的摘要模型（默认 Google Gemini Flash）将轨迹中间轮次替换为单条摘要消息。保护头部轮次（system、human、first gpt、first tool）和尾部 N 轮（默认 4）。仅压缩需要的部分以达到目标（默认 15,250 tokens）。支持并行异步处理（默认 4 workers，50 并发请求）。

**源码证据**：

- `CompressionConfig` 定义 token 目标（15250）、摘要目标（750）、保护策略 ^[trajectory_compressor.py:57-99]
- 压缩算法仅移除中间轮次，保护头部和尾部信号 ^[trajectory_compressor.py:663-781]
- 异步版本使用 `asyncio.Semaphore` 控制并发（默认 50）^[trajectory_compressor.py:90]
- 支持 `skip_under_target` 跳过已达标轨迹 ^[trajectory_compressor.py:91]
- 摘要失败时有 fallback 静态摘要文本 ^[trajectory_compressor.py:599]
- 支持 jittered backoff 重试（最多 3 次）^[trajectory_compressor.py:567-598]
- 完整指标跟踪：`TrajectoryMetrics` 和 `AggregateMetrics` ^[trajectory_compressor.py:157-304]

**牺牲**：压缩后的轨迹丢失了中间轮次的细粒度信号。摘要质量完全取决于所选的摘要模型。并行处理增加了 API 调用成本和速率限制风险。

---

## 9. Tool Output Pruning -- 压缩前的廉价预处理

**优化目标**：在 LLM 摘要之前先通过规则修剪工具输出，减少摘要模型的输入 token 成本。

**手段**：压缩流程中的第一步是 `_summarize_tool_result()`——将大型工具输出替换为简短的单行描述（如 `[terminal] ran 'npm test' -> exit 0, 47 lines output`）。这是纯规则匹配，无 LLM 调用。

**源码证据**：

- 文档明确："Tool output pruning before LLM summarization (cheap pre-pass)" ^[agent/context_compressor.py:15]
- `_summarize_tool_result()` 支持 20+ 种工具类型的专用摘要模板（terminal, read_file, write_file, search_files, patch, browser, web_search, web_extract, delegate_task, execute_code 等） ^[agent/context_compressor.py:63-182]
- 修剪后的占位符：`_PRUNED_TOOL_PLACEHOLDER = "[Old tool output cleared to save context space]"` ^[agent/context_compressor.py:56]

**牺牲**：修剪后的信息比原始输出粗糙，可能丢失关键的细节数据。规则模板无法捕捉所有边界情况。对于不匹配任何模板的工具类型，使用泛型回退。

---

## 10. 消息规范化以提升 KV Cache 命中率

**优化目标**：提升本地推理服务器（llama.cpp、vLLM、Ollama）和云端提供的 KV cache 命中率。

**手段**：在发送 API 请求前对消息进行规范化：去除 `content` 字符串首尾空白、按排序键和紧凑分隔符序列化 tool-call JSON arguments（`json.dumps(separators=(",", ":"), sort_keys=True)`）。

**源码证据**：

- 注释说明："Ensures bit-perfect prefixes across turns, which enables KV cache reuse on local inference servers" ^[run_agent.py:8640-8646]
- 对 `api_messages`（API 副本）进行操作，不对原始 `messages` 进行修改 ^[run_agent.py:8646-8668]

**牺牲**：规范化在每次 API 调用前都执行一次，对于非常大的消息列表有 CPU 开销。排序 JSON keys 可能改变工具参数的语义排序（尽管 JSON 规范认为无序）。

---

## 性能权衡汇总

| 优化项 | 优化目标 | 手段 | 牺牲 | 关键文件 |
|--------|---------|------|------|---------|
| Prompt Caching | Token 成本 (-75%) | system_and_3 策略 + ephemeral TTL | 1.25x 写入成本、5min 过期 | `agent/prompt_caching.py:41-72` |
| Context Compression | 会话连续性 | 50% 阈值 + 辅助模型摘要 | 历史细节丢失、摘要质量不确定 | `agent/context_compressor.py:185-301` |
| Anti-Thrashing | 压缩稳定性 | <10% 节省则停止自动压缩 | 可能错过合法压缩需求 | `agent/context_compressor.py:307-319` |
| Deterministic call_id | Cache 命中率 | 确定性 UUID 替代随机 UUID | 极端并发场景冲突风险 | `RELEASE_v0.7.0.md:62` |
| Memory Prefetch | API 调用成本 | 每轮一次而非每次工具调用 | 主题切换时上下文不够精准 | `run_agent.py:8479-8484` |
| Lazy Imports | 更新稳定性 | 延迟导入至实际使用 | 运行时错误延迟暴露 | `hermes_logging.py:214` |
| Pressure Warnings | LLM 行为质量 | 信息性通知，不注入消息 | 用户可能错过警告 | `run_agent.py:819-828` |
| Trajectory Compression | 训练数据 Token 预算 | LLM 摘要 + 中间轮次替换 | 细粒度信号丢失 | `trajectory_compressor.py:663-781` |
| Tool Output Pruning | 摘要模型输入成本 | 规则模板替换 | 细节丢失、模板覆盖不全 | `agent/context_compressor.py:63-182` |
| Message Normalization | KV Cache 命中率 | 空白去重 + JSON 排序 | 每次调用 CPU 开销 | `run_agent.py:8640-8668` |
