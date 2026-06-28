---
type: concept
concept: configuration-management
problem: 如何管理 Agent 框架的运行时配置，支持多环境隔离、配置模块化和安全值注入
concerns: [配置源可组合性, 多环境/Profile 隔离强度, Schema 验证与演化]
repos: [nanobot, hermes-agent, openclaw]
generated: 2026-06-25
---

# 配置管理

## 核心问题

构建 AI Agent 框架时，配置系统是第一个被触碰的模块——模型选择、API Key、工具开关、平台凭证、运行策略，每一项都需要可配置且不能硬编码。但"怎么配置"本身就是一个需要权衡的架构决策。

根本张力在于**配置的模块化程度与加载复杂度的权衡**：把配置拆成多个文件可以独立管理但需要 include 机制和循环检测；合并为单文件则简单但对数百项配置不可维护。另一个张力在于**隔离强度与便利性**：完全隔离的多环境（profiles）可以解决配置冲突，但要求用户管理多套配置的差异。三个框架给出了三种答案：nanobot 用 Pydantic 环境变量映射实现扁平分层，hermes-agent 用文件系统级 profile 隔离提供最强环境分离，openclaw 用 JSON5 include 指令实现任意深度的模块化组合。

第三个张力在于**类型安全与灵活性的平衡**：用强类型 schema（Zod/Pydantic）可以在启动时就捕获配置错误但增加维护成本，用 `extra` 字典允许任意扩展字段则灵活但运行时才能发现拼写错误。三个框架在验证严格度上逐步递进：nanobot 做基础校验，hermes-agent 用 dataclass + 18 种平台枚举约束，openclaw 用 30+ 个 Zod schema 文件分层验证并允许插件贡献额外的约束。

## 关切

- **配置源可组合性**：配置来自文件、环境变量、CLI 参数、远程存储等多个来源，它们的优先级、合并策略和引用解析决定了配置的可靠性和可调试性
- **多环境/Profile 隔离强度**：开发/测试/生产或不同项目的配置隔离可以是文件级（不同目录）、也可以是环境级（env vars），隔离强度直接影响配置冲突风险和用户体验
- **Schema 验证与演化**：配置 schema 随版本演化的兼容性保证——新增字段是否能自动补默认值、废弃字段是否有迁移路径、插件的自定义配置是否可以注册字段类型

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/config-system]]
**解法**：Pydantic BaseSettings 驱动的单文件 JSON5 配置 + 环境变量扁平映射覆盖，provide 自动匹配模型到 provider。
**实现**：
- 环境变量嵌套映射：`NANOBOT_AGENTS__DEFAULTS__MODEL` 用 `__` 做层级分隔映射到 `agents.defaults.model`，比多层扁平 key 更直观 ^[nanobot/config/schema.py:313]
- Provider 自动匹配：`_match_provider()` 按 provider 前缀直接匹配 > model 关键词匹配 > 本地 fallback 三优先级，无有效 API key 时自动跳过 ^[nanobot/config/schema.py:218-281]
- JSON5 文件格式：允许注释和尾部逗号，增加人工可编辑性。Pydantic 校验在加载后执行基础类型检查 ^[nanobot/config/loader.py]
**权衡**：环境变量路径式映射直观且不需要 include 机制，但没有 profile 隔离能力。Provider 自动匹配简化了多模型切换但规则是硬编码的（model 关键词如 `grok` → xai），新增 provider 需改源码。

### hermes-agent
来源：[[repos/hermes-agent/entities/config-system]]
**解法**：文件系统级 profile 隔离——HERMES_HOME 环境变量指向 profile 目录，每个 profile 拥有独立的 home/ 子目录隔离子进程配置。
**实现**：
- Profile 级文件系统隔离：`HERMES_HOME` 指向 `~/.hermes/profiles/<name>/`，每个 profile 有独立的 `config.yaml`、`home/` 目录（隔离 git/ssh/gh 等子进程配置），通过 `PER_PROFILE_DIRS` 决定哪些目录是 per-profile ^[hermes_constants.py:11-18]
- 二十三层配置优先级：环境变量 > config.yaml > 代码默认值，`${VAR}` 引用在 YAML 加载后展开；`GatewayConfig` 以 dataclass 承载 18 种平台枚举 + 三层重置策略 ^[hermes_cli/config.py]
- Subprocess HOME 隔离：`get_subprocess_home()` 返回 profile-scoped 的 `home/` 目录作为子进程 HOME，彻底解决不同 profile 间 git/ssh 密钥冲突 ^[hermes_constants.py:114-137]
**权衡**：文件系统级隔离提供了最强的环境分离（每个 profile 连 git/ssh 配置都独立），但要求用户理解 profile 概念和管理生命周期。23 层配置优先级带来了灵活性但调试"某值从哪来"的难度增加。

### openclaw
来源：[[repos/openclaw/entities/config-system]]
**解法**：JSON5 配置 + `$include` 递归模块化 + `${ENV}` 动态替换 + 固定顺序默认值填充 + Zod schema 分层验证。
**实现**：
- `$include` 模块化指令：单文件或数组形式引用，最多 10 层嵌套、2MB 单文件限制、循环引用检测——在灵活性和安全性间取得平衡 ^[src/config/includes.ts]
- 固定顺序默认值填充：`materializeRuntimeConfig()` 按 message→logging→session→agent→context pruning→compaction→model 的严格顺序填充默认值，后面默认值可能依赖前面的值 ^[src/config/materialize.ts]
- Zod schema 分层验证：30+ 个 `zod-schema.*.ts` 文件每个领域独立验证，插件通过 `configSchema` 贡献额外 schema，`validateConfigObjectWithPlugins()` 合并所有 schema 统一验证 ^[src/config/validation.ts]
- 运维机制：配置审计日志自动记录读写、备份轮转防止写坏、JSON5 格式支持注释 ^[src/config/io.audit.ts]
**权衡**：$include 模块化最灵活，但 10 层深度和循环检测带来的复杂度要求更严格的边界保护。30+ Zod schema 文件提供了编译时的类型安全但增加了 schema 维护成本。

## 对比

| 框架 | 配置源可组合性 | 多环境/Profile 隔离强度 | Schema 验证与演化 |
|------|------|------|------|
| nanobot | 单文件 JSON5 + env vars `__` 嵌套映射，无 include 机制 | 无 profile 支持；多环境需手动管理多个配置文件 | Pydantic BaseSettings 基础校验；无插件 schema 扩展 |
| hermes-agent | config.yaml + 23 层优先级 + `${VAR}` 引用展开 | 文件系统级 profile 隔离，每个 profile 有独立 home/ 目录隔离 git/ssh/gh | dataclass + 18 种 Platform enum 约束；`extra` 字典支持扩展字段；无版本化迁移 |
| openclaw | JSON5 + `$include` 递归模块化 + `${ENV}` + 固定顺序默认值填充 | 无 profile 概念；通过 `$include` 和 `${ENV}` 实现环境区分 | 30+ Zod schema 分层验证 + 插件 schema 贡献；审计日志追踪配置变更；备份轮转 |

## 演化记录

- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
