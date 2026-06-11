---
node_type: Component
scope: subsystem
motivated_by: [startup-over-memory-tradeoff]
sources:
  - src/process/supervisor/index.ts:1-12
---

# ProcessSupervisor

进程看门狗，管理 `ManagedRun` / `SpawnMode` / `RunState` 状态机，负责子进程生命周期和 respawn 策略（含 NODE_OPTIONS 修改后的重新 spawn）。二开接触子进程行为（超时、重启、信号处理）时的关键边界。
^[src/process/supervisor/index.ts:1-12]
