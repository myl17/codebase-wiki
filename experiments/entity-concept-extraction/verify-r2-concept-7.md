# Concept Page 源码核查报告：Context Engine Singleton vs Pluggable

**核查日期**: 2026-06-17
**Concept 页**: `concept/context-engine-singleton-vs-pluggable.md`

---

## 核查方法

逐条比对 Concept 页中的事实性声明与 openclaw 和 hermes 的实际源码。所有行号引用均来自核查时检出的源码版本。

### 源码路径

| 仓库 | 路径 |
|------|------|
| openclaw | `/Users/yuanlimiao/Work/agent_harness/openclaw/` |
| hermes | `/Users/yuanlimiao/Work/agent_harness/hermes-agent/` |

---

## 一、openclaw 核查

### 1.1 `registerContextEngine` 独占槽位机制

**声明**: 核心数据结构是 process-global 的 `Map<string, { factory, owner }>`，三行保护逻辑。

**源码**: `src/context-engine/registry.ts`

```typescript
// Line 309-326: Registry state is process-global via resolveGlobalSingleton
type ContextEngineRegistryState = {
  engines: Map<string, { factory: ContextEngineFactory; owner: string }>;
};

// Line 345-368: registerContextEngineForOwner with three-level protection
```

**核查结论**: **准确**。

- process-global Map 结构：确认 (line 309-326)。`resolveGlobalSingleton` 确保跨模块 chunk 共享同一个注册表。
- 三层保护全部在源码中逐条对应：
  1. **默认槽位锁定**: `id === defaultSlotIdForKey("contextEngine") && normalizedOwner !== CORE_CONTEXT_ENGINE_OWNER` → 返回 `{ ok: false }` (lines 354-359)
  2. **同 ID 不同 owner 互斥**: `existing && existing.owner !== normalizedOwner` → 返回 `{ ok: false }` (lines 360-362)
  3. **同 owner 刷新需显式声明**: `existing && opts?.allowSameOwnerRefresh !== true` → 返回 `{ ok: false }` (lines 363-365)

- `registerContextEngine(id, factory)` 始终以 `"public-sdk"` 调用 `registerContextEngineForOwner` (lines 377-382)，确认无权抢占 core 槽位。

### 1.2 默认槽位 ID

**声明**: 默认槽位 ID 为 `"legacy"`。

**源码**: `src/plugins/slots.ts:19`

```typescript
const DEFAULT_SLOT_BY_KEY: Record<PluginSlotKey, string> = {
  memory: "memory-core",
  contextEngine: "legacy",
};
```

**核查结论**: **准确**。`defaultSlotIdForKey("contextEngine")` 返回 `"legacy"`。

### 1.3 resolveContextEngine 解析逻辑

**声明**: 先读 `config.plugins.slots.contextEngine`，回退到 `"legacy"`；Map 中可注册多个但只有一个激活。

**源码**: `src/context-engine/registry.ts:411-427`

```typescript
export async function resolveContextEngine(config?: OpenClawConfig): Promise<ContextEngine> {
  const slotValue = config?.plugins?.slots?.contextEngine;
  const engineId =
    typeof slotValue === "string" && slotValue.trim()
      ? slotValue.trim()
      : defaultSlotIdForKey("contextEngine");
  const entry = getContextEngineRegistryState().engines.get(engineId);
  if (!entry) throw new Error(...);
  return wrapContextEngineWithSessionKeyCompat(await entry.factory());
}
```

**核查结论**: **准确**。config path 为 `config.plugins.slots.contextEngine`，在 `src/config/types.plugins.ts:23` 定义为 `contextEngine?: string`。解析逻辑只实例化一个 engine。

### 1.4 ContextEngine 接口范围

**声明**: 接口定义在 `types.ts:150-281`；"除了核心的 assemble、ingest、compact、maintain"。

**源码**: `src/context-engine/types.ts`

| 成员 | 签名行 | 必须/可选 |
|------|--------|-----------|
| `info` (property) | 152 | required |
| `bootstrap?` | 157 | optional |
| `maintain?` | 169 | **optional** |
| `ingest` | 179 | **required** |
| `ingestBatch?` | 190 | optional |
| `afterTurn?` | 203 | optional |
| `assemble` | 224 | **required** |
| `compact` | 244 | **required** |
| `prepareSubagentSpawn?` | 266 | optional |
| `onSubagentEnded?` | 275 | optional |
| `dispose?` | 280 | optional |

**核查结论**: **有一个事实错误**。

- `maintain?` (line 169) 带 `?`，是 **optional** 方法，不是核心/必须方法。
- Concept 页将 `maintain` 与 `assemble`、`ingest`、`compact` 并列为核心方法，不符合源码事实。核心（必须实现）方法只有 3 个：`ingest`、`assemble`、`compact`。

### 1.5 resolveContextEngine 调用位置

**声明**: "resolveContextEngine 在会话初始化时调用（run.ts:518）"。

**源码**: `src/agents/pi-embedded-runner/run.ts:518`

```typescript
const contextEngine = await resolveContextEngine(params.config);
```

**核查结论**: **路径不完整**。实际路径为 `src/agents/pi-embedded-runner/run.ts:518`，不是 `run.ts:518`。该文件位于 `pi-embedded-runner` 子目录下，Concept 页省略了中间目录层级。

---

## 二、hermes 核查

### 2.1 ContextEngine ABC 方法数量

**声明**: "4 个必须实现方法 + 7 个可选方法"。

**源码**: `agent/context_engine.py:32-185`

**必须实现方法** (@abstractmethod, 4 个):

| 方法 | 行号 |
|------|------|
| `name` (property) | 37-40 |
| `update_from_response(usage)` | 65-70 |
| `should_compress(prompt_tokens)` | 72-74 |
| `compress(messages, current_tokens)` | 76-89 |

**可选实现方法** (无 @abstractmethod, 8 个):

| 方法 | 行号 |
|------|------|
| `should_compress_preflight` | 93-99 |
| `on_session_start` | 103-108 |
| `on_session_end` | 110-115 |
| `on_session_reset` | 117-125 |
| `get_tool_schemas` | 129-135 |
| `handle_tool_call` | 137-147 |
| `get_status` | 151-165 |
| `update_model` | 169-184 |

**核查结论**: **可选方法数量有误**。

- 必须实现方法: 4 个 -- **准确**
- 可选实现方法: **8 个，不是 7 个**。Concept 页少计了 1 个。
- Concept 页描述的覆盖范围（预检查、会话生命周期、工具暴露、状态、模型切换）涵盖了所有 8 个方法，但数量统计少 1。

### 2.2 插件发现逻辑

**声明**: `discover_context_engines()` 扫描 `plugins/context_engine/` 目录，子目录含 `__init__.py` 即视为候选。

**源码**: `plugins/context_engine/__init__.py:33-76`

```python
def discover_context_engines() -> List[Tuple[str, str, bool]]:
    for child in sorted(_CONTEXT_ENGINE_PLUGINS_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith(("_", ".")):
            continue
        init_file = child / "__init__.py"
        if not init_file.exists():
            continue
        # Read plugin.yaml for description
        # Quick availability check via is_available()
```

**核查结论**: **准确**。

- 排除以下划线/点开头的目录: line 45
- 要求 `__init__.py` 存在: lines 47-49
- 读取 `plugin.yaml` 的 description: lines 53-61
- 调用 `is_available()` 做轻量检查: lines 69-70

### 2.3 加载逻辑: register(ctx) + fallback 扫描

**声明**: `_load_engine_from_dir`（第 100-196 行）支持两种模式。

**源码**: `plugins/context_engine/__init__.py:100-196`

- **register(ctx) 模式** (lines 176-183): `hasattr(mod, "register")` → `mod.register(collector)` → `collector.register_context_engine(engine)` 捕获实例。`_EngineCollector` (lines 199-219) 提供 `register_context_engine` 方法。
- **Fallback 扫描** (lines 185-194): `issubclass(attr, ContextEngine)` → 直接实例化 `attr()`。

**核查结论**: **准确**。两种模式均对应源码实现。

### 2.4 激活链和 fallback

**声明**: `config.yaml` → `context.engine: "lcm"` → `load_context_engine("lcm")` → fallback to `hermes_cli.plugins.get_plugin_context_engine()` → fallback to built-in `"compressor"`。

**源码**: `run_agent.py:1432-1499`

**核查结论**: **准确**。与源码逐级对应:

1. 配置读取 (line 1440-1441): `_agent_cfg.get("context", {}).get("engine", "compressor")`
2. 目录扫描加载 (line 1448): `load_context_engine(_engine_name)`
3. 通用插件系统兜底 (line 1456): `hermes_cli.plugins.get_plugin_context_engine()`
4. 内置 compressor 最终兜底 (lines 1491-1499): `ContextCompressor(...)`

**补充**: 源码第 1445 行有一个隐含逻辑：如果 `_engine_name == "compressor"`，直接跳过步骤 2-3，使用内置实现。Concept 页未提及这个短路行为，但不影响对 fallback chain 的宏观描述。

---

## 三、对比分析准确性核查

### 3.1 对比表

| 维度 | Concept 页 | 源码事实 | 判定 |
|------|-----------|----------|------|
| 注册方式 | 程序化 API vs 文件系统发现 | 准确 | OK |
| 接口广度 | "10+ 方法" vs "4 个抽象方法" | openclaw 3 required + 7 optional = 10; hermes 4 required + 8 optional = 12 | **两方都偏少了**，尤其是 hermes 总方法数是 12 不是 11 |
| 状态安全 | 所有者访问控制 + 三层保护 vs 配置选一 | 双方机制均对应源码 | OK |
| 切换方式 | `config.plugins.slots.contextEngine` vs `context.engine` | 两条 config path 均准确 | OK |
| 发现机制 | 显式注册 vs 隐式扫描 | 准确 | OK |
| 防止核心被覆盖 | owner 锁定 vs 回退链 | 双方均对应源码 | OK |
| 第三方扩展开销 | — | 定性比较，非事实性声明 | — |

### 3.2 "状态基础设施 vs 可替换压缩策略" 二分法

**声明**: openclaw 把 Context Engine 当作**状态基础设施**，hermes 当作**可替换的压缩策略**。

**核查**: 这不是纯粹的事实性声明，而是基于接口范围差异的设计解读。但源码证据支持这一解读：

- openclaw 的 `ContextEngine` 接口确实深度嵌入运行时基础设施：subagent 生命周期 (`prepareSubagentSpawn`, `onSubagentEnded`)、transcript 重写 (`runtimeContext.rewriteTranscriptEntries`)、prompt-cache 可观察性 (`runtimeContext.promptCache`)、维护周期 (`maintain`)。这些超越了压缩的范畴，覆盖了完整的会话状态管理。
- hermes 的 `ContextEngine` ABC 的 `@abstractmethod` 四个方法全部围绕 "何时压缩 + 怎么压缩" (`update_from_response`, `should_compress`, `compress`)，外加 `name`。会话生命周期、工具暴露等均为可选扩展。这表明压缩是其核心抽象。

**核查结论**: **设计解读有源码支撑，二分法合理**。

### 3.3 共同假设

**声明**: "两者都认为同一时间只有一个 engine 激活是硬性约束"。

**核查**:
- openclaw: `resolveContextEngine` 只返回一个 `ContextEngine` 实例。Map 可注册多个，但解析只拿一个。
- hermes: `run_agent.py` 中 `self.context_compressor` 是一个单一实例变量 (line 1471)。注释明确 "Only ONE can be active at a time" (`__init__.py:8`)。

**核查结论**: **准确**。

### 3.4 兜底默认值

**声明**: openclaw 的 `"legacy"` 和 hermes 的 `"compressor"` 都保证兜底。

**核查**:
- openclaw: `defaultSlotIdForKey("contextEngine")` → `"legacy"` (slots.ts:19)，`resolveContextEngine` 的 fallback 逻辑 (registry.ts:413-416)。
- hermes: `_engine_name = _ctx_cfg.get("engine", "compressor") or "compressor"` (run_agent.py:1441)，加载失败时回退到内置 `ContextCompressor` (run_agent.py:1463-1499)。

**核查结论**: **准确**。

### 3.5 防线位置对比

**声明**: openclaw 防线在编译时/注册时；hermes 防线在加载时/运行时。

**核查**: 这是一个架构差异的定性解读，不完全是事实性声明，但源码结构支持这种区分：
- openclaw 的 `registerContextEngineForOwner` 在注册阶段就返回 `{ ok: false }` 阻止冲突——冲突在 API 调用时即刻暴露。
- hermes 的 `discover_context_engines` + `load_context_engine` 只在配置驱动时触发——问题在运行时加载阶段暴露。

**核查结论**: **方向性判断准确**。

---

## 四、查到的错误汇总

### 错误 1: openclaw `maintain` 列为必须方法

- **所在位置**: 第 11 行 -- "除了核心的 assemble、ingest、compact、maintain"
- **事实**: `maintain?` 在接口中标记为 optional（`types.ts:169`）
- **影响**: 中等。误导读者认为 openclaw 有 4 个必须实现的接口方法，实际只有 3 个（ingest、assemble、compact）

### 错误 2: hermes 可选方法数量少计 1 个

- **所在位置**: 第 58 行 -- "7 个可选方法"
- **事实**: 实际有 8 个可选方法 (should_compress_preflight, on_session_start, on_session_end, on_session_reset, get_tool_schemas, handle_tool_call, get_status, update_model)
- **影响**: 轻微。方法全名已一一列举，仅总数统计偏差

### 错误 3: resolveContextEngine 调用位置路径不完整

- **所在位置**: 第 118 行 -- "run.ts:518"
- **事实**: 实际路径为 `src/agents/pi-embedded-runner/run.ts:518`
- **影响**: 轻微。文件定位时多查找一个目录层级

---

## 五、总结

| 类别 | 数量 |
|------|------|
| 事实完全准确 | 15 处 |
| 轻微偏差（路径不完整、统计偏差） | 2 处 |
| 实际错误（maintain 非必须） | 1 处 |
| 定性解读（有源码支撑） | 5 处 |

**总体评价**: Concept 页对两个仓库 Context Engine 机制的核心描述是准确的。三层保护机制、目录发现逻辑、fallback chain、独占激活约束等关键架构事实均与源码一致。三处错误中，`maintain` 被误列为必须方法是唯一实质性偏差——在未来的 Concept 页修订中应将其移入可选方法组。hermes 可选方法数量 7→8 和 openclaw 文件路径不完整属于轻微偏差。

**建议修复**:
1. 将第 11 行的 "assemble、ingest、compact、maintain" 改为 "assemble、ingest、compact"，或将 `maintain` 移到可选方法描述中
2. 将第 58 行的 "7 个可选方法" 改为 "8 个可选方法"
3. 将第 118 行的 "run.ts:518" 改为 "src/agents/pi-embedded-runner/run.ts:518"
