---
type: entity
repo: nanobot
slug: tool-registry
problem: 如何动态注册、发现和执行 Agent 可用的工具，支持内建工具和 MCP 扩展工具
generated: 2026-06-25
source_files:
  - nanobot/agent/tools/registry.py
  - nanobot/agent/tools/base.py
---

# Tool Registry / Base Tool

**代码位置**：`nanobot/agent/tools/registry.py`（注册中心）、`nanobot/agent/tools/base.py`（工具基类）
**这个模块解决什么问题**：
- 实现层：Tool 基类定义工具接口（名称、描述、参数 schema、验证、执行），ToolRegistry 管理工具的生命周期（注册、查找、执行、参数校验）
- 问题层：如何动态注册、发现和执行 Agent 可用的工具，支持内建工具和 MCP 扩展工具
**对外暴露什么**：`Tool` 抽象基类（nanobot/agent/tools/base.py）、`ToolRegistry` 类（nanobot/agent/tools/registry.py:8）
**它和谁交互**：
- 被 [[entities/agent-loop]] 调用（注册默认工具集，获取工具定义传给 LLM）
- 被 [[entities/agent-runner]] 调用（执行工具调用，获取工具定义）
- 被 [[entities/subagent-manager]] 调用（为子 agent 构建独立工具集）
- 被 MCP 连接器注入（通过 `register` 动态添加 MCP 工具）
**为什么它是可分离的**：独立的注册中心类，工具通过继承 Tool 基类添加，可在不同 agent 实例中拥有不同的工具集

**关键机制**（源码可见）：
- 稳定排序：`get_definitions()` 返回的 schema 列表按内建工具（字母序）在前、MCP 工具（字母序）在后排序，保证跨请求的工具顺序一致以优化 prompt cache ^[nanobot/agent/tools/registry.py:45-63]
- 参数验证链路：`prepare_call()` 先 cast 参数类型、再 validate、返回 (tool, params, error) 三元组，调用方直接判断即可 ^[nanobot/agent/tools/registry.py:65-83]
- Tool 基类定义模板：每个工具必需 `name`、`description`、`parameters` JSON Schema、`execute()` async 方法，可选 `cast_params()` 和 `validate_params()` ^[nanobot/agent/tools/base.py]

**源码证据**：
- 入口文件：nanobot/agent/tools/registry.py、nanobot/agent/tools/base.py
- 核心类型/接口定义：`class ToolRegistry` ^[nanobot/agent/tools/registry.py:8]

**关联 Concept**：
- [[concepts/tool-lifecycle-management]]
