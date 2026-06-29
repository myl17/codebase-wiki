---
type: entity
repo: openclaw
slug: model-configuration
problem: "如何管理多个 AI provider 的模型配置、认证凭据、故障切换和冷却策略？"
generated: 2026-06-25
source_files:
  - src/agents/models-config.ts
  - src/agents/model-auth.ts
  - src/agents/model-fallback.ts
  - src/agents/auth-profiles.ts
---

# Model Configuration

**代码位置**：`src/agents/models-config.ts`、`src/agents/model-auth.ts`、`src/agents/model-fallback.ts`
**这个模块解决什么问题**：
- 实现层：通过配置驱动的 provider 注册表 + 四种认证模式 + 带冷却策略的故障切换链管理所有 AI 模型
- 问题层：如何管理多个 AI provider 的模型配置、认证凭据、故障切换和冷却策略？
**对外暴露什么**：
- `resolveModelsConfig()` — 解析 models.json 配置，生成运行时模型目录 ^[src/agents/models-config.ts]
- `resolveProviderConfig(providerId)` — 查找 provider 配置 ^[src/agents/model-auth.ts]
- `runWithModelFallback(params)` — 文本模型故障切换主循环 ^[src/agents/model-fallback.ts:626]
- `runWithImageModelFallback(params)` — 图像模型故障切换 ^[src/agents/model-fallback.ts:904]
- `AuthProfileStore` — 认证凭据管理（api-key/oauth/token/aws-sdk） ^[src/agents/auth-profiles.ts]
- `ModelProviderAuthMode` — 认证模式联合类型 ^[src/config/types.models.ts]
- `resolveProviderSyntheticAuthWithPlugin()` — 插件提供的合成认证 ^[src/agents/model-auth.ts]
**它和谁交互**：
- 依赖 [[entities/config-system]]（从 `models` 配置段读取）
- 依赖 [[entities/plugin-system]]（provider 插件注册）
- 被 [[entities/agent-runtime]] 用于模型选择和认证
- 被 [[entities/subagent-system]] 用于孵化子 agent 时的模型规划
- 被 [[entities/cli-system]] 用于模型列表/状态命令
**为什么它是可分离的**：独立的配置解析 + 认证管理 + 故障切换模块，通过函数调用与 agent 循环交互

**关键机制**（源码可见）：
- 四种认证模式：`api-key`（静态密钥）、`oauth`（可刷新令牌）、`token`（Bearer 令牌）、`aws-sdk`（AWS 凭据链） ^[src/config/types.models.ts]
- 认证凭据存储：`auth-profiles.json` + `auth-state.json` 磁盘持久化，含冷却和失败追踪 ^[src/agents/auth-profiles.ts]
- 凭据优先级：`profile-first` | `env-first`，通过 `ProviderCredentialPrecedence` 控制 ^[src/agents/model-auth.ts]
- 故障切换链：主模型→配置降级→别名扩展→逐个尝试→全部失败时抛 `FallbackSummaryError` ^[src/agents/model-fallback.ts:374-626]
- 冷却策略：认证配置文件在失败后可进入冷却（避免浪费配额），`markAuthProfileCooldown` / `markAuthProfileFailure` ^[src/agents/auth-profiles.ts]
- Provider 规范化：自动填充缺失的 apiKey env var、规范化 Gemini 3 ID、处理 provider 别名 ^[src/agents/models-config.ts]
- 模型目录运行时：`resolveModelAsync` 从注册表查找模型，支持 fallback model 和 provider 聚合 ^[src/agents/model-catalog.runtime.ts]

**源码证据**：
- 配置解析：src/agents/models-config.ts
- 认证管理：src/agents/model-auth.ts、src/agents/model-auth-runtime-shared.ts
- 故障切换：src/agents/model-fallback.ts
- 认证配置：src/agents/auth-profiles.ts
- 模型目录：src/agents/model-catalog.runtime.ts
- 配置类型：src/config/types.models.ts、src/config/types.auth.ts

**关联 Concept**：
- [[concepts/provider-abstraction-pattern]]
