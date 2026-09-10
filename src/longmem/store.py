"""JSONL is authoritative; SQLite and FAISS are recoverable projections.

All operations serialize on a process/thread lock. Phase 1 favors correctness
over throughput: replay scans the log, and changed indexes are rebuilt lazily.
"""

import fcntl
import hashlib
import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from .retrieval import VectorIndex, atomic_write
from .schema import Memory, utc_now

_locks_guard = threading.Lock()
_locks = {}


class MemoryStore:
    def __init__(self, directory, embedder):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.log = self.directory / "events.jsonl"
        self.db_path = self.directory / "memory.sqlite3"
        self.embedder = embedder
        self.index = VectorIndex(self.directory, embedder.dimension)
        with _locks_guard:
            self._thread_lock = _locks.setdefault(str(self.directory), threading.RLock())
        with self._session():
            pass

    @contextmanager
    def _session(self):
        with self._thread_lock, (self.directory / ".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            db = sqlite3.connect(self.db_path)
            try:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("CREATE TABLE IF NOT EXISTS memories (memory_id TEXT PRIMARY KEY, record TEXT NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS vectors (memory_id TEXT, version TEXT, vector BLOB, PRIMARY KEY(memory_id, version))")
                self._replay(db)
                yield db
            finally:
                db.close()
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _replay(self, db):
        if not self.log.exists():
            if db.execute("SELECT count(*) FROM memories").fetchone()[0]:
                raise RuntimeError("Authoritative events.jsonl is missing; restore it from backup")
            atomic_write(self.log, b"")
        raw = self.log.read_bytes()
        if raw and not raw.endswith(b"\n"):
            boundary = raw.rfind(b"\n") + 1
            # Preserve a torn append as evidence before discarding only that tail.
            atomic_write(self.directory / ("torn-" + hashlib.sha256(raw[boundary:]).hexdigest()[:16] + ".bin"), raw[boundary:])
            with self.log.open("r+b") as stream:
                stream.truncate(boundary)
                stream.flush()
                os.fsync(stream.fileno())
            raw = raw[:boundary]
        records = {}
        replaced = set()
        for number, line in enumerate(raw.splitlines(), 1):
            try:
                event = json.loads(line)
                if event["schema_version"] != 1 or event["type"] != "memory_written":
                    raise ValueError("unsupported event")
                memory = Memory(**event["memory"])
                if memory.memory_id in records:
                    raise ValueError("duplicate ID in event log")
                if memory.supersedes:
                    if memory.supersedes not in records or memory.supersedes in replaced:
                        raise ValueError("invalid supersession chain")
                    replaced.add(memory.supersedes)
                records[memory.memory_id] = json.dumps(memory.to_dict(), sort_keys=True, ensure_ascii=False)
            except (ValueError, TypeError, KeyError) as error:
                raise RuntimeError(f"Corrupt event log at line {number}; no silent recovery") from error
        existing = dict(db.execute("SELECT memory_id, record FROM memories"))
        if existing != records:
            with db:
                db.execute("DELETE FROM memories")
                db.executemany("INSERT INTO memories VALUES (?, ?)", records.items())
                # Discard vectors if content changed outside the supported append path.
                changed = [key for key in existing if existing[key] != records.get(key)]
                db.executemany("DELETE FROM vectors WHERE memory_id=?", [(key,) for key in changed])

    @staticmethod
    def _records(db, include_superseded=False):
        records = [Memory(**json.loads(row[0])) for row in db.execute("SELECT record FROM memories ORDER BY rowid")]
        replaced = {record.supersedes for record in records if record.supersedes}
        return records if include_superseded else [record for record in records if record.memory_id not in replaced]

    def write(self, content, *, memory_id=None, importance=0.5, source="user",
              supersedes=None, metadata=None, timestamp=None):
        metadata = {} if metadata is None else metadata
        payload = dict(content=content, importance=importance, source=source,
                       supersedes=supersedes, metadata=metadata)
        # Exact logical retries are idempotent. Timestamp/model-version are not identity.
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False)
        memory_id = memory_id or "mem_" + hashlib.sha256(canonical.encode()).hexdigest()[:32]
        with self._session() as db:
            old = db.execute("SELECT record FROM memories WHERE memory_id=?", (memory_id,)).fetchone()
            if old:
                record = Memory(**json.loads(old[0]))
                if any(getattr(record, key) != value for key, value in payload.items()) or (timestamp and record.timestamp != timestamp):
                    raise ValueError("memory_id already exists with different content or attributes")
                return record
            if supersedes and supersedes not in {m.memory_id for m in self._records(db)}:
                raise ValueError("supersedes must refer to an existing active memory")
            memory = Memory(memory_id=memory_id, timestamp=timestamp or utc_now(),
                            embedding_version=self.embedder.version, **payload)
            event = {"schema_version": 1, "type": "memory_written", "memory": memory.to_dict()}
            data = (json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n").encode()
            with self.log.open("ab") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            with db:
                db.execute("INSERT INTO memories VALUES (?, ?)", (memory.memory_id, json.dumps(memory.to_dict(), sort_keys=True, ensure_ascii=False)))
            return memory

    def get(self, memory_id):
        with self._session() as db:
            row = db.execute("SELECT record FROM memories WHERE memory_id=?", (memory_id,)).fetchone()
            return Memory(**json.loads(row[0])) if row else None

    def list(self, include_superseded=False):
        with self._session() as db:
            return self._records(db, include_superseded)

    def _build(self, db, records):
        vectors = []
        missing = []
        for offset, memory in enumerate(records):
            row = db.execute("SELECT vector FROM vectors WHERE memory_id=? AND version=?",
                             (memory.memory_id, self.embedder.version)).fetchone()
            vector = np.frombuffer(row[0], dtype=np.float32).copy() if row else None
            if vector is not None and (vector.shape != (self.embedder.dimension,) or not np.isfinite(vector).all()):
                vector = None
            vectors.append(vector)
            if vector is None:
                missing.append(offset)
        if missing:
            encoded = np.asarray(self.embedder.documents([records[i].content for i in missing]), dtype=np.float32)
            if encoded.shape != (len(missing), self.embedder.dimension) or not np.isfinite(encoded).all():
                raise ValueError("invalid embeddings")
            with db:
                for i, vector in zip(missing, encoded):
                    vectors[i] = vector
                    db.execute("INSERT OR REPLACE INTO vectors VALUES (?, ?, ?)",
                               (records[i].memory_id, self.embedder.version, vector.tobytes()))
        matrix = np.stack(vectors) if vectors else np.empty((0, self.embedder.dimension), dtype=np.float32)
        return self.index.build([m.memory_id for m in records], matrix, self.embedder.version)

    def rebuild_index(self):
        with self._session() as db:
            records = self._records(db)
            self._build(db, records)
            return {"count": len(records), "embedding_version": self.embedder.version}

    def search(self, query, top_k=5):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be non-empty")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 100:
            raise ValueError("top_k must be an integer between 1 and 100")
        with self._session() as db:
            records = self._records(db)
            if not records:
                return []
            index = self.index.load([m.memory_id for m in records], self.embedder.version)
            if index is None:
                index = self._build(db, records)
            query_vector = np.asarray(self.embedder.query(query), dtype=np.float32)
            if query_vector.shape != (1, self.embedder.dimension) or not np.isfinite(query_vector).all():
                raise ValueError("invalid query embedding")
            norm = np.linalg.norm(query_vector)
            query_vector = np.ascontiguousarray(query_vector / max(norm, 1e-12))
            scores, positions = index.search(query_vector, min(top_k, len(records)))
            return [{"memory": records[int(position)].to_dict(), "score": float(score)}
                    for score, position in zip(scores[0], positions[0]) if position >= 0]
