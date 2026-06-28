---
type: entity
repo: nanobot
slug: cli-system
problem: 如何提供交互式的 Agent 命令行界面，支持对话、流式输出、模型选择和 onboarding
generated: 2026-06-25
source_files:
  - nanobot/cli/commands.py
  - nanobot/cli/stream.py
  - nanobot/cli/onboard.py
  - nanobot/cli/models.py
  - nanobot/__main__.py
---

# CLI System

**代码位置**：`nanobot/cli/`
**这个模块解决什么问题**：
- 实现层：基于 cyclopts 的命令行应用，提供交互式对话 REPL、流式输出（rich 渲染 Markdown）、首次运行 onboarding 向导、模型列表查询
- 问题层：如何提供交互式的 Agent 命令行界面，支持对话、流式输出、模型选择和 onboarding
**对外暴露什么**：`app()` 入口（nanobot/cli/commands.py）、`setup_app()` 配置函数、`StreamRenderer`（nanobot/cli/stream.py）
**它和谁交互**：
- 依赖 [[entities/agent-loop]]（通过 MessageBus 发送用户输入和接收响应）
- 依赖 [[entities/nanobot-facade]]（使用 Nanobot.from_config() 创建实例）
- 依赖 [[entities/channel-system]]（CLI 作为特殊 channel="cli" 工作）
- 依赖 [[entities/config-system]]（配置加载和保存）
**为什么它是可分离的**：CLI 是独立入口点，通过 `python -m nanobot` 启动，与核心逻辑在 bus 层解耦

**关键机制**（源码可见）：
- Cyclopts 命令架构：使用 cyclopts 框架定义子命令（`run` 交互模式、`onboard` 向导、`models` 查询、`channel-login`），支持 POSIX 风格的参数格式和帮助自动生成 ^[nanobot/cli/commands.py]
- Rich 流式渲染：`StreamRenderer` 使用 rich 库渲染 Markdown 流式输出，支持表格、代码块、列表的实时格式化 ^[nanobot/cli/stream.py]
- Onboarding 向导：交互式配置生成器，引导用户选择提供方、输入 API key、选择模型、设置 workspace，自动生成 `config.json` ^[nanobot/cli/onboard.py]
- 模型自动补全：`nanobot/cli/models.py` 提供模型列表查询和自动补全 ^[nanobot/cli/models.py]

**源码证据**：
- 入口文件：nanobot/cli/commands.py、nanobot/__main__.py
- 核心类型/接口定义：`def app()` ^[nanobot/cli/commands.py]
