# Hermes-Agent 扩展点维度分析

> 本文档基于 hermes-agent 源码静态分析，梳理所有可扩展接口、插件机制、生命周期钩子和定制化入口。

---

## 1. 核心插件系统 (Plugin System)

### 1.1 总览

hermes-agent 拥有一套完整的三源插件体系。插件入口文件为 `hermes_cli/plugins.py`，定义了 `PluginManager`、`PluginContext` 和模块级单例 `get_plugin_manager()`。^[hermes_cli/plugins.py:1-27]

### 1.2 插件的三种来源

| 来源 | 路径 | 激活条件 |
|------|------|----------|
| **用户插件** | `~/.hermes/plugins/<name>/` | 始终扫码 |
| **项目插件** | `./.hermes/plugins/<name>/` | 需设置 `HERMES_ENABLE_PROJECT_PLUGINS` 环境变量 |
| **Pip 插件** | Python 包暴露 `hermes_agent.plugins` entry-point | 始终扫码 |

^[hermes_cli/plugins.py:341-353]

### 1.3 插件目录结构要求

每个目录插件必须包含：

1. **`plugin.yaml`（或 `plugin.yml`）** — 声明元数据：`name`、`version`、`description`、`author`、`requires_env`、`provides_tools`、`provides_hooks` ^[hermes_cli/plugins.py:93-104]
2. **`__init__.py`** — 必须含有顶层的 `register(ctx)` 函数，接收一个 `PluginContext` 实例 ^[hermes_cli/plugins.py:14-15]

Pip 插件通过 `importlib.metadata.entry_points()` 发现，group 名为 `"hermes_agent.plugins"` ^[hermes_cli/plugins.py:67]

### 1.4 PluginContext API（插件的注册能力）

`PluginContext` 是 `register(ctx)` 函数接收的唯一参数，提供以下注册方法：

- **`register_tool(name, toolset, schema, handler, ...)`** — 向全局工具注册表注册一个新工具 ^[hermes_cli/plugins.py:132-159]
- **`register_hook(hook_name, callback)`** — 注册生命周期钩子回调 ^[hermes_cli/plugins.py:248-263]
- **`register_cli_command(name, help, setup_fn, ...)`** — 注册 CLI 子命令（如 `hermes honcho ...`） ^[hermes_cli/plugins.py:191-212]
- **`register_context_engine(engine)`** — 注册上下文引擎替代内置的 ContextCompressor（仅允许一个） ^[hermes_cli/plugins.py:216-244]
- **`register_skill(name, path, description)`** — 注册插件提供的只读技能，可通过 `<plugin_name>:<name>` 解析 ^[hermes_cli/plugins.py:267-310]
- **`inject_message(content, role)`** — 向活跃会话注入消息（支持中断正在运行的 agent） ^[hermes_cli/plugins.py:163-187]

### 1.5 插件禁用机制

用户可通过 `config.yaml` 中的 `plugins.disabled` 列表禁用特定插件 ^[hermes_cli/plugins.py:77-85]

---

## 2. 生命周期钩子 (Lifecycle Hooks)

### 2.1 钩子事件清单

插件系统定义了 10 个标准化钩子事件 ^[hermes_cli/plugins.py:54-65]：

| 钩子名称 | 触发时机 | 触发位置 |
|----------|----------|----------|
| `on_session_start` | 新会话创建时（首次对话，非续接） | `run_agent.py` ^[run_agent.py:8319-8325] |
| `on_session_end` | 会话结束时（interrupt 安全网） | `cli.py` ^[cli.py:9781-9789] |
| `on_session_finalize` | 会话关闭/退出前（CLI exit、/reset） | `cli.py` ^[cli.py:625-629] |
| `on_session_reset` | 会话重置后（新会话入口已创建） | `cli.py` ^[cli.py:4144] |
| `pre_llm_call` | 每次 LLM API 调用前 | `run_agent.py` ^[run_agent.py:8421-8430] |
| `post_llm_call` | 每次 LLM 工具调用循环完成后 | `run_agent.py` ^[run_agent.py:11167-11178] |
| `pre_tool_call` | 每个工具调用前（可阻止执行） | `model_tools.py` ^[model_tools.py:457-487] |
| `post_tool_call` | 每个工具调用后 | `model_tools.py` ^[model_tools.py:514-520] |
| `pre_api_request` | 每个 API HTTP 请求发送前 | `run_agent.py` ^[run_agent.py:8776-8793] |
| `post_api_request` | 每个 API 响应接收后 | `run_agent.py` ^[run_agent.py:10272-10295] |

### 2.2 pre_llm_call 上下文注入机制

`pre_llm_call` 钩子的独特之处在于它支持上下文注入。回调可返回一个包含 `context` 字段的 dict 或纯字符串，这些内容会被**注入到当前轮次的用户消息**中（而非系统提示词），以保持 prompt cache 前缀不变 ^[hermes_cli/plugins.py:556-567]

### 2.3 pre_tool_call 工具阻断机制

`get_pre_tool_call_block_message()` 函数检查 `pre_tool_call` 钩子的返回值。如果任何插件回调返回 `{"action": "block", "message": "原因"}`，工具调用将被阻止，错误消息作为工具返回结果 ^[hermes_cli/plugins.py:658-694]

阻断检测在 `model_tools.py` 的 `handle_function_call()` 中进行 ^[model_tools.py:457-472]

### 2.4 钩子调用容错

所有钩子调用都被 wrap 在 try/except 中，单个插件的异常不会破坏核心 agent 循环 ^[hermes_cli/plugins.py:570-582]

---

## 3. 工具注册中心 (Tool Registry)

### 3.1 架构

`ToolRegistry` 是全局单例（`tools/registry.py:437`），所有工具（内置、插件提供、MCP 动态注册）均通过它管理 ^[tools/registry.py:1-15]

### 3.2 工具注册接口

每个工具通过 `registry.register()` 注册，参数包括 ^[tools/registry.py:176-228]：

```python
registry.register(
    name,           # 工具名称，全局唯一
    toolset,        # 工具集归属
    schema,         # OpenAI 格式的 function schema
    handler,        # 调用处理函数 Callable
    check_fn,       # 可用性检查函数（返回 bool）
    requires_env,   # 所需环境变量列表
    is_async,       # 是否为异步 handler
    description,    # 工具描述
    emoji,          # 工具图标 emoji
    max_result_size_chars,  # 结果大小限制
)
```

### 3.3 工具模块自动发现

`discover_builtin_tools()` 通过 AST 分析扫描 `tools/` 目录下所有 `.py` 文件，识别包含顶层 `registry.register(...)` 调用的模块并自动导入 ^[tools/registry.py:56-73]

### 3.4 工具集别名 (Toolset Aliases)

支持为工具集注册别名，MCP 服务器工具集自动获得 `mcp-*` 前缀的别名 ^[tools/registry.py:151-170]

### 3.5 工具冲突保护

插件/MCP 工具不能覆盖内置工具（不同 toolset 间的同名注册会被拒绝日志记录）。MCP 到 MCP 的覆盖被允许（处理服务器刷新场景） ^[tools/registry.py:191-213]

### 3.6 工具注销

`deregister(name)` 支持动态移除工具。MCP 动态发现时使用（`notifications/tools/list_changed` 事件触发 nuke-and-repave 流程） ^[tools/registry.py:229-252]

---

## 4. MCP (Model Context Protocol) 集成

### 4.1 配置方式

在 `~/.hermes/config.yaml` 的 `mcp_servers` 键下配置。支持两种传输方式 ^[tools/mcp_tool.py:5-30]：

**Stdio 传输：**
```yaml
mcp_servers:
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    timeout: 120
    connect_timeout: 60
```

**HTTP/StreamableHTTP 传输：**
```yaml
mcp_servers:
  remote_api:
    url: "https://my-mcp-server.example.com/mcp"
    headers:
      Authorization: "Bearer sk-..."
    timeout: 180
```

### 4.2 采样支持 (Sampling)

MCP 服务器可请求 LLM 补全（`sampling/createMessage`） ^[tools/mcp_tool.py:35-43]

```yaml
analysis:
  command: "npx"
  args: ["-y", "analysis-server"]
  sampling:
    enabled: true
    model: "gemini-3-flash"       # 可选覆盖
    max_tokens_cap: 4096
    timeout: 30
    max_rpm: 10                    # 每分钟最大请求数
    allowed_models: []             # 模型白名单
    max_tool_rounds: 5             # 工具循环限制
```

### 4.3 架构

MCP 在专用守护线程中运行自己的 event loop，每个 MCP 服务器作为长期 asyncio Task 运行 ^[tools/mcp_tool.py:55-69]

---

## 5. 技能系统 (Skills)

### 5.1 目录结构

技能以目录组织在 `~/.hermes/skills/` 下 ^[tools/skills_tool.py:14-26]：

```
skills/
  my-skill/
    SKILL.md           # 必需：主指令文件
    references/        # 可选：参考文档
    templates/         # 可选：输出模板
    assets/            # 可选：辅助文件（agentskills.io 标准）
```

### 5.2 SKILL.md 格式（YAML 前置元数据）

^[tools/skills_tool.py:28-53]

```yaml
---
name: skill-name              # 必需，≤64 字符
description: 简要描述         # 必需，≤1024 字符
version: 1.0.0
platforms: [macos]            # 限 OS 平台
prerequisites:
  env_vars: [API_KEY]         # 被规范化为 required_environment_variables
  commands: [curl, jq]        # 命令检查（建议性）
metadata:
  hermes:
    tags: [fine-tuning]
    related_skills: [peft]
---
```

### 5.3 渐进式信息披露架构

- **层级 1**：`skills_list` — 仅返回元数据（名称、描述）^[tools/skills_tool.py:54-66]
- **层级 2**：`skill_view(name)` — 加载完整指令
- **层级 3**：`skill_view(name, reference_path)` — 按需加载链接文件

### 5.4 平台过滤

技能可通过 `platforms: [macos, linux, windows]` 声明 OS 限制，通过 `skill_matches_platform()` 在加载时过滤 ^[agent/skill_utils.py:92-115]

### 5.5 可选技能包

`optional-skills/` 目录包含 15 个技能类别（creative、devops、research、security 等），用户可选择安装 ^[optional-skills/]

### 5.6 技能命令（斜杠命令）

`agent/skill_commands.py` 支持通过 `/skill-name` 斜杠命令直接调用技能，CLI 和网关两端共享 ^[agent/skill_commands.py:1-18]

---

## 6. 上下文引擎 (Context Engine)

### 6.1 抽象基类

`agent/context_engine.py` 定义了 `ContextEngine` ABC。第三方引擎替换内置的 `ContextCompressor` ^[agent/context_engine.py:1-26]

### 6.2 必须实现的接口

^[agent/context_engine.py:32-100]

- **`name`** — 引擎标识符
- **`update_from_response(usage)`** — 每次 API 响应后更新 token 追踪
- **`should_compress(prompt_tokens)`** — 判断是否需要压缩
- **`compress(messages, current_tokens)`** — 压缩消息列表并返回新列表

### 6.3 可选接口

- **`should_compress_preflight(messages)`** — 预检（默认返回 False）
- **`threshold_percent`** (0.75)、**`protect_first_n`** (3)、**`protect_last_n`** (6) — 可配置压缩参数

### 6.4 注册方式

1. 插件通过 `PluginContext.register_context_engine()` 注册（仅限一个） ^[hermes_cli/plugins.py:216-244]
2. 通过 `config.yaml` 中的 `context.engine` 配置选择 ^[agent/context_engine.py:9]

---

## 7. 内存提供者 (Memory Provider)

### 7.1 抽象基类

`agent/memory_provider.py` 定义了 `MemoryProvider` ABC ^[agent/memory_provider.py:1-32]

### 7.2 强制接口

^[agent/memory_provider.py:42-101]

- **`name`** — 提供者标识符
- **`is_available()`** — 检查配置/凭据是否就绪（不应有网络调用）
- **`initialize(session_id, **kwargs)`** — 会话初始化连接/创建资源
- **`system_prompt_block()`** — 提供静态系统提示文本
- **`prefetch(query, session_id)`** — 每轮前后台召回相关上下文
- **`sync_turn(user_msg, assistant_msg)`** — 每轮后异步写入
- **`get_tool_schemas()`** / **`handle_tool_call(name, args)`** — 工具 schema 暴露和调用调度
- **`shutdown()`** — 清理退出

### 7.3 可选钩子

^[agent/memory_provider.py:25-30]

- **`on_turn_start(turn, message, ...)`** — 每轮 tick
- **`on_session_end(messages)`** — 会话结束提取
- **`on_pre_compress(messages) -> str`** — 压缩前提取摘要
- **`on_memory_write(action, target, content)`** — 镜像内置内存写入
- **`on_delegation(task, result, ...)`** — 子代理工作观察

### 7.4 注册限制

- 内置提供者始终激活，不可移除
- 同一时间仅允许一个外部提供者（防止 schema 膨胀和冲突） ^[agent/memory_provider.py:9-10]
- 外部提供者通过 `memory.provider` 配置激活，插件形式放置于 `plugins/memory/<name>/`

---

## 8. 模型与提供者 (Models & Providers)

### 8.1 规范提供者列表

`hermes_cli/models.py` 中的 `CANONICAL_PROVIDERS` 定义 24 个规范提供者，采用 `ProviderEntry(slug, label, tui_desc)` 结构，是所有模型选择路径的唯一数据源 ^[hermes_cli/models.py:531-556]

### 8.2 提供者别名系统

70+ 个别名映射到规范 slug（如 `"claude" → "anthropic"`, `"hf" → "huggingface"`, `"grok" → "xai"`） ^[hermes_cli/models.py:562-614]

### 8.3 模型目录

- **`_PROVIDER_MODELS`** — 每个提供者的模型 ID 列表 ^[hermes_cli/models.py:73-322]
- **`OPENROUTER_MODELS`** — OpenRouter 静态回退列表 ^[hermes_cli/models.py:26-57]
- **`fetch_openrouter_models()`** — 从 OpenRouter API 拉取实时模型目录 ^[hermes_cli/models.py:641-693]
- **`models_dev.py`** — 从 `models.dev` 拉取 4000+ 模型的完整元数据（离线优先 + 磁盘缓存 + 网络拉取） ^[agent/models_dev.py:1-20]

### 8.4 Codex 模型扩展

`hermes_cli/codex_models.py` 管理 OpenAI Codex 平台的模型列表，支持前向兼容模型合成 ^[hermes_cli/models.py:62-70]

### 8.5 自定义模型接入

用户可通过 `hermes_cli/models.py` 或 `config.yaml` 添加自定义模型和 provider 映射

---

## 9. 工具集系统 (Toolsets)

### 9.1 核心定义

`toolsets.py` 定义了 40+ 个命名工具集，支持可组合的层次结构 ^[toolsets.py:68-396]

### 9.2 工具集特性

- **组合** — 工具集可通过 `includes` 引用其他工具集（如 `"debugging": {includes: ["web", "file"]}`）
- **循环依赖安全** — `resolve_toolset()` 检测并安全处理循环/菱形依赖 ^[toolsets.py:447-498]
- **运行时创建** — `create_custom_toolset(name, description, tools, includes)` 支持动态创建 ^[toolsets.py:613-633]
- **特殊别名** — `"all"` 和 `"*"` 解析为所有工具集的并集 ^[toolsets.py:466-472]

### 9.3 插件工具集发现

`get_toolset()` / `get_all_toolsets()` 自动包含插件和 MCP 注册的工具集，与静态定义的 TOOLSETS 合并 ^[toolsets.py:519-588]

### 9.4 工具集禁用

通过 `disabled_toolsets` 参数在运行时排除整组工具 ^[run_agent.py:796]

---

## 10. 执行环境 (Execution Environments)

### 10.1 抽象基类

`tools/environments/base.py` 定义了 `BaseEnvironment` ABC。所有后端实现统一的 `execute()` 流程 ^[tools/environments/base.py:226-298]

### 10.2 必须实现的方法

- **`_run_bash(cmd_string, timeout, stdin_data)`** — 启动 bash 进程，返回 `ProcessHandle`
- **`cleanup()`** — 释放后端资源

### 10.3 已实现后端

| 后端 | 文件 |
|------|------|
| Local | `tools/environments/local.py` |
| Docker | `tools/environments/docker.py` |
| Singularity | `tools/environments/singularity.py` |
| SSH | `tools/environments/ssh.py` |
| Modal | `tools/environments/modal.py` |
| Daytona | `tools/environments/daytona.py` |

### 10.4 ProcessHandle 协议

SDK 后端（Modal、Daytona）使用 `_ThreadedProcessHandle` 适配器，将阻塞调用包装为 `ProcessHandle` 兼容接口 ^[tools/environments/base.py:143-209]

### 10.5 认证文件挂载

`tools/credential_files.py` 提供会话范围的凭据文件注册，确保远程后端可访问必要的凭据文件和安全目录挂载 ^[tools/credential_files.py:1-80]

---

## 11. 网关事件钩子 (Gateway Event Hooks)

### 11.1 总览

`gateway/hooks.py` 定义了独立的网关事件钩子系统，与插件系统的生命周期钩子并行 ^[gateway/hooks.py:1-20]

### 11.2 事件类型

^[gateway/hooks.py:8-17]

- **`gateway:startup`** — 网关进程启动
- **`session:start`** — 新会话创建
- **`session:end`** — 会话结束
- **`session:reset`** — 会话重置
- **`agent:start`** — Agent 开始处理消息
- **`agent:step`** — 工具调用循环中的每一步
- **`agent:end`** — Agent 处理完成
- **`command:*`** — 通配符匹配所有斜杠命令

### 11.3 钩子目录结构

放在 `~/.hermes/hooks/<name>/` 下，需包含 ^[gateway/hooks.py:84-136]：

- **`HOOK.yaml`** — 声明 `name`、`events` 列表、`description`
- **`handler.py`** — 包含顶层 `handle(event_type, context)` 函数（同步或异步均可）

### 11.4 内置钩子

- **`boot_md`** — 在网关启动时执行 `~/.hermes/BOOT.md` 中的指令 ^[gateway/builtin_hooks/boot_md.py:1-50]

---

## 12. ACP 适配器 (Agent Client Protocol)

### 12.1 总览

`acp_adapter/server.py` 实现了 Agent Client Protocol，将 hermes-agent 暴露给 VS Code、Zed、JetBrains 等编辑器 ^[acp_adapter/server.py:1-80]

### 12.2 子模块

- **`acp_adapter/auth.py`** — 提供者认证检测
- **`acp_adapter/events.py`** — 事件回调（消息、步骤、思考、工具进度）
- **`acp_adapter/permissions.py`** — 审批回调
- **`acp_adapter/session.py`** — 会话管理和状态
- **`acp_adapter/tools.py`** — 工具桥接

---

## 13. API 服务器

### 13.1 MCP 服务

`mcp_serve.py` 通过 MCP 协议暴露 hermes-agent，可作为 MCP 服务器被其他 MCP 客户端调用

### 13.2 OpenAI 兼容端点

支持 `hermes-api-server` 工具集，通过 HTTP 暴露 OpenAI 兼容的 API 端点（`/v1/chat/completions`），允许任何 OpenAI SDK 客户端接入 ^[toolsets.py:245-276]

---

## 14. 扩展难度梯度

| 扩展方式 | 难度 | 说明 |
|----------|------|------|
| 安装可选技能 | 最低 | 复制 SKILL.md 目录到 `~/.hermes/skills/` |
| 添加技能 | 低 | 创建 SKILL.md 目录，声明 YAML frontmatter |
| 配置 MCP 服务器 | 低 | 在 config.yaml 添加 mcp_servers 条目 |
| 修改模型/提供者列表 | 低 | 编辑 `hermes_cli/models.py` 中的 `_PROVIDER_MODELS` |
| 自定义工具集 | 低 | 调用 `create_custom_toolset()` 或在 config.yaml 配置 |
| 网关事件钩子 | 中 | 创建 `HOOK.yaml` + `handler.py` 在 `~/.hermes/hooks/` |
| 自定义工具模块 | 中 | 创建含 `registry.register()` 的 `.py` 文件放置在 `tools/` |
| 完整插件（目录） | 中 | 创建 `plugin.yaml` + `__init__.py`，使用 PluginContext API |
| 完整插件（pip） | 中高 | 同上 + 配置 `setup.py` entry_point |
| 自定义上下文引擎 | 高 | 实现 `ContextEngine` 所有抽象方法并注册 |
| 自定义内存提供者 | 高 | 实现 `MemoryProvider` 所有抽象方法并注册 |
| 自定义执行环境后端 | 最高 | 实现 `BaseEnvironment._run_bash()` 和 `cleanup()` |
| 自定义 LLM API 适配器 | 最高 | 实现类似 `anthropic_adapter.py` 的消息格式翻译和请求构建 |

---

## 15. 扩展点关联图

```
                     ┌──────────────────────┐
                     │   config.yaml/.env    │
                     │  (配置驱动扩展入口)    │
                     └──────┬───────────────┘
                            │
    ┌───────────────────────┼───────────────────────────┐
    │                       │                           │
    ▼                       ▼                           ▼
┌──────────┐        ┌──────────────┐          ┌────────────────┐
│  Skills   │        │ Plugin System │          │ MCP Servers     │
│ SKILL.md  │◄──────►│ plugin.yaml   │          │ (stdio/HTTP)    │
│ 目录结构  │        │ register(ctx) │          │ mcp_servers配置  │
└────┬─────┘        └──────┬───────┘          └───────┬────────┘
     │                     │                          │
     │            ┌────────┼────────┐                 │
     │            ▼        ▼        ▼                 │
     │     ┌──────────┐ ┌──────┐ ┌──────────┐       │
     │     │register_  │ │register│ │register_ │       │
     │     │tool()     │ │_hook() │ │context_  │       │
     │     │           │ │        │ │engine()  │       │
     │     └─────┬─────┘ └───┬────┘ └────┬─────┘       │
     │           │            │           │              │
     ▼           ▼            ▼           ▼              ▼
  ┌─────────────────────────────────────────────────────────┐
  │                  Tool Registry (tools/registry.py)        │
  │              全局单例 — 所有工具的注册、调度、发现          │
  └──────────────────────────┬──────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │ model_   │  │ run_agent│  │ gateway/      │
        │ tools.py │  │ .py      │  │               │
        │ 工具调度  │  │ Agent循环 │  │ 事件钩子系统   │
        └──────────┘  └──────────┘  └──────────────┘
```

---

## 16. 关键文件索引

| 文件 | 角色 |
|------|------|
| `hermes_cli/plugins.py` | 插件系统核心：PluginManager、PluginContext、钩子调用 |
| `tools/registry.py` | 工具注册中心：ToolRegistry 单例、工具自动发现 |
| `toolsets.py` | 工具集定义、组合、解析 |
| `tools/mcp_tool.py` | MCP 客户端：工具发现、自动注册 |
| `agent/context_engine.py` | 上下文引擎抽象基类 |
| `agent/memory_provider.py` | 内存提供者抽象基类 |
| `agent/skill_utils.py` | 技能元数据共享工具 |
| `agent/skill_commands.py` | 技能斜杠命令共享实现 |
| `tools/skills_tool.py` | 技能工具：skills_list、skill_view |
| `tools/environments/base.py` | 执行环境抽象基类 |
| `tools/credential_files.py` | 凭据文件注册和远程后端挂载 |
| `gateway/hooks.py` | 网关事件钩子系统 |
| `gateway/builtin_hooks/boot_md.py` | 内置启动钩子 |
| `hermes_cli/models.py` | 模型和提供者目录 |
| `agent/models_dev.py` | models.dev 集成 |
| `hermes_cli/config.py` | 配置管理 |
| `model_tools.py` | 工具调用调度、pre/post 钩子触发 |
| `run_agent.py` | Agent 主循环、生命周期钩子触发 |
| `acp_adapter/server.py` | ACP 协议服务器 |
| `environments/` | RL 训练环境扩展 |
| `cron/` | 定时任务系统 |
