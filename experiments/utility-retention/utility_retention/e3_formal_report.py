"""E3 reports consume formal schema; no selection, training or evaluation side effects."""
from collections import defaultdict
from statistics import mean

from longmem.experiment_io import read_json, read_jsonl, write_json


def report(output):
    manifest = read_json(output/'manifest.json')
    summary = read_json(output/'summary.json')
    plans = read_json(output/'plans.json')
    importance = read_jsonl(output/'importance.jsonl')
    responses = read_jsonl(output/'responses.jsonl')
    settings = manifest['parameters']
    ratios = settings['budget_ratios']
    names = ['utility_aware', 'importance', 'recency', 'retrieval_frequency', 'semantic_dedup',
             'random', 'hindsight_loo', 'full', 'no_memory']
    lookup = {(r['candidate'], r['budget_ratio']): r for r in summary['aggregates']}
    primary = summary['primary_result']
    cost = dict(importance_generations=len(importance), answer_generations=len(responses),
                importance_seconds=sum(r['duration_seconds'] for r in importance),
                answer_seconds=sum(r['duration_seconds'] for r in responses),
                history_similarity_seconds=manifest['history_similarity_seconds'],
                selection_seconds_by_candidate={n: sum(p['selection_seconds'] for p in plans if p['candidate'] == n)
                                                for n in names},
                importance_input_tokens=sum(r['input_tokens'] for r in importance),
                importance_output_tokens=sum(r['output_tokens'] for r in importance),
                answer_input_tokens=sum(r['input_tokens'] for r in responses),
                answer_output_tokens=sum(r['output_tokens'] for r in responses),
                importance_valid_fraction=mean(r['parsed']['valid'] for r in importance))
    write_json(output/'cost-report.json', cost)
    lines = ['# v0.2 E3 正式预算保留评估', '',
             f"后端：{manifest['backend']}。24条新轨迹，四类压力场景各6条，每条4条记忆、2个相关问题。",
             '主预测器固定full-a10；最强启发式固定importance。未重新拟合或用测试结果选择策略。', '',
             f"主比较（三预算轨迹内平均）：utility_aware − importance = {primary['metrics']['answer.paired_em_difference']:+.4f}；"
             f"轨迹bootstrap 95%区间 {primary['trajectory_bootstrap_95_ci']}；解释：{primary['interpretation']}。", '',
             '| 策略 | 10% EM | 25% EM | 50% EM | 75% EM |', '|---|---:|---:|---:|---:|']
    for name in names:
        lines.append('| '+name+' | '+' | '.join(f"{lookup[name, r]['metrics']['answer.exact_match']:.3f}" for r in ratios)+' |')
    lines += ['', '## 配对差异', '', '| 参照 | 预算 | EM差异 | 95%区间 |', '|---|---|---:|---|']
    for r in summary['paired_differences']:
        lines.append(f"| {r['baseline']} | {r['budget_ratio']} | {r['metrics']['answer.paired_em_difference']:+.4f} | {r['trajectory_bootstrap_95_ci']} |")
    lines += ['', '## 分场景 EM', '', '| 策略 | 预算 | old | frequent | redundancy | complementarity |', '|---|---|---:|---:|---:|---:|']
    families = settings['dataset']['families']
    for name in names:
        for ratio in settings['primary_budget_ratios']:
            lines.append(f'| {name} | {ratio:.0%} | '+' | '.join(f"{lookup[name, ratio]['scenario_em'][f]:.3f}" for f in families)+' |')
    lines += ['', '## 实际预算和成本', '', '| 策略 | 预算 | 存储tokens | 读取tokens | 空集比例 | F1 |', '|---|---|---:|---:|---:|---:|']
    for name in names:
        for ratio in ratios:
            m = lookup[name, ratio]['metrics']
            lines.append(f"| {name} | {ratio:.0%} | {m['cost.store_tokens']:.1f} | {m['cost.read_tokens']:.1f} | {m['retention.empty_rate']:.3f} | {m['answer.token_f1']:.3f} |")
    lines += ['', f"Importance评分{len(importance)}次，{cost['importance_seconds']:.1f}秒；有效率{cost['importance_valid_fraction']:.1%}。",
              f"唯一回答条件{len(responses)}次，{cost['answer_seconds']:.1f}秒；历史特征及相似度{cost['history_similarity_seconds']:.1f}秒。",
              '离线token总量、策略选择耗时详见cost-report.json。缓存只在本次冻结运行内复用；不同策略共享条件不重复计费。', '',
              '## 证据保留与生成失败', '', '| 策略 | 预算 | 场景 | 完整存储支持集 | 完整读取支持集 | 读全但答错 |', '|---|---|---|---:|---:|---:|']
    groups = defaultdict(list)
    for row in read_json(output/'support-diagnostics.json'):
        if row['candidate'] in ('utility_aware', 'importance', 'hindsight_loo', 'full') and row['budget_ratio'] in settings['primary_budget_ratios']:
            groups[row['candidate'], row['budget_ratio'], row['scenario']].append(row['metrics'])
    for (name, ratio, family), rows in sorted(groups.items()):
        lines.append(f'| {name} | {ratio:.0%} | {family} | '+' | '.join(f'{mean(r[k] for r in rows):.3f}' for k in
                     ('retention.support_set_complete', 'retrieval.support_set_complete', 'answer.hit_but_wrong'))+' |')
    lines += ['', '## 解释边界', '',
              'Full是无存储约束参照，不是性能上界；hindsight LOO使用未来标签，仅为诊断，不是集合上界。',
              '10%不进入主平均；实际是否空集由结果决定。随机策略先在轨迹内平均三个选择seed。',
              '置信区间重采样24条轨迹。每场景仅6条，两个问题询问同一事实；不将问题、预算或seed视为独立样本。',
              '数据与E1扩展所有split不重叠，但共享合成语法；四场景等比例不代表自然用户分布或真实长期记忆。',
              '固定MiniCPM系统、固定快照和窗口，一次保留决策；未执行在线更新、E4枚举或选择器误差分解。',
              '互补场景必须结合存储支持、上下文支持和生成错误解释；零LOO不能直接解释为可同时删除。',
              'test后端只验证工程行为，以上数字在test后端下不构成模型效果证据。', '']
    (output/'report.md').write_text('\n'.join(lines), encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    for name in names:
        ax.plot([100*r for r in ratios], [lookup[name, r]['metrics']['answer.exact_match'] for r in ratios],
                marker='o', label=name, linestyle='--' if name in ('full', 'no_memory', 'hindsight_loo') else '-')
    ax.set(xlabel='Storage budget (% of full snapshot tokens)', ylabel='Trajectory mean exact match',
           title=f'E3 budgeted retention ({manifest["backend"]} backend)', ylim=(-.03, 1.03))
    ax.grid(alpha=.2)
    ax.legend(loc='center left', bbox_to_anchor=(1, .5))
    fig.tight_layout()
    fig.savefig(output/'budget-curve.png', dpi=160)
    fig.savefig(output/'budget-curve.svg')
    plt.close(fig)
