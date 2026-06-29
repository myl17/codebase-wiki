# 演化信号 — codex-main（B3 @ Strategy C）

**日期**：2026-06-29
**来源**：codex-main Step 3 问题空间匹配（Strategy C, 1018 concepts）
**信号数量**：2

---

## 信号 1：plugin-system — 粒度不匹配（候选合并）

- **问题**：如何建模插件包的标识、能力和钩子元数据
- **来源 Entity**：plugin-system
- **相关 Concept**：skills-extension-mechanism, tool-lifecycle-management
- **信号类型**：粒度不匹配

- **理由**：codex-main 的 PluginId（namespace/name 格式）、PluginCapabilitySummary（能力声明：skills/MCP server/App connector）和 PluginProvider（来源抽象：本地目录/远程 registry/内置 bundle）构成独立的"二进制扩展包的元数据模型"设计空间。Round 1 grep（`plugin.*id\|plugin.*capabilit\|plugin.*metadata`）和 Round 2 扩展 grep（`plugin.*namespace\|capability.*declar\|能力.*声明\|二进制.*扩展`）均未命中语义匹配的独立 Concept——此设计空间介于 skills-extension-mechanism（关注声明式 Markdown 技能文件的安装和注入）和 tool-lifecycle-management（关注工具注册/发现/过滤）之间，未被现有 Concept 覆盖。

- **跨仓库信号**：openclaw 的 plugin-sdk（core-plugin 稳定边界）和 plugin-system（发现-加载-验证）同样涉及二进制插件扩展，与 skills 的声明式文件扩展形成不同的权衡维度。codex-main、openclaw 两个仓库均存在独立的插件二进制扩展机制，说明这不是单仓库特有设计。

- **信号历史**：此信号在 B1（2026-06-28）首次识别为 D "候选合并"，B2（2026-06-29）沿袭并升级为"建议拆分为独立 plugin-architecture Concept"。B3 在 1018 个 Concept 规模下再次确认：两轮 grep 后仍无独立 Concept 匹配，Rounds 1+2 共触发 33 个文件（18 真实 + 15 distractor），无一个语义匹配。现有 Concept 覆盖面有缺口。

- **建议演化动作**：评估是否从 skills-extension-mechanism 中拆分出独立的 "plugin-architecture" Concept，将"声明式配置文件扩展"（skills）与"二进制/包扩展"（plugins）分开讨论。拆分需通过 /evolve-apply 的三条硬门槛前置判断。

---

## 信号 2：plugin-management — 粒度不匹配（子维度扩展）

- **问题**：如何管理插件商城、安装、升级和卸载
- **来源 Entity**：plugin-management
- **相关 Concept**：skills-extension-mechanism, tool-lifecycle-management
- **信号类型**：粒度不匹配

- **理由**：codex-main 的 PluginsManager（统一生命周期管理）、ConfiguredMarketplace（商城抽象：openai-curated/openai-bundled/custom）和 startup_sync（启动时同步商城列表）与 skills-extension-mechanism 的"技能来源多样性"和"安装自动化程度"关切部分重叠。但 plugin-management 覆盖了技能（Skills）管理体系没有的设计维度：版本管理（upgrade/downgrade 命令）、二进制兼容性校验、启动时商城同步——Skills 安装只是文件复制（无版本追踪），Plugin 安装涉及版本依赖解析和二进制安全校验。Round 1 grep 命中 skills-extension-mechanism（`plugin.*marketplace\|plugin.*install\|plugin.*manag` 匹配 "plugin" 词），但语义不匹配——Concept body 聚焦于 Markdown Skills 文件的 Quarantine 安装和信任分级，未涉及二进制包的版本管理与商城同步。

- **跨仓库信号**：openclaw 的 plugin-system（插件全生命周期：发现-加载-验证-管理）同样涉及二进制插件的生命周期管理。两个仓库的 plugin 管理机制可以与 skills 的社区市场安装（hermes-agent 8 源联邦搜索）形成三叉对比：声明式文件安装 vs 二进制包安装 vs 联邦市场安装。

- **信号历史**：B1 将此条标记为 D "粒度不匹配"（建议作为 skills-extension-mechanism 实例追加），B2 沿袭。B3 维持此判断。

- **建议演化动作**：若信号 1 触发了独立的 "plugin-architecture" Concept，此信号可直接作为该 Concept 的"分发与版本管理"维度的子节处理。若信号 1 未触发拆分，则此信号应作为 skills-extension-mechanism 的演化方向记录——在现有 body 中增补"从 Skills 到 Plugins：能力打包与分发"子维度讨论，纳入 codex-main 和 openclaw 的插件商城管理方案。
