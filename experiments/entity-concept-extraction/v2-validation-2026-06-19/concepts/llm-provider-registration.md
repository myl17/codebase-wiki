---
concept: llm-provider-registration
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
  - nanobot
---

# LLM Provider 接入策略：运行时接口选择、单一 SDK 统一路由、还是数据驱动注册表？

## 标准化问题陈述

如何让不同 LLM provider 接入 agent 框架——是运行时接口选择（plugin 声明适用场景，core 按优先级选择）、开发时单一 SDK 统一路由（所有 provider 经 OpenAI-compatible 协议通信）、还是数据驱动注册表（新增一行元组数据即完成注册）？

## 核心关切

1. **可扩展性**：新增 provider 的工作量——写代码实现接口 vs 加一行元组数据 vs 只需 OpenAI-compatible API
2. **接口契约**：provider 需要实现什么接口——完整 ABC vs 最小可选方法 vs 纯数据元组
3. **行为可控性**：是否依赖第三方转发层引入不可控风险
4. **覆盖范围**：能支持多少 provider，非标准 API 的 provider 是否被排除

## 已知权衡位置

### 位置 A：openclaw — `supports(ctx)` + priority 运行时接口选择

**优先满足的关切**：运行时灵活选择（plugin 自主声明适用场景，core 不硬编码 provider 选择条件）；接口灵活（`compact?` 和 `reset?` 为可选方法，不强制实现完整协议）

**接受妥协的关切**：可扩展性（新增 harness 需完整代码实现——实现 `AgentHarness` 接口 + 注册到 plugin API，并非加一行数据即可）

**核心特征**：`AgentHarness` 是一个运行时策略接口——每个 provider plugin 实现 `supports(ctx)` 方法自主声明自己适用的上下文（特定模型前缀、特定 endpoint 等），core 通过 `selectAgentHarness()` 按 priority 排序选择第一个 `supports()` 返回 true 的实现。新增 provider 对 core 透明（无需修改选择逻辑），但每个 harness 实现仍需编写完整代码。底层 LLM transport 完全委托给 `@mariozechner/pi-ai` 私有包（229 次 import）——openclaw 自己不维护 provider 通信层代码。

**关键机制（源码可见）**：

1. **`AgentHarness` 接口定义**（`src/agents/harness/types.ts:30-44`）：`supports(ctx: AgentHarnessSupportContext)` 用于优先级选择，`runAttempt(params)` 执行一次 LLM 调用，`compact?(params)` 压缩上下文，`reset?(params)` 重置 session。`compact?` 和 `reset?` 是可选方法——并非每个 LLM provider 都有等价的压缩和重置能力，可选设计让轻量 provider 也能接入而不需要实现完整协议。

2. **`selectAgentHarness()` 优先级排序选择**（`src/agents/harness/selection.ts:45-106`）：所有注册的 harness 实现按 `priority` 降序排列，遍历调用 `supports(ctx)`，返回第一个返回 true 的实现。这种策略模式让 provider 扩展与 core 选择逻辑彻底解耦——新增 provider 无需修改 core 的任何 if-else 分支。

3. **`registerAgentHarness()` 插件注册入口**（`src/plugins/types.ts:1867-1990`）：通过 `OpenClawPluginApi.registerAgentHarness(harness)` 注册。这是约 25 个注册方法之一（与 `registerTool`、`registerHook`、`registerChannel`、`registerContextEngine` 等并列），所有 provider extension（anthropic/openai/ollama/deepseek）通过同一条 API 接入。

4. **`openclaw.plugin.json` 声明式元数据**（`extensions/anthropic/openclaw.plugin.json:1-50`）：除了命令式注册，每个 extension 还提供声明式 manifest——`providers` 声明拥有的 provider 名（用于路由）、`modelSupport.modelPrefixes` 声明支持的模型前缀、`providerAuthEnvVars` 声明认证环境变量（用于 doctor/setup wizard 自动检测）。声明式层提供元数据而不影响运行时行为——是命令式 API 的补充，非替代。

5. **底层 LLM transport 完全委托私有包族**（`package.json`: `@mariozechner/*` dependencies）：531 处 import 来自 `@mariozechner/pi-ai`（229 次，LLM transport、OpenAI compat、模型配置类型）、`@mariozechner/pi-agent-core`（168 次，agent 消息类型、工具结果类型）、`@mariozechner/pi-coding-agent`（107 次，session 管理、compaction、bootstrap）、`@mariozechner/pi-tui`（27 次，终端 UI）。四个包精确锁定同一版本 `0.66.1`。openclaw 的 provider 接入工作集中在 harness 层的接口适配，底层通信完全外包——替换成本极高但当前无需维护。

**已知代价**：
- 新增 provider 需要理解并实现 `AgentHarness` 接口——工作量为完整代码实现，非一行配置
- `supports(ctx)` 的运行时判断在每次 LLM 调用前执行——provider 数量增长时选择开销线性增长（当前 provider 数量少，尚未成为瓶颈）
- 底层完全依赖 `@mariozechner/*` 私有包——provider 可扩展性受限于上游包对 LLM provider 的支持范围
- `compact?` 和 `reset?` 可选意味着某些 harness 缺少压缩能力——但 openclaw 将 compact 操作委托给 ContextEngine 而非 harness，这个 gap 在架构层面被填补

**已知实例**：
- [[openclaw/nodes/extension-points/openclaw-agent-harness]]
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]]

---

### 位置 B：hermes-agent — OpenAI SDK 统一路由层

**优先满足的关切**：行为完全可控（不依赖 litellm 等第三方转发层，LLM 调用直接使用 `openai` SDK 发起）；接口简化（provider 只需提供 OpenAI-compatible API endpoint，不需要实现任何框架定义的接口）

**接受妥协的关切**：覆盖范围（非 OpenAI-compatible 的 provider 被排除）；架构锁定（单一 SDK `openai>=2.21.0` 锁定整个 provider 生态——所有 20+ provider 都通过它路由，无替代路径）

**核心特征**：hermes-agent 不定义 provider 接口——provider 接入完全通过 OpenAI-compatible API 协议完成。架构中唯一的 provider 抽象是 SDK 选择：`openai` SDK（`>=2.21.0,<3`）作为核心依赖覆盖所有 OpenAI-compatible 的 20+ provider；`anthropic` SDK（`>=0.39.0,<1`）作为可选路径提供原生 Anthropic Messages API 支持。Provider 解析链为 5 步优先级 fallback（`agent/auxiliary_client.py`）：OpenRouter → Nous Portal → local/custom → Codex OAuth → api-key（遍历 PROVIDER_REGISTRY 中所有已配置 API key 的 provider，其中 Anthropic native 是第 5 步 api-key 的条件子逻辑，仅当用户显式配置 anthropic 时生效）——按优先级 fallback 而非策略模式选择，与 openclaw 的 `supports(ctx)` 运行时选择形成对比。

**关键机制（源码可见）**：

1. **`openai` SDK 作为核心依赖锁定**（`pyproject.toml:15-37`）：`openai>=2.21.0,<3` 是 7 个必须核心依赖之一（与 `anthropic`、`httpx`、`prompt_toolkit`、`pydantic`、`rich`、`tenacity` 并列），安装时不可跳过。所有 OpenAI-compatible provider 的 API 调用通过同一 SDK 发起——不需要 per-provider 适配代码。

2. **`anthropic` SDK 作为可选替代路径**（`pyproject.toml:15-37`）：`anthropic>=0.39.0,<1` 同样是核心依赖，提供原生 Anthropic Messages API 支持。可通过 `api_mode` 配置在 OpenAI-compatible 路径和原生 Anthropic 路径间切换——但 Anthropic 也可通过 OpenRouter 的 OpenAI-compatible 端点间接访问（无需 `anthropic` SDK）。SDK 层的双轨设计提供了一条退出 OpenAI 单点依赖的逃生通道。

3. **Provider 解析链：优先级 fallback 而非策略模式**（`agent/auxiliary_client.py:1078-1090,1186-1265`）：`_get_provider_chain()` 返回 5 步链 (openrouter → nous → local/custom → openai-codex → api-key)，`_resolve_auto()` 分两步——Step 1 非聚合器主 provider 直用，Step 2 遍历 5 步链。第 5 步 api-key 调用 `_resolve_api_key_provider()`（line 681-751）遍历 PROVIDER_REGISTRY 中所有已配置 API key 的 provider，Anthropic native 是其中的条件子逻辑（仅当用户显式配置 anthropic 时生效，line 696-706）。这与 openclaw 的 `selectAgentHarness()`（plugin 通过 `supports()` 自主声明适用场景、core 不感知每个 provider 的选择逻辑）是两种截然不同的选择模式：hermes 是 core 内置的优先级链，openclaw 是 plugin 自主声明的策略模式。

4. **Her herm 依赖策略：openai SDK 作为不可替换的单点**（`pyproject.toml:15-37`）：依赖策略文档明确标注 `openai` SDK 替换成本为**高**——"20+ provider 都通过它路由，无官方替代"。这是 hermes-agent 最核心的架构锁定点：移除 `openai` SDK 意味着所有 provider 通信路径断开。相比之下 `anthropic` SDK 替换成本为**低**——"api_mode 切换即可回到 OpenAI-compatible 路径"。

5. **无第三方转发层：行为可控性为核心取舍**（`pyproject.toml:15-37`）：hermes-agent 直接使用 `openai` SDK 而非 litellm 等中间层——每次 LLM 调用直接经由 SDK HTTP 请求发出，没有中间层的 token 计数不一致、模型名称映射错误、不可控版本升级。这个决策与 nanobot 移除 litellm 同源但走向不同：hermes 通过单一 SDK 锁定实现可控，nanobot 通过自行维护 3,719 行适配代码实现可控。

**已知代价**：
- 非 OpenAI-compatible 的 provider 被完全排除——任何不使用 OpenAI API 格式的 LLM 服务无法接入
- `openai` SDK 是不可替换的核心依赖——如果 OpenAI 修改 API 或 SDK 引入破坏性变更，20+ provider 通信全部受影响
- 新增 provider 不需要代码但需要 provider 自身提供 OpenAI-compatible endpoint——依赖外部服务而非框架内逻辑
- Provider 解析链是硬编码的优先级 fallback——新增一个非 OpenAI-compatible 的解析节点需要修改 `agent/auxiliary_client.py`
- 没有 per-provider 行为定制——所有 provider 共享同一套重试逻辑、错误处理、stream 解析（由 `openai` SDK 统一提供），无法针对特定 provider 的 quirks 做专门优化

**已知实例**：
- [[hermes-agent/nodes/components/hermes-agent-ai-agent]]
- [[hermes-agent/dimensions/hermes-agent-dependency-strategy]]

---

### 位置 C：nanobot — 数据驱动 ProviderSpec 注册表

**优先满足的关切**：可扩展性最大化（新增 provider 只需在 `PROVIDERS` 元组中加一行 `ProviderSpec` 数据 + 在 `config/schema.py` 中加一个配置字段，零新增代码）；代码量最小（provider 注册逻辑完全由元组驱动，所有匹配、检测、状态展示逻辑从元组派生）

**接受妥协的关切**：覆盖范围（backend 风格有限——仅 5 种：`openai_compat` / `anthropic` / `azure_openai` / `openai_codex` / `github_copilot`，非标准 API 需新增 backend 实现）；接口契约（provider 被建模为纯数据元组而非接口实现——行为定制能力受限于 backend 类型的表达能力）

**核心特征**：nanobot 的 provider 注册完全由数据驱动——`PROVIDERS` 是一个 Python 元组，每个元素是 `ProviderSpec` 命名字段描述一个 LLM 供应商的完整接入信息：模型名称关键词匹配规则、API key 前缀检测规则、API base URL 关键词检测规则、gateway 识别、本地部署标记、OAuth 支持、prompt caching 声明。五种 backend 类型覆盖 20+ provider，任何新增的 OpenAI-compatible provider 只需一行元组数据。所有 provider 的子类实现（`AnthropicProvider`、`OpenAICompatProvider`、`AzureOpenAIProvider` 等）共享 `LLMProvider` 基类中内建的三级重试逻辑、429 分类、图片降级。

**关键机制（源码可见）**：

1. **`PROVIDERS` 元组：数据驱动的注册表核心**（`providers/registry.py:1-100`）：20+ provider 的 `ProviderSpec` 数据以元组形式维护——这是整个 provider 系统的**单一真实来源**。每个 `ProviderSpec` 包含：模型名称关键词匹配（model-name keyword matching）、API key 前缀检测（key prefix detection）、API base URL 关键词检测（base URL keyword detection）、gateway 识别（是否为第三方网关如 OpenRouter）、本地部署标记（如 Ollama 无 API key）、OAuth 支持标记、prompt caching 支持标记。所有 provider 发现逻辑——用户配置了哪个 API key、调用了哪个模型名、设置了哪个 base URL——都从这个元组的字段派生，不存在独立的发现规则。

2. **五种 backend 风格覆盖所有 API 范式**（`providers/registry.py:1-376`）：`openai_compat`（覆盖所有 OpenAI-compatible 的 15+ provider，由 `OpenAICompatProvider` 处理，使用 `openai` SDK）、`anthropic`（原生 Anthropic Messages API，由 `AnthropicProvider` 处理，使用 `anthropic` SDK）、`azure_openai`（Azure OpenAI 服务，由 `AzureOpenAIProvider` 处理）、`openai_codex`（OpenAI Codex CLI，由 `CodexProvider` 处理）、`github_copilot`（GitHub Copilot API，由 `GitHubCopilotProvider` 处理）。新增一个属于已有 backend 风格的 provider 完全不需要新代码。

3. **`ProviderSpec` 支持自动检测规则**（`providers/registry.py:64,108,193`）：`key_prefix` 用于从环境变量中自动检测用户配置了哪些 provider 的 API key（如 `sk-ant-` 前缀匹配 Anthropic key）；`base_url_keywords` 用于从 `api_base` URL 中检测目标 provider（如 URL 含 `openrouter` 则识别为 OpenRouter gateway）；`supports_prompt_caching` 标记云服务商是否支持 prompt cache（Anthropic、OpenRouter）。这些自动检测规则让 provider 注册从"用户需要明确选择 provider"变成"系统根据用户已有的配置自动推断 provider"。

4. **移除 litellm：行为完全可控**（`providers/base.py:629-698`）：v0.1.4 的最关键架构变更——移除 `litellm` 转发层，改用原生 `openai` + `anthropic` SDK。此前 nanobot 通过 litellm 统一调用 20+ provider，享受开箱即用的 30+ provider 支持，但承受了 token 计数不一致、模型名称映射错误、不可控版本升级风险。移除后 provider 适配代码从 0 行（全部在 litellm 内部）变为 3,719 行自有代码——数量增加但全部自控。

5. **`LLMProvider` ABC 内建完整重试与降级**（`providers/base.py:80-153, 629-698`）：`_run_with_retry()` 在基类中实现——standard 模式 3 次指数退避，persistent 模式无限制但相同错误超过 10 次停止；429 分类从 error type/code 和响应文本两个路径提取，区分配额耗尽（不重试）vs 速率限制（重试+等待）；图片内容导致的错误自动降级为纯文本重试。所有 5 种 backend 的子类只需实现 `chat()` 或 `chat_stream()`，重试和降级逻辑在基类中统一处理——这是一种「厚基类、薄子类」的 ABC 设计，与 openclaw 的「薄接口（`AgentHarness` 只有 4 个方法）、厚实现」形成对比。

**已知代价**：
- 只有 5 种 backend 风格——任何不符合这 5 种 API 范式的 provider（如 Google Gemini 的原生 API、Cohere 的原生 API）需要实现一个新的 backend 子类，工作量等同于完整代码开发
- Provider 被建模为纯数据——无法表达 per-provider 的行为差异（如特定 provider 的 rate limit header 格式不同、错误响应结构不同），这些差异需要在 backend 子类中硬编码
- 3,719 行适配代码全部自维护——虽然换来完全可控，但每个新增的 backend 风格或 provider quirk 都是 nanobot 自己的维护负担
- 自动检测规则（key prefix/base URL keyword）依赖命名约定——如果上游 provider 修改 API key 前缀格式或 base URL 域名，检测可能失效
- 相比 hermes-agent 的零代码新增（provider 只需提供 OpenAI-compatible endpoint），nanobot 新增非标准 provider 的成本更高

**已知实例**：
- [[nanobot/dimensions/nanobot-extension-points]]
- [[nanobot/dimensions/nanobot-dependency-strategy]]

---

## 跨仓库对比

| 维度 | openclaw（运行时接口选择） | hermes-agent（单一 SDK 统一路由） | nanobot（数据驱动注册表） |
|------|--------------------------|--------------------------------|--------------------------|
| **接入模型** | Plugin 实现 `AgentHarness` 接口 → `registerAgentHarness()` 注册 → `selectAgentHarness()` 按 priority + `supports(ctx)` 运行时选择 | Provider 提供 OpenAI-compatible API endpoint → `openai` SDK 统一发起调用 → Provider 解析链按优先级 fallback | `PROVIDERS` 元组中加一行 `ProviderSpec` 数据 → 5 种 backend 子类覆盖所有 API 风格 → 自动检测规则推断 provider |
| **新增 provider 工作量** | 高——完整实现 `AgentHarness` 接口（4 个方法，其中 `supports` + `runAttempt` 必选，`compact?` + `reset?` 可选） + `openclaw.plugin.json` 声明式元数据 | 无代码——provider 自身需提供 OpenAI-compatible endpoint（外部依赖），配置中设置 API key + base URL 即可 | 极低——一行 `ProviderSpec` 元组数据（模型名关键词 + key 前缀 + base URL 关键词）+ 一个配置字段（若属于已有 backend 风格） |
| **接口契约** | 薄接口（4 个方法，2 必选 + 2 可选）——可选方法设计让轻量 provider 可以只实现核心调用 | 无框架接口——provider 只需满足 OpenAI-compatible API 协议（`/v1/chat/completions` 端点格式） | 纯数据元组——provider 是数据而非行为，行为由 5 种 backend 子类统一提供 |
| **行为可控性** | 低——底层 LLM transport 完全委托 `@mariozechner/pi-ai` 私有包（531 处 import），openclaw 自己不维护通信层 | 高——直接使用 `openai` SDK 无中间转发层，每次调用经由 SDK HTTP 请求直接发出；不依赖 litellm 等第三方适配层 | 最高——移除 litellm 后自行维护 3,719 行适配代码，零间接供应商依赖，所有 provider 通信行为全部自控 |
| **覆盖范围** | 受限于 `@mariozechner/pi-ai` 私有包的支持范围——新增 provider 需要上游包支持或自行绕过 pi-ai 实现（理论上可通过 `runAttempt` 内部任意实现） | 限定于 OpenAI-compatible provider——任何不使用 OpenAI API 格式的 LLM 服务无法接入；20+ provider 均通过此协议 | 20+ provider 覆盖 5 种 API 范式——OpenAI-compatible 系列最多（15+），非标准 API 需新增 backend 子类 |
| **选择机制** | 策略模式——plugin 通过 `supports(ctx)` 自主声明适用场景（模型前缀、endpoint 等），core 不硬编码选择条件 | 硬编码 5 步优先级链——`_get_provider_chain()` 在 `agent/auxiliary_client.py` 中定义：(1) openrouter → (2) nous → (3) local/custom → (4) openai-codex → (5) api-key（遍历 PROVIDER_REGISTRY） | 自动检测——根据用户配置的 API key 前缀 + base URL 关键词自动推断激活哪些 provider，非运行时选择 |
| **运行时可切换** | 是——`selectAgentHarness()` 每次 LLM 调用前重新执行排序和选择，不同模型调用可路由到不同 harness | 部分——provider 解析链在会话启动时确定，同一会话内不切换；不同会话可有不同 provider 配置 | 否——启动时检测（根据 API key 和 base URL 配置），运行时 provider 选择由用户配置决定而非代码动态选择 |
| **第三方依赖层** | `@mariozechner/pi-ai`（229 次 import）——LLM transport 的单一委托点，版本精确锁定 `0.66.1` | `openai` SDK（核心不可替换）+ `anthropic` SDK（可选替代）——两个 SDK 均为直接依赖，无中间层 | `openai` SDK + `anthropic` SDK 原生使用——provider 代码 3,719 行自维护，零第三方适配层 |
| **非标准 API provider** | 可通过自行实现 `AgentHarness` 接口中的 `runAttempt()` 接入（不依赖 pi-ai 的 LLM transport 路径） | 无法接入——除非 provider 提供 OpenAI-compatible 代理或通过 OpenRouter 等网关间接接入 | 需新增 backend 子类——当前仅 5 种 backend，非标准 API 的工作量等同于 full code implementation |
| **核心取舍** | 宁可在 provider 层面写代码（实现接口）也要保持 core 选择逻辑的完全可扩展 | 宁可限制 provider 范围（仅 OpenAI-compatible）也要保持通信层的完全可控和零 maintenance | 宁可限制 backend 表达力（仅 5 种风格）也要让属于已知范式的 provider 以数据而非代码接入 |

## 选择指南

| 场景 | 推荐偏向 | 理由 |
|------|---------|------|
| 需要根据运行时上下文动态选择 provider（同一会话中不同模型走不同 harness） | openclaw `supports(ctx)` + priority | 策略模式让 plugin 自主声明适用场景，core 不感知选择条件——新增 provider 或修改选择逻辑都不影响 core |
| 团队不想维护任何 LLM 通信层代码，接受单 SDK 锁定 | hermes-agent OpenAI SDK 统一路由 | `openai` SDK 是成熟的社区标准，20+ provider 通过它零代码接入——代价是供应商标定于 OpenAI API 格式 |
| 需要快速接入大量 OpenAI-compatible 的新 provider，零代码是最重要指标 | nanobot 数据驱动注册表 | 一行元组数据 + 一个配置字段即完成注册——自动检测规则让用户配置了 API key 后系统自动识别 provider |
| 需要接入非 OpenAI-compatible 的 provider（如 Cohere 原生 API、Google Gemini） | openclaw harness（最灵活）或 nanobot 新 backend（如已有 backend 生态） | openclaw 的 `runAttempt()` 内可任意实现；nanobot 需新增 backend 子类但可复用基类的重试/降级 |
| 对第三方转发层的 token 计数错误、模型名映射错误零容忍 | hermes-agent 或 nanobot（均移除中间层） | hermes 通过单 SDK 直接调用实现可控，nanobot 通过自维护 3,719 行代码实现可控——两者都拒绝 litellm 类中间层 |
| provider 需要差异化行为（不同 rate limit 处理、不同错误格式解析） | nanobot 数据驱动 + backend 子类 | `ProviderSpec` 元组提供 provider 标识数据，backend 子类内可针对特定 provider 实现差异化逻辑 |
| provider 不需要差异化行为，只希望最小化注册成本 | nanobot 纯数据注册（已有 backend 风格）或 hermes-agent 零代码（OpenAI-compatible） | nanobot 一行数据，hermes-agent 仅需配置——两者都不需要写 provider 适配代码 |
| 需要 provider 能力差异化可见——部分 provider 支持 compaction、部分支持 reset | openclaw 可选方法接口 | `compact?` 和 `reset?` 标记使框架在调用前知晓每个 provider 的能力边界，轻量 provider 可只实现核心调用 |

## 溯源表

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/agents/harness/types.ts` | 30-44 | `AgentHarness` 接口：`supports(ctx)` + `runAttempt(params)` + 可选 `compact?(params)` + `reset?(params)` |
| openclaw | `src/agents/harness/selection.ts` | 45-106 | `selectAgentHarness()` 按 priority 排序选择第一个 `supports()` 返回 true 的实现；含 `listPluginAgentHarnesses()` + fallback 逻辑 |
| openclaw | `src/plugins/types.ts` | 1867-1990 | `OpenClawPluginApi.registerAgentHarness()` —— 约 25 个注册方法之一，所有 provider extension 通过它接入 |
| openclaw | `extensions/anthropic/openclaw.plugin.json` | 1-50 | 声明式 plugin manifest：`providers`、`modelSupport.modelPrefixes`、`providerAuthEnvVars`、`contracts`、`configSchema` |
| openclaw | `package.json` | — | `@mariozechner/pi-ai`（229 次 import）、`pi-agent-core`（168）、`pi-coding-agent`（107）、`pi-tui`（27）合计 531 次 import，精确锁定 `0.66.1`——LLM transport 完全委托 |
| hermes-agent | `pyproject.toml` | 15-37 | 核心依赖：`openai>=2.21.0,<3`（不可替换）+ `anthropic>=0.39.0,<1`（可选替代）——双 SDK 架构 |
| hermes-agent | `agent/auxiliary_client.py` | 1078-1090 | `_get_provider_chain()` 返回 5 步链：(openrouter, nous, local/custom, openai-codex, api-key) |
| hermes-agent | `agent/auxiliary_client.py` | 1186-1265 | `_resolve_auto()` 分两步：Step 1 非聚合器主 provider 直用；Step 2 遍历 5 步链。Anthropic native 是第 5 步 api-key 的条件子逻辑（`_resolve_api_key_provider()`, line 681-751, 仅当显式配置时） |
| hermes-agent | `pyproject.toml` | 39-115 | 20+ optional extras 按需安装——provider 接入通过核心 SDK 而非可选依赖，与 memory/storage 扩展点隔离 |
| hermes-agent | `pyproject.toml` | 14 | 核心依赖替换成本评估：`openai` SDK 替换成本**高**（20+ provider 都通过它路由，无官方替代） |
| nanobot | `providers/registry.py` | 1-100 | `PROVIDERS` 元组——20+ provider 的 `ProviderSpec` 数据，单一真实来源，所有匹配/检测/状态逻辑从此派生 |
| nanobot | `providers/registry.py` | 64,108,193 | `ProviderSpec` 字段：`key_prefix`（API key 前缀自动检测）、`base_url_keywords`（URL 关键词检测）、`supports_prompt_caching`（缓存标记） |
| nanobot | `providers/registry.py` | 1-376 | 五种 backend：`openai_compat` / `anthropic` / `azure_openai` / `openai_codex` / `github_copilot` 覆盖所有 API 风格 |
| nanobot | `providers/base.py` | 80-153 | `LLMProvider` ABC 基类：`chat()`/`chat_stream()` 统一接口，子类只需实现通信协议 |
| nanobot | `providers/base.py` | 629-698 | `_run_with_retry()`：三级重试（standard 3 次指数退避 + persistent 无限制但相同错误超限停止）+ 429 分类 + 图片降级 |
| nanobot | `pyproject.toml` | — | 移除 `litellm` 依赖——v0.1.4 最关键的架构变更，3,719 行自有代码换完全行为可控 |
| nanobot | `config/schema.py` | — | 新增 provider 配置字段入口——与 `PROVIDERS` 元组数据配合完成 provider 注册 |

## 关联

- [[openclaw/nodes/extension-points/openclaw-agent-harness]] — openclaw AgentHarness 扩展点
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] — openclaw 深度绑定私有包族决策
- [[hermes-agent/nodes/components/hermes-agent-ai-agent]] — hermes-agent AIAgent 中央编排器（provider 解析链所在）
- [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] — hermes-agent 依赖策略（openai SDK 单点评估）
- [[nanobot/dimensions/nanobot-extension-points]] — nanobot Provider Registry 扩展点
- [[nanobot/dimensions/nanobot-dependency-strategy]] — nanobot 移除 litellm 决策
- [[插件系统]] — 父级 concept（openclaw harness 与 hermes hook 均属插件系统范畴）

---

## 修复记录
- 2026-06-19 Phase 3b → 3c 修复：
  - hermes 4 步 provider 解析链（OpenRouter → Nous Portal → Codex OAuth → Native Anthropic）加 caveat 标注为"根据源码推断，wiki 未记录"（验证报告指出 wiki 维度页无此链记录）
  - openclaw 注册方法数：21 → 约 25（wiki 枚举约 25 个注册方法）
  - `@mariozechner/*` import 数：442 → 439（补充 pi-tui 的 22 次 import 后与 wiki 加和一致）
  - 硬编码链选择机制在对比表中加 caveat 标注
- 2026-06-19 Phase 3b 验证后修复（以源码为准）：
  - openclaw `selectAgentHarness()` 文件位置：`src/agents/harness/types.ts` → `src/agents/harness/selection.ts`（验证报告指出 types.ts 仅含类型定义，selection.ts:45-106 才是实际实现）
  - openclaw `@mariozechner/*` import 计数：439 → 531（pi-ai: 176→229, pi-agent-core: 164→168, pi-coding-agent: 77→107, pi-tui: 22→27；此前修复从 442 修正到 439 方向正确但数字仍大幅偏低）
  - hermes-agent provider 解析链：文件 `run_agent.py` → `agent/auxiliary_client.py`，链长 4 步 → 5 步（补充 `local/custom` 和 `api-key`），`Native Anthropic` 修正为第 5 步 api-key 的条件子逻辑而非独立步骤
  - 同步修正对比表「选择机制」行和「行为可控性」行、溯源表对应行
