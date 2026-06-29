# /lint — Wiki Health Check

全量 wiki 结构性健康检查。用户手动触发。

## Role

`lint.py` 是 wiki 结构完整性的全量体检工具。它扫描所有 wiki 页面，检查 wikilink 完整性、frontmatter 合规、repos 一致性、孤立页、provenance 覆盖、views 新鲜度。

**与 completion-gate 的关系：** gate 是操作范围自检（"这次操作我做对了吗？"），lint 是全量体检（"整个 wiki 健康吗？"）。gate 不自动跑 lint。用户定期手动跑 `/lint` 做全量健康检查，或在 gate 建议时跑。

## Trigger

```
/lint
/lint --fix      # attempt auto-fix for INFO-level issues
```

## Execution Protocol

### Step 1 — Run lint.py

```bash
python scripts/lint.py --wiki wiki/
```

### Step 2 — Frontmatter 合规检查

扫描所有 entity 页和 concept 页，检查必填字段。

**Entity 页** (`wiki/repos/*/entities/*.md`) 每个文件必须有：
- `type: entity`
- `repo:` — 所属仓库名
- `slug:` — entity 标识符
- `problem:` — 问题层描述，"如何..."形式
- `source_files:` — 来源文件列表（至少一个）
- `generated:` — 生成日期

缺任意一个 → `[ERROR] entity_missing_frontmatter`

**Concept 页** (`wiki/concepts/*.md`) 每个文件必须有：
- `type: concept`
- `concept:` — concept 标识符
- `problem:` — 核心问题，一句话
- `concerns:` — 关切列表（可为空数组 `[]`）
- `repos:` — 仓库列表
- `generated:` — 生成日期

缺任意一个 → `[ERROR] concept_missing_frontmatter`

**Concept 页结构检查：**
必须包含 `## 演化记录` 节。缺失 → `[WARN] concept_missing_evolution_log`

**Entity → Concept 反向链接检查：**
对每个 concept 页，取 `repos:` 列表中的仓库，检查对应来源 entity 页
文件末尾是否有 `**关联 Concept**：[[concepts/<slug>]]`。
缺失 → `[WARN] entity_missing_concept_backlink`

### Step 3 — Report findings

Present a summary organized by severity:

**Errors (must fix):**
- List each [ERROR] finding with file and detail

**Warnings (should fix):**
- List each [WARN] finding

**Info (optional):**
- List each [INFO] finding

**健康分：**
- Wikilink 完整性：X%（broken links / total links）
- Entity frontmatter 合规率：X%
- Concept frontmatter 合规率：X%
- Concept 演化记录覆盖率：X%

### Step 4 — 操作建议

- `check_broken_wikilinks` → 检查对端文件是否存在。若指向旧 `nodes/` 或 `dimensions/` 
  路径，是遗留链接，直接删除
- `entity_missing_frontmatter` → 补全对应 entity 页的 frontmatter 字段
- `concept_missing_frontmatter` → 补全对应 concept 页的 frontmatter 字段

WARN 级：
- `concept_missing_evolution_log` → 在 concept 页末尾追加 `## 演化记录` 节
  （至少一条初建记录）
- `entity_missing_concept_backlink` → 在 entity 页末尾追加
  `**关联 Concept**：[[concepts/<slug>]]`

Never auto-fix errors without user confirmation. Auto-fix only INFO-level issues with `--fix`.
