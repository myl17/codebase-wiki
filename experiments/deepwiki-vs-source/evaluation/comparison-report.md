# 实验报告：Source Code vs DeepWiki — Architecture 维度提取

> 日期: 2026-06-14 | 仓库: openclaw | 维度: Architecture

## 实验方法

| | Path A (Source Code) | Path B (DeepWiki) |
|---|---|---|
| 输入 | openclaw 源码目录 | DeepWiki 预解析 65 页内容 (968K) |
| 提取者 | subagent (general-purpose, 独立上下文) | subagent (general-purpose, 独立上下文) |
| 自由度 | 自主决定读哪些文件，不限定文件列表 | 自主决定读哪些页面，不限定页面 |
| 维度指南 | 相同 | 相同 |
| 输出格式 | 相同 (中文 Markdown + provenance + 核心抽象→分层→数据流→关注点分离→关联) | 相同 |

完全对称实验。唯一变量是输入源。

---

## 定量对比

| 指标 | Wiki 现有版 | Source Code | DeepWiki | DeepWiki vs Source | vs Wiki |
|------|-----------|-------------|----------|-------------------|---------|
| 文件大小 | 7.0K | 20.6K | 33.8K | +64% | +383% |
| 行数 | 97 | 261 | 343 | +31% | +254% |
| provenance 数 | 13 | 48 | 133 | +177% | +923% |
| 核心抽象数 | 9 | 10 | 8 | -2 | — |
| 分层数 | 未见明确分层 | 12 | 5 | — | — |
| 数据流路径 | 4 | 3 | 5 | +2 | — |
| 关注点分离项 | 0 | 7 | 7 | 持平 | — |

---

## 定性对比

### Source Code 的优势

1. **架构边界规则更精确。** 从 CLAUDE.md / AGENTS.md 读到了设计约束：「核心不能对特定扩展硬编码特判」「Plugin SDK 是唯一公共契约」「禁止从无关代码临时读取 plugins.entries.<id>.config」。这些反映了团队的架构纪律，不是代码结构本身能体现的。

2. **分层更细。** 12 层架构清楚标定每层的源码位置，可直接追踪。

3. **Plugin SDK 作为独立抽象。** 识别出 70+ 细粒度子路径的插件契约设计意图。

### DeepWiki 的优势

1. **全景覆盖。** 设备节点层 (iOS/Android NodeRuntime)、原生客户端、ACP Sub-Agent 编排、沙箱层、多平台构建分离——Source 完全没有涉及这些。因为这些代码在 `apps/`、`scripts/` 目录，不在 `src/` 核心区。

2. **数据流更完整。** 5 条数据流 vs 3 条。多了子 Agent 编排流和原生节点调用流。

3. **基础设施细节。** launchd/systemd 守护进程管理、协议代码自动生成、Docker 沙箱架构。

4. **天然跨仓库可比的抽象层次。** 关联区块主动对比了 Gpt-Corpuse、DataMaid 等仓库。

### 共同的盲区（两者都没有）

- **设计权衡分析。** 维度指南要求"Data flow direction? How is concern separation achieved?"但没要求分析"牺牲了什么"。两者都描述了架构事实，没有做因果链分析。
- **Provenance 来源不可验证。** 两个 agent 标注的 `^[文件:行号]` 未经过实际源码行号校验，准确性未知。尤其是 DeepWiki 的行号可能来自 DeepWiki 索引时刻已过时。

---

## 为什么三者差异这么大：根因不在输入源

| | Wiki 现有版 | 实验 agent |
|---|---|---|
| `/analyze` 流程 | draft → 用户确认 → 如果确认就停了 | "广泛探索直到全面理解" |
| 交互模式 | 对话式渐进深化 | 一次性穷尽可能 |

`/analyze` skill 的 Step 3-4 设计是：「草稿 → 告诉用户发现 → 问要不要调整或深入 → 用户确认后写入」。人的确认是一个「够好了」的信号，不是「完美了」。如果初稿看起来还行，深化就不会发生。

而实验 prompt 是「不要只读几个文件就收手。广泛探索直到全面理解」。agent 被要求穷尽。

**根因是 prompt 的 explore depth 不同，不是输入源不同。**

---

## 关键发现

1. **DeepWiki 能覆盖源码路径必然遗漏的东西。** Source agent 读了 58 次文件，全在 `src/` 里，从未进入 `apps/`、`scripts/`。单 agent turn 不可能完成全仓库探索。

2. **但 DeepWiki 缺乏设计意图。** 它描述「是什么」，但没有从源码注释和 AGENTS.md 中读到「为什么这么设计」「什么是鼓励的什么是禁止的」——这些设计约束大量存在于 AGENTS.md / CLAUDE.md 而非代码中。

3. **两者互补，不是替代。** DeepWiki 做广度扫描（什么都有），Source 做深度解读（为什么这样）。最理想的路径：DeepWiki 提供全局概念地图 → agent 定向深读关键源文件 → 产出既有全景又有因果链的维度页。

---

## 优化建议

### 短期（改 prompt 即可）

`/analyze` 的 Step 3 从「draft → confirm → write」改为二阶段：

```
阶段 A（穷尽探索）: agent 自由探索，不允许收手直到 agent 确认已经穷尽关键路径
阶段 B（人指导深化）: 展示穷尽探索的产出 → 人挑出最感兴趣的 2-3 点说 "这里再深入" → agent 重点深挖
```

核心改动：把「我可以停了吗？」的控制权从 agent 交给人，同时明确要求 agent 在等待确认前必须完成足够广的探索。

### 中期（引入 DeepWiki 作为预扫描）

在 `/analyze` Step 1 和 Step 2 之间插入 Step 1.5：

```
Step 1.5 — DeepWiki 预扫描（可选）
  如果仓库在 DeepWiki 上有预解析内容 → 通过 MCP 拉取 → 作为 agent 的参考地图
  agent 基于 DeepWiki 的全局概念地图，定向深读关键源文件
```

这不增加成本（DeepWiki MCP 公开仓库免费），不增加延迟（几个 API 调用），但能给 agent 提供一个它自己不可能在一个 turn 里完成的全局扫描。

### 长期（补齐结构层）

如果覆盖仓库超过 20 个且 DeepWiki 覆盖率不足 → 自建薄结构层：
- 模块树 + import 拓扑（服务 Architecture 和 Dependency 维度）
- 接口实现检测（服务 Extension Points 维度）
- 不需要完整 AST 管线，正则 + import 解析足够
