# ToolRegistry — 工具注册中心（Hermes Agent）

## 是什么 / 边界

ToolRegistry 是全局单例的工具注册中心，通过 AST 扫描自动发现工具注册调用，收集所有工具的 schema 和 handler，支持按 toolset 分组、MCP 动态刷新、运行时自定义 toolset 创建。

它不执行工具，只负责发现、注册、调度；不管理工具的执行权限（那是 ApprovalSystem 的职责）；不做工具逻辑，只是工具的目录和分发器。

## 关键实现

- 注册中心单例：`tools/registry.py:100-159`，RLock 线程安全
- AST 自动发现：`tools/registry.py:28-73`，扫描 `registry.register()` 顶层调用
- 自动导入：`model_tools.py:1-80` 导入所有自注册工具模块
- Toolset 系统：`toolsets.py:68-397`
  - `_HERMES_CORE_TOOLS`（`:31-63`）：核心工具清单，所有平台共享
  - `resolve_toolset()`（`:447-497`）：递归解析 includes 链，带去重和循环检测
  - `create_custom_toolset()`（`:613-632`）：运行时创建自定义 toolset
- MCP 动态刷新：工具名冲突时 MCP server 覆盖同名工具（`tools/registry.py:190-199`）

注册方式（任何 Python 文件顶层）：
```python
registry.register(
    name="my_tool",
    toolset="custom",
    schema={...},
    handler=my_handler,
    check_fn=lambda: True,
)
```

## 设计选择记录

- **维度**：Architecture
- **选择**：通过 AST 扫描自动发现工具注册，新工具只需在文件顶层调用 registry.register()
- **替代方案**：手动维护工具列表，新工具需要修改中央配置文件
- **为什么有这个选择**：AST 扫描让添加新工具的摩擦降到最低，不需要修改任何现有文件；代价是依赖静态分析约定（只扫描顶层调用），有一定的隐式假设

---

- **维度**：Architecture
- **选择**：ToolRegistry 作为全局单例，RLock 保护，所有工具共享一个实例
- **替代方案**：每个 AIAgent 实例有独立的工具注册中心
- **为什么有这个选择**：工具集在进程内是稳定的，全局单例避免重复初始化开销；MCP 动态刷新需要一个权威的注册中心，分散实例难以同步

---

- **维度**：Extension Points
- **选择**：Toolset 用 includes 递归组合，平台专用 toolset 从 _HERMES_CORE_TOOLS 继承
- **替代方案**：每个平台完全独立定义自己的工具列表，不共享核心
- **为什么有这个选择**：核心工具列表改一处所有平台自动获得；includes 组合避免工具名称在各平台重复列举；去重和循环检测确保组合安全
