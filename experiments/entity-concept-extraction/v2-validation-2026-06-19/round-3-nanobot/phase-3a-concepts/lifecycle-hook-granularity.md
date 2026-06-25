---
concept: lifecycle-hook-granularity
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
  - nanobot
---

# 生命周期 Hook 的拦截粒度：少数粗粒度事件还是密集覆盖全生命周期？

## 标准化问题陈述

在 agent 生命周期中设计 hook 系统的拦截粒度时，如何决定事件的拆分程度——是少数粗粒度事件还是密集覆盖全生命周期？此外，不同语义类型的 hook（内容变换 vs 事件通知）是否应采用不同的执行策略？

## 核心关切

1. **Hook handler 修改核心数据的边界**：Hook handler 可能修改核心数据（如 system prompt）——需明确区分可修改和只读的 hook，防止误用
2. **事件粒度的权衡**：过细增加 hook 实现者的记忆和文档负担，过粗限制精确拦截能力——handler 内需自行判断所处阶段
3. **多 handler 执行顺序与失败处理**：每个 hook 可注册多个 handler，执行顺序和失败处理需可预测——单个 handler 的异常不能阻塞主 pipeline
4. **Prompt 注入类 hook 的稳定性要求**：Prompt 注入类 hook 是记忆等关键系统的唯一入口——稳定性和性能要求极高
5. **Hook 的发现机制**：目录扫描 vs 显式注册——影响扩展的便利性和透明度
6. **Hook 语义分化与执行策略匹配**：不同语义的 hook（内容变换 vs 事件通知）对执行策略有不同要求——内容变换需要有序串联保证确定性输出，事件通知需要独立执行避免单点阻塞影响主流程

## 已知权衡位置

### 位置 A：28 个细粒度命名 Hook（openclaw）

**优先满足的关切**：关切 1（明确区分可修改/只读 hook）、关切 2（拦截精度——完整链路每个阶段都有精确拦截点）

**接受妥协的关切**：关切 2（复杂度——28 个 hook 名的记忆和文档负担）、关切 5（发现机制——显式注册需要维护注册代码）

**特征**：
- 29 个精细粒度的生命周期 hook，通过 `PLUGIN_HOOK_NAMES` 常量统一定义
- 每个 hook 在设计层面即明确划分为**修改型**（如 `before_prompt_build`，可返回 `systemPrompt`/`prependContext`/`appendSystemContext`）、**拦截型**（如 `before_agent_reply`，返回 `handled: true` 可阻断后续处理）、**只读型**（如 `llm_input`、`session_start`，纯观察无修改能力）
- 每个 hook 可注册多个 handler，通过 `priority` 数值决定执行顺序（降序），相同 priority 按注册顺序
- Prompt 注入类 hook（`before_prompt_build`、`before_agent_start`）是 active-memory 和记忆注入的唯一结构化入口
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
- `hermes_cli/plugins.py:570-582` 将所有钩子调用 wrap 在 try/except 中：单个插件的异常被捕获并记录，不会破坏核心 agent 循环。`pre_tool_call` 的阻断逻辑通过 `get_pre_tool_call_block_message()`（`hermes_cli/plugins.py:658-694`）统一检查所有回调返回值，任一回调返回 `{"action": "block", "message": "..."}` 即触发阻断，阻断消息注入为工具返回结果（`model_tools.py:457-472`）
- `pre_llm_call` 的上下文注入（`hermes_cli/plugins.py:556-567`）返回的字符串或 dict 被追加到当前轮次的**用户消息**中，而非系统提示词。这个设计决策是为了保持 prompt cache 前缀不变——系统提示词变更会导致整个 prefix cache 失效，而追加到用户消息末尾则只影响当前轮次

**代价**：
- 粗粒度事件（如 `agent:step`）覆盖整个工具调用循环中的每一步，handler 内需自行解析 context 判断当前处于哪个阶段——拦截逻辑分散在 handler 的条件分支中
- 不区分修改型和只读型事件——handler 在语义层面可以返回任何内容，框架不对返回值做结构化约束（除了 `pre_tool_call` 的阻断格式），缺少编译期/类型层面的安全保障
- 两套 hook 系统（网关事件钩子 + 插件生命周期钩子）并行存在，新增 hook 实现者需要理解两套系统的边界和适用场景

**已知实例**：hermes-agent

---

### 位置 C：CompositeHook 语义分化 — 管道 + 扇出（nanobot）

**优先满足的关切**：关切 6（语义分化——`finalize_content` 是内容变换用纯函数管道串联保证有序加工，其余五法 `before_iteration` / `on_stream` / `on_stream_end` / `before_execute_tools` / `after_iteration` 是事件通知用扇出避免单点阻塞）

**接受妥协的关切**：关切 2（复杂度——两种执行模式并存增加理解成本，实现者需要区分「我的 hook 结果是可累积的还是纯副作用」）、关切 2（拦截精度——仅 6 个生命周期拦截点，多轮迭代内的精确阶段（如 prompt 构建、LLM 调用前后、消息分发）不可单独拦截）

**特征**：
- 六个生命周期拦截点覆盖一次 agent 迭代的核心环节：迭代前（`before_iteration`）、流式输出中（`on_stream`）、流式输出结束（`on_stream_end`）、工具执行前（`before_execute_tools`）、迭代后（`after_iteration`）、内容最终化（`finalize_content`）
- `CompositeHook` 按 hook 语义自动选择执行策略：`finalize_content` 是**管道模式**——多个 handler 按注册顺序串联执行，前一个 handler 的返回值作为下一个 handler 的输入，保证内容变换的有序性和确定性；其余五法是**扇出模式**——每个 handler 独立执行，任一 handler 异常不阻塞其他 handler 和主流程
- Hook 通过 `AgentLoop._extra_hooks` 列表运行时注入，外部插件在 AgentLoop 初始化时向列表追加 `AgentHook` 实例，无需修改核心代码
- 每个 hook 方法接收统一的 `HookContext`，包含当前 `iteration` 计数、`agent` 引用等上下文信息

**关键机制**（源码可见）：
- `agent/hook.py:29-55` 定义 `AgentHook` 基类和六个生命周期拦截点的方法签名：`before_iteration`、`on_stream`、`on_stream_end`、`before_execute_tools`、`after_iteration`、`finalize_content`。每个方法接收 `HookContext` 并返回可选值（`finalize_content` 返回 `str | None`，其余方法返回 `None`）
- `agent/hook.py:57-103` 定义 `CompositeHook` 串联逻辑：`finalize_content` 将多个 hook 的返回值**管道串联**——每个 hook 接收上一个 hook 处理后的内容作为输入，形成 `f_n(...(f_2(f_1(content))))` 的确定性变换链；其余五法**扇出**——遍历所有 hook 独立调用，每个被 try/except 包裹，单 hook 异常不中断其他 hook 的执行
- `agent/loop.py:180` 中 `_extra_hooks: list[AgentHook]` 字段为外部插件提供运行时注入入口——插件在 AgentLoop 实例化后向该列表追加自定义 `AgentHook` 子类实例，无需修改 `agent/loop.py` 源码

**代价**：
- 两种执行模式（管道 vs 扇出）并存，hook 实现者需要理解不同 hook 方法的执行语义——`finalize_content` 的返回值会改变下游 hook 的输入，而其余方法纯副作用
- 事件数仅 6 个，拦截精度低于 openclaw 的 28 个——迭代内的精确阶段（如 prompt 构建前后、LLM 调用前后）不可单独拦截，handler 如需感知这些阶段需自行解析 context 或拓展钩子
- 管道模式下执行顺序依赖注入顺序（`_extra_hooks` 列表的 append 顺序），无显式的 priority 或排序机制——多插件协作时顺序依赖隐式约定

**已知实例**：nanobot

---

## 跨仓库对比

| | openclaw | hermes-agent | nanobot |
|---|---|---|---|
| 权衡位置 | 28 个细粒度命名 Hook | 8 个粗粒度事件 + 目录扫描 | CompositeHook 语义分化（管道 + 扇出） |
| 具体实现 | 29 个 hook 通过 `PluginHookRegistration<K>` 类型安全注册，`PluginHookHandlerMap` 提供每个 hook 的类型化 handler 签名；`api.on(hookName, handler)` 显式注册，`priority` 决定多 handler 执行顺序（`src/plugins/hook-types.ts:55-126`，`src/plugins/hook-types.ts:687-693`） | 网关钩子通过 `~/.hermes/hooks/<name>/` 目录扫描自动加载（`HOOK.yaml` + `handler.py`），8 个事件覆盖 gateway/session/agent 生命周期（`gateway/hooks.py:8-17`，`gateway/hooks.py:84-136`）；插件生命周期钩子另有 10 个标准化事件通过 `PluginContext.register_hook()` 显式注册（`hermes_cli/plugins.py:54-65`，`hermes_cli/plugins.py:248-263`） | 6 个生命周期拦截点通过 `AgentHook` 基类定义，`CompositeHook` 按语义自动选择执行策略——`finalize_content` 管道串联保证内容变换有序性，其余五法扇出确保事件通知互不阻塞；`_extra_hooks` 列表运行时注入实现零侵入扩展（`agent/hook.py:29-103`，`agent/loop.py:180`） |
| 优先满足的关切 | 关切 1（修改/只读明确区分——修改型 hook 返回 `mergeResults` 累积，只读型无返回值修改路径）；关切 2（拦截精度——28 个事件覆盖从模型选择、prompt 构建、LLM 调用、工具执行、消息分发、会话管理、子 agent 派生的完整生命周期） | 关切 2（简单性——8 个粗粒度事件覆盖 gateway/session/agent 三个层级，数量少易于理解和记忆）；关切 5（发现机制——目录扫描自动加载，新增 hook 零注册代码改动） | 关切 6（语义分化——内容变换用管道保证确定性有序加工，事件通知用扇出避免单点阻塞）；关切 3（多 handler 执行——管道模式天然保证顺序，扇出模式天然保证隔离） |
| 接受妥协的关切 | 关切 2（复杂度——29 个 hook 名，每个有独立的上下文接口和返回值语义，学习曲线陡峭）；关切 5（发现机制——显式调用 `api.on()` 注册，需维护注册代码） | 关切 1（修改/只读边界——粗粒度事件不区分语义，handler 需自行判断和约束）；关切 2（拦截精度——`agent:step` 覆盖整个工具调用循环，handler 内需解析 context 判断阶段，拦截逻辑分散） | 关切 2（两种执行模式增加理解成本——实现者需区分管道和扇出的语义差异）；关切 2（拦截精度——仅 6 个事件，迭代内精确阶段不可单独拦截） |
| 事件数量 | 29 | 8（网关）+ 10（插件）= 18 | 6 |
| 注册方式 | 显式 `api.on(hookName, handler)` | 目录扫描（网关）+ 显式 `register_hook()`（插件） | `_extra_hooks` 列表运行时注入 |
| 多 handler 排序 | `priority` 降序 + 相同 priority 按注册顺序 | 未明确排序机制（按发现/注册顺序执行） | `finalize_content` 按注入顺序管道串联；其余五法扇出无排序需求 |
| 错误处理 | 默认 "fail-open"，可按 hook 配置 "fail-closed" | 统一 try/except "fail-open" | 扇出模式：单 hook 异常被 try/except 捕获，不影响其他 hook；管道模式：异常中断管道传播 |
| Prompt 注入 | 结构化四字段（`systemPrompt`/`prependContext`/`prependSystemContext`/`appendSystemContext`）通过 `PLUGIN_PROMPT_MUTATION_RESULT_FIELDS` 定义 | `pre_llm_call` 返回值注入到用户消息末尾（非 system prompt），以保护 prompt cache 前缀 | 无独立 prompt 注入 hook；`finalize_content` 管道可对最终输出做后处理变换 |
| 类型安全 | `PluginHookHandlerMap[K]` 泛型映射保证每个 hook 的 handler 签名类型安全 | 无类型约束（动态语言），handler 接收通用 `context` dict | 无类型约束（动态语言），`AgentHook` 基类方法签名作为约定，`HookContext` 统一上下文 |
| 新增 hook 的改动范围 | 实现 handler + 调用 `api.on()` 注册 | 创建 `HOOK.yaml` + `handler.py`，不需修改框架代码 | 实现 `AgentHook` 子类 + 向 `_extra_hooks` 列表 append，不需修改核心循环代码 |

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
| hook 语义明确分化——部分需要有序内容变换、部分只需事件通知 | **语义分化（管道 + 扇出）**——`finalize_content` 管道串联保证内容变换确定性，其余事件扇出互不阻塞 |
| 需要多个 handler 对同一内容做有序后处理变换（如敏感词过滤 → 格式规范化 → 长度截断） | **语义分化（管道 + 扇出）**——管道模式天然支持 `f3(f2(f1(content)))` 的确定性变换链 |
| 事件数极少（<10）且扩展者需要快速理解整个 hook 系统全貌 | **语义分化（管道 + 扇出）**——6 个事件的认知负担极低，`_extra_hooks` 注入模式零框架改动 |

---

## 溯源

| 仓库 | 验证过的源码文件 | 关键行号 |
|------|----------------|---------|
| openclaw | `src/plugins/hook-types.ts` | `:55-126`（29 个 hook 名称定义及生命周期阶段分组，`PLUGIN_HOOK_NAMES` 常量 + `isPluginHookName()` 类型守卫） |
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
| nanobot | `agent/hook.py` | `:29-55`（六个生命周期拦截点方法签名定义：`before_iteration` / `on_stream` / `on_stream_end` / `before_execute_tools` / `after_iteration` / `finalize_content`，`AgentHook` 基类 + `HookContext` 上下文） |
| nanobot | `agent/hook.py` | `:57-103`（`CompositeHook` 串联逻辑——`finalize_content` 纯函数管道串联 `f_n(...(f_2(f_1(content))))`，其余五法扇出 try/except 独立执行） |
| nanobot | `agent/loop.py` | `:180`（`_extra_hooks: list[AgentHook]` 运行时注入入口——外部插件零侵入追加自定义 hook） |

> **注**：本次验证通过 `experiments/deepwiki-vs-source/llm-output-source/` 下的架构分析文档交叉确认上述源码位置和机制描述。源码原始文件未在本仓库中存放，溯源行号来自维度提取阶段及延伸阅读阶段的标注，后续可通过直接读取原始仓库源码做二次验证。
