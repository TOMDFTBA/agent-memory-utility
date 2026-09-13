# DeepNote: from retrieved passages to query-conditioned evidence notes

English | [简体中文](deepnote.md)

Reviewed on 2026-09-14 at [thunlp/DeepNote@cc2f013](https://github.com/thunlp/DeepNote/tree/cc2f0132737e04ec2d895e8c21673cee612ca1e7). This extends the v0.1 technical discussion, not its frozen experiments or performance claims.

## Question and mechanism

DeepNote maintains a note during one question-solving episode. Initial retrieval produces a note; the retained note guides follow-up queries, retrieved passages refine it, a comparison accepts or rejects the update, and the retained note supplies the answer.

This is not simply an offline chunk-to-note index replacement. init_note, refine_note, and compare_note receive the current query. The resulting state is query-conditioned working evidence, not demonstrated persistent memory for unknown future tasks. [Source](https://github.com/thunlp/DeepNote/blob/cc2f0132737e04ec2d895e8c21673cee612ca1e7/src/main.py#L165)

## Source review and bounded execution

| Mechanism | Observation | Scope |
|---|---|---|
| Initialization | Query and retrieved references enter the template | No generation-quality evaluation |
| Update | Only an accepted comparison replaces best_note | Acceptance/rejection checked with stubs |
| Stopping | Step ceiling and cumulative failure count | False / True / False stops after two failures |
| Answer | Uses best_note, not necessarily the final attempted revision | Two rejections retain the initial note |
| Provenance | ref_log, note_log, query_log are saved | Not a per-fact citation guarantee |

Two probes execute only the upstream retrieve_note AST function with deterministic retrieval/model stubs. They do not import the API-initializing CLI, train a model, or generate real answers. [Recorded probes](../../studies/deepnote/results/source-probe/probes.json)

## Connection to the existing experiments

v0.1 separates retrieval success from answer quality. DeepNote supplies an evidence-organization reference; it is not retroactively an implemented v0.1 component. v0.2 retention must use past-only inputs: a note written after seeing a future test query cannot be a historical retention feature.

A subsequent controlled study can ask whether organizing fixed retrieved evidence improves E4 cases with complete support but incorrect composition. That hypothesis remains untested.

## Proposed experiment and reuse boundary

Compare raw_evidence, plain_summary, and structured_note as representation values, not retention candidates. Fix retrieved source evidence, generator, scoring, and final read budget. Report organization-stage calls, input/output tokens, and time separately from answer costs.

Measure EM/F1, supporting-fact preservation, source traceability, and unsupported additions. An attached source ID alone does not establish factual grounding. A representation-only adaptation is DeepNote-inspired; adaptive retrieval additionally requires matched retrieval and compute budgets. No original preference-training reproduction is claimed.

Reuse longmem.config, generation, scoring, and experiment_io. Derived notes should preserve source_memory_ids without overwriting original records. A new organization interface should not duplicate the selector or modify frozen Engine.answer.

The present probe implementation lives in studies/memory_studies and uses longmem-study-v1/study_id, separate from experimental manifests. [Commands and source pin](../../studies/deepnote/README.md)

Sources: [paper](https://aclanthology.org/2025.findings-emnlp.1073/), [pinned repository](https://github.com/thunlp/DeepNote/tree/cc2f0132737e04ec2d895e8c21673cee612ca1e7).
