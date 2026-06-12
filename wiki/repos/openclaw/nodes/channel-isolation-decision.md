---
node_type: DesignDecision
scope: system
sources:
  - extensions/slack/package.json:1-15
---

# Channel SDK 故障域隔离

每个 channel extension 独立声明自己的 SDK 依赖（Slack 用 @slack/bolt、Telegram 用 grammy 等），不在 root package 聚合，通过 `workspace:*` 引用内部 plugin-sdk。核心运行时不因任何单个 channel SDK 变动受影响；代价是 monorepo 管理复杂度上升。
^[extensions/slack/package.json:1-15]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[openclaw/nodes/channel-plugin]]
<!-- /generated -->
