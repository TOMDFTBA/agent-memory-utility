"""Frozen development-only evidence controls; no prompt tuning or test diagnosis."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
import time

from longmem.config import load_config
from longmem.experiment_io import (append_jsonl, read_json, read_jsonl, runtime_metadata,
                                   sha256_file, source_hashes, write_json)
from utility_retention.engine import Engine, score
from utility_retention.runner import HERE, ROOT, model_identity


CONDITIONS = ('support_only', 'support_reversed', 'prefix_only', 'suffix_only')


def contexts(snapshot):
    ids = snapshot['diagnostic_metadata']
    by_id = {m['memory_id']: m for m in snapshot['memories']}
    pair_ids = {ids['prefix_memory_id'], ids['suffix_memory_id']}
    pair = [m for m in snapshot['memories'] if m['memory_id'] in pair_ids]
    if len(pair) != 2:
        raise ValueError('Complementarity requires two distinct support records')
    return dict(support_only=pair, support_reversed=list(reversed(pair)),
                prefix_only=[by_id[ids['prefix_memory_id']]], suffix_only=[by_id[ids['suffix_memory_id']]])


def record_key(row):
    return row['snapshot_id'], row['query_id'], row['seed'], row['condition']


def behavior(answer, gold):
    if score(answer, gold)['answer.exact_match']:
        return 'correct'
    answer = answer.strip()
    if answer in {gold[:3], gold[3:]}:
        return 'half_only'
    if gold in answer:
        return 'full_answer_with_extra_text'
    if answer.casefold() == 'unknown':
        return 'unknown'
    return 'other_error'


def validate_responses(snapshots, seeds, rows):
    expected = {(s['snapshot_id'], q['query_id'], seed, condition)
                for s in snapshots for q in s['future_queries'] for seed in seeds for condition in CONDITIONS}
    if len(rows) != len(expected) or {record_key(r) for r in rows} != expected:
        raise ValueError('Incomplete or duplicate diagnostic records')
    source = {s['snapshot_id']: s for s in snapshots}
    for row in rows:
        s = source[row['snapshot_id']]
        q = next(q for q in s['future_queries'] if q['query_id'] == row['query_id'])
        if row['context'] != contexts(s)[row['condition']] or row['split'] == 'test':
            raise ValueError('Diagnostic context/split mismatch')
        if row['gold_answer'] != q['gold_answer'] or row['query'] != q['text']:
            raise ValueError('Diagnostic query mismatch')
        if row['metrics'] != score(row['generated_answer'], q['gold_answer']) or row['status'] != 'OK':
            raise ValueError('Diagnostic scoring mismatch')
        if row['memory_tokens'] > 1024:
            raise ValueError('Diagnostic read budget exceeded')


def summarize(snapshots, rows, main_rows):
    import numpy as np
    ids = {s['snapshot_id'] for s in snapshots}
    baseline = [r for r in main_rows if r['snapshot_id'] in ids and r['condition'] == 'full']
    combined = baseline + rows
    grouped = defaultdict(list)
    for r in combined:
        grouped[(r['condition'], r['trajectory_id'])].append(r['metrics']['answer.exact_match'])
    scores = {c: mean(mean(v) for (cond, _), v in grouped.items() if cond == c) for c in ('full',) + CONDITIONS}
    differences = {}
    rng = np.random.default_rng(20260912)
    for c in CONDITIONS:
        values = [mean(grouped[(c, s['trajectory_id'])]) - mean(grouped[('full', s['trajectory_id'])]) for s in snapshots]
        bootstrap = rng.choice(values, size=(5000, len(values))).mean(axis=1)
        differences[c] = dict(mean=mean(values), trajectory_bootstrap_95_ci=np.quantile(bootstrap, [0.025, 0.975]).tolist())
    support_coverage = []
    for s in snapshots:
        needed = {s['diagnostic_metadata']['prefix_memory_id'], s['diagnostic_metadata']['suffix_memory_id']}
        support_coverage.extend(needed <= {m['memory_id'] for m in r['context']} for r in baseline if r['snapshot_id'] == s['snapshot_id'])
    return dict(trajectory_count=len(snapshots), additional_generations=len(rows), scores=scores,
                paired_differences_vs_full=differences, full_support_coverage=mean(support_coverage),
                behavior_by_condition={c: dict(Counter(behavior(r['generated_answer'], r['gold_answer'])
                                                       for r in combined if r['condition'] == c)) for c in scores},
                duration_seconds=sum(r['duration_seconds'] for r in rows),
                note='Development-only hindsight controls; no model-internal causal claim; test excluded.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--main-output', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-config', type=Path)
    parser.add_argument('--backend', choices=['test', 'model'], default='model')
    args = parser.parse_args()
    original = read_json(args.main_output / 'manifest.json')
    if original['status'] != 'COMPLETE' or original['parameters']['backend'] != args.backend:
        raise ValueError('Require complete main run with same backend')
    data = read_json(args.main_output / 'dataset-manifest.json')
    snapshots = [s for s in data['snapshots'] if s.get('scenario') == 'complementarity' and s['split'] != 'test']
    if not snapshots:
        raise ValueError('No development complementarity snapshots')
    seeds = data['seeds']
    config = load_config(args.model_config or (ROOT / 'configs/test.yaml' if args.backend == 'test' else None))
    identity = dict(main_manifest_sha256=sha256_file(args.main_output / 'manifest.json'),
                    main_responses_sha256=sha256_file(args.main_output / 'responses.jsonl'),
                    protocol_sha256=sha256_file(HERE / 'protocol-e1-extension.md'),
                    source_hashes=source_hashes(list(HERE.glob('*.py')) + list((HERE/'utility_retention').glob('*.py'))
                                                + list((ROOT/'src/longmem').glob('*.py')), root=ROOT),
                    model=model_identity(config, args.backend),
                    parameters=dict(conditions=CONDITIONS, seeds=seeds, max_generations=216,
                                    max_duration_seconds=900, read_budget=1024, backend=args.backend))
    # JSON roundtrip normalizes tuples for strict resume comparison.
    identity['parameters']['conditions'] = list(CONDITIONS)
    if identity['model'] != original['model']:
        raise ValueError('Diagnostic model differs from main experiment')
    path = args.output / 'manifest.json'
    args.output.mkdir(parents=True, exist_ok=True)
    if path.exists():
        previous = read_json(path)
        if any(previous.get(k) != v for k, v in identity.items()):
            raise ValueError('Diagnostic resume identity mismatch')
    elif any(args.output.iterdir()):
        raise ValueError('Nonempty diagnostic output without manifest')
    manifest = dict(**identity, status='RUNNING', runtime=runtime_metadata())
    write_json(path, manifest)
    try:
        response_path = args.output / 'responses.jsonl'
        rows = read_jsonl(response_path) if response_path.exists() else []
        done = {record_key(r) for r in rows}
        if len(done) != len(rows):
            raise ValueError('Duplicate saved diagnostic records')
        expected = {(s['snapshot_id'], q['query_id'], seed, c)
                    for s in snapshots for q in s['future_queries'] for seed in seeds for c in CONDITIONS}
        if not done <= expected or len(expected) > 216:
            raise ValueError('Unexpected records or generation ceiling exceeded')
        engine = Engine(config, args.backend, 1024, 3)
        spent = sum(r['duration_seconds'] for r in rows)
        for s in snapshots:
            for q in s['future_queries']:
                for seed in seeds:
                    for condition, context in contexts(s).items():
                        base = dict(snapshot_id=s['snapshot_id'], query_id=q['query_id'], seed=seed, condition=condition)
                        if record_key(base) in done:
                            continue
                        if spent >= 900:
                            raise RuntimeError('Diagnostic runtime ceiling reached')
                        start = time.perf_counter()
                        generated = engine.answer(q['text'], context, seed)
                        record = dict(**base, trajectory_id=s['trajectory_id'], split=s['split'], query=q['text'],
                                      gold_answer=q['gold_answer'], context=context, **generated, status='OK',
                                      metrics=score(generated['generated_answer'], q['gold_answer']),
                                      duration_seconds=time.perf_counter()-start)
                        append_jsonl(response_path, record)
                        rows.append(record)
                        done.add(record_key(record))
                        spent += record['duration_seconds']
        validate_responses(snapshots, seeds, rows)
        summary = summarize(snapshots, rows, read_jsonl(args.main_output/'responses.jsonl'))
        write_json(args.output/'summary.json', summary)
        manifest.update(status='COMPLETE', response_count=len(rows))
        write_json(path, manifest)
        print(summary, flush=True)
    except Exception as error:
        manifest.update(status='FAILED', error_type=type(error).__name__)
        write_json(path, manifest)
        raise


if __name__ == '__main__':
    main()
