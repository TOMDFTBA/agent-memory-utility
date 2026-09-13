"""Supplemental E3 audit: annotation semantics, numeric drift, no-generation replay."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).parents[1]/'experiments/utility-retention'
sys.path.insert(0, str(HERE))
from longmem.experiment_io import read_json, write_json  # noqa: E402
from utility_retention import e3_formal, e3_supplement  # noqa: E402
from utility_retention import e3_supplement_replay as replay  # noqa: E402
from utility_retention.e3_supplement_analysis import failure_category, gain_distribution  # noqa: E402


def test_failure_categories_use_alternative_supports_and_exemption():
    costs = {'a': 4, 'b': 5}
    # Redundancy: either one suffices; do not sum both alternatives.
    row = failure_category(0, [['a'], ['b']], costs, 4, [], [])
    assert row['minimum_support_tokens'] == 4 and row['category'] == 'support_not_retained'
    # Complementarity: both must fit.
    assert failure_category(0, [['a', 'b']], costs, 8, ['a'], ['a'])['category'] == 'budget_infeasible'
    assert failure_category(0, [['a']], costs, 4, ['a'], [])['category'] == 'support_not_retrieved'
    assert failure_category(0, [['a']], costs, 4, ['a'], ['a'])['category'] == 'supported_but_wrong'
    assert failure_category(0, [['a']], costs, 0, ['a'], ['a'], exempt=True)['category'] == 'supported_but_wrong'
    correct = failure_category(1, [['a']], costs, 0, [], [])
    assert correct['category'] == 'correct' and correct['correct_without_annotated_support']


def test_replay_tolerance_never_hides_integer_or_context_changes():
    assert replay.compare([.5+1e-7], [.5]) < 1e-6
    for actual, expected in [(100001, 100000), (['b', 'a'], ['a', 'b']), ([float('nan')], [.5]), ([.51], [.5])]:
        with pytest.raises(ValueError):
            replay.compare(actual, expected)


def test_gain_distribution_pairs_and_does_not_expand_samples():
    rows = [dict(candidate=name, trajectory_id=tid, budget_ratio=.5, metrics={'answer.exact_match': value})
            for tid, a, b in [('a', 1, 0), ('b', .5, .5), ('c', 0, 1)]
            for name, value in [('utility_aware', a), ('importance', b)]]
    result = gain_distribution({'per_trajectory': rows, 'primary_per_trajectory': []},
                               [dict(trajectory_id=t, scenario='one') for t in ('a', 'b', 'c')])
    all_rows = next(r for r in result['aggregates'] if r['scenario'] == 'all')
    assert all_rows['trajectory_count'] == 3 and all_rows['outcomes'] == {'win': 1, 'tie': 1, 'loss': 1}
    with pytest.raises(ValueError):
        gain_distribution({'per_trajectory': rows[:-1], 'primary_per_trajectory': []},
                          [dict(trajectory_id=t, scenario='one') for t in ('a', 'b', 'c')])


def test_supplement_resume_no_generation_and_parent_preservation(tmp_path, monkeypatch):
    parent = tmp_path/'formal'
    formal_args = SimpleNamespace(output=parent, backend='test', model_config=None)
    e3_formal.prepare(formal_args)
    e3_formal.execute(formal_args)
    before = {p.name: p.read_bytes() for p in parent.iterdir() if p.is_file()}
    args = SimpleNamespace(parent=parent, output=tmp_path/'supplement', model_config=None)
    e3_supplement.prepare(args)
    def forbid(*a, **kw):
        raise AssertionError('Supplement must not generate text')
    monkeypatch.setattr(e3_formal.Engine, 'answer', forbid)
    from longmem.generation import Generator
    monkeypatch.setattr(Generator, 'generate', forbid)
    original_append = replay.append_jsonl
    calls = 0
    def interrupt(path, row):
        nonlocal calls
        original_append(path, row)
        calls += 1
        if calls == 2:
            raise RuntimeError('fixture interruption')
    monkeypatch.setattr(replay, 'append_jsonl', interrupt)
    with pytest.raises(RuntimeError, match='fixture interruption'):
        e3_supplement.execute(args)
    e3_supplement.execute(args)
    result = e3_supplement.audit(args.output, parent)
    assert result['passed'] and not result['model_evidence']
    assert result['historical_feature_rows'] == 96 and result['benchmark_samples'] == 180
    saved = (args.output/'retrieval-replay.jsonl').read_bytes()
    e3_supplement.execute(args)
    assert saved == (args.output/'retrieval-replay.jsonl').read_bytes()
    assert before == {p.name: p.read_bytes() for p in parent.iterdir() if p.is_file()}
    aggregates = read_json(args.output/'failure-analysis.json')['aggregates']
    for r in aggregates:
        assert abs(sum(v for k, v in r['metrics'].items() if k.startswith('diagnostic.'))-1) < 1e-12
    path = args.output/'microbenchmark.json'
    original = read_json(path)
    altered = copy.deepcopy(original)
    altered['aggregates'][0]['timing']['scoring_seconds']['median_seconds'] += 1
    write_json(path, altered)
    manifest_path = args.output/'manifest.json'
    manifest = read_json(manifest_path)
    manifest['artifact_hashes']['microbenchmark.json'] = e3_supplement.sha256_file(path)
    write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match='Benchmark summary'):
        e3_supplement.audit(args.output, parent)
