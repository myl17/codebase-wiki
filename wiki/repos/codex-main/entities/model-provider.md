---
type: entity
repo: codex-main
slug: model-provider
problem: 如何抽象多个 LLM 后端为统一接口
generated: 2026-06-28
source_files:
  - codex-rs/model-provider/src/lib.rs
  - codex-rs/model-provider/src/provider.rs
  - codex-rs/model-provider/src/amazon_bedrock.rs
  - codex-rs/model-provider/src/auth.rs
---

# Model Provider

**代码位置**：codex-rs/model-provider/
**这个模块解决什么问题**：
- 实现层：通过 `ModelProvider` trait 抽象 OpenAI、Amazon Bedrock、ChatGPT 等 LLM 后端的差异，统一认证、模型发现和能力声明
- 问题层：如何抽象多个 LLM 后端为统一接口
**对外暴露什么**：
- `ModelProvider` trait：运行时 Provider 抽象，定义 info() 方法返回 Provider 元数据 ^[codex-rs/model-provider/src/provider.rs:95-100]
- `SharedModelProvider`：共享的 Provider 类型别名 ^[codex-rs/model-provider/src/provider.rs:19]
- `ProviderCapabilities`：Provider 能力声明（namespace_tools, image_generation, web_search） ^[codex-rs/model-provider/src/provider.rs:28-33]
- `ProviderAccountState`：Provider 账户状态 ^[codex-rs/model-provider/src/provider.rs:46-50]
- `create_model_provider`：工厂函数，根据配置创建对应的 Provider 实例 ^[codex-rs/model-provider/src/provider.rs:19]
- `CoreAuthProvider`：核心认证 Provider trait ^[codex-rs/model-provider/src/bearer_auth_provider.rs:10]
- `AmazonBedrockModelProvider`：Amazon Bedrock 后端实现 ^[codex-rs/model-provider/src/amazon_bedrock.rs:19]
- `auth_manager_for_provider`：Provider 认证管理器工厂 ^[codex-rs/model-provider/src/auth.rs:17]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 通过 ModelProvider 发送 API 请求）
- 依赖 [[entities/models-manager]]（Provider 使用 models-manager 获取可用模型列表）
- 与 [[entities/config-management]] 配合（Provider 配置来自 config 层）
**为什么它是可分离的**：独立的 crate，通过 trait 抽象实现多后端支持，新增 Provider 只需实现 ModelProvider trait

**关键机制**（源码可见）：
- **Provider trait 统一接口**：`ModelProvider` 是所有 LLM 后端的统一抽象，实现者需提供 info() 方法描述其元数据 ^[codex-rs/model-provider/src/provider.rs:95-100]
- **能力声明上限**：`ProviderCapabilities` 定义了 Provider 支持的最高能力边界（如 namespace_tools, web_search），上层可进一步禁用但不应超出此上限 ^[codex-rs/model-provider/src/provider.rs:28-33]
- **多后端工厂模式**：`create_model_provider` 根据配置动态选择 OpenAI/Bedrock/ChatGPT 后端 ^[codex-rs/model-provider/src/provider.rs:19]
- **认证分离**：`auth` 模块将认证逻辑从 Provider 中分离，`auth_manager_for_provider` 根据 Provider 类型返回对应的 AuthManager ^[codex-rs/model-provider/src/auth.rs:17]
- **默认模型选择**：预定义 `DEFAULT_APPROVAL_REVIEW_PREFERRED_MODEL`（codex-auto-review）、`DEFAULT_MEMORY_EXTRACTION_PREFERRED_MODEL`（gpt-5.4-mini）等特殊用途的默认模型 ^[codex-rs/model-provider/src/provider.rs:84-92]

**源码证据**：
- 入口文件：codex-rs/model-provider/src/lib.rs
- Provider trait：codex-rs/model-provider/src/provider.rs:95-100
- Provider 能力：codex-rs/model-provider/src/provider.rs:28-33
- Bedrock 实现：codex-rs/model-provider/src/amazon_bedrock.rs
