# Gateway（OpenClaw）

## 是什么 / 边界

Gateway 是 OpenClaw 的纯 HTTP 控制平面：处理 HTTP 路由、shared session 生命周期和认证 secret ref 解析（token / password / gateway auth 三种形式）。Gateway 明确不执行 AI 调用，不持有任何业务逻辑，不参与消息处理主路径的 LLM 调用环节。

## 关键实现

- 入口：`src/gateway/`
- 认证解析：`src/gateway/auth-config-utils.ts`（secret ref 解析三种认证形式）
- HTTP 框架：`hono`（精确锁定 `4.12.12`）
- 注册接口：`OpenClawPluginApi.registerGatewayMethod`（供 plugin 扩展 RPC 方法）
- exec 审批双路径：`src/agents/bash-tools.exec-approval-request.ts` 支持 host 路径和 gateway 路径两种审批通道

## 设计选择记录

- **维度**：Architecture
- **选择**：Gateway 是纯路由层，不包含 AI 调用逻辑
- **替代方案**：Gateway 作为 AI 调用的协调中心，统一调度 LLM
- **为什么有这个选择**：将控制平面和 AI 执行层分离，使两者可以独立扩展和替换；Gateway 负责网络边界，AI harness 负责模型选择，职责更清晰

---

- **维度**：Extension Points
- **选择**：`registerGatewayMethod` 允许 plugin 向 Gateway 注入 RPC 方法
- **替代方案**：Gateway API 完全由 core 控制，plugin 只能通过事件/hook 间接影响
- **为什么有这个选择**：channel plugin 需要与 gateway 直接通信（如审批协议），将这条扩展路径开放出来比绕道 hook 系统更直接
