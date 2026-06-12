---
node_type: ExtensionPoint
scope: component
concept: 人机审批协议
targets: [tool-policy]
motivated_by: [sync-gating-decision]
sources:
  - src/agents/bash-tools.exec-approval-request.ts:89-126
extracted_from:
  - architecture
  - extension-points
---

# ExecApprovalRequest

exec 类工具的异步阻塞审批扩展点。注册 `ExecApprovalRequest` 后等待 `waitForExecApprovalDecision`，支持 host/gateway 双路径。二开时在此注入自定义审批逻辑（UI 弹窗、Slack 通知等），不需改动 ToolPolicy pipeline。
^[src/agents/bash-tools.exec-approval-request.ts:89-126]

<!-- generated-wikilinks -->
## 关联

**所属概念：** [[人机审批协议]]

**设计原因**（motivates）：
- [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]] — 该决策催生了此节点

**作用于**（targets）：
- [[openclaw/nodes/components/openclaw-tool-policy]] — 改动会波及此组件

**同属「人机审批协议」的其他仓库实例：**
- [[hermes-agent/nodes/components/hermes-agent-approval-system]] — hermes-agent
<!-- /generated -->
