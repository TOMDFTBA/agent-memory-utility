"""Independently recompute all labels from saved scores and verify interventions."""
import argparse
from longmem.experiment_io import read_json, read_jsonl, write_json
from utility_retention.labeling import evaluate

if __name__ == '__main__':
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    manifest = read_json(args.output / 'manifest.json')
    data = read_json(args.output / 'dataset-manifest.json')
    utilities, labels, report = evaluate(data['snapshots'], read_jsonl(args.output / 'responses.jsonl'),
                                        data['seeds'], data['context_ids'],
                                        manifest['parameters']['settings'], manifest['parameters']['backend'])
    for name, value in [('query-utility', utilities), ('future-value-labels', labels), ('reliability-report', report)]:
        if read_json(args.output / f'{name}.json') != value:
            raise ValueError(f'{name} mismatch')
    write_json(args.output / 'verification.json', {'status': 'PASS', 'responses_and_labels_verified': True})
    print('PASS: saved responses and labels agree')
