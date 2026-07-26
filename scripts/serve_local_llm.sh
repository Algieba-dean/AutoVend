#!/usr/bin/env bash
# Launch the local vLLM inference server.
#
# vLLM lives in its own virtualenv (.venv-vllm) because it pins a different
# torch build than the main project: installing it alongside would upgrade
# torch 2.10 -> 2.11 and pull ~109 packages, putting the BGE-M3 / ChromaDB
# stack that the whole evaluation harness depends on at risk. Serving it over
# HTTP is also how vLLM is deployed in practice — it is a server, not a library.
#
# Usage:  ./scripts/serve_local_llm.sh [--port 8100]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv-vllm"

# Prefer locally downloaded weights (via modelscope — see README) over a hub
# id: HF's xet CDN proved unreliable from this network, failing mid-download.
#   .venv-vllm/bin/modelscope download \
#     --model LLM-Research/Meta-Llama-3.1-8B-Instruct-AWQ-INT4 \
#     --local_dir ./models/Meta-Llama-3.1-8B-Instruct-AWQ-INT4
DEFAULT_MODEL="hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4"
if [ -d "$ROOT/models/Meta-Llama-3.1-8B-Instruct-AWQ-INT4" ]; then
  DEFAULT_MODEL="$ROOT/models/Meta-Llama-3.1-8B-Instruct-AWQ-INT4"
fi
MODEL="${LOCAL_LLM_MODEL:-$DEFAULT_MODEL}"
PORT="${LOCAL_LLM_PORT:-8101}"
# Quantization method. awq_marlin is the Ada-optimised AWQ kernel; use
# `bitsandbytes` for NF4 checkpoints (needs `uv pip install bitsandbytes>=0.48.1`
# in the vLLM venv). GGUF is NOT an option — vLLM 0.26 dropped it from
# QUANTIZATION_METHODS; serve those with llama.cpp's llama-server instead, which
# speaks the same OpenAI protocol.
QUANT="${LOCAL_LLM_QUANT:-awq_marlin}"
# 4-bit weights are ~5.7GB; 0.55 of a 24GB card leaves room for the KV cache
# and for BGE-M3, which shares the GPU with the retrieval stack.
GPU_FRACTION="${LOCAL_LLM_GPU_FRACTION:-0.55}"
# The router sends this model short, schema-constrained prompts only; a small
# context keeps KV-cache allocation modest.
MAX_LEN="${LOCAL_LLM_MAX_LEN:-8192}"

# WSL2 needs two opt-ins, both of which cost a silent hang if missed.
#
# 1. Pinned host memory (UVA). vLLM's V1 engine requires it but leaves it off
#    under WSL because driver support varies. Kernel >= 4.19.121 has it and
#    torch's own `pin_memory=True` succeeds here, so opt in — otherwise engine
#    startup dies with "RuntimeError: UVA is not available".
#
# 2. Eager execution. torch.compile's parallel inductor workers deadlock under
#    WSL2: the engine sits at ~5% CPU with 128 threads all blocked in
#    futex_do_wait, logging nothing, forever. vLLM's own source notes that fork
#    is unsafe here ("WSL is detected and NVML is not compatible with fork").
#    Eager mode skips inductor and CUDA-graph capture entirely.
#
#    The cost is decode throughput, not TTFT — CUDA graphs mainly help the
#    per-token decode loop, while TTFT is dominated by prefill. Since this
#    server only handles short control-path prompts, that is the right trade.
#    Set LOCAL_LLM_EAGER=0 to try compiled mode (add
#    TORCHINDUCTOR_COMPILE_THREADS=1 if it hangs).
EAGER_FLAG=()
if grep -qi microsoft /proc/version 2>/dev/null; then
  export VLLM_WSL2_ENABLE_PIN_MEMORY="${VLLM_WSL2_ENABLE_PIN_MEMORY:-1}"
  if [ "${LOCAL_LLM_EAGER:-1}" = "1" ]; then
    EAGER_FLAG=(--enforce-eager)
  fi
  echo "WSL2 detected — pin_memory=$VLLM_WSL2_ENABLE_PIN_MEMORY eager=${LOCAL_LLM_EAGER:-1}"
elif [ "${LOCAL_LLM_EAGER:-0}" = "1" ]; then
  EAGER_FLAG=(--enforce-eager)
fi

if [ ! -x "$VENV/bin/vllm" ]; then
  echo "vLLM venv not found. Create it with:" >&2
  echo "  uv venv --python 3.12 .venv-vllm" >&2
  echo "  VIRTUAL_ENV=\$PWD/.venv-vllm uv pip install vllm" >&2
  exit 1
fi

echo "Serving $MODEL on port $PORT (quant=$QUANT, gpu fraction $GPU_FRACTION)"

# AWQ wants float16 explicitly (vLLM's own guidance); bitsandbytes checkpoints
# carry their own compute dtype, so leave that to `auto`.
DTYPE_FLAG=()
if [ "$QUANT" = "awq_marlin" ] || [ "$QUANT" = "awq" ]; then
  DTYPE_FLAG=(--dtype float16)
fi

exec "$VENV/bin/vllm" serve "$MODEL" \
  --port "$PORT" \
  --quantization "$QUANT" \
  "${DTYPE_FLAG[@]}" \
  --gpu-memory-utilization "$GPU_FRACTION" \
  --max-model-len "$MAX_LEN" \
  --served-model-name local-llama \
  "${EAGER_FLAG[@]}" \
  "$@"
