---
type: entity
repo: openclaw
slug: plugin-system
problem: "如何发现、加载、验证和注册插件，使 core 保持插件无关的同时支持 100+ 个渠道/provider/tool/skill 扩展？"
generated: 2026-06-25
source_files:
  - src/plugins/
---

# Plugin System

**代码位置**：`src/plugins/`
**这个模块解决什么问题**：
- 实现层：通过 manifest-first 发现机制 + 全局注册表单例 + 惰性加载实现插件全生命周期管理，core 不硬编码任何插件
- 问题层：如何发现、加载、验证和注册插件，使 core 保持插件无关的同时支持 100+ 个渠道/provider/tool/skill 扩展？
**对外暴露什么**：
- `setActivePluginRegistry(registry, cacheKey, mode)` — 设置活动插件注册表 ^[src/plugins/runtime.ts:76]
- `PluginRegistry` 类型 — 包含 channels、providers、tools、commands、services、hooks、capabilities 等所有注册信息 ^[src/plugins/registry-types.ts]
- `OpenClawPluginDefinition` — 插件定义类型（id, name, description, kind, configSchema, register） ^[src/plugins/types.ts]
- `OpenClawPluginApi` — 插件注册 API（registerProvider, registerTool, registerCommand, registerService 等） ^[src/plugins/types.ts]
- `createPluginRuntime()` — 创建插件运行时（channel, provider, tool 等懒加载服务） ^[src/plugins/runtime.ts]
- `loadPlugins()` — 从 bundled + workspace + clawhub 加载所有插件 ^[src/plugins/loader.ts]
- `installPlugin(spec)` — 安装插件（npm spec 解析 + 安全扫描） ^[src/plugins/install.ts]
- `buildPluginRegistry(config)` — 构建完整注册表（manifest 验证 + 加载 + 捕获） ^[src/plugins/registry.ts]
**它和谁交互**：
- 依赖 [[entities/plugin-sdk]]（插件遵循的契约）
- 依赖 [[entities/config-system]]（插件配置验证）
- 依赖 [[entities/channel-system]]（渠道插件注册到渠道注册表）
- 依赖 [[entities/model-configuration]]（provider 插件注册）
- 被 [[entities/gateway]] 在启动时初始化
- 被 [[entities/cli-system]] 用于插件管理命令
**为什么它是可分离的**：独立的插件生命周期管理模块，通过 registry 单例 + DI 模式与 core 交互

**关键机制**（源码可见）：
- Manifest-first：发现和验证先于插件运行时执行，支持静态安全检查 ^[src/plugins/AGENTS.md]
- 全局注册表单例：`PLUGIN_REGISTRY_STATE` Symbol 存储，`activeRegistry` + `activeVersion` 实现热重载 ^[src/plugins/runtime.ts:13-40]
- 三个注册表面：主注册表 + `httpRoute`（HTTP 路由 pinned）+ `channel`（渠道 pinned） ^[src/plugins/runtime.ts:22-32]
- 插件源分类：`bundled`（随 core 发布）、`managed`（npm 安装）、`workspace`（本地开发） ^[src/plugins/loader.ts]
- 安装安全扫描：npm 依赖 denylist + 静态代码审计钩子 ^[src/plugins/install-security-scan.ts]
- 惰性服务模块：`createPluginRuntime()` 返回 `{ channel, provider, tool, ... }` 懒加载对象 ^[src/plugins/runtime.ts]

**源码证据**：
- 注册表核心：src/plugins/registry.ts、src/plugins/registry-types.ts
- 运行时管理：src/plugins/runtime.ts、src/plugins/runtime-state.ts
- 插件加载：src/plugins/loader.ts
- 安装管理：src/plugins/install.ts、src/plugins/uninstall.ts、src/plugins/update.ts
- Manifest 处理：src/plugins/manifest.ts、src/plugins/manifest-registry.ts
- 边界规则：src/plugins/AGENTS.md
