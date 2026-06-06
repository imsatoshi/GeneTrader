"""JSON-safe session summary builder for mock-first GA execution results."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _genome_snapshot(genome: Any) -> dict[str, Any]:
    parameters = dict(_get_value(genome, "parameters", {}) or {})
    return {
        "genome_id": _get_value(genome, "genome_id", "unknown"),
        "bollinger_window": parameters.get("bb_window"),
        "bollinger_stddev": parameters.get("bb_stddev"),
        "stoploss": parameters.get("stop_loss_pct"),
        "takeprofit": parameters.get("take_profit_pct"),
        "leverage": parameters.get("leverage"),
        "risk_per_trade": parameters.get("risk_per_trade"),
        "parameters": parameters,
    }


def _metrics_snapshot(metrics: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(metrics):
        return dataclasses.asdict(metrics)
    if isinstance(metrics, Mapping):
        return dict(metrics)
    return {}


def _evaluation_snapshot(evaluation: Any) -> dict[str, Any]:
    genome = _get_value(evaluation, "genome")
    metrics = _metrics_snapshot(_get_value(evaluation, "metrics", {}))
    return {
        "genome_id": _get_value(genome, "genome_id", "unknown"),
        "fitness": float(_get_value(evaluation, "fitness", 0.0) or 0.0),
        "profit": float(metrics.get("profit", 0.0) or 0.0),
        "drawdown": float(metrics.get("drawdown", 0.0) or 0.0),
        "sharpe": float(metrics.get("sharpe", 0.0) or 0.0),
        "win_rate": float(metrics.get("win_rate", 0.0) or 0.0),
        "total_trades": int(metrics.get("total_trades", 0) or 0),
        "max_consecutive_losses": int(metrics.get("max_consecutive_losses", 0) or 0),
        "leverage": float(metrics.get("leverage", 0.0) or 0.0),
        "risk_per_trade": float(metrics.get("risk_per_trade", 0.0) or 0.0),
        "fitness_components": metrics.get("fitness_components") or {},
        "genome": _genome_snapshot(genome),
    }


def _generation_list(execution_result: Any) -> list[Any]:
    generations = _get_value(execution_result, "generations", [])
    return list(generations or [])


def _fitness_series(generations: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "generation": int(_get_value(generation, "generation", index + 1) or index + 1),
            "best_fitness": float(_get_value(_get_value(generation, "best"), "fitness", 0.0) or 0.0),
            "average_fitness": float(_get_value(generation, "average_fitness", 0.0) or 0.0),
            "diversity": float(_get_value(generation, "diversity", 0.0) or 0.0),
        }
        for index, generation in enumerate(generations)
    ]


def _leaderboard(generations: list[Any], top_n: int) -> list[dict[str, Any]]:
    evaluations: list[Any] = []
    for generation in generations:
        evaluations.extend(list(_get_value(generation, "evaluations", []) or []))

    ranked = sorted(
        (_evaluation_snapshot(evaluation) for evaluation in evaluations),
        key=lambda item: item["fitness"],
        reverse=True,
    )
    limited = ranked[: max(0, int(top_n))]
    return [
        {
            "rank": index,
            **entry,
        }
        for index, entry in enumerate(limited, start=1)
    ]


def _config_value(execution_result: Any, key: str, default: Any = None) -> Any:
    config = _get_value(execution_result, "config", {})
    return _get_value(config, key, default)


def build_ga_session_summary(execution_result: Any, *, top_n: int = 10, run_id: str | None = None) -> dict[str, Any]:
    """Build a stable, JSON-safe summary from a mock GA execution result."""

    generations = _generation_list(execution_result)
    final_generation = generations[-1] if generations else None
    series = _fitness_series(generations)
    board = _leaderboard(generations, top_n)
    best_entry = board[0] if board else None
    population_size = int(
        _config_value(
            execution_result,
            "population_size",
            len(_get_value(final_generation, "population", []) or []),
        )
        or 0
    )
    seed = _config_value(execution_result, "seed", 0)

    summary = {
        "schema_version": "ga-session-summary/v1",
        "source": "mock-ga-execution",
        "run_id": run_id or _get_value(execution_result, "run_id", None) or f"mock-ga-seed-{seed}",
        "status": "completed" if generations else "empty",
        "generation": int(_get_value(final_generation, "generation", 0) or 0),
        "population_size": population_size,
        "best_fitness": float(best_entry["fitness"]) if best_entry else None,
        "average_fitness": float(_get_value(final_generation, "average_fitness", 0.0) or 0.0),
        "diversity": float(_get_value(final_generation, "diversity", 0.0) or 0.0),
        "best_genome": best_entry["genome"] if best_entry else None,
        "fitness_series": series,
        "leaderboard": board,
    }
    return to_jsonable_ga_session_summary(summary)


def to_jsonable_ga_session_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Return a recursively JSON-serializable copy of a GA session summary."""

    def convert(value: Any) -> Any:
        if dataclasses.is_dataclass(value):
            return convert(dataclasses.asdict(value))
        if isinstance(value, Mapping):
            return {str(key): convert(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [convert(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (Path, datetime, date)):
            return str(value)
        return str(value)

    return convert(summary)
