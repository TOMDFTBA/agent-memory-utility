"""Immutable, JSON-serializable memory records."""

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Memory:
    memory_id: str
    content: str
    timestamp: str
    importance: float
    source: str
    embedding_version: str
    supersedes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        for key in ("memory_id", "content", "source", "embedding_version"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must be a non-empty string")
        if not math.isfinite(self.importance) or not 0 <= self.importance <= 1:
            raise ValueError("importance must be between 0 and 1")
        if datetime.fromisoformat(self.timestamp).tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        if self.supersedes is not None and (not isinstance(self.supersedes, str) or not self.supersedes):
            raise ValueError("supersedes must be a non-empty memory ID")
        if self.supersedes == self.memory_id:
            raise ValueError("a memory cannot supersede itself")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be an object")
        json.dumps(self.metadata, allow_nan=False)

    def to_dict(self):
        return asdict(self)


def utc_now():
    return datetime.now(timezone.utc).isoformat()
