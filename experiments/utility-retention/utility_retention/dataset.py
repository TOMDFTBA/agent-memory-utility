"""Independent synthetic trajectories and strict time/split validation."""
import math


def pilot_dataset():
    rows = []
    for split in ('train', 'validation', 'test'):
        for index in range(2):
            uid = f'{split}-{index}'
            memories = [dict(memory_id=f'{uid}-m{i}', canonical_id=f'{uid}-f{i}',
                             event_order=i + 1, content=f'{uid} locker {i} code is {731 + index * 10 + i}.')
                        for i in range(3)]
            rows.append(dict(trajectory_id=uid, user_id=uid, split=split, snapshot_id=f'{uid}-s0',
                             event_order=10, memories=memories,
                             history_queries=[dict(query_id=f'{uid}-h0', event_order=5,
                                                   text=f'What is {uid} locker 0 code?')],
                             future_queries=[dict(query_id=f'{uid}-q{i}', event_order=11 + i,
                                                  text=f'What is {uid} locker {i} code?',
                                                  gold_answer=str(731 + index * 10 + i),
                                                  supporting_memory_sets=[[f'{uid}-m{i}']]) for i in range(2)]))
    validate(rows)
    return rows


def validate(rows):
    if not rows:
        raise ValueError('Empty dataset')
    owners, snapshots = {}, set()
    def claim(kind, value, split):
        key = (kind, value)
        if key in owners and owners[key] != split:
            raise ValueError(f'Cross-split leakage: {kind} {value}')
        owners[key] = split
    def order(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('event_order must be finite numeric')
        return value
    for row in rows:
        split = row['split']
        if split not in {'train', 'validation', 'test'}:
            raise ValueError('Invalid split')
        for name in ('trajectory_id', 'user_id'):
            claim(name, row[name], split)
        sid = row['snapshot_id']
        if sid in snapshots:
            raise ValueError('Duplicate snapshot')
        snapshots.add(sid)
        t = order(row['event_order'])
        memories = row['memories']
        ids = {m['memory_id'] for m in memories}
        if not memories or len(ids) != len(memories):
            raise ValueError('Empty or duplicate memories')
        for memory in memories:
            if order(memory['event_order']) >= t:
                raise ValueError('Memory crosses historical boundary')
            for name in ('memory_id', 'canonical_id'):
                claim(name, memory[name], split)
            claim('content', ' '.join(memory['content'].casefold().split()), split)
            # Dataset producers must group semantic rewrites before splitting.
            claim('leakage_group', memory.get('leakage_group', memory['canonical_id']), split)
        queries = row['history_queries'] + row['future_queries']
        if len({q['query_id'] for q in queries}) != len(queries) or not row['future_queries']:
            raise ValueError('Duplicate query or empty future window')
        for q in row['history_queries']:
            if order(q['event_order']) >= t:
                raise ValueError('History crosses decision boundary')
        future = row['future_queries']
        if any(order(q['event_order']) <= t for q in future):
            raise ValueError('Future query precedes decision')
        if [q['event_order'] for q in future] != sorted(q['event_order'] for q in future):
            raise ValueError('Future window must be ordered')
        for q in future:
            if not isinstance(q['gold_answer'], str) or not q['gold_answer']:
                raise ValueError('Missing answer')
            supports = q['supporting_memory_sets']
            if not supports or any(not s or not set(s) <= ids for s in supports):
                raise ValueError('Unknown/empty supporting memory set')
