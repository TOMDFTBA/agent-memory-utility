# E3 supplement protocol v1

This is a post-test descriptive analysis and stronger replay audit of the completed e3-formal-model run. It does not change its protocol, sources, model, policies, labels, answers or primary comparison. No new answer/importance generation or model fitting is permitted.

## Identity and reuse

New lifecycle: e3_supplement.py / utility_retention.e3_supplement. New output: results/e3-supplement-model. The original formal audit must pass before work and at completion. Hash every parent top-level artifact, freeze this protocol and supplemental source snapshot, and require the same identity on resume. Use the existing Engine, historical_features, serialize, predict, select, baseline_scores, dedup_select, similarity_table, response_key and formal audit; do not edit their frozen implementations.

## Descriptive failure and budget analysis

For every policy plan/query, derive an operational failure category from saved EM, annotated alternative supporting sets, actual token costs, storage and context:

1. correct: EM=1, regardless of support annotation; report correct-without-annotated-context separately.
2. budget_infeasible: EM=0 and no annotated complete support set can fit the absolute store budget.
3. support_not_retained: a support set can fit, but no complete annotated support set was retained. This is a selection outcome, not proof that the predictor alone caused it.
4. support_not_retrieved: a complete support set was stored but none entered context in full.
5. supported_but_wrong: a complete support set entered context, but EM=0.

Use minimum sum of unique member costs across alternative support sets; redundancy alternatives are not incorrectly summed together. Full is storage-exempt. These labels diagnose observed pipeline stages, not counterfactual causes. Record no-record-fits, retained count, realized budget utilization, unused tokens and support feasibility. Aggregate questions/seeds within trajectory first, then trajectories; all five category rates sum to one. Report 25%/50% prominently, other budgets as context.

## Gain distribution and E4 cases

For utility_aware versus frozen importance, report paired win/tie/loss per trajectory at each budget and primary-average, plus each pressure family. Use 1e-12 tolerance for arithmetic ties. Reuse saved trajectory summaries (audit-verified), do not add a new primary endpoint. Do not choose a new baseline based on these results.

Case selection is post hoc and deterministic: first two snapshot/query IDs satisfying each category, preferring primary budgets in ascending order. Cover budget-infeasible utility failures, feasible support not retained, support not retrieved, redundancy hindsight failures with utility success, and complementarity with all support read but wrong. Explicitly report absent types. Each case carries memory IDs/content/cost, predictor score, LOO, support sets, retained and context IDs, actual output/gold, and parent response keys. They are explanatory handoff examples, not new blind E4 data or complete nonadditivity evidence.

## Strong model replay

Recompute all 96 historical feature rows, 24 similarity matrices and 600 retrieval conditions from the frozen model and saved snapshot/subset/query. Check every ranking ID/order and actual context exactly. Numeric feature similarities, matrix entries and retrieval scores use atol=1e-6, rtol=1e-5; all costs, counts, recency, token lengths and IDs must match exactly. Replay predictions with recomputed features and all deployable plans with recomputed similarities; predictions use the same tolerance, selected subsets must match exactly. Recount all memory costs and all saved importance/answer prompt, output and memory-context token lengths. Save recomputed values, maxima of numeric differences and individual comparison records. Never regenerate text. A discrepancy fails the supplement and does not silently rewrite the parent.

## Cost accounting and microbenchmark

Separate model identity/setup, historical feature computation, semantic similarity computation, policy scoring from cached historical inputs, budget selection, and original retrieval+generation. Synchronize GPU before/after model replay timings. The old selection_seconds measure only timed selection regions; old prediction and some baseline scoring were outside that clock.

Benchmark cached policy scoring and selection for all 24 snapshots/four budgets, 3 warm-ups and 30 recorded repetitions, reporting medians and p95 plus raw samples. utility_aware scores its 96 feature rows in one batch, as in formal execution. random runs the original three selection seeds and reports that scope; do not compare its total to a single seed without saying so. Dedup representative construction belongs to its selection step; importance score-map parsing/lookup is cached preparation, not fresh LLM scoring. Validate benchmark subsets against frozen plans. These CPU microbenchmarks characterize this tiny workload, not production latency or unmeasured original-run timings.

Original importance durations/tokens remain observed original costs (including any first-call initialization); original answer duration includes retrieval and generation together and cannot retrospectively be split. Replay historical/similarity times and cached scorer/selector microbenchmarks are new measurements, explicitly labeled, not replacements for original costs. No full end-to-end latency claim or synthetic sum of incompatible cold/warm measurements.

## Completion

Require original audit, supplemental analysis replay, strong model replay, token/plan validation and finite nonnegative cost samples. Save raw and derived artifacts, hashes, a Chinese report, E4 case list and implementation log. Test-backend fixtures may test boundaries but are never model evidence. Supplemental auditing must work without modifying the frozen formal modules. A COMPLETE resume is read-only; partial GPU replay resumes only under matching input/source/model identities.
