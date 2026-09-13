"""Read-only model replay and cached-policy microbenchmark for E3."""
import math
import time
from collections import defaultdict
from statistics import median

import numpy as np

from longmem.experiment_io import append_jsonl, read_json, read_jsonl, write_json
from .baselines import dedup_select, parse_importance, similarity_table
from .e2_metrics import response_key
from .e3_formal import make_deployable
from .e3_baselines import strip_times
from .engine import historical_features, serialize
from .policies import baseline_scores, select
from .prediction import FEATURES, predict

ATOL, RTOL = 1e-6, 1e-5


def compare(actual, expected, path='root'):
    """Exact discrete identities, bounded floating-point recomputation drift."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError('Replay keys mismatch: '+path)
        return max((compare(actual[k], v, path+'.'+k) for k, v in expected.items()), default=0.0)
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
            raise ValueError('Replay shape mismatch: '+path)
        return max((compare(a, b, f'{path}[{i}]') for i, (a, b) in enumerate(zip(actual, expected, strict=True))), default=0.0)
    if isinstance(expected, float):
        if not isinstance(actual, (int, float)) or not math.isfinite(actual) or not math.isfinite(expected):
            raise ValueError('Nonfinite replay value: '+path)
        delta = abs(actual-expected)
        if delta > ATOL + RTOL*abs(expected):
            raise ValueError('Replay numeric mismatch: '+path)
        return delta
    if type(actual) is not type(expected) or actual != expected:
        raise ValueError('Replay identity mismatch: '+path)
    return 0.0


def synchronize(engine):
    if engine.backend == 'model':
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()


def measured(engine, function):
    synchronize(engine)
    start = time.perf_counter()
    result = function()
    synchronize(engine)
    return result, time.perf_counter()-start


def replay_history(engine, parent, output):
    past = read_json(parent/'past.json')
    def features():
        result = []
        for s in past:
            for r in historical_features(s['memories'], s['history_queries'], s['event_order'], engine):
                result.append(dict(snapshot_id=s['snapshot_id'], trajectory_id=s['trajectory_id'], memory_id=r['memory_id'],
                                   features={k: r[k] for k in FEATURES}))
        return result
    fresh, history_seconds = measured(engine, features)
    feature_delta = compare(fresh, read_json(parent/'features.json'), 'features')
    similarities, similarity_seconds = measured(engine, lambda: {s['snapshot_id']: similarity_table(s['memories'], engine.embedder) for s in past})
    similarity_delta = compare(similarities, read_json(parent/'similarities.json'), 'similarities')
    plans, predictions = make_deployable(past, fresh, read_jsonl(parent/'importance.jsonl'), similarities,
                                         read_json(parent/'predictor.json'), read_json(parent/'settings.json'))
    prediction_delta = compare(predictions, read_json(parent/'predictions.json'), 'predictions')
    # Selection equality is strict even if numeric recomputations differ within tolerance.
    if strip_times(plans) != strip_times(read_json(parent/'deployable-plans.json')):
        raise ValueError('Recomputed model inputs change a deployable plan')
    result = dict(features=fresh, similarities=similarities, predictions=predictions,
                  plans=strip_times(plans), feature_max_abs_difference=feature_delta,
                  similarity_max_abs_difference=similarity_delta, prediction_max_abs_difference=prediction_delta,
                  history_seconds=history_seconds, similarity_seconds=similarity_seconds)
    path = output/'history-replay.json'
    if path.exists():
        saved = read_json(path)
        for k in ('features', 'similarities', 'predictions', 'plans'):
            compare(result[k], saved[k], k)
        return saved
    write_json(path, result)
    return result


def replay_retrieval(engine, parent, output):
    snapshots = {s['snapshot_id']: s for s in read_json(parent/'dataset.json')}
    responses = read_jsonl(parent/'responses.jsonl')
    path = output/'retrieval-replay.jsonl'
    saved = read_jsonl(path) if path.exists() else []
    def key(r):
        return response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed'])
    expected = {key(r): r for r in responses}
    done = {key(r) for r in saved}
    if len(done) != len(saved) or not done <= set(expected):
        raise ValueError('Duplicate/unexpected retrieval replay rows')
    for r in responses:
        if key(r) in done:
            continue
        s = snapshots[r['snapshot_id']]
        memories = {m['memory_id']: m for m in s['memories']}
        (context, ranking), duration = measured(engine, lambda: engine.retrieve([memories[mid] for mid in r['storage_ids']], r['query']))
        row = dict(snapshot_id=r['snapshot_id'], storage_ids=r['storage_ids'], query_id=r['query_id'], seed=r['seed'],
                   context_ids=[m['memory_id'] for m in context], ranking=ranking,
                   input_tokens=engine.tokens(r['prompt']), output_tokens=engine.tokens(r['generated_answer']),
                   memory_tokens=engine.tokens('\n'.join(serialize(m) for m in context)), duration_seconds=duration)
        compare(row['ranking'], r['ranking'], 'ranking')
        compare(row['context_ids'], [m['memory_id'] for m in r['context']], 'context_ids')
        for k in ('input_tokens', 'output_tokens', 'memory_tokens'):
            compare(row[k], r[k], k)
        append_jsonl(path, row)
        saved.append(row)
        if len(saved) % 100 == 0:
            print(f'retrieval/token replay {len(saved)}/{len(responses)}', flush=True)
    if {key(r) for r in saved} != set(expected):
        raise ValueError('Incomplete retrieval replay')
    for r in saved:
        original = expected[key(r)]
        compare(r['ranking'], original['ranking'], 'ranking')
        compare(r['context_ids'], [m['memory_id'] for m in original['context']], 'context_ids')
        for k in ('input_tokens', 'output_tokens', 'memory_tokens'):
            compare(r[k], original[k], k)
    return saved


def replay_other_tokens(engine, parent, output):
    features = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in read_json(parent/'features.json')}
    storage = []
    for s in read_json(parent/'past.json'):
        for m in s['memories']:
            value = engine.tokens(serialize(m))
            compare(value, features[s['snapshot_id'], m['memory_id']], 'store_tokens')
            storage.append(dict(snapshot_id=s['snapshot_id'], memory_id=m['memory_id'], store_tokens=value))
    importance = []
    for r in read_jsonl(parent/'importance.jsonl'):
        row = {k: r[k] for k in ('snapshot_id', 'memory_id')}
        for key, text_key in [('input_tokens', 'prompt'), ('output_tokens', 'generated_answer')]:
            row[key] = engine.tokens(r[text_key])
            compare(row[key], r[key], key)
        importance.append(row)
    result = dict(storage=storage, importance=importance)
    path = output/'token-replay.json'
    if path.exists():
        compare(result, read_json(path), 'token_replay')
    else:
        write_json(path, result)
    return result


def cached_policy(candidate, past, features, importance, similarities, model, settings):
    """One cached 24-snapshot decision batch; reuse frozen scorers and selectors."""
    start = time.perf_counter()
    grouped = defaultdict(list)
    for r in features:
        grouped[r['snapshot_id']].append(r)
    if candidate == 'utility_aware':
        values = predict(model, [r['features'] for r in features])
        lookup = {(r['snapshot_id'], r['memory_id']): v for r, v in zip(features, values, strict=True)}
    elif candidate == 'importance':
        lookup = {(r['snapshot_id'], r['memory_id']): parse_importance(r['generated_answer'])['score'] for r in importance}
    else:
        lookup = {}
    scorers = {}
    for sid, rows in grouped.items():
        if candidate in ('utility_aware', 'importance'):
            scorers[sid] = [(None, {r['memory_id']: lookup[sid, r['memory_id']] for r in rows})]
        elif candidate == 'random':
            scorers[sid] = [(seed, baseline_scores(rows, 'random', f'{seed}:{sid}')) for seed in settings['random_seeds']]
        elif candidate != 'semantic_dedup':
            scorers[sid] = [(None, baseline_scores(rows, candidate))]
    score_seconds = time.perf_counter()-start
    start = time.perf_counter()
    selected = []
    memories = {s['snapshot_id']: s['memories'] for s in past}
    for sid, rows in sorted(grouped.items()):
        costs = {r['memory_id']: r['features']['memory_tokens'] for r in rows}
        for ratio in settings['budget_ratios']:
            budget = math.floor(sum(costs.values())*ratio)
            if candidate == 'semantic_dedup':
                ids = dedup_select(memories[sid], costs, similarities[sid], settings['selected']['semantic_dedup_threshold'], budget)['storage_ids']
                selected.append((sid, ratio, None, tuple(ids)))
            else:
                for seed, scores in scorers[sid]:
                    ids = sorted(select(costs, scores, budget, candidate == 'utility_aware'))
                    selected.append((sid, ratio, seed, tuple(ids)))
    selection_seconds = time.perf_counter()-start
    return selected, dict(scoring_seconds=score_seconds, selection_seconds=selection_seconds,
                          cached_decision_seconds=score_seconds+selection_seconds)


def benchmark(parent, output, warmups=3, repeats=30):
    past, features = read_json(parent/'past.json'), read_json(parent/'features.json')
    importance, similarities = read_jsonl(parent/'importance.jsonl'), read_json(parent/'similarities.json')
    model, settings = read_json(parent/'predictor.json')['model'], read_json(parent/'settings.json')
    plans = read_json(parent/'deployable-plans.json')
    samples = []
    candidates = ('utility_aware', 'recency', 'retrieval_frequency', 'importance', 'semantic_dedup', 'random')
    for candidate in candidates:
        expected = {(p['snapshot_id'], p['budget_ratio'], p['selection_seed'], tuple(p['storage_ids'])) for p in plans if p['candidate'] == candidate}
        for iteration in range(-warmups, repeats):
            selected, timing = cached_policy(candidate, past, features, importance, similarities, model, settings)
            if len(selected) != len(expected) or set(selected) != expected:
                raise ValueError('Benchmark policy differs from frozen selection')
            if iteration >= 0:
                samples.append(dict(candidate=candidate, repetition=iteration, snapshot_count=len(past),
                                    plan_count=len(selected), **timing))
    aggregates = []
    for candidate in candidates:
        rs = [r for r in samples if r['candidate'] == candidate]
        aggregates.append(dict(candidate=candidate, repetitions=repeats, plan_count=rs[0]['plan_count'],
                               timing={k: dict(median_seconds=median(r[k] for r in rs),
                                               p95_seconds=float(np.quantile([r[k] for r in rs], .95)))
                                       for k in ('scoring_seconds', 'selection_seconds', 'cached_decision_seconds')}))
    result = dict(warmups=warmups, repeats=repeats, samples=samples, aggregates=aggregates,
                  scope='CPU cached-input batch of 24 snapshots and four budgets; random includes all three seeds; no fresh LLM scoring')
    write_json(output/'microbenchmark.json', result)
    return result
