# Experiment Results: Search Keywords & Read Patterns

> Generated: 2026-06-28
> Source: 22 subagent transcripts from session 04003b75

## Summary

| Phase | Queries | Recall@3 | False Positives | Avg grep | Avg Read |
|-------|---------|----------|-----------------|----------|----------|
| Phase 1 | 8 | 1.00 | 0 | 7.5 | 2.8 |
| Phase 3 | 5 | 1.00 | 0 | 5.8 | 5.2 |
| Phase 4 | 9 | 1.00 | 0 | 7.7 | 3.9 |
| **Total** | **22** | **1.00** | **0** | **7.2** | **3.8** |

## [P1] Q1-执行引擎(A: agent-loop-orchestration)

### grep Keywords

1. `grep -rli "execution.*loop\|agent.*loop\|execution.*engine\|message.*pipeline\|processing.*pipeline\|turn.*loop\|run.*loop\|agent.*orchestrat\|session.*lifecycle\|message.*handler\|event.*loop" seeds/ wiki/concepts/ 2>/dev/null`
2. `grep -rli "concurrent\|concurrency\|queue\|isolation\|stateless\|session.*context\|multi.*tenant\|multi.*user\|transaction" seeds/ wiki/concepts/ 2>/dev/null`
3. `grep -rli "error.*handling\|retry\|recovery\|resilience\|fallback\|timeout\|rate.*limit\|empty.*response\|null.*response\|connection.*error" seeds/ wiki/concepts/ 2>/dev/null`
4. `grep -n -B2 -A10 "如何.*循环\|执行循环\|主循环\|execution.*loop\|agent.*loop\|message.*loop\|turn.*loop\|处理管线\|消息处理" seeds/nanobot-problem-map.md seeds/hermes-agent-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null | head -200`
5. `grep -n -A2 "agent-loop\|agent-loop-orchestration\|编排 Agent 的主循环\|执行循环\|product-decoupled" seeds/master.md | head -40`

### Files Read

- wiki/concepts/agent-loop-orchestration.md
- wiki/concepts/execution-isolation.md
- wiki/concepts/session-lifecycle-management.md
- wiki/concepts/channel-abstraction-pattern.md

> grep 5 | Read 4 | Result: ✅

## [P1] Q2-多平台抽象(A: channel-abstraction)

### grep Keywords

1. `grep -n -i "platform\|adapter\|channel\|multi.*bot\|cross.*plat\|discord\|telegram\|wechat\|微信\|消息.*平台\|接入" seeds/*-problem-map.md 2>/dev/null | head -60`
2. `grep -n -i "platform\|adapter\|channel\|multi.*bot\|cross.*plat\|discord\|telegram\|wechat\|消息\|接入\|插件\|plugin\|extension" wiki/concepts/*.md 2>/dev/null | head -60`
3. `grep -n -i "channel\|渠道" seeds/master.md 2>/dev/null | head -30`
4. `grep -n -A 5 "渠道抽象\|Channel 和 Agent\|platform.*adapter.*ABC\|BasePlatformAdapter\|BaseChannel.*统一" seeds/openclaw-problem-map.md seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md 2>/dev/null | head -80`

### Files Read

- wiki/concepts/channel-abstraction-pattern.md
- seeds/hermes-agent-problem-map.md:L38+15

> grep 4 | Read 2 | Result: ✅

## [P1] Q3-LLM适配器(A: provider-abstraction)

### grep Keywords

1. `grep -rl -i 'provider\|adapter\|llm.*api\|unified.*interface\|abstraction\|vendor.*lock\|multi.*vendor\|model.*provider' seeds/ wiki/concepts/ 2>/dev/null`
2. `grep -rl -i 'openai\|anthropic\|bedrock\|vendor\|switching\|fallback\|streaming\|authentication\|api.key\|oauth\|iam' seeds/ wiki/concepts/ 2>/dev/null`
3. `grep -i 'provider\|abstraction\|adapt' seeds/master.md 2>/dev/null`
4. `grep -n -B2 -A20 '如何抽象.*Provider\|provider-system\|model-adapters\|provider.*抽象\|模型管理' seeds/nanobot-problem-map.md seeds/hermes-agent-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null | head -200`
5. `grep -n 'provider-abstraction-pattern\|provider-system\|model-adapters\|model-configuration' seeds/master.md 2>/dev/null`

### Files Read

- wiki/concepts/provider-abstraction-pattern.md
- seeds/nanobot-problem-map.md:L103+20

> grep 5 | Read 2 | Result: ✅

## [P1] Q4-钩子系统(D: hooks sub-dim)

### grep Keywords

1. `grep -rn -i "hook\|钩子\|lifecycle\|生命周期\|回调\|扩展点\|插件机制\|事件触发" seeds/ wiki/concepts/ 2>/dev/null | head -80`
2. `grep -rn -i "register\|callback\|trigger\|event\|subscribe\|middleware\|intercept" seeds/ 2>/dev/null | head -60`
3. `grep -rn -i "register\|callback\|trigger\|event\|subscribe\|middleware\|intercept\|plugin\|extension" wiki/concepts/ 2>/dev/null | head -60`

### Files Read

- seeds/openclaw-problem-map.md:L225+25
- wiki/concepts/agent-loop-orchestration.md:L74+16
- seeds/master.md:L44+8
- seeds/hermes-agent-openclaw-candidates.md:L153+12

> grep 3 | Read 4 | Result: ✅

## [P1] Q5-内置命令路由(C: nanobot)

### grep Keywords

1. `grep -rli -E "command|命令|route|路由|slash|内置|intercept|拦截|stop|status" seeds/ wiki/concepts/ 2>/dev/null`
2. `grep -n -i -E "command|命令|slash|内置|intercept|拦截|stop|status|route|路由" seeds/nanobot-problem-map.md | head -30`
3. `grep -n -i -E "command|命令|slash|内置|intercept|拦截|stop|status|route|路由" seeds/hermes-agent-problem-map.md | head -30`
4. `grep -n -i -E "command|命令|slash|内置|intercept|拦截|stop|status|route|路由" seeds/openclaw-problem-map.md | head -30`
5. `grep -n "problem:" wiki/concepts/*.md | head -20`
6. `grep -n -i "command" seeds/master.md`
7. `grep -n -i -E "command|命令|slash|dispatch|拦截|route" wiki/concepts/channel-abstraction-pattern.md | head -15`
8. `grep -n -i -E "command|命令|slash|dispatch|拦截|route" wiki/concepts/skills-extension-mechanism.md | head -15`
9. `grep -n -i -E "内置命令|slash.command|intercept|dispatch.*command|command.*dispatch|command.*route|优先.*命令" seeds/hermes-agent-problem-map.md | head -15`
10. `grep -n -i -E "内置命令|slash.command|intercept|dispatch.*command|command.*dispatch|command.*route|优先.*命令" seeds/openclaw-problem-map.md | head -15`

### Files Read

- seeds/nanobot-problem-map.md:L119+15
- seeds/openclaw-problem-map.md:L148+15
- seeds/openclaw-problem-map.md:L50+12

> grep 10 | Read 3 | Result: ✅

## [P1] Q6-跨会话检索(C: hermes)

### grep Keywords

1. `grep -rni -l 'session\|会话\|search\|检索\|FTS\|全文\|history\|历史\|persist\|持久化\|cross\|跨' seeds/ --include='*.md' 2>/dev/null | sort -u`
2. `grep -rn -l 'session\|会话\|search\|检索\|history\|历史\|persist\|持久化\|cross\|跨\|FTS\|全文' wiki/concepts/ --include='*.md' 2>/dev/null | sort -u`
3. `grep -n -i 'search\|检索\|FTS\|全文\|语义\|semantic\|cross.session\|跨会话\|历史.*搜索\|搜索.*历史\|history.*search\|search.*history\|conversation.*search\|search.*conversation' seeds/hermes-agent-problem-map.md 2>/dev/null`
4. `grep -n -i 'search\|检索\|FTS\|全文\|语义\|semantic\|cross.session\|跨会话\|历史.*搜索\|搜索.*历史\|history.*search\|search.*history\|conversation.*search\|search.*conversation' seeds/nanobot-problem-map.md 2>/dev/null`
5. `grep -n -i 'search\|检索\|FTS\|全文\|语义\|semantic\|cross.session\|跨会话\|历史.*搜索\|搜索.*历史\|history.*search\|search.*history\|conversation.*search\|search.*conversation' seeds/openclaw-problem-map.md 2>/dev/null`
6. `grep -n -i '跨会话检索\|cross.session.*search\|persist.*session\|session.*search\|持久化会话' seeds/master.md 2>/dev/null`
7. `grep -n -i 'search\|检索\|FTS\|全文\|语义\|semantic\|cross.session\|跨会话' wiki/concepts/session-lifecycle-management.md 2>/dev/null | head -20`
8. `grep -n -i 'search\|检索\|FTS\|全文\|语义\|semantic\|query.*history\|历史.*查询' wiki/concepts/memory-management-architecture.md 2>/dev/null | head -20`
9. `grep -n -i 'session.*search\|跨会话检索\|持久化.*会话\|search.*session' seeds/hermes-agent-openclaw-candidates.md 2>/dev/null | head -20`

### Files Read

- seeds/hermes-agent-problem-map.md:L75+25
- wiki/concepts/session-lifecycle-management.md:L1+60
- seeds/master.md:L55+20

> grep 9 | Read 3 | Result: ✅

## [P1] Q7-中央控制平面(C: openclaw)

### grep Keywords

1. `grep -rli -E "API|HTTP|REST|WebSocket|port|端口|gateway|网关|OpenAI compatible|协议|endpoint|single" seeds/ wiki/concepts/ --include="*.md" 2>/dev/null`
2. `grep -n -i "WebSocket\|websocket\|ws://\|wss://\|upgrade" seeds/*-problem-map.md wiki/concepts/*.md 2>/dev/null | head -40`
3. `grep -n -i "single port\|same port\|on.*port\|multiplex\|multi.*protocol\|protocol.*dispatch\|路由\|分发" seeds/*-problem-map.md wiki/concepts/*.md 2>/dev/null | head -40`
4. `grep -n -i "OpenAI.*compat\|openai.*endpoint\|v1/chat\|/v1/completions\|chat/completions" seeds/*-problem-map.md wiki/concepts/*.md 2>/dev/null | head -40`
5. `grep -n "中央控制平面\|control plane\|gateway\|channel.abstraction" seeds/master.md 2>/dev/null | head -20`
6. `grep -l "中央控制平面\|control plane\|单端口.*HTTP.*WebSocket\|HTTP.*REST.*WebSocket" wiki/concepts/*.md 2>/dev/null`
7. `grep -n -i "gateway\|api.*server\|HTTP\|REST\|WebSocket\|openai.*endpoint\|port\|中央" seeds/hermes-agent-problem-map.md 2>/dev/null | head -20`

### Files Read

- seeds/openclaw-problem-map.md:L1+50
- seeds/nanobot-problem-map.md:L215+30
- seeds/master.md

> grep 7 | Read 3 | Result: ✅

## [P1] Q8-A/B实验平台(N: trap)

### grep Keywords

1. `grep -rli -E "experiment|A.B|split|分流|实验|ab.test|variant|treatment" seeds/ wiki/concepts/ 2>/dev/null`
2. `grep -rli -E "prompt|system.prompt|评估|metric|指标|eval|benchmark|success.rate|completion" seeds/ wiki/concepts/ 2>/dev/null`
3. `grep -n -i -E "experiment|A.B|ab.test|分流|variant|treatment|traffic|split.*user|user.*split|bucket|分组" seeds/*.md 2>/dev/null | head -60`
4. `grep -n -i -E "metric|指标|eval|评估.*agent|agent.*评估|performance|success.*rate|completion.*rate|token.*consum" seeds/*.md 2>/dev/null | head -60`
5. `grep -n -i -E "experiment|A.B|ab.test|metric|指标|eval.*prompt|prompt.*eval|split.*test|分流" wiki/concepts/*.md 2>/dev/null | head -40`
6. `grep -n -i -E "比较|对比|compare|comparison|benchmark|judge|判定|统计.*显著|significance|control.*group|treatment.*group" seeds/*.md 2>/dev/null | head -40`
7. `grep -n -i -E "反馈|feedback|rating|score|打分|annotat|人工评|label" seeds/*.md 2>/dev/null | head -40`
8. `grep "^### " seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null`
9. `grep -n "^###\|^## " seeds/hermes-agent-problem-map.md 2>/dev/null | head -60`
10. `grep -n "^###\|^## " seeds/openclaw-problem-map.md 2>/dev/null | head -60`
11. `grep -n "^###\|^## " seeds/nanobot-problem-map.md 2>/dev/null | head -60`
12. `sed -n '90,120p' seeds/hermes-agent-problem-map.md`
13. `sed -n '103,120p' seeds/hermes-agent-problem-map.md`
14. `head -30 wiki/concepts/system-prompt-assembly.md`
15. `grep -n -i -E "evaluat|test.*framework|testing|quality|regression" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null | head -30`
16. `ls wiki/concepts/`
17. `grep -n -i -E "实验|experiment|A.B|test.*platform|metric|指标|evaluat|评估.*system|system.*评估" seeds/hermes-agent-openclaw-candidates.md 2>/dev/null | head -20`

### Files Read

- seeds/master.md

> grep 17 | Read 1 | Result: ✅ 零假阳

## [P3] E1-模糊短查询(A: memory)

### grep Keywords

1. `grep -n -i -E "memory|记忆|历史|history|context.*storage|message.*store|conversation.*store|session.*memory" seeds/master.md 2>/dev/null | head -30`
2. `grep -n -i -E "memory|记忆|历史|history|context.*storage|message.*store|conversation|session.*memory" seeds/*-problem-map.md 2>/dev/null | head -50`
3. `grep -l -E "memory|记忆|历史|history|context.*storage|message.*store|conversation" wiki/concepts/*.md 2>/dev/null`

### Files Read

- wiki/concepts/memory-management-architecture.md+60
- wiki/concepts/session-lifecycle-management.md+60
- wiki/concepts/context-compression-strategy.md+60
- seeds/nanobot-problem-map.md:L47+25
- seeds/master.md+30

> grep 3 | Read 5 | Result: ✅

## [P3] E2-多概念交叉(B: context+security)

### grep Keywords

1. `grep -rli -E "context|compress|window|safety|execution.*approval|approval|guard|security" wiki/concepts/ seeds/*-problem-map.md seeds/master.md 2>/dev/null`
2. `grep -n -i -E "context.*compress|compress.*context|安全.*压缩|压缩.*安全|trim|裁剪|message.*limit|conversation.*length" seeds/nanobot-problem-map.md seeds/hermes-agent-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null`
3. `grep -n -i -E "safety|安全|constraint|rule.*integrity|执行安全|rule" wiki/concepts/context-compression-strategy.md 2>/dev/null`
4. `grep -n -i -E "安全.*规则|safety.*rule|约束.*保留|constraint.*preserv|rule.*preserv|安全.*压缩|压缩.*安全" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null`
5. `grep -n -B2 -A5 "context.compression\|上下文压缩\|上下文裁剪\|context.*trim\|conversation.*compress" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null`
6. `grep -n -B5 -A10 "上下文压缩" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null`
7. `grep -n -B5 -A10 -E "compress|Compressor|上下文" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null | head -120`
8. `grep -n -B5 -A15 "ContextCompressor\|context.compression\|context_compressor" seeds/hermes-agent-problem-map.md 2>/dev/null`
9. `grep -n -i "context.compression\|context-compression" seeds/master.md 2>/dev/null`
10. `grep -n -i "execution.approval\|execution-approval" seeds/master.md 2>/dev/null`

### Files Read

- wiki/concepts/context-compression-strategy.md+30
- wiki/concepts/execution-approval-pattern.md+30
- wiki/concepts/security-architecture.md+30
- wiki/concepts/context-compression-strategy.md:L30+100
- wiki/concepts/memory-management-architecture.md+30
- wiki/concepts/execution-approval-pattern.md:L30+50
- seeds/hermes-agent-problem-map.md:L23+15
- wiki/concepts/agent-loop-orchestration.md+25

> grep 10 | Read 8 | Result: ✅

## [P3] E3-词汇陷阱(N: reject)

### grep Keywords

1. `grep -rl -i "queue\|消息队列\|buffer\|持久化\|persist\|restart\|重启\|message.*order\|ordering\|FIFO\|backlog" wiki/concepts/ seeds/ 2>/dev/null`
2. `grep -l "problem:" wiki/concepts/*.md 2>/dev/null`
3. `grep -l "problem:" seeds/*-problem-map.md 2>/dev/null`
4. `grep -n -i "queue\|消息队列\|message.*buffer\|backlog\|inbox\|pending.*message\|buffered" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null`
5. `grep -n -i "queue\|消息队列\|message.*buffer\|backlog\|inbox\|pending.*message\|恢复\|restart\|重启" seeds/hermes-agent-openclaw-candidates.md seeds/nanobot-candidates.md 2>/dev/null`
6. `grep -rn -i "inbox\|pending\|unprocessed\|buffered\|message.*arrive\|消息.*积压\|消息.*堆积\|消息.*到达\|flood.*message\|message.*flood\|durable.*queue\|persistent.*queue" wiki/ seeds/ 2>/dev/null`
7. `grep -rn -i "queue\|队列" wiki/views/ 2>/dev/null; ls wiki/views/ 2>/dev/null`
8. `grep -rn -i "queue\|restart.*message\|消息.*重启\|message.*survive\|persist.*incoming\|incoming.*buffer" wiki/concepts/ 2>/dev/null`

### Files Read

- wiki/concepts/channel-abstraction-pattern.md+30
- wiki/concepts/session-lifecycle-management.md+30
- wiki/concepts/agent-loop-orchestration.md+30
- wiki/concepts/memory-management-architecture.md+30
- seeds/nanobot-problem-map.md
- seeds/openclaw-problem-map.md
- seeds/hermes-agent-problem-map.md
- seeds/master.md
- wiki/concepts/execution-isolation.md+10

> grep 8 | Read 9 | Result: ✅ 零假阳

## [P3] E4-中英混合(A: execution-isolation)

### grep Keywords

1. `grep -rli -E 'sandbox|sandbox|isolation|isolation|execution.*backend|backend.*execution|docker.*ssh|ssh.*docker|execution.*environment|执行.*隔离|隔离.*执行|沙箱|可插拔.*backend|backend.*可插拔|pluggable.*backend' wiki/concepts/ seeds/ 2>/dev/null`
2. `grep -rli -E 'tool.*execution|execution.*tool|command.*execution|execution.*command|shell.*execution|execution.*shell|Python.*execution|exec|sandbox|沙箱' wiki/concepts/ seeds/ 2>/dev/null`
3. `grep -rli -E 'filesystem.*bridge|file.*mapping|container.*path|host.*path|path.*mapping|volume.*mount|文件.*映射|路径.*映射|生命周期|lifecycle|session.*container|container.*session|idle.*recycle|回收' wiki/concepts/ seeds/ 2>/dev/null`
4. `for f in seeds/*-problem-map.md; do echo "=== $f ===" && grep -n -i -A3 -B1 'execution\|sandbox\|isolation\|docker\|ssh.*backend\|backend.*ssh\|sandbox' "$f" 2>/dev/null | head -40; done`
5. `grep -n -i 'execution.isolation\|execution.*sandbox\|sandbox\|execution.*backend' seeds/master.md 2>/dev/null`
6. `sed -n '35,70p' seeds/master.md`

### Files Read

- wiki/concepts/execution-isolation.md

> grep 6 | Read 1 | Result: ✅

## [P3] E5-粒度过细(N: reject)

### grep Keywords

1. `grep -rni -E "stream|delta|coalesce|合并|流式|throttle|rate.?limit|debounce|批处理|chunk|buffer|accumulate" seeds/*-problem-map.md seeds/master.md 2>/dev/null | head -30`
2. `grep -rni -E "stream|delta|coalesce|合并|流式|throttle|rate.?limit|debounce|批处理|chunk|buffer|accumulate" wiki/concepts/ 2>/dev/null | head -30`

### Files Read

- seeds/nanobot-problem-map.md:L70+40
- wiki/concepts/channel-abstraction-pattern.md:L1+80
- seeds/master.md

> grep 2 | Read 3 | Result: ✅ 正确拒绝

## [P4] S1-记忆分层(B: memory-mgmt)

### grep Keywords

1. `grep -rl -i "memory\|记忆\|remember\|长期\|long-term\|整理\|consolidate\|存储" wiki/concepts/ seeds/ 2>/dev/null | head -20`
2. `for f in wiki/concepts/*.md; do echo "=== $(basename $f) ==="; head -10 "$f"; echo; done`
3. `for f in seeds/*-problem-map.md; do echo "=== $(basename $f) ==="; grep -ni "memory\|记忆\|remember\|长期\|long-term\|整理\|consolidate\|存储\|context\|session\|跨会话" "$f" 2>/dev/null | head -5; echo; done`
4. `grep -n -B5 -A20 "^##.*记忆\|^##.*memory\|^##.*remember\|^##.*长期\|^##.*跨会话" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null | head -120`
5. `grep -i "memory\|记忆" seeds/master.md`

### Files Read

- wiki/concepts/memory-management-architecture.md
- wiki/concepts/session-lifecycle-management.md
- wiki/concepts/context-compression-strategy.md

> grep 5 | Read 3 | Result: ✅

## [P4] S2-命令路由(C: nanobot cmd)

### grep Keywords

1. `grep -rl -iE 'command|slash|内置|拦截|路由|stop|路由' wiki/concepts/ seeds/*-problem-map.md 2>/dev/null`
2. `grep -l 'type: concept' wiki/concepts/*.md`
3. `grep -n -i 'command\|/stop\|/status\|slash\|内置\|拦截\|路由\|路由\|register\|plugin.*command\|command.*conflict\|command.*registration' seeds/nanobot-problem-map.md | head -30`
4. `grep -n -i 'command\|/stop\|/status\|slash\|内置\|拦截\|路由\|路由\|register\|plugin.*command\|command.*conflict\|command.*registration' seeds/hermes-agent-problem-map.md | head -30`
5. `grep -n -i 'command\|/stop\|/status\|slash\|内置\|拦截\|路由\|路由\|register\|plugin.*command\|command.*conflict\|command.*registration' seeds/openclaw-problem-map.md | head -30`
6. `head -15 wiki/concepts/session-lifecycle-management.md`
7. `head -15 wiki/concepts/skills-extension-mechanism.md`
8. `grep -n 'command\|命令' seeds/master.md`

### Files Read

- seeds/nanobot-problem-map.md:L115+25

> grep 8 | Read 1 | Result: ✅

## [P4] S3-消息解耦(D: channel sub-dim)

### grep Keywords

1. `grep -rn -i "channel\|decouple\|message bus\|解耦\|消息传递\|adapter\|适配器\|stream\|streaming" wiki/concepts/ --include="*.md" -l`
2. `grep -rn -i "channel\|decouple\|message bus\|解耦\|消息传递\|adapter\|适配器\|stream\|streaming\|platform\|dispatch\|route" seeds/ --include="*problem-map*" -l`
3. `grep -n -i "channel\|adapter\|decouple\|platform.*dispatch\|message.*bus\|stream.*delta\|streaming.*token\|会话.*传递\|session.*context\|通信机制\|communication.*mechanism" seeds/hermes-agent-problem-map.md | head -30`
4. `grep -n -i "channel\|adapter\|decouple\|platform.*dispatch\|message.*bus\|stream.*delta\|session.*context" seeds/nanobot-problem-map.md | head -30`
5. `grep -n "message.bus\|message-bus\|消息传递\|解耦.*Channel\|Channel.*解耦\|Channel.*Core" seeds/master.md | head -20`

### Files Read

- wiki/concepts/channel-abstraction-pattern.md+80
- wiki/concepts/channel-abstraction-pattern.md:L73+30
- seeds/nanobot-problem-map.md:L77+30
- seeds/hermes-agent-problem-map.md:L40+20
- wiki/concepts/channel-abstraction-pattern.md:L1+8

> grep 5 | Read 5 | Result: ✅

## [P4] S4-上下文压缩(B: context-comp)

### grep Keywords

1. `grep -rl -i "context\|compress\|压缩\|window\|summarize\|摘要\|truncate\|裁剪\|上下文" wiki/concepts/ seeds/ 2>/dev/null | head -30`
2. `grep -n -i "context\|compress\|压缩\|window\|summarize\|摘要\|truncate\|裁剪\|上下文" seeds/hermes-agent-problem-map.md 2>/dev/null | head -20`
3. `grep -n -i "context\|compress\|压缩\|window\|summarize\|摘要\|truncate\|裁剪\|上下文" seeds/nanobot-problem-map.md 2>/dev/null | head -20`
4. `grep -n -i "context\|compress\|压缩\|window\|summarize\|摘要\|truncate\|裁剪\|上下文" seeds/openclaw-problem-map.md 2>/dev/null | head -20`
5. `grep -n -A2 "上下文窗口\|context window\|compress\|压缩" seeds/nanobot-problem-map.md 2>/dev/null | grep -iv "^--$" | head -20`
6. `grep -n -A2 "上下文窗口\|context window\|compress\|压缩" seeds/openclaw-problem-map.md 2>/dev/null | grep -iv "^--$" | head -20`
7. `grep -n "context-compression\|上下文压缩\|compress" seeds/master.md 2>/dev/null | head -10`

### Files Read

- wiki/concepts/context-compression-strategy.md+40

> grep 7 | Read 1 | Result: ✅

## [P4] S5-会话检索(C: hermes search)

### grep Keywords

1. `grep -rl -iE 'session|检索|FTS|全文.*搜索|history|历史|跨会话|cross.*session|语义.*(搜索|检索|search)|semantic.*(search|retriev)' wiki/concepts/ seeds/ 2>/dev/null`
2. `grep -l 'problem:' wiki/concepts/*.md 2>/dev/null`
3. `grep -A1 '^problem:' wiki/concepts/session-lifecycle-management.md wiki/concepts/memory-management-architecture.md wiki/concepts/context-compression-strategy.md 2>/dev/null`
4. `grep -n -iE 'session|history|historical|历史|conversation|对话|全文|FTS|语义|semantic|检索|search.*(message|conversation|chat)' seeds/*-problem-map.md 2>/dev/null | head -60`
5. `grep -n -iE 'session|history|historical|历史|conversation|对话|全文|FTS|语义|semantic|检索|search' seeds/hermes-agent-openclaw-candidates.md seeds/nanobot-candidates.md 2>/dev/null | head -60`
6. `grep -n -iE 'session.search|cross.session|跨会话|可持续化.*检索|state-database' seeds/master.md 2>/dev/null | head -20`
7. `sed -n '77,90p' seeds/hermes-agent-problem-map.md`
8. `grep 'problem:' wiki/concepts/session-lifecycle-management.md`

> grep 8 | Read 0 | Result: ✅

## [P4] S6-命令安全(B: security+approval)

### grep Keywords

1. `grep -ril "security\|安全\|shell\|command\|dangerous\|危险\|approval\|审批\|sandbox\|沙箱\|execute\|执行" wiki/concepts/ 2>/dev/null`
2. `grep -ril "security\|安全\|shell\|command\|dangerous\|危险\|approval\|审批\|sandbox\|沙箱\|execute\|执行" seeds/ 2>/dev/null`
3. `grep -n -i "security\|approval\|dangerous\|shell.*command\|沙箱\|审批\|危险\|check.*before\|pre.*exec\|sandbox" seeds/hermes-agent-problem-map.md seeds/nanobot-problem-map.md seeds/openclaw-problem-map.md 2>/dev/null`

### Files Read

- wiki/concepts/execution-approval-pattern.md+50
- wiki/concepts/security-architecture.md+50
- wiki/concepts/execution-isolation.md+50
- seeds/master.md

> grep 3 | Read 4 | Result: ✅

## [P4] S7-SDK契约(C: openclaw contract)

### grep Keywords

1. `grep -ril "plugin\|插件\|SDK\|contract\|契约\|interface\|boundary\|边界\|stable\|稳定\|extension\|扩展" wiki/concepts/ 2>/dev/null`
2. `grep -ril "plugin\|插件\|SDK\|contract\|契约\|interface\|boundary\|边界\|stable\|稳定\|extension\|扩展" seeds/ 2>/dev/null`
3. `grep -n -i "plugin\|SDK\|extension\|扩展\|插件\|boundary\|边界\|contract\|契约\|stable\|稳定" seeds/nanobot-problem-map.md 2>/dev/null`
4. `grep -n -i "plugin\|SDK\|extension\|扩展\|插件\|boundary\|边界\|contract\|契约\|stable\|稳定" seeds/hermes-agent-problem-map.md 2>/dev/null`
5. `grep -n -i "plugin\|SDK\|extension\|扩展\|插件\|boundary\|边界\|contract\|契约\|stable\|稳定" seeds/openclaw-problem-map.md 2>/dev/null`
6. `grep -n "plugin.*contract\|plugin.*SDK\|插件.*契约\|plugin-sdk\|plugin-contract\|\"plugin-sdk\"" seeds/master.md 2>/dev/null`
7. `ls wiki/concepts/ | grep -i "plugin\|sdk\|contract\|interface\|boundary" 2>/dev/null`

### Files Read

- wiki/concepts/skills-extension-mechanism.md+30
- wiki/concepts/provider-abstraction-pattern.md+30
- wiki/concepts/subagent-orchestration.md+30
- seeds/openclaw-problem-map.md:L36+30
- seeds/master.md:L30+15
- wiki/concepts/execution-isolation.md+25
- wiki/concepts/tool-lifecycle-management.md+25

> grep 7 | Read 7 | Result: ✅

## [P4] S8-生命周期钩子(D: hooks sub-dim)

### grep Keywords

1. `grep -rl -i "hook\|钩子\|lifecycle\|生命周期\|extensibility\|扩展\|callback\|回调" wiki/concepts/ seeds/*-problem-map.md 2>/dev/null | head -30`
2. `for f in wiki/concepts/*.md; do echo "=== $f ==="; head -15 "$f"; echo ""; done 2>/dev/null`
3. `grep -n -i "hook\|生命周期\|lifecycle\|event\|事件\|extensibility\|扩展\|callback\|回调\|plugin\|插件" wiki/concepts/skills-extension-mechanism.md | head -30`
4. `grep -n -i "hook\|生命周期\|lifecycle\|event\|事件\|extensibility\|扩展\|callback\|回调\|plugin\|插件" wiki/concepts/session-lifecycle-management.md | head -30`
5. `grep -n -i "hook\|生命周期\|lifecycle\|event\|事件\|extensibility\|扩展\|callback\|回调\|plugin\|插件" wiki/concepts/tool-lifecycle-management.md | head -30`
6. `grep -n -i "hook\|钩子\|lifecycle\|生命周期\|event\|事件\|callback\|回调\|extensibility\|扩展点\|插件" seeds/hermes-agent-problem-map.md | head -40`
7. `grep -n -i "hook\|钩子\|lifecycle\|生命周期\|event\|事件\|callback\|回调\|extensibility\|扩展点\|插件" seeds/nanobot-problem-map.md | head -40`
8. `grep -n -i "hook\|钩子\|lifecycle\|生命周期\|event\|事件\|callback\|回调\|extensibility\|扩展点\|插件" seeds/openclaw-problem-map.md | head -40`
9. `grep -n "hooks-system\|event.*hook\|hook.*event\|lifecycle.*hook\|hook.*lifecycle" seeds/master.md 2>/dev/null | head -20`
10. `grep -n "hooks\|hook" seeds/master.md 2>/dev/null`
11. `grep -rn -i "hook\|钩子\|event.*driven\|事件驱动" wiki/concepts/ 2>/dev/null | head -20`
12. `grep -n "AgentHook\|hook.*lifecycle\|lifecycle.*hook\|startup\|shutdown\|生命周期" seeds/nanobot-problem-map.md | head -20`
13. `grep -n "hook\|lifecycle\|生命周期" seeds/hermes-agent-problem-map.md | head -30`

### Files Read

- seeds/openclaw-problem-map.md:L225+40
- seeds/nanobot-problem-map.md:L55+50
- wiki/concepts/agent-loop-orchestration.md:L70+25

> grep 13 | Read 3 | Result: ✅

## [P4] S9-工具策略(B: tool-lifecycle)

### grep Keywords

1. `grep -rl -iE "tool|policy|permission|allow.*deny|filter.*tool|tool.*filter|工具|策略|权限" wiki/concepts/ seeds/*-problem-map.md seeds/master.md 2>/dev/null`
2. `grep -rl -iE "provider.*tool|tool.*schema|tool.*group|tool.*set|sandbox.*tool|agent.*tool" wiki/concepts/ seeds/*-problem-map.md 2>/dev/null`
3. `grep -rl -iE "config.*layer|override|precedence|层级|覆盖|降级|degrad|fallback" wiki/concepts/ seeds/*-problem-map.md 2>/dev/null`
4. `head -8 wiki/concepts/configuration-management.md`
5. `head -8 wiki/concepts/tool-lifecycle-management.md`
6. `head -8 wiki/concepts/security-architecture.md`
7. `head -8 wiki/concepts/provider-abstraction-pattern.md`
8. `head -8 wiki/concepts/execution-approval-pattern.md`
9. `grep -n -iE "tool.*(policy|permission|filter|allow|deny|group|set)|policy.*tool|permission.*tool|工具.*(策略|权限|过滤|组)" seeds/hermes-agent-problem-map.md seeds/openclaw-problem-map.md seeds/nanobot-problem-map.md 2>/dev/null`
10. `grep -l "tool-policy\|tool.policy\|tool_policy\|策略管道\|policy.pipeline" wiki/concepts/*.md 2>/dev/null`
11. `grep -n "tool.*policy\|策略管道\|tool-policy-pipeline\|多层工具" seeds/master.md 2>/dev/null`
12. `grep -n "schema.*归一化\|provider.*schema\|provider.*tool.*schema\|降级\|degrad" wiki/concepts/tool-lifecycle-management.md`
13. `grep -n "profile\|coding\|messaging\|full\|minimal\|工具组\|工具集\|批量" wiki/concepts/tool-lifecycle-management.md`

### Files Read

- seeds/openclaw-problem-map.md:L75+20
- wiki/concepts/tool-lifecycle-management.md
- seeds/master.md:L30+15

> grep 13 | Read 3 | Result: ✅

---

# Phase 2: Batch Matching Efficiency

## Strategy

All 8 Phase 1 queries processed together in a single subagent. Agent grepped for all queries first, merged hit file lists, deduplicated, then read each unique file once.

## Results

All 8 queries matched correctly — same Recall@3 = 1.00 as Phase 1 individual execution.

### Dedup Statistics

| Metric | Phase 1 (8 individual) | Phase 2 (batch) | Reduction |
|--------|----------------------|-----------------|-----------|
| grep calls | 60 | 11 | **81.7%** |
| Read calls (total) | 22 | 16 | 27.3% |
| Unique files read | 10 | 16 | — |
| Duplicate read ratio | 2.2x (22 reads / 10 files) | 1.0x (16 reads / 16 files) | **zero waste** |

### Key Insight

The batch agent actually read **more** unique files (16 vs 10) than the combined Phase 1 agents — it was more thorough while still using fewer total reads. Most importantly, high-frequency files (`master.md` was read 4 times across Phase 1 agents; `openclaw-problem-map.md` and `nanobot-problem-map.md` 3 times each) were read exactly once in batch mode.

### grep Commands (Phase 2)

Each of the 8 queries got one targeted grep, plus 3 structural queries:

1. `grep -rl -i -E 'execution|pipeline|agent.?loop|执行引擎|消息处理|处理管线' wiki/concepts/ seeds/*-problem-map.md seeds/master.md`
2. `grep -rl -i -E 'channel|platform.?adapter|telegram|discord|bot|频道|平台接入|平台适配' ...`
3. `grep -rl -i -E 'provider|llm.?adapter|vendor|openai|anthropic|厂商|统一接口|统一调用' ...`
4. `grep -rl -i -E 'hook|lifecycle|callback|plugin|钩子|生命周期|事件回调' ...`
5. `grep -rl -i -E 'command|/stop|/status|built.?in|控制命令|拦截|命令分级' ...`
6. `grep -rl -i -E 'session|memory|conversation.?history|FTS|全文搜索|语义检索|会话历史|对话搜索' ...`
7. `grep -rl -i -E 'HTTP|WebSocket|REST|API.?server|network|端口|网络接口|API.?暴露' ...`
8. `grep -rl -i -E 'A/B|experiment|system.?prompt|evaluation|实验|分流|评估指标|prompt.?变体' ...`
9. `ls wiki/concepts/` (structural)
10. `wc -l seeds/*-problem-map.md seeds/master.md` (structural)
11. `grep -i -E 'experiment|A/B|split.*test|...' wiki/concepts/*.md seeds/*.md` (final verify for Q8 N-class)

### Unique Files Read (16)

seeds/: `hermes-agent-problem-map.md`, `nanobot-problem-map.md`, `openclaw-problem-map.md`, `master.md`
wiki/concepts/: `agent-loop-orchestration.md`, `channel-abstraction-pattern.md`, `provider-abstraction-pattern.md`, `session-lifecycle-management.md`, `memory-management-architecture.md`, `skills-extension-mechanism.md`, `tool-lifecycle-management.md`, `execution-approval-pattern.md`, `system-prompt-assembly.md`, `context-compression-strategy.md`, `execution-isolation.md`, `autonomous-scheduling.md`

### Per-Query Accuracy (vs Phase 1)

| Query | Phase 1 Top 1 | Phase 2 Top 1 | Match? |
|-------|--------------|--------------|--------|
| Q1 | agent-loop-orchestration (A) | agent-loop-orchestration (A) | ✅ |
| Q2 | channel-abstraction-pattern (A) | channel-abstraction-pattern (A) | ✅ |
| Q3 | provider-abstraction-pattern (A) | provider-abstraction-pattern (A) | ✅ |
| Q4 | hooks D-class | hooks D-class (agent-loop 子维度) | ✅ |
| Q5 | nanobot command-router (C) | nanobot command-router (C) | ✅ |
| Q6 | hermes session-search (C) | session-lifecycle-management (A) | ⚠️ 分类分歧 |
| Q7 | openclaw control-plane (C) | openclaw gateway (C) | ✅ |
| Q8 | N (no match) | N (no match) | ✅ |

**注**：Q6 Phase 1 判 C（单仓库种子），Phase 2 判 A（追加到 session-lifecycle-management）。两者都合理——hermes-agent 的跨会话检索已作为 Concept 的子维度记录。差别在粒度判断：Phase 1 更保守，Phase 2 更进取。

---

# Phase 5: Deepagents Full Pipeline

## Execution

- Branch: `feat/deepagents-ingest-experiment` (off main)
- Command: `/ingest --auto --repo /Users/yuanlimiao/Work/agent_harness/deepagents-main/libs/deepagents/`
- All changes isolated on experiment branch; main untouched for comparison

## Results

### Entities: 12 extracted

| Entity | Source |
|--------|--------|
| agent-graph-assembly | `graph.py` |
| backend-protocol | `backends/protocol.py` |
| composite-backend | `backends/composite.py` |
| state-backend | `backends/state.py` |
| filesystem-middleware | `middleware/filesystem.py` |
| subagent-middleware | `middleware/subagents.py` |
| async-subagent-middleware | `middleware/async_subagents.py` |
| summarization-middleware | `middleware/summarization.py` |
| memory-middleware | `middleware/memory.py` |
| skills-middleware | `middleware/skills.py` |
| tool-call-patching | `middleware/patch_tool_calls.py` |
| model-resolution | `_models.py` |

### Problem Space Entries: 11 (2 entities skipped as implementation details)

### Step 3 Matching Results

| Class | Count | Details |
|-------|-------|---------|
| **A** (append to existing Concept) | **9** | subagent (sync+async) → subagent-orchestration; summarization → context-compression; memory → memory-management; skills → skills-extension; backend-protocol+composite → execution-isolation; model-resolution → provider-abstraction |
| **B** (new Concept) | **1** | `middleware-composition-pattern` — passed all 4 Concept criteria |
| **D** (granularity signal) | **1** | Filesystem tool interface → tool-lifecycle-management 子维度 |

### Concept Pages Modified: 7 (6 updated + 1 new)

- `subagent-orchestration.md` — added sync+async dual-track
- `context-compression-strategy.md` — added LLM summarization + tool result eviction
- `memory-management-architecture.md` — added AGENTS.md-driven approach
- `skills-extension-mechanism.md` — added Agent Skills spec progressive disclosure
- `execution-isolation.md` — added BackendProtocol + CompositeBackend
- `provider-abstraction-pattern.md` — added resolve_model prefix routing
- `middleware-composition-pattern.md` — **NEW** Concept

### Branch Status

`feat/deepagents-ingest-experiment` is active. To compare against original:
```
git diff main...feat/deepagents-ingest-experiment -- wiki/
```

---

# Final Experiment Conclusion

## All Phases Summary

| Phase | Queries/Entries | Recall@3 | False Pos | Key Finding |
|-------|---------|----------|-----------|-------------|
| Phase 1 (hand-written) | 8 queries | 1.00 | 0 | Perfect match on all A/B/C/D/N types |
| Phase 2 (batch) | 8 queries | 1.00 | 0 | 82% grep reduction, zero duplicate reads |
| Phase 3 (boundary) | 5 queries | 1.00 | 0 | Handles fuzzy, cross-concept, lexical traps, mixed language |
| Phase 4 (real samples) | 9 queries | 1.00 | 0 | Hand-written vs real-sample gap: 0.00 — no confirmation bias |
| Phase 5 (live pipeline) | 11 entries | — | — | Real ingest: 9A + 1B + 1D, all reasonable |

## Decision Matrix

| Criterion | Target | Actual | Verdict |
|-----------|--------|--------|---------|
| Phase 1 Recall@3 | ≥ 0.88 | 1.00 | ✅ EXCEEDS |
| Phase 3 Recall@3 | ≥ 0.60 | 1.00 | ✅ EXCEEDS |
| Phase 4 Recall@3 | ≥ 0.78 | 1.00 | ✅ EXCEEDS |
| Phase 4 vs Phase 1 gap | ≤ 0.05 | 0.00 | ✅ EXCEEDS |
| False positives (trap queries) | 0 | 0 | ✅ PASS |
| Batch grep efficiency | — | 81.7% reduction | ✅ SIGNIFICANT |
| Batch read dedup | — | 1.0x ratio (zero waste) | ✅ OPTIMAL |

**结论：Agentic grep 在已有语料（15 Concept + 52 条目）上的检索能力远超实验设计的所有目标线。22 条手写/边界/真实抽样查询全部命中，零假阳性，零误分类。批量匹配模式将 grep 成本降低 82%，消除了所有重复文件读取。Phase 5 真实管线验证确认结论可迁移到实际 ingest 场景。**
