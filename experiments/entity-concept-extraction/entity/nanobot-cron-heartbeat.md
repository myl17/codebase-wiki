# Cron + Heartbeat（nanobot）

## 是什么 / 边界
nanobot 的调度子系统——Cron 提供三种定时触发方式（at/every/cron expression），Heartbeat 通过单工具 LLM 调用实现定期唤醒。两者均通过 bus.publish_inbound() 将触发消息注入 AgentLoop 的入站队列，与 IM 消息共享处理路径。

**边界**：Cron + Heartbeat 只负责定时触发和唤醒。不负责任务的实际执行（AgentLoop/AgentRunner）、不负责任务结果处理。

## 关键实现
- **Cron 三种调度类型**：
  - `at` — 一次性定时任务
  - `every` — 间隔重复任务
  - `cron` — cron 表达式调度
- **CronStore 持久化**：使用 `FileLock` 做文件级锁，防止多进程环境下同一任务被重复执行
- **Heartbeat 唤醒机制**：HeartbeatService 发起一个专用的单工具 LLM 调用——工具仅支持 `skip`/`run` 两个枚举值。agent 查看活跃任务，若需要执行则返回 `run`，否则 `skip`
- **统一触发路径**：Cron 到达时间后 `bus.publish_inbound()` 注入消息，Heartbeat 返回 `run` 后同样注入——与 Telegram 消息走相同的 AgentLoop 处理路径

## 设计选择记录
- **维度**：Architecture
- **选择**：Heartbeat 使用单工具 LLM 调用做定期唤醒——LLM 收到只有 skip/run 的 heartbeat tool，主动判断是否有任务需要执行
- **替代方案**：纯定时器轮询（不用 LLM，直接检查任务队列），或外部调度器（如系统 crontab、Kubernetes CronJob）
- **为什么有这个选择**：Heartbeat 让 LLM 参与唤醒决策——agent 可以基于上下文（最近的对话、活跃的长期任务、memory 中的提醒）决定是否执行，而非简单的时间驱动。这给了 agent 一定的「主动意识」。Cron 则覆盖确定性的时间驱动场景。两者互补
