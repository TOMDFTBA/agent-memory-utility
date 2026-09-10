"""Long-horizon persistent memory experiments.

Public objects are loaded lazily so lightweight helpers do not require optional
retrieval dependencies such as FAISS at import time.
"""

__all__ = ["Memory", "MemoryStore"]


def __getattr__(name):
    if name == "Memory":
        from .schema import Memory
        return Memory
    if name == "MemoryStore":
        from .store import MemoryStore
        return MemoryStore
    raise AttributeError(name)
