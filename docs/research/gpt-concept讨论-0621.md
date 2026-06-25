我觉得我们可以直接拿一个大家都熟悉的例子，这样最容易暴露问题。

就拿 **Attention Is All You Need** 这篇论文。

我不会按照知识图谱的思路，而是按照 **Karpathy 的 LLM Wiki** 的思路来分析一次。

---

# 第一步：Raw Source

输入就是论文。

```
Attention Is All You Need.pdf
```

---

# 第二步：Entity 提取

我认为这里的 Entity 应该都是**论文明确提到、可以唯一指代的对象**。

例如：

| Entity                       | 为什么是 Entity |
| ---------------------------- | ----------- |
| Transformer                  | 一个具体模型      |
| Encoder                      | 一个具体模块      |
| Decoder                      | 一个具体模块      |
| Self-Attention               | 一个具体机制      |
| Multi-Head Attention         | 一个具体机制      |
| Feed Forward Network         | 一个具体模块      |
| Positional Encoding          | 一个具体机制      |
| Residual Connection          | 一个具体结构      |
| Layer Normalization          | 一个具体技术      |
| Scaled Dot-Product Attention | 一个具体算法      |

注意。

这里全部都是：

> **论文里面真正存在的对象。**

如果换一篇论文，

```
FlashAttention
```

就会成为新的 Entity。

如果换成：

```
KV Cache
```

它也会成为新的 Entity。

所以我觉得：

> **Entity 是 source 里面可以直接定位的对象。**

这一点我觉得比较没有争议。

---

# 第三步：Concept

这里开始变得有意思了。

如果让 GPT 提取 Concept。

我觉得不会是：

```
Self Attention
```

因为：

Self Attention 已经是 Entity 了。

Concept 更可能是：

```
Attention replaces recurrence

Parallel sequence modeling

Context aggregation

Representation learning

Long-range dependency modeling
```

注意。

这些东西：

**论文里面没有一个章节叫这个。**

甚至很多词根本没出现。

但是：

它们代表了论文真正表达的思想。

例如：

Self Attention

只是一个东西。

但是：

```
Using attention instead of recurrence
```

这是一个思想。

这就是 Concept。

---

我举个最明显的。

论文里面有一句：

> Attention allows much more parallelization.

如果提 Entity：

```
Attention
```

如果提 Concept：

```
Parallel Computation
```

这是两个完全不同层级。

---

再举一个。

论文：

```
Multi-head Attention
```

Entity。

但是：

Concept：

```
Different representation subspaces
```

因为：

Multi-head 的真正目的不是 Multi-head。

而是：

> 从多个子空间学习表示。

这就是 Concept。

---

所以我目前觉得：

Entity 更像：

```
What exists.
```

Concept 更像：

```
Why it exists.
```

---

# 第四步：Wiki

我觉得这里才是最值得讨论的。

假设现在 wiki 已经存在。

里面已经有：

```
Transformer.md

Attention.md

Encoder.md

Sequence Modeling.md

Representation Learning.md

Parallelism.md
```

来了新论文。

LLM 会干什么？

不是创建：

```
Self Attention.md
```

因为：

已经有：

```
Attention.md
```

它应该更新：

```
Attention.md
```

增加：

```
Scaled Dot Product

Mask

Complexity

Advantages

Limitations
```

同时：

```
Parallelism.md
```

增加：

```
Transformer 证明 attention 可以完全并行
```

再更新：

```
Sequence Modeling.md
```

增加：

```
Transformer 不再依赖 RNN
```

注意。

这里就已经不是论文里面的内容了。

而是在：

**维护整个 Wiki。**

---

所以我现在突然发现了一个让我很惊讶的地方。

---

## Wiki Page 和 Entity 并不是一一对应的。

例如：

```
Attention.md
```

它里面可能包括：

```
Self Attention

Cross Attention

Linear Attention

FlashAttention

PagedAttention
```

全部都是 Entity。

但是：

```
Attention.md
```

是一个 Wiki。

---

再例如：

```
Parallelism.md
```

这里面可能出现：

```
Transformer

GPU

Tensor Parallel

Pipeline Parallel
```

这些都是 Entity。

但是：

```
Parallelism
```

不是任何一个 Entity。

它更像一个 Discussion Topic。

---

所以我开始怀疑：

**Wiki Page 本身其实有两种类型。**

一种：

```
Entity Page
```

例如：

```
Transformer.md

CUDA.md

PyTorch.md
```

一种：

```
Concept Page
```

例如：

```
Parallelism.md

Scaling.md

Representation Learning.md

In-context Learning.md
```

---

# 那我突然想到一个问题。

也是我读完 Gist 后最大的疑问。

Karpathy 写的是：

> update entity pages
>
> update concept pages

但是：

他从来没说：

**怎么判断一个东西应该成为 Concept Page。**

这正是我们最近卡住的地方。

---

## 我现在反而觉得，我们之前可能一直在提错东西。

例如你刚刚说：

> attention、FFN、KV Cache

我认为：

这些**全部都是 Entity。**

因为：

它们都有明确的定义。

都有唯一指代。

都有具体实现。

---

真正让我觉得是 Concept 的反而像：

```
Efficient Inference

Context Compression

Memory Optimization

Representation Learning

Scaling

Sparse Computation
```

这些东西。

它们没有明确边界。

它们更像：

> **一种持续讨论的话题。**

---

### 但是，到这里我还有一个疑问，而且我觉得这可能就是整个设计最关键的地方。

如果一个 Entity（比如 `KV Cache`）随着知识积累越来越丰富，它本身也会演化成一篇很长的 Wiki 页面。那么 **`KV Cache.md` 到底应该算 Entity Page，还是已经算一个 Concept Page？**

也就是说，**Karpathy 在 Gist 里用 "Entity Page" 和 "Concept Page" 来分类页面，还是用 "Entity" 和 "Concept" 来分类知识？**

这是两个完全不同的问题，而 Gist 并没有说明。

我现在倾向于认为，**真正稳定的一级对象不是 Entity 或 Concept，而是 Page。Entity 和 Concept 更像是 Page 的两种语义标签。**

如果这个判断是对的，那我们后面的整个 ontology 设计都会简单很多：我们首先决定**哪些东西值得拥有一个长期维护的页面**，然后再给页面打上 `entity`、`concept` 等标签，而不是一开始就试图先定义什么是 Concept。这个方向，我觉得值得我们下一步继续验证。


你指出的问题是对的，而且我觉得是我们讨论了这么久第一次真正需要把概念掰开。

我确实把 **Topic、Concept、Page** 混在一起了，这是不严谨的。

我重新梳理了一遍 Karpathy 的 Gist，我现在反而觉得**我们应该先把这几个东西彻底解耦**，否则后面的设计永远会绕。

---

## 我先说一个我现在越来越确定的观点

**Karpathy 的 Gist 里面，其实只明确存在两个对象。**

```
Raw Source
      │
      ▼
Wiki Page
```

然后他说：

> update entity pages

> update concept pages

这里说明：

```
Wiki Page
    ├── Entity Page
    └── Concept Page
```

也就是说，**Entity 和 Concept 是 Page 的分类。**

但是！！

这里完全没有出现：

```
Topic
```

Topic 是我们自己后来引入的词。

所以我们不能再拿 Topic 去解释 Concept。

否则就循环定义了。

---

# 那我现在重新定义一下（不是结论，而是我认为值得验证的假设）

## 第一层：Entity

这个我觉得最清楚。

Entity：

> 可以在 Source 中定位到的对象。

例如：

```
Transformer

Encoder

Decoder

KV Cache

FlashAttention

PyTorch
```

特点：

* 有名字
* 有边界
* 可以唯一引用
* 可以跨文章链接

所以：

Entity Page

就是：

```
KV Cache.md
```

没有问题。

---

## 第二层：Concept

这里才是真正困难。

我现在觉得，我们之前一直在犯一个错误。

一直在问：

> 「Concept 是什么？」

但是应该问：

> **「Concept Page 里面应该写什么？」**

这是两个完全不同的问题。

举个例子。

Entity：

```
KV Cache
```

如果我打开：

```
KV Cache.md
```

里面会写：

* 定义
* 工作原理
* 不同实现
* FlashAttention 的关系

这是一个 Object。

---

但是：

Concept Page：

例如：

```
Memory Optimization.md
```

里面不会写：

Memory Optimization 是什么。

而会写：

```
有哪些方法？

KV Cache

PagedAttention

FlashAttention

Quantization

Speculative Decoding
```

有没有发现？

Concept Page 其实是在组织：

> **多个 Entity。**

这一点我觉得特别重要。

---

所以：

Entity：

```
Object
```

Concept：

```
Organizing Principle
```

或者说：

```
Discussion Axis
```

---

例如：

Transformer。

Entity：

```
Self Attention
```

Concept：

```
Sequence Modeling
```

因为：

Sequence Modeling

下面会讨论：

```
RNN

LSTM

CNN

Transformer
```

它不是一个 Object。

而是：

一个讨论维度。

---

## 我觉得这里出现了一个很大的区别。

Entity Page：

回答：

> 它是什么？

Concept Page：

回答：

> 围绕一个问题，有哪些方案？

例如：

```
Memory Optimization
```

下面：

```
KV Cache

Compression

Quantization

Offloading
```

所以：

Concept 本身不是：

```
Memory Optimization
```

而是：

> **"Memory Optimization" 这个问题空间。**

---

# 那 Concept 是怎么来的？

这里就是你问的重点。

也是我现在觉得不能直接提取的原因。

我现在越来越觉得：

Concept **不是从文章直接抽出来的。**

而是：

**Entity 聚合出来的。**

举个例子。

论文：

```
FlashAttention
```

Entity：

```
FlashAttention

HBM

SRAM

Tile
```

这些都很好提。

但是：

Concept：

```
Memory Optimization
```

不是论文写出来的。

而是：

LLM发现：

```
这些Entity

都在解决：

Memory Bottleneck
```

于是：

形成：

```
Memory Optimization
```

所以：

我现在觉得：

```
Source

↓

Entity

↓

Entity之间共同解决的问题

↓

Concept
```

---

## 如果这个成立。

那么就回答了你的问题。

你刚才问：

> Entity 和 Concept 可以并行提取吗？

**我现在反而认为：不能。**

因为：

Concept 依赖于：

Entity。

Concept 是：

**Entity 的抽象。**

---

所以流程更可能应该是：

```
Source

↓

Entity Extraction

↓

Entity Normalization

↓

Entity Grouping

↓

Concept Formation

↓

Update Concept Page
```

而不是：

```
Source

↓

Entity

↓

Concept

并行
```

---

# 这也是为什么我现在开始怀疑，我们之前一直卡住。

因为：

我们一直让 LLM：

```
Extract Concept
```

但是：

它其实应该先完成：

```
Entity Layer
```

然后：

看这些 Entity：

```
共同围绕什么问题？

共同体现什么设计思想？

共同属于哪个讨论维度？
```

Concept 才自然出现。

---

## 但是，我现在还有一个地方没有想通，而且我觉得这里可能就是整个设计最关键的地方。

如果 Concept 是 **Entity 聚合出来的讨论维度**，那么它到底应该满足什么标准？

例如：

```
KV Cache

FlashAttention
```

可以抽象成：

```
Memory Optimization
```

也可以抽象成：

```
Inference Optimization
```

甚至：

```
Efficient LLM Serving
```

它们都没错。

所以，**Concept 的难点其实不是抽象，而是"抽象到哪一层"。**

而我重新读 Karpathy 的 Gist 后，反而觉得他没有试图解决这个问题。他假设你已经有了自己的 Schema，由 Schema 决定你的 Concept 粒度，然后 LLM 负责维护它。

**因此，我觉得我们真正应该研究的，不是"怎么提 Concept"，而是"Concept 的形成规则（Concept Formation Rule）"。**只要这套规则稳定，Concept 的提取自然就稳定了；否则，无论换什么 Prompt，它都会一直漂移。这也是我现在认为整个系统里最值得投入精力设计的一层。



我觉得这次你的问题提得非常好，而且我想先明确一点：

**我现在并不是不知道方案，而是我觉得我们之前一直在优化错对象。**

真正值得推理的不是：

> **Concept 怎么提？**

而是：

> **什么样的东西才有资格成为 Concept？**

这两个问题差别非常大。

---

## 我先引用一下工业界真正成熟的几类知识组织方式

其实过去几十年，这个问题已经有很多不同答案了。

### 第一类：Ontology（知识图谱）

Concept 是 Domain 定义好的。

例如医学：

```
Disease
Drug
Protein
Gene
```

Concept 根本不用提。

因为专家已经定义好了。

优点：

* 极其稳定

缺点：

* 无法迁移到新领域。

所以我们基本排除。

---

### 第二类：Wikipedia

Wikipedia 很有意思。

它没有 ontology。

它也没有人规定：

```
什么叫 Concept
```

但是它有一个原则：

> **Every page should represent one notable topic.**

注意。

这里不是：

Object。

也不是：

Entity。

而是：

Topic。

但是：

Wikipedia 为什么还能稳定？

因为：

**社区决定。**

如果：

```
Memory Optimization
```

已经有页面。

以后大家不会再创建：

```
Memory Efficient Inference
```

而会：

Merge。

所以：

Wikipedia 的稳定性：

来自：

**长期演化。**

不是：

第一次抽取。

---

### 第三类：Software Architecture

例如：

DDD（Domain Driven Design）。

这里有：

Entity

Value Object

Aggregate

Domain Service

这些其实都是：

人为定义。

不是模型抽。

---

### 第四类：Obsidian PKM

Karpathy 基本就是这一派。

特点：

没有固定 ontology。

允许不断长。

靠：

Link

Merge

Evolution。

---

所以。

工业界其实没有人解决：

> 如何稳定提 Concept。

他们都是：

**允许 Concept 演化。**

---

## 但是！

我觉得这里有一个工业界没有回答，而我们必须回答的问题。

因为我们不是做：

Personal Wiki。

我们是在做：

**自动构建 Wiki。**

所以：

Concept 如果一直变。

整个系统就炸了。

所以：

必须稳定。

---

## 那稳定从哪里来？

这里我反而想到另外一个领域。

不是知识图谱。

而是：

**Topic Modeling。**

例如：

LDA。

BERTopic。

它们一直都有一个经典问题：

```
Topic

不是唯一的。
```

为什么？

因为：

Topic：

不是数据里的东西。

而是：

解释。

举例：

论文：

```
FlashAttention

HBM

SRAM

Tile
```

Topic：

可以叫：

```
Memory Optimization
```

也可以叫：

```
IO Awareness
```

都合理。

所以：

Topic：

天然：

不是唯一。

这是统计学习几十年的共识。

---

## 那工业界怎么提高稳定性？

这里就来了。

他们基本都会做：

> **限制解释空间。**

例如：

不是：

```
自由命名 Topic
```

而是：

先得到：

```
关键词集合
```

例如：

```
FlashAttention

HBM

SRAM

Memory

Bandwidth
```

然后：

再：

命名。

你发现没有？

这里其实有两层。

```
Entity

↓

Keyword Cluster

↓

Label
```

其中：

真正稳定的是：

```
Keyword Cluster
```

不是：

Label。

---

## 我觉得这里突然给了我一个启发。

我们一直把：

Concept

理解成：

```
Memory Optimization
```

其实：

有没有可能：

真正稳定的不是：

Concept Name。

而是：

**Entity Cluster。**

举例：

例如：

```
FlashAttention

PagedAttention

KV Cache

Quantization
```

这是：

一个：

Cluster。

这个：

Cluster：

几乎不会变。

但是：

名字：

可以叫：

```
Memory Optimization
```

也可以：

```
Efficient Inference
```

是不是很像？

---

## 所以我现在突然有一个新的推理。

Concept：

应该拆成：

```
Concept
    ├── Semantic Core
    └── Human Label
```

其中：

Semantic Core：

其实就是：

```
Entity Set

+

Shared Relation
```

例如：

```
Entities

FlashAttention

KV Cache

PagedAttention

↓

共同解决：

Memory Bottleneck
```

这个：

几乎稳定。

然后：

Label：

可以：

```
Memory Optimization

Inference Memory

Attention Optimization
```

这些：

只是：

Presentation。

---

## 这也是为什么我觉得，我们一直纠结"名字"。

其实应该纠结：

> **Concept 的 Identity。**

Identity：

是什么？

我觉得：

不是：

```
Memory Optimization
```

而是：

```
Entity Graph
```

例如：

```
FlashAttention

KV Cache

PagedAttention

↓

共同作用：

减少Memory IO
```

这：

就是：

Concept。

名字：

以后再生成。

---

## 但是，我还想再往前推一步，我觉得这是最值得验证的假设。

你一直在说：

> **entity 是稳定的。**

我现在越来越同意。

那如果 entity 稳定，那么 Concept 是否也可以稳定？

**我的答案是：可以，但前提不是让 LLM "总结主题"，而是让 LLM "解释 Entity 之间共同解决的问题"。**

这两种 Prompt 看起来很像，但实际上完全不同：

**Prompt A（不稳定）：**

> 请提取这篇文章的 Concept。

模型会自由决定抽象层级，所以今天叫 *Memory Optimization*，明天叫 *Efficient Inference*。

**Prompt B（我认为更稳定）：**

> 对每一组强相关的 Entity，回答：
>
> 1. 它们共同试图解决什么问题？
> 2. 它们采用了哪些不同策略？
> 3. 它们之间形成了哪一个值得长期维护的讨论维度？

这里，Concept 不再是一个自由生成的名词，而是 **Entity Group + Shared Problem + Comparative Dimension** 的产物。

这其实和很多工程知识库、架构文档、甚至论文 Survey 的组织方式非常接近。Survey 很少直接发明一个 Concept，而是先确定**一个问题空间（Problem Space）**，再在这个空间下组织各种方法。

所以，如果让我现在重新设计整个系统，我不会再把 Concept 当成"摘要"或"主题"，而会把它定义为：

> **一个稳定的问题空间（Problem Space），用于组织多个 Entity 的比较、联系和演化。**

我觉得这个定义，比我们之前所有讨论都更接近一种可以真正实现、也更容易获得稳定性的知识单元。


我觉得你这一下问到了**真正的算法问题**。

而且我的答案其实是：

> **不是限制 Entity 数量，而是限制 Concept 的形成原则。**

这是两个完全不同的约束。

我慢慢推导一下，因为这里我觉得已经开始接近一个真正可以实现的算法了。

---

## 为什么聚类不稳定？

假设现在有 8 个 Entity。

```text
KV Cache
PagedAttention
FlashAttention
Speculative Decoding
Quantization
Tensor Parallel
Pipeline Parallel
MoE
```

LLM 完全可以聚成很多种。

例如

### 聚法1

```text
Memory Optimization
    KV Cache
    FlashAttention
    PagedAttention

Serving Optimization
    Quantization
    Speculative Decoding

Distributed Training
    Tensor Parallel
    Pipeline Parallel

Sparse Computation
    MoE
```

合理。

---

也可以

### 聚法2

```text
Inference Optimization
    KV Cache
    FlashAttention
    PagedAttention
    Quantization
    Speculative Decoding

Training
    Tensor Parallel
    Pipeline Parallel

Architecture
    MoE
```

也合理。

---

甚至

### 聚法3

```text
LLM System
    所有Entity
```

也不能说错。

所以你会发现：

> **聚类的不稳定，本质不是数量问题，而是"优化目标"没有定义。**

---

## 限制数量有没有帮助？

其实只有一点帮助。

例如规定：

```text
每个Concept最多5个Entity
```

模型可能变成

```text
Memory Optimization
    5个

Serving
    3个
```

但是下一次仍然可能

```text
Inference
    5个

Efficiency
    3个
```

没有解决根本问题。

原因很简单。

**聚类不是 k-means。**

Concept 根本不是：

> 距离最近。

而是：

> 有没有共同讨论价值。

---

## 我觉得真正应该限制的是：

不是 Size。

而是：

## 一个 Concept 只能回答一个 Question。

这是我今天最大的一个想法。

例如

Memory Optimization

其实回答的是

```text
如何减少Memory Bottleneck？
```

---

Parallelism

回答的是

```text
如何提升计算吞吐？
```

---

Context Management

回答的是

```text
如何管理长上下文？
```

---

有没有发现？

这里不是

```text
Entity
```

在聚。

而是

```text
Question
```

在聚。

---

所以我越来越觉得：

Concept 根本不是：

```text
Entity Cluster
```

而是：

```text
Question Space
```

Entity

只是：

Question 的 Solution。

例如

```text
Question：

如何降低Attention的Memory？

↓

Solution：

KV Cache

FlashAttention

PagedAttention
```

Concept：

就是：

```text
Memory Optimization
```

---

## 这一下其实就稳定很多。

因为：

Question

比

Topic

稳定。

例如

今天：

```text
FlashAttention
```

出来。

明天：

```text
FlashAttention2
```

出来。

后天：

```text
FlashAttention3
```

出来。

Question

没有变。

还是：

```text
如何降低Memory？
```

所以：

Concept

不用新增。

只是：

增加Entity。

---

## 我甚至觉得可以把 Concept 定义成：

> 一个长期存在的问题空间（Problem Space）。

而不是：

Topic。

为什么？

因为：

Problem

天然具有：

### 可扩展

```text
Memory Optimization

↓

加入新的Entity
```

---

### 可比较

```text
不同方案

优缺点
```

---

### 可演化

```text
以前：

KV Cache

后来：

PagedAttention

后来：

FlashAttention
```

全部都是：

回答：

一个问题。

---

## 那怎么保证 Concept 稳定？

我现在觉得应该限制的不是：

```text
Entity 数量
```

而是：

**一个 Concept 必须满足固定的 Schema。**

例如：

每个 Concept 必须有：

```text
Problem

↓

Solutions(Entity)

↓

Trade-offs

↓

Evolution
```

如果：

一个新的聚类。

填不满这个Schema。

例如：

```text
FlashAttention
Tensor Parallel
MoE
```

问：

共同Problem？

答不上来。

那说明：

不是一个Concept。

---

反过来：

```text
KV Cache
FlashAttention
PagedAttention
```

共同Problem：

```text
Attention Memory Bottleneck
```

共同Tradeoff：

```text
Memory

Latency

Complexity
```

共同Evolution：

```text
KV Cache

↓

PagedAttention

↓

FlashAttention
```

一下子：

整个Concept

就成立了。

---

## 我觉得这里开始出现一个很有意思的方向，而且它和我们前面讨论的 ontology 已经不一样了。

我们之前一直在问：

> **Concept 是什么？**

但现在我觉得应该问的是：

> **什么样的一组 Entity，值得拥有一篇独立的 Wiki 页面？**

如果答案只是"它们语义相近"，那聚类永远不稳定。

但如果答案变成：

> **它们共同回答了一个长期存在的问题，并且这个问题下存在多个方案、多个权衡、持续演化的历史。**

那么 Concept 的边界就会清晰得多，而且稳定性也会大幅提升。

所以，我现在甚至不想把 Concept 看成"概念"了，而更愿意把它看成**一个可持续维护的问题空间（Problem Space）**。这和 Survey Paper 的组织方式其实非常接近：Survey 很少围绕名词组织，而是围绕**研究问题（Research Question）**组织，每个章节下面再比较各种方法（Entity）。我觉得这种组织方式，比简单做 Entity 聚类更有希望得到稳定、可维护的 Concept。


哈哈，这个问题问得很好，而且我觉得它已经开始逼近整个系统的本质了。

我的第一反应其实是：

> **不能。至少不是所有 Entity 都能。**

而且，我觉得这是一个可以证明的结论，而不是我的猜测。

我们做几个实验。

---

# 实验一：Transformer

Entity：

```text
Transformer
```

请问它可以抽出哪些 Problem Space？

可以想到：

```text
Sequence Modeling
```

也可以：

```text
Neural Network Architectures
```

也可以：

```text
Foundation Models
```

也可以：

```text
Representation Learning
```

也可以：

```text
Long-range Dependency Modeling
```

你发现了吗？

**一个 Entity 可以属于很多 Problem Space。**

不是唯一的。

---

## 为什么？

因为：

Transformer

本身不是一个问题。

它是：

一个 Solution。

所以：

它解决了很多问题。

---

# 实验二：KV Cache

Entity：

```text
KV Cache
```

可以想到：

```text
Long Context
```

也可以：

```text
Inference Optimization
```

也可以：

```text
Memory Optimization
```

也可以：

```text
Attention Computation
```

也可以：

```text
LLM Serving
```

全部合理。

所以：

> **Entity → Problem**

不是唯一映射。

---

# 实验三：FlashAttention

更明显。

可以属于：

```text
Attention Optimization
```

也可以：

```text
GPU Optimization
```

也可以：

```text
Memory Optimization
```

也可以：

```text
IO-aware Algorithms
```

也可以：

```text
Efficient LLM Inference
```

---

所以：

## 一个 Entity

不能稳定推出

Problem。

---

## 那多个 Entity 呢？

假设：

```text
KV Cache

PagedAttention

FlashAttention
```

这时候：

大家都会觉得：

共同：

```text
Attention Efficiency
```

或者：

```text
Memory Optimization
```

是不是开始收敛一点了？

但是。

还是：

不是唯一。

---

## 再加几个。

```text
KV Cache

PagedAttention

FlashAttention

Attention Sinks

Context Compression
```

开始越来越明显。

大家都会觉得：

```text
Long Context

Context Management
```

---

所以：

**Problem Space 是由一组 Entity 决定的。**

不是：

一个。

---

# 我觉得这里其实很像机器学习。

一个样本。

不能决定：

Cluster。

很多样本。

才能形成：

Cluster。

---

所以：

如果按照这个思路。

Concept

其实不是：

```text
Entity

↓

Concept
```

而是：

```text
Entity Set

↓

Concept
```

---

## 但是！！

我觉得这里出现了一个更大的问题。

也是我刚刚想到的。

---

假设：

Entity：

```text
KV Cache
```

我们说：

属于：

```text
Memory Optimization
```

是不是。

那：

Memory Optimization

里面：

还有：

```text
Quantization
```

等等。

但是：

Quantization

其实：

又不仅属于：

Memory。

它还属于：

```text
Model Compression
```

是不是？

---

所以：

Entity

不是：

属于一个 Concept。

而是：

属于：

多个。

这和：

Wikipedia

完全一致。

例如：

```text
Transformer
```

Wikipedia：

不会：

属于：

一个分类。

而是：

```text
Machine Learning

Deep Learning

Artificial Intelligence

Natural Language Processing
```

全部属于。

---

## 所以。

如果我们把：

Concept

理解成：

Cluster。

我觉得：

一定失败。

因为：

Cluster：

默认：

一个东西：

属于：

一个。

但是：

知识：

不是这样。

知识：

天然：

多标签。

---

# 我觉得这里开始有点像 Knowledge Graph 了。

例如：

```text
Transformer

── solves ──>

Sequence Modeling

Transformer

── belongs_to ──>

Deep Learning

Transformer

── enables ──>

Foundation Models
```

其实：

不是：

一个。

而是：

很多。

---

## 所以我现在反而开始怀疑：

我们是不是一直把 Concept 想错了。

Concept

有没有可能：

根本不是：

Entity 的聚类。

而是：

Entity Network

里面：

某一种：

Pattern。

举例。

```
Memory Optimization

KV Cache

FlashAttention

PagedAttention

↓

全部：

optimize

Attention Memory
```

这里真正重要的是：

不是：

三个Entity。

而是：

```text
共同关系：

optimize
```

---

## 我觉得这里有一个特别值得注意的现象。

你有没有发现：

Survey Paper

其实根本不是：

先列Concept。

而是：

先列：

Research Question。

例如：

```text
How to reduce inference latency?

How to support long context?

How to reduce memory footprint?
```

然后：

下面：

才是：

Method。

是不是？

所以：

Survey：

天然就是：

```text
Question

↓

Methods
```

不是：

```text
Methods

↓

Question
```

---

# 这让我产生了一个新的怀疑，而且我觉得这个怀疑值得我们认真验证。

我们一直假设：

> **Concept 是由 Entity 提取出来的。**

但有没有可能方向正好相反？

真正稳定的其实不是 Entity 推导 Concept，而是**领域本身存在一组长期稳定的"问题空间（Problem Spaces）"**，新的 Entity 不断被放进这些问题空间里。

例如在 LLM 领域，这些问题空间可能一直都是：

* 长上下文（Long Context）
* 推理效率（Inference Efficiency）
* 训练效率（Training Efficiency）
* 模型压缩（Model Compression）
* 对齐（Alignment）
* Agent（Autonomous Agents）

这些问题五年前存在，五年后也存在。

而 `KV Cache`、`FlashAttention`、`Speculative Decoding`、`PagedAttention` 只是不断出现的新方案。

**如果这个方向是对的，那么整个系统就会发生一个根本性的变化：**

* Entity：从文章里提取（相对客观）。
* Problem Space（Concept）：不是每篇文章都重新提，而是整个 Wiki 持续维护的一组长期演化的问题空间。
* 新文章的任务不是"生成 Concept"，而是"判断这些 Entity 应该更新哪些已有的问题空间，以及是否真的出现了一个新的问题空间"。

我现在反而觉得，这个方向比"每篇文章都提 Concept"更符合 Karpathy 的 Gist，因为 Gist 一直强调的是 **update concept pages**，而不是 **generate concept pages**。这意味着，**Concept Page 更像 Wiki 中长期存在的骨架，而不是每次阅读时即时生成的摘要。**

不过，这里还有最后一个关键问题没有解决：**第一批 Concept Page 是怎么来的？** 我觉得这才是真正值得我们下一步推导的问题。因为如果第一批构建得合理，后面可能就主要是维护；如果第一批不稳定，整个 Wiki 后续都会漂移。

我觉得你这次提出的假设，比我们之前所有讨论都更接近一个**可以推导、可以验证**的理论了。

而且我不会直接赞同，因为这里面其实有两个假设，它们的可靠性是不一样的。

我把它拆开分析。

---

# 我先重述一下你的假设（避免理解错）

我理解你的意思是：

```
Document
      │
      ▼
Entity（稳定）
      │
      ▼
Entity 的功能（Function）
      │
      ▼
Function 决定 Problem Space
      │
      ▼
Problem Space 之间形成 Concept Graph
```

这里最关键的一句话其实是：

> **Problem Space 是由 Entity 的功能决定的。**

如果这句话成立，那么：

Concept 就不是 LLM 发明出来的。

而是：

Entity 的一种高层组织。

---

我觉得这里需要讨论三个命题。

---

# 命题一：Entity 是否稳定？

这个我基本认为成立。

例如

```
FlashAttention
```

它是什么？

基本不会变。

```
KV Cache
```

它是什么？

基本不会变。

```
MoE
```

也不会变。

工业界这么多年其实也是这样。

Entity 是最好抽的。

---

所以：

这一层：

我认为

> 成立。

---

# 命题二：Entity 的 Function 是否稳定？

这里开始有意思了。

举例。

```
KV Cache
```

Function：

你会怎么写？

可能：

```
缓存 Key/Value
```

但是：

真正一点：

```
避免重复Attention计算
```

再抽象一点：

```
降低推理成本
```

再抽象一点：

```
提高Inference Efficiency
```

再抽象一点：

```
提高System Throughput
```

有没有发现？

Function

开始漂了。

为什么？

因为：

Function

其实也有层级。

例如：

Transformer。

Function：

```
进行序列建模
```

还是：

```
学习Token之间关系
```

还是：

```
作为Foundation Model Backbone
```

全部合理。

所以：

Function

**不是唯一。**

---

所以。

这里我要反驳一下你的假设。

> Function 本身并不像 Entity 那么稳定。

它：

仍然存在：

抽象层级。

---

# 命题三：Problem Space 是否稳定？

这里我反而觉得：

可能比 Function 更稳定。

举例。

KV Cache。

你可以写很多 Function。

但是：

为什么发明 KV Cache？

回答：

```
降低Attention推理开销。
```

这个：

几乎不会变。

FlashAttention。

为什么？

```
减少Memory IO。
```

PagedAttention。

为什么？

```
支持更长Context。
```

然后：

你会发现：

他们其实共同回答：

```
如何提高Inference Efficiency？
```

所以：

Problem

开始稳定了。

---

这里其实让我想到一个经典理论。

---

# Simon 的 Means-End Analysis

AI 里面很经典。

一个算法。

不是：

因为它是什么。

而是：

因为它解决：

什么问题。

例如：

A*

解决：

```
最优路径。
```

不是：

Priority Queue。

Priority Queue

只是实现。

---

所以。

如果：

Problem

是真正的一层。

那：

Entity

其实就是：

Solution。

---

所以：

你的图：

可能要改一下。

不是：

```
Entity

↓

Function

↓

Problem
```

而是：

```
Problem

↓

Solution(Entity)
```

为什么？

因为：

Problem

先存在。

Entity

后来出现。

例如：

```
Long Context
```

一直存在。

后来：

KV Cache。

后来：

FlashAttention。

后来：

PagedAttention。

所以：

Entity

其实是：

Problem

下面不断新增的 Solution。

---

# 但是，我也要反驳我自己。

因为这里有一个最大的漏洞。

举个例子。

```
Transformer
```

它解决：

什么问题？

有人说：

```
Sequence Modeling
```

有人说：

```
Parallel Training
```

有人说：

```
Long Dependency
```

有人说：

```
Representation Learning
```

全部成立。

为什么？

因为：

Transformer

改变了很多 Problem。

所以：

Problem

不是唯一。

---

这说明：

> **一个 Entity 可以对应多个 Problem Space。**

这点我觉得几乎可以确定。

---

# 所以，我觉得真正的问题来了。

不是：

```
Entity

↓

Problem
```

而是：

```
Entity

↓

Problem Graph
```

例如：

Transformer：

```
Sequence Modeling

Representation Learning

Parallel Training

Scaling

Foundation Models
```

全部连接。

---

所以。

Concept

其实不是：

一个节点。

而是：

Graph。

---

# 这里我反而想到另外一个方向。

也是我今天最大的一个新想法。

我们一直假设：

```
Entity

↓

Concept
```

但是。

有没有可能。

Concept

根本不是：

Node。

而是：

Edge。

举例。

```
FlashAttention

── solves ──>

Memory Bottleneck
```

```
KV Cache

── optimizes ──>

Attention Computation
```

```
Transformer

── replaces ──>

RNN
```

你发现没有。

真正稳定的是：

这些：

**关系。**

不是：

Concept。

为什么知识图谱能稳定？

不是：

Entity。

也不是：

Ontology。

而是：

Relation。

---

所以。

如果：

最后我们的Wiki：

不是：

```
Concept

↓

Entity
```

而是：

```
Entity

── solves ──>

Problem

Entity

── improves ──>

Capability

Entity

── replaces ──>

Entity
```

那：

Concept

甚至可以不用定义。

Problem

自己就长出来了。

---

# 我最后说说，我现在站在哪一边。

其实我没有完全站在你的假设，也没有完全反对。

我觉得可以把这个问题变成两个相互竞争的理论，然后去验证，而不是继续靠直觉讨论。

---

## 理论 A（你的方向）

> **Problem Space 是知识库中的一级对象。**

流程：

```
Document
    ↓
Entity
    ↓
Entity → Problem（多对多）
    ↓
Problem 聚合成长期维护的 Concept Page
```

预测：

* Problem 的集合会比较稳定。
* 新论文主要新增 Entity，很少新增 Problem。
* Concept 的增长速度会越来越慢。

---

## 理论 B（我目前更倾向的方向）

我觉得一级对象甚至不是 Problem，而是 **Relation**。

也就是说，知识库真正稳定的不是"有哪些问题"，而是"Entity 与 Entity、Entity 与 Problem 之间有哪些稳定关系"。

例如：

```
FlashAttention
    solves → Memory Bottleneck

KV Cache
    reduces → Recomputing

Transformer
    replaces → RNN

MoE
    trades_off → Compute vs Memory
```

在这个图里，**Problem 只是某类节点**，而不是唯一的组织中心。

为什么我更倾向于 B？因为它解释了一个现象：**Transformer 同时属于多个 Problem Space**。如果 Concept 是唯一父节点，它就会很别扭；但如果它只是图中的一个节点，拥有很多条不同类型的边，一切就自然了。

---

### 不过，我认为你的理论有一个我非常认同、而且可能是整个设计里最重要的观点：

> **不要从文档直接提 Concept，而是从更稳定的东西演化出 Concept。**

这一点我现在基本赞同。

我们唯一还有分歧的是：那个"更稳定的东西"到底是 **Problem Space**，还是更底层的 **Relation Graph**。

而我觉得，这已经不是靠讨论能决定的了。我们完全可以设计一个实验：拿 100 篇 LLM 论文，分别构建 **Problem Graph** 和 **Relation Graph**，观察一年之后哪一种新增节点更少、复用率更高、人工修改更少。**哪个更稳定，它就更接近知识库真正的骨架。**

我觉得，这已经从"定义 Concept"变成了一个可以验证的研究问题。
