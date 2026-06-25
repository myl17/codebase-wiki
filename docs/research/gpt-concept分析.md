我换个更具体的例子。

我觉得你现在的思路大概是：

```text
仓库A -> 提取Entity
仓库B -> 提取Entity
仓库C -> 提取Entity

然后：
Entity Consolidation
```

比如：

```text
LangGraph:
  StateGraph
  Node
  Checkpointer

Claude Code:
  Todo
  Tool
  Workspace

DeepAgents:
  TaskTree
  Planner
  Executor
```

然后你发现：

```text
StateGraph
Todo
TaskTree
```

怎么合并？

根本没法合并。

因为它们名字不同。

---

但更深层的问题是：

**它们其实也不是同一种东西。**

例如：

```text
StateGraph
```

是运行时控制结构。

---

```text
Todo
```

是任务组织结构。

---

```text
Workspace
```

是状态存储结构。

---

它们甚至不在一个维度上。

所以当然无法统一。

---

# 问题出在哪？

因为你把：

```text
代码里的抽象
```

当成了：

```text
知识库里的抽象
```

但这两个层次其实不一样。

---

举个现实世界例子。

假设你研究交通工具。

你收集到：

```text
Tesla Model Y
Toyota Corolla
Boeing 737
高铁
```

然后你说：

> 我想把这些 Entity 统一起来

当然很困难。

因为：

```text
Tesla Model Y
Toyota Corolla
```

是具体车型。

---

```text
Boeing 737
```

是飞机型号。

---

```text
高铁
```

甚至不是型号。

---

但如果先引入一个更高层概念：

```text
Transportation Mode
```

那么：

```text
Car:
  Tesla Model Y
  Toyota Corolla

Aircraft:
  Boeing 737

Rail:
  高铁
```

突然就有组织了。

---

# Codebase Wiki 里也是一样

你抽出来的是：

```text
StateGraph
TaskTree
Todo
Workspace
Checkpointer
```

这些其实都是：

```text
仓库作者发明的名字
```

而不是通用概念。

---

例如：

LangGraph 作者创造了：

```text
StateGraph
```

---

Claude Code 作者创造了：

```text
Todo
```

---

DeepAgents 作者创造了：

```text
TaskTree
```

---

但你真正关心的是：

> 这些东西在系统里扮演什么角色？

---

这时候就出现了 Concept。

例如：

### Concept: Task Organization

用于组织未来要执行的工作。

不同仓库实现：

```text
Claude Code:
  Todo

DeepAgents:
  TaskTree
```

---

### Concept: Execution Control

用于控制执行顺序。

不同仓库实现：

```text
LangGraph:
  StateGraph

OpenHands:
  State Machine

Claude Code:
  Agent Loop
```

---

### Concept: State Storage

用于保存运行状态。

不同仓库实现：

```text
Claude Code:
  Workspace

LangGraph:
  Checkpointer

Mem0:
  Memory Store
```

---

注意这里发生了什么。

你比较的对象从：

```text
Todo vs StateGraph
```

变成：

```text
Task Organization:
    Todo
    TaskTree

Execution Control:
    StateGraph
    Agent Loop
```

这时候比较才有意义。

---

# 为什么 Karpathy 的 Wiki 能工作

因为 Karpathy 实际上一直在做这个事情。

例如研究 LLM。

如果直接收集 Entity：

```text
Transformer
Llama
GPT
MoE
KV Cache
RoPE
```

会越来越乱。

---

于是他会隐式地形成 Concept。

例如：

```text
Model Architecture
```

下面有：

```text
Transformer
MoE
```

---

```text
Position Encoding
```

下面有：

```text
RoPE
ALiBi
```

---

```text
Inference Optimization
```

下面有：

```text
KV Cache
Speculative Decoding
```

---

这样知识才能不断积累。

---

# 对你的项目意味着什么

我觉得你的系统未来应该有两套东西。

## 第一层：Repo Entity

保留原始抽取结果。

例如：

```yaml
repo: LangGraph

entities:
  - StateGraph
  - Node
  - Checkpointer
```

这是事实层。

---

## 第二层：Canonical Concept

这是知识层。

例如：

```yaml
concept: Execution Control

implementations:

  LangGraph:
    StateGraph

  Claude Code:
    Agent Loop

  OpenHands:
    State Machine
```

---

再例如：

```yaml
concept: Task Organization

implementations:

  Claude Code:
    Todo

  DeepAgents:
    TaskTree
```

---

这时候你会发现一个很有意思的现象：

用户问的很多问题其实都是 Concept 问题。

例如：

> Claude Code 和 DeepAgents 最大区别是什么？

本质上是在问：

```text
Task Organization
Execution Control
State Management
```

这些 Concept 的差异。

而不是在问：

```text
Todo
TaskTree
StateGraph
```

这些具体名字。

---

所以我会把那句话换一种表达：

> 不要试图让所有仓库使用同一套 Entity 名字，而要试图让所有 Entity 都能映射到同一套 Concept 体系。

因为 Entity 是仓库作者发明的。

Concept 才是你知识库应该维护的。

而且从你描述的问题来看，我怀疑你现在 consolidate 卡住的根本原因就是：

```text
你在试图做：
Entity A == Entity B ?

实际上应该做：
Entity A 属于哪个 Concept？
Entity B 属于哪个 Concept？
```

当它们落到同一个 Concept 下时，比较和关联自然就出现了。


你问到了最核心的问题。

因为很多知识库项目最后失败，不是因为抽不出 Entity，而是因为：

> **Ontology（本体）设计失败。**

即：

```text
什么东西是一类东西？
什么东西是另一类东西？
```

没有定义清楚。

---

## 先说结论

我不认为：

```text
Design Decision
Mechanism
Domain Concept
```

这三个类别内部天然就是统一粒度的。

事实上，它们内部也会出现：

```text
又大又小
又抽象又具体
```

的问题。

所以：

> 分类（Type）解决的是“它是什么”，
>
> 不解决“它有多大”。

这是两个不同的问题。

---

# 举个例子

你刚才说：

## Design Decision

例如：

```text
Prompt Caching
Explicit DAG
Single Thread
```

看起来都是 Design Decision。

但粒度完全不同。

---

Single Thread

影响整个系统：

```text
网络模型
并发模型
锁模型
性能模型
```

属于：

```text
System-Level Decision
```

---

Prompt Caching

可能只是：

```text
Inference Optimization
```

属于：

```text
Feature-Level Decision
```

---

两者显然不是一个层级。

---

所以：

```text
Design Decision
```

只是类型。

不是层级。

---

# 再看 Mechanism

例如：

```text
Plugin System
Middleware
Hook
```

---

Plugin System

可能覆盖整个框架。

---

Hook

可能只是一个接口。

---

粒度也不一样。

---

# 再看 Domain Concept

例如：

```text
Memory
```

---

这是超级大概念。

---

而：

```text
KV Cache
```

是非常具体的概念。

---

但两者都是：

```text
Domain Concept
```

---

所以你会发现：

分类并没有解决层级问题。

---

# 真正成熟的知识体系是什么样？

其实是二维的。

---

第一维：

## Type（是什么）

例如：

```text
Concept
Decision
Mechanism
Artifact
Pattern
```

---

第二维：

## Scope（影响范围）

例如：

```text
System
Subsystem
Component
Feature
Implementation
```

---

举例：

### Explicit DAG

```yaml
type: Design Decision

scope: System
```

---

### Prompt Caching

```yaml
type: Design Decision

scope: Feature
```

---

### Plugin System

```yaml
type: Mechanism

scope: Subsystem
```

---

### Hook

```yaml
type: Mechanism

scope: Component
```

---

这样粒度问题就解决了。

---

# 我觉得你真正缺的是 Canonical Layer

这可能比 Type 更重要。

---

例如：

你现在提到：

```text
Prompt Caching
```

---

问题来了：

这是一个 Design Decision 吗？

还是一个 Mechanism？

---

不同人会给不同答案。

---

有人会说：

```text
采用 Prompt Caching
```

是决策。

---

有人会说：

```text
Prompt Cache
```

是机制。

---

于是知识库开始混乱。

---

成熟知识库不会直接存：

```text
Prompt Caching
```

---

而会存：

```yaml
Concept:
  Caching
```

然后：

```yaml
Decision:
  Adopt Prompt Caching
```

以及：

```yaml
Mechanism:
  Cache Lookup Layer
```

---

这样层次就分开了。

---

# 我觉得你现在最大的危险

是把所有东西都叫 Entity。

---

因为：

```text
Prompt Caching
Plugin System
Context Compression
```

其实已经不是同一种对象了。

---

如果全部叫 Entity。

最终会出现：

```text
Memory

Prompt Caching

StateGraph

Middleware

RAG

Todo

Agent Loop
```

全部放一起。

---

最后无法推理。

---

# 如果是我设计

我不会从 Entity 开始。

我会从 Question 开始。

---

即：

用户最终会问什么？

---

比如：

### 用户问题1

```text
为什么 Claude Code 和 LangGraph 不一样？
```

需要：

```text
Design Decision
```

---

### 用户问题2

```text
它们怎么扩展？
```

需要：

```text
Mechanism
```

---

### 用户问题3

```text
Context Compression 是什么？
```

需要：

```text
Domain Concept
```

---

### 用户问题4

```text
StateGraph 在 LangGraph 里是什么？
```

需要：

```text
Artifact
```

---

你会发现：

这些其实已经形成了一套知识对象体系。

---

# 我对你项目的判断

我觉得你现在不要急着设计一个非常庞大的 Ontology。

因为会失败。

很多知识图谱项目都死在这里。

---

我会先定义一个极小集合：

```text
Concept
Decision
Mechanism
Artifact
```

只有4类。

---

然后增加一个属性：

```text
Scope

System
Subsystem
Component
Feature
```

---

例如：

```yaml
name: Agent Loop

type: Decision

scope: System
```

---

```yaml
name: Prompt Caching

type: Decision

scope: Feature
```

---

```yaml
name: Plugin System

type: Mechanism

scope: Subsystem
```

---

```yaml
name: Todo

type: Artifact

scope: Component
```

---

这样已经足够支持：

* Consolidation
* Comparison
* Wiki 构建

了。

---

我的感觉是，你现在的问题其实不是：

> Entity 如何统一？

而是：

> Entity 之间到底是什么关系？

真正的本体（Ontology）不是一个概念列表。

而是一套：

```text
对象类型（Type）
+
层级范围（Scope）
+
对象关系（Relation）
```

的规则。

当你把这三件事定义出来以后，Entity 自然就能被组织起来；否则无论抽多少 Entity，最终都会变成一个越来越大的名词堆。


我看了一圈之后，反而觉得你遇到的问题是整个领域都没解决好的问题。

先给结论：

> **主流开源项目几乎都不做你现在想做的事情。**
>
> 它们做的是 Code Graph。
>
> 你想做的是 Code Wiki。

这是两个完全不同的方向。

---

## 我找到的几个 1k+ Star 代表项目

### 1. [Graphify](https://graphify.net/zh/?utm_source=chatgpt.com)（3.7k+ Star）

核心思路：

```text
Code
 ↓
Tree-sitter
 ↓
Symbol
 ↓
Graph
```

提取：

* Function
* Class
* Module
* Dependency
* Call Graph

然后构建知识图谱。([Graphify][1])

---

### 2. GitNexus（1.1k+ Star）

核心思路：

```text
Repository
 ↓
Code Intelligence
 ↓
Knowledge Graph
```

重点是：

* dependency
* call chain
* execution flow

也是 Graph First。([Evermx][2])

---

### 3. Understand-Anything（15k+ Star）

非常像你的方向。

但是仔细看：

```text
Files
Functions
Classes
Dependencies
Architecture Layers
```

仍然是：

```text
Code Entity
 → Graph
```

路线。([SourcePulse][3])

---

### 4. CodeGraph（30k+ Star）

最近特别火。

它的核心实体：

```text
Symbol
Call
Import
Class
Function
```

然后做：

```text
Semantic Graph
```

供 Claude Code 查询。([SourcePulse][4])

---

## 这些项目共同特点

你会发现：

它们的 Entity 非常统一。

因为它们抽的是：

```text
Class
Function
Module
File
Import
Call
```

---

这是 AST 层面的实体。

天然有统一标准。

---

例如：

```python
class Planner:
```

无论哪个仓库。

都是：

```text
Class
```

---

所以：

这些项目几乎没有 Ontology 问题。

---

## 而你在做什么？

你在抽：

```text
Prompt Caching
Agent Loop
StateGraph
Task Tree
Plugin System
Context Compression
```

---

这已经不是：

```text
Code Entity
```

了。

而是：

```text
Knowledge Entity
```

---

这就进入了另一个领域。

---

# 谁在做类似事情？

我反而发现有两个方向更接近你。

---

## SwarmVault

Karpathy Wiki 路线。

他们不是提取：

```text
Function
Class
```

而是提取：

```text
Concept
Relationship
Wiki Page
```

然后构建：

```text
Markdown Wiki
+
Graph
```

([GitHub][5])

---

## Repowise

这个项目虽然没多少 Star。

但我觉得思想很先进。

他们直接把仓库分成：

```text
Graph
Git
Docs
Decisions
Health
```

五层。([Reddit][6])

---

这里第一次出现：

```text
Decision
```

这个概念。

---

因为作者发现：

仅有代码图谱不够。

还需要：

```text
Why
```

---

# 然后说你最关心的问题

## Ontology 到底是什么？

其实很简单。

Ontology 本质上就是：

```text
允许出现哪些对象

以及

这些对象之间允许存在什么关系
```

---

例如动物世界：

```text
Animal

Dog
Cat
Bird
```

---

关系：

```text
Dog is-a Animal

Cat is-a Animal
```

---

这就是一个简单 Ontology。

---

# 你的项目里面

其实已经隐约有 Ontology 了。

你刚刚说：

```text
Prompt Caching
→ Design Decision

Plugin System
→ Mechanism

Context Compression
→ Domain Concept
```

---

实际上已经在做：

```text
Type System
```

了。

---

我觉得你现在离正确答案只差一步。

---

# 我觉得最值得参考的不是知识图谱项目

而是软件架构领域的 C4 Model

C4 里面有：

```text
System
Container
Component
Code
```

四层。

---

大家为什么喜欢 C4？

因为：

```text
不同层次的信息
不放在一起
```

---

例如：

```text
Redis
```

和：

```text
HashTable
```

不在一个层次。

---

所以不会混乱。

---

# 我对你的建议

我不会继续纠结：

```text
Design Decision
Mechanism
Domain Concept
```

够不够。

---

因为问题不在那里。

---

真正的问题是：

### 你缺少 Layer

例如：

```yaml
Layer 1:
  Domain Concept

Layer 2:
  Pattern

Layer 3:
  Design Decision

Layer 4:
  Mechanism

Layer 5:
  Artifact
```

---

举例：

### Context Compression

```yaml
type: Domain Concept
```

---

### Hierarchical Planning

```yaml
type: Pattern
```

---

### Agent Loop

```yaml
type: Design Decision
```

---

### Plugin System

```yaml
type: Mechanism
```

---

### TaskTree

```yaml
type: Artifact
```

---

这样：

```text
TaskTree
```

和

```text
Context Compression
```

永远不会被放进同一个桶里。

---

## 但我认为更重要的发现

看完这些项目后，我最大的感受是：

> 绝大多数 Code Graph 项目都停留在「代码实体层」。

例如：

```text
Function
Class
Call
Import
```

([SourcePulse][4])

而你正在尝试构建：

```text
Concept
Pattern
Decision
Mechanism
Artifact
```

这一层。

---

这其实已经不属于 Code Intelligence。

更接近：

```text
Software Architecture Knowledge Base
```

或者：

```text
Repository Intelligence
```

了。

所以你很难找到一个成熟开源项目直接抄答案。

因为你遇到的「Entity 粒度不统一」问题，本质上是从代码图谱走向知识图谱时才会出现的问题，而大多数项目根本还没走到这一步。

[1]: https://graphify.net/zh/?utm_source=chatgpt.com "Graphify — Open-Source Knowledge Graph Skill for AI Coding Assistants"
[2]: https://evermx.com/open-source/gitnexus-knowledge-graph-code-intelligence?utm_source=chatgpt.com "GitNexus - Open Source AI Project"
[3]: https://www.sourcepulse.org/projects/26371840?utm_source=chatgpt.com "Understand-Anything by Lum1104 - SourcePulse"
[4]: https://www.sourcepulse.org/projects/26063108?utm_source=chatgpt.com "codegraph by colbymchenry - SourcePulse"
[5]: https://github.com/swarmclawai/swarmvault?utm_source=chatgpt.com "GitHub - swarmclawai/swarmvault: The local-first LLM Wiki: open-source knowledge graph builder, RAG knowledge base, and agent memory store. Built on Andrej Karpathy's pattern. An Obsidian alternative for personal knowledge management, AI second brain, and durable Claude Code / Codex / OpenClaw memory. · GitHub"
[6]: https://www.reddit.com/r/ClaudeAI/comments/1thw8fi/open_source_codebase_intelligence_for_claude_code/?utm_source=chatgpt.com "Open source codebase intelligence for Claude Code: graph, git history, docs, ADRs and code health"

