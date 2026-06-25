# Performance Tradeoffs — Hermes Agent 候选权衡清单

## 序号说明
- 每个权衡必须同时声明「优化了什么」和「牺牲了什么」
- 源码证据附带具体行号（基于已读源码）

---

## 1. agent - Anthropic Prompt Caching (system_and_3 策略)
   - 优化了什么：多轮对话中缓存 token 成本降低约 75%（缓存的 prompt token 价格为全价的 25%）
   - 牺牲了什么：Anthropic 最多支持 4 个 cache_control 断点，其中 3 个分配给最近的非 system 消息。长对话时超过 3 轮的历史无法被缓存，命中率随对话增长而下降
   - 源码证据：^agent/prompt_caching.py:1-9, agent/prompt_caching.py:63-71

## 2. agent - ContextCompressor 有损上下文压缩
   - 优化了什么：延长对话能力，允许超过模型 token 限制的超长会话继续运行
   - 牺牲了什么：
     a) 信息保真度：中间轮次被有损摘要替代，细节（如确切命令行输出）可能丢失
     b) 延迟：每次压缩需要额外一次 LLM 调用来生成摘要
     c) 工具结果被裁剪为单行摘要（如 `[terminal] ran 'npm test' -> exit 0, 47 lines output`），丢失完整输出
     d) 防抖动保护：连续 2 次低效压缩（每次节省<10%）后完全跳过压缩，上下文可能继续膨胀
   - 源码证据：^agent/context_compressor.py:185-194, agent/context_compressor.py:307-327, agent/context_compressor.py:333-464, agent/context_compressor.py:50-54

## 3. agent - Smart Model Routing (cheap-model 路由)
   - 优化了什么：将简单、短小的用户消息路由到更便宜的模型，降低 API 成本
   - 牺牲了什么：保守的启发式（最大 160 字符、28 个单词、无代码块/URL/复杂关键词）意味着绝大多数对话轮次仍走主模型。任何含 `debug`、`implement`、`refactor`、`terminal`、`test` 等关键词的消息不论复杂度均被判定为"复杂"，错过了一部分可降级的机会
   - 源码证据：^agent/smart_model_routing.py:62-107

## 4. agent - NousRateGuard 跨会话速率限制共享
   - 优化了什么：消除 429 重试放大效应（每个 429 最多触发 3 SDK 重试 x 3 Hermes 重试 = 9 次额外 API 调用），通过共享文件记录限流状态使所有会话（CLI、gateway、cron、auxiliary）共享感知
   - 牺牲了什么：基于文件系统的轮询而非实时通知——会话间信息传播依赖定时读取 JSON 文件，可能存在短暂的过时状态窗口（限流刚解除但文件尚未清理）
   - 源码证据：^agent/nous_rate_guard.py:1-11, agent/nous_rate_guard.py:138-159

## 5. agent - CredentialPool 多凭据故障转移
   - 优化了什么：提高可用性——同 provider 多个凭据通过 fill_first/round_robin/random/least_used 策略实现故障转移；exhausted 凭据冷却 1 小时后可重试
   - 牺牲了什么：
     a) 状态管理复杂度：每个凭据追踪 last_status / last_error_code / last_error_reset_at / request_count，增加了持久化和恢复的代码量
     b) 凭据粘性问题：fill_first 策略下首个凭据会被过度使用直至耗尽，其他凭据空闲
   - 源码证据：^agent/credential_pool.py:60-75

## 6. agent - Auxiliary Client 多后备链
   - 优化了什么：辅助任务（压缩摘要、session 搜索、网页提取、vision 分析）不会因单一 provider 不可用而中断，最多 7 级回退链
   - 牺牲了什么：每个后备尝试都是失败的 API 调用，增加了延迟和成本；402/429 错误会触发自动回退到下一个 provider，可能无意间在用户不知情的情况下切换到更贵的 provider
   - 源码证据：^agent/auxiliary_client.py:1-35

## 7. hermes_state - SQLite WAL 模式 + 应用层写重试
   - 优化了什么：WAL 模式支持并发读（gateway 多平台 + CLI 会话 + worktree agent），FTS5 全文搜索所有会话消息
   - 牺牲了什么：
     a) 写竞争：SQLite 超时仅 1 秒，写操作依赖应用层 20-150ms 随机抖动重试（最多 15 次，最坏情况 ~2.25 秒）来打破 convoy 效应
     b) WAL 文件增长：每 50 次写入触发一次 PASSIVE WAL checkpoint，高负载下 WAL 可能显著增长
   - 源码证据：^hermes_state.py:123-155, hermes_state.py:164-199

## 8. tools - 三层工具结果持久化
   - 优化了什么：保护上下文窗口不过载——单工具输出 >100K 字符或单轮累计 >200K 字符时溢出到沙箱临时文件
   - 牺牲了什么：
     a) 信息可发现性：模型只能看到 1500 字符预览 + 文件路径引用，需要额外 read_file 调用才能看到完整内容，浪费 token 和轮次
     b) read_file 豁免：read_file 阈值固定为无穷大（避免无限循环），意味着单次读取可能将大量内容直接注入上下文
   - 源码证据：^tools/tool_result_storage.py:1-23, tools/budget_config.py:1-18

## 9. tools - CheckpointManager 影子 Git 仓库快照
   - 优化了什么：透明安全——每次文件变异操作前自动创建 git 快照，支持任意回滚
   - 牺牲了什么：
     a) 延迟：每轮对话至少 1 次 git add + git commit（30 秒超时）
     b) 磁盘空间：影子 git 仓库存储所有文件变更历史
     c) 上限：单目录最多 50,000 个文件，超出则跳过快照
     d) 排除项：node_modules/、dist/、build/、.git/ 等不纳入快照，这些目录的变更不可回滚
   - 源码证据：^tools/checkpoint_manager.py:37-66

## 10. tools - Fuzzy Match 8 策略链
   - 优化了什么：鲁棒性——容忍 LLM 生成代码中常见的空白差异、缩进变化、unicode 引号、转义不一致等问题
   - 牺牲了什么：性能——按顺序尝试最多 8 种策略（exact → line_trimmed → whitespace_normalized → indentation_flexible → escape_normalized → trimmed_boundary → unicode_normalized → block_anchor），每次都做全文本搜索。简单场景（正确匹配）也要先试失败的策略
   - 源码证据：^tools/fuzzy_match.py:1-30, tools/fuzzy_match.py:72-80

## 11. tools - SkillsGuard 静态安全扫描
   - 优化了什么：安全性——regex 静态分析阻止包含数据窃取、提示注入、破坏性命令的外部技能安装
   - 牺牲了什么：
     a) 误报：community 来源的技能任何 finding（包括 caution 级别）都被阻止，正则误匹配会误杀合法技能
     b) 维护成本：需要维护威胁模式库（regex patterns），正则又无法覆盖所有攻击向量
   - 源码证据：^tools/skills_guard.py:1-23, tools/skills_guard.py:41-46

## 12. gateway - StreamConsumer 渐进式编辑
   - 优化了什么：用户体验——在 Telegram/Discord/Slack 上渐进式编辑机器人消息，实现流式输出效果
   - 牺牲了什么：
     a) 编辑间隔 1.0 秒、缓冲 40 字符：输出不是真正的实时流，而是批量块
     b) 洪泛控制容差：连续 3 次 flood-control 失败后永久禁用渐进编辑，该次流的剩余内容退化为仅最终消息
   - 源码证据：^gateway/stream_consumer.py:40-46, gateway/stream_consumer.py:63-65

## 13. gateway - StickerCache 贴纸描述缓存
   - 优化了什么：避免对同一 Telegram 贴纸重复调用 vision API，节省成本和延迟
   - 牺牲了什么：缓存无过期机制——贴纸描述一旦写入永久保留。如果 vision 模型升级（描述质量提升），旧贴纸不会自动重新分析
   - 源码证据：^gateway/sticker_cache.py:1-24, gateway/sticker_cache.py:57-79

## 14. tools - MixtureOfAgents 多模型并行
   - 优化了什么：通过 4 个前沿模型并行推理 + 聚合器合成，提升复杂推理任务质量
   - 牺牲了什么：成本极高——每次调用并发执行 4 个参考模型 + 1 个聚合模型，5 次 API 调用。参考模型包含 claude-opus-4.6 和 gpt-5.4-pro 等高价模型
   - 源码证据：^tools/mixture_of_agents_tool.py:63-72

## 15. cron - File-based Tick Lock
   - 优化了什么：防止多个进程（gateway + daemon + systemd timer）同时执行 cron tick
   - 牺牲了什么：基于文件的锁（fcntl/msvcrt）比内核级同步原语慢；文件锁在极端情况下可能因进程崩溃而残留，需要额外的清理逻辑
   - 源码证据：^cron/scheduler.py:62-64

## 16. plugins - Context Engine Plugin 懒加载 + 子模块预注册
   - 优化了什么：插件加载安全——扫描文件名、不执行 import 直到实际需要；为子模块创建 module spec 而不立即加载内容
   - 牺牲了什么：复杂的前置加载逻辑（>150 行）——需要手动注册父包、创建 spec、处理相对导入。发现时先尝试 register(ctx) 模式再回退到类扫描，增加代码路径和出错可能性
   - 源码证据：^plugins/context_engine/__init__.py:100-196, plugins/memory/__init__.py:184-284

## 17. skills - Index Cache TTL
   - 优化了什么：远程技能索引缓存（1 小时 TTL），避免每次 skills search 都拉取 GitHub 仓库索引
   - 牺牲了什么：1 小时 TTL 意味着新发布/更新的技能最快 1 小时后才能被发现。缓存过期后所有用户可能同时触发重新拉取
   - 源码证据：^tools/skills_hub.py:56-56

## 18. skills - SkillsSync Manifest 变更检测
   - 优化了什么：通过 manifest 文件的 origin_hash 对比，只同步有变更的内置技能，尊重用户自定义修改
   - 牺牲了什么：MD5 哈希比对——如果用户修改了技能但保持了相同的内容长度（极罕见），哈希不会变化，更新会覆盖用户修改
   - 源码证据：^tools/skills_sync.py:1-22

## 19. tools - TerminalTool 沙箱执行环境选择
   - 优化了什么：通过 BaseEnvironment ABC 支持多种执行后端（local、Docker、Singularity、SSH、Modal、Daytona），用户可根据安全/性能需求选择
   - 牺牲了什么：每个后端的实现独立维护，行为差异（如临时目录路径、网络隔离级别）可能导致同一命令在不同环境中结果不同
   - 源码证据：^tools/environments/__init__.py:1-13

## 20. agent - Rate Limit Tracker 全量 header 采集
   - 优化了什么：提供 /usage 命令的详细速率限制展示（12 个 x-ratelimit-* header：RPM/RPH/TPM/TPH 各 3 个维度）
   - 牺牲了什么：绑定到 Nous Portal header 格式——虽然 OpenRouter 和 OpenAI-compatible API 遵循相同约定，但不支持其他格式的第三方 provider
   - 源码证据：^agent/rate_limit_tracker.py:1-21

---

## 自审

- [x] 是否检查了所有子目录？（agent/, tools/, gateway/, cron/, skills/, hermes_cli/, plugins/）
- [x] 是否有遗漏的子目录？否。逐一检查了每个子目录的文件列表并选择性阅读了关键文件
- [x] 每条是否有明确的牺牲声明（不只是「使用了XX机制」的描述）？是。每条都包含「牺牲了什么」小节，具体说明权衡的代价
- [x] 所有 provenance 行号是否在已读源码范围内（不是猜测的）？是。所有行号来自本次会话中实际读取的文件内容
