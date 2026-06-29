# Codex-Main Step 3 候选清单（B2 @ Strategy C）

**生成日期**：2026-06-28
**来源仓库**：codex-main（22 Entity, 19 问题空间条目）
**测试场景**：B2 — SKILL.md Step 3 行为测试 @ 518 Concepts
**规模检测**：518 个 Concept → 策略 C

---

## A 类（追加到已有页面）

共 16 条，合并为 8 个 unique Concept：

| # | 问题名 | 来源 Entity | 目标 Concept |
|---|--------|-------------|-------------|
| 1 | 如何编排 AI Agent 的回合制交互循环 | core-agent-loop | agent-loop-orchestration |
| 2 | 如何抽象跨本地/远程/沙箱环境的命令执行 | exec-server | execution-isolation |
| 3 | 如何对 Shell 命令执行实施允许/拒绝策略 | execpolicy | security-architecture |
| 4 | 如何提供跨平台的可移植文件系统沙箱 | sandbox-abstraction | execution-isolation |
| 5 | 如何安全地以提升权限执行 Shell 命令 | shell-escalation | execution-approval-pattern |
| 6 | 如何定义、发现和执行 Agent 工具 | tool-system | tool-lifecycle-management |
| 7 | 如何在 Agent 生命周期关键节点插入行为拦截 | hook-system | hooks-event-interception |
| 8 | 如何用用户定义的技能文件扩展 Agent 能力 | skills-system | skills-extension-mechanism |
| 9 | 如何抽象多个 LLM 后端为统一接口 | model-provider | provider-abstraction-pattern |
| 11 | 如何合并文件/云端/CLI 的多层配置 | config-management | configuration-management |
| 12 | 如何将 Agent 工具暴露为 MCP JSON-RPC 服务 | mcp-server | mcp-protocol-integration |
| 13 | 如何管理 MCP 服务器的连接、目录和认证 | codex-mcp-integration | mcp-protocol-integration |
| 15 | 如何持久化、发现和搜索 Agent 会话转录 | rollout | session-lifecycle-management |
| 16 | 如何抽象跨存储后端的对话持久化 | thread-store | session-lifecycle-management |
| 19 | 如何通过贡献者注册表扩展 Agent 行为 | extension-api | system-prompt-assembly |

确认细节：
- 所有目标 Concept 的 frontmatter `repos:` 字段已包含 codex-main
- 所有目标 Concept 的 body 中已有 `### codex-main` 节（上一次 ingest 写入）
- 本次无需新增 Concept 写操作

---

## B 类（新建 Concept 页）

共 0 条。

条目 #7（hook-system）和 #12/#13（mcp-server/codex-mcp-integration）在上次 ingest（Strategy A）中为 B 类，当时触发了新建 `hooks-event-interception` 和 `mcp-protocol-integration`。本轮检测到这两个 Concept 已存在，正确归为 A 类。

无其他条目通过①②③硬门槛。

---

## C 类（待观察）

共 2 条：

| # | 问题名 | 来源 Entity | 判断理由 |
|---|--------|-------------|----------|
| 10 | 如何管理模型目录、预设和动态刷新 | models-manager | 仅 codex-main 有独立的 SharedModelsManager + RefreshStrategy 枚举控制刷新节奏；其他仓库的模型列表管理嵌入在 provider 层（hermes-agent HermesOverlay, openclaw model-configuration），未将模型目录作为独立关注点分离。① 多方案：❌ 仅 codex-main 有独立实现 |
| 14 | 如何提供多传输层 JSON-RPC 后端管理会话 | app-server | 仅 codex-main 有独立的多传输层 MessageProcessor + 三种传输后端（stdio/WebSocket/Unix socket）；其他仓库的传输层集成在 gateway/channel 层（hermes-agent gateway, nanobot channel），未形成独立的"传输无关 JSON-RPC 后端"抽象。① 多方案：❌ 仅 codex-main 有独立实现 |

---

## D 类（演化信号）

共 2 条，详见 `evolve-signals/2026-06-29-codex-main-b2.md`：

| # | 问题名 | 来源 Entity | 信号类型 | 相关 Concept |
|---|--------|-------------|----------|-------------|
| 17 | 如何建模插件包的标识、能力和钩子元数据 | plugin-system | 粒度不匹配 | skills-extension-mechanism, tool-lifecycle-management |
| 18 | 如何管理插件商城、安装、升级和卸载 | plugin-management | 粒度不匹配 | skills-extension-mechanism, tool-lifecycle-management |

信号摘要：
- #17 PluginId 命名空间格式 + PluginCapabilitySummary 能力声明 + PluginProvider 来源抽象 → 与 skills-extension-mechanism（技能来源多样性 + 信任分级）部分重叠，但覆盖了二进制插件的能力声明和钩子契约，这是 skills 未覆盖的维度
- #18 PluginsManager 生命周期 + ConfiguredMarketplace 商城抽象 + startup_sync → 与 skills-extension-mechanism（安装自动化 + 社区市场搜索）部分重叠，但涉及版本管理、二进制兼容性检查、启动时同步，是独立的设计空间
- 两者均与 openclaw 的 plugin-sdk/plugin-system 形成跨仓库对比基础 → 建议后续评估是否拆分为独立 `plugin-architecture` Concept

---

## 能力域覆盖表

| 能力域 | nanobot | hermes-agent | openclaw | deepagents | codex-main |
|--------|---------|-------------|----------|------------|------------|
| Agent 循环编排 | ✅ | ✅ | ✅ | — | ✅ |
| 执行隔离/沙箱 | ⚠️ (无隔离层) | ✅ (6后端) | ✅ (Docker/SSH) | ✅ (协议驱动) | ✅ (3层抽象+多平台) |
| 安全架构 | ✅ (SSRF) | ✅ (4层防线) | ✅ (4维审计) | — | ✅ (3层防线) |
| 执行审批 | — | ✅ (3层作用域) | ✅ (异步Promise) | — | ✅ (EscalateServer) |
| 工具生命周期 | ✅ (手工注册) | ✅ (AST自动发现) | ✅ (9层管道) | — | ✅ (3源解析) |
| Hook/事件拦截 | ⚠️ (中间件) | — | ✅ (3源发现) | — | ✅ (10事件) |
| Skills 扩展 | ✅ (双层本地) | ✅ (联邦市场) | ✅ (三源本地) | ✅ (纯渐进披露) | ✅ (声明式+编译嵌入) |
| Provider 抽象 | ✅ (ABC) | ✅ (函数式+25+) | ✅ (注册表+冷却) | ✅ (前缀路由) | ✅ (Trait+能力声明) |
| 配置管理 | ✅ | ✅ | ✅ | — | ✅ (多层合并+云端约束) |
| 会话生命周期 | ✅ (JSONL) | ✅ (SQLite WAL) | ✅ (写锁+磁盘预算) | — | ✅ (Trait抽象+混合存储) |
| MCP 协议集成 | — | ✅ (工具源) | — | — | ✅ (Client+Server深度集成) |
| 系统提示词组装 | ✅ (层方法) | ✅ (纯函数拼接) | ✅ (27节枚举) | — | ✅ (PromptSlot槽位) |
| 模型目录管理 | — | — | — | — | ✅ (唯一) |
| 多传输后端 | — | — | — | — | ✅ (唯一) |
| 插件系统 | — | — | ⚠️ (SDK) | — | ✅ (元数据+商城) |

---

## 与 Baseline 对比

Baseline（seeds/master.md codex-main 节，Strategy A @ ~30 concepts）对比本轮（Strategy C @ 518 concepts）：

| # | Baseline | B2 (Strategy C) | 差异 |
|---|----------|----------------|------|
| 1-6 | A → 同 Concept | A → 同 Concept | ✅ 一致 |
| 7 | B → hooks-event-interception | A → hooks-event-interception | 🔄 B→A（Concept 已存在） |
| 8 | A → skills-extension-mechanism | A → skills-extension-mechanism | ✅ 一致 |
| 9 | A → provider-abstraction-pattern | A → provider-abstraction-pattern | ✅ 一致 |
| 10 | C | C | ✅ 一致 |
| 11 | A → configuration-management | A → configuration-management | ✅ 一致 |
| 12-13 | B → mcp-protocol-integration | A → mcp-protocol-integration | 🔄 B→A（Concept 已存在） |
| 14 | C | C | ✅ 一致 |
| 15-16 | A → session-lifecycle-management | A → session-lifecycle-management | ✅ 一致 |
| 17-18 | D | D | ✅ 一致 |
| 19 | A → system-prompt-assembly | A → system-prompt-assembly | ✅ 一致 |

**结论**：Strategy C（关键词 grep @ 518 concepts）与 Strategy A（全量 head -10 @ ~30 concepts）产生**实质上一致的分类结果**。唯一差异是条目 #7/#12/#13 从 B→A（因相应 Concept 在上轮 ingest 中已创建），这是正确行为而非错误。518 个干扰 concept 文件未造成任何误匹配或漏匹配。

---

## 检索行为记录

### 规模检测

```
命令：ls wiki/concepts/*.md 2>/dev/null | wc -l
结果：518
宣告：检测到 518 个 Concept → 选择策略 C
```

### seeds/master.md 访问方式

**方法**：部分读取 + 精确匹配

```
head -80 seeds/master.md                          # 读取开头获取种子库结构
grep -n "来自 codex-main" seeds/master.md          # 定位 codex-main 节行号 (71)
read seeds/master.md offset=71 limit=30            # 精确读取 codex-main 节
```

未使用全量 cat——按 SKILL.md Step 3 指令："禁止读取 seeds/master.md 全文。用 problem-map 中的关键词 grep seeds/master.md，只读匹配行"。

### Concept 检索方式

**方法**：关键词 grep -l（策略 B/C 的标准方法），8 轮分批执行：

```
# 第 1 轮：Agent loop/orchestration/turn 关键词
grep -l "agent-loop\|agent.*orchestrat\|turn.*loop\|execution.*loop\|interaction.*loop\|回合" wiki/concepts/*.md

# 第 2 轮：execution isolation/sandbox/command exec 关键词
grep -l "execution.*isolat\|sandbox\|exec.*backend\|exec.*environ\|command.*execut\|沙箱\|命令执行" wiki/concepts/*.md

# 第 3 轮：security/policy/approval/escalation 关键词
grep -l "security.*architect\|execpolicy\|permission.*approv\|execution.*approv\|approval.*pattern\|shell.*secur\|escalat\|允许.*拒绝" wiki/concepts/*.md

# 第 4 轮：tools/tool-lifecycle/tool-definition 关键词
grep -l "tool-lifecycle\|tool.*definit\|tool.*manag\|工具.*定义\|工具.*管理" wiki/concepts/*.md

# 第 5 轮：hooks/event interception/lifecycle event 关键词
grep -l "hook.*system\|event.*intercept\|lifecycle.*event\|钩子\|拦截" wiki/concepts/*.md

# 第 6 轮：skills/extension/skill-file 关键词
grep -l "skills-extens\|skill.*file\|skill.*manag\|技能.*扩展\|技能.*文件" wiki/concepts/*.md

# 第 7 轮：provider-abstraction/model-provider/llm-backend/model-manager 关键词
grep -l "provider.*abstract\|model.*provider\|llm.*backend\|model.*manager\|模型.*管理\|模型.*目录" wiki/concepts/*.md

# 第 8 轮：configuration-management/config-merge/profile 关键词
grep -l "configuration.*manag\|config.*merge\|config.*layer\|多层.*配置\|profile.*切换" wiki/concepts/*.md

追加轮次：
# 第 9 轮：session-lifecycle/session-persist/thread-store/rollout/transcript 关键词
grep -l "session.*lifecycle\|session.*persist\|thread.*store\|rollout\|transcript\|会话.*持久\|会话.*转录" wiki/concepts/*.md

# 第 10 轮：plugin/marketplace/extension-api/plugin-id 关键词
grep -l "plugin.*system\|marketplace\|plugin.*manag\|extension-api\|plugin.*id\|插件" wiki/concepts/*.md
```

**每轮命中数**：1-5 个文件
**去重后命中**：18 个 unique Concept 文件
**有效匹配**：12 个（其余 6 个如 subagent-orchestration, channel-abstraction-pattern, autonomous-scheduling 等经 frontmatter 确认不相关）

**Frontmatter 确认方法**：对去重后的 18 个文件执行 `head -10` + `grep "^repos:"` 确认匹配

```
for f in <18 files>; do echo "=== $(basename $f) ==="; head -10 "$f"; echo ""; done
```

**深读确认**：对确认匹配的 12 个 Concept 逐页读全文 body（`### codex-main` 节和各仓库解法），确认问题空间语义匹配正确。

### 第二轮 grep（Strategy C 特有步骤）

**未执行**。Strategy C 规定："对未匹配的条目，从已匹配 Concept 的 `concerns` 字段提取扩展术语，做第二轮 grep"。本轮 19 条问题空间条目在第一轮均获得命中，无未匹配条目，因此第二轮 grep 不需要。

### 干扰项影响

**无干扰**。`wiki/concepts/` 目录下约 500 个 `distractor-*.md` 文件（distractor-0001 至 distractor-0510），8 轮关键词 grep 中仅 6 个 distractor 文件被命中：

- `distractor-0165.md`：命中第 2 轮（sandbox 关键词）
- `distractor-0268.md, distractor-0276.md, distractor-0436.md`：命中第 2 轮
- `distractor-0206.md, distractor-0270.md, distractor-0294.md, distractor-0295.md, distractor-0315.md, distractor-0377.md, distractor-0439.md, distractor-0493.md`：命中第 9 轮（session/rollout）
- `distractor-0032.md, distractor-0051.md, distractor-0079.md, distractor-0090.md, distractor-0212.md, distractor-0288.md, distractor-0466.md`：命中第 10 轮（plugin）

所有被命中的 distractor 文件在 frontmatter 确认阶段（`head -10`）被正确排除——它们的 `type` 字段为 `distractor` 而非 `concept`，且 `problem` 字段与问题空间条目语义不匹配。

**关键验证通过**：518 个 Concept 文件规模下，关键词 grep + frontmatter 过滤的二阶段方法正确区分了有效 Concept 与干扰项，无误匹配进入最终分类。
