# openclaw — Multi-channel AI gateway with extensible messaging integrations

OpenClaw 是一个个人 AI 助手运行时，运行在你的设备上，通过你已在使用的消息渠道（WhatsApp, Telegram, Slack, Discord 等 25+ 渠道）与你交互。Gateway 是控制平面——核心产品是助手本身。

核心设计哲学：**插件架构 + 渠道抽象 + 模型无关的 agent loop**。Core 保持精简，可选能力以插件形式发布。渠道通过统一的 adapter 接口抽象，同一 agent 可同时服务所有渠道。

## 核心子系统

- [[repos/openclaw/entities/gateway]] — HTTP/WebSocket 控制平面，路由所有客户端请求
- [[repos/openclaw/entities/plugin-sdk]] — 插件与 core 之间的公共契约边界
- [[repos/openclaw/entities/agent-runtime]] — 核心 AI agent 执行循环（PI Embedded），与模型无关
- [[repos/openclaw/entities/channel-system]] — 消息渠道抽象层，25+ adapter 的统一接口
- [[repos/openclaw/entities/plugin-system]] — 插件发现、加载、注册、生命周期管理
- [[repos/openclaw/entities/tool-system]] — Agent 工具目录、策略管道、按需组装与交付
- [[repos/openclaw/entities/subagent-system]] — 子 agent 孵化、跟踪、生命周期、孤立恢复
- [[repos/openclaw/entities/model-configuration]] — 模型/Provider 配置、认证、故障切换链
- [[repos/openclaw/entities/session-system]] — 会话生命周期、存储、转录、磁盘预算
- [[repos/openclaw/entities/config-system]] — 配置加载（JSON5 + $include + ${ENV}）、验证、运行时默认值
- [[repos/openclaw/entities/cli-system]] — 命令行界面，40+ 子命令
- [[repos/openclaw/entities/daemon]] — 系统服务管理（launchd/systemd/schtasks）
- [[repos/openclaw/entities/routing-system]] — 渠道到会话的消息路由与绑定
- [[repos/openclaw/entities/sandbox]] — 工具执行沙箱（Docker/SSH 后端，可插拔）
- [[repos/openclaw/entities/skills]] — 技能安装、工作区管理、系统提示注入
- [[repos/openclaw/entities/media-pipeline]] — 媒体摄取、MIME 检测、图像优化（sharp/sips）
- [[repos/openclaw/entities/hooks-system]] — Agent 生命周期钩子，事件驱动扩展点
- [[repos/openclaw/entities/cron-system]] — 定时任务调度与触发
- [[repos/openclaw/entities/approval-system]] — 执行审批工作流，超时 + 决策
- [[repos/openclaw/entities/security-system]] — 安全策略、allowlist/denylist、SSRF 保护

## 明确不做什么

- 不内建 MCP 运行时（通过 mcporter 桥接）
- 不维护与 wikilink 重复的结构化图谱数据
- 不对特定渠道/provider 做 core 级别的硬编码特殊处理
- 不在 core 中硬编码 bundled plugin 列表
