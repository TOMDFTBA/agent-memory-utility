"""FAISS CPU index with explicit string memory-ID mapping and cache validation."""

import hashlib
import json
import os
from pathlib import Path

import faiss
import numpy as np


def atomic_write(path: Path, data: bytes):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class VectorIndex:
    def __init__(self, directory, dimension):
        self.path = directory / "index.faiss"
        self.manifest = directory / "index.json"
        self.dimension = dimension

    def load(self, ids, version):
        try:
            meta = json.loads(self.manifest.read_text())
            data = self.path.read_bytes()
            if (meta["memory_ids"] != ids or meta["embedding_version"] != version
                    or meta["sha256"] != hashlib.sha256(data).hexdigest()):
                return None
            index = faiss.deserialize_index(np.frombuffer(data, dtype=np.uint8))
            if index.d != self.dimension or index.ntotal != len(ids):
                return None
            return index
        except (OSError, ValueError, KeyError, RuntimeError):
            return None

    def build(self, ids, vectors, version):
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.shape != (len(ids), self.dimension) or not np.isfinite(vectors).all():
            raise ValueError("invalid embedding shape or non-finite values")
        vectors = np.ascontiguousarray(vectors.copy())
        faiss.normalize_L2(vectors)
        index = faiss.IndexFlatIP(self.dimension)
        index.add(vectors)
        data = faiss.serialize_index(index).tobytes()
        atomic_write(self.path, data)
        atomic_write(self.manifest, json.dumps({
            "memory_ids": ids, "embedding_version": version,
            "sha256": hashlib.sha256(data).hexdigest(), "dimension": self.dimension,
        }).encode())
        return index
