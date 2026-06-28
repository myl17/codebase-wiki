# Codebase-Wiki 项目进展报告

> 生成日期：2026-06-28
> 覆盖范围：2026-06-08 ~ 2026-06-28 的全部会话

---

## 一、项目当前状态

### 规模数据

| 指标 | 数值 |
|------|------|
| 已 ingest 仓库 | 3（nanobot, hermes-agent, openclaw） |
| Entity 页 | 64（20 + 24 + 20） |
| Concept 页 | 15 |
| Seeds（problem-map） | 3 个文件，共 52 条问题空间条目 |
| Evolve signals | 0（2 条已处理） |
| Lint 通过 | ✓ 零错误 |
| 工作分支 | `feat/experiment-deepwiki-vs-src` |

### 仓库覆盖

| 仓库 | Entity 数 | entity_map 完整 | 首次 ingest |
|------|----------|----------------|-------------|
| nanobot | 20 | ✓（20 entries） | 2026-06-25 |
| hermes-agent | 24 | ✓（24 entries） | 2026-06-25 |
| openclaw | 20 | ✓（20 entries） | 2026-06-25 |

---

## 二、已完成操作清单

### 2.1 架构迁移（已完成）

旧五维度体系 → 新 Entity → Problem Space → Concept 管线。

| 提交 | 内容 |
|------|------|
| `f793855` | 删除 legacy dimensions/nodes/entities |
| `57433a9` | 重写 /ingest SKILL.md（6-step pipeline） |
| `f457d74` | 重写 /query, /compare, /lint SKILL.md |
| `8a2a387` | 新增 /evolve-apply skill |
| `ab4ed17` | 新增 concept-criteria.md（四条准则） |
| `785ef41` | 重写 lint.py，删除 dead scripts |
| `1b62b59` | Phase 0 修复 + --auto 开关 + 用户指令分析逻辑 |

### 2.2 基础设施修复（已完成）

| Fix | 内容 | 状态 |
|-----|------|------|
| 1 | plugin.json `analyze`→`ingest`，新增 `evolve-apply` | ✓ |
| 2 | commands/ symlinks 更新（ingest.md, evolve-apply.md） | ✓ |
| 3 | session-start.sh 重写 | ✗ **未完成** |
| 4 | /ingest SKILL.md 新增 `--auto` 开关 | ✓ |
| 5 | /evolve-apply SKILL.md 新增 `--auto` 开关 | ✓ |
| 6 | /compare SKILL.md 新增 `--auto` 开关 | ✓ |
| 7 | /evolve-apply 新增"用户直接指令的合理性分析"逻辑 | ✓ |
| 8 | `docs/evolve-signals/` → `evolve-signals/` 目录迁移 | ✓ |

### 2.3 Bug 修复

| Bug | 根因 | 修复 |
|-----|------|------|
| 50+ broken wikilinks | lint.py 只做 exact-match 解析 | 5 策略 resolution（exact/relative/prepend repos/prepend concepts/suffix match） |
| Orphan checker 失效 | 同上 | `_page_aliases()` + `_is_linked()` 多策略匹配 |
| hermes-agent-problem-map 错位 | Subagent 写到了 `wiki/repos/hermes-agent/seeds/` | 删除错位文件，SKILL.md 新增"路径纪律"节，lint.py 新增 `check_pipeline_file_placement` |
| entity_map 始终为空 | SKILL.md Step 6 从未指示填充 entity_map | Step 6 新增 4 行指令，三个仓库回填 |
| hermes-agent 2 个 broken wikilink | Entity 页链向不存在的 entity（checkpoint-manager, insights-system） | 改为纯文本 |

### 2.4 测试

| 场景 | 测试方法 | 结果 |
|------|---------|------|
| Scenario E（re-ingest 增量） | 全链路盲测：修改 openclaw 源码注释 → re-ingest | PASS — 正确识别"注释变更 ≠ 知识变更"，不修改任何 entity/concept |
| Scenario G（evolve-apply --auto） | 盲测：2 条信号 → 前置判断 → 执行 | PASS — 正确识别为粒度不匹配，在 Concept 页追加子维度观察 |
| lint.py 14 个测试 | pytest | 全部通过 |

---

## 三、未完成事项

### 3.1 基础设施遗留

| 事项 | 影响 | 优先级 |
|------|------|--------|
| session-start.sh 未重写 | 新会话启动时仍引用已删除的 `manifest.py stale` | 高 |

### 3.2 待执行场景测试（均需用户终端交互）

| 场景 | 测试内容 | 依赖 |
|------|---------|------|
| A | 暂停点用户否决 Concept | 用户真实介入 |
| B | ingest 中嵌套 evolve split（含合理性分析） | 用户真实介入 |
| C | compare 后用户要求 merge（含合理性分析） | 用户真实介入 |
| D | /query → insight 存档 | 用户真实介入 |
| H | 混合模式（--auto + 交互） | 用户真实介入 |

### 3.3 设计决策待定

| 议题 | 当前状态 | 影响 |
|------|---------|------|
| **master.md 的去留** | 已确认当前格式（路由表）对 Step 3 匹配无实际价值。讨论了三种方案：改造成聚合种子库、直接砍掉、改为 agentic search。**未定论** | Step 3 的匹配效率，500 仓库规模下的可行性 |
| **Step 3 agentic search 验证** | 实验设计已完成（`experiments/agentic-search-validation/design.md`）：4 个 Phase、20 个查询、完整 ground truth 矩阵和提示词。**未执行** | 决定 Step 3 的检索架构 |

### 3.4 SKILL.md 缺口

| 缺口 | 描述 |
|------|------|
| 粒度不匹配信号处理 | Scenario G 中 subagent 自主创建了"子维度观察"节，但 SKILL.md 中没有定义这个行为——subagent 是自由发挥的。需要在 /evolve-apply 或 /ingest 中正式定义 D 类信号（粒度不匹配）的处理流程 |

### 3.5 未入库改动

以下文件已修改但未提交：

| 文件 | 变更内容 |
|------|---------|
| `CLAUDE.md` | 新增"测试与验证规范"节 |
| `scripts/lint.py` | 5 策略 wikilink resolution + pipeline file placement check |
| `skills/code-compare/SKILL.md` | --auto 开关 |
| `skills/code-ingest/SKILL.md` | entity_map 填充指令 + 路径纪律 + --auto 开关 |
| `skills/code-query/SKILL.md` | 小幅修改 |
| `wiki/hot.md` | 更新 |
| `wiki/index.md` | 更新 |
| `wiki/log.md` | 追加 |
| `wiki/.obsidian/workspace.json` | 附带修改 |

未跟踪的新文件（部分）：
- `seeds/*-problem-map.md`（3 个）
- `seeds/*-candidates.md`（3 个）
- `seeds/master.md`
- `evolve-signals/2026-06-25-hermes-agent-openclaw.md`
- `wiki/repos/{nanobot,hermes-agent,openclaw}/`（64 entity + 3 overview + 3 .ingest-state.json）
- `wiki/concepts/*.md`（15 个）
- `experiments/agentic-search-validation/design.md`

---

## 四、当前架构与设计演进

### 4.1 管线现状

```
Source → Entity（Step 1）
  → Problem Space Mapping（Step 2）
  → 匹配（Step 3：读已有 Concept + Seeds → A/B/C/D 分类）
  → Concept 写作（Step 4）
  → 收尾（Step 6：index.md + hot.md + log.md + .ingest-state.json）

演化层：
  → /evolve-apply（信号驱动或用户指令 → merge/split/redirect）
```

### 4.2 已验证有效的部分

- **增量检测**（Step 0）：SHA-256 + entity_map 反向映射
- **Wikilink 解析**：5 策略 resolution 覆盖所有链接形式
- **Wikilink 网络自愈**：broken link 检测 + pipeline file placement 检查
- **--auto 模式**：全自动管线 + 前置判断仍然生效
- **子维度观察机制**：粒度不匹配信号可追加为父 Concept 的子维度节

### 4.3 设计变动

本次会话的核心设计讨论：

1. **master.md 价值重评估**：从"聚合路由表"→ 确认当前格式对 Step 3 匹配无实际价值 → 讨论改造或删除。本质问题是：大量仓库时 Step 3 需要的是搜索方案（agentic search 或向量检索），不是全量加载。

2. **agentic search 作为 Step 3 检索方案**：确认 agentic search（grep → read 命中文件 → 批量匹配）是 Claude Code 环境下的自然选择。设计中的关键洞察：15 个问题空间应批量搜索（一次 grep + 共享文件读取），而非 15 次独立搜索（同文件被重复读）。实验设计已完成但未执行。

3. **per-repo problem-map 文件结构验证有效**：每个条目有问题陈述 + 关切 + 解法 + 源码证据，这些文本就是 grep 的靶子，不需要额外的聚合索引。

---

## 五、关键问题与建议下一步

### 高优先级

1. **执行 agentic search 验证实验**：实验设计完整（20 个查询 + ground truth + 提示词），可直接启动 Phase 1。这是决定 Step 3 架构方向的基石——如果 agentic search 的 Recall@3 不达标（< 0.60），需要转向向量检索或其他方案。

2. **决定 master.md 去留**：依赖实验结论。如果 agentic search 在 problem-map 文件上的检索效果达标，master.md 可删除（减少维护负担）。如果不达标需要聚合索引，master.md 需改造为含设计选择内容的格式。

3. **修复 session-start.sh**：每次新会话的入口是坏的。

### 中优先级

4. **定义粒度不匹配信号处理**：在 /evolve-apply 或 /ingest SKILL.md 中正式定义——不是 subagent 自由发挥。

5. **提交当前改动**：9 个文件已修改，大量新文件未跟踪，需要在合适时机整理提交。

### 低优先级

6. **场景 A-D, H 测试**：需要用户在终端实时交互时执行。

---

## 六、实验基线对比（wiki vs experiments）

| 维度 | experiments/entity-concept-extraction/ | 当前 wiki/ |
|------|--------------------------------------|-----------|
| Entity 数量 | 35（14n + 8h + 10o + 3 misc） | 64（20n + 24h + 20o） |
| Entity 格式 | 无统一 frontmatter，无 wikilink | 有 frontmatter（type/repo/slug/problem/source_files） |
| Concept 数量 | 10 | 15 |
| Concept 格式 | 无 frontmatter | 有 frontmatter + 对比表 + 关切 + 演化记录 |
| 种子格式 | design-seeds.md（单文件 777 行，58 条，4 字段表格） | per-repo problem-map（3 文件，52 条，含问题陈述+关切+解法+溯源） |
| 链路完整性 | 无 entity→concept 反向链接 | entity 页末尾有"关联 Concept"节 |
| 演化机制 | 无 | 有（merge/split/redirect + 子维度观察） |
| 增量检测 | 无 | 有（.ingest-state.json + SHA-256 + entity_map） |

wiki 已吸收实验中的 13/15 个 Concept（2 个缺失：`context-engine-singleton-vs-pluggable`、`subsystem-assembly-visibility`，在实验 design-seeds.md 中有种子但 wiki 中未独立建 Concept——原因是当时不满足准则①多方案对比）。
