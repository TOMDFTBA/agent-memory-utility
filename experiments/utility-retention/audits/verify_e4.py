"""Independent bit-mask replay of E4 set algebra; does not call E4 derive/optimum."""
import argparse
from collections import defaultdict
from pathlib import Path
from statistics import mean

from longmem.experiment_io import read_json, read_jsonl, sha256_file, write_json
from longmem.scoring import score_answer as score


def verify(output):
    manifest = read_json(output/'manifest.json')
    if manifest['status'] != 'COMPLETE':
        raise ValueError('E4 is not complete')
    snapshots = read_json(output/'dataset.json')
    features = read_json(output/'features.json')
    predictions = read_json(output/'predictions.json')
    responses = read_jsonl(output/'inherited-responses.jsonl')+read_jsonl(output/'responses.jsonl')
    costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in features}
    pred = {(r['snapshot_id'], r['memory_id']): v for r, v in zip(features, predictions, strict=True)}
    scores = defaultdict(list)
    keys = set()
    for r in responses:
        key = (r['snapshot_id'], tuple(r['storage_ids']), r['query_id'], r['seed'])
        if key in keys or r['metrics'] != score(r['generated_answer'], r['gold_answer']):
            raise ValueError('Duplicate response or inconsistent score')
        keys.add(key)
        scores[key[:2]].append(r['metrics']['answer.exact_match'])
    function, loo = {}, {}
    expected_keys = set()
    for s in snapshots:
        sid = s['snapshot_id']
        ids = sorted(m['memory_id'] for m in s['memories'])
        all_sets = [tuple(ids[i] for i in range(len(ids)) if mask & (1 << i)) for mask in range(1 << len(ids))]
        for ids_subset in all_sets:
            for q in s['future_queries']:
                expected_keys.add((sid, ids_subset, q['query_id'], manifest['parameters']['generation_seed']))
            values = scores[sid, ids_subset]
            if len(values) != len(s['future_queries']):
                raise ValueError('Incomplete subset window')
            function[sid, ids_subset] = mean(values)
        for mid in ids:
            loo[sid, mid] = function[sid, tuple(ids)] - function[sid, tuple(m for m in ids if m != mid)]
    if keys != expected_keys:
        raise ValueError('Incomplete exhaustive coverage')
    for r in read_json(output/'labels.json'):
        if r['loo_value'] != loo[r['snapshot_id'], r['memory_id']]:
            raise ValueError('Independent LOO mismatch')
    for r in read_json(output/'subset-scores.json'):
        if r['metrics']['answer.exact_match'] != function[r['snapshot_id'], tuple(r['storage_ids'])]:
            raise ValueError('Independent subset score mismatch')
    for r in read_json(output/'interactions.json'):
        sid, c = r['snapshot_id'], set(r['background_ids'])
        i, j = r['memory_ids']
        def f(members):
            return function[sid, tuple(sorted(members))]
        interaction = f(c | {i, j}) - f(c | {i}) - f(c | {j}) + f(c)
        if interaction != r['metrics']['diagnostic.interaction']:
            raise ValueError('Independent interaction mismatch')
    plans = read_json(output/'plans.json')
    tie_rows = read_json(output/'ties.json')
    optimal = 0
    for p in plans:
        name, sid = p['candidate'], p['snapshot_id']
        feasible = [(ids, value) for (snapshot_id, ids), value in function.items()
                    if snapshot_id == sid and sum(costs[sid, m] for m in ids) <= p['budget_tokens']]
        if name not in ('best_subset', 'predicted_sum_optimal', 'hindsight_loo_sum_optimal'):
            continue
        values = {ids: value if name == 'best_subset' else
                  sum((pred if name == 'predicted_sum_optimal' else loo)[sid, m] for m in ids)
                  for ids, value in feasible}
        maximum = max(values.values())
        tolerance = 0 if name == 'best_subset' else 1e-12
        tied = [ids for ids, value in values.items() if abs(value-maximum) <= tolerance]
        chosen = min(tied, key=lambda ids: (sum(costs[sid, m] for m in ids), len(ids), ids))
        if tuple(p['storage_ids']) != chosen:
            raise ValueError('Independent exact optimum mismatch')
        if name != 'best_subset':
            saved = next(r for r in tie_rows if r['snapshot_id'] == sid and r['candidate'] == name and r['budget_ratio'] == p['budget_ratio'])
            if set(tied) != {tuple(ids) for ids in saved['optimal_subsets']}:
                raise ValueError('Independent complete tie membership mismatch')
        optimal += 1
    ties = read_json(output/'ties.json')
    for r in ties:
        sid = r['snapshot_id']
        value = [function[sid, tuple(ids)] for ids in r['optimal_subsets']]
        if min(value) != r['metrics']['diagnostic.tie_em_min'] or max(value) != r['metrics']['diagnostic.tie_em_max']:
            raise ValueError('Independent tie range mismatch')
    return dict(passed=True, response_count=len(keys), subset_count=len(function), exact_plans_verified=optimal,
                interaction_count=len(read_json(output/'interactions.json')), tie_ranges_verified=len(ties),
                verifier_sha256=sha256_file(Path(__file__)), parent_manifest_sha256=sha256_file(output/'manifest.json'),
                method='Independent bit-mask enumeration and set algebra; shared public I/O and answer scorer only')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--save', type=Path)
    args = parser.parse_args()
    result = verify(args.output)
    if args.save:
        write_json(args.save, result)
    print(result)
