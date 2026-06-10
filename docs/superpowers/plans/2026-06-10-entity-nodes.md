# Entity Nodes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 dimension 页行文中内联 entity wikilink，让架构模式/技术栈/领域概念成为 Obsidian 图谱中的独立节点，实现跨 repo 知识发现。

**Architecture:** 三处变更：(1) `schema/CLAUDE.md` 新增 entity wikilink 书写规则；(2) `scripts/lint.py` 新增 `check_missing_entity_links` 规则；(3) 补写现有两个 repo 的 dimension 页，加入 entity wikilink。consolidate pass（生成 entity 页内容）不在本次范围，留待积累更多 repo 后手动执行。

**Tech Stack:** Python 3, pytest, Markdown/YAML frontmatter

---

## File Map

| 文件 | 变更类型 | 职责 |
|---|---|---|
| `schema/CLAUDE.md` | Modify | 新增 entity wikilink 书写规则 |
| `scripts/lint.py` | Modify | 新增 `check_missing_entity_links` 函数 + 接入 `run_all` |
| `tests/test_lint.py` | Modify | 新增 `check_missing_entity_links` 的测试 |
| `wiki/repos/openclaw/dimensions/*.md` | Modify | 补写 entity wikilink（5 个文件） |
| `wiki/repos/hermes-agent/dimensions/*.md` | Modify | 补写 entity wikilink（5 个文件） |

---

## Task 1: 更新 schema/CLAUDE.md，新增 entity wikilink 规则

**Files:**
- Modify: `schema/CLAUDE.md`

- [ ] **Step 1: 在 Double-Link Rules 表格中新增三行**

在 `schema/CLAUDE.md` 的 Double-Link Rules 表格末尾（`| Associative concept...` 那行之前）插入：

```markdown
| 行文中提到架构模式（如事件驱动、分层架构、插件注册表） | ✅ 用 `[[概念名]]` 内联标记，例：`[[事件驱动]]` |
| 行文中提到技术栈（如 Python asyncio、TypeScript monorepo） | ✅ 用 `[[概念名]]` 内联标记，例：`[[TypeScript monorepo]]` |
| 行文中提到领域概念（如 Context 压缩、Memory Provider） | ✅ 用 `[[概念名]]` 内联标记，例：`[[Context 压缩]]` |
| 具体类名、函数名、文件路径 | ❌ 不标 entity wikilink，保持纯文本 |
```

- [ ] **Step 2: 在 Required Page Sections 中新增 entity wikilink 说明**

在 `## Required Page Sections` 段落末尾（`Every wiki/repos/<name>/overview.md...` 那行之后）新增：

```markdown
Entity wikilink 规则：dimension 页正文中，凡属于架构模式/技术栈/领域概念的词汇，首次出现时用 `[[概念名]]` 标记。同一概念在同一页面只标一次（首次出现）。overview 页不标 entity wikilink。
```

- [ ] **Step 3: 提交**

```bash
git add schema/CLAUDE.md
git commit -m "docs: add entity wikilink rules to schema/CLAUDE.md"
```

---

## Task 2: 新增 lint 规则 check_missing_entity_links

**Files:**
- Modify: `scripts/lint.py`
- Modify: `tests/test_lint.py`

- [ ] **Step 1: 先写失败测试**

在 `tests/test_lint.py` 末尾追加：

```python
from lint import check_missing_entity_links


def test_check_missing_entity_links_warns_when_no_entity_links(tmp_path):
    # dimension page with only repo cross-links, no entity wikilinks (no /‑less links)
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\ndimension: architecture\n---\n"
          "# Arch\n\nSee [[vue/dimensions/architecture]].")
    warnings = check_missing_entity_links(tmp_path / "wiki")
    assert len(warnings) == 1
    assert warnings[0]["rule"] == "check_missing_entity_links"
    assert "architecture" in warnings[0]["file"]


def test_check_missing_entity_links_passes_when_entity_link_present(tmp_path):
    write(tmp_path / "wiki/repos/react/dimensions/architecture.md",
          "---\nrepo: react\ndimension: architecture\n---\n"
          "# Arch\n\nUses [[事件驱动]] pattern. ^[src/core.js:1-10]")
    warnings = check_missing_entity_links(tmp_path / "wiki")
    assert warnings == []


def test_check_missing_entity_links_skips_overview(tmp_path):
    write(tmp_path / "wiki/repos/react/overview.md",
          "---\nrepo: react\ndimension: overview\n---\n"
          "# Overview\n\nLinks to [[react/dimensions/architecture]].")
    warnings = check_missing_entity_links(tmp_path / "wiki")
    assert warnings == []
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_lint.py::test_check_missing_entity_links_warns_when_no_entity_links -v
```

期望输出：`FAILED` 且包含 `ImportError: cannot import name 'check_missing_entity_links'`

- [ ] **Step 3: 在 lint.py 中实现 check_missing_entity_links**

在 `check_views_freshness` 函数之后、`run_all` 之前插入：

```python
def check_missing_entity_links(wiki_root: Path) -> list:
    """[WARN] Dimension pages with no entity wikilinks (wikilinks without a '/' in target)."""
    warnings = []
    dims_root = wiki_root / "repos"
    if not dims_root.exists():
        return []
    for page in dims_root.rglob("*.md"):
        body, fm = _strip_frontmatter(page.read_text(errors="replace"))
        # Skip overview pages
        if fm.get("dimension") == "overview":
            continue
        # Skip if not a dimension page
        if fm.get("dimension") is None and "dimensions" not in page.parts:
            continue
        # Entity wikilinks have no '/' in their target (repo cross-links always have '/')
        entity_links = [
            m.group(1) for m in WIKILINK_RE.finditer(body)
            if "/" not in m.group(1)
        ]
        if not entity_links:
            warnings.append({
                "level": "WARN",
                "rule": "check_missing_entity_links",
                "file": str(page.relative_to(wiki_root)),
                "detail": "no entity wikilinks found (expected [[架构模式]], [[技术栈]], or [[领域概念]])",
            })
    return warnings
```

- [ ] **Step 4: 将 check_missing_entity_links 接入 run_all**

在 `run_all` 函数中，`findings += check_views_freshness(wiki_root)` 之后追加：

```python
    findings += check_missing_entity_links(wiki_root)
```

- [ ] **Step 5: 运行全部新增测试，确认通过**

```bash
python -m pytest tests/test_lint.py::test_check_missing_entity_links_warns_when_no_entity_links tests/test_lint.py::test_check_missing_entity_links_passes_when_entity_link_present tests/test_lint.py::test_check_missing_entity_links_skips_overview -v
```

期望输出：`3 passed`

- [ ] **Step 6: 运行全量测试，确认无回归**

```bash
python -m pytest tests/test_lint.py -v
```

期望输出：全部 `passed`，无 `FAILED`

- [ ] **Step 7: 提交**

```bash
git add scripts/lint.py tests/test_lint.py
git commit -m "feat: add check_missing_entity_links lint rule"
```

---

## Task 3: 补写 openclaw dimension 页的 entity wikilink

**Files:**
- Modify: `wiki/repos/openclaw/dimensions/architecture.md`
- Modify: `wiki/repos/openclaw/dimensions/extension-points.md`
- Modify: `wiki/repos/openclaw/dimensions/performance-tradeoffs.md`
- Modify: `wiki/repos/openclaw/dimensions/dependency-strategy.md`
- Modify: `wiki/repos/openclaw/dimensions/testing-philosophy.md`

- [ ] **Step 1: 阅读 openclaw 各 dimension 页，识别 entity 概念**

```bash
grep -n "架构\|模式\|pattern\|async\|monorepo\|plugin\|hook\|middleware\|cache\|scheduler\|typescript\|python" \
  wiki/repos/openclaw/dimensions/architecture.md \
  wiki/repos/openclaw/dimensions/extension-points.md \
  wiki/repos/openclaw/dimensions/performance-tradeoffs.md \
  wiki/repos/openclaw/dimensions/dependency-strategy.md \
  wiki/repos/openclaw/dimensions/testing-philosophy.md \
  | head -60
```

- [ ] **Step 2: 在 architecture.md 中标记 entity wikilink**

原则：每个概念只标首次出现，用 `[[概念名]]` 替换行文中的纯文本。属于以下三层才标：架构模式、技术栈、领域概念。具体类名不标。

根据文件内容，典型替换示例（实际以文件内容为准）：
- `TypeScript monorepo` → `[[TypeScript monorepo]]`
- `九大子系统` 这类具体数字描述 → 不标
- `单例模式` → `[[单例模式]]`（如果出现）

- [ ] **Step 3: 在 extension-points.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `插件系统` / `plugin system` → `[[插件系统]]`
- `middleware` → `[[中间件模式]]`（如果是描述架构模式而非具体类）
- `hook` 机制 → `[[Hook 机制]]`

- [ ] **Step 4: 在 performance-tradeoffs.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `compile cache` / 编译缓存 → `[[编译缓存]]`
- `懒加载` → `[[懒加载]]`

- [ ] **Step 5: 在 dependency-strategy.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `monorepo` → `[[TypeScript monorepo]]`（若已在 architecture 标过则此页不重复，但本页是独立文件，首次出现仍标）
- peer dependency → `[[Peer Dependency 策略]]`（如果是领域概念层面的讨论）

- [ ] **Step 6: 在 testing-philosophy.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `行为驱动测试` / behavior-driven → `[[行为驱动测试]]`
- `集成测试` / `单元测试` — 这是通用词汇不是架构概念，不标
- `vitest` / `jest` — 技术栈层面，可标 `[[Vitest]]`

- [ ] **Step 7: 运行 lint 验证 openclaw dimension 页不再触发 check_missing_entity_links**

```bash
python scripts/lint.py --wiki wiki/ --manifest .manifest.json 2>&1 | grep "check_missing_entity_links.*openclaw"
```

期望输出：无任何 `openclaw` 相关的 `check_missing_entity_links` 警告

- [ ] **Step 8: 提交**

```bash
git add wiki/repos/openclaw/dimensions/
git commit -m "docs: add entity wikilinks to openclaw dimension pages"
```

---

## Task 4: 补写 hermes-agent dimension 页的 entity wikilink

**Files:**
- Modify: `wiki/repos/hermes-agent/dimensions/architecture.md`
- Modify: `wiki/repos/hermes-agent/dimensions/extension-points.md`
- Modify: `wiki/repos/hermes-agent/dimensions/performance-tradeoffs.md`
- Modify: `wiki/repos/hermes-agent/dimensions/dependency-strategy.md`
- Modify: `wiki/repos/hermes-agent/dimensions/testing-philosophy.md`

- [ ] **Step 1: 阅读 hermes-agent 各 dimension 页，识别 entity 概念**

```bash
grep -n "架构\|模式\|pattern\|async\|python\|plugin\|hook\|middleware\|cache\|compress\|memory\|routing" \
  wiki/repos/hermes-agent/dimensions/architecture.md \
  wiki/repos/hermes-agent/dimensions/extension-points.md \
  wiki/repos/hermes-agent/dimensions/performance-tradeoffs.md \
  wiki/repos/hermes-agent/dimensions/dependency-strategy.md \
  wiki/repos/hermes-agent/dimensions/testing-philosophy.md \
  | head -60
```

- [ ] **Step 2: 在 architecture.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `分层架构` → `[[分层架构]]`
- `Python asyncio` → `[[Python asyncio]]`
- `事件驱动` → `[[事件驱动]]`（如果出现）

- [ ] **Step 3: 在 extension-points.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `插件系统` → `[[插件系统]]`（与 openclaw 共享同一 entity 节点）
- `Hook 机制` → `[[Hook 机制]]`

- [ ] **Step 4: 在 performance-tradeoffs.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `Prompt caching` → `[[Prompt Caching]]`
- `Context 压缩` → `[[Context 压缩]]`
- `并行工具执行` → `[[并行工具执行]]`

- [ ] **Step 5: 在 dependency-strategy.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `可替换后端` / 多后端策略 → `[[多后端可替换策略]]`
- `优雅降级` → `[[优雅降级]]`

- [ ] **Step 6: 在 testing-philosophy.md 中标记 entity wikilink**

典型 entity（以实际内容为准）：
- `行为覆盖测试` → `[[行为驱动测试]]`（与 openclaw 共享同一 entity 节点，名称须一致）
- `并行 CI` → `[[并行 CI]]`

- [ ] **Step 7: 运行 lint 验证全量无 check_missing_entity_links 警告**

```bash
python scripts/lint.py --wiki wiki/ --manifest .manifest.json 2>&1 | grep "check_missing_entity_links"
```

期望输出：空（无任何警告）

- [ ] **Step 8: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -v
```

期望输出：全部 `passed`

- [ ] **Step 9: 提交**

```bash
git add wiki/repos/hermes-agent/dimensions/
git commit -m "docs: add entity wikilinks to hermes-agent dimension pages"
```

---

## 验收标准

1. `python -m pytest tests/ -v` 全部通过
2. `python scripts/lint.py --wiki wiki/ --manifest .manifest.json` 无 `check_missing_entity_links` 警告
3. 在 Obsidian 图谱中，`[[Context 压缩]]`、`[[插件系统]]` 等 entity 节点以虚线（unresolved）形式出现，且被多个 dimension 页链接
