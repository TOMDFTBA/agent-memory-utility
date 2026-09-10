"""Explicit test encoder and local MiniCPM encoder; no silent fallback."""

import hashlib
import json
import re
from pathlib import Path

import numpy as np


class HashEmbedder:
    """Deterministic lexical features for engineering tests, NOT semantic evaluation."""

    dimension = 256
    version = "hash-test-v1:256"

    def documents(self, texts):
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row, text in enumerate(texts):
            tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text.lower())
            for token in tokens:
                digest = hashlib.sha256(token.encode()).digest()
                vectors[row, int.from_bytes(digest[:4], "big") % self.dimension] += 1
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1e-12)

    def query(self, text):
        return self.documents([text])


class MiniCPMEmbedder:
    def __init__(self, model_path, device="cpu", max_length=512, batch_size=8,
                 query_prefix="Query: ", revision="local"):
        self.path = Path(model_path).resolve()
        config = json.loads((self.path / "config.json").read_text())
        self.dimension = config["hidden_size"]
        self.device, self.max_length, self.batch_size = device, max_length, batch_size
        self.query_prefix = query_prefix
        # Include local code/config/tokenizer content and weight file identities.
        # Explicit revision should be the upstream commit for published experiments.
        fingerprint = hashlib.sha256()
        for path in sorted(self.path.iterdir()):
            if path.suffix in {".json", ".py", ".model"}:
                fingerprint.update(path.name.encode() + path.read_bytes())
            elif path.suffix == ".safetensors":
                stat = path.stat()
                fingerprint.update(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode())
        settings = [revision, fingerprint.hexdigest(), max_length, query_prefix, "official-mean-v1"]
        self.version = "minicpm:" + hashlib.sha256(json.dumps(settings).encode()).hexdigest()
        self.model = self.tokenizer = None

    def _load(self):
        if self.model is not None:
            return
        import torch
        from transformers import AutoModel, AutoTokenizer

        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("GPU unavailable; allow GPU access or explicitly select device=cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(self.path, trust_remote_code=True, local_files_only=True)
        self.model = AutoModel.from_pretrained(
            self.path, trust_remote_code=True, local_files_only=True,
            torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32,
        ).to(self.device).eval()

    def documents(self, texts):
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        self._load()
        import torch
        import torch.nn.functional as F

        result = []
        with torch.inference_mode():
            for start in range(0, len(texts), self.batch_size):
                batch = self.tokenizer(texts[start:start + self.batch_size], padding=True,
                                       truncation=True, max_length=self.max_length,
                                       return_tensors="pt").to(self.device)
                hidden = self.model(**batch).last_hidden_state.float()
                mask = batch["attention_mask"].unsqueeze(-1).float()
                # The official model already applies positional weighting internally.
                pooled = (hidden * mask).sum(1) / mask.sum(1).clamp_min(1)
                result.append(F.normalize(pooled, p=2, dim=1).cpu().numpy())
        return np.concatenate(result).astype(np.float32)

    def query(self, text):
        return self.documents([self.query_prefix + text])
