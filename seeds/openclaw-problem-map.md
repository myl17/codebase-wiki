# openclaw Problem Space Mapping

> 生成于 Step 2：将单仓库 entity 翻译成跨仓库的"如何..."问题空间

---

## 中央控制平面：如何在单进程中统一 HTTP REST、WebSocket 双向通信和 OpenAI 兼容 API？

**问题陈述**：构建多渠道 AI 助手的框架都必须设计一个中心服务器来协调客户端通信、代理执行和状态传播
**核心关切**：
- 关切 1：单端口同时承载 HTTP REST、WebSocket 双向流、控制界面 SPA 和 OpenAI 兼容端点的路由分发
- 关切 2：如何设计版本化的 JSON 协议以支持客户端异构性和向前兼容？
- 关切 3：如何管理连接的认证、授权和速率限制？
**openclaw 的解法**：单端口 HTTP 服务器 + JSON-over-WebSocket 三帧协议（req/res/event）+ 分阶段 HTTP 请求管道 + ~30 领域方法分发
**源码证据**：src/gateway/server-http.ts:873、src/gateway/protocol/schema/frames.ts:139-174、src/gateway/server-methods.ts:69-100
**来源 Entity**：gateway
**层级**：架构决策

---

## Agent 执行循环：如何实现与模型 provider 无关、支持流式输出、自动压缩和故障切换的执行循环？

**问题陈述**：任何 LLM-based agent 框架的核心就是执行循环——如何调用模型、处理响应、在出错时恢复
**核心关切**：
- 关切 1：如何在不绑定特定 provider 的前提下支持流式订阅和结构化回复？
- 关切 2：上下文窗口溢出时如何自动压缩而不丢失关键信息？
- 关切 3：模型调用失败时如何实现平滑的故障切换（failover）链？
- 关切 4：如何管理并发执行（lane 排队）防止竞态条件？
**openclaw 的解法**：Provider 泛化的 `while(true)` 循环 + 流式订阅状态机 + 自动压缩重试（最多 3 次）+ 冷却感知的模型故障切换链 + lane 并发控制
**源码证据**：src/agents/pi-embedded-runner/run.ts:162-569、src/agents/pi-embedded-subscribe.ts:69、src/agents/model-fallback.ts:374-626
**来源 Entity**：agent-runtime
**层级**：架构决策

---

## 插件公共契约：如何在 core 与 100+ 个扩展之间定义一个稳定、安全、可演化的公共契约边界？

**问题陈述**：插件化框架必须在 core 保持精简和 plugin 拥有足够能力之间取得平衡，同时保证契约的向后兼容性
**核心关切**：
- 关切 1：如何设计 SDK 导出表面使插件作者无需了解 core 内部实现？
- 关切 2：如何确保 SDK 模块的加载开销可控（窄导入路径、零运行时类型）？
- 关切 3：如何避免 SDK facade 之间的循环依赖？
**openclaw 的解法**：三层入口体系（通用 definePluginEntry → provider 特化 defineSingleProviderPluginEntry → 渠道专用工厂）+ 窄 subpath export + 零运行时 channel-contract.ts
**源码证据**：src/plugin-sdk/plugin-entry.ts:174-206、src/plugin-sdk/channel-contract.ts:1-39、package.json（~100 个 exports subpath）
**来源 Entity**：plugin-sdk
**层级**：架构决策

---

## 渠道抽象：如何用统一接口抽象 25+ 消息平台，使共享的 routing/pairing/allowlist/command-gating 逻辑不需要为每个平台重写？

**问题陈述**：多渠道助手框架的核心挑战——每个平台有独特的概念（thread、reaction、poll、edit、unsend），但路由、配对、安全策略应是统一的
**核心关切**：
- 关切 1：adapter 接口的粒度——太粗无法覆盖平台差异，太细则每个平台变成模板填充？
- 关切 2：如何处理"重量级"模块（如渠道监控、探针、登录流程）的延迟加载？
- 关切 3：如何让第三方渠道插件与内置渠道享有相同的注册和查询路径？
**openclaw 的解法**：30+ 可选 adapter 的 `ChannelPlugin` 类型 + 渠道注册表懒加载 + manifest-first 的渠道 ID 体系（内置 ChatChannelId + 任意扩展 ID）
**源码证据**：src/channels/plugins/types.plugin.ts:53-97、src/channels/registry.ts:28
**来源 Entity**：channel-system
**层级**：架构决策

---

## 插件全生命周期：如何发现、加载、验证和管理 100+ 插件，使 core 不硬编码任何特定插件？

**问题陈述**：插件系统不能在 core 中硬编码插件列表或特殊处理逻辑——每个插件都应是平等的可发现资源
**核心关切**：
- 关切 1：manifest-first vs runtime 验证的权衡——静态安全检查何时进行？
- 关切 2：如何支持插件的安装、更新、卸载而不需要重启网关？
- 关切 3：如何确保插件之间不相互干扰（dependency denylist、安全扫描）？
**openclaw 的解法**：Manifest-first 发现 + 全局注册表单例（PLUGIN_REGISTRY_STATE Symbol）+ lazy service module + npm spec 安装 + 依赖 denylist 安全扫描
**源码证据**：src/plugins/runtime.ts:13-40、src/plugins/manifest.ts、src/plugins/install-security-scan.ts
**来源 Entity**：plugin-system
**层级**：架构决策

---

## 多层工具策略管道：如何在 agent 工具的 allow/deny 控制上实现 profile→provider→global→agent→group→sandbox→subagent 七层优先级？

**问题陈述**：不同上下文（哪个 agent、哪个渠道、哪个用户、是否沙箱化）需要不同的工具集合——策略系统必须有明确的分层和优先级
**核心关切**：
- 关切 1：策略层级的优先级顺序如何设计，使更具体的上下文覆盖更一般的？
- 关切 2：如何处理工具组（plugin tools、coding tools、messaging tools）的批量 allow/deny？
- 关切 3：特定 model provider 的工具 schema 如何归一化（如 Gemini 不支持某些 JSON Schema 约束）？
**openclaw 的解法**：9 层有序策略管道（profile→provider-profile→global→global-provider→agent→agent-provider→group→sandbox→subagent）+ 插件工具组展开 + provider schema 归一化
**源码证据**：src/agents/tool-policy-pipeline.ts、src/agents/pi-tools.ts（工具组装管道）
**来源 Entity**：tool-system
**层级**：架构决策

---

## 子 Agent 生命周期：如何管理嵌套 agent 的异步孵化、跟踪、完成和崩溃恢复？

**问题陈述**：当 agent 可以创建子 agent 时，必须设计完整的生命周期管理——从 spawn 到 complete，处理进程崩溃、网络中断、超时等各种异常
**核心关切**：
- 关切 1：如何防止无限递归的 agent 孵化（深度限制）？
- 关切 2：如何在网关重启后恢复"孤儿"子 agent（持久化 + 恢复）？
- 关切 3：子 agent 完成后如何通知父 agent（announce 机制 + 重试）？
**openclaw 的解法**：DI 构造的 SubagentRegistry + 内存/磁盘双层存储 + 定期清扫器 + 孤立恢复 + 指数退避 announce 重试
**源码证据**：src/agents/subagent-registry.ts、src/agents/subagent-registry-state.ts、src/agents/subagent-registry-helpers.ts
**来源 Entity**：subagent-system
**层级**：架构决策

---

## 模型管理：如何实现多 provider 的配置、认证、发现和故障切换，使 agent 不感知底层模型切换？

**问题陈述**：AI agent 框架必须管理数十个模型 provider，每个有不同的认证方式（API key、OAuth、AWS IAM）和故障模式
**核心关切**：
- 关切 1：认证凭据的四种模式（api-key/oauth/token/aws-sdk）如何在统一的抽象下管理？
- 关切 2：如何处理 api-key 轮换和 OAuth token 刷新？
- 关切 3：模型调用失败时何时冷却 provider（避免浪费配额），何时切换？
**openclaw 的解法**：四种认证模式 + 磁盘持久化的 AuthProfileStore（含冷却追踪）+ 多候选故障切换链 + provider 插件贡献的合成认证
**源码证据**：src/agents/model-auth.ts、src/agents/model-fallback.ts:374-626、src/agents/auth-profiles.ts
**来源 Entity**：model-configuration
**层级**：技术选型

---

## 会话持久化：如何在本地文件系统中管理对话状态的存储、压缩和磁盘预算？

**问题陈述**：非云端 agent 的对话状态必须存在本地——如何设计文件格式、并发控制（写锁）、磁盘空间管理（预算/清理）？
**核心关切**：
- 关切 1：会话键设计——如何在 agent、渠道、对等体之间唯一标识一个对话？
- 关切 2：如何管理磁盘空间（每个会话的预算、旧文件的归档和清理）？
- 关切 3：压缩检查点——如何追踪哪些对话段已被压缩以优化上下文窗口？
**openclaw 的解法**：结构化会话键（agent:{id}:{channel}:{account}:{peer}）+ 写锁保护的 JSON 存储 + 磁盘预算强制执行 + HTML 转录归档
**源码证据**：src/routing/session-key.ts、src/config/sessions/store.ts、src/config/sessions/disk-budget.ts
**来源 Entity**：session-system
**层级**：架构决策

---

## 模块化配置：如何设计一个支持 $include 模块化引用和 ${ENV} 动态替换的配置系统？

**问题陈述**：有三个相互制约的要求——配置文件应可拆分（include）、应在 git 中安全（敏感信息用 env var）、应可编程（运行时覆盖）
**核心关切**：
- 关切 1：如何实现 $include 而不引入无限递归或路径穿越？
- 关切 2：配置 schema 验证如何与插件贡献的 schema 合并？
- 关切 3：默认值填充的顺序如何保证（某些默认值依赖其他默认值）？
**openclaw 的解法**：JSON5 + `$include`（10 层限制、循环检测）+ `${ENV}` 替换 + 固定顺序的 `materializeRuntimeConfig` + Zod schema 分层验证
**源码证据**：src/config/includes.ts、src/config/env-substitution.ts、src/config/materialize.ts
**来源 Entity**：config-system
**层级**：技术选型

---

## CLI 架构：如何组织 40+ 子命令使常用操作绕过完整 CLI 框架加载实现快速响应？

**问题陈述**：AI 助手 CLI 有大量配置和状态查询命令——用户期望 status/health 等命令毫秒级响应，但完整 CLI 框架（Commander）加载需要时间
**核心关切**：
- 关切 1：如何在完整解析和快速路由之间取得平衡？
- 关切 2：插件贡献的命令如何延迟注册（避免启动时加载所有插件）？
**openclaw 的解法**：双层路由架构——快速路由表旁路 Commander（11 个路由 ID）处理常用查询 + 完整 Commander 程序处理复杂命令
**源码证据**：src/cli/route.ts、src/cli/command-catalog.ts、src/cli/run-main.ts
**来源 Entity**：cli-system
**层级**：技术选型

---

## 跨平台服务管理：如何统一 macOS launchd、Linux systemd 和 Windows Task Scheduler 的进程生命周期管理？

**问题陈述**：always-on AI 助手需要作为系统服务运行——三个主流 OS 的服务管理器有完全不同的概念和命令
**核心关切**：
- 关切 1：stage/install/start/stop/restart/uninstall 的接口设计应覆盖三个平台的所有语义？
- 关切 2：如何处理自重启（进程不能杀自己）的边界情况？
**openclaw 的解法**：统一 `GatewayService` 接口 + `process.platform` 查找表（darwin→launchd, linux→systemd, win32→schtasks）+ 安全重启握手（detached launchd restart handoff）
**源码证据**：src/daemon/service.ts、src/daemon/service-types.ts、src/daemon/launchd.ts
**来源 Entity**：daemon
**层级**：技术选型

---

## 消息路由：如何按渠道、账户、对等体和组身份的优先级将入站消息映射到正确的 agent 和对话？

**问题陈述**：多渠道助手的入站消息必须路由到特定的 agent 和会话——匹配规则需要分层优先级（从最具体到最宽泛）
**核心关切**：
- 关切 1：路由优先级顺序——从 peer exact match 到 guild+roles 到 team 到 account 到 channel 到 default？
- 关切 2：DM 会话的分组策略——所有人共享一个对话，还是每人独立？
- 关切 3：如何缓存路由决策以避免每次消息都重新计算？
**openclaw 的解法**：9 级路由优先级 + DM scope 模式（main/per-peer/per-channel-peer/per-account-channel-peer）+ 双层缓存（bindings 2000 条, routes 4000 条）
**源码证据**：src/routing/resolve-route.ts、src/routing/session-key.ts
**来源 Entity**：routing-system
**层级**：架构决策

---

## 执行隔离：如何设计一个可插拔的沙箱后端（Docker/SSH），使 agent 工具透明地路由到隔离环境？

**问题陈述**：能执行代码的 agent 必须有隔离——但文件系统和命令执行的抽象必须对 agent 透明
**核心关切**：
- 关切 1：Docker 容器 vs SSH 远程——如何用一个 `SandboxBackendFactory` 接口同时支持两者？
- 关切 2：文件系统桥——如何在宿主机路径和容器路径之间透明翻译 read/write/edit/stat？
- 关切 3：沙箱作用域——每会话独立容器 / 每 agent / 共享？
**openclaw 的解法**：可插拔后端注册表（registerSandboxBackend）+ 文件系统桥（SandboxFsBridge）+ session/agent/shared 三级作用域
**源码证据**：src/agents/sandbox/backend.ts、src/agents/sandbox/fs-bridge.ts、src/agents/sandbox/types.ts
**来源 Entity**：sandbox
**层级**：架构决策

---

## 技能（Skills）管理：如何从多个来源加载 agent 指令文件、按平台和配置过滤、安装依赖并注入系统提示？

**问题陈述**：让非技术人员编写 agent 行为指令（markdown 文件）是有价值的——但需要 loader、filter、installer 和 prompt injector
**核心关切**：
- 关切 1：从 bundled/plugin/clawhub/workspace 四个来源加载的技能如何合并和去重？
- 关切 2：如何在不完全加载的前提下检查技能的平台兼容性（requires.bins/env/config）？
- 关切 3：技能如何安装依赖（brew/node/go/uv/python）？
**openclaw 的解法**：多源加载 + YAML frontmatter 解析 + 平台/agent 过滤 + 五种安装策略（brew/node/go/uv/download）+ `<available_skills>` XML 提示注入
**源码证据**：src/agents/skills/workspace.ts、src/agents/skills/frontmatter.ts、src/agents/skills/types.ts
**来源 Entity**：skills
**层级**：架构决策

---

## 媒体管道：如何安全地处理用户上传的多媒体文件（图片/音频/视频/文档），支持格式检测、转换、优化和 SSRF 保护？

**问题陈述**：多渠道 AI 助手必须处理用户通过消息平台发送的各种媒体——格式多样、大小不一、需要安全处理
**核心关切**：
- 关切 1：如何在不引入二进制依赖的情况下处理 HEIC/HEIF（Apple 格式）？
- 关切 2：图像优化（JPEG 质量阶梯、PNG 压缩、resize）的后端如何选择（sharp vs sips）？
- 关切 3：如何防止 SSRF（通过 URL 下载媒体时避免内网请求）？
**openclaw 的解法**：sharp/sips 双后端 + JPEG 渐进质量 + HEIC→JPEG 转换 + SSRF 保护的 fetch 层 + 按媒体类型的大小限制
**源码证据**：src/media/web-media.ts、src/media/image-ops.ts、src/media/fetch.ts、src/media/constants.ts
**来源 Entity**：media-pipeline
**层级**：技术选型

---

## 事件驱动的扩展点：如何在 agent 生命周期的关键节点提供可发现、可过滤、安全隔离的钩子系统？

**问题陈述**：用户需要在 agent 启动、消息到达、会话变更时执行自定义逻辑——钩子系统必须可发现、可配置、故障隔离
**核心关切**：
- 关切 1：钩子来源的信任模型——bundled（可信）、managed、workspace（需显式 opt-in）如何区分？
- 关切 2：一个钩子失败是否应阻止其他钩子执行（故障隔离）？
- 关切 3：事件类型的分层匹配（通配符 + 精确）如何设计？
**openclaw 的解法**：四个来源目录 + 三级过滤 + 双层层事件匹配（通配符+精确）+ per-handler 错误隔离 + workspace 安全警告
**源码证据**：src/hooks/loader.ts、src/hooks/internal-hooks.ts、src/hooks/policy.ts
**来源 Entity**：hooks-system
**层级**：架构决策

---

## 执行审批流程：如何在 agent 高风险操作（shell 执行、文件写入）前插入人类审批，支持超时和决策审计？

**问题陈述**：安全与能力是矛盾的——既要让 agent 做有用的事，又要防止它做危险的事。人类审批是中间地带
**核心关切**：
- 关切 1：审批的异步性——agent 不应在等待审批时阻塞整个网关？
- 关切 2：如何支持 iOS 推送通知审批（移动场景）？
- 关切 3：审批 ID 如何防重放（其他客户端不能冒用）？
**openclaw 的解法**：创建-注册分离（create 同步, register 返回 Promise）+ setTimeout 超时拒绝 + 15s 宽限期 + 反重放元数据 + iOS 推送集成
**源码证据**：src/gateway/exec-approval-manager.ts:40-60、src/gateway/exec-approval-ios-push.ts
**来源 Entity**：approval-system
**层级**：架构决策

---

## 多层安全防御：如何在网关认证、执行限制、渠道访问控制、外部内容防护四个维度同时构建安全策略？

**问题陈述**：AI agent 是一把双刃剑——能力越强，攻击面越大。安全策略必须覆盖网络暴露、执行安全、社交访问和内容注入
**核心关切**：
- 关切 1：网关绑定模式（loopback→tailscale→public）的安全风险如何按等级审计？
- 关切 2：外部内容（邮件、webhook）中的提示注入攻击如何防护（Unicode 同形攻击）？
- 关切 3：DM/group 访问控制如何在不牺牲可用性的前提下实现最小权限？
**openclaw 的解法**：网关安全审计（bind/auth/rate-limit）+ 外部内容标记包装 + DM 四级策略（open/allowlist/pairing/disabled）+ HTTP 工具调用限制 + 可插拔安全审计收集器
**源码证据**：src/security/audit.ts:318、src/security/external-content.ts、src/security/dm-policy-shared.ts、src/security/dangerous-tools.ts:9
**来源 Entity**：security-system
**层级**：架构决策

---

## 定时任务调度：如何让 agent 在指定时间自动触发对话，同时让 agent 感知自己的调度状态？

**问题陈述**：AI 助手应能主动发起对话（日报、提醒、周期性检查）——但需要 cron 调度器 + agent 状态感知
**核心关切**：
- 关切 1：cron 触发时如何将"心跳"注入到正确的会话？
- 关切 2：如何让 agent 通过自然语言管理自己的 cron 计划（tool 接口）？
**openclaw 的解法**：Cron 表达式 → 网关 cron 服务 → 心跳系统提示注入 → agent 通过 cron 工具管理
**源码证据**：src/gateway/server-cron.ts、src/agents/system-prompt.ts:122
**来源 Entity**：cron-system
**层级**：技术选型

---

## 附录：跳过的 Entity（非跨仓库通用问题，或仅是本仓库的实现细节）

- 无。所有 20 个 entity 都代表了构建此类 AI agent 框架时必然面对的架构决策或技术选型。某些 entity（如 cron-system、daemon、cli-system）偏向技术选型层级，但其解决的问题（定时调度、跨平台服务管理、命令组织）在任何同规模 CLI 工具或 agent 框架中都是普遍存在的。
