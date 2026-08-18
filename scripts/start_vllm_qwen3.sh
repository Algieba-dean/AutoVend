#!/usr/bin/env bash
# Shell script to start Qwen3-8B-unsloth-bnb-4bit with vLLM using project configuration.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$ROOT/configs/vllm/qwen3_8b_bnb_4bit.json"
EXTRA_ARGS=("$@")

if [ $# -gt 0 ] && [ "${1:0:1}" != "-" ] && [ -f "$1" ]; then
  CONFIG_FILE="$1"
  EXTRA_ARGS=("${@:2}")
fi

# Check for virtual environment (.venv-vllm or .vev-vllm)
VENV="$ROOT/.venv-vllm"
if [ ! -d "$VENV" ] && [ -d "$ROOT/.vev-vllm" ]; then
  VENV="$ROOT/.vev-vllm"
fi

if [ ! -x "$VENV/bin/python" ]; then
  echo "Error: Virtual environment not found at $VENV" >&2
  exit 1
fi

echo "Launching vLLM using config: $CONFIG_FILE"
exec "$VENV/bin/python" "$ROOT/scripts/start_vllm.py" --config "$CONFIG_FILE" "${EXTRA_ARGS[@]}"

