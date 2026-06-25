# Skills（nanobot）

## 是什么 / 边界
nanobot 的 Markdown 知识注入系统——`SKILL.md` 文件（带 YAML frontmatter metadata）存放在 `nanobot/skills/`（内建）和 `workspace/skills/`（用户自定义）两个位置。通过 always 全文注入和渐进式按需加载两种方式接入 system prompt。

**边界**：Skills 负责知识内容的存储、发现、注入。不做工具注册（ToolRegistry）、不做记忆管理（Memory System）、不做 agent 行为编排。

## 关键实现
- **双路径存储**：`nanobot/skills/`（内建，随发行版提供）→ `workspace/skills/`（用户自定义，覆盖同名内建）
- **两种加载策略**：
  - **Always Skills**：frontmatter 中 `always: true` 的技能在每次 system prompt 组装时全文注入
  - **渐进式加载**：其他技能以 XML 摘要形式出现在 system prompt 中（名称 + 描述 + 路径 + 可用性），agent 需要时通过 `read_file` 工具按需读取
- **依赖检查**：frontmatter 中的 `requires.bins` 和 `requires.env` 声明工具依赖性——不满足条件的技能自动标记为不可用，不出现在摘要中
- **零配置新增**：创建 `skills/<name>/SKILL.md` 文件即自动可被发现

## 设计选择记录
- **维度**：Extension Points
- **选择**：Skills 以 Markdown 文件为载体，通过 always 全文注入 + 按需 read_file 两种方式接入，不需要代码
- **替代方案**：Skills 作为 Python 模块或配置文件（如 openclaw 的 skill 定义方式），需要编程接口加载
- **为什么有这个选择**：Markdown 是 LLM 原生友好的格式——不需要额外的解析层。渐进式加载（摘要 → 按需 read_file）避免 system prompt 膨胀，同时保持所有技能可被发现。`requires` 依赖检查保证了不可用技能不会误导 agent
