# Concept Index

归一化锚点。每个 Concept 入表须通过准入三问（见 schema/graph-schema.md）。
ingest 时 LLM 只标 `concept_candidate`，人工确认后才在此登记。

| Concept | 别名/曾用名 | 定义 | 实例数 |
|---------|------------|------|--------|
| 插件系统 | Plugin System, 扩展注册机制 | 通过注册 API 或 manifest 将核心运行时与可扩展能力解耦：核心不感知具体实现，扩展包按需加载，故障域互不影响。关键判别差异：接口契约式（ChannelPlugin 多 Adapter 组合）vs AST 扫描式（registry.register 自动发现）vs 声明式 manifest。 | 2 |
| Context 压缩 | Context Compression, compact | 上下文接近 LLM context window 上限时，用辅助 LLM 将历史 turns 有损压缩为摘要，以换取继续对话的容量。核心权衡：上下文容量 vs 历史信息保真度；不同实现差异体现在压缩阈值、摘要优先级（可恢复性优先 vs 压缩率优先）、失败冷却策略。 | 2 |
| Prompt Caching | Prompt Cache, 前缀缓存 | 将 LLM 请求中的稳定前缀（system prompt、早轮历史等）在 provider 侧打上缓存标记，后续 turn 命中时跳过该部分的 token 计算，大幅降低多轮对话输入成本（通常 ~75%）。关键差异：缓存边界粒度（单一标记 vs 多 breakpoint）、TTL 策略、与 context compression 的配合时机。 | 2 |
| 并行工具执行 | Parallel Tool Execution | LLM agent 在单轮 tool-calling 中同时执行多个无依赖关系的工具调用，以降低总延迟。关键设计差异：哪些工具归为安全并行（只读、无共享状态）vs 必须串行（交互式、有副作用）；并行上限（worker 数）的设定策略。 | 2 |
| 契约测试 | Contract Testing | 通过共享 test suite 定义验证接口实现方是否符合约定协议，新实现注册后自动被覆盖，避免接口漂移。与普通单元测试的关键差异：一次定义 suite，多实现复用，而非每实现重复手写。 | 1 |
| 性能预算 | Performance Budget | 将性能指标（启动时间、包体积等）纳入 CI 检查，超出预置基线即构建失败，防止性能退化静默累积。与普通性能测试的差异：有明确的量化基线文件（fixture），作为 CI gate 而非事后报告。 | 1 |
| 行为驱动测试 | Behavior-Driven Testing | 测试针对公共 API 表面和可观察行为，而非内部实现细节。避免对私有方法或 mock 内部调用做断言，使测试在重构时保持稳定。与其对立的风格是"实现驱动测试"（测试知道内部结构）。 | 2 |
| 可观测性集成 | OpenTelemetry, Observability | 将 Traces、Metrics、Logs 三路信号统一采集和导出，接入外部监控 backend。核心权衡：集成粒度越细（采样率、导出频率），运行时开销越高；敏感内容须在导出前脱敏。关键差异：深度集成（三路并行 + 自定义 sampler）vs 浅层集成（仅 logs）。 | 1 |

## 观察名单（暂不作为归一化锚点）

以下概念未通过判别测试——任何非玩具仓库都"有"，暂无有差异的跨仓库结论。
第 3-5 个仓库出现有判别力的变体差异时再准入：

- 分层架构
- 优雅降级
- 故障隔离
- 并行 CI
