# AutoVend 工业级全栈可观测性系统 (Industrial Observability Stack)

本目录提供生产级分布式链路追踪（Distributed Tracing）、指标监控（Metrics）与日志聚合（Logs）全套云原生观测方案。

---

### 🏛️ 技术栈架构 (Stack Architecture)

- **OpenTelemetry Collector (`:4317` / `:4318`)**：统一代理网关，接收 FastAPI、vLLM 与 Agent 发送的 OTLP Traces 与 Metrics。
- **Prometheus (`:9090`)**：指标监控数据库，自动抓取 vLLM（显存/KV Cache/QPS）、FastAPI 与 Collector 统计指标。
- **Grafana Tempo (`:3200`)**：分布式链路追踪后端，高效存储全量 Trace ID 拓扑。
- **Grafana Loki (`:3100`)**：日志聚合后端，支持基于 Trace ID 进行日志与链路联动双向跳转。
- **Grafana 仪表盘 (`:3001`)**：可视化控制台，开箱即用自动关联 Prometheus、Tempo 和 Loki 数据源。

---

### 🔌 端口映射与服务一览 (Services & Ports)

| 服务名称 | 监听端口 | 说明 / 访问方式 |
| :--- | :--- | :--- |
| **Grafana 控制台** | `http://localhost:3001` | **用户名/密码**: `admin` / `admin` |
| **OTEL Collector gRPC** | `localhost:4317` | 应用层发送 OTLP Traces (gRPC) |
| **OTEL Collector HTTP** | `localhost:4318` | 应用层发送 OTLP Traces (HTTP) |
| **Prometheus Web UI** | `http://localhost:9090` | 指标查询控制台 |
| **Loki Log Ingestion** | `http://localhost:3100` | 日志采集 HTTP 接口 |
| **Tempo API** | `http://localhost:3200` | 链路查询 API |

---

### 🚀 一键启动步骤 (Quick Start)

在项目根目录下，执行以下命令即可启动全套可观测性容器服务：

```bash
cd configs/observability
docker compose up -d
```

查看容器运行状态：

```bash
docker compose ps
```

---

### 🐍 Python / FastAPI 应用接入指南 (Instrumentation)

在 AutoVend 后端项目中，使用 `traceloop-sdk` 或 `opentelemetry-sdk` 自动植入链路追踪：

#### 1. 安装依赖
```bash
.venv/bin/pip install traceloop-sdk opentelemetry-exporter-otlp
```

#### 2. 代码接入（`backend/app/main.py`）
```python
from traceloop.sdk import Traceloop

# 在服务启动时初始化 Traceloop (自动注入 OpenAI, vLLM, ChromaDB 链路)
Traceloop.init(
    app_name="autovend-backend",
    api_endpoint="http://localhost:4317", # 发送到 OTEL Collector gRPC 端口
    disable_batch=False,
)
```

启动应用后，访问 **`http://localhost:3001`** 登录 Grafana，即可在 **Explore ➔ Tempo** 中检索全量 Agent 链路拓扑与实时性能曲线！
