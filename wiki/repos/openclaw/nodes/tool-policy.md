---
node_type: Component
scope: system
motivated_by: [sync-gating-decision]
sources:
  - src/agents/tool-policy-pipeline.ts:56-90
  - src/agents/tool-policy.ts:19-55
extracted_from:
  - architecture
---

# ToolPolicy

5 层同步 pipeline（profile → provider → global → agent → group policy），对每个工具调用做 allowlist/denylist 叠加。`OwnerOnlyToolApprovalClass` 将工具分为 `control_plane` / `exec_capable` / `interactive` 三类，`applyOwnerOnlyToolPolicy` 按 sender 是否为 owner 动态过滤工具集。修改此组件须保持门控的同步语义（不能改为异步审计）。
^[src/agents/tool-policy-pipeline.ts:56-90]
^[src/agents/tool-policy.ts:19-55]

<!-- generated-wikilinks -->
## 关联

**设计原因**（motivates）：
- [[openclaw/nodes/sync-gating-decision]] — 该决策催生了此节点

**被以下扩展点作用于**（被 targets）：
- [[openclaw/nodes/exec-approval-request]]
- [[openclaw/nodes/hook-system]]
<!-- /generated -->
