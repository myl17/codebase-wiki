# 新流程验证报告

> 日期: 2026-06-14 | 仓库: hermes-agent | 维度: Performance Tradeoffs | 流程: 完整新 `/analyze` Step 3

## 执行方式

5 个独立 subagent 串行执行，每个独立上下文窗口：

```
Phase 1: Architecture (56 tool uses)
  → 产出 26 个核心抽象 + 子系统清单
  → /tmp/experiment-arch-hermes.md

Phase 1: Extension Points (45 tool uses)
  → 基于 Architecture 清单逐个子系统检查扩展机制
  → 产出 25 个扩展点
  → /tmp/experiment-ext-hermes.md

Phase 2: Performance Tradeoffs — 3a 候选清单 (41 tool uses)
  → 基于 Architecture + Extension Points 清单逐个子系统检查
  → 产出 22 条候选权衡 + 自审 checklist
  → /tmp/experiment-perf-candidates.md

Phase 2: Performance Tradeoffs — 3b 对抗式评审 (60 tool uses)
  → 独立 subagent，不共享候选 agent 的上下文
  → 逐条验证 provenance + 检查覆盖完整性 + 验证自审诚实性
  → /tmp/experiment-perf-review.md

Phase 2: Performance Tradeoffs — 3c 修复+写入 (16 tool uses)
  → 基于评审反馈补充 4 条遗漏 + 诚实标注未覆盖子系统
  → hermes-agent-performance-tradeoffs-final.md

总 subagent 调用: 5 次
总 tool uses: 218 次
```

## 对抗式评审结果

| 指标 | 发现 |
|------|------|
| provenance 准确性 | 22/22 ✅ 全部通过（无行号偏移、无虚构） |
| 发现的遗漏 | 4 处：Smart Approval、Skills Guard、Prompt Caching、Tirith Security |
| 自审诚实性 | 部分诚实——文件路径真实、provenance 准确，但覆盖宣称过度（声称覆盖所有实际漏了 4 个） |

## 对比：三次实验

| 指标 | v1（单次提取） | v3（实验流程约束） | Final（新 prompt + 完整流程） |
|------|--------------|-----------------|---------------------------|
| 权衡数 | 10 | 30 | 26 |
| 行数 | 191 | 406 | 410 |
| provenance | 46 | 72 | 26 |
| subagent 数 | 1 | 4 | 5 |
| 已知盲区覆盖 | ❌（11 遗漏） | ✅ 补全 | ✅ 补全 |
| 每条是否有「与常规做法不同」 | ❌ 无 | ❌ 无 | ✅ 有 |

## 关键发现

1. **新 prompt 的「与最常规做法有什么不同」有效。** Final 版的 26 条每条都包含这个维度，这是 v1 和 v3 都没有的。这正是心智模型层提取所需的因果推理。

2. **对抗式评审持续有效。** 两次实验（v3 + Final）中，对抗式评审都发现了候选 agent 遗漏的子系统。自审 checklist 不足以保证覆盖完整性。

3. **Phase 1（Architecture + Extension Points）作为 Phase 2 的 checklist 有效。** 两个实验都证明了基于子系统清单的逐项检查比开放探索的覆盖度更高。

4. **自审不诚实是系统性问题。** agent 倾向于声称覆盖了但实际上跳过了某些目录。必须用独立 subagent 验证。

## 结论

新流程（Phase 1 → Phase 2 + 对抗式评审 + 「与常规做法不同」因果引导）有效。产出质量全面优于单次提取。
