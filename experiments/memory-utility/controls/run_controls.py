"""Development-only protocol selection followed by frozen test inference."""
import argparse
import json
import platform
import time
from pathlib import Path

from longmem.config import load_config
from longmem.experiment_io import public_model_config
from control_common import (HERE,UTILITY,ROOT,PROTOCOLS,sha,read_jsonl,write_json,content_prompt,
                            render_prompt,extract,completed_line,scoring)


def sources():
    paths=[HERE/'control_common.py',Path(__file__),UTILITY/'generate_dataset.py',
           UTILITY.parent/'memory-budget/generate_dataset.py',UTILITY/'score.py']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def verify_rows(rows,data,protocols,backend,complete=True):
    expected={(r['case_id'],c,p) for r in data for c in r['conditions'] for p in protocols}
    keys=[(r['case_id'],r['condition'],r['protocol']) for r in rows]
    if len(keys)!=len(set(keys)) or not set(keys)<=expected or (complete and set(keys)!=expected):
        raise ValueError('Incomplete, duplicate or unexpected response keys')
    lookup={r['case_id']:r for r in data}
    for r in rows:
        q=lookup[r['case_id']];memories=q['conditions'][r['condition']]
        if any(r[k]!=q[k] for k in ['seed','family','query']): raise ValueError('Case mismatch')
        if r['backend']!=backend or r['gold_answer']!=q['gold_answer']: raise ValueError('Backend/gold mismatch')
        if r['content_prompt']!=content_prompt(q,memories): raise ValueError('Content prompt mismatch')
        if r['evidence_ids']!=[m['memory_id'] for m in memories]: raise ValueError('Evidence mismatch')
        if r['generated_answer']!=extract(r['raw_output'],r['protocol']): raise ValueError('Answer extraction mismatch')
        if r['scores']!=scoring.score(r['generated_answer'],r['gold_answer']): raise ValueError('Score mismatch')
        if r['retrieval']!=q['retrieval'].get(r['condition'],{}): raise ValueError('Retrieval mismatch')


class Model:
    def __init__(self,config,design):
        import torch
        from transformers import AutoTokenizer,AutoModelForCausalLM
        self.torch=torch;self.design=design;self.config=config
        if config['device']=='cuda' and not torch.cuda.is_available():
            raise RuntimeError('GPU unavailable in sandbox; no fallback')
        torch.manual_seed(design['torch_seed'])
        self.tokenizer=AutoTokenizer.from_pretrained(config['model_path'],trust_remote_code=True,local_files_only=True)
        self.model=AutoModelForCausalLM.from_pretrained(config['model_path'],trust_remote_code=True,local_files_only=True,
            torch_dtype=torch.bfloat16 if config['device']=='cuda' else torch.float32).to(config['device']).eval()

    def answer(self,content,protocol):
        from transformers import StoppingCriteria,StoppingCriteriaList
        prompt=render_prompt(content,protocol,self.tokenizer.apply_chat_template)
        inputs=self.tokenizer(prompt,return_tensors='pt').to(self.config['device'])
        length=inputs['input_ids'].shape[1]
        if length>self.design['max_input_tokens']: raise ValueError('Input exceeds fixed budget')
        tokenizer=self.tokenizer
        class FirstLine(StoppingCriteria):
            def __call__(self,input_ids,scores,**kwargs):
                return completed_line(tokenizer.decode(input_ids[0,length:],skip_special_tokens=True))
        kwargs={}
        if protocol.endswith('_line'): kwargs['stopping_criteria']=StoppingCriteriaList([FirstLine()])
        with self.torch.inference_mode():
            output=self.model.generate(**inputs,max_new_tokens=self.design['max_new_tokens'],do_sample=False,
                use_cache=False,pad_token_id=self.tokenizer.eos_token_id,**kwargs)
        ids=output[0,length:].tolist()
        raw=self.tokenizer.decode(ids,skip_special_tokens=True)
        reason='newline' if protocol.endswith('_line') and completed_line(raw) else ('eos' if ids and ids[-1]==self.tokenizer.eos_token_id else 'max_tokens')
        return dict(prompt=prompt,raw_output=raw,generated_answer=extract(raw,protocol),input_tokens=length,
                    generated_token_ids=ids,stop_reason=reason)


def run(a):
    design=json.loads((HERE/'design.json').read_text())
    data=read_jsonl(HERE/(a.stage+'.jsonl'))
    if sha(HERE/(a.stage+'.jsonl'))!=design[a.stage+'_sha256']: raise ValueError('Dataset hash mismatch')
    # The synthetic backend must be runnable from a fresh clone without the
    # ignored, machine-local configs/local.yaml file.
    model_config=a.model_config or (ROOT/'configs/test.yaml' if a.backend=='test' else None)
    config=load_config(model_config)['generation']
    config.update(max_new_tokens=design['max_new_tokens'], max_input_tokens=design['max_input_tokens'])
    selection=None
    if a.stage=='test':
        selection=json.loads(a.frozen.read_text())
        if selection['backend']!=a.backend or selection['design_sha256']!=sha(HERE/'design.json') or selection['source_hashes']!=sources():
            raise ValueError('Frozen protocol backend/design/source mismatch')
        protocols=[selection['protocol']]
    else: protocols=PROTOCOLS
    model_path=config.get('model_path')
    metadata=({p.name:sha(p) for p in Path(model_path).iterdir() if p.name in
              ['config.json','generation_config.json','tokenizer_config.json','tokenizer.model','modeling_minicpm.py','configuration_minicpm.py']}
              if model_path else {})
    identity=dict(stage=a.stage,backend=a.backend,dataset_sha256=sha(HERE/(a.stage+'.jsonl')),
        design_sha256=sha(HERE/'design.json'),source_hashes=sources(),generation=public_model_config(config),
        model_metadata_sha256=metadata,protocols=protocols,selection=selection)
    if selection and selection['generation']!=config: raise ValueError('Frozen model config mismatch')
    if selection and selection['model_metadata_sha256']!=metadata: raise ValueError('Frozen model metadata mismatch')
    a.output.mkdir(parents=True,exist_ok=True)
    mp=a.output/'manifest.json'
    if mp.exists():
        if json.loads(mp.read_text())['identity']!=identity: raise ValueError('Resume mismatch')
    else: write_json(mp,dict(identity=identity,python=platform.python_version()))
    rp=a.output/'responses.jsonl'
    rows=read_jsonl(rp) if rp.exists() else []
    verify_rows(rows,data,protocols,a.backend,complete=False)
    done={(r['case_id'],r['condition'],r['protocol']) for r in rows}
    total=sum(len(r['conditions'])*len(protocols) for r in data)
    if len(done)==total:
        print(f'Already complete: {total}');return
    model=Model(config,design) if a.backend=='transformers' else None
    with rp.open('a') as stream:
        for row in data:
            for condition,memories in row['conditions'].items():
                for protocol in protocols:
                    if (row['case_id'],condition,protocol) in done: continue
                    content=content_prompt(row,memories);start=time.perf_counter()
                    if model: generated=model.answer(content,protocol)
                    else:
                        prompt=render_prompt(content,protocol,lambda messages,**kw:'<用户>'+messages[0]['content']+'<AI>')
                        generated=dict(prompt=prompt,raw_output='[TEST ONLY] UNKNOWN',generated_answer='[TEST ONLY] UNKNOWN',input_tokens=None,generated_token_ids=[],stop_reason='test')
                    record=dict(case_id=row['case_id'],seed=row['seed'],family=row['family'],query=row['query'],
                        condition=condition,protocol=protocol,backend=a.backend,content_prompt=content,gold_answer=row['gold_answer'],
                        evidence_ids=[m['memory_id'] for m in memories],retrieval=row['retrieval'].get(condition,{}),
                        scores=scoring.score(generated['generated_answer'],row['gold_answer']),seconds=time.perf_counter()-start,
                        memory_tokens=len(model.tokenizer.encode('\n'.join(m['content'] for m in memories),add_special_tokens=False)) if model else None,**generated)
                    stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush()
                    done.add((row['case_id'],condition,protocol))
                    print(f'{len(done)}/{total} {protocol} {condition} EM={record["scores"]["exact_match"]}',flush=True)
    print('Complete')


def freeze(a):
    manifest=json.loads((a.output/'manifest.json').read_text())['identity']
    if manifest['stage']!='dev': raise ValueError('Only development outputs may select protocol')
    if manifest['source_hashes']!=sources() or manifest['design_sha256']!=sha(HERE/'design.json'): raise ValueError('Development source/design mismatch')
    data=read_jsonl(HERE/'dev.jsonl')
    if sha(HERE/'dev.jsonl')!=manifest['dataset_sha256']: raise ValueError('Dev data mismatch')
    rows=read_jsonl(a.output/'responses.jsonl');verify_rows(rows,data,PROTOCOLS,manifest['backend'])
    trials=[]
    for protocol in PROTOCOLS:
        group=[r for r in rows if r['protocol']==protocol]
        trials.append(dict(protocol=protocol,n=len(group),exact_match=sum(r['scores']['exact_match'] for r in group)/len(group),
                           multiline=sum('\n' in r['generated_answer'] for r in group),truncated=sum(r['stop_reason']=='max_tokens' for r in group)))
    chosen=max(trials,key=lambda t:t['exact_match'])
    result=dict(protocol=chosen['protocol'],backend=manifest['backend'],trials=trials,
        selection_rule='Highest mean dev EM; ties follow fixed protocol order',
        design_sha256=sha(HERE/'design.json'),dev_responses_sha256=sha(a.output/'responses.jsonl'),
        source_hashes=sources(),generation=manifest['generation'],model_metadata_sha256=manifest['model_metadata_sha256'])
    if a.frozen.exists() and json.loads(a.frozen.read_text())!=result: raise ValueError('Refuse changed frozen selection')
    write_json(a.frozen,result);print(json.dumps(result['trials']));print('Selected:',chosen['protocol'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('stage',choices=['dev','freeze','test'])
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--frozen',type=Path,default=HERE/'frozen-protocol.json')
    p.add_argument('--model-config',type=Path,default=None,
                   help='YAML config; otherwise LONGMEM_CONFIG or configs/local.yaml')
    p.add_argument('--backend',choices=['transformers','test'],default='transformers')
    a=p.parse_args()
    freeze(a) if a.stage=='freeze' else run(a)
