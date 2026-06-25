# Context Engine（OpenClaw）

## 是什么 / 边界

Context Engine 是 OpenClaw 的对话上下文生命周期管理器：负责 prompt 的组装（assemble）、新消息摄入（ingest）、历史压缩（compact）和 transcript 重写（transcriptRewrite）四个核心操作。不直接调用 LLM（由 Agent Harness 负责），不决定记忆何时注入（由 hook 系统驱动），不做工具调度。

## 关键实现

- 主入口：`src/context-engine/index.ts`（四个生命周期操作 + `ContextEngineFactory` 注册点）
- 向后兼容：`LegacyContextEngine` 包装旧接口，支持平滑迁移
- 压缩逻辑：`src/agents/compaction.ts`（`BASE_CHUNK_RATIO = 0.4`、`MIN_CHUNK_RATIO = 0.15`、`SAFETY_MARGIN = 1.2`）
- Context Window 保护：`src/agents/context-window-guard.ts`（硬限 16000 tokens，软警告 32000 tokens）
- Prompt Cache Boundary：`src/agents/system-prompt-cache-boundary.ts`（`<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记切分稳定/动态前缀）
- Bootstrap 文件缓存：`src/agents/bootstrap-cache.ts`（`Map<sessionKey, files>` 缓存 CLAUDE.md 等，session rollover 时清除）
- 注册入口：`OpenClawPluginApi.registerContextEngine`（独占槽位）

## 设计选择记录

- **维度**：Performance Tradeoffs
- **选择**：压缩时优先保留活跃任务状态、批处理进度、最后一次用户请求（可恢复性优先），而非最大化压缩率
- **替代方案**：追求最高压缩率，均匀丢弃历史内容，最大化腾出 context 空间
- **为什么有这个选择**：agent 经常处理多步骤长任务，压缩后如果丢失任务状态会导致任务中断需要用户重新说明；可恢复性比压缩率更直接影响用户体验

---

- **维度**：Performance Tradeoffs
- **选择**：system prompt 通过 `OPENCLAW_CACHE_BOUNDARY` 标记切分稳定前缀和动态后缀，稳定部分命中 Anthropic Prompt Caching
- **替代方案**：每次调用发送完整 system prompt，不做任何缓存边界设计
- **为什么有这个选择**：稳定内容（技能定义、人格等）在每次对话轮次中不变，命中缓存可大幅降低 token 输入成本；代价是 system prompt 结构复杂度上升

---

- **维度**：Extension Points
- **选择**：`registerContextEngine` 为独占槽位，全局只能有一个活跃实现
- **替代方案**：允许多个 context engine 实现同时注册，core 按规则选择
- **为什么有这个选择**：context engine 控制整个对话状态，多个实现并存会导致状态冲突；独占设计迫使使用者明确选择一个实现，避免隐式竞争

---

- **维度**：Architecture
- **选择**：`tool_result.details` 在压缩前被 strip，防止冗长工具输出污染摘要
- **替代方案**：完整保留 tool result 内容参与摘要生成
- **为什么有这个选择**：工具输出（如长文件读取结果）通常冗长且不适合作为历史摘要素材，strip 后可显著提高摘要质量并减少摘要本身的 token 消耗
