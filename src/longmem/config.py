import os
from pathlib import Path

import yaml

from .embedder import HashEmbedder, MiniCPMEmbedder
from .store import MemoryStore


DEFAULT_CONFIG = "configs/local.yaml"


def config_path(path=None):
    """Resolve one configuration entry point for CLI, MCP, and new experiments.

    An explicit argument wins, followed by LONGMEM_CONFIG, then the repository
    default. Existing callers that pass a path retain their behavior.
    """
    selected = path or os.environ.get("LONGMEM_CONFIG") or DEFAULT_CONFIG
    return Path(selected).expanduser().resolve()


def load_config(path=None):
    path = config_path(path)
    config = yaml.safe_load(path.read_text())
    root = path.parent.parent
    for section, key in ((config, "store_dir"), (config["embedding"], "model_path"),
                         (config.get("generation", {}), "model_path")):
        if key in section:
            value = Path(os.path.expandvars(section[key])).expanduser()
            section[key] = str(value if value.is_absolute() else (root / value).resolve())
    if os.environ.get("LONGMEM_STORE_DIR"):
        config["store_dir"] = os.environ["LONGMEM_STORE_DIR"]
    return config


def make_store(config):
    embedding = dict(config["embedding"])
    backend = embedding.pop("backend")
    if backend == "hash-test":
        embedder = HashEmbedder()
    elif backend == "minicpm":
        embedder = MiniCPMEmbedder(**embedding)
    else:
        raise ValueError(f"Unknown embedding backend: {backend}")
    return MemoryStore(config["store_dir"], embedder)
