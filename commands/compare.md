# /compare — Cross-Repo Comparison

给定仓库名或设计问题关键词，按升级链找最便宜可用的信息来源做对比。

**Announce at start:** "正在使用 /compare skill 对比 <repo1> <repo2>..."

## Trigger

```
/compare <repo1> <repo2> [<repo3> ...] [--concept <keyword>] [--auto]
/compare --concept <keyword>
/compare <repo1> <repo2> ... --concept <keyword>
```

示例：
```
/compare hermes-agent nanobot openclaw
/compare --concept memory
/compare hermes-agent openclaw --concept agent
```

## --auto 模式

`--auto` 跳过用户交互，但不跳过正确性检查。具体影响见各节标注 `[--auto]`。

```
          正常模式              --auto 模式
          ─────────            ────────────
自检      MUST RUN              MUST RUN（不变）
准确性    MUST RUN → 问用户      MUST RUN → 写 evolve-signals/ → 继续
归档      问用户 A/B/C          AUTO = A（不存档）
结构问题  问用户 → 演化         写 evolve-signals/ → 继续
写 wiki   用户确认 → 写         NEVER auto-write
完成门    MUST PASS             MUST PASS（不变）
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

**前提：** 虽然没有匹配的 Concept 页，但多个仓库的 entity 可能都面对同一个抽象问题（通过 frontmatter 的 `problem:` 字段可判断）。

**操作：**

1. 读 `wiki/repos/<name>/entities/` 下所有 `.md` 的 frontmatter。
2. 把 `problem:` 字段相同或高度相似的 entity 归为一组。
3. 对每组，读每个 entity 页的 `**这个模块解决什么问题**`、`**关键机制**`、`**对外暴露什么**`。
4. 生成对比。有匹配 → 展示，标注 `Entity`，流程结束。
5. 无匹配 → 降级到 Level 3。

### Level 3 — 源码（最贵，最后手段）

1. 告知用户估算范围。获得确认后，在源码中按关键词搜索。
2. 读关键代码段，提取核心机制、设计取舍、差异。
3. 生成对比，信息来源标注 `源码`。

### 输出格式（所有 Level 统一）

```markdown
> 信息来源：<Concept / Entity / 源码>

## <对比维度>

**问题**：<一句话>

### <仓库名 A>
来源：<slug / 路径:行号>
- **解法**：<一句话>
- **关键机制**：<具体做法>
- **取舍**：<满足了什么、代价是什么>

### <仓库名 B>
...

### 核心差异
<一句话归纳根本张力>
```

---

## STOP 1：内容准确性自检

**对比展示完成后、询问归档前，必须运行此自检。不可跳过。静默执行——只在发现问题时向用户报告。**

```
INTERNAL CHECK. DO NOT OUTPUT TO USER UNLESS SOMETHING FAILS.

对于本次对比涉及的每个 Concept 页，检查：

□ 页面对每个仓库的描述是否引用了源码证据（^[文件路径:行号]）？
□ 有没有仓库的"解法"或"实现"节明显比其他仓库简短/模糊？
□ 如果是 Level 3 源码搜索产出的对比，Concept 页的对应节和源码是否一致？
□ 对比表中的结论是否有 Concept 页内对应仓库的解法描述支撑？

如果任何一项不通过 → 进入 STOP 1a：内容修正流程（此时才向用户报告）
如果全部通过 → 静默继续，不向用户输出检查结果
```

### STOP 1a：内容修正流程

发现 Concept 页对某仓库的描述与源码不符/不完整时：

**1. 展示 diff（必须）：**

```
⚠️ 内容准确性问题：

  Concept 页：<slug>
  仓库：<name>
  旧描述：<当前 Concept 页中的描述>
  源码实际：<从源码读到的准确信息>
  差异：<一句话>

是否修正此 Concept 页？修正后将重新生成受影响的对比维度。
```

**2. 用户确认后 → 当场写入 wiki 页。不确认 → 继续（但日志记录发现）。**

**3. 修正后 → 重新生成受影响的对比维度，替换已展示的旧内容。**

**[--auto]：** 跳过用户确认，写 evolve-signals/ 信号文件（含 diff 和源码证据），日志记录发现。**NEVER auto-write wiki 页。**

**4. 日志标记：** 在对比日志行尾追加 `[源码验证: <slug> <仓库名> 修正]`

---

## STOP 2：Concept 结构自检

**内容准确性检查完成后，运行此自检。不可跳过。静默执行——只在发现问题时向用户报告。**

```
INTERNAL CHECK. DO NOT OUTPUT TO USER UNLESS SOMETHING FAILS.

检查所有涉及的 Concept 页：

□ 有没有 Concept 页覆盖了差异很大的子议题？（→ 建议拆分，调用 /evolve-apply 逻辑）
□ 有没有两个 Concept 页在讨论本质相同的问题？（→ 建议合并）
□ 有没有跨仓库模式没有被任何 Concept 覆盖？（→ 建议新建）
□ 当前 Concept 粒度在 500 个 Concept 的规模下是否仍有区分度？

如果发现 → 向用户提问，用户同意后当场执行演化操作。
如果无发现 → 静默继续，不向用户输出检查结果。
```

**[--auto]：** 跳过用户确认，写 evolve-signals/ 信号文件，日志记录发现。不强制执行演化。

---

## 询问是否存档

> **这个对比需要归档吗？**
> - A: 不归档（临时查看）
> - B: 存入 wiki/views/
> - C: 发起 `/ingest <repo>` 将对比发现的问题空间纳入 Concept 演化

**[--auto]：** 跳过提问，默认选 A。Concept 结构检查仍执行并输出。

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

**写 view 前必须用户确认内容。不可跳过。**

追加 `wiki/log.md`：`[<timestamp>] compare <仓库列表> — <N> dimensions [源码验证: ...如有]`

---

## 完成前

**REQUIRED SUB-SKILL:** 在声称"对比完成"之前，必须调用 `completion-gate` 通过通用完成门（维护文件一致性、frontmatter 验证、写操作的 log/hot/index 同步）。

```
使用 completion-gate skill 验证本次操作：
- 如果用户选了 B → view 文件、log、index、hot 是否全部就位
- 如果有源码验证修正 → log 行尾是否有 [源码验证:] 标记
- 对比输出是否有信息来源标注
```

---

## 关键原则

1. **对比的正确性依赖 Concept 页的准确性。** 发现不准确时不修正 = 输出不可信。
2. **修正和对比是一体的。** 修了 Concept 页 → 刷新对比输出 → 一起归档。不分开。
3. **写操作必须用户确认。--auto 下永远不 auto-write wiki 页。**
4. **完成声明必须过门。** 不通过 completion-gate 不得声称完成。
