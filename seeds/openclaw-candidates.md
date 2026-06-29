# openclaw Candidates

> Generated: 2026-06-26 (incremental re-ingest)
> Source: seeds/openclaw-problem-map.md

## Candidate List

### A 类（追加到已有页面）：1 条

| # | 问题空间 | 目标 Concept | 理由 |
|---|---------|-------------|------|
| 1 | 子 Agent 生命周期：如何管理嵌套 agent 的异步孵化、跟踪、完成和崩溃恢复？ | [[concepts/subagent-orchestration]] | 问题空间与 subagent-orchestration 的核心问题完全一致。openclaw 已在此 Concept 中有完整条目，本次无新增内容。 |

### B 类（新建 Concept 页）：0 条

*(无新建 Concept)*

### C 类（待观察）：0 条

*(无待观察条目)*

### D 类（演化信号）：0 条

*(无演化信号)*

---

## 能力域覆盖表

| 能力域 | nanobot | hermes-agent | openclaw |
|--------|---------|-------------|----------|
| Agent 主循环编排 | -- | -- | -- |
| 上下文压缩 | -- | -- | -- |
| 渠道抽象 | -- | -- | -- |
| 会话生命周期 | -- | -- | -- |
| 系统提示词组装 | -- | -- | -- |
| 记忆管理 | -- | -- | -- |
| 工具管理 | -- | -- | -- |
| Provider 抽象 | -- | -- | -- |
| 子 Agent 编排 | ✅ | ✅ | ✅ |
| 安全架构 | -- | -- | -- |
| 执行审批 | -- | -- | -- |
| 技能扩展 | -- | -- | -- |
| 自主调度 | -- | -- | -- |
| 配置管理 | -- | -- | -- |
| 执行隔离 | -- | -- | -- |

> Note: "--" indicates coverage unchanged from previous ingest and not reassessed in this incremental run.

---

## Incremental Re-ingest Summary

- **Changed files**: 1 (`src/agents/subagent-registry.ts`)
- **Affected entities**: 1 (`subagent-system`)
- **Nature of change**: Cosmetic only — trailing comment added, no functional change
- **Concept impact**: Zero — all existing Concept entries remain accurate
