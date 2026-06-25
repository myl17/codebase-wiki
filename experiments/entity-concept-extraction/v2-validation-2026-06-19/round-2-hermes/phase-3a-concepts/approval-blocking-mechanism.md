---
concept: approval-blocking-mechanism
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# 审批阻塞机制如何选择——异步 Promise 等待还是同步线程阻塞？

## 标准化问题陈述

在高风险命令需要用户审批时，如何决定 agent 线程的阻塞等待机制——是异步 Promise 等待（不占事件循环）还是同步 `threading.Event` 阻塞（线程挂起）？

## 核心关切

1. **审批必须是同步阻塞的**——不能在命令执行后才通知用户。审批通过前命令不得执行，审批决策必须发生在命令执行路径的关键门控点上
2. **阻塞等待不应死锁 agent 进程**——需要超时、取消和多审批并发能力。一个审批请求的等待不应阻塞其他审批或 agent 的正常运作
3. **审批可通过多种路径到达用户**——CLI（本地 TUI）、Gateway HTTP（远程 `/approve` API）、chat reply（IM 平台回复）都可能承载审批决策，阻塞机制需支持多路径送达
4. **审批失败或超时不应导致 agent session 永久卡死**——拒绝或超时后应有明确的恢复路径（拒绝执行 + 通知 LLM 结果），不能留下悬挂的等待状态
5. **并行子 agent 的审批请求需要独立队列和独立等待**——父 agent 委派子 agent 后，各子 agent 的审批请求应独立排队、独立阻塞、独立解除，互不干扰

## 实例矩阵

| 仓库 | 阻塞机制 | 等待原语 | 审批路径 | 核心权衡 |
|------|---------|---------|---------|--------|
| openclaw | 异步阻塞双路径审批 | Promise (`waitForExecApprovalDecision`) | host CLI + gateway HTTP 双路径 | 不占事件循环（可中断异步等待）+ 多路径 > 实现复杂度 |
| hermes-agent | FIFO 队列 + 线程 Event | `threading.Event` 阻塞等待 | Gateway 单路径（依赖 `/approve` 回复） | 多审批并发（每个子 agent 独立 Event）+ 简单性 > 线程资源占用 |

## openclaw — 异步阻塞双路径审批

### 机制概述

`src/agents/bash-tools.exec-approval-request.ts:89-126` 定义了 `ExecApprovalRequest` 扩展点——exec 类工具在执行前通过此扩展点发起异步阻塞审批。

openclaw 的工具调用经过 5 层同步 pipeline（`src/agents/tool-policy-pipeline.ts:56-90`），对所有工具调用做 allowlist/denylist 叠加过滤。exec 类工具在通过 5 层过滤后，额外经过 `ExecApprovalRequest` 扩展点阻塞等待 owner 审批。pipeline 本身是同步串行的，但审批等待是异步的（Promise-based）——这是 openclaw 机制的核心特征：同步门控 + 异步等待。

### 异步等待机制

注册 `ExecApprovalRequest` 后，调用 `waitForExecApprovalDecision` 进入异步等待。由于使用 Promise 而非同步原语（如 `threading.Event`），等待过程不占用事件循环——agent 可以在等待审批的同时处理其他非阻塞任务。这是 Node.js 事件驱动模型的自然选择。

### 双路径审批

审批决策可通过两条路径到达：
- **Host CLI 路径**：本地运行的 openclaw 实例，owner 在 TUI 中直接响应审批请求
- **Gateway HTTP 路径**：通过 gateway 的 HTTP API 接收远程审批决策

双路径设计意味着审批不绑定特定通信渠道——二开时可在 `ExecApprovalRequest` 扩展点注入自定义审批逻辑（UI 弹窗、Slack 通知、邮件等），不需改动 ToolPolicy pipeline。这符合 openclaw 的 extension point 设计哲学：核心 pipeline 保持稳定，审批的通信方式由扩展决定。

### 可中断性

由于审批等待是 Promise-based，等待本身是可中断的——超时、取消、连接断开都可以通过 Promise rejection 或 AbortController 传播，在设计上避免了永久悬挂的等待状态。但这也意味着 Promise 链管理（取消传播、错误处理、状态恢复）的实现复杂度高于简单的同步 Event。

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 不占事件循环（Promise 异步等待，agent 在审批期间可处理其他非阻塞任务；可中断——超时/取消通过 Promise rejection 传播） | 实现复杂度（Promise 链管理——取消传播、错误处理、状态恢复——比同步 Event 复杂；调试异步审批流的状态比调试线程阻塞更难） |
| 多路径（host CLI + gateway HTTP 双路径，二开可在扩展点注入自定义审批 UI 而不改 pipeline） | |

## hermes-agent — FIFO 队列 + threading.Event

### 机制概述

`tools/approval.py:586-922` 的 `check_all_command_guards` 是所有命令执行的同步门控入口——任何 exec 类工具调用必须经过此函数，绕过它没有合法路径。

hermes-agent 的审批分三层（`tools/approval.py:586-922`）：
- **Layer 0 — 快速路径**：YOLO 模式 / 容器环境 / `approvals.mode=off`，全部放行不检查
- **Layer 1 — Smart**：辅助 LLM 风险评估 → 自动批准/拒绝/升级到 Layer 2
- **Layer 2 — Manual**：tirith 安全分析 + 25+ `DANGEROUS_PATTERNS` 正则匹配（`tools/approval.py:75-138`）→ 用户交互式审批

只有 Layer 2 进入阻塞等待——Layer 0 和 Layer 1 的自动决策不涉及用户交互，不触发阻塞。

### FIFO 队列 + threading.Event 阻塞

`tools/approval.py:219-284` 实现 Gateway 模式下的阻塞审批队列：

- **FIFO 队列**：审批请求按到达顺序排队，保证先请求先处理的公平性
- **`threading.Event`**：agent 线程调用 `event.wait()` 挂起，等待用户通过 Gateway 发送 `/approve` 或 `/deny` 命令
- **独立 Event**：每个并行子 agent 拥有独立的 `threading.Event` 实例，各自的审批请求独立排队、独立阻塞、独立解除
- **Gateway 单路径**：审批决策通过 Gateway 的 chat reply 路径到达——用户在同一对话线程中回复 `/approve` 或 `/deny`，Gateway 路由到对应审批请求的 Event 并 `set()` 唤醒等待线程

### 审批持久化

用户可选择审批级别（`tools/approval.py:299-303, 376-402`）：
- `once` — 仅本次有效
- `session` — 会话级允许，当前 session 内后续相同命令自动放行
- `always` — 写入 `config.yaml` 的 `command_allowlist`，跨会话持久化

审批级别的持久化减少了不必要的阻塞等待——已信任的命令不再触发 Layer 2 交互审批。

### 设计取向

| 满足的关切 | 接受妥协的关切 |
|-----------|--------------|
| 多审批并发（每个子 agent 独立 `threading.Event`，并行子 agent 的审批请求互不阻塞；FIFO 队列保证公平性） | 线程资源占用（每个阻塞的审批请求占用一个线程——Gateway 模式下 agent 线程在 `event.wait()` 中挂起，线程栈和上下文持续占用内存） |
| 简单性（`threading.Event` 是 Python 标准库中最简单的同步原语——`wait()` / `set()` 语义一目了然；FIFO 队列逻辑直观） | 路径单一（审批决策仅通过 Gateway `/approve` 回复到达——CLI TUI 模式下不适用此阻塞机制，CLI 路径使用 prompt_toolkit 的同步输入等待，属另一套机制） |

## 权衡对比

| 维度 | openclaw | hermes-agent |
|------|----------|-------------|
| **阻塞原语** | Promise（`waitForExecApprovalDecision`） | `threading.Event`（`event.wait()`） |
| **事件循环占用** | 不占用（异步等待，事件循环可处理其他任务） | 占用线程（线程在 `wait()` 中挂起，栈和上下文持续占用内存） |
| **审批路径** | 双路径（host CLI + gateway HTTP），扩展点可注入自定义路径 | Gateway 单路径（依赖同一对话线程的 `/approve` 回复）；CLI 模式另有 `prompt_toolkit` 同步输入路径 |
| **多审批并发** | 每个审批请求独立 Promise，Promise.all 或独立 await | 每个子 agent 独立 `threading.Event` + FIFO 队列 |
| **可中断性** | 天然可中断（Promise rejection / AbortController） | 依赖 `threading.Event` 超时参数或外部 `set()` |
| **超时处理** | Promise 超时通过 `Promise.race` 或 AbortSignal.timeout 传播 | `event.wait(timeout=N)` 返回 False 后执行拒绝逻辑 |
| **实现复杂度** | 高（Promise 链管理——取消传播、错误恢复、多个审批请求的状态协调） | 低（`Event.wait()` / `set()` 两个原语 + FIFO 队列） |
| **调试难度** | 高（异步审批流的状态追踪需要 async context / logging） | 低（线程堆栈直接显示阻塞位置，`threading.enumerate()` 即可查看所有等待线程） |
| **扩展性** | 高（ExtensionPoint 模式——二开注入自定义审批 UI 不改 pipeline） | 中（三层审批可配置，但审批路径固定在 Gateway chat reply） |
| **门控位置** | 5 层同步 pipeline 之后，exec 类工具专属审批等待 | `check_all_command_guards` 统一入口，所有命令必经 |
| **审批粒度** | 工具级（exec 类工具触发） | 命令级（每个命令经 25+ DANGEROUS_PATTERNS 正则匹配后决定是否需要审批） |
| **语言/运行时约束** | TypeScript / Node.js 事件循环模型 → 异步是自然选择 | Python / 多线程模型 → `threading.Event` 是自然选择 |
| **核心取舍** | 宁可增加实现复杂度也不占用事件循环（事件驱动模型的正确性压倒代码简单性） | 宁可占用线程资源也不增加协调复杂度（简单性和并发独立性压倒资源效率） |

## 选择指南

| 场景 | 推荐机制 | 原因 |
|------|---------|------|
| **Node.js / 事件循环运行时** | 异步 Promise 等待（openclaw 模式） | 同步阻塞在 Node.js 中会冻结整个事件循环，异步等待是自然选择（Worker Threads 也可实现同步阻塞，但增加线程协调复杂度和 Node.js 生态中的非惯用性） |
| **Python / 多线程运行时** | `threading.Event` 阻塞（hermes-agent 模式） | Python GIL 下多线程阻塞等待是成熟模式，实现简单、调试方便 |
| **需要多路径审批送达** | 异步 + 扩展点注入（openclaw 模式） | 扩展点模式允许审批通过 CLI / HTTP / Slack / 邮件等多路径送达，不绑定通信渠道 |
| **简单性优先、路径单一确定** | FIFO + Event（hermes-agent 模式） | 实现和调试成本最低，适合审批路径固定不变的场景 |
| **高并发子 agent 场景** | 独立 Promise 或独立 Event 均可 | 关键不在原语选择，而在是否每个子 agent 有独立的等待句柄——两种机制都满足此要求 |
| **需要审批结果跨会话持久化** | 参考 hermes-agent 的 `once/session/always` 三级持久化 | 减少重复审批、降低用户疲劳——此特性独立于阻塞机制，可叠加到任一方案 |

## 关键源码引用

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `src/agents/bash-tools.exec-approval-request.ts` | 89-126 | ExecApprovalRequest 扩展点：注册审批请求 + `waitForExecApprovalDecision` 异步等待 |
| openclaw | `src/agents/tool-policy-pipeline.ts` | 56-90 | 5 层同步 pipeline：exec 类工具在通过 5 层过滤后进入审批等待 |
| openclaw | `src/agents/tool-policy.ts` | 19-55 | OwnerOnlyToolApprovalClass：control_plane / exec_capable / interactive 三类工具分治 |
| hermes-agent | `tools/approval.py` | 586-922 | `check_all_command_guards` 统一门控入口 + 三层审批（Layer 0/1/2） |
| hermes-agent | `tools/approval.py` | 219-284 | Gateway 阻塞审批：FIFO 队列 + `threading.Event` 阻塞等待 `/approve`/`/deny` |
| hermes-agent | `tools/approval.py` | 534-583 | Smart Approval：辅助 LLM 风险评估 → auto-approve/deny/escalate |
| hermes-agent | `tools/approval.py` | 75-138 | DANGEROUS_PATTERNS：25+ 正则模式覆盖 rm/chmod/mkfs/kill/systemctl 等 |
| hermes-agent | `tools/approval.py` | 299-303 | 审批级别 `session`：会话级允许 |
| hermes-agent | `tools/approval.py` | 376-402 | 审批级别 `always`：写入 `config.yaml` 跨会话持久化 |

## 关联

- [[人机审批协议]]
- [[openclaw/nodes/extension-points/openclaw-exec-approval-request]]
- [[hermes-agent/nodes/components/hermes-agent-approval-system]]
- [[openclaw/nodes/design-decisions/openclaw-sync-gating-decision]]
- [[hermes-agent/nodes/design-decisions/hermes-agent-layered-approval-decision]]
- [[openclaw/nodes/components/openclaw-tool-policy]]
- [[openclaw/dimensions/openclaw-architecture]]
- [[hermes-agent/dimensions/hermes-agent-architecture]]

## 修复记录（2026-06-19 验证后修正）

| 判定 | 位置 | 修正内容 |
|------|------|---------|
| ⚠️ | 选择指南 — Node.js 行 | "唯一正确的选择" → "自然选择"，补充 Worker Threads 替代方案说明，降低绝对化程度 |
| ⚠️ | openclaw 可中断性段落 | "不会留下永久悬挂的等待状态" → "在设计上避免了永久悬挂的等待状态"，wiki 未验证 AbortController 具体保证 |
| ⚠️ | 已知增益细节 | `waitForExecApprovalDecision` 方法名、Promise rejection/AbortController 可中断细节、独立 Promise per sub-agent、超时恢复路径——均标注为 concept 页对源码的细粒度掌握，超出 wiki 当前覆盖范围（wiki 确认异步阻塞定性但未展开内部机制） |
| ⚠️ | hermes CLI prompt_toolkit 关联 | wiki 确认 CLI 层含 prompt_toolkit 但未将同步输入与审批阻塞机制交叉引用，concept 页推断合理但缺少 wiki 溯源 |
| ⚠️ | 权衡对比表 — 可中断性行 | openclaw 侧"Promise rejection / AbortController"细节——wiki 确认异步阻塞但未展开此机制；hermes 侧 `event.wait(timeout=N)` 已由 wiki 确认 |
| ⚠️ | 权衡对比表 — 超时处理行 | openclaw 侧 `Promise.race` / `AbortSignal.timeout` 细节——wiki 未确认具体超时实现路径；hermes 侧已由 wiki 确认 |
| ⚠️ | 权衡对比表 — 多审批并发行 | openclaw 侧"每个审批请求独立 Promise"——wiki 未明确描述独立 Promise 机制；hermes 侧已由 wiki 确认"并行子 agent 并发等待各自审批" |

**验证汇总**：本页所有核心架构事实（ExecApprovalRequest 扩展点、5 层 pipeline、三层审批、FIFO+Event、DANGEROUS_PATTERNS、审批持久化）均在 wiki 中有明确行号确认。Concept 页的源码细节深度超出 wiki 覆盖范围（方法级 API 名、可中断内部机制），属于概念页的正常增量——这些细节不构成事实错误，但验证时无法从 wiki 维度页溯源。
