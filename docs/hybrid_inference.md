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
| 路由 | **本地 8B 4-bit（vLLM）** | **云端链：Groq 70B → DeepSeek** |

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
│    Task → 尝试序列 · 单次健康探测 · 逐级降级              │
│    每次调用记录 telemetry（route/TTFT/tokens/cost）      │
└──────┬───────────────────────────────┬─────────────────┘
       │ OpenAI 协议                    │ OpenAI 协议（有序链）
┌──────┴─────────────┐        ┌────────┴────────────────┐
│ vLLM :8101         │        │ 1. Groq 70B             │
│ 8B 4-bit 量化       │        │ 2. DeepSeek（额度耗尽时）│
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

# 2. 准备一个 4-bit 量化的 8B 模型。两条路都验证过：
#
#    a) bitsandbytes NF4（本仓当前使用）—— 需要额外装 bitsandbytes
VIRTUAL_ENV=$PWD/.venv-vllm uv pip install "bitsandbytes>=0.48.1"
LOCAL_LLM_MODEL=/path/to/Qwen3-8B-unsloth-bnb-4bit \
LOCAL_LLM_QUANT=bitsandbytes ./scripts/serve_local_llm.sh
#
#    b) AWQ-INT4（吞吐更好，Ada 上走 Marlin 内核）
VIRTUAL_ENV=$PWD/.venv-vllm uv pip install modelscope
.venv-vllm/bin/modelscope download \
  --model LLM-Research/Meta-Llama-3.1-8B-Instruct-AWQ-INT4 \
  --local_dir ./models/Meta-Llama-3.1-8B-Instruct-AWQ-INT4
./scripts/serve_local_llm.sh   # 脚本自动优先 ./models/ 下的权重

# 3. 在 .env 里启用本地路由
#    LOCAL_LLM_BASE_URL=http://127.0.0.1:8101/v1
```

**GGUF 不能用**：vLLM 0.26 已从支持的量化方式里移除 `gguf`
（`QUANTIZATION_METHODS` 里没有它）。手上如果只有 `.gguf` 文件，需要换用
llama.cpp 的 `llama-server`——它同样是 OpenAI 协议，路由层无需改动，
把 `LOCAL_LLM_BASE_URL` 指过去即可。

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

路由不是"选一个后端"，而是给每个 Task 生成一条**有序尝试序列**（`plan_for`），
逐级降级直到有结果：

| 故障 | 行为 | 代价 |
|---|---|---|
| 本地挂 | 控制路径 → Groq → DeepSeek | 成本上升，正确性不变 |
| Groq 额度耗尽 | 合成路径 → DeepSeek | 换厂商，质量相当 |
| 云端全挂 | 合成路径 → 本地 8B | 质量下降，服务不中断 |
| 全挂 | 抛出最后一个错误 | — |

本地失败一次即标记不健康（不再为死服务器反复付超时），服务恢复后调
`router.reset_health()` 或重启进程。

云端链由 `.env` 决定：`LLM_API_KEY`/`GROQ_API_KEY` 为主，`DEEPSEEK_API_KEY`
为备。这条链不是假设——实测中 Groq 免费额度耗尽返回 429 后，DeepSeek 无缝接管，
对话未中断（见 `/telemetry/llm` 的 `by_route.cloud.n_failed`）。

## 遥测与验证

- `GET /health` —— 当前路由表（哪些任务在本地、模型与端点）。
- `GET /telemetry/llm` —— 各路由/各任务的调用数、延迟与 TTFT 百分位、token
  总量、实际花费 vs 全云端反事实成本。进程内存级，重启清零。
- **基准**：`uv run python -m src.eval.routing_bench --n 30` —— 用真实的抽取
  prompt 与解析 prompt（非合成 hello）对比本地/云端 TTFT 与成本，结果写入
  `evaluation/results/routing_bench.json`。

### 实测参考值

RTX 4090 / Qwen3-8B bnb-4bit / eager 模式 / 30 次真实控制路径调用
（`routing_bench --n 15 --routes local`，`evaluation/results/routing_bench_local.json`）：

| 指标 | 本地 |
|---|---|
| TTFT p50 | **0.066 s** |
| TTFT p95 | 0.172 s |
| TTFT p99 | 0.216 s |
| 端到端 p95 | 2.04 s |
| 平均 completion token | 39 /次 |

对照：同一批 prompt 走 Groq 的 TTFT p50 约 1.2 s（该次运行 30 调用中 21 次因
免费额度耗尽失败，故基准脚本已将其标记为 `reliable: false`，此数字仅供量级参考，
不可引用）。

> 引用任何 TTFT / 成本数字前先跑基准。数字随硬件、量化方式与云端排队情况变化。
> 基准脚本在单条路由失败率 > 10% 时会把结果标记为 `reliable: false` 并在 stderr
> 告警 —— 用残缺样本算出的百分位看起来像测量结果，但不是。

### 推理模型的思维链必须关掉

Qwen3 这类模型默认输出 `<think>...</think>`。在控制路径上这是纯损耗：JSON 解析
要额外剥离、TTFT 测到的是第一个*推理* token 而非第一个有用 token、单次抽取从
~40 completion token 膨胀到 ~185（实测 1.4 s → 5.5 s）。

`extra_body_for_local()` 统一注入 `chat_template_kwargs.enable_thinking=false`，
对不实现该参数的模型是 no-op。**基准脚本必须通过 `build_default_router()` 取
后端**，否则会绕开这个配置，测出与生产不一致的数字（早期版本正是如此，
completion token 虚高 4 倍）。

## 已知限制

- TTFT 通过流式响应测得（`OpenAILLM` 默认流式），但 `RoutedLLM` 对上层仍是
  单次返回——agent 目前没有增量消费 token 的地方。要做端到端 SSE 时再把流
  穿透上去。
- 遥测是进程内的开发/评估仪表，不是监控系统；多进程部署各自独立计数。
- 本地模型只有在 `LOCAL_LLM_BASE_URL` 配置且健康检查通过时才参与路由；
  CI 里不起 vLLM，控制路径自动全部走云端（或 mock），行为不变。
