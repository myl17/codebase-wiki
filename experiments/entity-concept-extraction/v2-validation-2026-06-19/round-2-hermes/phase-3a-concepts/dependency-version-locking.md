---
concept: dependency-version-locking
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# 依赖版本锁定：按风险分级还是全量统一？

## 标准化问题陈述

在管理项目依赖时，如何决定版本锁定的粒度——是全部精确锁定、全部范围版本，还是按风险级别分类锁定？

## 核心关切

1. **协议 SDK 的不兼容变更**：协议 SDK 的 breaking change 直接导致功能故障——如 MCP 协议、Agent Client Protocol 的变更会使通信层中断
2. **Native addon 的版本敏感性**：含 C/C++ 编译的包（sqlite-vec、playwright-core、node-pty）在不同平台上对版本高度敏感，编译失败难以排查
3. **核心引擎的全局影响**：AI agent 引擎的 breaking change 影响整个系统行为——替换成本极高且覆盖全部子系统
4. **工具类库的维护负担**：工具类库（commander、chalk、uuid）的 patch 变更不影响行为——范围版本允许自动 patch 可降低维护负担
5. **版本范围的宽松度权衡**：太松则可重复性差（CI/新成员环境安装结果不确定），太紧则更新成本高（每次安全修复都需手动调整）
6. **容器层的可重复性**：Docker 基础镜像版本浮动导致构建不可重复——需像代码依赖一样固定
7. **源码内嵌的边界**：是否内嵌第三方源码（vendor/bundle）——内嵌保证可重复性但升级困难且仓库体积膨胀；不内嵌依赖包管理器的 lockfile 机制兜底

## 已知权衡位置

### 位置 A：openclaw — 风险分级锁定

**优先满足的关切**：关切 1（协议 SDK 精确锁，防止不兼容中断）、关切 2（native addon 精确锁，防止编译失败）、关切 3（核心引擎 `@mariozechner/*` 四件套精确锁同一版本）、关切 4（工具类库范围版本允许自动 patch，降低维护负担）

**接受妥协的关切**：关切 5（范围版本的宽松程度——工具类库用 `^` 前缀，可重复性依赖 pnpm-lock.yaml 兜底而非版本声明本身）

**核心特征**：将 70 个运行时依赖按风险分为两类——高风险依赖（协议 SDK、native addon、核心引擎、关键框架）精确锁定共 29 个，低风险工具类库使用范围版本共 41 个。此外通过 pnpm overrides 额外精确锁定 10 个传递依赖（包括 hono、@sinclair/typebox、tar 等），覆盖构建工具链中版本敏感的传递依赖。Docker 基础镜像使用 SHA256 digest 固定。

**关键机制（源码可见）**：

1. **70 个运行时依赖的分级**（`package.json:140-193`）：共 70 个 `dependencies`，其中 29 个精确锁定（无版本前缀），41 个使用 `^` 范围版本。精确锁定覆盖：`@modelcontextprotocol/sdk`（`1.29.0`，MCP 协议）、`@agentclientprotocol/sdk`（`0.18.2`，Agent Client 协议）、`@mariozechner/*`（核心引擎 4 件套，同一版本）、`@lydell/node-pty`（native addon）、`playwright-core`（native 浏览器引擎）、`sqlite-vec`（native 向量数据库）、`matrix-js-sdk`（Matrix 协议）、`hono`（`4.12.12`，HTTP 框架）等。范围版本用于 `commander`、`chalk`、`yaml`、`uuid`（通过 `zod`）等工具类库。

2. **pnpm overrides 额外精确锁定传递依赖**（`package.json:227-240`）：10 个 pnpm overrides 全部精确锁定，覆盖 `hono`（HTTP 框架，`4.12.12`）、`@sinclair/typebox`（`0.34.49`，与直接依赖版本一致）、`tar`（`7.5.9`）、`fast-xml-parser`（`5.3.6`）、`tough-cookie`（`4.1.3`）等。overrides 机制确保传递依赖树中的这些包版本不受上游范围声明的浮动影响。

3. **peer dependencies 的半锁定策略**（`package.json:216-219`）：`node-llama-cpp` 精确锁定 `3.18.1`（本地 LLM 推理，安装体积 GB 级，设为 peer 避免默认拉入）；`@napi-rs/canvas` 使用范围 `^0.1.89`（Canvas 渲染，用户自行安装）。

4. **Docker 基础镜像 SHA256 固定**（`Dockerfile:1`）：`FROM node:22-bookworm@sha256:cd7bcd2e7...`，确保容器层的完全可重复性。

**已知代价**：
- 精确锁定的包需手动维护升级——每次协议 SDK 或 native addon 的安全修复都需要人工介入
- 分类边界依赖人工判断——新增依赖归入哪一类没有自动化规则，依赖人的风险感知
- pnpm overrides 的精确锁定会覆盖上游包的版本声明——可能与上游测试过的版本组合不一致
- 范围版本的自动 patch 升级虽然方便，但 `^` 语义仍允许 minor 版本升级——minor 变更可能引入非破坏性但意外的行为变化

**已知实例**：
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]]
- [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]]

---

### 位置 B：hermes-agent — 三层统一锁定

**优先满足的关切**：关切 5（可重复性——三层叠加确保从开发到部署的版本完全确定）、关切 6（容器层可重复性——Docker SHA256 固定 2 个基础镜像 + uv pip install 可重复安装）、关切 7（无 vendor——所有依赖通过 PyPI + lockfile 管理，不内嵌第三方源码）

**接受妥协的关切**：关切 4（更新成本——任何依赖的版本更新都需要手动调整 `>=lower,<upper` 边界，无法像 `^` 那样自动吸纳兼容版本）

**核心特征**：所有直接依赖（约 17 个非可选包）统一采用 `>=lower,<upper` 双边界定（如 `openai>=2.21.0,<3`），不像 openclaw 那样区分风险等级——所有依赖一视同仁。这构成了第一层范围锁。第二层 `uv.lock`（5512 行）精确锁定全依赖树的 hash，确保包管理层面的完全可重复。第三层 Docker 构建中使用 SHA256 digest 固定基础镜像 + `uv pip install` 从 lockfile 安装。Git 依赖精确 pin 到 commit SHA。可选依赖 20+ extras 也全部在 `pyproject.toml` 中单独声明版本边界。

**关键机制（源码可见）**：

1. **直接依赖的双边界定**（`pyproject.toml:13-37`）：17 个直接依赖全部使用 `>=lower,<upper`（如 `openai>=2.21.0,<3`、`anthropic>=0.39.0,<1`、`httpx>=0.28.1,<1`、`pydantic>=2.12.5,<3`）。`<major+1` 上限防止大版本破坏，同时 `>=lower` 允许安全补丁自动采纳。CVE 修复在约束声明中显式标注（`requests>=2.33.0` 修复 CVE-2026-25645，`PyJWT>=2.12.0` 修复 CVE-2026-32597）。注：维度文件中将其中 7 个定义为"核心依赖（无替代方案）"（openai/anthropic/httpx/prompt_toolkit/pydantic/rich/tenacity），本处"直接依赖"为更宽泛口径。

2. **uv.lock 全依赖树 hash 锁定**（`uv.lock`）：5512 行精确锁定了 ~200+ 传递依赖的具体版本和 hash。任何依赖的版本变更都需要更新 lockfile，在版本声明层面提供了传递依赖的完全可重复性。

3. **Docker 三层可重复构建**（`Dockerfile:1-3,38-39`）：第 1 行 `FROM ghcr.io/astral-sh/uv:0.11.6-python3.13-trixie@sha256:b3c543b6c...` 和第 2 行 `FROM tianon/gosu:1.19-trixie@sha256:3b176695959c...` 使用 SHA256 digest 固定基础镜像。第 38-39 行 `uv venv && uv pip install --no-cache-dir -e ".[all]"` 从 lockfile 可重复安装。

4. **Git 依赖精确 pin commit**（`pyproject.toml:82-89`）：`atroposlib @ git+https://github.com/NousResearch/atropos.git@c20c852...` 和 `tinker @ git+https://github.com/thinking-machines-lab/tinker.git@30517b6...`，Git 依赖全部精确锁定到 commit SHA，不跟随分支。

5. **可选依赖的条件约束**（`pyproject.toml:94-96,89`）：`matrix` extra 仅在 Linux 上可用（`python-olm` 上游 macOS 不兼容）；`yc-bench` 仅 Python >= 3.12。

6. **20+ optional extras 全部独立声明版本边界**（`pyproject.toml:39-115`）：messaging、voice、web、rl 等每个 extra 内部的所有依赖也使用 `>=lower,<upper` 边界，不因是可选依赖而放松约束。

**已知代价**：
- 版本更新需要手动调整范围——即使 patch 升级也需要检查并更新 `>=lower` 边界
- `<upper` 边界可能过于保守——大版本未发布前即设置 `<major+1`，可能排除后续兼容的大版本
- 双边界定的维护负担与依赖数量成正比——17 个直接依赖 + 20+ extras 的每个依赖都需要维护
- uv.lock 的 5512 行虽然保证了可重复性，但 PR review 中 lockfile 变更难以人工审查

**已知实例**：
- [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]]

---

## 跨仓库对比

| 维度 | openclaw（风险分级锁定） | hermes-agent（三层统一锁定） |
|------|--------------------------|-------------------------------|
| **版本声明策略** | 高风险精确锁（29/70）+ 低风险 `^` 范围版本（41/70）——按风险分类 | 全部 `>=lower,<upper` 双边界定（17 个直接依赖）——不分风险等级 |
| **精确锁定数量** | 直接 deps: 29 精确 + pnpm overrides: 10 精确 = 39 个精确固定位置 | 17 个直接依赖 + 20+ extras 全部双边界定（约 50+ 条版本约束） |
| **Lockfile 机制** | pnpm-lock.yaml（node 生态标准） | uv.lock（5512 行，覆盖 ~200+ 传递依赖 hash） |
| **传递依赖控制** | pnpm overrides 精确锁定 10 个关键传递依赖 + pnpm.minimumReleaseAge:2880 延迟新版本 | uv.lock 全量 hash 锁定所有传递依赖 |
| **Docker 可重复性** | 基础镜像 SHA256 固定（1 个 FROM） | 基础镜像 SHA256 固定（2 个 FROM，uv + gosu）+ uv pip install 可重复安装 |
| **版本上限** | 无显式上限——精确锁无版本范围，`^` 范围版本依赖 lockfile 兜底 | 所有直接依赖有 `<major+1` 显式上限，防止大版本破坏 |
| **CVE 应急** | 通过 overrides 精确锁定修复版本（如 tar:7.5.9、tough-cookie:4.1.3） | 在依赖声明中显式标注 CVE 关联（requests>=2.33.0、PyJWT>=2.12.0） |
| **Git 依赖** | 无 Git 依赖——全部通过 npm registry | 2 个 Git 依赖精确 pin commit SHA（仅限可选 rl extra，非核心路径） |
| **vendor/bundle** | 无——依赖 pnpm-lock.yaml 管理 | 无——依赖 PyPI + uv.lock 管理 |
| **新增依赖的决策流程** | 人工判断风险等级 → 选择精确或范围 | 统一使用双边界定 → 无需风险分类判断 |
| **核心取舍** | 精准控制高风险依赖的版本（安全性），同时通过范围版本降低工具库的维护负担（维护性） | 完全可重复构建压倒一切（可重复性），接受版本更新需要手动调整的维护成本 |

## 选择指南

| 场景 | 推荐偏向 | 理由 |
|------|---------|------|
| 存在高风险依赖（协议 SDK、native addon、闭源核心引擎），这些包的 breaking change 会导致系统故障 | 风险分级锁定 | 对高风险依赖精确锁定防止意外破坏，对工具库放宽版本降低维护负担——资源的聚焦投入 |
| 团队规模小、维护人力有限，需要自动吸纳安全补丁 | 风险分级锁定 | `^` 范围版本 + lockfile 兜底允许 `pnpm update` 批量升级低风险依赖，无需每个依赖都手动调整 |
| 需要多环境（开发/CI/生产/Docker）的完全可重复构建 | 三层统一锁定 | uv.lock 全量 hash + Docker SHA256 确保多环境安装的依赖版本完全确定（前提：相同 Python 版本/OS/架构） |
| 依赖数量多（~200+ 传递依赖）且需要审计传递依赖变更 | 三层统一锁定 | uv.lock 5512 行涵盖全依赖树，任何传递依赖变更都会被 lockfile diff 暴露 |
| 需要 CVE 可追溯的版本决策记录 | 三层统一锁定 | 在 pyproject.toml 中显式标注 CVE 编号（`requests>=2.33.0  # CVE-2026-25645`），版本边界的选择理由留在源码中 |
| 需要严格控制传递依赖树中特定包的版本（如处理菱形依赖冲突） | 风险分级锁定 | pnpm overrides 机制允许对传递依赖中任意位置的包做精确覆盖 |
| 依赖主要是纯 JavaScript/TypeScript，很少 native addon | 风险分级锁定 | 风险分级收益最大——JS 生态的 native addon 是主要风险源，如果很少则分级锁定成本低 |
| 依赖主要来自 PyPI 且生态中大版本破坏频率较高 | 三层统一锁定 | `<major+1` 上限主动防御大版本破坏，不依赖人工判断每个包的风险等级 |

## 溯源表

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `package.json` | 140-193 | 70 个 `dependencies`：29 个精确锁定（含 `@modelcontextprotocol/sdk`、`@agentclientprotocol/sdk`、`@mariozechner/*` x4、`@lydell/node-pty`、`playwright-core`、`sqlite-vec`、`matrix-js-sdk`、`hono` 等），41 个 `^` 范围版本 |
| openclaw | `package.json` | 227-240 | 10 个 pnpm overrides 全部精确锁定：`hono`（4.12.12）、`@sinclair/typebox`（0.34.49）、`tar`（7.5.9）、`fast-xml-parser`（5.3.6）、`tough-cookie`（4.1.3）等传递依赖 |
| openclaw | `package.json` | 216-219 | `peerDependencies`：`node-llama-cpp` 精确锁 3.18.1（本地 LLM），`@napi-rs/canvas` `^0.1.89`（Canvas） |
| openclaw | `package.json` | 220-222 | `optionalDependencies`：`@discordjs/opus` `^0.10.0`（Discord 语音编解码）、`@matrix-org/matrix-sdk-crypto-nodejs`（Matrix E2E 加密）、`openshell`（`0.1.0`，本地 shell 集成） |
| openclaw | `package.json` | 228 | `pnpm.minimumReleaseAge: 2880`：延迟 2 天采纳新版本，减少供应链攻击窗口 |
| openclaw | `Dockerfile` | 1 | `FROM node:22-bookworm@sha256:cd7bcd2e7...` 基础镜像 SHA256 固定 |
| hermes-agent | `pyproject.toml` | 13-37 | 17 个直接依赖全部 `>=lower,<upper` 双边界定（`openai>=2.21.0,<3`、`anthropic>=0.39.0,<1`、`httpx>=0.28.1,<1`、`pydantic>=2.12.5,<3` 等），`requests>=2.33.0` 标注 CVE-2026-25645 |
| hermes-agent | `pyproject.toml` | 39-115 | 20+ optional extras 全部独立声明版本边界（messaging、voice、web、rl 等），每个 extra 内依赖也使用 `>=lower,<upper` |
| hermes-agent | `pyproject.toml` | 82-89 | Git 依赖精确 pin：`atroposlib` @ `c20c852`、`tinker` @ `30517b6`、`yc-bench` @ `bfb0c88`，仅限 optional extras |
| hermes-agent | `pyproject.toml` | 94-96 | 条件依赖：`matrix` extra 仅 Linux（`python-olm` macOS 不兼容） |
| hermes-agent | `uv.lock` | — | 5512 行，全依赖树 hash 精确锁定 ~200+ 传递依赖 |
| hermes-agent | `Dockerfile` | 1-2 | 2 个基础镜像 SHA256 digest 固定：uv (`b3c543b6c...`)、gosu (`3b176695959c...`) |
| hermes-agent | `Dockerfile` | 38-39 | `uv venv && uv pip install --no-cache-dir -e ".[all]"` 从 lockfile 可重复安装 |

## 关联

- [[openclaw/dimensions/openclaw-dependency-strategy]] — OpenClaw 依赖策略（五维度之依赖维度）
- [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] — Hermes Agent 依赖策略（五维度之依赖维度）
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] — 深度绑定 @mariozechner 私有包族
- [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] — Channel SDK 独立依赖决策
- [[openclaw/nodes/design-decisions/openclaw-startup-over-memory-tradeoff]] — peer dep 设计决策
- [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]] — AST 自动发现（与 extras 模块化哲学一致）
- [[openclaw/nodes/design-decisions/openclaw-compaction-recoverability-priority]] — 波及依赖策略的架构决策

## 修复记录

**2026-06-19 验证修复**：
1. **❌ 版本号修正（与维度原始提取对齐）**：
   - `node-llama-cpp`：`3.15.1` → `3.18.1`（维度文件 `openclaw-dependency-strategy.md` 标注 `3.18.1`）
   - `hono`：`4.11.10` → `4.12.12`（维度文件标注 `4.12.12`）
   - `@sinclair/typebox`：`0.34.48` → `0.34.49`（维度文件标注 `0.34.49`）
2. **❌ 依赖数量修正**：`53 个 deps / 12 精确` → `70 个 deps / 29 精确`（全文 5 处：核心特征、关键机制、跨仓库对比表版本声明策略和精确锁定数量、溯源表），与维度文件一致。
3. **❌ 精确锁定列表对齐**：将精确锁定包列表从概念原有列表调整为与维度文件对齐——补充 `@modelcontextprotocol/sdk`、`matrix-js-sdk`、`hono`，移除 `@sinclair/typebox`（归类到 pnpm overrides）、`@whiskeysockets/baileys`、`@buape/carbon`、`tar`（归类到 pnpm overrides 或不再强调为直接 deps 精确锁）。
4. **❌ 溯源表补充**：`optionalDependencies` 行补充遗漏的 `@matrix-org/matrix-sdk-crypto-nodejs` 和 `openshell`。
5. **⚠️ 术语澄清**：hermes 侧 "17 个核心依赖" → "17 个直接依赖"，并添加注记说明维度文件中将其中 7 个定义为"核心依赖（无替代方案）"，本处为更宽泛口径（所有非可选直接依赖）。
6. **⚠️ 绝对化语言软化**：
   - selection guide "确保所有环境安装结果 bit-identical" → "确保多环境安装的依赖版本完全确定（前提：相同 Python 版本/OS/架构）"
   - 多处 "核心依赖" → "直接依赖"以消除术语歧义
7. **⚠️ 版本号偏差根因**：修复中发现本 Concept 页的版本号普遍比维度提取的版本号更低/更旧（3.15.1 vs 3.18.1、4.11.10 vs 4.12.12、0.34.48 vs 0.34.49），暗示本页可能基于更早的源码快照生成。已全部对齐到维度提取时的源码版本。
