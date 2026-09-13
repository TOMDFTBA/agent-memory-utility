# PilotDeck: memory pipeline and set-dependence study

English | [简体中文](README.md)

Reviewed on 2026-09-14 at [OpenBMB/PilotDeck@97633a0](https://github.com/OpenBMB/PilotDeck/tree/97633a08a73eca3d65c79494f9aa31cc18fd019f). This closes v0.2 after E1–E4 with a system study. It adds no E3 baseline, modifies no frozen result, and does not claim a full platform or Dream run.

## Why this system?

v0.2 found ambiguous individual LOO values for substitutes and answer failures even with complementary evidence fully read. PilotDeck provides a concrete capture, organization, and inspection pipeline. White-box visibility supports auditing; it does not establish future retention value.

## Pinned source observations

| Layer | Observation | Research boundary |
|---|---|---|
| Capture | Provider normalizes messages; service defaults to last_turn, includes assistant, caps each message at 6000 characters | Neither turn selection nor character length equals a storage token budget |
| Extraction | captureTurn queues L0 sessions; heartbeat classifies and extracts user/project/feedback notes | Turns and stored entries are different units |
| Storage | control.sqlite plus file memories and manifests | Preserve source and version mappings |
| Retrieval | ReasoningRetriever selects project/manifests and reads files with count/line limits | No directly equivalent B_store/B_read retention rule identified in reviewed paths |
| Dream | Staged rewrites record delete/write mutations before replacing live roots | Content transformation is not subset retention |
| Rollback | Pre-Dream snapshots can restore state and reset retrieval | Source-reviewed, not executed here |
| Scope | Workspace paths coexist with globalRootDir | Do not infer absolute cross-workspace isolation from the README |

Sources: [provider](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/EdgeClawMemoryProvider.ts#L94), [service](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/service.ts#L620), [heartbeat](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/core/pipeline/heartbeat.ts#L550), [retrieval](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/core/retrieval/reasoning-loop.ts#L23), [Dream](https://github.com/OpenBMB/PilotDeck/blob/97633a08a73eca3d65c79494f9aa31cc18fd019f/src/context/memory/edgeclaw-memory-core/src/core/review/dream-review.ts#L680). Reviewed file hashes are in [upstream.json](upstream.json).

## Executed bounded probes

The probe imports the committed lib/message-utils.js and calls normalizeMessages. It installs no dependencies and launches no service. Two user messages contain separate code halves, each followed by an assistant response.

| Probe | Observed output |
|---|---|
| last_turn | u2/a2 only |
| full_session | u1/a1/u2/a2 |
| user_only | u1/u2 |
| character_truncation | abcdefghij becomes abcde... at maxMessageChars=5 |

All four checks passed with zero model calls. [Output](results/source-probe/probes.json), [manifest](results/source-probe/manifest.json). Node 20.19.2 is below the core package's declared >=22.13,<23 range; this checks a dependency-free JS function, not supported full-platform execution.

A last_turn call returning only the second half does not prove long-term forgetting: earlier calls may already have captured and stored the first half. That requires sequential capture, flush, storage inspection, retrieval, and answering, none of which was executed here.

## Existing E4 case handoff

[e4-case-map.json](e4-case-map.json) contains one redundancy and one complementarity snapshot per E4 cohort, selected by stable ID rather than largest gain. It preserves original support sets, all 16 subset scores, and input hashes. It contains no new PilotDeck outcomes.

For redundancy, test whether capture/extraction and Dream preserve at least one substitute and its provenance. For complementarity, inspect whether both parts survive extraction, reach the prompt, and produce a correct answer. Record capture, stored entries, retrieved evidence, and answers separately; do not predeclare that Dream succeeds or fails.

## Naming and reuse

No pilotdeck or whitebox_memory retention candidate is added. An algorithm baseline requires an isolatable eviction rule under the same candidates, retriever, generator, and store/read budgets. A platform comparison remains a separate system study.

A future integrations/pilotdeck-memory adapter should preserve stable memory_id/version mappings and upstream_record_id, workspace, and source_memory_ids. Dream is a transformation, not a retention policy or legacy E1 condition. No empty adapter scaffolding is added now.

Reuse shared configuration, scoring, and I/O. The case handoff reads audited E4 subset-scores rather than reimplementing enumeration, LOO, selection, or statistics. Current shared study code lives in studies/memory_studies; top-level files are CLIs.

## Commands

From the repository root after installing this package, provide the pinned upstream checkout and a new output directory:

```bash
python studies/run.py pilotdeck-memory --checkout /path/to/PilotDeck --output /tmp/pilotdeck-memory-probe
python scripts/release_artifacts.py restore-results
python studies/build_case_map.py --output /tmp/pilotdeck-e4-cases.json
```

Source review, four capture-function probes, and the E4 handoff are complete. Model extraction, Dream, retrieval, and matched-budget baseline experiments remain separate future work, not v0.2 release requirements.
