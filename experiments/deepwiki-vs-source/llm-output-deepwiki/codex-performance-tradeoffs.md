# Codex — Performance Tradeoffs 维度分析

> 从 DeepWiki 预解析内容中提取的性能权衡知识。每条事实声明以 `^[文件路径:行号范围]` 结尾。

---

## 1. WebSocket 连接跨 Turn 缓存复用 vs. 连接陈旧风险

### 优化目标
消除每个 turn 建立 WebSocket 连接所需的握手延迟，降低首 token 延迟。

### 优化手段
- **连接池（容量=1）**：`cached_websocket_session` 在 `ModelClientState` 中缓存一个活跃 WebSocket 连接。^[codex-rs/core/src/client.rs:165]
- **turn 间复用**：`ModelClient::new_session()` 原子性地取走缓存的 WS 连接；如果存在则直接复用，否则创建新连接。^[codex-rs/core/src/client.rs:271]
- **turn 结束后归还**：`ModelClientSession` 在 drop 时通过 `store_cached_websocket_session()` 将连接存回共享缓存。^[codex-rs/core/src/client.rs:499-505]
- **两次预热层**：连接预热（`preconnect_websocket`）仅打开握手；请求预热 v2（`prewarm_websocket`）发送 `generate=false` 请求，服务端返回 `response_id` 但不生成内容，预填充后端缓存。^[codex-rs/core/src/client.rs:700-777]

### 牺牲
- **陈旧连接风险**：缓存的连接可能在网络层面已断开（对端超时），下次使用时才会发现失败。
- **内存占用**：WebSocket 连接即使空闲也占用文件描述符和内存。
- **负载均衡退化**：连接复用 + sticky routing 导致同一会话的所有请求路由到同一后端节点，减少了负载分配灵活性。

### 权衡理由
WebSocket 握手（TCP+TLS+Ws upgrade）通常需要几百毫秒。对于多 turn 交互式 agent 会话，每次 turn 重新连接的延迟叠加严重影响用户体验。单连接缓存配合预请求预热是流式 LLM API 场景下权衡延迟与资源的最优解。

### 源码证据
- 连接缓存字段 `cached_websocket_session` ^[codex-rs/core/src/client.rs:165]
- 新建会话时取走缓存连接 ^[codex-rs/core/src/client.rs:271]
- Drop 时归还 `store_cached_websocket_session()` ^[codex-rs/core/src/client.rs:499-505]
- 连接预热 `preconnect_websocket()` ^[codex-rs/core/src/client.rs:735-777]
- 请求预热 `prewarm_websocket()` with `generate=false` ^[codex-rs/core/src/client.rs:700-734]

---

## 2. Sticky Routing (`x-codex-turn-state`) vs. 负载均衡

### 优化目标
在同一 turn 内将增量请求路由到同一后端节点，利用后端内存缓存加速响应。

### 优化手段
- **per-turn 粘性令牌**：服务端响应流中返回 `x-codex-turn-state` header；客户端在 `Arc<OnceLock<String>>` 中缓存。^[codex-rs/codex-api/src/endpoint/responses_websocket.rs:155]
- **后续请求回传**：同一 turn 的后续请求在 `x-codex-turn-state` header 中回传此令牌。^[codex-rs/core/src/client.rs:596]
- **turn 级作用域**：令牌生命周期与 `ModelClientSession` 一致，跨 turn 不持久。

### 牺牲
- **负载均衡能力降低**：同一 turn 的所有请求固定到单一后端节点。
- **故障影响放大**：如果该后端节点过载，整个 turn 的所有请求都会受影响。
- **冷却启动问题**：后端节点可能因负载不均衡而出现热点。

### 权衡理由
LLM 推理服务通常在前一个请求的 KV-cache（Key-Value 注意力缓存）中保持上下文。如果增量请求被路由到不同节点，后端必须重新计算整个上下文的注意力状态，这会抵消增量请求节省的延迟收益。粘性路由是后端缓存效率与负载均衡之间的务实权衡——在单个 turn 的短时间窗口内维持亲和，但不跨 turn 持久。

### 源码证据
- 服务端返回 `x-codex-turn-state` header ^[codex-rs/codex-api/src/endpoint/responses_websocket.rs:155]
- 客户端缓存令牌 `turn_state: Arc<OnceLock<String>>` ^[codex-rs/core/src/client.rs:194]
- 后续请求回传 `x-codex-turn-state` ^[codex-rs/core/src/client.rs:596]
- Header 常量定义 `X_CODEX_TURN_STATE_HEADER` ^[codex-rs/core/src/client.rs:135]

---

## 3. 远程压缩 vs. 本地压缩（Provider 依赖 vs. 通用可用性）

### 优化目标
利用提供者原生的压缩 API 执行更高效的历史压缩。

### 优化手段
- **本地压缩**：使用标准推理 turn 让模型根据 `SUMMARIZATION_PROMPT` 生成摘要——适用于所有提供者。如果摘要请求因窗口满而失败，逐条删除最旧消息并重试。^[codex-rs/core/src/compact.rs:170-208]
- **远程压缩 v1**：调用提供者的 `compact_conversation_history()` API，服务端直接返回 `ResponseItem::Compaction`。^[codex-rs/core/src/compact_remote.rs:188-197]
- **远程压缩 v2**：优化版支持流式响应和增强重试逻辑（`MAX_REMOTE_COMPACTION_V2_STREAM_RETRIES = 2`），保留 `RETAINED_MESSAGE_TOKEN_BUDGET = 64,000`。^[codex-rs/core/src/compact_remote_v2.rs:49-53]
- **路由决策**：`should_use_remote_compact_task()` 根据提供者能力 + `Feature::RemoteCompactionV2` 开关决定使用哪个路径。^[codex-rs/core/src/compact.rs:65-67]
- **远程前历史修剪**：调用远程 API 前，`trim_function_call_history_to_fit_context_window` 移除最旧的工具调用和推理项。^[codex-rs/core/src/compact_remote.rs:293-323]

### 牺牲
- **远程路径提供者锁定**：只有支持 `supports_remote_compaction()` 的提供者才能使用远程压缩——提供者可移植性降低。
- **远程 API 稳定性风险**：远程压缩端点的可用性和行为由提供者控制，Codex 无法完全保证。
- **本地重试循环成本**：本地压缩失败时逐个删除消息的循环可能触发多次 LLM 调用。

### 权衡理由
远程压缩由提供者在后端优化执行，避免了客户端上传完整历史再下载摘要的往返延迟。但并非所有提供者都支持此功能，本地压缩作为通用回退确保在任何提供者上都能工作。v2 的流式支持和增强重试是通往更通用、更可靠远程压缩的演进路径。

### 源码证据
- 本地压缩循环与重试 ^[codex-rs/core/src/compact.rs:170-208]
- 远程压缩 API 调用 ^[codex-rs/core/src/compact_remote.rs:188-197]
- V2 保留预算 `RETAINED_MESSAGE_TOKEN_BUDGET = 64000` ^[codex-rs/core/src/compact_remote_v2.rs:49]
- 远程前修剪 `trim_function_call_history_to_fit_context_window` ^[codex-rs/core/src/compact_remote.rs:293-323]
- 提供者能力检查 `should_use_remote_compact_task()` ^[codex-rs/core/src/compact.rs:65-67]

---

## 4. 增量输入追加（`previous_response_id`）vs. 全量请求重传

### 优化目标
减少同一 turn 内工具调用后模型继续生成时的网络传输量和后端处理开销。

### 优化手段
- **增量对比**：`get_incremental_items` 验证新请求的 input 是旧请求 input 的正确扩展，计算 delta 输入项。^[codex-rs/core/src/client.rs:610-646]
- **增量发送**：`prepare_websocket_request` 判断：第一个 chunk 发送完整的 `response.create`；后续 chunk 发送带 `previous_response_id` 和 delta `input` 的增量更新。^[codex-rs/core/src/client.rs:658-698]

### 牺牲
- **客户端复杂度**：需要精确跟踪 `last_request` 并与新请求对比。
- **对比逻辑错误风险**：如果增量计算失败，可能需要回退到全量请求。
- **严格依赖序列一致性**：假设请求序列完全有序且无缺失。

### 权衡理由
同一 turn 内的多轮工具调用，上下文中有大量不变的历史消息。全量重传会重复发送这些数据的 JSON 序列化和网络传输开销。增量追加以客户端少量计算成本换取大幅减少的网络带宽和后端重复处理。

### 源码证据
- 增量对比函数 `get_incremental_items()` ^[codex-rs/core/src/client.rs:610-646]
- 增量请求构建 `prepare_websocket_request()` ^[codex-rs/core/src/client.rs:658-698]
- `last_request` 用于增量对比 ^[codex-rs/core/src/client.rs:206]

---

## 5. Bubblewrap/Landlock 沙盒隔离 vs. 进程创建开销

### 优化目标
在 Linux 上为 agent 执行的 shell 命令提供强文件系统和网络隔离。

### 优化手段
- **Bubblewrap**：Linux 上默认使用 `bwrap` 进行隔离——文件系统默认只读，显式指定可写路径，通过 network namespace 隔离网络。^[codex-rs/core/src/config/mod.rs:7-10]
- **Landlock 回退**：`UseLegacyLandlock` feature flag 允许在 Bubblewrap 不可用时回退到 Landlock 沙盒。^[codex-rs/features/src/lib.rs:114-119]
- **Windows 受限令牌**：在 Windows 上使用 restricted access tokens 和 private desktops。^[codex-rs/core/src/config/mod.rs:8-10]
- **细粒度配置文件**：`PermissionProfile` 控制具体权限——`ReadOnly`（只读无网络）、`WorkspaceWrite`（工作区可写可选网络）、`DangerFullAccess`（无限制）。^[codex-rs/core/src/config/mod.rs:122-130]

### 牺牲
- **进程创建延迟**：每个 agent 执行的 shell 命令需要先创建和配置沙盒容器/namespace，增加数百毫秒延迟。
- **兼容性限制**：Bubblewrap 在某些旧内核或受限环境（如 Docker-in-Docker）中不可用。
- **跨平台差异**：Linux (Bubblewrap/Landlock) 和 Windows (Restricted Tokens) 的安全模型不同，行为不一致。

### 权衡理由
Agent 执行任意 shell 命令是最危险的攻击面。沙盒隔离是防止恶意或错误命令破坏主机文件系统、泄露敏感数据或访问内部网络的关键保障。几百毫秒的额外延迟在 agent 工具的秒级执行时间尺度上可接受——安全优先于原始执行速度。

### 源码证据
- Bubblewrap 沙盒 ^[codex-rs/core/src/config/mod.rs:7-10]
- Landlock 回退 feature flag ^[codex-rs/features/src/lib.rs:114-119]
- 权限配置文件：`BUILT_IN_READ_ONLY_PROFILE`, `BUILT_IN_WORKSPACE_PROFILE`, `DANGER_FULL_ACCESS` ^[codex-rs/core/src/config/mod.rs:122-130]

---

## 6. TurnContext 隔离 vs. 对象创建开销

### 优化目标
确保每个 turn 的配置（模型参数、沙盒策略、审批规则、指令）完全隔离，不跨 turn 泄漏。

### 优化手段
- **per-turn 对象**：每个 turn 创建新的 `TurnContext` 实例，包含 turn 级配置、策略、元数据和状态。^[codex-rs/core/src/session/turn_context.rs:57-108]
- **细粒度字段**：包含 identity/routing、model/provider、approval/security、instructions/personality、environment、tools、metadata 等完整配置。^[codex-rs/core/src/session/turn_context.rs:58-105]
- **SessionTask 抽象**：通过 `SessionTask` trait 统一管理 `RegularTask`、`ReviewTask`、`CompactTask`、`UserShellCommandTask`。^[codex-rs/core/src/tasks/mod.rs:57-62]

### 牺牲
- **对象创建开销**：每个 turn 分配和填充完整的 `TurnContext` 结构体（含多个 Vec 和 String）。
- **配置解析开销**：`TurnContext::new()` 从 `Session`、`Config`、`ModelsManager` 等多个源头汇聚配置。^[codex-rs/core/src/session/turn_context.rs:57-108]

### 权衡理由
跨 turn 的配置泄漏可能导致安全漏洞（如一个 turn 的降级审批策略意外应用到下一个 turn）或功能 bug（如不同模型的指令混淆）。Rust 的所有权系统和 `TurnContext` 的构造即销毁模式提供了编译器级别的隔离保证。对象创建开销在 Rust 的零成本抽象下被编译器优化到最低。

### 源码证据
- TurnContext 结构体定义与字段 ^[codex-rs/core/src/session/turn_context.rs:57-108]
- SessionTask trait 与任务变体 ^[codex-rs/core/src/tasks/mod.rs:57-62]

---

## 7. 模型 Slug 最长前缀匹配 vs. 精确匹配确定性

### 优化目标
允许用户使用部分模型名称（如 `gpt-5.3` 匹配 `gpt-5.3-codex-test` 和 `gpt-5.3`）简化模型选择。

### 优化手段
- **最长前缀匹配**：`ModelsManager::get_model_info()` 在缓存列表中按最长匹配 slug 前缀找到最佳 `ModelInfo`。^[codex-rs/core/tests/suite/remote_models.rs:58-117]
- **上下文窗口钳制**：用户配置的 `model_context_window` override 被钳制到模型的 `max_context_window`。^[codex-rs/core/tests/suite/remote_models.rs:123-184]
- **配置覆盖**：`base_instructions` 覆盖模型默认指令，`Personality` feature 注入个性模板。^[codex-rs/core/tests/suite/personality.rs:109-127]

### 牺牲
- **歧义风险**：多个模型 slug 可能共享相同前缀，最长匹配可能选到非预期模型（如用户想要 `gpt-5.3` 但匹配到了 `gpt-5.3-codex`）。
- **无显式错误**：如果输入无法匹配任何已知模型，fallback 行为可能不透明。

### 权衡理由
完整 slug（如 `gpt-5.3-codex-test-2026-03-15`）对用户不友好。前缀匹配使得用户可以用简短别名选择模型，同时保留精确匹配作为 specialization。最坏情况是选中了功能更强的变体而非弱版本——这通常比反向更安全。

### 源码证据
- 最长前缀匹配实现 ^[codex-rs/core/tests/suite/remote_models.rs:58-117]
- 上下文窗口钳制 ^[codex-rs/core/tests/suite/remote_models.rs:123-184]
- 配置覆盖与个性注入 ^[codex-rs/core/tests/suite/personality.rs:109-127]

---

## 8. WebSocket 永久降级 vs. 连接恢复尝试

### 优化目标
在 WebSocket 连接发生严重故障后防止无休止的重试循环。

### 优化手段
- **会话级永久降级**：`activate_http_fallback()` 原子性地将 `disable_websockets` 设为 `true`。^[codex-rs/core/src/client.rs:508-515]
- **粘性降级**：一旦降级为 HTTP SSE，整个 Codex 会话后续所有请求不再尝试 WebSocket。^[codex-rs/core/src/client.rs:508-515]
- **触发条件**：WebSocket 握手失败或流重试耗尽后触发降级。^[codex-rs/core/src/client.rs:428-435]

### 牺牲
- **无法恢复**：即使网络状况好转或后端问题解决，当前会话无法恢复 WebSocket 传输。
- **HTTP SSE 更高的延迟和带宽**：相比持久连接，HTTP SSE 每次 streaming 需要新的 HTTP 请求。

### 权衡理由
WebSocket 的握手和连接维护在故障场景下可能陷入无限重试循环，浪费客户端和后端资源。永久降级是 "fail fast and stay safe" 的策略——承认当前会话的 WebSocket 不可靠并用 HTTP SSE 继续（功能等价但性能较低），而非让会话永久卡死。

### 源码证据
- HTTP 降级 `activate_http_fallback()` ^[codex-rs/core/src/client.rs:508-515]
- 降级触发：握手失败 ^[codex-rs/core/src/client.rs:428-435]
- `disable_websockets: AtomicBool` ^[codex-rs/core/src/client.rs:164]

---

## 9. 工具输出截断策略 vs. 完整输出保真度

### 优化目标
防止超大工具输出（shell 命令输出、文件读取）消耗过多上下文窗口 token。

### 优化手段
- **基于模型配置的截断策略**：`TruncationPolicyConfig` 支持按 `Bytes` 或 `Tokens` 限制工具输出。^[codex-rs/protocol/src/openai_models.rs:223-226]
- **自动截断**：超出限制的输出在发送给模型前被截断，标记 `…X chars truncated…`。^[codex-rs/core/tests/suite/truncation.rs:185]
- **历史记录时截断**：`record_items` 使用 `truncate_function_output_items_with_policy` 处理工具输出。^[codex-rs/core/src/context_manager/history.rs:26-27]

### 牺牲
- **信息丢失**：截断后的输出可能遗漏关键信息（如文件末尾的错误消息、日志关键行）。
- **模型可能基于不完整信息做出错误决策**：特别是在需要完整输出的场景（如读取配置文件）。

### 权衡理由
LLM API 按输入 token 计费且受上下文窗口限制。不加以控制的工具输出可能单次调用就消耗数万 token——编译错误日志、大文件内容、长命令输出。截断策略以可控的信息损失换取对 API 成本的确定性控制和对上下文窗口的保护。

### 源码证据
- 截断策略配置 `TruncationPolicyConfig` ^[codex-rs/protocol/src/openai_models.rs:223-226]
- 截断标记格式 ^[codex-rs/core/tests/suite/truncation.rs:185]
- 工具输出截断函数 `truncate_function_output_items_with_policy` ^[codex-rs/core/src/context_manager/history.rs:26-27]

---

## 权衡汇总表

| 权衡项 | 优化了什么 | 牺牲了什么 | 理由 |
|--------|-----------|-----------|------|
| WS 连接跨 turn 缓存与预热 | 首 token 延迟与连接建立开销 | 陈旧连接风险与内存占用 | 交互式会话的延迟是关键体验指标 |
| Sticky Routing | 后端 KV-cache 命中率 | 负载均衡能力 | 避免跨节点重算注意力上下文 |
| 远程 vs 本地压缩 | 压缩效率与延迟 | 提供者可移植性 | 提供者原生优化 > 通用方案 |
| 增量输入追加 | 网络带宽与后端处理 | 客户端对比逻辑复杂度 | 同一 turn 大量不变上下文重传浪费 |
| Bubblewrap 沙盒 | 命令执行安全性 | 进程创建延迟 | 安全性是 agent 工具执行的前提 |
| TurnContext 隔离 | 配置不跨 turn 泄漏 | per-turn 对象创建开销 | Rust 零成本抽象 + 安全隔离保证 |
| 最长前缀匹配 | 模型选择便利性 | 潜在歧义匹配 | 短期用户友好 > 极端精确性 |
| WS 永久降级 | 避免重试循环浪费 | 会话期无法恢复 WS | fail-fast 保持会话进行 > 无限等待 |
| 工具输出截断 | Token 成本与窗口控制 | 输出完整性 | API 计费模型与窗口限制的务实应对 |
