# /compare — Cross-Repo Comparison

给定仓库名或设计问题关键词，按升级链找最便宜可用的信息来源做对比。

## Trigger

```
/compare <repo1> <repo2> [<repo3> ...]
/compare --concept <keyword>
/compare <repo1> <repo2> ... --concept <keyword>
```

示例：
```
/compare hermes-agent nanobot openclaw
/compare --concept memory
/compare hermes-agent openclaw --concept agent
```

## 对比升级链

从便宜到贵。只在上一级无法满足时升级。必须在开头标注信息来源。

```
Level 1 → Concept 页对比表（预计算，直接展示）
  ↓ 无覆盖
Level 2 → Entity 页（同一类 problem 字段的 entity 对比）
  ↓ 无覆盖
Level 3 → 源码（按关键词现场分析，最贵）
```

### Level 1 — Concept 页（最便宜）

**前提：** Concept 页的 `## 对比` 节是 ingest 时 LLM 验证过的预计算结果。

**操作：**

1. 扫描 `wiki/concepts/` 下所有 `.md`，逐一读 frontmatter（前 10 行）：
   - 如果指定了仓库名：检查 `repos:` 是否包含**所有**指定仓库。保留完全覆盖的。
   - 如果指定了 `--concept <keyword>`：检查 `concept:` 或 `problem:` 是否含关键词。
   - 两者都指定：取交集。
2. 对每个匹配的 Concept 页，读 `## 对比` 节和 `## 核心问题` 节。
3. 有匹配 → 聚合展示，信息来源标注 `Concept`，流程结束。
4. 无匹配 → 降级到 Level 2。告知用户：
   ```
   Concept 页未覆盖此对比维度。降级到 Entity 页查找。
   ```

### Level 2 — Entity 页（中等成本）

**前提：** 虽然没有匹配的 Concept 页，但多个仓库的 entity 可能都面对同一个抽象问题（通过 frontmatter 的 `problem:` 字段可判断）。比如 openclaw 的 memory 模块和 nanobot 的 memory 模块——都有 `problem: "如何管理记忆后端的可替换性"`，说明它们在同一个问题空间里。

**操作：**

1. 按搜索目标列出所有 entity 页：
   - 指定仓库：读 `wiki/repos/<name>/entities/` 下所有 `.md` 的 frontmatter
   - 指定 `--concept`：grep 所有 entity 页 frontmatter 的 `problem:` 字段
   ```bash
   grep -rl "problem:" wiki/repos --include="*.md"
   ```
   （从 wiki 根目录执行）

2. 把 `problem:` 字段相同或高度相似的 entity 归为一组。

3. 对每组，读每个 entity 页的：
   - `**这个模块解决什么问题**` 的"实现层"和"问题层"
   - `**关键机制**` 列表
   - `**对外暴露什么**`

4. 生成对比：同一问题下，各仓库的解法、机制、取舍。

5. 有匹配 → 聚合展示，信息来源标注 `Entity`，流程结束。

6. 无匹配 → 降级到 Level 3。告知用户：
   ```
   Entity 页也未覆盖此对比维度。需降级到源码搜索（最贵）。
   将按关键词在指定仓库源码中搜索，继续？
   ```

### Level 3 — 源码（最贵，最后手段）

**前提：** Concept 没覆盖、entity 也没对应模块。只能直接读源码。

**操作：**

1. 先告知用户估算范围：
   ```
   对比维度未被任何 Concept 或 Entity 页覆盖。
   将按关键词搜索所有指定仓库的源码。继续？
   ```

2. 获得确认后，在每个指定仓库源码中按关键词搜索：
   ```bash
   grep -rn "<keyword>" <repo-path> --include="*.py" --include="*.ts" --include="*.go" | head -30
   ```

3. 读关键代码段，提取每个仓库在这个问题上的：
   - 核心机制
   - 设计取舍
   - 和其他仓库的差异

4. 生成对比，信息来源标注 `源码`。

### 输出格式（所有 Level 统一）

```markdown
> 信息来源：<Concept / Entity / 源码>

## <对比维度>

**问题**：<一句话，这个维度问的是什么>

### <仓库名 A>

来源：<concept slug / entity slug / 源码路径:行号>
- **解法**：<一句话>
- **关键机制**：<具体做法>
- **取舍**：<满足了什么、代价是什么>

### <仓库名 B>

...

### 核心差异

<一句话归纳各仓库在这个维度上的根本张力>
```

多个对比维度连续排列，中间用 `---` 分割。

## 输出后

### 询问是否存档

对比完成后，问用户：

> **这个对比需要归档吗？**
> - A: 不归档（临时查看）
> - B: 存入 wiki/views/
> - C: 发起 `/ingest <repo>` 将对比发现的问题空间纳入 Concept 演化

如果选 B，写入 `wiki/views/<YYYY-MM-DD>-compare-<slug>.md`：

```yaml
---
type: view
repos: [<仓库列表>]
concepts: [<concept-slug列表>]
generated: <YYYY-MM-DD>
source_level: <Concept | Entity | 源码>
sources: ["wiki/concepts/<slug>.md", ...]
---
```

追加 `wiki/log.md`：`[<timestamp>] compare <仓库列表> — <N> dimensions`

### 对比后主动检查 Concept 结构

对比展示完成后，LLM 应主动审视所涉及 Concept 页的结构质量（判断标准见 `schema/concept-criteria.md`）：

1. 这个 Concept 页是否覆盖了差异很大的子议题？（→ 建议拆分）
2. 两个 Concept 页是否在讨论本质相同的问题，只是粒度不同？（→ 建议合并）
3. 对比中发现的跨仓库模式，是否没有被任何 Concept 覆盖？（→ 建议新建）

如有发现，主动向用户提问：
> **发现 Concept 结构问题：**
> - "memory-management" 覆盖了压缩策略和后端可替换性两个独立子议题。是否拆分为两个 Concept？
> - "tool-timeout" 和 "tool-execution-safety" 讨论的是同一个设计问题。是否合并？

**用户同意后，LLM 当场执行演化操作（调用 `/evolve-apply` 的逻辑），不需要用户切换命令。**
