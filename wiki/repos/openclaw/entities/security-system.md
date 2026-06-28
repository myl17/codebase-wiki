---
type: entity
repo: openclaw
slug: security-system
problem: "如何在保持 agent 能力的同时，提供多层纵深防御的安全策略（网络暴露、执行限制、渠道访问控制、外部内容防护）？"
generated: 2026-06-25
source_files:
  - src/security/
---

# Security System

**代码位置**：`src/security/`
**这个模块解决什么问题**：
- 实现层：安全审计报告 + DM/group 访问控制 + 外部内容沙箱包装 + 工具 HTTP 调用限制 + 配置标志扫描
- 问题层：如何在保持 agent 能力的同时，提供多层纵深防御的安全策略（网络暴露、执行限制、渠道访问控制、外部内容防护）？
**对外暴露什么**：
- `SecurityAuditReport` / `SecurityAuditFinding` — 审计报告和发现 ^[src/security/audit.types.ts:17]
- `SecurityAuditOptions` — 审计选项（config, env, platform, deep probe, dependency injection） ^[src/security/audit.ts:54]
- `collectFilesystemFindings()` — 文件系统权限检查 ^[src/security/audit.ts:187]
- `collectGatewayConfigFindings()` — 网关/认证/网络安全审计 ^[src/security/audit.ts:318]
- `DEFAULT_GATEWAY_HTTP_TOOL_DENY` — 通过 HTTP 禁用的 15 个高风险工具 ^[src/security/dangerous-tools.ts:9]
- `resolveDmGroupAccessDecision()` — DM/group 访问控制决策树 ^[src/security/dm-policy-shared.ts]
- `wrapUntrustedExternalContent()` — 外部内容安全包装（注入检测 + Unicode 同形攻击防护） ^[src/security/external-content.ts]
- `ContextVisibilityMode` — 上下文可见性（all | allowlist | allowlist_quote） ^[src/security/context-visibility.ts]
**它和谁交互**：
- 依赖 [[entities/config-system]]（安全配置读取）
- 依赖 [[entities/channel-system]]（渠道安全检查）
- 被 [[entities/gateway]] 集成（认证配置审计、速率限制）
- 被 [[entities/cli-system]]（security audit 命令）
- 被 [[entities/tool-system]]（HTTP 工具调用限制）
- 被 [[entities/media-pipeline]]（SSRF 保护委托）
**为什么它是可分离的**：独立的安全审计和策略模块，通过配置驱动

**关键机制**（源码可见）：
- 网关认证安全：bind mode（loopback → tailscale → explicit IP）、auth mode（token/password/trusted-proxy/none） ^[src/security/audit.ts:318]
- HTTP 工具限制：15 个高风险工具（exec, spawn, shell, fs_write, fs_delete, sessions_spawn 等）默认禁止 HTTP 调用 ^[src/security/dangerous-tools.ts:9]
- DM 策略：`open`（任何人）→ `allowlist`（白名单用户）→ `pairing`（配对流程）→ `disabled` ^[src/security/dm-policy-shared.ts]
- Group 策略：辅助 `open` / `allowlist` / `disabled` + 命令门控 ^[src/security/dm-policy-shared.ts]
- 外部内容保护：`<<<EXTERNAL_UNTRUSTED_CONTENT id="hex">>>...<<<END_EXTERNAL_UNTRUSTED_CONTENT>>>` 包装 + 同形攻击检测 ^[src/security/external-content.ts]
- 文件系统审计：state dir 应 0o700、config file 应 0o600、符号链接检测 ^[src/security/audit.ts:187]
- 插件安全审计收集器：`SecurityAuditCollector` 类型让插件贡献自己的安全检查 ^[src/plugins/types.ts]

**源码证据**：
- 审计引擎：src/security/audit.ts
- 审计类型：src/security/audit.types.ts
- DM 策略：src/security/dm-policy-shared.ts
- 外部内容：src/security/external-content.ts
- 危险工具：src/security/dangerous-tools.ts
- 上下文可见性：src/security/context-visibility.ts

**关联 Concept**：
- [[concepts/security-architecture]]
