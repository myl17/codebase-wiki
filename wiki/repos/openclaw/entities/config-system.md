---
type: entity
repo: openclaw
slug: config-system
problem: "如何加载、合并和验证一个支持模块化 include、环境变量替换和多层默认值的配置系统？"
generated: 2026-06-25
source_files:
  - src/config/
---

# Config System

**代码位置**：`src/config/`
**这个模块解决什么问题**：
- 实现层：JSON5 文件 → `$include` 递归解析 → `${ENV}` 替换 → 运行时默认值按序填充 → Zod schema 验证
- 问题层：如何加载、合并和验证一个支持模块化 include、环境变量替换和多层默认值的配置系统？
**对外暴露什么**：
- `loadConfig()` — 加载配置的主入口 ^[src/config/io.ts]
- `OpenClawConfig` — 顶层配置类型（~30 个可选段：auth, models, agents, gateway, secrets, plugins, hooks, channels, cron, memory 等） ^[src/config/types.openclaw.ts]
- `getRuntimeConfig()` / `getRuntimeConfigSnapshot()` — 获取运行时配置 ^[src/config/config.ts]
- `writeConfigFile()` / `mutateConfigFile()` — 配置写回 ^[src/config/io.ts]
- `resolveConfigIncludes()` — `$include` 指令递归解析（最多 10 层，2MB/include，循环检测） ^[src/config/includes.ts]
- `resolveConfigEnvVars()` — `${VAR_NAME}` 环境变量替换 ^[src/config/env-substitution.ts]
- `materializeRuntimeConfig()` — 运行时默认值填充（mode: load/missing/snapshot） ^[src/config/materialize.ts]
- `validateConfigObjectWithPlugins()` — Zod schema 验证（含插件 schema 贡献） ^[src/config/validation.ts]
- `applyConfigOverrides()` — 运行时覆盖应用 ^[src/config/runtime-overrides.ts]
**它和谁交互**：
- 被所有子系统依赖（配置是全局单点）
- 依赖 [[entities/plugin-system]]（插件贡献的 configSchema）
- 被 [[entities/gateway]] 在启动时加载
- 被 [[entities/cli-system]] 用于 config 命令
**为什么它是可分离的**：完整的配置生命周期（load→merge→validate→write），通过纯函数管道实现

**关键机制**（源码可见）：
- JSON5 文件格式：支持注释、尾随逗号、裸键，比 JSON 更宽松 ^[src/config/io.ts]
- `$include` 指令：单文件或数组形式，最多 10 层嵌套，2MB 限制，循环引用检测 ^[src/config/includes.ts]
- `${ENV_VAR}` 替换：配置值中的环境变量引用自动解析，追踪未解析引用 ^[src/config/env-substitution.ts]
- 默认值填充顺序：message defaults→logging→session→agent→context pruning→compaction→model→talk→path normalization→exec-safe bins ^[src/config/materialize.ts]
- Zod schema 分层：30+ 个 `zod-schema.*.ts` 文件，每个领域独立验证，插件可贡献额外 schema ^[src/config/zod-schema.ts]
- 配置审计日志：读写操作自动记录到 audit log ^[src/config/io.audit.ts]
- 备份轮转：配置写入前自动备份 ^[src/config/backup-rotation.ts]
- 类型文件：30+ `types.*.ts` 文件，每个配置段独立类型定义

**源码证据**：
- I/O 引擎：src/config/io.ts
- 类型定义：src/config/types.openclaw.ts
- Include 解析：src/config/includes.ts
- 环境变量替换：src/config/env-substitution.ts
- 默认值填充：src/config/materialize.ts
- Schema 验证：src/config/validation.ts
- Zod schemas：src/config/zod-schema.ts
- 配置命令：src/cli/config-cli.ts

**关联 Concept**：
- [[concepts/configuration-management]]
