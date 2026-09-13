"""Context interventions are separate from storage-set candidates and oracle rankings."""
from .e2 import verify_responses
from .e2_metrics import response_key
from .engine import serialize


def context_plans(snapshots, responses, seed):
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    plans = []
    for s in snapshots:
        if s['scenario'] != 'complementarity':
            continue
        ids = sorted(m['memory_id'] for m in s['memories'])
        for q in s['future_queries']:
            full = index[response_key(s['snapshot_id'], ids, q['query_id'], seed)]
            support = sorted(q['supporting_memory_sets'][0])
            conditions = [('context_support_forward', None, support),
                          ('context_support_reversed', None, list(reversed(support)))]
            conditions += [('context_deletion', mid,
                            [m['memory_id'] for m in full['context'] if m['memory_id'] != mid]) for mid in support]
            for condition, deleted, context_ids in conditions:
                plans.append(dict(snapshot_id=s['snapshot_id'], query_id=q['query_id'], seed=seed,
                                  condition=condition, deleted_memory_id=deleted, context_ids=context_ids,
                                  source_response_key=[s['snapshot_id'], ids, q['query_id'], seed]))
    return plans


def control_key(row):
    return row['snapshot_id'], row['query_id'], row['condition'], row['deleted_memory_id'], row['seed']


def verify_controls(plans, rows, snapshots, settings, complete=True):
    required = {control_key(p): p for p in plans}
    seen = [control_key(r) for r in rows]
    if len(seen) != len(set(seen)) or not set(seen) <= set(required) or (complete and set(seen) != set(required)):
        raise ValueError('Missing, duplicate or unexpected context control')
    for r in rows:
        p = required[control_key(r)]
        if any(r[k] != v for k, v in p.items()) or r['context_ids'] != [m['memory_id'] for m in r['context']]:
            raise ValueError('Context intervention mismatch')
        # Adapter checks shared answer/prompt/score/isolation rules, without pretending
        # intervention order was produced by retrieval. Raw controls have no ranking.
        adapted = dict(r, storage_ids=sorted(r['context_ids']),
                       ranking=[dict(memory_id=mid, score=float(len(r['context_ids'])-i))
                                for i, mid in enumerate(r['context_ids'])])
        snapshot = next(s for s in snapshots if s['snapshot_id'] == r['snapshot_id'])
        snapshot = dict(snapshot, future_queries=[q for q in snapshot['future_queries'] if q['query_id'] == r['query_id']])
        verify_responses([adapted], [snapshot], [adapted], settings)


def verify_tokens(engine, rows):
    for r in rows:
        if (r['input_tokens'] != engine.tokens(r['prompt']) or
            r['output_tokens'] != engine.tokens(r['generated_answer'])):
            raise ValueError('Actual token count mismatch')
        if 'context' in r and r['memory_tokens'] != engine.tokens('\n'.join(serialize(m) for m in r['context'])):
            raise ValueError('Actual context token count mismatch')
