---
node_type: DesignDecision
scope: system
sources:
  - src/agents/tool-policy-pipeline.ts:56-90
  - src/agents/bash-tools.exec-approval-request.ts:89-126
extracted_from:
  - architecture
---

# 5层同步门控

选择同步串行 pipeline 而非异步审计：所有工具调用在执行前必须经过 5 层过滤，exec 类工具额外阻塞等待 owner 审批。代价是工具调用延迟增加；换取安全边界可被代码静态验证，不依赖运行时日志。
^[src/agents/tool-policy-pipeline.ts:56-90]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[openclaw/nodes/exec-approval-request]]
- [[openclaw/nodes/tool-policy]]
<!-- /generated -->
