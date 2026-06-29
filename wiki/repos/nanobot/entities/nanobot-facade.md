---
type: entity
repo: nanobot
slug: nanobot-facade
problem: 如何为程序化调用者提供简洁的 Python SDK 接口，隐藏 Agent 内部复杂性
generated: 2026-06-25
source_files:
  - nanobot/nanobot.py
  - nanobot/__init__.py
---

# Nanobot Facade

**代码位置**：`nanobot/nanobot.py`、`nanobot/__init__.py`
**这个模块解决什么问题**：
- 实现层：`Nanobot` 类提供 `from_config()` 工厂方法和 `run()` 方法，将 AgentLoop 内部细节封装为简洁的异步 API，返回 `RunResult` 包含 content/tools_used/messages
- 问题层：如何为程序化调用者提供简洁的 Python SDK 接口，隐藏 Agent 内部复杂性
**对外暴露什么**：`Nanobot` 类（nanobot/nanobot.py:23）、`RunResult` dataclass（nanobot/nanobot.py:14）、`__version__`（nanobot/__init__.py:27）
**它和谁交互**：
- 依赖 [[entities/agent-loop]]（通过 `from_config()` 创建 loop 实例并包装）
- 依赖 [[entities/config-system]]（加载配置）
- 依赖 [[entities/provider-system]]（`_make_provider()` 创建 provider）
- 依赖 [[entities/message-bus]]（创建 MessageBus 并传给 loop）
- 被外部 Python 代码调用（作为 SDK 入口）
**为什么它是可分离的**：轻量 facade 层，仅做依赖组装和方法委托，不包含业务逻辑

**关键机制**（源码可见）：
- 工厂方法组装：`from_config()` 集中处理配置加载、provider 创建、MessageBus 创建、AgentLoop 初始化，一条调用链完成全部组装 ^[nanobot/nanobot.py:36-86]
- Hook 注入：`run()` 支持每次调用传入自定义 hooks 列表，在 `_extra_hooks` 中临时替换，run 完成后恢复 ^[nanobot/nanobot.py:88-114]
- Provider 自动匹配：`_make_provider()` 根据注册表中的 backend 字段选择具体 provider 类，对 Azure 做特殊校验（必须提供 api_key 和 api_base）^[nanobot/nanobot.py:117-177]
- Session Key 隔离：默认使用 `sdk:default` 作为 session key，不同 SDK 调用者可指定不同 key 获得独立对话 ^[nanobot/nanobot.py:92]

**源码证据**：
- 入口文件：nanobot/nanobot.py、nanobot/__init__.py
- 核心类型/接口定义：`class Nanobot` ^[nanobot/nanobot.py:23]、`@dataclass class RunResult` ^[nanobot/nanobot.py:14]
