# OpenClaw Performance Tradeoffs

## 1. Node.js Compile Cache 启动优化

**优化目标**：降低 Node.js CLI 冷启动延迟。

**手段**：使用 Node.js 内置的 `enableCompileCache()` 将模块编译结果缓存到磁盘，避免每次启动重新编译 TypeScript/JavaScript 模块。

**源码证据**：

- 入口文件在非生产禁用标志下启用编译缓存，失败仅 best-effort，绝不阻塞启动 ^[src/entry.ts:52-57]
- 可通过 `NODE_DISABLE_COMPILE_CACHE` 环境变量禁用缓存 ^[src/entry.ts:52]

**牺牲**：编译缓存占据磁盘空间，且缓存过期后可能加载陈旧的字节码。缓存的失效由 Node.js 运行时自动管理，应用层面不感知。

---

## 2. Session Store 带 TTL 的文件缓存

**优化目标**：减少高频读取的 session store JSON 文件所触发的文件系统 I/O。

**手段**：使用 `ExpiringMapCache` 封装 session store，设置 45 秒默认 TTL，基于文件 mtime 和文件大小进行缓存失效判定。读写均使用 `structuredClone` 深拷贝以避免引用污染。

**源码证据**：

- 默认 TTL 为 45 秒（在 30-60 秒之间），可通过 `OPENCLAW_SESSION_CACHE_TTL_MS` 调整 ^[src/config/sessions/store-cache.ts:11-15]
- `readSessionStoreCache` 对比 `mtimeMs` 和 `sizeBytes`，不匹配即失效 ^[src/config/sessions/store-cache.ts:55-69]
- `writeSessionStoreCache` 深拷贝存储到缓存，同时维护序列化缓存副本 ^[src/config/sessions/store-cache.ts:71-87]
- TTL 解析支持环境变量覆盖和严格整数校验 ^[src/config/cache-utils.ts:4-16]
- 通用 `ExpiringMapCache` 支持惰性过期清理（`maybePruneExpiredEntries`） ^[src/config/cache-utils.ts:61-142]

**牺牲**：45 秒内的 session store 文件变更对缓存不可见（最终一致性）。对于 session store 写后立即读的场景，调用方需要显式失效缓存。

---

## 3. Entry Point 动态导入懒加载

**优化目标**：最小化 CLI 入口文件的模块加载体积，延迟加载非关键代码路径。

**手段**：`entry.ts` 使用顶层 `await import()` 动态加载 `runCli`、`rootHelp`、`version` 等模块，将完整的 CLI 依赖树推迟到实际需要时才解析。

**源码证据**：

- `--version` 快速路径：动态加载 `version.js` 和 `git-commit.js`，避免加载 Commander 等重型 CLI 依赖 ^[src/entry.ts:108-123]
- `--help` 快速路径：先尝试预计算的 help 文本，仅失败时才动态导入完整的 root-help 模块 ^[src/entry.ts:159-198]
- 主 CLI 入口仅在非 respawn、非版本、非帮助路径下才动态导入 `run-main.js` ^[src/entry.ts:200-213]
- `isMainModule` 守卫确保作为依赖导入时不执行任何入口副作用 ^[src/entry.ts:37-43]

**牺牲**：动态导入引入了首次调用时的异步延迟（用户感知不到，因为发生在解析命令行参数后）。模块加载图变得隐式，静态分析工具无法追踪完整依赖树。

---

## 4. Plugin 合约懒加载

**优化目标**：保持插件系统的启动开销趋近于零，尤其在插件全部禁用的场景下（常见于单元测试）。

**手段**：Plugin 合约注册表使用 `createLazyArrayView()` 惰性解析，Jiti loader 在插件全部禁用时不被创建。

**源码证据**：

- Plugin loader 惰性避免在插件全禁用时创建 Jiti loader ^[src/plugins/loader.ts:1137]
- `createLazyArrayView` 封装合约注册表的延迟加载 ^[src/plugins/contracts/registry.ts:608]
- Web Search、Web Fetch、Realtime Transcription、Voice、Media、Image、Video、Music 等所有合约注册表均懒加载 ^[src/plugins/contracts/registry.ts:695-719]
- Runtime 方法通过 `createLazyRuntimeMethod` 延迟绑定 ^[src/plugins/runtime/runtime-agent.ts:33-36]
- TTS runtime 通过 `createLazyRuntimeModule` 延迟加载 ^[src/plugins/runtime/index.ts:37]

**牺牲**：懒加载意味着首次使用插件功能时有冷启动延迟。插件系统在运行时才暴露配置错误（而非启动时早期发现）。

---

## 5. Docker 构建缓存分层

**优化目标**：加速 Docker 镜像构建，避免重复下载依赖。

**手段**：Dockerfiles 使用 `--mount=type=cache` 挂载持久化缓存卷，共享 pnpm store 和 apt 包缓存。

**源码证据**：

- PNPM store 缓存挂载到 `/root/.local/share/pnpm/store` 或 `/home/appuser/.local/share/pnpm/store`，模式为 `sharing=locked` ^[src/docker-build-cache.test.ts:28-43]
- APT 包缓存挂载到 `/var/cache/apt`，元数据缓存挂载到 `/var/lib/apt/lists`，模式均为 `sharing=locked` ^[src/docker-build-cache.test.ts:45-60]

**牺牲**：缓存卷必须挂载到 Docker daemon 所在主机，增加了 CI/CD 环境配置复杂度。locked sharing 模式防止并发构建冲突，但限制了并行构建的缓存利用。

---

## 6. Context Compaction with Configurable Strategy

**优化目标**：在长会话中保持上下文窗口可用，避免超限导致功能降级。

**手段**：提供可配置的 compaction 策略——`default` 模式和 `safeguard` 模式（更激进保护近期上下文）。支持自定义 compaction provider 插件来接管总结逻辑。预留 compaction reserve tokens 用于回复生成和工具输出。

**源码证据**：

- Compaction 支持 `"default"` 和 `"safeguard"` 两种模式 ^[src/config/schema.base.generated.ts:4277-4279]
- 支持外部 `compactionProvider` 插件的 `summarize()` 方法 ^[src/config/schema.base.generated.ts:4283-4285]
- `compactionReserveTokens` 控制为回复生成保留的 token 空间 ^[src/config/schema.base.generated.ts:4291-4293]
- Post-compaction memory reindex 默认为开启（可禁用以减少写入压力） ^[src/config/schema.base.generated.ts:4022-4026]
- Pre-compaction memory flush 可通过文件大小阈值触发 ^[src/config/schema.base.generated.ts:4438]

**牺牲**：Compaction 是破坏性操作（丢失中间历史细节），重复 compaction 会导致精度下降。需要平衡 token 储备和保留历史。

---

## 性能权衡汇总

| 优化项 | 优化目标 | 手段 | 牺牲 | 关键文件 |
|--------|---------|------|------|---------|
| Compile Cache | 启动速度 | Node.js `enableCompileCache()` | 磁盘空间、潜在陈旧字节码 | `src/entry.ts:52-57` |
| Session Store Cache | 文件 I/O | 45s TTL + mtime/size 失效 | 最终一致性（最大45s延迟） | `src/config/sessions/store-cache.ts:11-87` |
| Dynamic Import | 启动体积 | `await import()` 延迟加载 CLI | 首次调用异步延迟、静态分析困难 | `src/entry.ts:108-213` |
| Plugin Lazy Load | 插件系统开销 | `createLazyArrayView()` 惰性实例化 | 运行时首次使用冷启动 | `src/plugins/loader.ts:1137` |
| Docker Cache Mounts | 构建速度 | PNPM/APT `--mount=type=cache` | CI 环境配置复杂度 | `src/docker-build-cache.test.ts:28-60` |
| Context Compaction | 长会话稳定性 | 可配置策略 + 插件化总结 | 历史细节丢失、精度下降 | `src/config/schema.base.generated.ts:4263-4293` |
