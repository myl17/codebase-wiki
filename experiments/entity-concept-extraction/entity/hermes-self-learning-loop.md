# 自学习闭环（Hermes Agent）

## 是什么 / 边界

自学习闭环是 Hermes 最核心的差异化机制，由写入 system prompt 的三段驱动指令（MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE）和三个配套工具（memory / session_search / skill_manage）共同构成。

它的边界是：通过 prompt 指令让 LLM 主动创建技能、记忆事实、搜索历史——这些行为都是 LLM 在完成正常任务过程中的自驱动副产品，不需要人类触发，也不是独立的后台进程。

不做：技能和记忆内容的执行（工具模块自己执行）、记忆数据的持久化存储（MemoryManager 负责）、会话历史的建立（session 管理负责）。

## 关键实现

- 三段驱动指令：`agent/prompt_builder.py:145-171`
  - MEMORY_GUIDANCE（:145-156）：用户纠正/分享偏好时主动保存
  - SESSION_SEARCH_GUIDANCE（:158-162）：提及过去对话时主动搜索
  - SKILLS_GUIDANCE（:164-171）：完成复杂任务（5+ tool calls）后主动创建技能
- skill_manage 工具：`tools/skill_manager_tool.py:1-30`（create/edit/patch/delete）
- memory 工具：`tools/memory_tool.py:513-559`（add/replace/remove，写入 MEMORY.md/USER.md）
- session_search 工具：`tools/session_search_tool.py`（SQLite FTS5 全文搜索 + LLM 即时摘要）
- 技能注入：`agent/prompt_builder.py:449-453`，`build_skills_system_prompt()` 在每次会话启动时注入所有 SKILL.md
- 记忆注入：`agent/memory_manager.py`，`build_memory_context_block()` 注入当前相关记忆

三层时间尺度：
- 实时层：memory 工具每轮对话后写入，同一会话后续立即生效
- 跨会话层：session_search 搜索 FTS5 索引历史，用户无需重复
- 代际层：skill_manage 创建 SKILL.md，越用越能干

## 设计选择记录

- **维度**：Architecture
- **选择**：自学习行为通过 system prompt 驱动指令触发，而非独立后台进程或定时任务
- **替代方案**：每次会话结束后运行独立后台进程分析对话、提取技能和记忆
- **为什么有这个选择**：将学习行为内嵌到 agent 决策流程中，LLM 能在正确时机（刚完成复杂任务时）主动创建技能，时机比后台批处理更准确；同时不需要额外的分析模块

---

- **维度**：Architecture
- **选择**：技能以 SKILL.md markdown 文件存储，在每次会话启动时全量注入 system prompt
- **替代方案**：技能存入向量数据库，每次会话按相关性检索后注入
- **为什么有这个选择**：技能数量通常较少（用户个人技能库），全量注入简单可靠，不依赖向量搜索基础设施；全量注入也保证 agent 能看到所有技能，不遗漏低频但关键的技能

---

- **维度**：Extension Points
- **选择**：skill_manage 支持 patch 操作（agent 发现技能过时时就地修复）
- **替代方案**：技能只能由人类编辑，agent 无法修改已有技能
- **为什么有这个选择**：技能会随环境变化（工具版本升级、API 变更）而过时；允许 agent 在使用中发现过时就立即 patch，避免无效技能积累
