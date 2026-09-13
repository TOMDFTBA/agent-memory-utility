"""Explicit release-source compatibility; frozen artifact hashes are never rewritten.

A source mismatch is accepted only for a reviewed release mapping whose complete
Python implementation matches the registered hashes and whose old bytes survive
in the checksum-verified archive. Exact frozen execution is available separately.
"""
import json
from pathlib import Path

from .experiment_io import sha256_file


def source_matches(root, name, digest):
    root = Path(root)
    if sha256_file(root / name) == digest:
        return True
    registry_path = root / 'releases/v0.2.0/source-compatibility.json'
    if not registry_path.exists():
        return False
    registry = json.loads(registry_path.read_text())
    if digest not in registry['legacy_hashes'].get(name, []):
        return False
    for path, expected in registry['release_sources'].items():
        if not (root / path).is_file() or sha256_file(root / path) != expected:
            return False
    index_path = root / 'releases/v0.2.0/frozen-index.json'
    if sha256_file(index_path) != registry['index_sha256']:
        return False
    index = json.loads(index_path.read_text())
    archive = index_path.parent / index['archive']
    if sha256_file(archive) != index['sha256']:
        return False
    return any(value == digest and (path == name or path.endswith('/source-snapshot/' + name))
               for path, value in index['files'].items())
