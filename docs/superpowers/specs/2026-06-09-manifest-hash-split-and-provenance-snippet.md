# Design: manifest hash split + provenance code snippet

**Date:** 2026-06-09  
**Status:** Approved

---

## 背景

两个已确认的问题：

1. `.manifest.json` 把所有仓库的 `file_hashes` 存在同一个文件里，随仓库数量增长线性膨胀（实测 2 个仓库已达 1.8 MB，平均 121 bytes/条目），导致文件不可读、LLM 每次读取 token 成本飙升。

2. Wiki 页的 provenance 引用 `^[file:line]` 是纯文本标注，无法在 Obsidian 里跳转或验证结论，用户想确认 AI 结论是否准确时没有快捷路径。

---

## 设计一：file_hashes 拆分

### 目标

- `.manifest.json` 保持轻量（元数据只读），大小与仓库数量无关
- hash 状态按仓库隔离，按需加载
- 现有数据自动迁移，不丢失增量分析能力

### 存储结构变化

**变更前：**
```json
// .manifest.json
{
  "repos": {
    "openclaw": {
      "path": "...",
      "last_ingest": "...",
      "file_hashes": { "src/index.ts": "abc123", ... }  // 13299 条
    }
  }
}
```

**变更后：**
```json
// .manifest.json — 只保留元数据
{
  "repos": {
    "openclaw": {
      "path": "...",
      "last_ingest": "...",
      "dimensions_completed": [...],
      "dimensions_pending": [...],
      "category": "...",
      "dimensions_version": "v1.0"
    }
  }
}

// wiki/repos/openclaw/.hashes.json — 独立 hash 文件
{
  "src/index.ts": "abc123",
  ...
}
```

### 代码改动

**`scripts/manifest.py`**

新增 `HashStore` 类，职责单一：读写 `wiki/repos/<name>/.hashes.json`。

```python
class HashStore:
    def __init__(self, wiki_root: Path, repo_key: str):
        self.path = wiki_root / "repos" / repo_key / ".hashes.json"

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def save(self, hashes: dict):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(hashes, indent=2) + "\n")
```

`ManifestManager` 改动：
- `add_repo()` 不再初始化 `file_hashes: {}` 字段
- `update_after_ingest()` 移除 `file_hashes` 参数，不再写入 manifest
- hash 的读写全部委托给 `HashStore`

新增 `migrate` 子命令：
1. 遍历 `.manifest.json` 里每个 repo 的 `file_hashes`
2. 写到对应 `wiki/repos/<name>/.hashes.json`
3. 从 manifest 删除 `file_hashes` 字段
4. 保存 manifest

**`scripts/delta.py`**

`main()` 里改为通过 `HashStore` 读取上次 hashes：

```python
# 变更前
prev_hashes = manifest.get("repos", {}).get(repo_key, {}).get("file_hashes", {})

# 变更后
from manifest import HashStore
store = HashStore(Path("wiki"), repo_key)
prev_hashes = store.load()
```

`manifest.py update` 子命令里的 hash merge 逻辑同步移到 `HashStore.merge_delta(delta: dict)`。

**`.gitignore`**

新增：
```
wiki/repos/*/.hashes.json
```

### 迁移步骤（用户执行一次）

```bash
python scripts/manifest.py migrate --wiki wiki/
```

### 测试改动

- `tests/test_manifest.py`：新增 `HashStore` 的 load/save/merge 测试；更新 `update_after_ingest` 测试（移除 file_hashes 断言）
- `tests/test_delta.py`：更新 delta 读取 hash 的测试，改为通过 `HashStore`

---

## 设计二：provenance 内嵌折叠代码片段

### 目标

- 读者在 Obsidian 里看到 wiki 结论时，可以点击展开对应代码片段直接验证
- 正常阅读不受干扰（默认折叠）
- 格式规则简单，LLM 可机械执行，lint 可检查

### 格式规范

**变更前：**
```
React 调度器可以被中断。^[packages/scheduler/src/Scheduler.js:147-203]
```

**变更后：**
```
React 调度器可以被中断。^[packages/scheduler/src/Scheduler.js:147-203]

> [!source]- Scheduler.js:152-158
> ```js
> // 共 57 行，展示核心片段
> if (shouldYield()) { return callback; }
> workLoop(hasTimeRemaining, initialTime);
> ```
```

**规则：**
- 每个 `^[file:line]` 引用后必须紧跟一个折叠 callout
- callout 类型固定为 `[!source]-`（`-` 表示默认折叠）
- callout 标题格式：`文件名:展示的起止行`（不含目录前缀，保持简短）
- LLM 从引用的行范围内选最直接支持结论的片段，最多 **15 行**
- 超出 15 行时截断，代码块第一行加注释：`// 共 N 行，展示核心片段`
- 代码语言标注根据文件后缀自动选择（`.ts/.tsx` → `ts`，`.py` → `py`，`.go` → `go`，`.rs` → `rs`，其余 → 省略）

### schema/CLAUDE.md 新增规则

在"Provenance Format"小节后追加：

```
### Provenance Code Snippet

每个 ^[file:line] 引用后必须紧跟折叠 callout：

​```
结论文字。^[src/scheduler.js:147-203]

> [!source]- scheduler.js:152-158
> ​```js
> // 共 57 行，展示核心片段（超过 15 行时加此注释）
> if (shouldYield()) { return callback; }
> workLoop(hasTimeRemaining, initialTime);
> ​```
​```

规则：
- callout 类型：[!source]-（默认折叠）
- 最多展示 15 行，LLM 选最能支持结论的片段
- 超出 15 行加首行注释说明总行数
- 已有 wiki 页不强制回填，新 analyze / 补充时执行此规则
```

### lint 新增规则

在 `scripts/lint.py` 新增 `check_missing_code_snippet`：

- 扫描所有 `wiki/repos/` 页面
- 检测有 `^[file:line]` 但后面没有跟 `[!source]` callout 的情况
- 报 `[WARN] check_missing_code_snippet`（warn 而非 error，因历史页面不强制回填）

---

## 实施顺序

1. 执行 manifest 迁移（先做，避免后续 analyze 继续往 manifest 写 hash）
2. 更新脚本和测试
3. 更新 schema/CLAUDE.md
4. 更新 lint.py
5. 跑全量测试确认通过
