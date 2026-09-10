"""Rebuild one saved budget index using the run's shared embedding cache."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from generate_dataset import generate
from longmem.retrieval import VectorIndex

p=argparse.ArgumentParser()
p.add_argument('run',type=Path)
p.add_argument('case',help='e.g. balanced-10000-11/semantic_dedup-0.5')
args=p.parse_args()
manifest=json.loads((args.run/'manifest.json').read_text())
dest=args.run/args.case
meta=json.loads((dest/'index.json').read_text())
scenario,size,seed=dest.parent.name.split('-')
records,_=generate(max(manifest['sizes']),int(seed),'balanced')
texts=[r['content'] for r in records]
digest=hashlib.sha256((manifest['embedding_version']+'\n'+json.dumps(texts)).encode()).hexdigest()
vectors=np.load(Path(manifest['cache'])/(digest+'.npy'),mmap_mode='r')
positions={r['memory_id']:i for i,r in enumerate(records)}
selected=[positions[mid] for mid in meta['memory_ids']]
index=VectorIndex(dest,meta['dimension']).build(meta['memory_ids'],vectors[selected],meta['embedding_version'])
actual=json.loads((dest/'index.json').read_text())
if actual['sha256']!=meta['sha256']:raise RuntimeError('rebuilt index differs from original checksum')
print(f'Verified {index.ntotal} vectors: {dest / "index.faiss"}')
