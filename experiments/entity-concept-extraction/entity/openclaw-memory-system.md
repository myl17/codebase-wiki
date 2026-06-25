# Memory 系统（OpenClaw）

## 是什么 / 边界

Memory 系统是 OpenClaw 的向量化记忆存储与检索层：封装向量搜索和语义检索能力，在 prompt 组装阶段（非实时查询时）将相关记忆注入 context。不决定何时注入记忆（由 `before_prompt_build` / `before_agent_start` hook 驱动），不直接与 LLM 交互，不管理对话历史（由 Context Engine 负责）。

## 关键实现

- 接口定义：`src/memory-host-sdk/host/types.ts`（`MemorySearchManager`：向量搜索 + 语义检索，结果含 path / startLine / endLine / score / snippet / citation）
- 后端区分：`MemorySearchRuntimeDebug.backend`（`builtin` = SQLite + sqlite-vec 向量扩展；`qmd` = 外部引擎）
- Extension 实现：`memory-core`（核心接口）、`memory-lancedb`（LanceDB 向量存储）、`memory-wiki`（wiki-style 记忆）、`active-memory`（主动记忆注入）
- 注册入口：`OpenClawPluginApi.registerMemoryCapability`（独占槽位）
- 注入时机：`before_prompt_build` / `before_agent_start` hook（`active-memory` 扩展利用此机制）

## 设计选择记录

- **维度**：Architecture
- **选择**：记忆在 prompt 组装阶段注入，而非每次 LLM 输出后实时查询
- **替代方案**：agent 每轮都主动调用记忆检索工具，实时决定是否需要记忆
- **为什么有这个选择**：prompt 组装阶段注入可以确保记忆在 LLM 调用前稳定存在，避免记忆检索消耗额外的 LLM 调用；代价是注入时机固定，无法在对话中途动态补充

---

- **维度**：Extension Points
- **选择**：`registerMemoryCapability` 为独占槽位，底层实现（SQLite-vec、LanceDB 等）完全可替换
- **替代方案**：内置固定的向量存储实现，不开放替换
- **为什么有这个选择**：不同部署环境对记忆后端的要求差异大（本地轻量 vs 外部引擎），独占可替换设计让高级用户可以接入专业向量数据库，同时保持默认内置方案开箱即用

---

- **维度**：Dependency Strategy
- **选择**：内置 backend 使用 `sqlite-vec`（SQLite 向量扩展，native addon，精确版本锁定）
- **替代方案**：使用纯 JS 向量搜索库，避免 native addon 依赖
- **为什么有这个选择**：SQLite 已是 OpenClaw 的持久化基础设施（task flow、cron 等），向量扩展复用已有依赖；native addon 性能更优；精确锁定避免 native 编译版本不兼容
