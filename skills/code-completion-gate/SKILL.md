# /completion-gate — 完成质量门

所有 wiki 写操作结束前必须通过的共享质量门。不是用户直接调用的 skill——由其他 skill 在完成阶段以 `REQUIRED SUB-SKILL` 形式引用。

## Trigger

```
(not user-invoked — referenced by other skills as REQUIRED SUB-SKILL at completion)
```

**Announce at start:** 静默执行，不向用户输出。clean pass 时不展示任何内容。

## Iron Law

```
NO COMPLETION CLAIMS BEFORE THE GATE IS CLEARED
```

在声称"操作完成"之前，必须逐条通过此门的检查。跳过任何一条 = 未完成。

## The Gate Function

```
BEFORE claiming any wiki operation is complete:

1. IDENTIFY: 本次操作涉及哪些 wiki 文件？
2. CHECK: 每个文件是否处于正确状态？（操作范围，全量 wiki 全覆盖）
3. VERIFY: 日志和索引是否反映本次操作？
4. GATE: 全部通过 → 声明完成。任何一项不通过 → 补完。
```

## 检查清单

INTERNAL CHECK. DO NOT OUTPUT TO USER.

### 1. 写入正确性（操作范围）

```
□ 本次操作写入了哪些 wiki 页？列出完整文件清单。
□ 每个文件是否写成功（存在、非空、内容完整）？
□ 如果写入了 Concept 页 →
    ① frontmatter repos: 是否包含了 body 中讨论的**所有**仓库？（body 有 ### repo-name 节或 wikilink 但 frontmatter 没列 = 覆盖关系不可见 → BLOCK）
    ② body 中每个 frontmatter 列出的 repo 是否至少有一个 [[repos/<name>/entities/...]] wikilink？（有 repos 无 wikilink = 元数据声明了但文档无证据 → WARN，记录不阻断）
□ 如果写入了 Entity 页 → frontmatter 的 source_files: 是否和源码一致？
□ 如果写入了 View/Insight 页 → frontmatter 的 sources: / provenance_repos: 是否正确？
```

### 2. 增量 wikilink 验证（操作范围）

```
□ 本次操作新增的 wikilink 指向的页面是否存在？
  - 只检查本次写入文件中的 wikilink，不扫描全 wiki。
  - 如果目标页尚未创建但有合理理由（如后续步骤会创建）→ 通过，但记录。
  - 如果目标页不存在且不会有 → BLOCK，补充或修正链接。
```

### 3. 维护文件同步（全局）

```
□ wiki/log.md 是否追加了本次操作？格式是否正确（[<ts>] <操作> <详情>）？
□ wiki/hot.md 是否覆盖写入？Last operation 是否反映本次操作？
□ wiki/index.md 是否刷新（如有新增/修改页面）？
```

### 4. 残留检查

```
□ 如果操作中发现了内容准确性问题并修正了 Concept/Entity 页 →
   log.md 行尾是否有 [源码验证: ...] 标记？
□ 是否有遗留的"稍后做"、"TODO"、未完成的写入承诺？
```

## 与 /lint skill 的关系

两者 scope 不同，各自独立：

| | `completion-gate` | `/lint` |
|---|---|---|
| Scope | **操作范围** — 只查本次操作涉及的文件 | **全量范围** — 扫描所有 wiki 页面 |
| 问题 | "这次操作我做对了吗？" | "整个 wiki 健康吗？" |
| 触发 | 每次 write skill 完成时自动 | 用户手动 `/lint` |
| 检查内容 | 本次文件写入正确性 + 增量 wikilink + 维护文件同步 + 残留检查 | 全 wiki wikilink 完整性 + frontmatter 合规 + repos 一致性 + 孤立页 + provenance + views 新鲜度 |
| 运行 lint.py | 不运行 | 运行 `python scripts/lint.py --wiki wiki/` |

**gate 不跑 `lint.py`。** lint 是全量体检，gate 是操作自检。不要用全量工具做增量检查。

**gate 可以向用户建议跑 `/lint`**（如累计 N 次操作后、或发现维护文件不一致时），但不强制。

## Common Failures

| 声称 | 需要 | 不够 |
|------|------|------|
| ingest 完成 | Entity 页全部存在 + Concept 页更新 + log/hot/index 刷新 | "管线跑完了" |
| compare 完成 | 对比输出完成 + 归档决策已处理 + log/hot 更新 | "展示完了" |
| concept 修正完成 | 页面内容已写入 + 源码证据标注 + log 行尾标记 | "读到了源码" |
| evolve 完成 | 目标页改写 + 重定向页新建 + index/log/hot 更新 | "操作执行了" |

## Red Flags — 以下任何情况发生，不要声称完成

| 如果你发现自己在 | 这是 Red Flag | 正确做法 |
|-----------------|--------------|---------|
| 直接 Edit wiki 页而未先展示 diff 给用户 | 跳过了写前确认 | 回退，展示 diff |
| 说"稍后一起写日志" | 口头承诺 | 当场写，不要推迟 |
| log.md 追加了但没有同步更新 hot.md | 维护文件不一致 | 同步刷新三个维护文件 |
| 修正了 Concept 页但 log 行尾没有 [源码验证:] 标记 | 操作来源不可追溯 | 补标记 |
| 说"完成了"但没检查 frontmatter 是否包含正确的 repos | 格式未验证 | 补检查 |

## Rationalization Prevention

| 借口 | 现实 |
|------|------|
| "源码信息已经有了，不写 wiki 也行" | 不写 = 下次对比/查询拿到的还是旧信息 |
| "log 和 hot 下次再更新" | 下次 = 不会做 |
| "用户没让写 log 所以不写" | 写 log 是系统行为，不需要用户批准 |
| "就一行的改动不用标记 [源码验证:]" | 一行也是知识修正，需要追溯 |
| "这个门清单太机械了" | 机械 = 可靠。跳过 = 不可靠 |

## When To Apply

**每次完成以下操作时：**
- `/ingest` 的 Step 6（种子库更新 + 快照保存）之后
- `/compare` 的归档写入之后
- `/query` 的选择 B（补充现有页面）或 C（新建 Insight）之后
- `/evolve-apply` 的 merge/split/redirect 执行之后
- 任何其他写入了 wiki 页的操作

## The Bottom Line

**完成不是感觉——是清单全部打勾。**

日志没写 = 没完成。hot 没刷新 = 没完成。frontmatter 不对 = 没完成。

这是不可协商的。
