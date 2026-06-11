---
node_type: Component
scope: system
motivated_by: [layered-approval-decision]
sources:
  - tools/approval.py:586-922
  - tools/approval.py:219-284
---

# Approval System

`check_all_command_guards` 是所有命令执行的同步门控入口。Gateway 模式下用 FIFO 队列 + `threading.Event` 实现阻塞审批：agent 线程挂起等待用户 `/approve`/`/deny`，并行子 agent 并发等待各自审批。约束所有 exec 类工具调用——绕过它没有合法路径。
^[tools/approval.py:586-922]
