---
node_type: DesignDecision
scope: system
sources:
  - package.json:1-50
extracted_from:
  - dependency-strategy
---

# 深度绑定 @mariozechner 私有包族

选择完全依赖 `@mariozechner/*` 四件套（pi-ai / pi-agent-core / pi-coding-agent / pi-tui，442 处 import）而非自研 agent 引擎：快速复用成熟引擎，代价是 agent 层几乎无法在不重写的情况下切换，且受上游版本节奏约束。四包精确锁定同一版本，与主版本号同步发布。
^[package.json:1-50]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[openclaw/nodes/extension-points/agent-harness]]
<!-- /generated -->
