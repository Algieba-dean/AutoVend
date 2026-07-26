# AutoVend

智能汽车销售助手：混合检索（结构化预过滤 + 稠密 + 稀疏）驱动的有状态销售 Agent。

AutoVend 通过多阶段对话引导客户 —— 从问候和画像收集，到需求分析和车辆推荐，
再到试驾预约 —— 全程由与后端解耦的 AI 智能体驱动。

## 架构

```
┌──────────────────────────────────────────────────────────────┐
│  frontend/  (React 18 + MUI)                                 │
│  Chat · UserProfile · DealerPortal                           │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTP /api/*
┌───────────────────────────┴──────────────────────────────────┐
│  backend/app/  (FastAPI 薄编排层)                             │
│  路由 · 会话生命周期 · JSON 存储 · /health · /telemetry/llm    │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────────┐
│  src/  (核心库，零 web 依赖)                                   │
│                                                              │
│  privacy/     Presidio 中文 PII 识别 · 可逆脱敏                │
│  semantic_router/  锚点向量分类（µs 级，控制流短路）            │
│                                                              │
│  agent/       SalesAgent · 阶段 FSM · 抽取器 · 记忆 · 语音     │
│               observe() → 检索 → respond()                    │
│               ⚠ 禁止 import backend/fastapi/chromadb（CI 守卫）│
│                                                              │
│  retrieval/   HybridPipeline：意图解析 → SQLite 结构化预过滤   │
│               → 稠密(ChromaDB) + 稀疏(BM25) → RRF 融合         │
│                                                              │
│  filter/      LabelRegistry · FilterEngine（含降级阶梯）       │
│  rag/         BGE-M3 嵌入 · ChromaDB 向量库 · 检索器            │
│  llm/         HybridRouter：本地 vLLM ↔ 云端链 · 遥测          │
│  eval/        黄金集 · 检索指标 · CI 门禁 · RAGAS              │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────┴──────────────────────────────────┐
│  数据：DataInUse/VehicleData/ (1281 款车 · 56 维标签 TOML)      │
│  索引：data/vehicles.db (SQLite) · chroma_db/ · bm25_index.pkl │
└──────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18, Material-UI, Axios |
| 后端 | FastAPI, Pydantic v2, Uvicorn |
| Agent | LlamaIndex 协议, 阶段 FSM, ChatMemoryBuffer |
| 检索 | ChromaDB (HNSW) + rank-bm25 + SQLite 元数据预过滤, RRF 融合 |
| 嵌入 | BGE-M3 (中英双语, 1024 维) |
| 推理 | 本地 vLLM (8B 4-bit) + 云端链 (Groq → DeepSeek) |
| 隐私 | Presidio + 自建中文识别器，会话内可逆脱敏 |
| 意图 | 锚点向量（K-means 离线聚类，156 KB 常驻 FP32） |
| 评估 | 116 题黄金集 · recall/precision/MRR/NDCG · RAGAS |
| CI | GitHub Actions：lint · test · 架构隔离 · **检索质量门禁** |

## 快速开始

### 环境要求

- Python ≥ 3.11、[uv](https://docs.astral.sh/uv/)
- Node.js ≥ 18（前端）
- 可选：NVIDIA GPU（本地推理，见 [混合推理文档](docs/hybrid_inference.md)）

### 1. 安装与配置

```bash
uv sync --all-extras
cp .env.example .env      # 填入 LLM_API_KEY（或 GROQ_API_KEY）
```

没有任何 API key 也能启动：系统自动降级为 MockLLM，检索、阶段流转、存储等
非生成路径全部可用。

### 2. 构建索引与锚点

```bash
uv run python -m src.main build                       # 三层检索索引
uv run python -m spacy download en_core_web_lg        # Presidio 需要
uv run python -m src.semantic_router.build --probe    # 语义路由锚点
```

索引一次性构建 SQLite 结构化目录、ChromaDB 向量索引、BM25 稀疏索引；锚点由种子语料
经 K-means 聚类而成，服务启动时载入为常驻 FP32 张量。

### 3. 启动

```bash
# 后端
uv run python -m uvicorn backend.app.main:app --port 8000 --reload
# API 文档：http://localhost:8000/docs

# 前端
cd frontend && npm install && npm start
```

### 4. 可选：启用本地推理

```bash
./scripts/serve_local_llm.sh              # 独立 venv 里的 vLLM
# .env 中：LOCAL_LLM_BASE_URL=http://127.0.0.1:8101/v1
```

控制路径（查询解析、画像/需求抽取）转由本地 8B 模型服务，实测 TTFT p50 从
1.7 s 降到 0.064 s；客户可见的推荐话术仍走云端。详见
[docs/hybrid_inference.md](docs/hybrid_inference.md)。

## 检索质量

所有数字来自 116 题黄金集，真值是**独立于系统手写的 SQL 谓词**（不查
QueryParser / FilterEngine，避免自己给自己打分）。复现：

```bash
uv run python -m src.eval.runner --systems filter bm25 dense hybrid fusion
```

| 系统 | capped_recall@3 | hit_rate@3 | MRR |
|---|---|---|---|
| `filter` 仅结构化过滤 | 0.434 | 0.466 | 0.446 |
| `bm25` 纯词法 | 0.707 | 0.802 | 0.777 |
| `dense` 纯向量 | 0.707 | 0.845 | 0.782 |
| `hybrid` 预过滤 → 稠密 | 0.701 | 0.793 | 0.755 |
| **`fusion` 预过滤 → 稠密+BM25 → RRF** | **0.756** | 0.836 | **0.794** |

两路互补：BM25 在中文查询上只有 0.178（语料为英文），稠密路在冷门品牌上只有
0.333；融合后分别是 0.778 和 0.833。

融合权重经网格搜索确定（`python -m src.eval.weight_search`）：两端明显更差
（纯稀疏 0.707 / 纯稠密 0.681），中间 dense ∈ [0.20, 0.70] 是一片平台——差异全在
单题噪声（1/116 = 0.0086）以内，所以取等权而非 arg-max。基于意图的动态权重实现了
也测了，**分数低于静态权重**，默认关闭，详见 [src/retrieval/fusion.py](src/retrieval/fusion.py)。

`fusion` 是生产路径，CI 每次 push 用 [src/eval/gate.py](src/eval/gate.py) 对着
实测基线校验，低于容差直接阻断合并。

## 测试

```bash
uv run python -m pytest tests/ -m "not slow"    # 快速套件（500+）
uv run python -m pytest tests/ -m slow          # 需真实索引与嵌入模型
uv run python -m pytest tests/test_agent_isolation.py   # 架构隔离守卫
uv run python -m src.eval.gate                  # 检索质量门禁
```

> 注意用 `python -m pytest`：直接 `pytest` 可能解析到系统 Python 的版本。

## 对话阶段

```
WELCOME → PROFILE_ANALYSIS → NEEDS_ANALYSIS → CAR_SELECTION
                                                    ↓ ↑
                                          RESERVATION_4S
                                                    ↓ ↑
                                    RESERVATION_CONFIRMATION → FAREWELL
```

阶段转移由 Pydantic 状态字段决定，不交给 LLM 自由裁量 —— 流程是确定性的，
只有内容是生成的。

## 文档

- [混合推理架构](docs/hybrid_inference.md) —— 本地/云端分流依据、WSL2 部署坑、实测数字
- [脱敏与语义路由](docs/privacy_and_routing.md) —— PII 拦截、锚点向量、双重阈值
- [混合检索方案](docs/hybrid-retrieval-plan.md) —— 三层检索设计
- [性能指标](docs/PERFORMANCE_METRICS.md) · [测试指南](docs/TESTING_GUIDE.md)
- [部署指南](docs/deployment_guide.md)
- [问题记录](docs/record.md) —— 本轮遇到的 30 个问题、根因、解法与实测效力

## License

MIT
