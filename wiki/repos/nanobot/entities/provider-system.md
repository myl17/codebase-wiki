---
type: entity
repo: nanobot
slug: provider-system
problem: 如何抽象 LLM 提供商差异，支持 Anthropic/OpenAI/Azure 等多种 API 的统一调用和自动匹配
generated: 2026-06-25
source_files:
  - nanobot/providers/base.py
  - nanobot/providers/registry.py
  - nanobot/providers/anthropic_provider.py
  - nanobot/providers/openai_compat_provider.py
  - nanobot/providers/azure_openai_provider.py
  - nanobot/providers/openai_codex_provider.py
  - nanobot/providers/github_copilot_provider.py
  - nanobot/providers/openai_responses/converters.py
  - nanobot/providers/openai_responses/parsing.py
  - nanobot/providers/transcription.py
---

# Provider System

**代码位置**：`nanobot/providers/`
**这个模块解决什么问题**：
- 实现层：LLMProvider 抽象基类定义 `chat()` / `chat_stream()` 接口，自带 `LLMResponse` / `ToolCallRequest` 标准化类型、重试策略、错误分类；具体实现覆盖 Anthropic、OpenAI-compat、Azure OpenAI、OpenAI Codex、GitHub Copilot
- 问题层：如何抽象 LLM 提供商差异，支持多种 API 的统一调用和自动匹配
**对外暴露什么**：`LLMProvider` 抽象类（nanobot/providers/base.py:80）、`LLMResponse` dataclass（nanobot/providers/base.py:48）、`ToolCallRequest` dataclass（nanobot/providers/base.py:18）、`GenerationSettings` dataclass（nanobot/providers/base.py:72）、Provider Registry（nanobot/providers/registry.py）
**它和谁交互**：
- 被 [[entities/agent-loop]] 调用（作为核心 LLM 调用入口）
- 被 [[entities/agent-runner]] 调用（通过 provider 做 chat/chat_stream）
- 被 [[entities/nanobot-facade]] 调用（`from_config` 工厂选择 provider）
- 依赖 [[entities/config-system]]（从 config 读取 API key、base URL、模型名）
**为什么它是可分离的**：统一接口 + provider registry 模式，添加新提供商只需实现 chat() 方法并注册

**关键机制**（源码可见）：
- 标准化类型：`ToolCallRequest` 统一工具调用格式，`to_openai_tool_call()` 转换为 OpenAI 兼容格式；`LLMResponse` 包含结构化错误元数据（`error_status_code`、`error_kind`、`error_type`、`error_code`、`error_should_retry`）^[nanobot/providers/base.py:18-68]
- 智能重试：`_run_with_retry()` 区分 transient（`429`/`5xx`/timeout/connection）和非 transient 错误，支持 "persistent" 模式（无限重试 60s 上限，相同错误 10 次停止）和 "standard" 模式（3 次指数退避）^[nanobot/providers/base.py:629-698]
- 429 语义分析：从响应中提取 `error.type`/`error.code`，区分 rate_limit（可重试）和 insufficient_quota（不可重试）^[nanobot/providers/base.py:334-354]
- Retry-After 解析：支持多种格式（header `retry-after`/`retry-after-ms`、响应正文 `retry after Xs`、`wait Xs before retry`）^[nanobot/providers/base.py:532-607]
- 提供商自动匹配：按 model 名称关键词匹配（如 "anthropic/claude" -> AnthropicProvider），支持 provider prefix 直接路由 ^[nanobot/config/schema.py:218-281]
- 角色交替修正：`_enforce_role_alternation()` 合并连续同角色消息、移除末尾 assistant 消息，适配不支持 prefill 的提供商 ^[nanobot/providers/base.py:356-390]

**源码证据**：
- 入口文件：nanobot/providers/base.py
- 核心类型/接口定义：`class LLMProvider` ^[nanobot/providers/base.py:80]

**关联 Concept**：
- [[concepts/provider-abstraction-pattern]]
