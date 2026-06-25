# Codex Extension Points 维度知识

## 1. ExtensionRegistry —— 核心扩展注册框架

Codex 的扩展架构围绕 `ExtensionRegistryBuilder` 和一组 `Contributor` trait 构建。宿主（host）通过 builder 模式注册类型化的扩展贡献者，然后构建为不可变的 `ExtensionRegistry`。所有内置扩展（skills、web-search、memories、goal、guardian、image-generation、MCP）均通过同一套 `install()` 函数接入。

### 1.1 核心类型

`ExtensionRegistryBuilder<C>` 是泛型于宿主配置类型 `C` 的可变注册表，持有 12 种贡献者列表，每种贡献者通过独立的 `register` 方法添加。^[codex-rs/ext/extension-api/src/registry.rs:21-34]

```rust
pub struct ExtensionRegistryBuilder<C: Sync> {
    event_sink: Arc<dyn ExtensionEventSink>,
    thread_lifecycle_contributors: Vec<Arc<dyn ThreadLifecycleContributor<C>>>,
    turn_lifecycle_contributors:  Vec<Arc<dyn TurnLifecycleContributor>>,
    config_contributors:          Vec<Arc<dyn ConfigContributor<C>>>,
    token_usage_contributors:     Vec<Arc<dyn TokenUsageContributor>>,
    context_contributors:         Vec<Arc<dyn ContextContributor>>,
    mcp_server_contributors:      Vec<Arc<dyn McpServerContributor<C>>>,
    turn_input_contributors:      Vec<Arc<dyn TurnInputContributor>>,
    tool_contributors:            Vec<Arc<dyn ToolContributor>>,
    tool_lifecycle_contributors:  Vec<Arc<dyn ToolLifecycleContributor>>,
    turn_item_contributors:       Vec<Arc<dyn TurnItemContributor>>,
    approval_review_contributors: Vec<Arc<dyn ApprovalReviewContributor>>,
}
```

`build()` 将 builder 转为不可变的 `ExtensionRegistry<C>`，其字段为私有，通过只读访问器暴露。^[codex-rs/ext/extension-api/src/registry.rs:132-148]

### 1.2 12 种贡献者 Trait

每种贡献者 trait 代表一个纵向切面的扩展点，覆盖完整的线程/回合/工具/配置生命周期：

| 贡献者 Trait | 生命周期/切入点 | 返回/副作用 |
|---|---|---|
| `ThreadLifecycleContributor<C>` | on_thread_start / on_thread_resume / on_thread_idle / on_thread_stop | `ExtensionFuture<()>` |
| `TurnLifecycleContributor` | on_turn_start / on_turn_stop / on_turn_abort / on_turn_error | `ExtensionFuture<()>` |
| `ConfigContributor<C>` | on_config_changed | 同步，无返回值 |
| `TokenUsageContributor` | on_token_usage | `ExtensionFuture<()>` |
| `ContextContributor` | contribute (prompt 组装时) | `Vec<PromptFragment>` |
| `TurnInputContributor` | contribute (回合提交时) | `Vec<ContextualUserFragment>` |
| `ToolContributor` | tools（工具列表查询时） | `Vec<Arc<dyn ToolExecutor<ToolCall>>>` |
| `ToolLifecycleContributor` | on_tool_start / on_tool_finish | `ToolLifecycleFuture<()>` |
| `McpServerContributor<C>` | contribute（MCP 服务器解析时） | `Vec<McpServerContribution>` |
| `TurnItemContributor` | contribute（回合项后处理时） | `Result<(), String>` |
| `ApprovalReviewContributor` | contribute（审批提示渲染时） | `Option<ReviewDecision>` |

完整 trait 定义位于 ^[codex-rs/ext/extension-api/src/contributors.rs:54-259]

### 1.3 扩展状态存储

`ExtensionData` 是基于类型擦除的线程安全键值存储，支持 session/thread/turn 三级作用域。扩展通过 `insert<T>()` / `get<T>()` / `get_or_init<T>()` 操作类型化的附件。^[codex-rs/ext/extension-api/src/state.rs:49-118]

`ExtensionDataInit` 在作用域创建前由宿主注入初始值，克隆时冻结映射。^[codex-rs/ext/extension-api/src/state.rs:17-45]

### 1.4 宿主能力注入

扩展可通过 `ExtensionRegistryBuilder` 获取宿主提供的能力：
- `ExtensionEventSink`：发送协议事件到宿主的 fire-and-forget 通道 ^[codex-rs/ext/extension-api/src/capabilities/events.rs:1-14]
- `AgentSpawner`：从扩展中创建子 agent 的异步能力 ^[codex-rs/ext/extension-api/src/capabilities/agent.rs:11-21]
- `ResponseItemInjector`：在同回合内注入模型可见的响应项 ^[codex-rs/ext/extension-api/src/capabilities/response_items.rs:1-16]

---

## 2. Hooks 系统 —— 事件驱动的命令钩子

### 2.1 钩子事件类型

Codex 定义了 10 种钩子事件，覆盖完整的 Agent 交互生命周期：

| 事件名 | 触发时机 | 能否阻断 |
|---|---|---|
| `PreToolUse` | 工具执行前 | 是 |
| `PostToolUse` | 工具执行后 | 否（后处理） |
| `PermissionRequest` | 权限请求时 | 是 |
| `PreCompact` | 上下文压缩前 | 是 |
| `PostCompact` | 上下文压缩后 | 否 |
| `SessionStart` | 会话启动/恢复/清理 | 否 |
| `UserPromptSubmit` | 用户提交提示前 | 否 |
| `SubagentStart` | 子代理启动时 | 否 |
| `SubagentStop` | 子代理停止时 | 否 |
| `Stop` | 会话停止时 | 否 |

事件常量定义 ^[codex-rs/hooks/src/lib.rs:19-30]

8 种事件支持 matcher 字段用于细粒度分发，`UserPromptSubmit` 和 `Stop` 不支持 matcher。^[codex-rs/hooks/src/lib.rs:37-46]

### 2.2 钩子处理器类型

每个钩子组配置为 `MatcherGroup`，包含可选的 matcher 正则和多个 handler：
- **Command**：执行 shell 命令，stdin 传入 JSON，stdout 读取 JSON 输出 ^[codex-rs/hooks/src/engine/mod.rs:41-52]
- **Prompt**：将钩子输出注入 prompt 上下文
- **Agent**：触发子 agent 执行

### 2.3 钩子来源

钩子可从三层配置中加载：
1. **用户/项目 config.toml**：在 `[hooks]` 部分声明 ^[codex-rs/hooks/src/config_rules.rs:16-60]
2. **插件 hooks.json**：插件清单中的 `paths.hooks` 指向 hooks JSON 文件 ^[codex-rs/plugin/src/manifest.rs:19-31]
3. **受管钩子**：通过 `ManagedHooksRequirementsToml` 由组织策略注入 ^[codex-rs/hooks/src/engine/discovery.rs:63-80]

### 2.4 钩子发现与分发

`discovery::discover_handlers()` 遍历配置层栈，收集所有 `hooks.json` 路径，解析每个文件中的 `MatcherGroup`，生成 `ConfiguredHandler` 列表。^[codex-rs/hooks/src/engine/discovery.rs:34-80]

`ClaudeHooksEngine` 持有所有处理器并按事件类型分发。每个事件有 `preview_*()` 方法（返回摘要）和 `run_*()` 异步方法（实际执行）。输出通过 `HookOutputSpiller` 管理大文本溢出到文件。^[codex-rs/hooks/src/engine/mod.rs:100-219]

### 2.5 钩子 JSON Schema

每个钩子事件都有生成的输入/输出 JSON Schema，文件位于 `hooks/schema/generated/` 目录。^[codex-rs/hooks/src/schema.rs:17-37]

---

## 3. 插件系统 —— 可安装的功能包

### 3.1 插件清单

插件通过 `PluginManifest<Resource>` 定义，包含：
- 元数据：name、version、description、keywords
- 资源路径 `PluginManifestPaths`：skills、mcp_servers、apps、hooks
- 展示接口 `PluginManifestInterface`：display_name、description、category、logo、brand_color、default_prompt 等 ^[codex-rs/plugin/src/manifest.rs:6-50]

### 3.2 插件标识

`PluginId` 格式为 `<plugin_name>@<marketplace_name>`，段只能使用 ASCII 字母数字、`_`、`-`。^[codex-rs/plugin/src/plugin_id.rs:9-48]

### 3.3 插件加载

`PluginsManager` 是插件的中央管理器：
- `plugins_for_config()` 按配置加载插件，带缓存和信号量锁 ^[codex-rs/core-plugins/src/manager.rs:451-498]
- 分别加载插件的 skills、hooks、MCP servers、apps 四种能力 ^[codex-rs/core-plugins/src/manager.rs:8-14]
- 支持远程插件同步（RemoteInstalledPlugins）和市场升级 ^[codex-rs/core-plugins/src/manager.rs:663-829]

### 3.4 市场系统

插件来源于市场（Marketplace），市场是文件系统上的插件集合目录：
- OpenAI curated marketplace：pre-installed 精选插件
- 用户安装的 Git marketplace
- 远程安装的插件缓存 ^[codex-rs/core-plugins/src/manager.rs:1052-1066]

插件加载从市场路径中读取插件清单，经过产品限制和认证过滤后生效。^[codex-rs/core-plugins/src/manager.rs:384-389]

### 3.5 插件能力摘要

每个插件加载后产生 `PluginCapabilitySummary`，汇总其 skills、MCP servers、apps 暴露情况。^[codex-rs/plugin/src/lib.rs:51-59]

---

## 4. Tool 系统 —— 工具扩展

### 4.1 ToolExecutor Trait

工具通过 `ToolExecutor<Invocation>` trait 定义，是模型可见工具的核心接口：

```rust
pub trait ToolExecutor<Invocation>: Send + Sync {
    fn tool_name(&self) -> ToolName;
    fn spec(&self) -> ToolSpec;
    fn exposure(&self) -> ToolExposure { Direct }
    fn search_info(&self) -> Option<ToolSearchInfo> { ... }
    fn supports_parallel_tool_calls(&self) -> bool { false }
    fn handle(&self, invocation: Invocation) -> ToolExecutorFuture<'_>;
}
```

^[codex-rs/tools/src/tool_executor.rs:49-69]

### 4.2 ToolExposure 策略

四种暴露级别控制工具对模型的可见性：
- `Direct`：直接可见 + code-mode 下也可用
- `Deferred`：通过 ToolSearch 延迟发现
- `DirectModelOnly`：直接可见但不在 code-mode 中暴露
- `Hidden`：注册但不可见，仅内部路由 ^[codex-rs/tools/src/tool_executor.rs:14-36]

### 4.3 工具贡献途径

工具可通过以下方式贡献给模型：
1. **ToolContributor**：扩展注册表中的 `tool_contributor()` 方法 ^[codex-rs/ext/extension-api/src/contributors.rs:211-218]
2. **MCP Server**：MCP 协议工具自动转换为 ResponsesApiTool ^[codex-rs/tools/src/lib.rs:63]
3. **Plugin skills**：插件 skills 通过 `skill_tools()` 暴露为模型工具 ^[codex-rs/ext/skills/src/extension.rs:133-151]
4. **DynamicTool**：运行时解析的动态工具 ^[codex-rs/tools/src/lib.rs:29]

### 4.4 工具链

- `ToolSpec` / `ToolDefinition`：工具声明 ^[codex-rs/tools/src/tool_spec.rs]
- `ToolCall`：标准化调用模型 ^[codex-rs/tools/src/lib.rs:68]
- `ToolOutput` / `JsonToolOutput`：标准化输出 ^[codex-rs/tools/src/lib.rs:99-100]
- `ToolName`：命名空间+本地名的复合键 ^[codex-rs/tools/src/lib.rs:28]

---

## 5. MCP 服务器 —— 协议级扩展

### 5.1 MCP Server Config

MCP 服务器通过 `McpServerConfig` 配置，支持 stdio、SSE、streamable HTTP 三种传输方式。^[codex-rs/codex-mcp/src/plugin_config.rs:1-60]

### 5.2 McpServerContributor

扩展可通过 `McpServerContributor` trait 动态贡献 MCP 服务器配置：
- 支持全局解析和线程级解析两种上下文
- 可通过 `Set` 添加/替换或 `Remove` 移除服务器
- 注册顺序决定优先级 ^[codex-rs/ext/extension-api/src/contributors/mcp.rs:1-63]

### 5.3 MCP 工具转换

MCP 工具通过 `mcp_tool_to_responses_api_tool()` 转换为 Codex 的内部 Responses API 工具格式，实现跨协议桥接。^[codex-rs/tools/src/lib.rs:62-63]

### 5.4 插件 MCP 支持

插件可以在清单中声明 `mcp_servers` 路径，指向 MCP 服务器配置文件（支持 `.json` 扩展名）。加载时从插件根目录解析，支持环境归属和 cwd 标准化。^[codex-rs/codex-mcp/src/plugin_config.rs:58]

---

## 6. Connectors / Apps —— 应用连接器

### 6.1 概念

App Connector 是 Codex 与外部应用（如第三方 SaaS）集成的方式。每个 App 由 `AppConnectorId` 标识，并有可选的 category。^[codex-rs/plugin/src/lib.rs:28-36]

### 6.2 插件声明

插件清单中的 `paths.apps` 指向一个 JSON 文件，声明 `AppDeclaration` 列表。每个 declaration 包含 name、connector_id、category。^[codex-rs/plugin/src/lib.rs:31-36]

### 6.3 连接器目录

`ConnectorDirectoryCache` 维护来自后端的应用连接器目录缓存，TTL 为 3600 秒。支持按账户过滤和合并。^[codex-rs/connectors/src/lib.rs:22-56]

---

## 7. Model Provider —— 模型提供商扩展

### 7.1 提供者架构

通过 `Provider` trait（来自 `codex_api` 包）定义模型提供者。支持：
- OpenAI 标准提供者
- Amazon Bedrock 提供者（通过 `AmazonBedrockModelProvider` 实现）^[codex-rs/model-provider/src/provider.rs:18]
- 通过 `create_model_provider()` 工厂函数创建

### 7.2 ProviderCapabilities

每个提供者暴露其能力上限（namespace_tools、image_generation、web_search），宿主据此决定是否启用相应扩展。^[codex-rs/model-provider/src/provider.rs:28-33]

### 7.3 模型发现

通过 `OpenAiModelsEndpoint` 从 `/v1/models` 端点动态发现可用模型。^[codex-rs/model-provider/src/models_endpoint.rs]

静态模型列表可通过 `StaticModelsManager` 提供，动态模型通过 `OpenAiModelsManager` 管理。^[codex-rs/model-provider/src/provider.rs:11-13]

---

## 8. Skills 扩展 —— 内置扩展案例研究

Skills 扩展是最完整的扩展实现范例，展示了如何综合利用多个 contributor trait：

### 8.1 注册方式

```rust
pub fn install<C>(
    registry: &mut ExtensionRegistryBuilder<C>,
    config_from_host: impl Fn(&C) -> SkillsExtensionConfig + Send + Sync + 'static,
)
```

^[codex-rs/ext/skills/src/extension.rs:321-332]

### 8.2 实现的 Trait

Skills 扩展同时实现了 5 种 contributor：
- `ThreadLifecycleContributor<C>`：线程启动时初始化 `SkillsThreadState` ^[codex-rs/ext/skills/src/extension.rs:52-69]
- `ConfigContributor<C>`：配置变更时更新技能配置 ^[codex-rs/ext/skills/src/extension.rs:71-89]
- `ContextContributor`：prompt 组装时注入可用技能列表 ^[codex-rs/ext/skills/src/extension.rs:91-131]
- `TurnInputContributor`：用户提交时解析显式技能提及，注入技能指令 ^[codex-rs/ext/skills/src/extension.rs:153-269]
- `ToolContributor`：暴露技能工具（`list_skills`、`read_skill` 等）^[codex-rs/ext/skills/src/extension.rs:133-151]

### 8.3 技能来源

`SkillProviders` 聚合多种技能来源：host 提供的技能、bundled（捆绑）技能、orchestrator 技能。每种来源通过 `SkillProvider` trait 统一接口访问。^[codex-rs/ext/skills/src/sources.rs]

---

## 扩展难度梯度

| 层级 | 扩展方式 | 难度 | 适用场景 |
|---|---|---|---|
| 1. 配置级 | 用户 config.toml hooks / MCP servers | 最低 | 自定义钩子脚本、添加 MCP 服务器 |
| 2. 插件包 | Plugin Manifest（skills/hooks/MCP/apps） | 低 | 可安装的可复用功能包 |
| 3. 工具贡献 | 实现 `ToolExecutor` + 注册 `ToolContributor` | 中 | 添加新的模型可见工具 |
| 4. 生命周期切入 | 实现 `ThreadLifecycleContributor` / `TurnLifecycleContributor` | 中 | 在关键生命周期节点添加行为 |
| 5. 全功能扩展 | 实现多个 Contributor + ExtensionState | 高 | 大型功能特性（如 skills/web-search） |
| 6. 模型提供者 | 实现 `Provider` trait + 模型发现 | 高 | 接入新的 AI 模型后端 |

---

## 关键关联

- **Hooks <-> Plugins**：插件可通过 `PluginManifestPaths.hooks` 声明钩子，在加载时注入 `PluginHookSource`。^[codex-rs/plugin/src/lib.rs:61-69]
- **Skills <-> ExtensionRegistry**：Skills 通过 `install()` 函数注册到 `ExtensionRegistryBuilder`，无需单独的服务发现。^[codex-rs/ext/skills/src/extension.rs:321-351]
- **Tools <-> Extensions**：扩展通过 `ToolContributor` 贡献原生工具，MCP 服务器通过协议转换自动贡献工具。^[codex-rs/ext/extension-api/src/contributors.rs:211-218]
- **Config <-> Everything**：所有扩展点通过 `ConfigContributor` 接收配置变更通知，线程级状态通过 `ExtensionData` 在锁外读写。^[codex-rs/ext/extension-api/src/contributors.rs:177-187]
- **MCP <-> Plugins <-> Extensions**：MCP 服务器可有三种来源：用户配置、插件清单声明、`McpServerContributor` 扩展动态贡献，三者合并后统一管理。^[codex-rs/ext/extension-api/src/contributors.rs:54-62]
