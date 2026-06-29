---
type: entity
repo: codex-main
slug: execpolicy
problem: 如何对 Shell 命令执行实施允许/拒绝策略
generated: 2026-06-28
source_files:
  - codex-rs/execpolicy/src/lib.rs
  - codex-rs/execpolicy/src/policy.rs
  - codex-rs/execpolicy/src/rule.rs
---

# ExecPolicy

**代码位置**：codex-rs/execpolicy/
**这个模块解决什么问题**：
- 实现层：通过前缀规则（PrefixRule）匹配引擎，对每个待执行的 shell 命令做出 Allow/Deny/Ask 决策
- 问题层：如何对 Shell 命令执行实施允许/拒绝策略
**对外暴露什么**：
- `Policy`：执行策略主体，包含规则列表和全局缺省动作 ^[codex-rs/execpolicy/src/policy.rs:27]
- `Evaluation`：策略评估结果 ^[codex-rs/execpolicy/src/policy.rs:27]
- `Decision`：单条决策（Allow/Deny/Ask） ^[codex-rs/execpolicy/src/decision.rs:10]
- `PrefixRule`：前缀匹配规则（命令前缀 → 策略动作） ^[codex-rs/execpolicy/src/rule.rs:56]
- `PrefixPattern`：前缀模式匹配 ^[codex-rs/execpolicy/src/rule.rs:55]
- `PolicyParser`：策略解析器，从 TOML 配置解析规则 ^[codex-rs/execpolicy/src/parser.rs:19]
- `RuleMatch`：规则匹配结果 ^[codex-rs/execpolicy/src/rule.rs:67]
**它和谁交互**：
- 被 [[entities/core-agent-loop]] 调用（Agent 执行命令前查询策略）
- 依赖 [[entities/config-management]]（从配置层加载执行策略规则）
- 与 [[entities/shell-escalation]] 配合（allow 的规则可能通过 escalation 进行权限提升执行）
**为什么它是可分离的**：独立的 Rust crate，纯策略评估引擎，不依赖 IO 或网络

**关键机制**（源码可见）：
- **前缀规则匹配**：`PrefixRule` 通过前缀模式匹配命令字符串，支持通配符和参数匹配，返回 Allow/Deny/Ask ^[codex-rs/execpolicy/src/rule.rs:56-67]
- **策略评估管道**：`Evaluation` 将多条规则按优先级组合，提供"首次匹配即返回"和"缺省动作"的复合评估 ^[codex-rs/execpolicy/src/policy.rs:27]
- **规则修改**：`amend` 模块支持在运行时通过审批流程动态追加 allow-prefix 规则（用户批准后持久化） ^[codex-rs/execpolicy/src/amend.rs:10-12]
- **解析器分离关注点**：`PolicyParser` 只处理 TOML 到 `Policy` 的转换，不涉及 IO 或存储 ^[codex-rs/execpolicy/src/parser.rs:19]
- **网络策略扩展**：除命令执行规则外，也支持 `NetworkRuleProtocol` 和网络域名的策略评估 ^[codex-rs/execpolicy/src/rule.rs:24-29]

**源码证据**：
- 入口文件：codex-rs/execpolicy/src/lib.rs
- 策略定义：codex-rs/execpolicy/src/policy.rs:27
- 规则定义：codex-rs/execpolicy/src/rule.rs:55-67
