# vLLM Model Configuration Directory

本目录包含了用于通过 `vllm` 启动本地大模型（如 `Qwen3-8B-unsloth-bnb-4bit`）的配置文件说明及参数定义。

## 目录结构

```
configs/vllm/
├── qwen3_8b_bnb_4bit.json   # Qwen3-8B 4bit 模型的 JSON 配置文件
├── qwen3_8b_bnb_4bit.yaml   # Qwen3-8B 4bit 模型的 YAML 配置文件
└── README.md                # 配置说明文档
```

## 参数说明

| 配置字段 | 类型 | 说明 | 默认值 |
| :--- | :--- | :--- | :--- |
| `model_name` | string | 模型名称标识 | `Qwen3-8B-unsloth-bnb-4bit` |
| `served_model_name` | string | OpenAI 兼容接口对外暴露的模型名称 | `qwen3-8b-bnb-4bit` |
| `model_path` | string | 模型权重路径（支持 `~` 相对路径和绝对路径） | `~/models/Qwen/Qwen3-8B-unsloth-bnb-4bit` |
| `venv_path` | string | vLLM 虚拟环境路径 | `.venv-vllm` |
| `host` | string | 监听的主机 IP 地址 | `0.0.0.0` |
| `port` | int | 监听的端口号 | `8101` |
| `quantization` | string | 量化方式（bitsandbytes / awq / fp8 / auto） | `bitsandbytes` |
| `dtype` | string | 模型计算精度 (bfloat16 / float16 / auto) | `bfloat16` |
| `gpu_memory_utilization` | float | GPU 显存占用比例上限 | `0.6` |
| `max_model_len` | int | 最大上下文序列长度 | `8192` |
| `trust_remote_code` | bool | 是否信任远程代码 | `true` |
| `enforce_eager` | bool | 是否强制执行 Eager 模式 (建议在 WSL2 或 Inductor 异常时开启) | `true` |
| `extra_args` | array | 传给 vLLM 的额外参数列表 | `[]` |

## 启动方式

使用根目录或 `scripts` 下的启动脚本：

```bash
# 方式1: 运行 Shell 启动脚本 (默认读取 configs/vllm/qwen3_8b_bnb_4bit.json)
bash scripts/start_vllm_qwen3.sh

# 方式2: 运行 Python 启动脚本 (支持指定配置文件和命令行覆盖参数)
.venv-vllm/bin/python scripts/start_vllm.py --config configs/vllm/qwen3_8b_bnb_4bit.json

# 方式3: 命令行临时覆盖端口或显存占比
.venv-vllm/bin/python scripts/start_vllm.py --config configs/vllm/qwen3_8b_bnb_4bit.yaml --port 8102 --gpu-memory-utilization 0.5
```
