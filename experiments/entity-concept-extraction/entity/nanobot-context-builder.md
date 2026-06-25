# ContextBuilder（nanobot）

## 是什么 / 边界
nanobot 的系统 prompt 组装器——将六层独立内容依次拼接为发给 LLM 的完整 messages。纯数据到文本的转换层：不持有 AgentLoop 引用、不调用 LLM、不管理工具。每层用 `---` 分隔。

**边界**：ContextBuilder 是单向数据流——输入配置 + 文件内容 + skills 列表 + 历史记录，输出 messages 列表。不做任何状态管理，不缓存结果。

## 关键实现
- **六层拼接顺序**：
  1. `identity` — 渲染 `agent/identity.md` 模板
  2. `bootstrap files` — AGENTS.md / SOUL.md / USER.md / TOOLS.md 内容
  3. `memory` — MEMORY.md 内容
  4. `always skills` — `always: true` 标记的技能全文
  5. `skills summary` — 所有技能的 XML 摘要（名称 + 描述 + 路径 + 可用性）
  6. `recent history` — 上次 Dream 光标后的历史记录
- **渐进式加载支持**：Skills summary 只包含元数据，实际技能内容由 agent 按需通过 `read_file` 工具加载——避免 system prompt 膨胀
- **可测试性**：ContextBuilder 不依赖 AgentLoop 或任何运行时状态——可以独立构造输入进行单元测试

## 设计选择记录
- **维度**：Architecture
- **选择**：ContextBuilder 是纯数据到文本的转换层——不调用 LLM、不管理工具、不持有运行时引用
- **替代方案**：上下文组装与 agent 循环耦合（如 openclaw 的 context-engine 集成在 gateway 中），允许根据运行时状态动态调整 prompt 结构
- **为什么有这个选择**：纯函数式设计使 system prompt 可以独立于 AgentLoop 进行测试和调试。六层固定顺序也确保 prompt cache 稳定性——只要 bootstrap files 和 skills 不变，system prompt 前缀就不变
