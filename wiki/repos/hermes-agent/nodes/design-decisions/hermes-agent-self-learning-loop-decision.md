---
node_type: DesignDecision
scope: system
sources:
  - agent/prompt_builder.py:145-171
extracted_from:
  - architecture
---

# 自学习闭环内建于 system prompt

三段驱动指令（MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE）写入 system prompt，推动 LLM 在三个时间尺度自主改进：实时（memory 工具持久化事实）、跨会话（session_search 检索 FTS5 历史）、代际（skill_manage 积累技能库）。与 OpenClaw 的关键差异：OpenClaw 有 skills 和 memory 机制但无自驱动指令，创建/改进/回忆需人类触发；Hermes 让 agent 成为自驱动学习者。
^[agent/prompt_builder.py:145-171]

<!-- generated-wikilinks -->
## 关联

**催生了**（被此决策 motivates）：
- [[hermes-agent/nodes/components/hermes-agent-ai-agent]]
<!-- /generated -->
