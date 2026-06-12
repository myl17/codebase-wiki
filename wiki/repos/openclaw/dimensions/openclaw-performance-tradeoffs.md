---
repo: openclaw
dimension: performance-tradeoffs
dimensions_version: v1.0
generated: 2026-06-09
---

# OpenClaw — Performance Tradeoffs

OpenClaw 的性能优化集中在**启动时间**和**LLM token 成本**两个维度，牺牲的是内存占用（多个运行时缓存）和架构复杂度。

## 1. 启动时间优化

**Node.js Compile Cache**：启动时第一件事调用 `enableCompileCache()`（Node.js 22+ 内置 API），将 V8 字节码缓存到磁盘，第二次启动跳过 JS 解析。失败时静默降级（`try/catch` 吞掉错误），不阻塞启动。^[src/entry.ts:52-58]

**Respawn 策略**：`buildCliRespawnPlan` 在首次启动时判断是否需要以修改后的 `NODE_OPTIONS`（添加 `--disable-warning=ExperimentalWarning`）或 `NODE_EXTRA_CA_CERTS` 重新 spawn 进程。重启后设置 `OPENCLAW_NODE_OPTIONS_READY=1`，避免循环 respawn。代价是冷启动多一次 `spawn()`。^[src/entry.respawn.ts:24-80]

**Lazy Runtime Module**：`createLazyRuntimeModule` 用 Promise 缓存（`cached ??= importer().then(select)`）包装所有运行时模块的动态 import，确保每个模块只加载一次，且在真正需要时才加载。这是懒加载模式的典型应用。Plugin runtime 的 TTS、media-understanding、model-auth 等重型模块全部通过此机制延迟。^[src/shared/lazy-runtime.ts:1-44]

**Channel Entry 按需加载**：`defineBundledChannelEntry` 使用 `loadBundledEntryExportSync` 让 channel plugin 的实际代码只在该 channel 被使用时加载，未配置的 channel 代码不进入内存。^[src/plugin-sdk/channel-entry-contract.ts:31-60]

## 2. LLM Token 成本优化

**Prompt Cache Boundary**：在 system prompt 中插入 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记，将 prompt 切分为**稳定前缀**和**动态后缀**。稳定前缀（技能定义、人格等不变内容）打上 Anthropic `cache_control: { type: "ephemeral" }` 标记，在 API 层命中Prompt Caching，减少每轮输入 token 费用。动态后缀（记忆注入、实时上下文）在边界后插入，不影响缓存命中。^[src/agents/system-prompt-cache-boundary.ts:3-47]

**Anthropic Prompt Cache TTL**：根据 endpoint hostname 决定缓存保留时长——`api.anthropic.com` 和 `aiplatform.googleapis.com` 支持 `ttl: "1h"` 的长缓存；其他端点默认 short TTL。通过 `cacheRetention` 配置项或 `PI_CACHE_RETENTION` 环境变量控制。^[src/agents/anthropic-payload-policy.ts:37-65]

**Context 压缩**：上下文接近窗口上限时触发摘要压缩。关键参数：`BASE_CHUNK_RATIO = 0.4`、`MIN_CHUNK_RATIO = 0.15`、`SAFETY_MARGIN = 1.2`（20% 缓冲补偿 token 估算误差）。摘要指令优先保留活跃任务状态、批处理进度、最后一次用户请求——优先保证**可恢复性**而非压缩率。`tool_result.details` 在压缩前被 strip，防止冗长工具输出污染摘要。^[src/agents/compaction.ts:19-40]

**Bootstrap Files Cache**：用 `Map<sessionKey, files>` 缓存工作区 bootstrap 文件（CLAUDE.md 等），同一 session 内只读一次磁盘。session rollover 时主动清除，防止旧内容残留。^[src/agents/bootstrap-cache.ts:1-36]

**Context Window Guard**：设置硬限（`CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000`）和软警告线（`CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000`），在 modelsConfig、model 自报、agentContextTokens 之间按优先级选最保守值，防止因上下文不足导致截断失败。^[src/agents/context-window-guard.ts:4-81]

## 3. 消息处理吞吐优化

**Inbound Debounce**：消息入站时做防抖，合并短时间内连续到达的多条消息再交给 agent 处理，减少因"用户分多条发送一个问题"触发多次 LLM 调用。防抖窗口来自 channel plugin 的 `defaults.queue.debounceMs` 配置。^[src/channels/inbound-debounce-policy.ts:11-51]

**Command Poll 指数退避**：对长时间无输出的命令轮询实现指数退避：`5s → 10s → 30s → 60s`，有新输出时立即重置为 5s。牺牲最坏情况下的响应延迟，换取空轮询的 CPU 节省。^[src/agents/command-poll-backoff.ts:4-43]

## 关键权衡汇总

| 优化目标 | 手段 | 牺牲 |
|---|---|---|
| 冷启动速度 | Compile cache + lazy module + respawn | 首次启动额外 spawn，内存多个 Promise cache |
| LLM token 费用 | Prompt cache boundary + compaction | system prompt 复杂度上升，compaction 消耗额外 LLM 调用 |
| 消息处理吞吐 | Inbound debounce + poll backoff | 引入最大 debounce 延迟，长命令最坏 60s 才轮询一次 |
| 上下文质量 | 压缩时优先保留任务状态，strip tool details | 牺牲历史细节完整性 |

## 关联

*(暂无同类仓库已分析，链接待补充)*

<!-- generated-dimension-links -->
**本维度提取的节点：**

- [[openclaw/nodes/design-decisions/compaction-recoverability-priority]] — DesignDecision
- [[openclaw/nodes/design-decisions/startup-over-memory-tradeoff]] — DesignDecision
<!-- /generated-dimension-links -->
