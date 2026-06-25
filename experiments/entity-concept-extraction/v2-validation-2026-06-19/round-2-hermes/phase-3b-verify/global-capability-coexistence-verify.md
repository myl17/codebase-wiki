# 验证报告：global-capability-coexistence

## 格式完整性
- [x] 问题陈述是"如何..."问题形式 — `当多个实现竞争同一全局能力（上下文引擎/记忆后端）时，如何决定它们之间的共存关系——是加性叠加还是替换式互斥？`
- [x] 核心关切列表 >= 2 条 — 共 5 条
- [x] 每个权衡位置有"优先满足"和"接受妥协"两个字段 — openclaw 设计取向表（line 85-88）和 hermes-agent 设计取向表（line 161-164）均有
- [x] 跨仓库对比表列数 = 仓库数 — 2 列（权衡对比表）
- [x] 溯源表完整 — 有

---

## 逐仓库验证

### openclaw

**Claim 1**: "SLOT_BY_KIND 定义能力种类到槽位的映射"（`slots.ts:12-15`）

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/plugins/slots.ts:12-15`
```typescript
const SLOT_BY_KIND: Record<PluginKind, PluginSlotKey> = {
  memory: "memory",
  "context-engine": "contextEngine",
};
```

判定：✅ 行号和映射内容与源码完全一致。

---

**Claim 2**: "DEFAULT_SLOT_BY_KEY 默认值：context engine 默认 'legacy'，memory 默认 'memory-core'"（`slots.ts:17-19`）

源码：`slots.ts:17-19`
```typescript
const DEFAULT_SLOT_BY_KEY: Record<PluginSlotKey, string> = {
  memory: "memory-core",
  contextEngine: "legacy",
};
```

判定：✅ 默认值和行号与源码完全一致。

---

**Claim 3**: "applyExclusiveSlotSelection() 槽位切换 + 竞争者自动禁用"（`slots.ts:76-159`）

源码：`slots.ts:76-159` — 函数实现包含：(a) 槽位切换写入 slots 配置 (line 95)，(b) 竞争者遍历禁用逻辑 (line 104-129)，(c) 跳过仍在其他 slot 活跃的 plugin (line 117-121)，(d) 返回 immutable 更新后的 config (line 147-158)。

判定：✅ 机制描述的每个要点均可在源码中找到对应实现。

---

**Claim 4**: "CORE_CONTEXT_ENGINE_OWNER = 'core' / PUBLIC_CONTEXT_ENGINE_OWNER = 'public-sdk'"（`registry.ts:306-307`）

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/context-engine/registry.ts:306-307`
```typescript
const CORE_CONTEXT_ENGINE_OWNER = "core";
const PUBLIC_CONTEXT_ENGINE_OWNER = "public-sdk";
```

判定：✅ 双层身份常量与源码完全一致。

---

**Claim 5**: "registerContextEngineForOwner() core 身份保护"（`registry.ts:345-368`）

源码：`registry.ts:345-368` — 逻辑：(a) 行 354-358：若注册目标 id 是默认槽位且注册者非 core，直接拒绝；(b) 行 360-362：若 id 已被其他 owner 注册，拒绝；(c) 行 363-365：同一 owner 刷新需 `allowSameOwnerRefresh: true`。

判定：✅ 三层保护逻辑与源码完全一致。

---

**Claim 6**: "registerContextEngine() 公共 SDK 入口，以 public-sdk 身份注册，天然无法抢占 core 槽位"（`registry.ts:377-382`）

源码：`registry.ts:377-382` — `registerContextEngine` 内部调用 `registerContextEngineForOwner(id, factory, PUBLIC_CONTEXT_ENGINE_OWNER)`。由于 `PUBLIC_CONTEXT_ENGINE_OWNER !== CORE_CONTEXT_ENGINE_OWNER`，对默认槽位 `"legacy"` 的注册会被行 354-358 拒绝。

判定：✅ 公共 SDK 入口的身份隔离机制与描述一致。

---

**Claim 7**: "resolveContextEngine() 运行时解析：slot 配置 > 默认值 > factory 实例化"（`registry.ts:411-427`）

源码：`registry.ts:411-427` — 解析顺序：(a) 读 `config.plugins.slots.contextEngine`，(b) fallback 到 `defaultSlotIdForKey("contextEngine")` (即 `"legacy"`)，(c) 从注册表获取 factory 并实例化，(d) 若未注册则抛出含可用 engine 列表的错误。

判定：✅ 解析流程与描述完全一致。

---

**Claim 8**: "registerContextEngine plugin API 声明为 exclusive slot"（`types.ts:1966-1970`）；"registerMemoryCapability 声明为 exclusive slot"（`types.ts:1977-1980`）

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/plugins/types.ts:1966-1967`
```typescript
/** Register a context engine implementation (exclusive slot - only one active at a time). */
```
`types.ts:1977-1979`
```typescript
/** Register the active memory capability for this memory plugin (exclusive slot). */
```

判定：✅ 两个 API 的 JSDoc 注释中均明确标注 "exclusive slot"。

---

### hermes-agent

**Claim 1**: "MemoryManager._providers 列表 + _has_external 标志"（`memory_manager.py:90-93`）

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/memory_manager.py:90-93`
```python
def __init__(self) -> None:
    self._providers: List[MemoryProvider] = []
    self._tool_to_provider: Dict[str, MemoryProvider] = {}
    self._has_external: bool = False
```

判定：✅ 初始数据结构与源码完全一致。

---

**Claim 2**: "add_provider() 内置总是接受（行 104）+ 外部最多 1 个（行 106-119）+ 追加到列表（行 121）+ tool 冲突检测（行 124-135）"（`memory_manager.py:97-141`）

源码：`memory_manager.py:97-141` — (a) 行 104：`is_builtin = provider.name == "builtin"` 判断内置，(b) 行 106-119：`if self._has_external` 拒绝第二个外部 provider，输出 `logger.warning`，(c) 行 121：`self._providers.append(provider)` 追加到列表，(d) 行 124-135：遍历 `provider.get_tool_schemas()` 检查 tool 名冲突，先注册者优先。

判定：✅ 注册逻辑的每个步骤均与源码完全一致。

---

**Claim 3**: "加性遍历表——所有运行时操作遍历 _providers 列表"（`memory_manager.py:157-267`）

逐项验证：

| 操作 | Claim 行号 | 源码行号 | 加性行为 | 判定 |
|------|-----------|---------|--------|------|
| `build_system_prompt()` | 157-174 | 157-174 | 遍历所有 provider 的 `system_prompt_block()`，用 `\n\n` 连接 | ✅ |
| `prefetch_all()` | 178-195 | 178-195 | 遍历所有 provider 的 `prefetch()`，用 `\n\n` 连接结果 | ✅ |
| `queue_prefetch_all()` | 197-206 | 197-206 | 遍历所有 provider 的 `queue_prefetch()` | ✅ |
| `sync_all()` | 210-218 | 210-218 | 遍历所有 provider 的 `sync_turn()` | ✅ |
| `get_all_tool_schemas()` | 223-239 | 223-239 | 遍历所有 provider，按 tool 名去重后合并 | ✅ |
| `handle_tool_call()` | 249-267 | 249-267 | 通过 `_tool_to_provider` 字典按 tool 名路由 | ✅ |

判定：✅ 所有 6 个加性遍历操作的行号和加性行为描述与源码完全匹配。每条遍历路径均有独立的 try/except 异常隔离。

---

**Claim 4**: "MemoryProvider ABC — 4 抽象方法 + 11 可选覆盖方法"（`memory_provider.py:42-232`）

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/agent/memory_provider.py:42-232`

`@abstractmethod` 方法（4 个）：
1. `name` (line 46, property)
2. `is_available()` (line 53)
3. `initialize()` (line 60)
4. `get_tool_schemas()` (line 120)

可选覆盖方法（均有默认实现或文档注明 override 可选）：
1. `system_prompt_block()` (line 83, 默认 `""`)
2. `prefetch()` (line 92, 默认 `""`)
3. `queue_prefetch()` (line 106, no-op)
4. `sync_turn()` (line 114, no-op)
5. `handle_tool_call()` (line 131, 默认 `raise NotImplementedError`)
6. `shutdown()` (line 139, no-op)
7. `on_turn_start()` (line 144)
8. `on_session_end()` (line 153)
9. `on_pre_compress()` (line 163, 默认 `""`)
10. `on_delegation()` (line 175)
11. `on_memory_write()` (line 223)

共 11 个可选覆盖方法。

判定：✅ 4 抽象方法 + 11 可选覆盖方法与源码完全一致。

---

**Claim 5**: "内置不可移除——没有任何 API 能从 _providers 列表中移除 provider"（`memory_manager.py:97-104`）

源码：`MemoryManager` 类（`memory_manager.py:83-374`）中未定义任何 `remove_provider` / `unregister` / `clear_providers` 方法。`_providers` 为 Python `list`，有公开的 `providers` property（line 143-146）但只返回 `list(self._providers)` 的副本，调用方无法通过公开 API 移除 provider。

判定：✅ 内置持久性确由 API 缺失保证，无显式保护逻辑。

---

**Claim 6**: "单个 provider 失败不阻塞其他 provider（try/except per provider，失败日志级别为 debug 或 warning）"（`memory_manager.py` 各处）

源码验证：
- `prefetch_all()` line 190-194: `except Exception` → `logger.debug`
- `queue_prefetch_all()` line 202-205: `except Exception` → `logger.debug`
- `sync_all()` line 215-218: `except Exception` → `logger.warning`
- `build_system_prompt()` line 169-173: `except Exception` → `logger.warning`
- `get_all_tool_schemas()` line 234-238: `except Exception` → `logger.warning`

判定：✅ 每条遍历路径均有 try/except 隔离，失败日志级别在 debug（prefetch/queue 类非关键）和 warning（sync/system prompt/tool schema 类关键）之间。

---

## 关切验证

| 关切 | 权衡对比表对应维度 | 判定 |
|------|-------------------|------|
| 1. 正确性 | 「共存模型」「多实现处理」行 — openclaw exclusive slot 保证唯一活跃 | ✅ |
| 2. 健壮性 | 「内置保护」「容错策略」行 — hermes 内置不可移除 + 单 provider 故障隔离 | ✅ |
| 3. 可预测性 | 「状态可见性」「注册入口」行 — openclaw slot 切换产生 warning；hermes 外部拒绝产生 warning | ✅ |
| 4. 开放性 | 「共存模型」「注册入口」行 — openclaw 多实现不能共存（妥协）；hermes 允许外部叠加 | ✅ |
| 5. 简洁性 | 「扩展维度」行 — hermes 需为每种能力独立实现协调器（妥协）；openclaw 有通用 slot 框架 | ✅ |

所有 5 个关切在权衡对比表中均有明确对应维度，无悬空关切。

---

## 追加完整性

- [x] openclaw 在各节均有提及 — 实例矩阵、独立分析节（Exclusive 槽位覆盖注册）、权衡对比表、关键源码引用
- [x] hermes-agent 在各节均有提及 — 实例矩阵、独立分析节（加性叠加 + 最多 1 个外部 provider）、权衡对比表、关键源码引用

---

## 绝对化语言验证

| 绝对化表述 | 源码边界条件 | 判定 |
|-----------|------------|------|
| "必须保证全局只有唯一活跃实现" | openclaw `applyExclusiveSlotSelection` 将竞争 plugin 的 `enabled` 设为 `false` — 强制唯一 | ✅ 准确 |
| "内置始终排第一" | `_providers.append(provider)` — 内置注册顺序依赖调用方行为；但 docstring 约定内置先注册 | ⚠️ 顺序依赖调用方遵守约定，非硬编码保证。若调用方不按 `BuiltinMemoryProvider` 先注册的约定，顺序可能被打破 |
| "后注册者覆盖前者" | `applyExclusiveSlotSelection` 的 `slots[slotKey] = params.selectedId` (line 95) | ✅ 准确 |
| "所有运行时操作均遍历 _providers 列表" | 所有 build/prefetch/sync/tool 方法确实逐一遍历 `self._providers` | ✅ 准确 |
| "第三方 plugin 不能占用 core 预留的默认槽位" | `registerContextEngineForOwner` 行 354-358 的 `normalizedOwner !== CORE_CONTEXT_ENGINE_OWNER` 检查 | ✅ 准确 |
| "公共 SDK 天然无法抢占 core 拥有的槽位" | `registerContextEngine` 调用 `registerContextEngineForOwner` 时传入 `PUBLIC_CONTEXT_ENGINE_OWNER`，必然触发行 354-358 的拦截 | ✅ 准确 |
| "任何 API 能从 _providers 列表中移除 provider" | MemoryManager 无 `remove_provider` / `unregister` 方法 | ✅ 准确 |
| "解析失败抛异常" vs "静默拒绝" | `resolveContextEngine` (registry.ts:420) — `throw new Error(...)`；`add_provider` (memory_manager.py:118) — `return` 无异常 | ✅ 两类容错策略描述准确 |

---

## 汇总

总 claim 数：26 | ✅：25 | ⚠️：1 | ❌：0

关键发现：
1. **内置排第一是约定而非硬编码（⚠️）**：hermes-agent 中 `BuiltinMemoryProvider` 的列表位置 0 依赖调用方在 `add_provider()` 时的注册顺序。源码 docstring（line 6-7）写明 "The BuiltinMemoryProvider is always registered first"，但 `add_provider` 本身不强制顺序——若外部 provider 先于内置注册，内置将排在位置 1 而非 0。建议 Concept 页明确标注"依赖调用方遵守注册顺序约定"。
2. **所有 26 个 claim 中 25 个与源码完全一致**，是三个验证报告中准确率最高的 Concept 页。行号引用精确，机制描述与源码逻辑高度吻合。
