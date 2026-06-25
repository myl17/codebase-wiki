# Tool Execution Safety Approval

## 问题陈述

如何为高风险工具执行设计安全审批机制？——当 AI 编程助手需要执行 shell 命令时，哪些命令应该放行、哪些需要审批、谁来做决策、审批期间 agent 是继续执行还是阻塞等待、审批超时或失败时如何兜底。

[[openclaw-tool-policy]] 和 [[hermes-approval-system]] 分别给出了两个独立实现，代表了两种不同的审批哲学。

## 核心对比

| 维度 | OpenClaw | Hermes Agent |
|------|----------|-------------|
| 审批触发 | exec 类工具，在 host 层做同步门控 | 命令执行前，包含容器检测 + dangerous pattern 匹配 + tirith 安全扫描 |
| 审批决策者 | 人类 owner（通过 `/approve` 或 `/deny`） | 三层：YOLO 全放行 / 辅助 LLM 自动评估 / 用户交互式审批 |
| 阻塞方式 | 异步注册 + 同步阻塞等待（gateway RPC） | CLI：`input()` + threading timeout；Gateway：FIFO 队列 + `threading.Event` 阻塞 |
| 审批超时 | 30 分钟（`DEFAULT_EXEC_APPROVAL_TIMEOUT_MS = 1_800_000`） | CLI：60 秒；Gateway：300 秒（均可通过 config 调整） |
| 超时兜底 | 返回 `null`，fallback 到 `askFallback` 策略（默认 `deny`，超时时拒绝执行；`full` 模式下超时放行） | 超时视为 deny，返回 "BLOCKED" 消息，指示 agent 不可重试 |
| 容器环境 | 不做特殊豁免（依赖 owner 配置 `ask` 策略） | 容器环境（docker/singularity/modal/daytona）直接放行 |
| 审批持久化 | 无内置持久化。每次 exec 独立审批，`allow-always` 由 policy 配置控制 | 三级：`once`（单次）、`session`（会话级内存）、`always`（写入 config.yaml 跨会话持久化） |
| 审批通道 | 双路径：gateway 通道（命令在 gateway 服务器执行）和 node 通道（命令在远程节点执行），各有独立的注册/等待逻辑 | 双环境：CLI 交互（同步 `input()` 阻塞）和 Gateway 异步（队列 + Event 跨线程阻塞），共享同一套审批核心 |

## 架构分析

### OpenClaw：政策驱动的同步门控

OpenClaw 的审批系统是一个**政策驱动、人类在循环中的同步门控**。它不是判断命令是否危险，而是将所有 exec 类工具的执行权限问题交给**预先配置的政策**和**运行时的 owner 决策**。

**审批流程**：

```
工具调用 → tool-policy pipeline 过滤工具可见性
         → exec host 层检查 ask/security 配置
         → 需要审批 → registerExecApprovalRequest (两阶段注册)
                    → 服务端创建审批记录，注册到 pending map
                    → waitForExecApprovalDecision (阻塞等待)
                    → owner 通过 /approve 或 /deny 响应
                    → 决策返回，继续执行或拒绝
```

**关键实现细节**（来源：`src/agents/bash-tools.exec-approval-request.ts`）：

1. **两阶段注册协议**：先调用 `exec.approval.request` 注册审批请求到服务端，再调用 `exec.approval.waitDecision` 阻塞等待决策。两层解耦确保了审批 ID 在 `/approve` 命令到达之前就已经注册完毕，避免了竞态条件。

2. **同步阻塞（取决于 channel 类型）**：`requestExecApprovalDecision` 的阻塞行为受 channel 类型影响。内部消息 channel（Web Chat UI）真正同步阻塞，agent 线程挂起等待审批决策；外部 IM channel（Telegram、WhatsApp、Discord 等）走异步非阻塞模式，函数返回 `pendingResult` 立即返还给 agent loop，实际命令执行和审批等待在后台 Promise 中进行。

3. **双路径分发**：
   - **Gateway 路径**（`bash-tools.exec-host-gateway.ts`）：命令在 gateway 服务器本地执行，审批请求携带 `host: "gateway"`。
   - **Node 路径**（`bash-tools.exec-host-node.ts`）：命令在远程节点执行，审批请求携带 `host: "node"` + `systemRunPlan`（包含 argv、cwd、env 等完整执行计划） + `nodeId`。Node 路径在服务端有更严格的参数校验（必须有 `commandArgv` 和 `systemRunPlan`）。

4. **超时与兜底**（来源：`src/infra/exec-approvals.ts:167`）：
   - 审批超时为 30 分钟（1,800,000ms），远超典型的人工响应时间，设计意图是给异步审批（如移动端推送）留足窗口。
   - 超时时 `waitForExecApprovalDecision` 返回 `null`，触发 `askFallback`——默认 fallback 为 `deny`，即审批超时时拒绝执行。`askFallback = "full"` 时超时放行执行（`approvedByAsk: true`），`askFallback = "deny"` 时超时拒绝执行（`approvedByAsk: false`）。
   - 注册超时（`DEFAULT_APPROVAL_REQUEST_TIMEOUT_MS`）比审批超时多 10 秒，确保注册请求本身有足够网络余量。

### Hermes Agent：三层递进的风险评估

Hermes 的审批系统是一个**分层递进、从自动到人工逐步升级的风险评估管线**。它在命令执行前做主动的危险性判断，只有真正需要人类判断的情况才会打断用户。

**审批流程**（来源：`tools/approval.py:693-922`，`check_all_command_guards`）：

```
命令执行前 → Layer 0a: Hardline Blocklist + Sudo stdin Guard（无条件拒绝）
                → 命中 hardline 或 sudo -S 密码管道: 直接 BLOCKED（不可绕过）
                → 未命中: 进入 Layer 0b
           → Layer 0b: 容器 / YOLO / approvals.mode=off？
                → YES: 直接放行
                → NO:  进入 Layer 1
           → 收集发现：tirith 安全扫描 + DANGEROUS_PATTERNS 正则匹配
           → Layer 1: approvals.mode=smart？
                → 辅助 LLM 评估 → APPROVE: 自动放行 + 会话级记忆
                               → DENY:  硬拒绝
                               → ESCALATE: 进入 Layer 2
                → 非 smart 模式: 直接进入 Layer 2
           → Layer 2: 合并所有发现 → 单次审批提示
                → CLI: 同步 input() 阻塞
                → Gateway: FIFO 队列 + threading.Event 阻塞
           → 决策: once / session / always / deny
```

**Layer 0a -- Hardline Blocklist + Sudo stdin Guard（无条件拒绝）**：

在所有 bypass 检查之前，先执行两个不可绕过的硬性安全守卫：

- **Hardline Blocklist**（12 个 `HARDLINE_PATTERNS`）：覆盖递归删除系统根/系统目录/家目录、mkfs 格式化、dd 写裸块设备、fork bomb、kill -1、shutdown/reboot/halt/poweroff、init 0/6、systemctl poweroff/reboot、telinit 0/6。**这些命令无法被任何设置绕过**（包括 YOLO、`approvals.mode=off`、cron approve 模式）。
- **Sudo stdin Guard**：阻止 agent 通过 pipe 密码到 `sudo -S` 的暴力破解尝试。

**Layer 0b -- YOLO 全放行**：

三种条件任一满足即放行：
- 容器环境：`env_type in ("docker", "singularity", "modal", "daytona")` -- 容器提供天然隔离，命令即便危险也不会影响宿主机
- YOLO 模式：环境变量 `HERMES_YOLO_MODE` 或 session 级 `/yolo` 开启
- 审批关闭：`approvals.mode = "off"`

**Layer 1 -- Smart 辅助 LLM 自动评估**（来源：`tools/approval.py:534-583`）：

当 `approvals.mode = "smart"` 时启用。核心机制：

1. **模型选择**：通过 `get_text_auxiliary_client(task="approval")` 获取辅助 LLM 客户端。模型可配置（`auxiliary.approval.model` in config.yaml），支持任意 OpenAI-compatible provider。未配置时直接 escalate。
2. **评估 Prompt**：构造一个零样本分类 prompt，要求 LLM 区分三类情况：
   - **APPROVE**（明显安全）：良性脚本执行、安全文件操作、开发工具调用、包安装、git 操作等
   - **DENY**（明显危险）：递归删除重要路径、覆盖系统文件、fork bomb、擦除磁盘、删除数据库等
   - **ESCALATE**（模糊地带）：无法确定时升级到人工审批
3. **自动放行的附带效果**：Approved 的命令不仅本次放行，该危险模式还会被自动加入 session 级白名单，同一会话内相同模式不再触发审批。
4. **容错**：LLM 调用异常时直接 escalate，不阻塞执行。

**Layer 2 -- Manual 交互式审批**（来源：`tools/approval.py:409-491`）：

- **CLI 路径**：使用 `input()` 配合 daemon 线程 + `thread.join(timeout=60)`。四个选项：
  - `[o]nce`：仅本次有效，下次相同模式仍需审批
  - `[s]ession`：会话级生效，写入内存 set
  - `[a]lways`：写入 `config.yaml` 的 `command_allowlist`，跨会话永久生效（当检测到 tirith 安全问题时此选项隐藏，防止对内容级安全发现做宽泛的永久放行）
  - `[d]eny`：拒绝，返回 "BLOCKED" 消息，明确告诉 agent 不可重试

- **Gateway 路径**（来源：`tools/approval.py:219-284`）：使用 `_ApprovalEntry` 队列 + `threading.Event` 实现跨线程阻塞。关键机制：
  - 每个审批请求创建一个 `_ApprovalEntry`，包含独立的 `threading.Event`
  - Agent 线程调用 `entry.event.wait(timeout=300)` 阻塞（默认 5 分钟）
  - 用户通过 `/approve` 或 `/deny` 命令触发 `resolve_gateway_approval`，设置 `entry.result` 并 `event.set()` 唤醒 agent 线程
  - 支持 `/approve all` 一次性解决所有待审批命令
  - Session 结束时自动清理（`unregister_gateway_notify` 唤醒所有等待线程）

**Tirith 安全扫描集成**（来源：`tools/approval.py:693-759`）：

Hermes 在审批前并行运行两套检测——tirith 安全扫描和 dangerous pattern 正则匹配——然后将发现**合并**为单次审批提示。这杜绝了 gateway 的 `force=True` 重放只绕过其中一项检查的漏洞。Tirith 的 `block` 和 `warn` 级别发现都会进入审批流，用户可以看到具体的安全发现描述后做出知情决策。

**危险模式覆盖**（来源：`tools/approval.py:75-138`）：

25+ 正则模式覆盖：`rm -rf /`（根路径删除）、`chmod 777`（全局可写）、`mkfs`（格式化文件系统）、`dd`（磁盘拷贝）、`> /dev/sd*`（写块设备）、SQL DROP/TRUNCATE/DELETE WITHOUT WHERE、`systemctl stop`（停止系统服务）、`kill -9 -1`（杀所有进程）、fork bomb、`curl | sh`（管道远程内容到 shell）、`find -exec rm`、`git reset --hard`、`git push --force`、hermes gateway 自终止防护（`hermes gateway stop/restart`、`pkill hermes`）、`sed -i /etc/` 等。

## 设计对比

### 哲学分歧：政策驱动 vs 检测驱动

OpenClaw 的核心理念是**不判断命令危险性，只管理执行权限**。它依赖外部配置（`security` 级别 + `ask` 策略 + `allowlist`）来定义哪些命令需要审批，而不是在代码中枚举危险模式。这带来的结果是：OpenClaw 的审批系统极度简洁（<250 行核心逻辑），但需要使用者在 `exec-approvals.json` 中正确配置策略才能发挥作用。

Hermes 的核心理念是**主动检测危险 + 分层降低审批负担**。它在代码中维护了 25+ 个危险模式正则，用辅助 LLM 做智能预筛，目标是让大多数安全命令完全不触发审批。这带来的结果是：Hermes 的审批系统功能更丰富（~900 行的完整实现），但对危险模式的定义是硬编码的，需要持续维护正则列表。

### 阻塞策略：都是同步阻塞，但原因不同

两个系统最终都选择了**同步阻塞 agent 执行**，但背后的理由不同：

- **OpenClaw**：阻塞是因为审批决策者是**人类 owner**，agent 不能在没有获得授权的情况下自行推进。这是一个"请求许可"模型。
- **Hermes**：阻塞是因为在异步消息平台（如 Slack/Discord）上，不阻塞会导致 agent 在等待审批期间继续执行后续工具调用，可能造成不一致状态。Gateway 的 FIFO 队列 + Event 阻塞机制精确复现了 CLI 中 `input()` 的同步语义。

### 超时策略：保守等待 vs 快速拒绝

- **OpenClaw 的 30 分钟超时**：设计上兼容**异步审批场景**（如推送通知到移动端，owner 可能不在电脑前）。超时后走 fallback 策略而非直接拒绝，给配置层面留了弹性。
- **Hermes 的 60 秒 / 300 秒超时**：设计上假设用户在**实时交互场景**中（CLI 前或消息平台在线）。超时直接拒绝，偏向安全侧——宁可误拒也不冒险放行。

### 持久化策略：无状态 vs 有状态

- **OpenClaw**：每次 exec 都是独立的审批决策。`allow-always` 的语义由 policy 配置（`exec-approvals.json`）静态决定，不依赖运行时状态。这减少了状态管理复杂度，但增加了重复审批的摩擦。
- **Hermes**：三级持久化（once / session / always）让用户可以渐进式建立信任。`always` 写入 `config.yaml` 是持久化到文件的，重启后依然生效。代价是需要维护 `command_allowlist` 的清理机制。

## 共同模式

尽管哲学不同，两个系统在几个关键点上达成一致：

1. **审批是执行前门控，不是事后审计。** 两个系统都在命令实际执行之前完成审批决策，被拒绝的命令从不进入执行阶段。

2. **人类是最终决策者。** Hermes 的 Smart 层虽然引入了 LLM 自动审批，但它的设计是"自动处理明显的两端、模糊地带交给人类"。LLM 不能做最终决策——它只能 APPROVE（放行明显安全的）、DENY（拒绝明显危险的）、ESCALATE（升级到人类）。

3. **审批失败偏向安全侧。** 两个系统在超时、网络异常、注册失败等情况下都默认拒绝执行，不存在"审批系统挂了就放行"的兜底逻辑。

4. **容器环境天然豁免。** Hermes 显式豁免容器环境（docker/singularity/modal/daytona）。OpenClaw 没有硬编码豁免，但可以通过 policy 配置 `ask=off` 来实现等效效果。两者都认可容器提供的隔离性降低了 exec 审批的必要性。

5. **审批请求携带完整上下文。** 两个系统在审批请求中都传递了命令文本、工作目录、环境变量 keys、会话标识、来源通道等元数据，确保决策者（人或 LLM）有足够信息做知情决策。

## 待探索方向

1. **审批疲劳的量化与优化**：Smart 层能减少多少人工审批次数？是否可以引入"信任度评分"让经常被 approve 的模式自动降级？
2. **跨会话审批记忆的共享**：如果有多个 Hermes 实例，`command_allowlist` 如何同步？OpenClaw 的 policy 文件在多节点部署中如何保持一致？
3. **审批的审计与回放**：审批决策是否需要持久化日志？如果需要追溯"为什么当时批准了这个命令"，两个系统目前都没有内置审计日志。
4. **辅助 LLM 审批的准确性评估**：Smart 层的误批率（把危险命令评为 APPROVE）和误拒率（把安全命令评为 DENY）在真实场景中表现如何？是否需要定期校准 prompt？
