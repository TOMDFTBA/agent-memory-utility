"""Release compatibility: old evidence, new naming, and safe restoration."""
import importlib.util
from pathlib import Path
import sys

import pytest

from longmem.config import make_store
from longmem.experiment_contracts import canonical_diagnostic_plan, metric_key
from longmem.generation import Generator
from longmem.scoring import score_answer

ROOT = Path(__file__).resolve().parents[1]


def test_backend_aliases_execute_without_models(tmp_path):
    for backend in ('evidence-test', 'evidence_test'):
        assert Generator({'backend': backend}).generate('', []) == '[TEST ONLY] No memory evidence.'
    for backend in ('hash-test', 'hash_test'):
        store = make_store({'embedding': {'backend': backend}, 'store_dir': str(tmp_path / backend)})
        assert store is not None


def test_frozen_diagnostic_adapter_is_read_only_and_rejects_strategy():
    old = {'candidate': 'storage_deletion', 'deleted_memory_id': 'm1', 'storage_ids': ['m2']}
    new = canonical_diagnostic_plan(old)
    assert old['candidate'] == 'storage_deletion'
    assert new == {'intervention': 'storage_deletion', 'deleted_memory_id': 'm1', 'storage_ids': ['m2']}
    assert canonical_diagnostic_plan(new) == new
    with pytest.raises(ValueError):
        canonical_diagnostic_plan({'candidate': 'utility_aware'})
    assert metric_key('prediction', 'mae') == 'prediction.mae'


def test_shared_score_matches_v01_on_archived_answers():
    from longmem.experiment_io import read_jsonl
    spec = importlib.util.spec_from_file_location('frozen_v01_score', ROOT / 'experiments/memory-utility/score.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    rows = read_jsonl(ROOT / 'experiments/utility-retention/results/e3-formal-model/responses.jsonl')
    for row in rows:
        previous = old.score(row['generated_answer'], row['gold_answer'])
        assert score_answer(row['generated_answer'], row['gold_answer']) == {
            'answer.exact_match': previous['exact_match'], 'answer.token_f1': previous['f1']}


def test_restore_rejects_conflicts_before_writing(tmp_path):
    spec = importlib.util.spec_from_file_location('release_artifacts', ROOT / 'scripts/release_artifacts.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    victim = tmp_path / 'experiments/utility-retention/results/e3-formal-model/manifest.json'
    victim.parent.mkdir(parents=True)
    victim.write_text('user data')
    with pytest.raises(ValueError, match='overwrite'):
        module.restore(tmp_path, results_only=True)
    assert victim.read_text() == 'user data'
    assert not (tmp_path / 'experiments/utility-retention/results/e1-extension-model/manifest.json').exists()


def test_package_does_not_depend_on_top_level_cli_imports():
    sys.path.insert(0, str(ROOT / 'experiments/utility-retention'))
    from utility_retention.e1_extension_data import build
    from utility_retention.e3_formal import deletion_plans
    plans = deletion_plans(build()[:1], 42)
    assert all(p['intervention'] == 'storage_deletion' and 'candidate' not in p for p in plans)
    for path in (ROOT / 'experiments/utility-retention/utility_retention').glob('*.py'):
        for forbidden in ('from generate_e1_extension import', 'from report import', 'from diagnose_e1 import'):
            assert forbidden not in path.read_text()
