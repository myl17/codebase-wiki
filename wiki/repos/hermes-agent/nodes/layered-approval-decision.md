---
node_type: DesignDecision
scope: system
sources:
  - tools/approval.py:586-922
extracted_from:
  - architecture
---

# 三层审批而非单级开关

命令审批分三层：Layer 0 快速路径（YOLO/容器/off 全放行）、Layer 1 Smart（辅助 LLM 风险评估自动批/拒/升级）、Layer 2 Manual（tirith + 25+ DANGEROUS_PATTERNS 正则 → 用户交互审批）。选择渐进式而非二元开关：用复杂度换"安全性与流畅性可按场景调节"。审批级别 once/session/always 三级持久化。
^[tools/approval.py:586-922]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[hermes-agent/nodes/approval-system]]
- [[hermes-agent/nodes/skills-guard]]
<!-- /generated -->
