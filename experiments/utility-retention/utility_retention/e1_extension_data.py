"""E1 extension: independent opaque identities and varied historical signals."""
import argparse
import random
from pathlib import Path

from longmem.experiment_io import read_json, write_json
from utility_retention.dataset import validate


FAMILIES = ('old_but_useful', 'frequent_but_useless', 'redundancy', 'complementarity')


def build(seed=2026091301):
    rng = random.Random(seed)
    rows = []
    counts = {'train': 6, 'validation': 3, 'test': 3}
    used_codes = set()
    def opaque(prefix):
        return f'{prefix}-{rng.getrandbits(48):012x}'
    for split, count in counts.items():
        for family in FAMILIES:
            for number in range(count):
                uid = opaque('t')
                entity = f'{rng.choice(["Vault", "Cabinet", "Locker"])}-X{rng.getrandbits(32):08x}'
                code = str(rng.randrange(100000, 1000000))
                while code in used_codes:
                    code = str(rng.randrange(100000, 1000000))
                used_codes.add(code)
                desk = str(rng.randrange(10000, 100000))
                inventory = str(rng.randrange(10000, 100000))
                template = number % 3
                texts = [f'The access code for {entity} is {code}.',
                         f'The service desk reference for {entity} is {desk}.',
                         f'The maintenance ticket for {entity} is {rng.randrange(10000, 100000)}.',
                         f'The inventory label for {entity} is {inventory}.']
                if template == 1:
                    texts[0] = f'{entity} opens with access code {code}.'
                elif template == 2:
                    texts[0] = f'Use {code} as the access code to open {entity}.'
                if family == 'redundancy':
                    texts[1] = f'To open {entity}, enter the access code {code}.'
                if family == 'complementarity':
                    texts[0] = f'The first three digits of the six-digit access code for {entity} are {code[:3]}.'
                    texts[1] = f'The last three digits of the six-digit access code for {entity} are {code[3:]}.'
                # Neutral provenance varies length without inserting future-task annotations.
                provenance = ['', ' This record was transcribed from the local register.',
                              ' The facilities clerk recorded this entry during a routine inventory review.']
                ids = [opaque('m') for _ in texts]
                facts = [opaque('f') for _ in texts]
                if family == 'redundancy':
                    facts[1] = facts[0]
                events = sorted(rng.sample(range(1, 18), 4))
                roles = list(range(4))
                rng.shuffle(roles)
                if family == 'old_but_useful':
                    roles.remove(0)
                    roles.insert(0, 0)
                memories = [dict(memory_id=ids[role], canonical_id=facts[role], leakage_group=facts[role],
                                 event_order=event, content=texts[role] + rng.choice(provenance))
                            for event, role in zip(events, roles)]
                if family == 'complementarity':
                    supports = [[ids[0], ids[1]]]
                elif family == 'redundancy':
                    supports = [[ids[0]], [ids[1]]]
                else:
                    supports = [[ids[0]]]
                hcount = 3 + number % 3 if family == 'frequent_but_useless' else 1 + number % 3
                field = 'service desk reference' if family == 'frequent_but_useless' else 'inventory label'
                history = [dict(query_id=opaque('h'), event_order=20+i,
                                text=f'What is the {field} for {entity}?') for i in range(hcount)]
                questions = [f'What is the six-digit access code for {entity}?',
                             f'Give the complete access code needed to open {entity}.']
                rows.append(dict(trajectory_id=uid, user_id=opaque('u'), snapshot_id=opaque('s'),
                                 split=split, scenario=family, event_order=30, memories=memories,
                                 history_queries=history,
                                 future_queries=[dict(query_id=opaque('q'), event_order=31+i, text=text,
                                                      gold_answer=code, supporting_memory_sets=supports)
                                                 for i, text in enumerate(questions)],
                                 diagnostic_metadata=dict(entity=entity, prefix_memory_id=ids[0],
                                                          suffix_memory_id=ids[1], frequent_memory_id=ids[1],
                                                          expected_history_count=hcount)))
    validate(rows)
    return rows


def check_disjoint(rows, previous):
    for field, items in [('memory_id', lambda s: s['memories']), ('canonical_id', lambda s: s['memories']),
                         ('query_id', lambda s: s['future_queries'] + s['history_queries'])]:
        old = {x[field] for s in previous for x in items(s)}
        new = {x[field] for s in rows for x in items(s)}
        if old & new:
            raise ValueError(f'Reused {field}')
    old_content = {m['content'] for s in previous for m in s['memories']}
    if old_content & {m['content'] for s in rows for m in s['memories']}:
        raise ValueError('Reused content')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Refusing to overwrite dataset')
    rows = build()
    check_disjoint(rows, read_json(args.previous))
    write_json(args.output, rows)
