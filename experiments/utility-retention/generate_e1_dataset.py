"""Frozen synthetic pressure trajectories; no v0.1 or pilot facts are reused."""
import argparse
import random
from pathlib import Path

from longmem.experiment_io import write_json
from utility_retention.dataset import validate


def build(seed=2026091202):
    rng = random.Random(seed)
    rows = []
    for split in ('train', 'validation', 'test'):
        for family in ('old_but_useful', 'frequent_but_useless', 'redundancy', 'complementarity'):
            uid = f'e1-{split}-{family}'
            entity = f'Vault-{rng.randrange(100000, 999999)}'
            code = str(rng.randrange(100000, 999999))
            mid = lambda i: f'{uid}-m{i}'  # noqa: E731
            contents = [f'The access code for {entity} is {code}.',
                        f'The service desk reference for {entity} is {rng.randrange(10000, 99999)}.',
                        f'The maintenance ticket for {entity} is {rng.randrange(10000, 99999)}.',
                        f'The inventory label for {entity} is {rng.randrange(10000, 99999)}.']
            supports = [[mid(0)]]
            if family == 'redundancy':
                contents[1] = f'To open {entity}, use access code {code}.'
                supports = [[mid(0)], [mid(1)]]
            if family == 'complementarity':
                contents[0] = f'The first three digits of the six-digit access code for {entity} are {code[:3]}.'
                contents[1] = f'The last three digits of the six-digit access code for {entity} are {code[3:]}.'
                supports = [[mid(0), mid(1)]]
            memories = [dict(memory_id=mid(i), canonical_id=f'{uid}-fact{0 if family == "redundancy" and i == 1 else i}',
                             leakage_group=f'{uid}-fact{0 if family == "redundancy" and i == 1 else i}',
                             event_order=i + 1, content=content) for i, content in enumerate(contents)]
            history = [dict(query_id=f'{uid}-h{i}', event_order=6 + i,
                            text=f'What is the service desk reference for {entity}?') for i in range(3)]
            if family != 'frequent_but_useless':
                history = [dict(query_id=f'{uid}-h0', event_order=6,
                                text=f'What is the inventory label for {entity}?')]
            queries = [f'What is the six-digit access code for {entity}?',
                       f'Give the complete access code needed to open {entity}.']
            rows.append(dict(trajectory_id=uid, user_id=uid, split=split, snapshot_id=f'{uid}-s0',
                             event_order=10, scenario=family, memories=memories, history_queries=history,
                             future_queries=[dict(query_id=f'{uid}-q{i}', event_order=11+i,
                                                  text=text, gold_answer=code, supporting_memory_sets=supports)
                                             for i, text in enumerate(queries)]))
    validate(rows)
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Refusing to overwrite dataset')
    write_json(args.output, build())
