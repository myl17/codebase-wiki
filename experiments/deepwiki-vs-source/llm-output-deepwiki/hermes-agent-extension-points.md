# Hermes Agent - Extension Points 维度知识提取

## 1. 插件系统 (Plugin System)

### 1.1 概述

Hermes Agent 具备完善的插件架构，允许在不修改核心代码的情况下扩展 agent 的能力，包括添加自定义工具、生命周期钩子、专用记忆提供者和上下文压缩引擎。^[Plugins and Memory Providers:12083]

### 1.2 插件管理器 (PluginManager)

插件系统由 `PluginManager` 管理，负责插件的发现、加载和注册。^[hermes_cli/plugins.py:233-237] 插件默认为 opt-in，必须在配置中显式启用。^[hermes_cli/plugins.py:146-174]

#### 插件发现来源

插件从四个主要来源发现，后续来源在同名碰撞时覆盖前面的：^[hermes_cli/plugins.py:5-17]

| 来源 | 位置 | 说明 |
|------|------|------|
| **Bundled Plugins** | `<repo>/plugins/` | 内建插件，但 `memory/` 和 `context_engine/` 子目录被排除，它们有专用的发现路径 ^[hermes_cli/plugins.py:7-9] |
| **User Plugins** | `~/.hermes/plugins/<name>/` | 用户级插件 ^[hermes_cli/plugins.py:10] |
| **Project Plugins** | `./.hermes/plugins/<name>/` | 项目级插件，需要 `HERMES_ENABLE_PROJECT_PLUGINS=true` ^[hermes_cli/plugins.py:11-12] |
| **Pip Plugins** | 暴露 `hermes_agent.plugins` entry-point group | pip 分发包插件 ^[hermes_cli/plugins.py:13-14] |

#### 插件清单 (plugin.yaml)

每个目录型插件必须包含 `plugin.yaml` 清单和含 `register(ctx)` 函数的 `__init__.py` 文件。^[hermes_cli/plugins.py:19-20]

| 字段 | 说明 |
|------|------|
| `name` | 唯一标识符 ^[hermes_cli/plugins.py:183] |
| `kind` | 插件类别：`standalone`（默认）、`backend`（工具实现）、`exclusive`（记忆/上下文）^[hermes_cli/plugins.py:192-196] |
| `requires_env` | 运行所需的环境变量 ^[hermes_cli/plugins.py:185] |
| `provides_tools` | 插件注册的工具名称列表 ^[hermes_cli/plugins.py:186] |
| `provides_hooks` | 插件订阅的生命周期钩子列表 ^[hermes_cli/plugins.py:187] |

### 1.3 生命周期钩子 (Lifecycle Hooks)

插件通过 `ctx.register_hook()` 注册回调，可以拦截 agent 执行流程中的特定事件。^[hermes_cli/plugins.py:215-219] 有效钩子包括：^[hermes_cli/plugins.py:128-170]

| 钩子 | 触发时机 |
|------|----------|
| `pre_tool_call` / `post_tool_call` | 工具调用前后 |
| `transform_llm_output` | 允许插件在文本到达用户之前修改响应 ^[hermes_cli/plugins.py:136-137] |
| `pre_llm_call` / `post_llm_call` | LLM 推理循环前后 |
| `on_session_start` / `on_session_end` / `on_session_finalize` / `on_session_reset` | 会话各阶段 |
| `pre_gateway_dispatch` | 允许在消息网关中跳过或改写传入消息 ^[hermes_cli/plugins.py:148-155] |
| `pre_approval_request` / `post_approval_response` | 危险命令需要用户审批时 ^[hermes_cli/plugins.py:157-170] |

### 1.4 中间件 (Middleware)

插件可注册中间件来拦截 LLM 请求、工具请求或工具执行。^[hermes_cli/plugins.py:226-231] 中间件类型包括：^[hermes_cli/middleware.py:52-53]

- `llm_request`：拦截和修改 LLM 请求
- `tool_request`：拦截和修改工具请求
- `tool_execution`：拦截和修改工具执行

### 1.5 插件注册流程

插件通过 `register(ctx)` 函数完成注册：^[hermes_cli/plugins.py:196-231]

- `ctx.register_tool()`：向中央 `ToolRegistry` 注册自定义工具
- `ctx.register_hook()`：注册生命周期钩子
- `ctx.register_command()`：注册自定义斜杠命令

---

## 2. 技能系统 (Skills System)

### 2.1 概述

Skills 是 Hermes Agent 最核心的扩展机制。一个 **skill** 是包含 `SKILL.md` 文件的目录，为 agent 提供针对特定能力的分步操作指南、参考资料、模板和支持脚本。Agent 按需读取技能内容而非始终加载，以保持低 token 消耗。^[tools/skills_tool.py:9-13]

技能存储在 `~/.hermes/skills/` 中，按类别组织。新安装时，仓库 `skills/` 目录中捆绑的技能会通过 `tools/skills_sync.py` 种子到用户目录。Agent 创建的和从 Hub 安装的技能也落入同一目录。^[tools/skills_tool.py:85-91]

### 2.2 SKILL.md 格式

每个技能必须有一个包含 YAML frontmatter 的 `SKILL.md`，该格式兼容 [agentskills.io](https://agentskills.io/specification) 开放标准。^[tools/skills_tool.py:28-46]

关键 frontmatter 字段：
- `name`：技能标识符，最长 64 字符 ^[tools/skills_tool.py:94]
- `description`：简要描述，最长 1024 字符 ^[tools/skills_tool.py:95]
- `platforms`：可选的兼容平台列表（如 `[macos, linux, windows]`）^[tools/skills_tool.py:97-103]
- `required_environment_variables`：技能所需的密钥列表 ^[tools/skills_tool.py:128-150]
- `setup.collect_secrets`：安装期间交互式收集密钥的元数据 ^[tools/skills_tool.py:200-210]
- `metadata.hermes.config`：可选的 `config.yaml` 配置设置 ^[agent/skill_commands.py:124-128]

### 2.3 渐进式披露 (Progressive Disclosure)

At agent 启动时，system prompt builder 生成紧凑的技能索引。采用**渐进式披露**策略：主 system prompt 中只包含最少元数据（名称和截断的描述）以节省 token。^[agent/prompt_builder.py:170-176]

| 层级 | 工具调用 | 返回内容 |
|------|---------|---------|
| Tier 0 | `skills_list()` | 所有可用技能的名称和描述 ^[tools/skills_tool.py:53] |
| Tier 1 | `skill_view(name)` | 指定技能的完整 `SKILL.md` 指令 ^[tools/skills_tool.py:54] |
| Tier 2 | `skill_view(name, path)` | 特定参考、模板或资产文件的内容 ^[tools/skills_tool.py:65-67] |

### 2.4 Agent 面向工具

#### 只读工具 (`tools/skills_tool.py`)

- `skills_list`：返回所有兼容技能的元数据 (Tier 0)，遵守平台兼容性检查 ^[agent/skill_utils.py:128-169]
- `skill_view`：返回完整指令 (Tier 1) 或特定文件 (Tier 2)

#### 创作工具 (`tools/skill_manager_tool.py`)

`skill_manage` 工具允许 agent 维护自己的技能库。Agent 在完成复杂任务后被鼓励将新工作流保存为技能。^[agent/prompt_builder.py:150-163]

| 操作 | 说明 |
|------|------|
| `create` | 创建新技能目录和 `SKILL.md` ^[tools/skill_manager_tool.py:15] |
| `edit` | 替换现有技能文件的全部内容 ^[tools/skill_manager_tool.py:16] |
| `patch` | 对技能应用针对性的查找替换编辑 ^[tools/skill_manager_tool.py:17] |
| `delete` | 删除技能（仅允许用户创建的技能）^[tools/skill_manager_tool.py:18] |

### 2.5 技能同步与安全

#### 同步 (Sync)

捆绑技能通过基于清单的同步机制种子到用户目录，使用 `~/.hermes/skills/.bundled_manifest` 通过 MD5 哈希跟踪技能版本。^[tools/skills_sync.py:3-10]

- **新技能**：复制到用户目录，记录哈希 ^[tools/skills_sync.py:204]
- **未修改技能**：用户副本与清单哈希匹配时，仓库版本更新则同步更新 ^[tools/skills_sync.py:210-212]
- **已修改技能**：用户副本与清单哈希不同时，跳过同步以保护用户自定义 ^[tools/skills_sync.py:214-215]

#### 安全扫描 (Skills Guard)

`Skills Guard` 对外部来源（及可选对 agent 创建）的技能进行基于正则的静态分析。^[tools/skills_guard.py:3-9]

- **信任级别**：定义 `builtin`、`trusted`（OpenAI、Anthropic、HuggingFace、NVIDIA）和 `community` 级别 ^[tools/skills_guard.py:11-14, 40-49]
- **策略执行**：`community` 技能若包含任何 "caution" 或 "dangerous" 发现将被阻止 ^[tools/skills_guard.py:51-61]
- **威胁模式**：检测环境变量泄露（如 `curl` 配合 `$API_KEY`）、凭证存储访问（如 `~/.ssh`）和破坏性命令 ^[tools/skills_guard.py:95-143]

#### Curator 生命周期管理

`Curator` 是一个辅助模型任务，定期审查 agent 创建技能的集合。^[agent/curator.py:3-7]

- **生命周期状态**：`active` → `stale`（30 天不活跃后）→ `archived`（90 天后）^[agent/curator.py:10-12, 58-59]
- **不变性**：仅操作 agent 创建或内建技能（若启用）；从不自动删除，仅归档 ^[agent/curator.py:16-17]
- **Pin 保护**：已固定技能受保护不被删除或归档 ^[tools/skill_manager_tool.py:137-147, agent/curator.py:18]

---

## 3. 工具注册与扩展 (Tool Registry & Extension)

### 3.1 中央注册表模式

Hermes 采用**集中式工具注册表模式**，每个工具模块在导入时自注册其 schema、handler、toolset 类别和运行时可用性检查。^[model_tools.py:5-9]

- **ToolRegistry 单例**（`tools/registry.py`）收集所有工具条目，提供可用性检查和分发。^[tools/registry.py:151-167]
- **自注册**：每个工具模块通过 `registry.register()` 注册元数据，包括工具名称、toolset 成员关系、JSON schema（OpenAI function calling 风格）、handler 函数、可用性检查函数 ^[tools/registry.py:77-108]
- **注册包装**：工具被包装为 `ToolEntry` 对象，维护所有工具及其可用性检查的线程安全快照 ^[tools/registry.py:77-108]

### 3.2 工具发现流程

工具发现由 `model_tools.py` 触发，调用 `discover_builtin_tools()`：^[tools/registry.py:42-74]

1. **内置工具**：扫描 `tools/` 目录中使用 AST 解析包含 `registry.register` 调用的文件，然后导入有效模块触发注册 ^[tools/registry.py:29-74]
2. **MCP 工具**：从配置中读取 `mcp_servers` 并通过后台事件循环连接 ^[tools/mcp_tool.py:9-12, 63-67]
3. **插件工具**：发现并附加插件提供的 toolsets ^[model_tools.py:32-34]

### 3.3 Toolset 组合系统

Toolsets 在 `toolsets.py` 中定义，将工具按功能分组。^[toolsets.py:78-210]

核心 Toolsets：
- `web`：`web_search`、`web_extract`
- `terminal`：`terminal`、`process`
- `file`：`read_file`、`write_file`、`patch`
- `browser`：Playwright 浏览器自动化
- `vision`：图像分析
- `video`：视频分析
- `code_execution`：沙箱代码执行
- `delegation`：任务委派给子 agent
- `mcp`：通过 MCP 服务器的动态工具

Toolsets 支持使用 `includes` 键的嵌套组合。^[toolsets.py:83, 169]

### 3.4 工具定义

每个工具包含以下元素：

- **Schema**：OpenAI 兼容 function calling schema ^[tools/registry.py:89-91]
- **Handler**：`handler(args: dict, **kwargs) -> str`，返回字符串（通常 JSON）；支持同步和异步，通过 `_run_async` 透明桥接 ^[model_tools.py:83-102]
- **Availability Check**：`check_fn` 返回布尔值，支持条件暴露（如依赖 API 密钥、Docker、Playwright），结果缓存约 30 秒 ^[tools/registry.py:110-141]

---

## 4. MCP (Model Context Protocol) 集成

### 4.1 概述

Hermes 支持 Model Context Protocol，允许连接到外部工具服务器（如 GitHub、Filesystem）并动态注册其能力。^[tools/mcp_tool.py:3-11] MCP 服务器配置从 `~/.hermes/config.yaml` 的 `mcp_servers` 键读取。^[tools/mcp_tool.py:13-48]

### 4.2 架构

MCP 实现使用专用后台事件循环 (`_mcp_loop`) 运行在 daemon 线程中，每个服务器由 `MCPServerTask` 表示。^[tools/mcp_tool.py:63-67] MCP 子进程的 stderr 被重定向到 `~/.hermes/logs/mcp-stderr.log` 以防止 TUI 损坏。^[tools/mcp_tool.py:101-114]

### 4.3 Schema 映射与注册

- **前缀**：工具名称加 `mcp_{server_name}_` 前缀 ^[tools/mcp_tool.py:230-240]
- **清理**：连字符替换为下划线以兼容 LLM ^[tools/mcp_tool.py:232-235]
- **Schema 规范化**：`_normalize_mcp_input_schema` 确保 schema 符合预期格式，将 `$ref` 从 `#/definitions` 重写为 `#/$defs` ^[tools/mcp_tool.py:242-260]

### 4.4 OAuth 2.1 支持

对需要浏览器认证的服务器，`mcp_oauth.py` 实现带 PKCE 的 OAuth 2.1。^[tools/mcp_oauth.py:3-19]

- `HermesTokenStorage`：将 token 持久化到 `~/.hermes/mcp-tokens/`，限制权限 (0o600) ^[tools/mcp_oauth.py:175-195]
- **Callback Server**：生成临时 localhost HTTP 服务器以捕获授权码 ^[tools/mcp_oauth.py:16-17]
- **非交互环境**：在无法交互的环境中引发 `OAuthNonInteractiveError` ^[tools/mcp_oauth.py:83-85]

### 4.5 安全与可靠性

- **凭证脱敏**：使用正则模式从返回给 LLM 的错误消息中清除密钥 ^[tools/mcp_tool.py:173-185]
- **自动重连**：实现指数退避，最多 5 次重试 ^[tools/mcp_tool.py:53-56]
- **线程安全**：通过全局 `_lock` 保护对 `_servers` 注册表的修改 ^[tools/mcp_tool.py:73-77]
- **孤儿管理**：跟踪 PID 和进程组，确保 MCP 子进程在关闭时被回收 ^[tests/tools/test_mcp_stability.py:65-149]

---

## 5. 执行环境扩展 (Execution Environments)

### 5.1 概述

执行环境提供抽象层，允许 terminal tool 在不同的后端执行命令，从直接本地执行到隔离容器和远程云端沙箱。^[tools/terminal_tool.py:23-31] 环境后端通过 `TERMINAL_ENV` 环境变量选择，由 `_create_environment` 工厂函数实例化。^[tools/terminal_tool.py:534-585]

### 5.2 支持的后端

| 后端 | 环境变量值 | 实现类 | 用途 |
|------|-----------|--------|------|
| Local | `local` | `LocalEnvironment` | 直接主机执行（最快） |
| Docker | `docker` | `DockerEnvironment` | 安全加固的隔离容器 |
| SSH | `ssh` | `SSHEnvironment` | 通过 SSH 连接远程执行 |
| Modal | `modal` | `ModalEnvironment` | 无服务器云端沙箱（可扩展） |
| Daytona | `daytona` | `DaytonaEnvironment` | 云端开发工作空间 |
| Singularity | `singularity` | `SingularityEnvironment` | HPC 容器（研究集群） |

### 5.3 BaseEnvironment 接口

所有执行环境实现由 `BaseEnvironment` 抽象基类定义的最小接口。^[tools/environments/base.py:213-222]

| 方法 | 签名 | 用途 |
|------|------|------|
| `execute()` | `execute(command, cwd, timeout, stdin_data) -> dict` | 执行命令并返回 `output` 和 `returncode` ^[tools/environments/base.py:214-219] |
| `cleanup()` | `cleanup() -> None` | 释放资源 ^[tools/environments/base.py:216] |

### 5.4 扩展新环境

所有后端继承自 `BaseEnvironment` 抽象类，遵循统一的 spawn-per-call 模型（每次命令生成新 `bash -c` 进程但通过会话快照保持状态）。^[tools/environments/base.py:3-7] 关键扩展点：

- **配置层级**：`Per-task overrides` → `环境变量` → `默认值` ^[tools/terminal_tool.py:378-454]
- **工厂模式**：`_create_environment()` 作为中央工厂，解析后端类型并实例化 ^[tools/terminal_tool.py:406-454]
- **文件同步**：`FileSyncManager` 为远程后端提供凭证和技能的同步，支持事务性同步（全部成功才提交）^[tools/environments/file_sync.py:138-146]
- **安全隔离**：`LocalEnvironment` 和 `DockerEnvironment` 实现块名单系统，防止 Hermes 内部凭证泄露到子进程 ^[tools/environments/local.py:75-188]

---

## 6. 平台适配器扩展 (Platform Adapters)

### 6.1 概述

平台适配器提供统一接口，将 Hermes Agent 与消息平台（Telegram、Discord、WhatsApp、Slack、Signal、Email、Home Assistant、DingTalk、Matrix、Mattermost、SMS、Webhook、API Server、Feishu、Weixin、Bluebubbles、QQBot、Yuanbao、WeCom、Teams、Google Chat、IRC、LINE、SimplexChat）集成。^[Platform Adapters:7778]

### 6.2 架构

所有具体适配器继承自 `BasePlatformAdapter`。^[gateway/platforms/base.py:333-350] 该抽象基类定义了连接平台、发送/接收消息和处理媒体的契约。

适配器来源分布：
- **内置适配器**：`gateway/platforms/` 目录（Telegram、Slack、WhatsApp、Matrix、Feishu、DingTalk 等）
- **插件适配器**：`plugins/platforms/` 目录（Google Chat、IRC、Photon、Teams），通过插件系统加载

### 6.3 Gateway 编排

`GatewayRunner` 是网关的核心，作为守护进程管理多个 `AIAgent` 实例的动态编排。^[gateway/run.py:59-65]

- **Agent 缓存**：维护 `OrderedDict`，最大 128 个，空闲超过 1 小时被驱逐 ^[gateway/run.py:64-65]
- **扩展新平台**：实现 `BasePlatformAdapter`，标准化消息格式、媒体附件、认证和平台特定格式约定
- **Cron 集成**：`DeliveryRouter` 是无状态实用程序，用于将出站消息（如 cron 通知）路由到正确的适配器 ^[gateway/delivery.py:10-20]

---

## 7. 记忆提供者扩展 (Memory Providers)

### 7.1 概述

Memory Provider 是实现 `MemoryProvider` 抽象基类 (ABC) 的专用插件。^[agent/memory_provider.py:34] `MemoryManager` 编排这些提供者，确保同时只有一个外部提供者活跃，以防止工具 schema 膨胀。^[agent/memory_manager.py:6-9]

### 7.2 MemoryProvider 接口

Memory Provider 必须实现以下关键方法：^[agent/memory_manager.py:105-115]

- `initialize(session_id, **kwargs)`：设置记忆会话 ^[agent/memory_provider.py:41]
- `prefetch(query)`：在轮次开始前回忆上下文 ^[agent/memory_provider.py:48]
- `sync_turn(user, assistant)`：响应后持久化轮次 ^[agent/memory_provider.py:55]
- `handle_tool_call(name, args)`：处理对记忆特定工具的调用 ^[agent/memory_provider.py:61]
- `get_tool_schemas()`：返回记忆后端提供工具的 JSON schemas ^[agent/memory_provider.py:58]

### 7.3 内置 Memory Provider

| Provider | 实现 | 关键特性 |
|----------|------|---------|
| **Honcho** | `HonchoMemoryProvider` | AI-native 跨会话用户建模，辩证推理，peer 卡片和结论 ^[plugins/memory/honcho/__init__.py:1-5] |
| **Hindsight** | `HindsightMemoryProvider` | 知识图谱，实体解析，多策略检索，支持云端和本地模式 ^[plugins/memory/hindsight/__init__.py:1-6] |
| **OpenViking** | `OpenVikingMemoryProvider` | 字节跳动上下文数据库，文件系统式层级 (`viking://`)，分层上下文加载 ^[plugins/memory/openviking/__init__.py:1-23] |
| **Mem0** | `Mem0MemoryProvider` | 服务端 LLM 事实提取和去重 |
| **RetainDB** | `RetainDBMemoryProvider` | 云关系存储，崩溃安全 SQLite 写后队列 |
| **ByteRover** | `ByteRoverProvider` | 本地优先向量记忆和任务跟踪 |
| **Holographic** | `HolographicMemoryProvider` | 简单键值记忆存储 |

---

## 8. 模型传输与提供者扩展 (Provider & Transport Extension)

### 8.1 提供者注册表

Hermes 通过 `PROVIDER_REGISTRY` 字典维护提供者注册表，包含描述每个已知提供者的 `ProviderConfig` 数据类：认证类型、base URLs 和 API 密钥的环境变量。^[hermes_cli/auth.py:167-220]

支持的认证方案：
- **OAuth Device Code Flow**：主要用于 Nous Portal ^[hermes_cli/auth.py:750-845]
- **OAuth External Flow**：OpenAI Codex、Qwen、xAI、Google Gemini ^[hermes_cli/auth.py:1047-1121]
- **API Key**：Anthropic、OpenRouter 及众多其他提供者 ^[hermes_cli/auth.py:613-644]
- **Credential Pooling**：每提供者支持多凭证，实现故障转移、轮换和状态跟踪 ^[agent/credential_pool.py:13-35]

### 8.2 传输协议扩展

系统根据提供者和模型确定传输协议：

- **OpenAI Wire**：大多提供者的标准协议 ^[agent/auxiliary_client.py:105-106]
- **Anthropic Wire**：强制 `max_tokens` 字段 ^[agent/anthropic_adapter.py:123-126]
- **Codex**：使用特定适配器桥接 OpenAI Responses API ^[agent/codex_responses_adapter.py:1-10]

### 8.3 提供者插件

模型提供者可通过插件系统扩展，示例包括：^[Provider Runtime Resolution:11030-11031]
- `plugins/model-providers/minimax/`：MiniMax 提供者
- `plugins/model-providers/nous/`：Nous 提供者
- `plugins/model-providers/openrouter/`：OpenRouter 提供者

### 8.4 辅助客户端回退链

辅助客户端系统为非主要任务（如上下文压缩、视觉分析）提供统一的回退解析顺序：^[agent/auxiliary_client.py:1-30]

**文本任务回退顺序**：Main Provider → OpenRouter → Nous Portal → Custom → Anthropic → Direct API-key providers

**视觉任务回退顺序**：Main Provider → OpenRouter → Nous Portal → Anthropic → Custom

---

## 9. ACP Server (Agent Client Protocol)

### 9.1 概述

Hermes 实现了 **Agent Client Protocol (ACP)**，一个标准化通信层，允许 agent 作为 AI-native 编辑器和 IDE 的后端运行。^[ACP Server and IDE Integration:11871]

核心类是 `HermesACPAgent`，实现 `acp.Agent` 接口，将 ACP 生命周期事件转换为核心 `AIAgent` 操作。^[acp_adapter/server.py:39]

### 9.2 IDE 集成流程

1. **初始化**：客户端发送 `initialize` 请求，Hermes 响应能力（session fork、list、resume）^[acp_adapter/server.py:108-114]
2. **会话创建**：`new_session`、`load_session` 或 `resume_session`，提供工作目录 (`cwd`) ^[acp_adapter/server.py:282-358]
3. **Prompt 执行**：在 `ThreadPoolExecutor` 中运行 agent loop ^[acp_adapter/server.py:86]
4. **流式更新**：回调捕获工具进度、思考块和助手消息，通过 ACP session updates 发回 IDE ^[acp_adapter/events.py:96-101]

### 9.3 会话管理

`SessionManager` 是线程安全的，会话与编辑器的 `cwd` 绑定，持久化到共享 `SessionDB`。^[acp_adapter/session.py:186-206]

核心操作：`create_session`、`fork_session`、`list_sessions` ^[acp_adapter/session.py:209-314]

### 9.4 扩展特性

- **工具映射**：Hermes 工具名映射到 ACP `ToolKind`（如 `read_file` → `read`、`terminal` → `execute`）^[acp_adapter/tools.py:21-56]
- **编辑审批**：文件变更（`write_file`、`patch`）生成 `EditProposal`，可由客户端审批或自动通过 ^[acp_adapter/edit_approval.py:25-209]
- **MCP 集成**：IDE 可在会话初始化时提供 MCP 服务器，动态扩展 agent 的能力 ^[acp_adapter/session.py:140-155]
- **斜杠命令**：支持 `/steer`（注入引导）和 `/queue`（顺序排队执行）^[tests/acp_adapter/test_acp_commands.py:118-180]

---

## 10. Subagent 委派 (Subagent Delegation)

### 10.1 概述

`delegate_task` 工具允许 agent 生成一个或多个子 agent 在完全隔离的上下文中处理任务。子 agent 获得：^[tools/delegate_tool.py:9-13]

- 无父级历史的全新对话 ^[tools/delegate_tool.py:9-10]
- 自己的 `task_id`，创建隔离的 terminal 会话和文件操作缓存 ^[tools/delegate_tool.py:11]
- 受限 toolset（某些工具始终被阻止）^[tools/delegate_tool.py:45-53]
- 聚焦的 system prompt，由委派目标构建 ^[tools/delegate_tool.py:646-679]

### 10.2 隔离机制

- **上下文隔离**：`skip_context_files=True` 和 `skip_memory=True` ^[tools/delegate_tool.py:843-845]
- **会话隔离**：每个子 agent 获得唯一 `task_id` ^[tools/delegate_tool.py:837]
- **Toolset 限制**：`_strip_blocked_tools()` 从请求的 toolsets 中移除被阻止的工具 ^[tools/delegate_tool.py:718-724]
- **凭证覆写**：子 agent 可路由到与父级不同的模型/提供者 ^[tools/delegate_tool.py:795-799]

### 10.3 阻止的工具

| 工具 | 禁止原因 |
|------|---------|
| `delegate_task` | 防止递归委派（默认 `MAX_DEPTH=1`）^[tools/delegate_tool.py:47, 133] |
| `clarify` | 子 agent 不能与用户交互 ^[tools/delegate_tool.py:48, 61-63] |
| `memory` | 防止并发写入共享 `MEMORY.md` ^[tools/delegate_tool.py:49] |
| `send_message` | 防止不受控副作用 ^[tools/delegate_tool.py:50] |
| `execute_code` | 鼓励逐步推理而非单体脚本 ^[tools/delegate_tool.py:51] |

### 10.4 并行模式

使用 `ThreadPoolExecutor` 并行生成多个子 agent，最大并发数由 `delegation.max_concurrent_children` 决定（默认 3）。^[tools/delegate_tool.py:27-30, 132]

---

## 11. Skills Hub

### 11.1 概述

Skills Hub 是**用户驱动**的发现和安装系统，连接多个注册表（官方可选技能、GitHub 仓库、skills.sh 市场、ClawHub 和 LobeHub），提供搜索和安装技能的统一界面。^[tools/skills_hub.py:3-14]

关键原则：Skills Hub 完全由用户操作，Agent 不能自主安装、修改或删除 Hub 中的技能。^[website/docs/user-guide/features/skills.md:4-11]

### 11.2 Source Adapters (可插拔源适配器)

Hub 使用可插拔适配器系统获取技能，`create_source_router` 函数初始化活跃适配器：^[tools/skills_hub.py:1145-1155]

- **GitHubSource**：从任何 GitHub 仓库获取技能，使用 Contents API ^[tools/skills_hub.py:307-310]
- **SkillsShSource**：代理 `skills.sh` 市场，最终委托给 GitHubSource ^[tools/skills_hub.py:537-540, 623-630]
- **ClawHubSource**：连接 ClawHub API 搜索和获取技能 ^[tools/skills_hub.py:656-665]
- **LobeHubSource**：获取远程 JSON 索引并过滤 ^[tools/skills_hub.py:461-470]
- **OptionalSkillSource**：提供仓库 `optional-skills/` 目录中的技能，被认为是 `builtin` 级信任 ^[tools/skills_hub.py:245-250]

### 11.3 SkillSource 抽象基类

所有注册表适配器实现 `SkillSource` 抽象基类。^[tools/skills_hub.py:24] 关键实体：
- `SkillMeta`：搜索结果返回的最小元数据 ^[tools/skills_hub.py:69]
- `SkillBundle`：下载的技能文件和元数据容器 ^[tools/skills_hub.py:84]
- `HubLockFile`：跟踪已安装技能的来源、哈希和版本 ^[tools/skills_hub.py:844]
- `TapsManager`：管理用户添加的自定义 GitHub 仓库 ^[tools/skills_hub.py:1010]

---

## 12. Code Execution Sandbox

### 12.1 程序化工具调用 (PTC)

`execute_code` 工具允许 LLM 编写 Python 脚本通过 RPC 调用白名单工具，将多步工具链折叠为单次推理轮次，减少上下文窗口使用。^[tools/code_execution_tool.py:3-7]

### 12.2 传输层

支持两种传输方式：^[tools/code_execution_tool.py:8-29]
- **Local (UDS/TCP)**：适用于本地执行
- **Remote (File-based)**：适用于 Docker 或 SSH 等环境

### 12.3 工具 Stub 生成

`generate_hermes_tools_module` 函数构建 `hermes_tools.py` 模块源代码，包含将 Python 函数调用映射为 JSON-RPC 请求的 stub。^[tools/code_execution_tool.py:179-200]

沙箱允许的工具集合 (`SANDBOX_ALLOWED_TOOLS`)：^[tools/code_execution_tool.py:60-68]
- `web_search`、`web_extract`
- `read_file`、`write_file`、`search_files`、`patch`
- `terminal`

---

## 13. Batch Runner 与 Toolset Distributions

### 13.1 Batch Runner

`BatchRunner` 管理批量处理的完整生命周期：数据集加载、批次创建、通过 multiprocessing 并行执行、检查点持久化、统计聚合。^[batch_runner.py:1-21]

关键扩展参数：
- `distribution`：Toolset 分布名称，用于概率性工具采样 ^[batch_runner.py:533-534]
- `model`：模型标识符
- `num_workers`：并行工作进程数
- `ephemeral_system_prompt`：不保存到轨迹的 system prompt

### 13.2 Toolset Distributions

Toolset 分布通过受控的随机化实现评估场景的多样性。每个分布定义哪些 toolsets 可被采样及其选中概率。^[toolset_distributions.py:5-7]

- **独立采样**：每个 toolset 基于其概率百分比独立采样 ^[toolset_distributions.py:5-7]
- **预定义分布**：`default`（全部 100%）、`balanced`（全部 50%）、`research`、`development`、`science`、`creative`、`reasoning` 等 ^[toolset_distributions.py:29-220]
- **Fallback**：若无 toolset 被采样，自动选择最高概率的 toolset ^[toolset_distributions.py:279-284]

---

## 扩展难度梯度

| 难度 | 扩展机制 | 说明 |
|------|---------|------|
| **极低** | Skills 创作 | 仅需编写 `SKILL.md` YAML 文件，Agent 也可自行创建。无需修改代码 ^[tools/skills_tool.py:28-46] |
| **低** | Skills Hub 安装 | 用户通过 CLI `/skills install` 命令安装社区技能，自动安全扫描 ^[tools/skills_hub.py:3-14] |
| **低** | MCP Server 配置 | 在 `config.yaml` 添加 MCP 服务器条目，工具自动注册 ^[tools/mcp_tool.py:13-48] |
| **中** | Plugin 开发 | 创建 `plugin.yaml` + `__init__.py`（含 `register(ctx)`），可注册工具、钩子、命令 ^[hermes_cli/plugins.py:19-20] |
| **中** | Platform Adapter | 继承 `BasePlatformAdapter`，实现消息收发和媒体处理 ^[gateway/platforms/base.py:333-350] |
| **中** | Memory Provider | 实现 `MemoryProvider` ABC，提供 `initialize`、`prefetch`、`sync_turn`、工具 schemas ^[agent/memory_provider.py:34-61] |
| **中高** | Execution Environment | 继承 `BaseEnvironment`，实现 `execute()` 和 `cleanup()` ^[tools/environments/base.py:213-222] |
| **中高** | Provider/Transport | 实现 transport adapter + provider 插件注册 ^[agent/transports/] |
| **高** | ACP Server 定制 | 实现 `acp.Agent` 接口，管理会话生命周期 ^[acp_adapter/server.py:39] |

---

## 关联关系

```
                    ┌──────────────────────────────┐
                    │     Plugin System             │
                    │  (hermes_cli/plugins.py)      │
                    │  - 工具/Hook/Middleware注册     │
                    └──────────┬───────────────────┘
                               │ 统一注册接口
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
   │ Memory       │   │ Platform     │   │ Model Provider   │
   │ Providers    │   │ Adapters     │   │ Plugins          │
   │ (plugins/    │   │ (gateway/    │   │ (plugins/model-  │
   │  memory/)    │   │  platforms/) │   │  providers/)     │
   └──────────────┘   └──────────────┘   └──────────────────┘
          │                    │
          ▼                    ▼
   ┌──────────────────────────────────────────────┐
   │              Tool Registry                    │
   │           (tools/registry.py)                 │
   │  中央注册 + MCP集成 + Toolset组合              │
   └──────────────────┬───────────────────────────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
          ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────────┐
   │ Skills   │ │ Code     │ │ Subagent     │
   │ System   │ │ Execute  │ │ Delegation   │
   │ (skills/)│ │ Sandbox  │ │ (delegate)   │
   └──────────┘ └──────────┘ └──────────────┘
          │
          ▼
   ┌──────────────────────────┐
   │     Skills Hub           │
   │  (tools/skills_hub.py)   │
   │  社区技能分发 + 安全扫描    │
   └──────────────────────────┘

   ┌──────────────────────────┐
   │   Execution Environments  │
   │   (tools/environments/)  │
   │  Local/Docker/SSH/Modal/  │
   │  Daytona/Singularity      │
   └──────────────────────────┘

   ┌──────────────────────────┐
   │   ACP Server              │
   │   (acp_adapter/server.py) │
   │  IDE集成: VS Code/Zed     │
   └──────────────────────────┘
```

Skill 系统 + Skills Hub 是最低门槛的扩展入口。Plugin System 是最通用的钩子/中间件/工具扩展方式。MCP 提供外部工具服务器的标准协议接入。Execution Environments 抽象了命令执行后端。Platform Adapters 使新的消息平台可接入。Memory Providers 提供可插拔的记忆后端。Provider Plugins 扩展 LLM 提供者。ACP Server 将 Hermes 作为 IDE 后端暴露。
