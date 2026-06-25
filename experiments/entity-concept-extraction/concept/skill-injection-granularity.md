# skill-injection-granularity

## 问题陈述

如何在技能数量增长时平衡 LLM 可见性和 context window 消耗——全量注入 vs 完全不注入 vs 分级注入？

三个仓库对此问题给出了三个不同的答案，分别位于一条光谱上：**分级预算退化**（openclaw）、**紧凑索引 + 专用工具按需加载**（hermes）、**混合注入：always 全文 + 其余 XML 摘要**（nanobot）。没有一个仓库采用「全量注入所有技能全文」策略。

## 已知答案图谱

### 方案 A：三级预算退化（openclaw）

openclaw 的 `applySkillsPromptLimits()` (workspace.ts:560-606) 实现了一套三级降级机制，每级都由字符预算和数量上限驱动。

**默认预算常量**（workspace.ts:103-106）：
- `maxSkillsInPrompt`: 150（数量上限）
- `maxSkillsPromptChars`: 30,000（字符预算上限）
- 两者均可通过 `config.skills.limits` 覆盖

**三级降级流程**：

1. **Tier 1 — 完整格式**（`formatSkillsForPrompt`, skill-contract.ts:44-64）
   注入 XML 目录，每个技能包含 `<name>` + `<description>` + `<location>`。指令文本告诉 LLM：「Use the read tool to load a skill's file when the task matches its description」。如果字符总量在 `maxSkillsPromptChars` 内，直接使用。
   
2. **Tier 2 — 紧凑格式**（`formatSkillsCompact`, workspace.ts:538-555）
   同样数量的技能，但每个技能仅包含 `<name>` + `<location>`（去掉 description）。指令文本改为：「Use the read tool to load a skill's file when the task matches its name」。字符预算为 `maxSkillsPromptChars - 150`（预留紧凑模式警告行的开销）。此级**不丢弃任何技能**，仅降级格式。提示文本前置紧凑格式警告。
   
3. **Tier 3 — 截断**（workspace.ts:588-601）
   紧凑格式仍超出预算时，使用二分搜索找出能放入紧凑预算的最大前缀数量。剩余技能被丢弃，截断警告显示「included N of M skills」。

**关键设计细节**：
- 技能从 7 个来源按优先级合并：extra < bundled < managed < agents-skills-personal < agents-skills-project < workspace（workspace.ts:478-496）。低优先级来源的同名技能被高优先级覆盖。
- 技能加载阶段也有 `maxSkillsLoadedPerSource`（默认 200）和 `maxSkillFileBytes`（默认 256KB）的上限。
- 技能文件本身**从不注入全文**——LLM 必须用 `read_file` 工具按需加载。

### 方案 B：紧凑索引 + 专用工具按需加载（hermes）

hermes 的 `build_skills_system_prompt()` (prompt_builder.py:583-808) 构建一个**分类组织的紧凑索引**，仅包含 name + description，不含路径。LLM 通过专用工具 `skill_view(name)` 按需获取完整内容。

**索引格式**（prompt_builder.py:777-799）：
```
## Skills (mandatory)
Before replying, scan the skills below. If a skill matches ... you MUST load it with skill_view(name) ...

<available_skills>
  category_name: category description
    - skill_name: skill description
    - skill_name: skill description
</available_skills>
```

指令文本明确要求「Err on the side of loading」和「Only proceed without loading a skill if genuinely none are relevant to the task.」同时提示 LLM 可使用 `skill_manage(action='patch')` 修复有问题的技能。

**按需加载工具 `skill_view`**（skills_tool.py:804-）：
- 接受技能名称或带路径的名称（如 `"mlops/axolotl"`）
- 支持 `namespace:skill` 限定名（插件技能）
- 返回完整 SKILL.md 内容（JSON 包装，包含 success、content、description 等字段）
- 支持通过 `file_path` 参数读取技能目录内的子文件（references/api.md 等）
- 内置路径遍历防护（`has_traversal_component`）和注入模式检测（`_INJECTION_PATTERNS`）
- 平台过滤：按 frontmatter 中的 platforms 字段过滤不兼容技能
- 禁用技能列表：`get_disabled_skill_names()` 排除用户禁用的技能

**两层缓存**（prompt_builder.py:589-592, 623-704）：
1. **内存 LRU 缓存**：以 `(skills_dir, external_dirs, tools, toolsets, platform)` 为键，进程内复用
2. **磁盘快照**：`.skills_prompt_snapshot.json`，以 mtime/size 验证有效性，跨进程重启存活。冷路径时全量扫描文件系统并写入快照

**外部技能目录**（prompt_builder.py:706-740）：通过 `skills.external_dirs` 配置，只读挂载。本地技能同名时优先。

### 方案 C：混合注入——always 全文 + 其余 XML 摘要（nanobot）

nanobot 将技能分为两个层级处理，在 `ContextBuilder.build_system_prompt()` (context.py:46-54) 中按序组装：

**1. Always Skills — 全文注入**（context.py:46-50）：
标记 `always: true` 的技能（通过 frontmatter metadata 或顶层字段）通过 `load_skills_for_context()` 全文加载并注入 system prompt 的 `# Active Skills` 部分。内容经过 frontmatter 剥离（`_strip_frontmatter`），仅保留正文。各技能间以 `---` 分隔。

**2. Skills Summary — XML 摘要**（context.py:52-54）：
所有技能（包括 always skills）生成 XML 摘要，通过 `build_skills_summary()` (skills.py:109-142) 构建。格式：
```xml
<skills>
  <skill available="true|false">
    <name>...</name>
    <description>...</description>
    <location>/path/to/SKILL.md</location>
    <requires>CLI: cmd, ENV: VAR</requires>  <!-- 仅 unavailable 时 -->
  </skill>
</skills>
```

摘要注入到 `skills_section.md` 模板中，模板文本为：「To use a skill, read its SKILL.md file using the read_file tool. Skills with available="false" need dependencies installed first.」

**可用性检查**（skills.py:181-188）：通过 frontmatter 中 `requires.bins`（CLI 工具）和 `requires.env`（环境变量）检查技能的前置依赖是否满足。不满足的技能标记 `available="false"`。

**技能来源与优先级**（skills.py:52-71）：workspace 技能优先于 builtin 技能。同名时 workspace 覆盖 builtin。通过 `filter_unavailable` 参数控制是否过滤不可用技能。

**关键设计细节**：
- **无预算/截断机制**：XML 摘要始终包含所有技能，没有字符预算上限或降级逻辑
- **无缓存机制**：每次构建 system prompt 时都重新扫描文件系统
- **always 标记解析**（skills.py:195-205）：同时检查 `metadata.nanobot.always` 和顶层 `always` 字段，兼容两种 frontmatter 格式

## 跨仓库对比

| 维度 | openclaw | hermes | nanobot |
|------|----------|--------|---------|
| **注入内容** | XML 索引（name+desc+loc → name+loc） | 分类文本索引（name+desc only） | always: 全文；其余: XML 摘要 |
| **全文注入** | 从不 | 从不 | 仅 `always: true` 技能 |
| **按需加载方式** | `read_file` 通用工具 | `skill_view()` 专用工具 | `read_file` 通用工具 |
| **预算/降级** | 三级：完整→紧凑→截断 | 无（索引极紧凑） | 无（始终包含全部） |
| **缓存** | 无（按 run 重建） | 双层：LRU + 磁盘快照 | 无（按 build 重建） |
| **平台过滤** | 无 | 有（`skill_matches_platform`） | 无（仅前置依赖检查） |
| **外部来源** | 7 层优先级合并 | `external_dirs` 配置 | workspace + builtin |
| **字符预算默认值** | 30,000 chars / 150 skills | 无上限（索引自然紧凑） | 无上限 |
| **技能数量硬上限** | 150（可配置） | 无 | 无 |
| **注入安全** | XML 转义（`escapeXml`） | 注入模式检测 + 路径遍历防护 | XML 转义（`_escape_xml`） |

## 设计权衡

### 1. 索引紧凑度 vs 信息丰富度

hermes 的索引最紧凑（仅 name + 单行 description），因为 `skill_view()` 是 LLM 获取完整技能的唯一途径——索引中的 description 只需足够让 LLM 判断"这个技能是否相关"。openclaw 的完整格式包含 location 字段，为 `read_file` 提供路径。nanobot 的 XML 摘要信息最丰富（包含 availability 和依赖需求），但字符开销也最大。

### 2. 预算感知 vs 无预算

openclaw 是唯一有预算机制的实现，这是它作为**多租户网关**（服务多个 agent、多个 workspace）的必要设计——不同 workspace 可能各有大量技能。hermes 和 nanobot 面向单用户场景，索引/摘要的字符开销天生有限，无需预算控制。

### 3. 专用工具 vs 通用工具

hermes 使用专用的 `skill_view()` 和 `skills_list()` 工具，而非通用的 `read_file`。这带来几个优势：
- 返回结构化 JSON（success/content/description/linked_files），比原始 markdown 更易处理
- 内置安全防护（遍历检查、注入检测）
- 支持限定名（`plugin:skill`）、文件子路径指定、外部目录查找
- `skills_list()` 作为渐进披露的第一层，token 开销极小

代价是 LLM 必须学习专用工具的使用方式，而 `read_file` 是所有 agent 的通用能力。

### 4. always 技能的取舍

nanobot 的 always 技能全文注入是唯一将技能全文放入 system prompt 的机制。这适合少量**持续相关**的技能（如 memory、safety rules），但缺乏字符预算控制——如果过多技能标记 always，system prompt 可能膨胀失控。openclaw 和 hermes 选择了更保守的路径：永远不主动注入全文。

### 5. 缓存策略

hermes 的双层缓存是工程成熟度的体现：磁盘快照使冷启动无需重新扫描文件系统（只验证 mtime/size），内存 LRU 使热路径零开销。openclaw 和 nanobot 每次运行都重新扫描，这在技能数量较少时完全可接受。

## 溯源

### openclaw
- `src/agents/skills/workspace.ts:560-606` — `applySkillsPromptLimits()` 三级降级
- `src/agents/skills/workspace.ts:538-555` — `formatSkillsCompact()` 紧凑格式
- `src/agents/skills/skill-contract.ts:44-64` — `formatSkillsForPrompt()` 完整格式
- `src/agents/skills/workspace.ts:103-127` — 默认常量与 `resolveSkillsLimits()`
- `src/agents/skills/workspace.ts:478-496` — 7 层技能来源优先级合并
- `src/agents/skills/workspace.ts:680-697` — prompt 组装（警告 + 截断提示）

### hermes
- `agent/prompt_builder.py:583-808` — `build_skills_system_prompt()` 完整实现（缓存、快照、分类索引构建）
- `tools/skills_tool.py:647-712` — `skills_list()` 渐进披露第一层
- `tools/skills_tool.py:804-` — `skill_view()` 按需加载（限定名、遍历防护、注入检测、平台过滤）
- `tools/skills_tool.py:718-801` — `_serve_plugin_skill()` 插件技能服务
- `agent/prompt_builder.py:623-704` — 双层缓存机制（LRU + 磁盘快照）

### nanobot
- `nanobot/agent/skills.py:109-142` — `build_skills_summary()` XML 摘要构建（含可用性检查）
- `nanobot/agent/skills.py:92-107` — `load_skills_for_context()` 按需多技能加载
- `nanobot/agent/skills.py:195-205` — `get_always_skills()` always 标记解析
- `nanobot/agent/skills.py:181-188` — `_check_requirements()` 前置依赖检查（bins + env）
- `nanobot/agent/context.py:30-63` — `build_system_prompt()` 组装（always 全文 + summary）
- `nanobot/templates/agent/skills_section.md` — XML 摘要包装模板
