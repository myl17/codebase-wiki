# Plugin / Hook 系统（OpenClaw）

## 是什么 / 边界

Plugin / Hook 系统是 OpenClaw 的扩展协议层：通过声明式 manifest（`openclaw.plugin.json`）描述 plugin 元数据，通过命令式 `OpenClawPluginApi`（25 个注册方法）提供运行时能力注册，通过 28 个生命周期 hook 允许 plugin 在关键节点注入行为，通过纯 Markdown Skills 文件提供零代码扩展。不是 plugin 的具体功能实现，不管理 plugin 之间的消息传递。

## 关键实现

- 入口定义：`src/plugin-sdk/plugin-entry.ts`（`definePluginEntry` / `defineBundledChannelEntry`）
- API 接口：`src/plugins/types.ts`（`OpenClawPluginApi`：25 个注册方法，`registerContextEngine` 和 `registerMemoryCapability` 为独占槽位）
- Hook 类型：`src/plugins/hook-types.ts`（28 个 hook 名，`before_prompt_build` / `before_agent_start` 是记忆注入的关键入口）
- Manifest 格式：`openclaw.plugin.json`（id、enabledByDefault、providers、modelSupport、contracts、configSchema 等）
- Skills 扩展：`src/agents/skills.ts`（`buildWorkspaceSkillsPrompt` + `buildWorkspaceSkillCommandSpecs`，纯 Markdown 文件即可扩展 agent 行为）

## 设计选择记录

- **维度**：Extension Points
- **选择**：用两层扩展协议并存——声明式 manifest（静态元数据）+ 命令式 API（运行时注册）
- **替代方案**：只用声明式 manifest 描述所有扩展，core 根据 manifest 初始化所有能力
- **为什么有这个选择**：manifest 适合描述静态元数据（provider 名、模型前缀支持、认证变量等），命令式 API 适合运行时动态注册（工具、hook、服务）；两者分工不同，并存而非替代

---

- **维度**：Extension Points
- **选择**：提供纯 Markdown 的 Skills 文件作为最轻量的第三层扩展，无需任何代码
- **替代方案**：所有 agent 行为定制都需要编写 TypeScript plugin
- **为什么有这个选择**：大多数用户的需求是定制 agent 的「技能」（如特定的工作流说明、命令快捷键），这些本质上是 prompt 工程，用 Markdown 表达比写代码更自然，大幅降低扩展门槛

---

- **维度**：Extension Points
- **选择**：28 个生命周期 hook 覆盖从消息入站到 agent 结束的完整链路，`before_prompt_build` 是记忆注入的官方入口
- **替代方案**：只暴露少数关键 hook（如 `before_llm_call`、`after_llm_call`），不细分生命周期
- **为什么有这个选择**：不同 plugin 需要在不同粒度介入（如 `active-memory` 需要在 prompt 组装前注入，`before_tool_call` 需要在工具执行前检查）；细粒度 hook 使每个 plugin 只订阅自己需要的节点，不需要在 hook 内部再过滤

---

- **维度**：Testing Philosophy
- **选择**：契约测试（`installChannelActionsContractSuite`）自动覆盖所有注册到 registry 的 channel / plugin，新 plugin 无需手写契约测试
- **替代方案**：每个 plugin 作者手写自己的接口兼容性测试
- **为什么有这个选择**：plugin 接口是稳定性关键路径，手写测试容易遗漏；共享 test suite + 自动覆盖确保接口一致性，降低新 plugin 的测试门槛
