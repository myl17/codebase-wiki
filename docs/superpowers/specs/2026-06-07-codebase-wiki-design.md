# Codebase Wiki — 设计文档

**创建日期**：2026-06-07  
**状态**：待实现  
**目标用户**：架构师、开源框架二开开发者

---

## 一、项目定位

### 解决什么问题

现有 LLM Wiki 项目（claude-obsidian、obsidian-wiki、llm-wiki-compiler）把代码仓库当作普通文档处理，没有为代码仓库设计专门的提取框架，也没有把"跨仓库对比"作为一等功能。

Codebase Wiki 的定位是：**架构师用 LLM 进行跨项目代码研究的工具**。目标用户不是"想建知识库的任何人"，而是"需要做技术选型或框架二开、想深度理解多个代码仓库的技术人"。

### 两个核心差异化

1. **维度表（Dimensions Schema）**：专为代码仓库设计的知识提取框架。每个仓库按同一套维度提取，确保跨仓库知识可对比。
2. **跨仓库对比作为一等功能**：不是 ingest 的副产品，而是独立的查询操作，按 category + dimension 组织，不随仓库数量爆炸。

### 与现有项目的本质差别

| | claude-obsidian | obsidian-wiki | llm-wiki-compiler | Codebase Wiki |
|---|---|---|---|---|
| 代码专属提取框架 | ❌ | ❌ | ❌ | ✅ 维度表 |
| 跨仓库对比 | ❌ | ❌ | ❌ | ✅ 一等功能 |
| 目标用户 | 泛用户 | 泛用户 | 泛用户 | 架构师/二开者 |
| Delta tracking | ❌ | ✅ | ✅ | ✅ |
| Provenance 标注 | ❌ | ✅ | ✅ | ✅ 行级引用 |
| 分发方式 | Claude Code 插件 | PyPI | npm CLI | Claude Code 插件（先），CLI（后） |

---

## 二、整体架构

### 三层结构

```
raw/                              # 源代码仓库（只读，LLM 不写）
  repos/
    react/                        # git clone 进来的仓库
    vue/
    solid/

wiki/                             # LLM 生成的知识库（LLM 写，用户读）
  index.md                        # 所有页面的目录
  log.md                          # 操作日志（append-only）
  hot.md                          # 当前活跃上下文（SessionStart 注入）
  eval-history.jsonl              # 质量评分历史
  repos/
    react/
      overview.md                 # 架构概览
      dimensions/
        architecture.md
        extension-points.md
        performance-tradeoffs.md
        dependency-strategy.md
        testing-philosophy.md
    vue/
      ...
  views/                          # 查询产物（按需生成，可刷新）
    categories/
      frontend-frameworks.md      # 类别对比矩阵
    dimensions/
      extension-points.md         # 跨仓库维度横向视图
  insights/                       # 查询时生成的综合分析（可选存档）
    2026-06-07-fiber-reconciliation.md

schema/                           # 配置层（方法论文件）
  CLAUDE.md                       # wiki 维护规则和操作规范
  dimensions.md                   # 代码提取维度表（核心护城河）

scripts/                          # 程序化引擎（Python）
  delta.py                        # 文件变更检测 + 分层标注
  manifest.py                     # ingest 状态管理
  lint.py                         # wiki 健康检查（7条固定规则）
  eval.py                         # 质量评分

hooks/
  hooks.json                      # 只做 SessionStart（学 Superpowers）
  session-start.sh                # 注入 wiki 当前状态

skills/
  code-ingest/SKILL.md            # /analyze 命令
  code-query/SKILL.md             # /query 命令
  code-compare/SKILL.md           # /compare 命令
  code-lint/SKILL.md              # /lint 命令

.manifest.json                    # ingest 状态（由 manifest.py 维护）
```

### wiki 页面的两种性质

| | Ingest 产物 | 查询产物 |
|---|---|---|
| 位置 | `wiki/repos/` | `wiki/views/`、`wiki/insights/` |
| 生成时机 | `/analyze` 时 | `/query`、`/compare` 时 |
| 稳定性 | 高，版本化 | 低，可随时刷新 |
| Provenance | 精确到源码行 | 来自其他 wiki 页面 |
| 维度表更新影响 | 标记 stale | 重新生成即可 |

---

## 三、维度表（核心方法论）

存放在 `schema/dimensions.md`，是整个项目最核心的文件。所有 ingest 操作都按这张表提取，确保跨仓库知识可对比。

### 初始五个维度

**维度一：架构模式（Architecture）**
- 核心抽象是什么？（组件、模块、实体、层）
- 数据流方向？（单向/双向/事件驱动）
- 关注点如何分离？各层职责边界在哪里？

**维度二：扩展点设计（Extension Points）**
- 插件系统是否存在？入口文件在哪里？
- 哪些地方设计了 hook/middleware/interceptor？
- 框架二开时最容易切入的层是哪里？
- 有没有官方规定的扩展协议（接口/类型/约定）？

**维度三：性能取舍（Performance Tradeoffs）**
- 什么被优化了？（启动时间/运行时性能/内存）
- 什么被牺牲了？这个取舍的理由是什么？
- 取舍在代码哪里有体现？（具体文件和行）

**维度四：依赖策略（Dependency Strategy）**
- 对外部依赖的态度？（最小化/拥抱生态/自研替代）
- 核心依赖的可替换性？替换成本高不高？
- 有没有 peer dependency 或可选依赖的设计？

**维度五：测试哲学（Testing Philosophy）**
- 单元/集成/e2e 的比例？
- 测试的是行为还是实现细节？
- 有没有专门的测试工具或测试约定？

### 维度表的演进策略

维度表版本记录在 `.manifest.json` 的 `dimensions_version` 字段，每个 wiki 页面的 frontmatter 记录生成时的版本。

**演进规则（按优先级）**：
- **前 20 个仓库阶段**：只增不改（Strategy B）。新维度对老仓库留空，标记 `status: pending`。强迫把初始维度设计稳。
- **维度表成熟后**：版本化标记（Strategy A）。维度含义变更升版本号，旧页面标记 `stale`，用户主动触发重新分析。
- **兜底**：`/lint` 输出 stale 页面列表，用户决定重跑优先级。

---

## 四、Ingest 流程（/analyze）

### 触发方式

```
/analyze ./raw/repos/react
/analyze ./raw/repos/react --dimensions extension-points,architecture  # 只分析指定维度
/analyze ./raw/repos/react --resume  # 继续未完成的分析
```

### 完整流程

```
步骤 1：运行 scripts/delta.py <repo-path>
         → 输出变更文件列表，按 core/impl/config 分层
         → 如果是首次分析，所有文件都是"new"

步骤 2：LLM 读 core 层文件（README、包入口、设计文档）
         → 形成对 repo 的初步理解
         → 告诉用户："我看到这是一个 [描述]，准备按维度表分析"

步骤 3：逐维度提取（每个维度一个对话轮次）
         → LLM 读相关文件，提取这个维度的知识
         → 告诉用户发现了什么，询问是否深入某个方向
         → 用户确认/调整后，写 wiki/repos/<name>/dimensions/<dim>.md
         → 每个 claim 必须有 ^[file:line-range] 引用

步骤 4：写 wiki/repos/<name>/overview.md
         → 综合所有维度的 overview 级别摘要

步骤 5：运行 scripts/manifest.py update <repo>
         → 更新 file hashes、dimensions_completed、ingest 时间

步骤 6：更新 wiki/index.md、wiki/log.md

步骤 7：刷新 wiki/hot.md
         → 记录"当前活跃仓库"和"上次操作摘要"，供下次 SessionStart 注入
```

### 文件分层逻辑（delta.py 内置规则）

| 层级 | 文件特征 | LLM 优先级 |
|------|---------|-----------|
| core | README*, 设计文档, 包入口(index.js/main.rs/...), packages/*/src/index.* | 必读 |
| config | package.json, go.mod, Cargo.toml, tsconfig, .github/**, Makefile | 按需读 |
| impl | 其他所有 .ts/.js/.rs/.go/.py 文件 | 按需深入 |

---

## 五、Query 流程（/query）

### 触发方式

```
/query React 的 Fiber 架构和 Stack 架构有什么本质区别？
/query --repo react,vue 扩展点设计哪个更适合二开？
```

### 检索升级链（按成本从低到高）

```
第一层：读 wiki/index.md + 扫相关页面 frontmatter
        判断有没有相关页面 → 成本极低

第二层：读相关页面的 summary 字段
        判断这个页面能否回答问题 → 成本低

第三层：grep 相关段落和 provenance 引用
        找具体 claim → 成本中

第四层：全读相关页面
        综合多来源合成答案 → 成本高，最后手段
```

SKILL.md 明确要求 LLM 按顺序升级，不允许跳过。

### 答案的三种归宿

回答结束后，LLM 判断并询问用户：

| 归宿 | 条件 | 操作 |
|------|------|------|
| A：不存档 | 答案已在现有页面，只是汇总 | 直接结束 |
| B：补充现有页面 | 发现了现有维度页的补充或修正 | append 到对应维度页，记 log |
| C：新建 Insight 页 | 综合分析有独立价值 | 写 `wiki/insights/<date>-<slug>.md` |

LLM 固定在回答结束后问："**这个分析值得存入 wiki 吗？**"

### Insight 页格式

```markdown
---
title: Fiber 架构 vs Stack 架构：reconciliation 的本质差异
type: insight
query: "React 的 Fiber 架构和 Stack 架构的 reconciliation 有什么本质区别？"
generated: 2026-06-07
sources:
  - wiki/repos/react/dimensions/architecture.md
  - wiki/repos/react/dimensions/performance-tradeoffs.md
provenance_repos: [react]
dimensions_version: v1.0
---
```

`query` 字段记录原始问题——这本身就是知识，知道"这篇 insight 是为了回答什么问题"比光有答案更有价值。

---

## 六、Compare 流程（/compare）

### 触发方式

```
/compare --category frontend-frameworks
/compare --category frontend-frameworks --dimension extension-points
/compare --repos react,vue,solid --dimension architecture
```

### 对比组织方式

**不是仓库 vs 仓库**（会随仓库数 N 产生 N×(N-1)/2 个页面），而是：

- **类别视图** `wiki/views/categories/<category>.md`：同一 category 所有仓库的对比矩阵
- **维度视图** `wiki/views/dimensions/<dimension>.md`：所有分析过的仓库在某个维度的横向视图

### 执行逻辑

```
步骤 1：从 .manifest.json 找到 category 下的所有仓库
步骤 2：读各仓库对应维度的 wiki 页面（不重新读源码）
步骤 3：生成/刷新对比矩阵
         → 维度页是 stale 版本：在矩阵中标注 ⚠️ stale
         → 维度尚未分析（dimensions_pending）：该格显示 `—（未分析）`，不阻断对比
步骤 4：如果某仓库的维度页是 stale 版本，在矩阵中标注警告
步骤 5：写入 wiki/views/categories/<category>.md
步骤 6：询问用户是否存为 insight
```

对比页读的是 **wiki 内容**，不是源码——这是查询成本可控的关键。

---

## 七、Hooks 设计

极简原则，只做一件事：SessionStart 注入 wiki 当前状态。

```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh",
        "async": false
      }]
    }]
  }
}
```

`session-start.sh` 注入内容：
- 当前活跃分析的仓库列表（来自 hot.md）
- 上次操作摘要（wiki/log.md 最后 3 行）
- stale 仓库数量（维度表版本不匹配的）

输出格式：`hookSpecificOutput.additionalContext`（Claude Code 官方标准路径，不用 prompt hook）。

---

## 八、Scripts 设计

### delta.py

**职责**：告诉 LLM"哪些文件需要看"。

输入：repo 路径  
输出：变更文件列表（new/modified/deleted），按 core/impl/config 分层

核心逻辑：
1. 读 `.manifest.json` 里上次的 file hash 清单
2. 遍历 repo，计算当前每个文件的 SHA-256
3. 对比得出 new/modified/deleted
4. 按内置规则标注每个文件的层级

### manifest.py

**职责**：管理 ingest 状态。

`.manifest.json` 结构：
```json
{
  "repos": {
    "react": {
      "path": "./raw/repos/react",
      "last_ingest": "2026-06-07T14:23:00Z",
      "dimensions_version": "v1.2",
      "dimensions_completed": ["architecture", "extension-points"],
      "dimensions_pending": ["performance-tradeoffs"],
      "file_hashes": { "src/ReactFiber.js": "abc123..." },
      "category": "frontend-frameworks"
    }
  },
  "dimensions_version": "v1.3",
  "categories": {
    "frontend-frameworks": ["react", "vue", "solid"]
  }
}
```

`dimensions_version` 不匹配 → 对应维度页标记 stale。

### lint.py

**职责**：程序化检查 wiki 健康，7条固定规则，不依赖 LLM 每次自己发明方法。

```
[ERROR] check_broken_wikilinks       [[页面]] 对应文件不存在
[ERROR] check_stale_dimensions       manifest 版本 vs 页面版本不一致
[WARN]  check_orphan_pages           页面没有任何入链
[WARN]  check_missing_provenance     wiki 页面没有 ^[source] 引用
[WARN]  check_empty_pending          dimensions_pending 里的维度超过 30 天未分析
[INFO]  check_missing_category       repo 没有分配 category
[INFO]  check_views_freshness        views/ 页面比 repos/ 页面旧
```

输出格式固定，LLM 读 lint 结果时不需要猜测格式。

### eval.py

**职责**：量化 wiki 质量，给 health score。

三个指标：
- **Coverage score**：`dimensions_completed / total_dimensions` 均值，跨所有仓库
- **Provenance score**：有明确 `^[...]` 引用的 claim 占比，低于 70% 报警
- **Freshness score**：stale 维度页占总维度页的比例

每次运行追加到 `wiki/eval-history.jsonl`，可看趋势，health 下降时知道原因。

---

## 九、操作清单总览

| 操作 | Skill | 脚本 | 产物位置 |
|------|-------|------|---------|
| Ingest | code-ingest | delta.py + manifest.py | `wiki/repos/` |
| Query | code-query | 无 | `wiki/insights/`（可选） |
| Compare | code-compare | 无 | `wiki/views/` |
| Lint | code-lint | lint.py + eval.py | 终端输出 + log |

---

## 十、两个目标的实现路径

### 个人工具目标

插件安装后，第一周的工作流：
1. git clone 2-3 个同类框架到 `raw/repos/`
2. `/analyze` 逐个分析，过程中调整维度表
3. `/compare --category <name>` 生成对比矩阵
4. `/query` 针对技术选型问题深问
5. Insight 回存 wiki，知识库开始积累

### 开源展示目标

- 插件先上线，通过 Claude Code marketplace 分发（参考 claude-obsidian 的分发路径）
- 方法论文件（`schema/dimensions.md`）开源，这是最能展示技术深度的部分
- README 中展示几个真实仓库的分析样例（react/vue/nestjs 等）
- 护城河在维度表质量，不在技术实现——开源不是风险

---

## 十一、Obsidian 双链规则

Wiki 在 Obsidian 中浏览，LLM 负责建立双链。双链规则明确，防止假阳性（参考 claude-obsidian #69 的教训）。

### 建双链的三个时机

| 时机 | 建哪些链 |
|------|---------|
| Ingest 完一个维度页后 | 页面底部 `## 关联` 区块，列同 category 其他仓库的同维度页 |
| Insight 页生成时 | `sources` 字段里的每个 wiki 路径自动转双链 |
| Compare 生成对比矩阵时 | 每个仓库名链接到它的 overview 页 |

### 建链规则

| 场景 | 是否建双链 |
|------|-----------|
| 维度页提到另一个仓库的同维度 | ✅ `[[vue/dimensions/extension-points]]` |
| overview 指向自己的维度页 | ✅ `[[react/dimensions/architecture]]` |
| insight 页指向来源维度页 | ✅ |
| views/ 对比页指向各 repo 维度页 | ✅ |
| 代码块或行内代码内出现 `[[` | ❌ 禁止 |
| provenance 引用 `^[file:line]` | ❌ 保持文本，不转双链 |
| 随意联想的概念关联 | ❌ 只建确定有意义的链 |

### CLAUDE.md 强制规则

```
1. 代码块（``` 或行内代码）内永远不建双链
2. provenance 引用 ^[file:line] 不转为双链
3. 双链只指向 wiki/ 目录内已存在的页面，不预建指向未来页面的链接
4. 每个页面底部必须有 ## 关联 区块，列出相关页面的双链
```

规则 3 确保 lint.py 的 `check_broken_wikilinks` 能有效工作——所有双链应该都指向实际存在的文件。

---

## 十三、实现优先级

**P0（第一周，跑通端到端）**：
- delta.py + manifest.py（基础状态管理）
- code-ingest SKILL.md（能分析一个仓库）
- hooks/session-start.sh（SessionStart 注入）
- schema/dimensions.md 初始版本

**P1（第二周，核心功能完整）**：
- code-query SKILL.md + insight 回存
- code-compare SKILL.md + views/ 生成
- lint.py（7条固定规则）

**P2（第三周，质量保证）**：
- eval.py + eval-history.jsonl
- dimensions_version stale 标记
- README + 样例分析

---

## 十四、已知风险和对策

| 风险 | 对策 |
|------|------|
| Claude Code hook API 变更 | 核心逻辑在 scripts/ 而非 hooks，影响面有限 |
| LLM 提取质量不稳定 | Provenance 强制标注 + staged review（用户每维度确认） |
| 维度表早期设计不成熟 | 前 20 个仓库只增不改，强迫稳定 |
| 大型 monorepo token 成本过高 | delta.py 分层 + 检索升级链，避免全量读取 |
