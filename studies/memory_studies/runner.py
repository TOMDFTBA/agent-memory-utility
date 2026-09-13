"""Source-pinned study runner reusing longmem I/O and manifest utilities."""
import argparse
from pathlib import Path
import subprocess

from longmem.experiment_io import read_json, sha256_file, source_hashes, write_json
from .probes import deepnote

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('study', choices=['deepnote'])
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    pin = read_json(ROOT / 'studies' / args.study / 'upstream.json')
    commit = subprocess.check_output(['git', '-C', str(args.checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != pin['commit'] or any(sha256_file(args.checkout / p) != h for p, h in pin['files'].items()):
        raise ValueError('Upstream source identity mismatch')
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Use a new empty study output directory')
    output = deepnote(args.checkout)
    sources = [ROOT / name for name in (
        'studies/memory_studies/__init__.py', 'studies/memory_studies/probes.py',
        'studies/memory_studies/runner.py', 'studies/run.py',
        'src/longmem/experiment_io.py',
    )]
    write_json(args.output / 'probes.json', output)
    write_json(args.output / 'manifest.json', dict(schema_version='longmem-study-v1', study_id=args.study,
               status='COMPLETE', evidence_level='source_and_no_model_probe', upstream=pin,
               source_hashes=source_hashes(sources, root=ROOT), artifact_sha256=sha256_file(args.output / 'probes.json'),
               model_evidence=False))
    print(f'PASS: {args.study}, {len(output["probes"])} scoped probes; model calls=0')
