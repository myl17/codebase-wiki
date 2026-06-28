---
type: entity
repo: nanobot
slug: config-system
problem: 如何管理 AI Agent 的多维度运行时配置（模型、工具、Channel、提供方、Cron 等），支持文件和环境的组合加载
generated: 2026-06-25
source_files:
  - nanobot/config/schema.py
  - nanobot/config/loader.py
  - nanobot/config/paths.py
---

# Config System

**代码位置**：`nanobot/config/`
**这个模块解决什么问题**：
- 实现层：Pydantic-based 配置 schema（Config/AgentsConfig/ProvidersConfig/ChannelsConfig/ToolsConfig），JSON 文件加载 + 环境变量覆盖（`NANOBOT_` 前缀），提供方自动匹配逻辑
- 问题层：如何管理 AI Agent 的多维度运行时配置，支持文件和环境的组合加载
**对外暴露什么**：`Config` 根配置类（nanobot/config/schema.py:203）、`AgentDefaults`（nanobot/config/schema.py:62）、`load_config()`（nanobot/config/loader.py）、`ConfigPaths`（nanobot/config/paths.py）
**它和谁交互**：
- 被 [[entities/nanobot-facade]] 调用（`from_config()` 加载配置创建实例）
- 被 [[entities/cli-system]] 调用（CLI 启动时加载配置）
- 被 [[entities/provider-system]] 调用（通过 `get_provider()` / `get_api_key()` 获取提供商配置）
- 被 [[entities/agent-loop]] 调用（读取工具配置如 web/exec/mcp）
- 被 [[entities/channel-system]] 调用（读取 channels 配置判断启用状态）
**为什么它是可分离的**：独立包，纯 schema + loader，与任何运行时逻辑无耦合

**关键机制**（源码可见）：
- 环境变量嵌套映射：`NANOBOT_AGENTS__DEFAULTS__MODEL` 映射到 `agents.defaults.model`，用 `__` 做层级分隔 ^[nanobot/config/schema.py:313]
- 提供方自动匹配：`_match_provider()` 按三层优先级——provider 前缀直接匹配 > model 关键词匹配 > 本地 provider fallback，无有效 API key 时跳过 ^[nanobot/config/schema.py:218-281]
- 配置校验：`load_config()` 做版本检查、不同 provider 的特殊要求验证（如 Azure 需要 api_key 和 api_base）^[nanobot/config/loader.py]
- JSON5 支持：允许配置文件中使用注释和尾部逗号，增加人工可编辑性 ^[nanobot/config/loader.py]

**源码证据**：
- 入口文件：nanobot/config/schema.py、nanobot/config/loader.py
- 核心类型/接口定义：`class Config(BaseSettings)` ^[nanobot/config/schema.py:203]

**关联 Concept**：
- [[concepts/configuration-management]]
