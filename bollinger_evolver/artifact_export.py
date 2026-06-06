"""Artifact export helpers for mock-first GA execution results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bollinger_evolver.session_summary import build_ga_session_summary, to_jsonable_ga_session_summary


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _generation_list(execution_result: Any) -> list[Any]:
    return list(_get_value(execution_result, "generations", []) or [])


def _metrics_snapshot(metrics: Any) -> dict[str, Any]:
    if hasattr(metrics, "__dataclass_fields__"):
        return {
            name: getattr(metrics, name)
            for name in metrics.__dataclass_fields__.keys()
        }
    if isinstance(metrics, dict):
        return dict(metrics)
    return {}


def _genome_snapshot(genome: Any) -> dict[str, Any]:
    return {
        "genome_id": _get_value(genome, "genome_id", "unknown"),
        "parameters": dict(_get_value(genome, "parameters", {}) or {}),
    }


def _evaluation_entry(evaluation: Any) -> dict[str, Any]:
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


def _rank_generation(generation_result: Any, top_n: int) -> list[dict[str, Any]]:
    entries = sorted(
        (
            _evaluation_entry(evaluation)
            for evaluation in list(_get_value(generation_result, "evaluations", []) or [])
        ),
        key=lambda item: item["fitness"],
        reverse=True,
    )
    return [
        {"rank": rank, **entry}
        for rank, entry in enumerate(entries[: max(0, int(top_n))], start=1)
    ]


def _select_generation(execution_result: Any, generation: int | None) -> Any:
    generations = _generation_list(execution_result)
    if not generations:
        raise ValueError("execution_result_has_no_generations")
    if generation is None:
        return generations[-1]
    for item in generations:
        if int(_get_value(item, "generation", 0) or 0) == int(generation):
            return item
    raise ValueError(f"generation_not_found: {generation}")


def build_generation_artifact(
    execution_result: Any,
    *,
    generation: int | None = None,
    top_n: int = 10,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build one JSON-safe generation artifact from a mock GA execution result."""

    selected = _select_generation(execution_result, generation)
    session_summary = build_ga_session_summary(execution_result, top_n=top_n, run_id=run_id)
    leaderboard = _rank_generation(selected, top_n)
    best_entry = leaderboard[0] if leaderboard else None
    artifact = {
        "schema_version": "ga-generation-artifact/v1",
        "source": "mock-ga-execution",
        "run_id": session_summary["run_id"],
        "generation": int(_get_value(selected, "generation", 0) or 0),
        "population_size": len(list(_get_value(selected, "population", []) or [])),
        "best_fitness": float(best_entry["fitness"]) if best_entry else None,
        "average_fitness": float(_get_value(selected, "average_fitness", 0.0) or 0.0),
        "diversity": float(_get_value(selected, "diversity", 0.0) or 0.0),
        "best_genome": best_entry["genome"] if best_entry else None,
        "genomes": leaderboard,
        "session_summary": session_summary,
    }
    return to_jsonable_ga_session_summary(artifact)


def write_generation_artifact(
    execution_result: Any,
    output_dir: str | Path,
    *,
    generation: int | None = None,
    top_n: int = 10,
    run_id: str | None = None,
) -> Path:
    """Write one generation artifact JSON file and return the written path."""

    artifact = build_generation_artifact(
        execution_result,
        generation=generation,
        top_n=top_n,
        run_id=run_id,
    )
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    file_path = destination / f"generation-{int(artifact['generation']):03d}.json"
    file_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    return file_path


def write_all_generation_artifacts(
    execution_result: Any,
    output_dir: str | Path,
    *,
    top_n: int = 10,
    run_id: str | None = None,
) -> list[Path]:
    """Write one artifact per generation and return all written paths."""

    return [
        write_generation_artifact(
            execution_result,
            output_dir,
            generation=int(_get_value(generation_result, "generation", 0) or 0),
            top_n=top_n,
            run_id=run_id,
        )
        for generation_result in _generation_list(execution_result)
    ]
