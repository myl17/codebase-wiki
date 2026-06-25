# 第七轮实验执行追踪

> 日期: 2026-06-14 | 仓库: hermes-agent | 维度: Performance Tradeoffs | 流程: 三步过程约束

## 实际执行流程

**不是「一个模型接到包含三步骤的提示词」。是分别调用 3 次 subagent。** 每次 subagent 有独立上下文窗口，互不知晓对方存在。

```
Round 1: Step 0 (baseline)
  └─ Agent tool: general-purpose subagent
     ├─ prompt: 事实核查员，对 v1 维度页做反向验证
     ├─ 输入: v1 维度页 + hermes-agent 源码
     ├─ 产出: /tmp/step0-v1-review.md
     ├─ tool_uses: 60 次 (读取源码验证)
     └─ 发现: 5/5 行号准确，11 处遗漏，总评 8.5/10

Round 2: Step 1 (候选清单 + 自审)
  └─ Agent tool: general-purpose subagent
     ├─ prompt: 提取 Performance Tradeoffs，输出候选清单 + 自审
     ├─ 输入: hermes-agent 源码
     ├─ 产出: /tmp/step1-candidates.md
     ├─ tool_uses: 57 次
     └─ 产出: 20 条权衡 + 自审 checklist

Round 3: Step 2 (对抗式评审)
  └─ Agent tool: general-purpose subagent
     ├─ prompt: 事实核查员，对候选清单反向验证
     ├─ 输入: /tmp/step1-candidates.md + hermes-agent 源码
     ├─ 产出: /tmp/step2-review.md
     ├─ tool_uses: 38 次
     └─ 发现: 2 条不精确 provenance、5 个盲区全有遗漏、自审不诚实

Round 4: Step 3 (修复)
  └─ Agent tool: general-purpose subagent
     ├─ prompt: 基于评审修复 → 生成最终维度页
     ├─ 输入: /tmp/step1-candidates.md + /tmp/step2-review.md + hermes-agent 源码
     ├─ 产出: hermes-agent-performance-tradeoffs-v3.md
     ├─ tool_uses: 48 次
     └─ 产出: 30 条权衡，8 类问题全部修复

总 subagent 调用: 4 次
总 tool_uses: 203 次
```

## 中间结果位置

| 步骤 | 文件 |
|------|------|
| Step 0 | `evaluation/step0-v1-review.md` |
| Step 1 | `evaluation/step1-candidates.md` |
| Step 2 | `evaluation/step2-review.md` |
| Step 3 (最终) | `llm-output-source/hermes-agent-performance-tradeoffs-v3.md` |
| 评估 | `evaluation/process-constraint-validation.md` |

## 关键发现

**三步流程 = 多个独立 subagent 串行调用，不是单个 agent 自己分步执行。** Step 2 的评审 agent 完全不知道 Step 1 agent 的思路——它独立读源码验证。这是「对抗式评审」有效的根本原因：评审者的上下文没有被评审者污染。
