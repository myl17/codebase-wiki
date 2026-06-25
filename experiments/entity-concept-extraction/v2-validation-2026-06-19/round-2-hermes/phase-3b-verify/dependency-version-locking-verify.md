# 验证报告：dependency-version-locking

## 格式完整性 (checklist)

- [x] 标准化问题陈述
- [x] 核心关切 (7 项)
- [x] 已知权衡位置 (A: openclaw 风险分级锁定, B: hermes-agent 三层统一锁定)
- [x] 每个位置: 优先满足的关切 / 接受妥协的关切 / 核心特征 / 关键机制 / 已知代价
- [x] 跨仓库对比表 (11 维度)
- [x] 选择指南 (8 场景)
- [x] 溯源表 (13 行)
- [x] 关联链接
- [ ] 关切-实现对应: 关切 7 (源码内嵌边界) 在对比表中有 "vendor/bundle" 维度行 ✅
- [x] 每个仓库在各维度都有描述
- [x] 权衡位置分类: A="风险分级锁定", B="三层统一锁定" — 正确映射

## 逐仓库验证

### OpenClaw (位置 A)

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| 1 | `package.json:140-193` 53 个 dependencies，12 精确 + 41 范围 | ❌ | `openclaw-dependency-strategy.md` line 73 原始标注为 "70 个 runtime deps 中 29 个精确锁定（无 ^/~），41 个用范围版本"。概念页声明的 53/12 与维度原始提取的 70/29 冲突。修正建议：将 53→70, 12→29，或说明计数口径差异（是否排除了 types/workspace deps 等）。溯源表 line 124 同样修正 |
| 2 | 精确锁定覆盖 `@agentclientprotocol/sdk`、`@mariozechner/*` x4、`@lydell/node-pty`、`playwright-core`、`sqlite-vec`、`@sinclair/typebox`、`@whiskeysockets/baileys`、`@buape/carbon`、`tar` | ⚠️ | 维度文件列出的精确锁定列表为: `@mariozechner/*` x4、`@modelcontextprotocol/sdk`(1.29.0)、`@agentclientprotocol/sdk`(0.18.2)、`sqlite-vec`、`playwright-core`、`@lydell/node-pty`、`matrix-js-sdk`、`hono`(4.12.12)。概念页列出了 `@sinclair/typebox`、`@whiskeysockets/baileys`、`@buape/carbon`、`tar` 但维度文件未列出；维度文件列出了 `@modelcontextprotocol/sdk`、`matrix-js-sdk`、`hono` 但概念页未在直接 deps 精确锁列表中列出。两组列表不一致。修正建议：对齐维度文件，或说明来源差异（package.json 版本变更/提取口径不同） |
| 3 | `hono` 版本 `4.11.10` (pnpm overrides) | ❌ | `openclaw-dependency-strategy.md` line 78 标注 `hono` 精确锁定 `4.12.12`。概念页的 `4.11.10` 与维度提取冲突。修正建议：改为 `4.12.12` |
| 4 | `@sinclair/typebox` 版本 `0.34.48` (pnpm overrides) | ❌ | `openclaw-dependency-strategy.md` line 52 标注 `@sinclair/typebox` 精确锁定 `0.34.49`。概念页的 `0.34.48` 与维度提取冲突。修正建议：改为 `0.34.49` |
| 5 | 10 个 pnpm overrides 全部精确锁定 | ✅ | `openclaw-dependency-strategy.md` line 78-79 + 未逐项列出但维度文件提到了 overrides 用于 `tsdown`/`oxfmt`/`jscpd` 等构建工具链 |
| 6 | `node-llama-cpp` 精确锁 `3.15.1` | ❌ | `openclaw-dependency-strategy.md` line 61 标注 `3.18.1`。概念页的 `3.15.1` 与维度提取冲突。修正建议：改为 `3.18.1`，溯源表 line 126 同样修正 |
| 7 | `@napi-rs/canvas` `^0.1.89` (peer dep) | ⚠️ | 维度文件仅说 "@napi-rs/canvas：Canvas 渲染能力" 未标注版本号。无法从维度文件验证 `^0.1.89` 具体值。标记为无法独立验证 |
| 8 | Docker `FROM node:22-bookworm@sha256:cd7bcd2e7...` | ⚠️ | `openclaw-architecture.md` 未提及 Dockerfile SHA256。维度文件和节点文件均未覆盖 Docker 层。无法从可用源验证。保持为 ⚠️（可信但无直接证据） |
| 9 | `@discordjs/opus` `^0.10.0` (optional dep) | ⚠️ | 维度文件仅说 "@discordjs/opus：Discord 语音编解码" 未标注版本号。无法独立验证版本值 |
| 10 | `pnpm.minimumReleaseAge: 2880` (延迟2天) | ⚠️ | 维度文件未提及此配置。无法从可用源验证。概念页 line 128 溯源表引用 `package.json:228`，无法验证 |
| 11 | `@mariozechner/*` 四件套精确锁定同一版本 `0.66.1` | ✅ | `openclaw-dependency-strategy.md` line 27 + `openclaw-mariozechner-core-dependency.md`: "四包精确锁定同一版本，与主版本号同步发布" |

### Hermes-Agent (位置 B)

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| 12 | 17 个核心依赖全部 `>=lower,<upper` 双边界定 | ⚠️ | `hermes-agent-dependency-strategy.md` 明确列出 7 个 "核心依赖（无替代方案）": openai/anthropic/httpx/prompt_toolkit/pydantic/rich/tenacity。概念页说 17 个核心依赖——比维度文件的 7 个多了 10 个。这可能是术语差异：维度文件的 "核心" 指 "无可替代方案"，概念页的 "核心" 可能指 "所有非可选直接依赖"。修正建议：明确说明 "17 个" 的计数口径（是否包含了 requests/pyyaml/aiohttp/aiofiles/pyperclip 等其他直接依赖），并与维度文件的 "7 个无替代方案" 术语做区分 |
| 13 | CVE 标注: `requests>=2.33.0` (CVE-2026-25645), `PyJWT>=2.12.0` (CVE-2026-32597) | ✅ | `hermes-agent-dependency-strategy.md` line 99: "requests>=2.33.0 修复 CVE-2026-25645；PyJWT>=2.12.0 修复 CVE-2026-32597" |
| 14 | `uv.lock` 5512 行精确锁定 ~200+ 传递依赖 | ✅ | `hermes-agent-dependency-strategy.md` line 122: "uv.lock 5512 行，覆盖全依赖树", line 121: "传递依赖 ~200+" |
| 15 | Docker 2 个 FROM: `ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c...` + `tianon/gosu:1.19-trixie@sha256:3b176695959c...` | ⚠️ | `hermes-agent-dependency-strategy.md` line 104: "Docker 基础镜像全部使用 SHA256 digest 固定" 但未列出具体镜像名和 digest 前缀。概念页的具体 digest 值无法从维度文件独立验证。标记为无法验证（可信但无直接证据） |
| 16 | `uv venv && uv pip install --no-cache-dir -e ".[all]"` (Dockerfile:38-39) | ⚠️ | 维度文件未逐行引用 Dockerfile。无法从可用源验证具体行号和命令 |
| 17 | Git 依赖精确 pin: `atroposlib@c20c852`, `tinker@30517b6` | ✅ | `hermes-agent-dependency-strategy.md` lines 112-113: atroposlib @ c20c852, tinker @ 30517b6. 一致 |
| 18 | 20+ optional extras 全部独立声明版本边界 | ✅ | `hermes-agent-dependency-strategy.md` line 46: "20+ optional extras 将单体重安装拆分为按需安装 ^[pyproject.toml:39-115]" |
| 19 | `matrix` extra 仅 Linux, `yc-bench` 仅 Python >= 3.12 | ✅ | `hermes-agent-dependency-strategy.md` line 60: 两个条件依赖均标注 |
| 20 | 无 vendor/bundle 策略 | ✅ | `hermes-agent-dependency-strategy.md` line 42: "无 vendor/bundle 策略 — 所有依赖通过 PyPI + lockfile 管理" |

### 跨概念页一致性检查

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| C1 | `node-llama-cpp` 版本: 本页 `3.15.1`, optional-dependency-layering.md `3.18.1` | ❌ | 已在 optional-dependency-layering 验证报告中标注。维度提取原始值为 `3.18.1`，本页需要修正 |
| C2 | openclaw 依赖数量: 本页 53/12, optional-dependency-layering.md 70/29 | ❌ | 已在 optional-dependency-layering 验证报告中标注。维度提取原始值为 70/29 |
| C3 | `openshell` 版本: 本页溯源表未列出 openshell, optional-dependency-layering.md 列出 `0.1.0` | ⚠️ | 本页溯源表 line 127 optionalDependencies 仅列出 `@discordjs/opus ^0.10.0`，遗漏 `@matrix-org/matrix-sdk-crypto-nodejs` 和 `openshell`。修正建议：补充完整 optional deps 列表 |
| C4 | `hono` 版本: 本页 says `4.11.10`, 维度文件 says `4.12.12` | ❌ | 独立于跨页比较，直接与维度原始提取冲突 |
| C5 | openclaw 精确锁定列表: 本页列出 `@whiskeysockets/baileys`/`@buape/carbon`/`tar`，维度文件列出 `@modelcontextprotocol/sdk`/`matrix-js-sdk`/`hono` | ❌ | 两组列表几乎完全不重叠（除 `@agentclientprotocol/sdk`/`@mariozechner/*`/`sqlite-vec`/`playwright-core`/`@lydell/node-pty` 外）。修正建议：对齐维度文件，说明差异原因 |

## 关切验证

### 关切-对比表对应检查

| 关切 | 对比表对应维度 | 是否覆盖 |
|------|--------------|---------|
| 1. 协议 SDK 不兼容变更 | "版本声明策略" (协议 SDK 精确锁) | ✅ |
| 2. Native addon 版本敏感性 | "精确锁定数量" (native addon 精确锁) | ✅ |
| 3. 核心引擎的全局影响 | "版本声明策略" (核心引擎全锁) | ✅ |
| 4. 工具类库维护负担 | "精确锁定数量" (工具库范围版本) | ✅ |
| 5. 版本范围宽松度权衡 | "Lockfile 机制" + "版本上限" | ✅ |
| 6. 容器层可重复性 | "Docker 可重复性" | ✅ |
| 7. 源码内嵌边界 | "vendor/bundle" | ✅ |

所有 7 项关切在对比表中均有对应维度。

### 权衡位置分类验证

- **位置 A (openclaw)**: "风险分级锁定" — 正确。高风险精确锁 + 低风险范围版本，与维度文件描述一致。
- **位置 B (hermes-agent)**: "三层统一锁定" — 正确。范围锁 + 精确锁 + Docker 层，与维度文件描述一致。但 "统一" 的说法需注意：hermes 确实不按风险分级（所有直接 deps 统一双边界定），但通过 uv.lock 提供了精确层——严格来说并非 "统一"，而是 "多层叠加"。

## 绝对化语言标记

| 位置 (行) | 语言 | 风险 |
|-----------|------|------|
| line 64: "所有 17 个核心依赖统一采用 `>=lower,<upper` 双边界定" | "所有...统一" | 中风险——维度文件仅确认 7 个核心依赖。17 这个数字无法独立验证。修正建议：区分 "无替代方案核心(7)" 和 "所有直接依赖(~17)" 两种口径 |
| line 77: "任何依赖的版本变更都需要更新 lockfile" | "任何...都" | 低风险——uv.lock 机制确实如此 |
| line 96: "所有核心依赖有 `<major+1` 显式上限" | "所有...有" | 中风险——与 #12 相同，17 这个总数无法独立验证 |
| line 104: "完全可重复构建压倒一切" | "压倒一切" | 低风险——这是对取舍的定性描述，非事实声明 |
| line 103: "确保所有环境安装结果 bit-identical" | "所有...bit-identical" | 中风险——uv.lock + Docker SHA256 确实提供强可重复性，但 "bit-identical" 是一个极强的声称（要求相同的 Python 版本、OS、架构）。修正建议：改为 "确保多环境安装的依赖版本完全确定" |

## 追加完整性

### 两个仓库在各节描述完整性

| 章节 | openclaw 覆盖 | hermes-agent 覆盖 | 完整? |
|------|-------------|-----------------|------|
| 优先满足的关切 | 关切 1,2,3,4 | 关切 5,6,7 | ✅ |
| 接受妥协的关切 | 关切 5 | 关切 4 | ✅ |
| 核心特征 | ✓ | ✓ | ✅ |
| 关键机制 | 4 项 (分级+overrides+peer半锁+Docker) | 6 项 (双边界定+uv.lock+Docker+Git+条件约束+extras) | ✅ |
| 已知代价 | 4 项 | 4 项 | ✅ |
| 已知实例 | 2 个节点 | 1 个节点 | ⚠️ hermes 仅 1 个实例链接——可比 openclaw 少。hermes 的维度文件没有 generated-dimension-links 指向其他相关节点，可能确实是唯一关联节点 |
| 溯源表完整性 | ⚠️ optionalDependencies 遗漏 `@matrix-org/matrix-sdk-crypto-nodejs` 和 `openshell` | ✅ | ⚠️ |

### 溯源表行号验证

| 溯源表行 | 仓库 | 文件 | 行号 | 可验证? |
|----------|------|------|------|--------|
| package.json:140-193 | openclaw | package.json | 140-193 | ⚠️ 文件不存在于本仓库，行号来源于维度提取，无法二次验证 |
| package.json:227-240 | openclaw | package.json | 227-240 | ⚠️ 同上 |
| package.json:216-219 | openclaw | package.json | 216-219 | ⚠️ 同上 |
| package.json:220-222 | openclaw | package.json | 220-222 | ⚠️ 同上 |
| package.json:228 | openclaw | package.json | 228 | ⚠️ 同上 |
| Dockerfile:1 | openclaw | Dockerfile | 1 | ⚠️ 同上 |
| pyproject.toml:13-37 | hermes-agent | pyproject.toml | 13-37 | ⚠️ 同上 |
| pyproject.toml:39-115 | hermes-agent | pyproject.toml | 39-115 | ⚠️ 同上 |
| pyproject.toml:82-89 | hermes-agent | pyproject.toml | 82-89 | ⚠️ 同上 |
| pyproject.toml:94-96 | hermes-agent | pyproject.toml | 94-96 | ⚠️ 同上 |
| uv.lock | hermes-agent | uv.lock | — | ⚠️ 同上 |
| Dockerfile:1-2 | hermes-agent | Dockerfile | 1-2 | ⚠️ 同上 |
| Dockerfile:38-39 | hermes-agent | Dockerfile | 38-39 | ⚠️ 同上 |

**注意**: 所有溯源表行号均来源于维度提取阶段，原始源码文件不在本仓库中，无法做行号精确验证。

## 汇总

| 类别 | 总计 | ✅ | ⚠️ | ❌ |
|------|------|-----|------|-----|
| OpenClaw 声明 | 11 | 2 | 4 | 5 |
| Hermes 声明 | 9 | 6 | 3 | 0 |
| 跨概念页一致性 | 5 | 0 | 1 | 4 |
| 绝对化语言 | 5 | 1 (低风险) | 4 (中风险) | 0 |
| **总计** | **30** | **9** | **12** | **9** |

### 关键发现

1. **本 Concept 页存在 5 处与维度原始提取的事实冲突**——这是本轮三个 Concept 中问题最严重的一个:
   - `node-llama-cpp` 版本: `3.15.1` 应为 `3.18.1`
   - openclaw 依赖数量: `53/12` 应为 `70/29`
   - `hono` 版本: `4.11.10` 应为 `4.12.12`
   - `@sinclair/typebox` 版本: `0.34.48` 应为 `0.34.49`
   - openclaw 精确锁定列表与维度文件几乎不重叠
2. **hermes "17 个核心依赖" 术语模糊**——维度文件的 "核心" = 7 个无可替代方案，概念页的 "核心" = 所有非可选直接依赖。需明确术语口径。
3. **4 项绝对化语言**主要集中在 hermes 侧的 "所有...统一" / "所有...bit-identical" 等全面性声称。
4. **所有溯源表行号无法二次验证**——原始源码不在本仓库中，这是所有三个 Concept 页的系统性限制。
5. **版本号不一致的模式**: 本页的版本号普遍比维度提取的版本号 **更低/更旧**（3.15.1 vs 3.18.1, 4.11.10 vs 4.12.12, 0.34.48 vs 0.34.49），暗示本页可能基于更早的源码快照生成。
