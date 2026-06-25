# Nanobot 设计选择草稿

> 提取自 nanobot Entity 页 + 源码补充（2026-06-17）

---

## 子系统整体如何组装和连线

**维度**：Architecture
**问题陈述**：如何组织所有子系统的实例化和连线，使系统的整体构成具有最大可发现性？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 单体 Hub 集中式组装 | 所有子系统在一个构造函数中实例化和连线，读一个函数即知全貌 | entity/nanobot-agent-loop.md → agent/loop.py:115-228 |

---

## 执行引擎如何跨场景复用

**维度**：Architecture
**问题陈述**：如何让 LLM 执行引擎在不同使用场景（主 agent / 子 agent / Dream 记忆处理）间复用，而不耦合产品层逻辑？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | AgentRunner 完全产品层无关 | 不持有 channel/session/cron 引用，只接受 messages 和 tool_registry 纯数据输入 | entity/nanobot-agent-runner.md → agent/runner.py:83-89 |

---

## 上下文窗口治理如何在引擎内部自执行

**维度**：Performance Tradeoffs
**问题陈述**：如何在有限上下文窗口中管理长对话和多轮 tool calling，且对 LLM 透明？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 四层透明治理 | Backfill 补全孤立的 tool_use → Microcompact 压缩 10 轮前的 tool result → Budget 截断单结果 → Snip 按 token 预算从尾部裁剪 | entity/nanobot-agent-runner.md → agent/runner.py:102-107, agent/runner.py:553-640 |

---

## 内容变换钩子和事件通知钩子如何采用不同组合策略

**维度**：Extension Points
**问题陈述**：如何让内容变换钩子和事件通知钩子采用不同的组合策略，以适应它们各自的语义？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | finalize_content 管道串联 + 其余方法扇出 | 内容变换适合逐步加工，事件通知适合互不阻塞 | entity/nanobot-agent-hook.md → agent/hook.py:57 |

---

## IM 平台插件如何同时支持内置和第三方开发

**维度**：Extension Points
**问题陈述**：如何让新的 IM 平台接入同时支持内置开发和第三方插件，且不产生名称冲突？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 双层 Channel 发现——pkgutil 自发现 + entry_points 外部插件 | 内置 pkgutil 扫描 channels/ 目录自动发现，entry_points 支持 pip 可安装第三方插件，内置优先覆盖 | entity/nanobot-channel-system.md → channels/registry.py:23, channels/registry.py:42-55 |

---

## System Prompt 多层内容如何组织

**维度**：Architecture
**问题陈述**：如何组织 system prompt 的多层内容拼接，使其可独立测试且保持 Anthropic prompt cache 稳定？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 六层固定顺序纯函数式 ContextBuilder | identity → bootstrap files → memory → always skills → skills summary → recent history，每层 `---` 分隔，不依赖运行时状态，确保 prompt cache 稳定前缀 | entity/nanobot-context-builder.md → agent/context.py:17, agent/context.py:30-63 |

---

## 定期唤醒如何兼具确定性和 LLM 主动性

**维度**：Architecture
**问题陈述**：如何让定期唤醒机制兼具确定性调度和 LLM 基于上下文的主动判断？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | Heartbeat 单工具 LLM 调用 + Cron 确定性调度 | Heartbeat 用仅含 skip/run 的虚拟 tool 让 LLM 基于上下文判断是否需要执行；Cron 覆盖确定的 at/every/cron 时间触发 | entity/nanobot-cron-heartbeat.md → heartbeat/service.py:25-30, heartbeat/service.py:88-111; cron/service.py:65 |

---

## 如何适配多 LLM 供应商而不引入第三方转发层

**维度**：Dependency Strategy
**问题陈述**：如何适配 20+ LLM 供应商的 API 差异，同时避免第三方转发层的不可控风险？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 移除 litellm，自行维护原生 SDK 适配层 | 使用 openai + anthropic 原生 SDK，Provider 适配代码 3,719 行全部自控，5 种 backend 覆盖 20+ 供应商，零间接供应商依赖 | entity/nanobot-llm-provider.md → providers/base.py, providers/registry.py |

---

## 记忆压缩如何不阻塞主对话

**维度**：Architecture
**问题陈述**：如何让记忆压缩不阻塞主 agent 的对话流程？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | Consolidator 独立 provider + asyncio.create_task 异步后台运行 | 不共享主 agent 的 provider 实例，压缩失败不影响正在进行对话，结果在下一轮 context 组装时生效 | entity/nanobot-memory-system.md → agent/memory.py:346-365, agent/loop.py:470-474 |

---

## 不同来源的消息如何统一进入处理管线

**维度**：Architecture
**问题陈述**：如何让不同来源的消息（IM / 子 agent / Cron / Heartbeat）统一进入 AgentLoop 处理？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | asyncio.Queue 极简事件总线 | 两个单向队列（inbound/outbound）将 Channel 和 AgentLoop 完全解耦，入站不区分来源 | entity/nanobot-message-bus.md → bus/queue.py:8-20 |

---

## 测试资源如何分配以最大化安全效果

**维度**：Testing Philosophy
**问题陈述**：如何在 agent 框架的测试策略中分配有限资源，最大化安全防护的投入产出比？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 测试投入集中安全（SSRF / exec 沙箱 / workspace 隔离） | 26,048 行测试代码中安全测试比重最大，因为 agent 框架中安全漏洞的后果远大于功能 bug | entity/nanobot-security.md → security/network.py; tests/tools/test_exec_security.py |

---

## 会话数据如何存储以兼顾可读性和正确性

**维度**：Architecture
**问题陈述**：如何存储和加载会话数据，使其追加友好、人类可读，且发给 LLM 的历史始终从合法边界开始？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | JSONL 文件 + 惰性加载 + 合法边界裁剪 | JSONL 逐行追加无锁竞争，get_or_create 首次访问才加载，裁剪对齐到 user-turn 避免孤立的 tool 调用 | entity/nanobot-session-manager.md → session/manager.py:96, session/manager.py:69, session/manager.py:119 |

---

## 技能知识如何注入而不让 prompt 膨胀

**维度**：Extension Points
**问题陈述**：如何让技能知识的注入既不需要代码，又不让 system prompt 无限膨胀？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | Markdown 文件 + always 全文注入 + 渐进式按需加载 | SKILL.md 带 YAML frontmatter，always 技能全文注入 system prompt，其余以 XML 摘要呈现、agent 按需 read_file | entity/nanobot-skills.md → agent/skills.py:23-50, agent/skills.py:109-117 |

---

## 子 agent 如何复用主 agent 能力同时限制权限

**维度**：Architecture
**问题陈述**：如何让子 agent 复用主 agent 的执行能力，同时安全地限制其权限范围？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 共享 AgentRunner 引擎 + 独立受限 ToolRegistry + 结果经 bus 注入 | 子 agent 无 message/spawn/cron 工具防止递归，结果通过 bus.publish_inbound 走与 IM 消息完全相同的处理路径 | entity/nanobot-subagent.md → agent/subagent.py:70-85, agent/subagent.py:102-129 |

---

## 工具注册如何做到完全确定性

**维度**：Extension Points
**问题陈述**：如何让工具注册具有完全的确定性，避免隐式发现带来的不可预期行为？

| 仓库 | 选择 | 简述 | 溯源 |
|------|------|------|------|
| nanobot | 显式 register() 注册——不做 AST 扫描、装饰器发现、模块自省 | 每个工具在 _register_default_tools() 中点名，一眼可知系统有哪些工具；builtins 按名称排序在前保证 prompt cache 稳定前缀 | entity/nanobot-tool-registry.md → agent/tools/registry.py:8-18, agent/loop.py:225-229 |
