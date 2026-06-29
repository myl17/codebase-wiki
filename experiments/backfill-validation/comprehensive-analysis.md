# C3 综合分析：跨关切映射 + 向后传播

## 改进 A：解除一对一约束

### 验证结论：✅ 通过

| 检查项 | 结果 |
|--------|------|
| subagent-middleware 产出 ≥2 条 | ✅ 子任务委派 + 生命周期拦截（合并） |
| memory-middleware 产出 ≥2 条 | ✅ 持久化上下文 + 生命周期拦截（合并） |
| tool-call-patching 不再被跳过 | ✅ 独立条目 |
| 存在匹配 hooks-event-interception 的条目 | ✅ "如何在 Agent 生命周期关键节点拦截执行流程" |
| 条目数增加 | 12 entity → 16 条（旧版 ~8-10 条） |

### 关键洞察

解除约束后，生命周期拦截条目覆盖了 deepagents 的全部三种 hook 模式：

| Hook 类型 | 使用 Entity | 入口 |
|-----------|-----------|------|
| `before_agent` | memory-middleware, tool-call-patching | 懒加载记忆 + 修复悬空调用 |
| `wrap_model_call` | subagent-middleware | 注入 task 工具使用说明 |
| `interrupt_on` | subagent-middleware | 人工审批配置继承 |

**提示词中不包含任何 deepagents 特定术语**（`before_agent`、`wrap_model_call` 等来自 entity 页原文），模型从 entity 页提取机制名称并作为独立设计维度提交。

### 假阳性检查

没有产生硬套的多余条目。唯一可能的争议是 "上下文溢出管理" 从 filesystem-middleware 拆出——但这个拆分在语义上成立（文件系统工具提供 vs 上下文窗口保护是两个独立的关切，互不包含测试通过）。

---

## 改进 B：向后传播两层 grep

### 验证结论：⚠️ 通过但有退化风险

| 检查项 | 结果 |
|--------|------|
| 覆盖 ≥2 地面真值 | ✅ 5/5 全部覆盖 |
| 假阳性 < 3 | ❌ 6 个有效假阳性 |
| 机械 grep 独立贡献 | 3/5 地面真值（agent-graph-assembly, tool-call-patching, subagent-middleware） |
| LLM 搜索词独立贡献 | filesystem-middleware, memory-middleware（仅靠 `middleware`） |

### 机械 grep 层的局限

concerns 是中文概念语言 → entity 正文是混合语言实现语言。语言断层天然存在：

| concerns 词 | 预期语义 | 实际误中 |
|------------|---------|---------|
| 覆盖 | coverage | model-resolution 中 "覆盖不同格式" |
| 执行 | hook execution | 6 个 entity 中作为 "命令执行/任务执行" 通用词 |
| 过滤 | matcher filtering | state-backend 中数据过滤 |

这是中文通用词在 entity 正文中的多义性，无法通过调整 concerns 写法消除。

### LLM 搜索词层的退化

8 个搜索词中 `middleware` 命中 11/12 entity（92%），实际上丧失了语义区分度。如果去掉 `middleware`：

| 搜索词 | 命中 |
|--------|------|
| hook | 0 |
| lifecycle | 0 |
| wrap_ | 1 (subagent-middleware) |
| intercept | 0 |
| pipeline | 0 |
| callback | 0 |
| extension | 1 (skills-middleware) |

**仅 `wrap_` 有真实语义贡献。** 其他 6 个词的零命中说明 LLM 生成的模式词与 deepagents 的实现术语在字符串层面不匹配——尽管语义相关。

### 但提示词没有框架特定泄露

搜索词生成过程刻意避免了 codex API 术语：

| 跳过的 codex 术语 | 替代的抽象词 |
|-------------------|------------|
| PreToolUse, PostToolUse | before, wrap |
| PermissionRequest, SessionStart | lifecycle, intercept |
| 外部命令执行引擎 | pipeline, callback |

提示词设计是正确的——LLM 确实在抽象而非复用。问题不在于提示词泄露，而在于**抽象词和具体 API 名字之间的字符串级鸿沟，在一个 repo 内可以通过命名约定跨过（`middleware`），在另一个 repo 可能完全跨不过**。

### filesystem-middleware 的案例暴露了根本问题

filesystem-middleware 是地面真值——它的 `wrap_model_call` + `wrap_tool_call` 两个钩子是生命周期拦截的典型案例。但它：
- 第 1 层：零命中（entity 正文不含任何 concerns 中文词）
- 第 2 层：仅靠 `middleware` 命中（命名约定巧合，非语义选择）

**在 500 个仓库中，命名约定没有 deepagents 这么统一的仓库才是多数。** 如果一个仓库把 hook 机制实现在 `Executor.prototype.beforeExecute` 中，文件名是 `executor.js`，两层 grep 都找不到。

---

---

## 改进 A 重测：去掉指向性示例 (v3)

### 清理内容

v2 提示词中存在三处指向性内容：

| 位置 | 原文 | 问题 |
|------|------|------|
| 示例 | "例如，一个中间件...又通过生命周期钩子介入实现了'在 Agent 关键节点如何拦截'" | 直接告诉模型找 hook |
| 列举 | "如 before_agent、wrap_model_call、interrupt_on 等生命周期钩子" | 列出了具体 API 名 |
| 整体 | 只有一个示例，只指向 hook 一个方向 | 模型看到例子的那一刻就已经知道结论了 |

v3 的清理方案：**完全去掉例子，用程序性聚合检查替代。**

> 全部映射完成后，回头看所有 entity 的正文，列出其中出现过的技术机制（不是 entity 的主问题，而是 entity 正文中用于实现其功能的机制），标注每个机制被哪些 entity 使用。如果某个机制被 ≥2 个 entity 共用，且当前 problem-map 中没有独立条目覆盖该机制的设计维度，补充一条。

这不告诉模型找什么——它不知道自己会找到什么。它只是被要求做一个它没做过的机械操作：扫描正文 → 提取机制名 → 数出现次数。

### 验证结论：✅ 通过，且优于 v2

| 维度 | v2 (含 hook 示例) | v3 (纯程序性检查) |
|------|------------------|-------------------|
| 生命周期拦截 | ✅ 发现（逐 entity 阶段） | ✅ 发现（聚合检查阶段） |
| 发现时机 | 提示词暗示方向 → 逐 entity 时留意 | 数据驱动 → 3 个 entity 正文都写了 before_agent/wrap_model_call → 自然浮现 |
| 可辩护性 | 弱（"模型是听了话才找到的"） | 强（"数据里有，模型数出来≥2，所以补充"） |
| 意外发现 | 无 | **系统提示词组装**（6 entity 共用，v2 没发现） |

v3 多发现了"系统提示词组装"——6 个 entity 都描述了各自向系统提示词注入内容的方式。这在 v2 中不会出现，因为 v2 的注意力被 hook 示例垄断。

### 最终版提示词

```markdown
## 对每个 Entity 做判断

一个 entity 可能同时回答多个独立的设计问题。
一个 entity 的"实现手段"本身可能就是另一个独立的设计维度。

互不包含测试：
把 A 问题的讨论全部合并进 B 问题的页面，会不会损失 Framework Builder 在 A 上的独立决策价值？
如果会损失，两者就是独立的问题空间，分别产出条目。

判断时注意：大部分 entity 只有一条。仅当 entity 同时承载了多个互不包含的设计关切时才产出多条。

## 全部映射完成后，执行聚合检查

回头看所有 entity 的正文，列出其中出现过的技术机制——不是 entity 的主问题，而是 entity 正文中用于实现其功能的机制（如某种钩子、某种回调、某种拦截方式、某种注册模式、某种注入方式等）。标注每个机制被哪些 entity 使用。

如果某个机制被 ≥2 个 entity 共用，且当前 problem-map 中没有独立条目覆盖该机制的设计维度，补充一条。
```

**0 个例子，0 个框架特定术语，0 个 API 名称。** 纯粹的程序性规则 + 机械阈值。

---

## 综合评估

| 维度 | 改进 A | 改进 B |
|------|--------|--------|
| 解决什么问题 | 当下 ingest 的跨关切遗漏 | 过去 ingest 的向后传播 |
| 有效性 | ✅ 直接修复根因 | ⚠️ 在特定仓库命名约定下有召回，通用性待验证 |
| 假阳性 | ✅ 无 | ❌ > 3 |
| 成本 | 低（Step 2 产物体积 +50%） | 低（~1000 token/次，稀有触发）|
| 可靠性 | 高（entity 页原文就有实现术语） | 中（依赖 LLM 抽象 + 字符串匹配的联合概率）|

**改进 A 是确定性的修复**——entity 页的正文中已经写了 `before_agent`、`wrap_model_call`，只需要 Step 2 不压制它们。

**改进 B 的最优策略**：降低假阳性标准，接受它作为 "候选信号" 而非 "精确诊断"：
- 命中 entity 后不直接确认，而是 `head -10` + read 首段做语义判断
- 假阳性的成本是一轮 LLM 确认（~500 token），远低于一次遗漏的修复成本
- 即使召回不完整（漏掉 filesystem-middleware），也比零召回（当前状态）强

### 改进 B 的定位修正

改进 B 不应被视为 "能补全所有遗漏"，而是 "能发现被通用命名约定（如 middleware 后缀）或同源 API 惯例（如 LangGraph AgentMiddleware）覆盖的那部分遗漏"。对于命名完全不同的框架，它仍然可能漏，但那是进一步改进的空间（比如让 LLM 读命中的 entity 正文做语义确认，而非仅 head -10）。

---

## 对 SKILL.md 改进的建议

### 改进 A（Step 2 提示词）：已实验验证，建议直接应用

当前修改后版本在 C1 实验中表现正确。需采纳的关键措辞：

1. "互不包含测试" 作为是否拆分的判定标准
2. "entity 中引用的技术机制本身可能是独立设计维度" —— 防止模型把 hook 当作"实现手段"压制
3. "不是硬套 2-3 条" —— 防止过度拆分

### 改进 B（Step 6 收尾）：需二次设计，当前实验结果暴露了以下问题

1. **机械 grep 的分词策略需要调整**：当前纯中文分词在英文 entity 正文命中率低。应从 body 中也提取术语（不仅是 concerns 分词）。

2. **LLM 搜索词的个数和多样性需要合理上限**：8 个词中 1 个有效，性价比不高。建议限制在 5 个以内，且要求说明每个词与已有实现的对应关系（防止无依据的泛化）。

3. **命中确认不应依赖 `head -10`**：problem 字段写的是 entity 的主问题。subagent-middleware 的 problem 是"子Agent委派"，从 head -10 看不出它与 hook 的关联。需要 read 一段正文。

4. **输出格式**：标记为 evolve-signals 而非自动写入，保持人的决策权。

---

## 最终结论

| 改进 | 推荐状态 | 理由 |
|------|---------|------|
| A: 解除一对一约束 | ✅ 建议应用 | C1 实验确认有效，零假阳性，提示词无需调整 |
| B: 向后传播 | ⚠️ 建议应用但降低预期 | C2 实验找到 5/5 地面真值但假阳性超标；`middleware` 命中是命名巧合；通用性因仓库命名约定差异而受限。定位为"候选信号"而非"精确诊断" |

两个改进互补：A 防止未来的遗漏，B 修复过去的遗漏。A 是确定性的，B 是概率性的。
