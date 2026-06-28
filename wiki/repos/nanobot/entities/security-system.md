---
type: entity
repo: nanobot
slug: security-system
problem: 如何保护 Agent 不被 Web Fetch/Shell 工具利用进行 SSRF 攻击，限制对内部网络的访问
generated: 2026-06-25
source_files:
  - nanobot/security/network.py
---

# Security System

**代码位置**：`nanobot/security/network.py`
**这个模块解决什么问题**：
- 实现层：SSRF 防护——拦截 Web Fetch 请求到内网 IP（RFC 1918、link-local、loopback）、通过 URL 正则提取 + DNS 解析 + IP 黑名单校验的三层检测
- 问题层：如何保护 Agent 不被 Web Fetch/Shell 工具利用进行 SSRF 攻击，限制对内部网络的访问
**对外暴露什么**：`validate_url_target(url)` 函数（nanobot/security/network.py:46）、`configure_ssrf_whitelist(cidrs)` 函数（nanobot/security/network.py:28）
**它和谁交互**：
- 被 Web Fetch 工具调用（验证目标 URL 是否安全）
- 被 Web Search 工具调用（验证搜索结果 URL）
- 被 Shell 工具调用（sandbox 模式下的网络安全）
**为什么它是可分离的**：纯函数模块，无状态，可独立测试和替换

**关键机制**（源码可见）：
- 三层 SSRF 检测：URL 正则提取 → DNS 解析获取所有 IP → 每个 IP 与 `_BLOCKED_NETWORKS` 比对 ^[nanobot/security/network.py:10-21, 46-50]
- 内网黑名单：阻止 `0.0.0.0/8`、`10.0.0.0/8`、`100.64.0.0/10`、`127.0.0.0/8`、`169.254.0.0/16`、`172.16.0.0/12`、`192.168.0.0/16`、IPv6 的 `::1/128`、`fc00::/7`、`fe80::/10` ^[nanobot/security/network.py:10-21]
- 可配置白名单：`configure_ssrf_whitelist()` 允许绕过特定 CIDR 的拦截（如 Tailscale 的 `100.64.0.0/10`）^[nanobot/security/network.py:28-37]

**源码证据**：
- 入口文件：nanobot/security/network.py
- 核心接口：`def validate_url_target(url)` ^[nanobot/security/network.py:46]

**关联 Concept**：
- [[concepts/security-architecture]]
