# Concept 验证报告：Tool Execution Safety Approval

**验证日期**：2026-06-17
**待验证文件**：`concept/tool-execution-safety-approval.md`
**源码来源**：
- openclaw: `github.com/openclaw/openclaw` @ `2d91aaa`
- hermes-agent: `github.com/NousResearch/hermes-agent` @ `5e01a5d`

---

## 验证范围

按照用户要求，重点验证以下区域：

- openclaw：审批超时、fallback 行为、双路径差异、同步阻塞语义
- hermes：三层架构、Smart LLM 配置、o/s/a/d 选项、timeout 值

---

## OpenClaw 验证

### 1. 30 分钟审批超时（1,800,000ms）

**结论：准确。**

源码证据 (`src/infra/exec-approvals.ts:280`)：
```typescript
export const DEFAULT_EXEC_APPROVAL_TIMEOUT_MS = 1_800_000;
```
Concept 行 16 和行 50 声称 30 分钟/1,800,000ms，完全匹配。

---

### 2. 超时后的 fallback 行为

**结论：存在关键错误。**

Concept 行 52-53 声称：
> 超时时 `waitForExecApprovalDecision` 返回 `null`，触发 `askFallback`——默认 fallback 为 `full` 安全级别，即审批不可用时拒绝执行。

**两个层面的错误：**

#### (a) 默认值错误

实际默认值 (`src/infra/exec-approvals.ts:284`)：
```typescript
export const DEFAULT_EXEC_APPROVAL_ASK_FALLBACK: ExecSecurity = "deny";
```

默认值是 `"deny"`，不是 `"full"`。

#### (b) 语义映射与自身矛盾

`resolveBaseExecApprovalDecision`（`bash-tools.exec-host-shared.ts`）的超时分支：
```typescript
if (!params.decision) {  // timeout scenario
    if (params.askFallback === "full") {
        return { approvedByAsk: true, deniedReason: null, timedOut: true };
        //                           ^^^^ ALLOWS execution despite timeout
    }
    if (params.askFallback === "deny") {
        return { approvedByAsk: false, deniedReason: "approval-timeout", timedOut: true };
        //                            ^^^^^ DENIES execution
    }
}
```

- `"full"` 意味着**超时后仍然放行执行**（`approvedByAsk: true`）
- `"deny"` 意味着**超时后拒绝执行**（`approvedByAsk: false`）
- 默认值是 `"deny"`，即默认行为确实是拒绝执行
- 但 Concept 说默认值是 `"full"`，并错误地声称 `"full"` 的含义是"拒绝执行"——这在语义上与代码逻辑完全相反

**修正建议**：Concept 行 52-53 应改为：
> ...触发 `askFallback`——默认 fallback 为 `deny`，即审批超时时拒绝执行。

---

### 3. 双路径（host/gateway）审批差异

**结论：基本准确。**

源码确认了 gateway 和 node 两条路径的关键差异：

| 特征 | Gateway 路径 | Node 路径 |
|------|-------------|----------|
| 入口函数 | `processGatewayAllowlist` | `executeNodeHostCommand` |
| 审批注册 | `registerExecApprovalRequestForHostOrThrow` | 同 |
| Host 字段 | `host: "gateway"` | `host: "node"` |
| 额外字段 | 无 | `systemRunPlan`（包含 argv、cwd、完整执行计划）、`nodeId` |
| 服务端校验 | 标准 | 必须有 `commandArgv` 和 `systemRunPlan`（更严格） |

Concept 行 46-48 的描述准确。Node 路径确实需要更丰富的 payload。

---

### 4. 同步阻塞语义

**结论：存在不准确之处。**

Concept 行 44 声称：
> `requestExecApprovalDecision` 是一个完整的 async 函数，但它内部会阻塞等待人类决策。Agent 在执行审批中的命令时完全停摆

**实际情况更复杂：**

Gateway 路径 (`processGatewayAllowlist`) 中的阻塞行为取决于 channel 类型：

```typescript
function shouldAwaitGatewayApprovalInline(params): boolean {
    if (params.approvalFollowupMode !== undefined) return false;
    return normalizeMessageChannel(params.turnSourceChannel) === INTERNAL_MESSAGE_CHANNEL;
}
```

- **内部消息 channel**（Web Chat UI）：**同步阻塞**，agent 线程挂起等待审批决策。Concept 的"完全停摆"描述对此类 channel 正确。
- **外部 channel**（Telegram、WhatsApp、Discord 等）：**异步非阻塞**。函数返回 `pendingResult` 立即返还给 agent loop，实际的命令执行和审批等待在 `void (async () => {...})()` 后台 Promise 中进行。

同理，Node 路径 (`executeNodeHostCommand`) 也使用 fire-and-forget 模式处理需要人工审批的情况。

**因此"Agent 在执行审批中的命令时完全停摆"是一个过度概括**。外部 IM channel 上的 agent 会收到一个 `approval-pending` 状态的结果并继续处理后续工具调用，而实际的命令在后台等待审批。

**修正建议**：补充说明阻塞行为受 channel 类型影响。内部 channel 同步阻塞；外部 channel 异步返回 pending 状态，agent 不阻塞。

---

### 5. 注册超时（DEFAULT_APPROVAL_REQUEST_TIMEOUT_MS）

**结论：准确。**

源码证据 (`bash-tools.exec-runtime.ts`)：
```typescript
export const DEFAULT_APPROVAL_TIMEOUT_MS = DEFAULT_EXEC_APPROVAL_TIMEOUT_MS;
export const DEFAULT_APPROVAL_REQUEST_TIMEOUT_MS = DEFAULT_APPROVAL_TIMEOUT_MS + 10_000;
```

Concept 行 52 声称"注册超时比审批超时多 10 秒"，精确匹配。

---

## Hermes Agent 验证

### 1. 三层审批架构

**结论：基本准确，但遗漏了一个重要层级。**

Concept 描述的三层（YOLO/容器/mode=off -> Smart -> Manual）在 `check_all_command_guards` 函数中确实对应了：
- Layer 0：容器豁免 + YOLO + approvals.mode=off（行 1343-1370）
- Layer 1：Smart 辅助 LLM（行 1442-1462）
- Layer 2：Manual 交互式（行 1476-1551 CLI 路径，1573+ CLI 交互）

**但漏掉了两个无条件前置检查：**

#### (a) Hardline Blocklist

`check_all_command_guards:1346-1353` 在容器检查和 YOLO 检查**之间**：
```python
# Hardline floor: unconditional block for catastrophic commands
# (rm -rf /, mkfs, dd to raw device, shutdown/reboot, fork bomb,
# kill -1). Applies BEFORE yolo / mode=off / cron approve-mode so
# no session-level setting can bypass it.
is_hardline, hardline_desc = detect_hardline_command(command)
if is_hardline:
    return _hardline_block_result(hardline_desc)
```

12 个 HARDLINE_PATTERNS 覆盖：递归删除系统根/系统目录/家目录、mkfs 格式化、dd 写裸块设备、fork bomb、kill -1、shutdown/reboot/halt/poweroff、init 0/6、systemctl poweroff/reboot、telinit 0/6。

**这些命令无法被任何设置绕过**（包括 YOLO、approvals.mode=off、cron approve 模式）。这是 hermes 架构中最重要的安全边界，不应缺失。

#### (b) Sudo stdin Guard

`check_all_command_guards:1355-1364`：
```python
# Sudo stdin guard: unconditional block for sudo -S password piping
is_sudo_guess, sudo_guess_desc = _check_sudo_stdin_guard(command)
if is_sudo_guess:
    return _sudo_stdin_block_result(sudo_guess_desc)
```

同样在 YOLO 检查之前，阻止 agent 通过 pipe 密码到 `sudo -S` 的暴力破解尝试。

**修正建议**：Concept 的 Layer 0 描述应改为 Layer 0a（Hardline Blocklist + Sudo Guard，无条件拒绝）+ Layer 0b（容器豁免 + YOLO + mode=off，无条件放行）。这两个前置检查的先后顺序有重要的语义差异。

---

### 2. Smart 辅助 LLM 配置

**结论：准确。**

源码证据 (`tools/approval.py:1076-1081`)：
```python
response = call_llm(
    task="approval",
    messages=[{"role": "user", "content": prompt}],
    temperature=0,
    max_tokens=16,
)
```

Concept 行 89-93 声称 `temperature=0, max_tokens=16`，完全匹配。

模型通过 `call_llm(task="approval")` 选择，支持任意 OpenAI-compatible provider，未配置时 catch 异常并 escalate（行 1092-1094），Concept 行 87-88 的描述准确。

---

### 3. o/s/a/d 选项含义

**结论：准确。**

源码证据 (`tools/approval.py:970-981`)：
```python
if choice in {'o', 'once'}:       return "once"
elif choice in {'s', 'session'}:  return "session"
elif choice in {'a', 'always'}:
    if not allow_permanent:       return "session"  # downgrade
    return "always"
```

- `[o]nce`：仅本次有效（不持久化，不加入 session 白名单）
- `[s]ession`：写入内存 session 级白名单（`approve_session`）
- `[a]lways`：写入 config.yaml 永久持久化（`approve_permanent` + `save_permanent_allowlist`）
- `[d]eny`：拒绝，返回 BLOCKED 消息

Concept 行 99-101 的描述完全正确。关于 tirith 安全问题时 `[a]lways` 被隐藏的描述（`allow_permanent=not has_tirith`，行 1493）也准确。

---

### 4. Timeout 时间和行为

**结论：准确。**

CLI timeout (`tools/approval.py:1029-1034`)：
```python
def _get_approval_timeout() -> int:
    try:
        return int(_get_approval_config().get("timeout", 60))
    except (ValueError, TypeError):
        return 60
```
默认 60 秒，可通过 `approvals.timeout` 配置，Concept 行 16 准确。

Gateway timeout (`tools/approval.py:1288-1292`)：
```python
timeout = _get_approval_config().get("gateway_timeout", 300)
try:
    timeout = int(timeout)
except (ValueError, TypeError):
    timeout = 300
```
默认 300 秒（5 分钟），可通过 `approvals.gateway_timeout` 配置，Concept 行 16 准确。

超时行为：超时视为 deny，返回 BLOCKED 消息（`check_all_command_guards:1508-1537`），Concept 行 17 准确。

---

## 其他发现

### hermes DANGEROUS_PATTERNS 数量

Concept 行 117 声称"25+ 正则模式"，实际 DANGEROUS_PATTERNS 列表包含约 47 个正则（包括独立模式、变体、sensitive write targets）。加上 12 个 HARDLINE_PATTERNS，总计约 59 个安全检测模式。Concept 声称的计数偏低但保留了"+"号，不构成事实错误。

### openclaw 「无内置持久化」描述

Concept 行 19 声称 openclaw "无内置持久化。每次 exec 独立审批"，但 openclaw 实际上有 `allow-always` 机制（通过 `persistAllowAlwaysPatterns` 将 pattern 写入 `exec-approvals.json` 文件）和 `addDurableCommandApproval`（内存中的 durable approval）。这类似于 hermes 的 session 级 + 文件持久化。Concept 的描述不准确——openclaw 确实有持久化，只是机制不同于 hermes。

---

## 验证结论

| 区域 | 判定 | 严重程度 |
|------|------|---------|
| openclaw 30min 超时 | 准确 | - |
| **openclaw askFallback 默认值** | **错误："deny"非"full"，语义映射也倒置** | **高** |
| openclaw 双路径差异 | 基本准确 | - |
| openclaw 同步阻塞语义 | 不准确（仅限内部channel） | 中 |
| openclaw 注册超时 +10s | 准确 | - |
| hermes 三层架构 | 基本准确但遗漏 Hardline + Sudo Guard | 中 |
| hermes Smart LLM 配置 | 准确 | - |
| hermes o/s/a/d 选项 | 准确 | - |
| hermes timeout 值 | 准确 | - |
| openclaw 持久化描述 | 不准确（有持久化机制） | 低 |

### 必须修正

1. **第 52-53 行**：`askFallback` 默认值从 `"full"` 改为 `"deny"`，修正对应的行为描述
2. **第 44 行**：同步阻塞描述增加 channel 类型说明
3. **第 19 行**：openclaw 持久化描述修正为"文件持久化（allow-always patterns 写入 exec-approvals.json）"

### 建议补充

4. **hermes Layer 0**：增加 Hardline Blocklist 和 Sudo stdin Guard 作为架构描述的一部分
