"""Aggregate seed-level metrics and render reproducible tables and figures."""
import csv
import json
import os
import sys
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/longmem-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(sys.argv[1])
manifest=json.loads((root/'manifest.json').read_text())
if manifest['status']!='COMPLETE': raise ValueError('run is incomplete')
rows=list(csv.DictReader((root/'results.csv').open()))
keys=['recall_at_1','recall_at_5','mrr','exact_recall_at_1','exact_recall_at_5','exact_mrr',
      'target_fact_retained','superseded_fact_at_1','retrieval_p50_ms','retrieval_p95_ms',
      'query_p50_ms','query_p95_ms','search_p50_ms','search_p95_ms','index_bytes',
      'retrieved_tokens','selection_seconds','index_build_seconds']
groups={}
for row in rows:
    key=(row['scenario'],int(row['size']),row['policy'],float(row['budget']))
    groups.setdefault(key,[]).append(row)
summary=[]
for key,group in sorted(groups.items()):
    item=dict(zip(['scenario','size','policy','budget'],key),seeds=len(group))
    for metric in keys:
        vals=[float(r[metric]) for r in group]
        item[metric]=float(np.mean(vals));item[metric+'_std']=float(np.std(vals))
    summary.append(item)
(root/'summary.json').write_text(json.dumps(summary,indent=2))
with (root/'summary.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=summary[0]);w.writeheader();w.writerows(summary)
label='MiniCPM' if manifest['backend']=='minicpm' else 'ENGINEERING TEST ONLY'
policies=['full','recency','importance','semantic_dedup']
fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
for ax,scenario in zip(axes,['old','balanced']):
    for policy in policies:
        group=[r for r in summary if r['scenario']==scenario and r['policy']==policy and r['budget']==(1 if policy=='full' else .5)]
        ax.errorbar([r['size'] for r in group],[r['recall_at_5'] for r in group],yerr=[r['recall_at_5_std'] for r in group],marker='o',capsize=3,label=policy)
    ax.set_xscale('log');ax.set_ylim(-.05,1.05);ax.set_title(scenario+' target timestamps');ax.set_xlabel('Input memories');ax.set_ylabel('Equivalent-fact Recall@5');ax.grid(alpha=.2)
axes[0].legend(fontsize=8)
fig.suptitle(label+' — full baseline vs 50% retained; mean ± seed SD')
fig.savefig(root/'memory-size-vs-recall.png',dpi=170);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
maxsize=max(r['size'] for r in summary)
for ax,scenario in zip(axes,['old','balanced']):
    for policy in policies:
        group=[r for r in summary if r['scenario']==scenario and r['size']==maxsize and r['policy']==policy]
        ax.errorbar([1-r['budget'] for r in group],[r['recall_at_5'] for r in group],yerr=[r['recall_at_5_std'] for r in group],marker='o',capsize=3,label=policy)
    ax.set_xlim(-.05,.8);ax.set_ylim(-.05,1.05);ax.set_title(scenario);ax.set_xlabel('Compression ratio');ax.set_ylabel('Equivalent-fact Recall@5');ax.grid(alpha=.2)
axes[0].legend(fontsize=8);fig.suptitle(f'{label} — {maxsize:,} memories; matched budgets')
fig.savefig(root/'compression-vs-recall.png',dpi=170);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
for policy in policies:
    group=[r for r in summary if r['scenario']=='balanced' and r['policy']==policy and r['budget']==(1 if policy=='full' else .5)]
    axes[0].plot([r['size'] for r in group],[r['search_p50_ms'] for r in group],marker='o',label=policy)
    axes[1].plot([r['size'] for r in group],[r['index_bytes']/1024**2 for r in group],marker='o',label=policy)
for ax in axes: ax.set_xlabel('Input memories');ax.grid(alpha=.2)
axes[0].set_ylabel('FAISS-only P50 (ms)');axes[1].set_ylabel('FAISS index (MiB)');axes[0].legend(fontsize=8)
fig.suptitle(label+' — balanced; full baseline vs 50% retained')
fig.savefig(root/'cost-vs-size.png',dpi=170);plt.close(fig)
lines=['# 第二阶段：记忆预算实验 v0.1','',f'运行状态：{manifest["status"]}；后端：{manifest["backend"]}；{len(rows)} 组结果。',
       '', '主表：全量基线保留 100%，其他策略保留 50%。Recall 按等价事实计算；完整预算和精确 ID 指标见 summary.csv。', '',
       '| 场景 | 规模 | 策略 | R@1 | R@5 ± SD | MRR | P50 ms | P95 ms | 索引 MiB | tokens |',
       '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|']
for r in summary:
    if r['budget']!=(1 if r['policy']=='full' else .5):continue
    lines.append(f"| {r['scenario']} | {r['size']} | {r['policy']} | {r['recall_at_1']:.3f} | {r['recall_at_5']:.3f} ± {r['recall_at_5_std']:.3f} | {r['mrr']:.3f} | {r['retrieval_p50_ms']:.2f} | {r['retrieval_p95_ms']:.2f} | {r['index_bytes']/1024**2:.2f} | {r['retrieved_tokens']:.1f} |")
lines += ['', '延迟是查询编码与内存搜索的分项样本相加，表中为各随机种子分位数的均值；不包含加载、日志重放、持久化或 MCP。SD 为三次种子结果的总体标准差，不是置信区间。', '',
          '![规模与召回](memory-size-vs-recall.png)', '', '![压缩与召回](compression-vs-recall.png)', '', '![规模与成本](cost-vs-size.png)', '',
          '## 解释边界', '',
          '- 24 个事实主题、6 种关系；18 个测试主题 × 4 个查询改写 = 72 条查询/种子。改写不是独立事实样本，跨种子也复用主题模板。',
          '- 固定 12 条完全重复记忆用于验证等价 ID 评分；重复比例随规模扩大而下降，不是固定重复率实验。',
          '- 重要度是随机元数据，仅代表这一基线，不代表经过人工或效用学习的重要度。',
          '- 语义策略先按时间贪心去重，再按预算补回被抑制项，属于“去重优先的固定预算保留”；不等同于单纯阈值去重或摘要合并。',
          '- 时间元数据决定保留顺序，检索文本仅含 Currently/Previously，不包含绝对时间。',
          '- 开发集仅校准去重阈值，使用单独 seed=77；主实验查询与阈值选择分离。',
          '- 小样本、英文合成模板、本机单线程 FAISS；不能推广为真实聊天或所有硬件的结论。',
          '- 完整接口延迟、摘要合并的事实保真、多模态和模型利用效用均不在本实验中。']
(root/'report.md').write_text('\n'.join(lines)+'\n')
print('Wrote',root/'report.md')
