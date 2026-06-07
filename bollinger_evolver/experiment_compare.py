"""Local mock experiment comparison helpers.

The comparison engine consumes already-produced experiment summaries. It does
not run GA, invoke backtests, or touch runtime output paths.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "experiment-comparison/v1"
REQUIRED_METRIC_FIELDS = ("best_fitness", "max_drawdown", "stability_score")


def _json_clone(value: Any, *, error_code: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(error_code) from exc


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"experiment_summary_field_must_be_numeric:{field_name}")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"experiment_summary_field_must_be_finite:{field_name}")
    return numeric


def _validated_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_METRIC_FIELDS if field not in summary]
    if missing:
        raise ValueError(f"experiment_summary_missing_field:{missing[0]}")
    clone = _json_clone(dict(summary), error_code="experiment_summary_not_json_safe")
    for field in REQUIRED_METRIC_FIELDS:
        clone[field] = _finite_float(clone[field], field_name=field)
    return clone


def compare_experiment_summaries(summaries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare existing mock experiment summaries and return JSON-safe ranking."""

    if isinstance(summaries, (str, bytes)) or not isinstance(summaries, Sequence):
        raise ValueError("experiment_summaries_must_be_sequence")
    if not summaries:
        raise ValueError("experiment_summaries_required")

    validated: list[tuple[int, dict[str, Any]]] = []
    for index, summary in enumerate(summaries):
        if not isinstance(summary, Mapping):
            raise ValueError("experiment_summary_must_be_mapping")
        validated.append((index, _validated_summary(summary)))

    by_fitness = max(validated, key=lambda item: (item[1]["best_fitness"], -item[0]))
    by_drawdown = min(validated, key=lambda item: (item[1]["max_drawdown"], item[0]))
    by_stability = max(validated, key=lambda item: (item[1]["stability_score"], -item[0]))
    ranked_pairs = sorted(
        validated,
        key=lambda item: (
            -item[1]["best_fitness"],
            item[1]["max_drawdown"],
            -item[1]["stability_score"],
            item[0],
        ),
    )
    ranked: list[dict[str, Any]] = []
    for rank, (_, summary) in enumerate(ranked_pairs, start=1):
        item = dict(summary)
        item["rank"] = rank
        ranked.append(item)

    result = {
        "schema_version": SCHEMA_VERSION,
        "run_count": len(validated),
        "best_by_fitness": by_fitness[1],
        "best_by_drawdown": by_drawdown[1],
        "best_by_stability": by_stability[1],
        "ranked": ranked,
    }
    json.dumps(result, sort_keys=True)
    return result
