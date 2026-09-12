import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE=Path(__file__).parents[1]/'experiments/memory-utility/controls'
sys.path.insert(0,str(HERE))
import control_common as c  # noqa: E402
import run_controls as run  # noqa: E402


def test_protocol_boundary_never_searches_for_gold():
    assert c.extract('\n\nOslo\nAnswer: Perth','plain_line')=='Oslo'
    assert not c.completed_line('\n\n')
    assert not c.completed_line('\n\nOslo')
    assert c.completed_line('\n\nOslo\n')
    assert c.extract('Not Perth\nPerth','chat_line')=='Not Perth'
    assert c.extract('Perth\nMore','plain_eos')=='Perth\nMore'


def test_development_subjects_are_disjoint_and_wording_control_is_exact():
    dev=c.read_jsonl(HERE/'dev.jsonl')
    test=c.read_jsonl(HERE/'test.jsonl')
    assert len(dev)==6 and len(test)==54
    assert {r['family'].split(':')[0] for r in dev}.isdisjoint(r['family'].split(':')[0] for r in test)
    for row in dev+test:
        keep=row['conditions']['consolidation_keep_temporal_cue']
        strip=row['conditions']['consolidation_strip_temporal_cue']
        assert [m['content'] for m in keep]==[m['content'] for m in row['conditions']['relevant']]
        assert [dict(m,content=m['content'].removeprefix('Currently, ')) for m in keep]==strip


def make_dev_run(tmp_path):
    out=tmp_path/'dev'
    run.run(SimpleNamespace(stage='dev',output=out,frozen=tmp_path/'unused.json',
                            model_config=None,backend='test'))
    return out


def test_frozen_protocol_is_selected_only_from_dev(tmp_path):
    out=make_dev_run(tmp_path)
    target=tmp_path/'frozen.json'
    run.freeze(SimpleNamespace(output=out,frozen=target))
    assert json.loads(target.read_text())['protocol']=='chat_line'
    manifest=json.loads((out/'manifest.json').read_text())
    manifest['identity']['stage']='test'
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='Only development'):
        run.freeze(SimpleNamespace(output=tmp_path,frozen=target))


def test_corrupted_extraction_is_rejected(tmp_path):
    rows=c.read_jsonl(make_dev_run(tmp_path)/'responses.jsonl')
    rows[0]['generated_answer']='Perth'
    with pytest.raises(ValueError,match='extraction mismatch'):
        run.verify_rows(rows,c.read_jsonl(HERE/'dev.jsonl'),c.PROTOCOLS,'test')
