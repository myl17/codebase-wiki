# Phase 2: 轴定位 — hermes-agent 设计选择 × openclaw 种子库

> 日期：2026-06-19
> 输入：hermes 草稿 32 条 + openclaw 种子库 22 条
> 操作：轴定位 → 候选 Concept 识别 → 反向检查

---

## 轴定位总览

| hermes 条目 | 匹配的 openclaw 条目 | 匹配类型 | 操作 |
|------------|---------------------|---------|------|
| 1. 编排多轮 agent 对话的单一切入点 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 2. 系统 prompt 内建自学习驱动 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 3. 平衡命令执行的安全性与流畅性 | #1 如何门控工具权限 | 同一轴-新位置 | 候选 Concept 升级 |
| 4. 发现和注册工具 (AST 扫描) | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 5. 抽象多消息平台的统一接口 | #8 分解 Channel Plugin 适配器接口 | 同一轴-新位置 | 候选 Concept 升级 |
| 6. 管理外部记忆后端的集成约束 | #6 管理上下文引擎和记忆能力的全局唯一性 | 同一轴-新位置 | 候选 Concept 升级 |
| 7. 组织工具为可组合的能力组 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 8. 管理对话上下文超出窗口时的压缩策略 | #14 防止 Context Window 不足导致截断失败 | 同一轴-新位置 | 候选 Concept 升级 |
| 9. 集成外部工具服务（MCP 协议） | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 10. 管理 agent 生命周期事件的扩展点 | #10 将生命周期 Hook 设计为扩展拦截面 | 同一轴-新位置 | 候选 Concept 升级 |
| 11. 管理可安装技能的互操作性 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 12. 管理外部 skill 的安全信任 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 13. 多轮对话中降低 token 成本 (prompt caching) | #13 设计 Prompt 缓存边界 | 同一轴-新位置 | 候选 Concept 升级 |
| 14. 分类管理工具的并行执行 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 15. 为不同复杂度查询路由模型 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 16. 管理 API 多凭证的速率限制 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 17. 限制 agent 单次任务计算预算 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 18. 管理可选依赖的优雅降级 | #19 管理重型可选依赖 | 同一轴-新位置 | 候选 Concept 升级 |
| 19. 选择核心 API SDK 的架构锁定 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 20. 实现依赖的可重复构建 | #18 区分版本锁定策略 | 同一轴-新位置 | 候选 Concept 升级 |
| 21. 运行时选择多种后端实现 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 22. 隔离测试环境以确保零残留 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 23. 选择测试的抽象层级 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 24. CI 中防范供给链攻击 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 25. 为特定场景精简 agent 的工具面 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 26. Gateway 模式下实现阻塞式审批 | #3 设计 Exec 类工具的审批流程 | 同一轴-新位置 | 候选 Concept 升级 |
| 27. 分离关注点防止单层膨胀 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 28. 管理日志的安全性和可追溯性 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 29. 管理后台进程的生命周期 | 无 | 新轴 | 新轴：仅 hermes—待观察 |
| 30. 记忆上下文跨 turn 预取 | #4 注入记忆到 LLM 上下文 | 同一轴-新位置 | 候选 Concept 升级 |
| 31. 选择上下文压缩的摘要预算 | #11 平衡 Context 压缩的可恢复性与压缩率 | 同一轴-新位置 | 候选 Concept 升级 |
| 32. 缓存模型元数据加速启动 | 无 | 新轴 | 新轴：仅 hermes—待观察 |

**统计**：hermes 32 条中，同一轴匹配 12 条（全部为 Type A 新位置），新轴 20 条。

---

## 候选 Concept 清单

以下仅列出操作类型为"候选 Concept 升级"（首次出现第二位置）的条目，共 12 条。

---

### 候选 Concept #1：tool-security-gating（工具执行-安全介入程度）

**操作类型**：首次出现第二位置

**标准化问题陈述**：如何在工具执行的关键路径上决定安全检查的介入程度——是统一管道还是分层可调节？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：不同部署场景的安全需求差异巨大（个人开发机 vs 生产容器 vs 共享服务器）
- 关切 2：安全门控延迟不应影响正常的消息处理吞吐——安全检查与性能是零和博弈
- 关切 3：多来源配置的叠加规则必须产生可预测的结果，而非隐式交互
- 关切 4：高风险工具需要额外用户确认回路，但低风险工具不应被同等阻塞
- 关切 5：审批决策本身需要成本——辅助 LLM 评估引入额外 token 开销和延迟
- 关切 6：审批状态的持久化粒度（once/session/always）影响安全性和便利性的平衡

**涉及的种子库条目**：openclaw 种子库 #1「如何门控工具权限」+ hermes 草稿 #3「如何平衡命令执行的安全性与流畅性」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 统一同步管道 | 安全性（所有工具调用必须在执行前经 5 层 allowlist/denylist 串行过滤）；可预测性（多来源配置叠加规则确定） | 灵活性（无快速路径，低风险工具也被同等检查）；审批成本（无分层，exec 类一律需 owner 审批） |
| hermes-agent | 三层渐进式审批 | 灵活性（Layer 0 快速路径/YOLO 模式 + Layer 1 Smart 辅助 LLM + Layer 2 Manual tirith 正则）；场景适配（不同部署安全策略可调节） | 一致性（不同 Layer 之间的边界依赖正则匹配和 LLM 判断，存在误判风险）；审批成本增量写入（审批状态 once/session/always 持久化管理复杂） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/agents/tool-policy-pipeline.ts:56-90`, `src/agents/tool-policy.ts:19-55` |
| hermes-agent | `tools/approval.py:586-922`, `tools/approval.py:219-284` |

---

### 候选 Concept #2：im-platform-adapter-granularity（消息平台适配-接口分解粒度）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在为多平台 IM 系统设计适配器接口时，如何决定接口的拆分粒度——是单一抽象基类还是多个可选小接口？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：不同 IM 平台的能力差异巨大——不是所有平台都支持所有操作，大而全的接口会迫使简单平台实现空方法
- 关切 2：核心对 channel 的调用路径（入站解析、出站发送、生命周期）需要统一的接口约定——拆分过细会破坏调用的一致性
- 关切 3：新增平台的工作量应与所需能力成正比——简单平台不应被迫实现复杂接口
- 关切 4：抽象基类需要覆盖消息收发、会话管理、媒体处理、打字指示等异构能力
- 关切 5：新增平台需要修改的代码点数量直接影响扩展成本（hermes 16 步 checklist vs openclaw 注册入口）

**涉及的种子库条目**：openclaw 种子库 #8「如何分解 Channel Plugin 的适配器接口」+ hermes 草稿 #5「如何抽象多消息平台的统一接口」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 13+ Adapter 分解 | 灵活性（每个平台只实现自己支持的能力维度，可选 adapter）；扩展成本（新增平台只需实现相关 adapter + 注册入口） | 接口一致性（不同平台 adapter 组合不同，调用路径的强制统一性较弱） |
| hermes-agent | 单一 ABC 继承 | 接口统一（`BasePlatformAdapter` 统一 connect/disconnect/send/send_typing/send_image/get_chat_info）；调用一致性（所有平台走同一抽象路径） | 灵活性和扩展成本（简单平台被迫实现空方法；新增平台需按 16 步 checklist 修改 16 处代码） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/channels/plugins/types.plugin.ts:53-94`, `src/plugin-sdk/channel-entry-contract.ts:31-60` |
| hermes-agent | `gateway/platforms/base.py:813-893` |

---

### 候选 Concept #3：global-capability-coexistence（全局能力-共存策略）

**操作类型**：首次出现第二位置

**标准化问题陈述**：当多个实现竞争同一全局能力（上下文引擎/记忆后端）时，如何决定它们之间的共存关系——是加性叠加还是替换式互斥？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：Context engine 决定所有 LLM 交互的 prompt 组装方式——同时存在多个必然产生冲突（正确性要求）
- 关切 2：加性叠加保证基础功能永不丢失但可能产生冗余存储
- 关切 3：替换式更简洁但可能丢失内置存储的稳定性保障
- 关切 4：注册顺序应可预测——后注册者覆盖前者的规则必须明确且一致
- 关切 5：Plugin 应能自由注册自己的实现——开放性要求允许多个 plugin 竞争注册

**涉及的种子库条目**：openclaw 种子库 #6「如何管理上下文引擎和记忆能力的全局唯一性」+ hermes 草稿 #6「如何管理外部记忆后端的集成约束」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | Exclusive 槽位覆盖注册 | 正确性（全局只能有一个活跃实现，避免冲突）；可预测性（后注册者明确覆盖前者） | 健壮性（如果注册的实现有问题，无内置兜底）；开放性（多个实现不能共存） |
| hermes-agent | 加性叠加 + 最多 1 个外部 provider | 健壮性（BuiltinMemoryProvider 始终启用，外部 provider 不能移除它）；开放性（允许外部实现叠加内置基础） | 简洁性（加性可能产生冗余存储）；可预测性（内置+外部的叠加顺序和去重逻辑更复杂） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/context-engine/index.ts:1-27`, `src/plugins/types.ts:1867-1990`, `src/memory-host-sdk/host/types.ts:1-30` |
| hermes-agent | `agent/memory_manager.py:1-27` |

---

### 候选 Concept #4：context-window-overflow-guard（上下文窗口-溢出防护触发策略）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在 token 计数不精确的前提下，如何决定上下文窗口溢出防护的压缩触发策略——是固定阈值还是多源保守选择？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：压缩阈值的选择——太早触发浪费 token（无需压缩时压缩），太晚触发有截断丢失风险
- 关切 2：Token 估算误差不可避免（尤其是工具输出的实际大小）——需留安全余量，但余量过大会过早触发压缩
- 关切 3：必须在多个来源中选最保守值——宁可过早触发压缩也不能溢出导致 API 调用失败
- 关切 4：不必要的压缩浪费 LLM 调用成本——过早压缩的经济代价

**涉及的种子库条目**：openclaw 种子库 #14「如何防止 Context Window 不足导致截断失败」+ hermes 草稿 #8「如何管理对话上下文超出模型窗口时的压缩策略」（阈值部分）

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 多源保守最小选择 | 安全性（硬下限 16,000 + 软警告 32,000，在 modelsConfig/model 自报/agentContextTokens 之间按优先级选最保守值）；兼容性（不同 model 的 context window 不同，动态适配） | 经济性（过度保守可能导致不必要的过早压缩，浪费 LLM 调用成本） |
| hermes-agent | 固定 75% 阈值 | 简单性（单一阈值规则易于理解和调优）；性能一致性（所有 model 统一行为） | 安全性（不同 model 的 context window 大小差异大，固定 75% 对大窗口 model 太早、对小窗口 model 可能太晚）；适配性（不同 model 的 token 估算精度不同但共用同一阈值） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/agents/context-window-guard.ts:4-81`, `src/agents/compaction.ts:19-40` |
| hermes-agent | `agent/context_engine.py:32-60` |

---

### 候选 Concept #5：lifecycle-hook-granularity（生命周期扩展-事件粒度）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在 agent 生命周期中设计 hook 系统的拦截粒度时，如何决定事件的拆分程度——是少数粗粒度事件还是密集覆盖全生命周期？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：Hook handler 可能修改核心数据（如 system prompt）——需明确区分可修改和只读的 hook
- 关切 2：事件粒度——过细增加 hook 实现者的负担，过粗限制扩展能力
- 关切 3：每个 hook 可注册多个 handler，执行顺序和失败处理需可预测
- 关切 4：Prompt 注入类 hook 是记忆等关键系统的唯一入口——稳定性和性能要求极高
- 关切 5：hook 中的错误不能阻塞主 pipeline
- 关切 6：hook 的发现机制（目录扫描 vs 显式注册）影响扩展的便利性和透明度

**涉及的种子库条目**：openclaw 种子库 #10「如何将生命周期 Hook 设计为扩展拦截面」+ hermes 草稿 #10「如何管理 agent 生命周期事件的扩展点」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 28 个细粒度命名 Hook | 覆盖面（从 `before_model_resolve` 到 `agent_end` 的完整链路，28 个命名事件）；拦截精度（每个阶段可独立拦截） | 复杂度（28 个 hook 名需要文档和记忆负担）；handler 发现（显式 `registerHook(events, handler)` 注册，增加扩展代码量） |
| hermes-agent | 8 个粗粒度事件 + 目录扫描 | 简单性（8 个生命周期事件易于理解和选择）；扩展便利性（目录扫描自动加载，零代码注册） | 拦截精度（粗粒度意味着 hook 内部需自行判断更细的阶段，增加 handler 内逻辑）；覆盖面（事件数少于 openclaw，一些生命周期节点无法拦截） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/plugins/hook-types.ts:55-84`, `src/plugins/hook-types.ts:128-133` |
| hermes-agent | `gateway/hooks.py:9-19`, `gateway/hooks.py:34-80` |

---

### 候选 Concept #6：prompt-cache-boundary（Prompt 缓存-边界划分策略）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在利用 LLM prompt caching 机制时，如何决定缓存边界的划分策略——是按消息类型切分还是按内容稳定性高低分离？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：尽可能多的 token 命中缓存以减少每轮 API 费用——缓存区越大越好
- 关切 2：动态内容（记忆注入、实时上下文）必须放在缓存边界之后，不能混入缓存区——动态内容的存在限制了缓存区上限
- 关切 3：cache breakpoint 数量受限于 provider（Anthropic 上限 4 个）——需权衡 system prompt 占用几个、历史消息占用几个
- 关切 4：不同 LLM 平台的缓存 TTL 策略不同——边界设计需兼容多平台
- 关切 5：跨消息复用 agent 实例才能保持 cache prefix 有效

**涉及的种子库条目**：openclaw 种子库 #13「如何设计 Prompt 缓存边界」+ hermes 草稿 #13「如何在多轮对话中降低 token 成本」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 稳定前缀 + 动态后缀分离 | 缓存命中率（system prompt 中 `<!-- OPENCLAW_CACHE_BOUNDARY -->` 标记前的内容全部可缓存，稳定前缀尽可能大）；多平台兼容（根据不同 endpoint 决定 TTL 策略） | Breakpoint 数量利用（只用了 1 个 cache breakpoint 在 boundary 处，未利用剩余 breakpoint 配额） |
| hermes-agent | system_and_3（4 breakpoints） | Breakpoint 配额最大化利用（4 个全用：system prompt 1 个 + 最后 3 条非 system 消息滚动窗口 3 个）；跨 turn 复用（GatewayRunner 缓存 AIAgent 实例保持 cache prefix） | 缓存区稳定性（滚动窗口中的消息可能包含 tool_result 等动态内容，降低缓存命中稳定性） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/agents/system-prompt-cache-boundary.ts:3-47`, `src/agents/anthropic-payload-policy.ts:37-65` |
| hermes-agent | `agent/prompt_caching.py:1-73`, `gateway/run.py:604-611` |

---

### 候选 Concept #7：approval-blocking-mechanism（审批-阻塞等待机制）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在高风险命令需要用户审批时，如何决定 agent 线程的阻塞等待机制——是同步阻塞还是异步可中断等待？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：审批必须是同步阻塞的——不能在命令执行后才通知用户（安全性要求前置审批）
- 关切 2：阻塞等待不应死锁 agent 进程——需要超时、取消和多审批并发能力
- 关切 3：审批可通过多种路径到达用户（CLI / Gateway HTTP / chat reply）——路径选择应对 core 透明
- 关切 4：审批失败或超时不应导致 agent session 永久卡死——容错性要求优雅降级
- 关切 5：并行子 agent 的审批请求需要独立队列和独立等待

**涉及的种子库条目**：openclaw 种子库 #3「如何设计 Exec 类工具的审批流程」+ hermes 草稿 #26「如何在 Gateway 模式下实现阻塞式审批」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 异步阻塞双路径审批 | 不占事件循环（`waitForExecApprovalDecision` 是可中断的异步等待，不占用 Node.js event loop）；多路径（host CLI + gateway HTTP 双通道） | 实现复杂度（异步阻塞模式的 Promise 管理比同步 Event 更复杂） |
| hermes-agent | FIFO 队列 + threading.Event | 多审批并发（每个子 agent 独立 `threading.Event`，并行等待不互相干扰）；简单性（FIFO 队列 + Event 阻塞是 Python 标准同步原语） | 线程资源占用（同步阻塞占用一个 Python 线程，大量并发审批时线程数膨胀）；路径单一（Gateway 模式下依赖用户 `/approve` 聊天回复） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/agents/bash-tools.exec-approval-request.ts:89-126`, `src/agents/tool-policy.ts:19-55` |
| hermes-agent | `tools/approval.py:219-284`, `tools/approval.py:586-922` |

---

### 候选 Concept #8：memory-retrieval-timing（记忆-检索与注入时机）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在多轮对话中，如何决定记忆检索与注入 LLM 上下文的时机——是在 prompt 组装阶段批量注入还是后台异步预取？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：记忆内容的新鲜度——实时检索可获取最新记忆，避免使用过时信息
- 关切 2：Prompt 组装阶段的确定性——如果记忆内容在 prompt 构建后变化，可能导致行为不一致
- 关切 3：同步检索会增加用户感知延迟（等待记忆检索完成后才能调用 LLM）
- 关切 4：多个记忆后端并存——注入时机需兼容多种检索延迟
- 关切 5：异步预取返回的是上一轮的结果——可能已过时

**涉及的种子库条目**：openclaw 种子库 #4「如何注入记忆到 LLM 上下文」+ hermes 草稿 #30「如何记忆上下文跨 turn 预取」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | Prompt 组装阶段批量注入 | 确定性（记忆在 Context Engine `assemble` 阶段注入，同一次 LLM 调用期间 prompt 内容不变）；多后端兼容（hook 机制适配多种检索延迟） | 新鲜度（同一次 LLM 调用期间新增的记忆在当前轮不可见） |
| hermes-agent | 后台预取 + 不阻塞关键路径 | 延迟（`queue_prefetch()` 在当前 turn 完成后后台线程触发，下一轮 `prefetch()` 返回缓存结果——不阻塞 API 调用前的关键路径） | 新鲜度（记忆可能不是最新状态——上一轮完成后写入的新记忆在当前轮不可见）；确定性（缓存结果可能在两轮之间被修改） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/memory-host-sdk/host/types.ts:1-30`, `src/context-engine/index.ts:1-27` |
| hermes-agent | `agent/memory_provider.py:92-112` |

---

### 候选 Concept #9：compression-resource-allocation（上下文压缩-资源分配策略）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在对对话历史进行压缩时，如何决定压缩的资源分配策略——是优先保留任务可恢复性还是用定量预算控制成本？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：压缩后摘要必须保留足够信息使 agent 可恢复任务执行——信息保留与 token 削减直接冲突
- 关切 2：高压缩率必然损失细节——压缩率与保真度的零和关系
- 关切 3：工具输出通常冗长但对后续决策价值低，需特殊处理策略
- 关切 4：Token 估算存在固有误差——压缩参数需包含安全余量
- 关切 5：压缩失败后的冷却期——防止摘要失败触发重试风暴
- 关切 6：用户通知不能注入 LLM——避免模型因感知到上下文压力而提前放弃

**涉及的种子库条目**：openclaw 种子库 #11「如何平衡 Context 压缩的可恢复性与压缩率」+ hermes 草稿 #31「如何选择上下文压缩的摘要预算」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 可恢复性优先压缩 | 任务连续性（摘要指令优先保留活跃任务状态、批处理进度、最后一次用户请求）；成本控制（`tool_result.details` strip + `SAFETY_MARGIN = 1.2` 补偿 token 估算误差） | 历史细节完整性（为保留可恢复性牺牲了对话历史的细节保真度） |
| hermes-agent | 20% 定量预算 + 600s 冷却 | 成本可控（摘要预算明确上限——压缩内容的 20%、上限 12,000 tokens——可精确计算成本）；系统稳定性（压缩失败后 600s 冷却防重试风暴；用户通知分层 85%/95% 但不注入 LLM） | 信息丢失风险（定量预算不考虑信息重要性排序——可能 20% 预算不足以保留关键任务状态） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/agents/compaction.ts:19-40`, `src/context-engine/index.ts:1-27` |
| hermes-agent | `agent/context_compressor.py:51-53`, `agent/context_compressor.py:60` |

---

### 候选 Concept #10：optional-dependency-layering（可选依赖-分层管理策略）

**操作类型**：首次出现第二位置

**标准化问题陈述**：当系统需要支持可选功能（消息/记忆/语音/浏览器/搜索/容器运行时等）且对应依赖体积差异巨大时，如何决定可选依赖的分层策略——是统一降级还是按安装成本分层？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：默认安装不应拉入 GB 级二进制或复杂原生模块——默认体验的轻量性是用户留存的基础
- 关切 2：ImportError 检查点需要遍布所有使用可选依赖的代码路径，遗漏一处即崩溃
- 关切 3：降级行为需要明确告知用户（哪些功能因缺失依赖而不可用）
- 关切 4：条件依赖（特定 OS 或 Python 版本才可用）需要在包管理层面表达
- 关切 5：需要重型功能的用户必须清楚知道需要额外安装步骤——可发现性与轻量默认之间的张力

**涉及的种子库条目**：openclaw 种子库 #19「如何管理重型可选依赖」+ hermes 草稿 #18「如何管理可选依赖的优雅降级」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | Peer + Optional 依赖分层 | 轻量默认（GB 级 `node-llama-cpp` 设为 peer dependency 由用户显式安装，不会默认拉入）；用户知晓权（peer dep 安装时 npm 显式提示） | 可发现性（用户可能不知道需要额外安装 peer dep，首次使用时才报错）；降级覆盖（optional dep 数量有限，主要是编解码器） |
| hermes-agent | ImportError 降级 + 20+ extras 分组 | 健壮性（所有可选依赖遵循 ImportError 捕获后优雅降级模式，绝不因缺少可选包而启动失败）；按需安装（pyproject.toml 20+ extras 将单体重安装拆分为按需功能组） | 检查点覆盖（ImportError 检查点需遍布所有使用可选依赖的代码路径，遗漏一处即崩溃）；用户感知（降级行为需在每个降级点显式告知用户） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `package.json` (peerDependencies, optionalDependencies) |
| hermes-agent | `pyproject.toml:39-115` |

---

### 候选 Concept #11：dependency-version-locking（依赖版本-锁定粒度）

**操作类型**：首次出现第二位置

**标准化问题陈述**：在管理项目依赖时，如何决定版本锁定的粒度——是全部精确锁定、全部范围版本，还是按风险级别分类锁定？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：协议 SDK 的不兼容变更直接导致功能故障——高风险依赖必须精确锁定
- 关切 2：有 native addon 的包版本敏感——编译失败难以排查，精确锁定降低风险
- 关切 3：核心引擎的 breaking change 影响全局——必须精确锁定
- 关切 4：工具类库的 patch 变更不影响行为——范围版本可降低维护负担
- 关切 5：版本范围的宽松程度——太松可重复性差，太紧更新成本高
- 关切 6：容器层的可重复性——Docker 基础镜像也需固定
- 关切 7：不内嵌第三方源码（no vendor）——完全依赖包管理器的 lockfile

**涉及的种子库条目**：openclaw 种子库 #18「如何区分版本锁定策略」+ hermes 草稿 #20「如何实现依赖的可重复构建」

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | 风险分级锁定 | 精准控制（29/70 精确锁定高风险包：协议 SDK、native addon、核心引擎；41/70 范围版本用于工具库）；维护负担（工具类库用范围版本允许自动 patch 更新） | 可重复性（范围版本的工具库在不同时间安装结果可能不同，依赖 lockfile 兜底但范围语义本身不保证确定性） |
| hermes-agent | 三层统一锁定 | 可重复性（所有核心依赖 `>=lower,<upper` 双边界定 + `uv.lock` 5512 行全依赖树 hash + Docker SHA256 固定基础镜像——三重保证安装结果一致）；无 vendor/bundle 策略（完全依赖 PyPI + lockfile） | 更新成本（所有依赖收紧在双边界定内，版本更新需手动调整范围并重新锁定） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `package.json` (dependencies 精确/范围分布) |
| hermes-agent | `pyproject.toml:15-37`, `uv.lock`, `Dockerfile:1-3,38-39` |

---

### 候选 Concept #12：context-engine-pluggability（上下文压缩-可插拔架构）

**操作类型**：首次出现第二位置

**说明**：此候选 Concept 提取自 hermes #8 的另一面——不仅决定何时触发压缩（见候选 Concept #4），还决定压缩引擎本身的架构：是策略模式可插拔替换，还是共享基础设施仅替换参数？hermes #8 捆绑了两个设计选择——此处提取「压缩引擎的架构可替换性」单独形成轴。

**标准化问题陈述**：当上下文压缩需要在不同场景使用不同策略时，如何决定压缩引擎的架构——是策略模式允许完全替换引擎实现，还是在共享基础设施内仅配置参数？

**核心关切**（综合两仓库，合并去重）：
- 关切 1：第三方可扩展性——社区能否提供自己的压缩策略实现并即插即用
- 关切 2：同一时间只有一个 engine 激活——多个压缩策略同时运行必然冲突
- 关切 3：压缩引擎的注册机制——是通过配置显式选择还是通过注册 API 竞争覆盖
- 关切 4：引擎替换对核心代码的影响——新增引擎是否需修改 core

**涉及的种子库条目**：openclaw 种子库 #6「如何管理上下文引擎和记忆能力的全局唯一性」（context engine 部分）+ hermes 草稿 #8「如何管理对话上下文超出模型窗口时的压缩策略」（可插拔部分）

**各仓库权衡位置**：

| 仓库 | 权衡位置名称 | 优先满足的关切 | 接受妥协的关切 |
|------|------------|--------------|--------------|
| openclaw | Exclusive 槽位覆盖注册 | 第三方扩展（ContextEngineFactory 注册即可，不改 core）；注册规则明确（后注册覆盖前者，`LegacyContextEngine` 向后兼容） | 显式选择（无法通过配置直接指定引擎——依赖注册顺序，行为可能因加载顺序不同而变化） |
| hermes-agent | 策略模式 + 目录发现 | 显式选择（第三方放入 `plugins/context_engine/<name>/` 目录，config.yaml 指定激活哪个）；发现机制（目录扫描自动发现所有可用实现） | 扩展便利性（需创建目录结构 + 实现 ContextEngine ABC + 配置文件指定，比注册回调多步骤） |

**溯源**：

| 仓库 | 必须读的源码文件 |
|------|----------------|
| openclaw | `src/context-engine/index.ts:1-27`, `src/plugins/types.ts:1867-1990` |
| hermes-agent | `agent/context_engine.py:32-60` |

---

## 反向检查：openclaw 种子库"仅 openclaw—待观察"条目

以下对 openclaw 种子库中未匹配 hermes 的条目逐条检查 hermes 是否面对同一问题。

---

### openclaw #2：如何在消息驱动的 AI 助手中创建主动触发路径

**检查结果**：保持仅 openclaw—待观察

**分析**：hermes 的架构是中央 AIAgent 编排器——所有入口（CLI/Gateway/Cron/ACP）都通向同一编排循环。Cron 在 hermes 中只是又一个入口，不需要创建独立的主动触发路径。openclaw 是纯粹的消息驱动模型，Cron 是唯一无消息触发的入口，因此需要专门设计。hermes 不面对此问题。

---

### openclaw #5：如何选择 LLM Provider 的实现

**检查结果**：保持仅 openclaw—待观察

**分析**：hermes #19 选择 OpenAI SDK 作为统一路由层——所有 20+ provider 都通过 openai SDK 通信（利用 OpenAI-compatible 协议）。这个架构选择消除了运行时 provider harness 选择的问题——不存在多个 harness 竞争同一 model 的场景。hermes 在开发时做了 SDK 锁定（这是另一个轴，见 hermes #19 新轴），因此不面对 openclaw 的运行时 harness 选择问题。

---

### openclaw #7：如何在无代码情况下扩展 Agent 行为

**检查结果**：保持仅 openclaw—待观察

**分析**：hermes 的 skills 系统基于 agentskills.io 开放标准，skill 是代码文件（需要安装和扫描）。hermes 没有 markdown 文本文件即 skill 的零代码扩展机制。hermes #11（skills 互操作性）和 #12（skill 安全信任）是关于代码 skill 的不同维度。openclaw 的 markdown skills 是独特的扩展范式，hermes 不面对此问题。

---

### openclaw #9：如何提供 Plugin SDK 的双入口模式

**检查结果**：保持仅 openclaw—待观察

**分析**：hermes 没有正式的 plugin SDK。扩展通过 hooks（目录扫描）、toolsets（配置定义）、skills（agentskills.io）和 tools（AST 扫描注册）实现——但这些都不是一个统一的 plugin SDK 框架。没有轻量/重量级双入口的设计问题。hermes 不面对此问题。

---

### openclaw #12：如何优化冷启动速度

**检查结果**：保持仅 openclaw—待观察

**分析**：openclaw 是 Node.js 项目，冷启动优化的核心是 V8 compile cache + lazy runtime module + channel entry 懒加载——这是 Node.js 特有的技术栈。hermes 是 Python 项目，启动优化不同（Python import 时间、字节码缓存 `.pyc`）。hermes #32（模型元数据缓存）解决的是启动时避免网络阻塞，而非冷启动速度本身的综合优化。两个问题的技术约束和优化手段不同，属不同轴。

---

### openclaw #15：如何管理消息入站的突发流

**检查结果**：保持仅 openclaw—待观察

**分析**：hermes Gateway 处理多平台 IM 消息入站，但未将消息防抖合并作为显式设计选择。hermes 的中央 AIAgent 编排器逐条处理消息，没有显式的防抖窗口。可能 hermes 确实面对消息突发问题但未将其提升为设计选择——但这属于"面对但漏提"的潜在补充项。当前证据不足，保持 openclaw 独有。

---

### openclaw #16：如何选择 AI 引擎依赖策略

**检查结果**：保持仅 openclaw—待观察

**分析**：openclaw 深度绑定 `@mariozechner/*` 私有包族（pi-ai/pi-agent-core/pi-coding-agent/pi-tui），442 处 import。hermes 自己就是 agent 引擎——AIAgent 是自建的编排器（11510 行单文件），不依赖外部 agent 引擎。hermes 选择了"自建引擎"路径，而 openclaw 选择了"绑定外部引擎"路径。但"自建 vs 绑定"的选择已经反映在 hermes #1（中央编排器）和 openclaw #16 各自代表了不同的架构范式，不构成同一轴的竞争位置。保持 openclaw 独有。

---

### openclaw #17：如何隔离 Channel SDK 故障域

**检查结果**：保持仅 openclaw—待观察

**分析**：openclaw 是 monorepo，每个 channel extension 在自身 package.json 中独立声明 SDK 依赖，不在 root package 聚合。hermes 是单体仓库，所有依赖在同一个 pyproject.toml 中声明（通过 extras 分组而非独立包）。hermes 通过 #18（优雅降级）解决依赖缺失问题，但不是通过包级别的故障域隔离。架构差异（monorepo vs monolith）决定了不同的依赖管理策略，属不同轴。保持 openclaw 独有。

---

### openclaw #20：如何将架构边界约束从文档变为可执行检查

**检查结果**：保持仅 openclaw—待观察

**分析**：openclaw 通过 20+ 专项 lint 脚本（`lint:extensions:no-src-outside-plugin-sdk`、`lint:plugins:no-extension-imports` 等）将架构边界编码为 CI gate。hermes 是 Python 单体项目，没有显式的架构边界 lint 检查。hermes #24（CI 供给链审计）关注的是安全维度的恶意代码检测，而非架构边界约束。hermes 可能面对此问题但未将其提升为设计选择。保持 openclaw 独有。

---

### openclaw #21：如何保证 Plugin 接口稳定性

**检查结果**：保持仅 openclaw—待观察

**分析**：openclaw 通过共享 test suite（`installChannelActionsContractSuite(...)` 等）自动覆盖所有注册 plugin。hermes 没有正式的 plugin 系统——hooks/toolsets/skills/tools 各有一套独立的扩展机制，没有统一的契约测试框架。hermes 不面对"如何为 plugin 系统设计契约测试"的问题。

---

### openclaw #22：如何将性能预算纳入 CI 门控

**检查结果**：保持仅 openclaw—待观察

**分析**：openclaw 有 CLI 冷启动时间基准 fixture（`test/fixtures/cli-startup-bench.json`）和独立 CI 检查。hermes 没有显式的性能预算 CI 门控。hermes 不面对此问题。

---

## 新轴清单

### hermes 独有新轴（20 条，全部标记为"仅 hermes—待观察"）

| # | 条目 | 维度 | 核心关切验证 | 状态 |
|---|------|------|------------|------|
| 1 | 编排多轮 agent 对话的单一切入点 | Architecture | 2 个制约关切（集中编排避免分叉 vs 单文件膨胀 11510 行 + 单点故障无替换） | 合法新轴 |
| 2 | 系统 prompt 内建自学习驱动 | Architecture | 3 个制约关切（触发主动性 vs 虚假记忆风险，三个时间尺度的工具/路径差异，自建 skill 安全边界） | 合法新轴 |
| 4 | 发现和注册工具 (AST 扫描) | Architecture/Extension Points | 3 个制约关切（自动发现零接线 vs AST 扫描启动开销 + 静态调用限制） | 合法新轴 |
| 7 | 组织工具为可组合的能力组 | Extension Points | 3 个制约关切（组合粒度粗细、递归 include 去重循环检测、核心修改传播） | 合法新轴 |
| 9 | 集成外部工具服务（MCP 协议） | Extension Points | 3 个制约关切（自动重连 vs 资源消耗、双向通信安全、凭据脱敏） | 合法新轴 |
| 11 | 管理可安装技能的互操作性 | Extension Points | 3 个制约关切（开放标准互操作 vs 表达力约束、外部 skill 安全扫描、自我改进能力） | 合法新轴 |
| 12 | 管理外部 skill 的安全信任 | Architecture/Extension Points | 3 个制约关切（信任分级粒度、威胁模式覆盖面 100+、自建 skill 安全处理） | 合法新轴 |
| 14 | 分类管理工具的并行执行 | Performance Tradeoffs | 3 个制约关切（只读天然并行 vs 文件路径隐式依赖、破坏性命令正则匹配漏检、交互式工具阻塞） | 合法新轴 |
| 15 | 为不同复杂度查询路由模型 | Performance Tradeoffs | 3 个制约关切（误判代价非对称——复杂→弱模型代价更大、分类特征准确率有限、保守策略倾向） | 合法新轴 |
| 16 | 管理 API 多凭证的速率限制 | Performance Tradeoffs | 3 个制约关切（轮换策略 vs 配额利用率、被动追踪 vs 主动限流、多 key 管理复杂度） | 合法新轴 |
| 17 | 限制 agent 单次任务计算预算 | Performance Tradeoffs | 3 个制约关切（grace call vs 硬终止、退款机制、预算告警是否注入 LLM） | 合法新轴 |
| 19 | 选择核心 API SDK 的架构锁定 | Dependency Strategy | 3 个制约关切（单 SDK 简化 vs 架构锁定风险、多 SDK 维护代价、OpenAI-compatible 生态覆盖率） | 合法新轴 |
| 21 | 运行时选择多种后端实现 | Dependency Strategy/Extension Points | 3 个制约关切（自动发现 vs 显式配置、子系统替换粒度、降级优先级） | 合法新轴 |
| 22 | 隔离测试环境以确保零残留 | Testing Philosophy | 3 个制约关切（单例跨测试泄漏、敏感 key 误用、失控测试保护） | 合法新轴 |
| 23 | 选择测试的抽象层级 | Testing Philosophy | 3 个制约关切（行为接口覆盖不足 vs 实现细节大面积失效、mock 边界） | 合法新轴 |
| 24 | CI 中防范供给链攻击 | Testing Philosophy/Dependency Strategy | 3 个制约关切（PR 阶段阻断时机、检测模式覆盖面、CI 集成） | 合法新轴 |
| 25 | 为特定场景精简 agent 的工具面 | Performance Tradeoffs/Extension Points | 3 个制约关切（独立维护 vs 派生工具集、功能不完整、维护责任归属） | 合法新轴 |
| 27 | 分离关注点防止单层膨胀 | Architecture | 3 个制约关切（配置加载时序、PII 保护、资源隔离） | 合法新轴 |
| 28 | 管理日志的安全性和可追溯性 | Architecture | 3 个制约关切（40+ 脱敏模式覆盖面、截获时机、多组件路由） | 合法新轴 |
| 29 | 管理后台进程的生命周期 | Architecture | 3 个制约关切（崩溃恢复、缓冲容量、并发上限 LRU） | 合法新轴 |
| 32 | 缓存模型元数据加速启动 | Performance Tradeoffs | 2 个制约关切（缓存过期信息不准确 vs 启动速度、TTL 选择 1h） | 合法新轴（边界：关切数量刚好 ≥2） |

### openclaw 独有新轴（保持"仅 openclaw—待观察"，共 11 条）

| # | 条目 | 维度 | 保持原因 |
|---|------|------|---------|
| 2 | 消息驱动架构中的主动触发路径 | Architecture | hermes 的中央编排器架构不区分"消息驱动"和"主动触发"——cron 只是又一个入口，不面对同一问题 |
| 5 | LLM Provider harness 运行时选择 | Extension Points | hermes 的 OpenAI SDK 统一路由消除了多 harness 竞争的问题——架构层面的不同选择使此轴不适用 |
| 7 | 零代码 Markdown 扩展 | Extension Points | hermes 的 skills 基于 agentskills.io 代码标准，没有 markdown 扩展机制 |
| 9 | Plugin SDK 双入口模式 | Extension Points | hermes 没有统一的 plugin SDK 框架，不面对轻量/重量级双入口设计问题 |
| 12 | 冷启动速度优化 (Node.js) | Performance Tradeoffs | Node.js 特有的 V8 compile cache/lazy loading 优化手段与 Python 启动优化本质不同 |
| 15 | 消息入站防抖合并 | Performance Tradeoffs | hermes 未将消息防抖作为显式设计选择——可能是"面对但漏提"的补充项，当前证据不足 |
| 16 | AI 引擎依赖策略（绑定外部引擎） | Dependency Strategy | hermes 自建引擎（AIAgent），与 openclaw 绑定 `@mariozechner` 的思路不在同一轴上——"自建 vs 绑定"本身是更上层的架构选择 |
| 17 | Channel SDK 故障域隔离 (monorepo) | Dependency Strategy | hermes 是单体仓库，不面对 monorepo 中 per-channel package dependency isolation 问题 |
| 20 | 架构边界约束 CI lint | Testing Philosophy | hermes 没有将架构边界编码为 CI 检查——可能是未来补充项 |
| 21 | Plugin 接口契约测试 | Testing Philosophy | hermes 没有统一的 plugin 系统，不面对契约测试问题 |
| 22 | 性能预算 CI 门控 | Testing Philosophy | hermes 没有性能预算 CI 检查——可能是未来补充项 |

---

## 无法匹配的条目总结

### hermes 草稿中无法匹配的条目（20 条新轴）

以上"hermes 独有新轴"表格中的全部 20 条均标记为"仅 hermes—待观察"。

### openclaw 种子库中无法匹配的条目（11 条保持待观察）

以上"openclaw 独有新轴"表格中的全部 11 条均保持"仅 openclaw—待观察"。

### 验证说明

两条目可能看起来相关但判定为不同轴的情况：

1. **hermes #19 (OpenAI SDK 锁定) vs openclaw #5 (Provider harness 选择)**：hermes #19 是开发时依赖选择（单 SDK vs 多 SDK），openclaw #5 是运行时选择机制（多个已注册 harness 中选最优）。hermes 的选择使 openclaw #5 的问题不再存在（没有多 harness 竞争），属于架构层面的不同前提。

2. **hermes #29 (后台进程生命周期) vs openclaw 任务流**：hermes 管理的是通用后台进程（terminal background=true），openclaw 的 task-executor 管理的是 agent 任务流。能力域不同（通用进程 vs agent 任务），不做强行配对。

3. **hermes #27 (六层分离) vs openclaw 架构分层**：hermes 有显式的六层分离架构，openclaw 有多层架构但未将其作为显式设计选择录入种子库。这反映两个仓库在架构文档化程度上的差异——openclaw 的架构分离可能存在于代码中但未被提取为设计选择。

---

## 统计

| 指标 | 数量 |
|------|------|
| hermes 草稿总条目 | 32 |
| openclaw 种子库总条目 | 22 |
| 同一轴匹配 (Type A 新位置) | 12 |
| 同一轴匹配 (Type B 同位置) | 0 |
| hermes 独有新轴 | 20 |
| openclaw 独有保持待观察 | 11 |
| 候选 Concept 升级 | 12 |
| 新增 openclaw 条目（反向检查补充） | 0 |

> 注：hermes #8 同时参与候选 Concept #4（溢出防护阈值）和候选 Concept #12（压缩引擎可插拔架构），因为它捆绑了两个独立的设计选择。这是草稿条目粒度导致的——一个条目覆盖了两个不同轴的决策。
