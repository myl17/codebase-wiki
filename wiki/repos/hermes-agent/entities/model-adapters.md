---
type: entity
repo: hermes-agent
slug: model-adapters
problem: 如何适配不同 AI Provider 的原生 API 格式（Anthropic Messages、AWS Bedrock Converse、OpenAI Codex），统一转换为 OpenAI chat completions 兼容格式
generated: 2026-06-25
source_files:
  - agent/anthropic_adapter.py
  - agent/bedrock_adapter.py
  - agent/auxiliary_client.py
  - agent/copilot_acp_client.py
  - agent/smart_model_routing.py
---

# 模型适配器

**代码位置**：`agent/anthropic_adapter.py`、`agent/bedrock_adapter.py`、`agent/auxiliary_client.py`
**这个模块解决什么问题**：
- 实现层：函数式模块将 Anthropic Messages API、AWS Bedrock Converse API 和 OpenAI Codex Responses API 的请求/响应格式转换为 OpenAI chat completions 兼容格式，使 Agent 核心循环可透明地使用多种 Provider 原生 API
- 问题层：如何适配不同 AI Provider 的原生 API 格式（Anthropic Messages、AWS Bedrock Converse、OpenAI Codex），统一转换为 OpenAI chat completions 兼容格式
**对外暴露什么**：Anthropic 适配器函数集（`build_anthropic_client()`、`convert_tools_to_anthropic()`、`normalize_anthropic_response()` 等）、Bedrock 适配器函数集（`convert_tools_to_converse()`、`call_converse()`、`discover_bedrock_models()` 等）、AuxiliaryClient 类（`call_llm()`、`AnthropicAuxiliaryClient`、`CodexAuxiliaryClient`）、CopilotACPClient（agent/copilot_acp_client.py:256）
**它和谁交互**：
- 依赖 [[entities/provider-registry]]（provider 选择决定使用哪个适配器）
- 被 [[entities/agent-core]] 调用（API mode 自动检测选择适配路径；auxiliary 调用通过 `call_llm()` 路由）
- 被 [[entities/context-compressor]] 调用（压缩摘要通过 `call_llm(task="compression")`）
- 被 [[entities/state-database]] 调用（session_search 通过 `async_call_llm` 摘要）
**为什么它是可分离的**：每个适配器是独立的函数式模块，通过 API mode 枚举选择；添加新 Provider 无需修改现有适配器

**关键机制**（源码可见）：
- 四种 API mode：`chat_completions`（OpenAI 兼容）、`anthropic_messages`（Anthropic 原生）、`codex_responses`（OpenAI Codex）、`bedrock_converse`（AWS Bedrock）^[run_agent.py:690-709]
- Anthropic 适配：
  - `build_anthropic_client()` 支持 API key、OAuth setup token、Claude Code credentials（`~/.claude.json`）和 Bedrock 多模式认证 ^[agent/anthropic_adapter.py:243-790]
  - `convert_tools_to_anthropic()` 将 Hermes 工具格式转为 Anthropic tool 格式 ^[agent/anthropic_adapter.py:806]
  - `normalize_anthropic_response()` 将 Anthropic response 转回 OpenAI 兼容格式，含 thinking/content blocks ^[agent/anthropic_adapter.py:1380]
  - 每模型输出限制 `_ANTHROPIC_OUTPUT_LIMITS`（从 Claude 3 Opus 的 4096 到 Opus 4.6 的 128000）^[agent/anthropic_adapter.py:43]
  - Thinking budget 支持：`THINKING_BUDGET` + `ADAPTIVE_EFFORT_MAP` ^[agent/anthropic_adapter.py:30-31]
- Bedrock 适配：
  - 使用 boto3 SDK 直接调用 Bedrock Converse API，绕过 OpenAI 兼容端点 ^[agent/bedrock_adapter.py:61-74]
  - `discover_bedrock_models()` 通过 Bedrock 控制平面自动发现模型列表 ^[agent/bedrock_adapter.py:839]
  - AWS 凭证链支持：IAM roles、SSO profiles、env vars、instance metadata ^[agent/bedrock_adapter.py]
  - 支持 Guardrails 和跨区域推理配置 ^[agent/bedrock_adapter.py]
- Auxiliary 客户端：`call_llm()` 统一路由入口，按 provider 优先级（OpenRouter > Nous Portal > Custom > Codex > Anthropic > Direct）选择客户端 ^[agent/auxiliary_client.py:2346]
- Smart Model Routing：`agent/smart_model_routing.py` 根据任务复杂度自动选择不同 tier 的模型 ^[agent/smart_model_routing.py]
- Codex 适配：`_CodexCompletionsAdapter` 将 `chat.completions.create()` 桥接到 Codex Responses streaming API ^[agent/auxiliary_client.py:261]
- Copilot ACP：`CopilotACPClient` 通过 Agent Client Protocol 与 GitHub Copilot 集成 ^[agent/copilot_acp_client.py:256]

**源码证据**：
- 入口文件：agent/anthropic_adapter.py、agent/bedrock_adapter.py、agent/auxiliary_client.py
- 核心函数：`def call_llm(task=None, *, provider=None, ...)` ^[agent/auxiliary_client.py:2346]、`def build_anthropic_client()` ^[agent/anthropic_adapter.py:243]

**关联 Concept**：
- [[concepts/provider-abstraction-pattern]]
