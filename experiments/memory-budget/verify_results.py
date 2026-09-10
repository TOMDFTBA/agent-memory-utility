"""Audit run coverage, budgets, split isolation and saved per-query metrics."""
import csv
import json
import math
import sys
from pathlib import Path

root=Path(sys.argv[1])
m=json.loads((root/'manifest.json').read_text())
assert m['status']=='COMPLETE'
rows=list(csv.DictReader((root/'results.csv').open()))
expected=len(m['sizes'])*len(m['seeds'])*2*10
assert len(rows)==expected
seen=set()
for row in rows:
    key=(row['scenario'],int(row['size']),int(row['seed']),row['policy'],float(row['budget']))
    assert key not in seen;seen.add(key)
    scenario,size,seed,policy,budget=key
    directory=root/f'{scenario}-{size}-{seed}'/f'{policy}-{budget:g}'
    data=json.loads((directory.parent/'dataset.json').read_text())
    records={r['memory_id']:r for r in data['records']}
    assert len(records)==size
    dev={q['family'] for q in data['queries'] if q['split']=='dev'}
    test={q['family'] for q in data['queries'] if q['split']=='test'}
    assert not dev.intersection(test)
    ids=json.loads((directory/'index.json').read_text())['memory_ids']
    assert len(set(ids))==int(size*budget)==int(row['retained_count'])
    retained={records[mid]['canonical_id'] for mid in ids}
    pred=json.loads((directory/'predictions.json').read_text())
    assert len(pred)==72 and all(q['query']['split']=='test' for q in pred)
    r1=sum(q['canonical_hits'][0]==q['query']['target_canonical_id'] for q in pred)/len(pred)
    r5=sum(q['query']['target_canonical_id'] in q['canonical_hits'] for q in pred)/len(pred)
    rate=sum(q['query']['target_canonical_id'] in retained for q in pred)/len(pred)
    for name,value in [('recall_at_1',r1),('recall_at_5',r5),('target_fact_retained',rate)]:
        assert math.isclose(float(row[name]),value,abs_tol=1e-12)
    assert 0<=r1<=r5<=rate<=1
    assert float(row['exact_recall_at_5'])<=r5
    assert r1<=float(row['mrr'])<=rate
print(f'PASS: {expected} unique runs; exact budgets, split isolation and all saved Recall metrics verified.')
(root/'verification.json').write_text(json.dumps(dict(status='PASS',runs=expected,checks=['coverage','unique runs','fixed budgets','subject split isolation','saved prediction recall','target retention denominator','metric bounds']),indent=2))
