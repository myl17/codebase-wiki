# Graph Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 codebase-wiki 的 openclaw / hermes-agent 两个仓库补全图谱层——包括 schema 定义、概念索引、节点页、graph.py 脚本、lint 规则扩展、/analyze 节点抽取协议，以及 /query 的图遍历分支。

**Architecture:** 节点以 `wiki/repos/<name>/nodes/<slug>.md` 形式存储，frontmatter 即边表（`node_type / scope / concept / targets / motivated_by`），`scripts/graph.py` 从 frontmatter 派生出图遍历能力与 Mermaid 局部子图；`wiki/entities/_index.md` 是跨仓库 Concept 归一化的唯一锚点；叙事层（dimension 页）不承担图谱功能，保持现状。

**Tech Stack:** Python 3.10+，PyYAML（frontmatter 解析），现有 scripts/ 测试模式（stdlib tempfile + sys.path.insert），Obsidian Mermaid 原生渲染

---

## Step 0（手工，非编码）：价值预验证

> **在写任何代码之前，先验证图谱层的核心价值假设。**

- [ ] 手工创建 `wiki/repos/openclaw/nodes/tool-policy.md`：

```yaml
---
node_type: Component
scope: subsystem
concept: 权限管控
motivated_by: [sync-gating-decision]
sources:
  - src/agents/tool-policy-pipeline.ts:56-90
---

# ToolPolicy

5 层同步 pipeline（profile → provider → global → agent → group policy），对每个工具调用做 allowlist/denylist 叠加。改动此处必须保持同步门控语义（不能改为异步审计）。
^[src/agents/tool-policy-pipeline.ts:56-90]
```

- [ ] 手工创建 `wiki/repos/openclaw/nodes/exec-approval-request.md`：

```yaml
---
node_type: ExtensionPoint
scope: subsystem
concept: 人机审批协议
targets: [tool-policy]
motivated_by: [sync-gating-decision]
sources:
  - src/agents/bash-tools.exec-approval-request.ts:89-126
---

# ExecApprovalRequest

exec 类工具的异步审批扩展点。注册请求后阻塞等待 owner 决策，支持 host/gateway 双路径。二开时在此处注入自定义审批逻辑。
^[src/agents/bash-tools.exec-approval-request.ts:89-126]
```

- [ ] 手工创建 `wiki/repos/openclaw/nodes/sync-gating-decision.md`：

```yaml
---
node_type: DesignDecision
scope: system
sources:
  - src/agents/tool-policy-pipeline.ts:56-90
  - src/agents/bash-tools.exec-approval-request.ts:89-126
---

# 5 层同步门控

选择同步串行 pipeline 而非异步审计，代价是工具调用延迟增加，换取安全边界可被代码静态验证。所有 exec 类工具必须经过此链路。
^[src/agents/tool-policy-pipeline.ts:56-90]
```

- [ ] 手工创建 `wiki/repos/openclaw/nodes/channel-plugin.md`：

```yaml
---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [context-engine]
sources:
  - src/channels/plugins/types.plugin.ts:53-94
---

# ChannelPlugin

`ChannelPlugin<ResolvedAccount>` 接口，统一 13+ Adapter（Messaging/Outbound/Lifecycle/Auth/Setup）。每个 IM 平台实现全套 Adapter，扩展包独立 npm 包，按需懒加载。
^[src/channels/plugins/types.plugin.ts:53-94]
```

- [ ] 直接向 Claude 提问（不运行任何脚本）："改 ToolPolicy 会波及什么？" —— **只给 dimension 页**（openclaw-architecture.md + openclaw-extension-points.md）
- [ ] 再次提问 —— **同时给 dimension 页 + 上面四个节点页**
- [ ] 对比两次回答：节点页是否明显减少了「哪些地方会波及」的搜索范围？provenance 是否更精准？
- [ ] **决策点**：若节点页无明显增益，在此停止，重新评估图谱方向再继续后续 Task。

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `schema/graph-schema.md` | 新建 | 节点类型、边类型、scope 词表、准入三问、节点页模板 |
| `wiki/entities/_index.md` | 新建 | Concept 归一化索引，从分诊后的 entity 页初始化 |
| `wiki/repos/openclaw/nodes/*.md` | 新建（≥6 个） | openclaw 节点页回填 |
| `wiki/repos/hermes-agent/nodes/*.md` | 新建（≥4 个） | hermes-agent 节点页回填 |
| `scripts/graph.py` | 新建 | `build` / `query` / `mermaid` 三子命令 |
| `scripts/lint.py` | 修改 | 新增 3 条图结构规则 |
| `tests/test_graph.py` | 新建 | graph.py 单元测试 |
| `tests/test_lint.py` | 修改 | 新增图规则测试 |
| `skills/code-ingest/SKILL.md` | 修改 | 新增节点抽取子步骤（Step 3.5） |
| `skills/code-query/SKILL.md` | 修改 | 新增图遍历分支 |

---

## Task 1：schema/graph-schema.md

**Files:**
- Create: `schema/graph-schema.md`

- [ ] **Step 1: 创建 schema/graph-schema.md**

```markdown
# Graph Schema

**Version:** v0.1
**Evolution policy:** First 20 repos — add only, never remove or rename. New edge types require a real query use case.

---

## Node Types

每个节点页（`wiki/repos/<name>/nodes/<slug>.md`）的 `node_type` 必须是以下三种之一：

| type | 含义 | 对应受众问题 |
|------|------|-------------|
| `Component` | 系统中可定位的结构单元（子系统/核心抽象/数据结构） | 改这里会波及什么? |
| `ExtensionPoint` | 二开可操作的定制入口（接口/注册机制/钩子/配置项） | 这里怎么扩展? |
| `DesignDecision` | 存在明确因果链的架构选择，影响后续设计 | 为什么这样设计? |

**不入图的类型**（保持叙事文本即可）：
- 函数名、类名、文件路径（L1 实现细节）
- 教科书模式（单例、懒加载、退避——任何仓库都有，汇合无信息量）
- 工具/库名（Vitest、pytest——package.json 可见事实）

---

## Scope

`scope` 字段描述影响范围，用于 compare 排序和影响分析输出优先级。不参与连边合法性。

| scope | 含义 | 示例 |
|-------|------|------|
| `system` | 影响整个系统的架构决策或核心子系统 | 5层同步门控、Agent 生命周期 |
| `subsystem` | 影响一个独立子系统或扩展点集合 | ChannelPlugin、ToolPolicy |
| `component` | 影响单一组件或数据结构 | ManagedRun 状态机、ExecApprovalRequest |

---

## Edge Types（起步集）

边存储在源节点页的 frontmatter 字段中。`graph.py build` 读取后构建图。

| 边 | frontmatter 字段 | 方向 | 合法源类型 | 合法目标类型 |
|----|-----------------|------|-----------|------------|
| `embodies` | `concept:` | 实例 → Concept | Component, ExtensionPoint | wiki/entities/_index.md 中的 Concept |
| `targets` | `targets:` (list of slugs) | ExtensionPoint → Component | ExtensionPoint | Component |
| `motivates` | `motivated_by:` (list of slugs) | DesignDecision → 节点 | Component, ExtensionPoint | DesignDecision |

**reserved（未来）**：`constrains`（待影响发现查询验证后引入）；`alternative_to`（待有完整 ADR 仓库后引入）。

---

## Concept 准入三问

候选概念须**同时通过**三问才能入 `wiki/entities/_index.md`：

1. **问题测试**：它直接回答某个二开/架构师问题吗？（"怎么扩展？""为什么这样设计？""选型差异在哪？"）
2. **判别测试**：在此锚点上跨仓库汇合，能得出**有差异的结论**吗？还是任何仓库都"有"？
3. **沉淀测试**：其知识需读代码才能获得吗？还是 package.json/README 一眼可见？

ingest 时 LLM 只能在节点页标 `concept_candidate: <名>`，正式入索引须过三问。

---

## 节点页模板

```yaml
---
node_type: ExtensionPoint          # Component | ExtensionPoint | DesignDecision
scope: subsystem                   # system | subsystem | component
concept: 插件系统                   # 省略则该节点无跨仓库对应（仓库特有）
concept_candidate: ""              # 候选 Concept 名（待过三问后正式入索引）
targets:                           # list of node slugs in same repo
  - tool-policy
motivated_by:                      # list of DesignDecision slugs in same repo
  - sync-gating-decision
sources:
  - src/channels/plugins/types.plugin.ts:53-94
---

# <节点名>

一段人话描述：这是什么、怎么用、二开时从哪里切入。
^[src/channels/plugins/types.plugin.ts:53-94]
```

**字段说明**：
- `targets` / `motivated_by` 填同 repo `nodes/` 目录下的文件名（不含 `.md`）
- `concept` 填 `wiki/entities/_index.md` 中已有的 Concept 名，未注册不得填
- `sources` 格式：`<repo 内相对路径>:<起始行>-<结束行>`
```

- [ ] **Step 2: 提交**

```bash
git add schema/graph-schema.md
git commit -m "feat(schema): add graph-schema with node types, edges, concept admission criteria"
```

---

## Task 2：entity 分诊 + 初始化概念索引

**Files:**
- Create: `wiki/entities/_index.md`
- Delete: `wiki/entities/单例模式.md`, `wiki/entities/懒加载.md`, `wiki/entities/指数退避.md`, `wiki/entities/Vitest.md`, `wiki/entities/TypeScript monorepo.md`
- Modify: `wiki/entities/OpenTelemetry.md`（重命名概念）
- Keep: 插件系统、Context 压缩、Prompt Caching、并行工具执行、契约测试、性能预算、行为驱动测试
- Watchlist（不入索引）: 分层架构、优雅降级、故障隔离、并行 CI

- [ ] **Step 1: 删除降级出局的 5 个 entity 页**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
git rm wiki/entities/单例模式.md wiki/entities/懒加载.md wiki/entities/指数退避.md wiki/entities/Vitest.md wiki/entities/"TypeScript monorepo.md"
```

- [ ] **Step 2: 将 OClaw / Hermes 维度页中对应的 wikilink 改为纯文本**

修改 `wiki/repos/openclaw/dimensions/openclaw-architecture.md`：
- `[[单例模式]]` → `单例模式`
- `[[TypeScript monorepo]]` → `TypeScript monorepo`

修改 `wiki/repos/openclaw/dimensions/openclaw-performance-tradeoffs.md`：
- `[[指数退避]]` → `指数退避`
- `[[懒加载]]` → `懒加载`（此处已在 extension-points 页，两处均改）

修改 `wiki/repos/openclaw/dimensions/openclaw-extension-points.md`：
- `[[懒加载]]` → `懒加载`

修改 `wiki/repos/openclaw/dimensions/openclaw-testing-philosophy.md`：
- `[[Vitest]]` → `Vitest`（如有）

- [ ] **Step 3: 重新概念化 OpenTelemetry → 可观测性集成**

覆写 `wiki/entities/OpenTelemetry.md`（保留文件，更名概念）：

```markdown
---
type: entity
category: 架构模式
---

# 可观测性集成

将 Traces、Metrics、Logs 三路信号统一采集和导出，接入外部监控 backend。核心权衡：集成粒度越细，运行时开销越高；敏感内容须在导出前脱敏。

## 在各 repo 中的体现

- [[openclaw/dimensions/openclaw-architecture]] — `extensions/diagnostics-otel/` 实现完整 OpenTelemetry 集成：OTLPTraceExporter + OTLPMetricExporter + OTLPLogExporter 三路并行；TraceIdRatioBasedSampler 配置采样率；上报前经 redactSensitiveText 处理
```

- [ ] **Step 4: 将分层架构/优雅降级/故障隔离/并行 CI 标记为观察名单**

在这 4 个 entity 页 frontmatter 加一行 `watchlist: true`（lint 忽略它们缺少跨仓库实例的警告）：

```bash
for f in "wiki/entities/分层架构.md" "wiki/entities/优雅降级.md" "wiki/entities/故障隔离.md" "wiki/entities/并行 CI.md"; do
  sed -i '' 's/^---$/---\nwatchlist: true/' "$f" 2>/dev/null || \
  python3 -c "
import re, pathlib
p = pathlib.Path('$f')
t = p.read_text()
p.write_text(t.replace('---\n', '---\nwatchlist: true\n', 1))
"
done
```

验证：`head -5 wiki/entities/分层架构.md`  应见 `watchlist: true`

- [ ] **Step 5: 创建 wiki/entities/_index.md**

```markdown
# Concept Index

归一化锚点。每个 Concept 入表须通过准入三问（见 schema/graph-schema.md）。
ingest 时 LLM 只标 `concept_candidate`，人工确认后才在此登记。

| Concept | 别名/曾用名 | 一句话定义 | 实例数 |
|---------|------------|-----------|--------|
| 插件系统 | Plugin System, 扩展注册机制 | 通过注册 API 或 manifest 将核心与扩展解耦，核心不感知具体实现 | 2 |
| Context 压缩 | Context Compression, compact | 上下文超限时用辅助 LLM 有损压缩历史 turns，换取继续对话的容量 | 2 |
| Prompt Caching | Prompt Cache, 前缀缓存 | 将 LLM 请求的稳定前缀在 provider 侧缓存，命中时跳过 token 计算 | 2 |
| 并行工具执行 | Parallel Tool Execution | LLM agent 在单轮 tool-calling 中同时执行多个无依赖工具以降低延迟 | 2 |
| 契约测试 | Contract Testing | 通过共享 test suite 验证接口实现方符合约定协议，新实现自动被覆盖 | 1 |
| 性能预算 | Performance Budget | 将性能指标纳入 CI，超出基线即 fail，防止退化静默积累 | 1 |
| 行为驱动测试 | Behavior-Driven Testing | 测试公共 API 和可观察行为而非内部实现，使测试在重构时保持稳定 | 2 |
| 可观测性集成 | OpenTelemetry, Observability | 三路信号（Traces/Metrics/Logs）统一采集导出，接入外部监控 backend | 1 |
```

- [ ] **Step 6: 提交**

```bash
git add wiki/entities/ 
git commit -m "refactor(entities): triage 17 entities — demote 5, reframe 1, init concept index"
```

---

## Task 3：openclaw 节点页回填

**Files:**
- Create: `wiki/repos/openclaw/nodes/sync-gating-decision.md`
- Create: `wiki/repos/openclaw/nodes/tool-policy.md`
- Create: `wiki/repos/openclaw/nodes/exec-approval-request.md`
- Create: `wiki/repos/openclaw/nodes/channel-plugin.md`
- Create: `wiki/repos/openclaw/nodes/context-engine.md`
- Create: `wiki/repos/openclaw/nodes/agent-harness.md`

（Step 0 中手工创建的 4 个如已存在，直接跳到 Step 5 补充剩余 2 个。）

- [ ] **Step 1: 创建 sync-gating-decision.md**

```markdown
---
node_type: DesignDecision
scope: system
sources:
  - src/agents/tool-policy-pipeline.ts:56-90
  - src/agents/bash-tools.exec-approval-request.ts:89-126
---

# 5层同步门控

选择同步串行 pipeline 而非异步审计：所有工具调用在执行前必须经过 5 层过滤（profile → provider → global → agent → group），exec 类工具额外阻塞等待 owner 审批。代价是工具调用延迟增加；换取安全边界可被代码静态验证，不依赖运行时日志。
^[src/agents/tool-policy-pipeline.ts:56-90]
```

- [ ] **Step 2: 创建 tool-policy.md**

```markdown
---
node_type: Component
scope: subsystem
motivated_by: [sync-gating-decision]
sources:
  - src/agents/tool-policy-pipeline.ts:56-90
  - src/agents/tool-policy.ts:19-55
---

# ToolPolicy

5 层 allowlist/denylist 叠加 pipeline。`OwnerOnlyToolApprovalClass` 将工具分为 `control_plane` / `exec_capable` / `interactive` 三类，`applyOwnerOnlyToolPolicy` 按 sender 是否为 owner 动态过滤工具集。修改此组件须保持门控的同步语义（不能改为异步审计）。
^[src/agents/tool-policy-pipeline.ts:56-90]
^[src/agents/tool-policy.ts:19-55]
```

- [ ] **Step 3: 创建 exec-approval-request.md**

```markdown
---
node_type: ExtensionPoint
scope: component
concept: 人机审批协议
targets: [tool-policy]
motivated_by: [sync-gating-decision]
sources:
  - src/agents/bash-tools.exec-approval-request.ts:89-126
---

# ExecApprovalRequest

exec 类工具的异步阻塞审批扩展点。注册 `ExecApprovalRequest` 后等待 `waitForExecApprovalDecision`，支持 host/gateway 双路径。二开时在此注入自定义审批逻辑（UI 弹窗、Slack 通知等），不需改动 ToolPolicy pipeline。
^[src/agents/bash-tools.exec-approval-request.ts:89-126]
```

- [ ] **Step 4: 创建 channel-plugin.md**

```markdown
---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
targets: [context-engine]
sources:
  - src/channels/plugins/types.plugin.ts:53-94
---

# ChannelPlugin

`ChannelPlugin<ResolvedAccount>` 接口，统一 13+ Adapter（Messaging / Outbound / Lifecycle / Auth / Setup）。每个 IM 平台在 `extensions/` 下实现独立 npm 包，通过 `definePluginEntry` / `defineBundledChannelEntry` 注册，按需懒加载。二开时添加新平台只需实现接口并注册，不改动 core。
^[src/channels/plugins/types.plugin.ts:53-94]
```

- [ ] **Step 5: 创建 context-engine.md**

```markdown
---
node_type: Component
scope: subsystem
concept: Context 压缩
sources:
  - src/context-engine/index.ts:1-27
---

# ContextEngine

管理 prompt 生命周期的四个操作：`assemble`（组装）/ `ingest`（摄入）/ `compact`（压缩）/ `transcriptRewrite`（重写）。支持可注册的 `ContextEngineFactory`，通过 `LegacyContextEngine` 保持向后兼容。全局唯一实例（单进程内不应存在多个 ContextEngine）。
^[src/context-engine/index.ts:1-27]
```

- [ ] **Step 6: 创建 agent-harness.md**

```markdown
---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
sources:
  - src/agents/harness/types.ts:30-44
---

# AgentHarness

`AgentHarness` 接口：`supports(ctx)` 做优先级选择，`runAttempt(params)` 执行 LLM 调用，`compact?(params)` 压缩上下文，`reset?(params)` 重置 session。`selectAgentHarness()` 按 priority 排序选择实现。`extensions/` 下各 provider（anthropic/openai/ollama/deepseek）各自注册，对 core 透明。
^[src/agents/harness/types.ts:30-44]
```

- [ ] **Step 7: 提交**

```bash
git add wiki/repos/openclaw/nodes/
git commit -m "feat(wiki): add openclaw node pages (6 nodes, 3 edge types)"
```

---

## Task 4：hermes-agent 节点页回填

**Files:**
- Create: `wiki/repos/hermes-agent/nodes/tool-registry.md`
- Create: `wiki/repos/hermes-agent/nodes/toolset-system.md`
- Create: `wiki/repos/hermes-agent/nodes/memory-provider.md`
- Create: `wiki/repos/hermes-agent/nodes/ast-autodiscovery-decision.md`

- [ ] **Step 1: 创建 ast-autodiscovery-decision.md**

```markdown
---
node_type: DesignDecision
scope: system
sources:
  - hermes_agent/tools/registry.py:1-40
---

# AST 自动发现策略

选择在进程启动时通过 AST 扫描自动发现所有 `registry.register()` 调用，而非手动维护工具列表。优势：新增工具只需注册调用，无需修改其他文件；代价：启动时有 AST 解析开销，且工具必须在顶层显式注册（不支持动态注册）。
^[hermes_agent/tools/registry.py:1-40]
```

- [ ] **Step 2: 创建 tool-registry.md**

```markdown
---
node_type: Component
scope: subsystem
concept: 插件系统
motivated_by: [ast-autodiscovery-decision]
sources:
  - hermes_agent/tools/registry.py:1-40
---

# ToolRegistry

单例工具注册中心（RLock 线程安全），通过 AST 扫描自动发现 `registry.register()` 调用。支持跨模块工具发现，toolset 可组合。
^[hermes_agent/tools/registry.py:1-40]
```

- [ ] **Step 3: 创建 toolset-system.md**

```markdown
---
node_type: ExtensionPoint
scope: subsystem
targets: [tool-registry]
sources:
  - hermes_agent/tools/toolsets.py:1-30
---

# Toolset System

将工具按功能分组为 Toolset，可按需启用/禁用整组工具。二开时通过定义新 Toolset 并注册来扩展工具集，独立于 core 工具定义。
^[hermes_agent/tools/toolsets.py:1-30]
```

- [ ] **Step 4: 创建 memory-provider.md**

```markdown
---
node_type: ExtensionPoint
scope: subsystem
concept: 插件系统
sources:
  - hermes_agent/memory/base.py:1-30
---

# MemoryProvider

可替换的记忆后端扩展点。支持多种实现（内置 SQLite、LanceDB、外部引擎），通过统一接口注入 ContextEngine。二开时实现接口并替换注入点，不改动上层逻辑。
^[hermes_agent/memory/base.py:1-30]
```

- [ ] **Step 5: 提交**

```bash
git add wiki/repos/hermes-agent/nodes/
git commit -m "feat(wiki): add hermes-agent node pages (4 nodes)"
```

---

## Task 5：scripts/graph.py —— build 子命令

**Files:**
- Create: `scripts/graph.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: 写失败测试（build 子命令）**

创建 `tests/test_graph.py`：

```python
#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from graph import build_graph


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_node(tmp: Path, repo: str, slug: str, frontmatter: str, body: str = "# Node"):
    write(
        tmp / f"wiki/repos/{repo}/nodes/{slug}.md",
        f"---\n{frontmatter}\n---\n\n{body}\n"
    )


def test_build_graph_returns_nodes_and_edges(tmp_path):
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\n"
              "concept: 插件系统\ntargets:\n  - tool-policy")

    g = build_graph(tmp_path / "wiki")

    assert len(g["nodes"]) == 2
    node_ids = {n["id"] for n in g["nodes"]}
    assert "openclaw:tool-policy" in node_ids
    assert "openclaw:channel-plugin" in node_ids


def test_build_graph_targets_edge(tmp_path):
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\n"
              "targets:\n  - tool-policy")

    g = build_graph(tmp_path / "wiki")

    edges = g["edges"]
    assert any(
        e["type"] == "targets"
        and e["from"] == "openclaw:channel-plugin"
        and e["to"] == "openclaw:tool-policy"
        for e in edges
    )


def test_build_graph_embodies_edge(tmp_path):
    make_node(tmp_path, "openclaw", "channel-plugin",
              "node_type: ExtensionPoint\nscope: subsystem\nconcept: 插件系统")

    g = build_graph(tmp_path / "wiki")

    assert any(
        e["type"] == "embodies"
        and e["from"] == "openclaw:channel-plugin"
        and e["to"] == "concept:插件系统"
        for e in g["edges"]
    )


def test_build_graph_motivated_by_edge(tmp_path):
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem\n"
              "motivated_by:\n  - sync-gate")

    g = build_graph(tmp_path / "wiki")

    assert any(
        e["type"] == "motivates"
        and e["from"] == "openclaw:sync-gate"
        and e["to"] == "openclaw:tool-policy"
        for e in g["edges"]
    )
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python -m pytest tests/test_graph.py -v 2>&1 | head -20
```

期望：`ModuleNotFoundError: No module named 'graph'`

- [ ] **Step 3: 实现 build_graph 函数（graph.py）**

创建 `scripts/graph.py`：

```python
#!/usr/bin/env python3
"""
graph.py — derive and query the codebase knowledge graph from node page frontmatter.

Usage:
  python scripts/graph.py build [--wiki wiki/] [--out wiki/graph/graph.json]
  python scripts/graph.py query --impact <node-slug> [--repo <repo>] [--wiki wiki/]
  python scripts/graph.py mermaid <repo> <dimension> [--wiki wiki/] [--hops 2]
"""
import argparse
import json
import re
import sys
from pathlib import Path


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Uses simple line parser (no PyYAML dep)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[3:end]
    body = text[end + 4:]

    fm: dict = {}
    current_key = None
    current_list: list | None = None

    for line in fm_text.splitlines():
        # List item
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue
        # Key-value or key: (list start)
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # Start of a list block
                current_list = []
                fm[key] = current_list
                current_key = key
            else:
                current_list = None
                current_key = key
                fm[key] = val
        else:
            current_list = None

    return fm, body


def build_graph(wiki_root: Path) -> dict:
    """Scan all nodes/ pages and return {nodes: [...], edges: [...]}."""
    nodes = []
    edges = []

    nodes_dirs = list((wiki_root / "repos").glob("*/nodes"))
    for nodes_dir in nodes_dirs:
        repo = nodes_dir.parent.name
        for node_file in sorted(nodes_dir.glob("*.md")):
            slug = node_file.stem
            node_id = f"{repo}:{slug}"
            fm, _ = _parse_frontmatter(node_file.read_text())

            node = {
                "id": node_id,
                "repo": repo,
                "slug": slug,
                "node_type": fm.get("node_type", ""),
                "scope": fm.get("scope", ""),
                "concept": fm.get("concept", ""),
                "sources": fm.get("sources", []) if isinstance(fm.get("sources"), list) else [],
            }
            nodes.append(node)

            # embodies edge: node → concept
            concept = fm.get("concept", "")
            if concept:
                edges.append({
                    "type": "embodies",
                    "from": node_id,
                    "to": f"concept:{concept}",
                })

            # targets edges: ExtensionPoint → Component
            targets = fm.get("targets") or []
            if isinstance(targets, str):
                targets = [targets]
            for t in targets:
                edges.append({
                    "type": "targets",
                    "from": node_id,
                    "to": f"{repo}:{t}",
                })

            # motivates edges (stored as motivated_by on the target): Decision → node
            motivated_by = fm.get("motivated_by") or []
            if isinstance(motivated_by, str):
                motivated_by = [motivated_by]
            for d in motivated_by:
                edges.append({
                    "type": "motivates",
                    "from": f"{repo}:{d}",
                    "to": node_id,
                })

    return {"nodes": nodes, "edges": edges}
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest tests/test_graph.py -v
```

期望：4 tests PASSED

- [ ] **Step 5: 提交**

```bash
git add scripts/graph.py tests/test_graph.py
git commit -m "feat(scripts): add graph.py build_graph — scan node frontmatter into graph dict"
```

---

## Task 6：graph.py —— build CLI + query 子命令

**Files:**
- Modify: `scripts/graph.py`（新增 `query_impact` + `main`）
- Modify: `tests/test_graph.py`（新增 impact query 测试）

- [ ] **Step 1: 写失败测试（impact query）**

在 `tests/test_graph.py` 末尾追加：

```python
def test_query_impact_direct(tmp_path):
    """Nodes targeted by or motivated_by the queried node should appear."""
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem\n"
              "motivated_by:\n  - sync-gate")
    make_node(tmp_path, "openclaw", "exec-approval",
              "node_type: ExtensionPoint\nscope: component\n"
              "targets:\n  - tool-policy\n"
              "motivated_by:\n  - sync-gate")

    from graph import query_impact
    result = query_impact(tmp_path / "wiki", "openclaw", "tool-policy")

    ids = {r["id"] for r in result}
    # sync-gate motivates tool-policy → sync-gate should appear as upstream cause
    assert "openclaw:sync-gate" in ids
    # exec-approval targets tool-policy → exec-approval should appear as downstream affected
    assert "openclaw:exec-approval" in ids


def test_query_impact_excludes_unrelated(tmp_path):
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem")
    make_node(tmp_path, "openclaw", "context-engine",
              "node_type: Component\nscope: subsystem")

    from graph import query_impact
    result = query_impact(tmp_path / "wiki", "openclaw", "tool-policy")

    ids = {r["id"] for r in result}
    assert "openclaw:context-engine" not in ids
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_graph.py::test_query_impact_direct tests/test_graph.py::test_query_impact_excludes_unrelated -v
```

期望：`ImportError: cannot import name 'query_impact'`

- [ ] **Step 3: 实现 query_impact 和 main**

在 `scripts/graph.py` 末尾追加（`build_graph` 函数后）：

```python
def query_impact(wiki_root: Path, repo: str, slug: str) -> list[dict]:
    """Return all nodes directly related to repo:slug via any edge type."""
    g = build_graph(wiki_root)
    target_id = f"{repo}:{slug}"
    related_ids: set[str] = set()

    for edge in g["edges"]:
        if edge["from"] == target_id:
            related_ids.add(edge["to"])
        if edge["to"] == target_id:
            related_ids.add(edge["from"])

    node_map = {n["id"]: n for n in g["nodes"]}
    return [node_map[nid] for nid in related_ids if nid in node_map]


def _cmd_build(args):
    wiki_root = Path(args.wiki)
    g = build_graph(wiki_root)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n")
    print(f"graph.py build: {len(g['nodes'])} nodes, {len(g['edges'])} edges → {out_path}")


def _cmd_query(args):
    wiki_root = Path(args.wiki)
    results = query_impact(wiki_root, args.repo, args.impact)
    if not results:
        print(f"No related nodes found for {args.repo}:{args.impact}")
        return
    print(f"\n## Impact: {args.repo}:{args.impact}\n")
    for n in sorted(results, key=lambda x: x.get("scope", "")):
        scope_tag = f"[{n['scope']}]" if n.get("scope") else ""
        concept_tag = f" → {n['concept']}" if n.get("concept") else ""
        print(f"  {n['id']}  {n['node_type']} {scope_tag}{concept_tag}")


def main():
    parser = argparse.ArgumentParser(description="Codebase wiki graph operations.")
    sub = parser.add_subparsers(dest="cmd")

    p_build = sub.add_parser("build", help="Scan node pages, write graph.json")
    p_build.add_argument("--wiki", default="wiki")
    p_build.add_argument("--out", default="wiki/graph/graph.json")

    p_query = sub.add_parser("query", help="Graph traversal queries")
    p_query.add_argument("--wiki", default="wiki")
    p_query.add_argument("--impact", required=True, metavar="SLUG",
                         help="Show all nodes related to REPO:SLUG")
    p_query.add_argument("--repo", required=True)

    args = parser.parse_args()
    if args.cmd == "build":
        _cmd_build(args)
    elif args.cmd == "query":
        _cmd_query(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行全部 graph 测试**

```bash
python -m pytest tests/test_graph.py -v
```

期望：全部 PASSED（6 tests）

- [ ] **Step 5: 手工验证 CLI**

```bash
cd /Users/yuanlimiao/Work/codebase-wiki
python scripts/graph.py build --wiki wiki --out wiki/graph/graph.json
python scripts/graph.py query --wiki wiki --repo openclaw --impact tool-policy
```

期望：`query` 输出里包含 `sync-gating-decision` 和 `exec-approval-request`

- [ ] **Step 6: 提交**

```bash
git add scripts/graph.py tests/test_graph.py wiki/graph/graph.json
git commit -m "feat(scripts): add graph.py query --impact and build CLI"
```

---

## Task 7：graph.py —— mermaid 子命令

**Files:**
- Modify: `scripts/graph.py`（新增 `generate_mermaid`）
- Modify: `tests/test_graph.py`（新增 mermaid 测试）

- [ ] **Step 1: 写失败测试**

在 `tests/test_graph.py` 末尾追加：

```python
def test_generate_mermaid_contains_nodes(tmp_path):
    make_node(tmp_path, "openclaw", "sync-gate",
              "node_type: DesignDecision\nscope: system")
    make_node(tmp_path, "openclaw", "tool-policy",
              "node_type: Component\nscope: subsystem\n"
              "motivated_by:\n  - sync-gate")

    from graph import generate_mermaid
    result = generate_mermaid(tmp_path / "wiki", "openclaw", center_slug="tool-policy", hops=1)

    assert "graph LR" in result
    assert "sync-gate" in result
    assert "tool-policy" in result
    assert "motivates" in result
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_graph.py::test_generate_mermaid_contains_nodes -v
```

期望：`ImportError: cannot import name 'generate_mermaid'`

- [ ] **Step 3: 实现 generate_mermaid**

在 `scripts/graph.py` 的 `query_impact` 之后、`_cmd_build` 之前插入：

```python
def generate_mermaid(wiki_root: Path, repo: str,
                     center_slug: str = None, hops: int = 2) -> str:
    """Generate a Mermaid LR graph snippet for a repo's nodes.

    If center_slug is given, only include nodes within `hops` edges of it.
    """
    g = build_graph(wiki_root)

    # Filter to this repo's nodes + cross-repo Concept nodes referenced
    repo_nodes = {n["id"]: n for n in g["nodes"] if n["repo"] == repo}

    if center_slug:
        center_id = f"{repo}:{center_slug}"
        # BFS up to `hops`
        visited: set[str] = {center_id}
        frontier = {center_id}
        for _ in range(hops):
            next_frontier: set[str] = set()
            for edge in g["edges"]:
                if edge["from"] in frontier and edge["to"] not in visited:
                    next_frontier.add(edge["to"])
                if edge["to"] in frontier and edge["from"] not in visited:
                    next_frontier.add(edge["from"])
            visited |= next_frontier
            frontier = next_frontier
        relevant_ids = visited
    else:
        relevant_ids = set(repo_nodes.keys())

    # Build label map
    def _label(node_id: str) -> str:
        if node_id in repo_nodes:
            n = repo_nodes[node_id]
            return f'"{n["slug"]}<br/>{n["node_type"]}"'
        # Concept node
        concept_name = node_id.replace("concept:", "")
        return f'"concept:{concept_name}"'

    lines = ["graph LR"]
    edge_type_labels = {
        "embodies": "embodies",
        "targets": "targets",
        "motivates": "motivates",
    }

    seen_edges: set[tuple] = set()
    for edge in g["edges"]:
        frm, to, etype = edge["from"], edge["to"], edge["type"]
        if frm not in relevant_ids and to not in relevant_ids:
            continue
        key = (frm, to, etype)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        label = edge_type_labels.get(etype, etype)
        lines.append(f"    {frm.replace(':', '_')}[{_label(frm)}] -->|{label}| {to.replace(':', '_')}[{_label(to)}]")

    return "\n".join(lines)
```

同时在 `main()` 的 `sub` 下新增 mermaid 子命令（在 `p_query` 之后）：

```python
    p_mermaid = sub.add_parser("mermaid", help="Generate Mermaid subgraph snippet")
    p_mermaid.add_argument("repo")
    p_mermaid.add_argument("--wiki", default="wiki")
    p_mermaid.add_argument("--center", default=None, metavar="SLUG",
                           help="Center node slug; if omitted, render whole repo")
    p_mermaid.add_argument("--hops", type=int, default=2)
```

在 `main()` 的分发处追加：

```python
    elif args.cmd == "mermaid":
        print(generate_mermaid(Path(args.wiki), args.repo,
                               center_slug=args.center, hops=args.hops))
```

- [ ] **Step 4: 运行全部 graph 测试**

```bash
python -m pytest tests/test_graph.py -v
```

期望：全部 PASSED（7 tests）

- [ ] **Step 5: 手工验证 mermaid 输出**

```bash
python scripts/graph.py mermaid openclaw --center tool-policy --hops 2
```

期望：输出以 `graph LR` 开头，包含 `tool-policy`、`sync-gating-decision`、`motivates` 等标签

- [ ] **Step 6: 提交**

```bash
git add scripts/graph.py tests/test_graph.py
git commit -m "feat(scripts): add graph.py mermaid subcommand for Obsidian subgraph blocks"
```

---

## Task 8：lint.py —— 新增 3 条图结构规则

**Files:**
- Modify: `scripts/lint.py`
- Modify: `tests/test_lint.py`

- [ ] **Step 1: 写 3 个失败测试**

在 `tests/test_lint.py` 末尾追加：

```python
# ---- graph structure lint rules ----

def test_check_invalid_edge_type_targets(tmp_path):
    """Component 不能有 targets 字段（targets 只属于 ExtensionPoint）。"""
    write(tmp_path / "wiki/repos/openclaw/nodes/bad.md",
          "---\nnode_type: Component\nscope: subsystem\ntargets:\n  - other\n---\n# Bad\n")
    from lint import check_graph_edge_types
    errors = check_graph_edge_types(tmp_path / "wiki")
    assert len(errors) == 1
    assert "bad" in errors[0]["detail"]


def test_check_dangling_targets(tmp_path):
    """targets 指向不存在的节点页时报错。"""
    write(tmp_path / "wiki/repos/openclaw/nodes/ep.md",
          "---\nnode_type: ExtensionPoint\nscope: subsystem\ntargets:\n  - nonexistent\n---\n# EP\n")
    from lint import check_graph_dangling_edges
    errors = check_graph_dangling_edges(tmp_path / "wiki")
    assert len(errors) == 1
    assert "nonexistent" in errors[0]["detail"]


def test_check_concept_not_registered(tmp_path):
    """concept 字段的值不在 _index.md 时报错。"""
    write(tmp_path / "wiki/entities/_index.md",
          "# Concept Index\n\n| Concept | 别名 | 定义 | 实例数 |\n|---|---|---|---|\n| 插件系统 | Plugin System | desc | 1 |\n")
    write(tmp_path / "wiki/repos/openclaw/nodes/ep.md",
          "---\nnode_type: ExtensionPoint\nscope: subsystem\nconcept: 未注册概念\n---\n# EP\n")
    from lint import check_concept_registered
    errors = check_concept_registered(tmp_path / "wiki")
    assert len(errors) == 1
    assert "未注册概念" in errors[0]["detail"]
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_lint.py::test_check_invalid_edge_type_targets tests/test_lint.py::test_check_dangling_targets tests/test_lint.py::test_check_concept_not_registered -v
```

期望：3 tests FAILED（`ImportError`）

- [ ] **Step 3: 在 lint.py 中实现 3 个新规则**

在 `scripts/lint.py` 的 `check_missing_entity_links` 函数之后、`run_all` 之前插入：

```python
def _parse_node_frontmatter(text: str) -> dict:
    """Minimal frontmatter parser for node pages (same logic as graph.py)."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_text = text[3:end]
    fm: dict = {}
    current_list: list | None = None
    for line in fm_text.splitlines():
        if line.startswith("  - ") and current_list is not None:
            current_list.append(line[4:].strip())
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val == "":
                current_list = []
                fm[key] = current_list
            else:
                current_list = None
                fm[key] = val
        else:
            current_list = None
    return fm


def check_graph_edge_types(wiki_root: Path) -> list:
    """[ERROR] node_type/edge-type constraint violations.

    Rules:
    - Only ExtensionPoint nodes may have `targets`
    - Only Component/ExtensionPoint nodes may have `concept`
    - Only Component/ExtensionPoint/DesignDecision nodes may have `motivated_by`
    """
    errors = []
    nodes_dirs = list((wiki_root / "repos").glob("*/nodes"))
    for nodes_dir in nodes_dirs:
        repo = nodes_dir.parent.name
        for node_file in nodes_dir.glob("*.md"):
            fm = _parse_node_frontmatter(node_file.read_text())
            ntype = fm.get("node_type", "")
            slug = node_file.stem

            if fm.get("targets") and ntype != "ExtensionPoint":
                errors.append({
                    "level": "ERROR",
                    "rule": "check_graph_edge_types",
                    "file": str(node_file.relative_to(wiki_root)),
                    "detail": f"{repo}:{slug} has `targets` but node_type is {ntype!r} (only ExtensionPoint allowed)",
                })
            if fm.get("concept") and ntype == "DesignDecision":
                errors.append({
                    "level": "ERROR",
                    "rule": "check_graph_edge_types",
                    "file": str(node_file.relative_to(wiki_root)),
                    "detail": f"{repo}:{slug} DesignDecision cannot have `concept` (use motivated_by instead)",
                })
    return errors


def check_graph_dangling_edges(wiki_root: Path) -> list:
    """[ERROR] targets / motivated_by pointing to non-existent node pages."""
    errors = []
    nodes_dirs = list((wiki_root / "repos").glob("*/nodes"))
    for nodes_dir in nodes_dirs:
        repo = nodes_dir.parent.name
        existing_slugs = {f.stem for f in nodes_dir.glob("*.md")}
        for node_file in nodes_dir.glob("*.md"):
            fm = _parse_node_frontmatter(node_file.read_text())
            slug = node_file.stem

            for field in ("targets", "motivated_by"):
                refs = fm.get(field) or []
                if isinstance(refs, str):
                    refs = [refs]
                for ref in refs:
                    if ref not in existing_slugs:
                        errors.append({
                            "level": "ERROR",
                            "rule": "check_graph_dangling_edges",
                            "file": str(node_file.relative_to(wiki_root)),
                            "detail": f"{repo}:{slug} {field} → {ref!r} does not exist in nodes/",
                        })
    return errors


def check_concept_registered(wiki_root: Path) -> list:
    """[ERROR] concept field value not present in wiki/entities/_index.md."""
    index_path = wiki_root / "entities" / "_index.md"
    if not index_path.exists():
        return []

    index_text = index_path.read_text()
    # Extract concept names from table rows (first column after |)
    registered: set[str] = set()
    for line in index_text.splitlines():
        if line.startswith("|") and not line.startswith("| Concept") and not line.startswith("|---"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 2 and cols[1]:
                registered.add(cols[1])

    errors = []
    nodes_dirs = list((wiki_root / "repos").glob("*/nodes"))
    for nodes_dir in nodes_dirs:
        repo = nodes_dir.parent.name
        for node_file in nodes_dir.glob("*.md"):
            fm = _parse_node_frontmatter(node_file.read_text())
            concept = fm.get("concept", "")
            if concept and concept not in registered:
                errors.append({
                    "level": "ERROR",
                    "rule": "check_concept_registered",
                    "file": str(node_file.relative_to(wiki_root)),
                    "detail": f"concept {concept!r} not found in entities/_index.md",
                })
    return errors
```

在 `run_all` 函数中追加三个调用（`check_missing_entity_links` 之后）：

```python
    findings += check_graph_edge_types(wiki_root)
    findings += check_graph_dangling_edges(wiki_root)
    findings += check_concept_registered(wiki_root)
```

- [ ] **Step 4: 运行全部 lint 测试**

```bash
python -m pytest tests/test_lint.py -v
```

期望：全部 PASSED

- [ ] **Step 5: 对现有 wiki 运行 lint，确认无新 ERROR**

```bash
python scripts/lint.py --wiki wiki --manifest .manifest.json
```

期望：无 `[ERROR] check_graph_*` 输出（新规则对现存页面干净）

- [ ] **Step 6: 提交**

```bash
git add scripts/lint.py tests/test_lint.py
git commit -m "feat(lint): add 3 graph structure rules — edge types, dangling edges, unregistered concept"
```

---

## Task 9：更新 check_missing_entity_links 行为

**Files:**
- Modify: `scripts/lint.py`
- Modify: `tests/test_lint.py`

现行规则检查"维度页是否有 entity wikilink"，与准入三问的方向相反（召回 vs 精度）。改为检查 `concept_candidate` 积压。

- [ ] **Step 1: 写失败测试**

在 `tests/test_lint.py` 末尾追加：

```python
def test_check_candidate_backlog_warns_when_many(tmp_path):
    """当某个 repo 的 nodes/ 下积压 >=3 个 concept_candidate 时应报警。"""
    for i in range(3):
        write(tmp_path / f"wiki/repos/openclaw/nodes/ep{i}.md",
              f"---\nnode_type: ExtensionPoint\nscope: subsystem\n"
              f"concept_candidate: 候选概念{i}\n---\n# EP{i}\n")
    from lint import check_candidate_backlog
    warnings = check_candidate_backlog(tmp_path / "wiki")
    assert len(warnings) == 1
    assert "openclaw" in warnings[0]["detail"]


def test_check_candidate_backlog_ok_when_few(tmp_path):
    for i in range(2):
        write(tmp_path / f"wiki/repos/openclaw/nodes/ep{i}.md",
              f"---\nnode_type: ExtensionPoint\nscope: subsystem\n"
              f"concept_candidate: 候选{i}\n---\n# EP{i}\n")
    from lint import check_candidate_backlog
    warnings = check_candidate_backlog(tmp_path / "wiki")
    assert warnings == []
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest tests/test_lint.py::test_check_candidate_backlog_warns_when_many tests/test_lint.py::test_check_candidate_backlog_ok_when_few -v
```

- [ ] **Step 3: 实现 check_candidate_backlog，降级 check_missing_entity_links**

在 `scripts/lint.py` 的 `check_concept_registered` 之后、`run_all` 之前插入：

```python
def check_candidate_backlog(wiki_root: Path, threshold: int = 3) -> list:
    """[WARN] A repo has >= threshold unconfirmed concept_candidate nodes."""
    warnings = []
    nodes_dirs = list((wiki_root / "repos").glob("*/nodes"))
    for nodes_dir in nodes_dirs:
        repo = nodes_dir.parent.name
        candidates = []
        for node_file in nodes_dir.glob("*.md"):
            fm = _parse_node_frontmatter(node_file.read_text())
            if fm.get("concept_candidate"):
                candidates.append(node_file.stem)
        if len(candidates) >= threshold:
            warnings.append({
                "level": "WARN",
                "rule": "check_candidate_backlog",
                "file": f"wiki/repos/{repo}/nodes/",
                "detail": f"{repo} has {len(candidates)} unconfirmed concept_candidate(s): {candidates} — run normalization pass",
            })
    return warnings
```

在 `run_all` 中的 `check_missing_entity_links` 调用上方加注释，并追加新规则：

```python
    # check_missing_entity_links: demoted — signals quantity not quality.
    # Replaced by check_candidate_backlog for graph-layer projects.
    findings += check_missing_entity_links(wiki_root)
    findings += check_candidate_backlog(wiki_root)
```

- [ ] **Step 4: 运行全部 lint 测试**

```bash
python -m pytest tests/test_lint.py -v
```

期望：全部 PASSED

- [ ] **Step 5: 提交**

```bash
git add scripts/lint.py tests/test_lint.py
git commit -m "feat(lint): add check_candidate_backlog, demote check_missing_entity_links"
```

---

## Task 10：更新 skills/code-ingest 和 skills/code-query

**Files:**
- Modify: `skills/code-ingest/SKILL.md`（新增 Step 3.5）
- Modify: `skills/code-query/SKILL.md`（新增图遍历分支）

- [ ] **Step 1: 在 code-ingest/SKILL.md 的 Step 3 之后插入 Step 3.5**

在 `skills/code-ingest/SKILL.md` 找到 `### Step 4 — Write overview.md` 前，插入：

```markdown
### Step 3.5 — Node Extraction (graph layer)

After writing each dimension page, extract structured nodes for `wiki/repos/<name>/nodes/`.

**What to extract per node:**

For each identifiable Component / ExtensionPoint / DesignDecision (see `schema/graph-schema.md`):

1. Assign `node_type`: Component (can you point to it in the directory tree?), ExtensionPoint (does it have a register/interface/hook pattern?), DesignDecision (is there a "we chose X over Y because Z" chain in docs/commits/comments?)
2. Assign `scope`: system (affects whole architecture), subsystem (one area), component (single class/struct)
3. If this node matches a Concept in `wiki/entities/_index.md` (check by name + aliases), set `concept:`
4. If it matches nothing in the index but you believe it could be a cross-repo concept, set `concept_candidate: <proposed name>` instead — do NOT add it to _index.md without the three-question test
5. Set `targets:` (for ExtensionPoint → Component links found via code structure)
6. Set `motivated_by:` (for nodes caused by a DesignDecision found in design docs/comments)
7. Add `sources:` pointing to the key file:line ranges

Write one file per node: `wiki/repos/<name>/nodes/<slug>.md`

**Do not extract:**
- Functions, class names, file paths (implementation details)
- Patterns present in every codebase (singleton, lazy-loading, retry)
- Tool/library names visible in package.json without reading code

After writing nodes, run:
```bash
python scripts/lint.py --wiki wiki --manifest .manifest.json
```
Fix any `[ERROR] check_graph_*` findings before proceeding to Step 4.
```

- [ ] **Step 2: 在 code-query/SKILL.md 插入图遍历分支**

在 `## Retrieval Escalation Chain` 前插入：

```markdown
## Graph Traversal (run before escalation chain for structural questions)

If the question contains any of these patterns, use graph traversal **before** the retrieval escalation chain:

- "改 X 会波及什么" / "X 的影响范围" / "impact of X"
- "为什么有 X" / "X 为什么存在" / "why does X exist"
- "哪些仓库也有 X" / "which repos implement X" / "cross-repo X"

### Graph traversal steps

1. Identify the node slug from the question (map concept/component name to a slug in `wiki/repos/*/nodes/`)
2. Run:
   ```bash
   python scripts/graph.py query --wiki wiki --repo <repo> --impact <slug>
   ```
3. For each related node returned, read its node page (`wiki/repos/<repo>/nodes/<slug>.md`)
4. Format the answer as a traversal narrative (see output format below)

### Graph traversal output format

```
## 影响发现：<node name>

**直接关联节点**（通过 targets / motivates 边）：

- **<node-id>** [<node_type>, <scope>]
  <one-line description from node page>
  ^[source from node page]

**决策来源**（motivates 反向追溯）：

- <DesignDecision node>：<why this decision created the queried node>

**跨仓库同模式**（embodies → Concept ← embodies）：

- <other-repo node> also embodies <Concept> — compare: <key difference>

遍历路径：
  <node-id> ←edge-type─ <related-id> ─edge-type→ <related-id>
```

If graph.py returns no results, fall through to the retrieval escalation chain.
```

- [ ] **Step 3: 提交**

```bash
git add skills/code-ingest/SKILL.md skills/code-query/SKILL.md
git commit -m "feat(skills): add node extraction step to ingest, graph traversal branch to query"
```

---

## 自检

### Spec 覆盖

| 架构评估文档要求 | 对应 Task |
|---|---|
| schema/graph-schema.md（3 节点 + 3 边 + scope + 准入三问 + 节点页模板） | Task 1 |
| entity 分诊 + 降级 5 个 + 重命名 1 个 + 观察名单 | Task 2 |
| wiki/entities/_index.md 初始化（分诊幸存者） | Task 2 |
| openclaw 节点页 ≥6 个 | Task 3 |
| hermes-agent 节点页 ≥4 个 | Task 4 |
| graph.py build（frontmatter → 边表） | Task 5 |
| graph.py query --impact（影响发现遍历） | Task 6 |
| graph.py mermaid（局部子图） | Task 7 |
| lint 3 条新规则（边类型 / 悬空 / 未注册概念） | Task 8 |
| check_candidate_backlog 替代 check_missing_entity_links | Task 9 |
| /analyze 新增 Step 3.5 节点抽取协议 | Task 10 |
| /query 新增图遍历分支 | Task 10 |
| graph.json 为派生物（build 生成，不手写） | Task 6 |
| Step 0 价值预验证（手工，非编码） | Step 0 前置说明 |

### 类型一致性

- `build_graph` 返回 `{"nodes": [...], "edges": [...]}`，Task 6/7 均从此接口读取，一致。
- `query_impact` 参数 `(wiki_root, repo, slug)` 与 `_cmd_query` 调用 `query_impact(wiki_root, args.repo, args.impact)` 一致。
- lint 新规则均调用 `_parse_node_frontmatter`（同一函数），与 graph.py 的解析逻辑同构（两者均为 stdlib-only 实现，独立副本，避免跨脚本 import）。
- 节点页 frontmatter 字段名（`node_type / scope / concept / targets / motivated_by`）在 schema、graph.py、lint.py、skill 文档中完全一致。
