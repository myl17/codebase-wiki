# Experiment: DeepWiki vs Source Code — Dimension Extraction Quality

**日期**: 2026-06-14
**分支**: `feat/experiment-deepwiki-vs-src`
**目标**: 验证 LLM 从不同输入源提取维度叙事的质量差异

---

## 实验设计

| | Path A (Source Code First) | Path B (DeepWiki First) |
|---|---|---|
| **输入** | OpenClaw 源码（/analyze 直接读取） | DeepWiki 已解析的 OpenClaw 知识内容 |
| **提取指南** | 相同的 `schema/dimensions.md` v1.0 | 相同的 `schema/dimensions.md` v1.0 |
| **提取者** | LLM（Claude） | LLM（Claude） |
| **产出** | `wiki/repos/openclaw/dimensions/*.md` | `experiments/.../llm-output-deepwiki/*.md` |

---

## 待验证假设

1. **完整性假设**: Path B 能覆盖的维度信息比 Path A 更多（DeepWiki 有 65 页预解析内容）
2. **准确性假设**: Path B 的 provenance 可能不准确（DeepWiki 引用的行号可能过时或错误）
3. **深度假设**: Path A 的设计分析（因果链、取舍判断）可能更深（LLM 直接读代码能发现隐式模式）
4. **效率假设**: Path B 提取更快（DeepWiki 内容已被结构化，不需要 LLM 通读源码）

---

## 目录结构

```
experiments/deepwiki-vs-source/
├── README.md                           # 本文件
├── deepwiki-raw/                       # DeepWiki MCP 拉取的原始内容
│   ├── dw_openclaw_content.md
│   └── dw_hermes_content.md
├── llm-output-source/                  # Path A: 源码 → LLM → 维度页（现有产出）
│   ├── openclaw-architecture.md
│   └── openclaw-extension-points.md
├── llm-output-deepwiki/               # Path B: DeepWiki → LLM → 维度页（本次实验产出）
│   ├── openclaw-architecture.md
│   └── openclaw-extension-points.md
└── evaluation/                         # 对比评估
    └── comparison-report.md
```

---

## 实验方法

1. 从 DeepWiki MCP 拉取 OpenClaw 的完整内容（65 页，968K chars）
2. 选取与维度相关的页面作为输入（排除 Overview/Glossary/Getting Started 等基础页）
3. 使用相同的 `schema/dimensions.md` 指南和 `schema/CLAUDE.md` 规则
4. LLM 产出维度页，遵守相同的 provenance 格式、wikilink 规则
5. 与现有维度页做逐项对比

---

## 注意

- 此分支仅用于实验，不会合并回 `feat/graph-wikilinks`
- 实验产出的 `llm-output-deepwiki/` 不会影响 `wiki/` vault 中的现有内容
