# AgentLoop（nanobot）

## 是什么 / 边界
nanobot 的中央编排器，整个系统的唯一架构入口。`AgentLoop.__init__()` 是一个单体组装函数——在一个构造函数中实例化并注入 provider、bus、context、tools、runner、subagents、consolidator、dream、sessions、cron、heartbeat、MCP 全部子系统。运行时从 bus 消费入站消息 → 分发 → 构建 context → 交给 AgentRunner 执行 → 回写出站。

**边界**：AgentLoop 拥有所有子系统的生命周期和连线逻辑。它不负责 tool-calling 循环（那是 AgentRunner 的职责）、不负责上下文组装（ContextBuilder）、不负责消息收发（Channel/Bus）。

## 关键实现
- **单点组装**：`__init__()` 在 `agent/loop.py:115-228`，所有连线逻辑只存在于这一个文件中——读一个构造函数就能回答「这个系统有什么」
- **消息分发**：`_dispatch()` 做 session-lock + CommandRouter 拦截（/stop 等命令在 LLM 调用前被处理），然后路由到 `_process_message()`
- **agent 执行**：`_run_agent_loop()` 构建 `AgentRunSpec` 纯数据配置，交给 AgentRunner.run()
- **MCP 集成**：`_connect_mcp()` 惰性连接 MCP server，工具以 `mcp_` 前缀动态注册，AsyncExitStack 管理生命周期
- **外部钩子注入**：维护 `_extra_hooks` 列表，允许外部插件运行时注入 AgentHook 而不修改核心代码

## 设计选择记录
- **维度**：Architecture
- **选择**：单体 Hub 集中式组装——所有子系统在一个构造函数中实例化和连线，而非使用 DI 容器或 factory pattern
- **替代方案**：依赖注入容器（如 openclaw 的服务容器模式），将子系统注册和连线分散到各模块
- **为什么有这个选择**：追求极致的可发现性——「这个系统有什么」可以通过读一个文件的一个函数得到完整答案。代价是 AgentLoop 成为单一故障集中点，且子系统无法独立单元测试（因为没有接口注入点）
