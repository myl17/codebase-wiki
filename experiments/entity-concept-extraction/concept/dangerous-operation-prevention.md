# Dangerous Operation Prevention / 危险操作防护

## 问题陈述

在 agent 框架中，LLM 可以生成并执行任意 shell 命令、调用系统级工具。如何可靠地防止危险操作执行——同时不因过度保守而阻碍正常开发工作流？

这个问题可以拆为三个子问题：
1. **什么算危险？** —— 不同场景下对"危险"的定义不同：删除系统文件是危险的，但 `rm -rf node_modules` 是日常操作；chmod 777 是危险的，但 chmod +x build.sh 是正常需求。
2. **在哪个环节拦截？** —— 在 LLM 看到工具之前按 allowlist 过滤掉高危工具，还是在 LLM 决定调用后在执行前逐条检查命令内容？
3. **人何时参与？** —— 每条命令都让用户审批会产生审批疲劳（alert fatigue）；完全自动化又可能漏过高危操作。approval 的粒度和持久化策略怎么设计？

## 已知答案图谱

**openclaw** 采用双层防御：工具可见性过滤（pre-LLM）+ exec 命令审批（pre-exec），两层的机制和目的不同。

**hermes** 采用单层但三层递进的审批：YOLO bypass → aux LLM 自动评估 → 人工交互审批（pre-exec），所有防御集中在命令执行前的最后一道门。

两者不是竞争关系（选择 A 还是 B），而是**互补关系**（在不同环节加固，可组合）。详见下文。

## 跨仓库对比

### 防御层位置

| | openclaw | hermes |
|---|---|---|
| **pre-LLM（工具可见性）** | 7 层 allowlist/denylist pipeline 过滤工具集，LLM 看不到无权工具 | 无（LLM 可见所有工具，事后在命令执行前拦截） |
| **pre-exec（命令审批）** | exec 命令走 allowlist 匹配 + safeBins + skill trust + human approval | 44 种危险模式正则 + tirith 安全扫描 + aux LLM 评估 + 交互审批 |
| **post-exec（事后审计）** | 无 | 无 |

### 检测机制

| | openclaw | hermes |
|---|---|---|
| **工具可见性过滤** | 基于工具名的 glob pattern allowlist/denylist，7 层叠加（profile → provider profile → global → global provider → agent → agent provider → group）。每层独立配置，最终可见工具 = 所有层的交集 | N/A |
| **命令危险检测** | 基于可执行文件的 allowlist 匹配 + safeBin 白名单（如 jq/cut/uniq/head/tail/tr/wc 等只读文本处理工具） + skill trust 索引。结构化命令分析：解析 argv、解析 shell wrapper 嵌套、解析 shell chain（&&/||/;）。不是基于"什么危险"的签名匹配，而是基于"什么安全"的 allowlist | 44 种正则模式覆盖：文件系统破坏（rm/chmod/chown/mkfs/dd/tee）、SQL 破坏（DROP/DELETE/TRUNCATE）、系统服务控制（systemctl/kill/pkill）、shell 注入（curl\|sh/heredoc/process substitution）、git 破坏（reset --hard/force push/clean -f/branch -D）、gateway 自保护（hermes 进程终止）、敏感路径写入（/etc/、~/.ssh、.hermes/.env） |
| **辅助安全扫描** | 无外部扫描器 | tirith 安全规则引擎，检查命令内容级的安全问题（secrets、注入等），发现与危险模式合并后统一审批 |
| **辅助 LLM 评估** | 无 | aux LLM（小模型）做三级判断：approve（明显安全）/ deny（明确危险）/ escalate（不确定，转人工） |
| **Unicode/ANSI 混淆防护** | N/A（基于可执行文件路径匹配，不依赖命令文本内容） | `_normalize_command_for_detection()` 剥离 ANSI 转义序列、null 字节、NFKC Unicode 标准化，防止混淆绕过 |

### 审批流程

| | openclaw | hermes |
|---|---|---|
| **触发条件** | exec 类工具被 LLM 调用且命令不在 allowlist/safeBins 中 | 命令匹配危险正则模式 或 tirith 发现安全风险 |
| **审批协议** | 两阶段协议：`registerExecApprovalRequest`（注册审批请求）→ `waitForExecApprovalDecision`（阻塞等待，默认 timeout 2 分钟（120,000ms））。支持 host/gateway 双路径 | 三层递进：YOLO/容器/off → 放行；aux LLM（smart mode）→ 自动 approve/deny/escalate；Manual → 合并所有发现一次性交互审批 |
| **Gateway 阻塞机制** | FIFO 队列 + 异步回调，agent 线程等待 /approve 或 /deny | FIFO 队列 + threading.Event，agent 线程等待 /approve 或 /deny（与 openclaw 相同模式） |
| **审批选项** | allow / deny（二元），支持 `allow-always` 持久化 | once / session / always / deny（四元），tirith 发现时不允许 always（防止对内容级安全问题做永久白名单） |
| **持久化** | `allow-always` 写入 exec allowlist，下次同路径命令自动通过 | `always` 写入 config.yaml 的 `command_allowlist`，跨会话持久化 |
| **自动化 bypass** | 无 YOLO 模式；容器环境（docker 等）自动跳过审批 | --yolo 全局跳过；容器环境自动跳过；`approvals.mode=off` 全局关闭 |

### 架构根本差异

openclaw 和 hermes 最根本的差异不是「谁更安全」，而是**对 LLM 的信任模型不同**：

- **openclaw**：不信任 LLM 能判断什么工具该用、什么不该用。在 LLM 看到工具之前就做完过滤——LLM 甚至不知道有它不该调用的工具存在。这是一种**能力剥夺型**防御：不给 LLM 犯错的机会。
- **hermes**：信任 LLM 做任务规划，但不信任 LLM 生成的每条命令都安全。让 LLM 看见所有工具以保持灵活性，但在执行前逐条审查命令内容。这是一种**执行审计型**防御：允许 LLM 尝试任何操作，但在执行前检查。

这决定了它们对「危险」的定义方式也截然不同：
- openclaw：危险 = 工具本身（exec 类工具是危险的，但给 exec 配置 allowlist 后它只执行安全命令）
- hermes：危险 = 命令内容（工具无所谓危险不危险，危险的是特定命令签名）

## 设计权衡

### 工具可见性过滤 vs 命令内容检测

**openclaw 的 pre-LLM 过滤（工具级）**：
- 优点：LLM 看不到无权工具，从根本上无法尝试危险操作。减少 LLM context 中的工具描述 token，降低 prompt 成本。工具级粒度使策略管理简单——"agent A 可以用 exec，agent B 不可以"。
- 缺点：粗粒度。如果 exec 工具被允许，LLM 可以执行任何命令——除非进一步在 pre-exec 层做 allowlist 控制。这就是为什么 openclaw 需要双层防御：工具策略管「能不能用 exec」，exec allowlist 管「能执行什么命令」。

**hermes 的 pre-exec 检测（命令级）**：
- 优点：细粒度。同一个工具（terminal_tool），安全命令直接放行，危险命令触发审批。不需要提前知道所有安全命令的列表。
- 缺点：正则模式有盲区。44 种模式覆盖了已知攻击向量，但无法覆盖所有未来变种。`python -c "print('hello')"` 被标记为危险（"script execution via -c flag"），产生 false positive。aux LLM 的 smart 模式旨在降低这种 false positive 的审批负担。

### 核心权衡：安全 vs 灵活性 vs 审批疲劳

```
高安全 ───────────────────────────────────────────── 高灵活
  │                                                    │
  │  openclaw pre-LLM 工具级过滤                       │
  │  （不给你武器，你就不能伤人）                        │
  │                                                    │
  │           openclaw pre-exec allowlist               │
  │           （给了武器，但子弹是橡皮的）                │
  │                                                    │
  │                    hermes pre-exec 正则 + tirith    │
  │                    （给你真枪，但每发子弹要审批）      │
  │                                                    │
  │                              hermes aux LLM smart   │
  │                              （审批太累，雇个门卫）   │
  │                                                    │
  ├────────────────────────────────────────────────────┤
  │                              hermes --yolo          │
  │                              （不审批，信任 LLM）    │
  └────────────────────────────────────────────────────┘
```

理想组合可能是：openclaw 的工具级过滤（粗粒度能力划分）+ hermes 的命令级检测（细粒度安全审查）。两者目前没有直接集成。

### 审批持久化的风险

两个系统都支持「永久允许」：
- openclaw `allow-always`：下次同路径 + 同参数组合自动通过。相对安全，因为限定的是具体的命令路径。
- hermes `always`：下次匹配同一正则模式即自动通过。风险更大——允许「所有 shell -c 调用」意味着任何包装在 `sh -c` 里的危险命令也会通过。

hermes 对 tirith 发现不允许 `always` 是一个好的安全边界：正则模式可以白名单（结构已知），但内容级安全发现（tirith）不能（每次内容不同）。

## 溯源

### 源码验证

**openclaw tool policy pipeline** 在 `src/agents/tool-policy-pipeline.ts` 中实现：
- `buildDefaultToolPolicyPipelineSteps()`（第 39-89 行）构建 7 层 step 数组
- `applyToolPolicyPipeline()`（第 92-157 行）按序迭代各层，跳过无策略的层（pass-through），对有策略的层调用 `filterToolsByPolicy()`
- 过滤逻辑在 `src/agents/pi-tools.policy.ts`：denylist 优先，无 allow 条目时隐式 allow-all，有 allow 条目时只允许匹配项

**openclaw exec approval** 在 `src/agents/bash-tools.exec-approval-request.ts` 中实现：
- 两阶段协议：`registerExecApprovalRequest()`（注册）→ `waitForExecApprovalDecision()`（阻塞等待）
- 命令分析在 `src/infra/exec-approvals-allowlist.ts`：`evaluateShellAllowlist()` 解析 shell 命令链，逐段匹配 allowlist/safeBins/skill trust
- safeBins 机制：预定义的「安全二进制文件」列表（jq/cut/uniq/head/tail/tr/wc 等只读文本处理工具），在可信路径上的调用自动放行

**hermes dangerous patterns** 在 `tools/approval.py:75-138` 中定义：
- 44 个正则模式，每个附带人类可读描述作为 approval key
- 向后兼容：旧版 regex-derived key 与新 description key 通过 `_PATTERN_KEY_ALIASES` 双向映射（第 140-161 行）
- 规范化管道：`_normalize_command_for_detection()`（第 168-183 行）在匹配前剥离 ANSI、null 字节、NFKC Unicode 标准化
- 审批入口：`check_all_command_guards()`（第 693-922 行）统一执行 tirith + 危险模式检查，合并发现后走三层审批

### Entity 页
- [[openclaw-tool-policy]]
- [[hermes-approval-system]]

### 关键文件索引
- `openclaw/src/agents/tool-policy-pipeline.ts` — 7 层策略管线 + `applyToolPolicyPipeline()`
- `openclaw/src/agents/tool-policy.ts` — 策略类型定义、`ownerOnly` 访问控制、`analyzeAllowlistByToolType()`
- `openclaw/src/agents/pi-tools.policy.ts` — `filterToolsByPolicy()`、`makeToolPolicyMatcher()`（denylist 优先的 glob 匹配逻辑）
- `openclaw/src/agents/bash-tools.exec-approval-request.ts` — exec 审批两阶段协议
- `openclaw/src/infra/exec-approvals-allowlist.ts` — shell 命令 allowlist 评估、safeBins 验证、skill trust
- `hermes-agent/tools/approval.py:75-138` — `DANGEROUS_PATTERNS`（44 个正则模式定义）
- `hermes-agent/tools/approval.py:168-197` — 命令规范化 + `detect_dangerous_command()`
- `hermes-agent/tools/approval.py:534-583` — `_smart_approve()`（aux LLM 风险评估）
- `hermes-agent/tools/approval.py:586-659` — `check_dangerous_command()`（原审批入口）
- `hermes-agent/tools/approval.py:693-922` — `check_all_command_guards()`（综合审批入口）
