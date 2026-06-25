# ToolRegistry（nanobot）

## 是什么 / 边界
nanobot 的工具注册中心——`dict[name, Tool]` 的薄封装，提供 `register()`/`unregister()`/`get()`/`execute()` 四个方法。所有工具通过显式 `registry.register()` 调用注册，不做任何自动发现。

**边界**：ToolRegistry 只管理工具的注册、查找、执行。不做 AST 扫描、不做装饰器收集、不做模块自省。工具定义的生成和排序在 `get_definitions()` 中完成。

## 关键实现
- **显式注册**：`_register_default_tools()` 在 AgentLoop.__init__() 中逐一列出所有内建工具，每个新工具必须在此点名
- **定义排序**：`get_definitions()` 中 builtins 按名称排序在前，MCP 工具（`mcp_` 前缀）在后——构成 Anthropic prompt cache 的稳定前缀
- **执行前验证**：`prepare_call()` 在 tool 执行前做 `cast_params()` + `validate_params()`，返回结构化错误而非抛出异常
- **专用 Schema 类型**：`agent/tools/schema.py` 中的 `StringSchema`/`IntegerSchema`/`ObjectSchema` 等子类，非泛用 JSON Schema 库
- **MCP 注册**：MCP server 工具以 `mcp_` 前缀动态注入，AgentLoop 关闭时清理

## 设计选择记录
- **维度**：Extension Points
- **选择**：显式 `register()` 注册——不做 AST 扫描、不做装饰器发现、不做模块自省
- **替代方案**：装饰器自动收集（`@tool` 装饰器标记函数，框架扫描模块自动发现）、AST 分析（解析源码提取工具定义）
- **为什么有这个选择**：完全的确定性——不存在隐式工具被发现或遗漏的可能。每个工具在 `_register_default_tools()` 中点名，一眼可知系统有哪些工具。代价是新增工具需要手动注册，但 nanobot 定位为精简框架，工具数量可控
