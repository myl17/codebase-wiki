# AgentHook（nanobot）

## 是什么 / 边界
nanobot 的可组合生命周期钩子系统——六个拦截点覆盖 agent 循环的关键时刻。`CompositeHook` 将多个钩子串联为执行管道。AgentLoop 维护 `_extra_hooks` 列表允许外部插件注入。

**边界**：AgentHook 提供扩展入口，不做业务逻辑——它定义「何时可以介入」，不定义「介入后做什么」。钩子实现由外部提供。

## 关键实现
- **六个拦截点**：
  1. `before_iteration` — 每轮 LLM 调用前
  2. `on_stream` — 流式响应的每个 chunk
  3. `on_stream_end` — 流式响应完成
  4. `before_execute_tools` — tool 执行前
  5. `after_iteration` — 每轮 LLM 调用后
  6. `finalize_content` — 最终内容输出前
- **CompositeHook 管道策略**：
  - `finalize_content` — **纯函数管线**：数据流经每个 hook，前一个的输出是后一个的输入
  - 其余五个方法 — **扇出**：每个 hook 独立执行，一个 hook 的异常不阻塞其他
- **运行时注入**：AgentLoop 维护 `_extra_hooks` 列表，外部插件可在运行时添加钩子而不修改核心代码

## 设计选择记录
- **维度**：Extension Points
- **选择**：`finalize_content` 是纯函数管线（管道串联），其余方法是扇出（独立并发），两者采用不同的组合策略
- **替代方案**：所有钩子统一用管道模式，或统一用扇出模式
- **为什么有这个选择**：`finalize_content` 是内容变换——每个 hook 的输出是下一个的输入，适合管道串联实现逐步加工。其余方法是事件通知——多个 hook 各做各的互不干扰，适合扇出避免单点阻塞
