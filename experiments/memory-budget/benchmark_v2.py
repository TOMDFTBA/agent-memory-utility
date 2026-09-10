"""Five-scale experiment with development-only calibration and matched budgets."""
import argparse
import csv
import hashlib
import json
import os
import platform
import random
import time
from pathlib import Path

import faiss
import numpy as np
from generate_dataset import generate
from longmem.config import load_config
from longmem.embedder import HashEmbedder, MiniCPMEmbedder
from longmem.retrieval import VectorIndex


def save(path, obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False))


def semantic_order(records, vectors, threshold):
    """Exact greedy dedup: new representatives first, suppressed items as budget backfill."""
    index = faiss.IndexFlatIP(vectors.shape[1])
    kept, rejected = [], []
    for i in sorted(range(len(records)),key=lambda i:(-records[i]['event_order'],records[i]['memory_id'])):
        score = float(index.search(vectors[i:i+1],1)[0][0,0]) if kept else -2
        if score < threshold:
            kept.append(i); index.add(vectors[i:i+1])
        else:
            rejected.append(i)
    return kept+rejected, len(kept)


def ranking_metrics(records, selected, positions, queries):
    exact1=[]; exact5=[]; eq1=[]; eq5=[]; rr=[]; rrex=[]; retained=[]; old=[]
    canonical={records[i]['canonical_id'] for i in selected}
    for q, row in zip(queries, positions):
        ids=[records[selected[int(i)]]['memory_id'] for i in row]
        facts=[records[selected[int(i)]]['canonical_id'] for i in row]
        ex=ids.index(q['target_memory_id'])+1 if q['target_memory_id'] in ids else 0
        rank=facts.index(q['target_canonical_id'])+1 if q['target_canonical_id'] in facts else 0
        exact1.append(ex==1); exact5.append(0<ex<=5)
        eq1.append(rank==1); eq5.append(0<rank<=5)
        rr.append(1/rank if rank else 0); rrex.append(1/ex if ex else 0)
        retained.append(q['target_canonical_id'] in canonical)
        old.append(facts[0]==q['superseded_memory_id'])
    return {k:float(np.mean(v)) for k,v in dict(exact_recall_at_1=exact1,exact_recall_at_5=exact5,
        recall_at_1=eq1,recall_at_5=eq5,mrr=rr,exact_mrr=rrex,target_fact_retained=retained,
        superseded_fact_at_1=old).items()}


def encode_cached(encoder, texts, cache):
    digest=hashlib.sha256((encoder.version+'\n'+json.dumps(texts)).encode()).hexdigest()
    path=cache/(digest+'.npy')
    if path.exists():
        vectors=np.load(path)
        if vectors.shape != (len(texts),encoder.dimension) or not np.isfinite(vectors).all():
            raise ValueError('invalid cached vectors')
        return vectors
    chunks=[]
    for start in range(0,len(texts),500):
        chunks.append(encoder.documents(texts[start:start+500]))
        print(f'encoded {min(start+500,len(texts))}/{len(texts)}',flush=True)
    vectors=np.ascontiguousarray(np.concatenate(chunks),dtype=np.float32)
    faiss.normalize_L2(vectors)
    np.save(path,vectors)
    return vectors


def calibration(encoder, cache):
    records, queries=generate(500,77,'balanced')
    queries=[q for q in queries if q['split']=='dev']
    vectors=encode_cached(encoder,[r['content'] for r in records],cache)
    qv=encoder.documents([getattr(encoder,'query_prefix','')+q['query'] for q in queries])
    trials=[]
    for threshold in [.90,.95,.98]:
        order,count=semantic_order(records,vectors,threshold)
        values=[]
        for ratio in [.25,.5,.75]:
            chosen=order[:int(len(records)*ratio)]
            ix=faiss.IndexFlatIP(encoder.dimension); ix.add(vectors[chosen])
            positions=ix.search(qv,len(chosen))[1]
            values.append(ranking_metrics(records,chosen,positions,queries)['recall_at_5'])
        trials.append(dict(threshold=threshold,dev_recall5=float(np.mean(values)),representatives=count))
    best=max(trials,key=lambda r:(r['dev_recall5'],r['threshold']))
    return dict(threshold=best['threshold'],seed=77,size=500,split='dev',objective='mean equivalent-fact Recall@5 across budgets',trials=trials)


def run(args):
    out=Path(args.output).resolve(); out.mkdir(parents=True,exist_ok=False)
    cache=Path(args.cache).resolve(); cache.mkdir(parents=True,exist_ok=True)
    faiss.omp_set_num_threads(1)
    config=load_config(args.model_config)['embedding']; config.pop('backend')
    encoder=HashEmbedder() if args.backend=='hash-test' else MiniCPMEmbedder(**config)
    manifest=dict(vars(args),embedding_version=encoder.version,platform=platform.platform(),processor=platform.processor(),numpy=np.__version__,faiss=faiss.__version__,faiss_threads=1,query_batch_size=1,document_batch_size=getattr(encoder,'batch_size',None),status='RUNNING')
    if args.backend=='minicpm':
        import torch
        manifest.update(torch=torch.__version__,rocm=torch.version.hip,gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
    save(out/'manifest.json',manifest)
    save(out/'source-hashes.json', {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), Path(__file__).with_name('generate_dataset.py'), Path('src/longmem/embedder.py')]})
    calibrated=json.loads(Path(args.calibration_file).read_text()) if args.calibration_file else calibration(encoder,cache)
    if args.calibration_file and calibrated['embedding_version'] != encoder.version:
        raise ValueError('frozen calibration model version mismatch')
    save(out/'calibration.json',calibrated)
    print('calibrated',calibrated,flush=True)
    rows=[]
    for seed in args.seeds:
        maxrecords,allqueries=generate(max(args.sizes),seed,'balanced')
        vectors=encode_cached(encoder,[r['content'] for r in maxrecords],cache)
        queries=[q for q in allqueries if q['split']=='test']
        encoder.query(queries[0]['query'])
        qv=[]; qtimes=np.empty((args.repeats,len(queries)))
        # Randomized query order; GPU->CPU conversion synchronizes each measurement.
        for repeat in range(args.repeats):
            order=list(range(len(queries))); random.Random(seed+repeat).shuffle(order)
            encoded={}
            for qi in order:
                start=time.perf_counter(); encoded[qi]=encoder.query(queries[qi]['query']); qtimes[repeat,qi]=(time.perf_counter()-start)*1000
            if repeat==0: qv=np.concatenate([encoded[i] for i in range(len(queries))])
        np.save(out/f'query-times-{seed}.npy',qtimes)
        np.save(out/f'query-vectors-{seed}.npy',qv)
        if args.backend=='minicpm':
            lengths=[len(encoder.tokenizer.encode(r['content'],add_special_tokens=False)) for r in maxrecords]
        else: lengths=[len(r['content'].split()) for r in maxrecords]
        for scenario in ['old','balanced']:
            for size in args.sizes:
                folder=out/f'{scenario}-{size}-{seed}'; folder.mkdir()
                records,_=generate(size,seed,scenario)
                assert [r['content'] for r in records]==[r['content'] for r in maxrecords[:size]]
                save(folder/'dataset.json',dict(records=records,queries=allqueries))
                v=vectors[:size]
                start=time.perf_counter(); semorder,representatives=semantic_order(records,v,calibrated['threshold']); sem_seconds=time.perf_counter()-start
                plans=[('full',1.)]+[(p,r) for p in ['recency','importance','semantic_dedup'] for r in [.25,.5,.75]]
                random.Random(seed+size).shuffle(plans)
                for policy,ratio in plans:
                    start=time.perf_counter()
                    if policy=='full': selected=list(range(size))
                    elif policy=='semantic_dedup': selected=semorder[:int(size*ratio)]
                    else:
                        key='event_order' if policy=='recency' else 'importance'
                        selected=sorted(range(size),key=lambda i:(-records[i][key],records[i]['memory_id']))[:int(size*ratio)]
                    select_seconds=(time.perf_counter()-start)+(sem_seconds if policy=='semantic_dedup' else 0)
                    dest=folder/f'{policy}-{ratio:g}'; dest.mkdir()
                    start=time.perf_counter(); index=VectorIndex(dest,encoder.dimension).build([records[i]['memory_id'] for i in selected],v[selected],encoder.version); build_seconds=time.perf_counter()-start
                    positions=index.search(qv,len(selected))[1]  # full ranking for untruncated MRR, outside timed search
                    metrics=ranking_metrics(records,selected,positions,queries)
                    index.search(qv[:1],5)
                    searchtimes=np.empty_like(qtimes)
                    for repeat in range(args.repeats):
                        order=list(range(len(queries))); random.Random(seed+repeat).shuffle(order)
                        for qi in order:
                            start=time.perf_counter(); index.search(qv[qi:qi+1],5); searchtimes[repeat,qi]=(time.perf_counter()-start)*1000
                    total=qtimes+searchtimes
                    tokens=[sum(lengths[selected[int(i)]] for i in row[:5]) for row in positions]
                    row=dict(scenario=scenario,size=size,seed=seed,policy=policy,budget=ratio,retained_count=len(selected),retained_ratio=len(selected)/size,**metrics,
                        index_bytes=index.ntotal*encoder.dimension*4+45,selection_seconds=select_seconds,index_build_seconds=build_seconds,retrieved_tokens=float(np.mean(tokens)),dedup_representatives=representatives if policy=='semantic_dedup' else '',samples=total.size)
                    row['index_bytes']=(dest/'index.faiss').stat().st_size
                    for name,samples in [('query',qtimes),('search',searchtimes),('retrieval',total)]:
                        for percentile in [50,95]: row[f'{name}_p{percentile}_ms']=float(np.percentile(samples,percentile))
                    rows.append(row)
                    predictions=[]
                    for q,pos in zip(queries,positions):
                        predictions.append(dict(query=q,hits=[records[selected[int(i)]]['memory_id'] for i in pos[:5]],
                            canonical_hits=[records[selected[int(i)]]['canonical_id'] for i in pos[:5]]))
                    save(dest/'predictions.json',predictions)
                    np.save(dest/'search-times.npy',searchtimes)
                    # Index is exactly rebuildable from cached vectors and saved ID manifest.
                    # Avoid keeping gigabytes of redundant per-budget vector copies.
                    (dest/'index.faiss').unlink()
                    print(scenario,size,seed,policy,ratio,round(metrics['recall_at_5'],3),flush=True)
                with (out/'results.csv').open('w') as f:
                    writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    manifest['status']='COMPLETE';manifest['rows']=len(rows); save(out/'manifest.json',manifest)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--backend',choices=['minicpm','hash-test'],default='minicpm')
    p.add_argument('--model-config',default=None,help='YAML config; otherwise LONGMEM_CONFIG or configs/local.yaml')
    p.add_argument('--sizes',nargs='+',type=int,default=[100,500,1000,5000,10000])
    p.add_argument('--seeds',nargs='+',type=int,default=[11,22,33])
    p.add_argument('--repeats',type=int,default=5)
    p.add_argument('--cache',default='cache/memory-budget-v2')
    p.add_argument('--calibration-file',help='Frozen development-only calibration JSON')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    if min(args.sizes)<100 or args.repeats<1 or 77 in args.seeds: p.error('size>=100, repeats>=1, test seeds must exclude calibration seed 77')
    run(args)
