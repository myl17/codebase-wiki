#!/usr/bin/env python3
"""
generate_distractors.py — 为噪声压力测试生成假 Concept 页（仅 frontmatter）。

四类干扰项，固定种子可复现。输出到 wiki/concepts/distractor-*.md。
同时输出 distractor-manifest-{count}.json 记录每个干扰项的元数据。

Usage:
  python experiments/agentic-search-validation/generate_distractors.py --count 100
  python experiments/agentic-search-validation/generate_distractors.py --count 500 --seed 42
  python experiments/agentic-search-validation/generate_distractors.py --clean  # 删除所有干扰项
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# ============================================================
# 真实 Concept 的关键词（用于生成词汇近邻干扰项）
# ============================================================

REAL_CONCEPT_TERMS = {
    "agent": ["agent", "智能体", "代理"],
    "loop": ["循环", "执行循环", "主循环", "pipeline", "管线"],
    "message": ["消息", "message", "收发", "接收"],
    "llm": ["LLM", "大模型", "推理", "inference"],
    "tool": ["工具", "tool", "注册", "发现", "执行"],
    "streaming": ["流式", "streaming", "delta", "响应"],
    "channel": ["channel", "频道", "平台", "接入", "适配"],
    "abstract": ["抽象", "接口", "统一", "abstraction", "adapter"],
    "provider": ["provider", "厂商", "API", "模型管理"],
    "subagent": ["子代理", "subagent", "委托", "后台", "delegate"],
    "system-prompt": ["系统提示词", "system prompt", "分层", "注入"],
    "autonomous": ["定时", "自主", "自动", "调度", "schedule"],
    "security": ["安全", "防御", "审批", "权限", "沙箱"],
    "session": ["会话", "session", "身份", "持久化", "生命周期"],
    "memory": ["记忆", "memory", "长期", "存储", "上下文"],
    "context": ["上下文", "context", "窗口", "压缩", "token"],
    "skills": ["能力", "skill", "模块", "可插拔", "扩展", "插件"],
    "execution": ["执行", "隔离", "sandbox", "docker", "容器"],
    "approval": ["审批", "approval", "人类", "确认", "高风险"],
    "config": ["配置", "config", "模块化", "多环境", "YAML"],
}

# ============================================================
# 跨领域术语（数据库、编译器、OS、网络）
# ============================================================

CROSS_DOMAIN_TERMS = {
    "database": {
        "nouns": ["数据库", "索引", "B-Tree", "LSM-Tree", "WAL", "事务", "MVCC",
                   "查询优化", "SQL", "NoSQL", "分片", "复制", "一致性"],
        "verbs": ["存储", "查询", "写入", "读取", "持久化", "恢复", "压缩"],
        "concerns": ["读写性能", "数据一致性", "故障恢复", "水平扩展"],
    },
    "compiler": {
        "nouns": ["编译器", "AST", "语法树", "IR", "中间表示", "类型检查", "代码生成",
                   "寄存器分配", "优化遍", "词法分析", "LLVM", "JIT"],
        "verbs": ["编译", "解析", "优化", "类型推导", "内联", "向量化"],
        "concerns": ["编译速度", "运行时性能", "错误信息质量", "增量编译"],
    },
    "os": {
        "nouns": ["操作系统", "内核", "进程", "线程", "虚拟内存", "文件系统",
                   "IO多路复用", "epoll", "kqueue", "中断", "调度器", "页表"],
        "verbs": ["调度", "分配", "回收", "映射", "切换", "缓存"],
        "concerns": ["吞吐量", "延迟", "公平性", "内存开销"],
    },
    "network": {
        "nouns": ["网络", "TCP", "UDP", "HTTP/3", "QUIC", "负载均衡", "CDN",
                   "DNS", "TLS", "证书", "握手", "拥塞控制", "代理"],
        "verbs": ["路由", "转发", "握手", "加密", "压缩", "缓存"],
        "concerns": ["延迟", "吞吐量", "可靠性", "安全性"],
    },
}

# ============================================================
# 真实 Concept 的 problem 字段（用于结构近似模板）
# ============================================================

REAL_PROBLEMS = [
    "如何编排 Agent 的主循环，协调消息接收、LLM 调用、工具执行和流式响应",
    "如何用统一接口抽象异构消息平台",
    "如何抽象多个 LLM Provider 的 API 差异",
    "如何管理 Agent 工具的注册/发现/策略过滤",
    "如何让主 Agent 委托后台子 Agent 执行复杂任务",
    "如何组装 Agent 的系统提示词（分层注入）",
    "如何让 Agent 定时自主执行任务",
    "如何构建多层安全防御体系",
    "如何管理会话的身份/持久化/生命周期",
    "如何管理 Agent 的长期记忆",
    "如何在上下文窗口有限时自动压缩对话历史",
    "如何管理 Agent 的可插拔能力模块",
    "如何为工具执行提供可插拔隔离环境",
    "如何在高风险操作前插入人类审批",
    "如何管理配置（模块化/多环境隔离）",
]

# ============================================================
# 词汇近邻模板（30%）
# 用真实 Concept 的高频词 + 不同领域上下文
# ============================================================

VOCAB_NEIGHBOR_TEMPLATES = [
    # 共享 "agent" + "记忆" → 但实际是数据库存储引擎
    "如何在分布式 KV 存储中实现 Agent 级别的数据记忆与回放",
    # 共享 "工具" + "执行" → 但实际是 CI/CD pipeline
    "如何在 CI/CD 管线中实现工具的延迟注册与条件执行",
    # 共享 "消息" + "抽象" → 但实际是微服务消息队列
    "如何抽象多个消息队列后端（Kafka/Pulsar/RabbitMQ）的统一发布订阅接口",
    # 共享 "安全" + "审批" → 但实际是 Kubernetes admission webhook
    "如何在 Kubernetes 集群中构建多层安全审批链",
    # 共享 "上下文" + "压缩" → 但实际是视频编码
    "如何在实时视频编码中实现上下文感知的自适应压缩策略",
    # 共享 "模块" + "可插拔" → 但实际是 Webpack 插件系统
    "如何设计可插拔的构建工具模块系统，支持动态加载与热替换",
    # 共享 "会话" + "持久化" → 但实际是数据库连接池
    "如何管理数据库连接池中长会话的生命周期与持久化",
    # 共享 "隔离" + "执行" → 但实际是浏览器 tab 进程隔离
    "如何在浏览器引擎中为每个标签页提供独立的 JavaScript 执行隔离环境",
    # 共享 "定时" + "调度" → 但实际是分布式 cron
    "如何在分布式系统中实现精确一次的定时任务调度",
    # 共享 "LLM" + "推理" → 但实际是模型推理优化
    "如何在 GPU 集群上实现多个 LLM 推理请求的批处理与调度",
    # 共享 "流式" + "响应" → 但实际是 gRPC server-streaming
    "如何在 gRPC 服务端流式响应中实现背压与分块传输控制",
    # 共享 "配置" + "多环境" → 但实际是 feature flag 系统
    "如何管理多环境下特性开关的配置继承与覆盖规则",
    # 共享 "channel" + "接入" → 但实际是支付渠道
    "如何用统一接口抽象微信支付、支付宝和 Stripe 的支付渠道接入",
    # 共享 "provider" + "API" → 但实际是短信/邮件 provider
    "如何抽象多个短信和邮件服务提供商的 API 差异与故障切换",
    # 共享 "子代理" + "委托" → 但实际是分布式事务协调
    "如何在分布式事务中实现子事务的委托执行与补偿回滚",
    # 共享 "提示词" + "分层" → 但实际是 CSS z-index 层叠
    "如何设计 UI 组件的分层提示词系统，管理弹窗、工具提示和下拉菜单的层叠顺序",
    # 共享 "能力" + "扩展" → 但实际是浏览器 extension
    "如何管理浏览器扩展的能力声明与权限分级",
    # 共享 "生命周期" + "身份" → 但实际是 OAuth token
    "如何管理 OAuth 2.0 令牌的身份绑定与完整生命周期",
    # 共享 "防御" + "多层" → 但实际是 DDoS 防护
    "如何构建多层 DDoS 防御体系，从边缘到源站逐层过滤",
    # 共享 "压缩" + "窗口" → 但实际是 TCP 拥塞控制
    "如何在 TCP 拥塞窗口中实现基于 RTT 的自适应压缩与扩容",
]

# ============================================================
# 结构近似模板（20%）—— 句式相似但领域不同
# ============================================================

STRUCTURAL_NEIGHBOR_TEMPLATES = [
    # 前端框架
    "如何管理 React 组件的状态生命周期，协调 props、state 和 context 的数据流",
    "如何用声明式 DSL 抽象不同平台的 UI 渲染差异",
    "如何在前端构建工具链中实现插件的注册、发现与版本兼容检查",
    "如何让主线程委托 Web Worker 执行 CPU 密集型计算任务",
    "如何在单页应用中实现路由的分层配置与懒加载",
    "如何管理前端应用的多语言国际化配置与运行时切换",
    # 数据工程
    "如何编排 ETL 管线的执行顺序，处理任务间的依赖、失败重试和断点续跑",
    "如何用统一的数据格式（Arrow/Parquet）抽象不同数据源的行列存储差异",
    "如何在流处理引擎中实现窗口函数的自动压缩与状态清理",
    # 移动开发
    "如何管理 iOS 应用中后台任务的定时执行与系统节能策略的协调",
    "如何用响应式编程抽象 Android 和 iOS 的异步 UI 更新差异",
    "如何在移动应用中实现离线优先的数据同步与冲突解决策略",
    # DevOps
    "如何为 Terraform 模块设计可复用的抽象层，屏蔽 AWS/Azure/GCP 的 API 差异",
    "如何在多集群 Kubernetes 环境中实现统一的配置管理和秘钥分发",
]

# ============================================================
# 跨领域模板（40%）—— 完全无关
# ============================================================

CROSS_DOMAIN_TEMPLATES = [
    # 数据库
    "如何设计 LSM-Tree 的 Compaction 策略以平衡读放大、写放大和空间放大",
    "如何在分布式数据库中实现基于 Raft 共识的强一致性复制",
    "如何为时序数据库选择合适的数据编码和压缩算法",
    "如何在列式存储引擎中实现谓词下推和延迟物化",
    "如何设计 MVCC 的垃圾回收策略，在事务吞吐量和空间回收之间取得平衡",
    "如何在图数据库中实现高效的子图匹配和路径查询",
    "如何在内存数据库中实现高效的增量检查点与故障恢复",
    "如何为 NewSQL 系统设计全局事务标识和时钟同步机制",
    # 编译器
    "如何在 JIT 编译器中实现基于运行时反馈的推测性优化与反优化",
    "如何设计 IR 的 SSA 形式以支持稀疏条件常量传播和死代码消除",
    "如何在编译器中实现跨函数的过程间别名分析与内联决策",
    "如何为 GPU 编译后端设计 warp 级别的向量化指令选择和调度",
    "如何在增量编译器中实现细粒度的依赖跟踪与失效传播",
    "如何设计类型系统以支持泛型特化、单态化和运行时类型擦除",
    # 操作系统
    "如何在微内核架构中设计高效的 IPC 机制，减少上下文切换开销",
    "如何在 NUMA 架构上实现内存分配器的节点亲和性策略",
    "如何设计文件系统的写时复制（COW）快照机制与增量备份",
    "如何在虚拟化环境中实现 GPU 的 SR-IOV 设备直通与热迁移",
    "如何设计内核的完全公平调度器（CFS）以兼顾交互式任务的响应延迟",
    "如何在用户态网络栈中实现零拷贝的数据包处理管道",
    # 网络
    "如何设计 QUIC 协议的拥塞控制算法以适应 5G 高带宽高延迟网络",
    "如何在 CDN 边缘节点实现基于机器学习的自适应缓存替换策略",
    "如何在 Service Mesh 中实现基于 eBPF 的零侵入流量劫持和路由",
    "如何设计 DNS 的 Anycast 任播架构以保证全球用户的就近解析",
    "如何在负载均衡器中实现一致性哈希以最小化后端扩缩容时的连接迁移",
    "如何设计基于 TLS 1.3 的 0-RTT 握手以兼顾安全性与重放攻击防护",
    # 密码学
    "如何在多方安全计算中实现高效的秘密共享与不经意传输",
    "如何设计后量子密码算法的混合密钥交换，兼容 RSA/ECC 和 Kyber",
    # 机器学习系统
    "如何在分布式训练中实现梯度压缩与通信计算重叠以提升扩展效率",
    "如何设计特征存储以支持在线服务的低延迟特征查询和离线训练的一致性",
    "如何在模型推理服务中实现动态批处理与 GPU 显存的分时复用",
    # 前端
    "如何在虚拟 DOM 中实现细粒度的脏标记追踪与最小化 DOM 更新",
    "如何设计 CSS-in-JS 运行时的样式去重与原子化 class 生成",
    # 区块链
    "如何在权益证明共识中设计验证者选举的随机性与抗偏置机制",
    "如何在智能合约虚拟机中设计 Gas 计量与执行资源的安全边界",
    # 游戏引擎
    "如何在 ECS 架构中实现 System 的并行调度与 Archetype 的缓存局部性优化",
    "如何设计游戏引擎的资产管线，支持纹理、模型和音频的异步加载与格式转换",
]

# ============================================================
# 粒度陷阱模板（10%）—— Agent 框架领域但粒度过细
# ============================================================

GRANULARITY_TRAP_TEMPLATES = [
    # 实现细节，不应匹配到已有 Concept
    "如何在流式输出的 delta 合并中使用固定时间窗口减少 Telegram API 调用次数",
    "如何在工具注册表中使用 LRU 缓存加速高频工具的 schema 反序列化",
    "如何为 shell 命令的 stdout 捕获选择缓冲区大小以平衡内存和延迟",
    "如何在 LLM API 调用中实现指数退避重试的抖动因子以避免惊群效应",
    "如何选择消息序列化格式（JSON vs MessagePack vs Protobuf）以降低跨平台通信开销",
    "如何设计 Markdown 转义规则以正确处理 Discord 和 Telegram 的特殊格式差异",
    "如何在日志系统中实现凭证自动脱敏的正则表达式匹配策略",
    "如何为 session key 生成选择 UUID v4 vs ULID 以保证唯一性和排序性",
    "如何在 Docker sandbox 中配置 cgroup 内存限制的硬边界与软边界",
    "如何选择 HTTP 客户端的连接池大小以平衡并发请求和文件描述符开销",
    "如何设计工具执行超时的定时器粒度（秒级 vs 毫秒级）与取消传播策略",
    "如何为 subprocess 的标准错误流合并选择正确的缓冲区策略",
    "如何在配置文件热加载中实现 inotify/fsevents 的跨平台文件监控抽象",
]

# ============================================================
# 生成逻辑
# ============================================================

def _pick_repos(seed: int, count: int = 2) -> list:
    """Pick random fake repo names for a distractor."""
    rng = random.Random(seed)
    pools = [
        "django", "flask", "kubernetes", "react", "tensorflow", "postgres",
        "llvm-project", "linux", "redis", "nginx", "kafka", "spark",
        "pytorch", "vue", "elasticsearch", "docker", "grafana", "prometheus",
        "envoy", "grpc", "etcd", "rocksdb", "clickhouse", "swift",
    ]
    return rng.sample(pools, min(count, len(pools)))


def generate_vocab_neighbors(rng: random.Random, count: int, start_idx: int) -> list:
    """Generate vocabulary neighbor distractors."""
    templates = rng.sample(VOCAB_NEIGHBOR_TEMPLATES, min(count, len(VOCAB_NEIGHBOR_TEMPLATES)))
    if len(templates) < count:
        # If we need more than available templates, cycle through with variations
        while len(templates) < count:
            extra = VOCAB_NEIGHBOR_TEMPLATES[len(templates) % len(VOCAB_NEIGHBOR_TEMPLATES)]
            templates.append(extra + "（扩展变体）")
    result = []
    for i, problem in enumerate(templates[:count]):
        concerns = rng.sample([
            "读写性能", "数据一致性", "故障恢复时间", "接口简洁性",
            "扩展灵活性", "安全隔离性", "资源利用率", "响应延迟",
        ], k=min(3, rng.randint(2, 3)))
        result.append({
            "category": "vocab-neighbor",
            "problem": problem,
            "concerns": concerns,
            "repos": _pick_repos(start_idx + i),
        })
    return result


def generate_structural_neighbors(rng: random.Random, count: int, start_idx: int) -> list:
    """Generate structural近似 distractors."""
    templates = rng.sample(STRUCTURAL_NEIGHBOR_TEMPLATES, min(count, len(STRUCTURAL_NEIGHBOR_TEMPLATES)))
    while len(templates) < count:
        extra = STRUCTURAL_NEIGHBOR_TEMPLATES[len(templates) % len(STRUCTURAL_NEIGHBOR_TEMPLATES)]
        templates.append(extra + "（变体）")
    result = []
    for i, problem in enumerate(templates[:count]):
        concerns = rng.sample([
            "开发效率", "运行时性能", "代码可维护性", "学习成本",
            "生态兼容性", "调试便利性", "部署复杂度", "版本升级平滑性",
        ], k=min(3, rng.randint(2, 3)))
        result.append({
            "category": "structural-neighbor",
            "problem": problem,
            "concerns": concerns,
            "repos": _pick_repos(start_idx + i),
        })
    return result


def generate_cross_domain(rng: random.Random, count: int, start_idx: int) -> list:
    """Generate cross-domain distractors."""
    templates = rng.sample(CROSS_DOMAIN_TEMPLATES, min(count, len(CROSS_DOMAIN_TEMPLATES)))
    while len(templates) < count:
        extra = CROSS_DOMAIN_TEMPLATES[len(templates) % len(CROSS_DOMAIN_TEMPLATES)]
        templates.append(extra)
    result = []
    for i, problem in enumerate(templates[:count]):
        # Pick concerns from a generic set
        concerns = rng.sample([
            "吞吐量", "延迟", "可扩展性", "容错性", "一致性",
            "硬件效率", "运维复杂度", "兼容性",
        ], k=min(3, rng.randint(2, 3)))
        result.append({
            "category": "cross-domain",
            "problem": problem,
            "concerns": concerns,
            "repos": _pick_repos(start_idx + i),
        })
    return result


def generate_granularity_traps(rng: random.Random, count: int, start_idx: int) -> list:
    """Generate granularity trap distractors."""
    templates = rng.sample(GRANULARITY_TRAP_TEMPLATES, min(count, len(GRANULARITY_TRAP_TEMPLATES)))
    while len(templates) < count:
        extra = GRANULARITY_TRAP_TEMPLATES[len(templates) % len(GRANULARITY_TRAP_TEMPLATES)]
        templates.append(extra + "（粒度变体）")
    result = []
    for i, problem in enumerate(templates[:count]):
        concerns = rng.sample([
            "实现复杂度", "运行时性能", "磁盘 I/O", "内存开销",
            "网络带宽", "代码可维护性", "调试便利性",
        ], k=min(3, rng.randint(2, 3)))
        result.append({
            "category": "granularity-trap",
            "problem": problem,
            "concerns": concerns,
            "repos": _pick_repos(start_idx + i),
        })
    return result


def generate_distractors(count: int, seed: int = 42) -> list:
    """Generate N distractors with fixed ratios across 4 categories."""
    rng = random.Random(seed)

    # Ratios from experiment design
    n_vocab = int(count * 0.30)
    n_structural = int(count * 0.20)
    n_granularity = int(count * 0.10)
    n_cross = count - n_vocab - n_structural - n_granularity  # ~40%

    idx = 0
    all_items = []

    items = generate_vocab_neighbors(rng, n_vocab, idx)
    all_items.extend(items)
    idx += len(items)

    items = generate_structural_neighbors(rng, n_structural, idx)
    all_items.extend(items)
    idx += len(items)

    items = generate_cross_domain(rng, n_cross, idx)
    all_items.extend(items)
    idx += len(items)

    items = generate_granularity_traps(rng, n_granularity, idx)
    all_items.extend(items)
    idx += len(items)

    # Shuffle so categories are interleaved
    rng.shuffle(all_items)

    # Assign sequential IDs after shuffle
    for i, item in enumerate(all_items):
        item["id"] = i
        item["slug"] = f"distractor-{i:04d}"

    return all_items


def write_distractors(items: list, wiki_concepts: Path) -> dict:
    """Write distractor .md files and return manifest."""
    manifest = {
        "total": len(items),
        "generated": "2026-06-29",
        "seed": None,  # filled by caller
        "by_category": {},
        "items": [],
    }

    for item in items:
        slug = item["slug"]
        filepath = wiki_concepts / f"{slug}.md"

        repos_str = ", ".join(item["repos"])
        concerns_str = ", ".join(item["concerns"])

        content = f"""---
type: concept
concept: {slug}
problem: "{item['problem']}"
concerns: [{concerns_str}]
repos: [{repos_str}]
generated: 2026-06-29
---
"""

        filepath.write_text(content, encoding="utf-8")

        manifest["items"].append({
            "id": item["id"],
            "slug": slug,
            "category": item["category"],
            "problem": item["problem"],
            "grep_risk": _estimate_grep_risk(item),
        })

        # Count by category
        cat = item["category"]
        manifest["by_category"][cat] = manifest["by_category"].get(cat, 0) + 1

    return manifest


def _estimate_grep_risk(item: dict) -> str:
    """Estimate how likely common grep keywords will hit this distractor."""
    problem = item["problem"].lower()
    cat = item["category"]

    # High-frequency keywords from real Concepts
    high_risk_keywords = [
        "agent", "工具", "tool", "消息", "message", "会话", "session",
        "记忆", "memory", "上下文", "context", "安全", "security",
        "执行", "execution", "隔离", "sandbox", "channel", "llm",
        "流式", "streaming", "抽象", "abstract", "provider",
    ]
    medium_risk_keywords = [
        "插件", "plugin", "扩展", "extension", "模块", "module",
        "配置", "config", "调度", "schedule", "审批", "approval",
        "循环", "loop", "压缩", "compression", "生命周期", "lifecycle",
    ]

    hits_high = sum(1 for kw in high_risk_keywords if kw in problem)
    hits_medium = sum(1 for kw in medium_risk_keywords if kw in problem)

    if cat == "cross-domain":
        return "none"  # should not match any agent-framework grep
    elif cat == "granularity-trap":
        if hits_high >= 2:
            return "high"  # shares terms with agent domain
        return "medium"
    elif cat == "vocab-neighbor":
        if hits_high >= 2:
            return "high"
        return "medium"
    elif cat == "structural-neighbor":
        if hits_high >= 1 or hits_medium >= 2:
            return "medium"
        return "low"
    return "unknown"


def clean_distractors(wiki_concepts: Path) -> int:
    """Remove all distractor-*.md files. Returns count removed."""
    count = 0
    for f in wiki_concepts.glob("distractor-*.md"):
        f.unlink()
        count += 1
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Generate distractor Concept pages for noise stress testing."
    )
    parser.add_argument("--count", type=int, default=100, help="Number of distractors")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--wiki", default="wiki", help="Path to wiki/ root")
    parser.add_argument("--clean", action="store_true", help="Remove all distractor files and exit")
    parser.add_argument("--manifest-dir", default="experiments/agentic-search-validation",
                        help="Directory for manifest output")
    args = parser.parse_args()

    project_root = Path(args.wiki).parent if args.wiki == "wiki" else Path.cwd()
    wiki_root = project_root / args.wiki
    wiki_concepts = wiki_root / "concepts"

    if not wiki_concepts.exists():
        print(f"ERROR: {wiki_concepts} does not exist")
        sys.exit(1)

    # Clean mode
    if args.clean:
        removed = clean_distractors(wiki_concepts)
        print(f"Removed {removed} distractor files.")
        return

    # Generate
    print(f"Generating {args.count} distractors (seed={args.seed})...")
    items = generate_distractors(args.count, seed=args.seed)
    print(f"  vocab-neighbor:    {sum(1 for i in items if i['category'] == 'vocab-neighbor')}")
    print(f"  structural-neighbor: {sum(1 for i in items if i['category'] == 'structural-neighbor')}")
    print(f"  cross-domain:      {sum(1 for i in items if i['category'] == 'cross-domain')}")
    print(f"  granularity-trap:  {sum(1 for i in items if i['category'] == 'granularity-trap')}")

    manifest = write_distractors(items, wiki_concepts)
    manifest["seed"] = args.seed

    # Write manifest
    manifest_dir = project_root / args.manifest_dir
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"distractor-manifest-{args.count}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Summary of grep risk distribution
    risk_counts = {"high": 0, "medium": 0, "low": 0, "none": 0}
    for item in manifest["items"]:
        risk_counts[item["grep_risk"]] += 1
    print(f"\nGrep risk distribution:")
    for level, cnt in sorted(risk_counts.items()):
        print(f"  {level}: {cnt} ({cnt/len(items)*100:.0f}%)")

    print(f"\nWrote {len(items)} files to {wiki_concepts.relative_to(project_root)}/")
    print(f"Manifest: {manifest_path.relative_to(project_root)}")
    print(f"\nTo clean up: python {Path(__file__).name} --clean")


if __name__ == "__main__":
    main()
