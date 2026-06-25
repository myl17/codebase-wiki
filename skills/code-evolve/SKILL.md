# /evolve-apply — Concept 演化操作

Wikipedia 风格的 Concept 页面演化：合并、拆分、重定向。

## Trigger

```
/evolve-apply <signal-file>          # 处理指定信号文件中的所有信号
/evolve-apply                        # 列出所有可用的信号文件
/evolve-apply <signal-file> --skip-check  # 跳过前置判断（危险，仅在用户明确要求时允许）
```

`<signal-file>` 可以是文件名（如 `2026-06-24-hermes-agent.md`）或完整路径。

当用户表达合并、拆分、重定向 Concept 页的意图时触发——无论是从 `/ingest` 的 D 类信号、`/compare` 中的结构发现、还是直接指令。

## 执行协议

每次演化操作在 `wiki/log.md` 中追加时注明触发来源：
```
[<ts>] evolve merge <slug-A> → <slug-B> [触发: /compare 对话中]
[<ts>] evolve split <slug-src> → <new-slug> [触发: /ingest 暂停点 2]
[<ts>] evolve redirect <alias> → <target> [触发: 用户直接指令]
```

### Step 0 — 读取信号文件

```bash
ls -1 docs/evolve-signals/
```

展示：

```
可用的演化信号文件：

| 文件 | 日期 | 来源 ingest |
|------|------|-----------|`
| 2026-06-24-hermes-agent.md | 2026-06-24 | hermes-agent |
| 2026-06-20-openclaw.md     | 2026-06-20 | openclaw   |

运行 `/evolve-apply <文件名>` 处理。例如：
  /evolve-apply 2026-06-24-hermes-agent.md
```

停止。

### Step 1 — 读信号文件

读取 `docs/evolve-signals/<文件名>`，解析每条信号：

- 问题：<名称>
- 相关 Concept：<slug>
- 信号类型：粒度不匹配 / 候选合并
- 理由：<一句话>

向用户展示分组摘要：

```
信号文件：<文件名>
共 <N> 条演化信号：

  Merge 候选（<K> 条）：
    - "<slug-A>" 应合并入 "<slug-B>"：<理由>
    ...
  
  Split 候选（<K> 条）：
    - 从 "<slug-src>" 拆分出 "<子议题>"：<理由>
    ...
  
  Redirect 候选（<K> 条）：
    - "<别名>" → "<slug-target>"：<理由>
    ...

逐条处理？确认后开始。
```

用户确认后，按 merge → split → redirect 的顺序逐条处理。

### Step 2 — 逐条执行前置判断

对每条信号，先做前置判断。通过的才能进入执行。不通过的跳过并记录原因。

**如果用户传了 `--skip-check`：** 跳过前置判断，直接进入执行。但必须在执行前展示警告：

```
⚠️ --skip-check：跳过前置判断，直接执行。
以下操作将不经过条件验证，可能造成不可逆的 wiki 结构变更。
确认继续？
```

用户再次确认后才执行。

**本 skill 只定义三种操作的前置判断标准和执行步骤。**
具体的操作 prompt 在各小节中给出——这些 prompt 是给执行每个操作时 dispatch 的独立 agent 使用的。

**关键：每条操作执行完后，继续下一条——不要在中间停下来问"继续吗？"。**
前置判断的通过/不通过已经给了用户选择权。执行阶段是批量推进的。

---

## 操作 A：合并（Merge）

### 前置判断（执行前必须逐个检查）

读被合并页 `wiki/concepts/<slug-A>.md` 和合并目标页 `wiki/concepts/<slug-B>.md`，检查：

1. `<slug-A>` 讨论的问题是 `<slug-B>` 讨论问题的一个子维度？
2. 合并后 `<slug-A>` 的内容在 `<slug-B>` 页面内能被完整表达？（不会损失独立讨论价值）
3. `<slug-A>` 没有 `<slug-B>` 不覆盖的独立关切或对比维度？

**三条都满足 → 通过，展示变更预览，用户确认后执行。**
**任意一条不满足 → 不通过，向用户说明原因，跳过此信号。**

### 变更预览

```
Merge 操作预览：

  将 [[<slug-A>]] 的全部分内容合并至 [[<slug-B>]]
  <slug-A> 将变为重定向页

  影响范围：
  - 将追加 <N> 个仓库的解法至 <slug-B>
  - 将更新 <slug-B> 的对比表（新增对比维度）
  - <slug-A> 将被改写为重定向页
  - seeds/master.md 中对应条目标注 merged_into

  确认执行？
```

### 执行（独立 agent）

dispatch 一个 agent，运行以下 prompt：

```
你的任务是把两个 Concept 页合并为一个。

## 输入

- 被合并页：wiki/concepts/<slug-A>.md
- 合并目标页：wiki/concepts/<slug-B>.md
- 合并理由：<来自演化信号文件的描述>

## 判断确认（执行前必须检查）

合并是否成立，必须满足：
- <slug-A> 讨论的问题是 <slug-B> 讨论问题的一个子维度
- 合并后 <slug-A> 的内容在 <slug-B> 页面内能被完整表达
- <slug-A> 没有 <slug-B> 没有的独立关切或对比维度

任意一条不满足，停止操作，说明原因。

## 执行步骤

1. 把 <slug-A> 中各仓库的解法合并进 <slug-B> 对应位置
2. 更新 <slug-B> 的对比表，纳入 <slug-A> 引入的维度
3. 更新 <slug-B> 的演化记录，注明合并来源和日期
4. 把 <slug-A>.md 改写为重定向页：

   ---
   redirect_to: <slug-B>
   reason: <一句话>
   date: <YYYY-MM-DD>
   ---
   # <slug-A 原标题>
   > 此页面已合并至 [[<slug-B>]]。原因：<reason>

5. 更新 wiki/index.md Concepts 表：移除 <slug-A> 行，更新 <slug-B> 行
6. 更新 seeds/master.md，相关条目标注 merged_into: <slug-B>
7. 覆盖写入 wiki/hot.md（更新 Pending evolve signals 数）
8. 追加 wiki/log.md：[<timestamp>] evolve merge <slug-A> → <slug-B>

## 不修改

<slug-B> 中已有仓库的内容，只追加不覆盖。
```

---

## 操作 B：拆分（Split）

### 前置判断（执行前必须逐个检查）

读源页面 `wiki/concepts/<slug-src>.md`，检查：

1. 子议题下已有 ≥2 个仓库的不同方案？（从页面内提取计数）
2. 方案间有真实 trade-off？（不能一个方案在所有维度上都优于另一个）
3. 子议题独立成页后仍能通过 Concept 四条准则的①②③？

**三条都满足 → 通过，展示变更预览，用户确认后执行。**
**任意一条不满足 → 不通过，向用户说明原因，跳过此信号。**

### 变更预览

```
Split 操作预览：

  从 [[<slug-src>]] 拆分出新的子 Concept 页 [[<new-slug>]]

  影响范围：
  - 将新建 wiki/concepts/<new-slug>.md（<N> 个仓库的解法）
  - 将更新 <slug-src>（移除已迁移内容，保留摘要和链接）
  - seeds/master.md 中相关条目标注 split_to

  确认执行？
```

### 执行（独立 agent）

dispatch 一个 agent，运行以下 prompt：

```
你的任务是从现有 Concept 页中拆分出一个新的子 Concept 页。

## 输入

- 源页面：wiki/concepts/<slug-src>.md
- 拆分子议题：<子议题名称>
- 拆分理由：<来自演化信号文件的描述>

## 判断确认（执行前必须检查）

拆分是否成立，必须满足：
- 子议题下已有 ≥2 个仓库的不同方案，且方案间有真实 trade-off
- 子议题独立成页后仍能通过 Concept 四条准则的①②③：
  ① 多方案：至少两个不同仓库以明显不同的方式解决了同一个问题。
     注意：如果分析后一个方案在所有 trade-off 维度上都优于另一个，不成立。
  ② 独立设计空间：这个问题无法被某个已有问题空间完全覆盖——
     合并进去后，它自身的讨论维度会消失，决策价值会损失。
  ③ 持续存在的 Trade-off：不同方案之间的权衡没有银弹——
     满足关切 A 会增大满足关切 B 的成本，反之亦然。
- 拆分后的子议题不是源页面某个方案的单独描述

任意一条不满足，停止操作，说明原因。

## 执行步骤

1. 新建 wiki/concepts/<new-slug>.md
   包含从源页面剥离的相关仓库解法、关切、对比表
   演化记录注明"拆分自 [[<slug-src>]] on <date>"

2. 更新源页面：
   - 移除已迁移的详细内容
   - 保留摘要（一句话）并加 wikilink 到新页面
   - 演化记录注明"拆分出 [[<new-slug>]] on <date>"

3. 更新 wiki/index.md Concepts 表：新增 <new-slug> 行，更新 <slug-src> 行
4. 更新 seeds/master.md，相关条目标注 split_to: <new-slug>
5. 覆盖写入 wiki/hot.md（更新 Pending evolve signals 数）
6. 追加 wiki/log.md：[<timestamp>] evolve split <slug-src> → <new-slug>
```

---

## 操作 C：重定向（Redirect）

### 前置判断

检查目标页 `wiki/concepts/<slug-target>.md` 是否存在。

**存在 → 通过。**
**不存在 → 不通过，停止操作。**

### 变更预览

```
Redirect 操作预览：

  将新建重定向页 [[<alias-slug>]] → [[<slug-target>]]

  影响范围：
  - 将新建 wiki/concepts/<alias-slug>.md（仅 frontmatter + 一句话）
  - 不修改 <slug-target> 的任何内容

  确认执行？
```

### 执行（独立 agent）

dispatch 一个 agent，运行以下 prompt：

```
你的任务是为一个 Concept 页建立重定向别名。

## 输入

- 目标页：wiki/concepts/<slug-target>.md
- 别名名称：<alias-name>
- 理由：<为什么这两个名字指向同一个问题空间>

## 执行步骤

1. 新建 wiki/concepts/<alias-slug>.md：

   ---
   redirect_to: <slug-target>
   reason: <一句话>
   date: <YYYY-MM-DD>
   ---
   # <alias-name>
   > 此名称重定向至 [[<slug-target>]]。原因：<reason>

2. 更新 wiki/index.md Concepts 表：新增 <alias-slug> 行（标注重定向）
3. 覆盖写入 wiki/hot.md（更新 Pending evolve signals 数）
4. 追加 wiki/log.md：[<timestamp>] evolve redirect <alias-slug> → <slug-target>

## 不修改目标页的任何内容
```

---

## Step 3 — 汇总

全部信号处理完毕后，输出汇总：

```
演化信号处理完成：<文件名>

  ✅ Merge：<N> 条成功，<K> 条跳过
     - <slug-A> → <slug-B> ✅
     - <slug-C> → <slug-D> ⏭️ 理由：不满足前置判断第三条
  ✅ Split：<N> 条成功，<K> 条跳过
  ✅ Redirect：<N> 条成功，<K> 条跳过

跳过原因详情：
  - <slug-C> → <slug-D>：合并后 <slug-C> 的独立关切"<描述>"在 <slug-D> 中无对应维度，合并会损失讨论价值。
```

## 边缘情况

- 如果被合并页已经是一个重定向页 → 跳过，提示"<slug-A> 已是重定向页，无需合并"
- 如果合并目标页不存在 → 停止操作，提示"<slug-B> 不存在，请先确认 slug 是否正确"
- 如果拆分目标已存在 → 提示用户，确认是追加还是重命名
- 如果信号文件中有重复信号（同 slug 的多条信号） → 只处理第一条

## 不可逆性警告

merge 和 split 操作会修改 wiki 页面内容。虽然 git 可以回滚，但建议在操作前确认 git 状态是干净的：

```bash
git status --short
```
