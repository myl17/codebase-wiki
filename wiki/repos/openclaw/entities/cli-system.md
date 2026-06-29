---
type: entity
repo: openclaw
slug: cli-system
problem: "如何组织 40+ 个子命令的 CLI 程序，使常用查询命令能绕过完整 Commander 解析实现快速响应？"
generated: 2026-06-25
source_files:
  - src/cli/
---

# CLI System

**代码位置**：`src/cli/`
**这个模块解决什么问题**：
- 实现层：双层路由架构——快速路径（路由表旁路 Commander）处理 status/health/sessions 等查询 + 完整 Commander 程序处理复杂命令
- 问题层：如何组织 40+ 个子命令的 CLI 程序，使常用查询命令能绕过完整 Commander 解析实现快速响应？
**对外暴露什么**：
- `runCli()` — CLI 主入口 ^[src/cli/run-main.ts]
- `buildProgram()` — 构建完整 Commander 程序 ^[src/cli/program.ts]
- `tryRouteCli(argv)` — 快速路由解析（status, health, sessions, models-list 等 11 个路由 ID） ^[src/cli/route.ts]
- `CliCommandCatalogEntry` — 命令目录声明（commandPath, policy, route?） ^[src/cli/command-catalog.ts]
- `CliArgvInvocation` — 标准化 argv 解析结果 ^[src/cli/argv-invocation.ts]
- `resolveCliArgvInvocation(argv)` — argv 解析 ^[src/cli/argv-invocation.ts]
**它和谁交互**：
- 依赖 [[entities/gateway]]（gateway 命令通过 `openclaw gateway` 直接启动）
- 依赖 [[entities/plugin-system]]（plugin 命令管理插件生命周期）
- 依赖 [[entities/config-system]]（config 命令读写配置）
- 依赖 [[entities/model-configuration]]（models 命令显示目录）
- 依赖 [[entities/daemon]]（daemon 命令管理系统服务）
- 依赖 [[entities/session-system]]（会话相关命令）
- 调用所有其他子系统
**为什么它是可分离的**：独立的 CLI 层，通过 Commander + 路由表实现命令分发

**关键机制**（源码可见）：
- 双层路由：`tryRouteCli()` 先尝试快速路由（旁路 Commander）→ 未命中则 `buildProgram()` 完整解析 ^[src/cli/run-main.ts]
- 路由目录：~30 个命令路径条目，每个定义 `bypassConfigGuard`、`loadPlugins`、`hideBanner` 等策略 ^[src/cli/command-catalog.ts]
- 11 个快速路由 ID：health, status, gateway-status, sessions, agents-list, config-get, config-unset, models-list, models-status, upgrade-check, channels-add ^[src/cli/command-catalog.ts]
- 命令引导策略：`ensureCliCommandBootstrap()` 确保配置已加载，插件注册表已就绪 ^[src/cli/command-bootstrap.ts]
- 插件 CLI 命令延迟注册：`registerPluginCliCommandsFromValidatedConfig()` 将插件贡献的命令注入 Commander ^[src/cli/program.ts]
- 子命令分布：`src/cli/` 下 40+ 个 `*-cli.ts` 文件，每个实现一组子命令

**源码证据**：
- 程序构建：src/cli/program.ts
- 主入口：src/cli/run-main.ts
- 快速路由：src/cli/route.ts
- 命令目录：src/cli/command-catalog.ts
- argv 解析：src/cli/argv-invocation.ts
- 命令引导：src/cli/command-bootstrap.ts
