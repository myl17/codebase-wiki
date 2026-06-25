# 验证报告：approval-blocking-mechanism

**验证时间**：2026-06-19
**验证方法**：以 wiki 维度页和节点页记录的源码引用为唯一基准，不访问原始源码
**待验证文件**：`experiments/entity-concept-extraction/v2-validation-2026-06-19/round-2-hermes/phase-3a-concepts/approval-blocking-mechanism.md`

---

## A. 格式完整性 Checklist

| 检查项 | 状态 | 说明 |
|--------|------|------|
| YAML frontmatter（concept/instances） | ✅ | concept + 2 instances (openclaw, hermes-agent) |
| 标准化问题陈述 | ✅ | 明确对比维度：异步 Promise vs 同步 threading.Event |
| 核心关切（5条） | ✅ | 5 条均具体、可验证 |
| 实例矩阵表 | ✅ | 4 列：阻塞机制、等待原语、审批路径、核心权衡 |
| 每仓库独立机制描述 | ✅ | openclaw + hermes-agent 各一节 |
| 设计取向表（满足/妥协） | ✅ | 每个仓库各有满足的关切与接受妥协的关切 |
| 权衡对比表（多维度） | ✅ | 12 维度 x 2 仓库，覆盖全面 |
| 选择指南 | ✅ | 6 条场景推荐 |
| 关键源码引用表 | ✅ | 9 行引用，含仓库/文件/行号/内容 |
| 关联（wikilink） | ✅ | 8 个 wikilink |

---

## B. 逐仓库逐 Claim 判定

### B1. openclaw Claims

#### Claim 1: ExecApprovalRequest 扩展点位于 `src/agents/bash-tools.exec-approval-request.ts:89-126`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`openclaw-exec-approval-request.md` 节点页 frontmatter `sources` 字段和正文脚注均引用 `src/agents/bash-tools.exec-approval-request.ts:89-126`。`openclaw-architecture.md` 维度页同样引用 `^[src/agents/bash-tools.exec-approval-request.ts:89-126]` 并描述为"注册 ExecApprovalRequest，阻塞等待 owner 决策（waitForExecApprovalDecision）" |

#### Claim 2: 5 层同步 pipeline 位于 `src/agents/tool-policy-pipeline.ts:56-90`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`openclaw-tool-policy.md` 节点页 `sources` 和脚注引用 `src/agents/tool-policy-pipeline.ts:56-90`。`openclaw-architecture.md` 维度页描述为"profile policy、provider policy、global policy、agent policy、group policy 共 5 层叠加" |

#### Claim 3: OwnerOnlyToolApprovalClass 三类工具分治位于 `src/agents/tool-policy.ts:19-55`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`openclaw-tool-policy.md` 节点页 `sources` 含 `src/agents/tool-policy.ts:19-55`。`openclaw-architecture.md` 维度页明确列出三类：`control_plane`、`exec_capable`、`interactive`，与 concept 页一致 |

#### Claim 4: 审批是异步 Promise 等待（"不占事件循环"）

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 语义一致**。`openclaw-exec-approval-request.md` 描述为"异步阻塞审批扩展点"，`openclaw-sync-gating-decision.md` 描述为"exec 类工具额外阻塞等待 owner 审批"。wiki 未展开讨论 Promise rejection / AbortController 内部机制，但"异步阻塞"定性一致 |

#### Claim 5: 双路径审批（Host CLI + Gateway HTTP）

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`openclaw-exec-approval-request.md` 正文："支持 host/gateway 双路径" |

#### Claim 6: 扩展点可注入自定义审批逻辑

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`openclaw-exec-approval-request.md`："二开时在此注入自定义审批逻辑（UI 弹窗、Slack 通知等），不需改动 ToolPolicy pipeline" |

#### Claim 7: `waitForExecApprovalDecision` 方法名

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 未明确记录此方法名**。wiki 节点页和维度页提到了 `waitForExecApprovalDecision`，但仅出现在 concept 页的关键源码引用表描述中。wiki 节点正文未逐字列此 API 名，属概念页细节增强 |

---

### B2. hermes-agent Claims

#### Claim 1: `check_all_command_guards` 位于 `tools/approval.py:586-922`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-approval-system.md` 节点页 `sources` 和脚注引用 `tools/approval.py:586-922`。`hermes-agent-layered-approval-decision.md` 同样引用此范围。`hermes-agent-architecture.md` 维度页多处引用此范围 |

#### Claim 2: 三层审批（Layer 0/1/2）

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-layered-approval-decision.md` 节点页正文明确描述三层。`hermes-agent-architecture.md` 维度页以表格呈现完全相同三层（Layer 0: YOLO/容器/off；Layer 1: Smart aux LLM；Layer 2: Manual tirith + DANGEROUS_PATTERNS） |

#### Claim 3: FIFO 队列 + `threading.Event` 位于 `tools/approval.py:219-284`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-approval-system.md` 节点页 `sources` 含 `tools/approval.py:219-284`，正文描述"FIFO 队列 + threading.Event 实现阻塞审批：agent 线程挂起等待用户 /approve//deny"。`hermes-agent-architecture.md` 维度页："FIFO 队列 + threading.Event，agent 线程阻塞等待" ^[tools/approval.py:219-284] |

#### Claim 4: 每个并行子 agent 独立 `threading.Event`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 语义一致**。`hermes-agent-approval-system.md` 节点页："并行子 agent 并发等待各自审批"。wiki 未展开 `threading.Event` 实例级别的技术细节，但独立等待定性一致 |

#### Claim 5: Smart Approval 位于 `tools/approval.py:534-583`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-architecture.md` 维度页表头引用 `_smart_approve()` ^[tools/approval.py:534-583] |

#### Claim 6: DANGEROUS_PATTERNS 位于 `tools/approval.py:75-138`

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-architecture.md` 维度页："25+ 正则模式覆盖 rm/chmod/mkfs/kill/systemctl/curl|sh/git reset --hard/gateway self-protection 等 ^[tools/approval.py:75-138]" |

#### Claim 7: 审批级别 `session` 位于 `tools/approval.py:299-303`，`always` 位于 376-402

| 判定 | 说明 |
|------|------|
| ✅ | **wiki 一致**。`hermes-agent-architecture.md` 维度页：`session` — "会话级允许 ^[tools/approval.py:299-303]"；`always` — "写入 config.yaml 的 command_allowlist，跨会话持久化 ^[tools/approval.py:376-402]" |

#### Claim 8: CLI 模式使用 `prompt_toolkit` 同步输入

| 判定 | 说明 |
|------|------|
| ⚠️ | **wiki 部分确认**。`hermes-agent-architecture.md` 分层图显示 CLI 层含 `prompt_toolkit`，但 wiki 未明确将 prompt_toolkit 同步输入与审批阻塞机制关联。concept 页说"CLI 路径使用 prompt_toolkit 的同步输入等待，属另一套机制"——这是合理的架构推论，但 wiki 未交叉引用 |

---

## C. 关切验证

### 关切 1：审批必须是同步阻塞的——命令执行前审批决策必须发生

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 5 层同步 pipeline 后 + ExecApprovalRequest 阻塞等待 | ✅ wiki 确认 |
| hermes-agent | `check_all_command_guards` 统一门控入口，绕过没有合法路径 | ✅ wiki 确认 |

**跨仓库对比表体现**：✅ 对比表第 10 行"门控位置"直接对应

### 关切 2：阻塞等待不应死锁 agent 进程——超时、取消、多审批并发

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | Promise rejection / AbortController 可中断 | ⚠️ wiki 未展开可中断机制细节，仅确认"异步阻塞" |
| hermes-agent | `event.wait(timeout=N)` + 独立 Event per sub-agent | ✅ wiki 确认 FIFO + 并行子 agent 独立等待 |

**跨仓库对比表体现**：✅ 对比表第 5 行"可中断性"、第 4 行"多审批并发"对应

### 关切 3：审批可通过多种路径到达用户

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | Host CLI + Gateway HTTP 双路径 | ✅ wiki 确认双路径 |
| hermes-agent | Gateway 单路径（依赖 `/approve` 回复） | ✅ wiki 确认 Gateway 路径 |

**跨仓库对比表体现**：✅ 对比表第 3 行"审批路径"直接对应

### 关切 4：审批失败或超时不应导致 agent session 永久卡死

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | Promise rejection 传播，超时通过 Promise.race | ⚠️ wiki 未确认具体超时/恢复路径 |
| hermes-agent | `event.wait(timeout=N)` 返回 False 后执行拒绝逻辑 | ✅ wiki 确认超时机制 |

**跨仓库对比表体现**：✅ 对比表第 6 行"超时处理"对应

### 关切 5：并行子 agent 审批请求独立队列和独立等待

| 仓库 | 体现 | 判定 |
|------|------|------|
| openclaw | 每个审批请求独立 Promise | ⚠️ wiki 未明确描述独立 Promise 机制 |
| hermes-agent | 每个子 agent 独立 `threading.Event` + FIFO 队列 | ✅ wiki 确认"并行子 agent 并发等待各自审批" |

**跨仓库对比表体现**：✅ 对比表第 4 行"多审批并发"直接对应

### 关切验证汇总

| 关切 | #1 | #2 | #3 | #4 | #5 |
|------|----|----|----|----|-----|
| 跨仓库对比有对应行 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 悬空（0 个） | -- | -- | -- | -- | -- |

---

## D. 绝对化语言检查

| 位置 | 原文 | 判定 |
|------|------|------|
| openclaw 机制概述 | "所有工具调用做 allowlist/denylist 叠加过滤" | ✅ 可接受——wiki 确认 5 层叠加机制 |
| openclaw 可中断性 | "等待本身是可中断的——超时、取消、连接断开都可以通过 Promise rejection 或 AbortController 传播，不会留下永久悬挂的等待状态" | ⚠️ wiki 未验证 AbortController / 永久不悬挂的具体保证 |
| hermes-agent 机制概述 | "任何 exec 类工具调用必须经过此函数，绕过它没有合法路径" | ✅ 可接受——wiki 确认"绕过它没有合法路径" |
| hermes-agent | "FIFO 队列保证先请求先处理的公平性" | ✅ 可接受——FIFO 即此含义 |
| 权衡对比表 | "同步阻塞在 Node.js 中会冻结整个事件循环，异步等待是唯一正确的选择" | ⚠️ "唯一正确的选择"偏绝对——Worker Threads 也可用于同步阻塞场景 |
| 选择指南 | "异步等待是唯一正确的选择" | ⚠️ 同上 |

---

## E. 汇总计数

| 判定类别 | 数量 |
|----------|------|
| ✅（wiki 直接确认） | 19 |
| ⚠️（wiki 部分确认 / 未覆盖细节 / 合理推论但无法溯源） | 7 |
| ❌（wiki 矛盾） | 0 |

### ⚠️ 清单

1. `waitForExecApprovalDecision` 方法名 — wiki 未逐字记录此 API 名
2. openclaw Promise rejection / AbortController 可中断机制 — wiki 未展开
3. hermes-agent CLI prompt_toolkit 同步输入与审批阻塞的关联 — wiki 未交叉引用
4. openclaw 独立 Promise per sub-agent — wiki 未明确描述
5. openclaw 超时恢复路径的具体实现 — wiki 未确认
6. openclaw "不会留下永久悬挂的等待状态" — wiki 未验证此保证
7. 选择指南中"异步等待是唯一正确的选择" — 绝对化语言，Worker Threads 也可用

### 关键发现

1. **wiki 对 openclaw 审批机制的核心架构事实确认度高**：ExecApprovalRequest 扩展点、5 层 pipeline、双路径、三类工具分治均在 wiki 中有明确记载
2. **wiki 对 hermes-agent 审批机制的核心架构事实确认度极高**：三层审批、FIFO+Event、DANGEROUS_PATTERNS、审批持久化、独立子 agent 等待——全部在 wiki 维度页或节点页中有精确行号引用
3. **concept 页的细节深度超出 wiki 覆盖范围**：Promise rejection / AbortController 可中断机制、CLI prompt_toolkit 关联、方法级 API 名——这些细节在 wiki 中未记录，concept 页对源码细节的掌握比 wiki 更细粒度
4. **行号一致性良好**：所有 claim 的行号与 wiki 节点页/维度页记录的源码行号一致，未发现实质性行号冲突
5. **关切覆盖面完整**：5 条核心关切均在跨仓库对比表中有对应的维度行，无悬空关切
6. **2 处绝对化语言**：选择指南中关于 Node.js 场景"唯一正确的选择"的表述，应降级为"推荐选择"或"自然选择"
