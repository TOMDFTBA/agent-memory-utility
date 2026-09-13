"""E3 held-out data adapter; reuse E1 grammar without changing its frozen generator."""
import json
import random

from .e1_extension_data import build as build_extension, check_disjoint
from .dataset import validate


def build_formal(settings, previous):
    # E1 train branch has six examples/family; this is a new seeded generation,
    # not reuse of any training records. Surface RNG independently replaces facts.
    rows = [s for s in build_extension(settings['structure_seed']) if s['split'] == 'train']
    rng = random.Random(settings['surface_seed'])
    codes = set()
    for s in rows:
        old_entity = s['diagnostic_metadata']['entity']
        old_code = s['future_queries'][0]['gold_answer']
        entity = f'{rng.choice(["Vault", "Cabinet", "Locker"])}-X{rng.getrandbits(32):08x}'
        code = str(rng.randrange(100000, 1000000))
        while code in codes:
            code = str(rng.randrange(100000, 1000000))
        codes.add(code)
        for m in s['memories']:
            m['content'] = m['content'].replace(old_entity, entity)
            if 'first three digits' in m['content']:
                m['content'] = m['content'].replace(f'are {old_code[:3]}.', f'are {code[:3]}.')
            elif 'last three digits' in m['content']:
                m['content'] = m['content'].replace(f'are {old_code[3:]}.', f'are {code[3:]}.')
            else:
                m['content'] = m['content'].replace(old_code, code)
        for q in s['history_queries'] + s['future_queries']:
            q['text'] = q['text'].replace(old_entity, entity)
            if 'gold_answer' in q:
                q['gold_answer'] = code
        s['diagnostic_metadata']['entity'] = entity
        s['split'] = 'test'
    validate(rows)
    if len(rows) != settings['trajectory_count'] or any(
        sum(s['scenario'] == f for s in rows) != settings['per_family'] for f in settings['families']
    ) or any(len(s['memories']) != settings['memories_per_trajectory'] or
             len(s['future_queries']) != settings['queries_per_trajectory'] for s in rows):
        raise ValueError('Formal dataset shape mismatch')
    check_formal_disjoint(rows, previous)
    return rows


def check_formal_disjoint(rows, previous):
    check_disjoint(rows, previous)
    fields = {
        'entity': lambda s: [s['diagnostic_metadata']['entity']],
        'answer': lambda s: [q['gold_answer'] for q in s['future_queries']],
        'query': lambda s: [q['text'] for q in s['future_queries'] + s['history_queries']],
        'content': lambda s: [m['content'] for m in s['memories']],
        'trajectory': lambda s: [s['trajectory_id']],
        'snapshot': lambda s: [s['snapshot_id']],
    }
    for name, extract in fields.items():
        def norm(x):
            return ' '.join(x.casefold().split())
        if {norm(x) for s in rows for x in extract(s)} & {norm(x) for s in previous for x in extract(s)}:
            raise ValueError('Formal overlap: '+name)


def past_view(rows):
    return [dict(snapshot_id=s['snapshot_id'], trajectory_id=s['trajectory_id'], event_order=s['event_order'],
                 memories=[{k: m[k] for k in ('memory_id', 'content', 'event_order')} for m in s['memories']],
                 history_queries=[{k: q[k] for k in ('query_id', 'event_order', 'text')} for q in s['history_queries']])
            for s in rows]


def ensure_past(past, features):
    if any(set(s) != {'snapshot_id', 'trajectory_id', 'event_order', 'memories', 'history_queries'} for s in past):
        raise ValueError('Future/annotation fields in past view')
    for s in past:
        if any(set(m) != {'memory_id', 'content', 'event_order'} for m in s['memories']):
            raise ValueError('Memory annotation in scorer input')
        if any(set(q) != {'query_id', 'event_order', 'text'} or q['event_order'] >= s['event_order']
               for q in s['history_queries']):
            raise ValueError('Invalid history view')
    if any(set(r) != {'snapshot_id', 'trajectory_id', 'memory_id', 'features'} for r in features):
        raise ValueError('Future labels in features')
    # JSON serializability is also checked before plans are frozen.
    json.dumps(features, allow_nan=False)
