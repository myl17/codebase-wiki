---
type: entity
category: 技术栈
---

# Vitest

基于 Vite 的 JavaScript/TypeScript 测试框架，支持 ESM、并行执行、内置 vi.mock，API 与 Jest 兼容，配置更轻量。

## 在各 repo 中的体现

- [[openclaw/dimensions/openclaw-testing-philosophy]] — 全栈使用 Vitest（`^4.1.4`），90+ 个子配置按子系统分片并行运行，worker 数量根据系统负载动态计算
