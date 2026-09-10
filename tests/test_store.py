import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from longmem.embedder import HashEmbedder
from longmem.store import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(tmp_path, HashEmbedder())


def test_write_get_and_exact_retry(store):
    memory = store.write("Alice prefers Neovim", metadata={"session": 1})
    assert store.get(memory.memory_id) == memory
    assert store.write("Alice prefers Neovim", metadata={"session": 1}) == memory
    assert len(store.log.read_text().splitlines()) == 1


def test_id_conflict_is_rejected_without_extra_event(store):
    store.write("old", memory_id="fixed")
    with pytest.raises(ValueError, match="already exists"):
        store.write("different", memory_id="fixed")
    assert len(store.list()) == 1


def test_restart_in_separate_process(store):
    memory = store.write("Alice prefers Neovim")
    code = """
import json, sys
from longmem.store import MemoryStore
from longmem.embedder import HashEmbedder
s = MemoryStore(sys.argv[1], HashEmbedder())
print(json.dumps(s.search('Alice Neovim', 1)))
"""
    result = subprocess.run([sys.executable, "-c", code, str(store.directory)],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)[0]["memory"]["memory_id"] == memory.memory_id


def test_search_and_index_loss(store):
    expected = store.write("Alice prefers Neovim")
    store.write("Bob grows tomatoes")
    assert store.search("Alice Neovim", 1)[0]["memory"]["memory_id"] == expected.memory_id
    store.index.path.unlink()
    assert store.search("Alice Neovim", 1)[0]["memory"]["memory_id"] == expected.memory_id
    assert store.index.path.exists()


def test_corrupt_index_and_manifest_are_rebuilt(store):
    memory = store.write("Alice Neovim")
    store.rebuild_index()
    store.index.path.write_bytes(b"broken index")
    assert store.search("Alice")[0]["memory"]["memory_id"] == memory.memory_id
    store.index.manifest.write_text("{")
    assert store.rebuild_index()["count"] == 1


def test_database_loss_replays_log(store):
    memory = store.write("Alice prefers Neovim")
    store.rebuild_index()
    store.db_path.unlink()
    recovered = MemoryStore(store.directory, HashEmbedder())
    assert recovered.get(memory.memory_id) == memory
    assert recovered.search("Neovim")[0]["memory"]["memory_id"] == memory.memory_id


def test_event_durable_before_sqlite_commit(store):
    # Simulate the durable log append of a writer that crashed before updating SQLite.
    event = {"schema_version": 1, "type": "memory_written", "memory": {
        "memory_id": "crash", "content": "survives crash", "timestamp": "2026-09-05T00:00:00+00:00",
        "importance": 0.5, "source": "user", "embedding_version": store.embedder.version,
        "supersedes": None, "metadata": {},
    }}
    with store.log.open("ab") as stream:
        stream.write((json.dumps(event) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    assert store.get("crash").content == "survives crash"


def test_torn_tail_preserved_and_subsequent_write_works(store):
    first = store.write("first")
    with store.log.open("ab") as stream:
        stream.write(b'{"schema_version":')
    second = store.write("second")
    assert [m.memory_id for m in store.list()] == [first.memory_id, second.memory_id]
    assert list(store.directory.glob("torn-*.bin"))


def test_complete_corrupt_event_is_not_silently_dropped(store):
    store.write("first")
    with store.log.open("ab") as stream:
        stream.write(b"invalid-json\n")
    with pytest.raises(RuntimeError, match="line 2"):
        store.list()


def test_missing_authoritative_log_fails_closed(store):
    store.write("keep me")
    store.log.unlink()
    with pytest.raises(RuntimeError, match="missing"):
        store.list()


def test_supersession_keeps_history_and_filters_search(store):
    old = store.write("Alice prefers Vim", memory_id="old")
    new = store.write("Alice prefers Neovim", memory_id="new", supersedes="old")
    assert store.get("old") == old
    assert store.list() == [new]
    assert len(store.list(include_superseded=True)) == 2
    assert [hit["memory"]["memory_id"] for hit in store.search("Alice Vim")] == ["new"]
    assert store.write("Alice prefers Neovim", memory_id="new", supersedes="old") == new
    with pytest.raises(ValueError, match="active"):
        store.write("Alice prefers Emacs", supersedes="old")
    with pytest.raises(ValueError, match="active"):
        store.write("another", supersedes="nonexistent")


def test_embedding_version_change_rebuilds_without_rewriting_history(store):
    memory = store.write("Alice Neovim")
    store.rebuild_index()
    class NewEmbedder(HashEmbedder):
        version = "hash-test-v2"
    reopened = MemoryStore(store.directory, NewEmbedder())
    assert reopened.search("Alice")[0]["memory"]["embedding_version"] == memory.embedding_version
    assert json.loads(store.index.manifest.read_text())["embedding_version"] == "hash-test-v2"


def test_concurrent_writers_are_serialized(store):
    def write(i):
        return MemoryStore(store.directory, HashEmbedder()).write(f"fact {i % 5}")
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(40)))
    assert len(store.list()) == 5
    assert len(store.log.read_text().splitlines()) == 5


def test_process_writers_share_lock(store):
    code = """
import sys
from longmem import MemoryStore
from longmem.embedder import HashEmbedder
s = MemoryStore(sys.argv[1], HashEmbedder())
for i in range(8):
    s.write(f'process fact {i}')
"""
    workers = [subprocess.Popen([sys.executable, "-c", code, str(store.directory)]) for _ in range(3)]
    for worker in workers:
        assert worker.wait(timeout=20) == 0
    assert len(store.list()) == 8
    assert len(store.log.read_text().splitlines()) == 8


def test_restore_from_jsonl_alone_preserves_supersession(store):
    store.write("Alice Vim", memory_id="old")
    store.write("Alice Neovim", memory_id="new", supersedes="old")
    store.rebuild_index()
    for path in (store.db_path, store.index.path, store.index.manifest):
        path.unlink()
    reopened = MemoryStore(store.directory, HashEmbedder())
    assert reopened.get("old").content == "Alice Vim"
    assert [hit["memory"]["memory_id"] for hit in reopened.search("Alice")] == ["new"]


@pytest.mark.parametrize("kwargs", [{"importance": -1}, {"importance": float("nan")},
                                     {"timestamp": "2026-09-05"}, {"metadata": []}])
def test_invalid_records_are_rejected(store, kwargs):
    with pytest.raises((ValueError, TypeError)):
        store.write("fact", **kwargs)
    assert store.list() == []


def test_empty_store_and_query_validation(store):
    assert store.search("anything") == []
    assert store.get("unknown") is None
    assert store.rebuild_index()["count"] == 0
    with pytest.raises(ValueError):
        store.search("")
    with pytest.raises(ValueError):
        store.search("q", 0)
