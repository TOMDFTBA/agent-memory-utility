# E3 Formal Test Protocol

Status: frozen for future execution. This protocol defines the first formal test after the E2 predictor and E3 supplemental baselines have been selected. It must not be edited after any E3 formal test run starts.

## Frozen Inputs

- E2 predictor: `results/e2-development-model/frozen-predictor.json`
- E2 predictor SHA-256: `27f8919e662f20b34c1b6b72f37d203c05f6c88fc31d3d30008d802fa477671f`
- E3 supplemental strategies: `results/e3-baselines-development-model/frozen-strategies.json`
- E3 supplemental strategies SHA-256: `c3a1e393ded3917d4d88a53ff42f50cae1af6f86e4a26943bfbbb3a7379b6cb8`
- E3 development audit: `results/e3-baselines-development-model/audit.json`
- E3 development audit SHA-256: `05989d2dc400c7e7adcf65ffc852786ad4cda2bdf32b1ba1c596db105c464d06`

The E3 formal runner must verify these hashes before generating data or model responses.

## Dataset

Generate a new held-out test set from the same four pressure families used in the v0.2 extension dataset:

- `old_but_useful`
- `frequent_but_useless`
- `redundancy`
- `complementarity`

The formal set contains 24 trajectories, six per pressure family. Each trajectory contains four memories, historical queries available before the snapshot, and two future queries. Future queries and labels may be used only for evaluation, never for selection or storage scoring.

Dataset seeds:

- structure seed: `2026091401`
- surface seed: `2026091402`

The generated formal set must be disjoint from all E1 extension train, validation, and test trajectories by entity, gold answer, memory text, and query text. If the generator cannot satisfy this, stop and version a new formal protocol before running any model answers.

## Evaluated Policies

The deployable policies are:

- `utility_aware`: the frozen E2 `full-a10` predictor.
- `recency`: newest memories first.
- `retrieval_frequency`: highest historical retrieval frequency first.
- `importance`: frozen prompt, parser, fallback, and seed from `frozen-strategies.json`.
- `semantic_dedup`: frozen threshold `0.8`, newest-first representative selection, and recency fill over representatives.
- `random`: three frozen random seeds, averaged.

The diagnostic upper and lower bounds are:

- `full`: all memories stored.
- `no_memory`: no stored memories.
- `hindsight_loo`: label-based retrospective bound, computed only after all deployable plans and answers have been saved.

Do not refit the predictor, retune alpha, retune budgets, retune the dedup threshold, alter the importance prompt, or choose a new strongest heuristic on the formal test set.

## Budgets And Retrieval

Storage budget ratios:

- `0.10`
- `0.25`
- `0.50`
- `0.75`

Primary comparison budgets:

- `0.25`
- `0.50`
- `0.75`

Use read budget `1024`, top-k `3`, generation seed `20260912`, and the model identity recorded in `frozen-strategies.json`. The 10% budget is reported but excluded from the primary average because it produced empty selections throughout E2 development.

## Metrics

Primary metric: exact match averaged over the three primary budgets and all formal trajectories.

Primary contrast: `utility_aware` minus the strongest frozen heuristic, which is `importance`.

Secondary contrasts:

- `utility_aware` minus `recency`
- `utility_aware` minus `retrieval_frequency`
- `utility_aware` minus `semantic_dedup`
- `utility_aware` minus `random`
- `utility_aware` compared with `hindsight_loo`, `full`, and `no_memory` as diagnostics

Report per-budget exact match, paired trajectory-level exact-match differences, and 95% bootstrap intervals with 5000 resamples using seed `20260912`. Bootstrap intervals are descriptive; the formal pass condition is based on the predefined primary contrast and not on post hoc threshold changes.

## Execution Limits

Ceilings for one formal run:

- at most 96 importance generations
- at most 1500 answer generations
- at most 7200 seconds cumulative per-example model time

If a ceiling is exceeded, stop and report the partial run as failed. Do not drop conditions to fit the limit.

## Required Artifacts

The formal run must write:

- dataset manifest and frozen dataset JSON
- policy plans
- model responses
- summary metrics
- paired differences
- audit report
- source snapshot
- model identity
- final report

The audit must replay dataset identity, all policy plans, budget constraints, answer scoring, pairwise summaries, frozen-input hashes, current source hashes, and model identity.
