# SessionManager（nanobot）

## 是什么 / 边界
nanobot 的会话持久化层——会话以 JSONL 文件存储（第一行 `_type: metadata`），`get_or_create()` 是唯一天地入口。内存缓存 + 惰性加载。历史裁剪保证从合法边界（user-turn）开始。

**边界**：SessionManager 只负责会话数据的存储、加载、裁剪。不做上下文组装（ContextBuilder）、不做记忆处理（Memory System）。

## 关键实现
- **JSONL 格式**：第一行为 `_type: metadata` 元数据行，后续每行是一条消息——人类可读、追加友好
- **惰性加载**：`get_or_create()` 首次访问时才从磁盘加载完整历史，避免冷启动时全量读取
- **合法边界裁剪**：`get_history()` 或 `retain_recent_legal_suffix()` 将历史裁剪为合法边界——确保不会从 tool result 中间开始（导致孤立的 tool 调用），裁剪总是对齐到 user-turn
- **内存缓存**：加载后的会话缓存在内存中，减少重复 I/O

## 设计选择记录
- **维度**：Architecture
- **选择**：JSONL 文件 + 惰性加载 + 合法边界裁剪——会话以逐行追加的 JSONL 文件存储，首次访问时才加载，裁剪确保不从 tool result 中间开始
- **替代方案**：SQLite 数据库（结构化查询、事务支持）、或全内存存储（最快但无持久化）
- **为什么有这个选择**：JSONL 是人类可读的纯文本格式，追加写入无锁竞争，适合单进程 agent。惰性加载避免启动时全量 I/O。合法边界裁剪是 agent 特有的需求——发给 LLM 的历史如果从 tool result 开始会导致 LLM 看到不完整的 tool-call 对，必须从 user-turn 开始
