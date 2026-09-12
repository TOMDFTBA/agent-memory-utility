# Stage 3: Memory-Utility Results

[Chinese version](report.md) | Backend: `transformers` | 54 questions | 594 paired responses

| Condition | EM | F1 | Utility gain | Recall@k | Hit but wrong | Memory tokens |
|---|---:|---:|---:|---:|---:|---:|
| no_memory | 0.000 | 0.000 | +0.000 | — | — | 0.0 |
| relevant | 1.000 | 1.000 | +1.000 | — | — | 11.7 |
| irrelevant | 0.241 | 0.241 | +0.241 | — | — | 13.6 |
| conflicting | 1.000 | 1.000 | +1.000 | — | — | 24.9 |
| consolidation_strip_temporal_cue | 0.352 | 0.417 | +0.352 | — | — | 9.7 |
| retrieved:full-1:k1 | 0.630 | 0.630 | +0.630 | 0.630 | 0 | 11.7 |
| retrieved:full-1:k3 | 0.889 | 0.912 | +0.889 | 1.000 | 6 | 38.7 |
| retrieved:full-1:k5 | 0.944 | 0.944 | +0.944 | 1.000 | 3 | 68.0 |
| retrieved:semantic_dedup-0.5:k1 | 0.296 | 0.296 | +0.296 | 0.296 | 0 | 11.8 |
| retrieved:semantic_dedup-0.5:k3 | 0.593 | 0.605 | +0.593 | 0.519 | 3 | 40.0 |
| retrieved:semantic_dedup-0.5:k5 | 0.574 | 0.574 | +0.574 | 0.519 | 4 | 69.3 |

## Output-format sensitivity

After observing that the model sometimes continued with another question-and-answer pair, a post-hoc diagnostic recomputed exact match using only the first line. This rule never searches for the gold answer and does not replace the preregistered primary metric.

| Condition | Full-output EM | First-line EM | Multiline answers |
|---|---:|---:|---:|
| no_memory | 0.000 | 0.000 | 0 |
| relevant | 1.000 | 1.000 | 0 |
| irrelevant | 0.241 | 0.241 | 0 |
| conflicting | 1.000 | 1.000 | 0 |
| consolidation_strip_temporal_cue | 0.352 | 0.704 | 19 |
| retrieved:full-1:k1 | 0.630 | 0.630 | 8 |
| retrieved:full-1:k3 | 0.889 | 1.000 | 6 |
| retrieved:full-1:k5 | 0.944 | 0.944 | 0 |
| retrieved:semantic_dedup-0.5:k1 | 0.296 | 0.296 | 14 |
| retrieved:semantic_dedup-0.5:k3 | 0.593 | 0.648 | 3 |
| retrieved:semantic_dedup-0.5:k5 | 0.574 | 0.574 | 0 |

## Diagnostic cases

Cases are selected by diagnostic category and do not estimate prevalence.

### Positive utility

- Query: `Where does Person001 live now?`
- Condition: `relevant`; gold: `Perth`
- No-memory answer: `UNKNOWN`
- Current answer: `Perth.`
- Evidence: `current-1`

### Consolidation degradation

- Query: `Where does Person001 live now?`
- Condition: `consolidation_strip_temporal_cue`; gold: `Perth`
- The answer begins with `Perth.` but continues into another generated QA pair.
- Evidence: `merged-current-1`

### Retrieval hit but wrong under the strict output metric

- Query: `Where does Person001 live now?`
- Condition: `retrieved:full-1:k3`; gold: `Perth`
- The answer begins with `Perth.` but continues into another QA pair.
- Evidence: `current-1`, `old-1`, `distractor-277`

### Retrieval miss

- Query: `Where does Person001 live now?`
- Condition: `retrieved:semantic_dedup-0.5:k1`; gold: `Perth`
- Answer: begins with `Kyoto.`
- Evidence: `old-1`

### Hit but wrong value

- Query: `Where does Person013 live now?`
- Condition: `retrieved:semantic_dedup-0.5:k5`; gold: `Lisbon`
- Answer: `Perth.`
- Evidence includes `current-13`, `old-13`, and three distractors.

## Interpretation boundaries

- This is a descriptive experiment with one generator and English synthetic facts. The 54 questions are 18 subject/relation templates across three seeds, not 54 fully independent topics. `seed_sd` is a population standard deviation, not a confidence interval.
- Five conditions provide controlled evidence; retrieved conditions replay actual top-k results from the balanced 10,000-memory Stage 2 corpus and do not remeasure retrieval latency.
- `relevant` supplies only the current fact. `conflicting` includes current and previous facts in alternating order. Rule-based consolidation selects the newest fact by event order and removes its temporal prefix; it is not learned summarization.
- Conditions are not token-length matched. The top-k comparison is a context-size ablation, not an independently fixed token-budget experiment.
- A hit-but-wrong case is behavioral evidence, not proof that the model internally ignored the retrieved item. Consolidation errors also do not imply fact corruption: the current rule retained the correct value, while output formatting changed.
- EM strictly compares normalized short answers. F1 measures token overlap but does not make a partially overlapping fact correct. Evidence-citation accuracy was not evaluated. `UNKNOWN` receives zero, and an ungrounded correct guess would still count.
- Memory tokens come from the generator tokenizer. Runtime includes the first model load and is not a stable latency measurement.
- Aggregate statistics and validation are in [`summary.csv`](summary.csv) and [`verification.json`](verification.json). Raw response files are intentionally excluded from the public repository.
