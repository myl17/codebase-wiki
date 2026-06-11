---
repo: hermes-agent
dimension: testing-philosophy
dimensions_version: v1.0
generated: 2026-06-09
---

# Hermes Agent — Testing Philosophy

## 规模总览

| 指标 | 数值 |
|---|---|
| 测试文件 | 578 个 |
| 测试代码行数 | ~192,637 行 |
| 测试函数 | ~11,875 个 test 函数 |
| CI 超时 | 10 分钟 |
| 并行执行 | `pytest-xdist -n auto` |

## 分层结构

```
tests/
├── 根目录 (~50 文件) — 跨模块单元测试
├── agent/ (20+ 文件) — agent 内部模块测试
├── gateway/ (20+ 文件) — 网关/平台/会话/审批测试
├── hermes_cli/ (20+ 文件) — CLI/auth/config 测试
├── tools/ (10+ 文件) — 工具模块测试
├── cli/ — CLI TUI 测试
├── acp/ — ACP 适配器测试
├── cron/ — cron 调度器测试
├── run_agent/ — run_agent 核心测试
├── fakes/ (1 文件) — Fake Home Assistant 服务器 (301行)
├── integration/ (8 文件) — 需要外部服务的集成测试
├── e2e/ (3 文件) — 端到端测试
├── plugins/memory/ — 记忆插件测试
├── skills/ — 技能系统测试
└── environments/benchmarks/ — benchmark 环境测试
```

## 测试策略

### CI 配置 ^[.github/workflows/tests.yml:1-77]

| Job | 内容 | 运行方式 |
|---|---|---|
| **test** (10min) | 全部单元测试（排除 integration/ 和 e2e/） | `pytest -q -n auto` 并行 CI执行 |
| **e2e** (10min) | `tests/e2e/` 仅 3 个文件 | `pytest -v` 串行执行 |

默认排除集成/e2e 测试: `addopts = "-m 'not integration' -n auto"` ^[pyproject.toml:136]

### 自动隔离 — 零残留

**`_isolate_hermes_home`** (autouse fixture) 将 `HERMES_HOME` 重定向到 `tmp_path/hermes_test/`，保证测试永远不写入 `~/.hermes/` ^[tests/conftest.py:20-42]。同时：

- 清除 `OPENROUTER_API_KEY` 等关键 env var，防止测试意外调用真实 API
- 重置 `plugin_manager` 单例，防止跨测试泄漏
- 清除 gateway session 环境变量

**30 秒硬超时**: `SIGALRM` 信号处理，任何单个测试超时即 kill ^[tests/conftest.py:77-118]

### Mock/Stub 策略

- **Fake**: `tests/fakes/fake_ha_server.py` (301行) — 真实 aiohttp HTTP + WebSocket 服务器模拟 Home Assistant API，用于集成测试
- **Monkeypatch**: pytest built-in `monkeypatch` fixture 用于 env var 和模块属性注入
- **MockConfig**: `conftest.py:mock_config` fixture 提供最小化配置 dict ^[tests/conftest.py:51-66]
- **原则上 mocking 仅用于外部边界**（API/文件系统/环境），内部模块直接测试

### 测试行为 vs 实现细节

```
目标: 行为驱动测试（behavioral tests）
策略:
  ✅ 测试公共 API 表面（函数签名、返回格式、边界条件）
  ✅ 对错误路径和边界值有专门测试（如空 model fallback、SQL injection）
  ❌ 不测试私有实现细节
  ❌ 不对 mock 对象的内部调用做过度断言
```

**边界行为专项测试举例**: `test_empty_model_fallback.py`, `test_retry_utils.py`, `test_sql_injection.py`, `test_hermes_state.py` 等

### CI 安全层

**Supply Chain Audit** workflow 在每次 PR 上运行 ^[.github/workflows/supply-chain-audit.yml:1-60]:

| 检查 | 说明 |
|---|---|
| `.pth` 文件检测 | 阻止 litellm-style supply chain attack（Python 启动时自动执行）|
| base64+exec/eval 组合 | 检测 credential-stealing 载荷模式 |
| 新增依赖审查 | 阻止新增预构建 wheel/新增 pip install/不安全的 PYTHONPATH |

### 覆盖模式

测试覆盖率按模块镜像源码结构：
- `tools/` ↔ `tests/tools/`
- `gateway/` ↔ `tests/gateway/`
- `agent/` ↔ `tests/agent/`
- `hermes_cli/` ↔ `tests/hermes_cli/`
- `cron/` ↔ `tests/cron/`
- `acp_adapter/` ↔ `tests/acp/`

## 哲学总结

Hermes 的测试哲学是 "实用主义行为覆盖":

- ✅ 大量单元测试（578 文件，19 万行）— 高覆盖率
- ✅ 自动隔离（tmp_path + monkeypatch + 30s 超时）— 零残留
- ✅ 并行执行（pytest-xdist）— 快速反馈（10 分钟 CI）
- ✅ 行为测试而非实现测试 — 重构友好
- ✅ 少量集成/e2e 测试（8+3 文件）— 关键路径有兜底
- ✅ CI 安全扫描（supply-chain-audit）— 阻止恶意代码注入
- ⚠️ 集成测试比例低（1-2%）— 重度依赖单元测试
- ⚠️ 无传统覆盖率工具门槛（无 coverage.py 配置）

## 关联

- [[openclaw/dimensions/openclaw-testing-philosophy]]
