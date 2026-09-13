"""CPU-only release audit; restore-results first. No frozen artifact is rewritten."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/utility-retention'))
from release_artifacts import verified_members  # noqa: E402
from longmem.experiment_io import read_json, read_jsonl  # noqa: E402
from longmem.provenance import source_matches  # noqa: E402
from utility_retention.labeling import evaluate  # noqa: E402
from utility_retention.e2 import audit as audit_e2  # noqa: E402
from utility_retention.e3_baselines import audit as audit_baselines  # noqa: E402
from utility_retention.e3_formal import audit as audit_e3  # noqa: E402
from utility_retention.e3_supplement import audit as audit_supplement  # noqa: E402
from utility_retention.e4 import audit as audit_e4  # noqa: E402
from utility_retention.e1_diagnosis import summarize, validate_responses  # noqa: E402


def main():
    files = verified_members()
    for name, data in files.items():
        if '/results/' in name and (ROOT / name).read_bytes() != data:
            raise ValueError('Frozen evidence changed: ' + name)
    results = ROOT / 'experiments/utility-retention/results'
    checks = {}
    for run in ('pilot-test', 'pilot-model', 'e1-model-frozen', 'e1-extension-model'):
        output = results / run
        manifest = read_json(output / 'manifest.json')
        missing_sources = []
        for name, digest in manifest['source_hashes'].items():
            if not source_matches(ROOT, name, digest):
                if not run.startswith('pilot-'):
                    raise ValueError('Unregistered source change: ' + name)
                missing_sources.append(name)
        data = read_json(output / 'dataset-manifest.json')
        derived = evaluate(data['snapshots'], read_jsonl(output / 'responses.jsonl'), data['seeds'],
                           data['context_ids'], manifest['parameters']['settings'], manifest['parameters']['backend'])
        for name, value in zip(('query-utility', 'future-value-labels', 'reliability-report'), derived, strict=True):
            if read_json(output / (name + '.json')) != value:
                raise ValueError('E1 recomputation mismatch: ' + name)
        checks[run] = {'scores': 'PASS', 'unavailable_historical_sources': missing_sources}
    data = read_json(results / 'e1-extension-model/dataset-manifest.json')
    snapshots = [s for s in data['snapshots'] if s['scenario'] == 'complementarity' and s['split'] != 'test']
    rows = read_jsonl(results / 'e1-extension-diagnostic/responses.jsonl')
    validate_responses(snapshots, data['seeds'], rows)
    if summarize(snapshots, rows, read_jsonl(results / 'e1-extension-model/responses.jsonl')) != read_json(
            results / 'e1-extension-diagnostic/summary.json'):
        raise ValueError('E1 diagnosis mismatch')
    checks['e1-extension-diagnostic'] = 'PASS'
    audit_e2(results / 'e2-development-model')
    checks['e2'] = 'PASS'
    audit_baselines(results / 'e3-baselines-development-model', results / 'e2-development-model')
    checks['e3-baselines'] = 'PASS'
    audit_e3(results / 'e3-formal-model')
    checks['e3'] = 'PASS'
    audit_supplement(results / 'e3-supplement-model', results / 'e3-formal-model')
    checks['e3-supplement'] = 'PASS'
    audit_e4(results / 'e4-diagnostic-model')
    checks['e4'] = 'PASS'
    print(json.dumps({'checks': checks, 'scope': 'CPU score/selection/statistics and evidence hashes; no new model inference'}, indent=2))


if __name__ == '__main__':
    main()
