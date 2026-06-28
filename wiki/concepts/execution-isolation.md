---
type: concept
concept: execution-isolation
problem: 如何为 Agent 的工具执行提供可插拔的隔离环境（本地/Docker/SSH/云端），使文件系统和命令执行透明路由
concerns: [后端可插拔性, 文件系统透明性, 环境生命周期管理]
repos: [nanobot, hermes-agent, openclaw, deepagents]
generated: 2026-06-25
---

# 执行隔离

## 核心问题

AI Agent 必须执行代码——这是它区别于纯对话机器人的核心能力。但允许 LLM 生成的代码在宿主机上直接运行是危险的。每个 Agent 框架都必须回答：代码在哪里执行、执行环境如何隔离、以及 agent 是否需要感知"我在沙箱里"。

根本张力在于**隔离强度与便利性的权衡**：越强的隔离（容器/虚拟机/远端执行）安全性越高，但带来启动延迟、文件同步开销和调试困难；越弱的隔离（本地进程/Same-Process）对用户友好，但安全风险更大。hermes-agent 和 openclaw 选了不同的平衡点——前者用 per-call 临时环境 + 6 种后端覆盖本地到高性能计算的全场景，后者用沙箱桥抽象让 agent 文件操作透明落地到容器。nanobot 则代表了第三个极端：把安全责任完全放在工具本身（SSRF 过滤）而非执行环境层。

第二个张力在于**文件系统的可见性边界**：agent 能看到宿主机的文件吗？如果隔离，agent 是看到沙箱里的干净文件系统还是能看到宿主机的挂载点？读写权限如何控制？openclaw 的 `SandboxFsBridge` 提供了最细粒度的控制（readFile/writeFile/stat/rename 全路径翻译），hermes-agent 则依赖 Docker volume mount 做文件暴露。

第三个张力在于**环境的生命周期**：是每次命令调用创建新环境（高隔离低性能）、会话期内复用（中等）还是持久的 workspace（低隔离高便利性）？生命周期直接影响资源消耗、状态管理和用户体验。

## 关切

- **后端可插拔性**：新执行后端（新容器引擎/云平台/远程协议）的接入成本，接口抽象的稳定性和覆盖度
- **文件系统透明性**：agent 操作文件时是否感知沙箱存在，路径翻译和权限控制的粒度和正确性
- **环境生命周期管理**：环境的创建、复用、闲置回收和终止策略，直接影响资源效率和状态一致性

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/config-system]]
**解法**：无专用执行隔离层——工具在 agent 进程内执行，仅通过 SSRF 保护防止内网攻击。
**实现**：
- 无隔离环境抽象：nanobot 没有独立的执行环境概念，工具直接在 agent 进程内执行命令，依赖 OS 进程级权限 ^[nanobot/agent/loop.py]
- SSRF 防护：对 HTTP 请求做目标地址校验，阻止对内网地址（127.0.0.1、10.0.0.0/8、172.16.0.0/12、192.168.0.0/16）的访问 ^[nanobot/security/ssrf.py]
**权衡**：零延迟、零启动成本，但安全风险完全转嫁给工具实现层，无法防御恶意代码写入文件系统或调用系统命令。适合受控的内部环境场景，不适合面向外部用户的多租户部署。

### hermes-agent
来源：[[repos/hermes-agent/entities/terminal-execution]]
**解法**：`BaseEnvironment` ABC 抽象 6 种执行后端，spawn-per-call 模型 + CWD 持久化 + 300s 自动清理非活跃环境。
**实现**：
- 六种后端工厂路由：`_create_environment()` 按 `TERMINAL_ENV` 选择 local/Docker/Singularity/Modal/Daytona/SSH，统一 `bash -c` 执行接口。添加新后端只需实现 `BaseEnvironment.execute()` 三个方法 ^[tools/terminal_tool.py:686-760]
- Spawn-per-call + 会话快照：每次命令调用创建新环境实例，init 时捕获 env vars/functions/aliases，执行前 source 快照还原上下文。CWD 跨命令持久化通过 temp file（local）或 in-band marker（remote）实现 ^[tools/environments/base.py:1-8]
- 自动清理：`_cleanup_inactive_envs()` 后台线程定期回收空闲超过 300s 的环境，防止容器/远端资源泄漏 ^[tools/terminal_tool.py:815]
- Modal 托管网关：`managed_modal` 通过 Nous Research 托管网关转发 Modal 请求，用户无需配置 Modal credentials ^[tools/environments/managed_modal.py]
- 任务级环境覆盖：`register_task_env_overrides()` 允许不同 task 使用不同后端，实现多租户混合 ^[tools/terminal_tool.py:553]
**权衡**：6 种后端的广度覆盖了从本地开发到 HPC 的全场景，但 spawn-per-call 在频繁命令交互时有创建/销毁开销。CWD 持久化依赖 temp file 和 in-band marker 而非文件系统原生语义，有竞态风险。

### deepagents
来源：[[repos/deepagents/entities/backend-protocol]]、[[repos/deepagents/entities/composite-backend]]、[[repos/deepagents/entities/state-backend]]
**解法**：协议驱动——定义 BackendProtocol（文件操作）和 SandboxBackendProtocol（+命令执行）两个抽象协议，所有具体后端实现协议即可接入。CompositeBackend 实现按路径前缀的多后端路由。
**实现**：BackendProtocol 定义 ls/read/write/edit/grep/glob/upload/download 八个文件操作方法，SandboxBackendProtocol 扩展 execute 方法。标准化错误码（file_not_found/permission_denied/is_directory/invalid_path）供 LLM 理解。文件数据格式 v2（content 为 str + encoding 字段区分 utf-8/base64）。async 方法默认通过 `asyncio.to_thread` 委托同步版本。execute_accepts_timeout 通过 inspect.signature 缓存检查后端类是否接受 timeout 参数。CompositeBackend 按路径前缀路由（最长前缀优先），在 `/` 根路径下聚合所有后端（ls/grep/glob），grep/glob 搜索结果自动添加路由前缀。upload/download 按目标后端分组批量调用。命令执行总是委托给 default backend（不走路由）。StateBackend 作为默认后端，通过 LangGraph CONFIG_KEY_READ/CONFIG_KEY_SEND 机制读写 state channel，文件在对话线程内持久化，不跨线程。 ^[deepagents/backends/protocol.py:301-811, 33-48, 148-158, 788-807; deepagents/backends/composite.py:119-738; deepagents/backends/state.py:38-365]
**权衡**：协议优先设计提供了最强的后端可插拔性——任何实现 BackendProtocol 的类都可作为后端接入，无需注册表或工厂模式。标准化错误码让 LLM 能理解和处理常见错误。CompositeBackend 的路径前缀路由提供了透明的存储分层（ephemeral/persistent），中间件不感知。但 StateBackend 是短暂的——无磁盘持久化，跨会话不保留文件，限制了长对话场景的文件持久性。无 Docker/SSH 等执行后端的内置实现——执行隔离依赖外部提供 SandboxBackendProtocol 实现。

## 对比

| 框架 | 后端可插拔性 | 文件系统透明性 | 环境生命周期管理 |
|------|------|------|------|
| nanobot | 无执行隔离层，工具在进程内执行 | 无文件系统隔离，直接操作宿主机文件 | 无生命周期管理 |
| hermes-agent | BaseEnvironment ABC + 6 种内置后端；新后端实现 3 个接口方法；任务级环境覆盖 | Docker volume mount 暴露文件，agent 感知环境切换；无透明路径翻译 | spawn-per-call + 300s 自动回收；CWD 通过 temp file 持久化 |
| openclaw | 注册表 + 工厂接口；内置 Docker/SSH；开放 registerSandboxBackend | SandboxFsBridge 透明路径翻译（read/write/stat/rename/glob）；agent 零感知 | session/agent/shared 三种作用域；workspaceAccess 控制可见性；资源限制可配置 |
| deepagents | 协议驱动——BackendProtocol ABC，任何实现即可接入，无注册表 | 路径前缀路由（CompositeBackend），中间件不感知路由；标准错误码 | 短暂存储（StateBackend），对话线程内持久化，不跨线程；无环境回收机制 |

## 演化记录

- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
- 2026-06-28：新增 deepagents（BackendProtocol + CompositeBackend 路径路由 + StateBackend）
