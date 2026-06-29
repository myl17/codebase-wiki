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
2. CHECK: 每个文件是否处于正确状态？
3. VERIFY: 日志和索引是否反映本次操作？
4. GATE: 全部通过 → 声明完成。任何一项不通过 → 补完。
```

## 通用检查清单

INTERNAL CHECK. DO NOT OUTPUT TO USER.

```
□ 本次操作写入了哪些 wiki 页？是否全部写成功（非空、格式正确）？
□ 如果写入了 Concept 页 → frontmatter 的 repos: 是否包含正确的仓库列表？
□ 如果写入了 Entity 页 → frontmatter 的 source_files: 是否和源码一致？
□ 如果写入了 View/Insight 页 → frontmatter 的 sources: / provenance_repos: 是否正确？

□ wiki/log.md 是否追加了本次操作？格式是否正确（[<ts>] <操作> <详情>）？
□ wiki/hot.md 是否覆盖写入？Last operation 是否反映本次操作？
□ wiki/index.md 是否刷新（如有新增/修改页面）？

□ 如果操作中发现了内容准确性问题并修正了 Concept/Entity 页 →
   log.md 行尾是否有 [源码验证: ...] 标记？

□ 是否有遗留的"稍后做"、"TODO"、未完成的写入承诺？
```

## 最后一步：程序化 lint

**内部检查清单全部通过后，必须运行 lint。这是门里最后一道锁。**

```
cd <wiki-root> && python scripts/lint.py --wiki wiki/ 2>&1
```

```
如果 lint 输出 "✓ No issues found." → 静默通过，可以声明完成。
如果 lint 报告 ERROR → 不通过。回退检查本次操作引入的错误，当场修复。
如果 lint 报告 WARN/INFO → 记录但不阻塞完成。
```

**判断标准：**
- 第一次跑出 ERROR 时，与操作前基线对比（如果知道的话）。新引入的 ERROR → 必须修复。
- 如果 ERRORS 全是 pre-existing（操作前就有的），不阻塞完成，但在日志中记录。
- 不确定是否 pre-existing → 当作新引入处理，修复。

## 与 /lint skill 的关系

`/lint` 是用户手动触发的全局健康检查（在任何时间跑、看全部 wiki 状态）。`completion-gate` 在每次写操作完成时自动运行 lint.py 作为程序化验证。两者的检查逻辑相同（同一份 `scripts/lint.py`），但触发方式和 report 方式不同：

| | `/lint` | `completion-gate` |
|---|---|---|
| 触发 | 用户手动 `(/lint)` | write skill 完成时自动 |
| 输出 | 完整报告（error/warn/info + 健康分） | 静默；仅在 lint 失败时向用户报告 |
| fix | 用户决定是否修复 | 当场修复新引入的问题 |

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
