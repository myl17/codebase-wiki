---
concept: context-window-overflow-guard
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
  - nanobot
---

# Context Window Overflow Guard（上下文窗口-溢出防护触发策略）

## 标准化问题陈述

在 token 计数不精确的前提下，如何决定上下文窗口溢出防护的压缩触发策略——是固定阈值还是多源保守选择？

## 核心关切

1. **压缩阈值选择**：太早触发浪费 LLM 调用成本（无需压缩时压缩），太晚触发有上下文截断/API 调用失败风险
2. **Token 估算误差**：工具输出的实际 token 量与估算值之间不可避免地存在偏差，需留安全余量，但余量过大会导致过早触发不必要的压缩
3. **多源保守选择**：若有多个 token 预算数据源（model 配置、API 自报、agent 环境变量等），必须在其中选最保守值——宁可过早触发压缩也不能因预算虚高导致溢出失败
4. **经济代价**：每次压缩调用消耗一次 LLM 调用的 token 成本，过早压缩浪费这些调用

## 实例矩阵

| 仓库 | 策略 | 触发条件 | 优先级 |
|------|------|---------|--------|
| openclaw | 多源保守最小选择 | 硬下限 16,000 + 软警告 32,000，在 modelsConfig / model 自报 / agentContextTokens 之间按优先级选最保守值 | 安全性 > 兼容性 > 经济性 |
| hermes-agent | 固定 75% 阈值 | 当前上下文达到模型 context window 的 75% 时触发压缩 | 简单性 > 性能一致性 > 安全性 |
| nanobot | 四步透明上下文治理 | 不依赖阈值，每轮自动执行四步管道（Backfill → Microcompact → Budget → Snip） | 透明性 > 自动化 > LLM 策略自主性 |

## openclaw — 多源保守最小选择

### 上下文窗口守护（Context Window Guard）

`src/agents/context-window-guard.ts:4-81` 定义了双层守护防线：

```
CONTEXT_WINDOW_HARD_MIN_TOKENS = 16_000   // 硬下限：任何 model 不得低于此值
CONTEXT_WINDOW_WARN_BELOW_TOKENS = 32_000  // 软警告线：低于此值输出警告
```

守护逻辑在三类数据源之间按优先级取最保守（最小）值：
1. `modelsConfig` — 用户配置中显式声明的 token 预算
2. model 自报 — API 返回的 model metadata 中的 context window 大小
3. `agentContextTokens` — agent harness 层面设定的上下文 token 数

### 压缩触发参数

`src/agents/compaction.ts:19-40` 定义压缩触发参数：

| 参数 | 值 | 含义 |
|------|----|------|
| `BASE_CHUNK_RATIO` | 0.4 | 基础压缩块比例：被压缩内容占上下文窗口的 40% |
| `MIN_CHUNK_RATIO` | 0.15 | 最小压缩块比例：即使上下文接近满，至少保留 15% 未压缩内容 |
| `SAFETY_MARGIN` | 1.2 | 安全余量：20% 缓冲补偿 token 估算误差 |

### 压缩内容策略

压缩时优先保证**可恢复性**而非压缩率：
- 优先保留活跃任务状态、批处理进度、最后一次用户请求
- `tool_result.details` 在压缩前被 strip，防止冗长工具输出污染摘要

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 安全性（硬下限 16,000 防溢出 + 1.2x 安全余量补偿估算误差） | 经济性（过度保守可能导致不必要的过早压缩，浪费 LLM 调用成本） |
| 兼容性（不同 model 的 context window 不同，动态适配） | |

## hermes-agent — 固定 75% 阈值

### 上下文引擎抽象

`agent/context_engine.py:32-60` 定义了 `ContextEngine` 抽象基类（ABC），采用策略模式：
- 实现类放入 `plugins/context_engine/<name>/` 目录
- 内置两种实现：`Compressor`（默认）和 `LCM`

### 压缩触发条件

`agent/context_engine.py:59` 设置单一固定阈值：

```
触发条件：当前上下文的 token 估算值 >= model context_window * 0.75
```

压缩判断本身轻量：每次 turn 后检查一次估算 token 量，超过 75% 线即进入压缩流程。

### 压缩执行细节

`agent/context_compressor.py:1-60` 定义压缩器行为：

| 机制 | 细节 |
|------|------|
| 结构化摘要模板 | 压缩中间 turns 为非 LLM 可解析的结构化摘要，而非纯自然语言压缩 |
| Token-budget tail 保护 | 保留最后 N 条消息不压缩，保证最近上下文完整 |
| 工具输出修剪 | 先剪除冗长工具输出再送入摘要 LLM，节省摘要调用成本 |
| Summary budget | 压缩内容的 20%，上限 12,000 tokens（`agent/context_compressor.py:51-53`） |
| 失败退避 | 摘要失败后冷却 600 秒，防止重试风暴（`agent/context_compressor.py:60`） |

### 分层告警

`run_agent.py:824-828` 实现分层用户通知：
- **85% 线**：首次触及通知一次
- **95% 线**：首次触及通知一次
- 告警不注入 LLM prompt（避免模型因感知压力而提前放弃当前任务）

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 简单性（单一 `75%` 规则易于理解和调优） | 安全性（不同 model 的 context window 大小差异大，固定 75% 对大窗口 model 太早触发、对小窗口 model 可能太晚导致截断） |
| 性能一致性（所有 model 统一行为，行为可预测） | 适配性（不同 model 的 token 估算精度不同但共用同一阈值） |

## nanobot — 四步透明上下文治理

### 透明治理管道

`agent/runner.py:552-697` 定义了四步在关键路径上自动执行的上下文治理管道。每一步对 LLM 完全不可见——LLM 不知道上下文被裁剪过，避免了模型因感知到上下文压力而提前放弃当前任务或改变行为策略。

### 四步管道

| 步骤 | 机制 | 触发条件 | 目的 |
|------|------|---------|------|
| **Backfill**（回填） | 检查前一轮响应的 tool_use 是否有对应的 tool_result，若缺失则补回 | 每轮自动 | 修复孤立的 tool_use（API 返回不完整或传输丢失），保证 LLM 看到的结构完整 |
| **Microcompact**（微压缩） | 压缩 10 轮之前的 tool result 为摘要 | 每轮自动，10 轮前的 tool result | 回收老旧 tool result 占用的 token 空间，同时保留语义摘要供 LLM 回溯 |
| **Tool Result Budget**（工具结果预算） | 对超长 tool result 按预算截断，保留头部 | 每轮自动，超预算的 tool result | 防止单个超大工具输出撑爆上下文，截断后仍保留前置关键内容 |
| **Snip History**（历史裁剪） | 按 token 预算从消息历史尾部裁剪老旧消息 | 每轮自动，总 token 超预算时 | 最后的防线——当总上下文超过目标预算时，从最旧的消息开始裁剪 |

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| LLM 透明性（四步全部不可见，避免 LLM 感知压力后提前放弃或改变策略） | LLM 策略盲区（LLM 不知道自己上下文被裁剪，无法主动调整策略——例如无法判断哪些 tool result 已丢失从而主动重新获取） |
| 进程内自动化（不依赖 LLM 自身能力做治理，全部在 AgentRunner 层自动完成） | 关键路径性能开销（四步均在每轮请求前同步执行，任何一步出错导致 LLM 看到损坏的上下文） |

### 代价

四步均在关键路径上运行——Backfill、Microcompact、Budget、Snip 在每轮 LLM 请求发出前同步执行，任何一步的 bug 或边界条件处理不当都可能导致 LLM 收到格式损坏或不完整的上下文，进而产生不可预期的行为（幻觉、遗漏、错误重试）。

## 权衡对比

| 维度 | openclaw | hermes-agent | nanobot |
|------|----------|-------------|---------|
| **触发策略** | 多源保守最小选择（hard floor + soft warn + 优先级 fallback） | 固定 75% 窗口比例 | 不依赖阈值，每轮自动执行四步管道 |
| **安全余量** | `SAFETY_MARGIN = 1.2`（20% 缓冲） | 隐含在 75% 阈值中（剩余 25% 即余量） | 不适用——四步管道逐步回收空间，无需整体余量 |
| **Model 适配** | 每 model 动态计算有效窗口 | 所有 model 统一 75%，大窗口 model 过早触发 | Model 无关——治理逻辑不依赖 model context window 大小 |
| **告警机制** | 硬下限 + 软警告 | 85%/95% 分层通知（不注入 LLM） | 无告警——LLM 完全不知道治理发生 |
| **压缩侧重** | 可恢复性优先（保留任务状态 + strip tool details） | 容量优先（结构化摘要 + tail 保护） | 透明性优先（LLM 无感知的渐进式空间回收） |
| **失败处理** | 未从文档中检出 | 压缩失败冷却 600 秒 + summary budget 上限 12K tokens | 四步中任一步出错导致损坏上下文传入 LLM（无独立失败退避） |
| **架构解耦** | `ContextEngine`（exclusive slot）+ `CompactionProvider` 分开注册 | `ContextEngine` ABC + 策略目录，单继承点 | AgentRunner 内联——四步硬编码在 runner 主循环中，不可插拔 |
| **核心取舍** | 宁可过度保守也不允许溢出（安全性压倒经济性） | 宁可行为简单一致也不做 model 级动态适配（简单性压倒精确性） | 宁可 LLM 完全无感知也不暴露治理信息（透明性压倒 LLM 策略自主性） |

## 选择指南

| 场景 | 推荐策略 | 原因 |
|------|---------|------|
| 多 model 环境且 model context window 差异大 | openclaw 的多源保守最小选择 | 每 model 动态计算有效窗口，避免大窗口过早压缩或小窗口溢出 |
| 单 model 环境且追求行为简单可预测 | hermes-agent 的固定 75% 阈值 | 单一规则易于理解和调优，无需维护多源数据 |
| 追求 LLM 完全无感知的自动化治理，不信任 LLM 自我管理能力 | nanobot 的四步透明治理 | 四步管道在 AgentRunner 层静默执行，LLM 不知道上下文被裁剪，不会因感知压力提前放弃任务 |
| 工具调用频繁且工具输出大小不可预测 | nanobot 的 Microcompact + Tool Result Budget | 10 轮前 tool result 自动压缩 + 超长结果截断，防止工具输出撑爆上下文 |
| 多模型频繁切换且需统一行为 | hermes-agent 的固定 75% | 所有 model 统一行为，切换 model 无需调整压缩参数 |

## 关键源码引用

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/agents/context-window-guard.ts` | 4-81 | 硬下限 16,000 / 软警告 32,000 + 多源保守选择 |
| openclaw | `src/agents/compaction.ts` | 19-40 | BASE_CHUNK_RATIO 0.4 / MIN_CHUNK_RATIO 0.15 / SAFETY_MARGIN 1.2 |
| hermes-agent | `agent/context_engine.py` | 32-60 | ContextEngine ABC 抽象基类 + 策略模式注册 |
| hermes-agent | `agent/context_engine.py` | 59 | 固定 75% 触发阈值 |
| hermes-agent | `agent/context_compressor.py` | 333-465, 584-633 | tool output 修剪(333-465) + 结构化摘要模板(584-633) |
| hermes-agent | `agent/context_compressor.py` | 51-53 | Summary budget = 20% / max 12,000 tokens |
| hermes-agent | `agent/context_compressor.py` | 60 | 失败冷却 600 秒 |
| hermes-agent | `run_agent.py` | 824-828, 10688-10696 | 85%/95% 分层告警：初始化注释(824-828) + 阈值判断逻辑(10688-10696)（不注入 LLM） |
| nanobot | `agent/runner.py` | 552-697 | Backfill + Microcompact + Tool Result Budget + Snip History 四步透明上下文治理管道 |

## 关联

- [[openclaw/dimensions/openclaw-performance-tradeoffs]]
- [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]]
- [[openclaw/nodes/components/openclaw-context-engine]]
- [[hermes-agent/nodes/extension-points/hermes-agent-context-engine]]
- [[nanobot/dimensions/nanobot-performance-tradeoffs]]

## 修复记录

- **2026-06-19（v2-verify round-3）**：根据 phase-3b-verify 验证报告，修正溯源表两处行号：
  - `hermes-agent context_compressor.py`：`15-17`（模块 docstring 摘要）→ `333-465, 584-633`（tool output 修剪 + 结构化摘要模板实际实现）
  - `hermes-agent run_agent.py`：`824-828`（仅初始化注释）→ `824-828, 10688-10696`（补充阈值判断逻辑实现行号）
