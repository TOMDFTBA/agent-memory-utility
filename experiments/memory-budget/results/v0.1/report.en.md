# Stage 2: Memory-Budget Experiment

[Chinese version](report.md) | Status: `COMPLETE` | Backend: `minicpm` | 300 runs

The full baseline retains 100% of memories; the other rows below retain 50%. Recall is scored by equivalent fact rather than only exact memory ID. Exact-ID metrics and all budget levels are available in [`summary.csv`](summary.csv).

| Scenario | Size | Policy | R@1 | R@5 ± SD | MRR | P50 ms | P95 ms | Index MiB | Tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| balanced | 100 | full | 0.759 | 1.000 ± 0.000 | 0.879 | 34.67 | 37.04 | 0.88 | 61.0 |
| balanced | 100 | importance | 0.375 | 0.500 ± 0.045 | 0.437 | 34.66 | 37.03 | 0.44 | 61.4 |
| balanced | 100 | recency | 0.421 | 0.574 ± 0.026 | 0.498 | 34.66 | 37.03 | 0.44 | 61.5 |
| balanced | 100 | semantic_dedup | 0.537 | 0.704 ± 0.026 | 0.620 | 34.66 | 37.03 | 0.44 | 61.2 |
| balanced | 500 | full | 0.745 | 1.000 ± 0.000 | 0.868 | 34.70 | 37.07 | 4.39 | 63.5 |
| balanced | 500 | importance | 0.380 | 0.519 ± 0.026 | 0.447 | 34.68 | 37.05 | 2.20 | 65.4 |
| balanced | 500 | recency | 0.398 | 0.537 ± 0.026 | 0.467 | 34.68 | 37.05 | 2.20 | 65.6 |
| balanced | 500 | semantic_dedup | 0.477 | 0.630 ± 0.026 | 0.552 | 34.68 | 37.05 | 2.20 | 64.8 |
| balanced | 1,000 | full | 0.745 | 1.000 ± 0.000 | 0.865 | 34.73 | 37.10 | 8.79 | 63.6 |
| balanced | 1,000 | importance | 0.370 | 0.500 ± 0.045 | 0.433 | 34.71 | 37.07 | 4.39 | 65.8 |
| balanced | 1,000 | recency | 0.417 | 0.556 ± 0.000 | 0.485 | 34.70 | 37.07 | 4.39 | 65.6 |
| balanced | 1,000 | semantic_dedup | 0.412 | 0.556 ± 0.045 | 0.483 | 34.70 | 37.07 | 4.39 | 65.0 |
| balanced | 5,000 | full | 0.718 | 0.963 ± 0.007 | 0.833 | 35.37 | 37.78 | 43.95 | 64.1 |
| balanced | 5,000 | importance | 0.370 | 0.486 ± 0.049 | 0.427 | 34.86 | 37.23 | 21.97 | 66.1 |
| balanced | 5,000 | recency | 0.380 | 0.537 ± 0.026 | 0.447 | 34.86 | 37.22 | 21.97 | 65.9 |
| balanced | 5,000 | semantic_dedup | 0.361 | 0.519 ± 0.026 | 0.429 | 34.86 | 37.23 | 21.97 | 65.4 |
| balanced | 10,000 | full | 0.718 | 0.949 ± 0.007 | 0.826 | 36.42 | 38.80 | 87.89 | 64.1 |
| balanced | 10,000 | importance | 0.370 | 0.486 ± 0.049 | 0.425 | 35.36 | 37.78 | 43.95 | 66.0 |
| balanced | 10,000 | recency | 0.380 | 0.537 ± 0.026 | 0.447 | 35.33 | 37.72 | 43.95 | 65.9 |
| balanced | 10,000 | semantic_dedup | 0.343 | 0.519 ± 0.026 | 0.419 | 35.34 | 37.76 | 43.95 | 65.4 |
| old | 100 | full | 0.759 | 1.000 ± 0.000 | 0.879 | 34.67 | 37.04 | 0.88 | 61.0 |
| old | 100 | importance | 0.375 | 0.500 ± 0.045 | 0.437 | 34.66 | 37.03 | 0.44 | 61.4 |
| old | 100 | recency | 0.366 | 0.389 ± 0.000 | 0.377 | 34.66 | 37.03 | 0.44 | 64.4 |
| old | 100 | semantic_dedup | 0.403 | 0.500 ± 0.079 | 0.451 | 34.66 | 37.03 | 0.44 | 62.7 |
| old | 500 | full | 0.745 | 1.000 ± 0.000 | 0.868 | 34.70 | 37.07 | 4.39 | 63.5 |
| old | 500 | importance | 0.380 | 0.519 ± 0.026 | 0.447 | 34.68 | 37.05 | 2.20 | 65.4 |
| old | 500 | recency | 0.000 | 0.000 ± 0.000 | 0.000 | 34.68 | 37.05 | 2.20 | 68.4 |
| old | 500 | semantic_dedup | 0.171 | 0.204 ± 0.026 | 0.188 | 34.68 | 37.05 | 2.20 | 66.0 |
| old | 1,000 | full | 0.745 | 1.000 ± 0.000 | 0.865 | 34.73 | 37.10 | 8.79 | 63.6 |
| old | 1,000 | importance | 0.370 | 0.500 ± 0.045 | 0.433 | 34.70 | 37.07 | 4.39 | 65.8 |
| old | 1,000 | recency | 0.000 | 0.000 ± 0.000 | 0.000 | 34.70 | 37.07 | 4.39 | 68.2 |
| old | 1,000 | semantic_dedup | 0.120 | 0.130 ± 0.052 | 0.125 | 34.70 | 37.07 | 4.39 | 66.2 |
| old | 5,000 | full | 0.718 | 0.963 ± 0.007 | 0.833 | 35.34 | 37.71 | 43.95 | 64.1 |
| old | 5,000 | importance | 0.370 | 0.486 ± 0.049 | 0.427 | 34.85 | 37.23 | 21.97 | 66.1 |
| old | 5,000 | recency | 0.000 | 0.000 ± 0.000 | 0.000 | 34.88 | 37.24 | 21.97 | 68.2 |
| old | 5,000 | semantic_dedup | 0.019 | 0.019 ± 0.026 | 0.019 | 34.86 | 37.26 | 21.97 | 66.7 |
| old | 10,000 | full | 0.718 | 0.949 ± 0.007 | 0.826 | 36.42 | 38.81 | 87.89 | 64.1 |
| old | 10,000 | importance | 0.370 | 0.486 ± 0.049 | 0.425 | 35.33 | 37.74 | 43.95 | 66.0 |
| old | 10,000 | recency | 0.000 | 0.000 ± 0.000 | 0.000 | 35.33 | 37.74 | 43.95 | 68.2 |
| old | 10,000 | semantic_dedup | 0.019 | 0.019 ± 0.026 | 0.019 | 35.33 | 37.73 | 43.95 | 66.7 |

Latency combines separately sampled query encoding and in-memory search. Values are means of the per-seed percentiles and exclude model loading, event-log replay, persistence, and MCP overhead. SD is the population standard deviation across three seeds, not a confidence interval.

![Recall under memory growth](memory-size-vs-recall.png)

![Recall under compression](compression-vs-recall.png)

![Memory size and cost](cost-vs-size.png)

## Interpretation boundaries

- The dataset contains 24 fact topics across six relations. Each seed evaluates 18 test topics with four query paraphrases, giving 72 queries per seed; paraphrases are not independent fact samples.
- Twelve exact duplicate memories validate equivalent-ID scoring. Their proportion decreases as corpus size grows, so this is not a fixed-duplicate-rate experiment.
- Importance is random metadata in this baseline; it is neither human-labeled nor learned utility.
- Semantic deduplication greedily suppresses items by recency and then fills the remaining fixed budget. It is not pure threshold deduplication or summary merging.
- Temporal metadata controls retention order, while retrieval text contains only `Currently` or `Previously`, not absolute timestamps.
- A separate development seed (`77`) calibrates the deduplication threshold; test queries are not used for threshold selection.
- Results come from small English synthetic templates and single-threaded FAISS on one host. They do not generalize directly to real conversations or other hardware.
- End-to-end service latency, factual fidelity of merged summaries, multimodal behavior, and generation utility are outside this experiment.
