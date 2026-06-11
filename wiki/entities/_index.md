# Concept Index

归一化锚点。每个 Concept 入表须通过准入三问（见 schema/graph-schema.md）。
ingest 时 LLM 只标 `concept_candidate`，人工确认后才在此登记。

| Concept | 别名/曾用名 | 一句话定义 | 实例数 |
|---------|------------|-----------|--------|
| 插件系统 | Plugin System, 扩展注册机制 | 通过注册 API 或 manifest 将核心与扩展解耦，核心不感知具体实现 | 2 |
| Context 压缩 | Context Compression, compact | 上下文超限时用辅助 LLM 有损压缩历史 turns，换取继续对话的容量 | 2 |
| Prompt Caching | Prompt Cache, 前缀缓存 | 将 LLM 请求的稳定前缀在 provider 侧缓存，命中时跳过 token 计算 | 2 |
| 并行工具执行 | Parallel Tool Execution | LLM agent 在单轮 tool-calling 中同时执行多个无依赖工具以降低延迟 | 2 |
| 契约测试 | Contract Testing | 通过共享 test suite 验证接口实现方符合约定协议，新实现自动被覆盖 | 1 |
| 性能预算 | Performance Budget | 将性能指标纳入 CI，超出基线即 fail，防止退化静默积累 | 1 |
| 行为驱动测试 | Behavior-Driven Testing | 测试公共 API 和可观察行为而非内部实现，使测试在重构时保持稳定 | 2 |
| 可观测性集成 | OpenTelemetry, Observability | 三路信号（Traces/Metrics/Logs）统一采集导出，接入外部监控 backend | 1 |

## 观察名单（watchlist，暂不作为归一化锚点）

以下 entity 页保留但未通过判别测试（任何仓库都"有"，暂无有差异的跨仓库结论）。
第 3-5 个仓库出现有判别力的变体差异时再准入：

- 分层架构
- 优雅降级
- 故障隔离
- 并行 CI
