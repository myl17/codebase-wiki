# Manifest Hash Split + Provenance Code Snippet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `file_hashes` 从 `.manifest.json` 拆分到各仓库独立文件，并在 wiki provenance 引用后内嵌折叠代码片段以支持 Obsidian 内验证结论。

**Architecture:** Task 1-4 处理 manifest hash 拆分（新增 `HashStore` 类、改造 `delta.py`、迁移现有数据、更新测试）；Task 5-6 处理 provenance 代码片段（更新 `schema/CLAUDE.md` 规则、新增 `lint.py` 规则）；Task 7 跑全量测试并提交。

**Tech Stack:** Python 3, pytest, Obsidian callout syntax (`[!source]-`)

---

## 文件变更地图

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/manifest.py` | 修改 | 新增 `HashStore` 类；`ManifestManager` 移除 `file_hashes`；新增 `migrate` 子命令 |
| `scripts/delta.py` | 修改 | 通过 `HashStore` 读取上次 hashes，不再读 manifest |
| `tests/test_manifest.py` | 修改 | 新增 `HashStore` 测试；更新 `update_after_ingest` 测试 |
| `tests/test_delta.py` | 修改 | 更新 delta 读取 hash 的测试 |
| `schema/CLAUDE.md` | 修改 | 新增 Provenance Code Snippet 规则 |
| `scripts/lint.py` | 修改 | 新增 `check_missing_code_snippet` 规则 |
| `tests/test_lint.py` | 修改 | 新增 `check_missing_code_snippet` 测试 |
| `.gitignore` | 修改 | 新增 `wiki/repos/*/.hashes.json` |

---

## Task 1: 新增 HashStore 类并移除 ManifestManager 中的 file_hashes

**Files:**
- Modify: `scripts/manifest.py`
- Test: `tests/test_manifest.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_manifest.py` 末尾追加：

```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from manifest import HashStore   # 新增 import（与文件顶部的 ManifestManager import 合并）


def test_hashstore_load_missing(tmp_path):
    store = HashStore(tmp_path / "wiki", "react")
    assert store.load() == {}


def test_hashstore_save_and_load(tmp_path):
    store = HashStore(tmp_path / "wiki", "react")
    store.save({"src/index.ts": "abc123"})
    assert store.load() == {"src/index.ts": "abc123"}
    assert (tmp_path / "wiki" / "repos" / "react" / ".hashes.json").exists()


def test_hashstore_merge_delta(tmp_path):
    store = HashStore(tmp_path / "wiki", "react")
    store.save({"src/old.ts": "aaa", "src/gone.ts": "bbb"})
    delta = {
        "new": [{"path": "src/new.ts", "layer": "impl", "hash": "ccc"}],
        "modified": [{"path": "src/old.ts", "layer": "impl", "hash": "ddd"}],
        "deleted": ["src/gone.ts"],
    }
    store.merge_delta(delta)
    result = store.load()
    assert result == {"src/old.ts": "ddd", "src/new.ts": "ccc"}


def test_add_repo_no_file_hashes(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("vue", "./raw/repos/vue")
    assert "file_hashes" not in m.data["repos"]["vue"]


def test_update_after_ingest_no_file_hashes(tmp_path):
    m = ManifestManager(tmp_path / ".manifest.json")
    m.add_repo("react", "./raw/repos/react")
    m.update_after_ingest(
        repo_key="react",
        completed_dimensions=["architecture"],
        pending_dimensions=["extension-points"],
        timestamp="2026-06-09T10:00:00Z",
    )
    repo = m.data["repos"]["react"]
    assert "file_hashes" not in repo
    assert repo["dimensions_completed"] == ["architecture"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_manifest.py::test_hashstore_load_missing tests/test_manifest.py::test_hashstore_save_and_load tests/test_manifest.py::test_hashstore_merge_delta tests/test_manifest.py::test_add_repo_no_file_hashes tests/test_manifest.py::test_update_after_ingest_no_file_hashes -v 2>&1 | tail -20
```

预期：`ImportError: cannot import name 'HashStore'` 或类似失败。

- [ ] **Step 3: 实现 HashStore 并改造 ManifestManager**

在 `scripts/manifest.py` 中，紧接在 `import` 区块之后、`_DEFAULT_MANIFEST` 之前，插入 `HashStore` 类：

```python
class HashStore:
    """Manages per-repo file hashes in wiki/repos/<name>/.hashes.json."""

    def __init__(self, wiki_root: Path, repo_key: str):
        self.path = Path(wiki_root) / "repos" / repo_key / ".hashes.json"

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def save(self, hashes: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(hashes, indent=2) + "\n")

    def merge_delta(self, delta: dict):
        existing = self.load()
        for entry in delta.get("new", []) + delta.get("modified", []):
            existing[entry["path"]] = entry["hash"]
        for path in delta.get("deleted", []):
            existing.pop(path, None)
        self.save(existing)
```

然后在 `ManifestManager` 里做以下改动：

1. `add_repo()` 中删除 `"file_hashes": {}` 这一行
2. `update_after_ingest()` 签名改为移除 `file_hashes` 参数，方法体删除 `repo["file_hashes"] = file_hashes` 这行

改后的 `update_after_ingest` 签名：
```python
def update_after_ingest(
    self,
    repo_key: str,
    completed_dimensions: list,
    pending_dimensions: list,
    timestamp: str,
):
```

- [ ] **Step 4: 运行新测试确认通过**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_manifest.py::test_hashstore_load_missing tests/test_manifest.py::test_hashstore_save_and_load tests/test_manifest.py::test_hashstore_merge_delta tests/test_manifest.py::test_add_repo_no_file_hashes tests/test_manifest.py::test_update_after_ingest_no_file_hashes -v 2>&1 | tail -20
```

预期：5 个 PASS。

- [ ] **Step 5: 修复因签名变更导致的旧测试失败**

旧测试 `test_update_after_ingest` 和 `test_stale_repos` 和 `test_stale_count_returns_integer` 传了 `file_hashes` 参数，需要删除该参数。将 `tests/test_manifest.py` 中所有 `file_hashes=...` 参数调用删除：

- `test_update_after_ingest`：删除 `file_hashes={"src/index.js": "abc123"},` 一行，并删除 `assert repo["file_hashes"] == ...` 断言
- `test_stale_repos`：删除 `file_hashes={},` 一行
- `test_stale_count_returns_integer`：删除 `update_after_ingest` 调用中的 `{}` 第四参数（改为 `m.update_after_ingest("react", ["architecture"], [], "2026-06-08T10:00:00Z")`）

- [ ] **Step 6: 运行全部 manifest 测试**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_manifest.py -v 2>&1 | tail -20
```

预期：全部 PASS（旧测试 + 新测试）。

- [ ] **Step 7: Commit**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && git add scripts/manifest.py tests/test_manifest.py && git commit -m "feat: add HashStore class, remove file_hashes from ManifestManager"
```

---

## Task 2: 新增 manifest.py migrate 子命令

**Files:**
- Modify: `scripts/manifest.py`
- Test: `tests/test_manifest.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_manifest.py` 末尾追加：

```python
def test_migrate_moves_hashes_to_hashstore(tmp_path):
    import subprocess, sys as _sys
    wiki_root = tmp_path / "wiki"
    wiki_root.mkdir()
    # 构造一个有 file_hashes 的旧 manifest
    manifest_path = tmp_path / ".manifest.json"
    manifest_path.write_text(json.dumps({
        "repos": {
            "react": {
                "path": "./raw/repos/react",
                "last_ingest": "2026-06-09T10:00:00Z",
                "dimensions_completed": ["architecture"],
                "dimensions_pending": [],
                "file_hashes": {"src/index.ts": "abc123"},
                "category": None,
                "dimensions_version": "v1.0",
            }
        },
        "dimensions_version": "v1.0",
        "categories": {},
    }))
    result = subprocess.run(
        [_sys.executable, "scripts/manifest.py",
         "--manifest", str(manifest_path),
         "migrate", "--wiki", str(wiki_root)],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, result.stderr
    # hashes.json 已创建
    hashes_path = wiki_root / "repos" / "react" / ".hashes.json"
    assert hashes_path.exists()
    assert json.loads(hashes_path.read_text()) == {"src/index.ts": "abc123"}
    # manifest 中 file_hashes 已删除
    updated = json.loads(manifest_path.read_text())
    assert "file_hashes" not in updated["repos"]["react"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_manifest.py::test_migrate_moves_hashes_to_hashstore -v 2>&1 | tail -15
```

预期：FAIL（`migrate` 子命令不存在）。

- [ ] **Step 3: 在 manifest.py 中实现 migrate 子命令**

在 `main()` 的 `sub = parser.add_subparsers(...)` 区块中，在 `p_stale = sub.add_parser(...)` 之前新增：

```python
p_mig = sub.add_parser("migrate", help="Move file_hashes from manifest into per-repo .hashes.json")
p_mig.add_argument("--wiki", default="wiki", help="Path to wiki root (default: wiki)")
```

在 `main()` 的 `if args.cmd == ...` 分支末尾新增：

```python
elif args.cmd == "migrate":
    wiki_root = Path(args.wiki)
    migrated = 0
    for repo_key, info in m.data.get("repos", {}).items():
        hashes = info.pop("file_hashes", None)
        if hashes is not None:
            HashStore(wiki_root, repo_key).save(hashes)
            migrated += 1
    m.save()
    print(f"Migrated {migrated} repo(s). file_hashes removed from manifest.")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_manifest.py::test_migrate_moves_hashes_to_hashstore -v 2>&1 | tail -15
```

预期：PASS。

- [ ] **Step 5: Commit**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && git add scripts/manifest.py tests/test_manifest.py && git commit -m "feat: add manifest.py migrate subcommand"
```

---

## Task 3: 改造 delta.py 通过 HashStore 读取 hashes

**Files:**
- Modify: `scripts/delta.py`
- Test: `tests/test_delta.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_delta.py` 末尾追加：

```python
def test_delta_reads_from_hashstore(tmp_path):
    """delta.py CLI 应从 wiki/repos/<name>/.hashes.json 读取上次 hashes。"""
    import hashlib, subprocess, sys as _sys, json
    # 建 repo
    repo = make_repo(tmp_path / "repo", {"src/index.ts": "v1"})
    # 建 wiki 目录和 .hashes.json（模拟上次 ingest 后的状态）
    wiki_root = tmp_path / "wiki"
    store_path = wiki_root / "repos" / "myrepo" / ".hashes.json"
    store_path.parent.mkdir(parents=True)
    store_path.write_text(json.dumps({
        "src/index.ts": hashlib.sha256(b"v1").hexdigest()
    }))
    # 修改文件
    (repo / "src" / "index.ts").write_text("v2")
    result = subprocess.run(
        [_sys.executable, "scripts/delta.py", str(repo),
         "--wiki", str(wiki_root), "--repo", "myrepo"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert len(data["modified"]) == 1
    assert data["modified"][0]["path"] == "src/index.ts"
    assert len(data["new"]) == 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_delta.py::test_delta_reads_from_hashstore -v 2>&1 | tail -15
```

预期：FAIL（`delta.py` 还在读 manifest，不认识 `--wiki` 参数）。

- [ ] **Step 3: 改造 delta.py main()**

在 `delta.py` 顶部 `import` 区块末尾新增：

```python
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent))
from manifest import HashStore
```

在 `main()` 的 `argparse` 区块中，**替换**现有的 `--manifest` 和 `--repo` 参数为：

```python
parser.add_argument("--wiki", default="wiki",
                    help="Path to wiki root (default: wiki)")
parser.add_argument("--repo", help="Repo key (default: basename of repo_path)")
```

在 `main()` 中，**替换**现有读取 `prev_hashes` 的逻辑（原来读 manifest 的 5 行）为：

```python
repo_key = args.repo or repo_root.name
store = HashStore(Path(args.wiki), repo_key)
prev_hashes = store.load()
```

删除不再使用的 `manifest_path`、`manifest` 变量相关代码。

- [ ] **Step 4: 运行新测试和全部 delta 测试**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_delta.py -v 2>&1 | tail -20
```

预期：全部 PASS（包括原有的 7 个测试 + 新增 1 个）。

- [ ] **Step 5: Commit**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && git add scripts/delta.py tests/test_delta.py && git commit -m "feat: delta.py reads hashes from HashStore instead of manifest"
```

---

## Task 4: 更新 manifest.py update 子命令 + .gitignore + 执行迁移

**Files:**
- Modify: `scripts/manifest.py`
- Modify: `.gitignore`

- [ ] **Step 1: 改造 manifest.py update 子命令**

在 `scripts/manifest.py` 的 `main()` 中，`elif args.cmd == "update":` 分支里：

1. 删除 `--delta-json` 参数定义（`p_upd.add_argument("--delta-json", ...)` 一行）
2. 删除 hash merge 逻辑（`file_hashes = {}` 到 `file_hashes = existing` 的整块）
3. 将 `m.update_after_ingest(...)` 调用改为不传 `file_hashes`：

```python
elif args.cmd == "update":
    completed = [d for d in args.completed.split(",") if d]
    pending = [d for d in args.pending.split(",") if d]
    m.update_after_ingest(args.repo_key, completed, pending, args.timestamp)
    m.save()
    print(f"Updated '{args.repo_key}'")
```

- [ ] **Step 2: 更新 .gitignore**

在 `.gitignore` 末尾追加：

```
wiki/repos/*/.hashes.json
```

- [ ] **Step 3: 执行实际迁移（将现有 .manifest.json 数据迁移）**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python scripts/manifest.py migrate --wiki wiki/
```

预期输出：`Migrated 2 repo(s). file_hashes removed from manifest.`

验证：
```bash
python scripts/manifest.py show | python3 -c "import json,sys; d=json.load(sys.stdin); [print(k, 'file_hashes' in v) for k,v in d['repos'].items()]"
```

预期输出（两行均为 False）：
```
openclaw False
hermes-agent False
```

验证 hash 文件已生成：
```bash
wc -l wiki/repos/openclaw/.hashes.json wiki/repos/hermes-agent/.hashes.json
```

- [ ] **Step 4: 运行全量测试**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/ -v 2>&1 | tail -20
```

预期：全部 PASS。

- [ ] **Step 5: Commit**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && git add scripts/manifest.py .gitignore && git commit -m "feat: remove --delta-json from manifest update; add .hashes.json to gitignore"
```

---

## Task 5: 更新 schema/CLAUDE.md 新增 Provenance Code Snippet 规则

**Files:**
- Modify: `schema/CLAUDE.md`

- [ ] **Step 1: 阅读当前 schema/CLAUDE.md 的 Provenance Format 小节**

确认当前 "Provenance Format" 小节的结束位置（在 `## Frontmatter` 之前）。

- [ ] **Step 2: 在 Provenance Format 小节后插入新规则**

在 `schema/CLAUDE.md` 的 `## Frontmatter (required on every wiki/repos/ page)` 标题**之前**插入：

```markdown
### Provenance Code Snippet

每个 `^[file:line]` 引用后必须紧跟一个折叠 callout，供读者在 Obsidian 内直接验证结论：

```
结论文字。^[src/scheduler.js:147-203]

> [!source]- scheduler.js:152-158
> ```js
> // 共 57 行，展示核心片段（仅在超过 15 行时加此注释）
> if (shouldYield()) { return callback; }
> workLoop(hasTimeRemaining, initialTime);
> ```
```

规则：
- callout 类型固定为 `[!source]-`（`-` 使其在 Obsidian 中默认折叠）
- callout 标题格式：`文件名:展示起止行`，文件名不含目录前缀
- LLM 从引用的行范围内选最直接支持结论的片段，**最多 15 行**
- 超出 15 行时截断，代码块**第一行**加注释：`// 共 N 行，展示核心片段`
- 代码语言标注按后缀选择：`.ts/.tsx` → `ts`，`.py` → `py`，`.go` → `go`，`.rs` → `rs`，其余省略
- 已有 wiki 页不强制回填；新 analyze 或补充内容时执行此规则
```

- [ ] **Step 3: Commit**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && git add schema/CLAUDE.md && git commit -m "docs: add Provenance Code Snippet rule to schema/CLAUDE.md"
```

---

## Task 6: lint.py 新增 check_missing_code_snippet 规则

**Files:**
- Modify: `scripts/lint.py`
- Test: `tests/test_lint.py`

- [ ] **Step 1: 写失败测试**

查看 `tests/test_lint.py` 现有结构，在末尾追加：

```python
def test_check_missing_code_snippet_warns(tmp_path):
    """有 ^[file:line] 但没有后跟 [!source] callout 时报 WARN。"""
    from lint import check_missing_code_snippet
    wiki = tmp_path / "wiki"
    page = wiki / "repos" / "react" / "dimensions" / "architecture.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\nrepo: react\ndimension: architecture\ndimensions_version: v1.0\ngenerated: 2026-06-09\n---\n"
        "React uses fiber. ^[src/ReactFiber.js:1-10]\n"
        "No callout after this provenance.\n"
    )
    findings = check_missing_code_snippet(wiki)
    assert len(findings) == 1
    assert findings[0]["level"] == "WARN"
    assert findings[0]["rule"] == "check_missing_code_snippet"


def test_check_missing_code_snippet_passes_with_callout(tmp_path):
    """provenance 后紧跟 [!source] callout 时不报 WARN。"""
    from lint import check_missing_code_snippet
    wiki = tmp_path / "wiki"
    page = wiki / "repos" / "react" / "dimensions" / "architecture.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\nrepo: react\ndimension: architecture\ndimensions_version: v1.0\ngenerated: 2026-06-09\n---\n"
        "React uses fiber. ^[src/ReactFiber.js:1-10]\n"
        "\n"
        "> [!source]- ReactFiber.js:1-5\n"
        "> ```js\n"
        "> function createFiber() {}\n"
        "> ```\n"
    )
    findings = check_missing_code_snippet(wiki)
    assert findings == []


def test_check_missing_code_snippet_skips_overview(tmp_path):
    """overview 页没有 provenance，不应误报。"""
    from lint import check_missing_code_snippet
    wiki = tmp_path / "wiki"
    page = wiki / "repos" / "react" / "overview.md"
    page.parent.mkdir(parents=True)
    page.write_text(
        "---\nrepo: react\ndimension: overview\ndimensions_version: v1.0\ngenerated: 2026-06-09\n---\n"
        "Overview without any provenance.\n"
    )
    findings = check_missing_code_snippet(wiki)
    assert findings == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_lint.py::test_check_missing_code_snippet_warns tests/test_lint.py::test_check_missing_code_snippet_passes_with_callout tests/test_lint.py::test_check_missing_code_snippet_skips_overview -v 2>&1 | tail -15
```

预期：`ImportError: cannot import name 'check_missing_code_snippet'`。

- [ ] **Step 3: 在 lint.py 实现 check_missing_code_snippet**

在 `scripts/lint.py` 中，在 `check_missing_provenance` 函数**之后**插入：

```python
# Matches a line starting with "> [!source]"
_SOURCE_CALLOUT_RE = re.compile(r"^>\s*\[!source\]", re.MULTILINE)


def check_missing_code_snippet(wiki_root: Path) -> list:
    """[WARN] Dimension pages with ^[file:line] not followed by a [!source] callout."""
    warnings = []
    dims_root = wiki_root / "repos"
    if not dims_root.exists():
        return []
    for page in dims_root.rglob("*.md"):
        body, fm = _strip_frontmatter(page.read_text(errors="replace"))
        if fm.get("dimension") == "overview":
            continue
        provenance_matches = list(PROVENANCE_RE.finditer(body))
        if not provenance_matches:
            continue
        # For each provenance, check if a [!source] callout appears after it
        for m in provenance_matches:
            after = body[m.end():]
            # Allow blank lines between provenance and callout, but callout must appear
            # before the next provenance or end of relevant block (next 5 non-empty lines)
            lines_after = [l for l in after.split("\n") if l.strip()][:5]
            has_callout = any(_SOURCE_CALLOUT_RE.match(l) for l in lines_after)
            if not has_callout:
                warnings.append({
                    "level": "WARN",
                    "rule": "check_missing_code_snippet",
                    "file": str(page.relative_to(wiki_root)),
                    "detail": f"provenance ^[...] at offset {m.start()} has no [!source] callout",
                })
                break  # 每页只报一次，避免刷屏
    return warnings
```

在 `run_all()` 函数的 `findings` 列表末尾追加：

```python
findings += check_missing_code_snippet(wiki_root)
```

同时将文件顶部注释 `7 fixed health-check rules` 改为 `8 fixed health-check rules`。

- [ ] **Step 4: 运行所有新 lint 测试**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/test_lint.py::test_check_missing_code_snippet_warns tests/test_lint.py::test_check_missing_code_snippet_passes_with_callout tests/test_lint.py::test_check_missing_code_snippet_skips_overview -v 2>&1 | tail -15
```

预期：3 个 PASS。

- [ ] **Step 5: Commit**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && git add scripts/lint.py tests/test_lint.py && git commit -m "feat: add check_missing_code_snippet lint rule"
```

---

## Task 7: 全量测试并最终收尾

**Files:**
- 无新改动，仅验证

- [ ] **Step 1: 运行全量测试套件**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python -m pytest tests/ -v 2>&1 | tail -30
```

预期：全部 PASS，无 ERROR 无 FAIL。

- [ ] **Step 2: 手动验证 delta.py 端到端**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python scripts/delta.py ../path/to/any/local/repo --wiki wiki/ --repo test-verify 2>&1 | python3 -c "import json,sys; d=json.load(sys.stdin); print('new:', len(d['new']), 'modified:', len(d['modified']), 'deleted:', len(d['deleted']))"
```

将 `../path/to/any/local/repo` 替换为任意本地仓库路径（如已分析过的 openclaw 路径）。预期：输出三个数字，无报错。

- [ ] **Step 3: 手动验证 manifest show 不含 file_hashes**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && python scripts/manifest.py show | grep file_hashes
```

预期：无输出（说明 file_hashes 已完全从 manifest 清除）。

- [ ] **Step 4: 最终 commit**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki && git add -A && git status
```

确认没有遗漏的未提交文件。如有，补充提交。
