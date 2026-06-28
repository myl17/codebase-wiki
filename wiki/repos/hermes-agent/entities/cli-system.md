---
type: entity
repo: hermes-agent
slug: cli-system
problem: 如何提供一个功能完备的命令行界面，支持交互式聊天、模型切换、配置管理、诊断和 24 个子命令
generated: 2026-06-25
source_files:
  - cli.py
  - hermes_cli/main.py
  - hermes_cli/commands.py
  - hermes_cli/config.py
  - hermes_cli/auth.py
  - hermes_cli/setup.py
  - hermes_cli/doctor.py
  - hermes_cli/backup.py
  - hermes_cli/profiles.py
  - hermes_cli/tools_config.py
  - hermes_cli/models.py
  - hermes_cli/model_switch.py
  - hermes_cli/gateway.py
  - hermes_cli/cron.py
  - hermes_cli/logs.py
  - hermes_cli/plugins_cmd.py
  - hermes_cli/completion.py
  - hermes_cli/skin_engine.py
  - hermes_cli/banner.py
  - hermes_cli/runtime_provider.py
---

# CLI 系统

**代码位置**：`cli.py`、`hermes_cli/main.py`、`hermes_cli/` 包
**这个模块解决什么问题**：
- 实现层：通过 argparse 子命令架构提供 24+ CLI 子命令，包括交互式聊天（prompt_toolkit TUI）、模型选择（交互式搜索 UI）、配置管理、诊断、备份、profile 管理和 shell 补全
- 问题层：如何提供一个功能完备的命令行界面，支持交互式聊天、模型切换、配置管理、诊断和 24 个子命令
**对外暴露什么**：`main()` 函数（hermes_cli/main.py:4742，argparse 分发入口）
**它和谁交互**：
- 依赖 [[entities/agent-core]]（`cmd_chat()` 创建 AIAgent 实例启动交互式会话）
- 依赖 [[entities/gateway-runner]]（`cmd_gateway()` 管理 gateway 生命周期）
- 依赖 [[entities/provider-registry]]（`hermes model` 选择 provider/model）
- 依赖 [[entities/config-system]]（config 读写）
- 依赖 [[entities/state-database]]（session 列表）
- 依赖 [[entities/cron-scheduler]]（cron 子命令管理定时任务）
- 依赖 [[entities/skills-system]]（skills 配置）
- 依赖 [[entities/security-sandbox]]（pairing 命令管理授权）
- 依赖 [[entities/logging-system]]（logs 子命令查看日志）
- 依赖 [[entities/web-server]]（dashboard 命令启动 Web UI）
- 依赖 [[entities/plugin-system]]（plugins 命令管理插件）
- 依赖 [[entities/memory-system]]（profile 管理中的记忆目录初始化）
**为什么它是可分离的**：argparse 子命令架构，每个子命令有独立 `cmd_*` 函数，添加新命令不修改现有命令

**关键机制**（源码可见）：
- 24+ 子命令：`chat`（默认交互对话）、`model`、`gateway`、`setup`、`config`、`status`、`cron`、`doctor`、`backup`/`import`、`update`、`uninstall`、`acp`、`profile`、`dashboard`、`logs`、`completion`、`login`/`logout`、`auth`、`webhook`、`dump`、`debug`、`claw`、`pairing`、`insights`^[hermes_cli/main.py:4829-6240]
- Profile 预加载：`_apply_profile_override()` 在 argparse 解析前预解析 `--profile/-p` 设置 `HERMES_HOME`，避免模块导入时缓存错误的路径 ^[hermes_cli/main.py:83]
- prompt_toolkit TUI：交互式聊天使用 `prompt_toolkit` 提供多行编辑、slash 命令自动补全、对话历史和中断重定向 ^[cli.py]
- 模型交互式选择：`hermes model` 使用 curses UI（`simple-term-menu`）提供带搜索的 provider/model 选择器 ^[hermes_cli/model_switch.py]
- 跨平台补全：`hermes completion` 生成 bash/zsh/fish 的 shell 补全脚本 ^[hermes_cli/completion.py]
- 诊断工具：`hermes doctor` 检查配置完整性、依赖可用性和环境健康，支持 `--fix` 自动修复 ^[hermes_cli/doctor.py]
- 备份与恢复：`hermes backup` 创建 zip 归档，`hermes import` 恢复 ^[hermes_cli/backup.py]
- OAuth 认证流：`hermes login` 支持 device auth（Nous Portal）和 external auth（OpenAI Codex、Qwen）^[hermes_cli/auth.py:2826]
- Skin/主题系统：`SkinEngine` 为 TUI 提供可定制的颜色方案 ^[hermes_cli/skin_engine.py]
- 欢迎提示：`hermes_cli/banner.py` 和 `hermes_cli/tips.py` 提供启动 tips 和横幅 ^[hermes_cli/banner.py]

**源码证据**：
- 入口文件：hermes_cli/main.py
- 核心函数：`def main()` ^[hermes_cli/main.py:4742]、`def cmd_chat(args)` ^[hermes_cli/main.py:4834]
