# 验证报告：context-engine-pluggability

## 格式完整性 (checklist)

- [x] 标准化问题陈述
- [x] 核心关切 (4 项)
- [x] 已知权衡位置 (A: openclaw Exclusive 槽位覆盖注册, B: hermes-agent 策略模式 + 目录发现)
- [x] 每个位置: 优先满足的关切 / 接受妥协的关切 / 核心特征 / 关键机制 / 已知代价
- [x] 跨仓库对比表 (12 维度)
- [x] 选择指南 (9 场景)
- [x] 溯源表 (8 行)
- [x] 关联链接
- [x] 关切-实现对应: 4 项关切在对比表中均有对应维度 ✅
- [x] 每个仓库在各维度都有描述
- [x] 权衡位置分类: A="Exclusive 槽位覆盖注册", B="策略模式 + 目录发现" — 正确映射

## 逐仓库验证

### OpenClaw (位置 A)

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| 1 | ContextEngine 四大生命周期操作: assemble/ingest/compact/transcriptRewrite | ✅ | `openclaw-architecture.md` line 44: "四个生命周期操作：assemble（组装 prompt）、ingest（摄入新消息）、compact（Context 压缩历史）、transcriptRewrite（重写 transcript）" + `openclaw-context-engine.md`: 完全一致的四个操作 |
| 2 | ContextEngineFactory 工厂函数创建 ContextEngine 实例 | ✅ | `openclaw-context-engine.md`: "支持可注册的 ContextEngineFactory（exclusive 槽位，全局只能有一个活跃实现）" |
| 3 | LegacyContextEngine 包装旧接口保证向后兼容 | ✅ | `openclaw-context-engine.md`: "通过 LegacyContextEngine 向后兼容" |
| 4 | registerContextEngine 声明为 exclusive，全局只能有一个活跃实现 | ✅ | `openclaw-extension-points.md` line 58: "registerContextEngine — 注册上下文引擎实现（**exclusive**）" + line 67: "独占槽位：registerContextEngine 和 registerMemoryCapability 全局只能有一个活跃实现，后注册者覆盖前者" |
| 5 | registerCompactionProvider 是 ContextEngine 内部子策略替换点 | ✅ | `openclaw-compaction-provider.md`: "registerCompactionProvider 注册压缩/摘要后端，替换 Context 压缩的具体策略（摘要 LLM、chunk 策略）而无需重写 ContextEngine" + extension-points.md line 59: "registerCompactionProvider — 注册压缩/摘要后端" |
| 6 | registerMemoryCapability 共享同一 exclusive 设计模式 | ✅ | `openclaw-extension-points.md` line 67: "独占槽位：registerContextEngine 和 registerMemoryCapability 全局只能有一个活跃实现" |
| 7 | 三层保护的所有者访问控制: 默认槽位 core 锁定 + 跨 owner 拒绝 + 同 owner 刷新需 allowSameOwnerRefresh opt-in | ⚠️ | `src/context-engine/registry.ts:309-395` 在本仓库中没有对应的 wiki 提取文件。`openclaw-extension-points.md` 描述了 exclusive 机制（后注册覆盖前者）但未描述三层保护的所有者访问控制细节。此声明无法从可用源独立验证。修正建议：溯源表补充实际的 wiki 节点引用，或标注此信息来源于直接源码阅读 |
| 8 | resolveContextEngine(config) 先读 config.plugins.slots.contextEngine 显式覆盖 → 回退 default slot | ⚠️ | `src/context-engine/registry.ts:411-427` 在本仓库中没有对应的 wiki 提取文件。解析机制细节无法从可用源独立验证。修正建议：同 #7 |
| 9 | Map 中可注册多个 factory，但同一时刻只有一个解析激活 | ✅ | 与 exclusive 槽位机制一致——exclusive 的本质就是 "可注册多个但只有一个激活"。`openclaw-extension-points.md` line 67 确认了后注册覆盖前者 |
| 10 | 无法通过配置文件直接指定 engine——需修改代码注册逻辑 | ⚠️ | 此声明与 #8 部分矛盾。如果 `config.plugins.slots.contextEngine` 可以显式覆盖，那么配置文件层面是可以指定的。概念页声称 "无法通过配置文件直接指定" 需要更精确：可能是指 "无法在不写代码的情况下切换到一个尚未注册的 engine"，而非 "无法通过配置选择已注册的 engine"。修正建议：重新措辞为 "切换 engine 需要先通过代码注册 factory，再通过配置选择已注册的 engine——不能像 hermes 那样仅靠修改 YAML 即完成切换" |

### Hermes-Agent (位置 B)

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| 11 | ContextEngine ABC: name (属性) / threshold_percent=0.75 / protect_first_n=3 | ✅ | `hermes-agent-extension-points.md` lines 97-99: "name: str / threshold_percent: float = 0.75 / protect_first_n: int = 3" |
| 12 | 四个必须实现的方法: update_from_response(usage) / should_compress() / compress(messages) / name (属性) | ⚠️ | `hermes-agent-extension-points.md` lines 102-107 列出的方法包括: on_session_start(), update_from_response(usage_data), should_compress() -> bool, compress(messages) -> List, on_session_end(), get_tools() -> List[dict]。维度文件没有明确区分 "必须实现" 和 "可选扩展"。概念页的 4 必需 + 8 可选分类可能来自源码细节，但维度文件未做此区分。`on_session_start()` 和 `on_session_end()` 在维度文件中与 update_from_response/should_compress/compress 并列列出，未被标记为可选。修正建议：标注此区分来源于直接源码阅读 |
| 13 | 可选扩展 (8 个): should_compress_preflight / on_session_start/end/reset / get_tool_schemas / handle_tool_call / get_status / update_model | ⚠️ | 维度文件提到了 on_session_start(), on_session_end(), get_tools() 但未明确标记为可选，且未提及 should_compress_preflight, on_session_reset, handle_tool_call, get_status, update_model。这些细节无法从维度文件独立验证。修正建议：同 #12 |
| 14 | 目录发现: discover_context_engines() 扫描 plugins/context_engine/ 目录 | ⚠️ | `hermes-agent-extension-points.md` line 111: "放入 plugins/context_engine/<name>/ 目录，通过配置选择" 确认了目录结构和配置选择，但未命名 discover_context_engines() 函数，也未描述 register(ctx) 或 Fallback ABC 子类扫描这两种加载模式。这些细节无法从维度文件独立验证 |
| 15 | plugin.yaml 提供人类可读描述，is_available() 做轻量级前置检查 | ⚠️ | 维度文件未提及 plugin.yaml 和 is_available()。无法独立验证 |
| 16 | 声明式激活 + 回退链: config.yaml → context.engine → load_context_engine → hermes_cli.plugins.get_plugin_context_engine() → built-in "compressor" | ⚠️ | `hermes-agent-extension-points.md` line 110: "激活方式: config.yaml 中 context.engine: 'lcm'" 确认了 config.yaml 激活。但三层回退链的具体细节（load_context_engine → hermes_cli.plugins → built-in compressor）无法从维度文件验证 |
| 17 | 压缩触发阈值: 固定 75% context window | ✅ | `hermes-agent-extension-points.md` line 98: "threshold_percent: float = 0.75" |
| 18 | 内置 ContextCompressor (summary-based) 和 LCM (Low-Context-Mode) 两种实现 | ✅ | `hermes-agent-extension-points.md` line 111: "内置默认: ContextCompressor (summary-based 压缩)" + line 110提到 LCM |
| 19 | 同一时间只有一个 engine 激活的硬性约束 | ✅ | `hermes-agent-extension-points.md` line 112: "同一时间只有一个 engine 激活 ^[agent/context_engine.py:5-17]" |
| 20 | 扩展摩擦: 需创建目录 + __init__.py + ABC实现 + plugin.yaml + 修改config.yaml | ✅ | 与 #14/#15 一致——维度文件确认了目录结构和配置修改是扩展的必要步骤 |

### 跨概念页一致性检查

| # | 声明 | 判定 | 依据 |
|---|------|------|------|
| C1 | 对比表 "接口广度": 本页说 openclaw "全栈生命周期：assemble/ingest/compact/transcriptRewrite + subagent 状态管理 + prompt-cache 可观察性" | ⚠️ | "subagent 状态管理" 和 "prompt-cache 可观察性" 在 `openclaw-architecture.md` 和 `openclaw-context-engine.md` 中未被提及——wiki 文件仅描述了四个操作。这些额外能力可能来自源码但无法独立验证。修正建议：标注信息来源或弱化为 "可能还包括" |
| C2 | 对比表 "最小实现门槛": 本页说 hermes "4 个抽象方法，其余可选——最小实现可几十行代码" | ⚠️ | 维度文件未区分 required vs optional 方法。无法确认 "最小实现可几十行代码" 的声称。修正建议：标注为估算 |
| C3 | 本页引用 `src/plugins/types.ts:1867-1990` 作为 registerContextEngine 注册点 | ✅ | `openclaw-compaction-provider.md` sources 字段引用相同: "src/plugins/types.ts:1867-1990" |
| C4 | 本页引用 `src/context-engine/registry.ts:309-395` 和 `:411-427` | ⚠️ | 这些行号来源于概念页自身的溯源表，但 `registry.ts` 没有对应的 wiki 节点文件。其他 concept 页也未引用此文件。无法交叉验证行号精确性 |
| C5 | 对比表 "状态安全": hermes "配置选一 + 回退链兜底（无所有者概念，信任目录即授权）" | ✅ | 与 hermes 的目录发现机制一致——任何放在正确目录的实现都可被加载，与 openclaw 的注册 API + 所有者保护形成对比 |

## 关切验证

### 关切-对比表对应检查

| 关切 | 对比表对应维度 | 是否覆盖 |
|------|--------------|---------|
| 1. 第三方可扩展性 | "扩展摩擦" + "最小实现门槛" | ✅ |
| 2. 同一时间只有一个 engine 激活 | "多实现并存" (两者都是配置选一) + "状态安全" | ✅ |
| 3. 压缩引擎的注册机制 | "注册方式" + "激活方式" | ✅ |
| 4. 引擎替换对核心代码的影响 | "切换成本" (openclaw 改代码 vs hermes 改 YAML) | ✅ |

所有 4 项关切在对比表中均有对应维度。

### 权衡位置分类验证

- **位置 A (openclaw)**: "Exclusive 槽位覆盖注册" — 正确。registerContextEngine exclusive + 后注册覆盖，与维度文件描述一致。
- **位置 B (hermes-agent)**: "策略模式 + 目录发现" — 正确。ContextEngine ABC 作为策略接口 + 目录扫描加载，与维度文件描述一致。

## 绝对化语言标记

| 位置 (行) | 语言 | 风险 |
|-----------|------|------|
| line 16: "多个压缩策略同时运行必然冲突" | "必然" | 低风险——这是架构设计层面的判断，非事实声明。两个 engine 同时操作共享对话状态确实会产生冲突 |
| line 20: "同一时间只有一个 engine 激活" | "只有...一个" | 低风险——这是两仓库共同的设计约束，在 openclaw exclusive 槽位和 hermes agent/context_engine.py:5-17 都有确认 |
| line 33: "Exclusive 槽位的'覆盖'是注册机制层面的设计——后注册者覆盖同一 ID 的前者——而非运行时动态切换" | "而非"（排他性断言） | 低风险——`openclaw-extension-points.md` line 67 确认 "后注册者覆盖前者" |
| line 45: "Map 里可以注册多个，但同一时刻只有一个处于激活状态" | "只有...一个" | 低风险——exclusive 槽位的本质特征 |
| line 66-67: "不是一个全栈生命周期管理器，而是一个可以附带额外能力的压缩策略" | "不是...而是"（排他性断言） | 低风险——这是对接口设计的定性描述 |
| line 77: "用户不知道系统在加载哪些 engine"（hermes） | "不知道" | 中风险——维度文件未描述 hermes plugins list 命令。如果确实有 `hermes plugins list` 命令（概念页自身在对比表中提到了），则用户是可以知道的。存在自相矛盾风险——概念页 line 94 对比表说 hermes 有发现机制 "hermes plugins list 可查看"，但 line 77 说 "用户不知道"。修正建议：line 77 改为 "不显式调用 hermes plugins list 时，用户不知道系统加载了哪些 engine" |
| line 78: "任何第三方 engine 只要放在正确目录下即可与内置实现竞争激活位置" | "任何...只要...即" | 低风险——目录发现的本质特征 |
| line 95: "无所有者概念，信任目录即授权" | 绝对化定性 | 低风险——与 openclaw 的所有者保护形成对比，定性准确 |

## 追加完整性

### 两个仓库在各节描述完整性

| 章节 | openclaw 覆盖 | hermes-agent 覆盖 | 完整? |
|------|-------------|-----------------|------|
| 优先满足的关切 | 第三方扩展 + 注册规则 | 显式选择 + 发现机制 | ✅ |
| 接受妥协的关切 | 显式选择（注册顺序敏感） | 扩展便利性（多步骤） | ✅ |
| 核心特征 | ✓ | ✓ | ✅ |
| 关键机制 | 4 项 (生命周期接口+Exclusive槽位+三层保护+运行时解析) | 4 项 (精简ABC+目录发现+声明式激活+压缩阈值) | ✅ |
| 已知代价 | 4 项 | 5 项 | ✅ |
| 已知实例 | 3 个节点 | 2 个节点 | ✅ |

### 溯源表信息质量

与 dependency-version-locking 概念页不同，本页的溯源表为多个引用提供了具体的 wiki 节点映射：

| 溯源表行 | 是否有对应 wiki 节点 | 节点质量 |
|----------|-------------------|--------|
| openclaw `src/context-engine/index.ts:1-27` | ✅ `openclaw-context-engine.md` | 充分——确认了四大操作和 Factory |
| openclaw `src/plugins/types.ts:1867-1990` | ✅ `openclaw-compaction-provider.md` (sources 字段) | 充分——确认了 exclusive 注册 |
| openclaw `src/context-engine/registry.ts:309-395` | ❌ 无对应节点 | 无法验证三层保护的详细实现 |
| openclaw `src/context-engine/registry.ts:411-427` | ❌ 无对应节点 | 无法验证 resolveContextEngine 实现 |
| hermes-agent `agent/context_engine.py:32-60` | ✅ `hermes-agent-context-engine.md` + `hermes-agent-extension-points.md` | 充分——确认了 ABC 接口和核心方法 |
| hermes-agent `agent/context_engine.py:5-17` | ✅ `hermes-agent-extension-points.md` line 112 引用 | 充分——确认了单 engine 约束 |
| hermes-agent `plugins/context_engine/__init__.py:33-76` | ⚠️ 维度文件提到了目录扫描但未描述 discover_context_engines() 函数细节 | 部分——目录发现机制确认，但函数级细节无法验证 |
| hermes-agent `plugins/context_engine/__init__.py:100-196` | ⚠️ 同上 | 部分——_load_engine_from_dir() 的两种加载模式无法验证 |

### 自相矛盾风险

概念页 line 77 (已知代价): "用户不知道系统在加载哪些 engine，需显式调用 `hermes plugins list` 查看"

概念页 line 94 (对比表 "发现机制"): hermes-agent "有——目录扫描自动发现，`hermes plugins list` 可查看"

这两行存在**表面矛盾**——line 77 说 "用户不知道" 但 line 94 说 "可查看"。实际上 line 77 的含义是 "默认不可见，需主动查询"——这与 line 94 不直接矛盾但措辞容易误导。修正建议：统一为 "需显式查询（hermes plugins list）才能了解已加载的 engine 列表"。

## 汇总

| 类别 | 总计 | ✅ | ⚠️ | ❌ |
|------|------|-----|------|-----|
| OpenClaw 声明 | 10 | 6 | 4 | 0 |
| Hermes 声明 | 10 | 4 | 6 | 0 |
| 跨概念页一致性 | 5 | 2 | 3 | 0 |
| 绝对化语言 | 8 | 7 (低风险) | 1 (中风险) | 0 |
| **总计** | **33** | **19** | **14** | **0** |

### 关键发现

1. **本 Concept 页无硬事实错误**——0 处 ❌。但存在 14 处 ⚠️（无法从可用源独立验证的声明）。
2. **主要验证盲区**: openclaw 的 `registry.ts` (三层保护 + resolveContextEngine) 和 hermes 的 `plugins/context_engine/__init__.py` (discover_context_engines 函数细节) 在本仓库中没有对应的 wiki 节点文件。溯源表引用的这些文件行号无法二次验证。
3. **自相矛盾风险**: line 77 (用户不知道) vs line 94 (hermes plugins list 可查看) 措辞容易引起误解。
4. **接口 breadth 描述 quality**: 本页对两个 ContextEngine 接口的描述比维度文件更详细（如 openclaw 的 subagent 状态管理细节、hermes 的 4 必需 vs 8 可选方法分类）。这些额外细节可能来自直接源码阅读，但无法从 wiki 维度文件验证。
5. **对比维度选择质量高**——12 个维度覆盖了注册方式、激活方式、接口广度、发现机制、状态安全、扩展摩擦、切换成本、实现门槛、多实现并存、生命周期管理、兜底机制、核心取舍。维度选择全面且区分度高。
