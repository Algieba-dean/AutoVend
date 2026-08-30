# vLLM Model Configuration Directory

本目录包含了用于通过 `vllm` 启动本地大模型（如 `Qwen3-8B-unsloth-bnb-4bit`）的配置文件说明及参数定义。

## 目录结构

```
configs/vllm/
├── qwen3_8b_bnb_4bit.json       # Qwen3-8B 4bit 模型的 JSON 配置文件 (轻量级)
├── qwen3_8b_bnb_4bit.yaml       # Qwen3-8B 4bit 模型的 YAML 配置文件
├── qwen3.8_27b_nvfp4.json       # Qwen3.8-27B NVFP4 (Unsloth Dynamic V3.0) 配置文件 (高性能)
├── qwen3.8_27b_nvfp4.yaml       # Qwen3.8-27B NVFP4 YAML 配置文件
└── README.md                    # 配置说明文档
```

## 候选模型对照 (Candidate Models)

| 模型版本 | 模型目录 | 量化格式 | 显存占比要求 (RTX 4090 24G) | 特点与推荐场景 |
| :--- | :--- | :--- | :--- | :--- |
| **Qwen3-8B-unsloth-bnb-4bit** | `~/models/Qwen/Qwen3-8B-unsloth-bnb-4bit` | `bitsandbytes` (4bit) | `~0.60` (占用约 8~10GB) | 极速首字响应 (TTFT)，轻量低显存开销 |
| **Qwen3.8-27B-NVFP4** | `~/models/Qwen/Qwen3.8-27B-NVFP4` | `compressed-tensors` (NVFP4 / FP8 lm_head) | `~0.92` (占用约 21~22GB) | SOTA Agent 规划与复杂槽位抽取，支持 MTP |

## 参数说明

| 配置字段 | 类型 | 说明 | 默认值 |
| :--- | :--- | :--- | :--- |
| `model_name` | string | 模型名称标识 | `Qwen3.8-27B-NVFP4` / `Qwen3-8B-unsloth-bnb-4bit` |
| `served_model_name` | string | OpenAI 兼容接口对外暴露的模型名称 | `qwen3.8-27b-nvfp4` / `qwen3-8b-bnb-4bit` |
| `model_path` | string | 模型权重路径（支持 `~` 相对路径和绝对路径） | `~/models/Qwen/Qwen3.8-27B-NVFP4` |
| `venv_path` | string | vLLM 虚拟环境路径 | `.venv-vllm` |
| `host` | string | 监听的主机 IP 地址 | `0.0.0.0` |
| `port` | int | 监听的端口号 | `8101` |
| `quantization` | string | 量化方式（compressed-tensors / bitsandbytes / awq / fp8 / auto） | `compressed-tensors` |
| `dtype` | string | 模型计算精度 (bfloat16 / float16 / auto) | `bfloat16` |
| `gpu_memory_utilization` | float | GPU 显存占用比例上限 | `0.92` (27B) / `0.6` (8B) |
| `max_model_len` | int | 最大上下文序列长度 | `8192` |
| `trust_remote_code` | bool | 是否信任远程代码 | `true` |
| `enforce_eager` | bool | 是否强制执行 Eager 模式 (建议在 WSL2 或 Inductor 异常时开启) | `true` |
| `extra_args` | array | 传给 vLLM 的额外参数列表 | `["--enable-prefix-caching"]` |

## 启动方式

使用根目录或 `scripts` 下的启动脚本：

```bash
# ----------------------------------------------------
# 选项 A: 启动 Qwen3.8-27B-NVFP4 (高精度、强 Agent 规划能力)
# ----------------------------------------------------
# 1. Shell 一键启动:
bash scripts/start_vllm_qwen3_8_27b.sh

# 2. Python 脚本启动:
.venv-vllm/bin/python scripts/start_vllm.py --config configs/vllm/qwen3.8_27b_nvfp4.json

# ----------------------------------------------------
# 选项 B: 启动 Qwen3-8B-unsloth-bnb-4bit (轻量极速)
# ----------------------------------------------------
# 1. Shell 一键启动:
bash scripts/start_vllm_qwen3.sh

# 2. Python 脚本启动:
.venv-vllm/bin/python scripts/start_vllm.py --config configs/vllm/qwen3_8b_bnb_4bit.json
```

## AutoVend 后端对接配置 (`.env`)

如果切换本地模型为 Qwen3.8-27B-NVFP4，只需在 `.env` 中确认：

```env
LOCAL_LLM_BASE_URL=http://127.0.0.1:8101/v1
LOCAL_LLM_MODEL=qwen3.8-27b-nvfp4
```
