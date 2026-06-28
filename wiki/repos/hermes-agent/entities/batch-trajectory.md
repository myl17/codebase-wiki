---
type: entity
repo: hermes-agent
slug: batch-trajectory
problem: 如何批量生成 Agent 执行轨迹用于 RL 训练数据，并将轨迹压缩到目标 token 预算同时保留训练信号质量
generated: 2026-06-25
source_files:
  - batch_runner.py
  - trajectory_compressor.py
  - tools/rl_training_tool.py
  - rl_cli.py
---

# 批量轨迹生成与压缩

**代码位置**：`batch_runner.py`、`trajectory_compressor.py`、`tools/rl_training_tool.py`
**这个模块解决什么问题**：
- 实现层：`BatchRunner` 通过 multiprocessing 并行处理 JSONL 数据集，为每条 prompt 创建 AIAgent 实例执行并记录轨迹（JSONL 输出 + checkpoint）；`TrajectoryCompressor` 事后将完整轨迹压缩到目标 token 预算（默认 15250），通过保护首尾 + 摘要中间轮次保留训练信号
- 问题层：如何批量生成 Agent 执行轨迹用于 RL 训练数据，并将轨迹压缩到目标 token 预算同时保留训练信号质量
**对外暴露什么**：`BatchRunner` 类（batch_runner.py:514）、`TrajectoryCompressor` 类（trajectory_compressor.py:307）、`CompressionConfig` dataclass（trajectory_compressor.py:58）、`rl_training_start()` / `rl_training_stop()`（tools/rl_training_tool.py）
**它和谁交互**：
- 依赖 [[entities/agent-core]]（`_process_single_prompt()` 为每个 prompt 创建 AIAgent 实例执行）
- 依赖 [[entities/tool-registry]]（sample_toolsets_from_distribution 控制每个批次使用的工具集）
- 依赖 [[entities/model-adapters]]（轨迹压缩使用 Gemini Flash 辅助模型生成摘要）
- 被 [[entities/cli-system]] 调用（`hermes batch` 或 `python batch_runner.py`）
- 被 [[entities/provider-registry]] 调用（通过 OpenRouter 调用用于压缩的 LLM）
**为什么它是可分离的**：独立的离线工具链（batch_runner 和 trajectory_compressor），不参与 agent 运行时循环

**关键机制**（源码可见）：
- 多进程并行：`BatchRunner` 使用 `multiprocessing.Pool` 并行处理 prompt，每个 worker 独立创建 AIAgent 实例 ^[batch_runner.py:388-512]
- 检查点恢复：`_load_checkpoint()` / `_save_checkpoint()` 支持中断恢复，记录已完成的 prompt 和批次进度 ^[batch_runner.py:670-740]
- 工具统计归一化：`_normalize_tool_stats()` 确保所有可能的工具在输出中都有条目（HuggingFace dataset schema 兼容性）^[batch_runner.py:60-113]
- 推理统计：`_extract_reasoning_stats()` 从消息中提取 reasoning token 统计 ^[batch_runner.py:197-230]
- 三段式压缩策略：保护首轮（system + first human + first gpt + first tool）→ 保护最后 N 轮 → 压缩中间轮次，仅从第二个 tool response 开始压缩 ^[trajectory_compressor.py:307-662]
- 目标 token 预算：默认 `target_max_tokens = 15250` + `summary_target_tokens = 750`，使用 Kimi-K2-Thinking tokenizer 计算 ^[trajectory_compressor.py:58-100]
- 压缩模型：通过 OpenRouter 使用 `google/gemini-3-flash-preview`（temperature 0.3）生成压缩摘要 ^[trajectory_compressor.py:101-130]
- RL 训练工具：`rl_training_tool.py` 提供 Agent 启动/停止训练工作流的能力，连接 Atropos RL 环境和 Tinker 框架 ^[tools/rl_training_tool.py]
- 批量指标：`AggregateMetrics` dataclass 汇总多轨迹的压缩率、token 节省等统计 ^[trajectory_compressor.py:203-305]
- 分布采样：`sample_toolsets_from_distribution()` 按概率分布采样工具集组合，支持 "default" 和 "image_gen" 等预定义分布 ^[toolset_distributions.py:247]

**源码证据**：
- 入口文件：batch_runner.py、trajectory_compressor.py
- 核心类型：`class BatchRunner` ^[batch_runner.py:514]、`class TrajectoryCompressor` ^[trajectory_compressor.py:307]
