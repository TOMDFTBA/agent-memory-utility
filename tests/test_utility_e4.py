"""E4 regression: exhaustive oracles, tied objectives, interventions, resume and audit."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).parents[1]/'experiments/utility-retention'
sys.path.insert(0, str(HERE))
from longmem.experiment_io import read_json, read_jsonl, write_json, sha256_file  # noqa: E402
from utility_retention import e4, e3_formal  # noqa: E402
from utility_retention.e4_analysis import subsets, optimum, exact_predicted_plans, enumeration_plans  # noqa: E402


def test_zero_loo_ties_preserve_good_and_bad_sets():
    feasible = [dict(storage_ids=a, store_tokens=len(a)) for a in subsets(['a', 'b'])]
    chosen, tied, top = optimum(feasible, {'a': 0, 'b': 0})
    assert chosen['storage_ids'] == [] and top == 0
    assert len(tied) == 4
    assert ['a'] in [r['storage_ids'] for r in tied]
    # Shared deletion labels on a redundant pair are zero although either singleton works.
    f = {(): 0, ('a',): 1, ('b',): 1, ('a', 'b'): 1}
    assert f['a', 'b']-f['a',]-f['b',]+f[()] == -1
    assert f['a', 'b']-f['a',] == f['a', 'b']-f['b',] == 0


def test_exact_selection_solves_token_packing_and_zero_negative_scores():
    feasible = [dict(storage_ids=a, store_tokens=sum({'a': 6, 'b': 5, 'c': 5}[m] for m in a))
                for a in subsets(['a', 'b', 'c'])]
    chosen, _, top = optimum([r for r in feasible if r['store_tokens'] <= 10], {'a': 8, 'b': 7, 'c': 7})
    assert chosen['storage_ids'] == ['b', 'c'] and top == 14
    chosen, _, _ = optimum(feasible, {'a': -1, 'b': 0, 'c': -2})
    assert chosen['storage_ids'] == []


def test_enumeration_coverage_and_past_only_exact_choice():
    past = [{'snapshot_id': 's', 'memories': [{'memory_id': 'a'}, {'memory_id': 'b'}]}]
    features = [dict(snapshot_id='s', memory_id=m, features={'memory_tokens': 5}) for m in ('a', 'b')]
    plans = enumeration_plans(past, 1)
    assert len(plans) == 4 and all('candidate' not in p for p in plans)
    settings = {'budget_ratios': [.5], 'generation_seed': 1}
    selection = exact_predicted_plans(past, features, [0, 1], settings)
    assert selection[0]['storage_ids'] == ['b']
    assert selection[0]['store_tokens'] <= selection[0]['budget_tokens']


def test_e4_limits_include_final_call_and_repeats(tmp_path):
    settings = read_json(HERE/'configs/e4-diagnostic.json')
    (tmp_path/'winner-repeats.jsonl').write_text('{"duration_seconds":7200.01}\n')
    with pytest.raises(RuntimeError, match='ceiling'):
        e4.limit(tmp_path, settings)


def test_e4_complete_resume_and_corruption(tmp_path, monkeypatch):
    parent = SimpleNamespace(output=tmp_path/'parent', backend='test', model_config=None)
    e3_formal.prepare(parent)
    e3_formal.execute(parent)
    before = e4.parent_identity(parent.output)
    args = SimpleNamespace(output=tmp_path/'e4', parent=parent.output, backend='test', model_config=None)
    e4.prepare(args)
    original = e4.derive
    calls = 0
    def interrupt_once(*a, **kw):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError('interrupted after enumeration')
        return original(*a, **kw)
    monkeypatch.setattr(e4, 'derive', interrupt_once)
    with pytest.raises(RuntimeError, match='interrupted'):
        e4.execute(args)
    count = len(read_jsonl(args.output/'responses.jsonl'))
    e4.execute(args)
    assert len(read_jsonl(args.output/'responses.jsonl')) == count
    assert e4.audit(args.output)['passed']
    assert read_json(args.output/'manifest.json')['status'] == 'COMPLETE'
    assert e4.parent_identity(parent.output) == before
    saved = e4.parent_identity(args.output)
    e4.execute(args)
    assert e4.parent_identity(args.output) == saved
    assert e4.audit(args.output)['response_count'] == 1536
    # No pooled cohorts, and full enumeration remains checked even with a replaced hash.
    assert set(read_json(args.output/'cohort-summaries.json')) == {'e3_posthoc', 'e4_independent'}
    path = args.output/'responses.jsonl'
    content = path.read_bytes()
    path.write_bytes(b'\n'.join(content.splitlines()[:-1])+b'\n')
    manifest = read_json(args.output/'manifest.json')
    saved_manifest = copy.deepcopy(manifest)
    manifest['artifact_hashes']['responses.jsonl'] = sha256_file(path)
    write_json(args.output/'manifest.json', manifest)
    with pytest.raises(ValueError, match='Missing'):
        e4.audit(args.output)
    path.write_bytes(content)
    write_json(args.output/'manifest.json', saved_manifest)
    assert e4.audit(args.output)['passed']
    ties_path = args.output/'ties.json'
    saved_ties = read_json(ties_path)
    broken = copy.deepcopy(saved_ties)
    broken[0]['metrics']['diagnostic.tie_em_max'] = 123
    write_json(ties_path, broken)
    manifest = read_json(args.output/'manifest.json')
    manifest['artifact_hashes']['ties.json'] = sha256_file(ties_path)
    write_json(args.output/'manifest.json', manifest)
    with pytest.raises(ValueError, match='derived'):
        e4.audit(args.output)


@pytest.mark.parametrize('family, expected_interaction', [('redundancy', -1), ('complementarity', 1)])
def test_actual_derive_interaction_and_oracle_on_known_set_function(family, expected_interaction):
    from utility_retention.e4_analysis import derive
    memories = [{'memory_id': m, 'content': m} for m in ('a', 'b')]
    supports = [['a'], ['b']] if family == 'redundancy' else [['a', 'b']]
    snapshot = dict(snapshot_id='s', trajectory_id='t', scenario=family, memories=memories,
                    future_queries=[dict(query_id='q', supporting_memory_sets=supports)])
    features = [dict(snapshot_id='s', memory_id=m, features={'memory_tokens': 1}) for m in ('a', 'b')]
    predictions = [1, 1]
    settings = dict(budget_ratios=[.5, 1.0], primary_budget_ratios=[.5, 1.0], generation_seed=1,
                    bootstrap_seed=1, bootstrap_repeats=10)
    past = [dict(snapshot_id='s', memories=memories)]
    plans = exact_predicted_plans(past, features, predictions, settings)
    plans += [dict(p, candidate='utility_aware') for p in plans]
    responses = []
    for ids in subsets(['a', 'b']):
        value = int(bool(ids)) if family == 'redundancy' else int(len(ids) == 2)
        responses.append(dict(snapshot_id='s', storage_ids=ids, query_id='q', seed=1,
                              context=[m for m in memories if m['memory_id'] in ids], memory_tokens=len(ids),
                              metrics={'answer.exact_match': value, 'answer.token_f1': value}))
    result = derive([snapshot], features, predictions, plans, responses, settings, {'s': 'fixture'})
    assert result['interactions'][0]['metrics']['diagnostic.interaction'] == expected_interaction
    oracle = [p for p in result['plans'] if p['candidate'] == 'best_subset']
    assert oracle[0]['storage_ids'] == (['a'] if family == 'redundancy' else [])
    assert oracle[1]['storage_ids'] == (['a'] if family == 'redundancy' else ['a', 'b'])
    if family == 'redundancy':
        tie = next(r for r in result['ties'] if r['candidate'] == 'hindsight_loo_sum_optimal')
        assert tie['metrics']['diagnostic.tie_em_min'] == 0
        assert tie['metrics']['diagnostic.tie_em_max'] == 1
        assert tie['selected_ids'] == []
