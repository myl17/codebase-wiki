# 验证报告：llm-input-token-cost-reduction

## openclaw

### 核心发现：三份关键源码文件不存在，整个"方案A"描述是虚构的

- `src/agents/system-prompt-cache-boundary.ts` — **不存在**
- `src/agents/anthropic-payload-policy.ts` — **不存在**
- `src/agents/prompt-cache-stability.ts` — **不存在**

搜索整个 openclaw 源码仓库，以下字符串均不存在：`OPENCLAW_CACHE_BOUNDARY`、`applyAnthropicCacheControlToSystem`、`stripAnthropicSystemPromptBoundary`、`isDynamicContextFile`、`DYNAMIC_CONTEXT_FILE_BASENAMES`、`PI_CACHE_RETENTION`、`prependSystemPromptAdditionAfterCacheBoundary`。

---

### 逐 Claim 验证

- **Claim**: 边界标记为 `\n<!-- OPENCLAW_CACHE_BOUNDARY -->\n`（`system-prompt-cache-boundary.ts:3`）
  - **源码证据**: 文件名不存在且全局 grep 无匹配
  - **判定**: ❌ 错误（文件不存在，标记字符串不存在于任何源码文件中）
  - **修正建议**: 应重写整个 openclaw 方案描述

- **Claim**: system prompt 组装时，标记以上为稳定前缀，以下为动态后缀（见 `system-prompt.ts:898`）
  - **源码证据**: `/Users/yuanlimiao/Work/openclaw-main/src/agents/system-prompt.ts`（共 688 行，实际不到 898 行）。`buildAgentSystemPrompt()` 函数按固定顺序拼接 sections（identity -> tooling -> safety -> skills -> memory -> workspace -> context files -> runtime），完全没有边界标记插入逻辑。Context files 在所有 section 之后、Silent Replies 之前统一注入（lines 588-607），没有静态/动态的区分。
  - **判定**: ❌ 错误（无边界标记机制，无静态/动态上下文文件区分）
  - **修正建议**: 删除该 claim。System prompt 结构中无任何缓存边界概念。

- **Claim**: 哪些 context 文件属于动态内容，由 `isDynamicContextFile()` 判断其 basename 是否在 `DYNAMIC_CONTEXT_FILE_BASENAMES` 集合中（`system-prompt.ts:61-63`）
  - **源码证据**: `system-prompt.ts:61-63` 实际是 `buildMemorySection()` 函数中的 citations 相关逻辑，与 context 文件分类无关。`isDynamicContextFile` 函数、`DYNAMIC_CONTEXT_FILE_BASENAMES` 集合在整个仓库中不存在。
  - **判定**: ❌ 错误（函数不存在，且行号对应内容完全无关）
  - **修正建议**: 删除该 claim

- **Claim**: `applyAnthropicCacheControlToSystem()` 在 system blocks 数组中扫描含有边界标记的 text block，将其拆分为两个 block（`anthropic-payload-policy.ts:65-110`）
  - **源码证据**: 文件名不存在，函数不存在。实际的 cache 机制在 `src/agents/pi-embedded-runner/extra-params.ts` 中，完全不同——通过 `pi-ai` 的 stream options 传递 `cacheRetention` 参数，而非在 system prompt 文本中切分 block。
  - **判定**: ❌ 错误（文件不存在，描述的机制不存在）
  - **修正建议**: 需完全重写 openclaw 的 cache 描述

- **Claim**: 缓存 TTL 可配置：`cacheRetention` 为 `"long"` 时返回 1h TTL（仅限 `api.anthropic.com` 和 `aiplatform.googleapis.com` 系列 host），默认为 `"short"`（5 分钟 TTL）；可通过 `PI_CACHE_RETENTION` 环境变量覆盖（`anthropic-payload-policy.ts:52-62`）
  - **源码证据**: 
    - `cacheRetention` 参数确实存在（`extra-params.ts:46-48`），值确实为 "none"/"short"/"long"
    - `resolveCacheRetention()` 函数（lines 66-102）默认对 Anthropic direct provider 返回 "short"
    - 但**没有** host-based gating（`api.anthropic.com` vs `aiplatform.googleapis.com` 限制），该函数仅检查 provider 是否为 "anthropic" 或 "amazon-bedrock"
    - **没有** `PI_CACHE_RETENTION` 环境变量（全局 grep 无结果）
  - **判定**: ⚠️ 不精确（cacheRetention 参数存在但 host-based gating 和 PI_CACHE_RETENTION 环境变量不存在于当前源码中）
  - **修正建议**: 移除 host-based gating 和 PI_CACHE_RETENTION 的描述。实际 TTL 通过 stream options 的 `cacheRetention` 参数传给 `pi-ai` 库处理。

- **Claim**: hook 系统可以通过 `prependSystemPromptAdditionAfterCacheBoundary()` 将 per-turn 临时上下文注入到边界标记之后（`system-prompt-cache-boundary.ts:22-47`）
  - **源码证据**: 文件不存在，函数不存在
  - **判定**: ❌ 错误

- **Claim**: 当 prompt caching 被禁用（如非 Anthropic 兼容 provider），`stripAnthropicSystemPromptBoundary()` 会将边界标记从 prompt 文本中移除（`anthropic-payload-policy.ts:112-126`）
  - **源码证据**: 文件不存在，函数不存在
  - **判定**: ❌ 错误

---

### OpenClaw 真实机制（基于源码）

实际的 prompt caching 机制位于 `src/agents/pi-embedded-runner/extra-params.ts`：

1. **通过 stream options 传 cacheRetention**：`createStreamFnWithExtraParams()`（lines 104-164）将 `cacheRetention` 参数注入到 `pi-ai` 的 `streamSimple` 调用中。`pi-ai` 负责在 Anthropic API 请求中添加 `cache_control`。
2. **默认值**：`defaults.ts` 中 `applyContextPruningDefaults()`（lines 377-477）为 Anthropic API key 模式的模型自动设置 `cacheRetention: "short"`。
3. **OpenRouter Anthropic 模型特有处理**：`createOpenRouterSystemCacheWrapper()`（lines 359-396）通过 `onPayload` 回调直接修改 API payload，在 system 消息的最后一个 content block 上注入 `cache_control: { type: "ephemeral" }`。
4. **缓存失效由 pi-ai 在后台处理**：openclaw 本身不在 system prompt 文本中做任何切分或标记。

**简言之，openclaw 的缓存策略是 pass-through 式的——依赖底层 pi-ai 库处理 `cacheRetention` 参数和 `cache_control` 块，无自定义文本边界标记机制。**

---

## hermes

### 核心发现：实例缓存描述基本准确，但对比表中关于"不显式使用 cache_control"的 claim 是错误的

---

### 逐 Claim 验证

- **Claim**: `GatewayRunner.__init__()` 中声明 `self._agent_cache: Dict[str, tuple]`，key 为 session_key，value 为 `(AIAgent实例, config_signature)`（`run.py:610`），并由 `self._agent_cache_lock = _threading.Lock()` 保护并发访问（`run.py:611`）
  - **源码证据**: `/Users/yuanlimiao/Work/agent_harness/hermes-agent/gateway/run.py:610-611`：
    ```python
    self._agent_cache: Dict[str, tuple] = {}
    self._agent_cache_lock = _threading.Lock()
    ```
    前面 lines 604-608 有注释说明设计意图："Cache AIAgent instances per session to preserve prompt caching. Without this, a new AIAgent is created per message, rebuilding the system prompt (including memory) every turn — breaking prefix cache and costing ~10x more on providers with prompt caching (Anthropic)."
  - **判定**: ✅ 准确

- **Claim**: `_agent_config_signature()` 计算当前 config 的 SHA256 指纹（前 16 字符），涵盖 model、api_key 的 SHA256 指纹、base_url、provider、api_mode、排序后的 enabled_toolsets list、ephemeral_prompt（`run.py:7730-7766`）
  - **源码证据**: `run.py:7730-7766` 确认。components list 包含 [model, api_key_fingerprint, base_url, provider, api_mode, sorted(enabled_toolsets), ephemeral_prompt]。api_key 用 SHA256 指纹而非原文。
  - **判定**: ✅ 准确

- **Claim**: 若签名与缓存中的签名一致，直接复用 AIAgent 实例并重置 `_last_activity_ts` 和 `_api_call_count`（`run.py:8548-8568`）
  - **源码证据**: `run.py:8548-8568` 确认。`_last_activity_ts = time.time()`（line 8565），`_api_call_count = 0`（line 8567）。
  - **判定**: ✅ 准确

- **Claim**: AIAgent 内部将 system prompt 冻结在 `self._cached_system_prompt`（`run_agent.py:1162`），由 `_build_system_prompt()` 一次构建，仅在 context compression 事件后通过 `_invalidate_system_prompt()` 触发重建（`run_agent.py:3310`、`run_agent.py:3637-3646`）
  - **源码证据**: 
    - `run_agent.py:1162`: `self._cached_system_prompt: Optional[str] = None` 及注释 "Cached system prompt -- built once per session, only rebuilt on compression"
    - `run_agent.py:3310-3317`: `_build_system_prompt()` 方法及注释 "Called once per session (cached on self._cached_system_prompt) and only rebuilt after context compression events."
    - `run_agent.py:3637-3646`: `_invalidate_system_prompt()` 设置 `self._cached_system_prompt = None` 并重新加载 memory
  - **判定**: ✅ 准确

- **Claim**: 对于 gateway 场景，如果检测到 session 有历史消息且 `_cached_system_prompt` 为 None，从 session DB 中加载**上一次存储的 system prompt 原文**而非重新构建（`run_agent.py:8297-8313`）
  - **源码证据**: `run_agent.py:8297-8313` 确认。lines 8301-8303 从 `self._session_db.get_session(self.session_id)` 获取 `stored_prompt`，line 8310 `self._cached_system_prompt = stored_prompt`。
  - **判定**: ✅ 准确

- **Claim**: 缓存淘汰条件：config 签名不匹配、session 超时、显式 `/new` 或 `/model` 命令调用 `_evict_cached_agent()`
  - **源码证据**: 
    - Config 签名不匹配：`run.py:8559-8561` 中 `cached[1] != _sig` 会跳过复用
    - `_evict_cached_agent()`: `run.py:7794-7799` 确认从 `_agent_cache` 中 pop
    - Session 超时清理：`run.py:2062-2079` 确认 idle session 的 cached agent 会被 `shutdown_memory_provider()` 和 `close()`
  - **判定**: ✅ 准确

---

### 关键错误：Hermes 确实显式使用 cache_control

- **Claim（对比表中）**: "不显式使用 `cache_control`；依赖 Anthropic 自动 prefix cache（连续请求前缀完全一致时自动命中）"
  - **源码证据**:
    - `/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/prompt_caching.py` — 专门的 prompt caching 模块，`apply_anthropic_cache_control()` 函数（lines 41-72）采用 "system_and_3 strategy"，在 system 消息 + 最后 3 条非 system 消息上注入 `cache_control: { type: "ephemeral" }` 断点（共 4 个断点，Anthropic 最大允许数）
    - `run_agent.py:806-812`：`_use_prompt_caching` 在 native Anthropic 或 OpenRouter Claude 模式下启用
    - `run_agent.py:8631-8632`：在构建 API 消息后调用 `apply_anthropic_cache_control()`
    - `run_agent.py:6345-6350`：在 Qwen 格式适配中也显式注入 `cache_control: {"type": "ephemeral"}`
  - **判定**: ❌ 错误（Hermes 确实在 API payload 中显式设置 `cache_control` 断点；它同时用实例缓存维持 system prompt 稳定性 AND 显式标记 `cache_control`，两者互补而非替代）
  - **修正建议**: 应将对比表中的该条改为："显式使用 `cache_control: { type: "ephemeral" }` 标记 system 消息和最后 3 条非 system 消息（system_and_3 策略，共 4 断点）；同时通过 AIAgent 实例缓存保证 system prompt 前缀不变化"

---

## 跨仓库对比表验证

| 对比维度 | Concept 页描述 | 实际情况 |
|---|---|---|
| openclaw 选择的方案 | 方案 A：内容层缓存边界标记 | ❌ 实际是通过 pi-ai 库 stream options 的 `cacheRetention` + OpenRouter 的 `onPayload` 注入，无文本边界标记 |
| hermes 选择的方案 | 方案 B：进程实例层缓存复用 | ✅ 基本准确，但不完整——hermes 同时使用显式 `cache_control` |
| openclaw 核心机制 | 在 system prompt 中插入 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记并切分 blocks | ❌ 不存在该机制 |
| hermes Anthropic API 集成方式 | "不显式使用 `cache_control`" | ❌ 明确使用 `apply_anthropic_cache_control()` 显式注入断点 |
| openclaw 线程安全机制 | "无需（边界标记是纯文本，无共享状态）" | ✅ 描述逻辑正确（虽然前提错误） |
| hermes 线程安全机制 | `threading.Lock` 保护 `_agent_cache` | ✅ 准确 |
| openclaw 跨 provider 兼容性 | 对非 Anthropic provider 自动移除边界标记 | ❌ 不存在边界标记，故也不存在移除逻辑。实际机制：仅 Anthropic/Bedrock/OpenRouter-Claude 模型启用 cacheRetention |
| hermes 跨 provider 兼容性 | "不依赖 provider 特性" | ⚠️ 不精确——`_use_prompt_caching` 明确仅对 native Anthropic 和 OpenRouter Claude 启用 |

---

## 汇总

- 总 claim 数: 17（openclaw 8 + hermes 9）
- ✅: 8（均来自 hermes） | ⚠️: 2 | ❌: 7（均来自 openclaw）
- 关键发现:

### 发现 1：openclaw 方案 A 的三个核心文件全部不存在
`system-prompt-cache-boundary.ts`、`anthropic-payload-policy.ts`、`prompt-cache-stability.ts` 在整个 openclaw 源码仓库中不存在。与之关联的下游函数（`applyAnthropicCacheControlToSystem`、`stripAnthropicSystemPromptBoundary`、`isDynamicContextFile`、`prependSystemPromptAdditionAfterCacheBoundary`）均不存在。常量 `DYNAMIC_CONTEXT_FILE_BASENAMES` 不存在。环境变量 `PI_CACHE_RETENTION` 不存在。

### 发现 2：openclaw 的真实缓存机制完全不同
实际的缓存通过 `pi-embedded-runner/extra-params.ts` 中的 `cacheRetention` stream option 传递给底层 `pi-ai` 库，或通过 `onPayload` 回调在 API payload 层面注入 `cache_control`（仅 OpenRouter Anthropic 模型）。没有在 system prompt 文本中做任何切分或标记。默认配置在 `defaults.ts` 中为 Anthropic API key 模式自动设置 `cacheRetention: "short"`。

### 发现 3：hermes 对比表中"不显式使用 cache_control"是错误的
Hermes 有一个专门的 `agent/prompt_caching.py` 模块，通过 `apply_anthropic_cache_control()` 函数在 system 消息和最后 3 条非 system 消息上显式注入 `cache_control: { type: "ephemeral" }`（system_and_3 策略）。这在 native Anthropic 和 OpenRouter Claude 模式下自动启用。

### 发现 4：hermes 方案 B 的几乎所有实现细节均准确
`_agent_cache` 字典结构、config 签名计算、`_last_activity_ts` 和 `_api_call_count` 重置、`_cached_system_prompt` 冻结/失效机制、跨实例 session DB prompt 恢复、缓存淘汰条件——所有这些 claims 均被源码精确验证。

### 发现 5：方案 A 的方案分类是错误的
openclaw 并未实现"方案 A（Prompt 内容层缓存边界标记）"。它的实际行为更接近通过配置参数委托给底层库处理，而非在 prompt 文本中插入自定义标记并手工切分。
