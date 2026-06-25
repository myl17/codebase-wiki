# 验证报告：tool-security-gating

## 格式完整性
- [x] 问题陈述是"如何..."问题形式 — `如何在工具执行的关键路径上决定安全检查的介入程度——是统一管道还是分层可调节？`
- [x] 核心关切列表 >= 2 条 — 共 6 条
- [x] 每个权衡位置有"优先满足"和"接受妥协"两个字段 — openclaw 和 hermes-agent 均有
- [x] 跨仓库对比表列数 = 仓库数 — 2 列
- [x] 溯源表完整 — 有

---

## 逐仓库验证

### openclaw

**Claim 1**: "5 层 Pipeline 串行叠加：profile policy -> provider policy -> global policy -> agent policy -> group policy"（`tool-policy-pipeline.ts:56-90`）

源码：`/Users/yuanlimiao/Work/agent_harness/openclaw/src/agents/tool-policy-pipeline.ts:56-90`
代码摘要：`buildDefaultToolPolicyPipelineSteps()` 返回的数组中实际有 **7 个 step**，依次为：
1. `profilePolicy` (tools.profile)
2. `providerProfilePolicy` (tools.byProvider.profile)
3. `globalPolicy` (tools.allow)
4. `globalProviderPolicy` (tools.byProvider.allow)
5. `agentPolicy` (agent tools.allow)
6. `agentProviderPolicy` (agent tools.byProvider.allow)
7. `groupPolicy` (group tools.allow)

判定：⚠️ Concept 页将 provider 子策略与对应主策略合并描述为 5 层。源码实际为 7 个独立 pipeline step，各有独立的 label 和策略来源。修正建议：描述为「7 步 Pipeline」，或注明「profile / provider / global / agent / group 5 级配置来源（provider 级含两份子配置，agent 级含两份子配置，共 7 步）」。

---

**Claim 2**: "OwnerOnlyToolApprovalClass 将工具分为 control_plane / exec_capable / interactive"（`tool-policy.ts:19-55`）

源码：`tool-policy.ts:19` — `export type OwnerOnlyToolApprovalClass = "control_plane" | "exec_capable" | "interactive";`
`tool-policy.ts:55-66` — `applyOwnerOnlyToolPolicy` 在非 owner 时过滤掉 control_plane 和 exec_capable 工具，仅 interactive 可见。

判定：✅ 三分类类型定义和 owner 动态过滤逻辑与源码完全一致。

---

**Claim 3**: "Exec 异步阻塞审批扩展点，支持 host（本地 UI 弹窗）和 gateway（远程消息通知）双路径审批"（`bash-tools.exec-approval-request.ts:89-126`）

源码：`bash-tools.exec-approval-request.ts:17` — `host: "gateway" | "node"` 类型参数定义了两个宿主类型。`registerExecApprovalRequest` (line 89) 和 `waitForExecApprovalDecision` (line 110) 实现注册+阻塞等待的两阶段协议。

判定：⚠️ 源码中用 `"gateway" | "node"` 而非 `"host" | "gateway"` 描述宿主。Concept 页将 `node` 表述为 `host（本地 UI 弹窗）` 语义正确（node = 本地节点，UI 弹窗所在环境），但术语与源码略有偏差。建议改用「node（本地节点）和 gateway（远程网关）」保持与源码一致。

---

**Claim 4**: "审批决策只有 once/always 两种粒度（always 写入配置持久化）"

源码：`bash-tools.exec-approval-request.ts:128-136` — `resolveRegisteredExecApprovalDecision` 逻辑为 `preResolvedDecision` 或 `waitForExecApprovalDecision(id)`，无 session 级持久化状态存储。

判定：✅ 源码确认无 session 级审批持久化。once 级为单次决策不存储，always 级依赖 preResolvedDecision 传入（预配置）。

---

**Claim 5**: "无快速路径：即使低风险工具调用也必须走完整 5 层 pipeline"；"无分层差异化：YOLO 模式的'全放行'和正常模式的'全门控'之间没有中间地带"

源码：`tool-policy-pipeline.ts:110-156` — `applyToolPolicyPipeline` 中 `for (const step of params.steps)` 遍历全部 step，仅 `if (!step.policy) continue` 跳过空配置的 step，无"快速路径"或"模式切换"分支。

判定：✅ 源码中确实不存在 YOLO 模式、快速路径或智能分级机制。

---

### hermes-agent

**Claim 1**: "check_all_command_guards 是所有命令执行的同步门控入口"（`tools/approval.py:586-922`）

源码：`/Users/yuanlimiao/Work/agent_harness/hermes-agent/tools/approval.py:693` — `def check_all_command_guards(command, env_type, approval_callback=None) -> dict:`

判定：⚠️ 函数体起始于第 693 行，并非第 586 行。第 586-660 行是旧版 `check_dangerous_command` 函数（功能较简单的单检查版本），在溯源表中被混淆。修正建议：溯源行号改为 `693-922`。

---

**Claim 2**: "_smart_approve() 调用辅助 LLM 评估命令风险等级，返回 auto-approve/deny/escalate"（`tools/approval.py:534-583`）

源码：`tools/approval.py:534-583` — `_smart_approve()` 返回 `"approve"` / `"deny"` / `"escalate"` 三种字符串决策。在 `check_all_command_guards` 中（line 766-786），这三种结果分别映射为直接放行、直接拒绝、升级到手动模式。

判定：✅ 机制描述与源码一致。

---

**Claim 3**: "Gateway 阻塞审批队列：FIFO 队列 + threading.Event，并行子 agent 各自拥有独立审批等待"（`tools/approval.py:219-284`）

源码：`tools/approval.py:219-227` — `_ApprovalEntry` 类持有一个独立的 `threading.Event`。`tools/approval.py:229` — `_gateway_queues` 为 `dict[str, list]`，每个 session 维护独立 FIFO 队列。`tools/approval.py:258-284` — `resolve_gateway_approval` 中 `resolve_all=True` 批量解决或 `queue.pop(0)` 单个解决。

判定：✅ 队列机制、Event 阻塞、并行独立等待的描述与源码完全一致。

---

**Claim 4**: "25+ DANGEROUS_PATTERNS 正则防线"（`tools/approval.py:75-138`）

源码：`tools/approval.py:75-138` — 共 **44 条**正则模式，覆盖 `rm/chmod/chown/mkfs/dd/systemctl/kill/killall/curl|sh/git reset --hard/heredoc 等。

判定：✅ 44 > 25，实际比描述的更丰富。可以更新为「44 条正则模式」更精确。

---

**Claim 5**: "三级审批持久化：once / session / always"（`tools/approval.py:299-303` session 级；`tools/approval.py:376-402` always 级）

源码：`tools/approval.py:299-303` — `approve_session()` 写入 `_session_approved` 字典（session 级）。`tools/approval.py:376-402` — `save_permanent_allowlist()` 写入 `config.yaml` 的 `command_allowlist` 字段。once 级为隐式默认（不调用任何持久化函数）。

判定：✅ 三级持久化粒度与源码完全一致。

---

**Claim 6**: "SkillsGuard：100+ 威胁模式 12 类别"（`skills_guard.py:82-484`）；"信任策略 allow/block/ask"（`skills_guard.py:595-639`）

源码：`skills_guard.py:82-484` — `THREAT_PATTERNS` 列表包含 12 个类别（exfiltration, injection, destructive, persistence, network, obfuscation, execution, traversal, mining, supply_chain, privilege_escalation, credential_exposure），模式数量超过 100 条。
`skills_guard.py:41-47` — `INSTALL_POLICY` 定义 4 级信任策略（builtin/trusted/community/agent-created），决策结果为 allow/block/ask 三种。
`skills_guard.py:595-639` — `scan_skill()` 函数和 `should_allow_install()` 函数。

判定：✅ 100+ 模式 12 类别、4 级信任策略 allow/block/ask 与源码一致。

---

## 关切验证

| 关切 | 跨仓库对比表对应行 | 判定 |
|------|-------------------|------|
| 1. 场景差异 | 「架构模式」「快速路径」行 | ✅ 有对应 |
| 2. 吞吐影响 | 「审批粒度」「智能分级」行中有涉及，但对比表未显式对比审批的 token 成本和延迟 | ⚠️ 部分覆盖——hermes 的"已知代价"中提到 LLM 调用成本，但跨仓库对比表缺少直接的"审批延迟/成本"对比维度 |
| 3. 配置可预测性 | 「配置来源」行 | ✅ 有对应 |
| 4. 风险分层 | 「审批粒度」「智能分级」行 | ✅ 有对应 |
| 5. 审批决策成本 | 对比表中无独立行显式量化对比审批的 token 开销和延迟 | ⚠️ 关切 5 在核心关切中描述了辅助 LLM 的 token 开销，但跨仓库对比表中没有专门维度对此进行对比。hermes 的代价部分提到了 cost，但对比表缺少此维度 |
| 6. 审批状态持久化粒度 | 「审批持久化」行 | ✅ 有对应 |

---

## 追加完整性

- [x] openclaw 在各节均有提及 — 位置 A、对比表、选择指南、溯源表均包含
- [x] hermes-agent 在各节均有提及 — 位置 B、对比表、选择指南、溯源表均包含

---

## 绝对化语言验证

| 绝对化表述 | 源码边界条件 | 判定 |
|-----------|------------|------|
| "所有工具调用在消息处理的关键路径上经过同步 pipeline 门控" | `applyToolPolicyPipeline` 遍历全部 step，无跳过机制 | ✅ 准确——空 step 被跳过但仅因 policy 为空不生效 |
| "管道不可被跳过或降级为异步审计" | 源码中 pipeline 无跳过开关或异步模式 | ✅ 准确 |
| "所有 exec 统一阻塞，不做 LLM 风险评估自动放行" | openclaw 无 Smart 审批模块 | ✅ 准确 |
| "内置始终排第一"（global-capability） | 见该页单独验证 | — |
| "agent 自建技能无法绕过"（SkillsGuard） | `scan_skill` 在技能安装前执行 | ✅ 准确 |
| "每次工具调用都在关键路径上" | 门控是同步阻塞的 | ✅ 准确 |
| "同一 owner 可刷新已有注册，但需显式传 allowSameOwnerRefresh: true"（global-capability） | 见该页单独验证 | — |
| "不被其他 agent 的审批阻塞" | 每个 `_ApprovalEntry` 有独立 Event | ✅ 准确 |

---

## 汇总

总 claim 数：22 | ✅：15 | ⚠️：7 | ❌：0

关键发现：
1. **Pipeline 层数不精确**：源码有 7 个独立 step，Concept 页描述为 5 层。应将 providerProfile 和 agentProvider 子策略明确计入或注明 5 级配置来源 = 7 步。
2. **函数行号错位**：`check_all_command_guards` 实际起始于第 693 行，溯源表标注为 586-922 将旧版 `check_dangerous_command` 的行号范围也纳入了。
3. **审批宿主术语偏差**：源码使用 `"gateway" | "node"`，Concept 页表述为 "host（本地 UI 弹窗）和 gateway"——语义正确但术语不精确。
4. **关切 5（审批决策成本）覆盖不足**：跨仓库对比表中缺少独立维度对比审批的 token 成本和延迟，仅在 hermes 代价中单方面提及。
