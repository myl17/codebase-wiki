---
type: entity
repo: hermes-agent
slug: delegate-subagent
problem: 如何在父 agent 上下文中并行派生子 agent 执行独立任务，隔离上下文、限制工具、汇总结果
generated: 2026-06-25
source_files:
  - tools/delegate_tool.py
---

# 委派子 Agent

**代码位置**：`tools/delegate_tool.py`
**这个模块解决什么问题**：
- 实现层：`delegate_task()` 通过 ThreadPoolExecutor 并行创建独立 AIAgent 子实例，隔离上下文和工具集，执行完成后返回结构化摘要；支持单任务和批量模式，最大深度 2 层
- 问题层：如何在父 agent 上下文中并行派生子 agent 执行独立任务，隔离上下文、限制工具、汇总结果
**对外暴露什么**：`delegate_task()` 函数（tools/delegate_tool.py:623，注册为工具 `delegate_task`）
**它和谁交互**：
- 依赖 [[entities/agent-core]]（`_build_child_agent()` 创建子 AIAgent 实例，继承 iteration_budget 和 credential_pool）
- 依赖 [[entities/tool-registry]]（子 agent 获取受限工具集，屏蔽 delegate_task/clarify/memory/send_message/execute_code）
- 被 [[entities/agent-core]] 调用（通过工具分发，父 agent 在工具循环中调用 delegate_task）
**为什么它是可分离的**：独立模块，通过 AIAgent 构造函数创建子实例，不修改父 agent 状态

**关键机制**（源码可见）：
- 工具屏蔽清单：`DELEGATE_BLOCKED_TOOLS` 包含 5 个禁止工具（delegate_task/clarify/memory/send_message/execute_code），防止递归委派、用户交互、共享内存写入和脚本执行 ^[tools/delegate_tool.py:32-38]
- 最大嵌套深度 2：父（0）→ 子（1）→ 孙子拒绝（2），防止无限递归 ^[tools/delegate_tool.py:53]
- 并发控制：默认最多 3 个并发子 agent，通过 `ThreadPoolExecutor` 和 `as_completed()` 管理；可通过 `delegation.max_concurrent_children` 或 `DELEGATION_MAX_CONCURRENT_CHILDREN` 配置 ^[tools/delegate_tool.py:52-79]
- 迭代预算共享：子 agent 继承父的 `iteration_budget` 对象，统一限制 LLM 调用总数，默认每子 agent 50 步 ^[tools/delegate_tool.py:80, 238-284]
- 凭证解析：`_resolve_delegation_credentials()` 从 config.yaml `delegation.*` 段读取子 agent 专用的 provider/model/base_url/api_key 配置 ^[tools/delegate_tool.py:848]
- 子工具集交集：子 agent 可用的工具集是父 agent 工具集与委托允许工具集的交集，不会超过父的权限 ^[tools/delegate_tool.py:238-284]
- 进度回调：`_make_progress_callback()` 将子 agent 的工具调用中继到父 agent 的显示层（CLI spinner 或 gateway），仪表板显示 `[child N/5 progress]` ^[tools/delegate_tool.py:313-337]
- 心跳循环：每个子 agent 启动后台线程定期 `_touch_activity()` 防止 gateway 空闲超时 ^[tools/delegate_tool.py:238-284]
- 结果结构化：返回 `{status, summary, token_usage, tool_trace, duration_seconds}` ^[tools/delegate_tool.py:399-504]

**源码证据**：
- 入口文件：tools/delegate_tool.py
- 核心函数：`def delegate_task(task=None, tasks=None, ...)` ^[tools/delegate_tool.py:623]
- 工具注册：`registry.register(name="delegate_task", toolset="delegation", ...)` ^[tools/delegate_tool.py:1088]

**关联 Concept**：
- [[concepts/subagent-orchestration]]
