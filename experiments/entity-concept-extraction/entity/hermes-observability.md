# 可观测性层（Hermes Agent）

## 是什么 / 边界

可观测性层是横切所有子系统的独立关注点，包含三路旋转日志（含 API key 自动脱敏）、后台进程注册表（ProcessRegistry）、per-session 成本追踪（usage_pricing）和运行时状态管理（gateway/status）。

它的边界：只负责记录和追踪，不介入执行路径，不做决策。脱敏是单向的（日志写入时自动脱敏，无法从日志反推密钥）。

## 关键实现

- 日志系统：`hermes_logging.py:1-391`
  - 三路日志：`agent.log`（主日志，INFO+）、`errors.log`（WARNING+，快速分诊）、`gateway.log`（网关专用）
  - RotatingFileHandler：可配置 max_size_mb（默认 5MB）+ backup_count（默认 3）
  - Session Context 标签注入：`hermes_logging.py:72-119`，LogRecord 注入 `[session_id]`，支持 `hermes logs --session <id>` 过滤
  - Component Filter：按组件前缀路由（gateway/agent/tools/cli/cron）
- API key 脱敏：`agent/redact.py:1-60`，40+ 种 API key 前缀模式，密钥永不写入磁盘
- 后台进程注册表：`tools/process_registry.py:1-60`
  - 200KB 滚动输出缓冲区
  - 已完成进程保留 30 分钟
  - 最大并发跟踪 64 个进程（LRU 淘汰）
  - JSON checkpoint 文件，网关崩溃恢复
- 运行时状态：`gateway/status.py`，PID 文件（`~/.hermes/gateway.pid`）+ 状态 JSON（`~/.hermes/gateway_state.json`）
- 成本追踪：`agent/usage_pricing.py`，`estimate_usage_cost()` + `normalize_usage()`（跨 provider 标准化）
- 诊断工具：`hermes doctor`（配置完整性检查）、`/insights`（会话历史模式分析）

## 设计选择记录

- **维度**：Architecture
- **选择**：40+ API key 前缀模式自动脱敏，日志写入时实时处理，密钥永不落盘
- **替代方案**：日志写入后批量脱敏，或依赖开发者手动避免记录敏感信息
- **为什么有这个选择**：agent 日志会记录所有工具调用参数，不能依赖开发者每处手动脱敏；写入时脱敏是最可靠的，不存在"先写后脱敏"窗口期中日志泄露的风险

---

- **维度**：Architecture
- **选择**：三路日志文件按用途分离（主日志/错误日志/网关日志），支持按 session_id 过滤
- **替代方案**：单一日志文件，所有内容混合输出
- **为什么有这个选择**：多平台 gateway 运行时日志量大，按组件分离让错误排查直接看 errors.log，网关问题看 gateway.log；session_id 标签让跨组件追踪一个用户会话的完整链路成为可能

---

- **维度**：Performance Tradeoffs
- **选择**：ProcessRegistry 用 200KB 滚动缓冲区保存后台进程输出，LRU 淘汰超过 64 个进程
- **替代方案**：不缓存进程输出，只记录进程状态；或无上限缓存
- **为什么有这个选择**：后台进程输出需要随时可查（用户可能在任何时间问进程状态），但无上限会占用大量内存；200KB 是足够看最近状态同时不导致内存问题的权衡值
