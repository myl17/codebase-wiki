---
type: concept
concept: provider-abstraction-pattern
problem: 如何抽象 Anthropic、OpenAI、Bedrock 等多个 LLM Provider 的 API 差异、认证方式和故障模式
concerns: [适配器设计模式, 认证管理复杂度, 故障切换策略]
repos: [nanobot, hermes-agent, openclaw, deepagents, codex-main]
generated: 2026-06-25
---

# Provider 抽象模式

## 核心问题

每多支持一个 LLM Provider，Agent 框架就需要处理一组指数增长的差异：请求格式（OpenAI chat completions vs Anthropic Messages vs Bedrock Converse）、响应解析（tool call 的字段结构各不相同）、认证方式（API key vs OAuth device code vs AWS IAM vs PKCE）、流式语义（SSE vs streaming JSON Lines vs binary frames）和故障模型（rate limit 的响应格式、retry-after 的位置、quota 错误的字段名）。

这个问题的核心张力不在于"能不能适配"，而在于**适配器采用什么设计模式**。ABC（抽象基类）强制接口契约但限制灵活性——每个新 provider 必须继承基类，而不同 provider 的请求/响应格式可能无法用统一接口表达。函数式模块允许每个 provider 有自己的转换函数集，但缺乏类型约束，调用方需要记住哪个 provider 用哪个函数。配置驱动枚举（api_mode + transport type 查表）将选择逻辑集中化，但新 transport 需要修改枚举定义和路由逻辑。

认证管理是第二个张力。最简单的方案是环境变量（API key），但生产环境需要多 key 轮换、冷却追踪（某 key 被 rate limit 后暂时绕过）、OAuth 刷新和 AWS IAM 角色链。认证管理的复杂度直接决定了故障切换的可用性——如果冷却信息不持久化，进程重启后所有 key 重新进入可用池，导致重复触发 rate limit。

故障切换是第三个张力。naive failover 是线性链条（A 失败 → B → C），但冷却感知的 failover 需要追踪每个 provider/key 的健康状态，并用 probing（定期尝试恢复冷却的 provider）避免永久绕过。

## 关切

- **适配器设计模式**：ABC 继承 vs 函数式模块 vs 配置驱动 api_mode 枚举。哪种模式在 provider 数量增长到 10+ 时仍可维护？添加新 transport 是否需要修改核心路由逻辑？
- **认证管理复杂度**：环境变量 vs 多 key 轮换 vs OAuth PKCE vs AWS IAM。认证凭据是否持久化？冷却状态是否跨进程重启保持？合成认证（插件提供凭据）如何集成？
- **故障切换策略**：线性 fallback vs 冷却感知 failover vs probing 恢复。失败类型如何分类（transient vs non-transient）？Retry-after 是否被解析和遵守？

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/provider-system]]
**解法**：LLMProvider ABC + 提供商注册表 + 自动匹配，以 OpenAI 兼容 API 为统一格式。
**实现**：`LLMProvider` ABC 定义 `chat()` / `chat_stream()` 接口，标准化 `LLMResponse`（含 error_status_code/error_kind/error_type/error_code/error_should_retry）和 `ToolCallRequest`（含 to_openai_tool_call() 转换）。智能重试：区分 transient（429/5xx/timeout/connection）和 non-transient 错误，支持 persistent 模式（无限重试 60s 上限）和 standard 模式（3 次指数退避）。429 语义分析区分 rate_limit（可重试）和 insufficient_quota（不可重试）。Retry-After 多格式解析。Provider 自动匹配按 model 名称关键词路由。^[nanobot/providers/base.py:18-68, 334-354, 532-607, 629-698; nanobot/config/schema.py:218-281]
**权衡**：ABC 模式接口约束最清晰——标准化错误类型让调用方统一处理。但 OpenAI 兼容 API 为统一格式隐式限定了 provider 选择——非 OpenAI 兼容的原生 API（如 Anthropic Messages、Bedrock Converse）需要额外的转换层；认证管理最简（仅 API key/env var），无多 key 轮换、无冷却追踪、无 OAuth。

### hermes-agent
来源：[[repos/hermes-agent/entities/model-adapters]]、[[repos/hermes-agent/entities/provider-registry]]
**解法**：函数式适配器模块 + api_mode 枚举路由 + HermesOverlay 数据驱动 provider 注册 + CredentialPool 多 key 轮换。
**实现**：四种 api_mode（chat_completions / anthropic_messages / codex_responses / bedrock_converse）由 provider 名称 + URL 自动检测。每个适配器是独立函数式模块：Anthropic 适配器转换 tools 格式 + normalize response（含 thinking/content blocks）+ 每模型输出限制；Bedrock 适配器用 boto3 SDK 直调 Converse API + 自动发现模型列表 + AWS 凭证链（IAM/SSO/env/instance metadata）。HermesOverlay 元数据定义每个 provider 的 transport type 和 auth type。CredentialPool 多 key round-robin 轮换 + 速率限制感知选择。NousRateGuard 检查 `x-ratelimit-*` 响应头。OAuth device code + PKCE 支持。25 个注册 Provider。^[agent/anthropic_adapter.py:243-1380; agent/bedrock_adapter.py:61-839; hermes_cli/providers.py:33-149; agent/credential_pool.py; run_agent.py:690-709]
**权衡**：Provider 覆盖面最广（25+）+ 认证模式最丰富（API key/OAuth device code/OAuth external/external process）。函数式适配器灵活但类型契约弱——每个适配器有自己的函数签名，调用方需根据 api_mode 选择不同函数。CredentialPool 是唯一支持多 key 轮换的方案。但故障切换弱——无冷却持久化、无 probing 恢复、无 fallback 链。

### deepagents
来源：[[repos/deepagents/entities/model-resolution]]
**解法**：统一的 `resolve_model()` 入口 + provider 前缀特例处理 + OpenRouter 归属头自动注入 + 模型标识符提取/匹配工具。
**实现**：`resolve_model()` 按优先级处理：BaseChatModel 实例直通 → `openai:` 前缀启用 Responses API（`use_responses_api=True`） → `openrouter:` 前缀检查版本（>=0.2.0）并注入 `HTTP-Referer`/`X-Title` 归属头 → 其他 provider:model 通过 `init_chat_model` 通用解析。OpenRouter 归属头仅在用户未通过环境变量 `OPENROUTER_APP_URL`/`OPENROUTER_APP_TITLE` 覆盖时才注入 SDK 默认值。`get_model_identifier()` 通过 `model_dump()` 序列化后查找 `model_name` 或 `model` 字段，适配不同 provider 的字段名差异。`model_matches_spec()` 支持精确匹配和 `provider:model` 格式的 model_name 部分匹配。无认证管理（依赖环境变量），无故障切换。 ^[deepagents/_models.py:72-96, 30-47, 50-69, 99-113, 116-140]
**权衡**：最简洁——单一函数入口 + 前缀路由，无注册表、无认证层、无故障切换。添加新 provider 只需依赖 `init_chat_model` 的通用解析。OpenRouter 归属头自动注入是细节但有价值的用户体验优化。但功能最弱——无多 key 轮换、无冷却追踪、无 failover 链、无 OAuth——完全依赖环境变量和上游库的默认行为。适合作为 SDK 层的轻量模型解析，而非平台级的 provider 管理。

### codex-main

来源：[[repos/codex-main/entities/model-provider]]
**解法**：`ModelProvider` trait + `ProviderCapabilities` 能力上限 + `create_model_provider` 工厂 + 独立 `auth` 模块。
**实现**：
- `ModelProvider` trait 为所有 LLM 后端提供统一抽象，实现者需提供 `info()` 描述元数据 ^[codex-rs/model-provider/src/provider.rs:95-100]
- `ProviderCapabilities` 声明 Provider 支持的功能上限（namespace_tools, image_generation, web_search），上层可禁用但不应超出 ^[codex-rs/model-provider/src/provider.rs:28-33]
- `create_model_provider` 工厂根据配置动态选择 OpenAI/Bedrock/ChatGPT 后端 ^[codex-rs/model-provider/src/provider.rs:19]
- `auth` 模块将认证逻辑与 Provider 分离，`auth_manager_for_provider` 按 Provider 类型选择认证方式 ^[codex-rs/model-provider/src/auth.rs:17]
- 预定义特殊用途默认模型：`DEFAULT_APPROVAL_REVIEW_PREFERRED_MODEL`（codex-auto-review）、`DEFAULT_MEMORY_EXTRACTION_PREFERRED_MODEL`（gpt-5.4-mini） ^[codex-rs/model-provider/src/provider.rs:84-92]
**权衡**：Trait 抽象提供清晰的接口契约（与 nanobot 的 ABC 类似），`ProviderCapabilities` 的能力上限声明避免了客户端错误暴露不存在的功能。认证分离设计降低耦合但增加了调用路径。

## 对比
| 框架 | 适配器设计模式 | 认证管理复杂度 | 故障切换策略 |
|------|------|------|------|
| nanobot | ABC + 注册表，OpenAI 兼容为统一格式 | 最简——仅 API key/env var | 智能重试（transient 分类 + Retry-After 解析），无 failover 链 |
| hermes-agent | 函数式模块 + api_mode 枚举，25+ provider | 最丰富——多 key 轮换 + OAuth PKCE + 企业凭证链 | 弱——无冷却持久化，无 failover 链 |
| openclaw | 配置驱动注册表，依赖 OpenAI 兼容 SDK | 4 种认证 + 磁盘持久化 + 合成认证 | 最成熟——冷却感知 + probing 恢复 + 持久化 cooling state |
| deepagents | 前缀路由——单一 `resolve_model()` 入口，provider 特例处理 | 最简——仅环境变量 | 无故障切换 |
| codex-main | Trait 抽象 + ProviderCapabilities 能力声明的统一接口 | API key + 独立 auth 模块分离认证逻辑 | 弱——无冷却持久化，无 failover 链 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 codex-main（ModelProvider trait + ProviderCapabilities 能力上限 + 独立 auth 模块）
