---
concept: optional-dependency-layering
generated: 2026-06-19
phase: 3a-concepts
instances:
  - openclaw
  - hermes-agent
---

# 可选依赖分层：统一降级还是按安装成本分层？

## 标准化问题陈述

当系统需要支持可选功能且对应依赖体积差异巨大时，如何决定可选依赖的分层策略——是统一降级还是按安装成本分层？

## 核心关切

1. **默认安装体积**：默认安装不应拉入 GB 级二进制或复杂原生模块——用户的基础安装体验不应被偶发需求绑架
2. **ImportError 检查点覆盖**：ImportError 检查点需要遍布所有使用可选依赖的代码路径——遗漏一处即导致崩溃
3. **降级行为可见性**：降级行为需要明确告知用户哪些功能因缺失依赖而不可用——沉默降级使用户困惑地寻找不存在的功能
4. **包管理层面的条件表达**：条件依赖需要在包管理层面表达——Python extras 或 npm peer/optional dependencies，而非仅靠文档说明
5. **重型功能的安装路径**：需要重型功能的用户必须清楚知道需要额外安装步骤——安装路径的清晰度决定功能的实际可用性

## 已知权衡位置

### 位置 A：openclaw — Peer + Optional 依赖分层

**优先满足的关切**：关切 1（轻量默认——GB 级 peer dep 不默认拉入，`npm install` 基础安装保持轻量）；关切 5（用户知晓权——文档明确声明哪些能力需要额外 `npm install`）

**接受妥协的关切**：关切 3（可发现性——用户可能不知道需额外安装才能使用本地 LLM 或 Canvas 渲染）；关切 2（检查点覆盖——optional deps 的降级逻辑分散在各 channel extension 中，缺少统一的降级注册机制）

**核心特征**：将重型依赖分为两个隔离层——peer dependencies（用户显式安装）承载 GB 级本地 LLM 推理和 Canvas 渲染；optional dependencies（自动降级）承载原生编解码模块。用户的基础安装不包含前者，后者缺失时功能自动降级但不阻塞启动。

**关键机制（源码可见）**：

1. **Peer + Optional 双分层设计**（`package.json: peerDependencies, optionalDependencies`）：`node-llama-cpp`（精确锁定 `3.18.1`，GB 级本地 LLM 推理）和 `@napi-rs/canvas`（Canvas 渲染）设置为 peerDependencies——npm 不自动安装，用户需显式 `npm install node-llama-cpp` 才能启用本地模型能力。`@discordjs/opus`（Discord 语音编解码）、`@matrix-org/matrix-sdk-crypto-nodejs`（Matrix E2E 加密原生模块）、`openshell`（精确锁定 `0.1.0`，shell 集成）设置为 optionalDependencies——npm 尝试安装但失败不阻塞，运行时检测缺失后降级。

2. **Channel 级故障隔离**（`extensions/*/package.json`）：每个 channel extension 只声明自己需要的 SDK（Slack 的 `@slack/bolt`、Telegram 的 `grammy`、Matrix 的 `matrix-js-sdk` 等），不聚合到 root package。核心运行时不因任何单个 channel SDK 变动受影响，channel 故障域完全隔离——这实际上是另一种形式的分层：按功能域而非按体积。

3. **精确锁定重型依赖**（`package.json: dependencies`）：70 个 runtime deps 中 29 个精确锁定（无 `^`/`~`），锁定规律覆盖所有有 native addon 的包（`sqlite-vec`、`playwright-core`、`@lydell/node-pty`、`matrix-js-sdk`）和协议 SDK（`@modelcontextprotocol/sdk` 锁 `1.29.0`）。peer dep `node-llama-cpp` 也精确锁定到 `3.18.1`——保证用户安装的本地 LLM 引擎版本与预期一致。

**已知代价**：
- 无统一的降级注册机制：每个使用 optional dep 的模块自行做存在性检查，检查逻辑分散在各 channel extension 中
- 用户可发现性依赖文档：peer dep 的功能在运行时不主动告知用户"你需要安装 X 才能使用 Y"——用户需要读文档才知道
- peer dep 仅两层（内建 vs 手动安装）：缺少类似 hermes extras 的按功能分组机制（如 `[voice]`、`[llm-local]`）

**已知实例**：
- [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] — Channel 依赖隔离设计决策
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] — 核心 AI 引擎依赖决策

---

### 位置 B：hermes-agent — ImportError 降级 + 20+ extras 分组

**优先满足的关切**：关切 2（健壮性——不缺包启动失败，所有可选依赖遵循 ImportError → 降级/跳过模式）；关切 4（包管理条件表达——20+ extras 在 `pyproject.toml` 中按功能域分组，pip 原生支持按需安装）

**接受妥协的关切**：关切 2（检查点覆盖——20+ 可选依赖的 ImportError 检查点遍布代码库，遗漏一处即崩溃；维护覆盖完整性是持续负担）；关切 1（最低安装仍需 7 个核心依赖——`openai` SDK、`anthropic` SDK、`httpx`、`prompt_toolkit`、`pydantic`、`rich`、`tenacity`，无法进一步精简）

**核心特征**：将依赖分为三层——7 个无替代方案的核心依赖（安装时不可跳过）、20+ 按功能域分组的 extras（安装时可选，安装后直接可用）、运行时检测降级（缺失时优雅降级而非崩溃）。同时支持平台条件依赖（`matrix` 仅 Linux、`yc-bench` 仅 Python >= 3.12）。

**关键机制（源码可见）**：

1. **20+ extras 按功能域分组**（`pyproject.toml:39-115`）：将单体重安装拆分为按需安装组——`messaging`（5 库，gateway 多平台通信）、`modal`/`daytona`（云容器运行时）、7 个 memory provider 后端、`voice`/`tts-premium`（语音 I/O）、`browser`/`web`（浏览器自动化 + 搜索后端）。用户用 `pip install hermes-agent[messaging,voice]` 精确选择需要的功能组，而非全量安装。

2. **ImportError → 降级/跳过模式遍布代码库**（多文件）：这是 hermes 可选依赖设计的核心保障机制，关键模块入口处使用 try/except ImportError 守卫——`tools/web_tools.py:1925-1947`（多搜索后端回退，逐一检查 API key 可用性，至少一个可用才注册 `web_search` 工具）、`tools/vision_tools.py:325`（`faster-whisper` ImportError → TTS 静默降级，不报错）、`tools/mcp_tool.py:10-11`（`mcp` 包未安装 → debug 日志，不影响其他工具加载）、`environments/__init__.py:25-27`（`atroposlib` ImportError → environments 不可用但子模块可直接导入）。

3. **平台条件依赖**（`pyproject.toml:89,94-96`）：`matrix` extra 仅在 Linux 上可用（`python-olm` 上游不兼容 macOS），`yc-bench` extra 仅 Python >= 3.12。包管理层面即声明平台约束，避免用户在不受支持的平台上尝试安装后遭遇运行时错误。

4. **三层版本锁保护可选依赖稳定性**（`pyproject.toml:15-37` + `uv.lock`）：核心依赖双边界定（`>=lower,<upper`），可选依赖通过 `uv.lock`（5512 行）全依赖树 hash 锁定，确保按需安装的可选依赖版本与核心依赖兼容——避免了"安装可选 extra 后破坏已有功能"的常见陷阱。

5. **多后端可替换性减少锁定风险**（多子系统）：TTS 引擎支持 Edge TTS（免费内置）/ ElevenLabs / OpenAI 三种后端；搜索后端支持 Exa / Firecrawl / Tavily / Parallel-Web 四种后端；终端后端支持 local / docker / ssh / daytona / singularity / modal 六种后端；记忆后端支持 Builtin + 7 种外部 provider。每个子系统的多个后端独立可选，减少对单一可选依赖的锁定。

**已知代价**：
- 检查点覆盖完整性是持续负担：20+ 可选依赖的 ImportError 守卫遍布代码库，新增可选依赖时需确保所有使用点都有检查——遗漏一处即崩溃
- 7 个核心依赖无法进一步精简：最轻量的 CLI 安装仍需要 `openai` SDK + `anthropic` SDK + `httpx` + `prompt_toolkit` + `pydantic` + `rich` + `tenacity`，对仅需基础功能的用户有固定开销
- extras 分组粒度需维护：20+ extras 的分组需要持续对齐功能演进——新增功能可能跨现有分组边界
- `uv.lock` 5512 行的维护成本：全依赖树 hash 锁定保证了可重复构建，但升级任一可选依赖都需要重新生成锁文件并验证全树兼容性

**已知实例**：
- [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] — 依赖策略维度页
- [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]] — AST 自动发现设计决策（与 extras 模块化哲学一致：按需加载、组合灵活）

---

## 跨仓库对比

| 维度 | openclaw（Peer + Optional 分层） | hermes-agent（ImportError 降级 + Extras 分组） |
|------|----------------------------------|----------------------------------------------|
| **分层模型** | 三层：required deps / optionalDeps（自动降级） / peerDeps（手动安装） | 三层：7 个核心 deps / 20+ extras 分组 / 运行时 ImportError 降级 |
| **重型依赖处理** | 设为 peer dep——用户显式安装，不进入默认安装路径 | 放入独立 extras 组——用户通过 `[group]` 按需选择 |
| **轻量安装体积** | 基础 `npm install` 不含 GB 级 `node-llama-cpp` 和 Canvas 原生模块 | 基础 `pip install` 仅需 7 个依赖，但含 `openai` + `anthropic` SDK（非轻量） |
| **降级机制** | optionalDeps 缺失时 npm 静默跳过 + 运行时各模块自行检测降级 | ImportError → 降级/跳过（统一模式），try/except 遍布所有可选依赖使用点 |
| **用户知晓权** | 依赖文档——用户需读文档才知道需额外安装 | 功能缺失时运行时无主动提示（降级是静默的），但 extras 分组名直观（`[voice]`、`[messaging]`） |
| **包管理表达力** | npm peerDependencies + optionalDependencies——仅支持"可选"和"手动"两级 | pip extras——支持按功能域任意分组（`[messaging,voice]`），组合安装灵活 |
| **平台条件依赖** | 未使用——所有 peer/optional deps 跨平台统一声明 | `matrix` 仅 Linux（`python-olm` 无 macOS 支持），`yc-bench` 仅 Python >= 3.12 |
| **检查点覆盖风险** | 中——optional deps 的降级逻辑分散在各 channel extension，无统一入口 | 高——20+ 可选依赖的 ImportError 检查点遍布代码库，遗漏一处即崩溃 |
| **版本兼容保障** | 精确锁定重型 native 包（29/70 deps），防止编译失败 | 范围锁（双边界定）+ `uv.lock` 全树 hash 锁定，防止 extras 组合破坏已有功能 |
| **核心取舍** | 宁可分层简单也不增加包管理复杂度（轻量默认压倒可发现性） | 宁可检查点多也要功能域分组灵活（健壮性和按需安装压倒检查点覆盖的维护成本） |

## 选择指南

| 场景 | 推荐偏向 | 理由 |
|------|---------|------|
| 单个重型依赖（如本地 LLM 推理 GB 级）需要隔离 | openclaw peer dep 模式 | peer dep 精确表达"这是用户的选择，我们不替你装"——npm 不自动拉入，npm 的 `peer dep missing` warning 可提醒用户 |
| 20+ 可选功能需要按场景分组安装 | hermes-agent extras 模式 | pip extras 原生支持组合安装（`[messaging,voice]`），用户按需选择——npm 无等效原生机制 |
| 可选依赖有平台兼容性差异 | hermes-agent 平台条件 extras | `pyproject.toml` 支持 `sys_platform` / `python_version` 标记，包管理层面即声明约束，避免用户在不支持平台安装后崩溃 |
| 依赖体积差异不大（都是纯 JS/Python 库） | 统一 optional deps | 不需要分层——所有可选依赖设为 optional，运行时统一 ImportError 降级 |
| 用户需要极致轻量的基础安装 | openclaw 模式 | peer deps 不进入基础安装路径，`node-llama-cpp` 不在 `node_modules` 中——比 hermes 的 7 个核心 dep 更轻（`openai` SDK 本身有体积） |
| 团队希望降低检查点遗漏风险 | 需要结构化降级注册 | 两种方案都有风险：openclaw 的 optional deps 降级逻辑分散，hermes 的 20+ ImportError 检查点遍布代码库。都需要：集中注册降级行为 + 启动时自检报告全部可用功能（两仓库当前均未达到） |
| 跨平台分发（Linux/macOS/Windows）且可选依赖有原生模块 | hermes-agent 平台条件 extras | 包管理层面声明平台约束，用户在不同平台上 `pip install` 自动获得正确的依赖集——npm 的 optionalDeps 缺少等效的平台条件过滤 |
| JavaScript/TypeScript 项目 | openclaw | npm 的 peerDependencies + optionalDependencies 是 JS 生态标准模式，工具链和用户都熟悉 |
| Python 项目 | hermes-agent | pip extras 是 Python 生态标准模式，`[group]` 语法用户熟悉，pip 原生支持——不需要第三方工具 |

## 溯源表

| 仓库 | 文件 | 行号 | 内容 |
|------|------|------|------|
| openclaw | `package.json` | peerDependencies | `node-llama-cpp`（锁 `3.18.1`）、`@napi-rs/canvas`——用户显式安装，GB 级二进制隔离 |
| openclaw | `package.json` | optionalDependencies | `@discordjs/opus`、`@matrix-org/matrix-sdk-crypto-nodejs`、`openshell`（锁 `0.1.0`）——缺失自动降级 |
| openclaw | `extensions/*/package.json` | — | 各 channel extension 独立声明 SDK 依赖，channel 故障域隔离 |
| openclaw | `package.json` | dependencies | 29/70 deps 精确锁定——native addon 包（`sqlite-vec`、`playwright-core`、`@lydell/node-pty`）+ 协议 SDK（`@modelcontextprotocol/sdk` 锁 `1.29.0`） |
| hermes-agent | `pyproject.toml` | 39-115 | 20+ extras 按功能域分组定义（messaging/modal/daytona/memory/voice/browser/web...）+ `all` 全量安装 |
| hermes-agent | `pyproject.toml` | 89, 94-96 | 平台条件依赖：`matrix` 仅 Linux（`python-olm` 上游无 macOS）、`yc-bench` 仅 Python >= 3.12 |
| hermes-agent | `pyproject.toml` | 15-37 | 7 个核心依赖双边界定（`>=lower,<upper`）——安装时不可跳过 |
| hermes-agent | `tools/web_tools.py` | 1925-1947 | 多搜索后端回退：逐一检查各搜索后端 API key，至少一个可用才注册 `web_search` 工具 |
| hermes-agent | `tools/vision_tools.py` | 325 | `faster-whisper` ImportError → TTS 静默降级，不抛出错误 |
| hermes-agent | `tools/mcp_tool.py` | 10-11 | `mcp` 包未安装 → debug 日志记录，不影响其他工具正常注册 |
| hermes-agent | `environments/__init__.py` | 25-27 | `atroposlib` ImportError → environments 不可用但子模块仍可直接导入 |
| hermes-agent | `uv.lock` | — | 5512 行全依赖树 hash 锁定，确保 extras 组合安装时不引入版本冲突 |

> **注**：源码行号来自维度提取阶段（`openclaw-dependency-strategy.md`、`hermes-agent-dependency-strategy.md`）的标注。源码原始文件未在本仓库中存放，后续可通过直接读取原始仓库源码做二次验证。

## 关联

- [[openclaw/dimensions/openclaw-dependency-strategy]] — 依赖策略维度页（peer + optional 分层 + 精确锁定）
- [[hermes-agent/dimensions/hermes-agent-dependency-strategy]] — 依赖策略维度页（ImportError 降级 + 20+ extras + 三层防护）
- [[openclaw/nodes/design-decisions/openclaw-channel-isolation-decision]] — Channel 依赖隔离设计决策
- [[openclaw/nodes/design-decisions/openclaw-mariozechner-core-dependency]] — 私有包族核心依赖决策
- [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]] — AST 自动发现决策（与 extras 按需加载哲学一致）
- [[依赖管理策略]] — 父级 concept（class: Dependency Strategy）

## 修复记录（2026-06-19 验证后修正）

| 判定 | 位置 | 修正内容 |
|------|------|---------|
| ⚠️ | hermes ImportError 机制描述 | "每个使用可选依赖的模块入口处都有" → "关键模块入口处使用"——调低绝对化程度，wiki 仅列出 4 处示例，无法确认全覆盖 |
| ⚠️ | hermes 版本锁描述 | "所有核心依赖都双边界定" → "核心依赖双边界定"——去掉 "所有...都" 绝对化措辞（wiki 确认此事实，但措辞风格统一为约束性描述） |
| ⚠️ | hermes 已知实例 | 新增 [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]]——与 extras 按需加载、模块化哲学一致，补充原本只有 1 个实例链接的不足 |
| ❌ | 跨概念页：`node-llama-cpp` 版本号 | 本页 `3.18.1` 与 `openclaw-dependency-strategy.md` 维度页一致（line 61: "精确锁 3.18.1"）。兄弟概念页 `dependency-version-locking.md` 错误的记录了 `3.15.1`——该页需修正 |
| ❌ | 跨概念页：openclaw 精确锁定数量 | 本页 29/70 与 `openclaw-dependency-strategy.md` 维度页一致（line 73: "70 个 runtime deps 中 29 个精确锁定"）。兄弟概念页 `dependency-version-locking.md` 错误的记录了 12/53——该页需修正 |
| ❌ | 跨概念页：openclaw optionalDependencies 列表 | 本页列出了 `@discordjs/opus`、`@matrix-org/matrix-sdk-crypto-nodejs`、`openshell`（锁 `0.1.0`）三个 optional deps。兄弟概念页 `dependency-version-locking.md` 仅列出 `@discordjs/opus`——遗漏后两者，需补充 |
| ⚠️ | 对比表 "用户知晓权" hermes 侧 | "功能缺失时运行时无主动提示（降级是静默的）"——描述准确（ImportError 模式确为静默降级），但 wiki 维度页未直接确认运行时提示行为 |

**验证汇总**：本页所有内部声明均可从 wiki 维度文件验证（openclaw 10/10 ✅，hermes 11/11 ✅）。⚠️ 项为绝对化措辞调优。❌ 项均为跨概念页一致性冲突——本页的值与 wiki 原始提取一致，冲突方为 `dependency-version-locking.md`（该页 node-llama-cpp 版本号、deps 数量、optionalDependencies 列表均需修正）。
