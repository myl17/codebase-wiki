# Hermes 设计选择草稿

> 提取自 hermes Entity 页（2026-06-17）

---

## Agent 编排模型

**维度**：Architecture
**问题陈述**：如何在多工具系统中管理 LLM 交互循环，同时支持 failover 路由、子 agent 委派和资源预算控制？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 单一中央编排器 | AIAgent 作为唯一编排点管理完整 tool-calling 循环，避免各工具模块重复处理 LLM 协议差异 | entity/hermes-ai-agent.md → run_agent.py:535（入口）、run_agent.py:8130-8189（对话循环入口） |

---

## 工具执行并发策略

**维度**：Performance Tradeoffs
**问题陈述**：如何在保证安全的前提下最大化工具执行的并发度？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 并行执行（8 线程），破坏性命令强制串行 | 只读工具无共享状态可并行降低延迟；含 rm/mv/sed -i 等破坏性命令必须串行执行防并发冲突 | entity/hermes-ai-agent.md → run_agent.py:214-311 |

---

## 对话轮次预算控制

**维度**：Performance Tradeoffs
**问题陈述**：如何防止 agent 陷入无限循环消耗 token，又避免预算警告导致模型过早放弃任务？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 硬上限 + 一次 grace call，预算信息不注入 LLM | 父 agent 90 轮、子 agent 50 轮硬上限；耗尽时给一次完成机会；不向 LLM 注入预算警告（之前注入导致模型过早放弃） | entity/hermes-ai-agent.md → run_agent.py:170-199 |

---

## 命令安全审批层级

**维度**：Architecture
**问题陈述**：如何在自动化安全和用户体验之间取得平衡，避免消息平台场景下纯人工审批不可行？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 三层审批（YOLO → Smart → Manual） | 便宜辅助 LLM 自动处理明显安全/危险的命令，模糊情况才升级到人工审批，降低用户疲劳 | entity/hermes-approval-system.md → tools/approval.py:586-922（主入口）、tools/approval.py:534-583（Smart 层） |

---

## 审批结果持久化策略

**维度**：Performance Tradeoffs
**问题陈述**：如何在减少重复审批和保持安全审查之间取得平衡？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 三级持久化（once/session/always），always 写入 config.yaml allowlist | 常用命令一次审批永久生效；allowlist 需人工维护审查，但消除重复审批摩擦 | entity/hermes-approval-system.md → tools/approval.py:299-303（session）、tools/approval.py:376-402（always） |

---

## 危险命令检测机制

**维度**：Architecture
**问题陈述**：如何可靠地拦截高危操作而不依赖 LLM 判断的准确性？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 25+ 危险模式正则作为主防线，LLM 判断作为补充 | 正则确定性匹配（rm/chmod/curl\|sh/kill/systemctl/git reset --hard 等），不受 LLM 幻觉影响，与 tirith 结果合并审批 | entity/hermes-approval-system.md → tools/approval.py:75-138 |

---

## 长对话上下文管理

**维度**：Performance Tradeoffs
**问题陈述**：如何让 agent 处理超过单次 context window 的长对话，同时保留对话的语义连续性？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 辅助 LLM 摘要中间轮次，牺牲信息保真度换取无限长对话 | 结构化摘要模板 + token-budget tail 保护 + 工具输出修剪（先剪后摘要）；摘要 budget 为压缩内容的 20%，上限 12,000 tokens；失败冷却 600 秒 | entity/hermes-context-engine.md → agent/context_compressor.py:1-60、agent/context_compressor.py:51-53（budget）、agent/context_compressor.py:60（冷却） |

---

## 上下文压力通知策略

**维度**：Performance Tradeoffs
**问题陈述**：如何通知上下文耗尽风险而不干扰 agent 完成任务？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 85%/95% 阈值各通知一次用户，不注入 LLM | 用户需要知道压缩发生，但 LLM 不应感受压力（实验发现向 LLM 发送 context 警告会导致提前放弃未完成任务） | entity/hermes-context-engine.md → agent/context_engine.py:59 |

---

## 上下文压缩策略的可扩展性

**维度**：Extension Points
**问题陈述**：如何让不同场景使用最适合的上下文压缩策略？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | ContextEngine ABC 接口，第三方实现放入 plugins/context_engine/ | 不同场景需求不同（代码场景需保留代码块、对话场景重语义连续性）；插件化允许外部开发者实验不同压缩算法 | entity/hermes-context-engine.md → agent/context_engine.py:32-60 |

---

## 跨消息 Agent 实例复用

**维度**：Architecture
**问题陈述**：如何在多消息场景下降低 LLM API 的 input token 成本？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 跨消息缓存 AIAgent 实例，非每条消息新建 | 复用实例保持 LLM API 层的 prompt cache prefix 在跨消息对话中持续有效，降低 input token 成本 | entity/hermes-gateway-platform.md → gateway/run.py:604-611 |

---

## 多平台适配架构

**维度**：Architecture
**问题陈述**：如何为 20+ 消息平台提供统一的接入接口，同时确保所有集成点感知新平台的存在？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | BasePlatformAdapter 统一基类，新增平台需修改 16 处配置点 | 统一接口确保 toolset、认证映射、cron delivery 等跨平台逻辑只写一次；16 处修改点保证不遗漏集成点 | entity/hermes-gateway-platform.md → gateway/platforms/base.py:813-893 |

---

## Gateway 环境下的审批等待策略

**维度**：Architecture
**问题陈述**：如何在异步消息平台环境下处理需要用户审批的等待——阻塞 vs 超时自动拒绝？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | FIFO 队列 + threading.Event 阻塞等待用户 /approve 或 /deny | 消息平台场景用户不在场时间长，自动超时拒绝会中断合法任务；阻塞等待保证审批机会，代价是 agent 线程占用 | entity/hermes-gateway-platform.md → tools/approval.py:219-284 |

---

## 记忆系统的可靠性保障

**维度**：Architecture
**问题陈述**：如何确保基础记忆功能不因外部服务配置错误而失效？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | BuiltinMemoryProvider 始终启用且不可移除，外部 provider 加性扩展 | 内置记忆保证基础功能始终可用；外部 provider（Honcho/Mem0 等 7 种）提供增强能力，但不能造成基础功能空白 | entity/hermes-memory-manager.md → agent/memory_provider.py:42-232 |

---

## 记忆检索的延迟优化

**维度**：Performance Tradeoffs
**问题陈述**：如何避免记忆检索（尤其是外部 provider 的网络延迟）阻塞 LLM API 调用的关键路径？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 后台异步预取（queue_prefetch），下一轮使用上一轮完成后的缓存结果 | 记忆检索不在 LLM API 调用关键路径上阻塞；代价是记忆可能落后一轮 | entity/hermes-memory-manager.md → agent/memory_provider.py:106-112 |

---

## 记忆系统的可扩展性

**维度**：Extension Points
**问题陈述**：如何让外部记忆系统感知 agent 的关键状态变化，而不仅仅限于读写操作？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | MemoryProvider ABC 暴露 15+ 生命周期回调 | on_pre_compress（压缩前提取重要信息防丢失）、on_delegation（观察子 agent 输出）等 hook 让外部 provider 精准感知状态变化 | entity/hermes-memory-manager.md → agent/memory_provider.py:42-232 |

---

## 日志安全脱敏

**维度**：Architecture
**问题陈述**：如何防止 API 密钥通过 agent 日志泄露，尤其是在日志记录所有工具调用参数的场景下？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 40+ API key 前缀模式写入时实时脱敏，密钥永不落盘 | 不依赖开发者手动脱敏；写入时脱敏消除"先写后脱敏"窗口期的泄露风险 | entity/hermes-observability.md → hermes_logging.py:1-391、agent/redact.py:1-60 |

---

## 日志文件组织策略

**维度**：Architecture
**问题陈述**：如何在多组件系统中高效定位问题，支持跨组件追踪单个用户会话的完整链路？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 三路日志（主日志/错误日志/网关日志）+ session_id 标签注入 | 按组件分离让错误排查直接看 errors.log，网关问题看 gateway.log；session_id 标签让跨组件追踪单个会话链路成为可能 | entity/hermes-observability.md → hermes_logging.py:72-119 |

---

## 后台进程输出管理

**维度**：Performance Tradeoffs
**问题陈述**：如何在内存可控的前提下提供后台进程输出的随时查询能力？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 200KB 滚动缓冲区 + LRU 淘汰（最大 64 进程）+ 已完成进程保留 30 分钟 | 200KB 足够看最近状态而不致内存问题；64 进程 LRU 防止无界增长；30 分钟保留让用户有时间查询已完成进程 | entity/hermes-observability.md → tools/process_registry.py:1-60 |

---

## Agent 自学习触发机制

**维度**：Architecture
**问题陈述**：如何让 agent 在正确时机主动积累知识（创建技能、保存记忆、搜索历史），而不需要人类触发或独立后台进程？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | System prompt 驱动指令（三段 GUIDANCE），LLM 在完成任务过程中自发学习 | 将学习行为内嵌到 agent 决策流程，LLM 在刚完成复杂任务时主动创建技能，时机比后台批处理更准确；无需额外分析模块 | entity/hermes-self-learning-loop.md → agent/prompt_builder.py:145-171 |

---

## 技能注入策略

**维度**：Architecture
**问题陈述**：在技能数量较少的情况下，如何在简单性和检索精度之间选择技能注入方式？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | SKILL.md 文件全量注入 system prompt，每次会话启动时加载 | 技能数量通常较少，全量注入简单可靠，不依赖向量搜索基础设施；agent 能看到所有技能，不遗漏低频但关键的技能 | entity/hermes-self-learning-loop.md → agent/prompt_builder.py:449-453 |

---

## 技能的自我维护能力

**维度**：Extension Points
**问题陈述**：如何防止技能因环境变化（工具版本升级、API 变更）而过时失效？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | skill_manage 支持 patch 操作，agent 在使用中发现技能过时可就地修复 | 避免无效技能积累；agent 发现即修复而非等到下次使用时才报错 | entity/hermes-self-learning-loop.md → tools/skill_manager_tool.py:1-30 |

---

## 外部技能安全分级

**维度**：Architecture
**问题陈述**：如何在安全性和开放生态之间，按技能来源的可信度做差异化的安全策略？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 100+ 威胁模式静态扫描 + 四级信任矩阵（builtin/trusted/community/agent-created） | builtin 直接放行（项目维护者保证），community 最严格（不可信第三方），agent-created 询问但默认信任 | entity/hermes-skills-guard.md → tools/skills_guard.py:595-639（入口）、tools/skills_guard.py:39-48（信任矩阵） |

---

## 技能安装安全防护

**维度**：Dependency Strategy
**问题陈述**：如何在外部技能安装前，防止未经验证的代码在扫描期间被意外执行？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 隔离区（quarantine）暂存：Hub 下载 → quarantine/ → 扫描 → 通过后安装到 skills/<name>/ | 扫描失败直接删除隔离区文件，不影响已安装技能；确保未验证技能不会在扫描期间被意外执行 | entity/hermes-skills-guard.md → tools/skills_guard.py（隔离区流程） |

---

## 安全模块的测试策略

**维度**：Testing Philosophy
**问题陈述**：如何确保安全扫描规则的覆盖度和有效性，特别是针对变体绕过场景？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 100+ 规则用于边界条件专项测试（如 test_sql_injection.py），规则本身是测试覆盖重点 | 安全规则覆盖的边界条件（变体绕过等）需专项测试才能发现；行为测试而非实现测试的哲学在安全模块中尤为重要 | entity/hermes-skills-guard.md → 专项测试文件（如 test_sql_injection.py） |

---

## 工具注册的发现机制

**维度**：Architecture
**问题陈述**：如何在零手动配置的情况下让新工具自动可用，最小化添加工具的摩擦？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | AST 扫描自动发现 registry.register() 顶层调用 | 新工具只需在文件顶层调用 registry.register()，不需要修改任何现有文件；代价是依赖静态分析约定（只扫描顶层调用） | entity/hermes-tool-registry.md → tools/registry.py:28-73 |

---

## 工具注册中心的生命周期

**维度**：Architecture
**问题陈述**：如何在单进程内管理工具注册的唯一性和线程安全同步？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | 全局单例 + RLock 线程安全 | 工具集在进程内稳定，全局单例避免重复初始化；MCP 动态刷新需权威注册中心，分散实例难以同步 | entity/hermes-tool-registry.md → tools/registry.py:100-159 |

---

## 工具集的组合与复用

**维度**：Extension Points
**问题陈述**：如何让不同平台共享核心工具的同时拥有专用工具，避免工具名称在各平台重复列举？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| hermes | Toolset includes 递归组合，平台专用 toolset 从 _HERMES_CORE_TOOLS 继承，带去重和循环检测 | 核心工具列表改一处所有平台自动获得；includes 组合避免重复列举；去重和循环检测确保组合安全 | entity/hermes-tool-registry.md → toolsets.py:68-397、toolsets.py:447-497（递归解析） |
