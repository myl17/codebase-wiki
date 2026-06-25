---
concept: global-capability-coexistence
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# Global Capability Coexistence（全局能力-共存策略）

## 标准化问题陈述

当多个实现竞争同一全局能力（上下文引擎/记忆后端）时，如何决定它们之间的共存关系——是加性叠加还是替换式互斥？

## 核心关切

1. **正确性（Correctness）**：Context engine 决定所有 LLM 交互的 prompt 组装方式——同时存在多个必然产生冲突，必须保证全局只有唯一活跃实现
2. **健壮性（Robustness）**：加性叠加保证基础功能永不丢失但可能产生冗余存储；替换式更简洁但可能丢失内置存储的稳定性保障
3. **可预测性（Predictability）**：注册顺序应可预测——后注册者覆盖前者的规则必须明确且一致，不能出现非确定性竞态
4. **开放性（Openness）**：Plugin 应能自由注册自己的实现——开放性要求允许多个 plugin 竞争注册，但最终只能有一个胜出或全部共存
5. **简洁性（Simplicity）**：共存策略本身的实现复杂度不应超过被管理的能力本身——复杂的去重和冲突解决逻辑自身就是维护负担

## 实例矩阵

| 仓库 | 策略 | 注册模型 | 核心权衡 |
|------|------|---------|--------|
| openclaw | Exclusive 槽位覆盖注册 | 单槽单实现，后注册覆盖前者；同种竞争 plugin 在 slot 切换时自动禁用 | 正确性 + 可预测性 > 健壮性 + 开放性 |
| hermes-agent | 加性叠加 + 最多 1 个外部 provider | 内置始终排第一，外部 appending；严格限制 1 个外部 | 健壮性 + 开放性 > 简洁性 + 可预测性 |

## openclaw — Exclusive 槽位覆盖注册

### 能力-槽位映射

`src/plugins/slots.ts:12-15` 定义了能力种类到槽位的映射——每一种全局能力对应一个 exclusive slot：

```typescript
const SLOT_BY_KIND: Record<PluginKind, PluginSlotKey> = {
  memory: "memory",
  "context-engine": "contextEngine",
};
```

每个 slot 都有默认值（`slots.ts:17-19`）：context engine 默认 `"legacy"`，memory 默认 `"memory-core"`。这意味着 openclaw 在没有任何 plugin 注册时也有内置兜底实现，但一旦 plugin 通过 slot 机制覆盖，内置就会被替换。

### Exclusive 注册机制

**Context Engine 注册**（`src/context-engine/registry.ts:345-368`）：

`registerContextEngineForOwner()` 是带身份验证的注册入口。核心逻辑：

1. **Core 身份保护**（行 354-358）：若注册目标 id 是默认槽位 id `"legacy"` 且注册者不是 `"core"` 身份，直接拒绝——第三方 plugin 不能占用 core 预留的默认槽位
2. **Owner 冲突检测**（行 360-362）：若目标 id 已被其他 owner 注册，返回 `{ ok: false, existingOwner }` 拒绝
3. **同 owner 刷新控制**（行 363-365）：同一 owner 可刷新已有注册，但需显式传 `allowSameOwnerRefresh: true`

Public SDK 的入口 `registerContextEngine()`（行 377-382）以 `"public-sdk"` 身份注册，天然无法抢占 core 拥有的槽位。这种双层身份设计保证了内置实现的注册不会被第三方意外覆盖。

**Memory Capability 注册**（`src/plugins/types.ts:1977-1980`）：

```typescript
/** Register the active memory capability for this memory plugin (exclusive slot). */
registerMemoryCapability: (
  capability: import("./memory-state.js").MemoryPluginCapability,
) => void;
```

同样标注为 `exclusive slot`——全局只能有一个活跃的 memory capability。

### Slot 选择与竞争禁用

`src/plugins/slots.ts:76-159` 的 `applyExclusiveSlotSelection()` 是槽位切换的完整实现：

1. **槽位切换**（行 93-102）：新选中 plugin 的 id 写入 slot 配置，覆盖旧值。如果存在前一个 slot 占用人且不同，输出 warning 记录切换
2. **竞争者自动禁用**（行 104-129）：遍历所有已注册 plugin，找出与新选中 plugin 同类（相同 kind）的其他 plugin，将其 `enabled` 设为 `false`——但会跳过仍在其他 slot 中活跃的 plugin（行 117-121）。被禁用的 plugin id 列表追加到 warning 中
3. **产出变更后的 config**（行 147-158）：返回新的 config 对象（immutable 更新），包含更新后的 `slots` 和 `entries`

这意味着：当用户通过配置 `config.plugins.slots.contextEngine = "my-engine"` 选择某个 context engine 时，所有其他 context-engine 类型的 plugin 自动被禁用，确保运行时只有一个活跃的 context engine 实例。

### Context Engine 解析

`src/context-engine/registry.ts:411-427` 的 `resolveContextEngine()` 是运行时的唯一入口：先读 `config.plugins.slots.contextEngine` 配置，无配置则 fallback 到默认值 `"legacy"`，然后从注册表中查找对应 factory 并实例化。如果目标 engine 未注册，抛出包含所有可用 engine 列表的错误——确保问题可诊断。

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 正确性（全局只有一个活跃实现，避免 prompt 组装冲突；core 身份保护内置默认注册不被抢占） | 健壮性（如果注册的实现有问题，无内置兜底——slot 覆盖后内置实现被完全替换） |
| 可预测性（后注册明确覆盖前者，slot 切换产生 warning 日志 + 竞争者自动禁用列表，所有状态变更可追溯） | 开放性（多个实现不能共存——即使各自功能无冲突也不能同时激活） |

## hermes-agent — 加性叠加 + 最多 1 个外部 provider

### 注册模型

`agent/memory_manager.py:83-141` 的 `MemoryManager` 类是记忆后端共存策略的唯一协调点。

**内置不可移除**（行 97-104）：

```python
def add_provider(self, provider: MemoryProvider) -> None:
    is_builtin = provider.name == "builtin"
    if not is_builtin:
        ...
```

`BuiltinMemoryProvider`（name = `"builtin"`）始终被接受，不受外部 provider 数量限制。没有任何 API 能从 `_providers` 列表中移除 provider——内置存储的持久性由 API 缺失来保证，而非显式保护逻辑。

**严格限制 1 个外部 provider**（行 106-119）：

```python
if not is_builtin:
    if self._has_external:
        existing = next(
            (p.name for p in self._providers if p.name != "builtin"), "unknown"
        )
        logger.warning(
            "Rejected memory provider '%s' — external provider '%s' is "
            "already registered. ...",
            provider.name, existing,
        )
        return
    self._has_external = True
```

`_has_external` 布尔标志锁定外部槽位：第二个及之后的非内置 provider 被 `logger.warning` 拒绝并直接 `return`，不抛异常——静默拒绝而非崩溃。这种做法保证了 agent 启动的容错性（错误的 config 不会导致启动失败），但代价是问题可能被忽视。警告消息中包含已注册者的名称，指向 `config.yaml` 中的 `memory.provider` 配置项，为用户提供了诊断信息。

**追加式注册**（行 121）：

```python
self._providers.append(provider)
```

内置和外部的 provider 按注册顺序追加到同一个列表中，内置总是在位置 0（依赖调用方遵守注册顺序约定——`add_provider` 本身不强制顺序，但 docstring 约定 `BuiltinMemoryProvider` 先注册）。这种顺序为所有遍历操作（prefetch、sync、system prompt 构建）提供了确定性的执行顺序。

**Tool 名称冲突检测**（行 123-135）：当多个 provider 暴露同名 tool 时，先注册者优先，后注册者的重复 tool 名被忽略并产生 warning。这是加性模型中少有的排他性逻辑——但仅针对 tool 名称冲突，而非功能级别。

### 加性遍历

所有运行时操作均遍历 `_providers` 列表，收集所有 provider 的产出并拼接：

| 操作 | 方法 | 行号 | 加性行为 |
|------|------|------|---------|
| 系统提示组装 | `build_system_prompt()` | 157-174 | 遍历所有 provider 的 `system_prompt_block()`，用 `\n\n` 连接 |
| 记忆预取 | `prefetch_all()` | 178-195 | 遍历所有 provider 的 `prefetch()`，用 `\n\n` 连接结果 |
| 后台预取排队 | `queue_prefetch_all()` | 197-206 | 遍历所有 provider 的 `queue_prefetch()` |
| Turn 同步 | `sync_all()` | 210-218 | 遍历所有 provider 的 `sync_turn()` |
| Tool Schema 收集 | `get_all_tool_schemas()` | 223-239 | 遍历所有 provider，按 tool 名去重后合并 |
| Tool 调用路由 | `handle_tool_call()` | 249-267 | 通过 `_tool_to_provider` 字典按 tool 名路由到对应 provider |

每条遍历路径都有独立的异常隔离：单个 provider 的失败不会阻塞其他 provider 的执行（`try/except` 包在每个 provider 调用外层，失败日志级别为 `debug` 或 `warning`）。

### MemoryProvider 抽象

`agent/memory_provider.py:42-232` 定义了 `MemoryProvider` ABC，包含：
- **必须实现**（`@abstractmethod`）：`name`、`is_available()`、`initialize()`、`get_tool_schemas()`
- **可选覆盖**：`system_prompt_block()`（默认返回 `""`）、`prefetch()`、`sync_turn()`、`queue_prefetch()`、`handle_tool_call()`、`shutdown()`、`on_turn_start()`、`on_session_end()`、`on_pre_compress()`、`on_delegation()`、`on_memory_write()`

所有可选方法都有默认空实现，使得简单 provider 只需实现 4 个抽象方法即可接入——这是一种低门槛的扩展设计。

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 健壮性（BuiltinMemoryProvider 始终启用且无法移除——`add_provider` 无对应的 `remove_provider`，内置存储的持久性由 API 缺失保证；单个 provider 失败不阻塞其他 provider） | 简洁性（加性可能产生冗余存储——内置和外部 provider 各自维护独立的存储，写入时两边各写一份；去重仅在 tool schema 层面，数据层面的去重完全由各个 provider 自身负责） |
| 开放性（外部实现通过 `MemoryProvider` ABC 叠加内置基础——内置功能永不丢失，外部 provider 只做增量） | 可预测性（内置+外部的叠加顺序固定但去重逻辑分散在各 provider 中，整体行为不如 exclusive 模型那样一目了然；tool 名称冲突时先注册者静默胜出，可能掩盖配置错误） |

## 权衡对比

| 维度 | openclaw | hermes-agent |
|------|----------|-------------|
| **共存模型** | Exclusive 槽位覆盖（替换式） | 加性叠加 + 最多 1 个外部（加性式） |
| **注册入口** | `registerContextEngineForOwner(owner)` + `registerContextEngine()` 双层身份；`registerMemoryCapability()` | `MemoryManager.add_provider()` 单入口，通过 `provider.name` 区分内置/外部 |
| **多实现处理** | 竞争 plugin 自动禁用（`applyExclusiveSlotSelection` lines 126-128） | 第二个外部被静默拒绝（`_has_external` guard line 107） |
| **内置保护** | Core 身份 + 默认槽位保护（`CORE_CONTEXT_ENGINE_OWNER` line 306），第三方不能声明 core 拥有的 id | 无显式保护——通过 API 缺失（没有 `remove_provider`）+ `"builtin"` 名字判断实现 |
| **容错策略** | 解析失败抛异常（`resolveContextEngine` line 420-423），包含可用 engine 列表 | 单个 provider 失败不阻塞其他（try/except per provider），静默拒绝第二个外部 |
| **状态可见性** | Slot 切换产生 warning（line 100-102），竞争者禁用列表输出（line 133-135） | 外部拒绝产生 warning（line 111-118），tool 冲突产生 warning（line 129-135） |
| **实现位置** | 两个独立能力（context engine + memory）各自独立注册，但共享同一 slot 竞争框架（`SLOT_BY_KIND`） | 单一 `MemoryManager` 类统一管理所有 memory provider，无通用 slot 框架扩展到其他能力 |
| **扩展维度** | 新增能力种类只需在 `SLOT_BY_KIND` 和 `PluginSlotsConfig` 中添加条目 | 每种全局能力需要独立实现类似 `MemoryManager` 的协调器 |
| **核心取舍** | 宁可只有一个不完美的实现也不允许两个冲突的实现（正确性压倒开放性和健壮性） | 宁可有多余的存储和更复杂的协调逻辑也不允许基础功能丢失（健壮性压倒简洁性） |

## 关键源码引用

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/plugins/slots.ts` | 12-19 | `SLOT_BY_KIND` 能力-槽位映射 + `DEFAULT_SLOT_BY_KEY` 默认值 |
| openclaw | `src/plugins/slots.ts` | 76-159 | `applyExclusiveSlotSelection()` 槽位切换 + 竞争者自动禁用 |
| openclaw | `src/context-engine/registry.ts` | 306-307 | `CORE_CONTEXT_ENGINE_OWNER` / `PUBLIC_CONTEXT_ENGINE_OWNER` 双层身份常量 |
| openclaw | `src/context-engine/registry.ts` | 345-368 | `registerContextEngineForOwner()` core 身份保护 + owner 冲突检测 + 同 owner 刷新控制 |
| openclaw | `src/context-engine/registry.ts` | 377-382 | `registerContextEngine()` 公共 SDK 入口，以 `PUBLIC_CONTEXT_ENGINE_OWNER` 身份注册 |
| openclaw | `src/context-engine/registry.ts` | 411-427 | `resolveContextEngine()` 运行时解析：slot 配置 > 默认值 > factory 实例化 |
| openclaw | `src/plugins/types.ts` | 1966-1970 | `registerContextEngine` plugin API 声明（"exclusive slot"） |
| openclaw | `src/plugins/types.ts` | 1977-1980 | `registerMemoryCapability` plugin API 声明（"exclusive slot"） |
| hermes-agent | `agent/memory_manager.py` | 90-93 | `MemoryManager.__init__()` — `_providers` 列表 + `_has_external` 标志 |
| hermes-agent | `agent/memory_manager.py` | 97-141 | `add_provider()` — 内置总是接受（行 104）+ 外部最多 1 个（行 106-119）+ 追加到列表（行 121）+ tool 冲突检测（行 124-135） |
| hermes-agent | `agent/memory_manager.py` | 157-174 | `build_system_prompt()` — 遍历所有 provider 拼接系统提示 |
| hermes-agent | `agent/memory_manager.py` | 178-195 | `prefetch_all()` — 遍历所有 provider 收集预取上下文 |
| hermes-agent | `agent/memory_manager.py` | 210-218 | `sync_all()` — 遍历所有 provider 同步 turn |
| hermes-agent | `agent/memory_provider.py` | 42-232 | `MemoryProvider` ABC — 4 抽象方法 + 11 可选覆盖方法 |

## 关联

- [[openclaw/nodes/components/openclaw-context-engine]]
- [[openclaw/nodes/components/openclaw-memory-system]]
- [[hermes-agent/nodes/extension-points/hermes-agent-memory-provider]]
- [[openclaw/dimensions/openclaw-extension-points]]
- [[hermes-agent/dimensions/hermes-agent-extension-points]]

---
## 修复记录

**2026-06-19（v2 验证修复）**：
- **顺序约定标注（⚠️→✅）**：hermes-agent 中 `BuiltinMemoryProvider` 排在 `_providers` 列表位置 0 是调用方注册顺序约定，并非 `add_provider` 硬编码强制。若外部 provider 先于内置注册，内置将排在位置 1 而非 0。已在「追加式注册」描述处添加标注「依赖调用方遵守注册顺序约定——`add_provider` 本身不强制顺序，但 docstring 约定 `BuiltinMemoryProvider` 先注册」。
