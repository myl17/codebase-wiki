# 验证报告：subsystem-assembly-visibility

## 格式完整性
- [x] 问题陈述是"如何..."问题形式 — `一个由 10+ 子系统组成的 agent 框架，如何将所有子系统的初始化、依赖注入和生命周期管理集中在一个位置`
- [x] 核心关切列表 >= 2 条 — 共 4 条（可发现性、可测试性、扩展成本、规模膨胀）
- [x] 每个权衡位置有"优先满足"和"接受妥协"两个字段 — 位置 A（中央编排器）和位置 B（单体 Hub 集中组装）均有
- [x] 跨仓库对比表列数 = 仓库数 — 2 列（hermes-agent / nanobot）
- [x] 溯源表完整 — 有

---

## 逐仓库验证

### hermes-agent

**Claim 1**: "`AIAgent.__init__()` at `run_agent.py:559-1631`"

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py:559-1631`
代码摘要：`__init__` 方法签名起于 line 559 (`def __init__(self, ...)`)，方法体止于 line 1631。下一方法 `reset_session_state` 起于 line 1632。range 559-1631 共 1073 行（含 def 行）。
判定：✅ 行号范围精确。

---

**Claim 2**: "__init__ 规模 ~1072 行（559-1631）"

源码：同上
判定：⚠️ 含 `def __init__()` 签名行共 1073 行，纯方法体约 1072 行。表述为"1072 行"有 1 行的轻微偏差。建议明确为"约 1073 行（559-1631）"或"1072 行方法体"。

---

**Claim 3**: "provider 路由分支: 898-1070，4 条 provider 分支（anthropic_messages / bedrock_converse / chat_completions / codex_responses 四条路径各有独立 client 构建逻辑）"

源码：`run_agent.py:898-1070`
代码摘要：
- Line 898: `if self.api_mode == "anthropic_messages":` — Anthropic SDK 路径（含 Bedrock Anthropic 子路径，line 903-909）
- Line 937: `elif self.api_mode == "bedrock_converse":` — AWS Bedrock boto3 直接路径
- Line 964: `else:` — 覆盖 `chat_completions` 和 `codex_responses` 两种 api_mode，两者**共享同一 else 分支**。两者差异在 `run_conversation` 中体现（line 2937: `'/responses' if self.api_mode == 'codex_responses' else '/chat/completions'`），而非在 `__init__` 中。

判定：⚠️ api_mode 自动检测（line 690）区分 4 种模式，但在 `__init__` 的实际 client 构造分支中，`chat_completions` 和 `codex_responses` 共享同一 else 分支（line 964），并非"各有独立 client 构建逻辑"。建议修正为"三条 client 构造分支（anthropic_messages / bedrock_converse / chat_completions+codex_responses 共享 else），在 run_conversation 中进一步根据 api_mode 分化行为"。

---

**Claim 4**: "context compressor 插件加载（`run_agent.py:1432-1504`）"

源码：`run_agent.py:1432-1504`
代码摘要：line 1432-1504 包含 context engine 选择逻辑（配置驱动，三步探测：plugins/context_engine → general plugin system → built-in ContextCompressor）以及 plugin engine 的 model update 调用/ContextCompressor fallback 构造。
判定：✅ 行号范围准确。

---

**Claim 5**: "memory provider 热插拔（`run_agent.py:1238-1315`）"

源码：`run_agent.py:1238-1315`
代码摘要：line 1238 注释 `# Memory provider plugin`，包含 Honcho 自动迁移（1245-1268）、provider 加载（1270-1276）、`_memory_manager.initialize_all()` 热插拔激活（1308）、异常处理（1313-1315）。
判定：✅ 行号范围、热插拔机制描述均准确。

---

**Claim 6**: "外部 memory provider 插件（Honcho 等）在 `run_agent.py:1238-1315` 处通过 `_memory_manager.initialize_all()` 热插拔激活，无需修改 AIAgent 类签名"

源码：`run_agent.py:1271-1308`
代码摘要：line 1271 导入 `MemoryManager`，line 1273 创建实例，line 1274 `load_memory_provider` 加载插件，line 1276 `add_provider`，line 1308 `initialize_all(**kwargs)` 激活。整个过程未修改 `AIAgent.__init__` 签名。
判定：✅ 热插拔描述准确。外部插件通过 `MemoryManager + load_memory_provider` 注册，不侵入 AIAgent 类签名。

---

**Claim 7**: "单文件 11510 行"

源码：`wc -l /Users/yuanlimiao/Work/agent_harness/hermes-agent/run_agent.py` → 11510
判定：✅ 精确匹配。

---

**Claim 8**: "`AIAgent.run_conversation()` at `run_agent.py:8130`：单一入口被 CLI (`main()` at 11295)、Gateway (`gateway/run.py`)、Cron scheduler、ACP runtime 四类消费者共享"

源码验证（逐入口）：
- `run_agent.py:8130`: `def run_conversation(self, ...)` ✅
- CLI: `cli.py:9806` `def main()` → 创建 `HermesCLI` (line 9925) → 其内部创建 `AIAgent` (line 2872) → 调用 `agent.run_conversation()` (lines 7681, 10004)
- Gateway: `gateway/run.py:748` import AIAgent → `gateway/run.py:755` 创建 AIAgent → `gateway/run.py:823` 调用 `tmp_agent.run_conversation()`
- Cron: `cron/scheduler.py:587` import AIAgent → `cron/scheduler.py:736-760` 创建 AIAgent → `cron/scheduler.py:778` `agent.run_conversation`
- ACP: `acp_adapter/server.py:423` `agent.run_conversation(...)`

判定：⚠️ 四条入口路径全部经源码确认。但 CLI 入口表述 "main() at 11295" 指向的是 `run_agent.py` 中的简化版 `main()` 函数（`run_agent.py:11295`），而非实际 CLI 入口 `cli.py:main()`（`cli.py:9806`）。修复记录声称已将归属从 `run_agent.py:11295` 修正为 `cli.py:main()`，但正文第 29 行仍未更新。建议修正为 "CLI (`cli.py:main()` at 9806，通过 HermesCLI 间接调用 `run_conversation`)"。

---

**Claim 9**: "provider 路由：if/elif 分支链在 __init__ 中部展开为 ~170 行（898-1070）"

源码：898 至 1070 共 173 行。
判定：✅ ~170 行合理（实际 173 行）。

---

**Claim 10**: "工具定义加载（1097-1118 行）"

源码：`run_agent.py:1097-1118`
代码摘要：line 1097 `# Get available tools with filtering` — 调用 `get_tool_definitions()` → 提取 `valid_tool_names` → 打印 loaded tools / filtering info。
判定：✅ 行号准确。

---

**Claim 11**: "session 日志与 SQLite 持久化（1141-1198 行）"

源码：`run_agent.py:1141-1198`
代码摘要：line 1141 `# Session logging setup` — session id 生成 (1142-1150) → logs dir (1153-1156) → CheckpointManager (1165-1169) → SQLite session store `create_session` (1177-1188)。
判定：✅ 行号范围涵盖 session logging + SQLite 持久化。

---

**Claim 12**: "memory store 与外部 memory provider 插件激活（1211-1315 行）"

源码：`run_agent.py:1211-1315`
代码摘要：line 1211 `# Persistent memory (MEMORY.md + USER.md)` — 内置 MemoryStore (1211-1235) + line 1238 `# Memory provider plugin` — 外部插件激活 (1238-1315)。
判定：✅ 行号准确涵盖两部分。

---

**Claim 13**: "context compressor/engine 选择与配置（1354-1540 行）"

源码：`run_agent.py:1354-1540`
代码摘要：line 1354 `# Initialize context compressor` — 压缩配置读取 (1357-1363) → model context_length 解析 (1365-1430) → context engine 三步探测 (1432-1468) → plugin/builtin fallback (1470-1504) → 最小 context 校验 (1507-1518) → tool schemas 注入 (1520-1529) → session start notification (1532-1542)。
判定：✅ 行号范围涵盖完整 compressor/engine 初始化逻辑。

---

**Claim 14**: "Ollama num_ctx 检测（1563-1588 行）"

源码：`run_agent.py:1563-1588`
代码摘要：line 1563 `# Ollama num_ctx injection` — config override (1569-1576) → auto-detection via `query_ollama_num_ctx()` (1577-1583) → logging (1584-1588)。
判定：✅ 行号精确。

---

**Claim 15**: "主运行时快照保存（1602-1630 行）"

源码：`run_agent.py:1602-1630`
代码摘要：line 1602 `# Snapshot primary runtime for per-turn restoration` — `self._primary_runtime` dict 保存 model/provider/base_url/api_key/client_kwargs/compressor 状态。line 1625-1630 为 Anthropic 特有字段补充。
判定：✅ 行号准确，快照目的与源码注释一致。

---

### nanobot

**Claim 16**: "`AgentLoop.__init__()` at `agent/loop.py:129-228`，~99 行"

源码：`/Users/yuanlimiao/Work/agent_harness/nanobot/nanobot/agent/loop.py:129-228`
代码摘要：`__init__` 签名起于 line 129，方法体止于 line 227（`register_builtin_commands(self.commands)`），line 228 为方法间空行。129 至 228 共 100 行（含签名）。
判定：⚠️ 129-228 含签名行共 100 行，~99 行接近但略低。建议明确标注"约 100 行（129-228）"。

---

**Claim 17**: "构造函数共接收 20 个参数（含 17 个可选参数）"

源码：`nanobot/nanobot/agent/loop.py:129-150`，逐行计数：
- 必需（无默认值）: `bus` (131), `provider` (132), `workspace` (133) = **3 个必需**
- 可选（有默认值）: `model` (134), `max_iterations` (135), `context_window_tokens` (136), `context_block_limit` (137), `max_tool_result_chars` (138), `provider_retry_mode` (139), `web_config` (140), `exec_config` (141), `cron_service` (142), `restrict_to_workspace` (143), `session_manager` (144), `mcp_servers` (145), `channels_config` (146), `timezone` (147), `hooks` (148), `unified_session` (149) = **16 个可选**

总参数 = 3 + 16 = **19 个**（非 20）。可选参数 = **16 个**（非 17）。
判定：❌ 参数总数差 1，可选数差 1。实际为 **19 个参数（3 必需 + 16 可选）**。

---

**Claim 18**: "三阶段顺序组装——先存储简单参数 → 构建复合子系统 → 注册扩展"

源码：`nanobot/nanobot/agent/loop.py:151-227`
代码摘要：
- Phase 1 (line 151-180): 存储简单字段（bus, provider, workspace, model, max_iterations 等）
- Phase 2 (line 182-224): 构建复合子系统（ContextBuilder → SessionManager → ToolRegistry → AgentRunner → SubagentManager → Consolidator → Dream）
- Phase 3 (line 225-227): 注册扩展（`_register_default_tools()` + `register_builtin_commands()`）
判定：✅ 三阶段顺序完全符合源码结构。

---

**Claim 19**: "`ContextBuilder(workspace, timezone=timezone)` at `agent/loop.py:182`"

源码：`nanobot/nanobot/agent/loop.py:182`，`self.context = ContextBuilder(workspace, timezone=timezone)`
判定：✅ 行号精确。

---

**Claim 20**: "`SubagentManager(provider=..., workspace=..., bus=..., ...)` at `agent/loop.py:186-195`"

源码：`nanobot/nanobot/agent/loop.py:186-195`，`self.subagents = SubagentManager(provider=provider, workspace=workspace, bus=bus, model=self.model, web_config=self.web_config, max_tool_result_chars=self.max_tool_result_chars, exec_config=self.exec_config, restrict_to_workspace=restrict_to_workspace)`
判定：✅ 行号精确。描述"共享 provider、workspace、bus 引用"准确——所有参数均为已有实例引用。

---

**Claim 21**: "`self._register_default_tools()` at `agent/loop.py:225`"

源码：`nanobot/nanobot/agent/loop.py:225`: `self._register_default_tools()`
判定：✅ 行号精确。

---

**Claim 22**: "`_register_default_tools()` at `agent/loop.py:229-281`"

源码：`nanobot/nanobot/agent/loop.py:229-254`
代码摘要：`_register_default_tools()` 方法定义于 line 229。方法体内容：ReadFile (233) / WriteTool (234) / EditFileTool (234) / ListDirTool (234) / Glob (236) / Grep (236) → ExecTool 条件注册 (238-245) → WebSearch/WebFetch 条件注册 (246-248) → MessageTool (249) → SpawnTool (250) → CronTool 条件注册 (251-254)。**方法体结束于 line 254**。line 255 为空行，line 256 为 `async def _connect_mcp(self)`（MCP 懒连接），line 278 为 `_set_tool_context()`。
判定：❌ 方法实际结束于 **line 254**，而非 281。229-281 范围错误地将 `_connect_mcp()` (256-276) 和 `_set_tool_context()` (278-282) 也纳入了 `_register_default_tools`。溯源表应修正为 `229-254`。

---

**Claim 23**: "Consolidator 组装: 210-219"

源码：`nanobot/nanobot/agent/loop.py:210-219`，`self.consolidator = Consolidator(store=self.context.memory, provider=provider, model=self.model, sessions=self.sessions, context_window_tokens=context_window_tokens, build_messages=self.context.build_messages, get_tool_definitions=self.tools.get_definitions, max_completion_tokens=provider.generation.max_tokens)`
判定：✅ 行号精确。

---

**Claim 24**: "无 provider 分支展开——多 provider 支持通过 `LLMProvider` 抽象和多态实现，不在构造函数中展开条件逻辑"

源码：`nanobot/nanobot/agent/loop.py:156` — `self.provider = provider`。构造函数中无任何 `if/elif provider == ...` 分支。provider 差异通过 `LLMProvider` 基类多态（`providers/__init__.py` 中 5 个 provider 实现类）和 `ProviderRegistry`（`providers/registry.py:75-361`，27 个 ProviderSpec）在构造函数外部解决。
判定：✅ 构造函数仅做 `self.provider = provider` 单行赋值，无任何 provider 相关条件分支。

---

**Claim 25**: "ProviderRegistry 数据驱动注册表在 `provider.py` 中"

源码：实际位于 `nanobot/nanobot/providers/registry.py`（文件名为 `registry.py`，非 `provider.py`）。`provider.py` 文件不存在。`providers/__init__.py` 为 `LLMProvider` 基类懒加载模块。
判定：⚠️ 文件名不准。实际文件为 `providers/registry.py`。建议修正为 `providers/registry.py`。

---

**Claim 26**: "新增子系统：在 `_register_default_tools()` 加一行 `self.tools.register(XxxTool())`，或在构造函数参数列表增加一个带默认值的新参数"

源码：`nanobot/nanobot/agent/loop.py:229-254`。line 233-237 每行一个 `self.tools.register()`，line 239-245/247-248/249/250/252-254 为条件性注册。构造函数新增参数只需在参数列表添加带默认值的新参数。
判定：✅ 扩展模式描述与源码一致。

---

**Claim 27**: "去除了 litellm（30+ provider 开箱即用），保持核心的 provider 抽象足够简单以支撑构造函数内联"

源码：
- `nanobot/nanobot/cli/models.py:1-6`: 注释写 "Model database / autocomplete is **temporarily disabled** while litellm is being replaced." — litellm 正在被替换但**未完全移除**。
- `nanobot/nanobot/providers/registry.py` 包含 27 个 ProviderSpec，覆盖 anthropic/openai/deepseek/gemini/zhipu/mistral/ollama/azure 等。
- hermes-agent 的 `run_agent.py` 中 **0 处 litellm 引用**。litellm 仅出现在 `environments/benchmarks/` 和 `tests/` 中。

判定：⚠️ 三处不精确：① litellm 处于"正在替换中（temporarily disabled）"而非"已去除"；② nanobot 通过 ProviderRegistry 已支持 27 个 provider，并非"去除了 30+ provider 后只剩简单抽象"；③ hermes-agent 核心代码中也不使用 litellm，以 litellm 作为两者对比基础不完全成立。

---

**Claim 28**: "AgentLoop 作为编排 Hub，被 Channel 层（`channels/` 目录下各平台适配器）通过 MessageBus 异步队列驱动"

源码：
- `nanobot/nanobot/channels/base.py:28`: `BaseChannel.__init__(self, config, bus: MessageBus)` — 所有 channel 接收 MessageBus
- `nanobot/nanobot/nanobot.py:69`: `loop = AgentLoop(...)` — AgentLoop 在 main application 中创建
- Channels 目录包含 14+ 平台适配器（telegram/discord/slack/whatsapp/wechat/wecom/dingtalk/feishu/matrix/email/qq/mochat/weixin）
- 间接触发验证：`channels/telegram.py:837` 将 slash commands 转发到 bus 统一处理

判定：✅ Channel 层通过 MessageBus 异步队列与 AgentLoop 通信的架构描述准确。

---

## 关切验证

| 关切 | 跨仓库对比表对应行 | 判定 |
|------|-------------------|------|
| 1. 可发现性 | 「组装文件」「__init__ 规模」行 | ✅ 有对应——两个仓库的组装文件路径和规模直接对比 |
| 2. 可测试性 | 对比表无独立行专门对比可测试性 | ⚠️ 悬空——核心关切明确列出"可测试性：集中式组装无法对单个子系统做独立单元测试"，位置 A/B 的代价段均有提及，但**对比表中缺乏独立的"可测试性"对比维度** |
| 3. 扩展成本 | 「新增子系统成本」行 | ✅ 有对应——hermes 需修改 __init__ 中部追加 vs nanobot 一行注册 |
| 4. 规模膨胀 | 「组装文件」「__init__ 规模」行 | ✅ 有对应——11510 行 vs 100 行的直接对比 |

---

## 追加完整性

- [x] hermes-agent 在各节均有提及 — 位置 A、对比表（2 列）、选择指南（5 条场景）、溯源表、关联节均包含
- [x] nanobot 在各节均有提及 — 位置 B、对比表（2 列）、选择指南（5 条场景）、溯源表、关联节均包含

---

## 绝对化语言验证

| 绝对化表述 | 源码边界条件 | 判定 |
|-----------|------------|------|
| "单个类吸收 CLI、Gateway、Cron、ACP **全部**执行路径的初始化逻辑" | 四条路径均通过 `AIAgent` 类初始化。但 ACP 使用 `acp_adapter` 封装层（`acp_adapter/server.py:423`），run_agent.py 自身还有 `main()` (line 11295) 作为第五个独立入口 | ⚠️ 路径覆盖正确但"全部"忽略了第五入口（run_agent.py:main）和 ACP 的间接层 |
| "**所有**路径硬绑定到同一个 `AIAgent` 类" | CLI/Gateway/Cron/ACP 均创建 `AIAgent` 实例 | ✅ 准确——所有入口最终都依赖 AIAgent 类 |
| "provider 分支...**必须**理解全部四条路径才能掌握完整初始化逻辑" | `chat_completions` 和 `codex_responses` 在 __init__ 共享 else 分支（line 964），差异仅在 `run_conversation` 的端点选择 | ⚠️ 言过其实——理解 else 分支即可掌握两种 api_mode 的 __init__ 逻辑 |
| "nanobot 构造函数 **不**在构造函数中展开条件逻辑" | `self.provider = provider`（line 156）单行赋值 | ✅ 准确 |
| "nanobot **整个**系统**只有一个** provider 实例贯穿**全部**子系统" | SubagentManager (186)/Consolidator (212)/Dream (222)/AgentRunner (185) 均接收同一个 `provider` 引用 | ✅ 准确——6 个子系统共享同一 provider 实例 |
| "nanobot **所有**子系统在构造时**全部**实例化，无法按需懒加载" | MCP servers 通过 `_connect_mcp()` (line 256) **延迟**连接，`cron_service` 可为 `None` 即不实例化 | ⚠️ 不准确——MCP 采用懒连接模式（`_mcp_connected` flag + retry），cron_service 可选 |

---

## 汇总

总 claim 数：28 | ✅：18 | ⚠️：7 | ❌：3

关键发现：

1. **参数计数偏差**（❌ Claim 17）：nanobot `AgentLoop.__init__` 实际 19 个参数（3 必需 + 16 可选），Concept 页描述为"20 个参数（含 17 个可选）"，总数和可选数均差 1。需重新计数修正。

2. **`_register_default_tools()` 行号范围错误**（❌ Claim 22）：Concept 页及溯源表标注 `229-281`，实际方法结束于 line 254。line 256 起是 `_connect_mcp()`（MCP 懒连接），line 278 起是 `_set_tool_context()`。溯源表整体不可信——读者按 281 行号查找将看到无关代码。

3. **Provider 分支数不精确**（⚠️ Claim 3）：Concept 页称 __init__ 中有 4 条独立 provider 分支"各有独立 client 构建逻辑"，实际 `chat_completions` 和 `codex_responses` 在 __init__ 中共享同一 else 分支（line 964），只有 3 条 client 构造分支。差异在 `run_conversation` 中体现（`/responses` vs `/chat/completions` 端点选择）。

4. **litellm 对比失真**（⚠️ Claim 27）：Concept 页以 litellm 对比 hermes-agent（完备）vs nanobot（去除 litellm 求简单），但 hermes-agent 核心 `run_agent.py` 中 0 处 litellm 引用，nanobot 的 litellm 也仅 marked as "temporarily disabled" 且通过 `ProviderRegistry` 已支持 27 个 provider。

5. **CLI 入口行号修正未落实**（⚠️ Claim 8）：修复记录声称已将 `main()` 归属从 `run_agent.py:11295` 修正为 `cli.py:main()`，但正文机制描述中仍写 "main() at 11295"。修正未实际应用到正文。

6. **MCP 懒连接违背"全部实例化"断言**（⚠️ 绝对化语言）：Concept 页称 nanobot "所有子系统在构造时全部实例化，无法按需懒加载"，但 MCP server 连接通过 `_connect_mcp()` 延迟执行（line 256-276），cron_service 可为 None。

7. **关切 2（可测试性）在对比表中悬空**（⚠️）：核心关切明确列出"可测试性"维度，位置 A/B 的代价段均有涉及，但跨仓库对比表缺少独立的"可测试性"对比行。

8. **ProviderRegistry 文件名不准**（⚠️ Claim 25）：Concept 页写 "provider.py 中的 ProviderRegistry"，实际文件为 `providers/registry.py`。
