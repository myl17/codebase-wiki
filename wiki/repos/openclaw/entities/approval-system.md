---
type: entity
repo: openclaw
slug: approval-system
problem: "如何在 agent 执行高风险操作前插入人类审批流程，支持超时和决策记录？"
generated: 2026-06-25
source_files:
  - src/gateway/exec-approval-manager.ts
---

# Approval System

**代码位置**：`src/gateway/exec-approval-manager.ts`
**这个模块解决什么问题**：
- 实现层：创建审批记录 → 注册并等待决策 → 超时自动拒绝 → 15 秒宽限期清理
- 问题层：如何在 agent 执行高风险操作前插入人类审批流程，支持超时和决策记录？
**对外暴露什么**：
- `ExecApprovalManager<TPayload>` 类 — 审批管理器 ^[src/gateway/exec-approval-manager.ts:40]
- `ExecApprovalRecord<TPayload>` 类型 — 审批记录（id, request, createdAtMs, expiresAtMs, decision） ^[src/gateway/exec-approval-manager.ts:13-25]
- `create(request, timeoutMs, id?)` — 创建审批记录 ^[src/gateway/exec-approval-manager.ts:43]
- `register(record)` — 注册并返回 Promise<decision> ^[src/gateway/exec-approval-manager.ts:60]
- `resolve(id, decision)` — 解决审批 ^[src/gateway/exec-approval-manager.ts]
- `ExecApprovalIdLookupResult` — ID 查找结果（exact/prefix/ambiguous/none） ^[src/gateway/exec-approval-manager.ts:35-38]
**它和谁交互**：
- 依赖 [[entities/gateway]]（作为网关组件运行，通过 WebSocket 传递审批请求和决策）
- 被 [[entities/agent-runtime]]（执行工具前检查审批要求）
- 被 [[entities/tool-system]]（exec 等高风险工具触发审批）
**为什么它是可分离的**：独立的审批状态机，通过 Promise + 超时实现异步决策

**关键机制**（源码可见）：
- 创建-注册分离：`create()` 同步创建记录（不注册），`register()` 异步等待决策 ^[src/gateway/exec-approval-manager.ts:43-60]
- 超时机制：每个审批记录关联一个 `setTimeout`，到期自动拒绝 ^[src/gateway/exec-approval-manager.ts:31]
- 幂等注册：相同的 pending ID 重复注册返回已存在的 Promise ^[src/gateway/exec-approval-manager.ts:60]
- 15 秒宽限期：已解决的记录保留 15 秒处理滞后 `awaitDecision` 调用 ^[src/gateway/exec-approval-manager.ts:9]
- 反重放元数据：`requestedByConnId/DeviceId/ClientId` 防止其他客户端重放审批 ID ^[src/gateway/exec-approval-manager.ts:19-21]
- iOS 推送：审批请求可推动到 iOS 设备 ^[src/gateway/exec-approval-ios-push.ts]

**源码证据**：
- 审批管理器：src/gateway/exec-approval-manager.ts
- iOS 推送集成：src/gateway/exec-approval-ios-push.ts
- 审批 CLI：src/cli/exec-approvals-cli.ts

**关联 Concept**：
- [[concepts/execution-approval-pattern]]
