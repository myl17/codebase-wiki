# Codex-Main Candidate List

生成日期：2026-06-28
规模检测：检测到 16 个 Concept → 选择策略 A（全量 frontmatter 扫描）

## 匹配过程

1. 执行 `ls wiki/concepts/*.md | wc -l` → 16 个 Concept
2. 宣告策略 A（≤50），执行 `for f in wiki/concepts/*.md; do head -10 "$f"; done` 全量 frontmatter 扫描
3. `grep -i "<关键词>" seeds/master.md` 确认种子库中已有的匹配记录
4. 对 16 个 Concept 的 frontmatter 逐一比对 codex-main 的 19 条问题空间条目

---

## A 类（追加到已有页面）— 12 条

| # | 问题名 | 来源 Entity | 目标 Concept | 判断理由 |
|---|--------|-------------|-------------|----------|
| 1 | 如何编排 AI Agent 的回合制交互循环 | core-agent-loop | agent-loop-orchestration | CodexThread 的回合状态机 + ThreadConfigSnapshot 配置快照 + TryStartTurnIfIdle 自动空闲触发与已有 agent-loop-orchestration（覆盖 nanobot/hermes/openclaw 的主循环编排）是同一核心问题 |
| 2 | 如何抽象跨本地/远程/沙箱环境的命令执行 | exec-server | execution-isolation | Environment 枚举 + ExecBackend trait + ExecutorFileSystem trait 三层抽象与 execution-isolation（后端可插拔性、文件系统透明性）完全匹配 |
| 3 | 如何提供跨平台的可移植文件系统沙箱 | sandbox-abstraction | execution-isolation | SandboxManager 多后端抽象（Landlock/Bubblewrap/Seatbelt/Windows）是 execution-isolation 中"隔离环境"的具体实现维度 |
| 4 | 如何定义、发现和执行 Agent 工具 | tool-system | tool-lifecycle-management | ToolDefinition 统一元数据 + 多源工具解析（内置/MCP/动态）+ Responses API 适配，与 tool-lifecycle-management 的工具注册/发现/策略过滤核心问题一致 |
| 5 | 如何用用户定义的技能文件扩展 Agent 能力 | skills-system | skills-extension-mechanism | CODEX_HOME/skills/ 目录 + 内嵌系统技能 + 指纹校验安装，是 skills-extension-mechanism 的声明式技能文件方案 |
| 6 | 如何抽象多个 LLM 后端为统一接口 | model-provider | provider-abstraction-pattern | ModelProvider trait + ProviderCapabilities + 多后端工厂（OpenAI/Bedrock/ChatGPT），与 provider-abstraction-pattern 的 API 差异抽象完全匹配 |
| 7 | 如何合并来自文件、云端、环境变量和 CLI 的多层配置 | config-management | configuration-management | 多层配置栈（config.toml + CloudConfigBundle + Profile + CLI）+ ConfigRequirements 云端约束，与 configuration-management 的配置源可组合性一致 |
| 8 | 如何对 Shell 命令执行实施允许/拒绝策略 | execpolicy | security-architecture | PrefixRule 策略引擎 + Decision::Allow/Deny/Ask 三态 + amend 运行时追加规则，是 security-architecture 中"命令执行安全"维度的实现 |
| 9 | 如何安全地以提升权限执行 Shell 命令 | shell-escalation | execution-approval-pattern | EscalateServer 守护进程 + EscalationPolicy 权限检查，是 execution-approval-pattern 中"高风险操作审批"的特化实现（审批后执行 + 进程隔离） |
| 10 | 如何抽象跨存储后端的对话持久化 | thread-store | session-lifecycle-management | ThreadStore trait + LocalThreadStore 本地实现 + ThreadMetadataPatch 部分更新，与 session-lifecycle-management 的"持久化存储"维度匹配 |
| 11 | 如何持久化、发现和搜索 Agent 会话转录 | rollout | session-lifecycle-management | JSONL rollout 文件 + SQLite 搜索索引 + 后台压缩，是 session-lifecycle-management 的"会话检索与浏览"维度 |
| 12 | 如何通过贡献者注册表扩展 Agent 行为 | extension-api | system-prompt-assembly | PromptSlot 提示词槽位 + ExtensionDataInit 初始化 + LoadedUserInstructions 聚合，与 system-prompt-assembly 的"提示词各层组装"核心问题一致 |

---

## B 类（新建 Concept 页）— 2 条

### B1：如何拦截 Agent 生命周期的关键事件

**新建 slug**：`hooks-event-interception`

**准则判断**：
- ① 多方案：Codex 提供 10 个命名的生命周期事件点（PreToolUse/PostToolUse/PermissionRequest/SessionStart 等）+ 外部命令执行引擎；OpenClaw 有 hooks-system（种子库标注为 D 类演化信号"事件驱动扩展点"）；Nanobot 通过中间件机制实现类似拦截。至少三个不同框架以不同方式解决了 Agent 生命周期拦截问题。✅
- ② 独立设计空间：Hook 系统关注的是"在 Agent 生命周期的哪些点、以什么粒度、如何安全地拦截"——评价维度（事件覆盖完整性、匹配器精度、执行隔离、命令 vs 脚本 vs WebAssembly）与 middleware-composition-pattern（关注中间件组合顺序）和 tool-lifecycle-management（关注工具本身的注册/发现）都不同。✅
- ③ 持续 Trade-off：细粒度钩子（更多控制但更高复杂度）vs 粗粒度钩子（简单但灵活性低）；外部命令执行（通用但性能低）vs 内置脚本引擎（高效但受限）；同步阻塞（简单但影响 Agent 响应）vs 异步非阻塞（复杂但不影响响应）。无银弹。✅

### B2：如何集成 MCP 协议作为工具互操作标准

**新建 slug**：`mcp-protocol-integration`

**准则判断**：
- ① 多方案：Codex 提供 MCP Server（暴露工具为 MCP JSON-RPC 服务）+ MCP Connection Manager（客户端连接池/目录/OAuth）；HermesAgent 有 mcp-integration（种子库）；OpenAI 的 MCP 协议本身正在成为行业标准。至少三个不同的实现方式。✅
- ② 独立设计空间：MCP 协议集成关注的是"工具标准化协议的选择与实现深度"——评价维度（协议兼容性、连接管理策略、目录构建与冲突解决、OAuth 认证流程）与 tool-lifecycle-management（关注工具在框架内部的注册/发现/过滤）和 provider-abstraction-pattern（关注 LLM Provider 的 API 差异）都不同。✅
- ③ 持续 Trade-off：Native MCP 实现（深度集成但维护成本高）vs 薄封装（快速但功能受限）；Server 模式（主动暴露工具）vs Client 模式（被动消费工具）；OAuth 完整支持（安全但认证流程复杂）vs API Key 简化（便捷但安全性低）。无银弹。✅

---

## C 类（待观察）— 3 条

| # | 问题名 | 来源 Entity | 理由 |
|---|--------|-------------|------|
| C1 | 如何管理模型目录、预设和动态刷新 | models-manager | 独立的 SharedModelsManager + RefreshStrategy 架构仅 codex-main 有此设计。其他仓库（OpenClaw model-configuration）将模型管理嵌入 Provider 配置层。待其他仓库出现类似的独立模型管理器后升级 |
| C2 | 如何提供多传输层 JSON-RPC 后端来管理 Agent 会话 | app-server | stdio/WebSocket/Unix socket 三传输层 + MessageProcessor JSON-RPC 路由 + 远程控制策略的 daemon 架构仅 codex-main。其他仓库通常将传输层嵌入框架内而非独立 app-server 进程 |
| C3 | 如何管理插件商城、安装、升级和卸载 | plugin-management | ConfiguredMarketplace 双商城源 + 启动同步 + 远程 bundle 下载的完整生命周期管理仅 codex-main。OpenClaw 的 plugin-system 已被标记为 C（子维度），说明插件商城管理尚未成为跨仓库的普遍设计问题 |

---

## D 类（演化信号）— 2 条

| # | 问题名 | 来源 Entity | 信号类型 | 理由 |
|---|--------|-------------|----------|------|
| D1 | 如何建模插件包的标识、能力和钩子元数据 | plugin-system | 候选合并 | PluginId 标识符 + PluginCapabilitySummary 多能力声明 + PluginProvider 来源抽象——这些概念介于 skills-extension-mechanism（关注单 Skill 的安装/注入）和 tool-lifecycle-management（关注单工具的注册/过滤）之间。建议在 skills-extension-mechanism 中增加"插件作为能力包"的讨论维度 |
| D2 | 如何管理插件商城、安装、升级和卸载 | plugin-management | 粒度不匹配 | 商城生命周期管理是 skills-extension-mechanism 中"来源多样性"的具体展开。当前 skills-extension-mechanism 的 concerns 已含"技能来源多样性与安全风险"和"安装自动化程度"，无需拆分。plugin-management 的具体方案作为 codex-main 在 skills-extension-mechanism 中的实例追加 |

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
| **Hook 事件拦截** | — | — | — | — | ✅ (NEW) |
| **MCP 协议集成** | — | ✅ | — | — | ✅ (NEW) |
| 模型目录管理 | — | — | — | — | 🆕 |
| App Server/多传输后端 | — | — | — | — | 🆕 |
| 插件商城管理 | — | — | — | — | 🆕 |
