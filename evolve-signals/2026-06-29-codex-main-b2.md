# 演化信号 — codex-main（B2 @ Strategy C）

**日期**：2026-06-28
**来源**：codex-main Step 3 问题空间匹配（Strategy C, 518 concepts）
**信号数量**：2

---

## 信号 1：plugin-system — 粒度不匹配

- **问题**：如何建模插件包的标识、能力和钩子元数据
- **来源 Entity**：plugin-system
- **相关 Concept**：skills-extension-mechanism, tool-lifecycle-management
- **信号类型**：粒度不匹配
- **理由**：codex-main 的 PluginId（namespace/name 格式）、PluginCapabilitySummary（能力声明：skills/MCP server/App connector）和 PluginProvider（来源抽象：本地目录/远程 registry/内置 bundle）与 skills-extension-mechanism 的"技能来源多样性"关切部分重叠——两者都定义扩展单元的标识和来源。但 plugin-system 覆盖了额外的设计维度：二进制插件的能力声明（声明自己是 MCP server 还是 skill）、钩子契约（PluginHookDeclaration/PluginHookSource）——这些是 skills-extension-mechanism 未覆盖的独立设计空间。
- **跨仓库信号**：openclaw 的 plugin-sdk（core-plugin 稳定边界）和 plugin-system（发现-加载-验证）同样涉及插件二进制扩展，与 skills 的声明式文件扩展形成不同的权衡维度。
- **建议演化动作**：评估是否从 skills-extension-mechanism 中拆分出独立的 "plugin-architecture" Concept，将"声明式配置文件扩展"（skills）与"二进制/包扩展"（plugins）分开讨论。拆分需通过 /evolve-apply 的三条硬门槛前置判断。

---

## 信号 2：plugin-management — 粒度不匹配

- **问题**：如何管理插件商城、安装、升级和卸载
- **来源 Entity**：plugin-management
- **相关 Concept**：skills-extension-mechanism, tool-lifecycle-management
- **信号类型**：粒度不匹配
- **理由**：codex-main 的 PluginsManager（统一生命周期管理）、ConfiguredMarketplace（商城抽象：openai-curated/openai-bundled/custom）和 startup_sync（启动时同步商城列表）与 skills-extension-mechanism 的"安装自动化程度"关切部分重叠——两者都涉及从外部源安装扩展。但 plugin-management 覆盖了版本管理（upgrade/downgrade）、二进制兼容性检查、启动时同步——这些是 skills 管理体系中没有的设计维度。skills 的安装是文件复制（无版本管理），plugin 的安装涉及版本依赖和二进制安全校验。
- **跨仓库信号**：openclaw 的 plugin-system（插件全生命周期：发现-加载-验证-管理）同样涉及二进制插件的生命周期管理。两个仓库的 plugin 管理机制可以与 skills 的社区市场安装（hermes-agent 8 源联邦搜索）形成三叉对比：声明式文件安装 vs 二进制包安装 vs 联邦市场安装。
- **建议演化动作**：如果信号 1 触发了独立的 "plugin-architecture" Concept，此信号可直接作为该 Concept 的"安装与生命周期管理"子节处理。如果信号 1 未触发拆分，则此信号应作为 skills-extension-mechanism 的演进方向记录。
