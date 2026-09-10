"""Generate evidence-backed observations and candidate cases for phase 3."""
import json
import sys
from pathlib import Path
root=Path(sys.argv[1]);summary=json.loads((root/'summary.json').read_text())
lookup={(r['scenario'],r['size'],r['policy'],r['budget']):r for r in summary}
maxsize=max(r['size'] for r in summary);minsize=min(r['size'] for r in summary)
full=lookup['balanced',maxsize,'full',1.]
small=lookup['balanced',minsize,'full',1.]
sem=lookup['balanced',maxsize,'semantic_dedup',.5]
rec=lookup['balanced',maxsize,'recency',.5]
old=lookup['old',maxsize,'recency',.5]
lines=['# 第二阶段实验结论与第三阶段衔接','',
 f'1. 全量历史从 {minsize} 增至 {maxsize} 条时，等价事实 Recall@5 从 {small["recall_at_5"]:.3f} 变为 {full["recall_at_5"]:.3f}，Recall@1 从 {small["recall_at_1"]:.3f} 变为 {full["recall_at_1"]:.3f}。这反映该固定查询集面对新增干扰项的变化，不是新增主体问题的评估。',
 f'2. 在 {maxsize} 条、保留 50% 的同等预算下，均衡场景的近期策略 Recall@5 为 {rec["recall_at_5"]:.3f}，语义去重优先策略为 {sem["recall_at_5"]:.3f}；旧知识场景近期策略为 {old["recall_at_5"]:.3f}。策略表现依赖目标事实的时间分布。',
 f'3. 全量 {maxsize} 条的 FAISS 索引为 {full["index_bytes"]/1024**2:.2f} MiB，50% 预算索引为 {sem["index_bytes"]/1024**2:.2f} MiB。全量内存搜索 P50 为 {full["search_p50_ms"]:.3f} ms，而查询编码 P50 为 {full["query_p50_ms"]:.3f} ms。分项合成检索 P50 为 {full["retrieval_p50_ms"]:.3f} ms，不代表完整服务延迟。', '',
 '## 额外归一化指标', '',
 '以下为端点描述性差值，不是线性拟合或因果结论。召回损失以百分点计，可以为负。', '',
 '| 场景 | 策略 | 预算 | 每压缩10%的 Recall@5 损失（百分点） |',
 '|---|---|---:|---:|']
for r in summary:
 if r['size']!=maxsize or r['policy']=='full':continue
 baseline=lookup[r['scenario'],maxsize,'full',1.]
 loss=(baseline['recall_at_5']-r['recall_at_5'])*100*.1/(1-r['budget'])
 lines.append(f'| {r["scenario"]} | {r["policy"]} | {r["budget"]:.0%} | {loss:.2f} |')
slope=(full['search_p50_ms']-small['search_p50_ms'])/((maxsize-minsize)/1000) if maxsize!=minsize else 0.0
lines += ['', f'均衡场景全量索引：从 {minsize} 到 {maxsize} 条，FAISS 搜索 P50 的端点差值约为 {slope:.4f} ms/千条。', '',
          '## 下一阶段', '',
          '使用 utility-candidates.json 中的代表性查询建立 No memory / Relevant / Irrelevant / Conflicting / Consolidated 五条件对照，比较检索命中与答案得分。候选案例是按失败类型挑选的诊断样本，不是无偏测试集。', '',
          '特别检查旧事实排第一时模型是否仍能利用 top-5 中的新事实；去重后目标缺失是否会损害答案；以及保留更多事实的收益能否抵消上下文开销。', '',
          '本阶段没有评估生成器得分，不能据此宣称哪种策略最有利于推理。主实验限制、阈值选择、计时口径及完整结果见 report.md 和上级 README。']
(root/'observations.md').write_text('\n'.join(lines)+'\n')
cases=[];counts={}
for folder in sorted(root.glob(f'*-{maxsize}-*')):
 records={m['memory_id']:m for m in json.loads((folder/'dataset.json').read_text())['records']}
 for sub in sorted(folder.iterdir()):
  if not sub.is_dir():continue
  if sub.name not in ['full-1','recency-0.5','semantic_dedup-0.5']:continue
  retained=json.loads((sub/'index.json').read_text())['memory_ids']
  facts={records[mid]['canonical_id'] for mid in retained}
  for q in json.loads((sub/'predictions.json').read_text()):
   query=q['query']
   if query['target_canonical_id'] not in facts: kind='target_pruned'
   elif q['canonical_hits'][0]==query['superseded_memory_id']:kind='obsolete_rank1'
   elif q['canonical_hits'][0]==query['target_canonical_id']:kind='correct_rank1'
   elif query['target_canonical_id'] not in q['canonical_hits']:kind='retained_but_not_top5'
   else:kind='correct_below_rank1'
   if counts.get(kind,0)>=2:continue
   counts[kind]=counts.get(kind,0)+1
   cases.append(dict(kind=kind,case=str(sub.relative_to(root)),query=query['query'],
       target=records[query['target_memory_id']],retrieved=[records[mid] for mid in q['hits']]))
(root/'utility-candidates.json').write_text(json.dumps(cases,indent=2,ensure_ascii=False))
print('\n'.join(lines[:5]));print('diagnostic cases:',counts)
