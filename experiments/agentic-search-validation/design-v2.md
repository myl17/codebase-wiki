# Step 3 Agentic Search 验证实验 v2

> 设计日期：2026-06-28
> 替代 design.md（v1），v1 存在地面真值错误和实验框架偏差
> v2 所有地面真值已逐条交叉验证实际 wiki 内容

---

## 一、实验要回答什么问题

Step 3 的任务是：一个新仓库 ingest 进来，产生了 N 条问题空间条目（通常是 15-20 条），需要把它们匹配到已有的 Concept 页和 Seeds。实验要回答四个子问题：

1. **单条检索准确率**：agentic grep 能不能从已有知识里找到正确匹配？
2. **批量匹配效率**：同一仓库的多个问题空间一起匹配时，能不能利用去重降低 token 成本？
3. **分类准确率**：找到匹配后，能不能正确判断 A/B/C/D 类型？
4. **边界情况**：极短查询、模糊查询、词汇陷阱会不会导致假阳性？

---

## 二、实验语料（固定不变）

### 2.1 Concept 页（15 个）

| slug | problem（一句话） | repos |
|------|------------------|-------|
| agent-loop-orchestration | 如何编排 Agent 的主循环，协调消息接收、LLM 调用、工具执行和流式响应 | n, h, o |
| channel-abstraction-pattern | 如何用统一接口抽象异构消息平台 | n, h, o |
| provider-abstraction-pattern | 如何抽象多个 LLM Provider 的 API 差异 | n, h, o |
| tool-lifecycle-management | 如何管理 Agent 工具的注册/发现/策略过滤 | n, h, o |
| subagent-orchestration | 如何让主 Agent 委托后台子 Agent 执行复杂任务 | n, h, o |
| system-prompt-assembly | 如何组装 Agent 的系统提示词（分层注入） | n, h, o |
| autonomous-scheduling | 如何让 Agent 定时自主执行任务 | n, h, o |
| security-architecture | 如何构建多层安全防御体系 | n, h, o |
| session-lifecycle-management | 如何管理会话的身份/持久化/生命周期 | n, h, o |
| memory-management-architecture | 如何管理 Agent 的长期记忆 | n, h, o |
| context-compression-strategy | 如何在上下文窗口有限时自动压缩对话历史 | n, h, o |
| skills-extension-mechanism | 如何管理 Agent 的可插拔能力模块 | n, h, o |
| execution-isolation | 如何为工具执行提供可插拔隔离环境 | n, h, o |
| execution-approval-pattern | 如何在高风险操作前插入人类审批 | n, h, o |
| configuration-management | 如何管理配置（模块化/多环境隔离） | n, h, o |

### 2.2 子维度记录（已写入 Concept 页尾部）

| 父 Concept | 子维度标题 | 涉及仓库 | 状态 |
|-----------|----------|---------|------|
| agent-loop-orchestration | Agent 生命周期的可扩展钩子系统 | openclaw（一等公民）, hermes-agent（轻量回调）, nanobot（回调） | D 类，三个仓库都覆盖但成熟度差距大 |
| channel-abstraction-pattern | Channel-Agent Core 消息传输层解耦 | nanobot（独立 message-bus）, hermes-agent（嵌 gateway）, openclaw（嵌 gateway） | D 类，仅 nanobot 独立 |

### 2.3 C 类 Seeds（单仓库，待观察，未建 Concept 也未记录子维度）

| 问题空间 | 来源仓库 | master.md 状态 |
|---------|---------|---------------|
| 如何在 Agent 对话流中嵌入内置命令（命令分级和路由） | nanobot | C |
| 如何持久化会话并支持跨会话检索（FTS + LLM 摘要） | hermes-agent | C |
| 中央控制平面：单端口统一 HTTP REST + WebSocket + OpenAI 兼容 API | openclaw | C |
| 插件公共契约：core 与扩展之间的稳定 SDK 边界 | openclaw | C |
| 插件全生命周期：发现-加载-验证-管理 100+ 插件 | openclaw | C |
| CLI 架构：40+ 子命令 + 双层路由实现快速响应 | openclaw | C |
| 跨平台服务管理：统一 launchd/systemd/schtasks | openclaw | C |
| 消息路由：9 级优先级 + DM scope | openclaw | C |
| 媒体管道：多媒体安全处理 + SSRF 保护 | openclaw | C |

### 2.4 关键数据点

- 已有知识总条目：15 个 Concept + 9 个 C 类 Seed + 2 个 D 类子维度 = **26 个可检索目标**
- 分布在：15 个 `wiki/concepts/*.md` + 3 个 `seeds/*-problem-map.md` + 1 个 `seeds/master.md`（仅状态查询）
- `experiments/entity-concept-extraction/design-seeds.md` **不纳入检索语料**。该文件是历史基线，时间戳 2026-06-17，早于 wiki 建立。其中标记"已升级"的概念链接部分已失效（如 `subsystem-assembly-visibility` 页面不存在），部分已融入现有 15 个 Concept。将其作为检索目标会导致 agent 匹配到过期数据，不代表真实场景。

---

## 三、Phase 1：单条检索准确率（8 条查询）

### 目标
验证 agentic grep 能否在单条查询中准确找到正确的 Concept 或 Seed 匹配。

### 执行方式
每条查询作为一个独立 subagent 执行。Subagent 接收：系统指令 + 语料位置 + 查询文本。Subagent 使用 grep → read 命中文件 → 返回匹配结果。8 个 subagent 并行执行。

### 查询构造原则
- 每条查询模拟"一个新仓库的 entity 产生的问题空间条目"
- 措辞从**不同角度**写——不从已有条目复制粘贴
- 覆盖 A 类（追加 Concept）、C 类（新种子）、D 类（子维度）、N 类（无匹配）四种情况
- 每条查询的地面真值已逐条验证实际 wiki 内容

---

### Q1：A 类 — 三仓库 Concept（agent-loop-orchestration）

```
## 如何设计 Agent 的执行引擎——从收到用户消息到返回最终回复的完整处理管线

**问题陈述**：每个 AI Agent 框架都要定义一条消息处理流水线：消息进来后怎么调 LLM、LLM 返回工具调用后怎么执行并回传结果、最终文本回复怎么发回用户。这条流水线的设计决定了框架在面对 API 报错、多用户并发、长时间工具执行时的表现。
**核心关切**：
- 关切 1：多用户同时发消息时怎么保证同一个对话的顺序，同时不阻塞其他对话
- 关切 2：LLM 返回空响应、连接超时、上下文超长怎么自动恢复
- 关切 3：执行循环本身要不要感知 channel、session 这些产品概念
```

**地面真值**：
- 正确匹配：`agent-loop-orchestration`（Concept）
- 次级匹配：seeds 中三个仓库的 agent-loop/agent-core/agent-runtime 条目
- 类型：A（追加到已有 Concept，当前已有三个仓库覆盖）
- 验证：Concept 页 problem 字段 + 核心问题节覆盖了 Q1 的三个关切

---

### Q2：A 类 — 三仓库 Concept（channel-abstraction-pattern）

```
## 接 Telegram、Discord、微信都要写几千行代码——怎么把平台接入做成可复用的

**问题陈述**：做多平台机器人的团队发现，每接一个新平台都要从头写消息格式转换、流式输出控制、错误重试、用户身份识别。实际上这些逻辑每个平台都一样——能不能只写一次核心逻辑，每个平台只写一个薄薄的适配层？
**核心关切**：
- 关切 1：抽象层该多厚——只定义 send/receive，还是把 edit、react、thread 都包进来
- 关切 2：第三方想加一个新平台进去，需要改框架代码吗
- 关切 3：Telegram 的 inline button、Discord 的 embed card——这些平台特有功能要不要在统一接口里暴露
```

**地面真值**：
- 正确匹配：`channel-abstraction-pattern`（Concept）
- 次级匹配：三个仓库 problem-map 的 channel 条目
- 类型：A
- 验证：Concept 页直接覆盖"接口抽象粒度""平台特有能力的暴露程度"等关切

---

### Q3：A 类 — 三仓库 Concept（provider-abstraction-pattern）

```
## 换了三个 LLM 厂商，每个都要写一套适配器——怎么抽象出一个统一的调用层

**问题陈述**：团队从只用 OpenAI 发展到同时用 Anthropic Claude 和 AWS Bedrock。每个厂商的 API 消息格式不同、流式协议不同、错误返回格式不同、认证方式不同。现在代码里有三个 xxx_adapter，大量逻辑重复（重试、速率控制、连接池），但写法完全不同。能不能定义一个统一接口，所有厂商都适配到它上面？
**核心关切**：
- 关切 1：统一接口会不会损失厂商特有功能——比如 Anthropic 的 thinking blocks、OpenAI 的 structured outputs
- 关切 2：认证方式五花八门——API key、OAuth、AWS IAM——怎么在统一接口下管理
- 关切 3：一个厂商挂了怎么自动切到另一个，用户无感知
```

**地面真值**：
- 正确匹配：`provider-abstraction-pattern`（Concept）
- 次级匹配：三个仓库的 provider 相关条目
- 类型：A
- 验证：Concept 页覆盖"适配器设计模式""认证管理复杂度""故障切换策略"

---

### Q4：D 类 — 子维度（agent-loop-orchestration 下的 hooks）

```
## 想在 Agent 启动、收消息、切换会话的时候自动执行自定义脚本——怎么设计一套安全的钩子系统

**问题陈述**：框架的用户希望在 Agent 运行的不同阶段插入自己的逻辑——启动时初始化外部服务、收到消息时做内容审查、创建会话时记审计日志。框架需要提供一套钩子机制让用户注册回调，在特定事件触发时自动执行。
**核心关切**：
- 关切 1：钩子来源怎么管理——内置的、用户写的、社区下载的，它们的信任级别不同，应该区别对待
- 关切 2：一个钩子执行失败了，应不应该阻止其他钩子继续执行
- 关切 3：怎么设计触发条件——精确事件匹配还是支持通配符
```

**地面真值**：
- 正确匹配：`agent-loop-orchestration` 的子维度「Agent 生命周期的可扩展钩子系统」（页面第 76-81 行）
- 次级匹配：`seeds/openclaw-problem-map.md`「事件驱动的扩展点」
- 类型：**D 类**（粒度不匹配——hooks 是 agent-loop 的一个子维度，当前 openclaw 将其作为一等公民子系统但 hermes/nanobot 仅为附属回调。已在 agent-loop-orchestration.md 子维度观察中记录）
- 验证：子维度记录确认存在（agent-loop-orchestration.md 第 76 行）

**评分说明**：此查询测试 agent 能否 (a) 匹配到 openclaw hooks 条目，(b) 进一步读到 agent-loop-orchestration.md 的子维度记录，从而正确判断为 D 类。如果 agent 匹配到 hooks 但判为 C 类（仅因为只读了 seeds 没读 Concept 页），不计为检索失败——计为分类失败。检索成功 = 找到了正确关联的条目或 Concept。

---

### Q5：C 类 — 单仓库 Seed（nanobot 内置命令）

```
## 用户在聊天框里输入 /stop 要立刻停止 Agent——控制命令应该在进入 LLM 之前拦截还是让 LLM 自己判断

**问题陈述**：Agent 框架通常有内置命令如 /stop、/status、/new。有些命令需要即时响应（/stop 必须立刻停止，不能排队等 LLM），有些命令结合当前对话上下文回答效果更好。问题在于命令的分级策略——哪些拦截、哪些交给 LLM。
**核心关切**：
- 关切 1：紧急命令的响应延迟——不能卡在 LLM 推理队列里
- 关切 2：频道插件能不能注册自己的命令，怎么跟内置命令做命名空间隔离
```

**地面真值**：
- 正确匹配：`seeds/nanobot-problem-map.md`「如何在 Agent 对话流中嵌入内置命令」
- 类型：**C 类**（仅 nanobot 将命令路由作为独立 entity，hermes-agent 和 openclaw 无对应设计。问题空间对任何多命令 Agent 框架都有意义，但当前不满足准则①多方案对比）
- 验证：master.md 标记为 C，nanobot-problem-map 该条目确实存在

---

### Q6：C 类 — 单仓库 Seed（hermes-agent 会话检索）

```
## Agent 的会话历史存了几百个对话、几万条消息——用户问"我们三周前讨论的那个方案"怎么快速找到

**问题陈述**：长期运行的 Agent 积累了海量对话历史。用户经常引用过去的讨论（"上次说的那个配置""我们之前决定的架构"），Agent 需要跨会话搜索能力——不是简单的文本搜索，而是要理解语义关联。
**核心关切**：
- 关切 1：全文搜索（FTS）能快速命中关键词，但用户说"那个方案"时没有关键词可搜——需要语义级的摘要和检索
- 关切 2：多进程同时读写会话数据库时怎么解决写入冲突
```

**地面真值**：
- 正确匹配：`seeds/hermes-agent-problem-map.md`「如何持久化会话并支持跨会话检索」
- 类型：**C 类**（仅 hermes-agent 将跨会话检索作为独立设计决策，涉及 SQLite FTS5 + LLM 摘要。nanobot 和 openclaw 的会话存储均为文件级，不具备跨会话语义检索能力）
- 验证：master.md 标记为 C，条目存在于 hermes-agent-problem-map.md

---

### Q7：C 类 — 单仓库 Seed（openclaw 中央控制平面）

```
## Agent 框架需要对外暴露 API——能不能一个端口同时服务 HTTP REST、WebSocket 实时推送和 OpenAI 兼容的 /v1/chat/completions

**问题陈述**：构建对外暴露网络接口的 Agent 框架时，有三种外部通信需求：HTTP REST 给 webhook 和管理面板、WebSocket 给实时客户端推送、OpenAI 兼容端点让现有工具直接对接。能不能在一个端口上优雅地分发这三种协议，而不是开三个服务？
**核心关切**：
- 关切 1：怎么根据请求特征（HTTP headers、path、upgrade）把流量路由到正确的处理器
- 关切 2：JSON 协议的版本化——怎么保证新旧客户端的兼容性
- 关切 3：连接的认证、授权和速率限制怎么统一管理
```

**地面真值**：
- 正确匹配：`seeds/openclaw-problem-map.md`「中央控制平面：如何在单进程中统一 HTTP REST、WebSocket 双向通信和 OpenAI 兼容 API？」
- 类型：**C 类**（仅 openclaw 将单端口协议分发作为独立架构决策。nanobot 和 hermes-agent 无此设计。**注意**：此条目在 master.md 中备注为 "channel-abstraction-pattern 子维度"，但实际 channel-abstraction-pattern.md 的子维度记录是"Channel-Agent Core 消息传输层解耦"，不涉及 gateway 协议分发。属于 master.md 的备注不准确，实际应视为纯 C 类）
- 验证：条目存在于 openclaw-problem-map.md，master.md 标记为 C

---

### Q8：N 类 — 完全无匹配

```
## 想搞一个 A/B 实验平台来对比不同 system prompt 的效果——怎么设计分流、指标收集和结果判定

**问题陈述**：调优 system prompt 现在全靠经验和手动测试——改了 prompt、跑几条对话、凭感觉判断。需要系统化的对比：定义评估指标（任务完成率、用户满意度）、把用户分流到不同 prompt 变体、自动收集数据和生成结论。
**核心关切**：
- 关切 1：实验指标怎么定义——什么算"Agent 表现好"
- 关切 2：分流策略——同一用户固定在一个变体里还是每次随机分配
- 关切 3：数据收集——token 消耗、成功率、用户反馈怎么汇总和对比
```

**地面真值**：
- 正确匹配：**无**——已有知识中不存在 A/B 实验相关的问题空间条目
- 类型：**N 类**（新问题空间，当前无任何仓库覆盖，应新增 C 类种子）
- 验证：已逐条检查所有 15 个 Concept 和 9 个 C 类 Seed，无匹配
- **关键测试点**：agent 应该返回"无匹配"而不是强行找关联（假阳性）

---

### Phase 1 评分

| 指标 | 计算方式 | 合格线 | 目标线 |
|------|---------|--------|--------|
| Recall@1 | 地面真值排在 Top 1 的查询数 / 8 | ≥ 0.75 | ≥ 0.88 |
| Recall@3 | 地面真值在 Top 3 内的查询数 / 8 | ≥ 0.88 | 1.0 |
| MRR | mean(1 / 地面真值的排名) | ≥ 0.75 | ≥ 0.90 |
| 假阳性数 | 置信度 ≥ 中但实际错误的匹配数 | ≤ 1 | 0 |
| Q8 假阳性 | Q8 是否返回了匹配 | 0 | 0 |

### Phase 1 分类评分（检索和分类分开计分）

对每个查询额外记录：
- **检索得分**：正确条目是否在 Top 3 内（是/否）
- **分类得分**：A/B/C/D/N 标签是否正确（是/否）
- **失败模式**：（检索失败 / 分类失败 / 两者都失败 / 两者都成功）

这样能区分"agent 搜到了但分错了"和"agent 根本没搜到"。

### Phase 1 成本记录

每个查询记录：
- `grep 次数`
- `read 调用次数`
- `read 总行数`（token 代理指标）
- 搜索耗时（subagent 内部时间戳 delta）

---

## 四、Phase 2：批量匹配（模拟真实 Step 3）

### 目标
验证 agent 能否在**批量场景**（一个新仓库的 8 条问题空间同时匹配）中利用去重降低 token 成本，同时保持准确率不降。

### 为什么需要 Phase 2
单条查询测的是"理论能力"，批量匹配测的是"实际表现"。区别在于：
- 单条查询：8 个 subagent 各自独立 grep + read，同一个文件可能被读 8 次
- 批量匹配：1 个 subagent 拿到 8 条，grep 全部后去重文件列表，每个文件只读一次

真实 Step 3 是后者。Phase 2 和 Phase 1 的成本比就是去重的收益。

### 执行方式
1 个 subagent 同时接收 8 条查询。系统提示要求：先为每条做 grep、合并命中文件列表去重、只读每个唯一文件一次、在单轮推理中输出全部 8 条匹配结果。

### 查询集

与 Phase 1 的 Q1-Q8 **完全相同的查询**（相同文本）。这样 Phase 2 和 Phase 1 的准确率可以直接对比（同一批查询，不同执行模式）。

### 衡量指标

| 指标 | 对比基准 | 预期 |
|------|---------|------|
| Recall@3（批量） | Phase 1 Recall@3 | 不低于 Phase 1 |
| read 调用次数（批量） | Phase 1 的 8 条 read 次数之和 | 批量 ≤ Phase 1 的 40% |
| 每条查询的平均 read 行数 | Phase 1 的单条平均 | 批量 ≤ Phase 1 的 50% |
| 交叉引用收益 | 无基准 | 记录 agent 是否利用"一条查询的匹配启发另一条" |

---

## 五、Phase 3：边界情况（5 条查询）

### E1：极度模糊的短查询

```
## Agent 记忆怎么搞

**问题陈述**：用户跟 Agent 聊天，希望 Agent 记住之前聊过什么。下次用户说"上次那个事"的时候 Agent 能接上话。
**核心关切**：
- 关切 1：存哪里
- 关切 2：消息太多了怎么办
```

**地面真值**：
- Top 1：`memory-management-architecture`（长期记忆架构）
- Top 2：`context-compression-strategy`（上下文压缩——"消息太多了"关切）
- 类型：多候选，以 memory-management 为主
- 测试点：极短查询 + 极简关切，agent 能否从模糊描述中找到正确的 Concept

---

### E2：多 Concept 交叉匹配

```
## 如何在多轮工具调用过程中管理上下文增长、同时保证执行安全

**问题陈述**：Agent 调用工具→LLM 分析结果→再调用工具的多轮过程中，每轮的消息都会追加到上下文窗口。窗口快满时需要压缩旧消息，但压缩的同时还要保证安全性——不能因为压缩丢失了工具执行的安全约束。
**核心关切**：
- 关切 1：多轮工具调用的消息如何裁剪才不丢关键决策信息
- 关切 2：压缩后的上下文中如何保留安全规则的完整性
```

**地面真值**：
- Top 1：`context-compression-strategy`（上下文压缩是核心问题）
- Top 2：`security-architecture`（安全约束在压缩中保留）
- 类型：多候选，context-compression 为主、security 为副
- 测试点：agent 能否识别主次，而不是只返回一个

---

### E3：词汇陷阱（"消息队列"）

```
## 需要一个消息队列来缓存用户发来的消息——Agent 重启后队列里的消息不能丢

**问题陈述**：Agent 同时收到大量消息时需要缓冲——先存到队列里，按顺序处理。问题是进程重启后未处理的消息能不能恢复。
**核心关切**：
- 关切 1：队列的持久化——进程重启后消息能不能恢复
- 关切 2：顺序保证——同一会话的消息按发送顺序处理
```

**地面真值**：
- **不匹配** `seeds/nanobot-problem-map.md` "如何解耦 Channel 和 Agent Core 的消息传递"——那是 asyncio.Queue（内存队列，不持久化），用于 channel→agent 传输解耦，不是存储缓存
- **不匹配** 任何已有条目——查询描述的是一般意义上的持久化消息队列（类似任务队列），现有知识中没有覆盖
- 类型：**无匹配 / N 类 → C 类**
- 测试点：agent 不应被"消息队列"这个词汇误导到 nanobot 的 message-bus 条目（后者是 channel-agent 传输解耦，不是持久化存储队列）

---

### E4：中英混合 + 技术术语

```
## 如何设计 agent 的 tool execution sandbox，支持 docker backend 和 SSH backend 的可插拔切换

**问题陈述**：Agent 执行用户的 shell 命令和 Python 脚本时，直接在主进程里跑太危险。需要一个 sandbox——可以是本地 Docker 容器，也可以是远程 SSH 机器。框架应该提供一个统一的 SandboxBackend 接口，让 agent 工具不感知后端差异。
**核心关切**：
- 关切 1：filesystem bridge——agent 读写的文件路径在 host 和 container 之间怎么映射
- 关切 2：sandbox 的生命周期——每个 session 一个容器还是共享？空闲多久回收
```

**地面真值**：
- 正确匹配：`execution-isolation`（Concept）
- 类型：A 类
- 验证：Concept 覆盖"后端可插拔性""文件系统透明性""环境生命周期管理"
- 测试点：中英混合措辞不影响匹配

---

### E5：粒度过细——不应匹配

```
## 流式输出时 LLM 产生的 delta 太碎了，怎么在发给 Telegram 之前合并一下减少 API 调用

**问题陈述**：LLM 流式输出每几个 token 就产生一个 delta chunk。如果每个 delta 都直接发给 Telegram API，会因为速率限制被限流。需要在发送前对连续 delta 做合并（coalesce）。
**核心关切**：
- 关切 1：合并粒度——固定时间窗口还是固定 token 数量阈值
- 关切 2：合并对用户感知的"打字速度"有没有负面影响
```

**地面真值**：
- **不应匹配任何 Concept 或 Seed**。这是实现细节（stream delta coalescing），不是独立的问题空间。它属于 `channel-abstraction-pattern` 概念覆盖的实现范畴（三个仓库都有流式输出的 delta 合并处理），但不构成独立的问题空间条目。
- 类型：**N 类**（不满足问题空间提取条件——粒度过细）
- 测试点：agent 能否识别"这不是独立的问题空间"而不强行匹配

---

### Phase 3 评分

| 指标 | 合格线 | 目标线 |
|------|--------|--------|
| 整体 Recall@3 | ≥ 0.60 | ≥ 0.80 |
| E3 假阳性 | 0（不应匹配到 message-bus） | 0 |
| E5 正确拒绝 | 1（应返回"无匹配/粒度过细"） | 1 |

---

## 六、Phase 4：真实抽样查询（9 条，来自已有 problem-map）

### 为什么需要 Phase 4

Phase 1 的查询是我根据地面真值反向构造的——我知道答案再出题，天然存在确认偏差。Phase 4 从**真实 ingest 产出的 problem-map** 中抽取条目，改写措辞后投入检索。这些条目的问题空间是真实存在的，措辞风格保留了原始 Step 2 的"问题陈述 + 核心关切"结构，不是对着答案编的。

改写原则：
- 保留原始条目的**核心问题和关切维度**
- 改写措辞模拟"另一个仓库的 Step 2 产生了同样的底层问题但用了不同表述"
- 不复制原始条目的任何一句话
- 地面真值指向原始条目或其升级的 Concept

### 查询来源分布

| 来源 | 抽取数 | 覆盖类型 |
|------|--------|---------|
| nanobot-problem-map | 3 | B（Concept）、C（单仓库种子）、D（子维度） |
| hermes-agent-problem-map | 3 | B（Concept）×2、C（单仓库种子） |
| openclaw-problem-map | 3 | C（单仓库种子）、D（子维度）、B（Concept） |

---

### S1：B 类 — 来自 nanobot "如何管理 Agent 的长期记忆"

```
## Agent 需要跨会话记住用户偏好和重要信息——记忆系统怎么分层设计

**问题陈述**：用户跟 Agent 聊了几周后，Agent 应该知道用户是谁、上次讨论到哪了、有哪些长期约定。这不是简单存文件，而是要区分"当前聊天的上下文"和"跨会话的知识积累"——两者需要不同的存储策略和处理机制。
**核心关切**：
- 关切 1：记忆整理的时机——是等上下文快满了被动触发，还是在空闲时主动整理
- 关切 2：记忆的存储格式——纯文本、JSON、数据库各有代价，升级框架时旧数据怎么办
- 关切 3：要不要让 LLM 参与记忆整理——让它自己决定什么值得记住、什么可以丢掉
```

**地面真值**：
- 原始匹配：`seeds/nanobot-problem-map.md` "如何管理 Agent 的长期记忆"
- Concept 匹配：`memory-management-architecture`（Concept，覆盖三个仓库）
- 类型：**B 类**（已有 Concept，三个仓库覆盖）
- 验证：nanobot problem-map 该条目已 B → memory-management-architecture

---

### S2：C 类 — 来自 nanobot "如何在 Agent 对话流中嵌入内置命令"

```
## 用户在聊天窗口输入 /stop 要立刻中断 Agent——内置命令的路由应该在消息管线的哪一层拦截

**问题陈述**：Agent 框架通常有内置控制命令，如 /stop、/status、/new。关键设计问题是：这些命令在被转换成 LLM 的上下文消息之前就该拦截处理，还是应该作为普通消息流入 LLM 让模型自己判断意图？
**核心关切**：
- 关切 1：紧急命令（/stop）必须即时响应，不能排队等 LLM 推理完当前消息
- 关切 2：第三方开发的频道插件能不能注册自己的命令——跟框架内置命令的冲突怎么解决
- 关切 3：命令的执行结果要不要反馈给 LLM——比如 /status 的返回信息要不要作为上下文注入
```

**地面真值**：
- 原始匹配：`seeds/nanobot-problem-map.md` "如何在 Agent 对话流中嵌入内置命令"
- 类型：**C 类**（仅 nanobot 将命令路由作为独立 entity，hermes-agent 和 openclaw 无对应独立设计）
- 验证：master.md 标记为 C

---

### S3：D 类 — 来自 nanobot "如何解耦 Channel 和 Agent Core 的消息传递"

```
## 聊天平台适配器和 Agent 核心引擎之间应该用什么通信机制——让两边可以独立开发和部署

**问题陈述**：框架接入 Telegram、Discord 等多个平台后，每个平台的适配器负责收发消息，Agent 核心引擎负责理解和回复。问题在于：适配器和引擎之间怎么传递消息？如果适配器直接调用引擎的方法，换一个平台就得改引擎代码。
**核心关切**：
- 关切 1：适配器和引擎之间应该是异步的——平台收消息的速度和 Agent 处理的速度不一样
- 关切 2：流式输出时，LLM 产生的 token delta 怎么从引擎回传到正确的平台适配器
- 关切 3：会话信息（从哪个平台、哪个用户来的）怎么在通信中传递而不丢失
```

**地面真值**：
- 原始匹配：`seeds/nanobot-problem-map.md` "如何解耦 Channel 和 Agent Core 的消息传递"
- 子维度匹配：`channel-abstraction-pattern` 子维度「Channel-Agent Core 消息传输层解耦」（页面第 77 行）
- 类型：**D 类**（仅 nanobot 将消息传输作为独立 entity（message-bus），hermes-agent 和 openclaw 的消息流嵌入 gateway。已记录为 channel-abstraction-pattern 的子维度）
- 验证：channel-abstraction-pattern.md 第 73-87 行确认子维度记录存在

---

### S4：B 类 — 来自 hermes-agent "如何管理对话上下文窗口"

```
## 上下文窗口装不下了——怎么自动压缩对话历史，保留关键决策不丢

**问题陈述**：LLM 的上下文窗口有上限。用户和 Agent 聊了几十轮后，必须把旧消息裁剪掉才能继续。但简单地从头删会丢掉重要的上下文——之前的决策、约束条件、进行中的任务。怎么判断哪些内容值得保留、哪些可以安全丢弃？
**核心关切**：
- 关切 1：压缩后的摘要必须保留什么——用户的角色、正在进行的任务、已经做的决策不能丢
- 关切 2：压缩本身也要消耗 token——用便宜模型做摘要还是用规则裁剪更划算
- 关切 3：多轮工具调用的消息不能被从中间切断——不然 LLM 看到孤立的 tool result 没有对应的 tool call
```

**地面真值**：
- 原始匹配：`seeds/hermes-agent-problem-map.md` "如何管理对话上下文窗口"
- Concept 匹配：`context-compression-strategy`（Concept，覆盖三个仓库）
- 类型：**B 类**（已有 Concept）
- 验证：hermes-agent problem-map 该条目已 B → context-compression-strategy

---

### S5：C 类 — 来自 hermes-agent "如何持久化会话并支持跨会话检索"

```
## Agent 跟不同人聊了几百个会话、存了几万条消息——用户问"三周前我们讨论的那个方案"怎么找到

**问题陈述**：Agent 长期运行后会积累海量对话。用户经常引用历史讨论（"上次说的那个设计""之前你提过的方案"），Agent 不能只搜关键词——用户说"那个方案"的时候没有关键词可以匹配。需要理解语义关联。
**核心关切**：
- 关切 1：全文搜索能快速定位包含"设计"的消息，但用户说"上次说的"时没有可搜索的词汇——需要语义级的摘要和检索
- 关切 2：多条进程同时写会话数据库时怎么处理冲突——gateway、CLI、子 Agent 都可能在写
- 关切 3：几千个会话的全文本搜索怎么保证响应速度
```

**地面真值**：
- 原始匹配：`seeds/hermes-agent-problem-map.md` "如何持久化会话并支持跨会话检索"
- 类型：**C 类**（仅 hermes-agent 将跨会话检索作为独立设计决策，涉及 FTS5 + LLM 摘要。nanobot 和 openclaw 的会话存储为文件级，不具备跨会话语义检索能力）
- 验证：master.md 标记为 C

---

### S6：B 类 — 来自 hermes-agent "如何管理工具的安全执行"

```
## Agent 要执行用户给的 shell 命令——怎么在真正跑之前检查它是否危险、防止删库跑路

**问题陈述**：Agent 执行系统命令是不可或缺的能力，但也是最危险的操作。不能只靠一层防护——静态正则匹配防不住所有危险命令，但全交给 LLM 判断又太慢太贵。需要多层防线组合。
**核心关切**：
- 关切 1：怎么在静态规则和智能判断之间取得平衡——规则太严误杀正常命令，太松漏过危险操作
- 关切 2：多层检查的顺序——先用快的还是先用准的
- 关切 3：用户审批的体验——不能每条命令都弹窗确认，需要有分级策略（只确认高风险的）
```

**地面真值**：
- 原始匹配：`seeds/hermes-agent-problem-map.md` "如何管理工具的安全执行"
- Concept 匹配：`security-architecture`（Concept，覆盖三个仓库）
- 类型：**B 类**（已有 Concept）
- 验证：hermes-agent problem-map 该条目已 B → security-architecture
- 注意：此查询也可能触达 `execution-approval-pattern`（关切 3 的人类审批部分），但核心问题是命令执行安全链，主匹配应为 security-architecture

---

### S7：C 类 — 来自 openclaw "插件公共契约"

```
## 框架核心和一百多个扩展插件之间怎么定义稳定的接口边界——让插件作者不需要读懂核心源码

**问题陈述**：插件化框架的核心问题是 SDK 边界设计。接口太宽，核心的任何改动都会破坏插件兼容性。接口太窄，插件拿不到足够的能力做有用的事。而且这个边界要稳定——插件作者升级框架时不能发现自己的代码全坏了。
**核心关切**：
- 关切 1：SDK 的导出表面应该多宽——给插件足够的 API 但不暴露核心内部实现
- 关切 2：SDK 模块的加载成本——如果每个插件都 import 整个 SDK，启动会极慢
- 关切 3：怎么避免 SDK 内部出现循环依赖——facade 类互相引用会导致微妙的加载顺序 bug
```

**地面真值**：
- 原始匹配：`seeds/openclaw-problem-map.md` "插件公共契约：如何在 core 与 100+ 个扩展之间定义一个稳定、安全、可演化的公共契约边界？"
- 类型：**C 类**（仅 openclaw 将 SDK 边界作为独立架构决策。nanobot 的扩展通过 entry_points + 简单注册，hermes-agent 的插件系统为 infrastructure 层，均未将"SDK 契约"作为一等设计问题）
- 验证：master.md 标记为 C

---

### S8：D 类 — 来自 openclaw "事件驱动的扩展点"

```
## 想在 Agent 生命周期的不同阶段挂自定义逻辑——收到消息时审查内容、启动时初始化外部服务、创建会话时记审计日志

**问题陈述**：框架的用户想在 Agent 运行的各个阶段插入自己的代码。需要一个事件钩子系统——定义一组生命周期事件、让用户注册回调、在事件触发时自动执行。但钩子本身也有安全问题：用户下载的社区钩子可能有意或无意地破坏框架运行。
**核心关切**：
- 关切 1：钩子来源的信任分级——框架内置的、用户自己写的、从社区下载的，应该区别对待
- 关切 2：一个钩子跑挂了，其他钩子还能不能继续执行
- 关切 3：事件匹配的粒度——精确事件名匹配还是支持通配符（如 `message.*`）
```

**地面真值**：
- 原始匹配：`seeds/openclaw-problem-map.md` "事件驱动的扩展点：如何在 agent 生命周期的关键节点提供可发现、可过滤、安全隔离的钩子系统？"
- 子维度匹配：`agent-loop-orchestration` 子维度「Agent 生命周期的可扩展钩子系统」（页面第 76-81 行）
- 类型：**D 类**（粒度不匹配——hooks 是 agent-loop 的子维度，当前 openclaw 将其作为一等公民子系统但 hermes/nanobot 仅为附属回调。已记录子维度观察）
- 验证：agent-loop-orchestration.md 第 76 行确认子维度记录存在

---

### S9：B 类 — 来自 openclaw "多层工具策略管道"

```
## 不同场景下 Agent 能用的工具集合应该不同——怎么设计多层级的工具权限策略

**问题陈述**：Agent 框架中，不同上下文需要不同的工具集合。在 dev 环境下可能允许 shell 执行，在 prod 环境禁止。某个 agent 角色可能需要网络访问，另一个角色完全离线。怎么设计一个策略系统，让更具体的上下文自动覆盖更一般的配置？
**核心关切**：
- 关切 1：策略层级怎么排优先级——provider 级、agent 级、session 级、沙箱级的配置冲突时谁说了算
- 关切 2：能不能按工具组批量管理（如 coding tools 全开/全关）而不是逐个工具配置
- 关切 3：不同 LLM 厂商对工具的 schema 支持不一样——怎么在不支持某些特性的 provider 上降级
```

**地面真值**：
- 原始匹配：`seeds/openclaw-problem-map.md` "多层工具策略管道：如何在 agent 工具的 allow/deny 控制上实现 profile→provider→global→agent→group→sandbox→subagent 七层优先级？"
- Concept 匹配：`tool-lifecycle-management`（Concept，覆盖三个仓库）
- 类型：**B 类**（已有 Concept。openclaw 的 9 层策略管道是该概念下最复杂的实现，但核心问题——多层级工具权限——三个仓库各有解法）
- 验证：openclaw problem-map 该条目已 B → tool-lifecycle-management

---

### Phase 4 评分

| 指标 | 计算方式 | 合格线 | 目标线 |
|------|---------|--------|--------|
| Recall@3 | 地面真值在 Top 3 内的查询数 / 9 | ≥ 0.78 (7/9) | ≥ 0.89 (8/9) |
| MRR | mean(1 / 地面真值的排名) | ≥ 0.70 | ≥ 0.85 |
| B 类召回（S1, S4, S6, S9） | 匹配到对应 Concept 的比例 | ≥ 0.75 (3/4) | 1.0 (4/4) |
| C 类召回（S2, S5, S7） | 匹配到对应 problem-map 条目的比例 | ≥ 0.67 (2/3) | 1.0 (3/3) |
| D 类正确识别（S3, S8） | 识别为子维度/粒度不匹配的比例 | ≥ 0.50 (1/2) | 1.0 (2/2) |
| Phase 4 vs Phase 1 Recall@3 差距 | \|Phase 4 Recall - Phase 1 Recall\| | ≤ 0.15 | ≤ 0.05 |

**关键对比指标**：Phase 4 和 Phase 1 的 Recall@3 差距。如果差距很小，说明手写查询（对着答案出题）和真实抽样查询的难度相当——agentic grep 的能力评估是可靠的。如果差距很大，说明手写查询过于简单，真实场景更难。

---

## 七、补充实验：第 4 仓库全链路验证（Phase 5，高资源消耗）

### 为什么需要 Phase 5

Phase 1-4 都在用已有仓库的数据做模拟——查询是对着已有 problem-map 构造的，地面真值是根据已有匹配关系反推的。最严格的验证是：**找一个真正的第 4 个仓库，完整跑一遍 ingest，让 ingest subagent 在真实 Step 3 中自主完成匹配判断，然后我们事后审查它的 transcript 来评估质量。**

和旧方案的区别：旧方案想"跑到 Step 2 就停，然后拿 problem-map 回主分支单独测 Step 3"。那需要要么改 `/ingest` 加 `--stop-at`（污染生产管线），要么搞 worktree 复制文件（流程复杂）。

新方案简单得多：**直接跑完整 ingest，实验数据就是 ingest subagent 的对话 transcript**。Transcript 里天然包含了 Step 3 的全部搜索行为——它 grep 了什么、读了什么文件、匹配到了什么、判了什么分类。我们只需要事后读 transcript 做人工审查。

### 选定仓库：langchain-ai/deepagents

**路径**：`/Users/yuanlimiao/Work/agent_harness/deepagents-main/libs/deepagents/`

**规模**：~20 个核心源文件（不含 build/tests/examples），纯 Python，基于 LangChain + LangGraph。

**为什么选它**：与已有三个仓库（nanobot/hermes-agent/openclaw）形成鲜明对比——

| 维度 | nanobot | hermes-agent | openclaw | **deepagents** |
|------|---------|-------------|----------|---------------|
| 语言 | Python | Python | TypeScript | Python |
| 架构范式 | 类层次 + 依赖注入 | 单类巨型 | 函数式 + 插件化 | **中间件管道** |
| 底层引擎 | 自研 AgentLoop | 自研 AIAgent | 自研 runEmbeddedPiAgent | **LangGraph StateGraph** |
| 扩展机制 | Channel/Tool 插件 | AST 扫描 + MCP | Plugin Manifest | **Middleware 堆叠** |
| 后端抽象 | 无（直连 API） | BaseEnvironment ABC | SandboxBackendFactory | **BackendProtocol（State/Filesystem/Store/Sandbox/Composite）** |

**核心架构特征**（来自源码阅读）：

1. **Middleware 管道是唯一扩展机制**：`TodoList → Skills → Filesystem → SubAgent → Summarization → PatchToolCalls → (user middleware) → AnthropicPromptCaching → Memory → HumanInTheLoop`。每个 middleware 可以在 `wrap_model_call` / `wrap_tool_call` 两个生命周期钩子注入行为
2. **BackendProtocol 是文件系统和执行的统一抽象**：`ls/read/write/edit/grep/glob` + `execute`，五种实现（State/Filesystem/Store/Sandbox/Composite）
3. **基于 LangGraph 的 Agent 循环**：不自己写循环，用 `create_agent()` 生成 `CompiledStateGraph`，循环编排交给 LangGraph
4. **Provider 解析延迟到 LangChain**：`resolve_model()` 通过 `init_chat_model()` 支持 `provider:model` 字符串
5. **Summarization 是中间件不是独立模块**：上下文压缩作为 middleware 注入，按 token 阈值自动触发

### 执行方案

在独立的 git 分支上跑 `/ingest --auto`。分支隔离所有变更，main 分支保持原始状态作为对比基准。Ingest 完成后用 `git diff` 获取精确的变更集，人工逐条审查每条变更的合理性。

**为什么必须在分支上跑**：事后审查的关键问题是"我们不知道 agent 修改的对不对"——agent 已经把 Concept 页和 problem-map 合并/修改/新增了，原始状态丢失了。没有对比基准就没法判断质量。分支解决了这个问题：原始状态在 main 上完整保留，`git diff main...<分支>` 给出精确到每行增删的变更集，你可以随时切回 main 对照原始文件逐条验证。

```
Step A: 创建分支 + 跑 ingest
  git checkout -b feat/deepagents-ingest-experiment  # 从 main 创建
  cd /Users/yuanlimiao/Work/codebase-wiki
  /ingest --auto --repo /Users/yuanlimiao/Work/agent_harness/deepagents-main/libs/deepagents/
  → 完整管线：Entity 提取 → 问题空间映射 → Step 3 匹配 → Concept 写作
  → 所有变更仅存在于 feat/deepagents-ingest-experiment 分支上

Step B: 提取实验数据
  a) 从 ingest subagent 的 transcript 抓取：
     - Step 2 产出了哪些问题空间条目（标题 + 问题陈述 + 关切）
     - Step 3 中每条问题空间的 grep 命令、命中、Read 调用、匹配结果、分类
     - 总 token 消耗
  b) 获取变更集：
     git diff main...feat/deepagents-ingest-experiment -- wiki/
     → 精确到每个文件、每行增删的完整 diff

Step C: 人工审查（可随时切回 main 对比原始文件）
  对每条变更：
    - 匹配合理性：agent 判的 A/B/C/D/N 是否合理
    - 假阳性：agent 说匹配但实际不相关的条目
    - 遗漏：明显该匹配但 agent 没找到的条目
    - 概念污染：agent 是否错误修改了已有 Concept 页的内容（对比 main 上的原始版本）
    → 用 transcript 中的搜索行为 + 你对 deepagents 源码的理解双重验证

Step D: 审查完毕后
  如果结果满意：git checkout feat/experiment-deepwiki-vs-src && git merge feat/deepagents-ingest-experiment
  如果有问题：git branch -D feat/deepagents-ingest-experiment（main 毫发无损）
```

**这个方案的优点**：
1. 原始状态和变更结果之间有一道清晰的 `git diff` 桥梁，对比基准永不错失
2. 随时可以 `git checkout main` 对照原始 Concept 页逐条验证 agent 的修改
3. 没有中间拦截逻辑，ingest 走的是完全真实的管线
4. 满意就 merge，不满意就 `git branch -D`，零风险

### Phase 5 衡量标准

| 维度 | 评估方式 |
|------|---------|
| 匹配合理性 | 人工逐条审查 agent 的匹配结果（合理/不合理/待讨论） |
| 假阳性检查 | agent 匹配到的每个条目，人工确认是否真的相关 |
| 遗漏检查 | 人工判断是否有明显应该匹配但 agent 没找到的 |
| 分类正确性 | A/B/C/D/N 标签是否合理 |
| 关键词策略 | agent 的 grep 关键词是否有效命中了正确目标 |
| Token 成本 | 从 transcript 提取实际 grep 次数、read 行数 |
| 端到端行为 | ingest 是否在暂停点正确暂停？整体流程是否顺畅？ |

Phase 5 不设硬性的通过/失败线——它的定位是**现场验证 + 发现边缘问题**，为 Step 3 的系统提示词提供真实调优样本。

### Phase 5 衡量标准

| 维度 | 评估方式 |
|------|---------|
| 匹配合理性 | 人工逐条审查 agent 的匹配结果（无法自动化——没有地面真值） |
| 假阳性检查 | agent 说匹配的条目，人工确认是否真的合理 |
| 遗漏检查 | 人工检查是否有明显应该匹配但 agent 没找到的 |
| 分类正确性 | A/B/C/D/N 的标签是否合理 |
| Token 成本 | 记录实际 grep 次数、read 行数、推理 token |
| 端到端时间 | 从拿到 problem-map 到产出全部匹配结果的总时间 |

### Phase 5 的定位

Phase 5 **不用于决定 agentic search 是否可行**（那个由 Phase 1-4 决定）。Phase 5 用于：
- 验证 Phase 1-4 的结论在真实管线中是否成立
- 发现实验设计中没覆盖的边缘问题
- 给 Step 3 的系统提示词提供真实调优样本

---

## 八、实验执行流程

### Step 1：Phase 1 单条检索（8 个 subagent 并行）

```
对每个子agent：
- 系统角色：你是一个检索 agent。在给定的语料中搜索与本查询最匹配的已有问题空间条目。
- 语料位置：wiki/concepts/（15 个 Concept 页）、seeds/*-problem-map.md（3 个问题映射文件）、seeds/master.md（状态表，仅在需要确认条目状态时查询）
- 检索策略：先用 grep 在 seeds/ 和 wiki/concepts/ 中多关键词搜索 → 根据命中读相关段落 → 比较候选 → 返回匹配结果
- 约束：不要一次性读所有文件。grep 先粗筛。最多读 3 个文件的片段。

- 输出格式：
  ## 匹配结果
  ### Top 1: <条目名称或 Concept slug>
  - **位置**：<文件路径>
  - **匹配类型**：A/B/C/D/N
  - **置信度**：高/中/低
  - **匹配理由**：（引用已有条目的具体内容说明为什么匹配）

  ### Top 2: （如有）
  ...

  ### Top 3: （如有）
  ...

  ## 总结判断
  如果多个候选，说明它们之间的关系。最终推荐怎么处理。
```

> **搜索行为观测**：不要求 subagent 自报 grep 命令或搜索过程。所有搜索行为（grep 命令、命中、Read 调用）从 subagent 的 transcript 文件中直接抓取。Transcript 位于 `~/.claude/projects/-Users-yuanlimiao-Work-codebase-wiki/<会话ID>/subagents/agent-<id>.jsonl`，包含 `assistant` 事件（tool_use 含完整参数）和 `user` 事件（tool_result 含完整输出）。

```

### Step 2：Phase 3 边界情况（5 个 subagent 并行）

与 Phase 1 相同的独立 subagent 模式，但查询是 E1-E5。与 Phase 1 同时并行执行（共 13 个 subagent）。

### Step 3：Phase 4 真实抽样（9 个 subagent 并行）

查询是 S1-S9。与 Phase 1/3 相同的独立 subagent 模式。9 个 subagent 并行执行。

### Step 4：Phase 2 批量匹配（1 个 subagent）

与 Phase 1 相同的检索 task，但查询是 8 条同时接收：
```
- 同时接收 8 条查询（Q1-Q8 的原文）
- 检索策略：为每条查询提取关键词 → 汇总所有关键词做 grep → 收集命中文件名 → 去重后逐个读取 → 一次推理返回全部 8 条匹配
- 约束：只读每个命中文件一次。在单轮回复中完成全部 8 条的匹配输出。
- 输出格式：对每条查询单独输出匹配结果（同 Phase 1 格式）
```
搜索行为从 transcript 抓取，不要求自报。

### Step 5：结果汇总（主上下文）

分两步执行：

**a) 收集匹配结果**：读取每个 subagent 的返回文本，提取 Top 1-3 匹配结果 → 与地面真值对比 → 计算 Recall@3、MRR、假阳性率。

**b) 搜索行为分析**（从 transcript 抓取，不依赖自报）：

针对每个查询，用脚本解析对应 subagent 的 transcript 文件（`<proj>/<session>/subagents/agent-<id>.jsonl`）：
- 从 `assistant` 事件 `tool_use` blocks 提取每次 Bash/Read 调用的完整参数
- 从 `user` 事件 `tool_result` 提取 grep 命中内容和文件内容
- 统计：grep 命令数及关键词、Read 文件数及行数、命中→读取的筛选率

然后汇总分析：
- 成功匹配的关键词特征：单一关键词命中 vs 多词组合、中文 vs 英文 vs 中英混合
- 失败案例的根因：关键词搜偏 / 搜到了但判断错 / 关键词与语料用词不重叠
- grep 轮数分布、token 成本（Read 总行数）

**c) Phase 2 效率对比**：从 transcript 提取 Phase 2 的 Read 总行数，与 Phase 1 的 8 条总和对比，计算去重收益。

**总 subagent 数**：Phase 1 (8) + Phase 3 (5) + Phase 4 (9) = 22 个独立 subagent + Phase 2 (1 个批量 subagent) = **23 个 subagent 调用**。其中 Phase 1+3+4 全部并行，Phase 2 串行（依赖 Phase 1 结果做对比）。Phase 5 完全独立。

---

## 九、成功标准

| 实验阶段 | 指标 | 失败条件 | 通过条件 |
|---------|------|---------|---------|
| Phase 1 | Recall@3 | < 0.75 | ≥ 0.88 |
| Phase 1 | 假阳性 | > 1 个（含 Q8） | 0 个 |
| Phase 2 | Recall@3 vs Phase 1 | 低于 Phase 1 ≥ 0.15 | 不低于或微降（≤ 0.05） |
| Phase 2 | Token 效率 | read 行数 ≥ Phase 1 的 80% | ≤ Phase 1 的 50% |
| Phase 3 | E3 假阳性 | > 0 | 0 |
| Phase 3 | E5 正确拒绝 | 0 | 1 |
| Phase 4 | Recall@3 | < 0.67 (6/9) | ≥ 0.78 (7/9) |
| Phase 4 | vs Phase 1 Recall 差距 | > 0.20 | ≤ 0.10 |
| Phase 5 | 无硬性通过线 | — | 人工审查产出的定性结论 |

### 汇总决策

| 结果 | 决策 |
|------|------|
| Phase 1+3+4 Recall@3 全部达标 + 零假阳性 | Agentic grep 通过验证，可作为 Step 3 检索方案 |
| Phase 1 Recall@3 达标但 Phase 3/4 不达标 | Agentic grep 能力边界清晰，需要针对边界情况补充规则 |
| Phase 1 Recall@3 < 0.75 | 需要转向 hybrid 方案（grep + embedding 混合检索） |
| Phase 2 的 token 效率无提升 | 批量匹配不需要特殊优化，按单条并行执行即可 |
| Phase 4 远低于 Phase 1（差距 > 0.20） | 手写查询存在严重确认偏差，真实场景更难——可能需要 hybrid 方案 |

---

## 十、v1 到 v2 的变更记录

| v1 问题 | v2 修正 |
|---------|--------|
| Q8 地面真值分类自相矛盾（C 类 vs 子维度） | 已验证：中央控制平面未记录为任何 Concept 的子维度，master.md 备注不准确，实际为纯 C 类 |
| Q10 地面真值指向不存在的 Concept（subsystem-assembly-visibility） | 删除该查询。design-seeds.md 不纳入语料 |
| Q3 期望 agent 执行不自然搜索路径（读 agent-loop-orchestration.md 尾部） | 保留查询但明确评分分离：检索成功 = 找到 hooks 关联，分类成功 = 正确定 D 类 |
| Q7 可能遗漏第三个候选（session-lifecycle-management） | 已确认：Q7（v2 改为 E2）的主候选明确为 context-compression + security，session-lifecycle 不相关 |
| 检索和分类混在一起评分 | 新增独立的分类得分，区分"搜到了但分错了"和"没搜到" |
| 只测单条查询，不测批量匹配 | 新增 Phase 2：相同 8 条查询在批量模式下执行，对比准确率和成本 |
| 单一 subagent 类型 | 明确批量匹配使用不同系统提示（要求去重 + 批量输出） |
| 无 token 成本测量 | 所有 phase 记录 grep 次数、read 次数、read 行数 |
| 只有手写查询（对着答案出题） | 新增 Phase 4：9 条真实抽样查询（从已有 problem-map 中抽取，改写措辞），与 Phase 1 手写查询形成对照组，量化确认偏差 |
| 没有真实管线验证 | 新增 Phase 5：第 4 仓库全链路验证（真正跑 ingest → Step 2 → Step 3），作为 Phase 1-4 结论的现场确认。标记为高资源消耗，可选执行 |
