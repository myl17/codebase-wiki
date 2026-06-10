---
repo: hermes-agent
dimension: dependency-strategy
dimensions_version: v1.0
generated: 2026-06-09
---

# Hermes Agent — Dependency Strategy

## 1. 总体哲学：选择性生态系统，强版本边界

**核心理念**: 拥抱生态系统但严格版本锁定 — 不最小化依赖，但也不放任依赖膨胀。采用[[优雅降级]]策略，20+ 可选依赖缺失时运行时自动降级。^[pyproject.toml:14]

```
依赖层级：
  核心 (7个必须依赖) — 无替代方案，安装时不可跳过
  ├── OpenAI SDK (>=2.21.0,<3)
  ├── Anthropic SDK (>=0.39.0,<1)
  ├── httpx (>=0.28.1,<1)
  ├── prompt_toolkit (>=3.0.52,<4)
  ├── pydantic (>=2.12.5,<3)
  ├── rich (>=14.3.3,<15)
  └── tenacity (>=9.1.4,<10)

  可选依赖 (20+ extras) — 安装时可跳过，运行时优雅降级
  ├── messaging (5 库) — gateway 多平台通信
  ├── modal / daytona — 云容器运行时
  ├── memory providers — 7 个可选后端
  ├── voice / tts-premium — 语音 I/O
  ├── browser / web — 浏览器自动化 + 搜索后端
  └── ...
```

## 2. 版本锁策略 — 三层防护

| 层级 | 机制 | 文件 |
|---|---|---|
| **范围锁** | `>=lower,<upper` 所有核心依赖都双边界定 | `pyproject.toml:15-37` |
| **精确锁** | `uv.lock` (5512 行) — 全依赖树 hash 锁定 | `uv.lock` |
| **Docker 层** | 基础镜像 SHA256 固定 + COPY . 后再 `uv pip install` | `Dockerfile:1-3,38-39` |

**无 vendor/bundle 策略** — 所有依赖通过 PyPI + lockfile 管理，不内嵌第三方源码。

## 3. 可选依赖设计 — 最大模块化

20+ optional extras 将单体重安装拆分为按需安装 ^[pyproject.toml:39-115]:

```toml
# 最小安装（CLI only）
pip install hermes-agent

# 按需叠加
hermes-agent[messaging]    # 消息平台
hermes-agent[modal]        # Modal serverless 后端
hermes-agent[honcho]       # Honcho 记忆后端
hermes-agent[voice]        # 语音输入
hermes-agent[all]          # 全部功能
```

**条件依赖**: `matrix` extra 仅在 Linux 上可用（python-olm 上游 macOS 不兼容）^[pyproject.toml:94-96]；`yc-bench` 仅 Python >= 3.12 ^[pyproject.toml:89]

## 4. 核心依赖可替换性

| 依赖 | 用途 | 替换成本 | 替代方案 |
|---|---|---|---|
| `openai` SDK | 所有模型 API 调用（OpenAI-compatible 协议） | **高** — 20+ provider 都通过它路由 | 无官方替代 |
| `anthropic` SDK | 原生 Anthropic Messages API | **低** — `api_mode` 切换即可回到 OpenAI-compatible 路径 | OpenRouter 中转 |
| `prompt_toolkit` | CLI TUI | **中** — 3000+ 行深度集成 | 需重写 cli.py |
| `httpx` | 异步 HTTP 客户端 | **低** — 标准接口，可替换为 aiohttp | `requests` + `aiohttp` |
| `pydantic` | 数据验证 | **低** | dataclasses + 手写验证 |
| `rich` | CLI 输出格式化 | **低** | 纯 ANSI 输出 |
| `tenacity` | API 调用重试逻辑 | **低** | 手写 retry loop |

## 5. 运行时可替换性 — 多后端模式

部分系统允许多个实现选择，不强制单一依赖：

| 子系统 | 可选后端 | 切换方式 |
|---|---|---|
| **终端后端** | local / docker / ssh / daytona / singularity / modal (6 种) | `config.yaml`: `terminal.backend` |
| **搜索后端** | Exa / Firecrawl / Tavily / Parallel-Web (4 种) | 各自的 API key 存在即启用 ^[tools/web_tools.py:1925-1926] |
| **TTS 引擎** | Edge TTS (免费, 内置) / ElevenLabs / OpenAI | `config.yaml`: `tts.provider` |
| **记忆后端** | Builtin (内置) + 1 个外部 plugin (7 选 1) | `config.yaml`: `memory.provider` |
| **上下文压缩** | ContextCompressor (内置) / 第三方 engine | `config.yaml`: `context.engine` |

## 6. 优雅降级 — 缺失不崩溃

所有可选依赖遵循 ImportError → 降级/跳过 模式，绝不因缺少可选包而启动失败：

- **Web 搜索**: 多后端回退 — 检查每个后端的 API key，至少一个可用才注册 `web_search` 工具 ^[tools/web_tools.py:1925-1947]
- **Vision**: `faster-whisper` ImportError → TTS fallback 仅忽略，不报错 ^[tools/vision_tools.py:325]
- **MCP**: `mcp` 包未安装 → debug 日志，不影响其他工具 ^[tools/mcp_tool.py:10-11]
- **RL 环境**: `atroposlib` ImportError → environments 不可用但子模块可直接导入 ^[environments/__init__.py:25-27]

## 7. 供给链安全 — 主动防范

| 措施 | 说明 |
|---|---|
| **CVE 主动处理** | `requests>=2.33.0` 修复 CVE-2026-25645；`PyJWT>=2.12.0` 修复 CVE-2026-32597 ^[pyproject.toml:23,36] |
| **版本上限** | 所有核心依赖都有 `<major+1` 上限，防止大版本破坏 ^[pyproject.toml:15-37] |
| **Skill 安全扫描** | 外部 skills 在安装前经过 `skills_guard.py` 100+ 威胁模式扫描 ^[tools/skills_guard.py:82-484] |
| **MCP 凭据脱敏** | MCP server 错误消息中的 API key 被剥离后再返回 LLM ^[tools/mcp_tool.py:49-50] |
| **日志密文脱敏** | 40+ 种 API key 前缀模式自动脱敏，密钥永不写入日志 ^[agent/redact.py:1-60] |
| **Docker 基础镜像** | 全部使用 SHA256 digest 固定，非浮动 tag ^[Dockerfile:1-3] |
| **uv 构建系统** | `uv` 而非 `pip`，提供更快且可重复的安装 ^[Dockerfile:22,38-39] |

## 8. Git 依赖 — 受控使用

仅在 RL 训练环境使用（可选 extra），不上核心依赖路径 ^[pyproject.toml:82-88]:

```toml
"atroposlib @ git+https://github.com/NousResearch/atropos.git@c20c852..."
"tinker @ git+https://github.com/thinking-machines-lab/tinker.git@30517b6..."
```

Git 依赖全部精确 pin 到 commit SHA，不跟随分支。

## 9. 直接依赖 vs 传递依赖

- 直接依赖 ~20 个（核心+消息+工具）
- 传递依赖 ~200+（通过 uv.lock 锁定）
- `uv.lock` 5512 行，覆盖全依赖树

## 策略总结

Hermes 的依赖策略是 "选择性拥抱" — 不是最小化也不是最大化：

- ✅ 生态关键模块（openai SDK）深度集成，高替换成本
- ✅ 非关键模块（TTS/搜索/记忆/终端）多后端可选，低锁定风险
- ✅ 所有可选依赖优雅降级，不强制安装
- ✅ 三层锁定（范围+精确+容器）确保可重复构建
- ✅ 供给链安全内建（CVE/bounds/扫描/脱敏）
- ⚠️ openai SDK 单点 — 20+ provider 都通过它，无法绕过

## 关联

- [[openclaw/dimensions/openclaw-dependency-strategy]]
