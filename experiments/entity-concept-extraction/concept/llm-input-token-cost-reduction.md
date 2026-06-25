# LLM Input Token 成本降低策略

## 问题陈述
AI Agent 框架在多轮对话中，每轮都需要将 system prompt（含身份定义、技能列表、工具 schema、memory 快照等）作为前缀发送给 LLM。这些内容在跨轮次时不发生变化，但每次重建 system prompt 文本或重新实例化 Agent 对象都会导致 Anthropic prompt cache 的 prefix 匹配失败，使输入端 token 成本上升约 10 倍。三个框架分别从 prompt 内容层、进程实例层和纯函数式构建层解决了这个问题。

## 已知答案图谱

### 方案 A：Prompt 内容层缓存边界标记

- **特征**：在 system prompt 文本内部插入显式边界标记，将稳定内容与动态内容物理切分。向 LLM API 发送请求时，仅对稳定内容块附加 `cache_control` 标记，动态内容块不加标记。缓存命中/失效的粒度是 system prompt 内部的文本段级别。
- **关键机制细节（源码可见）**：
  - 边界标记为 `\n<!-- OPENCLAW_CACHE_BOUNDARY -->\n`（`system-prompt-cache-boundary.ts:3`）。该标记是纯文本 HTML 注释，对 LLM 语意不可见，但在构建 Anthropic API 请求时会触发切分逻辑。
  - system prompt 组装时，标记以上为稳定前缀（身份、技能、工具定义、静态 context 文件如 CLAUDE.md），以下为动态后缀（动态 context 文件、group chat context、provider 特定尾注、heartbeat 提示）——见 `system-prompt.ts:898`。
  - 哪些 context 文件属于动态内容，由 `isDynamicContextFile()` 判断其 basename 是否在 `DYNAMIC_CONTEXT_FILE_BASENAMES` 集合中，当前该集合仅包含 `"heartbeat.md"`（`system-prompt.ts:49, 61-63`）。
  - 发往 Anthropic API 时，`resolveAnthropicPayloadPolicy()` 在 `anthropic-transport-stream.ts:482` 处调用，`applyAnthropicPayloadPolicyToParams()` 随后将策略应用到 payload。其中的 `applyAnthropicCacheControlToSystem()` 在 system blocks 数组中扫描含有边界标记的 text block，将其拆分为两个 block：稳定部分附加 `cache_control: { type: "ephemeral" }`，动态部分不附加（`anthropic-payload-policy.ts:65-109`）。
  - 缓存 TTL 可配置：当 `cacheRetention` 为 `"long"` 且 baseUrl hostname 为 `api.anthropic.com` 或 `aiplatform.googleapis.com` 系列时返回 1h TTL，否则不设 TTL（即默认 5 分钟）；可通过 `PI_CACHE_RETENTION` 环境变量覆盖默认值（`anthropic-payload-policy.ts:52-62`）。
  - hook 系统可以通过 `prependSystemPromptAdditionAfterCacheBoundary()` 将 per-turn 临时上下文注入到边界标记之后、动态区域之前，避免破坏稳定前缀的缓存命中。该函数在 `pi-embedded-runner/run/attempt.prompt-helpers.ts:138` 处被调用（`system-prompt-cache-boundary.ts:22-47`）。
  - 当 prompt caching 被禁用（如非 Anthropic 兼容 provider），`stripAnthropicSystemPromptBoundary()` 会将边界标记从 prompt 文本中移除，不向 API 发送多余字符（`anthropic-payload-policy.ts:112-126`，在 `applyAnthropicPayloadPolicyToParams()` line 210 处调用）。
- **并行机制——pi-ai stream options 的 cacheRetention**：
  - `pi-embedded-runner/extra-params.ts` 中的 `createStreamFnWithExtraParams()`（lines 233-304）额外通过 `pi-ai` 库的 stream options 传递 `cacheRetention` 参数（`"short"` 或 `"long"`），由 `pi-ai` 在底层处理 `cache_control` 块的注入。
  - `resolveCacheRetention()`（`prompt-cache-retention.ts:17-51`）根据 provider/modelApi 决定是否返回默认 `"short"`：仅对 `"anthropic-direct"` 家族（native Anthropic 和 Anthropic Vertex）返回默认值，其余情况若无显式配置则返回 `undefined`。
  - `defaults.ts` 中的模型默认配置可为 Anthropic API key 模式的模型自动设置 `cacheRetention: "short"`。
  - 这是与内容层边界标记并行的补充路径——pi-ai 的 cacheRetention 提供粗粒度的全 system prompt 缓存，而内容层边界标记在此基础上实现精细的文本段级别切分。
- **OpenRouter Anthropic 模型特有路径**：
  - `proxy-stream-wrappers.ts` 中的 `createOpenRouterSystemCacheWrapper()`（lines 60-89）通过 `onPayload` 回调直接修改 API payload，调用 `applyAnthropicEphemeralCacheControlMarkers()`（`anthropic-payload-policy.ts:221-261`）在 system/developer 消息的最后一个 content block 上注入 `cache_control: { type: "ephemeral" }`，同时清除 assistant thinking blocks 上的 `cache_control`。
- **优势**：缓存粒度精细——只有真正变化的内容才会破坏缓存。与 Anthropic API 的 `cache_control` 机制原生集成。多路径覆盖不同 provider 场景（Anthropic direct、OpenRouter Anthropic、pi-ai pass-through）。
- **劣势**：system prompt 结构复杂化——编写 prompt 的人必须理解哪些内容应该放在边界上方。动态 context 文件分类依赖硬编码的 basename 集合（目前仅 `heartbeat.md`），新增需要修改代码。边界标记是 OpenClaw 特有的内部约定，对其他 provider 无意义。多路径机制（内容层边界 + pi-ai stream options + OpenRouter onPayload）增加了理解和维护成本。
- **实例**：OpenClaw

### 方案 B：进程实例层缓存复用

- **特征**：跨消息复用 AIAgent 进程实例，而非每条消息新建。由于 Anthropic prompt cache 的 prefix 匹配要求连续请求的前缀内容完全一致（包括 system prompt 和所有历史消息），只要同一个 AIAgent 实例存活，其内部冻结的 system prompt 和已累积的消息历史就不会变化，prefix cache 自然命中。
- **关键机制细节（源码可见）**：
  - `GatewayRunner.__init__()` 中声明 `self._agent_cache: Dict[str, tuple]`，key 为 session_key，value 为 `(AIAgent实例, config_signature)`（`run.py:610`），并由 `self._agent_cache_lock = _threading.Lock()` 保护并发访问（`run.py:611`）。
  - 每条消息到达时，`_agent_config_signature()` 计算当前 config 的 SHA256 指纹（前 16 字符），涵盖 model、api_key 的 SHA256 指纹、base_url、provider、api_mode、排序后的 enabled_toolsets list、ephemeral_prompt（`run.py:7730-7766`）。若签名与缓存中的签名一致，直接复用 AIAgent 实例并重置 `_last_activity_ts` 和 `_api_call_count`（`run.py:8548-8568`）。
  - AIAgent 内部将 system prompt 冻结在 `self._cached_system_prompt`（`run_agent.py:1162`），由 `_build_system_prompt()` 一次构建，仅在 context compression 事件后通过 `_invalidate_system_prompt()` 触发重建（`run_agent.py:3310`、`run_agent.py:3637-3646`）。
  - **关键细节——跨实例持久化**：对于 gateway 场景（每条消息重新创建 AIAgent），如果检测到 session 有历史消息且 `_cached_system_prompt` 为 None，从 session DB 中加载**上一次存储的 system prompt 原文**而非重新构建，以确保 prompt 字节完全一致从而命中 Anthropic prefix cache（`run_agent.py:8297-8313`）。这是项目注释中明确说明的设计意图（`run.py:604-607`）。
  - **关键细节——显式 cache_control 断点**：AIAgent 在构建 API 消息后，通过 `agent/prompt_caching.py` 中的 `apply_anthropic_cache_control()`（lines 41-72）采用 system_and_3 策略，在 system 消息 + 最后 3 条非 system 消息上显式注入 `cache_control: { type: "ephemeral" }` 断点（共 4 个，Anthropic 最大允许数）。该行为在 `run_agent.py:8631-8632` 处调用，由 `self._use_prompt_caching` 控制（line 812：native Anthropic 或 OpenRouter Claude 模式下自动启用）。
  - 缓存淘汰条件：config 签名不匹配（model/tools/api_key 变更）、session 超时（`run.py:2062-2079` 中关闭 cached agent 的资源并清理）、显式 `/new` 或 `/model` 命令调用 `_evict_cached_agent()`（`run.py:7794-7799`）。
- **优势**：不需要在 prompt 内容层做任何改造——system prompt 的构建逻辑与缓存策略完全解耦。整个 session 的所有内容（包括 memory 快照、历史消息）都维持在缓存命中状态。实现上只需要对象池 + 签名校验 + 锁，复杂度低。显式 `cache_control` 断点确保 `cache_control` 位置精确可控。
- **劣势**：AIAgent 实例占用进程内存，在多 session 场景下内存压力随并发 session 数线性增长。如果 config 签名变化（如切换 model 或 toolsets），整个缓存失效，需要重建 AIAgent 并重新发送完整 system prompt。AIAgent 对象本身必须支持安全复用（需处理 `_last_activity_ts`、`_api_call_count` 等状态重置）。缓存命中依赖 session DB 中存储的 prompt 原文保持一致，存在存储一致性问题。
- **实例**：Hermes Agent

### 方案 C：纯函数式 cache-stable 构造

- **特征**：不在 system prompt 文本内插入任何边界标记，也不跨消息缓存 Agent 进程实例。通过纯函数式构建纪律确保 system prompt 在相同 workspace 状态下字节完全一致，使 Anthropic prompt cache 的 prefix 匹配自然生效。cache_control 断点在 provider 层统一注入到已构建完成的 system prompt 整体 block 上，不涉及 prompt 文本的物理切分。
- **核心洞察**：隐式约定（deterministic construction）可以替代显式标记（boundary markers）——如果 system prompt 的每一层构建都是确定性的，那么在任何两层之间的物理位置插入边界标记的行为就等价于信任构建顺序本身。
- **关键机制细节（源码可见）**：
  - **六层固定拼接**（`context.py:30-63`）：`build_system_prompt()` 按固定顺序拼接六层内容：① Identity（`_get_identity(channel=channel)`）→ ② Bootstrap Files（`_load_bootstrap_files()`：AGENTS.md、SOUL.md、USER.md、TOOLS.md）→ ③ Memory（`self.memory.get_memory_context()`）→ ④ Always Skills（`self.skills.get_always_skills()` applied）→ ⑤ Skills Summary（`self.skills.build_skills_summary()` rendered via `agent/skills_section.md` template）→ ⑥ Recent History（`self.memory.read_unprocessed_history(since_cursor=…)` capped at 50 entries）。各层以 `"\n\n---\n\n"` 分隔符连接。
  - **纯函数语义**：`build_system_prompt()` 无副作用、不依赖运行时可变状态——MemoryStore 和 SkillsLoader 都基于 workspace 文件系统读取，给定相同的 workspace 状态必然产生字节相同的 system prompt。`_get_identity()` 通过 `render_template()` 渲染，其参数（workspace_path、runtime、platform_policy）在同一个进程生命周期内不变。
  - **get_definitions() 的 stable prefix 保证**（`registry.py:45-63`）：工具定义按 builtins 排序在前（alphabetically）、MCP tools 排序在后（alphabetically），确保工具列表的顺序在相同工具集下始终一致。这是"cache-stable construction"的一部分——工具定义本身也参与 system prompt 构成（通过 Skills Summary 渲染间接引入），排序稳定性保证同组工具的字节表示不变。注意：`get_definitions()` 返回的是有排序的 `list[dict]`，但 Python dict 默认插入顺序保证记录在编辑前后一致。
  - **provider 层 cache_control 注入**——provider 层在发送 API 请求前对已构建完成的 system prompt 整体施加 `cache_control: { type: "ephemeral" }`，不区分稳定/动态部分：
    - Anthropic provider（`anthropic_provider.py:314-339`）：对 system 消息整体注入 `cache_control`（str 时包装为 `[{text, cache_control}]`，list 时标记最后一个 block），同时对倒数第二条消息注入，对最后一个工具定义注入。共 3 个断点（system + n-1 message + last tool）。
    - OpenAI-compat Anthropic 路径（`openai_compat_provider.py:183-214`）：仅在 model 名以 `anthropic/` 或 `claude` 开头且 `spec.supports_prompt_caching` 时调用 `_apply_cache_control()`。对 system 消息和第 n-2 条消息注入 `cache_control`，对特定索引的工具定义注入（由 `_tool_cache_marker_indices()` 返回）。
  - **关键差异——何时缓存失效**：由于 cache_control 标记在 system 消息整体上（而非拆分后的稳定前缀），整个 system prompt 作为一个 cache block。Memory 更新（来自 `_mark_completed_goal()` 或 `_add_memory()`）、技能注册变化、bootstrap 文件修改都会导致 system prompt 整体变化，从而使整个 system block 的缓存失效。与方案 A（仅动态后缀失效）相比，失效粒度更粗；但代价更低——不需要维护边界标记和动态内容分类逻辑。
- **优势**：
  - 零侵入：不对 system prompt 文本内容做任何改造，不引入自定义标记。构建逻辑与缓存策略完全解耦——`ContextBuilder` 不感知 `cache_control` 的存在。
  - 构造纪律即文档：六层拼接顺序本身就是 prompt 结构的规范，不需要额外的"哪些内容是稳定的"设计文档。
  - provider 层调用简洁：一个 `_apply_cache_control()` 静态方法覆盖所有支持 prompt caching 的 provider，不需要像方案 A 那样维护多条路径（Anthropic direct transport split、pi-ai pass-through、OpenRouter onPayload injection）。
  - 适用于所有 Anthropic 兼容 provider：只要 provider 支持 `cache_control`，cache_control 的注入行为一致。
- **劣势**：
  - 缓存失效粒度粗：整个 system prompt 作为一个 cache block，任何一层内容变化（包括 memory 更新、recent history 追加）都导致全部 system prompt 重新发送。方案 A 可以做到仅动态后缀失效、稳定前缀保持命中。
  - 不区分稳定/动态内容：没有机制将变化频繁的内容（如 recent history）从稳定内容（如 identity、bootstrap files）中分离出来做差异化的缓存策略。
  - 依赖编程纪律：cache stability 完全取决于构建函数的确定性——如果将来有人在 `build_system_prompt()` 中引入非确定性元素（如时间戳、随机 ID），缓存会静默失效。没有类似方案 A 的边界标记作为 safety net。
  - tools 缓存标记仅最佳努力：`_tool_cache_marker_indices()` 的具体逻辑决定了仅对"最后的"工具定义注入缓存标记，tool 数量变化时可能导致缓存命中模式改变。
- **实例**：nanobot

## 跨仓库对比

| | OpenClaw | Hermes Agent | nanobot |
|---|---|---|---|---|
| **选择的方案** | 方案 A：内容层缓存边界标记 | 方案 B：进程实例层缓存复用 | 方案 C：纯函数式 cache-stable 构造 |
| **核心机制** | 在 system prompt 文本中插入 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记，API 请求时按标记切分 system blocks，仅对稳定前缀附加 `cache_control`；同时通过 pi-ai stream options 传递 `cacheRetention` 参数 | 跨消息缓存 AIAgent 进程实例，维持 system prompt 和历史消息不变，使 Anthropic prefix cache 自动命中 | 通过六层固定拼接 + 纯函数式构建确保 system prompt 在相同 workspace 状态下字节一致，不插入任何边界标记；`cache_control` 在 provider 层统一注入到 system 整体 block |
| **缓存粒度** | system prompt 内部文本段级别——稳定部分写入缓存，动态部分每次重新发送 | 整个 AIAgent 实例级别——冻结的 system prompt + 完整消息历史 | system prompt 整体——整个 system 作为一个 cache block，不分稳定/动态 |
| **缓存失效条件** | 动态 context 文件（`heartbeat.md`）变更、group chat context 变更、per-turn additions（均影响边界下方内容）；稳定前缀内容变更会破坏缓存 | config 签名不匹配（model/api_key/toolsets/ephemeral_prompt 任一变化）、session 超时、显式 `/new` 或 `/model` 命令 | system prompt 任何一层内容变化（memory 更新、skills 变更、bootstrap 文件修改、recent history 追加）均导致全部 system block 缓存失效 |
| **Anthropic API 集成方式** | 显式使用 `cache_control: { type: "ephemeral" }` 标记 system 稳定前缀 block 和最后一条 user message；OpenRouter 路径额外对 system/developer 消息注入 `cache_control` | 显式使用 `cache_control: { type: "ephemeral" }` 标记 system 消息和最后 3 条非 system 消息（system_and_3 策略，共 4 断点）；同时通过 AIAgent 实例缓存保证 system prompt 前缀不变化 | 显式使用 `cache_control: { type: "ephemeral" }` 标记 system 整体 block + 倒数第 2 条消息 + 最后一个 tool 定义（Anthropic provider）；OpenAI-compat Anthropic 路径标记 system + (n-2) 消息 + 特定索引 tool 定义 |
| **线程安全机制** | 无需（边界标记是纯文本，无共享状态） | `threading.Lock` 保护 `_agent_cache` 字典的读写 | 无需（`build_system_prompt()` 无副作用，provider 层 `_apply_cache_control()` 是 static 纯函数） |
| **跨 provider 兼容性** | 对非 Anthropic provider 自动移除边界标记（`stripAnthropicSystemPromptBoundary()`），不发送冗余字符；`cacheRetention` 仅对 anthropic-direct/bedrock 家族及手动配置的 custom Anthropic API 启用 | 显式 `cache_control` 注入仅对 native Anthropic 和 OpenRouter Claude 启用（`_use_prompt_caching`）；实例缓存部分受益于所有支持 prefix cache 的 provider | `cache_control` 注入通过 `spec.supports_prompt_caching` 开关控制（ProviderSpec），仅对 Anthropic 和 Anthropic-兼容路径启用；非 Anthropic provider 不受影响 |
| **内存开销** | 无额外进程内存开销 | 每个活跃 session 保留一个 AIAgent 实例，包含其 system prompt、memory store、工具注册等全部状态 | 无额外进程内存开销（每次 `build_system_prompt()` 新建字符串，不保留对象引用） |
| **付出的代价** | 约束了 system prompt 的结构设计——编写 prompt 时需明确区分稳定/动态内容的物理位置；动态文件分类仍需硬编码维护；多路径机制增加了复杂度 | 引入对象池管理复杂度（签名计算、并发安全、资源清理）；session 数量增长时内存线性增长；对象状态重置需要确保没有遗漏 | system prompt 任何变化都触发全量重发（无法精细豁免动态部分）；缓存稳定性依赖开发者维护构建函数的确定性——引入非确定性元素会静默破坏缓存，无编译期或运行期检查 |

## 设计权衡

三种方案解决的是同一个问题（维持 Anthropic prompt cache prefix 命中以降低 input token 成本），但选择的干预层次和策略哲学不同：

- **OpenClaw 选择了 prompt 内容层的精确控制（方案 A）**：直接操纵发给 API 的 system prompt 文本块结构，在内容层面明确标识出哪些是可缓存的、哪些是可变的。这种方式的前提是 system prompt 的结构由框架完全控制——OpenClaw 的 system prompt 通过 `buildAgentSystemPrompt()` 集中组装，开发者在 hook 中通过 API 注入内容而非直接拼接字符串，因此可以在边界标记处进行精确干预。代价是 system prompt 结构被缓存约束所塑造——哪些文件被视为"稳定"由 `DYNAMIC_CONTEXT_FILE_BASENAMES` 硬编码决定，改变分类规则需要修改代码。OpenClaw 同时通过 pi-ai 的 `cacheRetention` stream option 提供粗粒度的全 system prompt 缓存，与内容层边界标记形成互补。

- **Hermes Agent 选择了实例层的粗粒度复用（方案 B）**：信任 Anthropic prompt cache 的自动行为——只要连续请求的整个前缀不变，cache 自动命中。这种方式的前提是 AIAgent 实例可以安全复用——Hermes 在设计上保证了一次 session 内 system prompt 的稳定性（`_cached_system_prompt` 一次构建、仅在压缩时重建），并通过 config 签名机制确保配置变更时不会误用旧实例。与 OpenClaw 不同，Hermes 的 `cache_control` 注入策略更简洁（system_and_3），不涉及 prompt 文本的物理切分。代价是引入了对象池的复杂度，且缓存失效时影响面更大（整个实例重建 vs 仅重新发送动态后缀）。

- **nanobot 选择了纯函数式 cache-stable 构造（方案 C）**：通过**构建函数本身的确定性**来保证缓存命中——不在内容层插标记、不跨消息缓存实例，而是信任每一次 system prompt 构建的一致性。六层固定拼接（identity → bootstrap files → memory → always skills → skills summary → recent history）形成隐式约定：只要构建顺序不变、各层输出的确定性不变、分隔符不变，prompt 就是字节相同的。这不是"不知道缓存边界在哪"——恰恰相反，是"整个构建过程就是缓存边界的定义"。

三者不是互斥的——一个框架完全可以在内容层标记缓存边界的同时也缓存 Agent 实例。当前分离的路径反映了三个项目的不同约束：OpenClaw 作为通用 agent harness 需要在 system prompt 层面精细控制不同 provider 的缓存行为（pi-ai pass-through、Anthropic direct transport boundary split、OpenRouter onPayload injection 三条路径）；Hermes 作为 gateway 平台更关注在跨 session、跨消息的长周期运行中维持缓存命中，同时用轻量的 `apply_anthropic_cache_control()` 确保断点位置精确；nanobot 作为轻量 agent 框架选择了最低实现成本的路径——零侵入 + 构建纪律 = 缓存稳定性，避免在 prompt 工程和对象管理两个维度引入额外复杂度。

### 隐式约定 vs 显式标记

方案 A 和方案 C 的对立揭示了一个更深层的设计选择：

| | 方案 A（显式标记） | 方案 C（隐式约定） |
|---|---|---|
| **缓存边界定义方式** | 在 prompt 文本中插入自定义标记字符串 | 信任构建函数的确定性和固定拼接顺序 |
| **安全网** | 代码在标记处精确切分——即使构建逻辑引入了微妙的不确定性，marker 位置仍然"正确" | 无安全网——构建函数的任何非确定性改动都会静默破坏缓存，不会报错 |
| **代码复杂度** | 需要标记插入、切分扫描、移除/清理三套逻辑 | 仅需构建函数本身 + provider 层统一 injection |
| **可观测性** | 标记在 debug 时肉眼可见，可以在文本编辑器中定位缓存边界 | 缓存边界仅存在于构建函数的控制流中，不可见 |
| **重构风险** | 低——只要标记位置不变，构建逻辑的内部重构不影响边界 | 高——构建顺序、分隔符、各层输出格式的任何变化都可能破坏缓存 |
| **对 LLM 的影响** | 标记是 HTML 注释，对 LLM 语意不可见（OpenClaw 约定） | 无任何额外 token 发送 |

选择隐式约定的前提是 prompt 构建逻辑足够简单且受控——nanobot 的 `build_system_prompt()` 仅 33 行六层拼接，且 `ContextBuilder` 的职责单一，因此重构风险可控。选择显式标记的前提是需要支持复杂的多方注入场景（OpenClaw 的 hook 系统允许第三方通过 `prependSystemPromptAdditionAfterCacheBoundary()` 注入临时内容），且多条缓存路径需要统一的边界参考点。

## 溯源

| 仓库 | 验证过的源码文件 |
|------|-----------------|
| openclaw | `src/agents/system-prompt-cache-boundary.ts`（边界标记定义、split/strip/prepend 逻辑）；`src/agents/prompt-cache-stability.ts`（prompt section 行尾空白规范化）；`src/agents/system-prompt.ts:49, 61-63, 867-868, 895-918`（边界插入点、动态文件分类 `DYNAMIC_CONTEXT_FILE_BASENAMES`）；`src/agents/anthropic-payload-policy.ts:52-62, 65-109, 112-126, 174-218, 221-261`（Anthropic API payload 中的 cache_control 应用、边界标记清除、OpenRouter cache markers）；`src/agents/anthropic-transport-stream.ts:482-549`（Anthropic direct transport 中 payload policy 的应用入口）；`src/agents/pi-embedded-runner/extra-params.ts:233-304`（pi-ai stream options `cacheRetention` 传递）；`src/agents/pi-embedded-runner/prompt-cache-retention.ts:17-51`（cacheRetention 默认值解析）；`src/agents/pi-embedded-runner/proxy-stream-wrappers.ts:60-89`（OpenRouter Anthropic system cache wrapper）；`src/agents/pi-embedded-runner/anthropic-family-cache-semantics.ts`（Anthropic provider/model 识别与 cache retention family 分类） |
| hermes | `gateway/run.py:604-611`（agent_cache 声明和注释）；`gateway/run.py:7730-7766`（config 签名计算）；`gateway/run.py:8545-8599`（缓存查找与复用逻辑）；`gateway/run.py:7794-7799`（缓存淘汰）；`gateway/run.py:2060-2089`（超时 session 的 cached agent 清理）；`run_agent.py:806-813`（`_use_prompt_caching` 启用条件）；`run_agent.py:1162`（`_cached_system_prompt` 声明）；`run_agent.py:3310-3317`（system prompt 构建与缓存语义）；`run_agent.py:3637-3646`（prompt 失效与 memory 重载）；`run_agent.py:8297-8313`（跨实例 session 续接时从 DB 加载已存储 prompt）；`run_agent.py:8631-8632`（`apply_anthropic_cache_control` 调用点）；`agent/prompt_caching.py:41-72`（`apply_anthropic_cache_control` — system_and_3 策略，4 断点注入） |
| nanobot | `nanobot/agent/context.py:17`（ContextBuilder 类定义）；`nanobot/agent/context.py:30-63`（`build_system_prompt()` 六层固定拼接：identity → bootstrap files → memory → always skills → skills summary → recent history，分隔符 `"\n\n---\n\n"`）；`nanobot/agent/context.py:65-77`（`_get_identity()` 通过 `render_template()` 渲染身份模板，参数在进程生命周期内不变）；`nanobot/agent/context.py:103-113`（`_load_bootstrap_files()` 按固定顺序加载 AGENTS.md/SOUL.md/USER.md/TOOLS.md）；`nanobot/agent/tools/registry.py:45-63`（`get_definitions()` — builtins 按 schema_name 排序在前形成 stable prefix，MCP tools 排序在后）；`nanobot/providers/anthropic_provider.py:314-339`（`_apply_cache_control` — system 整体 block + 倒数第 2 条消息 + 最后 tool 定义注入 `cache_control`，共 3 断点）；`nanobot/providers/openai_compat_provider.py:183-214`（OpenAI-compat Anthropic 路径的 `_apply_cache_control`，仅在 model 名以 `anthropic/` 或 `claude` 开头时调用）；`nanobot/providers/registry.py:63-64, 108, 194`（`ProviderSpec.supports_prompt_caching` 开关定义，Anthropic 和 Anthropic bedrock 默认为 True） |
