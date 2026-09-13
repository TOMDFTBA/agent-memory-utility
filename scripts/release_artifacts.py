"""Verify and restore the checksum-pinned v0.2 evidence archive.

Restore never overwrites differing files. Use --output for an isolated frozen
checkout, or restore-results to materialize ignored evidence in this checkout.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'releases/v0.2.0'


def verified_members():
    index = json.loads((RELEASE / 'frozen-index.json').read_text())
    raw = (RELEASE / index['archive']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != index['sha256']:
        raise ValueError('Evidence archive checksum mismatch')
    result = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        for member in archive.getmembers():
            path = PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or '..' in path.parts or member.name in result:
                raise ValueError('Unsafe or duplicate archive member')
            data = archive.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != index['files'].get(member.name):
                raise ValueError('Archive member checksum mismatch: ' + member.name)
            result[member.name] = data
    if set(result) != set(index['files']):
        raise ValueError('Archive member coverage mismatch')
    return result


def restore(output, results_only=False, source_run=None):
    files = verified_members()
    if results_only:
        files = {k: v for k, v in files.items() if k.startswith('experiments/utility-retention/results/')}
    if source_run:
        manifest_key = f'experiments/utility-retention/results/{source_run}/manifest.json'
        manifest = json.loads(files[manifest_key])
        all_files = verified_members()
        for name, digest in manifest['source_hashes'].items():
            candidates = [data for path, data in all_files.items()
                          if (path == name or path.endswith('/source-snapshot/' + name))
                          and hashlib.sha256(data).hexdigest() == digest]
            if not candidates:
                raise ValueError('Missing frozen source: ' + name)
            files[name] = candidates[0]
    # Preflight the entire copy, including parent symlinks, before writing.
    output = Path(output).resolve()
    for name, data in files.items():
        target = output / name
        if not target.resolve().is_relative_to(output):
            raise ValueError('Destination escapes output root')
        if target.exists() and (not target.is_file() or target.read_bytes() != data):
            raise ValueError('Refusing to overwrite differing file: ' + name)
    for name, data in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'restore', 'restore-results'])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--source-run', help='Restore the exact source variant for this archived run')
    args = parser.parse_args()
    if args.action == 'verify':
        print(f'PASS: {len(verified_members())} checksum-verified evidence files')
    else:
        if args.action == 'restore' and args.output is None:
            parser.error('restore requires a new --output directory')
        if args.action == 'restore-results' and args.source_run:
            parser.error('--source-run requires an isolated restore')
        print(f'Restored {restore(args.output or ROOT, args.action == "restore-results", args.source_run)} files')


if __name__ == '__main__':
    main()
