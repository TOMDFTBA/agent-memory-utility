"""Recomputable paired labels and conservative development reliability gates."""
from collections import Counter, defaultdict
from statistics import mean, pstdev

from .engine import score


def key(row):
    return (row['snapshot_id'], row['query_id'], row['seed'], row['condition'], row['deleted_memory_id'])


def expected_keys(dataset, seeds, context_ids):
    return {(s['snapshot_id'], q['query_id'], seed, condition, mid)
            for s in dataset for q in s['future_queries'] for seed in seeds
            for condition, mid in [('full', None), ('no_memory', None)]
            + [('storage_deletion', m['memory_id']) for m in s['memories']]
            + [('context_deletion', mid) for mid in context_ids[s['snapshot_id']]]}


def evaluate(dataset, responses, seeds, context_ids, settings, backend):
    index = {key(r): r for r in responses}
    if len(index) != len(responses) or set(index) != expected_keys(dataset, seeds, context_ids):
        raise ValueError('Incomplete, duplicate, or unexpected responses')
    for r in responses:
        if r['status'] != 'OK' or r['metrics'] != score(r['generated_answer'], r['gold_answer']):
            raise ValueError('Failed response or score mismatch')
    utilities, labels, gaps = [], [], []
    for snapshot in dataset:
        sid = snapshot['snapshot_id']
        source = {m['memory_id']: m for m in snapshot['memories']}
        def get(q, seed, condition, mid=None):
            r = index[(sid, q['query_id'], seed, condition, mid)]
            if r['gold_answer'] != q['gold_answer'] or r['query'] != q['text']:
                raise ValueError('Query/answer mismatch')
            ids = [m['memory_id'] for m in r['context']]
            if len(ids) != len(set(ids)) or any(m != source.get(m['memory_id']) for m in r['context']):
                raise ValueError('Context does not match snapshot')
            expected = set(source) - ({mid} if condition == 'storage_deletion' else set())
            if condition == 'no_memory':
                expected = set()
            if set(r['storage_ids']) != expected or not set(ids) <= expected:
                raise ValueError('Storage intervention mismatch')
            if condition.endswith('deletion') and mid in ids:
                raise ValueError('Deleted memory still in context')
            if condition == 'context_deletion':
                full = index[(sid, q['query_id'], seed, 'full', None)]
                if r['context'] != [m for m in full['context'] if m['memory_id'] != mid]:
                    raise ValueError('Context deletion changed order or filled gap')
            if r['memory_tokens'] > settings['read_budget']:
                raise ValueError('Read budget exceeded')
            return r
        for seed in seeds:
            for q in snapshot['future_queries']:
                full = get(q, seed, 'full')
                empty = get(q, seed, 'no_memory')
                gaps.append(dict(trajectory_id=snapshot['trajectory_id'], split=snapshot['split'],
                                 value=full['metrics']['answer.exact_match'] - empty['metrics']['answer.exact_match']))
                for condition, mids in [('storage_deletion', source), ('context_deletion', context_ids[sid])]:
                    for mid in mids:
                        deleted = get(q, seed, condition, mid)
                        full_ids = [m['memory_id'] for m in full['context']]
                        after_ids = [m['memory_id'] for m in deleted['context']]
                        utilities.append(dict(snapshot_id=sid, trajectory_id=snapshot['trajectory_id'],
                                              split=snapshot['split'], query_id=q['query_id'], seed=seed,
                                              memory_id=mid, condition=condition,
                                              value=full['metrics']['answer.exact_match'] - deleted['metrics']['answer.exact_match'],
                                              retrieved=mid in full_ids,
                                              replacement_ids=[i for i in after_ids if i not in full_ids],
                                              hit_but_wrong=any(set(s) <= set(full_ids) for s in q['supporting_memory_sets'])
                                              and full['metrics']['answer.exact_match'] == 0))
    groups = defaultdict(list)
    for u in utilities:
        groups[(u['snapshot_id'], u['memory_id'], u['condition'])].append(u)
    for (sid, mid, condition), rows in groups.items():
        values = [mean(r['value'] for r in rows if r['seed'] == seed) for seed in seeds]
        effect, noise = mean(values), pstdev(values)
        signs = [1 if v > settings['minimum_effect'] else -1 if v < -settings['minimum_effect'] else 0 for v in values]
        stability = max(Counter(signs).values()) / len(signs)
        uncertain = noise > settings['max_label_std'] or stability < settings['minimum_sign_stability']
        labels.append(dict(snapshot_id=sid, trajectory_id=rows[0]['trajectory_id'], split=rows[0]['split'],
                           memory_id=mid, condition=condition, value=effect, repeat_values=values,
                           standard_deviation=noise, sign_stability=stability, uncertain=uncertain,
                           label='uncertain' if uncertain else 'positive' if effect > settings['minimum_effect']
                           else 'negative' if effect < -settings['minimum_effect'] else 'zero'))
    dev = [r for r in labels if r['split'] != 'test' and r['condition'] == 'storage_deletion']
    trajectory_gaps = defaultdict(list)
    for gap in gaps:
        if gap['split'] != 'test':
            trajectory_gaps[gap['trajectory_id']].append(gap['value'])
    dependency = mean(mean(v) for v in trajectory_gaps.values()) if trajectory_gaps else None
    reliable = bool(dev) and all(not r['uncertain'] for r in dev) and len(seeds) >= 2
    report = dict(backend=backend, model_claims_allowed=backend == 'model',
                  development_memory_dependency=dependency, development_labels_reliable=reliable,
                  ready_for_stage2=backend == 'model' and reliable and dependency is not None
                  and dependency >= settings['minimum_memory_dependency'],
                  distribution=dict(Counter(r['label'] for r in labels if r['condition'] == 'storage_deletion')),
                  nonzero_fraction=mean(r['value'] != 0 for r in labels if r['condition'] == 'storage_deletion'),
                  zero_cases=[u for u in utilities if u['value'] == 0],
                  note='Development gates only; test windows are hindsight diagnostics. Test backend verifies plumbing only.')
    return utilities, labels, report
