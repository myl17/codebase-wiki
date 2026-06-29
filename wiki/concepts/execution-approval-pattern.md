---
type: concept
concept: execution-approval-pattern
problem: 如何在 Agent 执行高风险操作（shell 命令、文件写入）前插入人类审批，平衡安全与自主性
concerns: [审批同步/异步模式, 记忆策略的安全影响, 多平台审批体验]
repos: [nanobot, hermes-agent, openclaw, codex-main]
generated: 2026-06-25
---

# Execution Approval Pattern

## 核心问题

Agent 执行高风险操作时，完全自主执行有安全隐患，每次都询问用户则失去自动化价值。审批机制的本质是在安全与自主之间建立一套可调节的信任刻度——不是二元的"信任/不信任"，而是沿着"从不信任 → 一次信任 → 短期信任 → 永久信任 → 完全信任"的渐进光谱。

这个光谱上每一级的选择都牵动三个维度。同步 vs 异步决定了 Agent 被阻塞等待还是继续执行其他任务——同步简单但阻塞，异步不阻塞但需要状态机管理。记忆策略决定了审批结果要不要跨会话复用——记住太久有安全风险（环境可能变化），记住太短增加用户摩擦。审批体验决定了人在什么设备上、通过什么渠道做决策——桌面弹窗、移动推送、CLI 交互各有适用场景。

最微妙的设计张力在永久记忆与安全之间。如果一个命令（如 `git push`）今天被批准为永久信任，明天 Agent 的上下文发生变化（如切换到了不同的 repo），同一个命令还会安全吗？这要求审批系统要么记录批准时的上下文快照用于比较，要么接受永久审批的固有风险。

## 关切

- **审批同步/异步模式**：同步阻塞 Agent 等待用户决策——实现简单但中断执行流；异步通过 Promise/回调让 Agent 继续工作——实现复杂但体验流畅。异步模式下超时处理策略（自动拒绝 vs 自动放行）直接影响安全。
- **记忆策略的安全影响**：session 级记忆（本次会话不再问）安全但重复摩擦；permanent 记忆（永远不问了）方便但环境变化时可能不安全。是否需要上下文快照来验证永久审批的前提条件未变化？
- **多平台审批体验**：用户在桌面端触发审批后可能切换到移动端。审批系统是否支持推送通知？能否在 CLI、Web、iOS 等多个平台上提供一致的审批体验？

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/security-system]]
**解法**：无专门审批机制——安全策略基于过滤而非审批，命令执行前无人类确认环节。
**实现**：安全防护仅限 SSRF 网络过滤，不介入命令执行流程的审批。适合完全自主运行的个人 Agent 场景。 ^[nanobot/security/network.py]
**权衡**：零摩擦但零人类监督。在信任 Agent 判断能力的场景下可行，但不适合高风险操作或共享环境。

### hermes-agent
来源：[[repos/hermes-agent/entities/security-sandbox]]
**解法**：三层审批作用域（session/permanent/YOLO）+ DM 配对码授权，同一命令在 session 内首次审批后自动放行。
**实现**：`approve_session()` 在当前会话内记住审批决定，后续相同命令自动通过；`approve_permanent()` 持久化到 `command_allowlist` 文件；`enable_session_yolo()` 完全绕过所有审批；DM 配对码通过加密随机码（`secrets.choice()`，8 字符，1h 过期）实现远程授权，含速率限制和锁定保护。 ^[tools/approval.py:299-359, gateway/pairing.py:34-75, 150-193]
**权衡**：记忆策略最丰富（会话/永久/YOLO 三档），配对码提供了远程审批渠道。但永久审批无上下文快照，依赖用户自行判断命令是否环境无关。

### openclaw
来源：[[repos/openclaw/entities/approval-system]]
**解法**：异步 Promise 模式——创建审批记录立即返回 requestId，注册后返回 Promise 等待 resolve，超时自动拒绝。
**实现**：`create()` 同步创建记录返回 ID，`register()` 返回 Promise<decision> 异步等待；每个审批关联 setTimeout，到期自动拒绝；已解决的记录保留 15 秒宽限期处理滞后调用；反重放元数据（requestedByConnId/DeviceId/ClientId）防止跨客户端重放；iOS 推送集成支持移动端审批。 ^[src/gateway/exec-approval-manager.ts:13-25, 43-60, 31, 9, 19-21]
**权衡**：异步模式体验最流畅（Agent 不被阻塞），iOS 推送实现移动审批。但记忆策略最简单——每次审批独立，无 session/permanent 复用机制，可能在高频操作中产生重复摩擦。

### codex-main

来源：[[repos/codex-main/entities/shell-escalation]]、[[repos/codex-main/entities/execpolicy]]
**解法**：EscalateServer 守护进程审批 + PrefixRule amend 运行时规则追加。
**实现**：
- `EscalateServer` 作为独立守护进程通过 Unix socket 接收特权命令执行请求，`EscalationDecision` 返回审批决策 ^[codex-rs/shell-escalation/src/unix.rs:17-23]
- `EscalationPolicy` trait 允许自定义权限检查逻辑，`EscalationSession` 封装单次提升的完整生命周期 ^[codex-rs/shell-escalation/src/unix.rs:21-22]
- execpolicy 的 `amend` 模块支持运行时追加 allow-prefix 规则——用户审批通过后规则被持久化到策略文件 ^[codex-rs/execpolicy/src/amend.rs:10-12]
- 审批通过规则在后续相同命令中自动匹配，实现隐式的 session 级记忆
**权衡**：EscalateServer 的守护进程隔离提供了最强的进程级审批安全保障。PrefixRule amend 提供了自然的审批记忆——批准的规则持久化为策略。但审批只针对 shell 命令（无文件操作审批），且审批流程同步阻塞 Agent。

## 对比
| 框架 | 审批同步/异步模式 | 记忆策略的安全影响 | 多平台审批体验 |
|------|------|------|------|
| nanobot | 无审批机制 | 不适用 | 不适用 |
| hermes-agent | 同步阻塞模式（首次审批停止执行） | 三层记忆（session/permanent/YOLO），永久审批无上下文快照 | DM 配对码 + 26+ 平台交付 |
| openclaw | 异步 Promise 模式（创建-注册分离，超时自动拒绝） | 每次独立审批，无记忆复用 | iOS 推送 + WebSocket 网关 |
| codex-main | 同步阻塞模式（EscalateServer 守护进程审批） | PrefixRule amend 运行时持久化——批准后自动记忆 | Unix socket 本地通信 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 codex-main（EscalateServer 守护进程审批 + PrefixRule amend 持久化记忆）
