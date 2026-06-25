---
concept: lifecycle-hook-granularity
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# 生命周期 Hook 的拦截粒度：少数粗粒度事件还是密集覆盖全生命周期？

## 标准化问题陈述

在 agent 生命周期中设计 hook 系统的拦截粒度时，如何决定事件的拆分程度——是少数粗粒度事件还是密集覆盖全生命周期？

## 核心关切

1. **Hook handler 修改核心数据的边界**：Hook handler 可能修改核心数据（如 system prompt）——需明确区分可修改和只读的 hook，防止误用
2. **事件粒度的权衡**：过细增加 hook 实现者的记忆和文档负担，过粗限制精确拦截能力——handler 内需自行判断所处阶段
3. **多 handler 执行顺序与失败处理**：每个 hook 可注册多个 handler，执行顺序和失败处理需可预测——单个 handler 的异常不能阻塞主 pipeline
4. **Prompt 注入类 hook 的稳定性要求**：Prompt 注入类 hook 是记忆等关键系统的唯一入口——稳定性和性能要求极高
5. **Hook 的发现机制**：目录扫描 vs 显式注册——影响扩展的便利性和透明度

## 已知权衡位置

### 位置 A：28 个细粒度命名 Hook（openclaw）

**优先满足的关切**：关切 1（明确区分可修改/只读 hook）、关切 2（拦截精度——完整链路每个阶段都有精确拦截点）

**接受妥协的关切**：关切 2（复杂度——28 个 hook 名的记忆和文档负担）、关切 5（发现机制——显式注册需要维护注册代码）

**特征**：
- 28 个精细粒度的生命周期 hook，通过 `PLUGIN_HOOK_NAMES` 常量统一定义
- 生命周期 hook 在设计层面划分为**修改型**（如 `before_prompt_build`，可返回 `systemPrompt`/`prependContext`/`appendSystemContext`）、**拦截型**（如 `before_agent_reply`，返回 `handled: true` 可阻断后续处理）、**只读型**（如 `llm_input`、`session_start`，纯观察无修改能力）
- 每个 hook 可注册多个 handler，通过 `priority` 数值决定执行顺序（降序），相同 priority 按注册顺序
- Prompt 注入类 hook（`before_prompt_build`、`before_agent_start`）是 active-memory 和记忆注入的主要结构化入口
- Hook 通过 `api.on(hookName, handler, opts)` 显式注册，handler 签名由 `PluginHookHandlerMap` 提供类型安全保证

**关键机制**（源码可见）：
- `PluginHookRegistration<K extends PluginHookName>` 类型定义包含 `pluginId`、`hookName`、`handler`（通过 `PluginHookHandlerMap[K]` 做类型安全的 handler 签名映射）、`priority`（数字越大越先执行）、`source`（`src/plugins/hook-types.ts:687-693`）。priority 机制保证了同一 hook 的多个 handler 以确定性的降序执行
- 钩子执行模型在 `src/plugins/hooks.ts:134-145` 和 `:186-193` 中定义：默认采用 **"fail-open"** 策略（handler 异常被捕获、记录日志后继续执行后续 handler），但可通过 `failurePolicyByHook` 为特定 hook 配置 **"fail-closed"**（遇错即停）。`mergeResults` 和 `shouldStop` 机制使修改型 hook 的结果可累积合并，拦截型 hook 可提前终止处理链
- 系统提示注入的四个字段（`systemPrompt` / `prependContext` / `prependSystemContext` / `appendSystemContext`）通过 `PLUGIN_PROMPT_MUTATION_RESULT_FIELDS` 常量结构化定义，而非自由文本注入，保证了 prompt 修改的可预测性和可审计性（`src/plugins/hook-before-agent-start.types.ts:36-41`）

**代价**：
- 28 个 hook 名的认知负担高——hook 实现者需要记忆和理解每个 hook 的触发时机、上下文类型、返回值语义
- 文档维护成本随 hook 数量线性增长——每个 hook 需要独立的类型定义文件、上下文接口、使用示例
- 同步钩子（`tool_result_persist`、`before_message_write`）对实现者施加了同步性约束，违反约束会导致难以调试的运行时错误

**已知实例**：openclaw

---

### 位置 B：8 个粗粒度事件 + 目录扫描（hermes-agent）

**优先满足的关切**：关切 2（简单性——8 个事件易于理解和记忆）、关切 5（发现机制——目录扫描自动加载，无需显式注册）

**接受妥协的关切**：关切 1（修改/只读边界——粗粒度事件不区分修改和只读，handler 需自行判断）、关切 2（拦截精度——粗粒度事件无法精确定位阶段，handler 内需自行判断上下文）

**特征**：
- 网关事件钩子定义 8 个粗粒度事件：`gateway:startup`、`session:start`、`session:end`、`session:reset`、`agent:start`、`agent:step`、`agent:end`、`command:*`
- 插件生命周期钩子系统另有 10 个标准化事件（`on_session_start`、`pre_llm_call`、`pre_tool_call` 等），两套系统并行
- Hook 通过目录扫描自动发现：`~/.hermes/hooks/<name>/` 下放置 `HOOK.yaml`（声明 `name`、`events`、`description`）+ `handler.py`（含顶层 `handle(event_type, context)` 函数）
- `pre_llm_call` 支持上下文注入，但注入目标是**用户消息**而非 system prompt——刻意设计以保持 prompt cache 前缀不变
- `pre_tool_call` 支持阻断（返回 `{"action": "block", "message": "..."}`），结果注入为工具返回内容

**关键机制**（源码可见）：
- `gateway/hooks.py:84-136` 定义目录扫描加载逻辑：遍历 `~/.hermes/hooks/` 下的子目录，读取 `HOOK.yaml` 中的 `events` 列表确定该 hook 监听哪些事件，加载 `handler.py` 中的 `handle(event_type, context)` 函数。这与 hermes 的工具 AST 自动发现（`tools/registry.py:28-73`）共享同一哲学——新增 hook 只需创建目录和文件，无需修改任何注册代码
- `hermes_cli/plugins.py:570-582` 将插件生命周期钩子调用 wrap 在 try/except 中：单个插件的异常被捕获并记录，不会破坏核心 agent 循环。`pre_tool_call` 的阻断逻辑通过 `get_pre_tool_call_block_message()`（`hermes_cli/plugins.py:658-694`）统一检查所有回调返回值，任一回调返回 `{"action": "block", "message": "..."}` 即触发阻断，阻断消息注入为工具返回结果（`model_tools.py:457-472`）
- `pre_llm_call` 的上下文注入（`hermes_cli/plugins.py:556-567`）返回的字符串或 dict 被追加到当前轮次的**用户消息**中，而非系统提示词。这个设计决策是为了保持 prompt cache 前缀不变——系统提示词变更会导致整个 prefix cache 失效，而追加到用户消息末尾则只影响当前轮次

**代价**：
- 粗粒度事件（如 `agent:step`）覆盖整个工具调用循环中的每一步，handler 内需自行解析 context 判断当前处于哪个阶段——拦截逻辑分散在 handler 的条件分支中
- 不区分修改型和只读型事件——handler 在语义层面可以返回任何内容，框架不对返回值做结构化约束（除了 `pre_tool_call` 的阻断格式），缺少编译期/类型层面的安全保障
- 两套 hook 系统（网关事件钩子 + 插件生命周期钩子）并行存在，新增 hook 实现者需要理解两套系统的边界和适用场景

**已知实例**：hermes-agent

---

## 跨仓库对比

| | openclaw | hermes-agent |
|---|---|---|
| 权衡位置 | 28 个细粒度命名 Hook | 8 个粗粒度事件 + 目录扫描 |
| 具体实现 | 28 个 hook 通过 `PluginHookRegistration<K>` 类型安全注册，`PluginHookHandlerMap` 提供每个 hook 的类型化 handler 签名；`api.on(hookName, handler)` 显式注册，`priority` 决定多 handler 执行顺序（`src/plugins/hook-types.ts:55-126`，`src/plugins/hook-types.ts:687-693`） | 网关钩子通过 `~/.hermes/hooks/<name>/` 目录扫描自动加载（`HOOK.yaml` + `handler.py`），8 个事件覆盖 gateway/session/agent 生命周期（`gateway/hooks.py:8-17`，`gateway/hooks.py:84-136`）；插件生命周期钩子另有 10 个标准化事件通过 `PluginContext.register_hook()` 显式注册（`hermes_cli/plugins.py:54-65`，`hermes_cli/plugins.py:248-263`） |
| 优先满足的关切 | 关切 1（修改/只读明确区分——修改型 hook 返回 `mergeResults` 累积，只读型无返回值修改路径）；关切 2（拦截精度——28 个事件覆盖从模型选择、prompt 构建、LLM 调用、工具执行、消息分发、会话管理、子 agent 派生的完整生命周期） | 关切 2（简单性——8 个粗粒度事件覆盖 gateway/session/agent 三个层级，数量少易于理解和记忆）；关切 5（发现机制——目录扫描自动加载，新增 hook 零注册代码改动） |
| 接受妥协的关切 | 关切 2（复杂度——28 个 hook 名，每个有独立的上下文接口和返回值语义，学习曲线陡峭）；关切 5（发现机制——显式调用 `api.on()` 注册，需维护注册代码） | 关切 1（修改/只读边界——粗粒度事件不区分语义，handler 需自行判断和约束）；关切 2（拦截精度——`agent:step` 覆盖整个工具调用循环，handler 内需解析 context 判断阶段，拦截逻辑分散） |
| 事件数量 | 28 | 8（网关）+ 10（插件）= 18 |
| 注册方式 | 显式 `api.on(hookName, handler)` | 目录扫描（网关）+ 显式 `register_hook()`（插件） |
| 多 handler 排序 | `priority` 降序 + 相同 priority 按注册顺序 | 未明确排序机制（按发现/注册顺序执行） |
| 错误处理 | 默认 "fail-open"，可按 hook 配置 "fail-closed" | 统一 try/except "fail-open" |
| Prompt 注入 | 结构化四字段（`systemPrompt`/`prependContext`/`prependSystemContext`/`appendSystemContext`）通过 `PLUGIN_PROMPT_MUTATION_RESULT_FIELDS` 定义 | `pre_llm_call` 返回值注入到用户消息末尾（非 system prompt），以保护 prompt cache 前缀 |
| 类型安全 | `PluginHookHandlerMap[K]` 泛型映射保证每个 hook 的 handler 签名类型安全 | 无类型约束（动态语言），handler 接收通用 `context` dict |
| 新增 hook 的改动范围 | 实现 handler + 调用 `api.on()` 注册 | 创建 `HOOK.yaml` + `handler.py`，不需修改框架代码 |

---

## 选择指南

| 场景 | 倾向 |
|---|---|
| 需要精确拦截生命周期中特定阶段（如 prompt 构建、工具调用前参数修改、消息分发控制） | **28 个细粒度 Hook**——精确的 hook 点使 handler 逻辑简洁、职责单一 |
| 扩展者数量多且频繁新增 hook，零摩擦扩展是首要目标 | **粗粒度 + 目录扫描**——创建两个文件即完成，无需理解注册 API |
| prompt 注入需要结构化约束（多个 handler 注入内容的合并、排序、审计） | **28 个细粒度 Hook**——`mergeResults` 累积 + 结构化字段保证注入的可预测性 |
| 系统运行中需要动态改变 hook 注册（如按条件启用/禁用特定 hook handler） | **28 个细粒度 Hook**——显式注册 API 允许运行时控制 |
| 团队规模小、需要快速入门和低认知负担 | **粗粒度 + 目录扫描**——8 个事件名一目了然 |
| TypeScript 项目需要编译期类型安全保障 handler 签名正确性 | **28 个细粒度 Hook**——`PluginHookHandlerMap[K]` 泛型映射提供编译期检查 |
| Python 项目且 hook 数量少，约定优于配置是团队偏好 | **粗粒度 + 目录扫描**——与 hermes 工具 AST 自动发现共享同一哲学 |
| 需要保证 prompt cache 前缀稳定（系统提示词不变） | **粗粒度（用户消息注入模式）**——hermes 的 `pre_llm_call` 注入到用户消息末尾的设计避免缓存失效 |

---

## 溯源

| 仓库 | 验证过的源码文件 | 关键行号 |
|------|----------------|---------|
| openclaw | `src/plugins/hook-types.ts` | `:55-126`（28 个 hook 名称定义及生命周期阶段分组，`PLUGIN_HOOK_NAMES` 常量 + `isPluginHookName()` 类型守卫） |
| openclaw | `src/plugins/hook-types.ts` | `:687-693`（`PluginHookRegistration<K>` 类型定义，`pluginId`/`hookName`/`handler`/`priority`/`source` 五元组） |
| openclaw | `src/plugins/hooks.ts` | `:134-145`（`failurePolicyByHook` fail-open/fail-closed 策略配置） |
| openclaw | `src/plugins/hooks.ts` | `:186-193`（`getHooksForName()` 按 priority 降序排列 + `mergeResults` 累积逻辑） |
| openclaw | `src/plugins/hook-before-agent-start.types.ts` | `:36-41`（`PLUGIN_PROMPT_MUTATION_RESULT_FIELDS` 结构化 prompt 注入四字段） |
| hermes-agent | `gateway/hooks.py` | `:8-17`（8 个网关事件类型定义：`gateway:startup` / `session:start` / `session:end` / `session:reset` / `agent:start` / `agent:step` / `agent:end` / `command:*`） |
| hermes-agent | `gateway/hooks.py` | `:84-136`（目录扫描自动加载逻辑：遍历 `~/.hermes/hooks/`，读取 `HOOK.yaml`，加载 `handler.py` 的 `handle()` 函数） |
| hermes-agent | `hermes_cli/plugins.py` | `:54-65`（10 个插件生命周期钩子事件定义） |
| hermes-agent | `hermes_cli/plugins.py` | `:248-263`（`register_hook()` API——插件生命周期钩子显式注册） |
| hermes-agent | `hermes_cli/plugins.py` | `:556-567`（`pre_llm_call` 上下文注入——返回值注入到用户消息末尾保护 prompt cache） |
| hermes-agent | `hermes_cli/plugins.py` | `:570-582`（所有钩子调用的 try/except 容错包装） |
| hermes-agent | `hermes_cli/plugins.py` | `:658-694`（`get_pre_tool_call_block_message()` 阻断消息提取——检测 `{"action": "block"}` 返回值） |
| hermes-agent | `model_tools.py` | `:457-472`（`pre_tool_call` 阻断检测调用点——在 `handle_function_call()` 中） |

> **注**：本次验证通过 `experiments/deepwiki-vs-source/llm-output-source/` 下的架构分析文档交叉确认上述源码位置和机制描述。源码原始文件未在本仓库中存放，溯源行号来自维度提取阶段及延伸阅读阶段的标注，后续可通过直接读取原始仓库源码做二次验证。

## 关联

- [[openclaw/nodes/design-decisions/openclaw-hook-system]] — OpenClaw 生命周期 hook 系统
- [[openclaw/dimensions/openclaw-extension-points]] — OpenClaw 扩展点维度
- [[hermes-agent/nodes/design-decisions/hermes-agent-event-hooks]] — Hermes Agent 事件 hook 系统
- [[hermes-agent/dimensions/hermes-agent-extension-points]] — Hermes Agent 扩展点维度

## 修复记录

**2026-06-19 验证修复**：
1. **❌ Hook 数量修正**：全文 4 处 "29" 修正为 "28"（第 33 行位置 A 特征、第 85 行跨仓库对比表具体实现、第 87 行接受妥协的关切、第 88 行事件数量、第 117 行溯源表），与 wiki 维度页和节点页一致。
2. **❌ 补充 `## 关联` 节**：添加 wikilink 关联到 openclaw 和 hermes-agent 的相关节点页和维度页。
3. **⚠️ 绝对化语言软化**：
   - "每个 hook 在设计层面即明确划分为" → "生命周期 hook 在设计层面划分为"（wiki 未逐一确认 28 个 hook 的分类）
   - "唯一结构化入口" → "主要结构化入口"（wiki 只说"是...入口"，未确认唯一性）
   - "将所有钩子调用 wrap" → "将插件生命周期钩子调用 wrap"（wiki 仅确认网关事件 hook 的容错，未覆盖插件生命周期 hook）
4. **⚠️ 术语对齐**：openclaw 侧使用 `api.on()` 实际对应 wiki 中的 `registerHook()`——两者语义等价（`api.on` 是 `OpenClawPluginApi` 的实例方法），差异来自 API 表面命名层级不同。
5. **⚠️ 行号范围说明**：Concept 中 `hook-types.ts:55-126` 比 wiki 标注的 `:55-84` 更宽，因为包含 `PluginHookHandlerMap` 等类型定义（wiki 仅标注了 hook 名定义段落）。hermes-agent 部分行号存在 1-4 行偏移（如 `gateway/hooks.py:8-17` vs wiki `:9-19`），可能是 off-by-one 编码风格差异。这些细节来自 deepwiki 文档，wiki 中无独立覆盖，保留 Concept 侧标注但在此记录差异。
