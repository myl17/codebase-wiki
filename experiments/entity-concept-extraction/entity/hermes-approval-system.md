# 三层审批系统（Hermes Agent）

## 是什么 / 边界

三层审批系统（ApprovalSystem）在命令执行前介入，按照 YOLO → Smart（aux LLM）→ Manual（tirith + 正则匹配）的层级顺序做风险评估和用户审批。

它的边界：只在工具调用路径的执行前阶段介入，不干预 LLM 的决策过程、不修改工具执行结果、不负责技能内容安全（那是 SkillsGuard 的职责）。

## 关键实现

- 审批主入口：`tools/approval.py:586-922`，`check_all_command_guards()`
- 三层架构：
  - Layer 0（YOLO / 容器 / approvals.mode=off）：全部放行
  - Layer 1（Smart）：`_smart_approve()`（`tools/approval.py:534-583`），aux LLM 评估 → auto-approve/deny/escalate
  - Layer 2（Manual）：tirith + DANGEROUS_PATTERNS 合并发现 → 用户交互式审批 [o/s/a/d]
- 25+ 危险模式正则：`tools/approval.py:75-138`（rm/chmod/mkfs/kill/systemctl/curl|sh/git reset --hard 等）
- 审批持久化级别：
  - `once`：仅本次有效
  - `session`：会话级允许（`tools/approval.py:299-303`）
  - `always`：写入 `config.yaml` 的 `command_allowlist`，跨会话持久化（`tools/approval.py:376-402`）
- Gateway 阻塞审批：FIFO 队列 + threading.Event，agent 线程阻塞等待用户 /approve 或 /deny（`tools/approval.py:219-284`）

## 设计选择记录

- **维度**：Architecture
- **选择**：三层审批（YOLO → Smart → Manual），中间层用辅助 LLM 做风险评估
- **替代方案**：仅双层（YOLO → Manual），全部由人工决定
- **为什么有这个选择**：Smart 层用便宜的辅助模型自动处理明显安全或明显危险的命令，只有模糊情况才升级到人工审批，降低用户疲劳；纯人工审批在消息平台场景下不可行

---

- **维度**：Performance Tradeoffs
- **选择**：审批结果可持久化为 `always`（跨会话），写入 config.yaml allowlist
- **替代方案**：每条命令每次都要重新审批，不允许持久化
- **为什么有这个选择**：常用命令每次都要审批会严重影响使用体验；allowlist 让用户一次审批、永久生效，代价是 config.yaml 需要人工维护审查

---

- **维度**：Architecture
- **选择**：25+ 危险模式正则覆盖常见攻击向量（rm/chmod/curl|sh 等），与 tirith 结果合并后审批
- **替代方案**：只依赖 LLM 判断危险性，不维护正则列表
- **为什么有这个选择**：正则模式是确定性的，不受 LLM 幻觉影响，可以可靠地拦截已知高危操作；LLM 判断作为补充而非主防线
