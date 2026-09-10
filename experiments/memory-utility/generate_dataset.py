"""Freeze paired utility cases from saved phase-two evidence (no model calls)."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('budget_dataset', HERE.parent/'memory-budget/generate_dataset.py')
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def answer_value(record):
    relation = next(r for r in budget.RELATIONS if r[0] == record['relation'])
    for value in relation[1]:
        if record['content'] == f"Currently, {record['subject']} " + relation[2].format(v=value) + '.':
            return value
    raise ValueError(f"Unrecognized ground truth: {record['memory_id']}")


def consolidate(records):
    """Resolve each subject/relation by event order; retain provenance, without gold labels."""
    groups = {}
    for r in records:
        groups.setdefault((r['subject'], r['relation']), []).append(r)
    result = []
    for group in groups.values():
        latest = max(group, key=lambda r: (r['event_order'], r['memory_id']))
        result.append(dict(memory_id='merged-' + latest['memory_id'],
                           canonical_id=latest['canonical_id'],
                           content=latest['content'].removeprefix('Currently, '),
                           source_ids=[r['memory_id'] for r in group]))
    return result


def build(source, config):
    rows, hashes = [], {}
    for seed in config['seeds']:
        case = source / f"{config['scenario']}-{config['size']}-{seed}"
        path = case/'dataset.json'
        hashes[str(path.relative_to(source))] = digest(path)
        data = json.loads(path.read_text())
        memories = {r['memory_id']: r for r in data['records']}
        predictions, retained = {}, {}
        for policy in config['policies']:
            path = case/policy/'predictions.json'
            hashes[str(path.relative_to(source))] = digest(path)
            predictions[policy] = {row['query']['query_id']: row for row in json.loads(path.read_text())}
            path = case/policy/'index.json'
            hashes[str(path.relative_to(source))] = digest(path)
            retained[policy] = {memories[i]['canonical_id'] for i in json.loads(path.read_text())['memory_ids']}
        queries = [q for q in data['queries'] if q['split']=='test' and q['query_id'].endswith(':'+config['query_variant'])]
        for i, q in enumerate(queries):
            current, old = memories[q['target_memory_id']], memories[q['superseded_memory_id']]
            unrelated = next(r for r in data['records'] if r['split']=='distractor' and r['relation']==current['relation'] and 'Currently' in r['content'])
            conflict = [old, current] if (i+seed)%2 else [current, old]
            conditions = dict(no_memory=[], relevant=[current], irrelevant=[unrelated],
                              conflicting=conflict,
                              consolidation_strip_temporal_cue=consolidate(conflict))
            retrieval = {}
            for policy in config['policies']:
                prediction = predictions[policy][q['query_id']]
                assert prediction['query']['target_memory_id'] == q['target_memory_id']
                for k in config['top_k']:
                    name = f'retrieved:{policy}:k{k}'
                    conditions[name] = [memories[mid] for mid in prediction['hits'][:k]]
                    retrieval[name] = dict(recall_at_k=int(q['target_canonical_id'] in [r['canonical_id'] for r in conditions[name]]),
                                           target_fact_retained=q['target_canonical_id'] in retained[policy])
            rows.append(dict(case_id=f"{seed}:{q['query_id']}", seed=seed, family=q['family'],
                             query=q['query'], gold_answer=answer_value(current),
                             target_memory_id=q['target_memory_id'],target_canonical_id=q['target_canonical_id'],
                             conditions=conditions, retrieval=retrieval))
    return rows, hashes


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=HERE.parent/'memory-budget/results/v2-full')
    p.add_argument('--config', type=Path, default=HERE/'configs/default.json')
    p.add_argument('--output', type=Path, default=HERE/'dataset.jsonl')
    a=p.parse_args()
    rows, hashes=build(a.source, json.loads(a.config.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    a.output.with_suffix('.manifest.json').write_text(json.dumps(dict(config=json.loads(a.config.read_text()),
        dataset_sha256=digest(a.output), source_hashes=hashes), indent=2))
    print(f'Saved {len(rows)} cases, {sum(len(r["conditions"]) for r in rows)} conditions')

if __name__=='__main__': main()
