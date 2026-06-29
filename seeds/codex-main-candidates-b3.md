# Codex-Main Candidate List — B3 @ Strategy C

生成日期：2026-06-29
规模检测：检测到 1018 个 Concept → 选择策略 C（>500，两轮 grep）
策略：第一轮 Strategy B grep → 未匹配条目从已匹配 Concept 的 concerns 字段提取扩展术语做第二轮 grep → 仍未匹配标记"待人工审核"

## 匹配过程

1. `ls wiki/concepts/*.md | wc -l` → 1018 个 Concept（含约 1000 个噪声干扰文件）
2. 宣告策略 C
3. 从 19 条 problem-map 条目各提取 2-4 个核心技术关键词（中英文）
4. 第一轮：`grep -l -i "关键词组合" wiki/concepts/*.md`，每个条目 1-6 次独立 grep
5. 合并去重：18 个真实 Concept 文件 + 21 个 distractor 文件被匹配
6. `head -12` 确认去重文件 frontmatter → 排除 distractor 误匹配
7. `grep -i "<关键词>" seeds/master.md` 确认种子库记录（match 所有 19 条）
8. 第二轮（条目 10/14/17 无明确首轮匹配）：从已匹配 Concept 的 concerns 字段提取扩展术语 → 未发现新的语义匹配
9. 分类判定

---

## A 类（已有 Concept 页覆盖，追加）— 14 条

| # | 问题名 | 来源 Entity | 目标 Concept | 判断理由 |
|---|--------|-------------|-------------|----------|
| 1 | 如何编排 AI Agent 的回合制交互循环 | core-agent-loop | agent-loop-orchestration | CodexThread 回合状态机 + ThreadConfigSnapshot 配置快照 + TryStartTurnIfIdle 自动空闲触发，与 agent-loop-orchestration 的主循环编排核心问题一致（已含 codex-main，repos 确认） |
| 2 | 如何抽象跨本地/远程/沙箱环境的命令执行 | exec-server | execution-isolation | Environment 枚举 + ExecBackend trait + ExecutorFileSystem trait 三层抽象，与 execution-isolation 的后端可插拔性和文件系统透明性核心问题一致（已含 codex-main） |
| 3 | 如何对 Shell 命令执行实施允许/拒绝策略 | execpolicy | security-architecture | PrefixRule 前缀匹配引擎 + Decision::Allow/Deny/Ask 三态决策 + amend 运行时追加规则。security-architecture body 已验证包含 codex-main 的 PrefixRule 策略引擎、SandboxManager、EscalateServer 三层防线（已含 codex-main） |
| 4 | 如何提供跨平台的可移植文件系统沙箱 | sandbox-abstraction | execution-isolation | SandboxManager 多后端（Landlock/Bubblewrap/Seatbelt/Windows）+ 平台自动选择。是 execution-isolation 中"隔离环境可插拔性"的具体实现维度（已含 codex-main） |
| 5 | 如何安全地以提升权限执行 Shell 命令 | shell-escalation | execution-approval-pattern | EscalateServer 守护进程 + EscalationPolicy 权限检查 + Unix domain socket 通信。是 execution-approval-pattern 中"高风险操作审批后执行+进程隔离"的特化实现（已含 codex-main） |
| 6 | 如何定义、发现和执行 Agent 工具 | tool-system | tool-lifecycle-management | ToolDefinition 统一元数据 + ToolCall 抽象 + MCP 工具解析器 + TurnItemEmitter 流式输出，与 tool-lifecycle-management 的工具注册/发现/生命周期管理一致（已含 codex-main） |
| 7 | 如何在 Agent 生命周期关键节点插入行为拦截 | hook-system | hooks-event-interception | 10 个命名事件点 + Hooks 注册表 + 外部命令执行引擎。hooks-event-interception 已创建且含 codex-main（repos: [codex-main, openclaw, nanobot]） |
| 8 | 如何用用户定义的技能文件扩展 Agent 能力 | skills-system | skills-extension-mechanism | CODEX_HOME/skills/ Markdown 技能文件 + include_dir! 嵌入系统技能 + marker 文件指纹校验。skills-extension-mechanism 已含 codex-main（repos 确认） |
| 9 | 如何抽象多个 LLM 后端为统一接口 | model-provider | provider-abstraction-pattern | ModelProvider trait + ProviderCapabilities 能力上限 + create_model_provider 工厂，与 provider-abstraction-pattern 的适配器设计模式一致（已含 codex-main） |
| 11 | 如何合并文件/云端/CLI 的多层配置 | config-management | configuration-management | 多层配置栈 + CloudConfigBundle + Profile 文件 + CLI overrides + ConfigRequirements 云端约束。configuration-management 已含 codex-main（repos 确认） |
| 12 | 如何将 Agent 工具暴露为 MCP JSON-RPC 服务 | mcp-server | mcp-protocol-integration | 基于 rmcp crate 的 MCP JSON-RPC 服务端 + MessageProcessor 路由 + codex_tool_runner 工具执行桥接。mcp-protocol-integration 已含 codex-main（repos 确认） |
| 13 | 如何管理 MCP 服务器的连接、目录和认证 | codex-mcp-integration | mcp-protocol-integration | McpConnectionManager 连接池 + McpCatalogBuilder 目录构建和冲突解决 + oauth_login_support OAuth 管理。是 mcp-protocol-integration 中"多服务器连接管理与认证"维度的具体实现（已含 codex-main） |
| 15 | 如何持久化、发现和搜索 Agent 会话转录 | rollout | session-lifecycle-management | JSONL rollout 文件 + SQLite 搜索索引 + spawn_rollout_compression_worker 后台压缩。是 session-lifecycle-management 中"存储可演化性与检索能力"维度的实现（已含 codex-main） |
| 16 | 如何抽象跨存储后端的对话持久化 | thread-store | session-lifecycle-management | ThreadStore trait + LocalThreadStore 本地实现 + ThreadMetadataPatch 部分更新。是 session-lifecycle-management 中"持久化存储"维度的实现（已含 codex-main） |
| 19 | 如何通过贡献者注册表扩展 Agent 行为 | extension-api | system-prompt-assembly | PromptSlot 提示词槽位 + ExtensionDataInit 初始化 + LoadedUserInstructions 指令聚合。是 system-prompt-assembly 中"层的可组合性"维度的实现（已含 codex-main） |

---

## B 类（新建 Concept 页）— 0 条

B1 中的 2 条 B 类（hooks-event-interception、mcp-protocol-integration）已在 B2 运行中创建，本 B3 运行中均为 A 类（已存在，无需新建）。

当前无新增 B 类候选——codex-main 剩余的独立设计空间（模型目录管理、App Server 多传输后端、插件元数据建模）均不满足三条硬门槛。

---

## C 类（待观察，进种子库）— 3 条

| # | 问题名 | 来源 Entity | 理由 |
|---|--------|-------------|------|
| C1 | 如何管理模型目录、预设和动态刷新 | models-manager | Round 1 grep 无匹配真实 Concept（匹配到的 agent-loop-orchestration、middleware-composition-pattern 均为"model"关键词误匹配）；Round 2 扩展 grep（model.*catalog/director/preset/refresh）命中 provider-abstraction-pattern 等，但语义不匹配——provider-abstraction 关注 Provider trait 的 API 差异抽象，不覆盖模型目录聚合和预设管理。独立的 SharedModelsManager + RefreshStrategy 架构仅 codex-main 有此设计 |
| C2 | 如何提供多传输层 JSON-RPC 后端来管理 Agent 会话 | app-server | Round 1 grep 无匹配真实 Concept（channel-abstraction-pattern、mcp-protocol-integration 均为关键词误匹配）；Round 2 扩展 grep（transport.*layer/daemon.*process/remote.*control）命中 execution-approval-pattern 等，但语义不匹配。stdio/WebSocket/Unix socket 三传输层 + MessageProcessor JSON-RPC 路由 + RemoteControlPolicy 的独立 daemon 架构仅 codex-main 有 |
| C3 | 如何管理插件商城、安装、升级和卸载 | plugin-management | Round 1 grep 命中 skills-extension-mechanism（"plugin.*marketplace\|plugin.*install\|plugin.*manag"匹配"plugin"相关词），但语义不匹配：skills-extension-mechanism 关注声明式 Markdown 技能文件的安装和注入，不覆盖二进制插件包的版本管理（upgrade/downgrade）、二进制兼容性校验和启动时同步（startup_sync）。ConfiguredMarketplace 双商城源 + PluginsManager 完整生命周期管理仅 codex-main 有 |

---

## D 类（演化信号）— 2 条

| # | 问题名 | 来源 Entity | 信号类型 | 理由 |
|---|--------|-------------|----------|------|
| D1 | 如何建模插件包的标识、能力和钩子元数据 | plugin-system | 候选合并 | PluginId（namespace/name 格式）+ PluginCapabilitySummary（多能力声明：skills/MCP server/App connector）+ PluginProvider（来源抽象：本地目录/远程 registry/内置 bundle）。Round 1 和 Round 2 grep 均无独立 Concept 匹配——此设计空间介于 skills-extension-mechanism（关注声明式 Skill 文件）和 tool-lifecycle-management（关注工具注册/过滤）之间。B2 演化信号已建议从 skills-extension-mechanism 拆分出独立 "plugin-architecture" Concept，将"声明式配置文件扩展"与"二进制/包扩展"分开讨论。此信号仍待 /evolve-apply 处理 |
| D2 | 如何管理插件商城、安装、升级和卸载 | plugin-management | 粒度不匹配 | 同上条被合并讨论。ConfiguredMarketplace + PluginsManager + startup_sync 的商城生命周期管理是 plugin-system 中"分发与版本管理"维度的具体展开。若 D1 触发独立 "plugin-architecture" Concept，D2 可作为该 Concept 的"安装与生命周期管理"子节。若 D1 未触发拆分，D2 应作为 skills-extension-mechanism 的扩展方向记录。此信号仍待 /evolve-apply 处理 |

---

## 能力域覆盖表

| 能力域 | nanobot | hermes-agent | openclaw | deepagents | codex-main |
|--------|---------|-------------|----------|------------|------------|
| Agent 主循环编排 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 上下文压缩策略 | ✅ | ✅ | ✅ | ✅ | — |
| Channel/平台抽象 | ✅ | ✅ | ✅ | — | — |
| 会话生命周期管理 | ✅ | ✅ | ✅ | — | ✅ |
| 系统提示词组装 | ✅ | ✅ | ✅ | — | ✅ |
| 记忆管理架构 | ✅ | ✅ | ✅ | ✅ | — |
| 工具生命周期管理 | ✅ | ✅ | ✅ | — | ✅ |
| Provider 抽象 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 子 Agent 编排 | ✅ | ✅ | ✅ | ✅ | — |
| 多层安全防御 | ✅ | ✅ | ✅ | — | ✅ |
| 执行审批 | — | ✅ | ✅ | — | ✅ |
| Skills 扩展机制 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 定时自主调度 | ✅ | ✅ | ✅ | — | — |
| 配置管理 | ✅ | ✅ | ✅ | — | ✅ |
| 执行隔离 | — | ✅ | ✅ | ✅ | ✅ |
| 中间件组合模式 | ✅ | ✅ | ✅ | ✅ | — |
| Hook 事件拦截 | — | — | ✅ | — | ✅ |
| MCP 协议集成 | — | ✅ | — | — | ✅ |
| 模型目录/预设管理 | — | — | — | — | 🆕 |
| App Server/多传输后端 | — | — | — | — | 🆕 |
| 插件包元数据建模 | — | — | ⚠️ | — | 🆕 |
| 插件商城/生命周期 | — | — | ⚠️ | — | 🆕 |

⚠️ = 部分覆盖（子维度），非独立 Concept

---

## 检索行为记录

### 1. 规模检测

- **检测命令**：`ls /Users/yuanlimiao/Work/codebase-wiki/wiki/concepts/*.md 2>/dev/null | wc -l`
- **结果**：1018 个 Concept 文件
- **宣告策略**：Strategy C（>500，两轮 grep）

### 2. master.md 访问方式

- **方法**：`grep -i "关键词\|关键词\|..." seeds/master.md`
- **实际命令**：单次 grep 涵盖 19 条 problem-map 的所有核心关键词（agent.*loop\|execution.*isolation\|security.*architecture\|execution.*approval\|tool.*lifecycle\|skill.*extension\|... 等，共约 50 个关键词变体，输出截断至前 60 行）
- **未使用 cat 全文读取**：严格遵守 SKILL.md "禁止读取 seeds/master.md 全文"规则
- **种子库命中**：所有 19 条 codex-main 条目均在 seeds/master.md 中有记录（B1 运行后写入），含分类标记（A/B/C/D）

### 3. Concept 检索方式（Round 1）

- **方法**：`grep -l -i "关键词组合" wiki/concepts/*.md`（每个条目独立 grep）
- **未使用全量 head -10 扫描**：1018 个文件的全量 frontmatter 扫描不在 Strategy C 允许范围内
- **分批执行**：19 个条目分为 5 批并发 grep（每批 3-4 条）
  - Batch 1（条目 1-4）：agent-loop, execution-isolation, exec-policy, sandbox
  - Batch 2（条目 5-8）：shell-escalation, tool-system, hook-system, skills-system
  - Batch 3（条目 9-12）：model-provider, models-manager, config-management, mcp-server
  - Batch 4（条目 13-16）：mcp-integration, app-server, rollout, thread-store
  - Batch 5（条目 17-19 + seed bank）：plugin-system, plugin-management, extension-api + master.md
- **去重后命中**：18 个真实 Concept + 21 个 distractor 文件
- **head -12 确认**：对 18 个真实 Concept 全部执行 frontmatter 读取确认匹配
- **Deep-read 验证**：对 3 个边界案例（条目 3→security-architecture vs execution-approval-pattern、条目 4→execution-isolation、条目 13→mcp-protocol-integration）执行 grep 深读验证

### 4. Round 2 grep（Strategy C 特有）

- **是否执行**：是
- **触发条件**：条目 10（models-manager）、条目 14（app-server）、条目 17（plugin-system）首轮 grep 无明确语义匹配
- **扩展术语来源**：从已匹配的 18 个 Concept 的 `concerns` 字段提取相关术语
  - 条目 10：`model.*catalog\|model.*director\|preset.*manag\|模型.*列表\|static.*model\|dynamic.*model\|cache.*model\|refresh.*strateg`
  - 条目 14：`transport.*layer\|daemon.*process\|守护进程\|multi.*transport\|session.*daemon\|remote.*control.*polic`
  - 条目 17：`plugin.*namespace\|标识符.*规范\|capability.*declar\|能力.*声明\|二进制.*扩展\|binary.*plugin\|包.*标识`
- **Round 2 结果**：
  - 条目 10：命中 provider-abstraction-pattern、system-prompt-assembly、middleware-composition-pattern——均为误匹配（概念语义不匹配）
  - 条目 14：命中 execution-approval-pattern、security-architecture、execution-isolation——均为误匹配
  - 条目 17：命中 provider-abstraction-pattern、channel-abstraction-pattern 及 16 个 distractor——均为误匹配
- **结论**：条目 10/14/17 确实无对应 Concept → 分别标记为 C、C、D

### 5. 干扰项影响

- **Distractor 文件总数**：约 1000 个（占全部 Concept 的 98%）
- **被误匹配的 distractor 数量**：21 个（占 distractor 总数的约 2%）
- **误匹配来源**：全部来自条目 3（exec-policy）的 grep 模式，该模式包含 `security.*architecture\|approval.*pattern`，在 distractor 文件体中匹配到巧合术语
- **误匹配 distractor 示例**：
  - `distractor-0135` 等：问题为"如何管理 iOS 应用中后台任务..."，匹配关键词未知（疑似文件体含 "security" 或 "architecture"）
  - `distractor-0491` 等：问题为"如何设计工具执行超时的定时器粒度..."，匹配关键词未知
- **影响评估**：21 个 distractor 被回收到去重列表中，但 `head -12` frontmatter 扫描时被排除——其 `type: concept` + `concept: distractor-NNNN` 字段明确暴露了噪声身份。未影响最终分类结果
- **其他 18 个条目**：grep 模式均未触发 distractor 误匹配（关键词特异性足够高）

### 6. 与 B1 基线（Strategy A, 16 Concept）的对比

| 维度 | B1 基线 | B3 (Strategy C, 1018 Concept) | 差异分析 |
|------|---------|------|----------|
| **Concept 总数** | 16 | 1018 | 98% 为噪声干扰文件 |
| **策略** | Strategy A（≤50，全量 frontmatter 扫描） | Strategy C（>500，两轮 grep） | B1 一次性读全部 frontmatter 可行；B3 必须 grep 前置过滤 |
| **A 类数量** | 12 | 14 | B1 的 2 条 B 类（hooks-event-interception、mcp-protocol-integration）在 B2 已创建，B3 中升级为 A 类 |
| **B 类数量** | 2 | 0 | 同上——B2 已消耗了 B 类候选 |
| **C 类数量** | 3 | 3 | C2（app-server）和 C3（plugin-management）分类一致；B1 的 C1（models-manager）仍为 C |
| **D 类数量** | 2 | 2 | 条目 17（plugin-system）和条目 18（plugin-management）均为 D。B1 将条目 18（plugin-management）标记为 D "粒度不匹配"，B3 跟进并明确将 C3 同时标记为 D（D2）——即 plugin-management 同时出现 C 类（单仓库）和 D 类（演化信号）双重属性 |
| **误匹配 distractor** | 0（distractor 不存在） | 21 个（条目 3 触发） | 策略 A 全量扫描无噪声概念；策略 C 中 grep 可能误匹配 noise，但 head -12 二次过滤有效排除 |
| **分类一致性** | 19 条中 19 条分类一致（100%） | — | 唯一的差异是 2 条 B→A 升级（符合预期，因 B2 已创建对应 Concept），核心判断无变化 |
| **检索 token 成本** | head -10 全部 16 个文件 ≈ 约 200 行 | 5 批 grep（文件系统级，token 零成本）+ head -12 共 18 个文件 ≈ 约 220 行 | B3 的 grep 不产生 LLM token 成本（shell 输出极短）；frontmatter 读取量相当（16→18），噪声干扰文件未进入 LLM 上下文 |
| **策略 C 特有：Round 2** | 不适用 | 执行了 3 次扩展 grep，零额外语义发现 | Round 2 确认了条目 10/14/17 确实无对应 Concept，提升了判定置信度 |

**关键发现**：Strategy C 的 grep-l + head-N 两步法在 1018 个 Concept（98% 噪声）场景下与 Strategy A 在 16 个纯净 Concept 下的分类结果完全一致。grep 关键词特异性是关键——条目 3 的模式过于宽泛（`security.*architecture`）导致 21 个 distractor 误匹配，但 head -12 frontmatter 二次过滤有效兜底。整体方案可规模化。
