# Context Engine：Singleton vs Pluggable

## 问题陈述

Context Engine 控制对话上下文的完整生命周期——组装 prompt、摄入新消息、压缩历史、重写 transcript。它直接操作 agent 的对话状态，是 agent harness 中最需要"安全"的扩展点之一。两个仓库都面临同一个设计问题：**如何在保证状态安全（同一时间只有一个 engine 操纵对话历史）的同时，允许第三方替换默认实现？** 它们的答案走了两条不同的路。

## openclaw：独占槽位 + 所有者访问控制

### 源码验证

openclaw 的 Context Engine 是一个 TypeScript interface，定义在 `src/context-engine/types.ts:150-281`。接口范围很广——核心必须实现的方法是 `assemble`、`ingest`、`compact`（3 个），可选方法包括 `maintain`、`bootstrap`、`afterTurn`、`prepareSubagentSpawn`、`onSubagentEnded`、`dispose` 等，还覆盖了 subagent 生命周期、prompt-cache 可观察性（`runtimeContext.promptCache`）、transcript 重写（`runtimeContext.rewriteTranscriptEntries`）。这不是一个轻量插件——它是一个深度嵌入运行时每个角落的基础设施组件。

注册机制在 `src/context-engine/registry.ts:309-395`。核心数据结构是 process-global 的 `Map<string, { factory, owner }>`：

```typescript
// registry.ts:345-368 — registerContextEngineForOwner
export function registerContextEngineForOwner(
  id: string, factory: ContextEngineFactory, owner: string,
  opts?: RegisterContextEngineForOwnerOptions,
): ContextEngineRegistrationResult {
  const existing = registry.get(id);
  if (id === defaultSlotIdForKey("contextEngine") && owner !== CORE_CONTEXT_ENGINE_OWNER) {
    return { ok: false, existingOwner: CORE_CONTEXT_ENGINE_OWNER };
  }
  if (existing && existing.owner !== owner) {
    return { ok: false, existingOwner: existing.owner };
  }
  if (existing && opts?.allowSameOwnerRefresh !== true) {
    return { ok: false, existingOwner: existing.owner };
  }
  registry.set(id, { factory, owner });
  return { ok: true };
}
```

三层保护：
1. **默认槽位 ID（`"legacy"`）只能由 core 所有者注册**——第三方 SDK 无法篡改核心默认值。
2. **同一 ID 只能由一个 owner 持有**——不同 owner 不可相互覆盖。
3. **同一 owner 刷新需要显式声明 `allowSameOwnerRefresh`**——防止无意覆盖。

第三方注册入口 `registerContextEngine(id, factory)` 始终以 `"public-sdk"` 身份调用，无权抢占 core 持有的默认 ID。

解析逻辑在 `registry.ts:411-427`。`resolveContextEngine(config)` 先读 `config.plugins.slots.contextEngine`（显式覆盖），回退到默认槽位值 `"legacy"`。这意味着**只有被选中的那一个 engine 会被实例化和调用**——Map 里可以注册多个，但同一时刻只有一个处于激活状态。

### 设计逻辑

openclaw 把 Context Engine 当作**状态基础设施**，类似于数据库连接池或文件系统——多个竞争者同时操作同一份对话历史必然冲突。独占槽位的设计不是为了"阻止创新"，而是承认一个事实：Context Engine 的 `maintain`、`compact`、`transcriptRewrite` 操作都是对共享状态的不可逆修改。让两个 engine 交替执行这些操作等同于让两个进程同时写同一个文件。

所有者（`owner`）的概念比单纯"第一注册者胜出"更进一步。它区分了 core（框架作者）、plugin（特定插件）和 public-sdk（任意第三方），让访问控制有层次。core 可以锁定默认实现不被第三方覆盖，而插件作者可以安全地刷新自己的注册——这是一个经过深思熟虑的权限模型，不是简单的互斥锁。

## hermes：文件系统发现 + 声明式切换

### 源码验证

hermes 的 ContextEngine 是一个 Python ABC，定义在 `agent/context_engine.py:32-185`。接口范围比 openclaw 窄：

- **必须实现**：`name`（属性）、`update_from_response(usage)`、`should_compress(prompt_tokens)`、`compress(messages, current_tokens)`
- **可选实现**（8 个）：`should_compress_preflight`、`on_session_start`、`on_session_end`、`on_session_reset`（会话生命周期）、`get_tool_schemas` / `handle_tool_call`（暴露工具给 agent）、`get_status`、`update_model`

接口聚焦在"何时压缩 + 怎么压缩"上，会话生命周期和工具暴露是可选扩展。这不是一个全栈生命周期管理器——它是一个可以附带额外能力的压缩策略。

插件发现逻辑在 `plugins/context_engine/__init__.py:33-76`：

```python
def discover_context_engines() -> List[Tuple[str, str, bool]]:
    """Scan plugins/context_engine/ for available engines."""
    for child in sorted(_CONTEXT_ENGINE_PLUGINS_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith(("_", ".")):
            continue
        init_file = child / "__init__.py"
        if not init_file.exists():
            continue
        # Read description from plugin.yaml
        # Quick availability check via is_available()
```

目录即接口：`plugins/context_engine/<name>/__init__.py` 存在就视为一个 engine 候选项。加载逻辑（`_load_engine_from_dir`，第 100-196 行）支持两种模式：
1. **`register(ctx)` 函数**：模块导出一个函数，调用 `ctx.register_context_engine(engine)` 注册实例。
2. **Fallback 扫描**：直接找 `ContextEngine` 的子类并实例化。

激活在 `run_agent.py:1432-1489`：
```
config.yaml → context.engine: "lcm"
  → load_context_engine("lcm")
  → fallback to hermes_cli.plugins.get_plugin_context_engine()
  → fallback to built-in "compressor"
```

### 设计逻辑

hermes 把 Context Engine 当作**可替换的策略模块**。目录扫描让发现过程对用户透明——放一个文件夹进去，`hermes plugins list` 就能看到它。`plugin.yaml` 提供人类可读的描述，`is_available()` 做轻量级前置检查。所有这些设计都指向一个目标：降低第三方编写和分发 Context Engine 的摩擦。

声明式切换（`context.engine: "lcm"`）让切换成本降到了修改一行 YAML。不需要重启进程，不需要重新编译，不需要理解插件的注册 API。

## 对比分析

| 维度 | openclaw | hermes |
|------|----------|--------|
| **注册方式** | 程序化 API（`registerContextEngine`） | 文件系统发现（目录扫描） |
| **接口广度** | 10+ 方法，覆盖完整会话生命周期 | 4 个抽象方法，聚焦压缩决策 |
| **状态安全** | 所有者访问控制 + 三层保护 | 配置选一，加载时选一 |
| **切换方式** | `config.plugins.slots.contextEngine` | `config.yaml` → `context.engine` |
| **发现机制** | 显式注册，需知道 ID | 隐式发现，扫描目录 |
| **第三方扩展开销** | 编写插件代码 + 调用注册 API | 创建目录 + `__init__.py` + 改配置 |
| **多实现并存** | Map 中可以注册多个，只有一个激活 | 目录中可以有多个，只有一个激活 |
| **防止核心被覆盖** | owner 机制锁定默认 ID | 回退链保证 compressor 为最终兜底 |

## 状态冲突风险分析

两个仓库都正确识别了核心风险——**多个 Context Engine 交替操作同一会话状态会导致不可恢复的数据损坏**——并都实现了"同一时间只有一个激活"的保证。但它们在"如何防止无意激活"上走了不同路径。

openclaw 的防线更靠近**编译时/注册时**：`registerContextEngineForOwner` 在注册阶段就阻止了大部分冲突场景。一个第三方插件无法"不小心"覆盖核心实现——API 直接返回 `{ ok: false }`。风险主要在运行时配置层面：如果用户在 `plugins.slots.contextEngine` 中写了一个未注册的 ID，`resolveContextEngine` 会抛出异常。

hermes 的防线更靠近**加载时/运行时**：配置文件指定 engine 名称，加载逻辑按名称查找目录。如果目录不存在或加载失败，回退链保证最终落到内置 `compressor`。风险主要在：如果用户创建了一个有 bug 的 engine 并放在正确目录下，配置切换到它后，压缩逻辑可能静默失败——因为 ABC 没有强制 `update_from_response` 必须正确更新 token 计数（它只是声明了方法签名，实际行为取决于实现）。

## 切换 Engine 的成本

**openclaw**：修改配置 + 注册新 engine。`resolveContextEngine` 从 `config.plugins.slots.contextEngine` 读取 engine ID 并查找注册表中的 factory。切换发生在下一次 agent 启动时——因为 `resolveContextEngine` 在会话初始化时调用（`src/agents/pi-embedded-runner/run.ts:518`），不需要运行时动态切换。成本在于：新 engine 必须实现完整的 `ContextEngine` interface，包括 subagent 生命周期管理——这对简单场景可能是过度工程。

**hermes**：修改 `context.engine` 配置 + 放置目录。切换也发生在会话初始化时。成本明显更低——只需要实现 4 个抽象方法。`get_tool_schemas` 和会话生命周期都是可选的。一个最小实现可以只有几十行代码。但代价是：如果 engine 选择不实现 `on_session_end`，会话结束时不会有任何清理——这是一个隐式契约，依赖实现者的自觉。

## 关键洞察

**这不是一个好与坏的选择，而是对"Context Engine 是什么"的根本定义不同。**

openclaw 的定义是 **状态基础设施**。正因为如此，它需要完整生命周期、所有者访问控制、与 subagent 系统深度集成。当你的 Context Engine 管理 transcript DAG、prompt-cache 可观察性和 subagent 状态的派生时，"独占槽位 + 访问控制"不是保守——它是唯一合理的架构。

hermes 的定义是 **可替换的压缩策略**。`should_compress` + `compress` 是其本质，其他都是可选能力。正因为如此，文件系统发现和声明式切换是正确的选择——摩擦最小化对于"让用户试验不同压缩算法"这个目标来说是必要的。

**共同假设**：两者都认为"同一时间只有一个 engine 激活"是硬性约束。这不是一个需要辩论的设计决策，而是一个从问题本质（共享可变状态的排他性修改）推导出的必然结论。

**分歧点**：唯一的分歧在于"需要多少基础设施来安全地实现这个约束"。openclaw 选择了编译时/注册时的防线 + 复杂接口 = 高安全 + 高扩展成本。hermes 选择了加载时/运行时的防线 + 简单接口 = 中等安全 + 低扩展成本。

## 适用场景启发

- **如果你的 Context Engine 管理的是完整会话生命周期**（DAG、subagent、transcript 重写），采用 openclaw 的独占槽位 + 所有者访问控制模式。register 阶段就阻止冲突，比运行时发现更安全。
- **如果你的 Context Engine 主要是压缩策略的替代实现**（不同类型的摘要、不同的 token 预算计算），采用 hermes 的目录发现 + 声明式切换。降低第三方参与的摩擦比防止边缘情况的安全风险更有价值。
- **无论哪种模式，兜底默认值都是必需的**。openclaw 的 `"legacy"` 和 hermes 的 `"compressor"` 都保证了即使插件加载失败，系统仍能正常运行。

## 关联页面

- [[openclaw-context-engine]] — openclaw 实现细节
- [[hermes-context-engine]] — hermes 实现细节
- [[openclaw-plugin-architecture]] — openclaw 插件系统的整体架构
- [[hermes-plugin-system]] — hermes 插件系统的整体架构
