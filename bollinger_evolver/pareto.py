"""Pareto frontier selection for mock GA candidates."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


DEFAULT_MAXIMIZE = ("profit", "sharpe", "stability_score")
DEFAULT_MINIMIZE = ("max_drawdown", "leverage", "risk_per_trade")


def _json_clone(value: Any, *, error_code: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(error_code) from exc


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"candidate_objective_must_be_numeric:{field_name}")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"candidate_objective_must_be_finite:{field_name}")
    return numeric


def _validated_candidate(
    candidate: Mapping[str, Any],
    *,
    maximize: tuple[str, ...],
    minimize: tuple[str, ...],
) -> dict[str, Any]:
    clone = _json_clone(dict(candidate), error_code="pareto_candidate_not_json_safe")
    for field in (*maximize, *minimize):
        if field not in clone:
            raise ValueError(f"candidate_missing_objective:{field}")
        clone[field] = _finite_float(clone[field], field_name=field)
    return clone


def _dominates(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    *,
    maximize: tuple[str, ...],
    minimize: tuple[str, ...],
) -> bool:
    at_least_as_good = True
    strictly_better = False

    for field in maximize:
        if left[field] < right[field]:
            at_least_as_good = False
            break
        if left[field] > right[field]:
            strictly_better = True
    if at_least_as_good:
        for field in minimize:
            if left[field] > right[field]:
                at_least_as_good = False
                break
            if left[field] < right[field]:
                strictly_better = True

    return at_least_as_good and strictly_better


def select_pareto_frontier(
    candidates: Sequence[Mapping[str, Any]],
    maximize: tuple[str, ...] = DEFAULT_MAXIMIZE,
    minimize: tuple[str, ...] = DEFAULT_MINIMIZE,
) -> list[dict[str, Any]]:
    """Return non-dominated candidates in stable input order."""

    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        raise ValueError("pareto_candidates_must_be_sequence")
    if not maximize and not minimize:
        raise ValueError("pareto_objectives_required")

    validated: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("pareto_candidate_must_be_mapping")
        validated.append(_validated_candidate(candidate, maximize=maximize, minimize=minimize))

    frontier: list[dict[str, Any]] = []
    for index, candidate in enumerate(validated):
        dominated = any(
            other_index != index
            and _dominates(other, candidate, maximize=maximize, minimize=minimize)
            for other_index, other in enumerate(validated)
        )
        if not dominated:
            frontier.append(candidate)

    json.dumps(frontier, sort_keys=True)
    return frontier
