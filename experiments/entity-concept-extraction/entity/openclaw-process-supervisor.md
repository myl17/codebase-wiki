# Process Supervisor（OpenClaw）

## 是什么 / 边界

Process Supervisor 是 OpenClaw 的进程生命周期管理器：作为 CLI 入口负责初始化运行时环境（compile cache、fetch compat、进程标题），通过 respawn 策略在需要时以修改后的 Node.js 参数重启进程，并在运行期管理子进程的生命周期（`ManagedRun` / `SpawnMode` / `RunState`）。不处理 IM 消息，不执行 AI 调用，不做业务逻辑。

## 关键实现

- CLI 入口：`src/entry.ts`（`enableCompileCache()`、gaxios fetch compat、`process.title = "openclaw"`、`isMainModule` 防重复启动）
- Respawn 逻辑：`src/entry.respawn.ts`（`buildCliRespawnPlan`：检测是否需要以修改后的 `NODE_OPTIONS` 或 `NODE_EXTRA_CA_CERTS` 重 spawn；`OPENCLAW_NODE_OPTIONS_READY=1` 防循环 respawn）
- 进程看门狗：`src/process/supervisor/`（单例：`getProcessSupervisor()`，管理 `ManagedRun` / `SpawnMode` / `RunState`）

## 设计选择记录

- **维度**：Performance Tradeoffs
- **选择**：启动时第一步调用 `enableCompileCache()`，将 V8 字节码缓存到磁盘，失败时静默降级
- **替代方案**：不使用 compile cache，每次启动都重新解析 JS
- **为什么有这个选择**：OpenClaw 是一个频繁启动的个人工具，冷启动体验对用户感知影响大；compile cache 可以跳过重复的 JS 解析，静默降级保证兼容性不受影响

---

- **维度**：Performance Tradeoffs
- **选择**：需要修改 `NODE_OPTIONS` 时通过 respawn 重启进程（而非运行时动态修改），代价是冷启动多一次 `spawn()`
- **替代方案**：直接修改进程内的 Node.js 选项（如果可能）
- **为什么有这个选择**：`NODE_OPTIONS` 等环境变量必须在进程启动时设置，无法运行时修改；通过 `OPENCLAW_NODE_OPTIONS_READY=1` 标志确保只 respawn 一次，不进入循环

---

- **维度**：Architecture
- **选择**：Process Supervisor 以单例模式暴露（`getProcessSupervisor()`），全局统一管理子进程
- **替代方案**：各子系统各自管理自己需要的子进程
- **为什么有这个选择**：集中的进程管理使 respawn 策略、状态机（`RunState`）和日志追踪可以统一处理；分散管理会导致进程生命周期难以观测和协调
