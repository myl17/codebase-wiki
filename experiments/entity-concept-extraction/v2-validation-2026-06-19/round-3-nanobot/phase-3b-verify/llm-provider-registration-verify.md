# 验证报告：llm-provider-registration

## 格式完整性
- [x] 问题陈述是"如何..."问题形式 — `如何让不同 LLM provider 接入 agent 框架——是运行时接口选择...还是单一 SDK 统一路由...还是数据驱动注册表？`
- [x] 核心关切列表 >= 2 条 — 共 4 条
- [x] 每个权衡位置有"优先满足"和"接受妥协"两个字段 — A/B/C 三位置均有
- [x] 跨仓库对比表列数 = 仓库数 — 3 列（openclaw / hermes-agent / nanobot）
- [x] 溯源表完整 — 有

---

## 逐仓库验证

### openclaw

**Claim 1**: "`AgentHarness` 接口定义（`src/agents/harness/types.ts:30-44`）...`compact?` 和 `reset?` 为可选方法，不强制实现完整协议"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/agents/harness/types.ts:30-44`
代码摘要：
```typescript
export type AgentHarness = {
  id: string;
  label: string;
  pluginId?: string;
  supports(ctx: AgentHarnessSupportContext): AgentHarnessSupport;       // 必选
  runAttempt(params: AgentHarnessAttemptParams): Promise<AgentHarnessAttemptResult>; // 必选
  compact?(params: AgentHarnessCompactParams): Promise<AgentHarnessCompactResult | undefined>; // 可选
  reset?(params: AgentHarnessResetParams): Promise<void> | void;       // 可选
  dispose?(): Promise<void> | void;                                     // 可选（未提及！）
};
```
判定：⚠️ 接口行号正确，但方法计数不正确。源码有 **5 个方法（2 必选 + 3 可选）**，Concept 页描述为"4 个方法，其中 `supports` + `runAttempt` 必选，`compact?` + `reset?` 可选"——遗漏了第 5 个可选方法 `dispose?()`。所有提及"4 个方法"的位置（位置 A 代价、对比表"接口契约"行、「选择指南」 provider 能力差异化行）均需补上 `dispose?()`。修正建议：描述为「5 个方法（2 必选 + 3 可选：supports / runAttempt 必选，compact? / reset? / dispose? 可选）」。

---

**Claim 2**: "`selectAgentHarness()` 优先级排序选择（`src/agents/harness/types.ts`）：所有注册的 harness 实现按 `priority` 降序排列，遍历调用 `supports(ctx)`，返回第一个返回 true 的实现"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/agents/harness/selection.ts:45-106`（**非 types.ts**）
代码摘要：`selectAgentHarness()` 定义于 `selection.ts:45`。其选择逻辑为：(1) 收集所有 plugin harness；(2) 对每个调用 `harness.supports(ctx)`；(3) 过滤 supported=true 的条目；(4) 按 priority 降序排列（`compareHarnessSupport`，line 34-43，先比 priority 再比 id 字母序）；(5) 返回第一个。若匹配到 none，回退到 `createPiAgentHarness()`（除非配置为 `fallback: "none"` 则抛错）。
判定：❌ **文件位置错误**。`selectAgentHarness()` 不在 `types.ts` 而在 `selection.ts`。`types.ts` 仅包含类型定义（共 45 行），没有任何函数实现。溯源表中 openclaw 第 2 行标注的 `src/agents/harness/types.ts` 位置错误，应改为 `src/agents/harness/selection.ts`。

---

**Claim 3**: "`registerAgentHarness()` 插件注册入口（`src/plugins/types.ts:1867-1990`）...约 25 个注册方法之一"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/plugins/types.ts:1867-2017`
代码摘要：`OpenClawPluginApi` 类型定义从第 1867 行开始，`registerAgentHarness` 位于第 1976 行。整个 `OpenClawPluginApi` 接口共有 **36 个 register* 方法**（registerTool / registerHook / registerHttpRoute / registerChannel / registerGatewayMethod / registerCli / registerReload / registerNodeHostCommand / registerSecurityAuditCollector / registerService / registerCliBackend / registerTextTransforms / registerConfigMigration / registerAutoEnableProbe / registerProvider / registerSpeechProvider / registerRealtimeTranscriptionProvider / registerRealtimeVoiceProvider / registerMediaUnderstandingProvider / registerImageGenerationProvider / registerVideoGenerationProvider / registerMusicGenerationProvider / registerWebFetchProvider / registerWebSearchProvider / registerInteractiveHandler / registerCommand / registerContextEngine / registerCompactionProvider / registerAgentHarness / registerMemoryCapability / registerMemoryPromptSection / registerMemoryPromptSupplement / registerMemoryCorpusSupplement / registerMemoryFlushPlan / registerMemoryRuntime / registerMemoryEmbeddingProvider）。
判定：⚠️ 行号范围 1867-1990 是 `OpenClawPluginApi` 类型定义的整体范围，`registerAgentHarness` 精确位置是第 1976 行。注册方法数量"约 25"低估了约 30%（实际 36 个）。修正建议：行号改为 1976，数量改为"约 36"。

---

**Claim 4**: "package.json: `@mariozechner/pi-ai`（176 次 import）、`@mariozechner/pi-agent-core`（164 次 import）、`@mariozechner/pi-coding-agent`（77 次 import）、`@mariozechner/pi-tui`（22 次 import）——四个包精确锁定同一版本 `0.66.1`"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/package.json:1362-1365` — 版本精确锁定 `0.66.1`，四个包均同版本。
源码（import 计数）：在 `src/` 目录的 `.ts` 文件中 grep 统计：
- `@mariozechner/pi-ai`: **229 次**（Concept 页写 176）
- `@mariozechner/pi-agent-core`: **168 次**（Concept 页写 164）
- `@mariozechner/pi-coding-agent`: **107 次**（Concept 页写 77）
- `@mariozechner/pi-tui`: **27 次**（Concept 页写 22）
- 合计：**531 次**（Concept 页写 439）
判定：❌ **所有四个包的 import 计数均严重偏差**。差距最大的是 `pi-coding-agent`（107 vs 77，偏差 39%）。版本号 `0.66.1` 正确。注意：修复记录中已从 442 修正到 439，但实际是 531 —— 修正方向正确但数量仍然远低。

---

**Claim 5**: "`openclaw.plugin.json` 声明式元数据（`extensions/anthropic/openclaw.plugin.json:1-50`）：`providers` 声明拥有的 provider 名...`modelSupport.modelPrefixes` 声明支持的模型前缀、`providerAuthEnvVars` 声明认证环境变量...`contracts`、`configSchema`"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/extensions/anthropic/openclaw.plugin.json:1-47`（文件共 47 行）
代码摘要：manifest 包含 `id: "anthropic"`, `providers: ["anthropic"]`, `modelSupport: { modelPrefixes: ["claude-"] }`, `providerAuthEnvVars: { anthropic: ["ANTHROPIC_OAUTH_TOKEN", "ANTHROPIC_API_KEY"] }`, `contracts: { mediaUnderstandingProviders: ["anthropic"] }`, `configSchema` 等字段。`priority` 不在 manifest 中——priority 是 `supports()` 返回值的一部分（`types.ts:16`），而非插件清单字段。
判定：✅ 声明式元数据内容描述准确。行号 1-47（Concept 页 1-50 接近，文件实际 47 行）。

---

**Claim 6**: "新增 provider 对 core 透明（无需修改选择逻辑），但每个 harness 实现仍需编写完整代码"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/agents/harness/selection.ts:55-98` — `listPluginAgentHarnesses()` 动态列出已注册 harness，`selectAgentHarness()` 遍历调用 `supports()`，无 if-else 分支。
判定：✅ 选择逻辑与 provider 完全解耦，无需修改 core。新增 harness 工作量：实现 `AgentHarness` 接口（5 个方法——比 Concept 页预估的多 1 个）+ 调用 `registerAgentHarness()`。

---

**Claim 7**: "compact? 和 reset? 可选意味着某些 harness 缺少压缩能力——但 openclaw 将 compact 操作委托给 ContextEngine 而非 harness，这个 gap 在架构层面被填补"

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/agents/harness/selection.ts:140-153` — `maybeCompactAgentHarnessSession()` 中 `if (!harness.compact) return undefined;` 直接返回空。另外 `OpenClawPluginApi` 提供了独立的 `registerCompactionProvider`（line 1972）和 `registerContextEngine`（line 1967）。
判定：✅ 架构上确实有独立于 harness 的 compaction 路径（CompactionProvider + ContextEngine）。harness 的 `compact?()` 是备选而非唯一压缩通道。

---

### hermes-agent

**Claim 8**: "Provider 解析链为 OpenRouter → Nous Portal → Codex OAuth → Native Anthropic，按优先级 fallback 而非策略模式选择（`run_agent.py:8130-8189`）"

源码：

(1) 位置验证：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py:8130-8189` 是 `run_conversation()` 函数体内进行用户输入清理（`_sanitize_surrogates` / `sanitize_context`）和连接健康检查的代码。**此处没有任何 provider 解析逻辑。**

(2) 实际解析链位于 `agent/auxiliary_client.py`：
- `_get_provider_chain()` (line 1078-1090) 返回 **5 步链**：
  ```
  ("openrouter", _try_openrouter)
  ("nous", _try_nous)
  ("local/custom", _try_custom_endpoint)
  ("openai-codex", _try_codex)
  ("api-key", _resolve_api_key_provider)
  ```
- `_resolve_auto()` (line 1186-1265) 分两步：
  Step 1: 如果用户主 provider 是非聚合器（非 OpenRouter/Nous），直接用该 provider
  Step 2: 遍历 `_get_provider_chain()` 的 5 步链
- `_resolve_api_key_provider()` (line 681-751) 遍历 `PROVIDER_REGISTRY` 中所有 api_key 类型的 provider，尝试 Credential Pool 或环境变量。最后也包括 `_try_anthropic()`（line 706，通过 `anthropic` SDK native 路径，但仅在用户显式配置 anthropic 时）。

判定：❌ **位置、链长、链组成三重错误**。

| 错误项 | Concept 页 | 源码实际 |
|--------|-----------|---------|
| 文件位置 | `run_agent.py:8130-8189` | `agent/auxiliary_client.py:1078-1090` (`_get_provider_chain`) + line 1186-1265 (`_resolve_auto`) |
| 链长 | 4 步 | **5 步**（缺少 `local/custom` 和 `api-key` 步） |
| 第 4 步 | "Native Anthropic" | Anthropic 不在主链独立步骤中，而是第 5 步 `api-key` 子逻辑（仅当用户显式配置 anthropic 时，line 696-706） |

实际链是：**openrouter → nous → local/custom → openai-codex → api-key**（第 5 步按 PROVIDER_REGISTRY 顺序遍历所有已配置 API key 的 provider）。"Native Anthropic" 前缺少 local/custom 和 api-key 两步。修正建议：完整记录 5 步链，并将 Anthropic 标注为第 5 步 api-key 子逻辑中的条件特例而非独立步骤。

---

**Claim 9**: "'`openai` SDK 作为核心依赖锁定（`pyproject.toml:15-37`）...7 个必须核心依赖之一...与 `anthropic`、`httpx`、`prompt_toolkit`、`pydantic`、`rich`、`tenacity` 并列"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/pyproject.toml:15-37`
代码摘要：核心依赖列表实际包含 **18 个包**（openai / anthropic / python-dotenv / fire / httpx / rich / tenacity / pyyaml / requests / jinja2 / pydantic / prompt_toolkit / exa-py / firecrawl-py / parallel-web / fal-client / edge-tts / PyJWT），并非 7 个。
判定：⚠️ "7 个必须核心依赖"是一种选择性列举（选取了与 LLM 通信最直接相关的），但表述容易被误解为核心依赖只有 7 个。修正建议：增加限定词，如「openai 是 18 个核心依赖之一，与 anthropic、httpx、prompt_toolkit、pydantic、rich、tenacity 等并列」。

---

**Claim 10**: "无第三方转发层：行为可控性为核心取舍（`pyproject.toml:15-37`）"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/pyproject.toml` — 整个依赖列表中无 `litellm`、`langchain` 或其他 LLM 适配层包。
源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/auxiliary_client.py:681-751` — `_resolve_api_key_provider()` 直接构造 `OpenAI(api_key=..., base_url=...)` 客户端，无中间层。
判定：✅ 直接使用 `openai` SDK，无第三方转发层。行为完全可控。

---

**Claim 11**: "`anthropic` SDK 作为可选替代路径（`pyproject.toml:15-37`）...可通过 `api_mode` 配置在 OpenAI-compatible 路径和原生 Anthropic 路径间切换"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/pyproject.toml:16` — `anthropic>=0.39.0,<1` 在核心依赖中。
源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py:690-704` — `api_mode` 可设为 `"anthropic_messages"` 切换到原生 Anthropic SDK 路径。自动检测条件：`provider == "anthropic"` (line 697)、base_url 含 `api.anthropic.com` (line 697)、base_url 以 `/anthropic` 结尾 (line 704)。
判定：✅ api_mode 切换机制存在且 `anthropic` SDK 在核心依赖中。但 `anthropic` SDK 并非"可选"——它是核心依赖，安装时不可跳过。"可选"指的是**通信路径的选择**（可用可不用），但依赖本身是必需的。

---

**Claim 12**: "Provider 解析链在会话启动时确定，同一会话内不切换"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py:690-709` — `api_mode` 在 `AIAgent.__init__()` 中确定后存入 `self.api_mode`。`run_agent.py:960-1035` — client 在 `__init__` 中构造一次后存入 `self._client_kwargs`。
判定：✅ `api_mode` 和 client 在构造时确定，同一会话内不变。对比表中"部分——provider 解析链在会话启动时确定，同一会话内不切换"的描述准确。

---

### nanobot

**Claim 13**: "`PROVIDERS` 元组：数据驱动的注册表核心（`providers/registry.py:1-100`）"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/registry.py:75-361`
代码摘要：`PROVIDERS` 元组从第 75 行开始定义，第 361 行结束。文件第 1-74 行为模块文档字符串、import、`ProviderSpec` dataclass 定义。第 100 行处于 OpenRouter 的 `ProviderSpec` 定义中间（`detect_by_base_keyword="openrouter",`）。
判定：⚠️ `PROVIDERS` 元组实际起止行为 **75-361**。行号 1-100 包括了模块头、import 和 ProviderSpec 类定义，这些不是 PROVIDERS 元组的内容。建议溯源表改为 `75-361` 更精确。

---

**Claim 14**: "五种 backend 风格覆盖所有 API 范式（`providers/registry.py:1-376`）"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/registry.py:21-65` — `ProviderSpec.backend` 字段注释明确列出 5 种值：
```
# "openai_compat" | "anthropic" | "azure_openai" | "openai_codex" | "github_copilot"
backend: str = "openai_compat"
```
覆盖范围：`openai_compat` 覆盖最多 provider（OpenAI / DeepSeek / Gemini / DashScope / Moonshot / MiniMax / Mistral / StepFun / Xiaomi MIMO / Zhipu / vLLM / Ollama / OVMS / Groq / Qianfan / 所有 gateway）；`anthropic` 覆盖 Anthropic；`azure_openai` 覆盖 Azure；`openai_codex` 和 `github_copilot` 各覆盖一个 OAuth provider。
判定：✅ 5 种 backend 类型与源码完全一致。

---

**Claim 15**: "`ProviderSpec` 支持自动检测规则（`providers/registry.py:64,108,193`）：`key_prefix` 用于...；`base_url_keywords` 用于...；`supports_prompt_caching` 标记..."

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/registry.py:46-64`
```python
detect_by_key_prefix: str = ""     # match api_key prefix, e.g. "sk-or-"
detect_by_base_keyword: str = ""   # match substring in api_base URL
supports_prompt_caching: bool = False
```
判定：⚠️ 字段名有出入。Concept 页使用的名称与源码不完全一致：
- `key_prefix` → 源码为 `detect_by_key_prefix`
- `base_url_keywords` → 源码为 `detect_by_base_keyword`（单数，非复数）

语义正确但精确字段名有偏差。修正建议：使用源码精确字段名。

---

**Claim 16**: "移除 litellm：行为完全可控（`providers/base.py:629-698`）...3,719 行自有代码"

源码：
- `/Users/yuanlimiao/Work/agent_harness/nanobot/pyproject.toml` — 依赖列表无 `litellm`（已验证移除）
- `/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/` 目录总行数：**3,719 行**
- 文件分布：`base.py` 703 + `openai_compat_provider.py` 935 + `anthropic_provider.py` 536 + `azure_openai_provider.py` 183 + `github_copilot_provider.py` 257 + `openai_codex_provider.py` 158 + `registry.py` 375 + `transcription.py` 94 + `__init__.py` 42 + `openai_responses/__init__.py` 29 + `openai_responses/converters.py` 110 + `openai_responses/parsing.py` 297 = **3,719**
判定：✅ litellm 已移除，3,719 行精确无误。

---

**Claim 17**: "`LLMProvider` ABC 内建完整重试与降级（`providers/base.py:80-153, 629-698`）：`_run_with_retry()` 在基类中实现——standard 模式 3 次指数退避...429 分类从 error type/code 和响应文本两个路径提取...图片内容导致的错误自动降级为纯文本重试"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/base.py`
- 行 83：`_CHAT_RETRY_DELAYS = (1, 2, 4)` — 3 次指数退避
- 行 85：`_PERSISTENT_IDENTICAL_ERROR_LIMIT = 10` — 相同错误 10 次停止
- 行 101-146：429 分类——`_RETRYABLE_STATUS_CODES` (408/409/429)、`_NON_RETRYABLE_429_ERROR_TOKENS` (insufficient_quota / billing 等)、`_NON_RETRYABLE_429_TEXT_MARKERS` (文本路径)、`_RETRYABLE_429_TEXT_MARKERS` (rate limit 等)
- 行 658-665：`_strip_image_content(original_messages)` — 非 transient 错误时降级图片重试
- 行 700-702：`@abstractmethod def get_default_model(self) -> str` — 唯一的抽象方法是 `get_default_model()`，并非 `chat()`/`chat_stream()`
判定：✅ 重试逻辑、429 分类、图片降级三项与源码完全一致。但溯源表中「`chat()`/`chat_stream()` 统一接口，子类只需实现通信协议」的表述有偏差——基类的唯一抽象方法是 `get_default_model()`；`chat()`/`chat_stream()` 是子类的具体方法，通过 `_run_with_retry(call=...)` 传入 callable 来复用基类重试逻辑，而非基类定义的抽象方法。

---

**Claim 18**: "新增 provider 只需在 `PROVIDERS` 元组中加一行 `ProviderSpec` 数据 + 在 `config/schema.py` 中加一个配置字段，零新增代码"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/registry.py:1-10` — 文件头部注释确认：「Adding a new provider: 1. Add a ProviderSpec to PROVIDERS below. 2. Add a field to ProvidersConfig in config/schema.py. Done.」
源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/config/schema.py:97-127` — `ProvidersConfig` 为 27 个 provider 定义了 `ProviderConfig` 字段，与 PROVIDERS 元组一一对应。
判定：✅ 与源码文件头部注释完全一致，前提是新增 provider 属于已有 backend 风格。

---

**Claim 19**: "27 provider 覆盖 5 种 API 范式"（Concept 页原文为"20+ provider"，此处标注实际确数）

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/registry.py:75-361` — `PROVIDERS` 元组精确包含 **27 个 ProviderSpec** 条目。
判定：⚠️ "20+" 正确（27 > 20），但既然源码精确可知，建议使用确数"27"替换模糊的"20+"。

---

**Claim 20**: "所有 provider 发现逻辑——用户配置了哪个 API key、调用了哪个模型名、设置了哪个 base URL——都从这个元组的字段派生，不存在独立的发现规则"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/providers/registry.py:1-10` — 文件头部注释：「Env vars, config matching, status display all derive from here.」
判定：✅ 确认单一真实来源设计。

---

## 关切验证

| 关切 | 跨仓库对比表对应行 | 判定 |
|------|-------------------|------|
| 1. 可扩展性（新增 provider 工作量） | 「新增 provider 工作量」行 | ✅ openclaw（高）/ hermes（无代码）/ nanobot（极低）均有对比 |
| 2. 接口契约（provider 需实现什么） | 「接口契约」行 | ✅ openclaw（薄接口）/ hermes（无框架接口）/ nanobot（纯数据元组）均有对比 |
| 3. 行为可控性（是否依赖第三方转发层） | 「行为可控性」行 + 「第三方依赖层」行 | ✅ 三仓库均有覆盖 |
| 4. 覆盖范围（能支持多少 provider） | 「覆盖范围」行 + 「非标准 API provider」行 | ✅ 三仓库均有覆盖 |

---

## 追加完整性

- [x] openclaw 在各节均有提及 — 位置 A、对比表、选择指南、溯源表均包含
- [x] hermes-agent 在各节均有提及 — 位置 B、对比表、选择指南、溯源表均包含
- [x] nanobot 在各节均有提及 — 位置 C、对比表、选择指南、溯源表均包含

---

## 绝对化语言验证

| 绝对化表述 | 源码边界条件 | 判定 |
|-----------|------------|------|
| "底层 LLM transport **完全**委托给 `@mariozechner/pi-ai` 私有包"（openclaw） | `selectAgentHarness()` 默认回退到 PI harness，但 plugin harness 可在 `runAttempt()` 内使用任意 transport（selection.ts:77-93，如已有 codex plugin harness 走 OpenAI 路径） | ⚠️ "完全委托"过度——plugin harness 不依赖 pi-ai |
| "**所有** OpenAI-compatible provider 的 API 调用通过同一 SDK 发起"（hermes-agent） | `api_mode == "anthropic_messages"` 和 `api_mode == "bedrock_converse"` 不使用 openai SDK | ✅ 限定词"OpenAI-compatible"成立——非 compat 走独立 SDK |
| "非 OpenAI-compatible 的 provider 被**完全**排除"（hermes-agent） | `api_mode == "anthropic_messages"` 使用 `anthropic` SDK（原生 Anthropic API，非 OpenAI-compatible）；`api_mode == "bedrock_converse"` 使用 boto3 Bedrock Converse | ❌ 不准确——Anthropic native 路径和 Bedrock 路径正是两个非 OpenAI-compatible 的反例 |
| "provider 注册**完全**由数据驱动"（nanobot） | 非标准 API 的 provider（非 5 种 backend）需要实现新的 backend 子类（代价第 1 条已注明此限制） | ✅ 有限定条件——"属于已有 backend 风格的 provider"零代码 |
| "**所有** provider 发现逻辑...都从这个元组的字段派生，不存在独立的发现规则"（nanobot） | `detect_by_key_prefix`/`detect_by_base_keyword` 从 ProviderSpec 字段派生；匹配逻辑从 registry.py 派生 | ✅ 文件头部注释明确写「Env vars, config matching, status display all derive from here」 |

---

## 汇总

总 claim 数：20 | ✅：10 | ⚠️：7 | ❌：3

关键发现：

1. **openclaw `selectAgentHarness` 位置错误（❌）**：Concept 页两次标注为 `src/agents/harness/types.ts`，实际在 `src/agents/harness/selection.ts`。`types.ts` 仅含类型定义，无函数实现。

2. **hermes-agent provider 解析链三重错误（❌）**：位置（run_agent.py → 实际在 auxiliary_client.py）、链长（4 步 → 实际 5 步）、链组成（"Native Anthropic" 不在主链中，缺少 "local/custom" 和 "api-key" 两个实际存在的步骤）。Concept 页虽有 caveat 标注"根据源码推断"，但推断结果仍然不对。修正后的链应为：Step 1（非聚合器主 provider 直用）+ Step 2（openrouter → nous → local/custom → openai-codex → api-key），其中 Anthropic native 是第 5 步 api-key 子逻辑中的条件特例。

3. **openclaw `@mariozechner` import 计数严重偏差（❌）**：四个包全部低估（pi-ai 229 vs 176, pi-agent-core 168 vs 164, pi-coding-agent 107 vs 77, pi-tui 27 vs 22，总 531 vs 439）。此前修复记录从 442 修正到 439，方向正确但实际数字差距更大。

4. **openclaw `AgentHarness` 方法计数不完整（⚠️）**：5 个方法（2 必选 + 3 可选），Concept 页描述为 4 个（2+2），遗漏 `dispose?()` 可选方法。影响：位置 A 核心特征、已知代价、对比表"接口契约"行、选择指南 provider 能力差异化行。

5. **openclaw 注册方法数量低估（⚠️）**："约 25"实际 36，偏差约 30%。

6. **hermes-agent 核心依赖数量误导（⚠️）**："7 个必须核心依赖"实际共 18 个核心依赖，7 只是与 LLM 通信相关的选择性列举。

7. **hermes-agent "非 OpenAI-compatible 完全排除"与源码不符（⚠️）**：Anthropic native 路径（`api_mode == "anthropic_messages"`）和 AWS Bedrock 路径（`api_mode == "bedrock_converse"`）均非 OpenAI-compatible 但可接入。

8. **nanobot 溯源表行号和字段名偏差（⚠️）**：PROVIDERS 起止行为 75-361（非 1-100），字段 `key_prefix`/`base_url_keywords` 与源码 `detect_by_key_prefix`/`detect_by_base_keyword` 不一致。

9. **所有三仓库在所有章节中均有提及，核心关切全覆盖**（✅）。
