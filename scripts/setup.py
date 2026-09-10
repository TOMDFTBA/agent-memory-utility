"""Install the minimal environment; preserve an already installed PyTorch runtime."""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ultrarag", required=True, type=Path, help="Existing external UltraRAG checkout")
    parser.add_argument("--allow-unsupported-python", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    upstream = args.ultrarag.resolve()
    if not (upstream / "src/ultrarag/client.py").exists():
        parser.error("--ultrarag must point to an UltraRAG source checkout")
    if sys.version_info >= (3, 13) and not args.allow_unsupported_python:
        parser.error("UltraRAG declares Python <3.13; use 3.11/3.12 or explicitly allow this locally tested exception")
    def run(*command):
        subprocess.run(command, check=True)
    environment = root / ".venv"
    if not environment.exists():
        run(sys.executable, "-m", "venv", "--system-site-packages", str(environment))
    python = str(environment / "bin/python")
    run(python, "-m", "pip", "install", "setuptools>=84", "wheel")
    run(python, "-m", "pip", "install", "-e", str(root) + "[models,mcp,test]")
    # Core stdio orchestration needs FastMCP/YAML/rich; avoid the upstream CUDA extras.
    command = [python, "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", str(upstream)]
    if args.allow_unsupported_python:
        command.append("--ignore-requires-python")
    run(*command)
    print("Ready. Run .venv/bin/python scripts/demo.py --mode test")


if __name__ == "__main__":
    main()
