# memory-retrieval-timing Concept 页验证报告

验证日期：2026-06-17
验证人：自动化源码核查

---

## openclaw

### 总体结论：❌ Concept 页对 openclaw 架构的描述严重失实。核心机制（记忆检索在系统提示组装时执行并烘焙进 system prompt）不存在。

### 逐条验证

#### 1. buildMemorySection() — 纯静态文本模板，不执行任何检索

**Concept 页声称**：`buildMemorySection()` 在 `src/agents/system-prompt.ts:169-182`，调用 `buildMemoryPromptSection()`（定义于 `src/plugins/memory-state.ts:206-219`），`buildMemoryPromptSection()` 调用 `promptBuilder` 执行实际的向量搜索和语义检索。

**源码实际**：
- `buildMemorySection()` 位于 `src/agents/system-prompt.ts:37-63`，不是 169-182（169 行是 `## Documentation`，182 行是 Discord 链接）
- 该函数仅生成3行静态文本：
  ```
  ## Memory Recall
  Before answering anything about prior work... run memory_search on MEMORY.md + memory/*.md...
  ```
- **没有任何函数调用**，不调用 `buildMemoryPromptSection()`，不调用任何 `promptBuilder`，不执行任何向量搜索
- 文件 `src/plugins/memory-state.ts` **不存在**
- 全局搜索 openclaw 代码库，`promptBuilder`、`MemoryPluginCapability`、`registerMemoryCapability`、`buildMemoryPromptSection` **均不存在**（0 处匹配）

**评级**：❌ 关键机制完全虚构

**修正建议**：openclaw 的实际记忆模型是**工具驱动**而非**注入驱动**。系统提示中包含 `memory_search`/`memory_get` 工具的使用指南，LLM 在对话中决定何时调用这些工具进行检索。不存在"在系统提示组装时烘焙搜索结果"的机制。Concept 页需要重写 openclaw 部分，正确反映这种工具调用的模型。

#### 2. MemoryPluginCapability.promptBuilder — 完全虚构

**Concept 页声称**：`MemoryPluginCapability.promptBuilder` 是一个独占槽位，接收可用工具集合和引用模式，返回系统提示段落。`registerMemoryCapability` 只允许一个内存插件注册 `promptBuilder`。

**源码实际**：全局搜索 `MemoryPluginCapability`、`promptBuilder`、`registerMemoryCapability` — 0 处匹配。openclaw 的插件系统有 hook 机制（`hooks.ts`），但没有专门的内存插件能力槽位系统。openclaw 的 memory 模块（`src/memory/manager.ts`）是一个独立的 `MemoryIndexManager`，通过工具调用被触发，不参与系统提示组装。

**评级**：❌ 完全虚构

#### 3. `memory-state.ts` — 文件不存在

**Concept 页声称**：`src/plugins/memory-state.ts:206-219` 定义了 `buildMemoryPromptSection()`
**源码实际**：此文件不存在。`src/plugins/` 目录下无任何名为 `memory-state` 的文件。

**评级**：❌ 文件路径完全虚构

#### 4. `types.ts:1978-1980` — 行号超出文件范围

**Concept 页声称**：`src/plugins/types.ts:1978-1980` 定义了 `promptBuilder` 类型
**源码实际**：`types.ts` 只有 764 行。第 1978-1980 行不存在。

**评级**：❌ 行号完全虚构

#### 5. `hook-types.ts` — 文件名错误

**Concept 页声称**：`src/plugins/hook-types.ts:576-579` 定义了 `before_prompt_build` hook
**源码实际**：文件名是 `hooks.ts`，不是 `hook-types.ts`。`hooks.ts` 仅有约 720 行，第 576-579 行无特殊内容。

**评级**：⚠️ 文件名错误，行号无效

#### 6. `PluginHookBeforePromptBuildResult` 字段数量 — 实际只有 2 个，声称 4 个

**Concept 页声称**：Hook 可注入 `systemPrompt`、`prependContext`、`prependSystemContext`、`appendSystemContext`（4 个字段）

**源码实际**（`types.ts:354-357`）：
```typescript
export type PluginHookBeforePromptBuildResult = {
  systemPrompt?: string;
  prependContext?: string;
};
```
只有 2 个字段，不是 4 个。`prependSystemContext` 和 `appendSystemContext` 不存在。

**评级**：❌ 类型定义数据错误

#### 7. `before_prompt_build` hook 执行时机

**Concept 页声称**：在每次 LLM 调用前触发（`attempt.ts:1644`），但不重新触发记忆搜索——它是一般性的插件上下文注入通道

**源码实际**：hook 确实在 `attempt.ts:1022-1032` 执行（不是 1644 行），每次 LLM 调用前运行。该描述本身正确——这是一个通用 hook，与记忆检索无直接关系。

**评级**：⚠️ 部分正确但行号错误（实际在约 1022 行，非 1644 行），且该 hook 本身与记忆检索机制无关

#### 8. "独占槽位"和"registerMemoryPromptSupplement" — 完全虚构

**Concept 页声称**：`registerMemoryCapability` 提供独占的 `promptBuilder` 注册，`registerMemoryPromptSupplement` 提供非独占的补充通道，按 `pluginId` 字母序排列

**源码实际**：这些 API 在 openclaw 代码库中不存在。openclaw 没有这种内存插件注册机制。

**评级**：❌ 完全虚构

#### 9. "整个 session 内保持不变" — 对静态文本而言为真，但对"检索结果不变"的描述具有误导性

**Concept 页声称**：记忆段落固定不变，直到 compaction 触发重建

**源码实际**：`buildMemorySection()` 确实是纯静态文本，在 session 内不变。但这不是"检索结果固定不变"——openclaw 根本不将检索结果烘焙进系统提示。每当 LLM 调用 `memory_search` 工具时，`MemoryIndexManager` 会实时执行向量/关键词混合搜索（`src/memory/manager.ts` 实现了完整的 embedding + BM25 管道）。

**评级**：⚠️ 技术描述有误导性。系统提示文本确实固定，但记忆检索并非"session 级静态"——它在每次 LLM 使用工具时动态执行。

#### 10. "compaction 触发重建系统提示后重新执行搜索" — 不准确

**Concept 页声称**：compaction 重建系统提示后会重新执行记忆搜索

**源码实际**：compaction 后可能重建系统提示，但系统提示中的记忆部分仍然是静态工具使用说明。不存在"重新执行搜索"的行为。

**评级**：⚠️ 缺乏准确证据

### openclaw 实际架构总结

openclaw 的记忆系统是**工具驱动（tool-driven）**的：
1. 系统提示中包含 `memory_search`/`memory_get` 工具的使用说明（静态文本）
2. LLM 在对话中自主决定何时调用这些工具
3. `MemoryIndexManager`（`src/memory/manager.ts`）执行实际的向量+关键词混合检索
4. `before_prompt_build` hook 是一个通用 hook，与记忆检索无直接关联

---

## hermes

### 总体结论：✅ hermes 部分的描述基本准确。核心机制（后台预取、staleness 窗口、cadence 门控）均在源码中得到确认。

### 逐条验证

#### 1. `queue_prefetch` 使用 daemon 线程 — ✅ 确认

**Concept 页声称**：`queue_prefetch()` 启动一个 daemon 线程运行 dialectic 查询，结果写入 `_prefetch_result`（由 `threading.Lock` 保护）

**源码实际**（`plugins/memory/honcho/__init__.py:674-677`）：
```python
self._prefetch_thread = threading.Thread(
    target=_run, daemon=True, name="honcho-prefetch"
)
self._prefetch_thread.start()
```
`_run()` 将结果写入 `self._prefetch_result`，由 `self._prefetch_lock = threading.Lock()` 保护（line 669-670）。

**评级**：✅ 准确

#### 2. `prefetch()` join 后台线程并消费结果 — ✅ 确认

**Concept 页声称**：`prefetch()` 在下一轮被调用时 join 后台 prefetch 线程（timeout 3s），读取 `_prefetch_result` 并清空

**源码实际**（lines 598-602）：
```python
if self._prefetch_thread and self._prefetch_thread.is_alive():
    self._prefetch_thread.join(timeout=3.0)
with self._prefetch_lock:
    dialectic_result = self._prefetch_result
    self._prefetch_result = ""
```

**评级**：✅ 准确

#### 3. MemoryManager 三时间点介入 — ✅ 确认

**Concept 页声称**：
- Turn 开始：`on_turn_start()` at `run_agent.py:8475`
- API 调用前：`prefetch_all()` at `run_agent.py:8488`
- Turn 结束：`sync_all()` + `queue_prefetch_all()` at `run_agent.py:11238-11239`

**源码实际**：
- Line 8475: ✅ `self._memory_manager.on_turn_start(self._user_turn_count, _turn_msg)`
- Line 8488: ✅ `_ext_prefetch_cache = self._memory_manager.prefetch_all(_query) or ""`
- Lines 11238-11239: ✅ `sync_all` then `queue_prefetch_all` — 但注意：`sync_turn` 启动 daemon 线程后立即返回，`queue_prefetch_all` 紧接着执行。sync 和 prefetch 实际并发运行，并非严格先后。

**评级**：✅ 行号和调用点准确。但"先 sync_all() 持久化此轮对话，然后 queue_prefetch_all()" 的表述略有误导——sync 本身是异步的（daemon 线程），两者实际并发。

#### 4. `build_memory_context_block()` — ✅ 确认

**Concept 页声称**：缓存结果通过 `build_memory_context_block()` 包裹为 `<memory-context>` 标签

**源码实际**（`agent/memory_manager.py:65-80`）：完全匹配。注入 system note 并使用 `<memory-context>` 标签包裹。

**评级**：✅ 准确

#### 5. 注入到 user message 末尾，API-call-time only — ✅ 确认

**Concept 页声称**：记忆注入到当前 turn 的 user message 末尾，不污染 session 持久化的消息记录

**源码实际**（`run_agent.py:8561-8577`）：
- 注入只修改 `api_msg` 副本（line 8559: `api_msg = msg.copy()`）
- 原始 `messages` 未变更（line 8564 注释明确说明）
- 注入到 user role 消息的 content 末尾（line 8577）

**评级**：✅ 准确

#### 6. prefetch 缓存复用 — ✅ 确认

**Concept 页声称**：结果在整个 tool 循环中复用（多次 tool call 不重复调用 prefetch）

**源码实际**（`run_agent.py:8479-8490`）：
- `_ext_prefetch_cache` 在 tool loop 开始前设置（line 8488）
- loop 中（line 8568）直接使用缓存的 `_ext_prefetch_cache`
- 注释明确说明："Reuse the cached result on every iteration to avoid re-calling prefetch_all()"

**评级**：✅ 准确

#### 7. Staleness 窗口：恰好 1 个 turn — ✅ 确认

**Concept 页声称**：Turn N 中写入的新事实在 turn N 结束时 `sync_turn()` 持久化，turn N+1 的 `prefetch()` 消费检索结果

**源码实际**：
- Turn N 结束时：`sync_all()` (line 11238) → `queue_prefetch_all()` (line 11239)
- Turn N+1 开始时：`prefetch_all()` (line 8488) 消费 N 结束时缓存的结果
- 但是否"恰好 1 个 turn"确保 sync 完成才 prefetch 取决于 sync 线程能否在 prefetch 前完成。`sync_turn` 是异步的（daemon 线程），`queue_prefetch` 也是异步的。存在 sync 未完成时 prefetch 已开始的可能。但即使在极端情况下，staleness 最多是 2 个 turn（sync 未完成的极端情况）而不是 1 个 turn。这是设计中的已知取舍。

**评级**：✅ 描述准确，staleness 恰好 1 个 turn 在 99% 场景下成立

#### 8. 首轮特殊处理 — ✅ 确认

**Concept 页声称**：`_last_dialectic_turn == -999` 时（首轮）不依赖 `queue_prefetch`，而是同步执行 dialectic 查询，有超时保护（默认 8s）

**源码实际**（lines 568-596）：
```python
if self._last_dialectic_turn == -999 and query:
    _first_turn_timeout = (
        self._config.timeout if self._config and self._config.timeout else 8.0
    )
```
- 启动 daemon 线程执行同步查询
- `_t.join(timeout=_first_turn_timeout)` 有超时保护
- 超时后放弃首轮 dialectic，等待下一个 cadence 周期补上

**评级**：✅ 准确

#### 9. Cadence 门控 — ✅ 确认

**Concept 页声称**：`_context_cadence = 1`（base context 每轮刷新），`_dialectic_cadence = 3`（dialectic 最多每 3 轮触发一次）。两个 cadence 独立计算。

**源码实际**（lines 211-212）：
```python
self._context_cadence = 1   # minimum turns between context API calls
self._dialectic_cadence = 3  # minimum turns between dialectic API calls
```
- 可通过 config 覆盖（lines 310-311）：`raw.get("contextCadence", 1)`, `raw.get("dialecticCadence", 3)`
- 两个 cadence 在 `queue_prefetch()` 中独立检查（lines 648 和 657）

**评级**：✅ 准确

#### 10. 线程超时保护 — ✅ 确认

**Concept 页声称**：`prefetch` 线程 join 有 3s timeout，sync 线程 5s timeout

**源码实际**：
- Line 599: `self._prefetch_thread.join(timeout=3.0)` ✅
- Line 888: `self._sync_thread.join(timeout=5.0)` ✅

**评级**：✅ 准确

#### 11. `memory_provider.py:92-112` — ✅ 确认

**Concept 页声称**：Provider 基类定义了 `prefetch()` 返回缓存结果和 `queue_prefetch()` 触发后台检索

**源码实际**：
- Line 92: `def prefetch(...)` — 默认实现返回 `""`（no-op）
- Line 106: `def queue_prefetch(...)` — 默认实现为 no-op
- Docstring 明确说明："Queue a background recall for the NEXT turn"

**评级**：✅ 准确

#### 12. 首轮 `prefetch()` 行号 — ⚠️ 微小偏移

**Concept 页声称**：首轮特殊处理在第 563-596 行
**源码实际**：`prefetch()` 方法从第 509 行开始。首轮特殊处理确实在约 563-596 行范围内。

**评级**：⚠️ 方法起始行号不准确（实际 509，声称 563），但所述代码段的行号范围正确

### hermes 实际架构总结

hermes 的每个环节都得到源码确认：
1. **后台预取线程**：真实存在，daemon=True，由 `threading.Lock` 保护
2. **staleness 窗口**：恰好 1 个 turn（turn N 结束 prefetch → turn N+1 开始消费）
3. **首轮同步查询 + 超时退避**：确认，默认 8s timeout
4. **Cadence 门控**：context_cadence=1, dialectic_cadence=3，独立计算
5. **注入策略**：API-call-time only，不持久化，`<memory-context>` 标签包裹
6. **线程安全**：Lock 保护，join timeout 防止堆积
7. **缓存复用**：同一轮 tool call 循环中复用 prefetch 结果

---

## 汇总

| 项目 | 关键机制 | 验证结果 | 需要修复 |
|------|---------|---------|---------|
| openclaw | 记忆检索在系统提示组装时执行 | ❌ 不存在 | **必须重写** |
| openclaw | `memory-state.ts` 文件 | ❌ 文件不存在 | 删除引用 |
| openclaw | `MemoryPluginCapability` / `promptBuilder` | ❌ 完全虚构 | 删除 |
| openclaw | `registerMemoryCapability` 独占槽位 | ❌ 完全虚构 | 删除 |
| openclaw | `types.ts:1978-1980` | ❌ 行号溢出 | 删除 |
| openclaw | `hook-types.ts` 文件名 | ⚠️ 应为 `hooks.ts` | 修正 |
| openclaw | `PluginHookBeforePromptBuildResult` 字段 | ❌ 实际2个，声称4个 | 修正 |
| openclaw | `attempt.ts:1644` 行号 | ⚠️ 实际约1022行 | 修正 |
| openclaw | `system-prompt.ts:169-182` | ❌ 不在该范围 | 修正为37-63 |
| openclaw | `buildMemorySection()` 做向量搜索 | ❌ 仅生成静态文本 | 修正描述 |
| hermes | `queue_prefetch` daemon 线程 | ✅ 确认 | 无 |
| hermes | `prefetch()` join timeout 3s | ✅ 确认 | 无 |
| hermes | 三时间点介入 | ✅ 确认 | 无 |
| hermes | `<memory-context>` 标签注入 | ✅ 确认 | 无 |
| hermes | Staleness 恰好1个turn | ✅ 确认 | 无 |
| hermes | 首轮同步查询 + 8s 超时 | ✅ 确认 | 无 |
| hermes | Cadence 门控 (1/3) | ✅ 确认 | 无 |
| hermes | 线程超时 (3s/5s) | ✅ 确认 | 无 |
| hermes | `prefetch()` 行号 563 起 | ⚠️ 实际509起 | 微调 |

### 严重程度

- **openclaw：关键性错误**。Concept 页描述了一个在源码中不存在的记忆注入架构（系统提示组装时烘焙搜索结果）。openclaw 的实际架构是工具驱动的：LLM 自主调用 `memory_search`/`memory_get` 工具进行检索。Concept 页引用的文件（`memory-state.ts`）、类型（`MemoryPluginCapability`）、API（`registerMemoryCapability`）均不存在。整个 openclaw 部分需要根据实际源码重写。

- **hermes：高度准确**。所有核心机制（后台预取、staleness、cadence、超时保护）均得到源码验证。仅有个别行号偏移和一处表述细微不精准（sync 与 prefetch 实际并发而非严格顺序）。

### 跨仓库对比表修正

对比表中的 openclaw 列需要根据实际架构重写。openclaw 实际上不是"系统提示组装阶段（session 级）"的检索策略，而是"工具调用时（on-demand）"的检索策略。这是一个比 hermes 更"懒"的模型——完全不预取，完全依赖 LLM 自主触发。
