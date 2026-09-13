"""Verify study evidence against current files or an explicitly pinned historical commit."""
import hashlib
from pathlib import Path
import re
import subprocess

from longmem.experiment_io import read_json, sha256_file

ROOT = Path(__file__).resolve().parents[1]


def main():
    history = read_json(ROOT / 'studies/source-history.json')['runs']
    for run, commit in history.items():
        manifest = read_json(ROOT / run / 'manifest.json')
        if sha256_file(ROOT / run / 'probes.json') != manifest['artifact_sha256']:
            raise ValueError('Study output mismatch: ' + run)
        if commit is not None and not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError('Historical sources require a full commit ID')
        for name, expected in manifest['source_hashes'].items():
            if commit is None:
                data = (ROOT / name).read_bytes()
            else:
                data = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{commit}:{name}'])
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError('Study source mismatch: ' + run + ': ' + name)
        print('PASS: ' + run)
    validation = read_json(ROOT / 'studies/validation.json')
    for name, expected in validation['files'].items():
        if sha256_file(ROOT / name) != expected:
            raise ValueError('Study validation mismatch: ' + name)
    print('PASS: study validation file hashes')


if __name__ == '__main__':
    main()
