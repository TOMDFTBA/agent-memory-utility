"""Read-only report renderer for the audited E4 schema."""
from collections import defaultdict
from statistics import mean
from longmem.experiment_io import read_json, read_jsonl
from .e4_analysis import CORE, EXACT_LOO


def report(output):
    summaries = read_json(output/'cohort-summaries.json')
    ties = read_json(output/'ties.json')
    interactions = read_json(output/'interactions.json')
    controls = read_jsonl(output/'context-controls.jsonl')
    cohorts = read_json(output/'cohorts.json')
    stability = read_json(output/'winner-stability.json')
    cost = read_json(output/'cost-report.json')
    audit = read_json(output/'audit.json')
    backend = read_json(output/'manifest.json')['backend']
    lines = ['# v0.2 E4：集合依赖诊断', '', f'后端：{backend}。独立审计：{audit["passed"]}。', '',
             'e3_posthoc是已观察E3测试集的事后解释；e4_independent是运行前冻结的新实体/事实轨迹。',
             '两组共享合成语法，各24条轨迹、四场景等比例、每条4记忆和2题；不构成分布外或自然用户泛化证据。', '',
             '每快照完整枚举16个存储集合，每子集重新检索，固定系统、top_k=3、B_read=1024。',
             'best_subset仅是该窗口、系统、预算、有限候选和单次确定性评估下的经验最高分。',
             '10%预算是参照，跨预算主平均仅含25%/50%/75%。', '']
    for cohort, summary in summaries.items():
        lines += [f'## {cohort}', '', '| 集合/参照 | 10% EM | 25% EM | 50% EM | 75% EM |', '|---|---:|---:|---:|---:|']
        for name in CORE+('importance', 'recency', 'retrieval_frequency', 'semantic_dedup', 'random', 'full', 'no_memory'):
            rr = sorted([r for r in summary['aggregates'] if r['candidate'] == name], key=lambda r: r['budget_ratio'])
            lines.append('| '+name+' | '+' | '.join(f'{r["metrics"]["answer.exact_match"]:.4f}' for r in rr)+' |')
        lines += ['', '三个主预算先在轨迹内平均；轨迹bootstrap描述性95%区间，未做多重比较校正。', '',
                  '| 对照 | EM差异 | 区间 |', '|---|---:|---|']
        for r in summary['paired_differences']:
            if r['budget_ratio'] == 'primary_average':
                low, high = r['trajectory_bootstrap_95_ci']
                lines.append(f'| {r["candidate"]} − {r["baseline"]} | {r["metrics"]["answer.paired_em_difference"]:+.4f} | [{low:.4f}, {high:.4f}] |')
        lines += ['', '### LOO并列最优', '',
                  '| 场景（主预算平均） | 选定EM | 最低EM均值 | 最高EM均值 | best_subset EM |', '|---|---:|---:|---:|---:|']
        tt = [r for r in ties if r['cohort'] == cohort and r['candidate'] == EXACT_LOO and r['budget_ratio'] != .1]
        for scenario in sorted({r['scenario'] for r in tt}):
            rr = [r for r in tt if r['scenario'] == scenario]
            keys = ('diagnostic.selected_em', 'diagnostic.tie_em_min', 'diagnostic.tie_em_max', 'diagnostic.best_subset_em')
            lines.append('| '+scenario+' | '+' | '.join(f'{mean(r["metrics"][k] for r in rr):.4f}' for k in keys)+' |')
        lines += ['', '并列规则：分数差≤1e-12时优先小token成本、少记录、稳定ID；不读取未来EM打破加总目标并列。',
                  '最优范围包含好坏集合时，说明目标不可辨别，不能称所有LOO最优解都失败。', '',
                  '### 标注支持对交互', '', '| 支持对 | 背景 | 个数 | 负/零/正 | 平均交互 |', '|---|---|---:|---|---:|']
        for role in ('redundant_support', 'complementary_support'):
            for background in ('empty', 'all_backgrounds'):
                rr = [r for r in interactions if r['cohort'] == cohort and r['pair_role'] == role and
                      (background != 'empty' or not r['background_ids'])]
                values = [r['metrics']['diagnostic.interaction'] for r in rr]
                signs = f'{sum(v < 0 for v in values)}/{sum(v == 0 for v in values)}/{sum(v > 0 for v in values)}'
                lines.append(f'| {role} | {background} | {len(rr)} | {signs} | {mean(values):.4f} |')
        lines += ['', '背景条件相关，不是独立样本；语义互补不保证当前模型能组合答案。', '',
                  '### 互补上下文对照', '', '| 条件 | EM |', '|---|---:|']
        for condition in sorted({r['condition'] for r in controls}):
            rr = [r for r in controls if cohorts[r['snapshot_id']] == cohort and r['condition'] == condition]
            lines.append(f'| {condition} | {mean(r["metrics"]["answer.exact_match"] for r in rr):.4f} |')
        lines += ['', 'forward/reversed按支持ID正序/反序；context_deletion从full实际上下文删指定支持项、不补位。',
                  '这些是hindsight上下文诊断，不参与存储排名，不把长度/顺序/覆盖变化解释成单一内部机制。', '',
                  '### 主方法失败位置', '', '| 预算 | 答对 | 放不下 | 未保留 | 未读全 | 读全答错 |', '|---|---:|---:|---:|---:|---:|']
        for r in summary['failures']['aggregates']:
            if r['candidate'] == 'utility_aware' and r['scenario'] == 'all':
                keys = ['diagnostic.'+k+'_rate' for k in ('correct', 'budget_infeasible', 'support_not_retained', 'support_not_retrieved', 'supported_but_wrong')]
                lines.append(f'| {r["budget_ratio"]:.0%} | '+' | '.join(f'{r["metrics"][k]:.2%}' for k in keys)+' |')
        lines += ['']
    lines += ['## 稳定性、成本与边界', '',
              f'{audit["response_count"]}个枚举回答、{audit["subset_count"]}个子集分数、{audit["interaction_count"]}个背景交互可重算。',
              f'独立重新执行{stability["repeated_conditions"]}个best_subset条件，答案/评分变化{len(stability["changed_conditions"])}个。',
              '同seed重复仅验证确定性，不估计随机解码方差、不消除同一窗口最大值选择的泛化乐观偏差。',
              f'继承{cost["inherited_answer_count"]}个回答；新增{cost["new_answer_count"]}个回答（含复核及上下文），新增{cost["new_importance_count"]}个importance。',
              f'新增逐例累计模型时间{cost["cumulative_model_seconds"]:.1f}秒；不等于含初始化、身份摘要、历史特征及审计的墙钟时间。', '',
              '## v0.3判断规则', '',
              '- 精确预测分数和与主方法之差：检查预算选择器；实际EM可能下降，分数提升不保证回答改善。',
              '- 真实LOO与预测之差：仅作标签/预测对照，不强制非负。',
              '- best_subset与LOO最优得分范围：区分目标不能打破并列与所有加总最优解都落后。',
              '- 互补best_subset仍低且支持读全：优先检查固定系统组合回答限制，不能直接归结为需要graph。',
              '- 未来修改模型须用新版本与新盲测；本轮不重新拟合。', '',
              '完整数据见cohort-summaries.json、ties.json、interactions.json；逐集合案例见cases.md。']
    (output/'report.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    cases(output)


def cases(output):
    snapshots = read_json(output/'dataset.json')
    cohorts = read_json(output/'cohorts.json')
    table = read_json(output/'subset-scores.json')
    features = read_json(output/'features.json')
    predictions = read_json(output/'predictions.json')
    labels = read_json(output/'labels.json')
    values = {(r['snapshot_id'], r['memory_id']): (r['features']['memory_tokens'], p)
              for r, p in zip(features, predictions, strict=True)}
    loo = {(r['snapshot_id'], r['memory_id']): r['loo_value'] for r in labels}
    groups = defaultdict(list)
    for s in snapshots:
        groups[cohorts[s['snapshot_id']], s['scenario']].append(s)
    lines = ['# E4代表性案例', '', '每组每场景按稳定snapshot ID取前两例，避免按事后最大差距选例。', '']
    for (cohort, scenario), ss in sorted(groups.items()):
        for s in sorted(ss, key=lambda s: s['snapshot_id'])[:2]:
            sid = s['snapshot_id']
            lines += [f'## {cohort} / {scenario} / {sid}', '',
                      f'问题：{s["future_queries"][0]["text"]}；答案：{s["future_queries"][0]["gold_answer"]}。',
                      f'支持集合：{s["future_queries"][0]["supporting_memory_sets"]}', '',
                      '| ID | tokens | predicted | LOO | 内容 |', '|---|---:|---:|---:|---|']
            for m in s['memories']:
                tokens, pred = values[sid, m['memory_id']]
                lines.append(f'| {m["memory_id"]} | {tokens} | {pred:.4f} | {loo[sid, m["memory_id"]]:.4f} | {m["content"]} |')
            lines += ['', '| 存储集合 | tokens | 窗口EM |', '|---|---:|---:|']
            for r in table:
                if r['snapshot_id'] == sid:
                    lines.append(f'| {r["storage_ids"]} | {r["store_tokens"]} | {r["metrics"]["answer.exact_match"]:.4f} |')
            lines += ['']
    (output/'cases.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
