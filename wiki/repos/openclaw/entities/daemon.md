---
type: entity
repo: openclaw
slug: daemon
problem: "如何跨平台（macOS launchd / Linux systemd / Windows schtasks）管理网关进程的系统级服务生命周期？"
generated: 2026-06-25
source_files:
  - src/daemon/
---

# Daemon

**代码位置**：`src/daemon/`
**这个模块解决什么问题**：
- 实现层：通过 `GatewayService` 接口统一 stage/install/uninstall/stop/restart/read 操作，按 `process.platform` 选择 launchd/systemd/schtasks 实现
- 问题层：如何跨平台（macOS launchd / Linux systemd / Windows schtasks）管理网关进程的系统级服务生命周期？
**对外暴露什么**：
- `GatewayService` 接口 — 平台无关的服务生命周期契约 ^[src/daemon/service-types.ts]
- `startGatewayService(args)` — 启动服务（先检查安装状态，未安装返回 `"missing-install"`） ^[src/daemon/service.ts]
- `GATEWAY_SERVICE_REGISTRY` — 平台实现查找表：darwin→launchd, linux→systemd, win32→schtasks ^[src/daemon/service.ts]
- `GatewayServiceEnv` / `GatewayServiceState` / `GatewayServiceRestartResult` — 配置和状态类型 ^[src/daemon/service-types.ts]
- `resolveGatewayService()` — 根据 platform 选择实现 ^[src/daemon/service.ts]
- 平台常量：`GATEWAY_LAUNCH_AGENT_LABEL = "ai.openclaw.gateway"` ^[src/daemon/constants.ts]
**它和谁交互**：
- 依赖 [[entities/gateway]]（管理其进程生命周期）
- 依赖 [[entities/config-system]]（读取服务配置路径）
- 被 [[entities/cli-system]] 管理（daemon 命令组）
**为什么它是可分离的**：独立的平台抽象层，通过接口统一三个完全不同的 OS 服务管理器

**关键机制**（源码可见）：
- 统一服务契约：`stage` → `install` → `start/stop/restart` → `uninstall` → `readCommand/readRuntime` ^[src/daemon/service-types.ts]
- macOS/launchd：plist 写入 `~/Library/LaunchAgents/`，`launchctl bootstrap/kickstart/bootout` ^[src/daemon/launchd.ts]
- Linux/systemd：`systemd --user` 单元文件，`systemctl --user enable/start/stop` ^[src/daemon/systemd.ts]
- Windows/schtasks：XML 任务定义，`schtasks.exe /create/delete/run/end` ^[src/daemon/schtasks.ts]
- 自重启 safe handoff：launchd 重启时通过 `scheduleDetachedLaunchdRestartHandoff` 避免自杀 ^[src/daemon/launchd.ts]
- 服务安装：`installLaunchAgent` / `installSystemdService` / `installScheduledTask`，含 env 注入和启动配置

**源码证据**：
- 服务接口：src/daemon/service.ts
- 类型定义：src/daemon/service-types.ts
- launchd 实现：src/daemon/launchd.ts
- systemd 实现：src/daemon/systemd.ts
- schtasks 实现：src/daemon/schtasks.ts
- 常量：src/daemon/constants.ts
