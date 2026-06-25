# ContextEngine — 上下文压缩（Hermes Agent）

## 是什么 / 边界

ContextEngine 是可插拔的上下文压缩策略组件，在对话达到 75% context window 时触发，用辅助 LLM 摘要中间轮次，让 agent 能进行超过单次 context window 的长对话。

它的边界：只负责检测压缩时机和执行压缩，不改变 LLM 选择，不感知工具执行结果的业务语义，不管理哪些内容"重要"（那由摘要模板和 MemoryProvider 的 on_pre_compress hook 决定）。同一时间只有一个 engine 激活。

## 关键实现

- 抽象基类：`agent/context_engine.py:32-60`
- 默认实现（summary-based）：`agent/context_compressor.py:1-60`
- 触发阈值：75% 的模型 context window（`agent/context_engine.py:59`）
- 压缩策略：结构化摘要模板 + token-budget tail 保护 + 工具输出修剪（先剪后摘要）
- Summary budget：压缩内容的 20%，上限 12,000 tokens（`agent/context_compressor.py:51-53`）
- 失败退避：摘要失败冷却 600 秒，防止重试风暴（`agent/context_compressor.py:60`）
- 用户通知：85% 和 95% 阈值各通知一次（只通知用户，不注入 LLM）
- 激活方式：`config.yaml` 中 `context.engine: "lcm"`；第三方 engine 放 `plugins/context_engine/<name>/`

ContextEngine ABC 接口：
```python
should_compress() -> bool
compress(messages) -> List
update_from_response(usage_data)
get_tools() -> List[dict]  # 可选附加工具（如 lcm_grep）
```

## 设计选择记录

- **维度**：Performance Tradeoffs
- **选择**：上下文压缩用辅助（便宜）LLM 摘要中间轮次，牺牲信息保真度换取无限长对话
- **替代方案**：严格限制对话长度，超出 context window 直接截断旧消息
- **为什么有这个选择**：直接截断会丢失完整的工具调用链，可能导致 agent 重复工作或状态不一致；摘要虽然损失一些细节，但保留了对话的语义连续性

---

- **维度**：Performance Tradeoffs
- **选择**：压缩通知只发给用户（85%/95% 阈值），不注入给 LLM
- **替代方案**：在接近 context 上限时向 LLM 发送警告，让它尝试提前总结或结束
- **为什么有这个选择**：实验发现向 LLM 发送 context 压力警告会导致模型提前放弃未完成的任务（同 IterationBudget 的选择逻辑相同）；用户需要知道压缩发生了，但 LLM 不应感受到这个压力

---

- **维度**：Extension Points
- **选择**：ContextEngine 以 ABC 接口提供，支持第三方实现放入 plugins 目录
- **替代方案**：硬编码单一压缩策略，不支持替换
- **为什么有这个选择**：不同场景对压缩策略需求不同（代码场景需要保留代码块、对话场景更看重语义连续性）；插件化允许外部开发者实验不同压缩算法
