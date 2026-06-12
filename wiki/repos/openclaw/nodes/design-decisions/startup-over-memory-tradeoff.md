---
node_type: DesignDecision
scope: system
sources:
  - src/shared/lazy-runtime.ts:1-44
  - src/entry.ts:52-58
extracted_from:
  - performance-tradeoffs
  - dependency-strategy
---

# 启动速度优先于内存占用

冷启动速度被当作一等公民优化：compile cache、lazy runtime module（Promise 缓存包装动态 import）、channel entry 按需加载、respawn 策略。代价是内存中持有多个 Promise cache、冷启动多一次 spawn。该决策约束所有运行时模块的加载方式——新增重型模块必须走 `createLazyRuntimeModule`。
^[src/shared/lazy-runtime.ts:1-44]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[openclaw/nodes/components/process-supervisor]]
<!-- /generated -->
