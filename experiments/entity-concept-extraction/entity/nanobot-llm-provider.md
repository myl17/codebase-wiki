# LLMProvider（nanobot）

## 是什么 / 边界
nanobot 的 LLM 供应商抽象层——`LLMProvider` 抽象基类定义统一的 `chat()`/`chat_stream()` 接口，子类只需实现通信协议。基类内建完整的三级重试逻辑、429 分类、图片降级。Provider 注册通过 `ProviderSpec` 数据表驱动，新增供应商只需加一行数据和一个配置字段。

**边界**：LLMProvider 负责 LLM API 调用的通信和错误处理。不做 prompt 构建（ContextBuilder）、不做 tool 执行（ToolRegistry）、不做 context 治理（AgentRunner）。

## 关键实现
- **Provider 基类**（`providers/base.py`）：
  - `_run_with_retry()` — standard 模式 3 次指数退避，persistent 模式无限制但相同错误超限停止
  - 429 分类 — 区分配额耗尽（不重试）vs 速率限制（重试+等待），从 error type/code 和响应文本两个路径提取
  - 图片降级 — 图片内容导致的错误自动降级为纯文本重试
- **Provider Registry**（`providers/registry.py`）：
  - `PROVIDERS` 元组维护 20+ 供应商的 `ProviderSpec` 数据——自动检测规则（key 前缀、base URL 关键词）、gateway/label 检测
  - 五种 backend：`openai_compat` / `anthropic` / `azure_openai` / `openai_codex` / `github_copilot`
  - 支持 `supports_prompt_caching` 标记（Anthropic、OpenRouter）
- **子类实现**：`AnthropicProvider`（原生 anthropic SDK）、`OpenAICompatProvider`（openai SDK 覆盖所有 OpenAI 兼容 API）、`AzureOpenAIProvider`、`CodexProvider`、`GitHubCopilotProvider`

## 设计选择记录
- **维度**：Dependency Strategy
- **选择**：移除 litellm 转发层，使用原生 `openai` + `anthropic` SDK，Provider 适配代码自行维护（3,719 行）
- **替代方案**：通过 litellm 统一调用 20+ LLM provider（v0.1.4 之前的方案），享受 30+ provider 开箱即用
- **为什么有这个选择**：litellm 作为间接依赖引入了 token 计数不一致、模型名称映射错误、不可控的版本升级风险。自行维护适配层换来完全的行为可控和零间接供应商依赖。nanobot 只支持 20 个最常用 provider，维护成本可控。provider 代码 3,719 行虽多但全部自控，调试时不需要追溯第三方库行为
