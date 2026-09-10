import importlib.util
import sys
from pathlib import Path

import pytest

HERE=Path(__file__).parents[1]/'experiments/memory-utility'
sys.path.insert(0,str(HERE))
# Other experiment modules have identically named files; isolate this import.
spec=importlib.util.spec_from_file_location('utility_dataset',HERE/'generate_dataset.py')
utility=importlib.util.module_from_spec(spec);spec.loader.exec_module(utility)
from score import score


def test_scoring_rejects_substring_and_negation():
    assert score('The Neovim.', 'Neovim')['exact_match']==1
    assert score('Not Neovim', 'Neovim')['exact_match']==0
    assert score('Neovim or Emacs', 'Neovim')['exact_match']==0
    assert score('UNKNOWN','Perth')['f1']==0


def test_consolidation_uses_event_order_not_input_order():
    old=dict(subject='A',relation='city',event_order=1,memory_id='a',canonical_id='a',content='Previously, A lives in Oslo.')
    new=dict(old,event_order=2,memory_id='b',canonical_id='b',content='Currently, A lives in Perth.')
    for inputs in ([old,new],[new,old]):
        result=utility.consolidate(inputs)[0]
        assert result['content']=='A lives in Perth.'
        assert result['canonical_id']=='b'
        assert set(result['source_ids'])=={'a','b'}


def test_frozen_cases_are_paired_and_recall_matches_evidence():
    import json
    cases=[json.loads(s) for s in (HERE/'dataset.jsonl').read_text().splitlines()]
    assert len(cases)==54
    assert len({r['case_id'] for r in cases})==54
    for r in cases:
        assert len(r['conditions'])==11
        assert r['conditions']['no_memory']==[]
        assert r['conditions']['relevant'][0]['canonical_id']==r['target_canonical_id']
        assert r['conditions']['consolidation_strip_temporal_cue'][0]['canonical_id']==r['target_canonical_id']
        assert r['target_canonical_id'] not in [m['canonical_id'] for m in r['conditions']['irrelevant']]
        for c, metrics in r['retrieval'].items():
            assert metrics['recall_at_k']==int(r['target_canonical_id'] in [m['canonical_id'] for m in r['conditions'][c]])
            if metrics['recall_at_k']: assert metrics['target_fact_retained']


@pytest.mark.parametrize('damage', ['duplicate','score','missing'])
def test_report_rejects_corrupt_outputs(tmp_path, damage):
    import json
    import subprocess
    smoke=tmp_path/'smoke'
    subprocess.run([
        sys.executable,str(HERE/'run_ablation.py'),'--output',str(smoke),
        '--backend','test','--limit','1'
    ],check=True,capture_output=True,text=True)
    rows=[json.loads(s) for s in (smoke/'responses.jsonl').read_text().splitlines()]
    if damage=='duplicate': rows.append(rows[0])
    elif damage=='missing': rows.pop()
    else: rows[0]['scores']['exact_match']=1
    damaged=tmp_path/'damaged';damaged.mkdir()
    (damaged/'manifest.json').write_text((smoke/'manifest.json').read_text())
    (damaged/'responses.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    result=subprocess.run([sys.executable,str(HERE/'report.py'),str(damaged)],capture_output=True,text=True)
    assert result.returncode!=0
    assert ('Incomplete or duplicate' if damage!='score' else 'Score mismatch') in result.stderr
