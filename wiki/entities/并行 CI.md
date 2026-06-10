---
type: entity
category: 技术栈
---

# 并行 CI

在 CI 环境中并行执行测试，缩短反馈周期。常见实现：pytest-xdist、Vitest worker pool、矩阵 job 等。

## 在各 repo 中的体现

- [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] — `pytest -q -n auto`（pytest-xdist）并行执行全量单元测试，CI 10 分钟超时硬限
