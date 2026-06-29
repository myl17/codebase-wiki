---
title: Claude Code开发模式详解
category: codebase
depth: representation
tags: [claude-code, plugin, hooks, skills, superpowers]
created: 2026-06-05
updated: 2026-06-05
sources:
  - ~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/hooks/hooks.json
  - ~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/hooks/run-hook.cmd
  - ~/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/hooks/session-start
  - https://github.com/AgriciDaniel/claude-obsidian
---

# Claude Code 开发模式详解

## 一、Claude Code 插件是什么

Claude Code 允许通过插件系统扩展其行为。一个插件包含两个核心组件：

**1. Skills（技能文件）**：Markdown 文件，告诉 Claude "在什么情况下做什么"。放在 `.claude/skills/` 目录下，Claude Code 启动时自动发现。

**2. Hooks（生命周期钩子）**：在 Claude Code 的特定生命周期节点执行自定义操作。定义在 `hooks/hooks.json` 中。

一个典型的 Claude Code 插件目录结构：
```
.claude-plugin/
  plugin.json              # 插件元数据
hooks/
  hooks.json               # 生命周期钩子定义
skills/
  my-skill/
    SKILL.md                # 技能指令
    references/             # 参考文档
scripts/                    # 独立脚本（可选）
```

---

## 二、Skills：给 Claude 的操作手册

### Skill 文件长什么样

一个 Skill 是一个 Markdown 文件，前面带 YAML frontmatter 描述触发条件：

```markdown
---
name: wiki-ingest
description: >
  当用户想要将文档摄入 wiki 时使用此技能。
  触发条件：用户说 "add this to the wiki"、"ingest this"、"/wiki-ingest" 等。
---

# Wiki Ingest

## 步骤 1：读取源文件
使用 Read 工具读取源文件内容。

## 步骤 2：提取知识
从源文件中识别：核心概念、实体、声明、关系、开放问题。

## 步骤 3：写入 wiki 页面
创建或更新 wiki 页面，更新 index.md 和 log.md。

## 注意事项
- raw/ 目录下的文件只读不写
- 每个页面必须有 frontmatter
- ...
```

### Skill 如何被执行

1. Claude Code 启动时扫描 `.claude/skills/` 下所有 `SKILL.md` 文件
2. 读取每个 Skill 的 `name` 和 `description` 字段
3. 将这些信息注入到 system prompt（系统提示词）中
4. 当用户说的话匹配某个 Skill 的 description 时，Claude 自动调用 `Skill` 工具加载该 Skill 的完整指令
5. Claude 按照 Skill 文件中的步骤执行操作

### 为什么 Skill 是一种强大的抽象

- **不需要写代码**：纯 Markdown 文件定义行为
- **可跨 Agent 复用**：obsidian-wiki 的同一个 Skill 文件可以被 Claude Code、Cursor、Codex、Gemini 等不同的 Agent 读取执行
- **可读可维护**：Skill 文件本身就是文档，人可以直接阅读和修改
- **版本管理和分发**：Skill 文件可以用 Git 管理，用 PyPI 分发

### Skill 的局限性

- **执行质量依赖 Claude 的理解能力**：没有程序化验证——同上一个 wiki-ingest 命令，每次 Claude 可能用不同的方式实现同一个步骤
- **没有状态管理**：Skill 文件本身不维护状态（比如"哪些源文件已经 ingest 过了"），需要 Claude 自己去读 manifest 文件来判断
- **不可组合**：每个 Skill 是独立的，没有 Skill A → Skill B 的链式调用
- **慢**：每次执行一个 Skill，Claude 需要读完整个 SKILL.md 再读所有相关文件再执行操作，token 消耗大

---

## 三、Hooks：在 Claude Code 生命周期中注入行为

### Claude Code 的生命周期事件

| 事件 | 触发时机 | 有什么用 |
|------|---------|---------|
| `SessionStart` | 会话启动或恢复时 | 注入初始上下文；告诉 Claude "你是 wiki 维护者" |
| `PreToolUse` | Claude 调用任何工具之前 | 拦截危险操作；添加策略约束 |
| `PostToolUse` | Claude 调用任何工具之后 | 自动 commit wiki 变更（git add + commit） |
| `PostCompact` | 上下文被压缩后 | 重新注入被压缩掉的关键信息 |
| `Stop` | 会话结束时 | 提醒用户有未 commit 的 wiki 修改 |

### Hook 的两种类型

**`type: "command"`（命令钩子）**：执行一个系统命令，stdout 的输出可以被 Claude Code 捕获和使用。

```json
{
  "type": "command",
  "command": "[ -f wiki/hot.md ] && cat wiki/hot.md || true"
}
```

Claude Code 会：
1. 在对应的生命周期节点执行这个 shell 命令
2. 捕获 stdout 输出
3. **但不保证将 stdout 注入到 LLM 的上下文窗口中**

要在 SessionStart 时向 LLM 注入上下文，命令钩子需要输出特定格式的 JSON：

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "这是要注入到 Claude 上下文的文本"
  }
}
```

**`type: "prompt"`（提示词钩子）**：期望直接向 LLM 的 prompt 中注入一段文本。

```json
{
  "type": "prompt",
  "prompt": "如果你在 wiki 目录中，请默默读取 wiki/hot.md 恢复上下文。"
}
```

**关键约束：** prompt hook 只支持 PreToolUse 和 PostToolUse 两个事件——这两个事件有 `ToolUseContext`（包含当前正在被使用的工具的信息）。`SessionStart` 和 `PostCompact` 没有工具调用上下文，所以 **prompt hook 在这些事件上不可用**。这是 Claude Code 的明确设计限制。

### 输出注入的正确姿势：`hookSpecificOutput.additionalContext`

这是 Claude Code 官方支持的在生命周期事件中注入上下文的机制：

```bash
# 在 SessionStart 时执行脚本
# 脚本输出一个 JSON 对象，其中 hookSpecificOutput.additionalContext 包含要注入的文本
printf '{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "<EXTREMELY_IMPORTANT>你是 wiki 维护者。当前 wiki 状态：...</EXTREMELY_IMPORTANT>"
  }
}\n'
```

Claude Code 收到这个 JSON 后：
1. 提取 `additionalContext` 字段的值
2. 将它追加到当前 session 的 system prompt 中
3. Claude 在后续对话中可以看到这段上下文

---

## 四、Superpowers vs claude-obsidian：好的实现 vs 有问题的实现

### Superpowers 的做法（正确示范）

**hooks/hooks.json**（仅 21 行）：
```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|clear|compact",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd session-start",
        "async": false
      }]
    }]
  }
}
```

只做了一件事：在 SessionStart 时，执行 `run-hook.cmd session-start` 这个脚本。

**session-start 脚本**（58 行 Bash）的核心逻辑：
1. 读取 `using-superpowers/SKILL.md` 的内容（用 `cat`）
2. 将内容进行 JSON 转义（处理 `"`、`\n` 等特殊字符）
3. 根据运行平台输出对应格式的 JSON：
   - Claude Code → 输出 `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`
   - Cursor → 输出 `{"additional_context":"..."}`
   - Copilot CLI → 输出 `{"additionalContext":"..."}`
4. 注入的文本是一个包裹在 XML 标签中的完整 Skill 内容：`<EXTREMELY_IMPORTANT>You have superpowers. **Below is your using-superpowers skill:** [skill内容]</EXTREMELY_IMPORTANT>`

**这个做法的优良品质：**
- hooks.json 极简——只有 21 行，不包含任何业务逻辑
- 所有逻辑在独立的 Bash 脚本中——可测试、可调试、可版本控制
- **只用 command hook**——不使用 prompt hook，避免了 ToolUseContext 依赖问题
- **正确使用 hookSpecificOutput.additionalContext**——这是 Claude Code 官方支持的标准注入路径
- 跨平台兼容（run-hook.cmd 是一个 polyglot 脚本，同时支持 Windows cmd.exe 和 Unix bash）
- async: false——确保脚本执行完毕后再开始处理用户输入

### claude-obsidian 的做法（问题所在）

**hooks/hooks.json**（80+ 行）包含：
- SessionStart：3 个子 hook（1 个 cat + 1 个 lock clear + **1 个 prompt**）
- PostCompact：**1 个 prompt hook**
- PostToolUse：1 个 git auto-commit
- Stop：1 个 change detection

**三个问题：**

**问题 1：在 SessionStart 上使用 prompt hook。** Claude Code 不允许——SessionStart 没有 ToolUseContext。从 v2.1.140 开始明确拒绝并报错。6 个不同的用户在不同版本下报告了同一个问题。

**问题 2：靠 `cat wiki/hot.md` stdout 注入上下文。** Claude Code **不保证** command hook 的 stdout 会被注入到模型上下文中——有些版本可以、有些不行。这导致了间歇性的"hot cache 不生效"问题。

**问题 3：在 hooks.json 内联复杂命令。** PostToolUse 的 auto-commit 命令是一个 300+ 字符的单行 shell 管道——不可读、不可调试、修改时容易出错。

### 一句话对比

```
Superpowers:  hooks.json 是薄薄的调度层 → 逻辑在独立脚本里
claude-obsidian: hooks.json 承载了全部业务逻辑 → 一坨 shell 命令嵌在 JSON 里
```

---

## 五、如果要基于 Claude Code 做 Code Wiki

### 推荐架构

```
code-wiki-plugin/
├── hooks/hooks.json          # 仅 SessionStart 注入上下文（学 Superpowers）
├── hooks/session-start.sh    # 独立的上下文注入脚本
├── skills/
│   ├── code-ingest/SKILL.md  # 告诉 Claude 如何摄入代码仓库
│   ├── code-query/SKILL.md   # 告诉 Claude 如何查询 wiki
│   └── code-lint/SKILL.md    # 告诉 Claude 如何检查 wiki 健康
├── scripts/                   # 核心 Python/TypeScript 脚本
│   ├── delta.py               # 计算变更：根据 content hash 判断哪些文件要更新
│   ├── manifest.py            # 管理 .manifest.json（记录每次 ingest 的状态）
│   ├── lint.py                # 程序化的 lint 规则（不依赖 Claude 每次自己发明）
│   └── eval.py                # 质量评分（health score）
└── schema.md                  # wiki 的结构和规则
```

### 职责划分

```
Skill 文件负责：
  ✅ "怎么读源码才能提取出有价值的表征"（三步法 + 维度表）
  ✅ "页面应该怎么写"（frontmatter 规范、结构模板）
  ✅ "处理用户对话"（讨论发现、等待确认）
  ❌ 不做：计算文件 hash、判断哪些文件变了、检查 wikilink 是否断裂

scripts/ 负责：
  ✅ "哪些源文件自上次 ingest 后变了"（delta.py）
  ✅ "这 300 个文件里只有 5 个是新/改的，只看这 5 个"（manifest.py）
  ✅ "wiki 里有 12 个死链需要修复"（lint.py）
  ✅ "wiki 健康分从 85 跌到 72，原因是 X"（eval.py）
  ❌ 不做：理解源码含义、写 wiki 页面、和用户讨论

hooks 负责：
  ✅ Claude session 启动时注入 wiki 状态上下文
  ✅ 仅用 command + hookSpecificOutput.additionalContext（学 Superpowers）
  ❌ 不做：承载业务逻辑
```

### 这条路的好处

- **一周内跑通端到端**：Skills 定义行为，脚本处理状态，比从头写 CLI 快得多
- **可以逐步重写**：初期用 Skill 做原型验证，确认后再把稳定逻辑迁移到脚本
- **分发成本低**：Claude Code 插件 marketplace 一键安装
- **不锁定 Claude Code**：脚本是独立的 Python/TS，如果以后要做独立 CLI，脚本可以直接复用

### 这条路的风险

- Claude Code 的行为不是 100% 可预测的——同一个 Skill、同样的输入，Claude 两次可能用略微不同的方式执行
- 如果 Claude Code 的 hook API 变化，需要更新 hooks.json（但影响面有限，因为核心逻辑不在 hooks 里）

---

## 六、Hook 和 Skill 是两个独立的系统

### 常见的误解

很多用户（包括 claude-obsidian 的大量 open issue 的提问者）把两件事搞混了：

```
误解："我装了这个插件，为什么有时候生效、有时候不生效？"
真相：SessionStart hook 每次会话都生效，但不代表某个技能每次都被调用。
```

### Hook 的工作方式：一定会执行的

Hook 定义在 `hooks/hooks.json` 中，是**强制性的**。SessionStart hook 在每个会话开始时必定执行。Superpowers 只用了这一个 hook——在每次会话启动时，把一个 "using-superpowers 技能在这里" 的提示词注入到 Claude 的上下文中。

```
每次会话 → SessionStart hook → 注入技能目录/使用说明 → Claude 知道自己有哪些技能
```

这个步骤 100% 执行，不会有例外。

### Skill 的工作方式：模型自己决定

每个技能文件有一个 `description` 字段：

```
writing-plans:        "Use when you have a spec or requirements for a multi-step task"
systematic-debugging: "Use when encountering any bug, test failure, or unexpected behavior"
test-driven-development: "Use when implementing any feature or bugfix, before writing implementation code"
```

Claude Code 把这些 `description` 全部列在 system prompt 中。当用户输入和某个描述匹配时，**模型自己判断要不要调用对应的技能**。

```
不是：if 用户说"修bug" → 调用 systematic-debugging
而是：Claude 读用户输入 → Claude 自己判断 → "这次需要 systematic-debugging 吗？"
```

### 为什么修 bug 时 system-debugging 可能不触发

三个因素共同作用：

**1. 任务复杂度**

```
"实现登录模块"                    → 模型判断：大任务，需要计划
                                  → 触发 writing-plans
                                  
"按钮颜色不对，改成蓝色"           → 模型判断：一行 CSS，不需要流程
                                  → 所有技能被跳过，直接写代码
```

模型在判断技能是否适用时，会评估任务的规模。一个看起来"一句话就能修"的 bug，模型可能认为不需要系统性的排查流程。

**2. 描述本身的匹配精度**

`systematic-debugging` 的描述是 "Use when **encountering** any bug, **before** proposing fixes"。关键词是 "encountering" + "before proposing fixes"——这暗示了一个时间窗口：刚发现的、还没开始修的 bug。如果你已经描述了 bug 的根因并给了修复方向，模型可能判断 "这个窗口已经过了"。

**3. 模型不确定性**

同一个输入、同一个模型、同一组技能描述——跑两次可能结果不同。因为 Skill 调用本质上是 LLM 做自然语言理解，不是程序化的规则匹配。温度非零时，有概率波动。

### 一个思维实验

把 Superpowers 想象成工具腰带：

```
SessionStart hook = 帮你把腰带系上       → 必然发生
Skill 描述 = 每个口袋上的标签            → 提示里面有什么
Skill 调用 = 你伸手去掏工具             → 模型自己决定要不要掏
```

当你说"做一个登录功能"——模型看看标签："writing-plans — multi-step task"——掏出来用。当你说"这个 bug 修一下"——模型看看标签，没找到完全匹配的——直接干了。

**不是腰带没系。是模型觉得这个活儿不用掏工具。**

### 这对做 Code Wiki 插件意味着什么

你不能靠 Skill 描述来保证 Code Wiki 功能每次都被触发。更好的做法是：

- **核心功能做成用户主动触发的命令**（`/code-ingest`、`/code-query`）——而不是依赖模型自动判断
- Hook 用于非侵入式的上下文注入（SessionStart 时注入 wiki 状态摘要）
- 在 `CLAUDE.md` 中明确告诉 Claude：每次操作 wiki 相关文件后更新 hot cache

## 关联

- [[llm-wiki-ecosystem-comparison]] — 三大项目实时数据对比
- [[codebase-wiki-methodology]] — 代码仓库知识提取方法论
