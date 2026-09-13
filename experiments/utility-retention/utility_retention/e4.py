"""E4 independent lifecycle; E1/E2/E3 implementations and artifacts remain frozen."""
from .numeric_replay import replay_equal

import argparse
import copy
import os
import shutil
import time
from pathlib import Path

from longmem.config import load_config
from longmem.provenance import source_matches
from longmem.experiment_contracts import SCHEMA_VERSION
from longmem.experiment_io import (append_jsonl, read_json, read_jsonl, runtime_metadata,
                                   sha256_file, source_hashes, write_json)
from .baselines import importance_prompt, parse_importance, similarity_table
from .e2 import expected_conditions, verify_responses
from .e2_metrics import response_key
from .e3_baselines import strip_times, verify_importance
from .e3_formal import audit as parent_audit, make_deployable, seal, verify_freeze
from .e3_formal_data import build_formal, past_view, ensure_past
from .engine import Engine, historical_features, score, serialize
from .prediction import FEATURES
from .runner import HERE, ROOT, model_identity
from .e4_analysis import derive, enumeration_plans, exact_predicted_plans, EXACT_PREDICTED
from .e4_controls import context_plans, control_key, verify_controls, verify_tokens


def records(path):
    return read_jsonl(path) if path.exists() else []


def parent_identity(parent):
    return {p.name: sha256_file(p) for p in parent.iterdir() if p.is_file()}


def prepare(args):
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('E4 prepare requires a new empty directory')
    parent_audit(args.parent)
    pm = read_json(args.parent/'manifest.json')
    if pm['status'] != 'COMPLETE' or pm['backend'] != args.backend:
        raise ValueError('Parent must be complete and use the same backend')
    settings = read_json(HERE/'configs/e4-diagnostic.json')
    base, _ = verify_freeze()
    for key in ('budget_ratios', 'primary_budget_ratios', 'generation_seed', 'read_budget', 'top_k',
                'random_seeds', 'bootstrap_seed', 'bootstrap_repeats', 'selected'):
        settings[key] = copy.deepcopy(base[key])
    if args.backend == 'test':
        settings['dataset'].update(structure_seed=2026091801, surface_seed=2026091802)
    old = read_json(args.parent/'dataset.json')
    previous = read_json(HERE/'results/e1-extension-model/dataset-manifest.json')['snapshots'] + old
    fresh = build_formal(settings['dataset'], previous)
    snapshots = old + fresh
    cohorts = {s['snapshot_id']: 'e3_posthoc' for s in old}
    cohorts.update({s['snapshot_id']: 'e4_independent' for s in fresh})
    count = sum(2**len(s['memories'])*len(s['future_queries']) for s in snapshots)
    if count > settings['limits']['max_enumeration_conditions']:
        raise ValueError('Enumeration ceiling exceeded before execution')
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in {'settings.json': settings, 'dataset.json': snapshots, 'past.json': past_view(snapshots),
                        'cohorts.json': cohorts, 'previous-snapshots.json': previous,
                        'parent-identity.json': dict(path=os.path.relpath(args.parent.resolve(), ROOT),
                                                     hashes=parent_identity(args.parent)),
                        'enumeration-plans.json': enumeration_plans(past_view(snapshots), settings['generation_seed'])}.items():
        write_json(args.output/name, value)
    for src, dest in [('predictor.json', 'predictor.json'), ('strategies.json', 'strategies.json'),
                      ('responses.jsonl', 'inherited-responses.jsonl'), ('importance.jsonl', 'inherited-importance.jsonl')]:
        shutil.copyfile(args.parent/src, args.output/dest)
    shutil.copyfile(HERE/'protocol-e4-diagnostic.md', args.output/'protocol.md')
    sources = list((HERE/'utility_retention').glob('*.py'))+list((ROOT/'src/longmem').glob('*.py'))
    sources += [HERE/'e4.py', HERE/'generate_e1_extension.py']
    for src in sources:
        dest = args.output/'source-snapshot'/src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    manifest = dict(schema_version=SCHEMA_VERSION, experiment_id='utility-retention-v0.2-e4-diagnostic',
                    status='PREPARED', backend=args.backend, model=pm['model'], parameters=settings,
                    runtime=runtime_metadata(), protocol_sha256=sha256_file(args.output/'protocol.md'),
                    dataset_sha256=sha256_file(args.output/'dataset.json'), source_hashes=source_hashes(sources, root=ROOT),
                    input_hashes={p.name: sha256_file(p) for p in args.output.iterdir() if p.is_file()}, artifact_hashes={})
    write_json(args.output/'manifest.json', manifest)
    print(f'PREPARED E4: {len(old)} post-hoc + {len(fresh)} independent; {count} enumeration conditions', flush=True)


def check(output):
    manifest = read_json(output/'manifest.json')
    for group in ('input_hashes', 'artifact_hashes'):
        for name, digest in manifest[group].items():
            if sha256_file(output/name) != digest:
                raise ValueError('E4 artifact identity mismatch: '+name)
    for name, digest in manifest['source_hashes'].items():
        if not source_matches(ROOT, name, digest) or sha256_file(output/'source-snapshot'/name) != digest:
            raise ValueError('E4 source identity mismatch: '+name)
    parent = read_json(output/'parent-identity.json')
    if parent_identity(ROOT/parent['path']) != parent['hashes']:
        raise ValueError('Frozen parent changed')
    if manifest['parameters'] != read_json(output/'settings.json'):
        raise ValueError('E4 settings changed')
    pm = read_json(ROOT/parent['path']/'manifest.json')
    if manifest['model'] != pm['model'] or manifest['backend'] != pm['backend']:
        raise ValueError('E4 parent model/backend mismatch')
    return manifest


def limit(output, settings):
    importance = records(output/'importance.jsonl')
    answers = records(output/'responses.jsonl')+records(output/'winner-repeats.jsonl')+records(output/'context-controls.jsonl')
    elapsed = sum(r['duration_seconds'] for r in importance+answers)
    limits = settings['limits']
    if len(importance) > limits['max_importance_generations'] or len(answers) > limits['max_new_answer_generations'] or elapsed > limits['max_cumulative_seconds']:
        raise RuntimeError('E4 execution ceiling exceeded')
    return dict(new_importance_count=len(importance), new_answer_count=len(answers), cumulative_model_seconds=elapsed,
                inherited_answer_count=len(records(output/'inherited-responses.jsonl')))


def replay_winners(plans, responses, repeated, snapshots, settings, complete=True):
    winners = [p for p in plans if p['candidate'] == 'best_subset']
    verify_responses(winners, snapshots, repeated, settings, complete)
    index = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']): r for r in responses}
    changed = []
    for r in repeated:
        key = response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed'])
        before = index[key]
        if r['context'] != before['context'] or r['prompt'] != before['prompt']:
            raise ValueError('Independent winner repeat changed its input')
        if r['generated_answer'] != before['generated_answer'] or r['metrics'] != before['metrics']:
            changed.append([key[0], list(key[1]), key[2], key[3]])
    return dict(repeated_conditions=len(repeated), changed_conditions=changed,
                interpretation='Same-seed independent execution tests determinism, not random-decoding variance or new-task generalization')


def execute(args):
    output = args.output
    manifest = check(output)
    if args.backend != manifest['backend']:
        raise ValueError('E4 execution backend mismatch')
    if manifest['status'] == 'COMPLETE':
        print(audit(output), flush=True)
        return
    settings = manifest['parameters']
    config = load_config(args.model_config or (ROOT/'configs/test.yaml' if args.backend == 'test' else None))
    if args.backend == 'test':
        config['embedding'] = {'backend': 'hash-test'}
        config['generation'] = {'backend': 'evidence-test'}
    if model_identity(config, args.backend) != manifest['model']:
        raise ValueError('Frozen model identity changed')
    manifest.update(status='RUNNING', runtime=runtime_metadata())
    write_json(output/'manifest.json', manifest)
    try:
        limit(output, settings)
        engine = Engine(config, args.backend, settings['read_budget'], settings['top_k'])
        past = read_json(output/'past.json')
        start = time.perf_counter()
        features = [dict(snapshot_id=s['snapshot_id'], trajectory_id=s['trajectory_id'], memory_id=r['memory_id'],
                         features={k: r[k] for k in FEATURES}) for s in past
                    for r in historical_features(s['memories'], s['history_queries'], s['event_order'], engine)]
        ensure_past(past, features)
        seal(output, manifest, 'features.json', features)
        similarities = {s['snapshot_id']: similarity_table(s['memories'], engine.embedder) for s in past}
        seal(output, manifest, 'similarities.json', similarities)
        manifest.setdefault('historical_feature_similarity_seconds', time.perf_counter()-start)
        importance = records(output/'inherited-importance.jsonl')+records(output/'importance.jsonl')
        strategies = read_json(output/'strategies.json')
        importance_seed = strategies['importance']['seed']
        verify_importance(past, importance, args.backend, importance_seed, False)
        done = {(r['snapshot_id'], r['memory_id']) for r in importance}
        for s in past:
            for m in s['memories']:
                if (s['snapshot_id'], m['memory_id']) in done:
                    continue
                limit(output, settings)
                start = time.perf_counter()
                prompt = importance_prompt(m['content'])
                if args.backend == 'model':
                    import torch
                    torch.manual_seed(importance_seed)
                    answer = engine.generator.generate(prompt, [])
                else:
                    answer = '3'
                row = dict(snapshot_id=s['snapshot_id'], memory_id=m['memory_id'], prompt=prompt,
                           generated_answer=answer, parsed=parse_importance(answer), backend=args.backend,
                           seed=importance_seed, status='OK', input_tokens=engine.tokens(prompt),
                           output_tokens=engine.tokens(answer), duration_seconds=time.perf_counter()-start)
                append_jsonl(output/'importance.jsonl', row)
                importance.append(row)
        verify_importance(past, importance, args.backend, importance_seed)
        deployable, predictions = make_deployable(past, features, importance, similarities,
                                                 read_json(output/'predictor.json'), settings)
        deployable = strip_times(deployable)
        deployable += exact_predicted_plans(past, features, predictions, settings)
        seal(output, manifest, 'predictions.json', predictions)
        seal(output, manifest, 'deployable-plans.json', deployable)
        seal(output, manifest, 'deployable-freeze.json', dict(
            plans_sha256=sha256_file(output/'deployable-plans.json'),
            features_sha256=sha256_file(output/'features.json'),
            predictor_sha256=sha256_file(output/'predictor.json')))
        # Both greedy and exact predicted selections are now frozen before future evaluation.
        snapshots = read_json(output/'dataset.json')
        data = {s['snapshot_id']: s for s in snapshots}
        seal(output, manifest, 'scenario-checks.json', scenario_checks(snapshots, features, args.backend))
        enumeration = read_json(output/'enumeration-plans.json')
        responses = records(output/'inherited-responses.jsonl')+records(output/'responses.jsonl')
        verify_responses(enumeration, snapshots, responses, settings, False)

        def generate(key):
            sid, ids, qid, seed = key
            s = data[sid]
            q = next(q for q in s['future_queries'] if q['query_id'] == qid)
            memories = {m['memory_id']: m for m in s['memories']}
            start = time.perf_counter()
            context, ranking = engine.retrieve([memories[mid] for mid in ids], q['text'])
            generated = engine.answer(q['text'], context, seed)
            return dict(snapshot_id=sid, trajectory_id=s['trajectory_id'], split='test', query_id=qid,
                        seed=seed, storage_ids=list(ids), context=context, ranking=ranking, query=q['text'],
                        gold_answer=q['gold_answer'], backend=args.backend, status='OK',
                        deployable_sha256=sha256_file(output/'deployable-plans.json'), **generated,
                        metrics=score(generated['generated_answer'], q['gold_answer']),
                        duration_seconds=time.perf_counter()-start)

        required = expected_conditions(enumeration, snapshots)
        done = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']) for r in responses}
        print(f'E4 plans frozen; enumeration {len(done)}/{len(required)} cached within verified parent identity', flush=True)
        for key in sorted(required):
            if key in done:
                continue
            limit(output, settings)
            row = generate(key)
            append_jsonl(output/'responses.jsonl', row)
            responses.append(row)
            if len(responses) % 50 == 0:
                print(f'E4 enumeration {len(responses)}/{len(required)}', flush=True)
        verify_responses(enumeration, snapshots, responses, settings)
        result = derive(snapshots, features, predictions, deployable, responses, settings, read_json(output/'cohorts.json'))
        for name, value in result.items():
            seal(output, manifest, name.replace('_', '-')+'.json', value)
        winners = [p for p in result['plans'] if p['candidate'] == 'best_subset']
        repeated = records(output/'winner-repeats.jsonl')
        replay_winners(result['plans'], responses, repeated, snapshots, settings, False)
        repeated_keys = {response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed']) for r in repeated}
        winner_keys = expected_conditions(winners, snapshots)
        print(f'E4 independent winner repetitions: {len(winner_keys)} conditions', flush=True)
        for key in sorted(winner_keys):
            if key not in repeated_keys:
                limit(output, settings)
                row = generate(key)
                append_jsonl(output/'winner-repeats.jsonl', row)
                repeated.append(row)
        seal(output, manifest, 'winner-stability.json', replay_winners(result['plans'], responses, repeated, snapshots, settings))
        controls = context_plans(snapshots, responses, settings['generation_seed'])
        seal(output, manifest, 'context-plans.json', controls)
        cr = records(output/'context-controls.jsonl')
        verify_controls(controls, cr, snapshots, settings, False)
        done_controls = {control_key(r) for r in cr}
        print(f'E4 context controls: {len(controls)} conditions', flush=True)
        for p in controls:
            if control_key(p) in done_controls:
                continue
            limit(output, settings)
            s = data[p['snapshot_id']]
            q = next(q for q in s['future_queries'] if q['query_id'] == p['query_id'])
            memories = {m['memory_id']: m for m in s['memories']}
            context = [memories[mid] for mid in p['context_ids']]
            start = time.perf_counter()
            generated = engine.answer(q['text'], context, p['seed'])
            row = dict(p, trajectory_id=s['trajectory_id'], split='test', context=context,
                       query=q['text'], gold_answer=q['gold_answer'], backend=args.backend, status='OK',
                       **generated, metrics=score(generated['generated_answer'], q['gold_answer']),
                       duration_seconds=time.perf_counter()-start)
            append_jsonl(output/'context-controls.jsonl', row)
            cr.append(row)
        verify_controls(controls, cr, snapshots, settings)
        verify_tokens(engine, importance+responses+repeated+cr)
        for r in features:
            m = next(m for m in data[r['snapshot_id']]['memories'] if m['memory_id'] == r['memory_id'])
            if r['features']['memory_tokens'] != engine.tokens(serialize(m)):
                raise ValueError('Store token cost mismatch')
        seal(output, manifest, 'cost-report.json', limit(output, settings))
        manifest.update(status='VERIFYING', actual_tokens_verified=True, expected_responses=len(required))
        for name in ('importance.jsonl', 'responses.jsonl', 'winner-repeats.jsonl', 'context-controls.jsonl'):
            manifest['artifact_hashes'][name] = sha256_file(output/name)
        write_json(output/'manifest.json', manifest)
        write_json(output/'audit.json', audit(output))
        from .e4_report import report
        report(output)
        for name in ('audit.json', 'report.md', 'cases.md'):
            manifest['artifact_hashes'][name] = sha256_file(output/name)
        manifest['status'] = 'COMPLETE'
        manifest.pop('error', None)
        write_json(output/'manifest.json', manifest)
        print('COMPLETE E4: exhaustive coverage, derived results and parent preservation audited', flush=True)
    except Exception as error:
        manifest.update(status='FAILED', error=str(error))
        write_json(output/'manifest.json', manifest)
        raise


def scenario_checks(snapshots, features, backend):
    index = {(r['snapshot_id'], r['memory_id']): r['features'] for r in features}
    expected = {(s['snapshot_id'], m['memory_id']) for s in snapshots for m in s['memories']}
    if set(index) != expected or len(features) != len(expected) or any(set(f) != set(FEATURES) for f in index.values()):
        raise ValueError('Feature coverage or whitelist mismatch')
    rows = []
    for s in snapshots:
        if s['scenario'] == 'old_but_useful':
            support = s['future_queries'][0]['supporting_memory_sets'][0][0]
            oldest = min(s['memories'], key=lambda m: m['event_order'])['memory_id']
            if support != oldest:
                raise ValueError('Old useful support is not oldest')
            rows.append(dict(snapshot_id=s['snapshot_id'], scenario=s['scenario'], support_is_oldest=True))
        if s['scenario'] == 'frequent_but_useless':
            mid = s['diagnostic_metadata']['frequent_memory_id']
            frequency = index[s['snapshot_id'], mid]['retrieval_frequency']
            expected_frequency = s['diagnostic_metadata']['expected_history_count']
            if backend == 'model' and frequency != expected_frequency:
                raise ValueError('Frequent distractor history does not match frozen scenario')
            rows.append(dict(snapshot_id=s['snapshot_id'], scenario=s['scenario'], memory_id=mid,
                             retrieval_frequency=frequency, expected_history_count=expected_frequency))
    return rows


def audit(output):
    manifest = check(output)
    settings = manifest['parameters']
    parent = ROOT/read_json(output/'parent-identity.json')['path']
    parent_audit(parent)
    old = read_json(parent/'dataset.json')
    fresh = build_formal(settings['dataset'], read_json(output/'previous-snapshots.json'))
    snapshots = read_json(output/'dataset.json')
    if snapshots != old+fresh or read_json(output/'past.json') != past_view(snapshots):
        raise ValueError('E4 dataset replay mismatch')
    cohorts = {s['snapshot_id']: 'e3_posthoc' for s in old}
    cohorts.update({s['snapshot_id']: 'e4_independent' for s in fresh})
    if cohorts != read_json(output/'cohorts.json'):
        raise ValueError('E4 cohort mismatch')
    if (records(output/'inherited-responses.jsonl') != records(parent/'responses.jsonl') or
        records(output/'inherited-importance.jsonl') != records(parent/'importance.jsonl')):
        raise ValueError('E4 inherited cache mismatch')
    past, features = read_json(output/'past.json'), read_json(output/'features.json')
    ensure_past(past, features)
    importance = records(output/'inherited-importance.jsonl')+records(output/'importance.jsonl')
    verify_importance(past, importance, manifest['backend'], read_json(output/'strategies.json')['importance']['seed'])
    deployable, predictions = make_deployable(past, features, importance, read_json(output/'similarities.json'),
                                             read_json(output/'predictor.json'), settings)
    deployable = strip_times(deployable)+exact_predicted_plans(past, features, predictions, settings)
    if (not replay_equal(predictions, read_json(output/'predictions.json'))
            or not replay_equal(deployable, read_json(output/'deployable-plans.json'))):
        raise ValueError('E4 past-only selection replay mismatch')
    old_ids = {s['snapshot_id'] for s in old}
    if [r for r in features if r['snapshot_id'] in old_ids] != read_json(parent/'features.json'):
        raise ValueError('E3 historical features changed')
    inherited_plans = [p for p in deployable if p['snapshot_id'] in old_ids and p['candidate'] != EXACT_PREDICTED]
    if inherited_plans != strip_times(read_json(parent/'deployable-plans.json')):
        raise ValueError('E3 deployable selection changed')
    marker = read_json(output/'deployable-freeze.json')
    if marker != dict(plans_sha256=sha256_file(output/'deployable-plans.json'),
                      features_sha256=sha256_file(output/'features.json'), predictor_sha256=sha256_file(output/'predictor.json')):
        raise ValueError('Deployable freeze mismatch')
    if any(r['deployable_sha256'] != marker['plans_sha256'] for r in records(output/'responses.jsonl')):
        raise ValueError('Evaluation is not bound to frozen deployable plans')
    if scenario_checks(snapshots, features, manifest['backend']) != read_json(output/'scenario-checks.json'):
        raise ValueError('Scenario checks mismatch')
    enumeration = enumeration_plans(past, settings['generation_seed'])
    if enumeration != read_json(output/'enumeration-plans.json'):
        raise ValueError('E4 enumeration mismatch')
    responses = records(output/'inherited-responses.jsonl')+records(output/'responses.jsonl')
    verify_responses(enumeration, snapshots, responses, settings)
    result = derive(snapshots, features, predictions, deployable, responses, settings, cohorts)
    for name, value in result.items():
        if not replay_equal(value, read_json(output/(name.replace('_', '-')+'.json'))):
            raise ValueError('E4 derived result mismatch: '+name)
    if any(p['candidate'] != 'full' and p['store_tokens'] > p['budget_tokens'] for p in result['plans']):
        raise ValueError('E4 storage budget exceeded')
    repeated = records(output/'winner-repeats.jsonl')
    stability = replay_winners(result['plans'], responses, repeated, snapshots, settings)
    if stability != read_json(output/'winner-stability.json'):
        raise ValueError('Winner repeat audit mismatch')
    controls = context_plans(snapshots, responses, settings['generation_seed'])
    if controls != read_json(output/'context-plans.json'):
        raise ValueError('Context plans mismatch')
    cr = records(output/'context-controls.jsonl')
    verify_controls(controls, cr, snapshots, settings)
    if any(r['backend'] != manifest['backend'] or r['split'] != 'test' for r in responses+repeated+cr):
        raise ValueError('E4 response backend/split mismatch')
    if limit(output, settings) != read_json(output/'cost-report.json'):
        raise ValueError('E4 cost replay mismatch')
    return dict(passed=True, enumeration_complete=True, response_count=len(responses),
                subset_count=len(result['subset_scores']), interaction_count=len(result['interactions']),
                tie_ranges_recomputed=True, cohort_statistics_recomputed=True, labels_scores_recomputed=True,
                past_only_plans_replayed=True, parent_unchanged=True, context_controls_verified=len(cr),
                winner_repeat_changes=len(stability['changed_conditions']),
                model_evidence=manifest['backend'] == 'model')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'audit'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--parent', type=Path, default=HERE/'results/e3-formal-model')
    parser.add_argument('--backend', choices=['test', 'model'], default='model')
    parser.add_argument('--model-config', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args)
    elif args.action == 'run':
        execute(args)
    else:
        print(audit(args.output))
