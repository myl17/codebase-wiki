# Hermes-Agent Architecture 维度知识提取

## 一、核心抽象

### 1.1 AIAgent —— 对话编排器

`AIAgent` 是整个 agent 的核心编排类，负责管理对话流程、工具调用循环和响应处理。它封装了一个完整的 LLM 对话生命周期：系统提示词组装、对话历史管理、工具调用执行、错误恢复和上下文压缩。^[run_agent.py:535-617]

关键职责：
- 管理工具调用循环（最多 `max_iterations` 轮，默认 90）^[run_agent.py:569-569]
- 通过回调系统向外部（CLI / Gateway）报告进度：`tool_progress_callback`, `stream_delta_callback`, `thinking_callback`, `clarify_callback`, `step_callback` 等 ^[run_agent.py:587-599]
- 支持多种 API 模式：`chat_completions`（OpenAI 兼容）、`codex_responses`（OpenAI Codex）、`anthropic_messages`、`bedrock_converse` ^[run_agent.py:690-709]
- 自身不感知平台差异，通过 `platform` 属性注入平台提示词 ^[run_agent.py:669-669]

入口方法 `run_conversation()` 串联完整的对话流程：上下文预压缩、系统提示词组装、消息历史加载、工具调用循环、上下文压缩、会话持久化。^[run_agent.py:8130-8157]

### 1.2 GatewayRunner —— 多平台网关控制器

`GatewayRunner` 管理所有平台适配器的生命周期，是消息平台与 AIAgent 之间的桥梁。^[gateway/run.py:538-561]

关键职责：
- 持有所有平台适配器实例（`self.adapters: Dict[Platform, BasePlatformAdapter]`）^[gateway/run.py:562-562]
- 管理会话存储（`SessionStore`）和消息投递路由（`DeliveryRouter`）^[gateway/run.py:579-583]
- 缓存 AIAgent 实例以保持 prompt caching 有效性 ^[gateway/run.py:608-611]
- 管理会话级别的模型覆盖（`/model` 命令）、执行审批和平台重连 ^[gateway/run.py:614-626]
- 核心消息处理管道 `_handle_message()`：授权检查 -> 命令处理 -> 中断处理 -> 会话获取 -> 上下文构建 -> Agent 运行 -> 响应返回 ^[gateway/run.py:2680-2692]

### 1.3 BasePlatformAdapter —— 平台适配器抽象基类

所有消息平台适配器的抽象基类，定义了统一的接口：连接认证、消息接收、消息发送、媒体处理。^[gateway/platforms/base.py:813-853]

子类需要实现的抽象方法包括 `connect()`、`disconnect()`、`send_message()` 等。每个适配器持有 `PlatformConfig` 和 `MessageHandler` 回调，并管理活动会话、待处理消息和后台任务。^[gateway/platforms/base.py:824-853]

当前已实现的平台适配器（共 22 个）：
- Telegram、Discord、WhatsApp、Slack、Signal、Matrix、Mattermost ^[gateway/config.py:48-70]
- Email、SMS、DingTalk、Feishu、WeCom、WeChat、BlueBubbles、QQBot ^[gateway/config.py:48-70]
- HomeAssistant、API Server、Webhook、WeCom Callback ^[gateway/config.py:48-70]

### 1.4 MessageEvent —— 跨平台归一化消息

所有平台适配器将收到的消息归一化为 `MessageEvent` 数据结构，包含消息文本、消息类型（文本/照片/语音/视频/文件/贴纸）、来源信息（`SessionSource`）、媒体附件、回复上下文和自动加载的技能。^[gateway/platforms/base.py:656-721]

### 1.5 SessionSource —— 消息来源描述

描述消息的来源：平台类型、聊天 ID、聊天名称、聊天类型（DM/群组/频道/话题）、用户标识和线程 ID。同时用于回复路由和系统提示词中的上下文注入。^[gateway/session.py:65-100]

### 1.6 SessionContext —— 任务级会话上下文

使用 Python 的 `contextvars.ContextVar` 实现每个 asyncio 任务独立的会话变量副本，解决了 `os.environ` 作为进程全局变量在并发消息处理中的竞争问题。^[gateway/session_context.py:1-67]

保存的上下文变量：`HERMES_SESSION_PLATFORM`、`HERMES_SESSION_CHAT_ID`、`HERMES_SESSION_CHAT_NAME`、`HERMES_SESSION_THREAD_ID`、`HERMES_SESSION_USER_ID`、`HERMES_SESSION_USER_NAME`、`HERMES_SESSION_KEY`。^[gateway/session_context.py:51-57]

### 1.7 SessionDB —— SQLite 会话持久化

SQLite 支持的会话存储，使用 WAL 模式支持并发读取 + 单一写入者。包含 `sessions` 表和 `messages` 表，并通过 FTS5 虚拟表（`messages_fts`）提供全文搜索。支持通过 `parent_session_id` 链实现压缩触发的会话拆分。^[hermes_state.py:1-112]

Schema 版本为 6，记录 token 用量、成本估算、模型配置和 billing 信息。^[hermes_state.py:34-91]

### 1.8 ToolRegistry —— 工具注册中心

所有工具的中央注册表。每个工具模块通过 `registry.register()` 在模块级别自注册其 schema、handler、toolset 归属和可用性检查函数。`ToolRegistry` 是线程安全的单例，使用 `threading.RLock` 保护 MCP 动态刷新时的并发访问。^[tools/registry.py:1-120]

核心数据结构 `ToolEntry` 包含：`name`、`toolset`、`schema`、`handler`、`check_fn`、`requires_env`、`is_async`、`description`、`emoji`、`max_result_size_chars`。^[tools/registry.py:76-97]

工具发现机制通过 AST 解析模块源码检测 `registry.register()` 调用，自动导入所有自注册工具模块。^[tools/registry.py:28-73]

### 1.9 工具集（Toolset）系统

工具集将相关工具分组，支持组合（一个工具集可 `includes` 其他工具集）。所有核心工具定义在 `_HERMES_CORE_TOOLS` 列表中，供 CLI 和所有消息平台共享。^[toolsets.py:31-63]

核心工具类别包括：Web（搜索+提取）、Terminal、文件操作（读写补丁搜索）、Vision/图像生成、浏览器自动化、TTS、Planning/Memory、Session Search、Clarify、代码执行、任务委托、Cronjob 管理、跨平台消息发送和 HomeAssistant 智能家居控制。^[toolsets.py:31-63]

### 1.10 DeliveryRouter / DeliveryTarget —— 消息投递路由

将 cron 任务输出和 agent 响应路由到适当的目标位置。支持格式："origin"（返回来源）、"local"（本地文件）、"platform"（平台主频道）、"platform:chat_id"（指定聊天）。^[gateway/delivery.py:1-80]

### 1.11 CredentialPool —— 多凭证池

支持同一 provider 的多凭证轮换和故障转移。管理 API key 和 OAuth token 的状态（ok/exhausted），支持填充策略（fill_first）和凭证来源标记。^[agent/credential_pool.py:1-60]

### 1.12 ContextCompressor —— 上下文压缩器

自动压缩长对话的上下文窗口。使用辅助模型（廉价/快速）摘要中间轮次，保护头部和尾部上下文。包含结构化摘要模板、token 预算尾部保护和迭代摘要更新。^[agent/context_compressor.py:1-60]

### 1.13 技能（Skills）系统

可扩展的技能插件系统，技能目录位于 `skills/` 之下（按领域分为 22 个类别：apple、autonomous-ai-agents、creative、data-science、devops 等）。^[skills/ 目录]

技能通过 `SKILL.md` 文件定义（含 frontmatter 元数据），agent 根据对话上下文自动匹配和加载相关技能。技能管理工具包括 `skills_list`、`skill_view`、`skill_manage`。^[toolsets.py:41-41]

### 1.14 HookRegistry —— 事件钩子系统

轻量事件驱动系统，在关键生命周期点触发处理器。支持的事件包括：`gateway:startup`、`session:start`、`session:end`、`session:reset`、`agent:start`、`agent:step`、`agent:end`、`command:*`。^[gateway/hooks.py:1-47]

钩子从 `~/.hermes/hooks/` 目录发现加载，每个钩子包含 `HOOK.yaml` 元数据和 `handler.py` 处理器。^[gateway/hooks.py:31-31]

### 1.15 MCP 集成（双向）

**MCP Client** (`tools/mcp_tool.py`)：连接外部 MCP 服务器，发现其工具并注册到 hermes-agent 工具注册表中。支持 stdio 和 HTTP/StreamableHTTP 传输，自动重连和指数退避，线程安全架构。^[tools/mcp_tool.py:1-80]

**MCP Server** (`mcp_serve.py`)：将 hermes-agent 的会话和消息能力暴露为 MCP 工具，供外部 MCP 客户端（Claude Code、Cursor、Codex 等）调用。提供 10 个工具：`conversations_list`、`conversation_get`、`messages_read`、`attachments_fetch`、`events_poll`、`events_wait`、`messages_send`、`permissions_list_open`、`permissions_respond`、`channels_list`。^[mcp_serve.py:1-78]

### 1.16 GatewayStreamConsumer —— 流式输出消费者

将 AIAgent 的同步流回调桥接到异步平台投递。接收 deltas，通过 `asyncio.Queue` 缓冲，按间隔逐步编辑平台上的消息（使用编辑传输模式：先发送初始消息，然后渐进编辑）。^[gateway/stream_consumer.py:1-60]

### 1.17 CronJob 调度器

周期性任务执行系统。任务存储在 `~/.hermes/cron/jobs.json`，输出保存到 `~/.hermes/cron/output/{job_id}/{timestamp}.md`。使用文件锁（`fcntl`）防止并发 tick。Gateway 每 60 秒从后台线程调用 `tick()`。^[cron/scheduler.py:1-64]^[cron/jobs.py:1-38]

---

## 二、分层架构

整个代码库从上到下分为七个层次：

```
┌──────────────────────────────────────────────────────────────────────┐
│  入口层 (Entry Layer)                                                 │
│  hermes (shell), cli.py, hermes_cli/main.py, batch_runner.py,        │
│  rl_cli.py, mini_swe_runner.py                                       │
├──────────────────────────────────────────────────────────────────────┤
│  编排层 (Orchestration Layer)                                         │
│  run_agent.py (AIAgent), gateway/run.py (GatewayRunner)               │
├──────────────────────────────────────────────────────────────────────┤
│  适配器层 (Adapter Layer)                                             │
│  gateway/platforms/ (22 个平台适配器)                                  │
│  acp_adapter/ (Agent Communication Protocol)                          │
├──────────────────────────────────────────────────────────────────────┤
│  核心服务层 (Core Services Layer)                                     │
│  agent/ (memory, context, credentials, prompts, display, errors,      │
│          model metadata, skills, usage pricing)                       │
│  tools/ (60+ 工具模块 + registry + MCP client)                        │
│  toolsets.py (工具集定义与解析)                                         │
│  model_tools.py (工具发现与调度编排)                                    │
├──────────────────────────────────────────────────────────────────────┤
│  存储层 (Storage Layer)                                               │
│  hermes_state.py (SQLite + FTS5)                                      │
│  gateway/session.py (会话存储与会话重置策略)                             │
│  cron/jobs.py (JSON 任务存储)                                          │
│  trajectory_compressor.py (轨迹压缩存储)                               │
├──────────────────────────────────────────────────────────────────────┤
│  集成层 (Integration Layer)                                           │
│  mcp_serve.py (MCP Server 暴露能力)                                    │
│  tools/mcp_tool.py (MCP Client 消费外部工具)                           │
│  gateway/delivery.py (消息投递路由)                                    │
│  gateway/hooks.py (事件钩子)                                           │
│  gateway/pairing.py (用户授权配对)                                     │
│  plugins/ (插件系统: context_engine, memory)                           │
├──────────────────────────────────────────────────────────────────────┤
│  UI 层 (UI Layer)                                                     │
│  hermes_cli/web_server.py (FastAPI Web UI + REST API)                  │
│  hermes_cli/ (CLI TUI: prompt_toolkit, curses, config, setup,         │
│               doctor, auth, models, profiles, plugins)                │
│  web/ (Vite + React 前端构建产物)                                      │
└──────────────────────────────────────────────────────────────────────┘
```

层间依赖方向是自上而下的：入口层导入编排层，编排层导入核心服务层和适配器层，核心服务层导入存储层和集成层。各层之间通过明确定义的公共 API 通信。

---

## 三、数据流

### 3.1 主数据流（消息平台 -> Agent -> 回复）

```
Message Platform (Telegram/Discord/WhatsApp/...)
  │  incoming message (webhook/polling/long-polling)
  ▼
BasePlatformAdapter (platform-specific)
  │  normalizes to MessageEvent + SessionSource
  ▼
GatewayRunner._handle_message(event)
  │  1. Authorization check (pairing store)
  │  2. Command interception (/new, /reset, /model, etc.)
  │  3. Session resolution (SessionStore.get_or_create)
  │  4. Session context injection (contextvars)
  ▼
GatewayRunner._handle_message_with_agent()
  │  1. Build AIAgent instance (or reuse from cache for prompt caching)
  │  2. Load conversation history from SessionDB
  │  3. Invoke AIAgent.run_conversation(user_message, history, callbacks)
  ▼
AIAgent.run_conversation()
  │  1. Preflight context compression (if needed)
  │  2. Build system prompt (identity + platform hints + skills + memory + context files)
  │  3. Tool-calling loop:
  │     a. Send messages to LLM API (with tool definitions)
  │     b. Parse response: text content + tool calls
  │     c. Execute tool calls (sequential or concurrent)
  │     d. Append results to messages, loop back to (a)
  │  4. Post-turn memory review nudge (periodic)
  │  5. Persist messages to SessionDB
  ▼
GatewayRunner
  │  Collect response text from AIAgent result
  ▼
BasePlatformAdapter.send_message(chat_id, text, ...)
  │  Platform-specific delivery (sendMessage, editMessageText, etc.)
  ▼
Message Platform → User receives response
```

### 3.2 工具调用数据流

```
AIAgent._execute_tool_calls()
  │
  ├─ Sequential mode (default)
  │    for each tool_call in assistant_message.tool_calls:
  │      model_tools.handle_function_call(name, args, task_id) → result
  │      append {"role": "tool", "tool_call_id": ..., "content": result}
  │
  └─ Concurrent mode (当所有工具调用都是独立只读操作时)
       ThreadPoolExecutor.map() → parallel tool execution
       append all results at once
  │
  ▼
model_tools.handle_function_call()
  │  1. Lookup tool in ToolRegistry
  │  2. Run check_fn() for availability
  │  3. Call tool handler (sync or async via event loop bridge)
  │  4. Apply result size limits, persist large results
  │  5. Run security checks (Tirith)
  ▼
Return formatted result to AIAgent → appended to messages
```

### 3.3 流式输出数据流

```
AIAgent (worker thread)
  │  stream_delta_callback(text) — synchronous, called per token delta
  ▼
GatewayStreamConsumer.on_delta(text)
  │  thread-safe queue.Queue.put(text) or sentinel (_DONE, _NEW_SEGMENT)
  ▼
GatewayStreamConsumer.run() (asyncio task)
  │  Buffers deltas, rate-limits, progressively edits platform message
  ▼
BasePlatformAdapter.edit_message(chat_id, message_id, accumulated_text)
```

### 3.4 Cron 任务数据流

```
GatewayRunner (background thread, every 60s)
  │  cron.scheduler.tick()
  ▼
cron.jobs.get_due_jobs() → filter by cron expression + last_run
  ▼
AIAgent.run_conversation(job.prompt) — in ThreadPoolExecutor
  ▼
cron.jobs.save_job_output(job_id, result) → ~/.hermes/cron/output/
  ▼
DeliveryRouter.route(output, job.delivery_target) → platform-specific delivery
```

### 3.5 上下文压缩数据流

```
AIAgent.run_conversation()
  │  estimate_request_tokens_rough(messages, system_prompt, tools)
  │  if tokens >= context_compressor.threshold_tokens:
  ▼
AIAgent._compress_context(messages, system_message)
  │  1. Compute summary budget (proportional to compressed content)
  │  2. Summarize middle turns via auxiliary LLM (cheap/fast model)
  │  3. Insert summary as system message at boundary
  │  4. Create new child session (parent_session_id chain)
  │  5. Return compressed messages + updated system prompt
```

数据流方向整体是**单向**的：用户消息进入 -> 编排处理 -> LLM 调用 -> 工具执行 -> 响应返回。中断支持提供了有限的**反向控制流**（用户发送新消息中断正在运行的 agent）。

---

## 四、关注点分离

### 4.1 平台无关核心 vs 平台适配

AIAgent 完全不感知具体的消息平台。平台差异通过以下机制注入：
- `platform` 属性 -> `PLATFORM_HINTS` 字典选择格式提示词 ^[agent/prompt_builder.py:83-83]
- `SessionContext` 通过 `contextvars` 传递平台上下文给工具 ^[gateway/session_context.py:51-57]
- `GatewayRunner` 负责将平台特定的 `MessageEvent` 转换为 AIAgent 的标准输入 ^[gateway/run.py:2680-2692]
- `BasePlatformAdapter` 负责将 AIAgent 的标准输出转换回平台特定的消息格式 ^[gateway/platforms/base.py:813-853]

### 4.2 工具系统解耦

工具模块通过**自注册模式**与编排层解耦：
- 每个工具文件在模块级别调用 `registry.register()` 声明其 schema、handler 和 toolset ^[tools/registry.py:1-15]
- `model_tools.py` 作为薄编排层，触发工具发现并提供公共 API ^[model_tools.py:1-31]
- `toolsets.py` 独立定义工具分组逻辑，与具体工具实现分离 ^[toolsets.py:1-25]
- MCP 工具通过相同注册机制动态注入，无需特殊处理 ^[tools/mcp_tool.py:1-70]

### 4.3 API 模式抽象

AIAgent 支持四种 LLM API 模式，通过适配器模块处理差异：
- `chat_completions`：标准 OpenAI 兼容 API（默认）
- `anthropic_messages`：Anthropic Messages API，通过 `agent/anthropic_adapter.py` ^[agent/anthropic_adapter.py:1-1]
- `bedrock_converse`：AWS Bedrock Converse API，通过 `agent/bedrock_adapter.py` ^[agent/bedrock_adapter.py:1-1]
- `codex_responses`：OpenAI Codex Responses API

API 模式在 `__init__` 中根据 provider 和 base_url 自动检测。^[run_agent.py:690-709]

### 4.4 会话与存储分离

- `gateway/session.py` 的 `SessionStore` 管理会话生命周期（创建、重置策略判定）^[gateway/session.py:1-100]
- `hermes_state.py` 的 `SessionDB` 负责持久化存储（SQLite + FTS5）^[hermes_state.py:1-112]
- Batch runner 和 RL trajectory 使用独立的存储系统，不进入 SessionDB ^[hermes_state.py:13-13]

### 4.5 异步与同步的桥接

- `model_tools.py` 提供 `_get_tool_loop()` 和 `_get_worker_loop()` 桥接异步工具处理器和同步调用者 ^[model_tools.py:44-78]
- `GatewayStreamConsumer` 桥接 AIAgent 的同步流回调到异步平台投递 ^[gateway/stream_consumer.py:1-60]
- `GatewayRunner` 使用 `run_in_executor` 在异步事件循环中运行同步的 AIAgent ^[gateway/run.py:727-737]

### 4.6 安全关注点

- `tools/tirith_security.py`：工具调用前后的安全扫描 ^[gateway/run.py:634-639]
- `agent/prompt_builder.py`：上下文文件注入前的注入攻击检测（`_CONTEXT_THREAT_PATTERNS`）^[agent/prompt_builder.py:36-47]
- `tools/path_security.py`：文件系统操作的路径安全检查
- `gateway/pairing.py`：用户授权配对系统 ^[gateway/run.py:650-651]
- `tools/approval.py`：工具执行审批流程
- `tools/url_safety.py`：URL 安全检查
- `tools/website_policy.py`：网站访问策略控制
- `agent/redact.py`：敏感信息脱敏

### 4.7 配置层次

配置通过多层叠加解决：
1. 代码内默认值（`DEFAULT_CONFIG`）^[hermes_cli/web_server.py:34-34]
2. 项目 `.env` 文件
3. 用户 `~/.hermes/.env` 文件 ^[gateway/run.py:87-87]
4. 用户 `~/.hermes/config.yaml`（对 terminal 配置具有权威性，覆盖 .env）^[gateway/run.py:89-107]
5. 环境变量 `$ENV_VAR`（最高优先级，通过 `${ENV_VAR}` 插值在 config.yaml 中展开）^[gateway/run.py:98-99]

---

## 五、核心抽象列表

1. **AIAgent** — 对话编排器，管理 LLM 工具调用循环 ^[run_agent.py:535-617]
2. **GatewayRunner** — 多平台网关控制器，管理适配器生命周期和消息路由 ^[gateway/run.py:538-561]
3. **BasePlatformAdapter** — 平台适配器抽象基类（22 个实现）^[gateway/platforms/base.py:813-853]
4. **MessageEvent** — 跨平台归一化消息 ^[gateway/platforms/base.py:656-721]
5. **SessionSource** — 消息来源描述 ^[gateway/session.py:65-100]
6. **SessionContext** — 任务级会话上下文（contextvars）^[gateway/session_context.py:1-67]
7. **SessionDB** — SQLite 会话持久化存储（FTS5 全文搜索）^[hermes_state.py:115-120]
8. **SessionStore** — 会话生命周期管理（重置策略判定）^[gateway/session.py:1-1]
9. **ToolRegistry** — 工具注册中心（自注册模式）^[tools/registry.py:100-120]
10. **ToolEntry** — 工具元数据条目 ^[tools/registry.py:76-97]
11. **Toolset（工具集）** — 工具分组与组合系统 ^[toolsets.py:31-63]
12. **DeliveryRouter / DeliveryTarget** — 消息投递路由 ^[gateway/delivery.py:1-80]
13. **GatewayConfig / PlatformConfig / HomeChannel** — 配置数据类 ^[gateway/config.py:1-120]
14. **CredentialPool** — 多凭证池（故障转移）^[agent/credential_pool.py:1-60]
15. **ContextCompressor** — 上下文窗口自动压缩 ^[agent/context_compressor.py:1-60]
16. **Skill（技能）** — 可扩展技能插件系统（22 个领域）^[skills/ 目录]
17. **HookRegistry** — 事件钩子系统 ^[gateway/hooks.py:1-47]
18. **MCP Client** — 消费外部 MCP 服务器的工具 ^[tools/mcp_tool.py:1-80]
19. **MCP Server** — 暴露 hermes-agent 能力给 MCP 客户端 ^[mcp_serve.py:1-78]
20. **GatewayStreamConsumer** — 流式输出同步-异步桥接 ^[gateway/stream_consumer.py:1-60]
21. **CronJob Scheduler** — 周期性任务执行系统 ^[cron/scheduler.py:1-64]
22. **WebServer** — FastAPI Web UI 服务器 ^[hermes_cli/web_server.py:1-64]
23. **BatchRunner** — 批量执行器 ^[batch_runner.py:1-1]
24. **RL Environment** — 强化学习训练环境 ^[environments/ 目录]
25. **Plugin（插件）** — context_engine 和 memory 插件系统 ^[plugins/ 目录]
26. **ACP Adapter** — Agent Communication Protocol 适配器 ^[acp_adapter/ 目录]
