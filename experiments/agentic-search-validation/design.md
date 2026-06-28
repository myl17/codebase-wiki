# Agentic Search 验证实验：Step 3 问题空间匹配

## 问题

Step 3 需要将新 entity 的问题空间匹配到已有知识（Concept 页 + C 类 seeds）。核心验证：
**agentic search（模型自己 grep + read 检索）能否可靠地找到正确匹配？**

---

## 实验语料

### 语料清单

| 文件 | 条目数 | 类型 |
|------|--------|------|
| `seeds/nanobot-problem-map.md` | 16 | 问题空间条目（含跳过的 entity 列表） |
| `seeds/hermes-agent-problem-map.md` | 14 | 问题空间条目（8 架构决策 + 6 技术选型） |
| `seeds/openclaw-problem-map.md` | 22 | 问题空间条目（架构决策 + 技术选型混合） |
| `wiki/concepts/*.md` | 15 | Concept 页（每个有 frontmatter `problem` + 核心问题节 + 对比表） |
| `experiments/entity-concept-extraction/design-seeds.md` | 58 | 实验基线种子（4 字段表格格式） |

### Ground Truth 矩阵

以下是从语料中提取的所有匹配关系，用于和 agentic search 结果对比。按 `problem` 字段对齐。

| # | 问题空间 | Concept（如已升级） | C 类匹配（如未升级） | 涉及仓库 | 类别 |
|---|---------|-------------------|-------------------|---------|------|
| GT01 | 如何编排 Agent 的主循环 | agent-loop-orchestration | — | n, h, o | B→Concept |
| GT02 | 如何用统一接口抽象异构消息平台 | channel-abstraction-pattern | — | n, h, o | B→Concept |
| GT03 | 如何抽象多个 LLM Provider 的 API 差异 | provider-abstraction-pattern | — | n, h, o | B→Concept |
| GT04 | 如何管理 Agent 工具的注册/发现/策略过滤 | tool-lifecycle-management | — | n, h, o | B→Concept |
| GT05 | 如何管理子 Agent 的孵化/执行/故障恢复 | subagent-orchestration | — | n, h, o | B→Concept |
| GT06 | 如何组装 Agent 的系统提示词（分层注入） | system-prompt-assembly | — | n, h | B→Concept |
| GT07 | 如何让 Agent 定时自主执行任务 | autonomous-scheduling | — | n, h, o | B→Concept |
| GT08 | 如何构建多层安全防御（命令/内容/网络/访问控制） | security-architecture | — | n, h, o | B→Concept |
| GT09 | 如何管理会话的身份/持久化/生命周期 | session-lifecycle-management | — | n, h, o | B→Concept |
| GT10 | 如何管理 Agent 长期记忆（持久化+演化） | memory-management-architecture | — | n, h | B→Concept |
| GT11 | 如何在上下文窗口有限时自动压缩对话历史 | context-compression-strategy | — | n, h, o | B→Concept |
| GT12 | 如何管理 Agent 的可插拔能力模块（Skills） | skills-extension-mechanism | — | n, h, o | B→Concept |
| GT13 | 如何为工具执行提供可插拔隔离环境（Docker/SSH） | execution-isolation | — | h, o | B→Concept |
| GT14 | 如何在高风险操作前插入人类审批 | execution-approval-pattern | — | h, o | B→Concept |
| GT15 | 如何管理配置（模块化/多环境隔离/敏感值注入） | configuration-management | — | h, o | B→Concept |
| GT16 | 如何解耦 Channel 和 Agent Core 的消息传递 | — | nanobot-problem-map "如何解耦 Channel 和 Agent Core 的消息传递" | n | C（+子维度） |
| GT17 | 如何在 Agent 对话流中嵌入内置命令 | — | nanobot-problem-map "如何在 Agent 对话流中嵌入内置命令" | n | C |
| GT18 | 如何让 Agent 具备自主唤醒能力（heartbeat） | — | nanobot-problem-map "如何让 Agent 具备自主唤醒能力" | n | C |
| GT19 | 事件驱动的扩展点（hooks 子系统） | — | openclaw-problem-map "事件驱动的扩展点"（+ agent-loop-orchestration 子维度） | o | D（子维度） |
| GT20 | 中央控制平面（单端口 HTTP+WS+API） | — | openclaw-problem-map "中央控制平面" | o | C |
| GT21 | 插件公共契约（core-plugin SDK 边界） | — | openclaw-problem-map "插件公共契约" | o | C |
| GT22 | 插件全生命周期管理 | — | openclaw-problem-map "插件全生命周期" | o | C |
| GT23 | 消息路由（渠道→agent 映射优先级） | — | openclaw-problem-map "消息路由" | o | C |
| GT24 | 媒体管道（图片/音频/视频安全处理） | — | openclaw-problem-map "媒体管道" | o | C |

---

## Phase 1: 检索有效性（10 个查询，盲测）

### 查询构造原则

- 每个查询格式与 problem-map 条目一致：`## <问题标题>` + `**问题陈述**：` + `**核心关切**：`
- 查询模拟"一个新仓库的 entity 的问题空间条目"——不是已有仓库的副本
- 覆盖不同的匹配类型：A（追加 Concept）、B（新建 Concept）、C（待观察）、D（演化信号）、无匹配

---

### Q1: 精确语义匹配 —— B 类（Concept 已存在）

**查询文本**：
```
## 如何在 Agent 框架中设计主循环来协调消息输入、模型推理和工具调用

**问题陈述**：所有 AI Agent 框架都需要一个核心执行循环——从消息输入开始，调用 LLM，解析响应，如果有工具调用就执行工具再把结果送给 LLM，直到 LLM 返回最终文本响应。这个循环的设计决定框架的可靠性、可扩展性和可调试性。
**核心关切**：
- 关切 1：如何处理 LLM 返回空响应、连接中断、超时等异常
- 关切 2：多个用户同时发消息时，如何保证同会话的顺序同时允许跨会话并发
- 关切 3：工具调用的结果如何格式化回传给 LLM，多轮工具调用如何管理上下文增长
```

**Ground Truth**：
- 正确答案：`agent-loop-orchestration`（Concept）+ `seeds/nanobot-problem-map.md` "如何编排 Agent 的主循环" + `seeds/hermes-agent-problem-map.md` "如何编排 Agent 的主循环" + `seeds/openclaw-problem-map.md` "Agent 执行循环"
- 匹配类型：A（追加到已有 Concept）
- 匹配理由：问题空间完全重合——都是在讨论 agent 主循环的异常处理、并发模型和工具调用管理

---

### Q2: 语义相近但措辞不同 —— A 类（追加到已有 Concept）

**查询文本**：
```
## 如何把不同聊天 App 的 API 差异屏蔽掉，让 Agent 只看到统一的消息格式

**问题陈述**：做多平台 Agent 的时候，Telegram 发消息是一套 API，Discord 又是另一套，Slack 更不一样。框架需要在中间加一层抽象，把各平台的原始消息转成统一格式，把统一格式的回复转回各平台的原生调用。
**核心关切**：
- 关切 1：这个抽象层应该多薄——只定义 send/receive，还是把 edit、react、thread 这些都包进来
- 关切 2：第三方想加一个新的聊天平台，需要改框架代码吗
```

**Ground Truth**：
- 正确答案：`channel-abstraction-pattern`（Concept）+ 三个 problem-map 的 Channel 条目
- 匹配类型：A（追加到已有 Concept）
- 匹配理由：口语化、措辞不同（"聊天 App""屏蔽 API 差异" vs "抽象异构消息平台"），但核心问题完全一致

---

### Q3: 粒度不匹配 —— D 类（子维度）

**查询文本**：
```
## 如何在 Agent 生命周期的关键节点（启动、收到消息、会话切换）提供可扩展的钩子机制

**问题陈述**：Agent 框架的用户和第三方开发者需要在 Agent 运行的不同阶段插入自定义逻辑——比如在收到消息时做内容过滤、在 Agent 启动时初始化外部服务、在会话创建时记录审计日志。框架需要提供一套钩子系统，让用户注册回调函数并在特定事件触发时自动执行。
**核心关切**：
- 关切 1：钩子函数的来源如何管理——内置的、用户写的、社区安装的，它们的信任级别不同，应区别对待
- 关切 2：一个钩子执行失败了，是否应该阻止其他钩子继续执行（故障隔离）
- 关切 3：钩子的触发条件如何设计——是精确事件匹配，还是支持通配符
```

**Ground Truth**：
- 正确答案：`agent-loop-orchestration` 子维度 "Agent 生命周期的可扩展钩子系统"（已有） + `seeds/openclaw-problem-map.md` "事件驱动的扩展点"
- 匹配类型：D（粒度不匹配——hooks 是一个子维度，当前只有 openclaw 将其作为一等公民子系统）
- 匹配理由：hooks 是对 agent 主循环的扩展机制，是 agent-loop-orchestration 的子维度。不应独立建 Concept（暂不满足准则①多方案对比），但可以追加子维度观察

---

### Q4: 仅单仓库覆盖 —— C 类（待观察）

**查询文本**：
```
## 如何处理用户输入的控制命令——哪些在进入 LLM 前拦截掉，哪些交给 LLM 自行理解

**问题陈述**：Agent 框架通常有内置命令如 /stop、/status、/new——有些命令需要即时响应（/stop 必须立刻停止，不能等 LLM 处理完），有些命令在 LLM 有上下文时处理效果更好（/status 可以结合当前对话状态回答）。框架需要决定命令的分级策略和路由机制。
**核心关切**：
- 关切 1：紧急命令（如停止）的响应延迟——不能卡在 LLM 的推理队列里
- 关切 2：频道插件是否可以注册自己的命令，如何与内置命令做命名空间隔离
```

**Ground Truth**：
- 正确答案：`seeds/nanobot-problem-map.md` "如何在 Agent 对话流中嵌入内置命令"
- 匹配类型：C（仅 nanobot 有此设计，但问题空间是任何多命令 Agent 框架都要面对的，新仓库加入后可能形成对比）
- 匹配理由：当前只有 nanobot 将命令路由作为独立 entity。新仓库如果也有类似设计，应标记为 C 类观察

---

### Q5: 无匹配 —— C 类（新种子）

**查询文本**：
```
## 如何设计一个 A/B 实验框架来对比不同 system prompt 对 Agent 行为的影响

**问题陈述**：Agent 框架的用户在调优 system prompt 时完全靠经验和手动测试——改了 prompt、跑几条对话、感觉效果好不好。需要一个系统化的对比机制：定义指标（完成任务的比例、用户满意度）、分流用户到不同的 prompt 变体、自动收集和报告结果。
**核心关切**：
- 关切 1：实验指标的定义——如何衡量"Agent 表现好不好"
- 关切 2：分流策略——同一用户应该固定在一个变体里还是每次随机
- 关切 3：数据收集——token 消耗、成功率、用户反馈如何汇总
```

**Ground Truth**：
- 正确答案：无（语料中不存在 A/B 实验相关的问题空间条目）
- 匹配类型：C（新种子——是一个有意义的框架设计问题，但当前没有仓库覆盖）
- 匹配理由：所有 22 条 Ground Truth 均不匹配

---

### Q6: 反向措辞 —— A 类（追加到已有 Concept）

**查询文本**：
```
## 为什么不应该为每个 LLM 提供商写独立的调用代码——论统一 Provider 抽象层的必要性

**问题陈述**：如果为 Anthropic 写一套调用逻辑，为 OpenAI 写另一套，为 Bedrock 再写一套，框架的维护成本会随着 provider 数量线性增长。每种 API 的消息格式不同、流式协议不同、错误码不同——把它们全部分开处理会让代码库充满重复的 retry logic、error mapping 和 format conversion。正确的做法是定义一个统一的 Provider 接口，让所有 provider 适配到同一个抽象。
**核心关切**：
- 关切 1：统一抽象会不会损失 provider 特有的能力（比如 Anthropic 的 thinking blocks、OpenAI 的 structured outputs）
- 关切 2：认证方式的多样性——API key、OAuth、AWS IAM——如何在统一接口下管理
- 关切 3：一个 provider 挂了怎么自动切到另一个
```

**Ground Truth**：
- 正确答案：`provider-abstraction-pattern`（Concept）+ 三个 problem-map 的 Provider 条目
- 匹配类型：A（追加到已有 Concept）
- 匹配理由：反向措辞（"为什么不应该分开写"→"如何统一抽象"），但核心问题完全一致

---

### Q7: 跨文件模糊措辞 —— 多候选

**查询文本**：
```
## 如何在 Agent 内存和存储方面做架构决策

**问题陈述**：Agent 框架需要保存用户的对话历史和长期记忆。这就涉及几个层面的决策：用什么格式存（JSON、SQLite、纯文本）、要不要做压缩、要不要让 LLM 参与整理记忆。
**核心关切**：
- 关切 1：存储格式——简单文件 vs 数据库，各有什么场景适用
- 关切 2：旧消息的自动压缩——怎么在 token 预算不够的时候不丢关键信息
```

**Ground Truth**：
- 正确答案：两个候选——
  - (a) `memory-management-architecture`（Concept）— 长期记忆架构，匹配"长期记忆"、"LLM 参与整理"
  - (b) `context-compression-strategy`（Concept）— 上下文压缩，匹配"旧消息自动压缩"、"token 预算"
- 匹配类型：多候选——需要模型判断哪个更匹配或两者都相关
- 匹配理由：查询同时触达了两个 Concept 的问题空间，测试模型能否识别多维度匹配并正确排序

---

### Q8: 精确技术匹配 —— B 类（本应升级但仅有单仓库覆盖）

**查询文本**：
```
## 如何实现一个单端口网关，同时承载 HTTP REST API、WebSocket 双向通道和 OpenAI 兼容的 /v1/chat/completions 端点

**问题陈述**：构建多渠道 AI 助手的框架需要一个中央网关来统一处理所有外部通信——HTTP REST 给 webhook 和管理面板、WebSocket 给实时客户端、OpenAI 兼容端点让现有工具和 SDK 可以无缝对接。问题在于如何在一个端口上优雅地分发这三种不同协议。
**核心关切**：
- 关切 1：协议分发——如何根据请求特征将流量路由到正确的处理器（HTTP headers、path、upgrade 请求）
- 关切 2：JSON 协议版本化——如何保证新旧客户端的兼容性
- 关切 3：连接的认证和速率限制如何统一管理
```

**Ground Truth**：
- 正确答案：`seeds/openclaw-problem-map.md` "中央控制平面：如何在单进程中统一 HTTP REST、WebSocket 双向通信和 OpenAI 兼容 API？"
- 匹配类型：C（仅 openclaw 有此设计，但问题空间对任何需要暴露网络接口的 Agent 框架都是通用的）
- 匹配理由：精确匹配 openclaw 的 gateway entity

---

### Q9: 子议题匹配父 Concept —— 粒度判断

**查询文本**：
```
## 如何让多个子 Agent worker 并行处理不同的子任务，然后汇总结果

**问题陈述**：当 Agent 面对一个复杂任务（比如"比较 React、Vue、Angular 三个框架的性能"），最自然的做法是同时启动三个子 Agent 各自研究一个框架，然后汇总。问题在于子 Agent 的并发管理——是线程池、进程池还是异步协程，以及子 Agent 失败时如何优雅降级。
**核心关切**：
- 关切 1：子 Agent 的工具限制——不应该允许子 Agent 再创建子 Agent（防止递归爆炸）
- 关切 2：父 Agent 如何知道子 Agent 完成了——轮询、回调还是消息通知
- 关切 3：多个子 Agent 的总 token 消耗如何控制
```

**Ground Truth**：
- 正确答案：`subagent-orchestration`（Concept）+ 三个 problem-map 的 Subagent 条目
- 匹配类型：A（追加到已有 Concept）
- 匹配理由：问题空间完全在 subagent-orchestration 的覆盖范围内。虽然是"子议题"视角（并行 worker），但核心关切与已有 Concept 一致

---

### Q10: 实验设计种子匹配 —— 跨格式检索

**查询文本**：
```
## 如何组织所有子系统的实例化和装配，让系统结构一目了然

**问题陈述**：Agent 框架由几十个子系统组成——channel、tool、memory、session、provider、sandbox——每个都是独立的模块。问题是这些模块的实例化和连接方式对代码可读性和可维护性影响巨大。是让一个上帝对象在构造函数里 new 所有东西，还是用依赖注入容器，还是让插件自己注册？
**核心关切**：
- 关切 1：依赖的声明和解析——A 需要 B，B 需要 C——这个依赖链如何管理
- 关切 2：启动顺序——某些子系统必须在其他子系统之前初始化
- 关切 3：测试便利性——能否轻松替换某个子系统为 mock
```

**Ground Truth**：
- 正确答案：`experiments/entity-concept-extraction/design-seeds.md` 问题 "如何组织所有子系统的实例化和连线以最大化可发现性？"
- 匹配类型：B（跨仓库种子——此问题在 design-seeds 中有记录，但在当前 wiki 中未独立建 Concept）
- 匹配理由：测试 agentic search 能否搜到 experiments 目录下的历史基线（格式不同——design-seeds 是表格格式，不是 problem-map 格式）

---

## Phase 2: 词汇鲁棒性（5 个变体）

对 Phase 1 的 3 个查询（Q1、Q2、Q6）做词汇改写，加 2 个额外查询。每个变体和原文语义一致但用词完全不同。

### W1: Q1 术语替换（英文专业术语 → 中文通用表达）

**查询文本**：
```
## AI 机器人的大脑中枢怎么设计：从收消息到调模型到回结果的一条流水线

**问题陈述**：搞 AI 机器人的时候，最核心的就是那条"处理链"——用户说了句话，机器人要先理解、可能需要查资料或执行操作、然后把结果告诉用户。这条链怎么组织直接影响机器人的稳定性和响应速度。
**核心关切**：
- 关切 1：模型抽风了怎么办——如果调用大模型的时候挂了，整个机器人就卡住了吗
- 关切 2：好几个人同时跟机器人聊天，消息处理顺序会不会乱
- 关切 3：怎么让模型一步一步思考，如果有工具要调用就自动调
```

**Ground Truth**：同 Q1 — `agent-loop-orchestration`

---

### W2: Q2 反向描述（解决方案视角 → 问题视角）

**查询文本**：
```
## 对接 Telegram、Discord、微信的成本太高了——每个平台都写一遍同样的逻辑是不是浪费

**问题陈述**：团队在做多平台机器人时发现，Telegram 接入写了几千行，Discord 接入又写了几千行，微信企业号再来几千行，里面大量的逻辑是重复的——消息格式转换、流式输出控制、错误重试、用户身份识别。明明做的是同一件事，为什么每加一个平台都要从头开始？
**核心关切**：
- 关切 1：能不能只写一次核心逻辑，然后每个平台只写一个薄薄的"翻译层"
- 关切 2：但这个翻译层太薄也不行——Telegram 有按钮、Discord 有嵌入式卡片，这些高级特性丢了用户体验就差了
```

**Ground Truth**：同 Q2 — `channel-abstraction-pattern`

---

### W3: Q6 口语化（论证语气 → 用户自然提问）

**查询文本**：
```
## 我们接了好几个模型厂商的 API，每次加新的都要重新写一套调用代码，有没有更好的办法

**问题陈述**：最开始只用了 OpenAI，后来加了 Anthropic Claude，最近团队又要求支持 AWS Bedrock。每个厂商的 API 格式都不一样——消息结构不同、流式协议不同、错误返回格式也不同。现在代码里三个 xxx_adapter.py 文件，大部分逻辑是重复的（retry、rate limit 处理、连接池管理），但写法完全不一样。能不能抽象出一层，所有厂商都适配到这层上面？
**核心关切**：
- 关切 1：不同厂商的消息格式怎么统一——Anthropic 有 thinking blocks、OpenAI 有 structured outputs
- 关切 2：认证方式——API key、OAuth、AWS IAM，能不能用一种配置格式管理
```

**Ground Truth**：同 Q6 — `provider-abstraction-pattern`

---

### W4: 新增 —— 极其简短模糊的查询

**查询文本**：
```
## Agent 的记忆功能怎么实现

**问题陈述**：用户跟 Agent 聊天，Agent 要记住之前聊过什么，下次用户说"上次那个事"的时候 Agent 能接上。这个记忆功能具体怎么实现？
**核心关切**：
- 关切 1：存哪里——文件？数据库？云端？
- 关切 2：怎么压缩——对话很长的时候不可能全部留着
```

**Ground Truth**：
- 正确答案：`memory-management-architecture`（Concept）为主，`context-compression-strategy` 为副
- 匹配类型：P1 候选 `memory-management-architecture`，P2 候选 `context-compression-strategy`
- 测试点：面对极度模糊的查询，模型能否找到正确的多个候选并合理排序

---

### W5: 新增 —— 中英混合查询

**查询文本**：
```
## 如何设计 agent 的 tool execution sandbox，支持 docker backend 和 SSH backend 的可插拔切换

**问题陈述**：Agent 执行用户的 shell 命令和 Python 脚本时，直接在主进程里跑太危险了。需要一个 sandbox——可以是本地 Docker 容器，也可以是远程 SSH 机器。框架应该提供一个统一的接口，让 agent 工具不感知后端差异。
**核心关切**：
- 关切 1：filesystem bridge——agent 读写的文件路径在 host 和 container 之间怎么映射
- 关切 2：sandbox 的生命周期——每个 session 一个容器还是共享？空闲多久回收
```

**Ground Truth**：
- 正确答案：`execution-isolation`（Concept）
- 匹配类型：A（中英混合措辞不影响语义匹配）

---

## Phase 3: 规模退化

略（Phase 1 通过后再设计合成数据生成脚本）。

---

## Phase 4: 边界情况（5 个查询）

### E1: 近重复判断

**查询文本**：
```
## 如何让 Agent 按照预设的时间表自动执行任务

**问题陈述**：用户可能想设置"每天早上 8 点给我发天气预报"或"每小时检查一次服务器状态"。Agent 框架需要一个定时调度器，在指定时间自动触发 Agent 执行预定任务。
**核心关切**：
- 关切 1：调度表达——cron 表达式 vs 自然语言（"每天早上"）
- 关切 2：多实例部署时防止同一任务被重复执行
```

**Ground Truth**：
- 正确答案：`autonomous-scheduling`（Concept）— top match
- **近重复项**：`seeds/nanobot-problem-map.md` "如何为 Agent 提供定时任务调度" + `seeds/openclaw-problem-map.md` "定时任务调度" — 两者描述几乎相同的核心问题，措辞略有差异
- 测试点：模型应识别所有三个条目指向同一个问题空间（autonomous scheduling），将它们合并为一个匹配组，而不是分别列出

---

### E2: 跨维度词汇陷阱（都提到"消息队列"但问题不同）

**查询文本**：
```
## 如何为 Agent 框架设计一个消息队列来缓存待处理的消息

**问题陈述**：当 Agent 同时收到大量消息时，需要一个消息队列来缓冲——先存起来，然后按顺序处理。这个队列应该持久化吗？如果 Agent 重启，队列里的消息会不会丢？
**核心关切**：
- 关切 1：持久化——Agent 进程重启后未处理的消息能否恢复
- 关切 2：顺序保证——如何确保同一会话的消息按发送顺序处理
```

**Ground Truth**：
- **NOT** matching `seeds/nanobot-problem-map.md` "如何解耦 Channel 和 Agent Core 的消息传递"（虽然也涉及"消息队列"，但那是 channel→agent 的传输解耦，使用 asyncio.Queue）
- 正确答案：查询涉及的是**消息持久化存储队列**（类似任务队列的语义），在现有语料中无精确匹配
- 匹配类型：无匹配 / C 类（新种子）
- 测试点：模型不应被"消息队列"这个词汇误导到 message-bus 条目——message-bus 是 channel-agent 传输解耦，这是存储缓存

---

### E3: 粒度不匹配（子议题需要识别为已作为子维度记录）

**查询文本**：
```
## 如何在 Agent 发送消息前对流式输出的 delta 进行合并优化

**问题陈述**：LLM 的流式输出会产生大量小 delta——每几个 token 就生成一个 delta chunk。如果把这些 delta 逐条发送到 Telegram API，会因为速率限制被封。需要在发送前对连续的 delta 进行合并（coalesce），减少 API 调用次数。
**核心关切**：
- 关切 1：合并的粒度——是固定时间窗口还是固定 token 数量阈值
- 关切 2：合并对用户体验的影响——会不会让用户觉得"打字"变卡了
```

**Ground Truth**：
- 正确答案：这是一个**实现细节级别的问题**（stream delta coalescing），不是一个独立的问题空间。它属于 `channel-abstraction-pattern` 概念下的实现细节（nanobot 的 `_coalesce_stream_deltas()`、hermes-agent 的 GatewayStreamConsumer）
- 匹配类型：不应独立匹配——应识别为 channel-abstraction-pattern 的**子实现细节**，不满足问题空间提取条件
- 测试点：模型能否识别"这不是一个独立的问题空间"而不是强行匹配到某个已有条目

---

### E4: 完全无匹配

**查询文本**：
```
## 如何为 Agent 框架设计一个内置的 prompt 版本管理系统

**问题陈述**：Agent 的系统提示词经常需要调整——改了一句话想看看效果，过几天觉得不好又想回滚。一个 prompt 版本管理系统应该像 git 一样：记录每次修改的 diff、支持回滚到历史版本、支持分支（experimental vs production prompt）。
**核心关切**：
- 关切 1：diff 粒度——按段落还是按行
- 关切 2：版本切换的时机——立即生效还是下次会话生效
- 关切 3：A/B 测试集成——能否让 10% 的用户用新版 prompt
```

**Ground Truth**：
- 正确答案：无匹配（与 Q5 A/B 实验框架部分重叠但核心问题不同——这是版本管理，不是实验平台）
- 匹配类型：无匹配（无假阳性）
- 测试点：模型应返回空结果而不是强行匹配到无关条目（如 system-prompt-assembly——那是关于 prompt 组装结构，不是版本管理）

---

### E5: 真正的多候选（每个候选匹配角度不同）

**查询文本**：
```
## 如何实现一个安全的命令执行链——在 shell 命令真正运行之前进行多层检查

**问题陈述**：Agent 执行 shell 命令是刚需，但也是最大的安全风险。不能只靠一层检查——需要多层防御：静态模式匹配（禁止 `rm -rf /`）、内容扫描（检测 homograph 攻击）、LLM 智能审批（理解命令意图）、用户最终确认。
**核心关切**：
- 关切 1：多层检查的顺序——是先做快速的静态匹配还是先做昂贵的 LLM 分析
- 关切 2：误报处理——静态规则太严会让正常命令也通不过，太松会漏过危险命令
- 关切 3：审批体验——不能让用户每条命令都点确认，需要分级策略
```

**Ground Truth**：
- 多个正确匹配：
  - (a) `security-architecture`（Concept）— 覆盖多层安全防御体系（含命令执行安全）
  - (b) `execution-approval-pattern`（Concept）— 覆盖人类审批流程
  - (c) `seeds/hermes-agent-problem-map.md` "如何管理工具的安全执行" — 精确匹配"多层检查 + LLM 智能审批 + 用户确认"
- 最佳匹配：(c) hermes-agent 的安全执行条目——查询的核心是"命令执行的安全检查链"，与 hermes 的 `check_all_command_guards()` 流水线精确对应。但 (a) 和 (b) 也有部分覆盖
- 匹配类型：多候选——模型应排序为 (c) > (a) > (b) 并说明每个候选的匹配角度
- 测试点：模型是否给出多个相关候选并解释每个的匹配角度，还是只返回一个

---

## 提示词（给 subagent 的完整指令）

### 系统角色

```
你是一个检索 agent。你的任务是在给定的知识语料中，为一个新的问题空间条目找到最匹配的已有条目。

## 语料位置

语料包含以下目录和文件：

1. `seeds/` 目录：
   - `seeds/nanobot-problem-map.md` — nanobot 的问题空间映射（16 个条目）
   - `seeds/hermes-agent-problem-map.md` — hermes-agent 的问题空间映射（14 个条目）
   - `seeds/openclaw-problem-map.md` — openclaw 的问题空间映射（22 个条目）
   格式：每个条目以 `## <问题标题>` 开头，包含 `**问题陈述**`、`**核心关切**`、`**[仓库] 的解法**` 等字段

2. `wiki/concepts/` 目录 — Concept 页面（15 个）：
   格式：每个文件包含 YAML frontmatter（含 `problem` 字段）和详细的跨仓库对比表

3. `experiments/entity-concept-extraction/design-seeds.md` — 历史基线种子（58 个条目）：
   格式：`## <问题陈述>` + 表格（仓库/选择/简述/溯源）

## 任务

给你一个"查询"——一个来自新代码仓库的问题空间条目（包含问题陈述和核心关切）。你需要在语料中通过 grep + read 等方式检索，找到最相关的已有条目。

## 检索策略

你拥有 grep 和文件读取工具。建议流程：
1. 先用 grep 在以上目录中搜索关键词（尝试多个同义词）
2. 根据 grep 命中结果，读取最可能匹配的文件的相关段落
3. 比较多个候选后，给出最终匹配判断

不要一次性阅读所有文件——用 grep 做初筛。

## 输出格式

严格按照以下格式输出：

```
## 搜索过程

（记录你执行的 grep 命令、读取了哪些文件、几轮搜索）

## 匹配结果

### Top 1: <条目名称或 Concept slug>
- **位置**：<文件路径>
- **匹配类型**：A（追加已有 Concept）/ B（新建 Concept）/ C（待观察种子）/ D（演化信号）/ 无匹配
- **置信度**：高 / 中 / 低
- **匹配理由**：（说明为什么这个问题空间匹配这个已有条目，具体引用已有的问题陈述或关切）

### Top 2: （如有）
...

### Top 3: （如有）
...

## 总结判断

（如果有多个候选，说明它们之间的关系——是同一个问题的不同表述，还是不同的问题空间？最终推荐怎么处理？）
```
```

### 每个查询的具体指令

对 Phase 1 的每个查询（Q1-Q10），额外传给 subagent 的文本：

```
## 查询

<此处填入完整的查询文本>

请在上述语料中检索与此查询最匹配的已有问题空间条目。返回匹配结果。
```

**重要**: 不要给 subagent 任何关于 ground truth 的提示。不要告诉它"这个应该匹配 X"。不要告诉它查询来自哪个仓库。

---

## 执行流程（全部在 subagent 中）

每个查询作为一个**独立 subagent** 执行。Subagent 接收完整的系统角色指令 + 查询文本。执行完毕后返回格式化的匹配结果。

### 批量执行

Phase 1: 10 个 subagent 并行执行（Q1-Q10）
Phase 2: 5 个 subagent 并行执行（W1-W5）
Phase 4: 5 个 subagent 并行执行（E1-E5）

### 结果收集

所有 subagent 返回后，由主上下文（我）做以下评估：
1. 对比每个 subagent 的匹配结果和 Ground Truth
2. 计算 Recall@1、Recall@3、MRR、Precision
3. 分析失败案例：为什么会匹配错误？
4. 计算搜索轮数分布和 token 成本估算
5. 生成汇总报告

---

## 评估标准

### 评分规则

对每个查询的返回结果：

| 结果 | 分数 | 标准 |
|------|------|------|
| Top 1 命中 ground truth | 3 | 第一个候选就是正确的 |
| Top 2-3 命中 ground truth | 2 | 正确匹配在候选列表但未排第一 |
| 候选列表中有正确匹配但置信度为低 | 1 | 找到了但不确定 |
| 候选列表中没有正确匹配 | 0 | 漏检 |
| 返回了错误匹配且置信度高 | -1 | 假阳性（严重） |

### 指标计算

- **Recall@1** = Top 1 命中数 / 总查询数
- **Recall@3** = Top 3 内命中数 / 总查询数
- **MRR** = mean(1 / rank_of_first_correct)
- **假阳性率** = 返回错误匹配且置信度≥中的查询数 / 总查询数
- **搜索轮数中位数** = median(grep 命令执行次数)
- **Token 成本估算** = 每个查询的 read 调用行数总和

### 分类分析

按匹配类型分组统计：

| 分组 | 查询 | 预期正确率 |
|------|------|-----------|
| A 类（追加 Concept） | Q1, Q2, Q6, Q9 | 应高（>80%） |
| B 类（新建 Concept） | Q8, Q10 | 应高（>80%） |
| C 类（待观察） | Q4, Q5 | 应高（>80%） |
| D 类（演化信号） | Q3 | 应中（>60%） |
| 多候选 | Q7 | 记录是否列出所有候选 |

---

## 成功标准

| 指标 | 合格线 | 目标线 | 失败条件 |
|------|--------|--------|---------|
| Recall@3（Phase 1） | ≥ 0.80 | ≥ 0.95 | < 0.60 |
| MRR（Phase 1） | ≥ 0.70 | ≥ 0.90 | < 0.50 |
| 词汇变体 Recall@3（Phase 2） | ≥ 0.60 | ≥ 0.80 | < 0.40 |
| 假阳性率（Phase 1+2+4） | ≤ 0.10 | 0 | > 0.30 |
| E4 空匹配假阳性 | 0 | 0 | > 0 |
| 搜索轮数中位数 | ≤ 5 | ≤ 3 | > 8 |
