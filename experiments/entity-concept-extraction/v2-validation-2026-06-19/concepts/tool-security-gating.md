---
concept: tool-security-gating
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# 工具执行安全门控：统一管道还是分层可调节？

## 标准化问题陈述

如何在工具执行的关键路径上决定安全检查的介入程度——是统一管道还是分层可调节？

## 核心关切

1. **场景差异**：不同部署场景（容器内自托管 vs 多租户 Gateway）的安全需求差异巨大，统一策略或过于宽松或阻碍正常使用
2. **吞吐影响**：安全门控延迟不应影响正常的消息处理吞吐——门控是同步阻塞操作，每次工具调用都在关键路径上
3. **配置可预测性**：多来源配置（profile/provider/global/agent/group）的叠加规则必须产生可预测的结果，否则运维人员无法信任门控
4. **风险分层**：高风险工具（如 exec 类任意命令执行）需要额外用户确认回路，但低风险工具（如只读查询）不应被同等阻塞
5. **审批决策成本**：辅助 LLM 评估引入额外 token 开销和延迟——安全本身有成本，且该成本随工具调用频率线性增长
6. **审批状态持久化粒度**：审批决策（once/session/always）的持久化粒度直接影响安全性和便利性的平衡——过粗则危险，过细则繁琐

## 已知权衡位置

### 位置 A：openclaw — 统一同步管道

**优先满足的关切**：安全性（7 步 allowlist/denylist 串行过滤，不可旁路）；可预测性（管道顺序固定，叠加规则确定）

**接受妥协的关切**：灵活性（无快速路径，所有工具调用必经全量管道）；审批成本（exec 类工具无智能分级，统一阻塞等待 owner）

**核心特征**：所有工具调用在消息处理的关键路径上经过同步 pipeline 门控——管道执行完之前工具不得执行，管道不可被跳过或降级为异步审计。exec 类工具额外经过异步阻塞审批扩展点，但审批逻辑本身是可插拔的（二开可在扩展点注入自定义审批，不需改动 pipeline 核心）。

**关键机制（源码可见）**：

1. **7 步 Pipeline 串行叠加**（`src/agents/tool-policy-pipeline.ts:56-90`）：`profile → providerProfile → global → globalProvider → agent → agentProvider → group`，7 步独立配置 allowlist/denylist，层层叠加后产生最终工具可见集。5 级配置来源（profile/provider/global/agent/group），其中 provider 级含两份子配置、agent 级含两份子配置，共 7 步串行叠加。管道是同步的——执行前完成，不做事后审计。

2. **工具三分类与 Owner 动态过滤**（`src/agents/tool-policy.ts:19-55`）：`OwnerOnlyToolApprovalClass` 将工具分为 `control_plane`（控制平面，仅 owner 可见）、`exec_capable`（可执行任意命令，需审批）、`interactive`（交互式，按需授权）。`applyOwnerOnlyToolPolicy` 根据 sender 是否为 owner 动态裁剪工具集——非 owner 看不到 `control_plane` 和 `exec_capable`。

3. **Exec 异步阻塞审批扩展点**（`src/agents/bash-tools.exec-approval-request.ts:89-126`）：注册 `ExecApprovalRequest` 后调用 `waitForExecApprovalDecision`，agent 线程阻塞等待 owner 决策，支持 node（本地节点，UI 弹窗所在环境）和 gateway（远程网关，消息通知）双路径审批。这是 ExtensionPoint 模式——二开可替换审批实现但不影响 ToolPolicy pipeline 核心。

**已知代价**：
- 无快速路径：即使低风险工具调用也必须走完整 7 步 pipeline
- exec 类工具无智能分级：所有 exec 统一阻塞，不做 LLM 风险评估自动放行
- 审批决策只有 once/always 两种粒度（always 写入配置持久化），无 session 级审批状态
- 无分层差异化：YOLO 模式的"全放行"和正常模式的"全门控"之间没有中间地带

**已知实例**：
- [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]]
- [[openclaw/nodes/components/openclaw-tool-policy]]
- [[openclaw/nodes/extension-points/openclaw-exec-approval-request]]

---

### 位置 B：hermes-agent — 三层渐进式审批

**优先满足的关切**：灵活性（YOLO 快速路径 + Smart LLM 自动分级 + Manual 交互审批，可场景切换）；场景适配（容器/off/YOLO/smart/manual 四种模式覆盖不同部署场景）

**接受妥协的关切**：一致性（Layer 1 Smart 的自动审批边界依赖 LLM 判断质量，结果不完全确定；Layer 2 Manual 的正则匹配有边界模糊问题）；复杂度（三层 + 44 条正则 + 辅助 LLM 调用 + 三级持久化 + 并发审批队列，运维心智负担重）

**核心特征**：命令审批从二元开关演进为三层架构——Layer 0 快速路径全放行不检查、Layer 1 Smart 用辅助 LLM 做风险评估自动批/拒/升级、Layer 2 Manual 用正则 + 交互式审批做最终防线。每层可独立开关和配置，审批结果支持 once/session/always 三级持久化。

**关键机制（源码可见）**：

1. **三层审批总入口**（`tools/approval.py:693-922`）：`check_all_command_guards` 是所有命令执行的同步门控入口。三层依次判断：Layer 0 命中 YOLO/容器/off 模式直接返回放行；Layer 1 走 `_smart_approve()` 辅助 LLM 风险评估；Layer 2 走 tirith 安全规则 + `DANGEROUS_PATTERNS` 正则匹配后向用户展示交互式审批提示。

2. **Smart 辅助 LLM 自动分级**（`tools/approval.py:534-583`）：`_smart_approve()` 调用辅助 LLM 评估命令风险等级，根据返回的风险评分自动做出三种决策：`auto-approve`（低风险，直接放行）、`auto-deny`（高风险，直接拒绝）、`escalate`（中等风险，升级到 Layer 2 Manual 模式）。这层在牺牲一致性的同时换取了无需人类等待的快速路径。

3. **Gateway 阻塞审批队列**（`tools/approval.py:219-284`）：Gateway 模式下用 FIFO 队列 + `threading.Event` 实现阻塞审批。agent 线程挂起等待用户通过聊天消息发送 `/approve` 或 `/deny`，并行子 agent 各自拥有独立的审批等待——不被其他 agent 的审批阻塞。

4. **44 条 DANGEROUS_PATTERNS 正则防线**（`tools/approval.py:75-138`）：覆盖 `rm -rf`、`chmod 777`、`mkfs`、`kill -9`、`systemctl stop`、`curl | sh`、`git reset --hard`、`dd if=`、Gateway 自身进程保护等危险模式。这些正则作为 Layer 2 Manual 的输入，与 tirith 安全规则合并后展示给用户。

5. **三级审批持久化**（`tools/approval.py:299-303` session 级；`tools/approval.py:376-402` always 级）：`once` 仅本次有效、`session` 会话级记忆（同会话后续同类命令自动放行）、`always` 写入 `config.yaml` 的 `command_allowlist` 跨会话持久化。always 级持久化降低了重复审批的摩擦，但引入了持久化条目的管理负担。

**已知代价**：
- Layer 1 Smart 每次调用消耗一次辅助 LLM 调用的 token 成本和延迟
- Layer 2 Manual 的 44 条正则边界依赖人工维护，新危险命令类型可能不匹配
- 三层之间边界非硬隔离——Smart 升级到 Manual 的判断依赖 LLM 输出质量
- always 级持久化条目随时间累积，需人工清理过期条目
- 并发审批队列的 `threading.Event` 在子 agent 嵌套时增加调试复杂度

**已知实例**：
- [[hermes-agent/nodes/design-decisions/hermes-agent-layered-approval-decision]]
- [[hermes-agent/nodes/components/hermes-agent-approval-system]]
- [[hermes-agent/nodes/components/hermes-agent-skills-guard]]

---

## 跨仓库对比

| 维度 | openclaw（统一同步管道） | hermes-agent（三层渐进式审批） |
|------|--------------------------|-------------------------------|
| **架构模式** | 7 步串行 pipeline（5 级配置来源），不可旁路 | 3 层渐进，每层可独立配置/关闭 |
| **快速路径** | 无——所有调用必须走完整管道 | 有——Layer 0 YOLO/容器/off 模式全放行 |
| **审批粒度** | 二分类：exec 类阻塞审批 / 非 exec 类只做可见性过滤 | 三分级：LLM 自动审批 / 正则+交互审批 / 直接放行 |
| **智能分级** | 无——exec 统一阻塞，不做风险评估 | 有——Layer 1 Smart 辅助 LLM 自动分 low/medium/high 风险 |
| **审批成本** | 固定管道遍历开销（7 步叠加，纯内存计算，延迟可忽略）；exec 类阻塞等待人工决策时间 | Layer 1 Smart 每次调用消耗一次辅助 LLM 的 token 成本和推理延迟；Layer 2 Manual 消耗人工等待时间；三层整体延迟随调用频率线性增长 |
| **审批持久化** | once / always 两级（always 写入配置） | once / session / always 三级（session 级降低重复摩擦） |
| **并发审批** | 单路径阻塞——一次等一个审批决策 | FIFO 队列 + threading.Event——多 agent 并行等待互不阻塞 |
| **配置来源** | 7 步叠加（profile/providerProfile/global/globalProvider/agent/agentProvider/group），确定性叠加 | 3 层 + 4 模式切换 + 正则规则集 + tirith，组合空间大 |
| **安全扫描配套** | 无独立 skill 扫描——工具门控即安全边界 | 独立 SkillsGuard：100+ 威胁模式 12 类别，agent 自建 skill 落盘前必经 |
| **核心取舍** | 宁可全部阻塞也不漏过一个（安全性压倒灵活性） | 宁可复杂度高也要分层可调节（灵活性压倒一致性） |

## 选择指南

| 场景 | 推荐偏向 | 理由 |
|------|---------|------|
| 单用户自托管，安全性为首要约束 | openclaw 统一管道 | 管道可被代码静态验证，不依赖 LLM 判断质量和运行时日志 |
| 多用户 Gateway，需适配不同用户风险容忍度 | hermes-agent 三层渐进 | 可为不同用户/平台配置不同审批模式，YOLO 模式对信任用户无摩擦 |
| 工具调用频率极高，延迟敏感 | hermes-agent Smart 模式 | Layer 1 LLM 自动分级减少人工等待，低风险命令无需阻塞 |
| 运维团队需要可审计的安全决策轨迹 | openclaw 统一管道 | 管道叠加规则确定，每次门控决策可追溯到具体配置层 |
| 大量社区/第三方技能需要安全审查 | hermes-agent SkillsGuard | 100+ 威胁模式 + 4 级信任策略，agent 自建技能无法绕过 |
| 安全团队要求零信任——任何 AI 发起的命令必须人工确认 | openclaw exec 审批扩展点 | 可注入自定义审批 UI（弹窗/Slack/审计系统），不依赖 LLM 自动判断 |

## 溯源表

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/agents/tool-policy-pipeline.ts` | 56-90 | 7 步 Pipeline 串行叠加：profile → providerProfile → global → globalProvider → agent → agentProvider → group |
| openclaw | `src/agents/tool-policy.ts` | 19-55 | OwnerOnlyToolApprovalClass 三分类 + applyOwnerOnlyToolPolicy 动态过滤 |
| openclaw | `src/agents/bash-tools.exec-approval-request.ts` | 89-126 | ExecApprovalRequest 注册 + waitForExecApprovalDecision 阻塞等待 + node/gateway 双路径 |
| hermes-agent | `tools/approval.py` | 693-922 | check_all_command_guards 三层审批总入口 |
| hermes-agent | `tools/approval.py` | 534-583 | _smart_approve() 辅助 LLM 风险评估 → auto-approve/deny/escalate |
| hermes-agent | `tools/approval.py` | 219-284 | Gateway FIFO 队列 + threading.Event 阻塞审批（并行子 agent 独立等待） |
| hermes-agent | `tools/approval.py` | 75-138 | DANGEROUS_PATTERNS：44 条正则覆盖 rm/chmod/mkfs/kill/systemctl/curl\|sh/git reset --hard 等 |
| hermes-agent | `tools/approval.py` | 299-303 | Session 级审批持久化 |
| hermes-agent | `tools/approval.py` | 376-402 | Always 级审批持久化（写入 config.yaml command_allowlist） |
| hermes-agent | `tools/skills_guard.py` | 595-639 | scan_skill 入口 + 信任策略 allow/block/ask |
| hermes-agent | `tools/skills_guard.py` | 82-484 | 100+ 威胁模式 12 类别（exfiltration/injection/destructive/persistence 等） |

## 关联

- [[openclaw/dimensions/openclaw-architecture]] — Tool Policy / 权限管理层（第 4 子系统）
- [[hermes-agent/dimensions/hermes-agent-architecture]] — 安全层（三层审批架构 + Skill 安全扫描）
- [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]] — 7 步同步门控设计决策
- [[openclaw/nodes/components/openclaw-tool-policy]] — ToolPolicy 组件
- [[openclaw/nodes/extension-points/openclaw-exec-approval-request]] — ExecApprovalRequest 扩展点
- [[hermes-agent/nodes/design-decisions/hermes-agent-layered-approval-decision]] — 三层审批设计决策
- [[hermes-agent/nodes/components/hermes-agent-approval-system]] — Approval System 组件
- [[hermes-agent/nodes/components/hermes-agent-skills-guard]] — SkillsGuard 组件
- [[人机审批协议]] — 父级 concept（人机审批协议维度）

---

## 修复记录

**2026-06-19**：根据 `phase-3b-verify/tool-security-gating-verify.md` 修复 6 项 ⚠️：

1. **Pipeline 层数**：全文「5 层」→「7 步 Pipeline（5 级配置来源，provider 和 agent 级各含两份子配置，共 7 步串行叠加）」。涉及位置：优先满足的关切、关键机制 #1、已知代价、对比表架构模式行和配置来源行、溯源表 openclaw row 1、关联节设计决策引用。
2. **审批宿主术语**：`host（本地 UI 弹窗）` → `node（本地节点，UI 弹窗所在环境）`，与源码 `"gateway" | "node"` 术语对齐。同步修正溯源表 openclaw row 3 中的 host/gateway → node/gateway。
3. **check_all_command_guards 行号**：关键机制 #1 行号 `586-922` → `693-922`，溯源表同步修正（旧版 `check_dangerous_command` 的行号范围被混入，实际函数体起始于第 693 行）。
4. **DANGEROUS_PATTERNS 计数**：全文「25+」→「44 条」（源码实际 44 条正则模式）。涉及位置：关键机制 #4、已知代价、接受妥协的关切、溯源表 hermes-agent row 4。
5. **关切 2+5 覆盖不足**：跨仓库对比表新增「审批成本」行，显式对比双方审批的延迟来源和 token 开销（openclaw 固定管道遍历开销 + 人工等待；hermes 辅助 LLM token 成本 + 推理延迟 + 人工等待，延迟随调用频率线性增长）。
6. **修复记录**：追加本段。
