# Concept 验证报告: plugin-subsystem-auto-discovery

**验证日期**: 2026-06-17  
**Concept 页路径**: `concept/plugin-subsystem-auto-discovery.md`  
**验证方式**: 逐条对照源码

---

## 验证总览

| 验证项 | 结论 |
|--------|------|
| openclaw `supports(ctx)` 动态调用 | 正确 |
| openclaw priority 排序逻辑 | 正确 |
| openclaw 解决的是 provider 选择而非通用 tool 发现 | 正确 |
| hermes AST 扫描使用 `ast.parse()` + 顶层扫描 | 正确 |
| hermes `discover_builtin_tools()` 调用时机 | 正确 |
| hermes 新增文件是否需要重启 | 描述准确 |
| 概念层面区分（provider 选择 vs 工具注册） | 正确 |
| 敏感度/脆弱性分析 | 正确 |

**总评**: 所有关键声明均通过源码验证，无事实错误。有两处值得标注的细节说明。

---

## 逐项验证

### 1. openclaw: `supports(ctx)` 是否真的每次请求动态调用？

**声明** (第 31 行): "每次请求都动态调用 `supports()`。这不是启动时的一次性扫描。"

**源码证据**: `selection.ts:77-85`
```typescript
const supported = pluginHarnesses
    .map((harness) => ({
      harness,
      support: harness.supports({
        provider: params.provider,
        modelId: params.modelId,
        requestedRuntime: runtime,
      }),
    }))
```

`selectAgentHarness()` 是每次请求的入口函数（被 `runAgentHarnessAttemptWithFallback` 调用，见 `selection.ts:118`）。没有缓存层，没有 memoization。每次调用都遍历全部 plugin harness 并逐个调用 `supports()`。

测试文件 `selection.test.ts:88-89` 进一步确认了动态性——同一个 harness 实例的 `supports` 根据 `ctx.provider` 返回不同结果。

**验证结论**: 正确。无缓存，每次请求都重新调用。

---

### 2. openclaw: priority 排序逻辑

**声明** (第 23 行): "按 `priority` 降序排序（priority 相同时按 harness ID 字母序保证确定性）"

**源码证据**: `selection.ts:34-43`
```typescript
function compareHarnessSupport(left, right): number {
  const priorityDelta = (right.support.priority ?? 0) - (left.support.priority ?? 0);
  if (priorityDelta !== 0) {
    return priorityDelta;
  }
  return left.harness.id.localeCompare(right.harness.id);
}
```

排序在第 94 行通过 `.toSorted(compareHarnessSupport)` 调用。逻辑：priority 高的排前（降序）；priority 相同时按 harness ID 字母序升序（`a.localeCompare(b)` 返回负数时 a 在前）。

优先级默认值 `?? 0` 意味着未指定 priority 的 harness 视为 0。

PI harness 在 `builtin-pi.ts:8` 也硬编码 priority 0，与其他未指定 priority 的 harness 同级——但它不在 plugin candidate 列表中（第 55 行注释明确：PI is intentionally not part of the plugin candidate list），仅在第 100-105 行作为 fallback 返回。

**验证结论**: 正确。但第 27 行说 PI "priority 0 的最低优先级兜底"——技术上准确，PI 的 priority 确实最低（0），但 PI 并非通过 priority 排序被选中，而是作为排序失败后的 fallback 直接返回。

---

### 3. openclaw: 解决的是 provider 选择而非通用 tool 发现

**声明** (对比表第 87 行): "运行时选择哪个 harness 处理当前请求"  
**声明** (第 100-102 行): "openclaw 的 harness 选择解决的是**多个实现竞标同一个请求**的问题...有限候选者（每个 provider 一个 harness，总数不超过两位数）"

**源码证据**: `types.ts:9-13` 的 `AgentHarnessSupportContext` 包含 `provider`、`modelId`、`requestedRuntime`——这些是 LLM API provider 级别的上下文，不是 tool 级别的。Registry 存储的是 `AgentHarness` 实例（`registry.ts:8` 为 `Map<string, RegisteredAgentHarness>`），每个 harness 代表一个 LLM backend（PI、Codex 等）。

**验证结论**: 正确。harness 选择的粒度和语义确实是 provider/runtime 选择，与 hermes 的 tool 发现属于不同层面。

---

### 4. hermes: AST 扫描是否真的用 `ast.parse()`？扫描范围是否正确？

**声明** (第 48-52 行): "核心逻辑在 `tools/registry.py:28-73`...调用 `ast.parse(source)` 解析...只扫描顶层 body，不进入函数内部"

**源码证据**: `registry.py:47-53`
```python
source = module_path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(module_path))
# ...
return any(_is_registry_register_call(stmt) for stmt in tree.body)
```

- 使用 `ast.parse()` 解析源码（第 49 行）
- 只遍历 `tree.body`，即模块的顶层语句（第 53 行）
- `_is_registry_register_call()` (第 28-38 行) 精确匹配 `ast.Expr > ast.Call > ast.Attribute(attr="register") + ast.Name(id="registry")` 的 AST 形态

**验证结论**: 正确。确实使用 `ast.parse()`，确实只扫描 `tree.body`（顶层），不递归进入函数体。

---

### 5. hermes: `discover_builtin_tools()` 调用时机

**声明** (第 71 行): "`model_tools.py:132` 在模块加载时调用 `discover_builtin_tools()`，一次性完成所有工具的发现和导入"

**源码证据**: `model_tools.py:132`
```python
discover_builtin_tools()
```

该调用位于 `model_tools.py` 的模块级作用域（第 128-132 行的 "Tool Discovery" 区块注释下，不在任何函数内）。Python 在首次 import 该模块时执行这些语句。

**验证结论**: 正确。调用发生在模块级别，即首次 `import model_tools` 时（启动时）。

---

### 6. hermes: 新增文件是否需要重启？

**声明** (第 71 行): "后续请求只从已填充的 Registry 内存中查询，不再重新扫描"

**源码证据**: `discover_builtin_tools()` 仅在 `model_tools.py` 模块级别调用一次。没有定时刷新、文件监控或按需重新扫描机制。新的 `.py` 文件在进程运行期间不会被 `glob("*.py")` 发现——因为 glob 只在函数调用时执行一次。

对比 MCP 动态工具：`registry.py:229-252` 的 `deregister()` 方法确实支持 MCP 工具的运行时增删（nuke-and-repave），但这是 MCP 独立路径（`mcp_tool.py`），不经过 AST 扫描。

**验证结论**: 描述准确。新工具文件需要进程重启才能被发现。第 109 行也已正确指出 "MCP 动态刷新是例外，走独立路径"。

---

## 细节标注

### 标注 A: `selectAgentHarness()` 的 6 步流程省略了早退路径

Concept 页描述的 6 步流程（收集 → 调用 supports → 过滤 → 排序 → 选第一个 → fallback）准确描述了 `runtime === "auto"` 的核心路径。但源码中还有两个早退路径未提及：
1. `runtime === "pi"` 时直接返回 PI（第 58-60 行）
2. `runtime !== "auto"` 时按 ID 直接查找指定 harness（第 62-75 行）

这不影响 Concept 页的准确性——因为它关注的是"自动发现/选择"机制，而早退路径是"强制指定"逻辑。属于合理的简化。

### 标注 B: PI harness 的 priority 0 角色

Concept 页说 PI "priority 0 的最低优先级兜底"（第 27 行）。技术上 PI 不在 plugin candidate 排序池中（第 55 行注释明确），而是排序失败后作为 fallback 直接返回。priority 值 0 在此场景下不参与排序比较，但语义上确实是"最低优先级"的准确表达。

---

## 结论

所有关键声明均通过源码验证。Concept 页准确描述了 openclaw 的运行时动态策略选择机制和 hermes 的启动时静态 AST 扫描机制，并正确区分了两者解决的不同层面问题（provider 选择 vs 工具注册）。无事实错误。
