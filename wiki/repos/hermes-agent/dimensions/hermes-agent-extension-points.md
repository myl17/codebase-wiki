---
repo: hermes-agent
dimension: extension-points
dimensions_version: v1.0
generated: 2026-06-09
---

# Hermes Agent — Extension Points

Hermes Agent 的插件系统提供九大扩展机制，覆盖从最低层工具注入到最高层平台适配的全频谱。

## 1. Tool Registry — 工具自动发现与动态注册

**入口文件**: `tools/registry.py:176-199`  
**发现机制**: AST 扫描 `registry.register()` 顶层调用 ^[tools/registry.py:28-73]

任何 Python 文件只需在模块顶层调用 `registry.register()` 即可注册新工具，无需手动配置：

```python
# tools/my_new_tool.py
from tools.registry import registry

registry.register(
    name="my_tool",
    toolset="custom",
    schema={...},       # OpenAI function-calling schema
    handler=my_handler,  # Callable
    check_fn=lambda: True,  # 可用性检查
    emoji="🔧",
    description="My custom tool",
)
```

`model_tools.py` 自动导入所有自注册工具模块 ^[model_tools.py:1-80]。Registry 线程安全（RLock），支持 MCP-to-MCP 覆盖（server 刷新时工具名冲突）^[tools/registry.py:190-199]。

## 2. Toolset System — 可组合工具分组

**入口文件**: `toolsets.py:68-397`

| 机制                       | 说明                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------ |
| **Leaf toolsets**        | 每个 toolset 是工具名列表 + `includes` 引用其他 toolsets                                         |
| **Composition**          | `resolve_toolset()` 递归解析 `includes` 链，带去重和循环检测 ^[toolsets.py:447-497]                |
| **`_HERMES_CORE_TOOLS`** | 共享核心工具清单，编辑一次即可更新所有平台 ^[toolsets.py:31-63]                                           |
| **Platform toolsets**    | 20+ 平台各自定义 `hermes-<platform>` toolset，均继承核心工具                                       |
| **Custom at runtime**    | `create_custom_toolset("my_custom", ...)` — CLI 或 Agent 运行时创建 ^[toolsets.py:613-632] |
| **Plugin toolset**       | `_get_plugin_toolset_names()` 动态发现 registry 中的非静态 toolset ^[toolsets.py:519-533]     |
| **Special aliases**      | `all` / `*` 解析为所有已注册工具的并集 ^[toolsets.py:466-472]                                     |

**最简单的自定义方式**: 编辑 `_HERMES_CORE_TOOLS` 列表，所有平台自动获得新工具。

## 3. Memory Providers — 记忆插件系统

**入口文件**: `agent/memory_provider.py:42-232`  
**编排器**: `agent/memory_manager.py`

抽象基类定义完整生命周期 ^[agent/memory_provider.py:42-232]：

```python
class MemoryProvider(ABC):
    # 核心生命周期（必须实现）
    name: str                             # 标识符
    is_available() -> bool                # 配置和凭据检查
    initialize(session_id, **kwargs)      # 会话级初始化
    get_tool_schemas() -> List[dict]      # 暴露工具的 OpenAI schema

    # 数据流
    prefetch(query) -> str                # 回溯相关记忆（每次调用前）
    sync_turn(user, asst)                 # 每轮后持久化
    system_prompt_block() -> str          # 静态 prompt 注入
    handle_tool_call(name, args) -> str   # 工具调用分发

    # 可选 hooks（15+ 生命周期回调）
    on_turn_start(turn, message, **kwargs)  # 每个 turn 开始时
    on_session_end(messages)               # 会话结束时
    on_pre_compress(messages) -> str       # 上下文压缩前提取信息
    on_delegation(task, result, ...)        # 子 agent 完成时观察
    on_memory_write(action, target, content)  # 内置记忆写入镜像
    get_config_schema() -> List[dict]       # setup wizard 配置表单
    save_config(values, hermes_home)        # 非密文配置持久化
    shutdown()                             # 干净退出
```

**已捆绑 7 种 provider**: `plugins/memory/{honcho, mem0, supermemory, hindsight, holographic, byterover, retaindb}` ^[plugins/memory/]

**约束**: 最多 1 个外部 provider。BuiltinMemoryProvider 始终启用且不可移除 ^[agent/memory_manager.py:1-27]。外部 provider 是加性的（additive），不会禁用内置存储。

**激活方式**: `config.yaml` 中 `memory.provider: "honcho"`

## 4. Context Engines — 上下文压缩策略

**入口文件**: `agent/context_engine.py:32-60`

```python
class ContextEngine(ABC):
    name: str
    threshold_percent: float = 0.75
    protect_first_n: int = 3
    last_prompt_tokens / last_completion_tokens / last_total_tokens
    threshold_tokens / context_length / compression_count

    on_session_start()
    update_from_response(usage_data)   # 每个 API 响应后更新 token 使用量
    should_compress() -> bool          # 判断是否应触发压缩
    compress(messages) -> List         # 执行压缩（摘要/DAG/等）
    on_session_end()
    get_tools() -> List[dict]          # 可选的附加工具（如 lcm_grep）
```

**激活方式**: `config.yaml` 中 `context.engine: "lcm"`  
**内置默认**: `ContextCompressor` (summary-based 压缩)  
**第三方**: 放入 `plugins/context_engine/<name>/` 目录，通过配置选择。同一时间只有一个 engine 激活 ^[agent/context_engine.py:5-17]

## 5. MCP (Model Context Protocol) Integration

**入口文件**: `tools/mcp_tool.py`

外部 MCP server 的工具通过 `~/.hermes/config.yaml` 的 `mcp_servers` 键自动发现和注入 ^[tools/mcp_tool.py:15-43]：

```yaml
mcp_servers:
  filesystem:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
  remote:
    url: "https://my-mcp-server.example.com/mcp"
    headers:
      Authorization: "Bearer sk-..."
```

| 特性 | 说明 |
|---|---|
| **Stdio transport** | 子进程通信，自动重连（指数退避，最多 5 次） |
| **HTTP/StreamableHTTP** | 远程 MCP server |
| **Sampling 支持** | MCP server 可发起 LLM 请求（`sampling/createMessage`） |
| **线程安全** | 独立后台 event loop 运行在 daemon 线程中 |
| **凭据脱敏** | 返回给 LLM 的错误消息中自动剥离凭据 |

## 6. Platform Adapters — 消息平台适配器

**入口文件**: `gateway/platforms/base.py:813-893`  
**完整指南**: `gateway/platforms/ADDING_A_PLATFORM.md` — 16 步 checklist

```python
class BasePlatformAdapter(ABC):
    # 必须实现
    connect() -> bool
    disconnect()
    send(chat_id, text, ...) -> SendResult
    send_typing(chat_id)
    send_image(chat_id, image_url, caption)
    get_chat_info(chat_id) -> dict

    # 可选覆盖
    send_document()  send_voice()  send_video()  send_animation()
```

**已实现 22 平台**: Telegram, Discord, Slack, WhatsApp, Signal, Matrix, BlueBubbles (iMessage), HomeAssistant, Email, SMS, Mattermost, DingTalk, Feishu, WeCom, WeCom-Callback, Weixin, QQBot, Webhook, API Server ^[gateway/platforms/]

**新增平台需修改 16 处** — 覆盖 adapter 本身、enum、factory、auth maps、session source、system prompt hints、toolset、cron delivery、send_message tool、channel directory、status display、gateway setup wizard、redaction、docs、tests ^[gateway/platforms/ADDING_A_PLATFORM.md:1-313]

## 7. Event Hooks — 生命周期事件系统

**入口文件**: `gateway/hooks.py:1-139`

| 事件 | 触发时机 |
|---|---|
| `gateway:startup` | 网关进程启动 |
| `session:start` | 新会话创建 |
| `session:end` | 会话结束（/new 或 /reset） |
| `session:reset` | 会话重置完成 |
| `agent:start` | Agent 开始处理消息 |
| `agent:step` | Tool-calling 循环的每一轮 |
| `agent:end` | Agent 完成处理 |
| `command:*` | 任意 slash 命令执行（通配符匹配） |

- **目录扫描加载**: `~/.hermes/hooks/<name>/HOOK.yaml` + `handler.py`，handler 中实现 `async def handle(event_type, context)` ^[gateway/hooks.py:80-136]
- **内置 hook**: `boot-md` — 网关启动时执行 `~/.hermes/BOOT.md` ^[gateway/hooks.py:54-67]
- **错误隔离**: hook 中的异常被捕获并记录，不阻塞主 pipeline ^[gateway/hooks.py:18-19]

## 8. Skills — 可安装技能

**标准**: [agentskills.io](https://agentskills.io) 开放标准 — 与 Claude Code / Codex CLI 互操作 ^[tools/skills_tool.py] ^[tools/skills_hub.py]

| 阶段 | 组件 |
|---|---|
| **下载** | Skill Hub registry → `skills/.hub/quarantine/` |
| **安全扫描** | `skills_guard.py` — 100+ 威胁模式 × 3 级信任策略 ^[tools/skills_guard.py:82-484] |
| **安装** | 通过扫描后安装到 `skills/<skill-name>/` |
| **自我改进** | Skill 在使用中可通过 `skill_manage` 工具更新 |
| **同步** | 每次 CLI 启动 `sync_skills()` 自动同步捆绑 skills（跳过未更改的）^[hermes_cli/main.py:743-747] |

## 9. ACP Adapter — 编辑器集成

**入口文件**: `acp_adapter/`  
**协议**: [Agent Communication Protocol](https://agentcommunicationprotocol.dev/)  
**支持编辑器**: VS Code, Zed, JetBrains  
**专用 toolset**: `hermes-acp` — 编码专用工具，无消息/音频/clarify UI ^[toolsets.py:226-243]

---

## 扩展难度梯度

| 扩展类型 | 难度 | 最快路径 |
|---|---|---|
| 添加单个工具 | 低 | 创建 `tools/my_tool.py`，调用 `registry.register()` |
| 自定义 toolset | 低 | `_HERMES_CORE_TOOLS` 加一行，所有平台自动获得 |
| 运行时 toolset | 低 | `create_custom_toolset()` |
| 自定义 event hook | 低 | 创建 `~/.hermes/hooks/<name>/HOOK.yaml` + `handler.py` |
| MCP server 连接 | 低 | 编辑 `config.yaml` 的 `mcp_servers` |
| 安装外部 skill | 低 | `/skill install <url>`（经 `skills_guard` 扫描） |
| 自定义 memory provider | 中 | 实现 `MemoryProvider` ABC，放 `plugins/memory/<name>/` |
| 自定义 context engine | 中 | 实现 `ContextEngine` ABC，放 `plugins/context_engine/<name>/` |
| 新增平台适配器 | 中-高 | 按 `ADDING_A_PLATFORM.md` 16 步 checklist |

## 关联

- [[openclaw/dimensions/openclaw-extension-points]]
