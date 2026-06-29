---
type: entity
repo: hermes-agent
slug: context-compressor
problem: 如何在接近模型 token 限制时自动压缩对话历史，保留关键信息的同时减少上下文成本
generated: 2026-06-25
source_files:
  - agent/context_compressor.py
  - agent/context_engine.py
---

# 上下文压缩器

**代码位置**：`agent/context_compressor.py`、`agent/context_engine.py`
**这个模块解决什么问题**：
- 实现层：`ContextCompressor` 继承 `ContextEngine` ABC，通过三阶段压缩算法（工具结果裁剪 → 结构化摘要生成 → 组装压缩消息列表），在接近 token 限制时自动压缩对话历史
- 问题层：如何在接近模型 token 限制时自动压缩对话历史，保留关键信息的同时减少上下文成本
**对外暴露什么**：`ContextCompressor` 类（agent/context_compressor.py:185）、`ContextEngine` ABC（agent/context_engine.py:32）
**它和谁交互**：
- 依赖 [[entities/model-adapters]]（通过 `call_llm(task="compression", ...)` 调用便宜模型生成摘要）
- 依赖 [[entities/state-database]]（压缩触发会话拆分为 parent_session_id 链）
- 被 [[entities/agent-core]] 调用（每轮检查 `should_compress()`，触发时调用 `compress()`）
- 被 [[entities/plugin-system]] 调用（ContextEngine 插件可替换默认压缩器）
**为什么它是可分离的**：通过 ABC 定义接口，`ContextCompressor` 是默认实现，可通过插件系统替换为其他引擎

**关键机制**（源码可见）：
- 三阶段压缩管线：
  1. Phase 1 - 工具结果裁剪：`_prune_old_tool_results()` 用一句话摘要替换旧工具结果、去重、截断大参数。无需 LLM 调用 ^[agent/context_compressor.py:333]
  2. Phase 2 - 边界确定：保护头部 N 条消息（`protect_first_n=3`）、按 token 预算找到尾部（~20K tokens 的近期上下文）^[agent/context_compressor.py:827-926]
  3. Phase 3 - 结构化摘要：`_generate_summary()` 通过辅助 LLM 生成 11 字段结构化摘要（Goal, Constraints, Completed Actions, Active State, In Progress, Blocked, Key Decisions, Resolved/Pending Questions, Relevant Files, Remaining Work, Critical Context）^[agent/context_compressor.py:542]
- 反震荡保护：连续 2 次压缩效果不明显（减少 <10%）时指数退避（300s → 1800s → 3600s max）^[agent/context_compressor.py:307-330]
- 迭代摘要：存在上一轮摘要时，`_generate_summary()` 使用 "update" 模式，合并新旧信息而非从头生成 ^[agent/context_compressor.py:542-590]
- 工具配对修复：`_sanitize_tool_pairs()` 修复压缩后孤立的 tool_call/tool_result 配对，防止 API 报错 ^[agent/context_compressor.py:767]
- 上下文感知压缩触发：`should_compress()` 在 `estimated_total > threshold_tokens`（默认 context_length 的 50%）时触发 ^[agent/context_compressor.py:307]
- 可插拔引擎：`ContextEngine` ABC 定义 `on_session_start`、`update_from_response`、`should_compress`、`compress`、`on_session_end` 接口，支持运行时替换 ^[agent/context_engine.py:32]

**源码证据**：
- 入口文件：agent/context_compressor.py
- 核心类型：`class ContextCompressor(ContextEngine)` ^[agent/context_compressor.py:185]、`class ContextEngine(ABC)` ^[agent/context_engine.py:32]

**关联 Concept**：
- [[concepts/context-compression-strategy]]
