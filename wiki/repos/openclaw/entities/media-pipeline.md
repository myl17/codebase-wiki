---
type: entity
repo: openclaw
slug: media-pipeline
problem: "如何处理用户上传的多媒体文件（图片/音频/视频/文档），支持格式检测、尺寸限制、图像优化和 SSRF 保护？"
generated: 2026-06-25
source_files:
  - src/media/
---

# Media Pipeline

**代码位置**：`src/media/`
**这个模块解决什么问题**：
- 实现层：下载 → MIME 检测 → 格式转换（HEIC→JPEG）→ 图像优化（sharp/sips 后端）→ 尺寸限制强制执行 → TTL 清理
- 问题层：如何处理用户上传的多媒体文件（图片/音频/视频/文档），支持格式检测、尺寸限制、图像优化和 SSRF 保护？
**对外暴露什么**：
- `downloadToFile(url, destDir)` — 下载媒体到磁盘（SSRF 保护） ^[src/media/store.ts]
- `cleanOldMedia(ttlMs)` — TTL 清理过期的媒体文件 ^[src/media/store.ts]
- `resolveWebMedia(source, opts)` — 高层媒体摄取（URL/本地路径/base64） ^[src/media/web-media.ts]
- `detectMime(buffer)` — MIME 类型检测 ^[src/media/mime.ts]
- `convertHeicToJpeg(buffer)` — HEIC/HEIF 转换 ^[src/media/image-ops.ts]
- `optimizeImageToPng(buffer)` — PNG 优化 ^[src/media/image-ops.ts]
- `resizeToJpeg(buffer, maxSide)` — JPEG 缩放 ^[src/media/image-ops.ts]
- `fetchRemoteMedia(url, opts)` — 远程媒体获取（SSRF 保护） ^[src/media/fetch.ts]
- `MediaKind` — 媒体类型：`"image" | "audio" | "video" | "document"` ^[src/media/constants.ts]
**它和谁交互**：
- 依赖 [[entities/security-system]]（SSRF 策略、local root 策略、host-read 能力检查）
- 被 [[entities/agent-runtime]]（agent 处理入站媒体附件）
- 被渠道 adapter（消息平台传递媒体附件）
**为什么它是可分离的**：独立的媒体处理管道，输入文件→输出标准化结果

**关键机制**（源码可见）：
- 按媒体类型设置大小限制：图片 6MB、音频 16MB、视频 16MB、文档 100MB ^[src/media/constants.ts]
- 图像处理双后端：优先 `sharp`（npm 模块），降级 `sips`（macOS 原生），通过 `OPENCLAW_IMAGE_BACKEND` 控制 ^[src/media/image-ops.ts]
- JPEG 渐进质量降低：`[85, 75, 65, 55, 45, 35]` 逐档尝试 ^[src/media/image-ops.ts]
- 最大输入像素 25M，resize 侧边网格 `[maxSide, 1800, 1600, 1400, 1200, 1000, 800]` ^[src/media/image-ops.ts]
- 存储格式：`{original}---{uuid}.{ext}` 保留原始文件名 ^[src/media/store.ts]
- SSRF 保护：`fetchWithSsrFGuard` 防止请求内部网络地址 ^[src/media/fetch.ts]
- TTL 默认 2 分钟，`cleanOldMedia` 递归清理过期文件 ^[src/media/store.ts]

**源码证据**：
- 存储引擎：src/media/store.ts
- Web 媒体处理：src/media/web-media.ts
- MIME 检测：src/media/mime.ts
- 图像操作：src/media/image-ops.ts
- 远程获取：src/media/fetch.ts
- 大小限制：src/media/constants.ts
