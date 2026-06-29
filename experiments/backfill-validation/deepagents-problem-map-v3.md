# deepagents Problem Space Mapping v3

生成日期：2026-06-29
提示词版本：清理后（无 hook 示例，纯程序性检查）

---

## 中间件组合与 Agent 图组装

**问题陈述**：构建 AI Agent 框架时，如何将多个独立中间件按正确顺序组装成完整可执行的 Agent 图，确保横切关注点（工具注入、系统提示词增强、上下文压缩、缓存）正确协同工作。
**核心关切**：
- 关切 1：中间件执行顺序约束——某些中间件的输出是其他中间件的输入（如 FilesystemMiddleware 必须在 SubAgentMiddleware 之前，子代理需要文件系统工具）
- 关切 2：默认行为与用户自定义的集成——用户可能提供自己的中间件和子代理规范，框架需要决定默认堆栈与用户堆栈的合并策略
**deepagents 的解法**：通过 `create_deep_agent()` 单一入口函数按固定顺序组装中间件堆栈，用户中间件插入在固定堆栈尾部、缓存中间件之前，缺失的子代理自动创建默认实例。
**源码证据**：`deepagents/graph.py:363-395`（默认中间件堆栈顺序）、`deepagents/graph.py:358-360`（通用子代理自动注入）
**来源 Entity**：agent-graph-assembly
**层级**：架构决策

---

## 远程异步子代理编排

**问题陈述**：构建 AI Agent 框架时，如何支持长时间运行的后台任务——让主 Agent 派发任务到远程服务器后立即恢复交互，而不是阻塞等待任务完成。
**核心关切**：
- 关切 1：异步任务的生命周期管理——任务创建、状态查询、中途更新、取消，需要一组完整的工具来管理
- 关切 2：状态持久化与上下文压缩的兼容——异步任务状态必须在 Agent 状态中持久化，即使对话历史被压缩也不会丢失任务跟踪能力
**deepagents 的解法**：通过 `AsyncSubAgentMiddleware` 提供 start/check/update/cancel/list 五工具套件，任务状态存储在 Agent state 的自定义 reducer 中，通过 LangGraph SDK 连接远程 Agent Protocol 服务器。
**源码证据**：`deepagents/middleware/async_subagents.py:113-126`（任务状态持久化）、`deepagents/middleware/async_subagents.py:862`（核心类定义）
**来源 Entity**：async-subagent-middleware
**层级**：架构决策

---

## 后端接口抽象

**问题陈述**：构建 AI Agent 框架时，Agent 需要文件存储和命令执行能力，但底层存储实现可能是内存 state、磁盘文件系统、数据库或远程沙箱——如何定义一个统一接口让中间件不依赖具体实现。
**核心关切**：
- 关切 1：接口的完备性与简洁性的平衡——需要覆盖 ls/read/write/edit/grep/glob/upload/download 等操作，同时保持接口足够简单让新后端容易实现
- 关切 2：错误处理的一致性——不同的后端实现会产生不同类型的错误，需要统一的错误表示让 LLM 能理解和处理
**deepagents 的解法**：定义 `BackendProtocol`（文件操作）和 `SandboxBackendProtocol`（扩展 execute）两个抽象协议，所有 async 方法默认委托给 sync 版本，错误码标准化为四种可恢复错误的字面量。
**源码证据**：`deepagents/backends/protocol.py:301`（BackendProtocol 定义）、`deepagents/backends/protocol.py:33-48`（标准化错误码）
**来源 Entity**：backend-protocol
**层级**：架构决策

---

## 多后端路由

**问题陈述**：构建 AI Agent 框架时，如果不同类别的文件需要不同的存储策略（临时工作文件用短暂存储，长期记忆用持久化存储），如何在不修改中间件代码的情况下，根据路径前缀将操作路由到不同后端。
**核心关切**：
- 关切 1：路由的透明性——中间件调用 backend 接口时不应感知路由逻辑，路由应完全封装在后端层
- 关切 2：跨后端的聚合操作——ls、grep、glob 等操作需要在多个后端上执行并合并结果，同时保持路径前缀的正确性
**deepagents 的解法**：`CompositeBackend` 实现 `BackendProtocol`，按最长前缀优先匹配路由到不同后端，根路径下的 ls/grep/glob 跨所有后端聚合结果，未匹配路径走 default backend。
**源码证据**：`deepagents/backends/composite.py:87-116`（最长前缀优先路由）、`deepagents/backends/composite.py:213-229`（ls 聚合）、`deepagents/backends/composite.py:307-363`（跨 backend grep/glob）
**来源 Entity**：composite-backend
**层级**：架构决策

---

## 文件系统工具提供

**问题陈述**：构建 AI Agent 框架时，如何为 Agent 提供一套完整的文件系统操作工具（ls、read、write、edit、glob、grep、execute），同时工具集能根据后端能力动态调整（如有沙箱才提供 execute）。
**核心关切**：
- 关切 1：工具集的完备性——Agent 需要哪些文件操作工具才能完成常见任务？工具的 Schema 如何设计让 LLM 容易使用？
- 关切 2：工具的动态可用性——不是所有后端都支持命令执行，工具集需要根据后端能力自适应
**deepagents 的解法**：`FilesystemMiddleware` 提供 ls/read_file/write_file/edit_file/glob/grep 六个核心工具，execute 工具仅在后端实现 `SandboxBackendProtocol` 时动态注入。
**源码证据**：`deepagents/middleware/filesystem.py:522`（核心类定义）、`deepagents/middleware/filesystem.py:333-350`（动态 execute 工具注入）
**来源 Entity**：filesystem-middleware
**层级**：技术选型

---

## 工具结果溢出管理

**问题陈述**：构建 AI Agent 框架时，Agent 调用工具可能返回超大结果（大文件内容、长命令输出），如何在保留完整结果的同时防止撑爆 LLM 上下文窗口。
**核心关切**：
- 关切 1：信息保留 vs 上下文预算——需要保留完整结果供后续使用，但不能让 LLM 在单次推理中看到全部内容
- 关切 2：驱逐策略的选择——哪些工具的结果需要驱逐？哪些工具的输出本身就小不应该驱逐？
**deepagents 的解法**：当工具结果超过 token 阈值时，将完整结果写入文件系统，替换为截断预览 + 文件路径引用；ls/glob/grep/read_file/edit_file/write_file 从不驱逐（有自己的截断机制）。
**源码证据**：`deepagents/middleware/filesystem.py:384-393`（超大结果驱逐）、`deepagents/middleware/filesystem.py:374-381`（排除列表）
**来源 Entity**：filesystem-middleware
**层级**：技术选型

---

## 跨会话记忆加载

**问题陈述**：构建 AI Agent 框架时，Agent 需要跨会话记住项目约定、用户偏好和学到的经验，如何在 Agent 启动时自动加载持久化记忆并注入到上下文中。
**核心关切**：
- 关切 1：记忆的加载时机——在 Agent 执行前加载记忆内容，但 checkpoint 恢复时应跳过重复加载
- 关切 2：记忆的自主更新——Agent 应能通过现有工具（如 edit_file）自主决定何时更新记忆，而不是依赖单独的 API
**deepagents 的解法**：`MemoryMiddleware` 的 `before_agent` 钩子在启动时从配置的 source 路径加载 AGENTS.md 文件，注入到系统提示词的 `<agent_memory>` 标签；系统提示词中的 `<memory_guidelines>` 指导 Agent 自主更新记忆。
**源码证据**：`deepagents/middleware/memory.py:253-254`（lazy loading）、`deepagents/middleware/memory.py:97-155`（memory guidelines 系统提示词）
**来源 Entity**：memory-middleware
**层级**：架构决策

---

## 模型标识符解析

**问题陈述**：构建 AI Agent 框架时，用户可能以多种格式指定模型（已初始化的 BaseChatModel 实例、"openai:gpt-4o"、"openrouter:claude-sonnet-4-20250514"），如何一致地将这些输入统一解析为可用的模型实例。
**核心关切**：
- 关切 1：输入格式的多样性——纯字符串、provider:model 格式、已实例化对象，需要有统一的解析路径
- 关切 2：Provider 特殊需求——不同 provider 有不同的初始化参数（如 OpenAI 的 Responses API、OpenRouter 的归属头），解析时需要处理这些差异
**deepagents 的解法**：`resolve_model()` 函数处理三种输入格式：BaseChatModel 实例直接返回，`openai:` 前缀默认启用 Responses API，其他 `provider:model` 字符串委托给 LangChain 的 `init_chat_model`。
**源码证据**：`deepagents/_models.py:72`（resolve_model 函数）、`deepagents/_models.py:89-92`（BaseChatModel 直通和 OpenAI 特殊处理）
**来源 Entity**：model-resolution
**层级**：技术选型

---

## 技能发现与渐进披露

**问题陈述**：构建 AI Agent 框架时，如何让 Agent 获得丰富的领域能力（代码审查、Web 研究等），同时不因将所有技能内容加载到系统提示词而浪费 token——即实现按需加载。
**核心关切**：
- 关切 1：技能元数据的披露量——系统提示词中应该包含多少技能信息（名称、描述、参数），让 Agent 能判断何时需要哪个技能
- 关切 2：技能来源的优先级——如果多个 source 路径下有同名技能，哪个优先（用户级覆盖项目级，项目级覆盖框架默认）
**deepagents 的解法**：`SkillsMiddleware` 扫描 backend 中 source 路径下的 SKILL.md 文件，解析 YAML frontmatter 获取元数据，在系统提示词中只注入元数据（渐进披露），Agent 需要时通过 `read_file` 读取完整内容；同名技能后加载的覆盖先加载的。
**源码证据**：`deepagents/middleware/skills.py:560-599`（渐进披露模式）、`deepagents/middleware/skills.py:755-758`（多源合并与优先级）
**来源 Entity**：skills-middleware
**层级**：架构决策

---

## 短暂状态内文件存储

**问题陈述**：构建 AI Agent 框架时，Agent 需要文件存储能力，但某些场景下不希望引入外部存储依赖——如何利用 LangGraph 自身的 state checkpoint 机制提供轻量级、线程内持久化的文件存储。
**核心关切**：
- 关切 1：存储生命周期的界定——文件在对话线程内持久化，但不跨线程，这与 checkpoint 语义一致
- 关切 2：零依赖——不引入外部文件系统、数据库或网络存储，完全基于 LangGraph 内置机制
**deepagents 的解法**：`StateBackend` 实现 `BackendProtocol`，通过 `CONFIG_KEY_READ`/`CONFIG_KEY_SEND` 直接读写 LangGraph state channel，文件数据存储为 state 的一部分，随 checkpoint 一起持久化。
**源码证据**：`deepagents/backends/state.py:38`（核心类定义）、`deepagents/backends/state.py:104-141`（直接 state 通道读写）
**来源 Entity**：state-backend
**层级**：技术选型

---

## 同步子代理任务委派

**问题陈述**：构建 AI Agent 框架时，如何让主 Agent 将复杂子任务委派给隔离的短期子 Agent 执行，子 Agent 完成后返回聚合结果，从而减少主 Agent 的上下文压力和 token 消耗。
**核心关切**：
- 关切 1：子代理的隔离边界——哪些状态应该传递给子代理，哪些应该保留在主代理？继承过少影响子代理能力，继承过多造成状态泄漏和 token 浪费
- 关切 2：子代理规范的声明方式——用户如何以声明式配置（而非编程）定义子代理的模型、工具、中间件、中断策略
**deepagents 的解法**：`SubAgentMiddleware` 注入 `task` 工具，支持三种子代理形态（声明式 SubAgent + 预编译 CompiledSubAgent + 远程 AsyncSubAgent）；messages/todos/structured_response/skills_metadata/memory_contents 被排除不传递给子代理。
**源码证据**：`deepagents/middleware/subagents.py:392`（核心类定义）、`deepagents/middleware/subagents.py:126`（状态键过滤排除列表）
**来源 Entity**：subagent-middleware
**层级**：架构决策

---

## 对话历史压缩

**问题陈述**：构建 AI Agent 框架时，Agent 的长时间对话会超出模型输入 token 限制，如何在保留关键上下文信息的同时，压缩历史消息以适应上下文窗口。
**核心关切**：
- 关切 1：触发时机的选择——基于 token 数量、上下文窗口占比、消息数量？能否组合多个触发条件？
- 关切 2：压缩策略与完整历史的平衡——摘要保留关键信息，但完整对话历史不能丢失，需要持久化以便事后审计或恢复
**deepagents 的解法**：`SummarizationMiddleware` 支持 tokens/fraction/messages 三种可组合触发策略，超出阈值时调用 LLM 生成摘要替换旧消息，完整历史 append 到 backend 上的对话历史文件；支持 ContextOverflowError 自动回退。
**源码证据**：`deepagents/middleware/summarization.py:217-219`（三种触发策略）、`deepagents/middleware/summarization.py:735-807`（对话历史持久化）
**来源 Entity**：summarization-middleware
**层级**：架构决策

---

## 悬空工具调用修复

**问题陈述**：构建 AI Agent 框架时，Agent 可能被中断（人工审批拒绝、超时、并发冲突），导致消息历史中出现 AIMessage 有 tool_calls 但无对应 ToolMessage 响应的不一致状态——如何自动检测并修复。
**核心关切**：
- 关切 1：修复的时机——在每次 Agent 执行前扫描消息历史，确保 LLM 不会看到不一致的工具调用历史
- 关切 2：修复策略——是注入取消通知还是重试工具调用？取消通知如何表述让 LLM 理解并优雅处理
**deepagents 的解法**：`PatchToolCallsMiddleware` 的 `before_agent` 钩子在每次 Agent 执行前扫描消息历史，对每个悬空 tool_call 注入内容为"另一条消息在其完成前到达"的取消 ToolMessage，通过 LangGraph 的 Overwrite 替换整个消息列表。
**源码证据**：`deepagents/middleware/patch_tool_calls.py:11`（核心类定义）、`deepagents/middleware/patch_tool_calls.py:26-43`（悬空检测与取消注入）
**来源 Entity**：tool-call-patching
**层级**：技术选型

---

## 聚合检查补充：生命周期钩子拦截

**问题陈述**：构建 AI Agent 框架时，中间件需要在 Agent 生命周期的特定节点（执行前、每次模型调用前、工具调用后等）插入自定义逻辑——如何设计一组标准的生命周期钩子让中间件以声明式方式注册拦截逻辑。
**核心关切**：
- 关切 1：钩子的粒度——需要提供哪些钩子？before_agent（每次执行前）和 wrap_model_call（每次 LLM 调用前）是否足够，还是需要更细粒度的钩子（如 after_tool_call、before_state_update）？
- 关切 2：钩子的执行顺序——多个中间件注册了同一个钩子时，执行顺序如何确定？是否与中间件堆栈顺序一致？
**deepagents 的解法**：通过 AgentMiddleware 基类提供 `before_agent` 和 `wrap_model_call` 两个标准生命周期钩子，中间件在子类中重写这些方法；MemoryMiddleware、PatchToolCallsMiddleware 使用 `before_agent`，SubAgentMiddleware 使用 `wrap_model_call`，执行顺序由中间件堆栈顺序决定。
**源码证据**：
- memory-middleware: `deepagents/middleware/memory.py:253-254`（before_agent 懒加载）
- subagent-middleware: `deepagents/middleware/subagents.py:520-529`（wrap_model_call 系统提示词注入）
- tool-call-patching: `deepagents/middleware/patch_tool_calls.py:11-44`（before_agent 悬空检测）
**来源 Entity**：memory-middleware, subagent-middleware, tool-call-patching（跨 entity 共用机制）
**层级**：架构决策

---

## 聚合检查补充：系统提示词组装

**问题陈述**：构建 AI Agent 框架时，多个中间件各自需要向系统提示词贡献内容（记忆的 `<agent_memory>`、技能的元数据列表、文件系统的使用说明、子代理的任务指令）——如何将这些来自不同来源的内容组装成一个结构良好的最终系统提示词。
**核心关切**：
- 关切 1：组装策略——各中间件的内容应该按什么顺序拼接？是简单追加还是按章节组织？是否需要模板引擎？
- 关切 2：注入时机——系统提示词是在 Agent 图构建时静态组装，还是在每次 LLM 调用前动态注入？不同策略影响缓存效率和内容新鲜度
**deepagents 的解法**：基础提示词（`BASE_AGENT_PROMPT`）固定写入，用户自定义提示词前置；各中间件通过 `append_to_system_message` 工具函数在运行时向系统消息追加内容；MemoryMiddleware 在 `before_agent` 中注入 `<agent_memory>`，SkillsMiddleware 注入技能列表，FilesystemMiddleware 注入使用说明，AsyncSubAgentMiddleware 注入异步规则。
**源码证据**：
- agent-graph-assembly: `deepagents/graph.py:398-404`（系统提示词组合）
- memory-middleware: `deepagents/middleware/memory.py:97-155`（memory guidelines 注入）
- skills-middleware: `deepagents/middleware/skills.py:560-599`（技能元数据注入）
- subagent-middleware: `deepagents/middleware/subagents.py:520-529`（任务说明注入）
**来源 Entity**：agent-graph-assembly, memory-middleware, skills-middleware, subagent-middleware（跨 entity 共用机制）
**层级**：架构决策

---

## 附注

### 1. 跳过的 Entity 及理由

无跳过。所有 12 个 entity 均产出了至少一条问题空间条目。

### 2. 拆分 entity 及理由

**filesystem-middleware 拆分为两条**：
- "文件系统工具提供"（主问题）和"工具结果溢出管理"（机制转化）
- 拆分理由：工具结果溢出管理不依赖于文件系统——任何可能产生大输出的工具（web fetch、数据库查询、日志检索）都面临同样问题。文件系统只是一种溢出缓冲方案（写入文件后返回截断预览），其他方案包括流式传输、分页、摘要压缩。将两者合并会导致 Framework Builder 在"如何管理大工具结果"这一独立设计维度上失去决策空间。应用互不包含测试通过。

### 3. 聚合检查结果

对全部 12 个 entity 正文的技术机制进行了跨 entity 共用扫描，发现以下共用机制：

| 机制 | 使用的 Entity | 是否补充条目 | 理由 |
|------|--------------|-------------|------|
| `before_agent` 生命周期钩子 | memory-middleware, tool-call-patching | 见下 | 与 wrap_model_call 合并为"生命周期钩子拦截" |
| `wrap_model_call` 生命周期钩子 | subagent-middleware | 见下 | 与 before_agent 合并为"生命周期钩子拦截" |
| 系统提示词注入 | agent-graph-assembly, memory-middleware, skills-middleware, subagent-middleware, filesystem-middleware, async-subagent-middleware | **是** — 补充"系统提示词组装" | 6 个 entity 共用，无现有条目覆盖 |
| 生命周期钩子（总） | memory-middleware, subagent-middleware, tool-call-patching | **是** — 补充"生命周期钩子拦截" | 3 个 entity 共用，无现有条目覆盖 |
| 懒加载 + checkpoint 恢复 | memory-middleware, skills-middleware | 否 | 这是优化实现细节，不构成 Framework Builder 需要独立决策的设计维度 |
| PrivateStateAttr 隐私状态 | memory-middleware, skills-middleware | 否 | 仅 2 个 entity 使用，且是 LangGraph 平台特性，不属于框架设计层面的通用问题 |

**补充了 2 条**：生命周期钩子拦截、系统提示词组装。

### 4. 与 v2（含 hook 示例版本）的对比

**v2 背景**：上一版提示词包含了一个钩子机制的具体示例（"例如，一个中间件...通过生命周期钩子介入..."），在给模型的指导中暗示了生命周期钩子是一个值得关注的维度。

**v3 差异**：

1. **发现路径不同**：
   - v2：模型被提示词中的 hook 示例引导，在逐 entity 映射时就会留意到生命周期钩子，可能直接在 `before_agent` 相关的 entity 上产出独立条目
   - v3：模型在逐 entity 映射阶段完全不知道"钩子是一个特殊维度"。memory-middleware 被映射为"跨会话记忆加载"，tool-call-patching 被映射为"悬空工具调用修复"，subagent-middleware 被映射为"同步子代理任务委派"——各自的条目均聚焦于各自的业务问题，不涉及钩子机制本身。钩子机制完全是在聚合检查阶段被发现的——当回头扫描所有 entity 的技术机制列表时，发现 `before_agent` 在 3 个 entity 中出现，`wrap_model_call` 在 1 个 entity 中出现，合并为一个跨 entity 的共用机制

2. **条目总数对比**：
   - v2：未知（需要对比）
   - v3：15 条（12 个 primary + 1 个 filesystem 拆分 + 2 个聚合补充）

3. **关键验证**：去掉指向性示例后，模型**仍然自主发现了生命周期钩子拦截**这一跨 entity 的设计维度。但发现的时机不同——不是在逐 entity 映射时（那会带有"因为提示词暗示了这个方向"的嫌疑），而是在聚合检查阶段（纯数据驱动，因为 3 个 entity 的正文中明确提到了 `before_agent`/`wrap_model_call`）。这证明：
   - 地面真值（subagent-middleware、memory-middleware、tool-call-patching 共享生命周期钩子）在 entity 正文中有足够的文本证据支撑
   - 聚合检查步骤（回头看所有 entity 的技术机制 → 标注重合度 → 补充缺失条目）足以替代提示词中的引导性示例
   - v3 的发现比 v2 更可辩护——不是"因为提示词暗示了方向"，而是"因为数据支撑了这个结论"

4. **系统提示词组装**是 v3 独立发现的一个意外收获。v2 中如果提示词没有暗示，可能不会出现这个条目。v3 中它来自聚合检查：6 个 entity 的正文都描述了各自向系统提示词注入内容的方式，这是明确的跨 entity 共用机制。
