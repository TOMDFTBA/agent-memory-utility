"""Read-only selection of existing E4 evidence for a system-study handoff."""
import argparse
from pathlib import Path

from longmem.experiment_io import read_json, sha256_file, write_json

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Refusing to overwrite a study artifact')
    parent = ROOT / 'experiments/utility-retention/results/e4-diagnostic-model'
    index = read_json(ROOT / 'releases/v0.2.0/frozen-index.json')['files']
    inputs = {}
    for name in ('manifest.json', 'dataset.json', 'cohorts.json', 'subset-scores.json'):
        path = parent / name
        relative = path.relative_to(ROOT).as_posix()
        digest = sha256_file(path)
        if digest != index[relative]:
            raise ValueError('Frozen E4 input changed')
        inputs[relative] = digest
    dataset, cohorts, scores = (read_json(parent / n) for n in ('dataset.json', 'cohorts.json', 'subset-scores.json'))
    cases = []
    for cohort in ('e3_posthoc', 'e4_independent'):
        for scenario in ('redundancy', 'complementarity'):
            snapshot = min((s for s in dataset if cohorts[s['snapshot_id']] == cohort and s['scenario'] == scenario),
                           key=lambda s: s['snapshot_id'])
            rows = [r for r in scores if r['snapshot_id'] == snapshot['snapshot_id']]
            cases.append(dict(cohort=cohort, scenario=scenario, snapshot=snapshot, subset_scores=rows,
                              proposed_system_check='preserve_at_least_one_substitute' if scenario == 'redundancy'
                              else 'preserve_both_support_parts_and_trace_their_sources'))
    write_json(args.output, dict(schema_version='longmem-study-v1', study_id='pilotdeck-memory',
               evidence_level='existing_e4_case_handoff', pilotdeck_evaluated=False,
               selection='first stable snapshot ID per cohort/scenario; no selection by largest gain',
               source_hashes=inputs, extractor_sha256=sha256_file(__file__), cases=cases))
    print('PASS: four existing E4 cases mapped; no new model or PilotDeck result')
