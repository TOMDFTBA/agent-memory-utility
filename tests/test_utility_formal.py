"""Formal E3 boundaries: independent datasets, frozen inference and complete resume."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).parents[1]/'experiments/utility-retention'
sys.path.insert(0, str(HERE))
from longmem.experiment_io import read_json, read_jsonl, write_json  # noqa: E402
from utility_retention import e3_formal as formal  # noqa: E402
from utility_retention.e3_formal_data import build_formal, check_formal_disjoint, ensure_past, past_view  # noqa: E402


def test_formal_data_reproducible_disjoint_and_annotation_boundary():
    settings, _ = formal.verify_freeze()
    previous = read_json(HERE/'results/e1-extension-model/dataset-manifest.json')['snapshots']
    # Engineering fixture never generates the formal-seed dataset.
    fixture = dict(settings['dataset'], structure_seed=2026091501, surface_seed=2026091502)
    rows = build_formal(fixture, previous)
    assert rows == build_formal(fixture, previous)
    assert len(rows) == 24 and all(s['split'] == 'test' for s in rows)
    with pytest.raises(ValueError):
        check_formal_disjoint(rows, rows)
    past = past_view(rows)
    ensure_past(past, [])
    past[0]['future_queries'] = rows[0]['future_queries']
    with pytest.raises(ValueError, match='Future'):
        ensure_past(past, [])
    with pytest.raises(ValueError, match='labels'):
        ensure_past(past_view(rows), [{'target': {'value': 1}}])


def test_formal_limits_fail_even_after_last_answer():
    settings, _ = formal.verify_freeze()
    with pytest.raises(RuntimeError):
        formal.enforce_limits([], [{'duration_seconds': 7200.01}], settings)
    with pytest.raises(RuntimeError):
        formal.enforce_limits([{'duration_seconds': 0}]*97, [], settings)


def test_formal_complete_resume_and_corruption(tmp_path, monkeypatch):
    args = SimpleNamespace(output=tmp_path/'formal', backend='test', model_config=None)
    formal.prepare(args)
    # A resumed later phase must not treat its valid deletion rows as unexpected.
    original = formal.loo_labels
    calls = 0
    def interrupt_once(*a, **kw):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError('simulated interrupt after deletion')
        return original(*a, **kw)
    monkeypatch.setattr(formal, 'loo_labels', interrupt_once)
    with pytest.raises(RuntimeError, match='simulated interrupt'):
        formal.execute(args)
    count = len(read_jsonl(args.output/'responses.jsonl'))
    formal.execute(args)
    assert formal.audit(args.output)['passed']
    assert read_json(args.output/'manifest.json')['status'] == 'COMPLETE'
    assert len(read_jsonl(args.output/'responses.jsonl')) >= count
    before = (args.output/'responses.jsonl').read_bytes()
    formal.execute(args)
    assert before == (args.output/'responses.jsonl').read_bytes()
    marker = read_json(args.output/'deployable-complete.json')
    assert marker['response_count'] <= count
    manifest = read_json(args.output/'manifest.json')
    original_manifest = copy.deepcopy(manifest)
    # Even if an attacker updates the result hash, raw score replay rejects it.
    path = args.output/'responses.jsonl'
    import json
    lines = path.read_text().splitlines()
    row = json.loads(lines[-1])
    row['metrics']['answer.exact_match'] = 123
    lines[-1] = json.dumps(row)
    path.write_text('\n'.join(lines)+'\n')
    manifest['artifact_hashes']['responses.jsonl'] = formal.sha256_file(path)
    write_json(args.output/'manifest.json', manifest)
    with pytest.raises(ValueError):
        formal.audit(args.output)
    path.write_bytes(before)
    write_json(args.output/'manifest.json', original_manifest)
    assert formal.audit(args.output)['passed']


def test_primary_contrast_excludes_ten_percent_and_pairs_trajectories(monkeypatch):
    settings, _ = formal.verify_freeze()
    rows = []
    for name in ('utility_aware',)+formal.REFERENCES:
        for tid in ('a', 'b'):
            for ratio in settings['budget_ratios']:
                value = (1 if ratio == .1 else .5) if name == 'utility_aware' else (0 if tid == 'a' else 1)
                rows.append(dict(candidate=name, trajectory_id=tid, budget_ratio=ratio,
                                 metrics={'answer.exact_match': value}))
    monkeypatch.setattr(formal, 'summarize', lambda *args: {'aggregates': [], 'per_trajectory': rows})
    result = formal.derive([], [], [], [], settings)
    primary = result['primary_result']
    assert primary['trajectory_count'] == 2
    assert primary['metrics']['answer.paired_em_difference'] == 0
    assert primary['trajectory_bootstrap_95_ci'] == [-.5, .5]
    assert primary['interpretation'] == 'inconclusive'
    assert len(result['primary_per_trajectory']) == 18
