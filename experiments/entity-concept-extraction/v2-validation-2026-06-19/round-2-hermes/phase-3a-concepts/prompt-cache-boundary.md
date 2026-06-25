---
concept: prompt-cache-boundary
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# Prompt Cache Boundary（LLM Prompt 缓存-边界划分策略）

## 标准化问题陈述

在利用 LLM prompt caching 机制时，如何决定缓存边界的划分策略——是按消息类型切分还是按内容稳定性高低分离？

## 核心关切

1. **缓存命中率最大化**：尽可能多的 token 命中缓存以减少每轮 API 费用——prompt caching 的写入成本通常是基础价格的 1.25x，只有多次命中才能摊销
2. **动态内容隔离**：动态内容（记忆注入、实时上下文、工具调用结果）必须放在缓存边界之后——这些内容每轮都在变化，若出现在缓存区中会导致整个缓存段失效
3. **Breakpoint 配额约束**：cache breakpoint 数量受限于 provider——Anthropic 上限 4 个，OpenAI 上限根据模型不同而异（gpt-4o 上限 4 个，其他模型 1-3 个不等）——每个 breakpoint 的位置选择都是稀缺资源的分配问题
4. **多平台 TTL 兼容**：不同 LLM 平台的缓存 TTL 策略不同——Anthropic 支持 5 分钟和 1 小时两档且与 endpoint hostname 绑定，OpenAI 的自动缓存（`promptCaching: "auto"`）在连续 1024+ tokens 且命中时自动生效——边界设计需兼容多平台
5. **跨消息实例复用**：Agent 实例的生命周期决定 cache prefix 的有效期——如果每次消息处理都创建新的 agent 实例，前一轮写入的缓存段会在新实例上失效，cache 写入成本白白浪费

## 已知权衡位置

| 仓库 | 权衡位置 | 优先满足的关切 | 接受妥协的关切 |
|------|---------|--------------|--------------|
| openclaw | 稳定前缀 + 动态后缀分离 | 缓存命中率最大化（一个边界标记前的全部内容缓存）；多平台兼容 | Breakpoint 配额利用（只用 1 个，浪费剩余 3 个配额） |
| hermes-agent | system_and_3（4 breakpoints） | Breakpoint 配额最大化利用（4 个全用）；跨 turn 复用 | 缓存区稳定性（滚动窗口含动态内容，breakpoints 2-4 可能因消息内容变化而失效） |

## openclaw — 稳定前缀 + 动态后缀分离

### 缓存边界标记注入

`src/agents/system-prompt-cache-boundary.ts:3-47` 实现单一缓存边界的完整注入管线：

**边界标记**：在 system prompt 中插入 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 字符串标记，将整个 prompt 切分为两段——边界前的稳定前缀和边界后的动态后缀。

**稳定前缀**：边界前的所有内容（技能定义、人格声明、工具 schema、系统指令等不随对话轮次变化的内容）被打上 Anthropic `cache_control: { type: "ephemeral" }` 标记。这些内容在连续多轮对话中保持字节级一致，每次 API 调用都能命中缓存，仅支付缓存写入成本（首轮）后的折扣读取价。

**动态后缀**：记忆注入结果、实时上下文信息、当前时间、用户特定数据等每轮可能变化的内容统一放在边界标记之后，不进入缓存区域。这样动态内容的变化不会导致稳定前缀部分的缓存失效。

**跨平台适配**：边界标记的实现本身与平台无关——`cache_control` 的打标逻辑在 provider-specific payload policy 中处理，不同 LLM 平台各自解析边界标记并应用各自的缓存协议。`src/agents/anthropic-payload-policy.ts:37-65` 的 `cacheRetention` 函数根据 endpoint hostname 选择 TTL —— `api.anthropic.com` 和 `aiplatform.googleapis.com` 使用 `ttl: "1h"` 的长缓存，其他端点（如代理、自部署）默认使用 short TTL。用户可通过 `cacheRetention` 配置项或 `PI_CACHE_RETENTION` 环境变量显式控制。

### 核心取舍

openclaw 选择只用一个 breakpoint 将所有稳定内容打包在一起。这个决策的深层逻辑是：**缓存命中的收益取决于稳定前缀的大小**——openclaw 的 system prompt 体量大（包含 20+ 种技能定义和完整的工具 schema），单个 breakpoint 已经覆盖了最大块的稳定 token 基数。额外的 breakpoints 能额外保护的 token 量（用户消息历史）远少于系统提示，且 user message 滚动窗口的不稳定性让额外 breakpoints 的命中率不可预测。因此 openclaw 选择用最简单（1 个 breakpoint）同时覆盖最大稳定内容基数的方案。

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 缓存命中率最大化（单一 breakpoint 覆盖最大稳定前缀——system prompt 的全部静态内容，命中一次即摊销全部写入成本） | Breakpoint 配额利用（只用 1 个，剩余 3 个配额未使用——如果未来需要按粒度切分缓存区以应对部分失效场景，将受到局限） |
| 多平台兼容（cache_control 打标逻辑在 per-provider payload policy 中实现，边界标记本身是平台无关的字符串） | |

## hermes-agent — system_and_3（4 breakpoints）

### 多点缓存边界策略

`agent/prompt_caching.py:1-73` 实现 `system_and_3` 策略——充分利用 Anthropic 的 4 个 cache breakpoint 上限：

```
Breakpoint 1: System prompt（跨 turn 稳定内容）
Breakpoints 2-4: 最后 3 条非 system 消息（滚动窗口，按距当前 turn 从近到远排列）
```

**缓存标记注入流程**：每次 turn 前调用 `apply_prompt_caching()`（行 28-43），对 message 列表做 deep copy 后逐条注入 `cache_control: { type: "ephemeral" }` marker。System prompt 固定打在第 1 个 breakpoint 上；user/assistant 消息按 `num_breakpoints - 1 = 3` 的配额从消息列表尾部向前分配（跳过 system 消息），最新 3 条非 system 消息各占一个 breakpoint。这种设计确保最近上下文（最可能在后续 turn 中保持不变的消息）享有缓存保护。

**滚动窗口的不稳定性**：breakpoints 2-4 覆盖的是最近 3 条非 system 消息——这些消息在每一轮对话后都会滚动（新一轮消息加入，最旧的消息被挤出窗口）。被挤出窗口的消息其对应 breakpoint 缓存失效；新进入窗口的消息需要重新写入缓存。因此只有 breakpoint 1（system prompt）是真正跨 turn 稳定的，breakpoints 2-4 的命中率取决于对话轮次与缓存 TTL 的相对节奏。

**TTL 策略**（行 57-59）：默认 `5m`（5 分钟），写入成本为基础价格的 1.25x。可配置切换为 `1h`（1 小时）用于更激进的缓存策略——1h TTL 写入成本更高但适合低频长对话场景。TTL 选择通过 `ANTHROPIC_CACHE_TTL` 环境变量或配置文件控制。

**跨消息实例复用**：`gateway/run.py:604-611` 的 `GatewayRunner` 缓存 `AIAgent` 实例以保持 prompt cache prefix 跨消息有效。如果每次消息处理都重新创建 agent 实例，前一轮写入的缓存段会在新实例中失效——Gateway 模式下 agent 实例被复用，使得 prompt cache 的写入成本能被多轮消息分摊。

**自动启用条件**（`run_agent.py:809-812`）：OpenRouter + Claude 模型自动启用缓存，原生 Anthropic API 自动启用缓存——其他 provider/模型组合不自动启用，需手动配置。

### 核心取舍

hermes-agent 选择用满 4 个 breakpoint 将 system prompt 和最近上下文都纳入缓存保护。这个决策的深层逻辑是：**hermes-agent 的长对话场景中，最近几条消息在连续多轮中保持不变的概率很高**——用户通常不会在每轮都回溯修改历史，因此 breakpoints 2-4 在多数轮次中能命中缓存。四个 breakpoints 全用的边际收益（在长对话中额外保护滚动窗口）超过其边际成本（每轮 deep copy + marker 注入的计算开销和复杂度）。

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| Breakpoint 配额最大化（4 个全用不浪费——system prompt + 最近 3 条消息全缓存保护） | 缓存区稳定性（breakpoints 2-4 覆盖滚动窗口——消息滚动时对应 breakpoint 失效需重写，命中率不如纯静态前缀稳定） |
| 跨 turn 复用（Gateway 模式缓存 AIAgent 实例保持 prefix 有效） | |

## 跨仓库对比

| 维度 | openclaw | hermes-agent |
|------|----------|-------------|
| **策略名称** | 稳定前缀 + 动态后缀分离 | `system_and_3` |
| **Breakpoint 数量** | 1 | 4（Anthropic 上限全用） |
| **缓存覆盖** | 仅 system prompt 稳定前缀 | System prompt + 最近 3 条非 system 消息（滚动窗口） |
| **边界标记方式** | `<!-- OPENCLAW_CACHE_BOUNDARY -->` 字符串插入 system prompt | `cache_control: { type: "ephemeral" }` 逐条注入 message 对象（deep copy 后操作） |
| **TTL 策略** | Endpoint-aware：`api.anthropic.com` / `aiplatform.googleapis.com` → 1h，其他 → short；可通过 `cacheRetention` config 或 `PI_CACHE_RETENTION` 环境变量覆盖 | 默认 5min，可通过 `ANTHROPIC_CACHE_TTL` 切换到 1h |
| **多平台兼容路径** | Cache 标记字符串平台无关，per-provider payload policy 各自解析并应用平台缓存协议 | 仅 Anthropic/OpenRouter 路径自动启用——其他 provider 不应用缓存，通过检查 provider 类型分支 (`run_agent.py:809-812`) |
| **Agent 实例复用** | 未从文档中检出显式的实例缓存机制 | `GatewayRunner` 缓存 `AIAgent` 实例 (`gateway/run.py:604-611`) |
| **每次 turn 开销** | 一次性边界注入（system prompt 构建阶段），后续 turn 无额外操作 | 每次 turn deep copy messages + 逐条注入 markers |
| **缓存命中确定性** | 高——稳定前缀内容完全不变，缓存一定命中直到 TTL 过期 | 中——breakpoint 1 确定命中，breakpoints 2-4 命中取决于消息是否被滚动覆盖 |
| **核心取舍** | 宁可少用 breakpoints 也要保证覆盖内容的绝对稳定（稳定性 > 配额利用率） | 宁可用满 breakpoints 也要最大化缓存保护面（覆盖率 > 稳定性） |

## 选择指南

| 场景 | 推荐策略 | 原因 |
|------|---------|------|
| System prompt 体量大（>10K tokens）且动态内容少 | openclaw 的稳定前缀分离 | 单个 breakpoint 已覆盖最大 token 基数，剩余 breakpoints 边际收益低 |
| 长多轮对话，用户消息在相邻轮次间高度重叠 | hermes-agent 的 system_and_3 | 滚动窗口中的最近消息在连续轮次间保持不变，4 个 breakpoints 都能命中 |
| 需要多 LLM 平台兼容（Anthropic + OpenAI + 自部署） | openclaw 的边界标记 + per-provider policy | 边界标记字符串无关平台，各 provider 自行解析 |
| 低频长对话（单轮间隔 >5 分钟） | hermes-agent 配合 1h TTL | 5min TTL 在低频场景下过期频繁，1h TTL 牺牲写入成本换命中率 |
| 记忆/上下文注入频繁且内容变化大 | openclaw 的稳定前缀分离 | 动态内容全部放在边界后，缓存区绝对纯净，不受注入变化影响 |
| Gateway 模式（多用户多 session 复用同一进程） | hermes-agent 配合 agent 实例缓存 | 实例复用 + 缓存复用双重优化，写入成本被多次摊销 |

## 关键源码引用

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/agents/system-prompt-cache-boundary.ts` | 3-47 | `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记注入 + 稳定前缀 `cache_control: { type: "ephemeral" }` 打标 |
| openclaw | `src/agents/anthropic-payload-policy.ts` | 37-65 | `cacheRetention()` endpoint-aware TTL 选择：`api.anthropic.com` / `aiplatform.googleapis.com` → `ttl: "1h"`，其他 → short |
| hermes-agent | `agent/prompt_caching.py` | 1-73 | `system_and_3` 策略：4 breakpoints（system + 最近 3 条非 system 消息），`apply_prompt_caching()` deep copy + marker 注入 |
| hermes-agent | `agent/prompt_caching.py` | 28-43 | `apply_prompt_caching()` 主逻辑——遍历 messages，跳过 system，对最后 N 条注入 `cache_control` |
| hermes-agent | `agent/prompt_caching.py` | 57-59 | TTL 默认 `5m`，可通过 `ANTHROPIC_CACHE_TTL` 切换为 `1h` |
| hermes-agent | `gateway/run.py` | 604-611 | `GatewayRunner` 缓存 `AIAgent` 实例保持 prompt cache prefix 跨消息有效 |
| hermes-agent | `run_agent.py` | 809-812 | OpenRouter + Claude 或原生 Anthropic API 自动启用 prompt caching |

## 关联

- [[openclaw/dimensions/openclaw-performance-tradeoffs]]
- [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]]
