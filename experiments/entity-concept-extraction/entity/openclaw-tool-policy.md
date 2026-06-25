# Tool Policy / 权限管理（OpenClaw）

## 是什么 / 边界

Tool Policy 是 OpenClaw 的工具可见性过滤 + exec 审批系统：在消息处理的关键路径上决定哪些工具对当前 LLM 调用可见，以及 exec 类工具是否获得执行授权。不执行工具本身，不管理工具的注册（由 `registerTool` 负责），不做会话管理。

## 关键实现

- 多层 pipeline 过滤：`src/agents/tool-policy-pipeline.ts`（5 层叠加：profile / provider / global / agent / group，每层可配置 allowlist / denylist）
- owner 访问控制：`src/agents/tool-policy.ts`（`OwnerOnlyToolApprovalClass` 将工具分为 `control_plane` / `exec_capable` / `interactive` 三类，`applyOwnerOnlyToolPolicy` 根据 sender 是否为 owner 过滤）
- exec 异步审批：`src/agents/bash-tools.exec-approval-request.ts`（注册 `ExecApprovalRequest`，阻塞等待 `waitForExecApprovalDecision`，支持 host / gateway 双路径审批）

## 设计选择记录

- **维度**：Architecture
- **选择**：权限决策在消息处理关键路径上做同步门控，工具集在进入 LLM 之前就已过滤完毕
- **替代方案**：工具调用完成后做事后审计，违规则回滚或告警
- **为什么有这个选择**：事前门控可以阻止未授权工具进入 LLM 的 function-calling 视野，根本上防止 LLM 尝试调用无权限工具；事后审计只能补救，不能预防

---

- **维度**：Architecture
- **选择**：exec 类工具走异步审批协议，阻塞等待 owner 决策后才执行
- **替代方案**：exec 工具直接执行，依赖 LLM 自身判断是否合适
- **为什么有这个选择**：exec 类工具（shell 命令执行）风险最高，需要人类在循环中确认；异步审批让助手可以「请求许可」而不是「请求原谅」

---

- **维度**：Extension Points
- **选择**：tool policy 通过 5 层 pipeline 叠加，每层独立配置 allowlist / denylist
- **替代方案**：单一全局 allowlist，所有过滤逻辑合并在一处
- **为什么有这个选择**：不同粒度的策略（profile 级、provider 级、agent 级）需要独立可配置，pipeline 架构使各层策略正交，不互相耦合
