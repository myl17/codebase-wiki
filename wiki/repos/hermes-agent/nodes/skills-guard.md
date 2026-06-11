---
node_type: Component
scope: subsystem
motivated_by: [layered-approval-decision]
sources:
  - tools/skills_guard.py:82-484
  - tools/skills_guard.py:595-639
---

# SkillsGuard

Skill 安全扫描器：100+ 威胁模式覆盖 12 类别（exfiltration/injection/destructive/persistence 等），按信任级别（builtin/trusted/community/agent-created）执行 allow/block/ask 策略。agent 自建技能落盘前必经此关——是自学习闭环的安全配套。
^[tools/skills_guard.py:595-639]
