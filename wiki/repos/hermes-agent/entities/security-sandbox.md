---
type: entity
repo: hermes-agent
slug: security-sandbox
problem: 如何在 Agent 执行系统命令前提供多层安全防护，包括预执行内容扫描、危险模式检测、用户审批和 DM 配对授权
generated: 2026-06-25
source_files:
  - tools/tirith_security.py
  - tools/approval.py
  - gateway/pairing.py
  - tools/path_security.py
  - tools/url_safety.py
  - tools/env_passthrough.py
---

# 安全沙箱

**代码位置**：`tools/tirith_security.py`、`tools/approval.py`、`gateway/pairing.py`
**这个模块解决什么问题**：
- 实现层：执行前多层次安全检查流水线——Tirith 二进制扫描（homograph URL、pipe to interpreter、终端注入）→ 危险模式正则匹配（rm -rf、curl | bash 等 40+ 模式）→ 会话级/永久审批 → 智能辅助审批（LLM 辅助判断误报）→ 配对码 DM 授权
- 问题层：如何在 Agent 执行系统命令前提供多层安全防护，包括预执行内容扫描、危险模式检测、用户审批和 DM 配对授权
**对外暴露什么**：`check_command_security()`（tools/tirith_security.py:614）、`check_all_command_guards()`（tools/approval.py:693）、`detect_dangerous_command()`（tools/approval.py:186）、`PairingStore`（gateway/pairing.py:75）、`approve_session()` / `approve_permanent()`（tools/approval.py:299/359）
**它和谁交互**：
- 依赖 [[entities/terminal-execution]]（所有终端命令执行前经过 `check_all_command_guards()`）
- 依赖 [[entities/config-system]]（security.* config + command_allowlist）
- 依赖 [[entities/gateway-runner]]（配对系统管理 DM 授权）
- 被 [[entities/agent-core]] 调用（indirectly via terminal tool）
- 被 [[entities/skills-system]] 调用（Skills Guard 使用相同的模式检测和不可见 Unicode 检测）
**为什么它是可分离的**：三组独立的安全模块（Tirith 扫描、审批管理、配对授权），通过统一的 `check_all_command_guards()` 流水线串联

**关键机制**（源码可见）：
- Tirith 二进制扫描：子进程执行 `tirith check --json --non-interactive`，exit code 为权威裁决源（0=allow, 1=block, 2=warn），JSON stdout 丰富但不覆盖裁决 ^[tools/tirith_security.py:614-684]
- Tirith 自动安装：从 GitHub releases 下载二进制到 `$HERMES_HOME/bin/tirith`，SHA-256 校验 + cosign 溯源验证（可选），后台安装不阻塞启动 ^[tools/tirith_security.py:281-489]
- 40+ 危险模式：涵盖 rm 递归删除、chmod 777、chown -R、mkfs/dd、SQL DROP/DELETE、systemctl stop、kill -9 -1、fork bomb、curl | bash、git reset --hard、self-termination 等 ^[tools/approval.py:75-138]
- 三层审批作用域：session-scoped（`approve_session()`，当前会话有效）、permanent（`approve_permanent()`，持久化到 command_allowlist）、YOLO mode（`enable_session_yolo()`，完全绕过）^[tools/approval.py:299-359]
- LLM 辅助智能审批：`_smart_approve()` 使用辅助 LLM 评估实际风险（误报如 `python -c "print('hello')"` 匹配 python -c 模式），返回 approve/deny/escalate ^[tools/approval.py:534-583]
- 配对码 DM 授权：`PairingStore` 使用 `secrets.choice()` 生成 8 字符加密随机码（1h 过期），支持速率限制（10min/请求）和锁定（5 次失败锁定 1h），文件权限 chmod 0600 ^[gateway/pairing.py:34-75, 150-193]
- 路径安全：`tools/path_security.py` 验证文件路径不逃逸工作目录 ^[tools/path_security.py]
- URL 安全：`tools/url_safety.py` 检查 URL scheme 和已知恶意模式 ^[tools/url_safety.py]
- 环境变量透传过滤：`tools/env_passthrough.py` 控制哪些环境变量可透传给子进程 ^[tools/env_passthrough.py]
- Fail-open 默认：Tirith 不可用时默认允许命令，config 可切换为 fail-close ^[tools/tirith_security.py:614-684]

**源码证据**：
- 入口文件：tools/tirith_security.py、tools/approval.py、gateway/pairing.py
- 核心函数：`def check_all_command_guards(command, task_id=None)` ^[tools/approval.py:693]、`def check_command_security(command, ...)` ^[tools/tirith_security.py:614]

**关联 Concept**：
- [[concepts/security-architecture]]
- [[concepts/execution-approval-pattern]]
