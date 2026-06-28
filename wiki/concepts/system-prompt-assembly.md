---
type: concept
concept: system-prompt-assembly
problem: 如何组装 Agent 的系统提示词，集成身份定义、平台提示、技能列表、记忆上下文和项目文件
concerns: [层的可组合性与顺序, Prompt Caching 友好度, 注入安全]
repos: [nanobot, hermes-agent, openclaw]
generated: 2026-06-25
---

# 系统提示词组装

## 核心问题

每个 AI Agent 框架都必须回答：如何将零散的上下文碎片——身份定义、平台约束、可用技能、长期记忆、项目环境——组装成一个结构良好的系统提示词。这个问题的难度不在于单个片段的质量，而在于**片段的组合方式和顺序**：任意两个片段的排列都代表一种优先级取舍，而每种取舍都会影响模型行为。

组装顺序直接决定了 **Prompt Caching 的断点位置**——Anthropic 的 cache_control 断点只能设在静态前缀内，一旦动态内容（如会话历史）插入中间，后续所有块的 cache 都失效。因此，将最常变化的内容（记忆、上下文文件）放在最末尾，将最稳定的内容（身份、技能索引）放在最前面，是最优的缓存策略。但安全考虑反向推动：上下文文件注入可能包含恶意提示，必须在进入模型前做扫描，而这又依赖先注入平台提示和工具约束来建立安全基线。

三个框架在"层的可组合性"上走了完全不同的路线：nanobot 将每层封装为独立函数（用函数边界做组合），hermes-agent 将层定义为纯函数的顺序拼接（纯粹性优先），openclaw 则将层数量推向极致——27 个有序节（用枚举式排序消解模糊性）。

## 关切

- **层的可组合性与顺序**：各层是独立函数、纯函数拼接、还是枚举式节数组？顺序是硬编码还是可配置？与 Prompt Caching 断点策略如何互锁？
- **Prompt Caching 友好度**：cache_control 断点放在哪里？动态内容是否在静态块之后、避免污染前缀？技能内容如何缓存？
- **注入安全**：上下文文件、用户记忆、外部内容在进入系统提示词前是否有威胁扫描？扫描了哪些模式？安全检查对延迟和缓存的影响有多大？

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/context-builder]]
**解法**：每层作为 ContextBuilder 的独立方法，按固定顺序调用组装完整上下文。
**实现**：运行时上下文注入（`[Runtime Context]` 块含时间/channel/chat_id）→ 渐进式技能加载（always skills 完整 + XML 技能摘要）→ 引导文件分层（AGENTS.md > SOUL.md > USER.md > TOOLS.md）→ 最近历史注入（Dream 游标后的未处理条目） ^[nanobot/agent/context.py:21, 46-53, 103-113, 56-61]
**权衡**：层边界清晰、组合灵活（每个方法可独立替换），但无显式 Prompt Caching 断点标记，缓存效率依赖 LLM 实现的自动前缀匹配。注入安全弱——未见提示注入扫描，依赖引导文件的作者可信性。

### hermes-agent
来源：[[repos/hermes-agent/entities/prompt-builder]]
**解法**：纯函数模块按序拼接多层提示词，每层独立函数输出字符串段，顶层组装函数连接所有段。
**实现**：SOUL.md 身份 → PLATFORM_HINTS（20+ 平台格式化约束）→ 记忆上下文 → 技能索引（紧凑摘要格式）→ 上下文文件（注入前扫描 10+ 提示注入模式和不可见 Unicode）→ Anthropic cache_control 断点标记。模型特定执行纪律（TOOL_USE_ENFORCEMENT、OPENAI_MODEL_EXECUTION、GOOGLE_MODEL_OPERATIONAL）作为独立段注入。^[agent/prompt_builder.py:36-49, 173-283, 583-700]
**权衡**：注入安全最成熟——10+ 模式 + Unicode 检测，且扫描在注入前执行；cache_control 显式管理断点位置。代价是 20+ 平台提示常量 + 多套模型纪律使维护成本高，每个新平台或模型需要新增常量。

### openclaw
来源：[[repos/openclaw/entities/agent-runtime]]
**解法**：27 个按序排列的节硬编码在 `buildAgentSystemPrompt` 中，从 Identity 到 Runtime，每节有明确的边界和标题。
**实现**：Identity → Tooling → Skills（XML 格式注入）→ Memory → Workspace → Sandbox → Voice → Context Files → Runtime，全部 27 节顺序固定。Skills 以 XML 标签包裹注入，Memory 块含 `this is not user input` 上下文围栏。^[src/agents/system-prompt.ts:631-920]
**权衡**：节数最多、结构最显式（每节标题 = 功能边界），适合大规模多模块协作——新增功能只需插入新节。但 27 节硬编码顺序缺乏灵活性；Prompt Caching 断点未在 entity 页中显式记录，cache 友好度不透明。

## 对比
| 框架 | 层的可组合性与顺序 | Prompt Caching 友好度 | 注入安全 |
|------|------|------|------|
| nanobot | 每层独立方法，固定顺序调用 | 无显式 cache_control，依赖自动前缀匹配 | 弱，依赖引导文件可信性 |
| hermes-agent | 纯函数顺序拼接，每层独立函数 | 显式 `apply_anthropic_cache_control()` 设断点 | 强，10+ 注入模式 + Unicode 扫描 |
| openclaw | 27 个硬编码节，枚举式排序 | 未显式记录断点策略 | 中等，上下文围栏隔离 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
