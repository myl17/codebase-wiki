# Hermes Agent — Architecture 维度分析

## 核心抽象

### 1. AIAgent（中央编排器）

`AIAgent` 是整个系统的核心抽象，位于 `run_agent.py`。它是一个完整的对话代理，管理模型调用、工具执行、响应处理和上下文生命周期。每个代理实例拥有独立的迭代预算（`IterationBudget`）、工具定义列表、会话 ID 和回调管道。

关键职责：
- 持有与 LLM 提供商的连接（OpenAI 兼容客户端、Anthropic 适配器或 Bedrock 适配器）
- 维护对话消息列表（`messages`），支持会话历史继承
- 在每个 turn 中构建 API 消息（含记忆注入、插件上下文、ephemeral 系统提示），执行 LLM 调用，处理工具调用或文本响应
- 管理子代理委托（通过 `delegate_task` 工具生成子 `AIAgent` 实例，每子代理拥有隔离上下文和受限工具集）
- 暴露回调接口（`stream_delta_callback`、`tool_progress_callback`、`clarify_callback`、`step_callback`、`thinking_callback` 等），供上层平台层接入

^[run_agent.py:535-617]

### 2. ToolRegistry（工具注册中心）

`ToolRegistry` 是一个单例注册中心，集中管理所有工具的 schema、handler 和元数据。每个工具文件在模块导入时通过 `registry.register()` 自注册，无需手动维护工具清单。

关键设计：
- `ToolEntry` 封装工具名、所属 toolset、schema、handler（同步或异步）、可用性检查函数 `check_fn`、所需环境变量等
- `discover_builtin_tools()` 通过 AST 扫描 `tools/` 目录下所有 `.py` 文件，自动发现包含顶层 `registry.register()` 调用的模块
- `dispatch()` 执行工具调用：异步 handler 自动通过持久化事件循环桥接，所有异常统一捕获为 JSON 错误响应
- 线程安全：所有写操作由 `threading.RLock` 保护，读操作返回快照

^[tools/registry.py:100-320]

### 3. Toolset（工具集组合器）

`toolsets.py` 定义了工具集系统，将工具按场景分组。工具集支持组合（`includes` 引用其他工具集），形成可分层的工具能力图谱。

核心设计：
- `_HERMES_CORE_TOOLS`：共享工具清单，涵盖 Web、Terminal、文件、浏览器、技能、TTS、规划、代码执行、委托、cronjob、Home Assistant 等 60+ 工具
- `TOOLSETS` 字典：定义基础工具集（web、terminal、vision 等）、组合工具集（research、development、full_stack 等）和场景工具集（safe、hermes-telegram 等）
- `resolve_toolset()`：递归解析所有 includes，展平为工具名列表

^[toolsets.py:31-63]

### 4. GatewayRunner（消息网关控制器）

`GatewayRunner` 管理所有消息平台适配器的生命周期，将来自不同平台（Telegram、Discord、Slack、WhatsApp、Signal、飞书、钉钉、企业微信、Matrix 等）的消息路由到 `AIAgent`。

关键职责：
- 初始化所有已配置的平台适配器，启动适配器的监听循环
- 消息处理管线：用户鉴权 → 命令拦截（/new、/reset、/stop 等）→ 运行中代理检查/中断 → 获取或创建会话 → 构建上下文 → 运行 AIAgent → 返回响应
- 并发控制：每个会话键（`session_key`）只允许一个活跃代理，使用 sentinel 值防止竞态
- 支持 running agent 的中断（`interrupt()`）和超时驱逐

^[gateway/run.py:538-599]

### 5. Platform Adapter（平台适配器抽象）

`BasePlatformAdapter` 定义了消息平台适配器的统一接口。每个平台实现自己的适配器，将平台特定的事件转换为统一的 `MessageEvent` 格式。

平台适配器列表：`telegram.py`、`discord.py`、`slack.py`、`whatsapp.py`、`signal.py`、`homeassistant.py`、`dingtalk.py`、`feishu.py`、`wecom.py`、`matrix.py`、`email.py`、`sms.py`、`qqbot.py`、`bluebubbles.py`、`mattermost.py`、`webhook.py`、`api_server.py`

平台适配器统一处理：消息收发、媒体附件（图片/音频/文件）、命令解析、忙时输入排队

^[gateway/platforms/base.py:1-60（推断）]

### 6. SessionDB（会话持久化存储）

`hermes_state.py` 提供基于 SQLite 的会话持久化存储，使用 WAL 模式支持并发读和单一写（gateway 多平台场景）。

核心设计：
- `sessions` 表：存储会话元数据（模型、source、user_id、耗时、token 统计、成本估算）
- `messages` 表：存储完整消息历史（role、content、tool_calls、tool_call_id、token_count）
- FTS5 全文索引：支持跨会话消息搜索
- `parent_session_id` 链：压缩触发的会话拆分，子会话通过外键链接到父会话

^[hermes_state.py:1-80]

### 7. MemoryProvider（可插拔记忆后端）

`MemoryProvider` 是一个抽象基类，定义记忆后端的生命周期接口。内置记忆（基于 `MEMORY.md`/`USER.md` 文件）始终激活；外部提供商（Honcho 等）通过 `memory.provider` 配置激活，最多一个。

生命周期：`initialize()` → `prefetch()` → `sync_turn()` → `on_session_end()` → `shutdown()`

`MemoryManager` 统一编排所有已注册的记忆提供商，在系统提示构建、turn 前预取、turn 后同步三个阶段调用

^[agent/memory_provider.py:1-31, agent/memory_manager.py:1-27]

### 8. ContextCompressor（上下文压缩器）

自动上下文窗口压缩器，使用辅助 LLM（廉价/快速模型）总结对话的中间部分，保护头部（系统提示 + 早期上下文）和尾部（最近对话）。

关键设计：
- 结构化摘要模板：包含已解决/待解决问题追踪
- 摘要前缀明确告知模型摘要仅供参考，不应作为活跃指令
- 支持迭代式摘要更新（多次压缩保留信息）
- Token 预算保护尾部而非固定消息数
- 工具输出裁剪后再送入摘要 LLM（廉价预处理）

^[agent/context_compressor.py:1-60]

### 9. IterationBudget（迭代预算）

线程安全的迭代计数器，限制每个代理实例的 LLM 调用次数。父代理默认 90 次，子代理默认 50 次（可配）。`execute_code` 的迭代可退还。父代理和子代理拥有独立预算，总调用次数可超父代理上限。

^[run_agent.py:170-212]

---

## 分层架构

hermes-agent 采用分层架构，自底向上依次为：

```
┌──────────────────────────────────────────────────────────────┐
│  接入层 (Entry Layer)                                         │
│  hermes CLI  │  Gateway  │  ACP Adapter  │  Batch Runner    │
│  (hermes_cli/) (gateway/)  (acp_adapter/)  (batch_runner.py) │
├──────────────────────────────────────────────────────────────┤
│  编排层 (Orchestration Layer)                                 │
│  AIAgent (run_agent.py)                                      │
│  - 对话循环、API 调用管理、工具执行分发、上下文管理          │
├──────────────────────────────────────────────────────────────┤
│  适配层 (Adapter Layer)                                       │
│  anthropic_adapter.py  │  bedrock_adapter.py                 │
│  (provider-specific API translation)                         │
├──────────────────────────────────────────────────────────────┤
│  工具层 (Tool Layer)                                          │
│  tools/registry.py → tools/*.py (60+ self-registering tools) │
├──────────────────────────────────────────────────────────────┤
│  平台层 (Platform Layer)                                      │
│  gateway/platforms/*.py (20+ messaging platform adapters)     │
├──────────────────────────────────────────────────────────────┤
│  基础设施层 (Infrastructure Layer)                            │
│  SessionDB │ Cron Scheduler │ Skills │ Memory │ Plugins      │
│  (hermes_state.py) (cron/) (skills/) (agent/memory_*.py)    │
└──────────────────────────────────────────────────────────────┘
```

### 各层职责

**接入层**：用户与代理交互的入口点。CLI 提供完整的 TUI（prompt_toolkit），Gateway 将代理暴露为消息平台机器人，ACP Adapter 提供编辑器集成（VS Code / Zed / JetBrains），Batch Runner 支持批量轨迹生成。

^[hermes_cli/main.py:1-44, gateway/run.py:1-14, acp_adapter/entry.py:1-60, batch_runner.py:1-21]

**编排层**：`AIAgent` 是唯一的核心编排器。Gateway、CLI、Batch Runner 和 RL 环境都通过创建 `AIAgent` 实例来使用代理能力。这保证了所有入口点的对话行为一致性。

^[run_agent.py:535-617]

**适配层**：将内部的 OpenAI 风格消息格式翻译为特定提供商的 API 格式。Anthropic 适配器处理 Messages API（含 `anthropic` SDK 调用、OAuth 认证），Bedrock 适配器处理 AWS Bedrock Converse API。

^[agent/anthropic_adapter.py:1-50]

**工具层**：每个工具是独立的 Python 模块，导入时自注册到 `ToolRegistry`。工具发现通过 AST 扫描自动完成，无需手动枚举。工具按 toolset 分组，在 `model_tools.py` 中统一对外暴露 API。

^[model_tools.py:1-30, tools/registry.py:56-73]

**平台层**：每个消息平台有独立的适配器实现，遵循 `BasePlatformAdapter` 接口。平台层将平台特定事件规范化后，调用 GatewayRunner 的统一消息处理管线。

^[gateway/platforms/base.py（推断）]

**基础设施层**：提供跨层共享的服务——会话持久化（SQLite + FTS5）、定时任务调度（cron scheduler）、技能系统、记忆系统、插件钩子系统。

^[hermes_state.py:17-80, cron/scheduler.py:1-40]

---

## 数据流

### 整体数据流方向

hermes-agent 采用 **单向请求-响应 + 事件驱动** 的混合数据流模型：

```
用户输入
  │
  ▼
平台适配器 (Normalize to MessageEvent)
  │
  ▼
GatewayRunner._handle_message()
  ├── 鉴权检查
  ├── 命令拦截 (/new, /reset, /stop)
  ├── 运行中代理检查/中断/排队
  └── 创建/恢复会话上下文
       │
       ▼
AIAgent.run_conversation()
  │
  ├── 1. 构建系统提示 (cached per session)
  │      ├── prompt_builder.py (identity, platform hints)
  │      ├── MemoryManager.prefetch_all() (记忆预取)
  │      ├── Skills index injection
  │      └── Context files injection (SOUL.md, AGENTS.md, .cursorrules)
  │
  ├── 2. 预检压缩 (如果历史超过阈值)
  │
  ├── 3. 主循环 (while api_call_count < max_iterations):
  │      │
  │      ├── a. 构建 API 消息
  │      │     ├── 注入记忆上下文到当前 user message
  │      │     ├── 注入插件 pre_llm_call 上下文
  │      │     ├── 剥离内部字段 (reasoning, finish_reason)
  │      │     └── 应用 Anthropic prompt caching 标记
  │      │
  │      ├── b. 调用 LLM
  │      │     ├── _interruptible_streaming_api_call() (优先流式)
  │      │     └── _interruptible_api_call() (fallback)
  │      │
  │      ├── c. 处理响应
  │      │     ├── 文本响应 → 累加到最终响应
  │      │     └── 工具调用 → registry.dispatch() 执行
  │      │           ├── 同步 handler: 直接调用
  │      │           ├── 异步 handler: _run_async() 桥接
  │      │           └── 并行执行: ThreadPoolExecutor (最大 8 线程)
  │      │
  │      └── d. 将工具结果追加到 messages，继续循环
  │
  └── 4. 后处理
        ├── 会话持久化到 SessionDB
        ├── MemoryManager.sync_all() (记忆同步)
        ├── 技能 nudge 检查
        └── 返回最终响应
             │
             ▼
GatewayRunner → DeliveryRouter → 平台适配器 → 用户
```

^[run_agent.py:8130-8500, gateway/run.py:2680-2900]

### 数据流关键特征

**1. API-call-time 注入（非持久化）**：记忆上下文、插件上下文通过 API-call-time only 模式注入到当前 user message 副本中。`messages` 列表中的原始消息永远不会被修改，确保注入内容不会泄漏到会话持久化或轨迹存储中。

^[run_agent.py:8557-8577]

**2. 系统提示缓存**：系统提示在会话首个 turn 构建一次后缓存（`_cached_system_prompt`）。后续 turn 从 SessionDB 加载存储的提示以保持 Anthropic prefix cache 的命中率。仅在上下文压缩事件后重建。

^[run_agent.py:8286-8334]

**3. 回调管道**：`AIAgent` 暴露丰富的回调接口（`stream_delta_callback`、`tool_progress_callback`、`clarify_callback`、`step_callback`、`thinking_callback`、`reasoning_callback` 等），平台层通过回调接入代理内部状态，实现解耦的 UI 更新。

^[run_agent.py:559-617]

**4. 委托的数据隔离**：子代理获得全新的对话（无父代理历史）、独立 task_id（独立终端会话）、受限工具集（移除 `delegate_task`、`clarify`、`memory` 等）。父代理上下文仅看到委托调用和摘要结果，看不到子代理的中间工具调用或推理过程。

^[tools/delegate_tool.py:1-38]

---

## 关注点分离

### 1. 提供商适配 vs 核心逻辑

LLM 提供商的 API 差异完全隔离在适配器层：

- `agent/anthropic_adapter.py`：处理 Anthropic Messages API 的消息格式转换、thinking token 预算、OAuth 认证
- `agent/bedrock_adapter.py`：处理 AWS Bedrock Converse API
- OpenAI 兼容协议直接通过 `openai` SDK 在 `run_agent.py` 中处理

`AIAgent` 核心逻辑通过 `api_mode` 字段分发，适配层对上层透明。

^[agent/anthropic_adapter.py:1-12, run_agent.py:690-709]

### 2. 平台适配 vs 代理逻辑

消息平台差异隔离在 `gateway/platforms/` 中，每个平台实现 `BasePlatformAdapter`。平台层负责消息格式标准化、媒体预处理（图片/音频/文档）、命令解析，但不涉及代理决策逻辑。

GatewayRunner 通过 `_handle_message()` 统一消息处理管线，通过 `_session_key_for_source()` 生成稳定会话键。

^[gateway/run.py:2680-2900]

### 3. 工具实现 vs 工具编排

每个工具是独立的 Python 模块（`tools/*.py`），通过 `registry.register()` 自注册 schema 和 handler。工具编排逻辑（`model_tools.py`）仅负责触发工具发现和提供查询 API（`get_tool_definitions()`、`handle_function_call()`），不包含工具实现代码。

^[model_tools.py:1-30, tools/registry.py:176-228]

### 4. 记忆后端 vs 代理核心

记忆通过 `MemoryProvider` 抽象基类与代理核心解耦。内置文件记忆（`MEMORY.md`）和外部的 Honcho 等提供商通过统一接口接入。`MemoryManager` 强制"最多一个外部提供商"的约束，防止工具 schema 膨胀。

^[agent/memory_provider.py:1-31, agent/memory_manager.py:1-27]

### 5. 会话持久化 vs 代理运行时

`SessionDB`（SQLite）负责所有持久化操作，`AIAgent` 仅在 turn 结束时触发保存。会话 DB 独立于代理生命周期：gateway 创建新 `AIAgent` 实例处理每条消息，但会话状态从 DB 恢复。这支持跨进程、跨重启的会话连续性。

^[hermes_state.py:1-80]

### 6. UI 渲染 vs 代理逻辑

CLI 的 TUI 渲染（prompt_toolkit、Rich）集中在 `hermes_cli/` 和 `cli.py` 中。代理核心通过回调向 UI 层推送状态更新（流式 token、工具进度、思考动画），但代理本身不包含任何 UI 渲染代码。

`_SafeWriter` 包装 stdout/stderr 防止断管错误导致代理崩溃，体现了防御性边界的明确划分。

^[run_agent.py:113-167, cli.py:1-50]

### 7. 系统提示组装 vs 代理运行时

系统提示的各个组件（身份、平台提示、记忆指导、技能索引、上下文文件、环境提示）通过 `agent/prompt_builder.py` 中的无状态函数分别构建，`AIAgent._build_system_prompt()` 负责组装。每个组件可独立修改而不影响其他部分。

^[agent/prompt_builder.py:1-6]

---

## 关联（与其他仓库的架构对比）

### 与 OpenClaw 的关系

AGENTS.md 中提到 `hermes claw migrate` 命令支持从 OpenClaw 迁移配置和数据。hermes-agent 在架构上继承了 OpenClaw 的多平台网关模式，但增加了自改进闭环（技能创建、记忆 nudge、会话搜索）和更丰富的工具系统。

^[AGENTS.md:63-64]

### 与 Atropos / Tinker 的关系

`environments/` 目录包含 RL 训练环境（`atropos` + `tinker`），使 hermes-agent 可作为 RL 训练的 agent harness。`batch_runner.py` 和 `trajectory_compressor.py` 支持批量轨迹生成和压缩，用于训练下一代工具调用模型。这是独立于对话代理主循环的训练数据管线。

^[pyproject.toml:82-88, environments/agent_loop.py（推断）]

### 与 ACP（Agent Client Protocol）的关系

`acp_adapter/` 实现了 ACP 协议服务器，使 hermes-agent 可作为编辑器（VS Code / Zed / JetBrains）的内联 AI 代理运行。ACP 适配器将 hermes-agent 的工具调用能力暴露给编辑器的 ACP 客户端，扩展了代理的使用场景。

^[acp_adapter/entry.py:1-60, pyproject.toml:64]
