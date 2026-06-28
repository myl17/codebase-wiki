---
type: entity
repo: hermes-agent
slug: provider-registry
problem: 如何管理 20+ AI Provider 的注册、标准化和模型发现，支持多种认证方式和 provider 间 failover
generated: 2026-06-25
source_files:
  - hermes_cli/providers.py
  - hermes_cli/models.py
  - hermes_cli/model_switch.py
  - hermes_cli/model_normalize.py
  - agent/model_metadata.py
  - agent/credentials_pool.py
  - agent/nous_rate_guard.py
  - agent/rate_limit_tracker.py
  - agent/models_dev.py
  - agent/insights.py
---

# Provider 注册与模型管理

**代码位置**：`hermes_cli/providers.py`、`hermes_cli/models.py`、`agent/credential_pool.py`
**这个模块解决什么问题**：
- 实现层：`HermesOverlay` 元数据（transport type, auth type, base_url）+ `ProviderDef` 合并定义 20+ Provider；`CANONICAL_PROVIDERS` 列表驱动交互式选择 UI；`model_metadata.py` 使用 models.dev API 和 ollama 获取模型上下文长度；credential_pool 管理多 key 轮换和速率限制
- 问题层：如何管理 20+ AI Provider 的注册、标准化和模型发现，支持多种认证方式和 provider 间 failover
**对外暴露什么**：
- `HERMES_OVERLAYS` dict（hermes_cli/providers.py:45-149）覆盖了 20+ provider 的传输类型、认证方式和回退 URL
- `CANONICAL_PROVIDERS` 列表（hermes_cli/models.py:531）定义交互式界面中的 provider 选择项
- `fetch_model_metadata()` / `estimate_tokens_rough()` / `get_cached_context_length()`（agent/model_metadata.py）
- `CredentialPool` 类（agent/credential_pool.py）、`NousRateGuard`（agent/nous_rate_guard.py）
**它和谁交互**：
- 依赖 [[entities/model-adapters]]（transport type 决定使用哪个适配器）
- 依赖 [[entities/config-system]]（provider 配置回退）
- 被 [[entities/cli-system]] 调用（`hermes model` 交互选择）
- 被 [[entities/agent-core]] 调用（获取 provider 配置和模型信息）
- 被 [[entities/web-server]] 调用（`/api/providers/oauth/*` OAuth 流）
**为什么它是可分离的**：Provider 定义是通过 dict/overlay 数据驱动，添加新 provider 只需添加配置项而非修改代码

**关键机制**（源码可见）：
- HermesOverlay 元数据：每个 provider 的传输类型（`openai_chat` / `anthropic_messages` / `codex_responses` / `bedrock_converse`）和认证类型（`api_key` / `oauth_device_code` / `oauth_external` / `external_process`）^[hermes_cli/providers.py:33-149]
- Provider 别名映射：`human-friendly → canonical`（`openai → openrouter`、`claude → anthropic`、`aws → bedrock`、`copilot → github-copilot`）^[hermes_cli/providers.py:170-275]
- Model 标准化：`normalize_model_for_provider()` 根据 provider 自动添加/移除模型前缀 ^[hermes_cli/model_normalize.py]
- 25 个注册 Provider：Nous Portal、OpenRouter、Anthropic、OpenAI Codex、Xiaomi MiMo、Qwen OAuth、GitHub Copilot、Copilot ACP、HuggingFace、Google AI Studio、DeepSeek、xAI、Z.AI/GLM、Kimi/Moonshot、MiniMax、Alibaba Cloud、AWS Bedrock、Copilot Browser、Local、LM Studio、Ollama Cloud、Custom ^[hermes_cli/models.py:531-724]
- 模型上下文发现：`fetch_model_metadata()` 从 models.dev API 获取，`query_ollama_num_ctx()` 从本地 Ollama 获取；结果缓存到 `~/.hermes/model_metadata.json` ^[agent/model_metadata.py:439-712]
- 多 Key 凭证池：`CredentialPool` 管理多个 API key，支持 round-robin 轮换和速率限制感知的选择 ^[agent/credential_pool.py]
- 速率限制跟踪：`RateLimitTracker` 跟踪每个 key 的剩余限额；`NousRateGuard` 检查 `x-ratelimit-*` 响应头 ^[agent/rate_limit_tracker.py, agent/nous_rate_guard.py]
- 使用分析引擎：`InsightsEngine` 分析 SQLite 会话历史，生成 token 消耗、成本估算、工具使用、活跃模式、model/platform breakdown 报告 ^[agent/insights.py:93-728]

**源码证据**：
- 入口文件：hermes_cli/providers.py、hermes_cli/models.py、agent/model_metadata.py
- 核心类型：`@dataclass class HermesOverlay` ^[hermes_cli/providers.py:33]、`CANONICAL_PROVIDERS` ^[hermes_cli/models.py:531]

**关联 Concept**：
- [[concepts/provider-abstraction-pattern]]
