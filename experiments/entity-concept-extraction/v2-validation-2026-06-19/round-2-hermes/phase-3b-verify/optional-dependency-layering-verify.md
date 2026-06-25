# 验证报告：optional-dependency-layering

## 格式完整性 (checklist)

- [x] 标准化问题陈述
- [x] 核心关切 (5 项)
- [x] 已知权衡位置 (A: openclaw, B: hermes-agent)
- [x] 每个位置: 优先满足的关切 / 接受妥协的关切 / 核心特征 / 关键机制 / 已知代价
- [x] 跨仓库对比表 (10 维度)
- [x] 选择指南 (9 场景)
- [x] 溯源表 (12 行)
- [x] 关联链接
- [ ] 关切-实现对应: 关切 5 ("安装路径清晰度") 在对比表中没有独立行——已合并入"用户知晓权"维度，可接受
- [x] 每个仓库在每个复杂度维度都有描述
- [x] 权衡位置分类: A="Peer + Optional 依赖分层", B="ImportError 降级 + 20+ extras 分组" — 正确映射

## 逐仓库验证

### OpenClaw (位置 A)

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| 1 | `node-llama-cpp` 精确锁 `3.18.1`，设为 peerDependencies | ✅ | `openclaw-dependency-strategy.md` line 61: "node-llama-cpp（精确锁 3.18.1）...设为 peer 避免默认拉入" |
| 2 | `@napi-rs/canvas` 设为 peerDependencies | ✅ | `openclaw-dependency-strategy.md` line 60: "@napi-rs/canvas：Canvas 渲染能力" (peer deps) |
| 3 | `@discordjs/opus` 设为 optionalDependencies | ✅ | `openclaw-dependency-strategy.md` line 65: "@discordjs/opus：Discord 语音编解码" (optional deps) |
| 4 | `@matrix-org/matrix-sdk-crypto-nodejs` 设为 optionalDependencies | ✅ | `openclaw-dependency-strategy.md` line 66: Matrix E2E 加密原生模块 (optional deps) |
| 5 | `openshell` 精确锁 `0.1.0`，设为 optionalDependencies | ✅ | `openclaw-dependency-strategy.md` line 67: "openshell（精确锁 0.1.0）：shell 集成" (optional deps) |
| 6 | `@modelcontextprotocol/sdk` 锁 `1.29.0` | ✅ | `openclaw-dependency-strategy.md` line 76: "@modelcontextprotocol/sdk（1.29.0）" |
| 7 | 70 个 runtime deps 中 29 个精确锁定 | ✅ | `openclaw-dependency-strategy.md` line 73: "70 个 runtime deps 中 29 个精确锁定（无 ^/~），41 个用范围版本" |
| 8 | `@mariozechner/*` 四件套精确锁定同一版本 | ✅ | `openclaw-dependency-strategy.md` line 27: "四个包精确锁定到同一版本 0.66.1" |
| 9 | Channel extension 各自独立声明 SDK，不聚合到 root | ✅ | `openclaw-dependency-strategy.md` lines 31-40: Channel SDK 各自独立 + `openclaw-channel-isolation-decision.md`: "不在 root package 聚合" |
| 10 | 无统一的降级注册机制 | ✅ | `openclaw-dependency-strategy.md`: 未描述统一降级注册机制——确认不存在（evaluate absence） |

### Hermes-Agent (位置 B)

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| 11 | 20+ extras 按功能域分组 (messaging/modal/daytona/memory/voice/browser/web...) | ✅ | `hermes-agent-dependency-strategy.md` lines 25-31: 列出 messaging(5库)/modal/daytona/memory(7后端)/voice/tts-premium/browser/web 等 |
| 12 | 7 个核心依赖: openai, anthropic, httpx, prompt_toolkit, pydantic, rich, tenacity | ✅ | `hermes-agent-dependency-strategy.md` lines 17-23: 7 个核心依赖列表完全一致 |
| 13 | 核心依赖双边界定 (`>=lower,<upper`) | ✅ | `hermes-agent-dependency-strategy.md` line 38: ">=lower,<upper 所有核心依赖都双边界定" |
| 14 | `matrix` extra 仅 Linux (python-olm 上游不兼容 macOS) | ✅ | `hermes-agent-dependency-strategy.md` line 60: "matrix extra 仅在 Linux 上可用（python-olm 上游 macOS 不兼容）" |
| 15 | `yc-bench` 仅 Python >= 3.12 | ✅ | `hermes-agent-dependency-strategy.md` line 60: "yc-bench 仅 Python >= 3.12" |
| 16 | `tools/web_tools.py:1925-1947` 多搜索后端回退 | ✅ | `hermes-agent-dependency-strategy.md` line 81: "搜索后端...各自的 API key 存在即启用 ^[tools/web_tools.py:1925-1926]" |
| 17 | `tools/vision_tools.py:325` faster-whisper ImportError → TTS 静默降级 | ✅ | `hermes-agent-dependency-strategy.md` line 91: "faster-whisper ImportError → TTS fallback 仅忽略，不报错 ^[tools/vision_tools.py:325]" |
| 18 | `tools/mcp_tool.py:10-11` mcp 包未安装 → debug 日志 | ✅ | `hermes-agent-dependency-strategy.md` line 92: "mcp 包未安装 → debug 日志，不影响其他工具 ^[tools/mcp_tool.py:10-11]" |
| 19 | `environments/__init__.py:25-27` atroposlib ImportError → 子模块仍可导入 | ✅ | `hermes-agent-dependency-strategy.md` line 93: "atroposlib ImportError → environments 不可用但子模块可直接导入 ^[environments/__init__.py:25-27]" |
| 20 | `uv.lock` 5512 行全依赖树 hash 锁定 | ✅ | `hermes-agent-dependency-strategy.md` line 39: "uv.lock (5512 行) — 全依赖树 hash 锁定" |
| 21 | 多后端可替换性: TTS 3后端/搜索4后端/终端6后端/记忆7后端 | ✅ | `hermes-agent-dependency-strategy.md` lines 78-84: TTS(Edge/ElevenLabs/OpenAI), 搜索(Exa/Firecrawl/Tavily/Parallel-Web), 终端(local/docker/ssh/daytona/singularity/modal), 记忆(Builtin+7种) |

### 跨概念页一致性检查

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| C1 | `openshell` 版本: 本页说 `0.1.0`, dependency-version-locking.md 溯源表未列出 openshell | ⚠️ | dependency-version-locking.md 溯源表 line 127 说 `optionalDependencies` 仅有 `@discordjs/opus ^0.10.0`——遗漏了 `@matrix-org/matrix-sdk-crypto-nodejs` 和 `openshell`。修正建议：dependency-version-locking.md 溯源表补充 `@matrix-org/matrix-sdk-crypto-nodejs` 和 `openshell` (锁 `0.1.0`) |
| C2 | `node-llama-cpp` 版本: 本页说 `3.18.1`, dependency-version-locking.md line 42 说 `3.15.1` | ❌ | **版本号冲突**。`openclaw-dependency-strategy.md` line 61 原始标注为 `3.18.1`。dependency-version-locking.md 的 `3.15.1` 是错误的。修正建议：dependency-version-locking.md line 42 将 `3.15.1` 改为 `3.18.1`，line 126 溯源表同样修正 |
| C3 | openclaw runtime deps 数量: 本页说 70 个 (29 精确), dependency-version-locking.md 说 53 个 (12 精确) | ❌ | **数量冲突**。`openclaw-dependency-strategy.md` line 73 原始标注为 "70 个 runtime deps 中 29 个精确锁定"。dependency-version-locking.md line 38 的 "53 个 dependencies...12 个精确锁定" 与原始提取不一致。修正建议：dependency-version-locking.md 将 53→70, 12→29，或说明计数差异原因（是否排除了 devDependencies 等） |
| C4 | 对比表"用户知晓权": 本页说 hermes "功能缺失时运行时无主动提示（降级是静默的）" | ⚠️ | `hermes-agent-dependency-strategy.md` 未确认运行时是否有主动提示机制。从 ImportError 模式看降级确实是静默的（debug log 而非 user-facing message）。描述准确但无法从维度文件直接验证。保持为 ⚠️（可信但无直接证据） |

## 关切验证

### 关切-对比表对应检查

| 关切 | 对比表对应维度 | 是否覆盖 |
|------|--------------|---------|
| 1. 默认安装体积 | "轻量安装体积" | ✅ |
| 2. ImportError 检查点覆盖 | "降级机制" + "检查点覆盖风险" | ✅ |
| 3. 降级行为可见性 | "用户知晓权" | ✅ |
| 4. 包管理层面的条件表达 | "包管理表达力" | ✅ |
| 5. 重型功能的安装路径 | "重型依赖处理" | ✅ |

所有 5 项关切在对比表中均有对应维度。

### 权衡位置分类验证

- **位置 A (openclaw)**: "Peer + Optional 依赖分层" — 正确。两个 peer deps + 三个 optional deps 构成两级分层。
- **位置 B (hermes-agent)**: "ImportError 降级 + 20+ extras 分组" — 正确。核心特征描述准确。

## 绝对化语言标记

| 位置 (行) | 语言 | 风险 |
|-----------|------|------|
| line 80, 89: "每个 channel extension" | 强调全量 | 低风险——事实上每个 channel 确实有独立 package.json |
| line 63-64: "所有使用可选依赖的模块入口处都有 try/except ImportError 守卫" | "所有...都" | 中风险——维度文件仅列出 4 处示例，无法确认 "所有"。修正建议：改为 "关键模块入口处使用 try/except ImportError 守卫" |
| line 72: "所有核心依赖都双边界定" | "所有...都" | 低风险——从维度文件描述看确实如此 |
| line 47-48: "npm 不自动安装" (peer deps) | 绝对化描述 | 低风险——这是 npm 行为事实，非项目选择 |
| line 69: "每个 extra 内部的所有依赖也使用 >=lower,<upper 边界" | "每个...所有" | 中风险——维度文件未逐一验证 20+ extras 的每个依赖。修正建议：改为 "每个 extra 内部的依赖也使用版本边界约束" |

## 追加完整性

### 两个仓库在各节描述完整性

| 章节 | openclaw 覆盖 | hermes-agent 覆盖 | 完整? |
|------|-------------|-----------------|------|
| 优先满足的关切 | 关切 1, 5 | 关切 2, 4 | ✅ |
| 接受妥协的关切 | 关切 3, 2 | 关切 2 (持续负担), 1 | ✅ |
| 核心特征 | ✓ | ✓ | ✅ |
| 关键机制 | 2 项 (package.json 分层 + channel 隔离 + 精确锁定) | 5 项 (extras + ImportError + 平台条件 + 版本锁 + 多后端) | ✅ |
| 已知代价 | 3 项 | 4 项 | ✅ |
| 已知实例 | 2 个节点 | 1 个节点 | ⚠️ hermes 仅 1 个实例链接，openclaw 有 2 个——hermes 可补充 [[hermes-agent/nodes/design-decisions/hermes-agent-ast-autodiscovery-decision]]（与 extras 模块化哲学一致） |

## 汇总

| 类别 | 总计 | ✅ | ⚠️ | ❌ |
|------|------|-----|------|-----|
| OpenClaw 声明 | 10 | 10 | 0 | 0 |
| Hermes 声明 | 11 | 11 | 0 | 0 |
| 跨概念页一致性 | 4 | 0 | 2 | 2 |
| 绝对化语言 | 5 | 3 (低风险) | 2 (中风险) | 0 |
| **总计** | **30** | **24** | **4** | **2** |

### 关键发现

1. **本 Concept 页内部自洽**，所有声明均可从维度提取文件验证。
2. **与兄弟 Concept 页 (dependency-version-locking.md) 存在 2 处事实冲突**: `node-llama-cpp` 版本号 (3.18.1 vs 3.15.1) 和 openclaw 精确锁定数量 (29 vs 12)。以本页为准（与维度原始提取一致）。
3. **2 处绝对化语言** ("所有...都" / "每个...所有") 缺乏全量验证支持，建议弱化措辞。
4. **hermes-agent 已知实例仅 1 个**，建议补充 ast-autodiscovery 节点链接。
