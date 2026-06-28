---
type: concept
concept: security-architecture
problem: 如何为 AI Agent 构建多层安全防御体系，覆盖命令执行、内容注入、网络访问和访问控制
concerns: [防御深度 vs 可用性摩擦, 误报率控制, 不同部署场景的安全模型适应性]
repos: [nanobot, hermes-agent, openclaw]
generated: 2026-06-25
---

# Security Architecture

## 核心问题

AI Agent 具有执行系统命令、读写文件、访问网络的能力——这些能力既是功能的基础，也是安全风险的来源。攻击面覆盖四个维度：命令执行层（Agent 生成的危险 shell 命令）、内容注入层（外部内容中的恶意负载或同形攻击）、网络层（SSRF、DNS 重绑定）、访问控制层（谁可以触发 Agent 执行什么操作）。一个完整的 Agent 安全架构必须在这四个维度上建立防线，且防线之间需要纵深配合。

核心张力在于防御深度与可用性摩擦的平衡。每增加一层安全检查，都会增加误报率（将合法操作标记为危险）和执行延迟（安全检查本身耗时）。尤其是在 LLM 生成命令的场景下，LLM 的输出天然包含变异性——同一意图可能用多种写法表达，静态模式匹配容易误判。三层防线（模式匹配、语义分析、人类审批）提供了渐进式升级路径，但每一层的设计决策（fail-open vs fail-close、同步 vs 异步）都会深刻影响用户体验。

不同部署场景要求不同的安全姿态。个人单机 Agent（开发者在自己电脑上运行）的安全需求远低于多租户平台 Agent（陌生人通过 DM 触发 Agent 执行）。安全模型需要从宽松的面向开发者到严格的面向平台线性伸缩，同时保持核心安全机制的复用性。

## 关切

- **防御深度 vs 可用性摩擦**：多层安全检查虽然提高了安全性，但每层都增加延迟和误报风险。如何在层数、延迟、准确性之间找平衡点？
- **误报率控制**：静态模式匹配不可避免地对 LLM 生成的自然语言命令产生误报。是否引入 LLM 辅助的语义风险评估来降低误报？如果引入，LLM 评估本身的安全性如何保证？
- **不同部署场景的安全模型适应性**：个人工具 vs 多租户平台需要不同的安全级别。能否用同一套机制通过配置伸缩，还是需要两套完全不同的安全架构？

## 各框架的解法

### nanobot
来源：[[repos/nanobot/entities/security-system]]
**解法**：聚焦网络层 SSRF 防护，通过三层 URL/IP 检测阻止访问内网地址。
**实现**：URL 正则提取 → DNS 解析获取所有 IP → 每个 IP 与 `_BLOCKED_NETWORKS` 黑名单比对（涵盖 RFC 1918、link-local、loopback、IPv6 的同级地址）；`configure_ssrf_whitelist()` 支持白名单绕过（如 Tailscale 的 `100.64.0.0/10`）。 ^[nanobot/security/network.py:10-21, 46-50, 28-37]
**权衡**：极低摩擦的纯网络安全方案，没有命令执行层的安全检查。适合个人工具场景，不适合多租户平台。

### hermes-agent
来源：[[repos/hermes-agent/entities/security-sandbox]]
**解法**：`check_all_command_guards()` 流水线串联多层防御：Tirith 二进制扫描 → 40+ 危险模式正则 → LLM 智能审批 → 三层审批作用域 → DM 配对码授权。
**实现**：Tirith 作为独立二进制子进程执行（exit code 为权威裁决源，fail-open 默认）；40+ 模式涵盖 rm -rf、curl | bash、fork bomb 等；LLM 辅助 `_smart_approve()` 评估实际风险以降低误报；配对码使用 `secrets.choice()` 生成 8 字符加密随机码（1h 过期、5 次失败锁定）；额外包含路径安全、URL 安全、环境变量透传过滤。 ^[tools/tirith_security.py:614-684, tools/approval.py:75-138, 534-583, gateway/pairing.py:34-75]
**权衡**：防御深度最强（命令+内容+授权三层），但摩擦也最高。LLM 智能审批是创新的误报控制手段，但引入 LLM 调用的额外延迟和成本。

### openclaw
来源：[[repos/openclaw/entities/security-system]]
**解法**：4 维安全审计框架：网关安全 + 外部内容标记 + DM 4 级访问策略 + HTTP 工具调用限制 + 可插拔审计收集器。
**实现**：网关认证审计覆盖 bind mode 和 auth mode 组合；外部内容用 `<<<EXTERNAL_UNTRUSTED_CONTENT>>>` 包裹标记防止注入，含 Unicode 同形攻击检测；DM 策略四档 `open → allowlist → pairing → disabled`；15 个高风险工具（exec/spawn/shell 等）默认禁止通过 HTTP 调用；`SecurityAuditCollector` 类型让插件贡献自身安全检查。 ^[src/security/audit.ts:318, src/security/external-content.ts, src/security/dm-policy-shared.ts, src/security/dangerous-tools.ts:9, src/plugins/types.ts]
**权衡**：安全模型适应性最强——通过四档策略和可插拔收集器实现了从个人到平台的柔性伸缩。但在命令执行层缺乏 hermes-agent 那种 Tirith 级别的深度扫描，偏向网关侧和访问控制侧。

## 对比
| 框架 | 防御深度 vs 可用性摩擦 | 误报率控制 | 不同部署场景的安全模型适应性 |
|------|------|------|------|
| nanobot | 单层 SSRF，极低摩擦 | 无命令检查因此无误报问题 | 仅适合个人工具 |
| hermes-agent | 四层流水线（Tirith+模式+LLM+审批），最高摩擦 | LLM 智能审批主动降误报 | 通过三层审批作用域适应，但偏重个人开发者 |
| openclaw | 四维审计框架，可插拔伸缩摩擦 | 同形攻击检测 + 外部内容标记，无命令层语义分析 | 四档 DM 策略 + 可插拔审计收集器，从个人到平台自然伸缩 |

## 演化记录
- 2026-06-25：初建，包含 nanobot, hermes-agent, openclaw
