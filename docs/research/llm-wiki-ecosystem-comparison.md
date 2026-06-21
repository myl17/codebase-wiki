---
title: LLM-Wiki生态三大项目对比分析
category: codebase
depth: representation
tags: [llm-wiki, code-wiki, analysis]
created: 2026-06-05
updated: 2026-06-05
sources:
  - https://github.com/Ar9av/obsidian-wiki
  - https://github.com/atomicstrata/llm-wiki-compiler
  - https://github.com/AgriciDaniel/claude-obsidian
  - https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
---

基于 2026年6月5日实时拉取的 GitHub issue 和 PR 数据，三个基于 Karpathy LLM Wiki 模式的代表性开源项目对比。

## 基本数据（截至 2026-06-05）

| | claude-obsidian | obsidian-wiki | llm-wiki-compiler |
|---|---|---|---|
| Stars | 6,072 | 1,716 | 1,446 |
| Forks | 706 | 190 | 150 |
| Issues 总数 | **31** | 23 | 14 |
| Open / Closed | 25 / 5 | 0 / 23 | 4 / 10 |
| 今日 PR | 0 | 1 (#78 merged) | **6** (#79-86) |
| 维护者 | AgriciDaniel | Ar9av | ethanj (atomicstrata) |
| 创建时间 | 2026-04-07 | 2026-04-06 | 2026-04-05 |
| 本质形态 | Claude Code 插件 | Agent Skills 包 + PyPI CLI | 独立 CLI + MCP Server |

> 三个项目都是在 Karpathy gist 发表后一周内（2026年4月第一周）创建的，距今约2个月。都处于早期快速迭代阶段。

---

## 一号项目：claude-obsidian（6k stars）

### 项目本质

Claude Code 插件 + Obsidian vault 模板。核心机制是通过 `hooks/hooks.json` 在 Claude Code 的 SessionStart/PostToolUse/Stop 生命周期注入 wiki 上下文。用户安装后在 Claude Code 里直接使用 `/wiki`、`/save`、`/autoresearch` 等斜杠命令。

### Issue 真实数据

对 2026-06-05 拉取的 30 条 issue（总量 31）逐条分类：

**A. SessionStart/PostCompact hook 兼容性问题（6 条）**

| # | 状态 | 日期 | 报告者 | 关键信息 |
|---|------|------|--------|---------|
| #42 | CLOSED | 5-13 | @eng-eslam-a-y | "ToolUseContext is required for prompt hooks" |
| #45 | OPEN | 5-16 | @seo-yas | "break under Claude Code v2.1.140+" |
| #47 | OPEN | 5-17 | @fracampit | "no conversation context is available" |
| #48 | OPEN | 5-18 | @sleggett-ai | "rejected by Claude Code v2.1.143" |
| #59 | OPEN | 5-28 | @xXt0rm | "[bug] prompt-type hooks not supported" |
| #61 | OPEN | 5-28 | @ecik666 | "fails on resume" |

同一个问题，6 个不同用户在 6 个不同时间/版本下报告。从最早的 #10（4-16，已关闭）到最新的 #61（5-28），问题持续了 6 周。有一个已合并的解决方案（#42），但后续版本仍然出现。根本原因是 Claude Code 本身在收紧 hook 语义——SessionStart 不提供 ToolUseContext，prompt-type hook 无法运行。

**B. 安装/发现路径（3 条）**

| # | 状态 | 关键信息 |
|---|------|---------|
| #75 | OPEN | README 说 clone 后直接 `/wiki`，实际需要 `--plugin-dir` |
| #11 | OPEN | `setup-vault.sh` 不复制文件到 `.claude/` 目录（7 条评论） |
| #2 | OPEN | git clone 后命令不被发现（3 条评论） |

**C. 架构/质量问题（3 条，高质量反馈）**

| # | 状态 | 报告者 | 关键信息 |
|---|------|--------|---------|
| #70 | OPEN | @hyogoa2c | lint 7 项检查没有标准数据采集方法——Claude 每次临时发明 shell 命令 |
| #69 | OPEN | @hyogoa2c | wikilink 提取假阳性：代码块里的 `[[link]]` 被当作真实引用；表格内 `\|` 转义没处理 |
| #37 | OPEN | @kiluazen | "real-world ingestion friction"——同一个提问者也给 obsidian-wiki 提了 commit-keyed manifest 的建议 |

**D. 功能请求/UX（5 条）**

| # | 状态 | 关键信息 |
|---|------|---------|
| #33 | OPEN | 增量 ingest 请求（5-4 创建，一个月无维护者回复） |
| #6 | OPEN | 300+ 文件 ingest 耗时 4 小时（4-14 创建） |
| #5 | OPEN | `.raw/` 在 Obsidian 中不可见（点文件），破坏 Web Clipper 集成 |
| #25 | OPEN | Glossary 功能请求 |
| #41 | OPEN | 预设 graph.json 供更好的 Obsidian 图谱可视化 |

**E. 维护者争议（已关闭）**

| # | 状态 | 报告者 | 关键信息 |
|---|------|--------|---------|
| #16 | CLOSED | @B0R0koko | "维护者创建了 50+ 类似 repo，大量 AI 生成提交，不是真人？" |
| #14 | CLOSED | @FrancisBehnen | "这个仓库还维护吗？" |

> **注意**：这两条是社区提出的质疑，不是确认的事实。维护者是否真实不影响对代码质量的评估。

**F. 其他（1 条）**

| # | 状态 | 关键信息 |
|---|------|---------|
| #76 | OPEN | CodeGuilds 自动通知（第三方平台注册） |

### PR 真实数据

近 7 天有 8 个 PR：

| # | 状态 | 作者 | 内容 |
|---|------|------|------|
| #74 | OPEN | @EbadSiddiquis | Windows 兼容：`pgrep` 不可用时 fallback 到 `tasklist` |
| #72 | DRAFT | @ryu-kraken | Codex OSS 公共包范围调整 |
| #71 | OPEN | @caioribeiroclw-pixel | 删除不支持的 prompt 生命周期 hooks |
| #68 | OPEN | @eileenallen | 同上，另一个人的独立实现 |
| #66 | OPEN | @kevinassemi | `/autoresearch --merge` 模式：自动将研究发现合并到已有页面 |
| #63 | OPEN | @vinsocci | 本地 Ollama prefix tier：零网络传输的 LLM 级前缀生成 |
| #65 | CLOSED | @tilusnet | 修复 tag 列表中数字值的引用问题 |
| #13 | OPEN | @jhsong-musinsa | 用 jq+command hook 替代 prompt hook（第一个完整的技术方案） |

**社区贡献活跃，但 PR 合并速度慢——多个 PR 在等待维护者 review。**

### 小结

- **用户量最大**（6k stars, 706 forks），社区问题反馈最活跃
- **对 Claude Code 版本变更有脆弱性**——hook 兼容性问题持续 6 周，不同版本反复出现
- 有两个来自 @hyogoa2c 的**高质量架构反馈**（lint 数据采集、wikilink 假阳性），触及了 "skill 文件就是全部规范" 的结构性极限
- **性能上限明确**（#6 300 文件 4 小时），增量 ingest（#33）请求了一个月但无回复
- 好几个用户在独立修同一个 hook 问题（#71, #68, #13），但维护者似乎没有及时合并

---

## 二号项目：obsidian-wiki（1.7k stars）

### 项目本质

Markdown 技能文件包 + Python CLI 安装器。不绑定单一 Agent——通过 symlink 支持 Claude Code、Cursor、Codex、Gemini、Hermes、Pi、OpenClaw 等十几种 Agent。通过 PyPI 分发（`pip install obsidian-wiki`）。

### Issue 真实数据

总量 23，**全部 CLOSED**。按来源分：

**A. 维护者 Ar9av 主动规划（12 条）**

5月15日一天内开了 8 条 feature issue（#43-50），全部在 5月16-18日之间实现并关闭。这是一个**高度纪律化的"先写 issue 再实现"的工作流**：

| # | 内容 | 设计输入来源 |
|---|------|-------------|
| #43 | typed relationships（7种关系类型） | gist 评论 @mikhashev |
| #44 | wiki-dedup（身份消歧+页面去重） | gist 评论 @nowissan |
| #45 | importance tiering（core/supporting/peripheral） | gist 评论 @nowissan |
| #46 | token budget monitoring + footprint report | gist 评论 @ojuschugh1 |
| #47 | wiki-context-pack（bounded token 上下文包） | gist 评论 @paulmchen |
| #48 | wiki-lint --consolidate（dream cycle） | gist 评论 @nowissan |
| #49 | WIKI_STAGED_WRITES（人工审核门） | gist 评论 @rohitg00 + @aadjadj-bit |
| #50 | wiki-status "What to Do Next" 章节 | gist 评论 @waydelyle + @cagataysengor |

> 8 条 feature 全部有明确的 gist 评论区引用作为设计来源。这不是凭空拍脑袋，是在回应社区在 gist 评论区提出的真实需求。

其余维护者开启的 issue：#71(PyPI 打包), #73-74(export/import 增强), #76(pip 升级后 skills 过时), #34(skill 同步)

**B. 外部社区贡献（10 条）**

| # | 报告者 | 内容 |
|---|--------|------|
| #69 | @BenRoe | wiki-quick-chat-capture 技能提案（4 条评论讨论） |
| #66 | @MathiasOki | Hermes named profiles 支持 |
| #64 | @kiluazen | commit-keyed manifest（3 条评论的深度讨论） |
| #62 | @DxVapor | Pi coding agent 支持 |
| #35 | @Jason-Wheeler | daily-update.sh 相对路径 bug |
| #32 | @vvlisn | OpenCode 支持请求 |
| #30 | @madebymlai | config resolution 一致性 |
| #28 | @nova28 | Confidence + Lifecycle 前言行 RFC |
| #26 | @cjescudero | 标准 Markdown link 格式支持 |
| #11 | @Medenor | 仓库缺少 LICENSE 文件 |

**10 条外部 issue，全部 CLOSED。外部反馈处理率为 100%。**

### PR 真实数据

| # | 状态 | 作者 | 内容 |
|---|------|------|------|
| #78 | MERGED 今天 | @Ar9av | wiki-query 多跳关系图遍历 |
| #77 | MERGED | @Ar9av | pip 升级后 skills 过时警告 |
| #75 | MERGED | @BenRoe | _raw source 继承规则修复 |
| #72 | MERGED | @Ar9av | PyPI 打包发布 |
| #70 | MERGED | @Ar9av | wiki-quick-chat-capture 技能 |
| #67 | MERGED | @Ar9av | Hermes named profiles 修复 |
| #65 | MERGED | @Ar9av | wiki-update rebase/force-push 防护 |
| #63 | MERGED | @DxVapor | Pi agent 支持（来自外部） |
| #42 | MERGED | @BenRoe | QMD CLI 传输支持（来自外部） |

**外部贡献者数：3 人（@BenRoe, @DxVapor, @Ic1558）。** @BenRoe 是其中最活跃的，贡献了 3 个 PR 跨越不同领域。

### 小结

- **工程纪律最清晰**——所有 23 个 issue 已关闭，feature 规划有明确的社区来源引用
- **设计决策有可追溯性**——8 条 feature 直接引用了 gist 评论区具体用户的反馈
- **多 Agent 覆盖面**——支持十几种 Agent 的 skill 安装，是三个项目中最广的
- **社区贡献有质量但规模小**——3 个活跃外部贡献者
- **无独立 eval/metrics 系统**——质量依赖 skill 指令的质量，没有程序化验证

---

## 三号项目：llm-wiki-compiler（1.4k stars）

### 项目本质

独立 CLI + MCP Server + 编译管线。完全自包含——TypeScript 实现自有编译引擎、embedding、搜索、eval harness。不依赖任何外部 Agent 运行时。

### Issue 真实数据

总量 14（最少）。OPEN 4，CLOSED 10。

**OPEN：**

| # | 报告者 | 日期 | 内容 |
|---|--------|------|------|
| #78 | @dohu012 | 6-4 | Eval 扩展：source utilization + health weight + page distribution + citation depth + freshness + graph health（带 37 个测试的 fork，维护者已回复建议拆小） |
| #60 | @tienlx91 | 5-19 | 需要一个 `llmwiki rm` 命令删除错误 ingest（1 条评论） |
| #59 | @kiluazen | 5-12 | post-compile verifier 设计讨论（1 条评论） |
| #56 | @suyunzzz | 5-11 | Codex OAuth 支持请求（1 条评论） |

**CLOSED（按日期）：**

| # | 报告者 | 关键信息 |
|---|--------|---------|
| #39 | @lllcccwww | prompt blowup——多 source 共享同一概念时无界拼接→超过 context window。修复：per-concept prompt budget |
| #38 | @ishan5ain | 本地 Web UI 需求讨论（5 条评论）→ 已实现 |
| #37 | @lllcccwww | 输出语言可配置→ 已实现 `--lang` |
| #36 | @lllcccwww | 同名文件 basename 碰撞覆盖→ 已修复 |
| #35 | @lllcccwww | CJK 文件名 slugify 到空字符串→ 已修复 |
| #33 | @lllcccwww | youtube-transcript 依赖版本不兼容→ 一行修复 |
| #11 | @BenGSt | Ollama 10分钟超时→ 已修复（可配置超时） |
| #10 | @sy2ruto | 多源引用 `^[fileA, fileB]` lint 误报→ 已修复 |
| #3 | @goforu | 多 provider 支持请求→ 已实现 |

> 观察到：`@lllcccwww` 在 4月27日一天内提交了 5 个 issue，都是中文用户在使用中遇到的具体 bug。全部在 4月28-29日（1-2天内）修复关闭。

### PR 真实数据（最近 24 小时内）

| # | 状态 | 作者 | 内容 |
|---|------|------|------|
| #86 | OPEN 今天 | @dohu012 | Eval 扩展：source utilization + citation depth（按 #78 讨论缩小范围） |
| #85 | OPEN 今天 | @alvins82 | activity log（log.md）——Karpathy gist 中描述的日志系统 |
| #84 | MERGED 今天 | @ethanj | v0.9.0 README 更新 |
| #83 | MERGED 今天 | @ethanj | Source freshness：page-level freshnessStatus + stale lint |
| #81 | OPEN 昨天 | @alvins82 | Claude Agent SDK provider（用 Claude Code 登录免 API key） |
| #77 | DRAFT | @ethanj | Rule-candidate extraction pipeline（W1-W5） |
| #79 | MERGED 昨天 | @ethanj | Viewer wikilink alias 解析 |
| #74 | MERGED 6-2 | @joshuaknipe | MCP eval tool + eval resources |
| #67 | MERGED 5-27 | @joshuaknipe | Full eval harness（health score + citation + judge + CI 门禁） |

**今日 6 个 PR，其中 2 个已合并、2 个 open review、1 个 draft、1 个 merged 昨天。维护者和社区都在高频提交。**

外部贡献者：@joshuaknipe（eval 系统）、@alvins82（log + Claude SDK provider）、@dohu012（eval 扩展）、@ishan5ain（Web UI 讨论）

### 小结

- **工程速度最快**——今天 6 个 PR，测试数量 1215+，有 fallow 死代码/复杂度检查
- **唯一有程序化质量评估的项目**——eval harness + CI 门禁 + 回归检测
- **社区贡献质量高**——@joshuaknipe 的 eval 系统是近 100 个测试的全功能贡献；@alvins82 同时提了 log.md 和 Claude SDK 两个大 PR
- **issue 数量少**——14 总量说明要么用户少、要么 bug 少。从 4月 @lllcccwww 的 5 个 bug 全部 1-2天修复来看，更像是快速修复降低了后续 issue
- **对外部 Agent 无依赖**——全栈自包含，MCP 和 CLI 双通路

---

## 诚实对比

### 你可以确定的事实

1. **三个项目处于不同的设计路径上，不是同一维度的高下之分。** claude-obsidian 是 Claude Code 生态的"应用层"，obsidian-wiki 是跨 Agent 的"中间件"，llmwiki-compiler 是自包含的"全栈引擎"。

2. **claude-obsidian 用户量最大（6k vs 1.7k vs 1.4k），issue 反馈最多（31），open issue 最多（25/31=81%）。** 说明：(a) 用户是真的在用，(b) 存在一些持续未解决的问题。

3. **obsidian-wiki 的 issue 管理最干净。** 23/23 CLOSED。但大量 issue 是维护者自己规划+自己实现，社区 issue 仅占约 40%（10/23）。

4. **llmwiki-compiler 的代码变更最活跃。** 今日 6 个 PR 涵盖 activity log、source freshness、eval 扩展、viewer 增强等多个维度。有测试门禁、有死代码检查、有 CI。

5. **三个项目都在不到 2 个月内从零建到了可用的程度。** 这说明 llm-wiki 的基础模式（source→compile→wiki→query）已经被充分验证为可行性，争议主要在"用什么架构实现"上。

### 你无法确定的事实

1. **我不知道 claude-obsidian 的维护者是否是 AI 生成的身份。** #16 是一个社区质疑，不是确认事实。即使维护者用了 AI 辅助开发，这也不等于代码质量差。

2. **我不知道哪个项目"基础设施最深"。** 三个项目的架构方式不同，不能直接用同一把尺量。claude-obsidian 依赖 Claude Code 做执行引擎，它的"基础设施"分散在 hooks、skills、scripts 里——跟 llmwiki-compiler 集中在 TypeScript 模块里是不同的组织方式。

3. **我不知道哪个项目会活得更久。** 2 个月的时间太短，任何一个项目都可能在一周内被维护者放弃，也可能在一年后成为标准。

### 三个项目的风险

| | claude-obsidian | obsidian-wiki | llm-wiki-compiler |
|---|---|---|---|
| 平台绑定风险 | 高（依赖 Claude Code） | 低（跨 Agent） | 无（自包含） |
| 维护者风险 | 高（单人，有争议） | 中（单人但活跃） | 低（双人+社区） |
| 质量退化风险 | 中（无程序化验证） | 中（无程序化验证） | 低（有 CI + eval 门禁） |
| 规模天花板 | 已知（#6: 300文件=4h） | 未知 | 已知有解决方案（chunk + BM25） |
| 分发风险 | 低（Claude Code marketplace） | 低（PyPI） | 中（npm global install） |

### 对 Code Wiki 项目的参考价值

**从 claude-obsidian 学什么**：分发是第一增长力。一个 Claude Code 插件就能拿到 6k stars。如果你做的工具也需要用户安装，渠道比功能重要。但注意它对 Claude Code 的脆弱依赖——所有的 hook 兼容性问题都在这里。

**从 obsidian-wiki 学什么**：设计决策的可追溯性。每条 feature 都引用 gist 评论区具体反馈，这让项目有方向感。你的维度表和代码三步法也可以追溯到你和小步的讨论笔记。

**从 llmwiki-compiler 学什么**：工程质量是可以量化的。eval harness + CI 门禁 + fallow + 1215 测试——这些不是"以后再做"的装饰，而是"现在就做"的地基。2 个月内能做到的工程标准。

**三个项目共同的空白**：代码仓库作为一等 raw source。没有一个项目在 skill/CLI 层面明确区分了 "这是文章，直接提炼观点" 和 "这是代码仓库，需要维度表指导提取"。**这就是你的空间。**

## 关联

- [[agent-framework-domain]]
- [[codebase-wiki-methodology]]
