# 混合推理架构（Hybrid Inference）

本地 vLLM 承接控制路径，云端 API 承接合成路径。本文说明分流依据、部署方式、
降级行为，以及如何复现所有引用的数字。

## 分流依据

系统里的 LLM 调用只有两种形状，路由按形状而不是按"贵贱"划分：

| | 控制路径 | 合成路径 |
|---|---|---|
| 任务 | 查询解析、画像/需求/预约抽取 | 车辆对比与推荐话术 |
| 输出 | schema 约束的短 JSON | 开放式长文本，客户直接阅读 |
| 频率 | **每轮 1–3 次**，必然发生 | 每轮 1 次 |
| 质量要求 | 输出空间被 schema 限死，8B 足够 | 质量主导，用最强的模型 |
| 路由 | **本地 Llama-3.1-8B AWQ-INT4** | **云端（Groq Llama-3.3-70B）** |

任务枚举在 [src/llm/router.py](../src/llm/router.py) 的 `Task` / `LOCAL_TASKS`；
新增调用点时在那里归类一次即可，不要在调用处内联挑模型。

## 组件

```
┌────────────────────────────────────────────────────────┐
│  SalesAgent（不知道路由存在，见架构隔离守卫）              │
│    llm=RoutedLLM(EXTRACTION)  gen=RoutedLLM(GENERATION) │
└──────────────┬─────────────────────────────────────────┘
               │ LlamaIndex 协议
┌──────────────┴─────────────────────────────────────────┐
│  HybridRouter（src/llm/router.py）                      │
│    Task → 后端选择 · 单次健康探测 · 双向降级              │
│    每次调用记录 telemetry（route/TTFT/tokens/cost）      │
└──────┬───────────────────────────────┬─────────────────┘
       │ OpenAI 协议                    │ OpenAI 协议
┌──────┴─────────────┐        ┌────────┴────────────────┐
│ vLLM :8100         │        │ Groq API                │
│ Llama-3.1-8B       │        │ llama-3.3-70b-versatile │
│ AWQ-INT4（4bit）    │        │                         │
└────────────────────┘        └─────────────────────────┘
```

`LLMParser`（检索侧的 LLM fallback）通过 `router.bind(Task.QUERY_PARSE)` 拿到一个
`BaseLLM` 形状的视图，同样被路由与遥测覆盖。

## 部署本地服务

```bash
# 1. vLLM 装在独立 venv —— 它锁定的 torch 版本与主环境不同，
#    混装会把 torch 2.10 升到 2.11 并动 109 个包，殃及 BGE-M3/ChromaDB。
uv venv --python 3.12 .venv-vllm
VIRTUAL_ENV=$PWD/.venv-vllm uv pip install vllm

# 2. 从 ModelScope 下载权重（HF 的 xet CDN 在本网络环境下多次中断）
VIRTUAL_ENV=$PWD/.venv-vllm uv pip install modelscope
.venv-vllm/bin/modelscope download \
  --model LLM-Research/Meta-Llama-3.1-8B-Instruct-AWQ-INT4 \
  --local_dir ./models/Meta-Llama-3.1-8B-Instruct-AWQ-INT4

# 3. 起服务（脚本自动优先本地权重）
./scripts/serve_local_llm.sh

# 4. 在 .env 里启用本地路由
#    LOCAL_LLM_BASE_URL=http://127.0.0.1:8100/v1
```

### WSL2 的两个坑（脚本已处理，此处备档）

1. **`RuntimeError: UVA is not available`** —— vLLM V1 引擎需要 pinned host
   memory，但在 WSL 下保守禁用。内核 ≥ 4.19.121 且 torch 的 `pin_memory=True`
   实测可用时，设 `VLLM_WSL2_ENABLE_PIN_MEMORY=1` 显式开启。
2. **torch.compile 静默死锁** —— inductor 的并行编译 worker 在 WSL2 下 fork
   不安全：现象是 EngineCore 进程 128 线程全部停在 `futex_do_wait`、CPU ~5%、
   日志无输出、永不恢复。脚本默认 `--enforce-eager` 绕过。代价是解码吞吐而非
   TTFT（CUDA graph 主要加速逐 token 解码；TTFT 由 prefill 主导），对只跑短
   控制路径 prompt 的本场景是正确取舍。

## 降级行为（不对称，有意为之）

| 故障 | 行为 | 代价 |
|---|---|---|
| 本地挂 | 控制路径转云端 | 成本上升，正确性不变 |
| 云端挂 | 合成路径转本地 8B | 质量下降，服务不中断 |
| 都挂 | 该请求报错 | — |

本地失败一次即标记不健康（不再为死服务器反复付超时），服务恢复后调
`router.reset_health()` 或重启进程。

## 遥测与验证

- `GET /health` —— 当前路由表（哪些任务在本地、模型与端点）。
- `GET /telemetry/llm` —— 各路由/各任务的调用数、延迟与 TTFT 百分位、token
  总量、实际花费 vs 全云端反事实成本。进程内存级，重启清零。
- **基准**：`uv run python -m src.eval.routing_bench --n 30` —— 用真实的抽取
  prompt 与解析 prompt（非合成 hello）对比本地/云端 TTFT 与成本，结果写入
  `evaluation/results/routing_bench.json`。

> 引用任何 TTFT / 成本数字前先跑基准。数字随硬件、量化方式与云端排队情况变化，
> 这份文档故意不内嵌任何未标注出处的数值。

## 已知限制

- TTFT 通过流式响应测得（`OpenAILLM` 默认流式），但 `RoutedLLM` 对上层仍是
  单次返回——agent 目前没有增量消费 token 的地方。要做端到端 SSE 时再把流
  穿透上去。
- 遥测是进程内的开发/评估仪表，不是监控系统；多进程部署各自独立计数。
- 本地模型只有在 `LOCAL_LLM_BASE_URL` 配置且健康检查通过时才参与路由；
  CI 里不起 vLLM，控制路径自动全部走云端（或 mock），行为不变。
