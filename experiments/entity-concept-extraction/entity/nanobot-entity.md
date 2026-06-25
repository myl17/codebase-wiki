# nanobot — 系统表征

## 这个系统是什么
nanobot 是一个用 Python 编写的超轻量个人 AI Agent 框架（v0.1.5，4,583 行核心代码），受 OpenClaw 启发并以 99% 更少代码为目标。通过 20+ IM 平台（Telegram、Slack、Discord、微信、飞书、钉钉、QQ 等）与用户交互，支持 20+ LLM provider，提供完整的 agent 功能：tool calling、子 agent、记忆系统、定时任务、心跳唤醒、MCP 集成。

## 核心子系统

| 子系统 | 文件 | 一句话边界 |
|--------|------|-----------|
| **AgentLoop** | `agent/loop.py` | 中央编排器，单体 hub——在单一构造函数中组装所有子系统，运行时从 bus 取消息、调度 AgentRunner、回写出站 |
| **AgentRunner** | `agent/runner.py` | 共享执行引擎——纯 tool-calling 循环，不依赖任何产品层模块（channel/session/cron），同时服务于主 agent、子 agent、Dream 记忆处理 |
| **MessageBus** | `bus/queue.py` | `asyncio.Queue` 封装——Channel 和 AgentLoop 之间的唯一通信通道，子 agent 结果和 Cron 触发也通过同一入站队列注入 |
| **ContextBuilder** | `agent/context.py` | 系统 prompt 组装器——六层内容依次拼接（identity → bootstrap → memory → always skills → skills summary → recent history），纯数据到文本的转换，不调用 LLM |
| **ToolRegistry** | `agent/tools/registry.py` | 工具注册中心——`dict[name, Tool]` 薄封装，显式 register() 注册，不做 AST/装饰器自动发现 |
| **LLMProvider** | `providers/base.py` + `providers/registry.py` | LLM 供应商抽象层——统一 chat/chat_stream 接口，基类内建三级重试逻辑（429 分类、图片降级）、ProviderSpec 数据表驱动注册 |
| **Memory System** | `agent/memory.py` | 三层记忆栈——MemoryStore（文件 I/O）+ Consolidator（异步压缩）+ Dream（两阶段记忆处理：LLM 分析 → AgentRunner 执行写入） |
| **Channel System** | `channels/registry.py` + `channels/*.py` | IM 平台插件架构——内置 channel pkgutil 自发现 + 外部 entry_points 插件，BaseChannel ABC 统一接口 |
| **AgentHook** | `agent/hook.py` | 生命周期钩子系统——六个拦截点，CompositeHook 串联为管道（finalize_content 纯函数管线，其余扇出） |
| **Subagent** | `agent/subagent.py` | 隔离代理生成器——共享 AgentRunner 引擎但独立 ToolRegistry（无 message/spawn/cron 工具），结果通过 bus 注入主 agent 入站队列 |
| **Skills** | `agent/skills.py` | Markdown 知识注入——always skills 全文注入 system prompt + 渐进式按需加载，支持 requires 依赖检查 |
| **SessionManager** | `session/manager.py` | 会话持久化——JSONL 文件存储，惰性加载，get_or_create() 唯一天地入口，裁剪保证 tool-result 边界完整性 |
| **Cron + Heartbeat** | `cron/service.py` + `heartbeat/service.py` | 定时调度——三种调度类型（at/every/cron）+ 单工具 LLM 心跳唤醒，CronStore FileLock 防重复 |
| **Security** | `security/network.py` | SSRF 防护——10 个 CIDR 私有网络拦截 + 白名单配置 |
| **API Server** | `api/server.py` | OpenAI 兼容 REST API——`/v1/chat/completions` + `/v1/models`，aiohttp 实现 |

## 关键机制

1. **AgentRunner 产品层无关**：AgentRunner 不知道自己在为主 agent、子 agent 还是 Dream 记忆处理服务——不知道 channel 类型、不知道会话状态。代价是牺牲上下文感知能力，换取引擎的零修改复用。这是 nanobot 最核心的架构取舍。

2. **四层透明上下文治理**：AgentRunner 在每次 LLM 调用前自动执行 Backfill（孤立 tool result 修复）→ Microcompact（旧 tool result 压缩为摘要）→ Tool Result Budget（单结果截断）→ Snip History（跨轮次裁剪）。四层全部在 AgentRunner 内部完成，对 LLM 完全透明——LLM 不知道上下文被裁剪过。

3. **子 agent = IM 消息**：子 agent 完成后通过 `bus.publish_inbound()` 将结果注入主 agent 的入站队列，与 Telegram/Discord 等 IM 消息走完全相同的处理路径。Cron 触发同理。这意味着 AgentLoop 不需要区分「这条消息来自哪个源头」。

4. **显式即确定性**：ToolRegistry 不做 AST 扫描、Provider 用数据表而非代码注册、Channel 用 pkgutil 自发现但内置优先——所有扩展点都不依赖隐式约定或魔法发现。

## 明确不做什么

- **不做依赖注入容器**：所有子系统在 AgentLoop.__init__() 中集中实例化和连线，没有 IoC 容器、没有 provider factory、没有延迟加载
- **不做向量检索或嵌入式数据库**：MemoryStore 是纯文件 I/O（读写 MEMORY.md、history.jsonl），无向量数据库、无 embedding
- **不做图数据库或知识图谱**：不维护结构化知识表示
- **不做自动工具发现**：ToolRegistry 不做 AST 扫描、不做装饰器收集、不做模块自省——每个工具必须在 `_register_default_tools()` 中显式点名
- **不做多进程并发**：核心运行时设计为单进程 asyncio 模型，Cron 用 FileLock 防止多进程重复但不主动管理多实例
