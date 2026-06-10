# Entity Nodes Design

**Date:** 2026-06-10  
**Status:** Approved

## Problem

当前 codebase-wiki 的 Obsidian 图谱中，节点粒度是「维度页」（每个 repo × 每个 dimension 一个页面）。这些连接都是预先设计好的，图谱只是把已知结构可视化，不能发现跨 repo 的知识关联。

Karpathy 原文描述的是 entity 粒度的节点（架构模式、技术栈、领域概念），同一个概念节点可以被多个 repo 链接——这才是知识发现。

## Solution

方案 B：在 dimension 页行文中内联 entity wikilink，按需延迟生成 entity 页内容。

- analyze 流程基本不变，摩擦最小
- Obsidian 的 unresolved node（虚线节点）在 entity 页生成前就能展示「哪些概念被多个 repo 引用」，本身是知识发现信号
- 积累若干 repo 后手动跑 consolidate pass，补全 entity 页内容

## Entity 层次边界

只抽取以下三层，第四层（具体实现）不进入 entity 节点：

| 层次 | 示例 | 说明 |
|---|---|---|
| 架构模式 | `[[事件驱动]]`、`[[分层架构]]`、`[[插件注册表]]` | 跨 repo 可共享的设计模式 |
| 技术栈 | `[[Python asyncio]]`、`[[TypeScript monorepo]]` | 语言/运行时/构建体系层面的技术选型 |
| 领域概念 | `[[Context 压缩]]`、`[[Memory Provider]]` | AI agent 领域特有的抽象概念 |
| ~~具体实现~~（不标） | `BasePlatformAdapter`、`MemoryManager`、文件路径 | 单 repo 内部的类名/函数名/实现细节 |

## Schema 变更

在 `schema/CLAUDE.md` 的 Double-Link Rules 表格中新增 entity wikilink 规则：

```
| 行文中提到架构模式/技术栈/领域概念 | ✅ 用 [[概念名]] 内联标记，如 [[事件驱动]]、[[Context 压缩]] |
| 具体类名、函数名、文件路径 | ❌ 不标 entity wikilink |
| 代码块内 | ❌ 不标，遵循现有规则 |
```

entity wikilink 和 repo cross-link 不冲突，一个句子里可以同时出现 `[[事件驱动]]` 和 `[[hermes-agent/dimensions/architecture]]`。

## Entity 页模板

consolidate pass 时，`wiki/entities/<概念名>.md` 使用以下格式：

```markdown
---
type: entity
category: 架构模式   # 或 技术栈 / 领域概念
---

# 概念名

一句话定义。

## 在各 repo 中的体现

- [[openclaw/dimensions/architecture]] — 简短说明
- [[hermes-agent/dimensions/architecture]] — 简短说明
```

consolidate pass 不自动触发，手动执行。执行时机：新增 repo 后，或图谱中出现较多 unresolved entity 节点时。

## Lint 变更

新增一条 lint 规则 `check_missing_entity_links`：

- **触发条件：** dimension 页正文中完全没有 `[[` 开头且不包含 `/` 的 wikilink（即没有任何 entity wikilink）
- **级别：** `[WARN]`
- **例外：** `overview.md` 页不检查（它只链接 dimension 页，不负责标 entity）

entity 页本身为空（只有 frontmatter + 标题）是正常的早期状态，不触发 lint 警告。

## 不在本次范围内

- 重命名 dimension 文件（解决 Obsidian 图谱同名节点问题）——这是独立问题，可单独处理
- entity 去重/consolidate 的自动化——手动 pass 足够，不过度设计
- embedding-based 相似度检测——repo 数量有限时不需要
