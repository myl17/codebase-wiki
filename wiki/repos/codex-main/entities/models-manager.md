---
type: entity
repo: codex-main
slug: models-manager
problem: 如何管理模型目录、预设和动态刷新
generated: 2026-06-28
source_files:
  - codex-rs/models-manager/src/manager.rs
---

# Models Manager

**代码位置**：codex-rs/models-manager/
**这个模块解决什么问题**：
- 实现层：通过 `SharedModelsManager` 统一管理多个 Provider 的模型目录、预设和刷新策略，支持客户端缓存和定期更新
- 问题层：如何管理模型目录、预设和动态刷新
**对外暴露什么**：
- `SharedModelsManager`：共享模型管理器，维护模型目录和预设的中央注册表 ^[codex-rs/models-manager/src/manager.rs]
- `OpenAiModelsManager`：OpenAI 兼容 API 的模型管理实现 ^[codex-rs/models-manager/src/manager.rs]
- `StaticModelsManager`：静态模型列表管理器（用于不支持动态发现的 Provider） ^[codex-rs/models-manager/src/manager.rs]
- `RefreshStrategy`：模型列表刷新策略枚举 ^[codex-rs/models-manager/src/manager.rs:74]
- `ModelInfo`：模型信息结构体 ^[codex-rs/protocol/src/openai_models.rs]
- `ModelPreset`：模型预设（组合选定模型 + 参数预设） ^[codex-rs/protocol/src/openai_models.rs]
**它和谁交互**：
- 被 [[entities/model-provider]] 调用（Provider 通过 ModelsManager 获取可用模型列表）
- 被 [[entities/core-agent-loop]] 使用（Agent 通过 ModelsManager 选择模型）
- 与 [[entities/config-management]] 配合（模型预设可来自配置层）
**为什么它是可分离的**：独立的 crate，将模型目录管理与 Provider 实现解耦，支持统一的多 Provider 模型视图

**关键机制**（源码可见）：
- **多 Provider 模型聚合**：`SharedModelsManager` 聚合所有已配置 Provider 的模型列表，提供统一的查询接口 ^[codex-rs/models-manager/src/manager.rs]
- **刷新策略**：`RefreshStrategy` 控制模型列表的更新策略（启动时加载、定期刷新、手动触发） ^[codex-rs/models-manager/src/manager.rs:74]
- **静态与动态并存**：`StaticModelsManager` 为不支持 API 动态发现模型的 Provider（如本地 Ollama、LM Studio）提供硬编码模型列表；`OpenAiModelsManager` 通过 API 动态拉取 ^[codex-rs/models-manager/src/manager.rs]
- **预设系统**：`ModelPreset` 将模型选择与参数（temperature、max_tokens 等）组合为命名预设，方便用户切换 ^[codex-rs/protocol/src/openai_models.rs]

**源码证据**：
- 入口文件：codex-rs/models-manager/src/manager.rs
- 刷新策略：codex-rs/models-manager/src/manager.rs:74
