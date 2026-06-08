# Codebase Wiki 实现计划评审

**评审对象：** [2026-06-08-codebase-wiki.md](../plans/2026-06-08-codebase-wiki.md)  
**评审日期：** 2026-06-08  
**结论：** 方向正确、任务拆分完整，但 manifest 状态、wikilink 路径、hook JSON 等契约需在实现前收紧。

---

## 计划概要

| 维度 | 内容 |
|------|------|
| 目标 | Claude Code 插件：多仓库按共享维度抽取知识，支持查询与跨仓对比 |
| 架构 | `raw/`（只读源码）+ `wiki/`（LLM 产出）+ `schema/` / `scripts/` / `skills/`（工具层） |
| 命令 | `/analyze`、`/query`、`/compare`、`/lint` |
| 技术栈 | Python 3 stdlib、Bash、Markdown、Claude Code hooks + SKILL.md |
| 任务规模 | 13 个 Task，P0（Week 1）→ P1（Week 2）→ P2（Week 3） |

**证据：** plan L5–9, L36–1945

---

## 优点（有证据）

1. **目标与边界清晰** — LLM 写 wiki，Python 做确定性工作（hash、状态、lint）。证据：plan L5–9  
2. **分层合理** — raw / wiki / tooling 职责分离。证据：plan L5–9  
3. **端到端拆分完整** — scaffold → schema → delta/manifest → hook → skills → lint/eval。证据：plan L36–1945  
4. **脚本层测试先行** — delta、manifest、lint、eval 均先写 failing test。证据：plan L279–538, L555–780, L1201–1553, L1641–1875  

---

## 风险与优化建议

### High

| # | 问题 | 证据 | 建议 |
|---|------|------|------|
| 1 | **Manifest 丢失 file hashes，delta 无法真正增量** | `manifest.py update` 硬编码 `{}`（L747–750）；`/analyze` 只更新 completed/pending/timestamp（L963–976） | 给 `manifest update` 增加 `--hashes-json` 或 `--delta-json`；`/analyze` 写 wiki 后持久化当前 hashes |
| 2 | **Wikilink 规范与 lint 不一致** | 文档用 `[[react/overview]]`（L960–982），文件在 `wiki/repos/react/overview.md`；lint 比较 `repos/react/overview`（L1343–1352） | 统一 link resolver，或调整目录结构与链接格式一致 |
| 3 | **SessionStart hook 可能输出非法 JSON** | `hot.md` / log 直接拼进 JSON 字符串（L812–831） | 用 `python json.dumps` 或 `jq -Rs` 生成 |
| 4 | **stale_count 可能误报为 1** | 无 stale 时打印 `No stale repos.`；hook 用 `grep -c .`（L754–760, L822–825） | `manifest stale --json`；hook 只统计数组长度 |

### Medium

| # | 问题 | 证据 | 建议 |
|---|------|------|------|
| 5 | **`/query` 依赖 `summary` frontmatter 但未定义** | query Level 2（L1037–1041）vs frontmatter 仅 repo/dimension/version/generated/status（L230–240） | 加入 required `summary`，或删除 Level 2 |
| 6 | **views freshness 读不到 YAML list sources** | frontmatter parser 只支持单行 `key: value`（L1487–1493） | 最小 YAML list 解析，或改为单行 JSON 数组 |
| 7 | **stale 状态无闭环** | compare 看 `status: stale`（L1135–1138），lint 看 dimensions_version（L1361–1380），无写入 stale 的流程 | compare 直接比对 manifest version，或提供 `mark-stale` |
| 8 | **delta 缺 ignore / 大文件保护** | 只跳过隐藏路径，全量 `read_bytes`（L456–469） | 默认 ignore、`node_modules`、文件大小上限、`.codebase-wikiignore` |

### Low

| # | 问题 | 证据 | 建议 |
|---|------|------|------|
| 9 | **`.manifest.json` 版本控制策略矛盾** | 文件结构写 git-ignored template（L29），Task 1 又 commit（L82–98） | 提交 `.manifest.example.json`，`.manifest.json` 进 `.gitignore` |

---

## 建议修改顺序

**实现脚本前：**

1. 统一 wiki 路径与 wikilink 契约  
2. 修复 manifest hash 持久化  
3. 安全生成 hook JSON  

**上真实仓库前：**

4. delta 增加 ignore 与大文件/二进制保护  
5. 补 `summary` frontmatter 或调整 `/query` 检索链  
6. stale 从 manifest 推导，而非依赖手工 `status`  

---

## 与 plan 自评的差异

Plan 文末写「All spec requirements covered. No gaps found.」（L1940）。上述 9 项为基于 plan 原文的可验证缺口，建议在动手实现前先修订 plan 或 spec。
