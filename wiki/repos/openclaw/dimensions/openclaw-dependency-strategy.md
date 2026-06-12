---
repo: openclaw
dimension: dependency-strategy
dimensions_version: v1.0
generated: 2026-06-09
---

# OpenClaw — Dependency Strategy

OpenClaw 的依赖态度：**核心逻辑大量依赖 Node.js stdlib，channel/provider 能力拥抱生态专用 SDK，同时对不稳定或关键路径依赖实施精确版本锁定。**

## 1. 核心层：重度依赖 Node.js stdlib

`src/` 中有 3,125 处 `node:` stdlib import，最高频：`node:path`（1036 次）、`node:fs/promises`（565 次）、`node:fs`（460 次）、`node:os`（417 次）、`node:crypto`（199 次）。进程管理、文件 IO、加密、网络全部走 stdlib，不引入第三方替代。这是**最低替换成本**的依赖选择。^[src/ 全局 import 统计]

## 2. 核心 AI 引擎：完全依赖一个私有包族

442 处 import 来自 `@mariozechner/*`，按频率排序：^[package.json: @mariozechner/* dependencies]

| 包 | import 次数 | 用途 |
|---|---|---|
| `pi-ai` | 176 | LLM transport、OpenAI compat、模型配置类型 |
| `pi-agent-core` | 164 | agent 消息类型、工具结果类型 |
| `pi-coding-agent` | 77 | session 管理、compaction、bootstrap |
| `pi-tui` | 22 | TUI 组件（SlashCommand、Component） |

这是 OpenClaw **替换成本最高**的依赖——agent 层几乎无法在不重写的情况下切换。四个包精确锁定到同一版本 `0.66.1`，与主版本号同步发布。^[package.json: @mariozechner/pi-agent-core 0.66.1]

## 3. Channel SDK：拥抱生态，各自独立

每个 channel extension 只声明自己需要的 SDK，通过 `workspace:*` 引用内部 plugin-sdk，不在 root package 中聚合。这是故障隔离的典型实践——代表性依赖：^[extensions/slack/package.json:1-15]

- Slack：`@slack/bolt`、`@slack/web-api`
- Telegram：`grammy`、`@grammyjs/runner`
- Discord：`discord-api-types`
- Matrix：`matrix-js-sdk`、`@matrix-org/matrix-sdk-crypto-wasm`
- LINE：`@line/bot-sdk`
- Feishu：`@larksuiteoapi/node-sdk`

核心运行时不因任何单个 channel SDK 的变动受影响，channel 故障域完全隔离。

## 4. HTTP 框架：双框架并存

`hono`（精确锁定 `4.12.12`）用于主 Gateway HTTP 服务；`express`（`^5.2.1`）仅用于 `src/media/server.ts` 一个文件的媒体服务。两框架并存是历史分工，非架构意图。^[src/media/server.ts:3]

## 5. Schema 验证：三库并存

三个验证库在不同子系统独立引入，非统一选型：^[src/ 全局 import 统计]

| 库 | 用处 | import 次数 | 版本策略 |
|---|---|---|---|
| `@sinclair/typebox` | Gateway protocol JSON Schema | 69 | 精确锁定 `0.34.49` |
| `zod` | 配置类型验证 | 45 | 范围 `^4.3.6` |
| `ajv` | plugin 配置 schema 校验 | 9 | 范围 `^8.18.0` |

## 6. peer / optional 依赖设计

**peer dependencies**（用户自行安装）：

- `@napi-rs/canvas`：Canvas 渲染能力
- `node-llama-cpp`（精确锁 `3.18.1`）：本地 LLM 推理，安装体积达 GB 级，故设为 peer 避免默认拉入

**optional dependencies**（缺失时自动降级）：

- `@discordjs/opus`：Discord 语音编解码
- `@matrix-org/matrix-sdk-crypto-nodejs`：Matrix E2E 加密原生模块
- `openshell`（精确锁 `0.1.0`）：shell 集成

^[package.json: peerDependencies, optionalDependencies]

## 7. 版本锁定策略

70 个 runtime deps 中 29 个精确锁定（无 `^`/`~`），41 个用范围版本。精确锁定规律：^[package.json: dependencies]

- **所有 `@mariozechner/*`**：core 依赖，破坏性变更风险极高
- **协议 SDK**：`@modelcontextprotocol/sdk`（`1.29.0`）、`@agentclientprotocol/sdk`（`0.18.2`）——协议不兼容即故障
- **有 native addon 的包**：`sqlite-vec`、`playwright-core`、`@lydell/node-pty`、`matrix-js-sdk`——native 编译版本敏感
- **HTTP 框架**：`hono`（`4.12.12`）
- **构建工具链**：`tsdown`、`oxfmt`、`jscpd`

范围版本用于工具类库（`commander`、`chalk`、`uuid`、`yaml`），patch 变更不影响运行时行为。

## 关键权衡

| 决策 | 理由 | 代价 |
|---|---|---|
| 深度依赖 `@mariozechner/*` | 快速复用成熟 AI agent 引擎 | 替换成本极高，受上游版本节奏约束 |
| Channel SDK 各自独立 | 避免 channel 间相互污染，按需安装 | monorepo 管理复杂度上升 |
| 精确锁定协议/native 包 | 防止协议不兼容和 native 编译失败 | 需手动维护升级 |
| peer dep 设计本地 LLM | 避免默认安装拉入 GB 级二进制 | 用户需额外安装步骤 |

## 关联

*(暂无同类仓库已分析，链接待补充)*

<!-- generated-dimension-links -->
**本维度提取的节点：**

- [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] — DesignDecision
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] — DesignDecision
- [[openclaw/nodes/design-decisions/openclaw-startup-over-memory-tradeoff]] — DesignDecision
<!-- /generated-dimension-links -->
