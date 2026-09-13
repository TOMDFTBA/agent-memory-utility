"""Formal E3 lifecycle; frozen E1/E2 functions remain unchanged and reusable."""
import argparse
import math
import shutil
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean

from longmem.config import load_config
from longmem.provenance import source_matches
from longmem.experiment_contracts import SCHEMA_VERSION, canonical_diagnostic_plan
from longmem.experiment_io import (append_jsonl, read_json, read_jsonl, runtime_metadata,
                                   sha256_file, source_hashes, write_json)
from .baselines import importance_prompt, parse_importance, similarity_table
from .e2 import expected_conditions, verify_responses
from .e2_metrics import paired, response_key, summarize
from .e3_baselines import plans_from_past as baseline_plans, strip_times, verify_importance
from .e3_formal_data import build_formal, ensure_past, past_view
from .engine import Engine, historical_features, score, serialize
from .policies import baseline_scores, select
from .prediction import FEATURES, predict
from .runner import HERE, ROOT, model_identity


REFERENCES = ('recency', 'retrieval_frequency', 'importance', 'semantic_dedup', 'random',
              'hindsight_loo', 'full', 'no_memory')


def verify_freeze():
    freeze = read_json(HERE/'e3-formal-freeze-manifest.json')
    for key in ('protocol', 'config'):
        item = freeze[key]
        if sha256_file(HERE/item['path']) != item['sha256']:
            raise ValueError('Original formal freeze changed')
    settings = read_json(HERE/'configs/e3-formal-test.json')
    for item in settings['frozen_inputs'].values():
        if sha256_file(HERE/item['path']) != item['sha256']:
            raise ValueError('Frozen development input changed')
    strategies = read_json(HERE/settings['frozen_inputs']['e3_strategies']['path'])
    for name, digest in strategies['source_hashes'].items():
        if not source_matches(ROOT, name, digest):
            raise ValueError('Frozen shared implementation changed: '+name)
    if importance_prompt('{memory_content}') != strategies['importance']['prompt']:
        raise ValueError('Frozen importance prompt changed')
    return settings, strategies


def prepare(args):
    settings, strategies = verify_freeze()
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Use a new empty E3 output directory')
    if args.backend == 'test':
        settings['dataset'] = dict(settings['dataset'], structure_seed=2026091501, surface_seed=2026091502)
    previous_path = HERE/'results/e1-extension-model/dataset-manifest.json'
    previous = read_json(previous_path)['snapshots']
    snapshots = build_formal(settings['dataset'], previous)
    sources = list((HERE/'utility_retention').glob('*.py')) + list((ROOT/'src/longmem').glob('*.py'))
    sources += [HERE/'e3_formal.py', HERE/'generate_e1_extension.py']
    args.output.mkdir(parents=True, exist_ok=True)
    values = {'settings.json': settings, 'strategies.json': strategies,
              'predictor.json': read_json(HERE/settings['frozen_inputs']['e2_predictor']['path']),
              'dataset.json': snapshots, 'past.json': past_view(snapshots),
              'previous-snapshots.json': previous,
              'dataset-manifest.json': dict(dataset=settings['dataset'], split='test', trajectory_count=len(snapshots),
                                            previous_sha256=sha256_file(previous_path), disjoint_checked=True)}
    for name, value in values.items():
        write_json(args.output/name, value)
    for src, name in [(HERE/'protocol-e3-formal-test.md', 'protocol.md'),
                      (HERE/'protocol-e3-formal-clarification.md', 'clarification.md'),
                      (HERE/'e3-formal-freeze-manifest.json', 'original-freeze.json')]:
        shutil.copyfile(src, args.output/name)
    for src in sources:
        dest = args.output/'source-snapshot'/src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    manifest = dict(schema_version=SCHEMA_VERSION, experiment_id='utility-retention-v0.2-e3-formal',
                    status='PREPARED', backend=args.backend, parameters=settings,
                    protocol_sha256=sha256_file(args.output/'protocol.md'),
                    clarification_sha256=sha256_file(args.output/'clarification.md'),
                    dataset_sha256=sha256_file(args.output/'dataset.json'),
                    source_hashes=source_hashes(sources, root=ROOT), runtime=runtime_metadata(),
                    input_hashes={p.name: sha256_file(p) for p in args.output.iterdir() if p.is_file()},
                    artifact_hashes={}, model=None)
    write_json(args.output/'manifest.json', manifest)
    print(f'PREPARED: {len(snapshots)} independent trajectories; backend={args.backend}', flush=True)


def check(output):
    verify_freeze()
    manifest = read_json(output/'manifest.json')
    for group in ('input_hashes', 'artifact_hashes'):
        for name, digest in manifest[group].items():
            if sha256_file(output/name) != digest:
                raise ValueError('E3 artifact identity mismatch: '+name)
    for name, digest in manifest['source_hashes'].items():
        if not source_matches(ROOT, name, digest) or sha256_file(output/'source-snapshot'/name) != digest:
            raise ValueError('E3 source identity mismatch: '+name)
    if manifest['parameters'] != read_json(output/'settings.json'):
        raise ValueError('Settings identity mismatch')
    return manifest


def seal(output, manifest, name, value):
    path = output/name
    if path.exists():
        saved = read_json(path)
        equal = strip_times(saved) == strip_times(value) if name.endswith('plans.json') else saved == value
        if not equal:
            raise ValueError('Frozen intermediate changed: '+name)
        value = saved
    else:
        write_json(path, value)
    manifest['artifact_hashes'][name] = sha256_file(path)
    write_json(output/'manifest.json', manifest)
    return value


def make_deployable(past, features, importance, similarities, predictor, settings):
    ensure_past(past, features)
    predictions = predict(predictor['model'], [r['features'] for r in features])
    grouped = defaultdict(list)
    for row, value in zip(features, predictions, strict=True):
        grouped[row['snapshot_id']].append((row, value))
    plans = []
    for sid, items in sorted(grouped.items()):
        rows = [r for r, _ in items]
        costs = {r['memory_id']: r['features']['memory_tokens'] for r in rows}
        scorers = [('utility_aware', None, {r['memory_id']: v for r, v in items}, True)]
        scorers += [(n, None, baseline_scores(rows, n), False) for n in ('recency', 'retrieval_frequency')]
        scorers += [('random', seed, baseline_scores(rows, 'random', f'{seed}:{sid}'), False)
                    for seed in settings['random_seeds']]
        scorers += [('full', None, {}, False), ('no_memory', None, {}, False)]
        for ratio in settings['budget_ratios']:
            budget = math.floor(sum(costs.values())*ratio)
            for name, selection_seed, scores, positive in scorers:
                start = time.perf_counter()
                ids = sorted(costs) if name == 'full' else ([] if name == 'no_memory' else
                       sorted(select(costs, scores, budget, positive)))
                plans.append(dict(snapshot_id=sid, candidate=name, selection_seed=selection_seed,
                                  budget_ratio=ratio, budget_tokens=budget, storage_ids=ids,
                                  store_tokens=sum(costs[m] for m in ids), seed=settings['generation_seed'],
                                  selection_seconds=time.perf_counter()-start))
    extra = baseline_plans(past, features, importance, similarities,
                           dict(settings, dedup_thresholds=[settings['selected']['semantic_dedup_threshold']]))
    for p in extra:
        if p['candidate'].startswith('semantic_dedup-t'):
            p['candidate'] = 'semantic_dedup'
    return plans+extra, predictions


def deletion_plans(snapshots, seed):
    return [dict(snapshot_id=s['snapshot_id'], intervention='storage_deletion', deleted_memory_id=m['memory_id'],
                 storage_ids=sorted(x['memory_id'] for x in s['memories'] if x != m), seed=seed)
            for s in snapshots for m in s['memories']]


def loo_labels(snapshots, responses, seed):
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    labels = []
    for s in snapshots:
        ids = sorted(m['memory_id'] for m in s['memories'])
        for mid in ids:
            effects = []
            for q in s['future_queries']:
                full = index[response_key(s['snapshot_id'], ids, q['query_id'], seed)]
                deleted = index[response_key(s['snapshot_id'], [m for m in ids if m != mid], q['query_id'], seed)]
                effects.append(dict(query_id=q['query_id'], utility=full['metrics']['answer.exact_match']-
                                    deleted['metrics']['answer.exact_match']))
            labels.append(dict(snapshot_id=s['snapshot_id'], memory_id=mid,
                               loo_value=mean(e['utility'] for e in effects), query_utilities=effects))
    return labels


def hindsight_plans(features, labels, settings):
    by_sid = defaultdict(list)
    values = {(r['snapshot_id'], r['memory_id']): r['loo_value'] for r in labels}
    for r in features:
        by_sid[r['snapshot_id']].append(r)
    plans = []
    for sid, rows in sorted(by_sid.items()):
        costs = {r['memory_id']: r['features']['memory_tokens'] for r in rows}
        scores = {mid: values[(sid, mid)] for mid in costs}
        for ratio in settings['budget_ratios']:
            start = time.perf_counter()
            budget = math.floor(sum(costs.values())*ratio)
            ids = sorted(select(costs, scores, budget, True))
            plans.append(dict(snapshot_id=sid, candidate='hindsight_loo', selection_seed=None,
                              budget_ratio=ratio, budget_tokens=budget, storage_ids=ids,
                              store_tokens=sum(costs[m] for m in ids), seed=settings['generation_seed'],
                              selection_seconds=time.perf_counter()-start))
    return plans


def derive(plans, responses, snapshots, labels, settings):
    adapted = [dict(r, target={'value': r['loo_value']}) for r in labels]
    summary = summarize(plans, responses, snapshots, adapted)
    averaged = defaultdict(list)
    for row in summary['per_trajectory']:
        if row['budget_ratio'] in settings['primary_budget_ratios']:
            averaged[(row['candidate'], row['trajectory_id'])].append(row['metrics']['answer.exact_match'])
    pooled = {'per_trajectory': [dict(candidate=c, trajectory_id=t, budget_ratio='primary_average',
                                     metrics={'answer.exact_match': mean(v)}) for (c, t), v in sorted(averaged.items())]}
    contrasts = []
    for ratio in ['primary_average']+settings['budget_ratios']:
        for baseline in REFERENCES:
            result = paired(pooled if ratio == 'primary_average' else summary, 'utility_aware', baseline,
                            ratio, settings['bootstrap_seed'], settings['bootstrap_repeats'])
            result['inference'] = 'held-out finite synthetic pressure set; descriptive trajectory bootstrap'
            contrasts.append(result)
    summary['primary_per_trajectory'] = pooled['per_trajectory']
    summary['paired_differences'] = contrasts
    main = next(r for r in contrasts if r['baseline'] == 'importance' and r['budget_ratio'] == 'primary_average')
    low, high = main['trajectory_bootstrap_95_ci']
    summary['primary_result'] = dict(main, interpretation='positive' if low > 0 else 'negative' if high < 0 else 'inconclusive')
    return summary


def support_diagnostics(plans, responses, snapshots):
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    data = {s['snapshot_id']: s for s in snapshots}
    result = []
    for p in plans:
        s = data[p['snapshot_id']]
        for q in s['future_queries']:
            r = index[response_key(p['snapshot_id'], p['storage_ids'], q['query_id'], p['seed'])]
            context = {m['memory_id'] for m in r['context']}
            stored = any(set(group) <= set(p['storage_ids']) for group in q['supporting_memory_sets'])
            read = any(set(group) <= context for group in q['supporting_memory_sets'])
            result.append(dict(snapshot_id=s['snapshot_id'], trajectory_id=s['trajectory_id'], scenario=s['scenario'],
                               candidate=p['candidate'], budget_ratio=p['budget_ratio'], selection_seed=p['selection_seed'],
                               query_id=q['query_id'], metrics={'retention.support_set_complete': int(stored),
                               'retrieval.support_set_complete': int(read),
                               'answer.hit_but_wrong': int(read and not r['metrics']['answer.exact_match'])},
                               generated_answer=r['generated_answer'], gold_answer=q['gold_answer']))
    return result


def enforce_limits(importance, responses, settings):
    limits = settings['limits']
    spent = sum(r['duration_seconds'] for r in importance+responses)
    if (len(importance) > limits['max_importance_generations'] or len(responses) > limits['max_answer_generations']
            or spent > limits['max_cumulative_seconds']):
        raise RuntimeError('Formal execution ceiling exceeded')
    return spent


def execute(args):
    output = args.output
    manifest = check(output)
    if args.backend != manifest['backend']:
        raise ValueError('Backend mismatch')
    if manifest['status'] == 'COMPLETE':
        print(audit(output))
        return
    settings = manifest['parameters']
    config = load_config(args.model_config or (ROOT/'configs/test.yaml' if args.backend == 'test' else None))
    if args.backend == 'test':
        config['embedding'] = {'backend': 'hash-test'}
        config['generation'] = {'backend': 'evidence-test'}
    identity = model_identity(config, args.backend)
    strategies = read_json(output/'strategies.json')
    if args.backend == 'model' and identity != strategies['model']:
        raise ValueError('Frozen model identity mismatch')
    if manifest['model'] is not None and identity != manifest['model']:
        raise ValueError('Resume model mismatch')
    manifest.update(model=identity, status='RUNNING', runtime=runtime_metadata())
    write_json(output/'manifest.json', manifest)
    importance = read_jsonl(output/'importance.jsonl') if (output/'importance.jsonl').exists() else []
    responses = read_jsonl(output/'responses.jsonl') if (output/'responses.jsonl').exists() else []
    try:
        enforce_limits(importance, responses, settings)
        engine = Engine(config, args.backend, settings['read_budget'], settings['top_k'])
        past = read_json(output/'past.json')
        start = time.perf_counter()
        features = []
        for s in past:
            for r in historical_features(s['memories'], s['history_queries'], s['event_order'], engine):
                features.append(dict(snapshot_id=s['snapshot_id'], trajectory_id=s['trajectory_id'], memory_id=r['memory_id'],
                                     features={k: r[k] for k in FEATURES}))
        features = seal(output, manifest, 'features.json', features)
        similarities = {s['snapshot_id']: similarity_table(s['memories'], engine.embedder) for s in past}
        similarities = seal(output, manifest, 'similarities.json', similarities)
        manifest.setdefault('history_similarity_seconds', time.perf_counter()-start)
        importance_seed = strategies['importance']['seed']
        verify_importance(past, importance, args.backend, importance_seed, False)
        done = {(r['snapshot_id'], r['memory_id']) for r in importance}
        for s in past:
            for m in s['memories']:
                if (s['snapshot_id'], m['memory_id']) in done:
                    continue
                start = time.perf_counter()
                prompt = importance_prompt(m['content'])
                if args.backend == 'model':
                    import torch
                    torch.manual_seed(importance_seed)
                    answer = engine.generator.generate(prompt, [])
                else:
                    answer = '3'
                row = dict(snapshot_id=s['snapshot_id'], memory_id=m['memory_id'], prompt=prompt,
                           generated_answer=answer, parsed=parse_importance(answer), backend=args.backend, seed=importance_seed,
                           status='OK', input_tokens=engine.tokens(prompt), output_tokens=engine.tokens(answer),
                           duration_seconds=time.perf_counter()-start)
                append_jsonl(output/'importance.jsonl', row)
                importance.append(row)
                enforce_limits(importance, responses, settings)
        verify_importance(past, importance, args.backend, importance_seed)
        manifest['artifact_hashes']['importance.jsonl'] = sha256_file(output/'importance.jsonl')
        plans, predictions = make_deployable(past, features, importance, similarities,
                                             read_json(output/'predictor.json'), settings)
        plans = seal(output, manifest, 'deployable-plans.json', plans)
        seal(output, manifest, 'predictions.json', predictions)
        print(f'Deployable plans frozen: {len(plans)}; importance={len(importance)}', flush=True)
        # Only this evaluation phase accesses future questions and support annotations.
        snapshots = read_json(output/'dataset.json')
        data = {s['snapshot_id']: s for s in snapshots}

        def evaluate(required):
            verify_responses(required, snapshots, responses, settings, False)
            keys = expected_conditions(required, snapshots)
            if len(keys) > settings['limits']['max_answer_generations']:
                raise RuntimeError('Formal answer ceiling exceeded before generation')
            done = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']) for r in responses}
            for sid, ids, qid, seed in sorted(keys):
                if (sid, ids, qid, seed) in done:
                    continue
                enforce_limits(importance, responses, settings)
                s = data[sid]
                q = next(q for q in s['future_queries'] if q['query_id'] == qid)
                memories = {m['memory_id']: m for m in s['memories']}
                start = time.perf_counter()
                context, ranking = engine.retrieve([memories[mid] for mid in ids], q['text'])
                generated = engine.answer(q['text'], context, seed)
                row = dict(snapshot_id=sid, trajectory_id=s['trajectory_id'], split='test', query_id=qid,
                           seed=seed, storage_ids=list(ids), context=context, ranking=ranking, query=q['text'],
                           gold_answer=q['gold_answer'], backend=args.backend, status='OK', **generated,
                           metrics=score(generated['generated_answer'], q['gold_answer']),
                           duration_seconds=time.perf_counter()-start)
                append_jsonl(output/'responses.jsonl', row)
                responses.append(row)
                spent = enforce_limits(importance, responses, settings)
                if len(responses) % 25 == 0:
                    print(f'answers {len(responses)}/{len(keys)}; cumulative {spent:.1f}s', flush=True)
            verify_responses(required, snapshots, responses, settings)

        # Resume later phases against their union, preserving the first-phase seal.
        if 'deployable-complete.json' not in manifest['artifact_hashes']:
            evaluate(plans)
            seal(output, manifest, 'deployable-complete.json', dict(response_count=len(responses),
                 response_prefix_sha256=sha256_file(output/'responses.jsonl'),
                 plans_sha256=sha256_file(output/'deployable-plans.json')))
        diagnostic = seal(output, manifest, 'diagnostic-plans.json', deletion_plans(snapshots, settings['generation_seed']))
        existing_hindsight = read_json(output/'hindsight-plans.json') if (output/'hindsight-plans.json').exists() else []
        evaluate(plans+diagnostic+existing_hindsight)
        labels = seal(output, manifest, 'hindsight-labels.json', loo_labels(snapshots, responses, settings['generation_seed']))
        hindsight = seal(output, manifest, 'hindsight-plans.json', hindsight_plans(features, labels, settings))
        evaluate(plans+diagnostic+hindsight)
        all_plans = seal(output, manifest, 'plans.json', plans+hindsight)
        for r in importance+responses:
            if r['input_tokens'] != engine.tokens(r['prompt']) or r['output_tokens'] != engine.tokens(r['generated_answer']):
                raise ValueError('Actual tokenizer cost mismatch')
        for r in responses:
            if r['memory_tokens'] != engine.tokens('\n'.join(serialize(m) for m in r['context'])):
                raise ValueError('Read tokens mismatch')
        seal(output, manifest, 'summary.json', derive(all_plans, responses, snapshots, labels, settings))
        seal(output, manifest, 'support-diagnostics.json', support_diagnostics(all_plans, responses, snapshots))
        manifest.update(status='VERIFYING', token_costs_recomputed=True, historical_inputs_replayed=True,
                        response_count=len(responses), importance_count=len(importance),
                        cumulative_seconds=enforce_limits(importance, responses, settings))
        manifest['artifact_hashes']['responses.jsonl'] = sha256_file(output/'responses.jsonl')
        write_json(output/'manifest.json', manifest)
        write_json(output/'audit.json', audit(output))
        from .e3_formal_report import report
        report(output)
        for name in ('audit.json', 'report.md', 'cost-report.json', 'budget-curve.png', 'budget-curve.svg'):
            manifest['artifact_hashes'][name] = sha256_file(output/name)
        manifest['status'] = 'COMPLETE'
        write_json(output/'manifest.json', manifest)
        print('COMPLETE: formal evaluation and independent replay passed', flush=True)
    except Exception as error:
        manifest.update(status='FAILED', error_type=type(error).__name__, error=str(error))
        write_json(output/'manifest.json', manifest)
        raise


def audit(output):
    manifest = check(output)
    settings = manifest['parameters']
    snapshots = read_json(output/'dataset.json')
    if snapshots != build_formal(settings['dataset'], read_json(output/'previous-snapshots.json')):
        raise ValueError('Dataset replay mismatch')
    past = read_json(output/'past.json')
    if past != past_view(snapshots):
        raise ValueError('Past view mismatch')
    features = read_json(output/'features.json')
    importance = read_jsonl(output/'importance.jsonl')
    strategies = read_json(output/'strategies.json')
    verify_importance(past, importance, manifest['backend'], strategies['importance']['seed'])
    plans, predictions = make_deployable(past, features, importance, read_json(output/'similarities.json'),
                                         read_json(output/'predictor.json'), settings)
    if strip_times(plans) != strip_times(read_json(output/'deployable-plans.json')):
        raise ValueError('Deployable selection mismatch')
    if predictions != read_json(output/'predictions.json'):
        raise ValueError('Prediction mismatch')
    responses = read_jsonl(output/'responses.jsonl')
    marker = read_json(output/'deployable-complete.json')
    prefix = responses[:marker['response_count']]
    verify_responses(plans, snapshots, prefix, settings)
    import hashlib
    with (output/'responses.jsonl').open('rb') as stream:
        prefix_hash = hashlib.sha256(b''.join(next(stream) for _ in prefix)).hexdigest()
    if prefix_hash != marker['response_prefix_sha256'] or marker['plans_sha256'] != sha256_file(output/'deployable-plans.json'):
        raise ValueError('Deployable-before-hindsight seal mismatch')
    diagnostic = deletion_plans(snapshots, settings['generation_seed'])
    if diagnostic != [canonical_diagnostic_plan(row) for row in read_json(output/'diagnostic-plans.json')]:
        raise ValueError('Deletion plans mismatch')
    labels = loo_labels(snapshots, responses, settings['generation_seed'])
    if labels != read_json(output/'hindsight-labels.json'):
        raise ValueError('LOO recomputation mismatch')
    hindsight = hindsight_plans(features, labels, settings)
    if strip_times(hindsight) != strip_times(read_json(output/'hindsight-plans.json')):
        raise ValueError('Hindsight selection mismatch')
    all_plans = plans+hindsight
    if strip_times(all_plans) != strip_times(read_json(output/'plans.json')):
        raise ValueError('Combined plans mismatch')
    if any(p['candidate'] != 'full' and p['store_tokens'] > p['budget_tokens'] for p in all_plans):
        raise ValueError('Storage budget exceeded')
    verify_responses(all_plans+diagnostic, snapshots, responses, settings)
    if any(r['backend'] != manifest['backend'] or r['split'] != 'test' for r in responses):
        raise ValueError('Backend/split mismatch')
    if derive(all_plans, responses, snapshots, labels, settings) != read_json(output/'summary.json'):
        raise ValueError('Summary replay mismatch')
    if support_diagnostics(all_plans, responses, snapshots) != read_json(output/'support-diagnostics.json'):
        raise ValueError('Support diagnostic mismatch')
    enforce_limits(importance, responses, settings)
    if manifest['backend'] == 'model' and manifest['model'] != strategies['model']:
        raise ValueError('Model identity mismatch')
    return dict(passed=True, dataset_replayed=True, predictions_replayed=True, plans_replayed=True,
                labels_recomputed=True, scores_recomputed=True, paired_statistics_recomputed=True,
                deployable_before_hindsight_verified=True, budgets_verified=True,
                response_count=len(responses), importance_count=len(importance),
                model_evidence=manifest['backend'] == 'model')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'audit'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=['test', 'model'], default='model')
    parser.add_argument('--model-config', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args)
    elif args.action == 'run':
        execute(args)
    else:
        print(audit(args.output))
