# Plugin Subsystem Auto-Discovery

## 问题陈述

如何让 plugin 子系统无需手动配置即可被框架发现和使用？当插件数量增长、多个贡献者同时添加新能力时，维护中心化的插件/工具列表会成为摩擦和冲突的来源。自动发现机制让新增扩展只需要写好代码、放在正确的位置，框架自己找到它。

## 实例

### openclaw: AgentHarness 的 `supports(ctx)` + priority 排序

**所属仓库**: [[openclaw-agent-harness|Agent Harness (OpenClaw)]]  
**维度**: Extension Points  
**机制类型**: 运行时动态策略选择

**机制**

`AgentHarness` 接口（`src/agents/harness/types.ts:30-39`）定义了 `supports(ctx: AgentHarnessSupportContext): AgentHarnessSupport` 方法。每个 harness plugin 实现 `supports()`，根据请求上下文（provider、modelId、requestedRuntime）声明自己是否适用，并可选返回一个 `priority` 数值。

选择逻辑在 `selectAgentHarness()`（`src/agents/harness/selection.ts:45-106`）：
1. 收集所有已注册的 plugin harness（从全局 registry Map 中获取）
2. 对每个 harness 调用 `supports()` 传入当前请求的 provider / modelId / runtime
3. 过滤出 `supported: true` 的候选
4. 按 `priority` 降序排序（priority 相同时按 harness ID 字母序保证确定性）
5. 选择排序后的第一个
6. 如果没有匹配的 plugin harness，回退到内置的 PI harness（priority 0 的最低优先级兜底）

内置 PI harness（`src/agents/harness/builtin-pi.ts:4-11`）的 `supports()` 始终返回 `{ supported: true, priority: 0 }`，作为永远存在的保底选项。

**注册方式**：Harness 插件通过 `registerAgentHarness()`（`src/agents/harness/registry.ts:21-34`）显式注册到全局 Registry Map。新增 provider 的 harness 需要调用注册函数，但不需要修改 `selectAgentHarness()` 的选择逻辑或任何配置文件。

**调用时机**：每次请求都动态调用 `supports()`。同一个 harness 实例在不同请求中可能返回不同结果（例如根据 provider 名称判断是否匹配）。这不是启动时的一次性扫描。

**关键源码**：
- `src/agents/harness/types.ts:9-44` — `AgentHarnessSupportContext`、`AgentHarnessSupport`、`AgentHarness` 接口
- `src/agents/harness/selection.ts:77-94` — `supports()` 调用 + 过滤 + priority 排序
- `src/agents/harness/registry.ts:21-34` — `registerAgentHarness()` 全局注册
- `src/agents/harness/builtin-pi.ts:4-11` — PI harness 的兜底实现

---

### hermes: AST 扫描自动发现 `registry.register()` 顶层调用

**所属仓库**: [[hermes-tool-registry|ToolRegistry (Hermes)]]  
**维度**: Extension Points  
**机制类型**: 启动时静态代码分析

**机制**

工具注册中心通过 AST 静态分析自动发现哪些 Python 模块包含工具注册。核心逻辑在 `tools/registry.py:28-73`：

1. `_is_registry_register_call(node)`（`:28-38`）：检查一个 AST 节点是否是 `registry.register(...)` 调用表达式。精确匹配 `ast.Attribute` 且 `func.attr == "register"` 且 `func.value.id == "registry"` 的模式。

2. `_module_registers_tools(module_path)`（`:41-53`）：读取源文件，调用 `ast.parse(source)` 解析，然后检查 `tree.body`（即模块顶层语句）中是否存在 `registry.register(...)` 调用。**只扫描顶层 body，不进入函数内部**——这是刻意的设计选择，防止辅助模块中函数内部含有的 `registry.register()` 调用被误判。

3. `discover_builtin_tools(tools_dir)`（`:56-73`）：遍历 `tools/*.py` 文件，用 AST 扫描筛选出含有顶层注册调用的模块，然后通过 `importlib.import_module()` 逐一导入。导入动作触发模块顶层代码执行，从而实际调用 `registry.register()` 完成注册。

**注册方式**：新工具只需在 Python 文件的顶层写一个 `registry.register()` 调用（通常在文件末尾），不需要修改任何现有文件或配置。例如 `tools/code_execution_tool.py` 末尾：
```python
from tools.registry import registry, tool_error
registry.register(
    name="execute_code",
    toolset="code_execution",
    schema=EXECUTE_CODE_SCHEMA,
    handler=...,
    check_fn=check_sandbox_requirements,
    emoji="🐍",
    max_result_size_chars=100_000,
)
```

**调用时机**：`model_tools.py:132` 在模块加载时调用 `discover_builtin_tools()`，一次性完成所有工具的发现和导入。后续请求只从已填充的 Registry 内存中查询，不再重新扫描。

**关键源码**：
- `tools/registry.py:28-38` — `_is_registry_register_call()` AST 节点匹配
- `tools/registry.py:41-53` — `_module_registers_tools()` ast.parse + tree.body 扫描
- `tools/registry.py:56-73` — `discover_builtin_tools()` 文件遍历 + importlib 导入
- `model_tools.py:132` — 触发发现时机

---

### nanobot: pkgutil 包扫描 + entry_points 外部插件（Channel 发现）

**所属仓库**: [[nanobot|nanobot]]
**维度**: Extension Points
**机制类型**: 启动时包结构扫描 + Python 标准插件分发

**机制**

Channel 的自动发现采用双路线策略。核心逻辑在 `nanobot/channels/registry.py:17-71`：

1. `discover_channel_names()`（`:17-25`）：使用 `pkgutil.iter_modules()` 扫描 `nanobot.channels` 包的目录结构，列出所有 `.py` 模块名。排除 `_INTERNAL = frozenset({"base", "manager", "registry"})` 中的基础设施模块。**只读目录结构，不导入任何模块**——与 hermes 的 AST 扫描同样追求零副作用发现。

2. `load_channel_class(module_name)`（`:28-37`）：对通过筛选的模块名执行 `importlib.import_module()`，然后遍历模块中的属性，通过 `isinstance(obj, type) and issubclass(obj, BaseChannel)` 找到第一个 `BaseChannel` 子类并返回。**约定是"模块文件中定义一个 BaseChannel 子类"**，而非"模块文件中有特定的注册函数调用"。

3. `discover_plugins()`（`:40-51`）：通过 `importlib.metadata.entry_points(group="nanobot.channels")` 发现通过 pip 安装的外部插件。这是 Python 生态的标准插件分发机制——第三方包在 `pyproject.toml` 中声明 `[project.entry-points."nanobot.channels"]` 即可被框架发现，无需框架维护任何外部插件目录。

4. `discover_all()`（`:54-71`）：合并内置和外部 channel——`{**external, **builtin}`。**内置优先于同名外部插件**：如果外部插件试图注册与内置 channel 同名的名称，会被警告并忽略，保证核心功能不被第三方覆盖。

**发现目标 vs hermes**

nanobot Channel 发现的是**类型层级关系**（谁是 `BaseChannel` 的子类），而非**函数调用模式**（谁在顶层写了 `registry.register()`）。这是一个本质差异：Channel 的"注册"不是通过调用某个注册函数完成，而是通过继承基类隐式声明——框架通过 `issubclass` 来识别注册意图。这比 AST 扫描更鲁棒：不依赖特定代码格式或命名规范，只依赖 Python 类型系统本身。

**注册方式**：新增内置 Channel 只需在 `nanobot/channels/` 下创建新 `.py` 文件，定义一个 `BaseChannel` 子类。不需要在任何地方调用注册函数，不需要修改现有文件。外部 Channel 通过 entry_points 分发，`pip install` 即可被框架发现。

**调用时机**：启动时一次性扫描 pkgutil + 查询 entry_points 后导入。后续请求直接从已填充的内存 dict 中查询，不再重新扫描。

**关键源码**：
- `nanobot/channels/registry.py:17-25` — `discover_channel_names()` pkgutil 包扫描
- `nanobot/channels/registry.py:28-37` — `load_channel_class()` BaseChannel 子类识别（issubclass）
- `nanobot/channels/registry.py:40-51` — `discover_plugins()` entry_points 外部插件
- `nanobot/channels/registry.py:54-71` — `discover_all()` 合并 + 内置优先

---

### nanobot: 显式 `register()` 确定性注册（Tool 注册）

**所属仓库**: [[nanobot|nanobot]]
**维度**: Extension Points
**机制类型**: 显式声明式注册（反自动发现，完全确定性）

**机制**

nanobot 的 Tool 注册采用最直接的方式：在代码中显式列出所有可用工具，逐个调用 `register()`。这是 hermes AST 扫描的**对立方案**——可以视为自动发现光谱上的"零自动发现"端点。

`ToolRegistry`（`nanobot/agent/tools/registry.py:8-20`）提供简单的 `register(tool: Tool)` API——按 `tool.name` 存入内部 dict。不需要扫描、不需要约定、不需要继承特定基类。

`_register_default_tools()`（`nanobot/agent/loop.py:229-243`）是注册的唯一入口：

```python
self.tools.register(ReadFileTool(workspace=..., allowed_dir=..., extra_allowed_dirs=...))
for cls in (WriteFileTool, EditFileTool, ListDirTool):
    self.tools.register(cls(workspace=..., allowed_dir=...))
for cls in (GlobTool, GrepTool):
    self.tools.register(cls(workspace=..., allowed_dir=...))
if self.exec_config.enable:
    self.tools.register(ExecTool(working_dir=..., timeout=..., ...))
```

每个工具在注册时完成参数化（workspace、allowed_dir、timeout、sandbox 等），注册与配置一体化。

**与 hermes AST 扫描的直接对立**

| | hermes AST 扫描 | nanobot 显式 register() |
|---|---|---|
| 发现方式 | 扫描源码找 `registry.register()` 顶层调用 | 无发现——所有注册写在一处 |
| 新增工具 | 创建 .py 文件，顶层写注册调用 | 修改 `_register_default_tools()`，加一行 |
| 是否修改现有文件 | 不需要 | 需要 |
| 工具数量多时的维护成本 | 低（零冲突） | 高（单一函数增长、合并冲突） |
| 工具数量少时的清晰度 | 稍低（需理解 AST 扫描约定） | 高（直接可见，代码即文档） |
| 确定性 | 取决于文件系统的文件列表 | 完全确定——不依赖文件系统内容 |

这不是一个"哪个更好"的问题——这是**规模决定策略**的经典案例。hermes 有 30+ 工具，集中维护会频繁冲突；nanobot 有 ~7 个工具，分散到独立文件反而降低可发现性和可读性。两个方案在各自的规模下都是正确选择。

**关键源码**：
- `nanobot/agent/tools/registry.py:8-20` — `ToolRegistry.register()` API
- `nanobot/agent/loop.py:229-243` — `_register_default_tools()` 显式注册入口

---

## 对比分析

四个实例覆盖了插件自动发现光谱上的四个不同位置：从完全显式（nanobot Tool）到包结构约定（nanobot Channel），从源码级扫描（hermes）到运行时动态决策（openclaw）。它们在不同维度上有本质差异。

| 维度 | openclaw `supports()` + priority | hermes AST 扫描 | nanobot pkgutil + entry_points | nanobot 显式 register() |
|------|------|------|------|------|
| **解决什么问题** | 运行时选择哪个 harness 处理当前请求 | 启动时发现哪些工具模块存在 | 启动时发现内置与外部 Channel 实现 | 启动时注册所有可用工具（不发现） |
| **时机** | 每次请求动态决策 | 启动时一次性扫描 | 启动时一次性扫描 | 启动时一次性执行 |
| **技法** | 策略模式：逐个询问 `supports()` | 静态代码分析：`ast.parse()` 匹配语法模式 | pkgutil 读包目录 + issubclass 基类识别 + entry_points | 直接实例化并调用 `register()` |
| **发现层级** | 不发现——动态选择 | 源码内容级（AST） | 包结构级（目录）+ 类型层级（issubclass） | 不发现——显式枚举 |
| **决策依据** | 运行时上下文（provider、modelId） | 源代码中是否存在顶层 `registry.register()` | 目录下有哪些 .py 文件 + 谁继承了 BaseChannel | 开发者维护的显式工具列表 |
| **注册动作** | 显式调用 `registerAgentHarness()` | importlib 导入触发 `registry.register()` 执行 | importlib 导入后 issubclass 识别 BaseChannel 子类 | 显式 `self.tools.register(Tool(...))` |
| **新增扩展** | 实现 `supports()` + 调用注册函数 | 创建 .py 文件，顶层写 `registry.register()` | 内置：创建 .py + 定义 BaseChannel 子类；外部：pip install | 修改 `_register_default_tools()` 加一行 |
| **外部/三方扩展** | 不支持 | 不支持（仅内置 tools/ 目录） | entry_points 原生支持 pip 分发 | 不支持（需改源码） |
| **失败模式** | 无匹配时回退到 PI harness | AST 扫描不到则模块被静默跳过 | 内置优先；外部同名被忽略（警告） | 不改代码则工具不存在（无失败） |
| **可扩展点数量** | 少量（每个 provider 一个 harness） | 大量（30+ 工具模块） | 中等（10+ Channel 类型） | 少量（~7 个工具，增长有限） |
| **适合规模** | O(10) | O(100) | O(10)-O(100) | O(10) |

## 设计权衡

### 自动发现是光谱，不是二元选择

四个实例揭示的核心理念是：插件自动发现不是一个"有/无"的开关，而是一个连续光谱。光谱的一端是 nanobot Tool 的"零自动发现"——所有工具在 `_register_default_tools()` 中显式枚举；另一端是 openclaw 的"每次请求动态决策"——运行时根据上下文选出最适合的 harness。中间是 hermes 的源码级静态扫描和 nanobot Channel 的包结构级扫描。

光谱上的位置主要由两个因素决定：**扩展点数量**和**扩展的内外部属性**。扩展点多时，发现机制往自动化方向移动（hermes）；扩展点少时，显式枚举的清晰度收益超过自动化节省的维护成本（nanobot Tool）。面向三方扩展时，entry_points 是 Python 生态的标准答案（nanobot Channel）。只在内部使用时，pkgutil 或 AST 扫描都足够好。

### 三个发现层级：包结构级 → 源码内容级 → 类型层级

nanobot Channel 引入了 hermes 未覆盖的新维度：**发现层级**。

- **包结构级**（pkgutil）：`pkgutil.iter_modules()` 只读目录下的 .py 文件列表，不读文件内容。这是最"轻"的发现——不需要解析 AST，不需要导入模块，不需要理解代码。约定是"一个文件 = 一个扩展"。
- **源码内容级**（AST）：hermes 的 `ast.parse()` 读文件内容但只匹配语法模式，不执行代码。约定的粒度更细——"一个文件中包含 `registry.register(...)` 顶层调用"。
- **类型层级**（issubclass）：nanobot Channel 在导入模块后用 `issubclass` 识别 BaseChannel 子类。约定是"文件中的某个类继承了 BaseChannel"。这比 AST 更鲁棒——不关心具体调用了什么函数、怎么命名，只关心类型关系。即使模块因为导入别名、封装函数等导致 AST 模式不匹配，issubclass 仍然能正确识别。
- **不发现**：nanobot Tool 和 openclaw 不涉及发现——前者显式枚举，后者运行时动态选择。

选择哪一层级取决于**你需要多大程度的脆性约定**。包结构级约定最粗、最鲁棒，但表达能力最弱（无法在一个文件里放多个扩展）；源码内容级（AST）最精细，但最容易因为代码风格变化而断裂；类型层级在两者之间——既允许一个文件放多个类，又不依赖具体调用形式。

### 动态 vs 静态

openclaw 选择动态的原因是需求本身是动态的——同一个 harness 在不同请求中可能返回不同的 `supported` 值（取决于用户选择的 provider / modelId），这不是启动时就能确定的。

hermes 和 nanobot Channel 都是启动时一次性静态发现——因为工具列表和 Channel 类型列表在进程生命周期内不变化。hermes 用 `ast.parse()` 先筛出真正注册工具的模块再导入，避免导入每个 .py 文件；nanobot Channel 用 `pkgutil.iter_modules()` 先列出模块名再逐个导入，同样追求零副作用发现。

nanobot Tool 是启动时一次性执行，但不存在"发现"动作——它是一个确定性的代码序列。

### 复杂度来源

openclaw 的复杂度在 `selectAgentHarness()` 中：需要遍历、过滤、排序、处理 fallback 策略。但 harness 开发者侧的复杂度低——实现 `supports()` 返回一个简单的 `{ supported: true, priority: 100 }` 即可。

hermes 的复杂度在 AST 匹配逻辑中：必须精确匹配 `registry.register(...)` 的语法模式，只扫描顶层，排除函数内的调用。但如果 Python 代码格式或风格略有差异（例如用 `import tools.registry as reg; reg.register()`），AST 扫描就会遗漏。这是一种**隐式约定**，工具开发者必须遵守"在顶层用 `registry.register()` 这个精确形式"的规范。

nanobot Channel 的复杂度在两个发现路线的合并逻辑中：内置优先于外部，同名时外部被静默降级为警告。但核心发现逻辑（pkgutil + issubclass + entry_points）都依赖 Python 标准库，不需要维护 AST 匹配规则。pkgutil 和 issubclass 的鲁棒性意味着几乎不会因为代码风格变化而遗漏扩展——只要文件存在且定义了正确的子类就行。

nanobot Tool 几乎无复杂度——唯一需要维护的是 `_register_default_tools()` 函数本身，保持列表顺序和参数正确即可。

### 外部可扩展性：entry_points 的独特价值

nanobot Channel 是四个实例中**唯一支持第三方外部扩展**的方案。`entry_points(group="nanobot.channels")` 让任何 pip 可安装的包都能声明自己是 nanobot channel——框架只查询 entry_points 名称空间，不扫描用户文件系统上的任意路径。

内置优先（`{**external, **builtin}`）的设计保证了安全性：外部插件不能 shadow 内置 channel，避免恶意 pip 包覆盖核心行为。而 hermes 和 nanobot Tool 的外部扩展都需要修改源码或 monkey-patch，不是设计意图内的扩展路径。

### 适合什么场景

- **用 openclaw 模式**（动态策略选择）：候选实现少（O(10)），需要根据运行时上下文做决策，存在多个实现可能都满足条件需要排优先级，需要 fallback 机制。
- **用 hermes 模式**（静态约定扫描）：候选模块多（O(100)），注册逻辑是纯粹声明式的，在启动时就能确定全貌，希望新增模块的摩擦降到"只加文件不改任何其他文件"。
- **用 nanobot Channel 模式**（pkgutil + issubclass + entry_points）：候选模块中等（O(10)-O(100)），约定是"类型继承"而非"函数调用"，需要支持三方 pip 插件。当扩展的注册意图通过基类继承就能表达时，issubclass 比 AST 扫描更鲁棒。
- **用 nanobot Tool 模式**（显式注册）：候选模块少（O(10)），每个扩展的初始化参数各不相同（workspace、timeout、sandbox 等），代码即文档的清晰度高于自动发现节省的维护成本。

这些方案不是互斥的——同一个系统可以组合使用。例如在 nanobot 内部，Channel 使用 pkgutil + entry_points 做自动发现，Tool 使用显式 register() 做确定性注册——两种策略在同一仓库内按各自规模选择各自最合适的方案。hermes 的 AST 扫描负责发现所有工具，而工具内部可能需要类似 openclaw 的策略模式来根据请求上下文选择不同的执行后端。

## 关联概念

- **Plugin Registry 模式**：openclaw 的 `registerAgentHarness()` 全局 Map、hermes 的 `ToolRegistry` 单例、nanobot 的 `ToolRegistry` dict 都是中心化注册中心。自动发现解决的是"谁往注册中心写数据"，注册中心本身解决的是"如何高效查询"。
- **约定优于配置（Convention over Configuration）**：hermes 的顶层 `registry.register()` 和 nanobot Channel 的"定义 BaseChannel 子类"都是纯编码约定——没有配置文件声明该模块包含扩展，全凭位置惯例和代码结构被框架发现。后者比前者的约定更粗粒度、更鲁棒。
- **策略模式（Strategy Pattern）**：openclaw 的 `supports()` + priority 排序是策略模式的变体——每个 harness 是一个策略，`supports()` 是策略的适用性声明，`selectAgentHarness()` 是上下文驱动的策略选择器。
- **Python entry_points（插件分发）**：nanobot Channel 的 `importlib.metadata.entry_points` 是 Python 生态的标准插件发现机制。与 pkgutil 互补——pkgutil 发现内置模块，entry_points 发现外部包。
