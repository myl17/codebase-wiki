# 最终实验报告：Source Code vs DeepWiki — 内容质量与 Concept 提取价值

> 日期: 2026-06-14 | 仓库: openclaw + hermes-agent | 维度: Architecture

## 一、实验设置

| 对照组 | 提取方式 | 独立上下文 |
|--------|---------|-----------|
| Wiki 现有 | `/analyze` 完整流程（LLM 读源码 → 草稿 → 人工确认） | 对话式 |
| Source 实验 | subagent 自主探索源码，一次穷尽可能 | 独立 |
| DeepWiki 实验 | subagent 自主探索 DeepWiki 预解析内容，一次穷尽可能 | 独立 |

两个 subagent 完全对称：同样维度指南、同样输出格式、同样探索自由度。唯一变量是输入源。

## 二、总览对比（四组实验 × 两个仓库）

| 仓库 | 版本 | 大小 | provenance | 核心变量 |
|------|------|------|-----------|---------|
| OpenClaw | Wiki | 7.0K | 13 | — |
| OpenClaw | Source | 20.6K | 48 | 漏了设备节点层、沙箱层、协议层 |
| OpenClaw | DeepWiki | 33.8K | 133 | 全覆盖，但缺设计意图和架构纪律 |
| Hermes | Wiki | 15.9K | 33 | 有自学习闭环（唯一） |
| Hermes | Source | 18.0K | 29 | 数据流最详细，缺自学习闭环 |
| Hermes | DeepWiki | 18.7K | 75 | 有 BaseEnvironment、跨框架对比 |

## 三、理解质量：每个版本独有的洞察

### Hermes Agent

**Wiki 独有（人工参与的价值）：**

| 洞察 | 为什么重要 |
|------|-----------|
| **自学习闭环三条驱动指令**（MEMORY_GUIDANCE / SESSION_SEARCH_GUIDANCE / SKILLS_GUIDANCE） | Hermes 最核心的架构特征，三个时间尺度的自我改进 |
| **与 OpenClaw 的关键差异**——「OpenClaw 有 skills 和 memory，但**没有系统 prompt 中那三条自驱动的指令**」 | 这是跨仓库对比最精确的因果分析 |
| **三层审批架构**（YOLO / Smart / Manual） | 安全模型的完整描述 |
| **设计模式显式命名**——单例+线程安全、适配器模式、策略模式、事件/Observer、Agent 缓存 | 模式命名使跨仓库同构识别更容易 |

**DeepWiki 独有（预扫描全景的价值）：**

| 洞察 | 为什么重要 |
|------|-----------|
| **BaseEnvironment** 抽象——6 种后端（local/docker/ssh/modal/daytona/singularity） | 这是纯扩展点模式，与 OpenClaw 的 ChannelPlugin 形成完美同构对比 |
| **渐进式技能披露**（Progressive Disclosure）—— Tier 0/1/2 三级 | 命名的设计模式，可跨仓库匹配 |
| **跨框架定位**——vs LangChain 图编排、vs CrewAI 多代理协作 | 将 Hermes 放入已知范式坐标系，降低理解门槛 |
| **ACP 协议数据流**——JSON-RPC over STDIO | 编辑器集成的完整描述 |

**Source 独有（深读代码的价值）：**

| 洞察 | 为什么重要 |
|------|-----------|
| **API-call-time injection 模式**——messages 永不修改，注入不泄漏到持久化 | 一个精巧的内部设计决策 |
| **子代理数据隔离规则**——无父代理历史、独立 task_id、受限工具集 | 委托模式的精确语义 |
| **回调管道**——stream_delta/tool_progress/clarify/step/thinking 全套回调 | 平台层解耦的关键机制 |

### OpenClaw（简要）

- **Wiki 独有**：Process Supervisor + 自监控进程管理
- **DeepWiki 独有**：设备节点层、协议层、沙箱层、原生客户端——全是 Source 漏掉的东西
- **Source 独有**：架构纪律规则（不要硬编码扩展 ID、不要从无关代码读插件配置）、Plugin SDK 70+ 子路径设计意图

## 四、对 Concept 提取的助益

Concept 提取需要三样东西：

1. **命名的抽象模式**——跨仓库同构时能找到共同语言
2. **清晰的接口边界**——能判断两个仓库的组件是否「在做同一件事」
3. **跨仓库对比锚点**——直接的 comparanda

### 哪个版本最适合做 Concept 提取？

**Wiki 现有版最适合**，因为它做了实验版本没做的事情：
- 显式对比两个仓库的关键差异（「OpenClaw 没有自驱动的指令」）
- 使用设计模式名称描述架构（适配器、策略、单例、Observer）
- 抓住了仓库最独特的架构特征（自学习闭环）

但 Wiki 版覆盖范围有限——Hermes 缺失了 BaseEnvironment 抽象，OpenClaw 缺失了设备节点层。

**DeepWiki 版本补充了 Wiki 版缺失的内容**：
- BaseEnvironment vs ChannelPlugin 的同构关系（接口+多实现+配置切换）
- 渐进式技能披露（可与 OpenClaw 的 Skills 系统做匹配）
- 跨框架定位语境

**Source 版本提供了最精确的接口级细节**——API-call-time injection、子代理隔离规则、回调管道——这些在 Concept 页的「实现范式」段中可以直接用。

### 最理想路径

```
DeepWiki 做广度预扫描 → 给出概念地图 + 跨框架定位
   ↓
Source 做关键接口深读 → 提取精确的接口签名和内部设计决策
   ↓
结合两者产出 + 维度指南 → LLM 写 Architecture 维度页
   ↓
人确认 → 补充跨仓库对比 + 最独特的架构特征（如自学习闭环）
```

**单靠 DeepWiki 不够——它缺设计意图和架构纪律。单靠 Source 也不够——对复杂 monorepo 它会遗漏整个子系统。**

## 五、到底要不要引入 DeepWiki

| 场景 | 建议 |
|------|------|
| 复杂 monorepo（多目录、多包、扩展目录与核心无 import 连接） | **建议**。单 agent turn 无法完成全局探索。DeepWiki 的预扫描是唯一能在一个 turn 里给出全貌的方法 |
| 简洁项目（单一语言、核心在根目录、模块边界明确） | **不需要**。Source agent 自己探索就能覆盖 90%。DeepWiki 只多了 4% |
| DeepWiki 未索引的仓库 | 不可用。只能走 Source 路径 |
| 所有场景 | **改 `/analyze` prompt 比引入 DeepWiki 更优先。** Source 实验对 OpenClaw (+195%) 和 Hermes (+13%) 的提升已经证明了这一点 |

### 如果引入 DeepWiki，怎么用

不是替代 Source，而是作为 `/analyze` 的 **Step 1.5（可选预扫描）**：

```
Step 1: delta.py 文件分类
Step 1.5: 如果 DeepWiki 有此仓库 → MCP 拉取结构，作为 agent 的全局概念地图
Step 2: agent 基于概念地图 + core 文件，定向深读关键源文件
Step 3: 生成维度页（穷尽探索模式）
```

DeepWiki 提供的是「这个仓库有哪些地方值得看」的地图。Source 提供的是「这里面的关键设计决策是什么」的解读。两者组合 = 既有全景又有因果链。

## 六、优先级排序

1. **P0：改 `/analyze` prompt。** 从「草稿→确认即停」改成「穷尽探索→人选 2-3 点深挖→agent 定向深入」。不改这个，引入什么数据源都没用。
2. **P1：对复杂 monorepo 启用 DeepWiki 预扫描。** 作为一个无成本的全景地图提供商。
3. **P2：不要对简洁项目引入 DeepWiki。** 边际收益可以忽略。
4. **Human curation remains irreplaceable** —— 自学习闭环这个 Hermes 最独特的架构特征，两个实验 agent 都没有捕捉到。人参与的方向引导仍然是最重要的质量保证。
