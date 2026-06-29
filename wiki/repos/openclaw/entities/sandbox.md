---
type: entity
repo: openclaw
slug: sandbox
problem: "如何为 agent 工具执行提供隔离的沙箱环境，同时保持文件系统和命令执行对 agent 透明？"
generated: 2026-06-25
source_files:
  - src/agents/sandbox/
---

# Sandbox

**代码位置**：`src/agents/sandbox/`
**这个模块解决什么问题**：
- 实现层：通过可插拔后端（Docker/SSH）+ 文件系统桥（fs-bridge）将工具执行透明路由到隔离容器，agent 无需感知沙箱存在
- 问题层：如何为 agent 工具执行提供隔离的沙箱环境，同时保持文件系统和命令执行对 agent 透明？
**对外暴露什么**：
- `resolveSandboxContext(params)` — 解析沙箱上下文并启动容器 ^[src/agents/sandbox/context.ts]
- `registerSandboxBackend(id, registration)` — 注册沙箱后端 ^[src/agents/sandbox/backend.ts]
- `SandboxBackendFactory` / `SandboxBackendHandle` — 后端接口（buildExecSpec, finalizeExec, env, updateResourceLimits） ^[src/agents/sandbox/backend.ts]
- `SandboxConfig` — 沙箱配置（mode, backend, scope, workspaceAccess, docker, ssh, browser, tools, prune） ^[src/agents/sandbox/types.ts]
- `SandboxContext` — 运行时上下文（enabled, backendId, containerName, workspaceDir, fsBridge, browser） ^[src/agents/sandbox/types.ts]
- `SandboxFsBridge` — 文件系统桥接口（readFile, writeFile, stat, rename, glob） ^[src/agents/sandbox/fs-bridge.ts]
- `buildSandboxCreateArgs(options)` — Docker 容器创建参数 ^[src/agents/sandbox/docker.ts]
**它和谁交互**：
- 依赖 [[entities/tool-system]]（read/write/edit/exec 工具适配到沙箱文件系统和命令执行）
- 依赖 [[entities/skills]]（技能同步到沙箱工作区）
- 依赖 [[entities/config-system]]（沙箱配置段）
- 被 [[entities/agent-runtime]] 在启动时解析沙箱上下文
**为什么它是可分离的**：通过后端注册表 + fs-bridge 抽象实现工具执行与沙箱后端的完全解耦

**关键机制**（源码可见）：
- 后端注册表：`registerSandboxBackend(id, registration)`，内置 docker 和 ssh 两个后端 ^[src/agents/sandbox/backend.ts]
- 沙箱模式：`off`（禁用）| `non-main`（仅非主 agent）| `all`（全部） ^[src/agents/sandbox/types.ts]
- 工作区访问：`none` | `ro`（只读）| `rw`（读写），决定宿主机文件是否可见 ^[src/agents/sandbox/types.ts]
- 作用域：`session`（每会话独立容器）| `agent`（每 agent）| `shared`（共享） ^[src/agents/sandbox/types.ts]
- Docker 创建参数：image + user + binds + working dir + network + resource limits ^[src/agents/sandbox/docker.ts]
- SSH 后端：`createSshSandboxSessionFromConfigText` → `runSshSandboxCommand` → 文件上传 ^[src/agents/sandbox/ssh.ts]
- 文件系统桥：将宿主路径翻译为容器路径，文件操作通过容器命令执行 ^[src/agents/sandbox/fs-bridge.ts]
- 浏览器沙箱：可选启动浏览器 Docker 容器，通过 CDP/VNC/NoVNC 端口暴露 ^[src/agents/sandbox/browser.ts]

**源码证据**：
- 沙箱上下文：src/agents/sandbox/context.ts
- 后端注册表：src/agents/sandbox/backend.ts
- 配置类型：src/agents/sandbox/types.ts
- Docker 实现：src/agents/sandbox/docker.ts
- SSH 实现：src/agents/sandbox/ssh.ts
- 文件系统桥：src/agents/sandbox/fs-bridge.ts

**关联 Concept**：
- [[concepts/execution-isolation]]
