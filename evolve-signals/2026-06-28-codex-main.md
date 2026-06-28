# 演化信号 — codex-main

生成日期：2026-06-28
来源：Step 3 问题空间匹配，codex-main vs 已有 16 个 Concept 页

---

## D1：Plugin System 与 Skills Extension 的边界模糊

- **问题**：如何建模插件包的标识、能力和钩子元数据
- **相关 Concept**：skills-extension-mechanism
- **信号类型**：候选合并
- **理由**：PluginId 标识符 + PluginCapabilitySummary 多能力声明 + PluginProvider 来源抽象这些概念介于 skills-extension-mechanism（关注单 Skill 的安装/注入）和 tool-lifecycle-management（关注单工具的注册/过滤）之间。当前 skills-extension-mechanism 的 concerns 未明确区分"技能作为行为单元"和"插件作为能力包"，建议在 skills-extension-mechanism 中增加"插件打包与分发"的子维度讨论。
- **建议操作**：在 skills-extension-mechanism.md 中新增"插件作为能力包"子节，将 codex-main 和 openclaw 的插件元数据模型作为实例追加

---

## D2：Plugin Marketplace 管理是 Skills 来源的子维度

- **问题**：如何管理插件商城、安装、升级和卸载
- **相关 Concept**：skills-extension-mechanism
- **信号类型**：粒度不匹配
- **理由**：商城生命周期管理（ConfiguredMarketplace + PluginsManager + startup_sync）是 skills-extension-mechanism 中"来源多样性"和"安装自动化程度"两个 concerns 的具体展开。当前 skills-extension-mechanism 已经覆盖了这些 concerns，plugin-management 的实现细节可以作为 codex-main 对该 Concept 的实例贡献追加，无需独立成页。
- **建议操作**：在 skills-extension-mechanism.md 的 codex-main 实例中，详细记录双商城源 + 启动同步 + 远程 bundle 下载的实现方案
