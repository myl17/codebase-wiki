---
title: LLM-Wiki生态基础设施深度调研
category: codebase
depth: representation
tags: [llm-wiki, code-wiki, infrastructure]
created: 2026-06-05
updated: 2026-06-05
sources:
  - https://github.com/Ar9av/obsidian-wiki
  - https://github.com/atomicstrata/llm-wiki-compiler
  - https://github.com/AgriciDaniel/claude-obsidian
  - https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
---

三个头部llm-wiki项目的issue历史、PR修复链条、设计动机、对比分析。

## 调研范围

三个代表性项目：
- **claude-obsidian** (6,072 stars, 706 forks) — Claude Code 插件形态
- **obsidian-wiki** (1,716 stars, 190 forks) — 独立 Skill 包 + PyPI 分发
- **llm-wiki-compiler** (1,446 stars, 150 forks) — 独立 CLI + MCP Server + eval harness

---

## 一、Karpathy Gist 评论区 —— 整个生态的 RFC 讨论区

https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

这个 gist 发布后，评论区变成了 llm-wiki 社区的事实标准讨论地。几十个实现者在里面交流各自的架构决策和遇到的坑。**obsidian-wiki 的大量 feature 直接来自 gist 评论者的反馈**：

| Gist 评论者 | 提出的问题 | 变成 obsidian-wiki 的哪个功能 |
|-------------|-----------|---------------------------|
| `nowissan` | "all pages treated equally" 和 "duplicate concepts accumulate" | Importance Tiering + wiki-dedup |
| `paulmchen` (Synthadoc) | "context packs for bounded token retrieval across large wikis" | wiki-context-pack |
| `rohitg00` (AKBP protocol) | "all writes require human approval before being finalized" | WIKI_STAGED_WRITES |
| `aadjadj-bit` | 同上 | 同上 |
| `ojuschugh1` (sqz) | "128K tokens saved across 3K compressions via dedicated token compression tool" | Token budget monitoring + footprint report |
| `mikhashev` (DPC Messenger) | "plain wikilinks carry no semantic weight" | Typed Relationships (7 种关系类型) |
| `waydelyle` (SwarmVault v3.14) | "progressive disclosure and a `next` orientation as the key onboarding fix" | wiki-status → "What to Do Next" section |
| `cagataysengor` | 同上 | 同上 |
| `nowissan` (nohmitaina) | "dream cycle: background consolidation that merges fragments" | wiki-lint --consolidate mode |
| `nova28` | "no quantitative trust score, no lifecycle management" | Confidence + Lifecycle frontmatter schema |

**本质：** gist 评论区不是一个简单的留言板，而是整个 llm-wiki 生态的需求发现和方案评审场所。

---

## 二、六大基础设施详解

### ① Provenance 标记

**解决的问题：** 区分"源文档直接说的"和"LLM 自己推断的"。代码仓库中推断比例远高于文章。

**obsidian-wiki 的实现：**
- 三级标记：`^[extracted]` (默认，无标记) / `^[inferred]` (LLM 推断) / `^[ambiguous]` (源文档矛盾或模糊)
- frontmatter 中 `provenance: { extracted: 0.72, inferred: 0.25, ambiguous: 0.03 }` 全局概览
- `wiki-lint` 可以标注漂移——现实比例和记录比例不一致时报警

**llmwiki-compiler 的实现（更细粒度）：**
- 段落级引用：`^[source.md]` 指向源文件
- **行级引用**：`^[source.md:42-58]` 或 `^[source.md#L42-L58]` 精确到源文件行号
- `numberLines` 机制：源码传入 LLM 时附带右对齐行号（`42 | ...`），让 LLM 能准确引用行范围

**踩坑历史：**
- llmwiki-compiler #10: `^[fileA, fileB]` 被 lint 当作不存在的文件名报错 → 修复 `splitCitationEntries` 只在逗号后跟字母时才拆分
- llmwiki-compiler #67: `^[source.md:1, 12]` 被错误地按逗号拆分成两个引用 → `SPAN_SUFFIX_PATTERN` 更新支持 `:N,M` 格式
- llmwiki-compiler #78 (社区 fork): 提出 "citation depth" 应区分行级引用和段落引用，`extractClaimCitations` 已经解析了但 eval 没展示

**设计动机：** provenance 不只是给读者看的。真正价值是——当 wiki 里有 100 个 LLM 推断时，你能区分哪些是"代码直接说的"、哪些是"看多了产生的幻觉"、哪些是"两个源矛盾了"。代码仓库 ingest 中决策层大量依赖推断，没有这套系统 wiki 会从内部腐烂。

---

### ② Delta Tracking（增量追踪）

**解决的问题：** 避免每次 ingest 全量重读所有源文件。代码仓库持续演进，不做 delta 意味着 token 成本不可接受。

**三个项目的实现方式：**

| 项目 | Delta 机制 | 关键设计 |
|------|-----------|---------|
| obsidian-wiki | `.manifest.json` + SHA-256 content hash | hash 优先于 mtime 判断变更 |
| llmwiki-compiler | `.llmwiki/state.json` + per-source hash | hash-based change detection |
| claude-obsidian | **无** (issue #33 请求中) | 每次全量重读 |

**踩坑历史：**
- obsidian-wiki #35: `daily-update.sh` 用相对路径存 manifest，在非 vault 根目录运行时 `os.path.exists()` 全部返回 False → 每次全量重跑
- obsidian-wiki #64: `wiki-update` 用 `git log <last_sha>..HEAD` 做 delta，rebase 或 force-push 后 `last_sha` 不在祖先链上 → 加了 `git merge-base --is-ancestor` 前置检查，不满足时 fallback 全量扫描
- llmwiki-compiler #36: 两个不同目录的同名文件进 `sources/` 被静默覆盖 → basename 变 key 为 `slugify(title)` 没有 collision check → 修了但暴露出 `titleFromFilename` 用 `path.basename` 丢弃了目录信息的结构问题
- llmwiki-compiler #35: CJK 文件名 slugify 到空字符串，所有中文文件互相覆盖到 `sources/.md` → `\w` 不加 `/u` flag 的 JS regex bug

**修复链条：**
```
时间戳 delta → hash delta（防 touch 触发重跑）
→ 祖先链检查（防 rebase 破坏 delta）
→ basename 碰撞检测
→ Unicode-safe slugify
```

**设计动机：** delta 不是提速优化，是正确性保证。代码场景中 delta 的脆弱性被放大——频繁 rebase、rename、refactor 都会破坏 delta。不做 delta 意味着每次 ingest 全量重读 repo 所有文件，这不是慢的问题，是 token 成本在几百个源文件时根本不可能接受。

---

### ③ Confidence 量化

**解决的问题：** 代码表征的质量方差远大于文章——LLM 读小 repo 生成的表征可能相当准，读大型 monorepo 可能严重错误。需要可测量的信任度。

**obsidian-wiki 的实现 (来自 issue #28 RFC):**

**base_confidence 公式：**
```
base_confidence = source_count_score × 0.5 + source_quality_score × 0.5
source_count_score = min(distinct_source_ids / 3, 1.0)
source_quality_score = avg(quality score per distinct source_id)
```

**Source-quality 评分表：**

| Bucket | Score | 示例 |
|--------|-------|------|
| `paper` | 1.0 | arXiv, 会议论文 |
| `official` | 0.9 | *.gov, vendor docs |
| `documentation` | 0.85 | 第三方技术文档 |
| `book` | 0.8 | 书籍、技术参考 |
| `repository` | 0.75 | GitHub README, 代码库 |
| `blog` | 0.55 | 个人博客 |
| `session_transcript` | 0.5 | 对话历史 |
| `forum` | 0.4 | Stack Overflow, HN, Reddit |
| `unknown` | 0.4 | 未知来源 |
| `llm_generated` | 0.3 | LLM 自我反思 |

**Lifecycle 状态机：** `draft → reviewed → verified` (只能由人推进)，`disputed`(覆盖)、`archived`(终止态)。`stale` 不是状态，是计算出的叠加层：`updated > 90天`。

**Per-skill 默认值：** `wiki-ingest` 按源分类器计算，`wiki-research` 通常 0.85+，`wiki-capture` 默认 0.42，`data-ingest` 默认 0.37

**llmwiki-compiler 的实现 (来自 PR #67 eval harness):**
- 增加 LLM-as-judge 验证：抽样 `(claim, source span)` 对，judge 模型评分 0-2 (unsupported → fully supported)
- 确定性采样：`SHA-256(claim + span)` 排序取前 N，确保同一对总是被选中——避免随机噪声
- JSONL cache：每个 judgement 追加到 `.llmwiki/eval/citation-cache.jsonl`，跑过的不再重跑
- CI 门禁：`.llmwiki/eval/thresholds.yaml` 配置最低可接受分数

**设计动机：** 没有量化指标，你无法区分"我有了 100 个页面"和"我有了 100 个值得信的知识"。代码仓库场景尤其重要——粗粒度 LLM 生成的 representation 质量浮动大，需要用 confidence 识别哪些页需要人工 review。

---

### ④ Tier 分级 + Token Budget

**解决的问题：** wiki 增长后所有页面被平等对待，查询成本非线性上升。不到 100 页时可以每页都读，500 页时必须分层。

**obsidian-wiki 的实现：**

**三级 tier：**

| Tier | 含义 | Ingest 行为 | Query 优先级 |
|------|------|------------|-------------|
| `core` | 支柱页 — 高入链数或桥接位置 | 总是更新 | 先出现 |
| `supporting` (默认) | 标准页 | 有明确新 claim 才更新 | 标准 |
| `peripheral` | 低连接页 | 只有 source 主要针对该 topic 才处理 | 最后，可能被裁剪 |

**晋升/降级规则：**
- 新页 default `supporting`
- ≥5 入链或被 `wiki-status` insights 标记为 bridge → 晋升 `core`
- ≤1 入链 + 90+天未更新 → 降为 `peripheral`
- 人工覆盖永远赢

**检索升级链（四项 escaltion）：**

| 需求 | 方法 | 相对成本 |
|------|------|---------|
| 页是否存在？title/category/tags？ | 读 index.md + Grep frontmatter | **最便宜** |
| 1-2 句话预览 | 读 `summary:` field | **便宜** |
| 特定 claim 或节 | `grep -A -B` | **中等** |
| 全文 | `Read` | **最贵**——最后手段 |

**原则：** 只在便宜方法不够时才升级。一个 500 行页面只为了读 15 行而打开 = 485 行 token 浪费。

**Token Footprint Report (obsidian-wiki #46):**
- 按 tier 拆算 token 成本（4 chars/token 启发式）
- `WIKI_TOKEN_WARN_THRESHOLD` (默认 100K) 超限报警
- 500 页 wiki 全读 ~18K tokens，检索升级链下典型 query ~150 tokens

**llmwiki-compiler 的相关问题 (#39 prompt blowup):**
- 多个 source 共享同一 concept 时 `mergeExtractions` 无界拼接全部 source 内容
- prompt 超过 context window，LLM 返回 `context window exceeds limit` 错误
- 修复：`LLMWIKI_PROMPT_BUDGET_CHARS` per-concept 截断 (默认 200K chars / ~50K tokens)
- 截断时每个 source 公平分配份额，stderr 打印 truncation warning

**设计动机：** 代码 wiki 规模增长更快——一个 monorepo 可能有几十个 package，每个可以有多个有意义的 design decision。不做 tier 和检索升级链，wiki 的可用性随规模非线性下降。

---

### ⑤ Staged Review（人工审核门）

**解决的问题：** 代码提取中决策层的 LLM 推断比例高，不做审核 wiki 会充满幻觉。文章 ingest 推断比例低得多，review 边际收益也低——所以代码场景 review 是必须的。

**obsidian-wiki 的实现 (`WIKI_STAGED_WRITES` env var):**
- 开启后所有 LLM 写的新页面进 `_staging/<category>/`, 更新进 `_staging/<category>/<page>.patch.md`
- `wiki-stage-commit` 逐文件审核：显示 title/tags/summary/tier/confidence
- 支持 `--all` (全接受) / `--reject-all` / `--list`
- 冲突检测：目标页在 staging 后被修改时报警
- `index.md` 和 `log.md` 永远立即更新（低风险跟踪文件），`hot.md` 标注有 staged writes pending
- `wiki-status` 首页显示 "Staged writes pending: N pages · M patches"
- rejected 文件移到 `_raw/rejected-*` 供手动编辑

**llmwiki-compiler 的实现 (`compile --review`):**
- 候选页写入 `.llmwiki/candidates/` 而非 `wiki/`
- `review approve <id>` → 正式导入 wiki + 更新 index/MOC/embeddings
- `review reject <id>` → archive 到 `.llmwiki/candidates/archive/`
- **Per-source defer**：同一 source 产生多个候选，最后一个 approve 之前 source 不标记为已完成——防止部分候选被遗漏
- approve/reject 获取 `.llmwiki/lock` 串行化防止并发竞态

**设计动机：** 跟得到笔记里那个 600+ 页知识库项目的经验一致——"Java 类页太浅，需要设计 7 段深度模板，批量生成并审查"。code wiki 不做 staged review 等同于放任 LLM 幻觉进入知识库。

---

### ⑥ Eval Harness（质量评分系统）

**解决的问题：** wiki 持续演进时，不知道是在变好还是变差。600 页时不可能逐页检查。

**llmwiki-compiler 的实现 (PR #67, 最完整的 eval):**

**Health Score (0-100):**
- 聚合 10+ lint 规则，按严重程度扣分
- error (broken citation/duplicate concepts) 扣分 > warning > suggestion
- CI 门禁可通过 `.llmwiki/eval/thresholds.yaml` 配置

**Citation Coverage:**
- 带 `^[...]` 的 prose paragraph 占比
- citation 指向存在的源文件的 precision

**Citation Support (LLM-as-judge, --suite full only):**
- 抽样 N 个 (claim, source span) 对
- Judge 模型评分 0-2 (unsupported → partially supported → fully supported)
- SHA-256 确定性采样 → 分数变化有意义，不是随机噪声
- JSONL cache → 跑过的不再重跑

**Corpus Stats:**
- 页面数、源文件数、总字符数、embedding 数
- 追加到 `history.jsonl` 做时序趋势
- 回归检测：当前 vs 上一次 diff

**CI 门禁 (`thresholds.yaml`):**
```yaml
health_score: 85
citation_coverage_percent: 70
citation_precision_percent: 90
citation_support_mean: 1.4   # --suite full only
```
任意阈值 breached → exit code 非零，CI 可拦截。

**社区 PR #78 提出的 6 个额外维度 (未合入):**
1. Source utilization — 检测 `sources/` 中从未被任何页面引用的文件
2. Health weight restructuring — 4 级扣分 (blocking -8 / error -4 / warning -2 / suggestion -1)
3. Page health distribution — 每页分桶 (healthy/adequate/needs_work/broken) + worst-5 列表
4. Citation depth — 行级 vs 段落级区分
5. Knowledge freshness — mtime 过期的 stale source 检测
6. Graph health — wikilink 图分析 (入度孤页、连通分量、hub 页)

**设计动机：** eval 不是锦上添花。代码仓库 ingest 不是一次性的——源码在变、持续摄入新项目——每次变更都可能破坏已有知识。没有 eval 你就不知道 600 页 wiki 是在进化还是在退化。CI 门禁确保"部署前的 wiki 质量不低于上一次"。

---

## 三、三个项目的本质差异

### obsidian-wiki (1.7k stars) — Ar9av

```
本质：独立 Skill 包 + PyPI 分发
架构：Markdown 技能文件 → 由调用方 Agent (Claude/Cursor/Codex/...) 执行
基础设施深度：中等
强项：provenance / confidence / tier / staged review / typed relationships / dedup / consolidate
弱项：无独立 eval harness、无独立编译管线
```

**社区贡献生态良好** — 来自多个贡献者的 PR：@BenRoe (provenance 修复)、@DxVapor (Pi agent 支持)、@georgelichen (QMD 索引刷新)、@MathiasOki (Hermes named profile)、@cjescudero (Markdown link 格式)。

**关键特征：** 大量的 feature issue 和 PR 来自 `Ar9av` 本人，设计决策来自 gist 评论区讨论。每个 feature 有独立的 issue + PR 记录，迭代清晰。

### llmwiki-compiler (1.4k stars) — atomicstrata

```
本质：独立 CLI + MCP Server + 完整编译管线
架构：Two-phase compile → embed → search → eval，完全自治
基础设施深度：最深
强项：eval harness (最完整) / 行级 citation / context pack / 两阶段编译无排序依赖 / 增量 hash + embedding / CI 门禁
弱项：无 tier 分级、无 typed relationships、界面依赖 viewer (只读)
```

**工程文化严谨** — @ethanj (maintainer) 提交密集，每个 PR 附带 typecheck + build + test + fallow 死代码检查。从 #66 可以看出——专门升级 fallow 从 2.42 到 2.77，把 2.77 复杂度 findings 逐个消解而非 suppress。**这是一个工程纪律最高的项目。**

**关键特征：** 社区贡献质量高——@joshuaknipe 的 eval harness (#67, #74) 是近 70 个测试文件的全功能贡献，设计文档详尽。@dohu012 的 #78 提出了 6 个 eval 维度的扩展但未合入。

### claude-obsidian (6k stars) — AgriciDaniel

```
本质：Obsidian vault 模版 + Claude Code 技能文件 + hooks 自动注入
架构：Claude Code 是它的执行引擎——负责读文件、写文件、调 LLM
基础设施深度：最浅
强项：分发渠道（Claude Code 插件 marketplace） / 开箱即用 / hooks 自动上下文注入
弱项：无 delta tracking / 无 provenance / 无 confidence / 无 eval / 无 tier
```

**issue 类型分布：**
- Claude Code 兼容性问题占大头：#42 #45 #47 #48 #59 #61 — 全是 SessionStart/PostCompact hook 报 ToolUseContext required
- 安装/发现路径问题：#75 #2 #11 — `/wiki` 命令找不到
- 用户体验摩擦：#5 (.raw/ 在 Obsidian 不可见)；#6 (300 个文件 4 小时)；#25 (需要 glossary)
- 真正的架构讨论极少：#33 (incremental ingest 请求，一个月无回复) #70 (lint 无标准数据采集方法) #69 (wikilink 假阳性)

**PR 特征：** 30 个 PR 中大量是用户向自己 fork 的 wiki vault 提交内容——不是代码贡献，是用 wiki 的痕迹误提交到了上游。这反映了 claude-obsidian 的工作流设计：**用户在一个 git repo 里 run wiki，自然把 wiki 内容也 commit 到了 repo。**

**维护者问题：** #16 质疑 "is this repository legit?"——维护者创建了 50+ 个类似内容的 repo，大量 AI 生成提交。claude-obsidian 是其中星数最高的。这解释了它基础设施浅的原因——**没有真正的人在持续演进设计。**

---

## 四、claude-obsidian 的 issue 详细列表

### 已关闭 (CLOSED)

| # | 标题 | 关键信息 |
|---|------|---------|
| #42 | SessionStart/PostCompact prompt hooks fail with "ToolUseContext is required" | Claude Code 的 prompt hook 需要 ToolUseContext，但 SessionStart 不提供 |
| #10 | 同上，详细描述+建议修复 | @jhsong-musinsa 提出，修法是删除两个 prompt 类型的 hook |
| #1 | Automatize the learning? | @Llorx 问能否像 claude-memory-compiler 那样自动学习 |
| #14 | Maintenance of this repo | @FrancisBehnen 问 "will it be maintained?" |
| #16 | Is this repository legit? | @B0R0koko 质疑维护者真实性：50+ 个类似 repo，AI 生成提交 |

### 仍打开 (OPEN)

| # | 标题 | 关键信息 |
|---|------|---------|
| #75 | README implies cloned repo auto-loads /wiki, but requires --plugin-dir | 安装路径误导 |
| #70 | wiki-lint: Core lint checks (1-7) have no specified data-gathering method | lint 无标准数据采集方法，Claude 每次临时发明 shell 命令 |
| #69 | wiki-lint: Wikilink extraction edge cases cause persistent false-positive dead links | wikilink 假阳性误报模式未文档化 |
| #64 | obsidian now accepts "version" argument 而非 --version | CLI interface change |
| #61 | SessionStart hook uses unsupported type: "prompt" — fails on resume | 同 #42 的持久问题 |
| #59 | hooks.json SessionStart prompt hook 问题 | 同上，多个用户重复报告 |
| #58 | Skills integrated with Obsidian CLI natively | 建议用 Obsidian CLI 替代文件直接操作 |
| #48 | SessionStart/PostCompact prompt-type hooks rejected by Claude Code v2.1.143 | 同上但版本号更新 |
| #47 | SessionStart prompt-type hook fails: "no conversation context available" | 同上但报错信息不同 |
| #45 | SessionStart and PostCompact prompt-type hooks break under Claude Code v2.1.140+ | 同上 |
| #40 | SessionStart prompt hook fails with ToolUseContext required (4 条评论) | 同上 |
| #37 | Question on real-world ingestion friction | @TomLucidor 问实际使用痛点 |
| #36 | How to using Obsidian Web Clipper save to Obsidian | 用户操作困惑 |
| #33 | Feature request: incremental ingest with source tracking (avoid re-reading unchanged files) | **关键需求，一个月无回复** |
| #29 | SessionStart prompt-type hook fails (7 条评论，最多人关注) | 同上 hook 问题系列 |
| #12 | Proposal: Batch auto-commits per user turn instead of per tool call | PostToolUse → Stop 迁移 |
| #11 | setup-vault.sh doesn't move commands/, skills/, hooks/ to .claude/ directory (7 条评论) | 安装脚本 bug |
| #7 | SessionStart:resume and PostCompact prompt-type hooks fail (3 条评论) | 同 #42 系列 |
| #6 | How large the wiki is acceptable? 300+ files, 4 hours | 性能上限暴露 |
| #5 | .raw folder not visible in Obsidian — breaks Web Clipper integration (5 条评论) | 点文件在 Obsidian 中不可见 |
| #2 | Commands (/wiki, /save) not discovered out of box when using git clone (3 条评论) | 安装摩擦 |
| #25 | Feature Proposal: Glossary | 用户请求 glossary 功能 |

### 关键观察

**claude-obsidian 的 issue 集中暴露三个结构性弱点：**

1. **对 Claude Code 版本变更极度脆弱** — SessionStart/PostCompact prompt hook 问题被 10+ 个独立 issue 反复报告，每个新版本都可能 break。因为它的基础设施深度在 Claude Code 的 hook 层，不是自己的运行时。

2. **性能和可扩展性基础缺失** — #33 (增量 ingest) 一个月无回复，#6 (300 文件 4 小时) 没有机制性的解决。

3. **技能指令的质量控制缺失** — #70 (lint 无标准数据采集)、#69 (wikilink 误报未文档化) 暴露了 "skill 文件就是全部规范" 的极限——没有程序化验证，LLM 每次执行的策略不一致。

---

## 五、基础设施优先级矩阵

```
                     P0: 必须有             P1: 100+ 页前必须         P2: 持续演进需要
                     ──────────             ─────────────────         ──────────────
Provenance 标记       ✅                     —                          —
Delta tracking        ✅                     —                          —
Confidence 量化        —                     ✅                          —
Tier + Token Budget    —                     ✅                          —
Staged Review          —                     —                          ✅
Eval Harness           —                     —                          ✅

为什么这个顺序：
- Provenance + Delta: 没有它们，wiki 的建立就是无效的——  推断污染 + token 成本不可接受
- Confidence + Tier: 100 页之前不紧急，但到了那个规模再补就来不及——需要前端设计就带
- Review + Eval: 代码仓库 ingest 中 LLM 写的推断比例高，"信任建基线"的前提是有人工审核和量化指标
```

---

## 六、对 Code Wiki 项目的启示

### claude-obsidian 的 6k star ≠ 基础设施好

它赢在：
1. **分发渠道** — Claude Code 插件 marketplace 一键安装，零门槛
2. **开箱即用** — hooks 自动注入 hot.md 到 session context，用户甚至感知不到
3. **Obsidian 生态绑定** — 可视化 + 双向链接 + 图谱 = 用户体验好

它输在：
1. **对 Claude Code API 变更极度脆弱** — 10+ 个重复 issue 都是 hook 兼容性
2. **无增量 ingest** — 300 文件 = 4 小时
3. **无质量保证** — 每次 lint LLM 自己发明方法
4. **基础设施几乎为零** — provenance / confidence / tier / eval 全缺
5. **维护者有争议** — AI 生成身份，大量自动化 repo

### 对于 Code Wiki 方向

你是全栈自建的路线（类似 llmwiki-compiler），不是插件路线（类似 claude-obsidian）。这意味着：
- **你需要自己解决核心基建** — provenance + delta + confidence
- **但你可以拿到 claude-obsidian 拿不到的质量上限** — eval harness + CI 门禁
- **你的目标用户更精准** — 不是"会用 Obsidian 的人"，而是"需要跨项目代码理解的架构师和二开人员"

### 关于产品定位

claude-obsidian 的成功证明了一件事：**分发的易用性比技术深度更决定早期增长。** 但这不意味着你要学它——因为在 code wiki 这个更窄的领域，你的用户需要的是技术深度。一个不能区分 LLM 推断和源码事实的 code wiki，用了比没用好不到哪去。

## 关联

- [[agent-framework-domain]]
- [[codebase-wiki-methodology]]
