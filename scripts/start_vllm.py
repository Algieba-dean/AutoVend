#!/usr/bin/env python3
"""
vLLM Model Starter Script.

Reads launch configurations from `configs/vllm/` (JSON or YAML format)
and starts the vLLM OpenAI API server using the specified virtual environment (.venv-vllm).
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Project root anchor
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def expand_path(p: str) -> Path:
    """Expand ~ and resolve path relative to project root if not absolute."""
    path_obj = Path(os.path.expanduser(p))
    if not path_obj.is_absolute():
        path_obj = (PROJECT_ROOT / path_obj).resolve()
    return path_obj

def load_config(config_path: Path) -> dict:
    """Load config from JSON or YAML file."""
    if not config_path.exists():
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    content = config_path.read_text(encoding="utf-8")
    if config_path.suffix in [".yaml", ".yml"]:
        try:
            import yaml
            return yaml.safe_load(content)
        except ImportError:
            print("Error: PyYAML package is missing. Please install pyyaml or use a .json config file.", file=sys.stderr)
            sys.exit(1)
    else:
        return json.loads(content)

def main():
    parser = argparse.ArgumentParser(description="Start vLLM Server using project configuration.")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/vllm/qwen3_8b_bnb_4bit.json",
        help="Path to vLLM JSON/YAML config file (default: configs/vllm/qwen3_8b_bnb_4bit.json)",
    )
    parser.add_argument("--host", type=str, help="Override host address")
    parser.add_argument("--port", type=int, help="Override port number")
    parser.add_argument("--gpu-memory-utilization", type=float, help="Override GPU memory utilization ratio")
    parser.add_argument("--max-model-len", type=int, help="Override max model length")
    parser.add_argument("--dry-run", action="store_true", help="Print command without executing")
    
    args = parser.parse_args()

    config_file = expand_path(args.config)
    cfg = load_config(config_file)

    # Resolve paths
    raw_model_path = cfg.get("model_path", "~/models/Qwen/Qwen3-8B-unsloth-bnb-4bit")
    model_path = expand_path(raw_model_path)
    
    venv_name = cfg.get("venv_path", ".venv-vllm")
    venv_dir = expand_path(venv_name)

    # Fallback check if user's venv is named .vev-vllm instead of .venv-vllm
    if not venv_dir.exists():
        alt_venv = expand_path(".vev-vllm")
        if alt_venv.exists():
            venv_dir = alt_venv

    vllm_binary = venv_dir / "bin" / "vllm"
    if not vllm_binary.exists():
        python_binary = venv_dir / "bin" / "python"
        if not python_binary.exists():
            print(f"Error: Virtual environment not found at {venv_dir}", file=sys.stderr)
            print("Please create it with: uv venv --python 3.12 .venv-vllm && VIRTUAL_ENV=$PWD/.venv-vllm uv pip install vllm bitsandbytes", file=sys.stderr)
            sys.exit(1)

    if not model_path.exists():
        print(f"Error: Model directory not found at {model_path}", file=sys.stderr)
        sys.exit(1)

    # Configuration values with CLI overrides
    host = args.host or cfg.get("host", "0.0.0.0")
    port = args.port or cfg.get("port", 8101)
    gpu_util = args.gpu_memory_utilization or cfg.get("gpu_memory_utilization", 0.6)
    max_len = args.max_model_len or cfg.get("max_model_len", 8192)
    served_model_name = cfg.get("served_model_name", "qwen3-8b-bnb-4bit")
    quantization = cfg.get("quantization", "bitsandbytes")
    dtype = cfg.get("dtype", "bfloat16")
    trust_remote_code = cfg.get("trust_remote_code", True)
    enforce_eager = cfg.get("enforce_eager", True)
    extra_args = cfg.get("extra_args", [])

    # WSL2 environment adjustments
    if Path("/proc/version").exists() and "microsoft" in Path("/proc/version").read_text().lower():
        os.environ["VLLM_WSL2_ENABLE_PIN_MEMORY"] = os.environ.get("VLLM_WSL2_ENABLE_PIN_MEMORY", "1")
        print("WSL2 environment detected - VLLM_WSL2_ENABLE_PIN_MEMORY=1 set.")

    # Construct vLLM CLI parameters
    cmd = [
        str(vllm_binary) if vllm_binary.exists() else str(venv_dir / "bin" / "python"),
    ]
    if not vllm_binary.exists():
        cmd.extend(["-m", "vllm.entrypoints.openai.api_server"])
    else:
        cmd.append("serve")

    cmd.extend([
        str(model_path),
        "--host", str(host),
        "--port", str(port),
        "--served-model-name", str(served_model_name),
        "--gpu-memory-utilization", str(gpu_util),
        "--max-model-len", str(max_len),
    ])

    if quantization:
        cmd.extend(["--quantization", str(quantization)])
    if dtype:
        cmd.extend(["--dtype", str(dtype)])
    if trust_remote_code:
        cmd.append("--trust-remote-code")
    if enforce_eager:
        cmd.append("--enforce-eager")
    
    if extra_args:
        cmd.extend([str(a) for a in extra_args])

    print("=" * 60)
    print(f"Starting vLLM Server for model: {cfg.get('model_name', model_path.name)}")
    print(f"Model Path : {model_path}")
    print(f"Venv Path  : {venv_dir}")
    print(f"Host & Port: {host}:{port}")
    print(f"Quantization: {quantization} | dtype: {dtype} | GPU Fraction: {gpu_util}")
    print("=" * 60)
    print("Executing command:", " ".join(cmd))
    print("=" * 60)

    if args.dry_run:
        print("[Dry-run] Command constructed successfully.")
        return

    # Execute vLLM
    os.execv(cmd[0], cmd)

if __name__ == "__main__":
    main()
