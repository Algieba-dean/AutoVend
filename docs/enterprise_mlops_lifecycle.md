# AutoVend 企业级 MLOps & LLMOps 全生命周期架构

## 1. 架构概览 (Overview)

AutoVend 汽车销售 AI Agent 与混合 RAG 系统构建了端到端生产级 MLOps / LLMOps 闭环基础设施。模块位于 [`src/mlops/`](file:///home/algieba/projects/hackthon/AutoVend/src/mlops/)，涵盖从模型与提示词注册、实验追踪、数据版本管理、语义分布偏移与 RAG 检索劣化监控，到金丝雀灰度发布、影子路由、自动熔断回滚，以及 OpenTelemetry 追踪、Prometheus 指标导出与死信队列（DLQ）重放。

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AutoVend MLOps Lifecycle                        │
├─────────────────────┬───────────────────────┬──────────────────────────┤
│   1. 资产与注册表    │   2. 部署与流量调度   │     3. 生产监控与治理    │
│  (Asset Registry)   │ (Traffic & Canary)    │ (Drift & Observability)  │
├─────────────────────┼───────────────────────┼──────────────────────────┤
│ • ExperimentTracker │ • DeploymentRouter    │ • SemanticDriftDetector  │
│ • PromptRegistry    │ • Canary Splitting    │   - Centroid Drift       │
│ • ModelRegistry     │ • Shadow Execution    │   - JS Divergence Intent │
│ • DatasetRegistry   │ • Automated Rollback  │   - RAG Degradation      │
│                     │ • Candidate Promotion │ • OpenTelemetry Tracing  │
│                     │                       │ • Prometheus Exporter    │
│                     │                       │ • AlertManager Engine    │
│                     │                       │ • DLQReplayEngine        │
└─────────────────────┴───────────────────────┴──────────────────────────┘
```

---

## 2. 核心模块详解

### 2.1 实验追踪与多维注册表 (`src/mlops/registry.py`)
- **`ExperimentTracker`**:
  - 轻量级持久化追踪（无重型外部服务依赖），记录超参数、评价指标（召回率、忠实度、SLA 耗时、Token 开销）、产物工件（Artifacts）与 Git Commit SHA。
  - 支持 `get_best_run(experiment_name, metric, mode="max")` 自动检索最优实验超参配置。
- **`PromptRegistry`**:
  - 不可变提示词版本控制（`v1`, `v2`, ...），自动计算模板 SHA-256 指纹。
  - 严格的状态机生命周期：`DRAFT` → `CANARY` → `ACTIVE` → `ARCHIVED`。
  - 生产零停机一键回滚 (`rollback_prompt`) 与版本语义比对 (`diff_prompts`)。
- **`ModelRegistry`**:
  - 统一大模型与端点目录，维护生产部署阶段（`DEV`, `STAGING`, `CANARY`, `PRODUCTION`）。
  - 支持上线新版本时自动将旧版本归档，防止多版本混杂。
- **`DatasetRegistry`**:
  - Golden Set 及知识库切片数据集版本管理，计算 SHA-256 数据防篡改哈希，支持完整性校验 (`verify_integrity`)。

### 2.2 语义漂移与分布偏移检测 (`src/mlops/drift.py`)
- **向量空间中心漂移 (Embedding Drift)**:
  - 记录黄金基线查询的归一化中心向量 $\mathbf{c}_{\text{base}}$。
  - 实时监控生产滑动窗口查询的中心向量余弦距离 $d = 1 - \cos(\mathbf{c}_{\text{base}}, \mathbf{c}_{\text{curr}})$ 以及 P10/P50/P90 相似度分位数。
  - $d \ge 0.15$ 触发 `WARNING`，$d \ge 0.25$ 触发 `CRITICAL` 告警。
- **意图与状态分布偏移 (Intent Shift)**:
  - 计算各对话阶段与意图类别的经验概率分布 $Q$ 与基准分布 $P$。
  - 采用对称 Jensen-Shannon 散度（JS Divergence）：
    $$JS(P \parallel Q) = \frac{1}{2} D_{KL}(P \parallel M) + \frac{1}{2} D_{KL}(Q \parallel M),\quad M = \frac{1}{2}(P + Q)$$
  - 准确定位占比异动最大的异常意图类别（如咨询突发集中在售后维权或退订阶段）。
- **RAG 混合检索质量劣化 (Retrieval Degradation)**:
  - 监控滚动窗口的 Hit Rate 召回率、零命中查询占比（Zero-hit Ratio）、Top-1 置信度分值。
  - 命中率低于 90% 触发预警，低于 80% 触发严重告警。

### 2.3 金丝雀灰度、影子部署与自动回滚 (`src/mlops/deployment.py`)
- **基于 Session 确定性哈希的分流**:
  - 基于 `MD5(session_id) % 10000 / 10000.0` 计算用户流量桶，保证同一用户会话的所有轮次持续命中同一版本（Session Stickiness），消除多轮对话跨版本上下文不一致风险。
- **影子模式 (Shadow Mode)**:
  - 用户请求由基线模型/提示词实时响应，候选版本通过异步线程池并行执行，记录候选版本耗时、输出差异与护栏拒绝情况，零风险检验候选模型。
- **自动熔断回滚 (Automated Rollback Engine)**:
  - 实时统计候选版本的错误率、P95 延迟与护栏拒绝率。
  - 连续达到违反阈值（如错误率 $> 5\%$ 或 P95 耗时 $> 4.0\text{s}$）时，系统自动切断灰度流量，将流量百分之百退回基线版本并持久化事故原因记录。

### 2.4 可观测性、Prometheus 指标与死信队列重放
- **OpenTelemetry 追踪 (`src/mlops/observability.py`)**:
  - 遵循 OpenTelemetry GenAI 语义约定，记录 `gen_ai.system`、`gen_ai.usage.prompt_tokens`、`gen_ai.usage.completion_tokens`、耗时与步骤级故障归因。
- **Prometheus 格式指标导出 (`/metrics`)**:
  - 提供标准 OpenMetrics/Prometheus 文本格式：
    - `autovend_requests_total{stage="..."}`
    - `autovend_gauge_metrics{name="..."}`
    - `autovend_latency_seconds_bucket{le="..."}`
- **告警触发引擎 (`AlertManager`)**:
  - 支持多指标规则评估（错误率超标、尾部延迟超标、检索命中率下跌、语义漂移），自动归档告警事件。
- **死信队列与精确重放 (`src/mlops/dlq_replay.py`)**:
  - 自动捕获因超时、网络波动或格式解析失败的 LLM 生成与批处理评估任务。
  - 自适应指数退避与抖动重试机制（Full Jitter Backoff）。
  - 支持批量精确重放 (`replay_pending_tasks`)，并在达到最大重试次数后移入 `DEAD_LETTER` 隔离区。

---

## 3. REST API 接入端点

| 端点路径 | HTTP 方法 | 功能说明 |
|---|---|---|
| `/metrics` | `GET` | Prometheus 官方标准指标导出 |
| `/api/v1/mlops/experiments` | `GET` | 查询历史实验与基准测试运行记录 |
| `/api/v1/mlops/prompts` | `GET` | 获取指定提示词的所有版本及激活版本 |
| `/api/v1/mlops/prompts/rollback` | `POST` | 执行提示词模板秒级回滚 |
| `/api/v1/mlops/models` | `GET` | 查看大模型目录与当前所处部署阶段 |
| `/api/v1/mlops/drift` | `GET` | 实时计算并返回语义漂移报告 (支持 JSON 与 Markdown) |
| `/api/v1/mlops/canary` | `GET` | 查看灰度部署健康度、候选 vs 基线对比指标 |
| `/api/v1/mlops/canary/config` | `POST` | 动态调整灰度比例 (如 10% -> 25%) 或切换为影子模式 |
| `/api/v1/mlops/canary/rollback` | `POST` | 运维人员手动触发紧急回滚 |
| `/api/v1/mlops/dlq` | `GET` | 列出死信队列中积压的失败任务 |
| `/api/v1/mlops/dlq/replay` | `POST` | 触发死信队列任务重放 |
| `/api/v1/mlops/alerts` | `GET` | 查看近期触发的系统健康告警事件 |

---

## 4. CI/CD 自动化门禁

在 `.github/workflows/ci.yml` 中集成了 `mlops-gate`：
1. **测试套件检验**: 自动化执行 [`tests/test_mlops.py`](file:///home/algieba/projects/hackthon/AutoVend/tests/test_mlops.py)。
2. **注册表完整性检验**: 校验提示词、模型与评测数据集元数据。
3. **语义漂移回归基线检测**: 针对回归测试集自动生成漂移报告并阻断超标提交。
