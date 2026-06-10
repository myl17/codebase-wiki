---
type: entity
category: 技术栈
---

# TypeScript monorepo

将多个相关包放在同一代码仓库中统一管理，通过 workspace 协议（如 `workspace:*`）引用内部包，共享 TypeScript 类型和构建工具链。

## 在各 repo 中的体现

- [[openclaw/dimensions/openclaw-architecture]] — 九大子系统集成于单一 TypeScript monorepo；`extensions/` 下每个 channel/provider 是独立 npm 包，通过 `workspace:*` 引用 plugin-sdk
