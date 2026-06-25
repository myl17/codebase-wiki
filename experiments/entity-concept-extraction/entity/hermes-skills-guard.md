# SkillsGuard — 技能安全扫描（Hermes Agent）

## 是什么 / 边界

SkillsGuard 是外部技能安装前的静态安全扫描器，用 100+ 威胁模式覆盖 12 类安全风险，按四级信任策略（builtin/trusted/community/agent-created）决定放行、警告或阻止。

它只在技能安装阶段介入，不影响已安装技能的运行时执行，不扫描用户自己编写的技能（内置技能属于 builtin 信任级别，直接放行）。

## 关键实现

- 扫描入口：`tools/skills_guard.py:595-639`，`scan_skill()`
- 100+ 威胁模式（12 类别）：`tools/skills_guard.py:82-484`
  - exfiltration / injection / destructive / persistence / network / obfuscation / execution / traversal / mining / supply_chain / privilege_escalation / credential_exposure
- 信任策略矩阵：`tools/skills_guard.py:39-48`

  | 信任级别 | Safe | Caution | Dangerous |
  |---|---|---|---|
  | builtin | allow | allow | allow |
  | trusted（openai/anthropics） | allow | allow | block |
  | community | allow | block | block |
  | agent-created | allow | allow | ask |

- 安装流程：Hub 下载 → `skills/.hub/quarantine/` → 扫描 → 通过后安装到 `skills/<name>/`
- agentskills.io 开放标准，与 Claude Code / Codex CLI 互操作

## 设计选择记录

- **维度**：Architecture
- **选择**：静态扫描 100+ 威胁模式，分四级信任策略而非单一通过/阻止
- **替代方案**：统一标准扫描，全部通过或全部阻止
- **为什么有这个选择**：不同来源技能风险不同，builtin 技能由项目维护者保证，无需扫描；community 技能来自不可信第三方，更严格；agent-created 技能由自身 agent 产生，需要询问但默认信任

---

- **维度**：Dependency Strategy
- **选择**：外部技能经过隔离区（quarantine）暂存后再安装，扫描通过才移出
- **替代方案**：直接安装，安装后再扫描
- **为什么有这个选择**：隔离区确保未经验证的技能不会在扫描期间被意外执行，扫描失败可以直接删除隔离区文件不影响已安装技能

---

- **维度**：Testing Philosophy
- **选择**：100+ 规则用于边界条件专项测试（如 test_sql_injection.py），规则本身是测试覆盖的重点
- **替代方案**：只测试整体扫描函数的输入输出，不分类测试各规则
- **为什么有这个选择**：安全规则覆盖的边界条件（如变体绕过）需要专项测试才能发现；行为测试而非实现测试的哲学在安全模块中尤为重要
