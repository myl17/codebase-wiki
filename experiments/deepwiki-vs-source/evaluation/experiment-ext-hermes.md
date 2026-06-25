# Hermes-Agent Extension Points 维度知识提取

## 一、扩展点逐个分析

对照 Architecture 产出的核心抽象列表，逐个检查每个子系统的扩展机制。

---

### 1.1 工具注册机制（ToolRegistry）

工具是最核心的扩展点。每个工具模块在文件顶层调用 `registry.register()` 完成自注册，无需修改任何中心配置。^[tools/registry.py:176-228]

**注册签名：**

```python
registry.register(
    name,          # 工具唯一名
    toolset,       # 所属工具集
    schema,        # OpenAI-format function schema (dict)
    handler,       # 可调用对象 (sync/async)
    check_fn,      # 可用性检查函数，返回 bool
    requires_env,  # 所需环境变量列表
    is_async,      # 是否异步 handler
    description,   # 工具描述
    emoji,         # 展示 emoji
    max_result_size_chars,  # 结果大小上限
)
```

**扩展机制细节：**

- **自发现机制**：`discover_builtin_tools()` 通过 AST 解析模块源码检测 `registry.register(...)` 调用，自动导入所有自注册工具模块。^[tools/registry.py:56-73]
- **安全检查**：register() 使用 `threading.RLock` 保护并发访问，拒绝非 MCP 工具覆盖已有同名工具。^[tools/registry.py:190-213]
- **注销**：`deregister(name)` 允许移除工具，同时清理关联的 toolset check 和别名。^[tools/registry.py:229-252]
- **分发**：`dispatch(name, args)` 执行工具 handler，自动桥接异步 handler。^[tools/registry.py:292-309]
- **查询 API**：提供 `get_definitions()`、`get_entry()`、`get_tool_names_for_toolset()` 等完整的查询接口。^[tools/registry.py:258-286]

**扩展难度：低**。添加新工具只需要创建一个 Python 文件，调用 `registry.register()`，放置在 `tools/` 目录下即可被自动发现。

---

### 1.2 工具集（Toolset）系统

工具集将相关工具分组，支持通过 `includes` 实现组合。^[toolsets.py:68-397]

**扩展机制：**

- **静态定义**：`TOOLSETS` 字典定义工具集，每个 toolset 包含 `description`、`tools`（直接包含的工具名列表）、`includes`（引用的其他工具集）。^[toolsets.py:68-397]
- **运行时创建**：`create_custom_toolset(name, description, tools, includes)` 允许在运行时动态创建工具集。^[toolsets.py:613-632]
- **递归解析**：`resolve_toolset(name)` 递归展开所有 `includes`，支持 `"all"` / `"*"` 通配符获取所有工具集。^[toolsets.py:447-497]
- **插件集成**：`get_all_toolsets()` 自动合并静态定义的 TOOLSETS 和插件/MCP 注册的工具集。^[toolsets.py:545-567]
- **平台工具集**：每个平台（Telegram/Discord/Slack 等）有独立 toolset，均为 `_HERMES_CORE_TOOLS` 的拷贝；新增平台需复制此模式。^[toolsets.py:278-396]

**扩展难度：低**。添加新工具集只需在 `TOOLSETS` 字典中新增条目；代码内调用 `create_custom_toolset()` 即可动态扩展。

---

### 1.3 MCP Client —— 消费外部 MCP 工具

通过 MCP 协议连接外部工具服务器，将其工具动态注册到 hermes-agent 的 ToolRegistry 中。配置在 `~/.hermes/config.yaml` 的 `mcp_servers` 键下。^[tools/mcp_tool.py:1-70]

**扩展接口：**

- **Stdio 传输**：配置 `command` + `args`，启动本地进程通信。^[tools/mcp_tool.py:15-18]
- **HTTP/StreamableHTTP 传输**：配置 `url` + 可选 `headers`（如 Bearer token）。^[tools/mcp_tool.py:28-30]
- **Sampling 支持**：MCP 服务器可以请求 LLM 补全，通过 `sampling` 配置节控制模型、token 上限、频率限制。^[tools/mcp_tool.py:34-43]
- **动态工具发现**：监听 `notifications/tools/list_changed` 通知，支持 MCP 服务器运行时变更工具列表。^[tools/mcp_tool.py:128-136]
- **注册协议**：发现的 MCP 工具通过相同的 `registry.register()` 注册，toolset 名称格式为 `mcp-<server_name>`。^[tools/registry.py:195-197]
- **隔离保护**：MCP 工具与内置工具隔离——非 MCP 源的工具不允许覆盖非 MCP 源的工具名。^[tools/registry.py:205-213]
- **配置属性**：`timeout`（默认 120s）、`connect_timeout`（默认 60s）、自动重连（最多 5 次，指数退避）。^[tools/mcp_tool.py:163-167]

**扩展难度：低**。用户只需在 `config.yaml` 添加 MCP 服务器配置即可接入外部工具生态。

---

### 1.4 MCP Server —— 暴露 Hermes 能力给外部客户端

将 hermes-agent 的会话和消息功能作为 MCP 工具暴露，供外部 MCP 客户端（Claude Code、Cursor、Codex 等）调用。^[mcp_serve.py:1-78]

**暴露的工具（10+1 个）：**

| 工具名 | 功能 |
|--------|------|
| `conversations_list` | 列出所有会话 |
| `conversation_get` | 获取指定会话详情 |
| `messages_read` | 读取消息历史 |
| `attachments_fetch` | 提取附件 |
| `events_poll` | 轮询新事件 |
| `events_wait` | 等待新事件（长轮询） |
| `messages_send` | 发送消息 |
| `permissions_list_open` | 列出待审批授权请求 |
| `permissions_respond` | 响应授权请求 |
| `channels_list` | 列出所有聊天频道 |

**扩展协议：** 使用 FastMCP（`mcp.server.fastmcp`）构建，通过 stdio 传输。客户端配置只需指定 `hermes mcp serve` 命令。^[mcp_serve.py:50-55]

**扩展难度：低**。启动即用；新增暴露工具在 `mcp_serve.py` 中添加新的 `@mcp.tool()` 装饰函数。

---

### 1.5 事件钩子系统（HookRegistry）

轻量事件驱动系统，在关键生命周期点触发自定义处理器。钩子从 `~/.hermes/hooks/` 目录自动发现和加载。^[gateway/hooks.py:1-171]

**支持的事件类型：**

| 事件 | 触发时机 |
|------|---------|
| `gateway:startup` | 网关进程启动 |
| `session:start` | 新会话创建（首次消息） |
| `session:end` | 会话结束（/new 或 /reset） |
| `session:reset` | 会话重置完成 |
| `agent:start` | Agent 开始处理消息 |
| `agent:step` | 工具调用循环的每一步 |
| `agent:end` | Agent 处理完成 |
| `command:*` | 任何斜杠命令执行（通配符匹配） |

**扩展协议：**

- 每个钩子目录包含两个文件：`HOOK.yaml`（元数据：`name`、`description`、`events`）和 `handler.py`（提供一个 `handle(event_type, context)` 函数，sync 或 async 均可）。^[gateway/hooks.py:76-136]
- 发现机制：`discover_and_load()` 扫描 `~/.hermes/hooks/` 下的子目录，使用 `importlib` 动态加载 handler。^[gateway/hooks.py:69-136]
- 通配符匹配：注册 `command:*` 的 handler 会触发所有 `command:reset`、`command:model` 等事件。^[gateway/hooks.py:157-161]
- 内置钩子：`boot-md` 在 `gateway:startup` 时执行 `~/.hermes/BOOT.md`。^[gateway/hooks.py:54-67]
- 错误隔离：钩子中的异常被捕获和记录，永不阻塞主流水线。^[gateway/hooks.py:163-170]

**扩展难度：低**。创建 `HOOK.yaml` + `handler.py` 放入 `~/.hermes/hooks/<name>/` 即可。

---

### 1.6 插件系统：Memory Provider

外部记忆后端插件系统，支持 8 个内置 providers（honcho、hindsight、holographic、mem0、openviking、retaindb、supermemory、byterover），同时支持用户安装自定义 providers。^[plugins/memory/__init__.py:1-406]

**扩展协议 —— MemoryProvider ABC：** ^[agent/memory_provider.py:42-60]

所有 memory provider 必须实现以下抽象方法：
- `name` 属性：provider 标识符
- `is_available()`：检查配置和依赖是否就绪
- `initialize()`：连接、创建资源、预热
- `system_prompt_block()`：注入系统提示词的静态文本
- `prefetch(query)`：每轮对话前后台召回
- `sync_turn(user_msg, assistant_msg)`：每轮对话后异步写入
- `get_tool_schemas()`：暴露给模型的工具 schema
- `handle_tool_call()`：分发工具调用
- `shutdown()`：清理退出

**可选钩子：** `on_turn_start()`、`on_session_end()`、`on_pre_compress()`、`on_memory_write()`、`on_delegation()`。^[agent/memory_provider.py:25-30]

**注册协议：**

- **内置 providers**：位于 `plugins/memory/<name>/`，通过 `plugin.yaml` 描述元数据，`__init__.py` 中 `register(ctx)` 函数调用 `ctx.register_memory_provider(instance)`。^[plugins/memory/__init__.py:263-271]
- **用户安装 providers**：位于 `$HERMES_HOME/plugins/<name>/`，`_is_memory_provider_dir()` 通过检查源码中含 `register_memory_provider` 或 `MemoryProvider` 来判断。^[plugins/memory/__init__.py:50-63]
- **发现优先级**：内置 providers 优先于用户安装的（名称冲突时）。^[plugins/memory/__init__.py:82-92]
- **激活方式**：配置驱动，`memory.provider` 在 `config.yaml` 中选择活跃 provider，同时只能有一个外部 provider 激活（内置 memory 始终运行）。^[plugins/memory/__init__.py:307-319]

**扩展难度：中**。需实现 `MemoryProvider` ABC 的完整方法集合（9+ 个方法），但注册流程简单（目录 + `register()` 函数）。

---

### 1.7 插件系统：Context Engine

上下文引擎插件，控制 LLM 上下文窗口压缩策略。^[agent/context_engine.py:1-60]

**扩展协议 —— ContextEngine ABC：** ^[agent/context_engine.py:32-60]

所有 context engine 必须实现：
- `name` 属性：引擎标识符
- Token 状态属性：`last_prompt_tokens`、`last_completion_tokens`、`last_total_tokens`、`threshold_tokens`、`context_length`、`compression_count`
- `on_session_start()`：会话开始时调用
- `update_from_response(api_response_data)`：每次 API 响应后更新 token 用量
- `should_compress(system_message, messages)`：判断是否应压缩
- `compress(system_message, messages)`：执行压缩，返回压缩后的消息
- `on_session_end()`：会话结束时调用

**注册协议：**

- 引擎位于 `plugins/context_engine/<name>/`，`__init__.py` 中提供 `register(ctx)` 函数或 ContextEngine 子类。^[plugins/context_engine/__init__.py:174-196]
- 发现采用双模式：优先 `register(ctx)` 模式（`ctx.register_context_engine(instance)`），回退到 ABC 子类扫描。^[plugins/context_engine/__init__.py:176-194]
- 激活方式：`context.engine` 在 `config.yaml` 中选择，默认 `"compressor"`。^[plugins/context_engine/__init__.py:8-10]

**扩展难度：中**。需实现完整的压缩逻辑，但 ABC 提供清晰的接口契约。

---

### 1.8 平台适配器（BasePlatformAdapter）

通过子类化 `BasePlatformAdapter` 添加对新消息平台的支持。^[gateway/platforms/base.py:813-853]

**扩展接口（必须实现的方法）：** ^[gateway/platforms/ADDING_A_PLATFORM.md:1-51]

| 方法 | 用途 |
|------|------|
| `__init__(config)` | 解析配置，初始化状态 |
| `connect() -> bool` | 连接平台，启动监听器 |
| `disconnect()` | 断开连接，清理资源 |
| `send(chat_id, text, ...) -> SendResult` | 发送文本消息 |
| `send_typing(chat_id)` | 发送打字指示器 |
| `send_image(chat_id, image_url, caption) -> SendResult` | 发送图片 |
| `get_chat_info(chat_id) -> dict` | 获取聊天信息 |

**可选覆写方法：** `send_document()`、`send_voice()`、`send_video()`、`send_animation()`、`send_image_file()`。

**集成点清单（共 16 处）：** ^[gateway/platforms/ADDING_A_PLATFORM.md:1-314]

1. `gateway/platforms/<platform>.py` — adapter 实现
2. `gateway/config.py` — `Platform` 枚举 + `_apply_env_overrides()`
3. `gateway/run.py` — `_create_adapter()` 工厂
4. `gateway/run.py` — `_is_user_authorized()` 授权映射
5. `gateway/session.py` — `SessionSource` 扩展字段
6. `agent/prompt_builder.py` — `PLATFORM_HINTS`
7. `toolsets.py` — 平台 toolset 定义 + `hermes-gateway` 引用
8. `cron/scheduler.py` — cron delivery platform_map
9. `tools/send_message_tool.py` — 发送消息平台路由
10. `tools/cronjob_tools.py` — deliver 参数描述
11. `gateway/channel_directory.py` — 频道发现
12. `hermes_cli/status.py` — 状态展示
13. `hermes_cli/gateway.py` — 设置向导
14. `agent/redact.py` — 敏感信息脱敏
15. Documentation — README / AGENTS.md / 网站文档
16. Tests — 测试覆盖

**扩展难度：高**。需要跨越 16+ 个文件的修改点，深入理解网关内部路由机制。

---

### 1.9 Agent 回调系统

AIAgent 构造函数接受多个回调函数，允许外部（CLI、Gateway）监听和干预 agent 执行流程。^[run_agent.py:587-599]

**回调列表：** ^[run_agent.py:587-598]

| 回调参数 | 用途 |
|---------|------|
| `tool_progress_callback` | 工具执行进度通知 |
| `tool_start_callback` | 工具开始执行回调 |
| `tool_complete_callback` | 工具完成执行回调 |
| `thinking_callback` | LLM 思考过程输出 |
| `reasoning_callback` | LLM 推理过程输出 |
| `clarify_callback` | 交互式用户问题（choices -> 答案） |
| `step_callback` | 每步循环回调 |
| `stream_delta_callback` | 流式 token 增量输出 |
| `interim_assistant_callback` | 中间助手消息 |
| `tool_gen_callback` | 工具生成回调 |
| `status_callback` | 生命周期状态通知（弃用旧 callback，新代码用此） |

**扩展方式：**
- CLI 和 Gateway 各自实现回调函数，在构造 `AIAgent` 时传入。无需子类化。^[run_agent.py:535-617]
- `status_callback("lifecycle", message)` 是新代码推荐的统一状态报告机制。^[run_agent.py:1888-1890]

**扩展难度：低**。只需实现回调函数并传入 AIAgent 构造函数。

---

### 1.10 Skills 技能系统

渐进式信息披露的技能文档系统，agent 根据对话上下文自动匹配和加载相关技能。^[tools/skills_tool.py:1-80]

**技能定义格式 —— SKILL.md：** ^[tools/skills_tool.py:28-52]

```yaml
---
name: skill-name           # 必需，max 64 chars
description: Brief desc    # 必需，max 1024 chars
version: 1.0.0
license: MIT
platforms: [macos]         # 可选，OS 平台限制
prerequisites:             # 可选，运行时要求
  env_vars: [API_KEY]
  commands: [curl, jq]
metadata:                  # 可选，自定义 key-value
  hermes:
    tags: [fine-tuning, llm]
---
# 技能正文
```

**扩展机制：**

- **目录结构**：`skills/<category>/<skill-name>/SKILL.md`，支持子文件和引用。^[tools/skills_tool.py:14-27]
- **自动匹配**：agent 根据系统提示词中的 skill 列表（名称 + 描述）自动加载相关技能。^[tools/skills_tool.py:1-7]
- **技能同步**：`tools/skills_sync.py` 通过 manifest 管理打包技能到用户目录的同步更新，支持检测用户自定义修改并跳过更新。^[tools/skills_sync.py:1-22]
- **技能中心（Skills Hub）**：`tools/skills_hub.py` 提供远程技能注册源适配器（`SkillSource` ABC）和支持 GitHub 仓库的技能拉取（`GitHubSource`）。^[tools/skills_hub.py:1-38]
- **可选技能**：`optional-skills/` 目录包含官方提供的可选技能（不默认激活），通过 Skills Hub 安装。^[tools/skills_hub.py:8-9]

**扩展难度：低**。创建 `SKILL.md` 文件放入 `skills/` 目录即可被系统识别和加载。

---

### 1.11 凭证池（CredentialPool）

支持同一 LLM provider 的多凭证轮换和故障转移。^[agent/credential_pool.py:1-60]

**扩展机制：**
- 凭证来源：手动添加（`SOURCE_MANUAL`）、OAuth 自动获取、Codex CLI 导入。
- 凭证状态：`ok` / `exhausted`，自动跳过 `exhausted` 状态。
- 填充策略：`fill_first`（用完第一个再切换下一个）。
- 多 provider 支持：通过 `PROVIDER_REGISTRY` 管理不同 provider 的凭证类型。^[agent/credential_pool.py:19-25]

**扩展协议：** 通过 `read_credential_pool()` / `write_credential_pool()` 读写凭证持久化存储，新增 provider 类型需在 `PROVIDER_REGISTRY` 注册。^[agent/credential_pool.py:33-35]

**扩展难度：低**。用户通过配置添加新凭证即生效；新增 provider 类型需注册到 `PROVIDER_REGISTRY`。

---

### 1.12 LLM API 模式适配

AIAgent 支持四种 LLM API 模式，通过适配器模式处理差异。^[run_agent.py:690-709]

| API 模式 | 适配器 | 用途 |
|----------|--------|------|
| `chat_completions` | 内置（OpenAI 兼容） | 标准模式 |
| `anthropic_messages` | `agent/anthropic_adapter.py` | Anthropic API |
| `bedrock_converse` | `agent/bedrock_adapter.py` | AWS Bedrock |
| `codex_responses` | 内置（OpenAI Codex） | Codex CLI |

**扩展方式：** 新增 API 模式需要：
1. 在 `run_agent.py` 的 `_prepare_api_request()` 中添加请求构建逻辑
2. 在 `_parse_api_response()` 中添加响应解析逻辑
3. 在 `__init__` 的自动检测逻辑中添加 URL 匹配

**扩展难度：中**。需要理解 agent 内部的 API 请求/响应管线。

---

### 1.13 配置驱动扩展

多层配置系统允许通过声明式配置打开/关闭功能和调整行为。^[gateway/run.py:87-107]

**配置层次：** ^[gateway/run.py:89-107]

1. 代码内默认值（`DEFAULT_CONFIG`）
2. 项目 `.env` 文件
3. 用户 `~/.hermes/.env` 文件
4. 用户 `~/.hermes/config.yaml`（对 terminal 配置具有权威性，覆盖 `.env`）
5. 环境变量（最高优先级，通过 `${ENV_VAR}` 插值在 `config.yaml` 中展开）

**通过配置可扩展的功能：**
- LLM provider / model / API key 切换
- MCP 服务器列表（`mcp_servers`）
- Memory provider 选择（`memory.provider`）
- Context engine 选择（`context.engine`）
- 平台启用/禁用（`platforms.<name>.enabled`）
- Session reset 策略（`session_reset`）
- Toolset 启用/禁用（每个平台的 toolset 配置）
- 系统提示词定制（`system_prompt_append`）

**扩展难度：低**。修改配置文件即可，无需编码。

---

### 1.14 上下文文件注入

系统提示词自动注入 `~/.hermes/` 下的上下文文件，实现无代码的 agent 行为定制。^[agent/prompt_builder.py:1006]

**注入文件类型：**

| 文件 | 用途 |
|------|------|
| `BOOT.md` | 网关启动时执行（通过 boot-md 钩子） |
| `MEMORY.md` | Agent 持久记忆，自动注入系统提示词 |
| `USER.md` | 用户档案信息 |
| `CONTEXT.md` | 项目级上下文（通过 CLAUDE.md 等机制） |

**扩展方式：** 用户直接编辑 `~/.hermes/` 下的 Markdown 文件，内容自动注入系统提示词。无需编程。^[agent/prompt_builder.py:1006]

**扩展难度：极低**。编辑文本文件即可。

---

### 1.15 Cron 任务系统

周期性任务调度系统，支持用户自定义 cron job。^[cron/scheduler.py:1-65]

**扩展接口：**
- **任务创建**：通过 `cronjob` 工具创建，指定 cron 表达式、提示词、交付目标。^[cron/scheduler.py:52]
- **交付目标格式**：`"origin"`（返回来源）、`"local"`（本地文件）、`"platform"`（平台主频道）、`"platform:chat_id"`（指定聊天）。^[gateway/delivery.py:1-80]
- **执行引擎**：`tick()` 每 60 秒检查到期任务，使用 `ThreadPoolExecutor` 运行 AIAgent。^[cron/scheduler.py:10-12]
- **防并发**：使用基于 `fcntl` 的文件锁（`~/.hermes/cron/.tick.lock`）防止多进程重叠执行。^[cron/scheduler.py:63-64]
- **静默抑制**：agent 输出以 `[SILENT]` 开头时抑制投递（输出仍保存本地）。^[cron/scheduler.py:57]
- **添加新交付平台**：在 `cron/scheduler.py` 的 `_KNOWN_DELIVERY_PLATFORMS` 和 `platform_map` 中注册。^[cron/scheduler.py:45-49]

**扩展难度：低**。通过 `cronjob` 工具交互式创建任务；编程扩展需在 scheduler 中注册新平台。

---

### 1.16 Web 服务扩展（FastAPI）

Web UI 服务器基于 FastAPI，支持 CORS 中间件、静态文件服务和 REST API。^[hermes_cli/web_server.py:64]

**扩展点：**
- **REST API 端点**：直接在 `app` (FastAPI 实例) 上添加新路由。^[hermes_cli/web_server.py:64]
- **中间件**：已配置 CORS 中间件，可添加额外的 middleware。^[hermes_cli/web_server.py:51]
- **静态文件**：Vite/React 前端构建产物通过 `StaticFiles` 挂载。^[hermes_cli/web_server.py:53]

**扩展难度：低**。标准 FastAPI 扩展方式。

---

### 1.17 ACP Adapter —— Agent Communication Protocol

通过 ACP 协议将 hermes-agent 暴露给编辑器集成（VS Code、Zed、JetBrains）。^[acp_adapter/entry.py:1-80]

**扩展点：**
- `HermesACPAgent`（`acp_adapter/server.py`）实现 ACP agent 接口。
- 使用专用 toolset `hermes-acp`，排除 messaging、audio、clarify 等不适合编辑器的工具。^[toolsets.py:226-243]
- ACP 协议版本可通过 `use_unstable_protocol` 标志切换。^[acp_adapter/entry.py:76]

**扩展难度：中**。需要修改 `acp_adapter/server.py` 和 toolset 定义。

---

### 1.18 RL 环境扩展

强化学习训练环境框架。^[environments/hermes_base_env.py:78-221]

**扩展点：**
- **基础环境**：`HermesAgentEnvConfig`（配置数据类）和 `HermesAgentBaseEnv`（BaseEnv 子类）提供扩展基底。^[environments/hermes_base_env.py:78-221]
- **已实现环境**：`web_research_env`、`agentic_opd_env`、`hermes_swe_env`。
- **扩展方式**：子类化 `HermesAgentBaseEnv`，实现环境特定的 reward、action space、observation 逻辑。

**扩展难度：高**。需要理解 RL 训练框架和 BaseEnv 抽象。

---

### 1.19 工具集分布（Toolset Distributions）

为数据生成运行的批次处理定义工具集概率分布，控制各工具集被启用的概率。^[toolset_distributions.py:1-80]

**扩展方式：** 在 `DISTRIBUTIONS` 字典中添加新的分布配置，每个分布指定 toolset -> probability 映射。^[toolset_distributions.py:29-80]

**扩展难度：低**。纯配置式扩展。

---

### 1.20 安全扫描扩展（Tirith）

工具执行前后的安全扫描系统。^[tools/tirith_security.py]

**扩展点：** 通过 `gateway/run.py` 中的配置启用/禁用安全检查。^[gateway/run.py:634-639] 各工具通过 `requires_env` 在注册时声明环境依赖，ToolRegistry 的 `check_fn` 机制提供细粒度可用性控制。^[tools/registry.py:226-227]

**扩展难度：低**。配置驱动。

---

## 二、扩展难度梯度总结

| 难度 | 扩展点 | 扩展方式 |
|------|--------|---------|
| 极低 | 上下文文件注入 | 编辑 `~/.hermes/*.md` 文本文件 |
| 低 | 配置驱动扩展 | 修改 `config.yaml` / `.env` |
| 低 | Skills 技能 | 创建 `SKILL.md` 放入 `skills/` 目录 |
| 低 | 工具注册 | 创建 Python 文件 + `registry.register()` |
| 低 | 工具集定义 | 在 `TOOLSETS` 字典添加条目 / `create_custom_toolset()` |
| 低 | MCP Client | 在 `config.yaml` 添加 MCP 服务器配置 |
| 低 | MCP Server | `@mcp.tool()` 装饰器添加新工具 |
| 低 | 事件钩子 | 创建 `HOOK.yaml` + `handler.py` 放入 `~/.hermes/hooks/` |
| 低 | Agent 回调 | 实现回调函数，传入 AIAgent 构造函数 |
| 低 | 凭证池 | 通过配置添加凭证 |
| 低 | Web 服务 | 标准 FastAPI 路由/中间件扩展 |
| 低 | 工具集分布 | `DISTRIBUTIONS` 字典添加配置 |
| 低 | 安全扫描 | 配置启用/禁用 |
| 低 | Cron 任务 | `cronjob` 工具交互式创建 |
| 中 | Memory Provider 插件 | 实现 `MemoryProvider` ABC（9+ 方法） |
| 中 | Context Engine 插件 | 实现 `ContextEngine` ABC（6+ 方法） |
| 中 | LLM API 模式 | 修改 agent 内 API 管线 |
| 中 | ACP Adapter | 修改 `acp_adapter/server.py` + toolset |
| 高 | 平台适配器 | 16 个集成点，跨越多个子系统 |
| 高 | RL 环境 | 子类化 BaseEnv，需要 RL 领域知识 |

---

## 三、扩展点列表（供后续维度使用）

1. **ToolRegistry** — 工具自注册机制 ^[tools/registry.py:176-228]
2. **Toolset 系统** — 工具集定义与组合 ^[toolsets.py:68-397]
3. **MCP Client** — 消费外部 MCP 服务器工具 ^[tools/mcp_tool.py:1-70]
4. **MCP Server** — 暴露 Hermes 能力给 MCP 客户端 ^[mcp_serve.py:1-78]
5. **HookRegistry** — 生命周期事件钩子 ^[gateway/hooks.py:1-171]
6. **MemoryProvider 插件** — 外部记忆后端 ^[plugins/memory/__init__.py:1-406] ^[agent/memory_provider.py:42-60]
7. **ContextEngine 插件** — 上下文压缩策略 ^[plugins/context_engine/__init__.py:1-220] ^[agent/context_engine.py:32-60]
8. **BasePlatformAdapter** — 消息平台适配器 ^[gateway/platforms/base.py:813-853] ^[gateway/platforms/ADDING_A_PLATFORM.md:1-314]
9. **Agent 回调系统** — 进度/状态/流式回调 ^[run_agent.py:587-599]
10. **Skills 技能系统** — 渐进式信息披露文档 ^[tools/skills_tool.py:1-80]
11. **Skills Hub** — 远程技能注册源 ^[tools/skills_hub.py:1-38]
12. **Skills Sync** — 打包技能同步更新 ^[tools/skills_sync.py:1-22]
13. **CredentialPool** — 多凭证轮换故障转移 ^[agent/credential_pool.py:1-60]
14. **LLM API 模式** — 多 API 后端适配 ^[run_agent.py:690-709]
15. **配置层次** — 多层配置驱动扩展 ^[gateway/run.py:87-107]
16. **上下文文件注入** — 无代码 Agent 行为定制 ^[agent/prompt_builder.py:1006]
17. **Cron 任务调度** — 周期性任务系统 ^[cron/scheduler.py:1-65] ^[cron/jobs.py:1-38]
18. **Web 服务** — FastAPI REST API 扩展 ^[hermes_cli/web_server.py:64]
19. **ACP Adapter** — Agent Communication Protocol ^[acp_adapter/entry.py:1-80]
20. **RL 环境** — 强化学习训练环境 ^[environments/hermes_base_env.py:78-221]
21. **工具集分布** — 数据生成概率分布配置 ^[toolset_distributions.py:1-80]
22. **Tirith 安全扫描** — 工具调用安全检查 ^[tools/tirith_security.py]
23. **SessionSource 扩展** — 会话来源字段扩展 ^[gateway/session.py:65-100]
24. **DeliveryRouter** — 消息投递路由 ^[gateway/delivery.py:1-80]
25. **GatewayStreamConsumer** — 流式输出桥接 ^[gateway/stream_consumer.py:1-60]
