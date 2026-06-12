# Concept Index

归一化锚点。每个 Concept 入表须通过准入三问（见 schema/graph-schema.md）。
ingest 时 LLM 只标 `concept_candidate`，人工确认后才在此登记。

| Concept | 别名/曾用名 | 定义 | 实例数 |
|---------|------------|------|--------|
| 插件系统 | Plugin System, 扩展注册机制 | 通过注册 API 或 manifest 将核心运行时与可扩展能力解耦：核心不感知具体实现，扩展包按需加载，故障域互不影响。关键判别差异：接口契约式（ChannelPlugin 多 Adapter 组合）vs AST 扫描式（registry.register 自动发现）。 | 2 |
| Context 压缩 | Context Compression, compact | 上下文接近 LLM context window 上限时，用辅助 LLM 将历史 turns 有损压缩为摘要，换取容量。核心权衡：容量 vs 保真度；差异体现在压缩阈值、摘要优先级、失败冷却策略。 | 2 |
| 人机审批协议 | Approval Protocol, Exec Guard | 对高风险操作（exec 类工具）在执行前实施审批拦截。关键差异：单一阻塞式（等待 owner 决策，host/gateway 双路径）vs 三层渐进式（YOLO/Smart/Manual，辅助 LLM 自动分级）。 | 2 |
| 可替换记忆后端 | Pluggable Memory Backend | 记忆存储后端以接口抽象，支持多种实现（SQLite/LanceDB/外部引擎），通过注册机制在工作时替换。关键差异：exclusive 槽位（替换式，全局唯一）vs additive provider（加性，内置存储不可移除）。 | 2 |

## 叙事层概念（有维度叙事但尚无对应节点）

以下概念通过了准入三问，但当前仓库的节点提取中未产出 directly embodies 它们的节点——它们是跨维度的观察/主题：

| Concept | 关联仓库 | 说明 |
|---------|---------|------|
| Prompt Caching | openclaw, hermes-agent | 两仓库均使用，属性能优化主题，缺少单节点锚定 |
| 并行工具执行 | hermes-agent | performance-tradeoffs 维度覆盖 |
| 契约测试 | openclaw | testing-philosophy 维度覆盖，contract test suite |
| 性能预算 | openclaw | testing-philosophy 维度覆盖，cli-startup-bench |
| 行为驱动测试 | openclaw, hermes-agent | testing-philosophy 维度覆盖 |
| 可观测性集成 | openclaw | architecture 维度覆盖，OTel extension |

## 观察名单（暂不作为归一化锚点）

以下概念未通过判别测试——任何非玩具仓库都"有"，暂无有差异的跨仓库结论：

- 分层架构
- 优雅降级
- 故障隔离
- 并行 CI

## 候选积压（concept_candidate，待归一化 pass）

以下候选因实例数不足（<2 repos）未通过判别测试，积压至第 3-5 个仓库后重新评估：

- 任务编排（openclaw:task-flow）
- 无消息主动触发（openclaw:cron-scheduler）
- 声明式行为定制（openclaw:skills-extension）
