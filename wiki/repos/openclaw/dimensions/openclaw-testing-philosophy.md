---
repo: openclaw
dimension: testing-philosophy
dimensions_version: v1.0
generated: 2026-06-09
---

# OpenClaw — Testing Philosophy

OpenClaw 的测试策略：**测试数量极多（2671 个单元测试文件）、分层极细（90+ 个独立 vitest 配置）、类型丰富（单元/契约/e2e/live/Docker/perf），并把静态分析和性能预算也当作"测试"来维护。**

## 1. 测试框架与配置

全栈使用 **[[Vitest]]**（`^4.1.4`），根配置 `vitest.config.ts` 注册 90+ 个独立子配置，每个子系统（agents、gateway、channels、cron、tasks、memory 等）各有专属配置文件，按子系统分片并行运行。Worker 数量根据 `os.availableParallelism()`、系统负载（`os.loadavg()[0]`）、内存动态计算，高负载时自动降低并发。^[test/vitest/vitest.config.ts:1-55]

## 2. 五类测试

### ① 单元测试（`*.test.ts`，2671 个文件）

主体。测试文件与被测文件共存于 `src/`，命名规则 `foo.ts` / `foo.test.ts`。大量使用 `vi.mock` 模拟外部依赖（如整个 `@mariozechner/pi-ai` 模块），测试内部行为和边界条件。pool 类型通过 `OPENCLAW_VITEST_MAX_WORKERS` 控制并发。^[src/agents/pi-embedded-runner.e2e.test.ts:1-30]

### ② e2e 测试（`*.e2e.test.ts`，27 个文件）

与单元测试混合存放于 `src/`，由 `vitest.e2e.config.ts` 独立运行。测试完整子系统集成路径（如 `pi-embedded-runner` 完整运行 + MCP bundle），使用真实文件系统 fixture 和专用 helper（`createEmbeddedPiRunnerTestWorkspace`），会创建/清理临时工作区。^[test/vitest/vitest.e2e.config.ts]

### ③ [[契约测试]]（`src/{channels,plugins}/contracts/**/*.test.ts`）

验证所有 channel plugin 和 provider plugin 符合标准接口契约。每个 channel 的 actions、DM policy、group policy 均有对应 contract test，以 `installChannelActionsContractSuite(...)` 共享 test suite 定义——新 channel 注册到 registry 后自动被契约测试覆盖，无需手写。运行时用 `forks` pool + `isolate: false`（契约测试间共享注册表状态）。^[src/channels/plugins/contracts/actions.registry-backed.contract.test.ts:1-12]

### ④ Live 测试（`*.live.test.ts`，18 个文件）

需真实 API key，通过环境变量门控（`isLiveTestEnabled(["XAI_LIVE_TEST"])`），默认 `describe.skip`。测试真实 LLM 调用、stream 解析、模型切换等。CI 中按 provider 分别通过 `OPENCLAW_LIVE_TEST=1` 触发。^[src/agents/xai.live.test.ts:1-15]

### ⑤ Docker e2e 测试（`test:docker:*`，10+ 场景）

完整端到端，在 Docker 容器中运行真实 gateway + channel 流程（onboard、MCP channel、gateway-network、QR 导入、doctor-switch 等），通过 bash 脚本驱动。只在完整 CI pipeline（`test:all`）中运行，是最重的测试层。^[package.json: test:docker:* scripts]

## 3. 性能预算作为测试

`test:startup:bench:check` 将 CLI 冷启动时间对比 `test/fixtures/cli-startup-bench.json` 中的基线 fixture，超出 budget 即 CI 失败。`test:perf:budget` 监控整体性能指标。**启动性能是一等公民，有专用 fixture 文件和 CI 检查。** 这是[[性能预算]]实践的典型形式。^[scripts/test-cli-startup-bench-budget.mjs:1-40]

## 4. 重复代码检测

`dup:check` 用 `jscpd`（精确锁定 `4.0.9`）扫描全量 TypeScript/JavaScript：≥12 行或 ≥80 token 的重复即报告，作为 CI `check` 流水线的一部分。^[package.json: dup:check]

## 5. 文件大小约束

`check:loc` 强制单文件最大 500 行（`--max 500`），超出即 CI 失败，防止大文件积累。^[scripts/check-ts-max-loc.ts:1-30]

## 6. 大量自定义 lint 脚本（架构边界守护）

20+ 个专项 `lint:*` 脚本检测架构边界，是架构约束的可执行文档：^[package.json: lint:* scripts]

| lint 脚本 | 检测内容 |
|---|---|
| `lint:extensions:no-src-outside-plugin-sdk` | extensions 不能直接 import `src/` 内部模块 |
| `lint:plugins:no-extension-imports` | plugin 不能反向 import extension |
| `lint:plugins:no-monolithic-plugin-sdk-entry-imports` | 禁止 import plugin-sdk 单体入口 |
| `lint:webhook:no-low-level-body-read` | webhook 处理必须走正确 body 解析顺序 |
| `lint:auth:no-pairing-store-group` | auth 层禁止访问 pairing store group |
| `lint:web-fetch-provider-boundaries` | web fetch provider 边界隔离 |

## 7. 关键观察

- **测试针对行为而非实现**：单元测试大量 mock 外部包而不 mock 内部实现细节，确保测试不与实现耦合
- **契约测试保证 plugin 接口稳定性**：新 channel 只需注册到 registry，契约测试自动覆盖，不需手写
- **live 测试作为可选层**：不强制本地运行，但 CI 对每个 provider 有专属 pipeline
- **静态分析即架构守护**：20+ 专项 lint 脚本保证层间边界不被侵蚀，架构约束可执行化

## 关联

*(暂无同类仓库已分析，链接待补充)*
