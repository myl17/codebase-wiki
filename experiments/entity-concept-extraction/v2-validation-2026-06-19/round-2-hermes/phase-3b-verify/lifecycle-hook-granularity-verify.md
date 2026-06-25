# Lifecycle Hook Granularity -- 验证报告

**验证时间**: 2026-06-19
**验证方法**: 以 wiki 维度页和节点页中记录的源码引用为基准，逐 claim 交叉比对
**验证范围**: 仅验证 wiki 中有对应引用的 claim；wiki 中无覆盖的细节标注为"不可验证"

---

## A. 格式完整性 Checklist

| 检查项 | 状态 | 备注 |
|--------|------|------|
| Frontmatter (concept/generated/phase/instances) | ✅ | 字段齐全 |
| 标准化问题陈述 | ✅ | 一个明确的问题 |
| 核心关切 (5 条) | ✅ | 编号完整 |
| 已知权衡位置（位置 A + 位置 B） | ✅ | 两个位置各有完整分析 |
| 每个位置有：特征 + 关键机制 + 代价 + 已知实例 | ✅ | 结构一致 |
| 跨仓库对比表 | ✅ | 10 行对比维度 |
| 选择指南表 | ✅ | 8 个场景 |
| 溯源表 | ✅ | 13 行引用 |
| 关联节 | ❌ | **缺失**——没有 wikilink 关联节链接到维度页或节点页。根据项目规范，Concept 页必须有到维度页和节点页的 wikilink 关联 |

---

## B. 逐仓库逐 Claim 判定

### B1. openclaw

| # | Claim | Wiki 溯源 | 判定 | 修正建议 |
|---|-------|-----------|------|---------|
| 1 | Hook 系统有 28 个生命周期 hook | openclaw-hook-system.md:15 -- "28 个生命周期 hook" | ✅ | -- |
| 2 | PLUGIN_HOOK_NAMES 常量统一定义 | openclaw-extension-points.md:71 -- `registerHook(events, handler)` 支持以下 hook 名：列出完整 28 个 | ✅ | Name consistent |
| 3 | 28 个 hook 名称列表（before_model_resolve, before_prompt_build, llm_input, llm_output 等） | openclaw-extension-points.md:73-85 -- 列出了全部 28 个 hook 名 | ✅ | 逐一比对，名称完全一致 |
| 4 | Prompt 注入 hook: `before_prompt_build`, `before_agent_start` | openclaw-extension-points.md:87 -- "Prompt 注入 hook（`before_prompt_build`、`before_agent_start`）" | ✅ | -- |
| 5 | Hook 通过 `api.on(hookName, handler, opts)` 显式注册 | openclaw-extension-points.md:71 -- `registerHook(events, handler)` | ⚠️ | Wiki 使用 `registerHook` 而非 `api.on`。API 表面名称不同，但语义等价——`registerHook` 是 `OpenClawPluginApi` 上的方法，`api` 即该 API 实例。建议统一术语 |
| 6 | 源码位置 `src/plugins/hook-types.ts:55-126` | openclaw-extension-points.md:71 -- `^[src/plugins/hook-types.ts:55-84]` | ⚠️ | Wiki 注行号 55-84，Concept 注 55-126。行号范围差异可能因为 Concept 包含了更多类型定义（如 PluginHookHandlerMap），而 Wiki 仅注了 hook 名定义段落。建议对齐为 Wiki 的行号或标注扩展范围的原因 |
| 7 | PluginHookRegistration<K> 类型定义含 pluginId/hookName/handler/priority/source (src/plugins/hook-types.ts:687-693) | Wiki 中无此粒度的源码引用 | ⚠️ | 不可从 wiki 验证。Concept 引用的行号 687-693 远超 wiki 标注的 55-84 范围，暗示来自 direct source reading 或 deepwiki 文档 |
| 8 | fail-open/fail-closed 策略 (src/plugins/hooks.ts:134-145, 186-193) | Wiki 中无此机制的引用 | ⚠️ | 不可从 wiki 验证 |
| 9 | PLUGIN_PROMPT_MUTATION_RESULT_FIELDS 四字段 (src/plugins/hook-before-agent-start.types.ts:36-41) | Wiki 中无此机制的引用 | ⚠️ | 不可从 wiki 验证 |
| 10 | Prompt 注入 hook 是 active-memory 和记忆注入的唯一结构化入口 | openclaw-hook-system.md:15 -- "Prompt 注入类 hook（`before_prompt_build`、`before_agent_start`）允许 plugin 在 LLM 调用前修改 system prompt——是 active-memory 和记忆注入的入口" | ✅ | "唯一结构化入口"的"唯一"未在 wiki 中出现，wiki 只说"是...入口" |
| 11 | "29 个精细粒度的生命周期 hook" (第 33 行) | openclaw-hook-system.md:15 -- "28 个生命周期 hook" | ❌ | **数字错误。** Wiki 一致地说 28 个 hook。Concept 文件本身在第 15 行说"28 个 hook 名的认知负担高"，在第 33 行却说"29 个精细粒度的生命周期 hook"，在第 88 行说"29 个 hook"。应为 28 |
| 12 | "29 个 hook 通过 PluginHookRegistration<K> 类型安全注册" (第 85 行跨仓库对比表) | openclaw-hook-system.md:15 -- "28 个生命周期 hook" | ❌ | **同上，数字错误。** 应为 28 |
| 13 | "事件数量: 29" (跨仓库对比表第 88 行) | Wiki: 28 | ❌ | **数字错误。** 应为 28 |

### B2. hermes-agent

| # | Claim | Wiki 溯源 | 判定 | 修正建议 |
|---|-------|-----------|------|---------|
| 1 | 8 个网关事件: `gateway:startup`, `session:start`, `session:end`, `session:reset`, `agent:start`, `agent:step`, `agent:end`, `command:*` | hermes-agent-extension-points.md:166-175 -- 列出完全相同的 8 个事件 | ✅ | -- |
| 2 | 源码位置 `gateway/hooks.py:8-17` | hermes-agent-extension-points.md:166 -- 未直接注行号但 hermes-agent-architecture.md:214 注 `^[gateway/hooks.py:9-19]` | ⚠️ | Wiki 注 9-19，Concept 注 8-17。1 行偏移，可能是 off-by-one 编码风格差异 |
| 3 | 目录扫描加载：`~/.hermes/hooks/<name>/HOOK.yaml` + `handler.py` | hermes-agent-extension-points.md:177 -- "`~/.hermes/hooks/<name>/HOOK.yaml` + `handler.py`" | ✅ | -- |
| 4 | 源码位置 `gateway/hooks.py:84-136` | hermes-agent-extension-points.md:177 -- `^[gateway/hooks.py:80-136]` | ⚠️ | Wiki 注 80-136，Concept 注 84-136。4 行偏移。建议对齐为 Wiki 的行号 |
| 5 | 10 个插件生命周期钩子事件 (hermes_cli/plugins.py:54-65) | Wiki 中无此机制的独立记录。hermes-agent-extension-points.md 第 4 节 (Context Engines) 和第 7 节 (Event Hooks) 均未提及 `hermes_cli/plugins.py:54-65` | ⚠️ | 不可从 wiki 验证。Concept 声称两套 hook 系统并行（网关事件钩子 + 插件生命周期钩子），但 wiki 节点页和维度页中未找到对 `hermes_cli/plugins.py` 中 10 个插件生命周期事件的独立描述 |
| 6 | `register_hook()` API (hermes_cli/plugins.py:248-263) | Wiki 中无此引用 | ⚠️ | 不可从 wiki 验证 |
| 7 | `pre_llm_call` 上下文注入到用户消息末尾 (hermes_cli/plugins.py:556-567) | Wiki 中无此粒度的引用 | ⚠️ | 不可从 wiki 验证 |
| 8 | try/except 容错包装 (hermes_cli/plugins.py:570-582) | gateway/hooks.py 的事件 hook 有错误隔离说明 (hermes-agent-extension-points.md:179 -- "hook 中的异常被捕获并记录，不阻塞主 pipeline")，但 `hermes_cli/plugins.py` 的插件生命周期 hook 容错机制未在 wiki 中独立描述 | ⚠️ | 不可从 wiki 验证 |
| 9 | `pre_tool_call` 阻断机制 (hermes_cli/plugins.py:658-694 + model_tools.py:457-472) | Wiki 中无此引用 | ⚠️ | 不可从 wiki 验证 |
| 10 | 两套 hook 系统并行（网关事件钩子 + 插件生命周期钩子） | hermes-agent-event-hooks.md:17 -- "生命周期事件系统：gateway:startup、session:start、agent:step、agent:end 等事件"；hermes-agent-extension-points.md Section 7 -- 仅描述网关事件钩子。Memory Provider 有独立 hook 接口但那是另一个维度 | ⚠️ | Wiki 仅描述了网关事件钩子一套系统。两套系统并行的 claim 不可从 wiki 完全验证 |
| 11 | 网关事件数 "8（网关）+ 10（插件）= 18" | Wiki 仅记录 8 个网关事件。插件生命周期事件数不可验证 | ⚠️ | 网关 8 个确认；插件 10 个不可从 wiki 验证 |

---

## C. 核心关切验证

| 关切 # | 关切内容 | 是否在对比表体现 | 判定 |
|--------|---------|----------------|------|
| 1 | 修改/只读 hook 明确区分 | 对比表行 "优先满足的关切" openclaw 列和 "Prompt 注入" 行 | ✅ |
| 2 | 事件粒度权衡（过细 vs 过粗） | 对比表标题和每个位置的 "优先满足/接受妥协" 都直接对比了粒度 | ✅ |
| 3 | 多 handler 执行顺序与失败处理 | 对比表行 "多 handler 排序" 和 "错误处理" | ✅ |
| 4 | Prompt 注入类 hook 的稳定性要求 | 对比表行 "Prompt 注入" 和 "类型安全" | ✅ |
| 5 | Hook 发现机制（目录扫描 vs 显式注册） | 对比表行 "注册方式" 和 "新增 hook 的改动范围" | ✅ |

---

## D. 绝对化语言标记

| 位置 | 原文 | 类型 | 判定 |
|------|------|------|------|
| 第 34 行 openclaw 特征 | "通过 `PLUGIN_HOOK_NAMES` 常量**统一**定义" | "统一" | ✅ 准确——wiki 确认 28 个 hook 名在常量中集中定义 |
| 第 35 行 openclaw 特征 | "**每个** hook 在设计层面即明确划分为修改型/拦截型/只读型" | "每个" | ⚠️ Wiki 未逐一确认 28 个 hook 的分类，只说 prompt 注入类 hook 是修改型。若能从源码逐一验证则为准确，但 wiki 中无此粒度的证据 |
| 第 37 行 openclaw 特征 | "Prompt 注入类 hook 是 active-memory 和记忆注入的**唯一**结构化入口" | "唯一" | ⚠️ Wiki 只说 "是...入口"，未说 "唯一"。若存在其他注入路径（如 skills 文件直接注入 system prompt），则 "唯一" 不成立 |
| 第 75 行 跨仓库对比表 | "**所有**钩子调用 wrap 在 try/except 中" | "所有" | ⚠️ 不可从 wiki 验证。Wiki 只说网关事件 hook 的错误隔离，未说明插件生命周期 hook 的容错范围 |

---

## E. 权衡位置分类准确性

| 仓库 | Concept 中的权衡位置 | Wiki 对应 | 判定 |
|------|---------------------|-----------|------|
| openclaw | 28 个细粒度命名 Hook | openclaw-hook-system.md (ExtensionPoint) + openclaw-extension-points.md (dimension) 均描述为 28 个 hook | ✅ 分类一致 |
| hermes-agent | 8 个粗粒度事件 + 目录扫描 | hermes-agent-event-hooks.md (ExtensionPoint) + hermes-agent-extension-points.md Section 7 描述 8 个事件 + 目录扫描 | ✅ 分类一致 |

---

## F. 汇总计数

| 判定 | 数量 |
|------|------|
| ✅ 一致 | 17 |
| ⚠️ 推断/不可验证/行号偏移 | 17 |
| ❌ 错误 | 3 |
| 格式缺陷 | 1 |

---

## G. 关键发现

1. **Hook 数量错误 (❌)**：Concept 文件在多处将 openclaw 的 hook 数量写作 29，但 wiki 一致记录为 28。需全局替换为 28。

2. **行号偏移 (⚠️)**：多处源码行号与 wiki 脚注存在 1-4 行的偏移：
   - openclaw `hook-types.ts`: Concept 注 55-126 vs wiki 注 55-84
   - hermes-agent `gateway/hooks.py`: Concept 注 8-17 vs wiki 注 9-19; Concept 注 84-136 vs wiki 注 80-136

3. **大量不可验证的细节 (⚠️)**：hermes-agent 的 `hermes_cli/plugins.py` 中插件生命周期钩子系统（10 个事件、pre_llm_call、pre_tool_call、register_hook 等）的详细行号在 wiki 节点页和维度页中均无覆盖。这些 claim 可能来自 deepwiki 文档或直接源码阅读，但无法从本仓库的 wiki 溯源验证。建议：
   - 若这些 claim 确实正确，应在 wiki 中补充对应的节点页或维度页引用
   - 或在 Concept 溯源表中标注这些引用来自 deepwiki 而非 wiki 节点页

4. **缺少关联节 (❌ format)**：Concept 文件末尾缺少 wikilink 关联节（对比其他两个 Concept 文件都有 `## 关联` 节链接到维度页）。
