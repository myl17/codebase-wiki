# Execution Engine Decoupling

## 问题陈述

Agent harness 的核心价值是执行引擎：接收消息、调用 LLM、执行工具、返回结果。但这个引擎要服务于不同的使用场景——CLI 交互、Telegram bot、cron 定时任务、HTTP API——每个场景有不同的 channel 概念、session 生命周期和产品层逻辑。**如何让执行引擎不耦合到特定的产品层，使其在不同使用场景间复用？** 三个仓库走了三条不同的路。

## 实例

### nanobot: AgentRunner 纯数据接口

**所属仓库**: [[nanobot|nanobot]]
**维度**: Architecture
**解耦方式**: 执行引擎与产品层的完全分离

**机制**

nanobot 将执行引擎抽象为 `AgentRunner`（`nanobot/agent/runner.py:83-89`），它的构造函数只接受一个 `LLMProvider`——没有 channel、没有 bus、没有 session_manager、没有 cron_service：

```python
class AgentRunner:
    """Run a tool-capable LLM loop without product-layer concerns."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def run(self, spec: AgentRunSpec) -> AgentRunResult:
```

`AgentRunSpec`（`runner.py:44-68`）是一个纯数据 dataclass，包含 `initial_messages`、`tools: ToolRegistry`、`model`、`max_iterations`、`max_tool_result_chars` 等执行级参数。`session_key` 字段仅为 `str | None`，用于日志标注和 checkpoint 回调，不持有任何 Session 对象引用。`AgentRunResult`（`runner.py:70-80`）同样是纯数据——`final_content`、`messages`、`tools_used`、`usage`、`stop_reason`。整个执行循环（`runner.py:89-320`）只操作 messages 列表和 tool 调用，完全没有 channel、routing、bus 的概念。

产品层桥接由 `AgentLoop`（`nanobot/agent/loop.py:115-224`）完成。`AgentLoop` 持有 `bus`、`session_manager`、`cron_service`、`channels_config`——所有产品层依赖——并将入站消息翻译为 `AgentRunSpec`，将 `AgentRunResult` 翻译为出站消息：

- `_process_message()`（`loop.py:481-586`）从 `InboundMessage` 提取 `channel`、`chat_id`、`content`，构建 messages 上下文，组装 `AgentRunSpec`，调用 `self.runner.run(spec)`。
- `_run_agent_loop()`（`loop.py:300-361`）创建 `AgentRunSpec` 并委托给 `AgentRunner`，只负责组装参数和回传结果。
- `_dispatch()`（`loop.py:398-456`）处理流式回调、消息发布等产品层逻辑。

`AgentRunner` 完全不知道消息是从 Telegram 来的还是 CLI 来的。

**关键源码**：
- `nanobot/agent/runner.py:44-68` — `AgentRunSpec` dataclass（纯数据，无 channel/session/cron 引用）
- `nanobot/agent/runner.py:83-89` — `AgentRunner.__init__` 和 `run()` 签名（仅接受 provider + spec）
- `nanobot/agent/runner.py:89-320` — 完整的执行循环（只操作 messages 和 tools）
- `nanobot/agent/loop.py:115-224` — `AgentLoop` 持有所有产品层依赖
- `nanobot/agent/loop.py:339-355` — `AgentRunSpec` 的组装位置（bridge 层）

---

### openclaw: pi-agent-core 委托 + channel 参数透传

**所属仓库**: [[openclaw-agent-harness|Agent Harness (OpenClaw)]]
**维度**: Architecture
**解耦方式**: 通过 pi-agent-core 委托实现核心执行的产品无关，但 channel/gateway 信息作为参数流入

**机制**

openclaw 的执行引擎有两层：外层的 `runEmbeddedPiAgent`（`src/agents/pi-embedded-runner/run.ts:162-1779`）和内层的 `runEmbeddedAttempt`（`src/agents/pi-embedded-runner/run/attempt.ts`），后者委托给 `@mariozechner/pi-agent-core`（`createAgentSession`、`SessionManager`）完成实际的 LLM 交互循环。pi-agent-core 本身是一个独立包，不感知 channel/gateway。

但外层 `runEmbeddedPiAgent` 接收的 `RunEmbeddedPiAgentParams`（`src/agents/pi-embedded-runner/run/params.ts:22-80`）包含了大量 channel/gateway 字段：`messageChannel`、`messageProvider`、`agentAccountId`、`messageTo`、`messageThreadId`、`groupId`、`groupChannel`、`groupSpace`、`senderId`、`senderName`、`currentChannelId`、`currentThreadTs`、`currentMessageId`、`replyToMode` 等——字段数超过 40 个。这些参数并非被执行引擎直接"使用"，而是透传到底层 tool resolution（工具策略基于 channel/group 决定谁可以用什么工具）、auth profile selection（基于 session 选择 API key）、和 messaging tool（回复发送到正确的 channel）。

Harness 插件系统进一步抽象了这一层。`AgentHarness` 接口（`src/agents/harness/types.ts:30-39`）定义了 `runAttempt(params: AgentHarnessAttemptParams)` 的统一签名。`EmbeddedRunAttemptParams`（`src/agents/pi-embedded-runner/run/types.ts:21-40`）继承了全部 channel 字段，插件 harness 可以选择性使用或忽略它们。`selectAgentHarness()`（`src/agents/harness/selection.ts:45-106`）根据 provider/modelId 动态选择 harness 实现，内置 PI harness 永远作为 `priority: 0` 兜底。

所以 openclaw 的解耦方式是**两层委托**：pi-agent-core 完全不感知产品层；外层 runEmbeddedPiAgent 以参数透传的方式把 product context 交给 tool policy 和 messaging 层，而非执行引擎本身持有 channel 对象。

**关键源码**：
- `src/agents/pi-embedded-runner/run/params.ts:22-80` — `RunEmbeddedPiAgentParams` 包含 40+ channel/gateway 字段
- `src/agents/pi-embedded-runner/run/backend.ts:4-8` — 委托给 `runAgentHarnessAttemptWithFallback`
- `src/agents/harness/types.ts:30-39` — `AgentHarness` 接口（统一 `runAttempt` 签名）
- `src/agents/harness/selection.ts:45-106` — `selectAgentHarness()` 动态 selection + PI fallback
- `src/agents/harness/builtin-pi.ts:4-11` — PI harness 的兜底实现（`supports()` 始终返回 true）

---

### hermes: AIAgent 直接持有 platform/user/session

**所属仓库**: [[hermes-agent|Hermes Agent]]
**维度**: Architecture
**解耦方式**: 无解耦——执行引擎与产品层直接耦合

**机制**

hermes 的 `AIAgent`（`run_agent.py:535-733`）是一个单体类，约 11,000 行的 `run_agent.py` 中包含了模型配置、对话流、工具执行、session 管理、memory、trajectory 持久化等全部逻辑。`__init__` 直接接受并存储产品层参数（`run_agent.py:669-671`）：

```python
self.platform = platform  # "cli", "telegram", "discord", "whatsapp", etc.
self._user_id = user_id  # Platform user identifier (gateway sessions)
self._gateway_session_key = gateway_session_key  # Stable per-chat key
```

这些不是"透传的参数"——它们是 `self` 上的实例属性，在整个 `run_conversation()` 方法中随时可用。`platform` 被注入 system prompt 做格式化提示；`user_id` 参与 memory 作用域判断；`gateway_session_key` 影响 session DB 查询路径。AIAgent 没有"核心执行循环"和"产品层适配"的边界——两者是同一段代码。

gateway（`gateway/run.py:5690-5711`）创建 AIAgent 时传入 `platform=platform_key`、`user_id=source.user_id`、`session_db=self._session_db`。每个消息或 turn 创建一个新的 AIAgent 实例——类级别缓存 `_context_pressure_last_warned` 的存在（`run_agent.py:547`）正是因为"gateway creates a new AIAgent per message"，实例级状态在每次消息处理后被丢弃。

这种设计意味着 hermes 的执行引擎**无法脱离 gateway 独立复用**。AIAgent 不只是"知道" platform——它的整个构造和运行依赖于 platform、user、session 的存在。CLI 入口（`cli.py:2872`）和 batch runner（`batch_runner.py:314`）各自以不同参数集实例化 AIAgent，没有共享的执行核心。

**关键源码**：
- `run_agent.py:535-733` — `AIAgent.__init__` 接受 `platform`、`user_id`、`gateway_session_key`、`session_db` 等产品层参数
- `run_agent.py:669-671` — 产品层参数作为实例属性存储
- `run_agent.py:547-548` — 类级别注释确认"gateway creates a new AIAgent per message"
- `gateway/run.py:5690-5711` — gateway 创建 AIAgent 时传入 `platform=platform_key`、`user_id=source.user_id`

---

## 对比分析

| 维度 | nanobot | openclaw | hermes |
|------|---------|----------|--------|
| **执行引擎实例** | `AgentRunner`（100 行纯循环） | pi-agent-core（独立包）+ 外层参数管理层 | `AIAgent`（~11,000 行单体） |
| **引擎持有 channel 引用？** | 否——连 channel 概念都不存在 | 否——参数透传，非对象持有 | 是——`self.platform`、`self._user_id` |
| **引擎持有 session 引用？** | 否——只接受 `session_key: str` | 否——`sessionFile`/`sessionKey` 是字符串参数 | 是——`session_db`、`session_id`、`gateway_session_key` |
| **引擎持有 cron 引用？** | 否——AgentRunner 无 cron 概念 | 否——`trigger: "cron"` 仅为字符串枚举 | 无关——gateway 独立处理调度 |
| **产品层桥接在哪？** | `AgentLoop` 是唯一的桥接层 | `runEmbeddedPiAgent` 做参数组装 + tool policy 路由 | 无桥接——AIAgent 本身就是产品层 |
| **在不同场景间复用的方式** | 每个场景写自己的 AgentLoop（或用同一个） | 切换 messageChannel/enqueue 参数 | 每次创建新的 AIAgent 实例 |
| **单元测试可行性** | AgentRunner 可以直接用 mock provider + spec 测试 | pi-agent-core 独立可测；外层需 mock 40+ 参数 | 需要 mock platform/user/session/db 全部依赖 |
| **新增一个 channel 的成本** | 实现 AgentLoop 的消息接收/发送逻辑 | 提供 messageChannel/messageProvider 参数适配 | 在 AIAgent 中修改 platform 相关的条件分支 |

## 设计权衡

### 分离的代价

nanobot 的 `AgentRunner` 是最干净的分离。但这不是免费的——`AgentRunner` 的简洁性依赖于 `AgentRunSpec` 预先包含了执行所需的一切（messages、tools、model、所有配置），而这些配置在真实场景中来自不同的来源：`AgentLoop.__init__` 从 config、环境变量、构造参数中收集它们。分离越好，组装层的复杂度越高。

`AgentLoop._process_message()`（`loop.py:481-586`）就是这份"组装税"——它必须理解 session 恢复、runtime checkpoint 回放、slash command 拦截、context building、streaming callback 适配，然后才把干净的 `AgentRunSpec` 交给 `AgentRunner`。如果新增一个关键配置（例如 temperature 控制），需要在 `AgentRunSpec` 加字段、在 `AgentLoop._run_agent_loop()` 透传、在 `AgentRunner._build_request_kwargs()` 消费——三个位置的修改。

### 参数透传是不是"耦合"？

openclaw 的 `RunEmbeddedPiAgentParams` 包含 40+ channel 字段。这算不算耦合？取决于"耦合"的定义。

如果耦合指的是"执行引擎 *持有* channel 对象引用，并主动调用 channel 的方法"，那 openclaw 没有这个问题——channel 信息是参数，是数据，引擎不调用 channel 的 API。如果耦合指的是"执行引擎的接口签名中出现了 channel 概念"，那 openclaw 确实耦合——修改 channel 模型（例如新增 `groupSpace`）需要同步修改 params 类型和所有调用方。

关键区别在调用方向：hermes 的 AIAgent *调用* `self.platform` 来决定行为；openclaw 的 `runEmbeddedPiAgent` *接收* channel 信息但自己不消费——它透传给 tool policy/messaging 层。consumer 是下游，不是引擎本身。这是一种"数据耦合"而非"行为耦合"。

### 单体 ≠ 错误

hermes 的 AIAgent 单体设计不是"糟糕的工程"——它反映了一个事实：hermes 最初是 CLI 工具（`run_agent.py` 顶部 docstring 的用法示例是 `agent = AIAgent(base_url=..., model=...)`），gateway、batch runner、RL CLI 是后来加上的。当一个系统从单一 CLI 工具逐步演进到多平台 gateway 时，单体类是最自然的起点。

class-level 的 `_context_pressure_last_warned` 缓存和"gateway creates a new AIAgent per message"的注释说明团队已经意识到实例化的开销模式，但还没有把重构"从 AIAgent 中提取产品无关的执行核心"排上优先级。这不是架构选择的失败，而是演进阶段的问题——重构的 ROI 还没超过其他优先级。

### 什么时候该分离？

三个仓库给出了三种答案，对应三种规模：

- **CLI tool 阶段**（hermes 的起点）：单体类足够。一个 `AIAgent` 类直接接受 platform 字符串做格式化差异，不需要抽象层。
- **单仓库多场景阶段**（nanobot）：提取纯执行引擎 + bridge 层。`AgentRunner` 只有 724 行（runner.py 全长），`AgentLoop` 751 行（loop.py 全长）——两层加起来和一个 hermes AIAgent 的一段 __init__ 差不多长。关键在于"谁负责组装"——bridge 层承担了从产品模型到执行模型的翻译。
- **多场景 + 多 provider + 插件生态阶段**（openclaw）：两重委托 + harness 插件接口。pi-agent-core 保证核心执行的产品无关；`runEmbeddedPiAgent` 做参数组装和 policy 路由；`AgentHarness` 接口让第三方注册自己的执行后端。channel 字段数量多不是因为耦合深，而是因为 tool policy 的粒度细——不同的 tool 在不同 channel/group/space 上有不同的权限策略。

## 关键洞察

**这不是"解耦 vs 不解耦"的二元选择，而是"在哪一层画线"的粒度问题。**

nanobot 的线画在 `AgentRunner.run()` 的边界——输入是 messages + tools + config，输出是 result。线内只有 LLM 调用循环；线外是所有产品层逻辑。这条线画得最靠内——AgentRunner 是三个仓库中最小的执行核心。

openclaw 的线有两层：内层在 pi-agent-core（独立包，完全产品无关），外层在 `runEmbeddedPiAgent`（接受 channel 参数但不持有 channel 对象）。tool policy 层需要 channel 信息做权限判断，所以外层接受 channel ——但它是"数据流入"，不是"控制反转"。

hermes 没有画线。AIAgent 同时扮演执行引擎、session manager、tool dispatcher、platform adapter。这不意味着"hermes 错了"——只是说明在当前演进阶段，重构的 ROI 低于其他优先级。

**共同趋势**：三个仓库都在不同程度上承认"执行引擎应该是纯函数"——`(messages, tools, model) -> result`。但产品层的 reality（权限、routing、streaming、session persistence）强迫引擎边界外移。真正的工程问题不是"能不能画线"，而是"线外的组装复杂度谁来承担"。

## 适用场景启发

- **如果你的 agent harness 服务多个 channel 且 channel 之间有显著的行为差异**（不同 tool 权限、不同 context 注入），采用 openclaw 的参数透传模式——让 channel 信息作为数据流入 policy 层，不要让引擎持有 channel 对象。
- **如果你的执行循环逻辑本身在不同场景间完全相同**，采用 nanobot 的纯数据接口——`AgentRunner` 的 `run(spec) -> result` 签名保证了引擎可以独立测试、独立演进。组装层（AgentLoop）的成本是一次性的。
- **如果你只有一个使用场景**（CLI 或单一 bot），不需要过早分离。hermes 的单体 AIAgent 说明了"先让它 work，等场景多了再考虑提取"是完全合理的路径。但注意：当第二个场景出现时，重构的成本会比从零开始就分离更高。
- **如果你需要支持第三方注册自己的执行后端**，采用 openclaw 的 harness 插件接口——`AgentHarness.supports()` + priority 排序 + PI fallback 的模式让核心执行可以被替换而不破坏产品层。

## 关联页面

- [[openclaw-agent-harness]] — openclaw harness 系统整体架构
- [[hermes-agent]] — hermes AIAgent 实现细节
- [[nanobot]] — nanobot AgentRunner + AgentLoop 架构
- [[plugin-subsystem-auto-discovery]] — harness/channel 的自动发现机制对比
- [[context-engine-singleton-vs-pluggable]] — Context Engine 的类似解耦问题（另一个维度的"在哪画线"）
