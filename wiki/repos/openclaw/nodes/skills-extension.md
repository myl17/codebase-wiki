---
node_type: ExtensionPoint
scope: component
concept_candidate: 声明式行为定制
targets: [context-engine]
sources:
  - src/agents/skills.ts:8-39
---

# Skills 扩展

独立于 plugin 系统的最轻量扩展点：用户在工作区放置 Markdown 技能文件，`buildWorkspaceSkillsPrompt` 将其注入 agent system prompt，`buildWorkspaceSkillCommandSpecs` 把技能文件中的命令 spec 注册为可用命令。不需要代码，纯 Markdown 即可定制 agent 行为。
^[src/agents/skills.ts:8-39]

<!-- generated-wikilinks -->
## 关联

**作用于**（targets）：
- [[openclaw/nodes/context-engine]] — 改动会波及此组件
<!-- /generated -->
