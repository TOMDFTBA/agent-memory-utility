"""Independent E3 supplemental lifecycle, preserving all frozen formal artifacts."""
import argparse
import math
import shutil
import time
from pathlib import Path
from statistics import median

import numpy as np

from longmem.config import load_config
from longmem.provenance import source_matches
from longmem.experiment_contracts import SCHEMA_VERSION
from longmem.experiment_io import read_json, read_jsonl, runtime_metadata, sha256_file, source_hashes, write_json
from .e3_formal import audit as formal_audit
from .e3_supplement_analysis import analyze, case_list, gain_distribution
from .e3_supplement_replay import (ATOL, RTOL, benchmark, cached_policy, compare, replay_history,
                                   replay_other_tokens, replay_retrieval)
from .e3_baselines import strip_times
from .e2_metrics import response_key
from .engine import Engine
from .runner import HERE, ROOT, model_identity


def prepare(args):
    formal_audit(args.parent)
    parent_manifest = read_json(args.parent/'manifest.json')
    if parent_manifest['status'] != 'COMPLETE':
        raise ValueError('Formal parent must be COMPLETE')
    if args.output.exists() and any(args.output.iterdir()):
        raise ValueError('Use a new empty supplement directory')
    args.output.mkdir(parents=True, exist_ok=True)
    sources = list((HERE/'utility_retention').glob('e3_supplement*.py')) + [HERE/'e3_supplement.py']
    for src in sources:
        dest = args.output/'source-snapshot'/src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    shutil.copyfile(HERE/'protocol-e3-supplement.md', args.output/'protocol.md')
    manifest = dict(schema_version=SCHEMA_VERSION, experiment_id='utility-retention-v0.2-e3-supplement',
                    status='PREPARED', backend=parent_manifest['backend'], model=parent_manifest['model'],
                    source_hashes=source_hashes(sources, root=ROOT), runtime=runtime_metadata(),
                    protocol_sha256=sha256_file(args.output/'protocol.md'), artifact_hashes={},
                    parent_hashes={p.name: sha256_file(p) for p in args.parent.iterdir() if p.is_file()},
                    parameters=dict(warmups=3, repetitions=30, absolute_tolerance=ATOL, relative_tolerance=RTOL,
                                    answer_generations=0, importance_generations=0, post_test_descriptive=True))
    write_json(args.output/'manifest.json', manifest)
    print('PREPARED: read-only E3 supplement; no text generation', flush=True)


def check(output, parent):
    manifest = read_json(output/'manifest.json')
    if sha256_file(output/'protocol.md') != manifest['protocol_sha256']:
        raise ValueError('Supplement protocol mismatch')
    for name, digest in manifest['parent_hashes'].items():
        if sha256_file(parent/name) != digest:
            raise ValueError('Frozen formal parent changed: '+name)
    for name, digest in manifest['source_hashes'].items():
        if not source_matches(ROOT, name, digest) or sha256_file(output/'source-snapshot'/name) != digest:
            raise ValueError('Supplement source changed: '+name)
    for name, digest in manifest['artifact_hashes'].items():
        if sha256_file(output/name) != digest:
            raise ValueError('Supplement artifact changed: '+name)
    return manifest


def derived(parent):
    plans, responses = read_json(parent/'plans.json'), read_jsonl(parent/'responses.jsonl')
    snapshots, features = read_json(parent/'dataset.json'), read_json(parent/'features.json')
    analysis = analyze(plans, responses, snapshots, features)
    gains = gain_distribution(read_json(parent/'summary.json'), snapshots)
    cases = case_list(analysis, plans, responses, snapshots, features,
                      read_json(parent/'predictions.json'), read_json(parent/'hindsight-labels.json'))
    return {'failure-analysis.json': analysis, 'gain-distribution.json': gains, 'e4-cases.json': cases}


def seal(output, manifest, name, value):
    path = output/name
    if path.exists():
        if read_json(path) != value:
            raise ValueError('Supplement derived data changed: '+name)
    else:
        write_json(path, value)
    manifest['artifact_hashes'][name] = sha256_file(path)
    write_json(output/'manifest.json', manifest)


def execute(args):
    output, parent = args.output, args.parent
    manifest = check(output, parent)
    formal_audit(parent)
    if manifest['status'] == 'COMPLETE':
        print(audit(output, parent))
        return
    manifest.update(status='RUNNING', runtime=runtime_metadata())
    write_json(output/'manifest.json', manifest)
    try:
        for name, value in derived(parent).items():
            seal(output, manifest, name, value)
        config = load_config(args.model_config or (ROOT/'configs/test.yaml' if manifest['backend'] == 'test' else None))
        if manifest['backend'] == 'test':
            config['embedding'] = {'backend': 'hash-test'}
            config['generation'] = {'backend': 'evidence-test'}
        start = time.perf_counter()
        identity = model_identity(config, manifest['backend'])
        identity_seconds = time.perf_counter()-start
        if identity != manifest['model']:
            raise ValueError('Model replay identity differs from formal run')
        settings = read_json(parent/'settings.json')
        start = time.perf_counter()
        engine = Engine(config, manifest['backend'], settings['read_budget'], settings['top_k'])
        setup_seconds = time.perf_counter()-start
        if not (output/'replay-setup.json').exists():
            write_json(output/'replay-setup.json', dict(identity_seconds=identity_seconds, engine_setup_seconds=setup_seconds,
                                                       model=identity, backend=manifest['backend']))
        replay_history(engine, parent, output)
        replay_retrieval(engine, parent, output)
        replay_other_tokens(engine, parent, output)
        if not (output/'microbenchmark.json').exists():
            benchmark(parent, output, manifest['parameters']['warmups'], manifest['parameters']['repetitions'])
        for name in ('replay-setup.json', 'history-replay.json', 'retrieval-replay.jsonl', 'token-replay.json', 'microbenchmark.json'):
            manifest['artifact_hashes'][name] = sha256_file(output/name)
        manifest['status'] = 'VERIFYING'
        write_json(output/'manifest.json', manifest)
        write_json(output/'audit.json', audit(output, parent))
        report(output, parent)
        for name in ('audit.json', 'report.md', 'e4-cases.md', 'cost-accounting.json'):
            manifest['artifact_hashes'][name] = sha256_file(output/name)
        manifest['status'] = 'COMPLETE'
        write_json(output/'manifest.json', manifest)
        print('COMPLETE: supplemental analysis, retrieval replay and cost benchmark', flush=True)
    except Exception as error:
        manifest.update(status='FAILED', error_type=type(error).__name__, error=str(error))
        write_json(output/'manifest.json', manifest)
        raise


def audit(output, parent):
    manifest = check(output, parent)
    formal = formal_audit(parent)
    for name, value in derived(parent).items():
        if value != read_json(output/name):
            raise ValueError('Supplement analysis replay differs: '+name)
    history = read_json(output/'history-replay.json')
    feature_delta = compare(history['features'], read_json(parent/'features.json'), 'features')
    similarity_delta = compare(history['similarities'], read_json(parent/'similarities.json'), 'similarities')
    prediction_delta = compare(history['predictions'], read_json(parent/'predictions.json'), 'predictions')
    if history['plans'] != strip_times(read_json(parent/'deployable-plans.json')):
        raise ValueError('History-recomputed selection differs')
    for name, delta in [('feature', feature_delta), ('similarity', similarity_delta), ('prediction', prediction_delta)]:
        if history[name+'_max_abs_difference'] != delta:
            raise ValueError('Maximum replay difference mismatch')
    responses = read_jsonl(parent/'responses.jsonl')
    def key(r):
        return response_key(r['snapshot_id'], r['storage_ids'], r['query_id'], r['seed'])
    expected = {key(r): r for r in responses}
    fresh = read_jsonl(output/'retrieval-replay.jsonl')
    if len(fresh) != len(expected) or {key(r) for r in fresh} != set(expected):
        raise ValueError('Incomplete/duplicate retrieval replay')
    max_score_delta = 0.0
    for r in fresh:
        original = expected[key(r)]
        max_score_delta = max(max_score_delta, compare(r['ranking'], original['ranking'], 'ranking'))
        compare(r['context_ids'], [m['memory_id'] for m in original['context']], 'context_ids')
        for k in ('input_tokens', 'output_tokens', 'memory_tokens'):
            compare(r[k], original[k], k)
    tokens = read_json(output/'token-replay.json')
    costs = {(r['snapshot_id'], r['memory_id']): r['features']['memory_tokens'] for r in read_json(parent/'features.json')}
    storage = {(r['snapshot_id'], r['memory_id']): r['store_tokens'] for r in tokens['storage']}
    if len(storage) != len(tokens['storage']) or storage != costs:
        raise ValueError('Storage token replay mismatch')
    original_importance = [{k: r[k] for k in ('snapshot_id', 'memory_id', 'input_tokens', 'output_tokens')}
                           for r in read_jsonl(parent/'importance.jsonl')]
    if tokens['importance'] != original_importance:
        raise ValueError('Importance token replay mismatch')
    micro = read_json(output/'microbenchmark.json')
    if micro['warmups'] != manifest['parameters']['warmups'] or micro['repeats'] != manifest['parameters']['repetitions']:
        raise ValueError('Benchmark protocol mismatch')
    seen = {(r['candidate'], r['repetition']) for r in micro['samples']}
    names = {'utility_aware', 'importance', 'recency', 'retrieval_frequency', 'random', 'semantic_dedup'}
    if len(seen) != len(micro['samples']) or seen != {(n, i) for n in names for i in range(micro['repeats'])}:
        raise ValueError('Benchmark sample coverage mismatch')
    if {r['candidate'] for r in micro['aggregates']} != names or len(micro['aggregates']) != len(names):
        raise ValueError('Benchmark aggregate coverage mismatch')
    times = [r['duration_seconds'] for r in fresh]+[history['history_seconds'], history['similarity_seconds']]
    for r in micro['samples']:
        if r['snapshot_count'] != len(read_json(parent/'past.json')) or r['plan_count'] != (288 if r['candidate'] == 'random' else 96):
            raise ValueError('Benchmark scope mismatch')
        times += [r[k] for k in ('scoring_seconds', 'selection_seconds', 'cached_decision_seconds')]
        if abs(r['cached_decision_seconds']-r['scoring_seconds']-r['selection_seconds']) > 1e-12:
            raise ValueError('Benchmark timing sum mismatch')
    for candidate in sorted(names):
        selected, _ = cached_policy(candidate, read_json(parent/'past.json'), read_json(parent/'features.json'),
                                    read_jsonl(parent/'importance.jsonl'), read_json(parent/'similarities.json'),
                                    read_json(parent/'predictor.json')['model'], read_json(parent/'settings.json'))
        expected_plans = {(p['snapshot_id'], p['budget_ratio'], p['selection_seed'], tuple(p['storage_ids']))
                          for p in read_json(parent/'deployable-plans.json') if p['candidate'] == candidate}
        if len(selected) != len(expected_plans) or set(selected) != expected_plans:
            raise ValueError('Audit cached policy differs from formal')
    for row in micro['aggregates']:
        rs = [r for r in micro['samples'] if r['candidate'] == row['candidate']]
        if row['repetitions'] != micro['repeats'] or row['plan_count'] != rs[0]['plan_count']:
            raise ValueError('Benchmark aggregate scope mismatch')
        for k in ('scoring_seconds', 'selection_seconds', 'cached_decision_seconds'):
            expected_timing = dict(median_seconds=median(r[k] for r in rs),
                                   p95_seconds=float(np.quantile([r[k] for r in rs], .95)))
            if row['timing'][k] != expected_timing:
                raise ValueError('Benchmark summary mismatch')
    setup = read_json(output/'replay-setup.json')
    if setup['model'] != manifest['model'] or setup['backend'] != manifest['backend']:
        raise ValueError('Replay model identity mismatch')
    times += [setup['identity_seconds'], setup['engine_setup_seconds']]
    if any(not math.isfinite(t) or t < 0 for t in times):
        raise ValueError('Invalid cost sample')
    return dict(passed=True, parent_audit_passed=formal['passed'], formal_parent_unchanged=True,
                historical_feature_rows=len(history['features']), similarity_matrices=len(history['similarities']),
                retrieval_conditions=len(fresh), storage_token_records=len(storage), importance_token_records=len(original_importance),
                deployable_plans_replayed=len(history['plans']), feature_max_abs_difference=feature_delta,
                similarity_max_abs_difference=similarity_delta, prediction_max_abs_difference=prediction_delta,
                retrieval_score_max_abs_difference=max_score_delta, context_ids_exact=True, token_counts_exact=True,
                benchmark_samples=len(micro['samples']), descriptive_analysis_replayed=True,
                new_answer_generations=0, new_importance_generations=0, model_evidence=manifest['backend'] == 'model')


def report(output, parent):
    analysis = read_json(output/'failure-analysis.json')
    gains = read_json(output/'gain-distribution.json')
    cases = read_json(output/'e4-cases.json')
    verification = read_json(output/'audit.json')
    micro = read_json(output/'microbenchmark.json')
    history = read_json(output/'history-replay.json')
    original = read_json(parent/'cost-report.json')
    setup = read_json(output/'replay-setup.json')
    cost = dict(original_observed=dict(importance_seconds=original['importance_seconds'],
                                      retrieval_and_generation_seconds=original['answer_seconds'],
                                      combined_history_similarity_seconds=original['history_similarity_seconds'],
                                      selector_regions_seconds_by_candidate=original['selection_seconds_by_candidate']),
                new_replay=dict(identity_seconds=setup['identity_seconds'], setup_seconds=setup['engine_setup_seconds'],
                                history_seconds=history['history_seconds'], similarity_seconds=history['similarity_seconds'],
                                retrieval_seconds=sum(r['duration_seconds'] for r in read_jsonl(output/'retrieval-replay.jsonl'))),
                new_cached_microbenchmark=micro['aggregates'],
                original_scoring_time_missing=True, new_generated_answers=0,
                scope='Original, replay and cached timings are separate; do not sum them as end-to-end latency')
    write_json(output/'cost-accounting.json', cost)
    cn = {'correct': '答对', 'budget_infeasible': '支持集放不下', 'support_not_retained': '支持集未保留',
          'support_not_retrieved': '支持集未读全', 'supported_but_wrong': '读全但答错'}
    lines = ['# E3 补充分析与独立模型重算审计', '',
             '本报告为正式测试后的描述性补充，不改变原主指标、策略、数据或答案。',
             f"模型证据：{verification['model_evidence']}；test后端仅用于工程验证。", '',
             '## 低预算失败位置', '',
             '先判断答案是否正确，再按完整标注支持集的最小成本、存储与上下文归类。冗余支持集按替代方案取最小成本；未保留不等于预测器单独出错。',
             '比例先在轨迹内平均问题和随机seed，再平均轨迹；五类比例合计为1。', '',
             '| 策略 | 预算 | 答对 | 支持集放不下 | 支持集未保留 | 支持集未读全 | 读全但答错 |',
             '|---|---|---:|---:|---:|---:|---:|']
    for r in analysis['aggregates']:
        if r['scenario'] == 'all' and r['budget_ratio'] in (.25, .5):
            lines.append(f"| {r['candidate']} | {r['budget_ratio']:.0%} | "+' | '.join(f"{r['metrics']['diagnostic.'+c+'_rate']:.1%}" for c in cn)+' |')
    lines += ['', '## 预算利用', '', '| 策略 | 预算 | 保留条数 | 利用率 | 剩余tokens | 无单条可容纳 | 空集 |', '|---|---|---:|---:|---:|---:|---:|']
    for r in analysis['aggregates']:
        if r['scenario'] == 'all' and r['candidate'] in ('utility_aware', 'importance', 'hindsight_loo'):
            m = r['metrics']
            lines.append(f"| {r['candidate']} | {r['budget_ratio']:.0%} | {m['retention.record_count']:.2f} | {m['retention.budget_utilization']:.1%} | {m['cost.unused_store_tokens']:.1f} | {m['retention.no_record_fits']:.1%} | {m['retention.empty_rate']:.1%} |")
    lines += ['', '## 相对 importance 的轨迹收益分布', '', '| 预算 | 场景 | 轨迹数 | 胜 | 平 | 负 | 平均EM差异 |', '|---|---|---:|---:|---:|---:|---:|']
    for r in gains['aggregates']:
        o = r['outcomes']
        lines.append(f"| {r['budget_ratio']} | {r['scenario']} | {r['trajectory_count']} | {o['win']} | {o['tie']} | {o['loss']} | {r['metrics']['answer.paired_em_difference']:+.4f} |")
    lines += ['', '## 成本口径与新增微基准', '',
              f"原始importance评分{original['importance_seconds']:.3f}秒；原始检索加生成{original['answer_seconds']:.3f}秒。原始逐题计时不能事后拆成纯检索和纯生成。",
              '旧selection_seconds仅覆盖选择区域，不能当完整决策成本。新微基准计入缓存输入整理、预测/评分和选择；LLM importance评分仍使用单独列出的原始观测成本。',
              f"本次模型重算：历史特征{history['history_seconds']:.3f}秒，相似度{history['similarity_seconds']:.3f}秒；GPU计算边界显式同步。",
              '下表是24轨迹×4预算的整批CPU微基准，3次预热、30次记录。random包含三个seed共288个计划，其余各96个计划；不是单次线上延迟。', '',
              '| 策略 | 评分中位ms | 选择中位ms | 缓存决策中位ms | 缓存决策p95 ms |', '|---|---:|---:|---:|---:|']
    for r in micro['aggregates']:
        t = r['timing']
        lines.append(f"| {r['candidate']} | {1000*t['scoring_seconds']['median_seconds']:.3f} | {1000*t['selection_seconds']['median_seconds']:.3f} | {1000*t['cached_decision_seconds']['median_seconds']:.3f} | {1000*t['cached_decision_seconds']['p95_seconds']:.3f} |")
    lines += ['', 'Dedup代表项构造计入选择阶段；其memory相似度计算单列。Importance评分栏只含缓存输出解析/映射，不含新的LLM推理。Ridge训练成本属于E2，本次未训练。',
              '这些原始、重算和微基准时间不能拼成一次端到端耗时，也不能用于四条memory之外的规模结论。', '',
              '## 强重算审计', '',
              f"通过：{verification['passed']}；历史特征{verification['historical_feature_rows']}行，相似度{verification['similarity_matrices']}组，检索条件{verification['retrieval_conditions']}条，部署计划{verification['deployable_plans_replayed']}条。",
              f"特征/相似度/预测/检索分数最大绝对差异：{verification['feature_max_abs_difference']} / {verification['similarity_max_abs_difference']} / {verification['prediction_max_abs_difference']} / {verification['retrieval_score_max_abs_difference']}。",
              '所有检索排序ID和上下文ID严格一致，所有存储、prompt、输出、上下文token数一致。浮点容差atol=1e-6、rtol=1e-5；计划必须严格相同。',
              '本次不重生成答案或importance评分。轻量audit根据保存的模型重算记录再验算；run负责实际模型重算。原正式审计及所有顶层产物hash再次核验。', '',
              '## E4交接', '',
              f"输出{len(cases['cases'])}个可定位案例，详见e4-cases.md/json。没有出现的类型：{', '.join(cases['absent_case_types']) or '无'}。",
              '案例是事后解释材料，不作为新的盲测数据；E4仍需独立诊断协议、预算子集枚举及LOO加总目标对照。',
              '每场景仅6轨迹、同轨迹两题相关，四类压力场景不代表自然用户分布。支持集标注用于行为归类，不声称揭示模型内部因果机制。', '']
    (output/'report.md').write_text('\n'.join(lines), encoding='utf-8')
    case_lines = ['# E4案例交接：来自E3的事后诊断', '', cases['scope'], '']
    for c in cases['cases']:
        case_lines += [f"## {c['case_id']}：{c['case_type']}", '',
                       f"snapshot={c['snapshot_id']}；query={c['query']['query_id']}；budget={c['budget_ratio']:.0%}。",
                       f"问题：{c['query']['text']}；答案：{c['query']['gold_answer']}；支持集：{c['query']['supporting_memory_sets']}。", '',
                       '| memory_id | tokens | 预测值 | LOO | 内容 |', '|---|---:|---:|---:|---|']
        for m in c['memories']:
            case_lines.append(f"| {m['memory_id']} | {m['token_cost']} | {m['predicted_value']:.4f} | {m['loo_value']:.4f} | {m['content']} |")
        case_lines += ['', '| 策略 | 保留ID | 上下文ID | 实际输出 | EM |', '|---|---|---|---|---:|']
        for p in c['comparisons']:
            answer = p['generated_answer'].replace('\n', ' ').replace('|', '\\|')
            case_lines.append(f"| {p['candidate']} | {p['storage_ids']} | {p['context_ids']} | {answer} | {p['metrics']['answer.exact_match']} |")
        case_lines += ['', '完整response_key、预算、标注和数值见同名JSON；不得将该案例当作独立盲测。', '']
    case_lines += ['未出现的类型：'+', '.join(cases['absent_case_types']), '']
    (output/'e4-cases.md').write_text('\n'.join(case_lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'run', 'audit'])
    parser.add_argument('--parent', type=Path, default=HERE/'results/e3-formal-model')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model-config', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args)
    elif args.action == 'run':
        execute(args)
    else:
        print(audit(args.output, args.parent))
