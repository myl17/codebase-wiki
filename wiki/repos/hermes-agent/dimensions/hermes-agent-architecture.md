---
repo: hermes-agent
dimension: architecture
dimensions_version: v1.0
generated: 2026-06-09
---

# Hermes Agent — Architecture

## 核心抽象

Hermes Agent 的架构围绕七个核心抽象构建，形成清晰的分层架构：

| 抽象 | 所在文件 | 职责 |
|---|---|---|
| **AIAgent** | `run_agent.py:535` (11510行) | 中央编排器 — 对话循环、工具调用、模型 API 交互、fallback 路由、子 agent 委派 |
| **GatewayRunner** | `gateway/run.py:538` | 多平台消息网关控制器 — 管理所有平台适配器的生命周期，路由消息进出 agent |
| **BasePlatformAdapter** | `gateway/platforms/base.py:813` | 20+ 消息平台的抽象基类 — 统一消息收发、会话管理、媒体处理的接口 |
| **ContextEngine** | `agent/context_engine.py:32` | 可插拔上下文压缩策略 — 决定何时以及如何压缩对话上下文 |
| **MemoryManager** | `agent/memory_manager.py` | 记忆提供者编排器 — 内置记忆 + 最多一个外部插件提供者（Honcho/Mem0/Supermemory 等 7 种） |
| **ToolRegistry** | `tools/registry.py:100` | 单例模式工具注册中心 — 收集工具 schema + handler，支持 MCP 动态刷新 |
| **IterationBudget** | `run_agent.py:170` | 线程安全的迭代计数器 — 父子 agent 独立预算，`execute_code` 调用可退款 |

## 分层架构

数据流方向：用户界面层 → 编排层 → 安全层 → 插件层 → 工具层 → 基础设施层（单向为主，部分双向回调）：

```
┌──────────────────────────────────────────────────────────┐
│  用户界面层                                                │
│  cli.py (TUI, 10032行) │ gateway/platforms/ (20+ 平台)    │
│  prompt_toolkit │ Telegram Discord Slack WhatsApp ...    │
├──────────────────────────────────────────────────────────┤
│  编排层                                                    │
│  AIAgent (run_agent.py) │ GatewayRunner (gateway/run.py) │
│  对话循环 · 工具调用 · fallback · 子agent委派 · Cron调度   │
├──────────────────────────────────────────────────────────┤
│  安全层                                                    │
│  approval.py │ skills_guard.py │ tirith_security         │
│  三层审批 (YOLO → Smart/Manual → Block) + Skill安全扫描   │
├──────────────────────────────────────────────────────────┤
│  插件层                                                    │
│  MemoryManager │ ContextEngine │ Event Hooks             │
│  7 memory providers (Honcho/Mem0/Supermemory/...) │ Compressor/LCM │
├──────────────────────────────────────────────────────────┤
│  工具层                                                    │
│  ToolRegistry → terminal · browser · web · file · ...     │
│  process_registry (后台进程跟踪)                            │
├──────────────────────────────────────────────────────────┤
│  基础设施层                                                │
│  终端后端 (local/docker/ssh/daytona/singularity/modal)     │
│  会话存储 (SQLite FTS5) │ ACP 适配器 │ Cron 调度器         │
├──────────────────────────────────────────────────────────┤
│  可观测性层                                                │
│  hermes_logging (3 日志 + 密文脱敏 + session context)     │
│  gateway/status (PID + runtime state)                     │
│  usage_pricing (token 计数 + 成本估算)                     │
│  agent/insights (会话搜索 + 模式分析)                       │
└──────────────────────────────────────────────────────────┘
```

## 数据流

### CLI 路径 ^[hermes_cli/main.py:676-783] ^[cli.py:1-10032]

1. 用户输入 → `hermes_cli/main.py:cmd_chat()` 解析参数
2. → `cli.py:main()` 启动 prompt_toolkit TUI
3. → `AIAgent.run_conversation()` 执行 tool-calling 循环 ^[run_agent.py:8130-8189]
4. → OpenAI-compatible API 调用（支持 20+ provider）
5. → 工具调用通过 `model_tools.handle_function_call()` → `ToolRegistry.dispatch()` 执行
6. → 响应经 TUI 渲染返回用户，底部显示 token 使用量和成本摘要

### Gateway 路径 ^[gateway/run.py:9537]

1. 消息从平台到达 → `BasePlatformAdapter` 子类接收
2. → `GatewayRunner` 查找/创建 session，注入 memory context
3. → `AIAgent.run_conversation()` 执行
4. → 响应通过 `DeliveryRouter` 路由回对应平台 ^[gateway/delivery.py]
5. → Agent 实例按 session 缓存以保持Prompt Caching ^[gateway/run.py:604-611]

## 自学习闭环

Hermes 最核心的架构特性是内建于 system prompt 的自学习闭环——三段驱动指令推动 LLM 在三个时间尺度上自主改进自身：

### 指令-工具矩阵 ^[agent/prompt_builder.py:145-171]

| 驱动指令 | 触发时机 | 调用工具 | 产出的持久化 artifact |
|---|---|---|---|
| **MEMORY_GUIDANCE** | 用户纠正/分享偏好/发现环境事实 | `memory` | `~/.hermes/memories/MEMORY.md`, `USER.md` |
| **SESSION_SEARCH_GUIDANCE** | 用户提及过去对话/需要跨会话上下文 | `session_search` | SQLite FTS5 搜索结果 → 即时 LLM 摘要 |
| **SKILLS_GUIDANCE** | 完成复杂任务(5+ tool calls)/修复棘手错误/发现 skill 过时 | `skill_manage` | `~/.hermes/skills/<name>/SKILL.md` |

### 三层时间尺度的自我改进

```
实时层 (per-turn):     memory 工具在每轮对话后持久化事实
                      → 同一会话后续轮次立即生效

跨会话层 (cross-session): session_search 搜索 FTS5 索引的历史会话
                          → 用户不需要重复之前说过的信息

代际层 (generational):  skill_manage 创建/改进可复用的操作步骤
                       → Agent 越用越能干，积累专属技能库
```

### 闭环数据流

```
Agent 完成复杂任务
    │
    ├─→ SKILLS_GUIDANCE 驱动 → skill_manage 创建技能 → ~/.hermes/skills/
    │                                                      │
    ├─→ MEMORY_GUIDANCE 驱动 → memory 写入事实 → MEMORY.md/USER.md
    │                                                      │
    └─→ 下次会话 system prompt 组装:                         │
         ├── build_skills_system_prompt() 注入所有 SKILL.md  ^[agent/prompt_builder.py:449-453]
         ├── build_memory_context_block() 注入记忆条目        ^[agent/memory_manager.py]
         └── 下一次复杂任务 → 更高效的完成 → 继续改进 → 循环
```

### 与 OpenClaw 的关键差异

OpenClaw 有 skills（markdown 文件注入 system prompt）和 memory（向量搜索 + sqlite-vec），但**没有系统 prompt 中那三条自驱动的指令**。因此 OpenClaw 的 agent 不会**主动**去创建、改进、回忆——这些行为需要人类触发。Hermes 通过这三段 prompt 让 LLM 变成了一个自驱动的学习者。

## 权限检查与安全护栏

### 三层审批架构 ^[tools/approval.py:586-922]

| 层级 | 组件 | 说明 |
|---|---|---|
| **Layer 0 — 快速路径** | YOLO 模式 / 容器环境 / `approvals.mode=off` | 全部放行，不检查 |
| **Layer 1 — Smart** | `_smart_approve()` ^[tools/approval.py:534-583] | Aux LLM 风险评估 → auto-approve/deny/escalate |
| **Layer 2 — Manual** | tirith + `DANGEROUS_PATTERNS` | 合并发现 → 用户交互式审批 [o/s/a/d] |

**DANGEROUS_PATTERNS**: 25+ 正则模式覆盖 rm/chmod/mkfs/kill/systemctl/curl\|sh/git reset --hard/gateway self-protection 等 ^[tools/approval.py:75-138]

**审批级别**:
- `once` — 仅本次有效
- `session` — 会话级允许 ^[tools/approval.py:299-303]
- `always` — 写入 `config.yaml` 的 `command_allowlist`，跨会话持久化 ^[tools/approval.py:376-402]

**Gateway 阻塞审批**: FIFO 队列 + `threading.Event`，agent 线程阻塞等待用户 `/approve` / `/deny`，并行子 agent 并发等待各自审批 ^[tools/approval.py:219-284]

### Skill 安全扫描 ^[tools/skills_guard.py:595-639]

100+ 威胁模式覆盖 12 类别：exfiltration / injection / destructive / persistence / network / obfuscation / execution / traversal / mining / supply_chain / privilege_escalation / credential_exposure ^[tools/skills_guard.py:82-484]

信任策略 ^[tools/skills_guard.py:39-48]:

| 信任级别 | Safe | Caution | Dangerous |
|---|---|---|---|
| builtin | allow | allow | allow |
| trusted (openai/anthropics) | allow | allow | block |
| community | allow | block | block |
| agent-created | allow | allow | ask |

### 日志密文脱敏 ^[agent/redact.py:1-60]

40+ 种 API key 前缀模式（OpenAI/Anthropic/GitHub/Slack/Google/AWS/Stripe 等）的日志自动脱敏，密钥永不写入磁盘。

## 可观测性模块

### 日志系统 ^[hermes_logging.py:1-391]

| 日志文件 | 级别 | 用途 |
|---|---|---|
| `agent.log` | INFO+ | 所有 agent/tool/session 活动（主日志） |
| `errors.log` | WARNING+ | 错误和警告（快速分诊） |
| `gateway.log` | INFO+, `gateway.*` 组件 | 网关专用 |

关键特性:
- **RotatingFileHandler**: 可配置 max_size_mb（默认 5MB）+ backup_count（默认 3）
- **Session Context**: `[session_id]` 标签注入 LogRecord → 支持 `hermes logs --session <id>` 过滤 ^[hermes_logging.py:72-119]
- **Component Filter**: 按组件前缀路由日志 (gateway/agent/tools/cli/cron) ^[hermes_logging.py:126-149]
- **Managed Mode**: NixOS 环境自动 chmod 0660 保证多用户共享日志 ^[hermes_logging.py:299-329]
- **幂等**: 多次调用 `setup_logging()` 安全，除非 `force=True`

### 运行时状态 ^[gateway/status.py:1-60]

- PID 文件: `~/.hermes/gateway.pid` → 检测网关守护进程是否运行
- Runtime 状态文件: `~/.hermes/gateway_state.json` → 平台连接状态持久化
- Token-scoped 锁目录: `XDG_STATE_HOME/hermes/gateway-locks/`

### 进程注册表 ^[tools/process_registry.py:1-60]

管理所有后台进程（terminal background=true）:
- 200KB 滚动输出缓冲区
- 已完成进程保留 30min
- 最大并发跟踪 64 个进程（LRU 淘汰）
- JSON checkpoint 文件 → 网关崩溃恢复

### 使用量追踪 ^[agent/usage_pricing.py]

- `estimate_usage_cost()` — 按模型定价估算每次会话成本
- `normalize_usage()` — 跨 provider 标准化 token 使用量

### 诊断工具

- `hermes doctor` — 检查配置和依赖完整性 ^[hermes_cli/main.py:61]
- `/insights [--days N]` — 会话搜索和历史模式识别 ^[agent/insights.py]

## 关注点分离

1. **配置层**: `config.yaml` → 环境变量桥接 → 模块级读取。CLI 和 Gateway 在启动时独立加载，避免循环依赖 ^[gateway/run.py:88-218]
2. **会话层**: `gateway/session.py` 管理会话持久化（SQLite + FTS5 全文搜索），PII 哈希化，重置策略 ^[gateway/session.py:1-60]
3. **安全边界**: `_SafeWriter` 包装 stdout/stderr 防止管道破裂导致 agent 崩溃 ^[run_agent.py:113-167]；profile override 必须在所有模块导入之前应用 ^[hermes_cli/main.py:83-138]
4. **资源隔离**: 每个 agent 实例有独立的 `task_id`，终端 VM 按 task_id 隔离 ^[run_agent.py:8130]

## 关键设计模式

- **自动发现**: 工具通过 AST 扫描 `registry.register()` 调用自动发现 ^[tools/registry.py:28-73]；hooks 通过目录扫描加载 ^[gateway/hooks.py:34-80]；skills 通过 `sync_skills()` 双同步 ^[hermes_cli/main.py:743-747]
- **适配器模式**: 20+ 平台通过 `BasePlatformAdapter` 统一接口 ^[gateway/platforms/base.py:813-893]
- **策略模式**: `ContextEngine` 用于压缩策略 ^[agent/context_engine.py:32]；`MemoryProvider` 用于记忆后端；三种审批模式 (manual/smart/off) ^[tools/approval.py:520-523]
- **事件/Observer**: Hook 系统支持 `gateway:startup`, `session:start`, `agent:step`, `agent:end` 等生命周期事件 ^[gateway/hooks.py:9-19]
- **单例 + 线程安全**: `ToolRegistry` 全局唯一，RLock 保护，支持 MCP 动态刷新 ^[tools/registry.py:100-115]
- **Agent 缓存**: GatewayRunner 跨消息复用 AIAgent 实例以保持 prompt caching ^[gateway/run.py:604-611]

## 关键源码引用

| 文件 | 行号 | 内容 |
|---|---|---|
| `run_agent.py` | :535 | AIAgent 类定义 |
| `run_agent.py` | :8130-8189 | run_conversation 入口 |
| `run_agent.py` | :170-199 | IterationBudget 线程安全迭代器 |
| `run_agent.py` | :113-167 | _SafeWriter 管道保护 |
| `gateway/run.py` | :538-617 | GatewayRunner 类 |
| `gateway/run.py` | :604-611 | Agent 缓存机制 |
| `gateway/platforms/base.py` | :813-893 | BasePlatformAdapter 抽象基类 |
| `gateway/hooks.py` | :1-80 | 事件 Hook 系统 |
| `gateway/session.py` | :1-60 | 会话管理 |
| `gateway/status.py` | :1-60 | 运行时状态 |
| `agent/context_engine.py` | :32-60 | ContextEngine 抽象基类 |
| `agent/memory_manager.py` | :1-60 | MemoryManager 编排器 |
| `agent/redact.py` | :1-60 | 日志密文脱敏 |
| `agent/usage_pricing.py` | — | Token 使用量 + 成本估算 |
| `agent/insights.py` | — | 会话搜索与模式分析 |
| `tools/registry.py` | :28-73 | 工具自动发现 |
| `tools/registry.py` | :100-159 | ToolRegistry 单例注册中心 |
| `tools/approval.py` | :75-138 | DANGEROUS_PATTERNS（25+ 正则） |
| `tools/approval.py` | :586-922 | check_all_command_guards 入口 |
| `tools/approval.py` | :534-583 | Smart Approval (aux LLM) |
| `tools/approval.py` | :219-284 | Gateway 阻塞审批队列 |
| `tools/skills_guard.py` | :82-484 | 100+ 威胁扫描模式 |
| `tools/skills_guard.py` | :595-639 | scan_skill 入口 |
| `tools/process_registry.py` | :1-60 | 后台进程注册表 |
| `hermes_logging.py` | :1-391 | 日志系统 |
| `hermes_cli/main.py` | :83-138 | Profile override 预解析 |
| `hermes_cli/main.py` | :676-783 | cmd_chat CLI 入口 |
| `model_tools.py` | :1-80 | 工具编排薄层 |
| `pyproject.toml` | :1-80 | 依赖声明与可选模块化 |
| `environments/__init__.py` | :1-36 | RL 环境分层集成 |
| `cron/__init__.py` | :1-42 | Cron 调度器模块 |

## 关联

- [[openclaw/dimensions/openclaw-architecture]]

<!-- generated-dimension-links -->
**本维度提取的节点：**

- [[hermes-agent/nodes/components/hermes-agent-ai-agent]] — Component
- [[hermes-agent/nodes/components/hermes-agent-approval-system]] — Component
- [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]] — DesignDecision
- [[hermes-agent/nodes/extension-points/hermes-agent-event-hooks]] — ExtensionPoint
- [[hermes-agent/nodes/design-decisions/hermes-agent-layered-approval-decision]] — DesignDecision
- [[hermes-agent/nodes/design-decisions/hermes-agent-self-learning-loop-decision]] — DesignDecision
- [[hermes-agent/nodes/components/hermes-agent-skills-guard]] — Component
- [[hermes-agent/nodes/components/hermes-agent-tool-registry]] — Component
<!-- /generated-dimension-links -->
