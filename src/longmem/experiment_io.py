"""Shared deterministic I/O and publication-safe experiment metadata."""

import hashlib
import json
import os
import platform
import tempfile
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: str | Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_hashes(paths: Iterable[str | Path], *, root: str | Path) -> dict[str, str]:
    """Hash sources using unique, portable project-relative keys."""
    root = Path(root).resolve()
    result = {}
    for item in paths:
        path = Path(item).resolve()
        try:
            key = path.relative_to(root).as_posix()
        except ValueError as error:
            raise ValueError(f"Source must be inside project root: {path}") from error
        if key in result:
            raise ValueError(f"Duplicate source key: {key}")
        result[key] = sha256_file(path)
    return dict(sorted(result.items()))


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"Blank JSONL record at line {number}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSONL record at line {number}") from error
        if not isinstance(value, dict):
            raise ValueError(f"JSONL record at line {number} must be an object")
        rows.append(value)
    return rows


def _serialized(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def write_json(path: str | Path, value: Any) -> None:
    """Atomically write deterministic UTF-8 JSON with a trailing newline."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(_serialized(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_jsonl(path: str | Path, value: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    with path.open("ab") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def public_model_config(config: dict[str, Any]) -> dict[str, Any]:
    """Keep reproducibility settings while removing the workstation path."""
    result = dict(config)
    if result.get("model_path"):
        result["model_path"] = Path(result["model_path"]).name
    return result


def runtime_metadata() -> dict[str, Any]:
    """Portable runtime metadata; deliberately excludes absolute paths."""
    metadata: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    try:
        import numpy

        metadata["numpy"] = numpy.__version__
    except ImportError:
        pass
    try:
        import torch

        metadata.update(
            torch=torch.__version__,
            rocm=torch.version.hip,
            accelerator_available=torch.cuda.is_available(),
            accelerator_name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        )
    except ImportError:
        pass
    return metadata
