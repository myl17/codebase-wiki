---
type: entity
repo: deepagents
slug: model-resolution
problem: 如何将不同格式的模型标识符（字符串、provider:model、已初始化实例）统一解析为可用的 BaseChatModel 实例
generated: 2026-06-28
source_files:
  - deepagents/_models.py
---

# Model Resolution

**代码位置**：`deepagents/_models.py`
**这个模块解决什么问题**：
- 实现层：提供 `resolve_model()` 函数统一解析多种模型输入格式（BaseChatModel 实例、`openai:`前缀、`openrouter:`前缀、其他 provider:model 字符串），以及 `get_model_identifier()`、`model_matches_spec()` 等模型检查和版本验证工具
- 问题层：如何在接受多种模型指定方式的 API 中，一致地将用户输入转换为可用的模型实例，同时处理不同 provider 的特殊需求（如 OpenAI Responses API、OpenRouter 归属头）

**对外暴露什么**：
- `resolve_model(model)` -- `deepagents/_models.py:72`
- `get_model_identifier(model)` -- `deepagents/_models.py:99`
- `model_matches_spec(model, spec)` -- `deepagents/_models.py:116`
- `check_openrouter_version()` -- `deepagents/_models.py:50`
- `OPENROUTER_MIN_VERSION` 常量 -- `deepagents/_models.py:13`

**它和谁交互**：
- 被 [[entities/agent-graph-assembly]] 用于解析 `create_deep_agent()` 的 model 参数和子代理的 model 参数
- 依赖 `langchain.chat_models.init_chat_model` 解析 provider:model 字符串
- 与 OpenRouter SDK 版本检查交互

**为什么它是可分离的**：`_models.py` 是纯工具模块——无状态、无副作用，只做模型标识符的解析和比较。可以在 SDK 和 CLI 中复用。

**关键机制**（源码可见）：
- BaseChatModel 直通：如果 model 已是 BaseChatModel 实例，直接返回 ^[deepagents/_models.py:89-90]
- OpenAI 特殊处理：`openai:` 前缀的模型默认启用 Responses API（`use_responses_api=True`）^[deepagents/_models.py:91-92]
- OpenRouter 归属头：自动注入 `HTTP-Referer` 和 `X-Title` 头用于 OpenRouter 归属，除非用户已通过环境变量覆盖 ^[deepagents/_models.py:30-47]
- OpenRouter 版本检查：在解析前检查 `langchain-openrouter >= 0.2.0` ^[deepagents/_models.py:50-69]
- 模型标识符提取：通过 `model_dump()` 序列化后查找 `model_name` 或 `model` 字段，适配不同 provider 的字段名差异 ^[deepagents/_models.py:99-113]
- 模型匹配比较：支持精确匹配和 `provider:model` 格式的 model_name 部分匹配 ^[deepagents/_models.py:116-140]

**源码证据**：
- 入口文件：`deepagents/_models.py`
- 核心函数定义：`deepagents/_models.py:72`

**关联 Concept**：
- [[concepts/provider-abstraction-pattern]]
