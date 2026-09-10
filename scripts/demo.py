"""Two-session MCP + actual UltraRAG build/run acceptance demo."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "integrations/ultrarag-memory/src/ultrarag-memory.py"


async def mcp_session(phase):
    from fastmcp import Client

    client = Client({"mcpServers": {"longmem": {
        "command": sys.executable, "args": [str(SERVER)], "env": dict(os.environ),
    }}})
    async with client:
        tool_names = [tool.name for tool in await client.list_tools()]
        def tool_name(short):
            return next(name for name in tool_names if name == short or name.endswith("_" + short))
        async def call(name, args):
            result = await client.call_tool(tool_name(name), args, timeout=300)
            if result.is_error:
                raise RuntimeError(str(result))
            return json.loads(result.content[0].text)
        if phase == "seed":
            records = []
            for memory_id, content in [("alice-editor", "Alice prefers Neovim as her code editor."),
                                       ("bob-garden", "Bob grows tomatoes in his garden.")]:
                payload = {"content": content, "memory_id": memory_id, "importance": 0.8, "source": "user"}
                record = await call("memory_write", payload)
                assert await call("memory_write", payload) == record
                records.append(record)
            result = {"phase": "session-1-write", "tools": tool_names, "records": records}
        else:
            fact = await call("memory_get", {"memory_id": "alice-editor"})
            assert fact["found_memory"]["content"].startswith("Alice prefers Neovim")
            hits = (await call("memory_search", {"query": "What editor does Alice prefer?", "top_k": 5}))["hits"]
            assert any(hit["memory"]["memory_id"] == "alice-editor" for hit in hits)
            result = {"phase": "session-2-after-restart", "fact": fact, "hits": hits}
        print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["test", "model"], default="test")
    parser.add_argument("--worker", choices=["seed", "verify"])
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.worker:
        asyncio.run(mcp_session(args.worker))
        return
    run = ROOT / "artifacts/demo/runs" / (time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env["LONGMEM_CONFIG"] = str(ROOT / "configs" / ("test.yaml" if args.mode == "test" else "local.yaml"))
    env["LONGMEM_STORE_DIR"] = str(run / "memory")
    env["HF_HOME"] = str(ROOT / "cache/huggingface")
    env["HF_HUB_OFFLINE"] = "1"
    env["TOKENIZERS_PARALLELISM"] = "false"

    def execute(label, command):
        print(f"[{label}]", flush=True)
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        (run / f"{label}.stdout.log").write_text(result.stdout)
        (run / f"{label}.stderr.log").write_text(result.stderr)
        if result.returncode:
            print(result.stderr[-5000:], file=sys.stderr)
            raise RuntimeError(f"{label} failed; see {run}")
        return result.stdout

    session1 = json.loads(execute("01-write", [sys.executable, str(__file__), "--worker", "seed"]))
    cli = str(Path(sys.executable).with_name("ultrarag"))
    execute("02-build", [cli, "build", "configs/ultrarag-memory.yaml"])
    execute("03-pipeline", [cli, "run", "configs/ultrarag-memory.yaml", "--log_level", "info"])
    session2 = json.loads(execute("04-verify", [sys.executable, str(__file__), "--worker", "verify"]))

    from longmem.config import load_config, make_store
    config = load_config(env["LONGMEM_CONFIG"])
    config["store_dir"] = env["LONGMEM_STORE_DIR"]
    store = make_store(config)
    generated = [memory.to_dict() for memory in store.list() if memory.source == "generated"]
    assert len(generated) == 1, "UltraRAG must complete generation and persist exactly one response"
    assert "alice-editor" in generated[0]["metadata"]["evidence_ids"]
    assert "neovim" in generated[0]["content"].lower(), "Answer must use the retrieved fact"
    # Test mode is explicitly labeled and never presented as real model verification.
    audit = {"status": "PASS", "mode": args.mode, "session1": session1, "session2": session2,
             "generated": generated, "embedding_version": store.embedder.version,
             "pipeline": "configs/ultrarag-memory.yaml", "run_directory": str(run)}
    (run / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    (ROOT / "artifacts/demo" / f"latest-{args.mode}.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps({"status": "PASS", "mode": args.mode, "audit": str(run / "audit.json"),
                      "answer": generated[0]["content"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
