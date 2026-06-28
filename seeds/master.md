# Master Seed Bank

所有待观察（C 类）问题空间条目的聚合库。等待其他仓库 ingest 后向 Concept 页升级。

---

## 来自 nanobot（2026-06-25）

| # | 问题名 | 层级 | 来源 Entity | 情况 |
|---|--------|------|-------------|------|
| 1 | 如何编排 Agent 的主循环 | 架构决策 | agent-loop | B → agent-loop-orchestration |
| 2 | 如何实现与产品逻辑解耦的通用 tool-use LLM 执行循环 | 架构决策 | agent-runner | B → agent-loop-orchestration, context-compression-strategy |
| 3 | 如何组装 Agent 的系统提示词 | 架构决策 | context-builder | B → system-prompt-assembly |
| 4 | 如何管理 Agent 的长期记忆 | 架构决策 | memory-system | B → memory-management-architecture |
| 5 | 如何管理 Agent 工具的生命周期 | 架构决策 | tool-registry | B → tool-lifecycle-management |
| 6 | 如何解耦 Channel 和 Agent Core 的消息传递 | 架构决策 | message-bus | D（演化信号，粒度不匹配） |
| 7 | 如何让 Agent 同时支持多个聊天平台 | 架构决策 | channel-system | B → channel-abstraction-pattern |
| 8 | 如何抽象 LLM 提供商的差异 | 架构决策 | provider-system | B → provider-abstraction-pattern |
| 9 | 如何在 Agent 对话流中嵌入内置命令 | 架构决策 | command-router | C（待观察，仅 nanobot 有此设计） |
| 10 | 如何为 Agent 提供定时任务调度 | 架构决策 | cron-service | B → autonomous-scheduling |
| 11 | 如何让 Agent 具备自主唤醒能力 | 架构决策 | heartbeat-service | B → autonomous-scheduling |
| 12 | 如何持久化管理 Agent 的多会话对话历史 | 架构决策 | session-manager | B → session-lifecycle-management |
| 13 | 如何管理 Agent 的可插拔能力模块 | 架构决策 | skills-loader | B → skills-extension-mechanism |
| 14 | 如何让主 Agent 委托后台子 Agent 执行复杂任务 | 架构决策 | subagent-manager | B → subagent-orchestration |
| 15 | 如何保护 Agent 的 Web/Shell 工具安全 | 架构决策 | security-system | B → security-architecture |

## 来自 openclaw（2026-06-25）

| # | 问题名 | 层级 | 来源 Entity | 情况 |
|---|--------|------|-------------|------|
| 1 | 中央控制平面：单端口统一 HTTP/WebSocket | 架构决策 | gateway | C（channel-abstraction-pattern 子维度） |
| 2 | Agent 执行循环：provider 无关+流式+压缩+故障切换 | 架构决策 | agent-runtime | B → agent-loop-orchestration, context-compression-strategy |
| 3 | 插件公共契约：core↔plugin 稳定边界 | 架构决策 | plugin-sdk | C（仅 openclaw） |
| 4 | 渠道抽象：统一接口覆盖 25+ 平台 | 架构决策 | channel-system | B → channel-abstraction-pattern |
| 5 | 插件全生命周期：发现-加载-验证-管理 | 架构决策 | plugin-system | C（tool-lifecycle-management 子维度） |
| 6 | 多层工具策略管道：9 层优先级 | 架构决策 | tool-system | B → tool-lifecycle-management |
| 7 | 子 Agent 生命周期：孵化-跟踪-完成-恢复 | 架构决策 | subagent-system | B → subagent-orchestration |
| 8 | 模型管理：多 provider 配置-认证-故障切换 | 技术选型 | model-configuration | B → provider-abstraction-pattern |
| 9 | 会话持久化：本地文件系统+写锁+磁盘预算 | 架构决策 | session-system | B → session-lifecycle-management |
| 10 | 模块化配置：$include + ${ENV} + Zod 验证 | 技术选型 | config-system | B → configuration-management |
| 11 | CLI 架构：双层路由实现快速响应 | 技术选型 | cli-system | C（仅 openclaw） |
| 12 | 跨平台服务管理：launchd/systemd/schtasks | 技术选型 | daemon | C（仅 openclaw） |
| 13 | 消息路由：9 级优先级+DM scope | 架构决策 | routing-system | C（session-lifecycle-management 子维度） |
| 14 | 执行隔离：可插拔沙箱后端 Docker/SSH | 架构决策 | sandbox | B → execution-isolation |
| 15 | 技能管理：多源加载+过滤+安装+提示注入 | 架构决策 | skills | B → skills-extension-mechanism |
| 16 | 媒体管道：安全处理多媒体+SSRF 保护 | 技术选型 | media-pipeline | C（仅 openclaw） |
| 17 | 事件驱动扩展点：钩子发现-过滤-隔离 | 架构决策 | hooks-system | D（粒度不匹配，演化信号） |
| 18 | 执行审批流程：异步+超时+反重放 | 架构决策 | approval-system | B → execution-approval-pattern |
| 19 | 多层安全防御：四维审计+策略执行 | 架构决策 | security-system | B → security-architecture |
| 20 | 定时任务调度：cron→心跳注入→agent 管理 | 技术选型 | cron-system | B → autonomous-scheduling |

## 来自 hermes-agent（2026-06-25）

| # | 问题名 | 层级 | 来源 Entity | 情况 |
|---|--------|------|-------------|------|
| 1 | 如何编排 Agent 的主循环 | 架构决策 | agent-core | B → agent-loop-orchestration |
| 2 | 如何管理对话上下文窗口 | 架构决策 | context-compressor | B → context-compression-strategy |
| 3 | 如何将不同通讯平台的消息路由到统一 Agent | 架构决策 | platform-adapters, gateway-runner | B → channel-abstraction-pattern |
| 4 | 如何实现跨会话的身份和状态管理 | 架构决策 | session-manager | B → session-lifecycle-management |
| 5 | 如何管理工具的安全执行 | 架构决策 | security-sandbox | B → security-architecture |
| 6 | 如何持久化会话并支持跨会话检索 | 架构决策 | state-database | C（session-lifecycle-management 子维度） |
| 7 | 如何管理系统提示词的复杂性 | 架构决策 | prompt-builder | B → system-prompt-assembly |
| 8 | 如何让 Agent 从经验中学习 | 架构决策 | skills-system, memory-system | B → skills-extension-mechanism, memory-management-architecture |
| 9 | 如何抽象多种 AI Provider | 技术选型 | model-adapters, provider-registry | B → provider-abstraction-pattern |
| 10 | 如何实现可扩展的远程执行环境 | 技术选型 | terminal-execution | B → execution-isolation |
| 11 | 如何扩展 Agent 的功能 | 技术选型 | tool-registry, mcp-integration | B → tool-lifecycle-management |
| 12 | 如何将多个子任务并行化 | 技术选型 | delegate-subagent | B → subagent-orchestration |
| 13 | 如何管理配置和 Profile | 技术选型 | config-system | B → configuration-management |
| 14 | 如何实现定时自主任务 | 技术选型 | cron-scheduler | B → autonomous-scheduling |
