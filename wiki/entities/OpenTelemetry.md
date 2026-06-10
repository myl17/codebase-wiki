---
type: entity
category: 技术栈
---

# OpenTelemetry

云原生可观测性标准，统一 Traces、Metrics、Logs 三路信号的采集和导出协议，支持多种 exporter backend。

## 在各 repo 中的体现

- [[openclaw/dimensions/openclaw-architecture]] — `extensions/diagnostics-otel/` 实现完整集成：OTLPTraceExporter + OTLPMetricExporter + OTLPLogExporter 三路并行导出；采样率通过 TraceIdRatioBasedSampler 配置；敏感内容上报前经 redactSensitiveText 处理
