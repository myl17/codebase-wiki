# Hermes-Agent Performance Tradeoffs 事实核查报告

核查日期：2026-06-13
核查对象：`/tmp/experiment-perf-candidates.md`
源码根目录：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/`

---

## A. Provenance 验证

对候选清单中全部 22 条的逐条号线验证结果：

### 条目 1: SessionDB — 应用层随机退避代替 SQLite busy handler
- 文件：`hermes_state.py:122-208`
- `_WRITE_MAX_RETRIES = 15` @ L132: ✅
- `_WRITE_RETRY_MIN_S = 0.020` @ L133: ✅
- `_WRITE_RETRY_MAX_S = 0.150` @ L134: ✅
- `timeout=1.0` @ L150: ✅
- `BEGIN IMMEDIATE` @ L183: ✅
- jitter retry loop @ L198-208: ✅ (jitter computing at L203-207, sleep at L207)
- **判定: ✅ 全部正确**

### 条目 2: SessionContext — contextvars.ContextVar 代替 os.environ
- 文件：`gateway/session_context.py:1-146`
- 文档说明覆盖问题 @ L8-37: ✅ (docstring at L8-37 describes the race condition)
- 7 个 ContextVar 定义 @ L51-57: ✅
- `get_session_env` 三级回退 @ L139-145: ✅
- **判定: ✅ 全部正确**

### 条目 3: ContextCompressor — 辅助 LLM 摘要代替截断/滑动窗口
- 文件：`agent/context_compressor.py:1-80`, `run_agent.py:1904-1940`
- 模块文档 @ L1-18: ✅
- SUMMARY_PREFIX + handoff @ L37-46: ✅
- `_MIN_SUMMARY_TOKENS=2000`, `_SUMMARY_RATIO=0.20`, `_SUMMARY_TOKENS_CEILING=12000` @ L48-53: ✅
- `_check_compression_model_feasibility` @ run_agent.py L1904-1940: ✅
- **判定: ✅ 全部正确**

### 条目 4: GatewayRunner — AIAgent 实例缓存以保持 Prompt Caching
- 文件：`gateway/run.py:604-611`
- `_agent_cache` @ L604-611: ✅ (含文档说明 "costing ~10x more on providers with prompt caching")
- **判定: ✅ 全部正确**

### 条目 5: GatewayStreamConsumer — 渐进式编辑代替一次性发送
- 文件：`gateway/stream_consumer.py:1-165`
- 模块文档说明 @ L1-14: ✅
- `edit_interval=1.0, buffer_threshold=40` @ L42-44: ✅
- `_MAX_FLOOD_STRIKES=3` @ L65: ✅
- 自适应退避状态 @ L98-101: ✅
- **判定: ✅ 全部正确**

### 条目 6: 并行工具执行 — 路径重叠检测 + 安全名单白名单
- 文件：`run_agent.py:214-325, 7186-7207, 7321-7322`
- `_NEVER_PARALLEL_TOOLS` @ L214: ✅
- `_PATH_SCOPED_TOOLS` @ L233: ✅
- `_should_parallelize_tool_batch` @ L267-308: ✅
- `_extract_parallel_scope_path` @ L311-325: ✅
- `_execute_tool_calls` 分发 @ L7186-7207: ✅
- `_execute_tool_calls_concurrent` @ L7321: ✅ (ThreadPoolExecutor 在方法体内 L7327+)
- **判定: ✅ 全部正确**

### 条目 7: ToolRegistry — AST 解析源代码完成工具自发现
- 文件：`tools/registry.py:28-73`
- `_is_registry_register_call` AST 检测 @ L28-38: ✅
- `_module_registers_tools` 文件扫描 @ L41-53: ✅
- `discover_builtin_tools` 遍历 + importlib @ L56-73: ✅
- **判定: ✅ 全部正确**

### 条目 8: ToolRegistry — RLock 保护 + 快照模式保证并发安全
- 文件：`tools/registry.py:107-119`
- `self._lock = threading.RLock()` @ L110: ✅
- `_snapshot_state` 带锁快照 @ L112-115: ✅
- `_snapshot_entries` 快照 API @ L117-119: ✅
- **判定: ✅ 全部正确**

### 条目 9: CredentialPool — fill_first 策略 + 1 小时耗尽冷却
- 文件：`agent/credential_pool.py:1-80`
- `STRATEGY_FILL_FIRST` @ L60, `EXHAUSTED_TTL_429_SECONDS=60*60` @ L74: ✅
- `STATUS_OK`/`STATUS_EXHAUSTED` @ L52-53: ✅
- **判定: ✅ 全部正确**

### 条目 10: MCP Client — 长生命周期守护线程事件循环
- 文件：`tools/mcp_tool.py:55-167`
- Architecture 注释 @ L55-69: ✅
- `timeout=120` @ L163, `connect_timeout=60` @ L164, 重连 5 次 @ L165: ✅
- **判定: ✅ 全部正确**

### 条目 11: CronJob Scheduler — fcntl 文件锁代替外部调度器
- 文件：`cron/scheduler.py:1-64`
- 注释 "only one tick runs at a time" @ L7-8: ✅
- fcntl/msvcrt 平台适配 @ L20-28: ✅
- LOCK_FILE = .tick.lock @ L63-64: ✅
- **判定: ✅ 全部正确**

### 条目 12: API 模式自动检测 — URL/Provider 启发式代替显式配置
- 文件：`run_agent.py:692-754`
- 四种模式自动检测 @ L692-709: ✅
- OpenRouter 后台预取 @ L747-754: ✅
- **判定: ✅ 全部正确**

### 条目 13: SessionDB WAL 检查点 — 应用层控制代替自动管理
- 文件：`hermes_state.py:136, 216-235`
- `_CHECKPOINT_EVERY_N_WRITES = 50` @ L136: ✅
- `_try_wal_checkpoint` PASSIVE 模式 @ L216-235: ✅
- **判定: ✅ 全部正确**

### 条目 14: Session 持久化 — 逐轮写入代替会话结束批量写入
- 文件：`hermes_state.py:9-14`, `run_agent.py:616, 2437-2447`
- 设计文档 @ L9-14: ✅ ("WAL mode for concurrent readers", "compression-triggered session splitting via parent_session_id chains")
- `persist_session: bool = True` @ run_agent.py L616: ✅
- `_apply_persist_user_message_override` @ run_agent.py L2437-2447: ✅
- **判定: ✅ 全部正确**

### 条目 15: Skill 系统 — 渐进式信息披露代替全量注入
- 文件：`tools/skills_tool.py:1-7`, `toolsets.py:41`
- skills_tool.py 模块文档 @ L1-7: ✅ (描述渐进式披露架构)
- `skills_list, skill_view, skill_manage` @ toolsets.py L41: ✅
- **判定: ✅ 全部正确**

### 条目 16: HookRegistry — 错误隔离（静默捕获永不传播）
- 文件：`gateway/hooks.py:19, 163-170`
- "Errors in hooks are caught and logged but never block" @ L19: ✅
- emit 中 try-except @ L163-170: ✅
- **判定: ✅ 全部正确**

### 条目 17: 平台适配器 — 最小公分母消息格式代替平台原生功能
- 文件：`gateway/platforms/base.py:656-721, 813-853`
- MessageEvent 归一化消息结构 @ L656-721: ✅
- BasePlatformAdapter 抽象方法 @ L813-853: ✅ (send/send_image/send_typing, 无平台特定 API)
- **判定: ✅ 全部正确**

### 条目 18: Session 系统提示词 — PII 哈希 + 平台选择性脱敏
- 文件：`gateway/session.py:34-54, 175-204`
- `_hash_id` SHA256 @ L34-36: ✅
- `_PII_SAFE_PLATFORMS` @ L175-180: ✅ (WhatsApp/Signal/Telegram/BlueBubbles)
- `build_session_context_prompt` redact_pii @ L186-204: ✅
- **判定: ✅ 全部正确**

### 条目 19: 上下文文件注入 — 正则威胁检测代替信任注入
- 文件：`agent/prompt_builder.py:36-73`
- `_CONTEXT_THREAT_PATTERNS` 10 条正则 @ L36-47: ✅
- `_CONTEXT_INVISIBLE_CHARS` @ L49-52: ✅
- `_scan_context_content` + BLOCKED @ L55-73: ✅
- **判定: ✅ 全部正确**

### 条目 20: BatchRunner — Multiprocessing 代替单进程顺序处理
- 文件：`batch_runner.py:1-57`
- `from multiprocessing import Pool, Lock` @ L30: ✅
- `_WORKER_CONFIG` @ L48: ✅
- `ALL_POSSIBLE_TOOLS` @ L50-54: ✅
- **判定: ✅ 全部正确**

### 条目 21: 流式输出 think-block 过滤 — 客户端过滤代替服务端配置
- 文件：`gateway/stream_consumer.py:67-106, 159`, `run_agent.py:2096-2108`
- `_OPEN_THINK_TAGS` 6 种 + `_CLOSE_THINK_TAGS` 6 种 @ L67-77: ✅
- `_in_think_block` 状态机 @ L104: ✅
- `_filter_and_accumulate` @ L159: ✅
- `_strip_think_blocks` @ run_agent.py L2096-2108: ✅
- **判定: ✅ 全部正确**

### 条目 22: 会话级模型覆盖 — 内存字典代替持久化
- 文件：`gateway/run.py:613-618`
- `_session_model_overrides` @ L613-615: ✅
- 仅在内存中, 无持久化 @ L616-618: ✅ (L616-618 同时存储 `_pending_approvals`, 模型覆盖无持久化逻辑)
- **判定: ✅ 全部正确**

### Provenance 总评

所有 22 条的号线均经过与源码逐行比对验证。结论：**22/22 条 provence 正确（✅），无偏移（⚠️ 0），无错误（❌ 0）**。

---

## B. 覆盖完整性

### B.1 Architecture 26 核心抽象覆盖情况

| # | 子系统 | 覆盖条目 | 状态 |
|---|--------|----------|------|
| 1 | AIAgent | 3, 6, 12, 14, 21 | 间接覆盖 |
| 2 | GatewayRunner | 4, 22 | ✅ |
| 3 | BasePlatformAdapter | 17 | ✅ |
| 4 | MessageEvent | 无（纯数据结构） | 合理跳过 |
| 5 | SessionSource | 无（纯数据结构） | 合理跳过 |
| 6 | SessionContext | 2 | ✅ |
| 7 | SessionDB | 1, 13, 14 | ✅ |
| 8 | SessionStore | 无 | ⚠️ 未覆盖 |
| 9 | ToolRegistry | 7, 8 | ✅ |
| 10 | ToolEntry | 无（纯元数据） | 合理跳过 |
| 11 | Toolset | 7, 15（间接） | 间接覆盖 |
| 12 | DeliveryRouter/DeliveryTarget | 无 | ⚠️ 未覆盖 |
| 13 | GatewayConfig/PlatformConfig | 无（纯配置） | 合理跳过 |
| 14 | CredentialPool | 9 | ✅ |
| 15 | ContextCompressor | 3 | ✅ |
| 16 | Skill | 15 | ✅ |
| 17 | HookRegistry | 16 | ✅ |
| 18 | MCP Client | 10 | ✅ |
| 19 | MCP Server | 无 | ⚠️ 未覆盖 |
| 20 | GatewayStreamConsumer | 5, 21 | ✅ |
| 21 | CronJob Scheduler | 11 | ✅ |
| 22 | WebServer | 无（声称"标准FastAPI"） | ⚠️ 需确认 |
| 23 | BatchRunner | 20 | ✅ |
| 24 | RL Environment | 无（训练专用） | 合理跳过 |
| 25 | Plugin (MemoryProvider/ContextEngine) | 无 | ⚠️ 未覆盖 |
| 26 | ACP Adapter | 无（声称间接覆盖） | 合理跳过 |

### B.2 Extension Points 25 扩展点覆盖情况

大部分扩展点与架构抽象重叠。额外未覆盖的扩展点：
- MemoryProvider 插件 — 外部记忆后端抽象
- ContextEngine 插件 — 上下文压缩引擎可替换性
- Skills Hub / Skills Sync — 远程技能管理
- 配置层次 — 多层配置叠加
- Tirith 安全扫描 — 工具执行前后安全检查
- 工具集分布 — 数据生成概率分布
- Agent 回调系统 — 非核心

### B.3 实际遗漏的重要权衡

通过深入源码目录确认，以下子系统存在明确的设计权衡但未被候选清单收录：

#### ❌ 遗漏 1: `tools/approval.py` — 智能审批（辅助 LLM 风险评估）

**源码位置**: `tools/approval.py:534-583` (`_smart_approve`), `tools/approval.py:693-779` (`check_all_command_guards` 三阶段流程)

**描述**: 当 `approvals.mode=smart` 时，在用户审批提示之前先用辅助 LLM 评估危险命令的风险。辅助 LLM 可以 auto-approve（跳过用户提示）、deny（硬拦截）或 escalate（回退到用户提示）。

**优化了什么**: 减少用户因正则假阳性（如 `python -c "print('hello')"` 被标记为"script execution via -c flag"）而产生的中断。

**牺牲了什么**: 每次潜在危险命令需额外的 LLM API 调用（成本+延迟）；辅助模型可能误判真正危险的命令为安全（false negative），使危险性命令绕过人工审批。

**证据**: `tools/approval.py` L534-583（`_smart_approve` 使用 auxiliary LLM，temperature=0，max_tokens=16），L762-779（Phase 2.5 smart approval 流程）。

**严重程度**: 高。此权衡与条目 3（ContextCompressor 使用辅助 LLM）同级，但被完全遗漏。`tools/approval.py` 共 926 行，agent 从未读取此文件。

#### ❌ 遗漏 2: `tools/skills_guard.py` — 信任感知技能安全扫描

**源码位置**: `tools/skills_guard.py:1-406`

**描述**: 外部技能安装前的安全扫描。使用大量正则模式检测数据外泄、prompt injection、破坏性命令、持久化等威胁。配合信任级别策略（builtin 永远信任、trusted repos 允许 caution、community 任何发现即拦截）。

**优化了什么**: 防止恶意技能注入——用户下载社区技能时不会引入后门或数据外泄。

**牺牲了什么**: 正则假阳性可能阻止合法技能安装（community 级别尤其严格）；假阴性可能漏过新型攻击；信任级别硬编码（`TRUSTED_REPOS = {"openai/skills", "anthropics/skills"}`）。

**证据**: `tools/skills_guard.py` L38-39（TRUSTED_REPOS）, L41-47（INSTALL_POLICY 信任矩阵）, L82-239（THREAT_PATTERNS 大量正则）。

**严重程度**: 中。与条目 19（上下文文件威胁检测）模式相同但范围不同，可合并或单独列出。

#### ⚠️ 遗漏 3: `agent/prompt_caching.py` — Anthropic 特定 system_and_3 缓存策略

**源码位置**: `agent/prompt_caching.py:1-72`

**描述**: 针对 Anthropic API 的 "system_and_3" prompt caching 策略：使用 4 个 cache_control 断点（Anthropic 最大限制），分别标记系统提示词和最近 3 条非系统消息。

**优化了什么**: 多轮对话中约 75% 的输入 token 成本节省。

**牺牲了什么**: Anthropic 特定——其他 provider 不支持此机制；4 断点限制意味着旧消息必须丢失缓存标记；需要 deep copy 消息列表修改后不影响原始数据。

**证据**: `agent/prompt_caching.py` L41-72 (`apply_anthropic_cache_control`)。

**严重程度**: 低-中。条目 4（GatewayRunner 缓存 AIAgent 实例）已覆盖 Gateway 侧的 prompt caching 策略，但此文件展示了请求级别的缓存标记策略，与条目 4 互补但角度不同。

#### ⚠️ 遗漏 4: `tools/tirith_security.py` — 工具执行安全扫描

**源码位置**: `tools/tirith_security.py`

**描述**: 工具调用前后的安全检查系统。与 approval.py 配合工作（`check_all_command_guards` 中的 Phase 1）。

**权衡**: 额外的安全检查增加工具调用延迟；安全检查的覆盖面与假阳性率之间的权衡。

**严重程度**: 低。安全扫描的权衡模式与条目 19（上下文威胁检测）类似，且已在 approval.py 的三阶段流程中被引用。

#### ⚠️ 遗漏 5: `hermes_cli/` CLI 层的未尽检查

Agent 声称读取了 `hermes_cli/web_server.py (L1-80)`，但该文件共 2108 行，仅读取了前 3.8%。CLI 包含以下未检查的子系统：
- `hermes_cli/auth.py` — OAuth/API key 认证流程
- `hermes_cli/curses_ui.py` — TUI 渲染
- `hermes_cli/config.py` — 多层配置解析
- `hermes_cli/stream_consumer.py` 等效逻辑（已在 gateway/ 侧覆盖）
- `hermes_cli/callbacks.py` — CLI 回调

这些文件可能存在额外权衡，但 agent 未检查。

### B.4 合理未覆盖的子系统（核查确认）

以下子系统经源码确认确实不包含显著的设计权衡：

- **MessageEvent**: 纯 dataclass，无行为逻辑。✅ 合理
- **SessionSource**: 纯数据容器。✅ 合理
- **ToolEntry**: 纯元数据 slots 类。✅ 合理
- **GatewayConfig/PlatformConfig**: dataclass 配置容器。✅ 合理
- **DeliveryRouter**: 薄路由层（256 行），简单平台映射。✅ 合理
- **RL Environment**: `environments/` 下为训练框架，非面向用户的运行时权衡。✅ 合理
- **ACP Adapter**: 通过 `toolsets.py` 中的 `hermes-acp` toolset 间接涉及。✅ 合理

---

## C. 自审验证

### C.1 声称读过的文件路径是否真实

候选清单末尾列出的文件：

| 文件 | 是否存在 | 大小(行) | agent 声称读取范围 | 评估 |
|------|----------|----------|-------------------|------|
| `hermes_state.py` (L1-293) | ✅ | 293+ | L1-293 | 充分 |
| `gateway/session_context.py` (L1-146) | ✅ | 146 | L1-146 | 完整读完 |
| `agent/context_compressor.py` (L1-80) | ✅ | 80+ | L1-80 | 读完核心段 |
| `tools/registry.py` (L1-120) | ✅ | 120+ | L1-120 | 充分 |
| `gateway/stream_consumer.py` (L1-160) | ✅ | 160+ | L1-160 | 充分 |
| `run_agent.py` (多个片段) | ✅ | 8500+ | 7个片段 | 覆盖了关键段 |
| `gateway/run.py` (多个片段) | ✅ | 2700+ | 3个片段 | 覆盖了关键段 |
| `agent/credential_pool.py` (L1-80) | ✅ | 80+ | L1-80 | 充分 |
| `model_tools.py` (L1-100) | ✅ | 562 | L1-100 | 表面阅读 |
| `cron/scheduler.py` (L1-80) | ✅ | 80+ | L1-80 | 充分 |
| `tools/mcp_tool.py` (L1-180) | ✅ | 180+ | L1-180 | 充分 |
| `gateway/session.py` (L1-319) | ✅ | 319+ | L1-319 | 充分 |
| `agent/anthropic_adapter.py` (L1-60) | ✅ | 1438 | L1-60 | 仅4.2% |
| `gateway/hooks.py` (L1-80) | ✅ | 170+ | L1-80 | 充分 |
| `mcp_serve.py` (L1-80) | ✅ | 80+ | L1-80 | 表面阅读 |
| `hermes_cli/web_server.py` (L1-80) | ✅ | 2108 | L1-80 | 仅3.8% |
| `batch_runner.py` (L1-180) | ✅ | 180+ | L1-180 | 充分 |
| `agent/prompt_builder.py` (L36-90) | ✅ | 90+ | L36-90 | 充分 |
| `plugins/memory/__init__.py` (L263-342) | ✅ | 406 | L263-342 | 部分 |
| `gateway/delivery.py` (L1-100) | ✅ | 256 | L1-100 | 表面阅读 |

**结论**: 所有文件路径均真实存在 ✅。但部分文件的阅读深度不足（`anthropic_adapter.py` 4.2%, `web_server.py` 3.8%）。

### C.2 是否真正覆盖了所有子系统

Agent 声称："实际检查了 Architecture 的 26 个核心抽象 + Extension Points 的 25 个扩展点，合并去重后共 28 个子系统。识别出 22 个有明确性能/设计权衡的条目。"

**核查结论**: ❌ 此声明不完全属实。

以下**有实际权衡的源文件 agent 从未读取**：
- `tools/approval.py`（926 行）— **完全未读**。包含智能审批（辅助 LLM 风险评估）这一显著权衡
- `tools/skills_guard.py` — **完全未读**。包含信任感知安装策略权衡
- `agent/prompt_caching.py` — **完全未读**。包含 Anthropic 特定缓存策略
- `tools/tirith_security.py` — **完全未读**。安全扫描权衡

Agent 对以下子系统的"经检查未发现权衡"声明是**基于 Architecture/Extension Points 文档的间接推断**，而非实际源码审查：
- WebServer: 声称"标准 FastAPI 模式，无特殊权衡"——仅读了 80/2108 行
- DeliveryRouter: 声称"简单路由，无权衡"——仅读了 100/256 行
- MCP Server: 声称"无面向用户的设计权衡"——仅读了 80 行

### C.3 Agent 是否诚实

**总体评价**: 部分诚实，但过度自信于覆盖完整性。

- ✅ provenance 行号准确（22/22 全部验证通过）——这是诚实的
- ✅ 每条都有「常规做法」「优化」「牺牲」三要素——这是诚实的
- ⚠️ 「覆盖了所有子系统」——过度宣称。关键文件未读
- ⚠️ 「逐个子系统检查了 Architecture + Extension Points」——实际检查的是文档列表而非源码

**核心问题**: Agent 将「读了 Architecture/Extension Points 文档中关于某子系统的描述」等同于「读了源码并做了权衡分析」。这在安全敏感子系统中尤其危险——如 approval.py 包含的智能审批权衡完全被遗漏。

---

## D. 总结与建议

### 已验证可信任的内容
- 22 条候选条目的 provenance（文件路径、行号、代码逻辑）全部准确
- 每条的结构完整性（优化/牺牲/常规做法对比）良好
- 主要子系统（SessionDB、ToolRegistry、GatewayStreamConsumer、ContextCompressor 等）覆盖充分

### 需要补充的内容
1. **必须补齐**: `tools/approval.py` 的智能审批权衡（高优先级，与条目 3 同级）
2. **建议补充**: `tools/skills_guard.py` 的信任感知扫描权衡（中优先级）
3. **可选补充**: `agent/prompt_caching.py` 的 system_and_3 策略（低优先级，与条目 4 部分重叠）
4. **深度不足**: `hermes_cli/`、`agent/anthropic_adapter.py` 仅做表面阅读，可能存在额外权衡

### 自审声明修正
- "是否逐个子系统检查了 Architecture + Extension Points 清单中的每个条目？" — 应修正为: "检查了 Architecture + Extension Points 文档列表中的子系统，但部分子系统的源码未深入阅读"
- "是否有源码目录未被覆盖？" — 应列出未直接阅读但有源码的目录
