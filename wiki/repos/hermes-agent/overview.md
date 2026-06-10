---
repo: hermes-agent
dimension: overview
dimensions_version: v1.0
generated: 2026-06-09
---

# Hermes Agent — Overview

Hermes Agent 是由 [Nous Research](https://nousresearch.com) 构建的**自学习 AI Agent 框架**。它是目前唯一内置完整学习闭环的 agent —— 从经验中自动创建技能、使用过程中自我改进、跨会话持久化记忆、并构建渐进式用户模型。支持从 $5 VPS 到 GPU 集群的任何环境运行，通过 Telegram/Discord/Slack/WhatsApp 等 20+ 消息平台与用户交互。

## 自学习闭环

Hermes 最核心的差异化能力是内建于 agent system prompt 的三段驱动指令 + 三个支撑工具，共同构成无需人类干预的完整自学习闭环：

### 闭环三段式

```
Session 1: 用户给任务 → Agent 完成复杂任务(5+ tool calls)
    → SKILLS_GUIDANCE 推动 agent 主动调用 skill_manage 创建技能
    → MEMORY_GUIDANCE 推动 agent 主动写入用户偏好/环境事实到 memory

Session 2 (几天后): 用户给新任务
    → 系统 prompt 自动注入上次的 memory 条目 + skill 文件
    → SESSION_SEARCH_GUIDANCE 推动 agent 调用 session_search 搜索历史会话
    → Agent 找回上次成功的步骤，用 skill_view 读取技能
    → 如果技能内容已过时，SKILLS_GUIDANCE 推动 agent 调用 skill_manage(action='patch') 即时修复
```

### 三段驱动指令 ^[agent/prompt_builder.py:145-171]

| 指令 | 源码位置 | 驱动行为 |
|---|---|---|
| **MEMORY_GUIDANCE** | `agent/prompt_builder.py:145-156` | "用户纠正你、分享偏好时主动保存到 memory；发现新的做事方式时保存为 skill" |
| **SESSION_SEARCH_GUIDANCE** | `agent/prompt_builder.py:158-162` | "当用户提及过去对话时，用 session_search 主动回忆，不要让他们重复" |
| **SKILLS_GUIDANCE** | `agent/prompt_builder.py:164-171` | "完成复杂任务(5+ tool calls)后主动创建 skill；使用 skill 时发现过时就立即 patch" |

### 三个支撑工具

| 工具 | 源码位置 | 能力 |
|---|---|---|
| `skill_manage` | `tools/skill_manager_tool.py:1-30` | `create/edit/patch/delete` — Agent 自主管理技能文件 |
| `memory` | `tools/memory_tool.py:513-559` | `add/replace/remove` — 跨会话持久化事实到 `MEMORY.md`/`USER.md` |
| `session_search` | `tools/session_search_tool.py` | SQLite FTS5 全文搜索历史会话，LLM 即时摘要 |

### 为什么这是"真正的自学习"

| | 普通 AI agent | Hermes 自学习 |
|---|---|---|
| 技能来源 | 人类手写或从 hub 下载 | **Agent 在完成任务后自主创建** |
| 技能维护 | 人类手动更新 | **Agent 使用中发现过时就自动 patch** |
| 用户偏好 | 每次重新问 | **Agent 跨会话自动记忆和注入** |
| 上下文 | 单次会话 | **Agent 主动搜索历史会话回忆** |

## 架构概览

Hermes 采用六层分层架构，数据流从用户界面层向下经过编排层、安全层、插件层、工具层、基础设施层，全程配有独立的可观测性层。

**核心编排器** `AIAgent` (run_agent.py, 11510行) 管理完整的 tool-calling 对话循环，支持 20+ LLM provider 的 failover 路由和子 agent 委派。**GatewayRunner** (gateway/run.py) 通过 22 个平台适配器将 agent 连接到消息平台，每个适配器都继承自统一的 `BasePlatformAdapter` 抽象基类。

安全层是一个独特的关注点：三层审批架构（YOLO → Smart(aux LLM) → Manual(tirith+pattern matching)）在命令执行前干预，100+ 威胁模式的 skill 安全扫描器在外部技能安装前检查。可观测性层提供多文件旋转日志（带 API key 脱敏）、session context 标签、后台进程注册表和 per-session 成本追踪。

## 关键维度

- [[hermes-agent/dimensions/hermes-agent-architecture]] — 分层架构、安全护栏、可观测性系统
- [[hermes-agent/dimensions/hermes-agent-extension-points]] — 工具注册、toolset 组合、记忆插件、平台适配器、事件 hooks 等九大扩展机制
- [[hermes-agent/dimensions/hermes-agent-performance-tradeoffs]] — Prompt caching、context compression、并行工具执行、smart model routing 等 10 项性能权衡
- [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] — 选择性拥抱策略、三层版本锁、多后端可替换、优雅降级与供给链安全
- [[hermes-agent/dimensions/hermes-agent-testing-philosophy]] — 实用主义行为覆盖、578 文件自动隔离、并行 CI + supply chain audit

## 关联

- [[openclaw/overview]]
