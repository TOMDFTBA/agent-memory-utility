"""Verify complete paired outputs, then export descriptive tables and diagnostic cases."""
import argparse
import csv
import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

from score import score
from generate_dataset import digest
from run_ablation import prompt_for


def summarize(rows):
    baseline={r['case_id']:r for r in rows if r['condition']=='no_memory'}
    grouped=defaultdict(list)
    for r in rows: grouped[r['condition']].append(r)
    summaries=[]
    for condition, group in grouped.items():
        gain=[r['scores']['exact_match']-baseline[r['case_id']]['scores']['exact_match'] for r in group]
        means=[statistics.mean(r['scores']['exact_match'] for r in group if r['seed']==s) for s in sorted({r['seed'] for r in group})]
        retrieval=[r for r in group if r['retrieval']]
        summaries.append(dict(condition=condition,n=len(group),exact_match=statistics.mean(r['scores']['exact_match'] for r in group),
            seed_sd=statistics.pstdev(means),f1=statistics.mean(r['scores']['f1'] for r in group),utility=statistics.mean(gain),
            positive=sum(g>0 for g in gain),negative=sum(g<0 for g in gain),
            recall=statistics.mean(r['retrieval']['recall_at_k'] for r in retrieval) if retrieval else None,
            retrieval_misses=sum(not r['retrieval']['recall_at_k'] for r in retrieval) if retrieval else None,
            pruned_target=sum(not r['retrieval']['target_fact_retained'] for r in retrieval) if retrieval else None,
            hit_but_wrong=sum(r['retrieval']['recall_at_k'] and not r['scores']['exact_match'] for r in retrieval) if retrieval else None,
            memory_tokens=statistics.mean(r['memory_tokens'] for r in group) if group[0]['memory_tokens'] is not None else None))
    return summaries


def verify(dataset, rows, identity):
    expected={(r['case_id'],c) for r in dataset for c in r['conditions']}
    actual=[(r['case_id'],r['condition']) for r in rows]
    if len(actual)!=len(set(actual)) or set(actual)!=expected:
        raise ValueError('Incomplete or duplicate paired responses')
    lookup={r['case_id']:r for r in dataset}
    for r in rows:
        q=lookup[r['case_id']]; c=r['condition']
        if any(r[k]!=q[k] for k in ('seed','family','query')): raise ValueError('Case metadata mismatch')
        if r['backend']!=identity['backend'] or r['gold_answer']!=q['gold_answer']:
            raise ValueError('Backend or gold mismatch')
        if r['prompt']!=prompt_for(q,q['conditions'][c]): raise ValueError('Prompt mismatch')
        if r['evidence_ids']!=[m['memory_id'] for m in q['conditions'][c]]: raise ValueError('Evidence mismatch')
        if r['scores'] != score(r['generated_answer'],q['gold_answer']):
            raise ValueError('Score mismatch')
        if r['retrieval'] != q['retrieval'].get(c,{}):
            raise ValueError('Retrieval mismatch')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('result',type=Path)
    p.add_argument('--dataset',type=Path,default=Path(__file__).parent/'dataset.jsonl')
    a=p.parse_args()
    manifest=json.loads((a.result/'manifest.json').read_text())
    identity=manifest['identity']
    if digest(a.dataset)!=identity['dataset_sha256']: raise ValueError('Dataset hash mismatch')
    dataset=[json.loads(s) for s in a.dataset.read_text().splitlines()]
    if identity['limit'] is not None: dataset=dataset[:identity['limit']]
    rows=[json.loads(s) for s in (a.result/'responses.jsonl').read_text().splitlines()]
    verify(dataset, rows, identity)
    table=summarize(rows)
    (a.result/'verification.json').write_text(json.dumps(dict(status='PASS',cases=len(dataset),responses=len(rows),
        checks=['complete paired coverage','unique responses','dataset hash','gold and evidence','prompt','scores','retrieval metrics','backend']),indent=2))
    (a.result/'summary.json').write_text(json.dumps(table,indent=2))
    with (a.result/'summary.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    # Post-hoc diagnostic only: fixed first-line boundary, never search for gold.
    sensitivity=[]
    for t in table:
        group=[r for r in rows if r['condition']==t['condition']]
        first=[score(r['generated_answer'].split('\n',1)[0],r['gold_answer'])['exact_match'] for r in group]
        sensitivity.append(dict(condition=t['condition'],strict_em=t['exact_match'],
            first_line_em=statistics.mean(first),multiline_answers=sum('\n' in r['generated_answer'] for r in group)))
    (a.result/'format-sensitivity.json').write_text(json.dumps(sensitivity,indent=2))
    lookup={(r['case_id'],r['condition']):r for r in rows}
    candidates={}
    for r in rows:
        base=lookup[(r['case_id'],'no_memory')]
        categories=[]
        if r['scores']['exact_match']>base['scores']['exact_match']: categories.append('positive_utility')
        if r['scores']['exact_match']<base['scores']['exact_match']: categories.append('negative_utility')
        if r.get('retrieval',{}).get('recall_at_k')==0: categories.append('retrieval_miss')
        if r.get('retrieval',{}).get('recall_at_k')==1 and r['scores']['exact_match']==0: categories.append('hit_but_wrong')
        if r.get('retrieval',{}).get('recall_at_k')==1 and score(r['generated_answer'].split('\n',1)[0],r['gold_answer'])['exact_match']==0: categories.append('hit_but_wrong_value')
        if r['condition']=='conflicting' and r['scores']['exact_match']<lookup[(r['case_id'],'relevant')]['scores']['exact_match']: categories.append('conflict_degradation')
        if r['condition']=='consolidation_strip_temporal_cue' and r['scores']['exact_match']<lookup[(r['case_id'],'conflicting')]['scores']['exact_match']: categories.append('consolidation_degradation')
        for category in categories:
            if category not in candidates and len(candidates)<5:
                candidates[category]=dict(row=r,baseline=base)
    (a.result/'cases.json').write_text(json.dumps(candidates,indent=2))
    lines=['# 第三阶段：记忆效用实验结果','',f"Backend: `{identity['backend']}`；{len(dataset)} 个问题，{len(rows)} 条配对回答。",'',
           '| 条件 | EM | F1 | 效用增益 | Recall@k | 命中但答错 | 记忆 tokens |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for t in table:
        recall='—' if t['recall'] is None else f"{t['recall']:.3f}"
        tokens='—' if t['memory_tokens'] is None else f"{t['memory_tokens']:.1f}"
        lines.append(f"| {t['condition']} | {t['exact_match']:.3f} | {t['f1']:.3f} | {t['utility']:+.3f} | {recall} | {t['hit_but_wrong'] if t['hit_but_wrong'] is not None else '—'} | {tokens} |")
    lines+=['','## 输出格式敏感性（事后诊断，不替换主指标）','',
        '观察到模型续写问答后，额外按第一个换行截取答案并重算 EM；该规则不搜索标准答案。以下仅检查格式影响，不能当作预注册的主结论。','',
        '| 条件 | 全输出 EM | 首行 EM | 多行回答数 |','|---|---:|---:|---:|']
    for t in sensitivity:
        lines.append(f"| {t['condition']} | {t['strict_em']:.3f} | {t['first_line_em']:.3f} | {t['multiline_answers']} |")
    lines+=['','## 诊断案例（按类型选择，不代表发生率）','']
    for kind,case in candidates.items():
        r=case['row']
        lines += [f"### {kind}: {r['case_id']}",f"- 问题：{r['query']}",f"- 条件：{r['condition']}；标准答案：{r['gold_answer']}",
                  f"- 无记忆回答：{case['baseline']['generated_answer']!r}",f"- 当前回答：{r['generated_answer']!r}",f"- 提供证据：{', '.join(r['evidence_ids'])}",'']
    lines+=['## 解释范围','',
        '这是单个生成模型在英文合成事实上的描述性实验。54 个问题来自 18 个主体/关系模板 × 3 种子，不能视为 54 个完全独立主题；seed_sd 是种子间总体标准差，不是置信区间。',
        '五条件是人工控制证据的利用实验；retrieved 条件回放第二阶段 10,000 条均衡语料的真实 top-k，不重新测检索延迟。',
        'Relevant 仅提供当前事实；Conflicting 同时提供 Currently/Previously 新旧事实，顺序交替；Consolidation 按事件顺序从同一新旧对中选择最新事实并删除前缀，是规则整合，不是学习式摘要。',
        '五条件没有匹配 token 长度，因此条件差异同时包含内容和长度变化；top-k 是上下文预算消融，未做独立固定 token 预算实验。',
        '命中但答错是行为诊断，不能证明模型内部未使用证据。整合后答错也不等于事实损坏；当前规则整合保留正确事实，格式敏感性需单独解释。',
        'EM 严格比较规范化短答案；F1 补充反映词重叠，不能把部分词重叠视为事实正确。未评测证据引用准确率。UNKNOWN 按任务答案计零分，无记忆时猜对也计分。',
        '记忆 token 由生成模型 tokenizer 计算；seconds 含首条模型加载，不能作为稳定推理延迟结论。',
        '完整原始提示、回答与证据 ID 见 responses.jsonl；统计及核验见 summary.csv / verification.json。']
    if identity['backend']=='test': lines.insert(2,'**仅工程测试，不能据此报告模型效用。**')
    (a.result/'report.md').write_text('\n'.join(lines)+'\n')
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/longmem-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax=plt.subplots(figsize=(11,3.4)); ax.axis('off')
    cells=[[t['condition'],f"{t['exact_match']:.3f}",f"{t['utility']:+.3f}",str(t['positive']),str(t['negative'])] for t in table[:5]]
    artist=ax.table(cellText=cells,colLabels=['Condition','Exact match','Utility gain','Positive cases','Negative cases'],loc='center',cellLoc='center')
    artist.auto_set_font_size(False);artist.set_fontsize(11);artist.scale(1,1.7)
    ax.set_title(f"Memory utility | {identity['backend']} | n={len(dataset)}")
    fig.tight_layout();fig.savefig(a.result/'memory-utility-table.png',dpi=180);plt.close(fig)
    print(f'PASS: {len(dataset)} cases, {len(rows)} paired responses; report exported')

if __name__=='__main__': main()
