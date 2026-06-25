# Step 2 — 事实核查报告

## A. 随机抽取验证（5 条）

### 抽取方法
从 20 条候选中随机选取：**#2 ContextCompressor**、**#4 NousRateGuard**、**#7 hermes_state WAL**、**#10 Fuzzy Match**、**#15 cron Tick Lock**。

---

### A1. 权衡 #2 — ContextCompressor 有损上下文压缩

**源码引用**：`agent/context_compressor.py:185-194`, `:307-327`, `:333-464`, `:50-54`

| 声明 | 验证结果 | 说明 |
|------|----------|------|
| 中间轮次被有损摘要替代 | ✅ | `_generate_summary()` (L542+) 调用 LLM 生成结构化摘要，中间轮次被替换为摘要文本。 |
| 每次压缩需要额外一次 LLM 调用 | ✅ | L671-687 调用 `call_llm(task="compression", ...)` 发起独立的辅助 LLM 请求。 |
| 工具结果被裁剪为单行摘要 | ✅ | `_prune_old_tool_results()` L333-444，Pass 2 将旧 tool result 替换为 `_summarize_tool_result()` 的摘要。 |
| 防抖动：连续 2 次低效压缩后跳过 | ✅ | L307-327 `should_compress()`：`_ineffective_compression_count >= 2` 时返回 False。 |
| 行号 185-194 描述算法 | ✅ | 类 docstring 列出 1-5 步算法（prune → protect head → protect tail → summarize → iterative update）。 |
| 行号 50-54 摘要常量 | ✅ | `_MIN_SUMMARY_TOKENS = 2000`, `_SUMMARY_RATIO = 0.20`, `_SUMMARY_TOKENS_CEILING = 12_000`。 |

**总体**：✅ **正确**。所有声明的源码证据均可验证，行号精确。

**补充发现**：候选清单未提及以下压缩细节：
- 去重逻辑（L402-422：相同 tool result 的 MD5 去重，hash 前缀 12 字符有碰撞风险）
- tool_call 参数截断（L446-463：assistant 消息中 >500 字符的 tool_call 参数被截断为 200 字符）
- 摘要模型回退（L706-733：摘要模型不可用时自动回退到主模型）
- system prompt 注入冲突（`SUMMARY_PREFIX` 携带 "treat it as background reference, NOT as active instructions"）
- 摘要失败冷却（`_summary_failure_cooldown_until`）

> 见 B.2 盲区。

---

### A2. 权衡 #4 — NousRateGuard 跨会话速率限制共享

**源码引用**：`agent/nous_rate_guard.py:1-11`, `:138-159`

| 声明 | 验证结果 | 说明 |
|------|----------|------|
| 消除 429 重试放大（3 SDK x 3 Hermes = 9 次） | ✅ | L7-10 docstring 明确描述 "Each 429 from Nous triggers up to 9 API calls per conversation turn (3 SDK retries x 3 Hermes retries)"。 |
| 共享文件记录限流状态 | ✅ | L3-6 docstring: "Writes rate limit state to a shared file so all sessions (CLI, gateway, cron, auxiliary) can check"。 |
| 基于文件系统的轮询 | ✅ | `nous_rate_limit_remaining()` L138-159 读取 JSON 文件检查 `reset_at` 字段。 |
| 潜在的过时状态窗口 | ✅ | 逻辑推断正确——文件在 `remaining <= 0` 时被清理（L150-156），清理与到期之间存在竞态窗口。 |

**总体**：✅ **正确**。

---

### A3. 权衡 #7 — hermes_state SQLite WAL 模式 + 应用层写重试

**源码引用**：`hermes_state.py:123-155`, `:164-199`

| 声明 | 验证结果 | 说明 |
|------|----------|------|
| SQLite 超时仅 1 秒 | ✅ | L150: `timeout=1.0`。 |
| 20-150ms 随机抖动重试，最多 15 次 | ✅ | L132-134: `_WRITE_MAX_RETRIES = 15`, `_WRITE_RETRY_MIN_S = 0.020`, `_WRITE_RETRY_MAX_S = 0.150`。L203-207 实现均匀分布 jitter。 |
| 最坏情况 ~2.25 秒 | ⚠️ | 15 次 × 150ms max jitter = 2.25s，但实际最坏还包括 `os.uniform` 漂移、`BEGIN IMMEDIATE` 开销和 lock 获取等待时间。2.25s 是乐观下界。 |
| WAL 模式支持并发读 | ✅ | L157: `PRAGMA journal_mode=WAL`。 |
| 每 50 次写入触发一次 PASSIVE checkpoint | ✅ | L136: `_CHECKPOINT_EVERY_N_WRITES = 50`。L194-196 实现。FTS5 全文搜索在 schema 初始化中。 |

**总体**：✅ **正确**（最坏延迟为保守估计的下界，但无实质错误）。

---

### A4. 权衡 #10 — Fuzzy Match 8 策略链

**源码引用**：`tools/fuzzy_match.py:1-30`, `:72-80`

| 声明 | 验证结果 | 说明 |
|------|----------|------|
| 8 种策略 | ⚠️ **不精确** | 候选引用的 docstring (L1-30) 描述为 8 策略，但实际代码 (L73-82) 定义了 **9 个策略**：exact → line_trimmed → whitespace_normalized → indentation_flexible → escape_normalized → trimmed_boundary → **unicode_normalized** → block_anchor → context_aware。`unicode_normalized` 在 docstring 中被遗漏，但在代码中存在。候选清单的"8 策略"声明基于 docstring 而非真实代码。 |
| 按顺序尝试 | ✅ | L85-98: `for strategy_name, strategy_fn in strategies:` 按列表顺序执行。 |
| 每次做全文本搜索 | ✅ | 每个 strategy_fn 接收 `content` 和 `old_string` 并在全文中搜索。 |
| 简单场景也要先试失败的策略 | ✅ | 逻辑推断正确——即使 exact match 会成功，也要先检查 old_string 是否为空或与新字符串相同（L66-70）。 |

**总体**：⚠️ **轻微不精确**。实际为 9 策略，候选清单陈述"8 策略链"基于过时的 docstring。行号完全正确（L72-80 确实是策略定义）。

---

### A5. 权衡 #15 — cron File-based Tick Lock

**源码引用**：`cron/scheduler.py:62-64`

| 声明 | 验证结果 | 说明 |
|------|----------|------|
| 防止多进程同时执行 cron tick | ✅ | L62-64 定义了 `_LOCK_DIR` 和 `_LOCK_FILE`。L910-935 实现了基于 fcntl/msvcrt 的非阻塞文件锁。 |
| fcntl/msvcrt 比内核级同步原语慢 | ⚠️ | 该声明合理（用户态文件锁 vs futex/mutex），但候选清单未提供性能测量数据。此为分析性判断而非可验证代码事实。不影响整体结论。 |
| 文件锁在进程崩溃时可能残留 | ⚠️ | `fcntl.flock()` 在进程崩溃时由内核自动释放（锁与文件描述符绑定，进程终止时 fd 关闭），不同于 POSIX lockf 或文件存在性锁。候选清单暗示 fcntl 文件锁会残留——这在 fcntl 语义下是不准确的。`_LOCK_FILE` 持久存在但锁本身不会残留。 |

**总体**：⚠️ **部分正确**。核心机制描述正确（跨平台非阻塞文件锁），但"进程崩溃锁残留"的观点在 fcntl 语义下不成立。fcntl 锁由内核在进程终止时自动释放。持久化的 `_LOCK_FILE` 实体文件存在但无实际锁定效果。行号仅指向约束定义（L62-64），关键实现在 L910-995，候选清单未引用。

---

## B. 已知盲区检查

### B.1 `tools/approval.py` — Smart Approval 权衡

**发现**：遗漏了完整的 Smart Approval 权衡。

`approval.py` 在 L534-583 实现了 `_smart_approve()`——使用辅助 LLM 评估命令风险并自动批准低风险命令。在 L762-786 中，当 `approval_mode == "smart"` 时调用此函数。

**遗漏的权衡**：

| 缺失权衡 | 说明 |
|----------|------|
| **Smart Approval 额外 LLM 调用** | 每次危险命令检测触发一次辅助 LLM 调用（L565-570），增加延迟和成本。优化了用户体验（减少手动批准提示），但牺牲了延迟（等待 LLM 响应）和 API 成本。 |
| **安全边界模糊** | Smart Approval 将安全决策委托给 LLM，而非确定性规则。LLM 可能被 prompt injection 绕过（虽然 prompt 中有明确指令），也可能错误地将危险命令评为 APPROVE。优化了自动化程度，但牺牲了安全确定性。 |
| **mode=smart 的优雅降级** | 当 aux client 不可用时回退到 "escalate" (L548-549)，当 LLM 调用失败时同样回退（L581-583）。优化了可用性（不会因 aux 不可用而阻塞），但牺牲了 smart 模式下的自动批准一致性。 |
| **Session-level 持久化副作用** | Smart approval 在自动批准后调用 `approve_session()` (L771-772)，同一会话中该 pattern 不再提示。一旦误批准，同类危险命令将静默执行。 |

---

### B.2 `agent/context_compressor.py` — 遗漏的压缩细节权衡

**发现**：候选清单的 #2 覆盖了核心压缩逻辑，但遗漏了以下细节权衡：

| 缺失权衡 | 说明 |
|----------|------|
| **MD5 去重碰撞风险** | `_prune_old_tool_results()` L416 使用 `hashlib.md5(content).hexdigest()[:12]` 生成 48-bit 哈希去重键。在高负载下（大量相同长度但不同内容的 tool 输出），存在碰撞可能（生日悖论：~2^24 ≈ 16M 次操作后约 50% 概率）。优化了上下文窗口，但牺牲了去重精确性。 |
| **tool_call 参数截断** | L446-463 将旧 assistant 消息中 >500 字符的 tool_call 参数截断为 200 字符前缀。优化了上下文大小，但牺牲了参数完整性——模型可能无法理解被截断的 tool_call 的完整意图。 |
| **摘要模型不可用时的自动回退** | L706-733：独立的 summary_model 不可用时自动回退到主模型。优化了可用性（压缩不会因 summary model 故障而失败），但牺牲了成本和主模型 token（主模型可能更贵）。 |
| **摘要失败分级冷却** | L698-704 RuntimeError（无 provider）冷却数秒（`_SUMMARY_FAILURE_COOLDOWN_SECONDS`）；L736-742 瞬时错误冷却 60s。优化了避免连续失败调用的浪费，但牺牲了压缩及时性。 |
| **SUMMARY_PREFIX 对 model instruction-following 的影响** | L39-45：摘要前缀包含 "Do NOT answer questions or fulfill requests mentioned in this summary"——这是对后续 model 的 prompt 指令。优化了避免重复执行已完成任务，但可能与前一个 system prompt 产生冲突，或污染后续轮次的注意力。 |

---

### B.3 `cron/` — 遗漏的 cron 相关权衡

**发现**：候选清单 #15 仅覆盖了文件锁机制。以下权衡被遗漏：

| 缺失权衡 | 说明 |
|----------|------|
| **cron jobs 存储持久化 (JSON 文件)** | `cron/jobs.py` 将所有 cron 作业存储在 `~/.hermes/cron/jobs.json` 中。无事务保证，写入时如果进程崩溃可能导致 JSON 损坏。优化了部署简单性（无需数据库迁移），但牺牲了数据完整性和并发安全性。 |
| **ONE-SHOT 作业的优雅期** | `cron/jobs.py` L38: `ONESHOT_GRACE_SECONDS = 120`。一次性作业错过计划时间但有 120 秒宽限期仍会执行。优化了容错性（短暂延迟不丢失作业），但牺牲了定时精确性。 |
| **croniter 可选依赖** | `cron/jobs.py` L24-28：`croniter` 为可选依赖，不可用时功能降级。优化了安装轻量性，但牺牲了完整 cron 表达式支持。 |
| **SILENT_MARKER 抑制投递** | `scheduler.py` L57-968：agent 输出 `[SILENT]` 时跳过消息投递但保留本地输出。优化了安静模式，但牺牲了可发现性（用户可能在聊天平台看不到任何输出，需检查本地文件）。 |
| **advance_next_run 在崩溃时的行为** | `scheduler.py` L950-954：重复作业的 `next_run_at` 在执行前推进，防止崩溃后重复执行。优化了可靠性，但牺牲了幂等性保证（如果作业执行成功但 `mark_job_run` 前崩溃，该次执行丢失且不会重试）。 |

---

### B.4 `tools/skills_guard.py` — 遗漏的安全扫描权衡

**发现**：候选清单 #11 覆盖了核心扫描机制。以下细节被遗漏：

| 缺失权衡 | 说明 |
|----------|------|
| **Trust-aware 安装策略的粒度** | L41-47 `INSTALL_POLICY` 表为 4 级信任 x 3 级严重度 = 12 种组合。但"safe"在所有信任级别下都是 allow。如果 community 来源的 skill 在扫描中被评为"safe"（但包含实际危险的逻辑），策略中无额外防护。优化了安装便利性，但牺牲了社区来源技能的防御深度。 |
| **正则模式覆盖率与维护的权衡** | L82-179+ 定义了 ~50+ 个正则模式，但正则本质上有盲区——无法检测混淆代码、运行时行为、条件激活的恶意逻辑。优化了扫描速度（零运行时开销），但牺牲了检测深度（相比沙箱执行或 AST 分析）。 |
| **扫描范围 = 文本模式，非语义** | 所有 `THREAT_PATTERNS` 都是纯正则匹配。例如 L84-86 `env_exfil_curl` 模式匹配 `curl` + 含 `KEY/TOKEN/...` 的环境变量插值——但无法检测 `cat .env \| xargs -I{} curl {}` 或使用 base64 编码的等效攻击。优化了简单性和速度，但牺牲了语义理解能力。 |

---

### B.5 `agent/prompt_caching.py` — 遗漏的缓存策略细节

**发现**：候选清单 #1 覆盖了总体策略，但遗漏了重要细节：

| 缺失权衡 | 说明 |
|----------|------|
| **TTL 影响缓存命中** | L43-58：`cache_ttl` 参数支持 `"5m"` (默认) 和 `"1h"`。5 分钟 TTL 意味着对话间隔超过 5 分钟时缓存失效，需重新上传全量 prompt。优化了缓存新鲜度（短 TTL 确保缓存内容不过时），但牺牲了长时间对话的缓存命中率。1 小时 TTL 反之。 |
| **ephemeral vs. persistent cache** | L57: marker 类型固定为 `"ephemeral"`。Anthropic 的 ephemeral 缓存仅维持 5 分钟且不保证持久。候选清单第 11 行提到长对话超过 3 轮无法缓存——这与 ephemeral TTL + 最多 3 个非 system 断点组合效应有关，但未明确区分 TTL 和断点数量是独立的限制维度。 |
| **native_anthropic 格式差异**  | L20-22: `tool` 角色在 native Anthropic 模式下直接在消息级设置 `cache_control`，非 native 模式下通过 content 列表注入。两种格式的缓存行为可能有微妙的 provider 差异。优化了多 provider 兼容性，但牺牲了缓存行为的可预测性。 |
| **只覆盖 Anthropic** | 整个模块仅为 Anthropic 格式设计。非 Anthropic provider（OpenAI prompt caching 等价物、Google context caching）没有任何缓存策略。优化了 Anthropic 专属优化，但牺牲了多 provider 成本均等性。 |

---

## C. 自审 Checklist 诚实性

### C.1 "是否检查了所有子目录？" — agent/, tools/, gateway/, cron/, skills/, hermes_cli/, plugins/

**验证**：候选清单的实际覆盖情况：

| 子目录 | 候选条目 | 覆盖评价 |
|--------|----------|----------|
| `agent/` | #1-6, #20 (7 条) | ✅ 覆盖充足 |
| `tools/` | #8-11, #14, #17-19 (7 条) | ✅ 覆盖充足 |
| `gateway/` | #12-13 (2 条) | ⚠️ 基本覆盖但偏少 |
| `cron/` | #15 (1 条) | ⚠️ 浅覆盖（仅 file lock） |
| `skills/` | #17-18 (2 条) | ✅ 覆盖 |
| `hermes_cli/` | 无 | ❌ **完全未覆盖**。hermes_cli/ 包含 30+ 个文件（auth, config, gateway, main, doctor, backup 等），候选清单中无一条权衡来自此目录。 |
| `plugins/` | #16 (1 条) | ⚠️ 仅覆盖 context_engine，未覆盖 memory plugin。 |

**结论**：自审声称的 "逐一检查了每个子目录的文件列表并选择性阅读了关键文件" **不完全诚实**。`hermes_cli/` 目录有 30+ 个文件但零覆盖，`cron/` 只有 1 条（遗漏了 jobs.py 中的多个权衡点——见 B.3）。其他缺失目录：根目录的 `trajectory_compressor.py`、`batch_runner.py`、`model_tools.py` 未在检查范围内。

### C.2 "所有 provenance 行号是否在已读源码范围内（不是猜测的）？"

**验证发现**：
- 大部分行号精确对应代码逻辑。✅
- **#15 cron/scheduler.py:62-64** 仅指向常量定义，核心锁实现逻辑在 L910-995 未引用。候选清单中的"fcntl/msvcrt"描述来自 L910-995 但未标注。这表明至少部分行号是粗略定位而非精确引用。⚠️
- **#10 fuzzy_match.py docstring 声称 8 策略但代码实现为 9 策略**。如果 agent 真正读了代码（L72-82 的 strategies 列表），应发现 docstring 与实现不一致。这暗示 agent 可能更依赖 docstring 而非逐行阅读实际逻辑。⚠️

### C.3 "每条是否有明确的牺牲声明？"

✅ **基本诚实**。每条候选都包含"优化了什么"和"牺牲了什么"小节。但部分牺牲声明过于笼统（如 #13 sticker_cache "缓存无过期机制"未区分这是有意设计选择还是遗漏），部分缺乏技术深度。

---

## 综合评分

| 维度 | 评级 | 说明 |
|------|------|------|
| 源码证据准确性 | 8/10 | 大部分行号精确，少数依赖 docstring 而非实现代码 |
| 覆盖完整性 | 5/10 | hermes_cli/ 零覆盖，cron/ 浅覆盖，多个遗漏权衡（见 B 节） |
| 牺牲声明质量 | 7/10 | 每条都有牺牲，但部分深度不足 |
| 自审诚实性 | 4/10 | 目录覆盖声明不实（hermes_cli/ 缺失），部分行号引用可能未深度阅读代码 |

---

## 关键遗漏总结

候选清单遗漏的最重要权衡（跨所有盲区）：

1. **Smart Approval LLM 安全决策**（approval.py）— 将安全决策从确定性规则委托给 LLM 的权衡
2. **hermes_cli/ 全目录零覆盖** — CLI 界面、认证流程、配置管理、备份、troubleshooting 等模块完全未分析
3. **cron jobs JSON 持久化无事务保证**（cron/jobs.py）— 数据完整性 vs 部署简单性的经典权衡
4. **context_compressor 三级错误恢复**（冷却/回退/跳过）— 多层降级策略的权衡
5. **prompt_caching 仅 Anthropic**（agent/prompt_caching.py）— 单 provider 优化 vs 多 provider 公平性
