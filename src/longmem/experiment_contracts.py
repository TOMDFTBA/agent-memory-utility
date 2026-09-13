"""Canonical field names and v0.1 compatibility adapters for experiments."""

from typing import Any


SCHEMA_VERSION = "longmem-experiment-v1"

RETENTION_POLICIES = frozenset({"full", "random", "recency", "importance", "semantic_dedup", "utility_aware", "oracle_utility",
                                "retrieval_frequency", "hindsight_loo", "best_subset"})
MEMORY_CONDITIONS = frozenset({
    "no_memory",
    "relevant",
    "irrelevant",
    "conflicting",
    "consolidation_keep_temporal_cue",
    "consolidation_strip_temporal_cue",
})
RETRIEVAL_MODALITIES = frozenset({"visual", "native_text", "ocr_text"})


def canonical_target(record: dict[str, Any]) -> dict[str, Any]:
    """Expose unambiguous target names while accepting a frozen v0.1 query."""
    target = record.get("target_canonical_id", record.get("target"))
    if not isinstance(target, str) or not target:
        raise ValueError("target_canonical_id must be a non-empty string")
    exact = record.get("target_memory_id", target)
    if not isinstance(exact, str) or not exact:
        raise ValueError("target_memory_id must be a non-empty string")
    return {"target_memory_id": exact, "target_canonical_id": target}


def canonical_event_order(record: dict[str, Any]) -> float:
    """Read synthetic ordering without confusing it with an ISO created_at."""
    value = record.get("event_order", record.get("temporal_position", record.get("timestamp")))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("event_order must be numeric for synthetic experiment records")
    return float(value)


def canonical_condition(name: str) -> str:
    aliases = {
        "consolidated": "consolidation_strip_temporal_cue",
        "merged_keep_current": "consolidation_keep_temporal_cue",
        "merged_strip_current": "consolidation_strip_temporal_cue",
    }
    result = aliases.get(name, name)
    if result not in MEMORY_CONDITIONS and not result.startswith("retrieved:"):
        raise ValueError(f"Unknown memory condition: {name}")
    return result


def canonical_modality(name: str) -> str:
    aliases = {"pdf": "native_text", "ocr": "ocr_text"}
    result = aliases.get(name, name)
    if result not in RETRIEVAL_MODALITIES:
        raise ValueError(f"Unknown retrieval modality: {name}")
    return result


def metric_key(namespace: str, name: str, *, k: int | None = None) -> str:
    if namespace not in {"retention", "retrieval", "answer", "cost", "prediction", "diagnostic"}:
        raise ValueError(f"Unknown metric namespace: {namespace}")
    if k is not None:
        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("k must be a positive integer")
        name = f"{name}_at_{k}"
    return f"{namespace}.{name}"


# Candidate IDs are separate from policy families and content conditions.
EXACT_SET_CANDIDATES = frozenset({"predicted_sum_optimal", "hindsight_loo_sum_optimal"})
MEMORY_INTERVENTIONS = frozenset({"storage_deletion", "context_deletion", "subset_enumeration"})
WRITE_RETENTION_POLICIES = RETENTION_POLICIES - {"oracle_utility"}


def canonical_diagnostic_plan(record: dict[str, Any]) -> dict[str, Any]:
    """Read frozen E3 diagnostics without rewriting the original artifact."""
    result = dict(record)
    if result.get("candidate") == "storage_deletion":
        if "intervention" in result and result["intervention"] != "storage_deletion":
            raise ValueError("Conflicting diagnostic fields")
        result.pop("candidate")
        result["intervention"] = "storage_deletion"
    if result.get("intervention") not in MEMORY_INTERVENTIONS or "candidate" in result:
        raise ValueError("Expected a diagnostic plan, not a retention candidate")
    return result
