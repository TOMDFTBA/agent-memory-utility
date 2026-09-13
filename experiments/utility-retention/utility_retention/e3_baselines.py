"""Versioned baseline supplementation; preserves frozen E1/E2 artifacts."""
import argparse
import math
import shutil
import time
from collections import Counter
from pathlib import Path
from statistics import mean

from longmem.config import load_config
from longmem.provenance import source_matches
from longmem.experiment_contracts import SCHEMA_VERSION
from longmem.experiment_io import (append_jsonl, read_json, read_jsonl, runtime_metadata,
                                   sha256_file, source_hashes, write_json)
from .baselines import dedup_select, importance_prompt, parse_importance, similarity_table
from .e2 import audit as audit_e2, expected_conditions, verify_responses
from .e2_metrics import paired, summarize
from .engine import Engine, score, serialize
from .policies import select
from .runner import HERE, ROOT, model_identity


def prepare(args):
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Use a new empty output directory')
    audit_e2(args.e2)
    parent = read_json(args.e2/'manifest.json')
    frozen = read_json(args.e2/'frozen-predictor.json')
    if parent['status'] != 'COMPLETE' or sha256_file(args.e2/'frozen-predictor.json') != parent['frozen_predictor_sha256']:
        raise ValueError('E2 not complete/frozen')
    settings = read_json(args.config)
    for name in ('budget_ratios', 'selection_budget_ratios', 'read_budget', 'top_k', 'generation_seed', 'random_seeds'):
        if settings[name] != parent['parameters'][name]:
            raise ValueError('System/budget mismatch with E2')
    snapshots = read_json(args.e2/'validation-snapshots.json')
    past = [dict(snapshot_id=s['snapshot_id'], trajectory_id=s['trajectory_id'],
                 memories=[{k: m[k] for k in ('memory_id', 'content', 'event_order')} for m in s['memories']])
            for s in snapshots]
    sources = list((HERE/'utility_retention').glob('*.py')) + [HERE/'e3_baselines.py'] + list((ROOT/'src/longmem').glob('*.py'))
    manifest = dict(schema_version=SCHEMA_VERSION, experiment_id='utility-retention-v0.2-e3-baselines-development',
                    status='PREPARED', backend=args.backend, parameters=settings,
                    protocol_sha256=sha256_file(args.protocol), source_hashes=source_hashes(sources, root=ROOT),
                    model=parent['model'] if args.backend == 'model' else None,
                    parent_hashes={p.name: sha256_file(p) for p in args.e2.iterdir() if p.is_file()},
                    runtime=runtime_metadata())
    args.output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.protocol, args.output/'protocol.md')
    write_json(args.output/'past.json', past)
    write_json(args.output/'settings.json', settings)
    write_json(args.output/'predictor.json', frozen)
    # Copy only historical features from handoff; no values accessible to baseline scorers.
    features = [{k: r[k] for k in ('snapshot_id', 'trajectory_id', 'memory_id', 'features')}
                for r in read_json(args.e2/'validation.json')]
    write_json(args.output/'features.json', features)
    for src in sources:
        dest = args.output/'source-snapshot'/src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    manifest['input_hashes'] = {p.name: sha256_file(p) for p in args.output.iterdir() if p.is_file()}
    write_json(args.output/'manifest.json', manifest)
    print('PREPARED: importance and dedup development, frozen E2 predictor preserved', flush=True)


def check(output, e2):
    manifest = read_json(output/'manifest.json')
    for name, digest in manifest['input_hashes'].items():
        if sha256_file(output/name) != digest:
            raise ValueError('Input identity mismatch: '+name)
    for name, digest in manifest['parent_hashes'].items():
        if sha256_file(e2/name) != digest:
            raise ValueError('Parent E2 changed: '+name)
    for name, digest in manifest['source_hashes'].items():
        if not source_matches(ROOT, name, digest) or sha256_file(output/'source-snapshot'/name) != digest:
            raise ValueError('Source identity mismatch')
    return manifest


def importance_index(past):
    return {(s['snapshot_id'], m['memory_id']): m for s in past for m in s['memories']}


def verify_importance(past, rows, backend, seed, complete=True):
    expected = importance_index(past)
    keys = [(r['snapshot_id'], r['memory_id']) for r in rows]
    if len(keys) != len(set(keys)) or not set(keys) <= set(expected) or (complete and set(keys) != set(expected)):
        raise ValueError('Missing/duplicate/unexpected importance output')
    for r in rows:
        m = expected[(r['snapshot_id'], r['memory_id'])]
        if (r['prompt'] != importance_prompt(m['content']) or r['backend'] != backend or r['seed'] != seed
                or r['parsed'] != parse_importance(r['generated_answer']) or r['status'] != 'OK'):
            raise ValueError('Importance replay mismatch')
        if not math.isfinite(r['duration_seconds']) or r['duration_seconds'] < 0:
            raise ValueError('Invalid importance cost')


def plans_from_past(past, features, importance, similarities, settings):
    costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in features}
    scores = {(r['snapshot_id'], r['memory_id']): r['parsed']['score'] for r in importance}
    expected = set(importance_index(past))
    if set(costs) != expected or set(scores) != expected or set(similarities) != {s['snapshot_id'] for s in past}:
        raise ValueError('Historical input join mismatch')
    plans = []
    for s in past:
        sid = s['snapshot_id']
        cs = {m['memory_id']: costs[(sid, m['memory_id'])] for m in s['memories']}
        for ratio in settings['budget_ratios']:
            budget = math.floor(sum(cs.values()) * ratio)
            start = time.perf_counter()
            ids = sorted(select(cs, {mid: scores[(sid, mid)] for mid in cs}, budget))
            plans.append(dict(snapshot_id=sid, candidate='importance', selection_seed=None,
                              budget_ratio=ratio, budget_tokens=budget, storage_ids=ids,
                              store_tokens=sum(cs[mid] for mid in ids), seed=settings['generation_seed'],
                              selection_seconds=time.perf_counter()-start))
            for threshold in settings['dedup_thresholds']:
                start = time.perf_counter()
                result = dedup_select(s['memories'], cs, similarities[sid], threshold, budget)
                ids = result['storage_ids']
                plans.append(dict(snapshot_id=sid, candidate=f'semantic_dedup-t{threshold:g}', selection_seed=None,
                                  budget_ratio=ratio, budget_tokens=budget, store_tokens=sum(cs[mid] for mid in ids),
                                  seed=settings['generation_seed'], **result, selection_seconds=time.perf_counter()-start))
    return plans


def derive(output, e2, plans, responses, snapshots):
    settings = read_json(output/'settings.json')
    base = read_json(e2/'summary.json')
    # E2 summary is independently recomputed by audit_e2, with all source/input hashes checked.
    main = read_json(output/'predictor.json')['candidate']
    names = {main: 'utility_aware', 'recency': 'recency', 'retrieval_frequency': 'retrieval_frequency',
             'random': 'random', 'hindsight_loo': 'hindsight_loo', 'full': 'full', 'no_memory': 'no_memory'}
    new = summarize(plans, responses, snapshots, read_json(e2/'validation.json'))
    combined = {}
    for key in ('aggregates', 'per_trajectory'):
        combined[key] = [dict(r, candidate=names[r['candidate']], result_source='frozen-e2') for r in base[key] if r['candidate'] in names]
        combined[key] += [dict(r, result_source='baseline-supplement') for r in new[key]]
    candidates = {r['candidate'] for r in combined['aggregates']}
    scores = {name: mean(r['metrics']['answer.exact_match'] for r in combined['aggregates']
                         if r['candidate'] == name and r['budget_ratio'] in settings['selection_budget_ratios']) for name in candidates}
    threshold = max(settings['dedup_thresholds'], key=lambda t: (scores[f'semantic_dedup-t{t:g}'], t))
    dedup_name = f'semantic_dedup-t{threshold:g}'
    strongest = min(('recency', 'retrieval_frequency', 'importance', dedup_name), key=lambda name: (-scores[name], name))
    importance = read_jsonl(output/'importance.jsonl')
    valid_fraction = mean(r['parsed']['valid'] for r in importance)
    selection = dict(dedup_threshold=threshold, dedup_candidate=dedup_name,
                     strongest_heuristic='semantic_dedup' if strongest == dedup_name else strongest,
                     strongest_heuristic_candidate=strongest, selection_em=scores,
                     importance_valid_fraction=valid_fraction,
                     importance_score_histogram=dict(Counter(str(r['parsed']['score']) for r in importance)),
                     importance_valid=valid_fraction >= settings['importance_minimum_valid_fraction'],
                     main_predictor=main, model_refit=False, test_evaluated=False)
    combined['paired_differences'] = [paired(combined, 'utility_aware', baseline, ratio,
                                           settings['bootstrap_seed'], settings['bootstrap_repeats'])
                                     for baseline in ('recency', 'retrieval_frequency', 'importance', dedup_name)
                                     for ratio in settings['budget_ratios']]
    return combined, selection


def execute(args):
    manifest = check(args.output, args.e2)
    if args.backend != manifest['backend']:
        raise ValueError('Backend mismatch')
    if manifest['status'] == 'COMPLETE':
        print(audit(args.output, args.e2))
        return
    settings = manifest['parameters']
    config = load_config(args.model_config or (ROOT/'configs/test.yaml' if args.backend == 'test' else None))
    if args.backend == 'test':
        config['embedding'] = {'backend': 'hash-test'}
        config['generation'] = {'backend': 'evidence-test'}
    identity = model_identity(config, args.backend)
    if args.backend == 'model' and identity != manifest['model']:
        raise ValueError('E1/E2 model identity differs')
    if manifest['model'] is not None and identity != manifest['model']:
        raise ValueError('Resume model identity differs')
    manifest.update(model=identity, status='RUNNING', runtime=runtime_metadata())
    write_json(args.output/'manifest.json', manifest)
    past = read_json(args.output/'past.json')
    feature_rows = read_json(args.output/'features.json')
    ipath, rpath = args.output/'importance.jsonl', args.output/'responses.jsonl'
    importance = read_jsonl(ipath) if ipath.exists() else []
    responses = read_jsonl(rpath) if rpath.exists() else []
    verify_importance(past, importance, args.backend, settings['importance_seed'], False)
    try:
        engine = Engine(config, args.backend, settings['read_budget'], settings['top_k'])
        spent = sum(r['duration_seconds'] for r in importance+responses)
        expected = importance_index(past)
        if len(expected) > settings['max_importance_generations']:
            raise ValueError('Importance generation ceiling')
        done = {(r['snapshot_id'], r['memory_id']) for r in importance}
        for (sid, mid), m in sorted(expected.items()):
            if (sid, mid) in done:
                continue
            if spent >= settings['max_duration_seconds']:
                raise RuntimeError('Cumulative runtime ceiling')
            start = time.perf_counter()
            prompt = importance_prompt(m['content'])
            if args.backend == 'model':
                import torch
                torch.manual_seed(settings['importance_seed'])
                answer = engine.generator.generate(prompt, [])
            else:
                answer = '3'  # Explicit test fixture, not a semantic importance estimate.
            row = dict(snapshot_id=sid, memory_id=mid, prompt=prompt, generated_answer=answer,
                       parsed=parse_importance(answer), backend=args.backend, seed=settings['importance_seed'],
                       status='OK', input_tokens=engine.tokens(prompt), output_tokens=engine.tokens(answer),
                       duration_seconds=time.perf_counter()-start)
            append_jsonl(ipath, row)
            importance.append(row)
            spent += row['duration_seconds']
            if len(importance) % 12 == 0:
                print(f'importance {len(importance)}/{len(expected)}; valid={sum(r["parsed"]["valid"] for r in importance)}', flush=True)
        verify_importance(past, importance, args.backend, settings['importance_seed'])
        simpath = args.output/'similarities.json'
        if simpath.exists():
            similarities = read_json(simpath)
            if manifest.get('similarities_sha256') != sha256_file(simpath):
                raise ValueError('Similarity cache identity mismatch')
        else:
            start = time.perf_counter()
            similarities = {s['snapshot_id']: similarity_table(s['memories'], engine.embedder) for s in past}
            manifest['similarity_seconds'] = time.perf_counter()-start
            write_json(simpath, similarities)
            manifest['similarities_sha256'] = sha256_file(simpath)
            write_json(args.output/'manifest.json', manifest)
        plans = plans_from_past(past, feature_rows, importance, similarities, settings)
        planpath = args.output/'plans.json'
        if planpath.exists():
            saved = read_json(planpath)
            if strip_times(saved) != strip_times(plans):
                raise ValueError('Frozen plans changed on resume')
            plans = saved
        else:
            write_json(planpath, plans)
        # Only evaluation gets future queries and annotations; baseline functions received a past-only view.
        snapshots = read_json(args.e2/'validation-snapshots.json')
        write_json(args.output/'validation-snapshots.json', snapshots)
        verify_responses(plans, snapshots, responses, settings, False)
        expected_keys = expected_conditions(plans, snapshots)
        if len(expected_keys) > settings['max_generations']:
            raise ValueError('Answer generation ceiling')
        done = {(r['snapshot_id'], tuple(r['storage_ids']), r['query_id'], r['seed']) for r in responses}
        data = {s['snapshot_id']: s for s in snapshots}
        for sid, ids, qid, seed in sorted(expected_keys):
            if (sid, ids, qid, seed) in done:
                continue
            if spent >= settings['max_duration_seconds']:
                raise RuntimeError('Cumulative runtime ceiling')
            s = data[sid]
            q = next(q for q in s['future_queries'] if q['query_id'] == qid)
            memories = {m['memory_id']: m for m in s['memories']}
            start = time.perf_counter()
            context, ranking = engine.retrieve([memories[mid] for mid in ids], q['text'])
            generated = engine.answer(q['text'], context, seed)
            r = dict(snapshot_id=sid, trajectory_id=s['trajectory_id'], split='validation', query_id=qid,
                     seed=seed, storage_ids=list(ids), context=context, ranking=ranking, query=q['text'],
                     gold_answer=q['gold_answer'], backend=args.backend, status='OK', **generated,
                     metrics=score(generated['generated_answer'], q['gold_answer']),
                     duration_seconds=time.perf_counter()-start)
            append_jsonl(rpath, r)
            responses.append(r)
            spent += r['duration_seconds']
            if len(responses) % 25 == 0:
                print(f'answers {len(responses)}/{len(expected_keys)}; cumulative {spent:.1f}s', flush=True)
        verify_responses(plans, snapshots, responses, settings)
        for r in importance+responses:
            if r['input_tokens'] != engine.tokens(r['prompt']) or r['output_tokens'] != engine.tokens(r['generated_answer']):
                raise ValueError('Prompt/output token cost mismatch')
        for r in responses:
            if r['memory_tokens'] != engine.tokens('\n'.join(serialize(m) for m in r['context'])):
                raise ValueError('Read token cost mismatch')
        if args.backend == 'model':
            costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in feature_rows}
            for s in past:
                for m in s['memories']:
                    if costs[(s['snapshot_id'], m['memory_id'])] != engine.tokens(serialize(m)):
                        raise ValueError('Storage token cost differs from E2')
        summary, selection = derive(args.output, args.e2, plans, responses, snapshots)
        write_json(args.output/'summary.json', summary)
        write_json(args.output/'selection.json', selection)
        ready = args.backend == 'model' and selection['importance_valid']
        freeze = dict(status='FROZEN' if ready else 'DEVELOPMENT_ONLY',
                      predictor_sha256=sha256_file(args.output/'predictor.json'),
                      importance=dict(prompt=importance_prompt('{memory_content}'), parse_rule='single digit 1-5; optional .0/punctuation',
                                      invalid_fallback=3, minimum_valid_fraction=settings['importance_minimum_valid_fraction'],
                                      seed=settings['importance_seed']),
                      semantic_dedup=dict(threshold=selection['dedup_threshold'], representatives='newest-first greedy',
                                          fill='recency over representatives only'),
                      strongest_heuristic=selection['strongest_heuristic'],
                      budgets=settings['budget_ratios'], selection_budgets=settings['selection_budget_ratios'],
                      random_seeds=settings['random_seeds'], generation_seed=settings['generation_seed'],
                      read_budget=settings['read_budget'], top_k=settings['top_k'], model=manifest['model'],
                      source_hashes=manifest['source_hashes'], protocol_sha256=manifest['protocol_sha256'],
                      selection_sha256=sha256_file(args.output/'selection.json'),
                      responses_sha256=sha256_file(rpath), importance_sha256=sha256_file(ipath))
        write_json(args.output/'frozen-strategies.json', freeze)
        manifest.update(token_costs_recomputed=True, ready_for_e3=ready, importance_count=len(importance),
                        response_count=len(responses), cumulative_seconds=spent,
                        importance_seconds=sum(r['duration_seconds'] for r in importance),
                        answer_seconds=sum(r['duration_seconds'] for r in responses),
                        status='VERIFYING')
        write_json(args.output/'manifest.json', manifest)
        report(args.output, summary, selection, manifest)
        artifact_names = ['importance.jsonl', 'similarities.json', 'plans.json', 'validation-snapshots.json',
                          'responses.jsonl', 'summary.json', 'selection.json', 'frozen-strategies.json', 'report.md']
        manifest['result_hashes'] = {name: sha256_file(args.output/name) for name in artifact_names}
        write_json(args.output/'manifest.json', manifest)
        write_json(args.output/'audit.json', audit(args.output, args.e2))
        manifest['status'] = 'COMPLETE'
        write_json(args.output/'manifest.json', manifest)
        print(f'COMPLETE: ready_for_e3={ready}; dedup={selection["dedup_threshold"]}; strongest={selection["strongest_heuristic"]}', flush=True)
    except Exception as error:
        manifest.update(status='FAILED', error_type=type(error).__name__)
        write_json(args.output/'manifest.json', manifest)
        raise


def strip_times(rows):
    return [{k: v for k, v in r.items() if k != 'selection_seconds'} for r in rows]


def audit(output, e2):
    manifest = check(output, e2)
    audit_e2(e2)
    for name, digest in manifest.get('result_hashes', {}).items():
        if sha256_file(output/name) != digest:
            raise ValueError('Result identity mismatch: '+name)
    settings = read_json(output/'settings.json')
    past, features = read_json(output/'past.json'), read_json(output/'features.json')
    importance = read_jsonl(output/'importance.jsonl')
    verify_importance(past, importance, manifest['backend'], settings['importance_seed'])
    similarities = read_json(output/'similarities.json')
    if sha256_file(output/'similarities.json') != manifest['similarities_sha256']:
        raise ValueError('Similarity matrix changed')
    plans = plans_from_past(past, features, importance, similarities, settings)
    saved = read_json(output/'plans.json')
    if strip_times(plans) != strip_times(saved) or any(p['store_tokens'] > p['budget_tokens'] for p in saved):
        raise ValueError('Budget/selection replay mismatch')
    snapshots = read_json(output/'validation-snapshots.json')
    if snapshots != read_json(e2/'validation-snapshots.json') or any(s['split'] != 'validation' for s in snapshots):
        raise ValueError('Validation task identity mismatch')
    responses = read_jsonl(output/'responses.jsonl')
    verify_responses(saved, snapshots, responses, settings)
    if any(r['backend'] != manifest['backend'] for r in responses):
        raise ValueError('Response backend mismatch')
    summary, selection = derive(output, e2, saved, responses, snapshots)
    if summary != read_json(output/'summary.json') or selection != read_json(output/'selection.json'):
        raise ValueError('Metrics/threshold selection replay mismatch')
    frozen = read_json(output/'frozen-strategies.json')
    if (frozen['semantic_dedup']['threshold'] != selection['dedup_threshold']
            or frozen['strongest_heuristic'] != selection['strongest_heuristic']
            or frozen['predictor_sha256'] != sha256_file(output/'predictor.json')
            or frozen['selection_sha256'] != sha256_file(output/'selection.json')
            or frozen['responses_sha256'] != sha256_file(output/'responses.jsonl')
            or frozen['importance_sha256'] != sha256_file(output/'importance.jsonl')):
        raise ValueError('Frozen strategy mismatch')
    return dict(passed=True, importance_count=len(importance), response_count=len(responses),
                importance_reparsed=True, selections_replayed=True, scores_recomputed=True,
                e2_reaudited=True, threshold_selection_replayed=True, budgets_verified=True,
                test_evaluated=False, source_hashes=manifest['source_hashes'])


def report(output, summary, selection, manifest):
    names = ['utility_aware', 'recency', 'retrieval_frequency', 'importance', selection['dedup_candidate'],
             'random', 'hindsight_loo', 'full', 'no_memory']
    table = {(r['candidate'], r['budget_ratio']): r for r in summary['aggregates']}
    ratios = manifest['parameters']['budget_ratios']
    lines = ['# E3 基线补齐：验证开发报告', '',
             f"后端：{manifest['backend']}；12条既有验证轨迹，正式测试未执行。",
             f"新增importance生成{manifest['importance_count']}次，回答生成{manifest['response_count']}次；累计逐条{manifest['cumulative_seconds']:.1f}秒。",
             f"importance有效率：{selection['importance_valid_fraction']:.1%}；分数分布：{selection['importance_score_histogram']}。",
             f"选定dedup阈值：{selection['dedup_threshold']}；补齐后的最强启发式：{selection['strongest_heuristic']}。", '',
             '| 策略 | 10% EM | 25% EM | 50% EM | 75% EM |', '|---|---:|---:|---:|---:|']
    for name in names:
        lines.append('| '+name+' | '+' | '.join(f"{table[(name, r)]['metrics']['answer.exact_match']:.3f}" for r in ratios)+' |')
    lines += ['', '## 去重阈值开发', '', '| 阈值 | 三预算平均EM |', '|---|---:|']
    for threshold in manifest['parameters']['dedup_thresholds']:
        lines.append(f"| {threshold} | {selection['selection_em'][f'semantic_dedup-t{threshold:g}']:.3f} |")
    lines += ['', '## 主方法相对新增基线的配对差异', '', '| 基线 | 预算 | EM差异 | 轨迹95%区间 |', '|---|---:|---:|---|']
    for r in summary['paired_differences']:
        if r['baseline'] in ('importance', selection['dedup_candidate']):
            lines.append(f"| {r['baseline']} | {r['budget_ratio']:.0%} | {r['metrics']['answer.paired_em_difference']:+.3f} | {r['trajectory_bootstrap_95_ci']} |")
    lines += ['', '## 成本与边界', '',
              f"importance评分耗时{manifest['importance_seconds']:.1f}秒；回答推理{manifest['answer_seconds']:.1f}秒；embedding相似度计算{manifest['similarity_seconds']:.1f}秒。不含模型摘要等前置成本。",
              'importance与三个dedup候选为本轮真实推理；其余比较行复用已独立重算的冻结E2结果，来源明确标记。未将其计为新增推理。',
              '验证集已用于E2选模，再用于本轮阈值和最强启发式选择，置信区间仅为描述，不作正式显著性结论。',
              '主predictor保持full-a10及原六特征；importance作为基线，不作为新增预测特征。当前provenance没有独立可靠语义属性，首版不加入。',
              '语义相似不保证答案等价；dedup不读取canonical/support标注。importance并列和无效输出全部保留，不根据答案修补分数。',
              'E3正式测试应使用策略冻结后生成的新轨迹；现有E1测试已披露汇总，不能称全新盲测。', '']
    (output/'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'audit'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--e2', type=Path, default=HERE/'results/e2-development-model')
    parser.add_argument('--config', type=Path, default=HERE/'configs/e3-baselines-development.json')
    parser.add_argument('--protocol', type=Path, default=HERE/'protocol-e3-baselines-development.md')
    parser.add_argument('--model-config', type=Path)
    parser.add_argument('--backend', choices=['model', 'test'], default='model')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args)
    elif args.action == 'run':
        execute(args)
    else:
        print(audit(args.output, args.e2))


if __name__ == '__main__':
    main()
