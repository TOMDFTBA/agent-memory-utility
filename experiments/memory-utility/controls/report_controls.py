"""Audit frozen control run; pair wording and protocol effects with original outputs."""
import argparse
import csv
import json
import os
import statistics
from pathlib import Path

from control_common import HERE,UTILITY,read_jsonl,sha,write_json,CONDITIONS,extract,scoring
from run_controls import verify_rows,sources


def paired(a,b):
    differences=[x-y for x,y in zip(a,b)]
    return dict(n=len(a),mean_difference=statistics.mean(differences),
                improved=sum(d>0 for d in differences),worsened=sum(d<0 for d in differences),
                unchanged=sum(d==0 for d in differences))


def main():
    p=argparse.ArgumentParser();p.add_argument('result',type=Path)
    p.add_argument('--dev',type=Path,default=HERE/'results/dev')
    p.add_argument('--previous',type=Path,default=UTILITY/'results/v0.1')
    a=p.parse_args()
    identity=json.loads((a.result/'manifest.json').read_text())['identity']
    if identity['stage']!='test': raise ValueError('Expected frozen test run')
    if identity['source_hashes']!=sources(): raise ValueError('Source hash mismatch')
    if identity['design_sha256']!=sha(HERE/'design.json'): raise ValueError('Design mismatch')
    if identity['dataset_sha256']!=sha(HERE/'test.jsonl'): raise ValueError('Test dataset mismatch')
    frozen=identity['selection']
    if frozen['dev_responses_sha256']!=sha(a.dev/'responses.jsonl'): raise ValueError('Dev response mismatch')
    dev_identity=json.loads((a.dev/'manifest.json').read_text())['identity']
    dev=read_jsonl(a.dev/'responses.jsonl')
    from control_common import PROTOCOLS,render_prompt
    verify_rows(dev,read_jsonl(HERE/'dev.jsonl'),PROTOCOLS,identity['backend'])
    if dev_identity['stage']!='dev' or dev_identity['source_hashes']!=identity['source_hashes'] or dev_identity['model_metadata_sha256']!=identity['model_metadata_sha256']:
        raise ValueError('Dev/test provenance mismatch')
    trials=[]
    for protocol in PROTOCOLS:
        group=[r for r in dev if r['protocol']==protocol]
        trials.append((protocol,statistics.mean(r['scores']['exact_match'] for r in group)))
    if max(trials,key=lambda t:t[1])[0]!=frozen['protocol']: raise ValueError('Dev selection mismatch')
    data=read_jsonl(HERE/'test.jsonl');rows=read_jsonl(a.result/'responses.jsonl')
    verify_rows(rows,data,[frozen['protocol']],identity['backend'])
    for r in rows+dev:
        expected=render_prompt(r['content_prompt'],r['protocol'],lambda messages,**kw:'<用户>'+messages[0]['content']+'<AI>')
        if r['prompt']!=expected: raise ValueError('Rendered prompt mismatch with local MiniCPM template')
        if r['stop_reason']=='newline' and '\n' not in r['raw_output'].lstrip(): raise ValueError('Invalid newline stop')
    baseline={r['case_id']:r['scores']['exact_match'] for r in rows if r['condition']=='no_memory'}
    table=[]
    for condition in data[0]['conditions']:
        group=[r for r in rows if r['condition']==condition]
        gains=[r['scores']['exact_match']-baseline[r['case_id']] for r in group]
        hits=[r for r in group if r['retrieval']]
        table.append(dict(condition=condition,n=len(group),exact_match=statistics.mean(r['scores']['exact_match'] for r in group),
            f1=statistics.mean(r['scores']['f1'] for r in group),utility=statistics.mean(gains),
            positive=sum(v>0 for v in gains),negative=sum(v<0 for v in gains),
            recall=statistics.mean(r['retrieval']['recall_at_k'] for r in hits) if hits else None,
            hit_but_wrong=sum(r['retrieval']['recall_at_k'] and not r['scores']['exact_match'] for r in hits) if hits else None,
            memory_tokens=statistics.mean(r['memory_tokens'] for r in group) if group[0]['memory_tokens'] is not None else None,
            reached_limit=sum(r['stop_reason']=='max_tokens' for r in group),
            returned_multiline=sum('\n' in r['generated_answer'] for r in group)))
    lookup={(r['case_id'],r['condition']):r for r in rows}
    old_path=a.previous/'responses.jsonl'
    old=read_jsonl(old_path);old_lookup={(r['case_id'],r['condition']):r for r in old}
    comparisons=[]
    for t in table:
        condition=t['condition'];old_condition={'consolidation_keep_temporal_cue':'relevant','consolidation_strip_temporal_cue':'consolidation_strip_temporal_cue'}.get(condition,condition)
        current=[lookup[(q['case_id'],condition)] for q in data]
        previous=[old_lookup[(q['case_id'],old_condition)] for q in data]
        if any(x['content_prompt']!=y['prompt'] for x,y in zip(current,previous)): raise ValueError('Old/new content mismatch')
        comparisons.append(dict(condition=condition,old_condition=old_condition,
            old_em=statistics.mean(r['scores']['exact_match'] for r in previous),new_em=t['exact_match'],
            **paired([r['scores']['exact_match'] for r in current],[r['scores']['exact_match'] for r in previous])))
    keep=[lookup[(q['case_id'],'consolidation_keep_temporal_cue')] for q in data]
    strip=[lookup[(q['case_id'],'consolidation_strip_temporal_cue')] for q in data]
    relevant=[lookup[(q['case_id'],'relevant')] for q in data]
    if any(a['prompt']!=b['prompt'] or a['generated_answer']!=b['generated_answer'] for a,b in zip(keep,relevant)):
        raise ValueError('Identical Relevant/keep prompts failed deterministic equality check')
    wording=paired([r['scores']['exact_match'] for r in keep],[r['scores']['exact_match'] for r in strip])
    effects=dict(wording_keep_minus_strip=wording,protocol_comparisons=comparisons,original_responses_sha256=sha(old_path),
        note='Original test outcomes were already seen. Follow-up diagnosis, not a new untouched test set; no significance claim.')
    write_json(a.result/'summary.json',table);write_json(a.result/'paired-effects.json',effects)
    with (a.result/'summary.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    cases=[]
    # Predefined diagnostic types; first case per type, not incidence estimates.
    for kind,predicate in [
        ('wording_improves',lambda q:lookup[(q['case_id'],'consolidation_keep_temporal_cue')]['scores']['exact_match']>lookup[(q['case_id'],'consolidation_strip_temporal_cue')]['scores']['exact_match']),
        ('wording_equal',lambda q:lookup[(q['case_id'],'consolidation_keep_temporal_cue')]['scores']['exact_match']==lookup[(q['case_id'],'consolidation_strip_temporal_cue')]['scores']['exact_match']),
        ('remaining_retrieval_error',lambda q:lookup[(q['case_id'],'retrieved:full-1:k5')]['retrieval']['recall_at_k'] and not lookup[(q['case_id'],'retrieved:full-1:k5')]['scores']['exact_match'])]:
        q=next((q for q in data if predicate(q)),None)
        if q: cases.append(dict(kind=kind,case_id=q['case_id'],query=q['query'],gold=q['gold_answer'],
            keep=lookup[(q['case_id'],'consolidation_keep_temporal_cue')]['generated_answer'],
            strip=lookup[(q['case_id'],'consolidation_strip_temporal_cue')]['generated_answer'],
            top5=lookup[(q['case_id'],'retrieved:full-1:k5')]['generated_answer']))
    write_json(a.result/'cases.json',cases)
    verification=dict(status='PASS',dev_cases=6,dev_responses=len(dev),test_cases=len(data),test_responses=len(rows),
        checks=['dev-only protocol selection','source/model/design/data hashes','paired coverage','no duplicate responses',
                'rendered and content prompts','answer extraction','scores','retrieval labels','Relevant/keep identical outputs','old/new content equality'])
    write_json(a.result/'verification.json',verification)
    lines=['# 第三阶段补充实验：时间措辞与输出协议','',
        f"开发集 6 个主题 × 6 条件 × 4 协议 = {len(dev)} 次；按开发集 EM 选择 `{frozen['protocol']}`。冻结后在原有 54 个问题上运行 12 条件，共 {len(rows)} 次。",'',
        '## 开发集协议选择','', '| 协议 | 开发集 EM |','|---|---:|']
    for protocol,em in trials: lines.append(f'| {protocol} | {em:.3f} |')
    lines+=['','所有条件同权，平分按预先规定的 chat_line、chat_eos、plain_line、plain_eos 顺序选择。仅用 seed 77 的开发主体；测试主体不参与协议选择。',
        '','## 冻结协议下的结果','',
        '| 条件 | EM | F1 | 效用 | Recall@k | 命中但答错 |','|---|---:|---:|---:|---:|---:|']
    for t in table:
        recall='—' if t['recall'] is None else f"{t['recall']:.3f}"
        lines.append(f"| {t['condition']} | {t['exact_match']:.3f} | {t['f1']:.3f} | {t['utility']:+.3f} | {recall} | {t['hit_but_wrong'] if t['hit_but_wrong'] is not None else '—'} |")
    lines+=['','## 配对控制','',
        f"保留 Currently 相对删除前缀：平均 EM 差 {wording['mean_difference']:+.3f}；改善 {wording['improved']}、恶化 {wording['worsened']}、不变 {wording['unchanged']} 个问题。",'',
        '两种整合的事实、来源与所选版本相同，正文只差 Currently 前缀。保留前缀与 Relevant 的输入正文完全一致，所有对应输出也一致；这不证明整合优于原始单条正确事实。前缀也增加 token，未做等长度同义改写对照。','',
        '| 条件 | 原协议 EM | 冻结协议 EM | 改善数 | 恶化数 |','|---|---:|---:|---:|---:|']
    for t in comparisons: lines.append(f"| {t['condition']} | {t['old_em']:.3f} | {t['new_em']:.3f} | {t['improved']} | {t['worsened']} |")
    lines+=['','原协议来自未覆盖的第一版回答；keep 对照映射原 Relevant，strip 映射原 Consolidated；已核验所有原始内容提示一致。跨协议差异可能包含对话包装与终止规则，不能一概解释为模型知识改善。','',
        '## 代表案例','']
    for c in cases: lines.append(f"- {c['kind']} / {c['case_id']}：标准答案 {c['gold']}；保留前缀 `{c['keep']}`；删除前缀 `{c['strip']}`；全量 top-5 `{c['top5']}`。")
    lines+=['','## 限制与可复现性','',
        '这是一轮由第一版观察驱动的后续诊断，原测试集已被观察，不能声称新的盲测。开发集仅六个主题，选择稳定性有限；54 个问题仍来自 18 个主题 × 三种子。',
        '主 EM 的规范化规则未改。*_line 在首个非空文本后的换行停止，并删除边界之后的后缀；不读取 gold。保留原始输出、实际 token ID、终止原因与协议后答案。*_eos 为 EOS 或固定 24-token 上限。',
        'Chat 包装使用本地 tokenizer 中已有模板，plain 使用原始文本；生成参数均为 greedy、use_cache=False、24 新 tokens、2048 输入上限。',
        '未训练模型、未扩充答案空间、未评测引用或真实长会话；无关记忆偶然答对和目标缺失时猜对的问题仍存在。',
        '全部结果均为描述性配对统计。模型元数据与源码有散列，外部权重分片未散列。详见 design.json、frozen-protocol.json、manifest.json、responses.jsonl 与 verification.json。']
    if identity['backend']=='test': lines.insert(2,'**仅工程测试，不能用于模型效果结论。**')
    (a.result/'report.md').write_text('\n'.join(lines)+'\n')
    os.environ.setdefault('MPLCONFIGDIR','/tmp/longmem-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,4));ax.axis('off')
    cells=[[t['condition'],f"{t['old_em']:.3f}",f"{t['new_em']:.3f}",f"{t['mean_difference']:+.3f}"] for t in comparisons[:6]]
    artist=ax.table(cellText=cells,colLabels=['Condition','Original EM','Frozen protocol EM','Difference'],loc='center',cellLoc='center',colWidths=[.4,.2,.2,.2])
    artist.auto_set_font_size(False);artist.set_fontsize(10);artist.scale(1,1.7)
    ax.set_title(f"Wording / output controls | {frozen['protocol']} | n={len(data)}")
    fig.tight_layout();fig.savefig(a.result/'control-comparison.png',dpi=180);plt.close(fig)
    print(json.dumps(verification));print(json.dumps(wording))

if __name__=='__main__': main()
