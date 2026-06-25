# Security（nanobot）

## 是什么 / 边界
nanobot 的安全防护层——SSRF 私有网络拦截 + exec 沙箱 + workspace 隔离。集中覆盖 agent 框架最不可出错的三个安全面：网络出口、命令执行、文件系统边界。

**边界**：Security 只负责安全拦截和防护。不做一般的网络安全（TLS/认证由 LLM Provider 层处理）、不做输入验证（ToolRegistry 负责）。

## 关键实现
- **SSRF 防护**（`security/network.py`）：10 个 CIDR 私有网络块拦截，防止 agent 访问内网地址。支持通过 `configure_ssrf_whitelist()` 自定义白名单
- **Exec 沙箱**：命令执行在隔离的 workspace 目录中进行，限制文件系统访问范围
- **Workspace 隔离**：测试中使用 `tmp_path` fixture 和临时 workspace 目录——防止测试中的 shell 命令影响真实文件系统
- **测试投入集中**：`test_exec_security.py`、`test_web_fetch_security.py`、`test_sandbox.py` 覆盖安全关键路径

## 设计选择记录
- **维度**：Testing Philosophy
- **选择**：测试投入集中在安全（SSRF、沙箱、workspace 隔离）和跨平台兼容性——26,048 行测试代码（5.7x 核心运行时）中安全测试比重最大
- **替代方案**：均衡分配测试资源到所有模块，或依赖外部安全审计而非自建测试
- **为什么有这个选择**：agent 框架中安全漏洞的后果远大于功能 bug——一个 SSRF 漏洞可能让 agent 成为内网跳板，一个 exec 逃逸可能让 agent 获得宿主机权限。因此安全测试的投入远超其他模块，即使这意味着其他功能域的测试覆盖相对薄弱
