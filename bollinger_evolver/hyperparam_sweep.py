"""Custom strategy hyperparameter sweep over mock-only evaluations."""

from __future__ import annotations

import itertools
import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.custom_strategy_schema import (
    CUSTOM_STRATEGY_PARAMETER_NAMES,
    CustomStrategyGenome,
    custom_strategy_config_from_genome,
    validate_custom_strategy_genome,
)
from bollinger_evolver.ga_execution_custom import evaluate_custom_genome


@dataclass(frozen=True)
class HyperparamSweepConfig:
    mode: str = "grid"
    seed: int = 42
    max_samples: int = 20
    pair: str = "BTC/USDT"
    timeframe: str = "1h"
    trade_count: int = 100


def _validate_sweep_space(sweep_space: Mapping[str, Sequence[Any]]) -> dict[str, list[Any]]:
    if not isinstance(sweep_space, Mapping) or not sweep_space:
        raise ValueError("sweep_space_required")
    allowed = set(CUSTOM_STRATEGY_PARAMETER_NAMES)
    unknown = sorted(set(sweep_space) - allowed)
    if unknown:
        raise ValueError(f"unknown_sweep_parameters:{','.join(unknown)}")
    normalized: dict[str, list[Any]] = {}
    for key, values in sweep_space.items():
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
            raise ValueError(f"sweep_values_required:{key}")
        normalized[key] = list(values)
    return normalized


def _grid_overrides(space: Mapping[str, Sequence[Any]], max_samples: int) -> list[dict[str, Any]]:
    keys = list(space)
    combinations = itertools.product(*(space[key] for key in keys))
    return [
        dict(zip(keys, values, strict=True))
        for values in itertools.islice(combinations, max_samples)
    ]


def _random_overrides(space: Mapping[str, Sequence[Any]], *, max_samples: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    keys = list(space)
    return [
        {key: rng.choice(list(space[key])) for key in keys}
        for _ in range(max_samples)
    ]


def _build_genome(base: CustomStrategyGenome, overrides: Mapping[str, Any], index: int) -> CustomStrategyGenome:
    data = base.to_dict()
    data.update(overrides)
    data["genome_id"] = f"sweep-{index:03d}"
    genome = CustomStrategyGenome(**data)
    validate_custom_strategy_genome(genome)
    return genome


def run_custom_hyperparam_sweep(
    sweep_space: Mapping[str, Sequence[Any]],
    *,
    base_genome: CustomStrategyGenome | None = None,
    config: HyperparamSweepConfig | None = None,
) -> dict[str, Any]:
    """Evaluate grid or random custom genome combinations with mock backtests."""

    active = config or HyperparamSweepConfig()
    if active.max_samples <= 0:
        raise ValueError("max_samples_must_be_positive")
    if active.mode not in {"grid", "random"}:
        raise ValueError("sweep_mode_must_be_grid_or_random")

    normalized_space = _validate_sweep_space(sweep_space)
    base = base_genome or CustomStrategyGenome(genome_id="sweep-base")
    before = base.to_dict()
    overrides = (
        _grid_overrides(normalized_space, active.max_samples)
        if active.mode == "grid"
        else _random_overrides(normalized_space, max_samples=active.max_samples, seed=active.seed)
    )

    runs: list[dict[str, Any]] = []
    for index, override in enumerate(overrides, start=1):
        genome = _build_genome(base, override, index)
        evaluation = evaluate_custom_genome(
            genome,
            seed=active.seed + index,
            pair=active.pair,
            timeframe=active.timeframe,
            trade_count=active.trade_count,
        )
        run = {
            "rank": 0,
            "run_id": genome.genome_id,
            "genome": genome.to_dict(),
            "strategy_config": custom_strategy_config_from_genome(genome),
            "fitness": float(evaluation.fitness),
            "metrics": dict(evaluation.mock_backtest),
            "session_summary": {
                "schema_version": "custom-sweep-session-summary/v1",
                "source": "custom-hyperparam-sweep",
                "run_id": genome.genome_id,
                "status": "completed",
                "generation": 1,
                "population_size": 1,
                "best_fitness": float(evaluation.fitness),
                "fitness_series": [{"generation": 1, "best_fitness": float(evaluation.fitness)}],
                "leaderboard": [{"rank": 1, **evaluation.to_dict()}],
            },
        }
        runs.append(run)

    ranked = sorted(runs, key=lambda item: item["fitness"], reverse=True)
    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank
    payload = {
        "schema_version": "custom-hyperparam-sweep/v1",
        "mode": active.mode,
        "seed": active.seed,
        "run_count": len(ranked),
        "runs": ranked,
        "best_run": ranked[0] if ranked else None,
        "config": asdict(active),
        "base_genome": before,
        "base_genome_mutated": before != base.to_dict(),
        "safety": {
            "real_backtest_used": False,
            "freqtrade_used": False,
            "exchange_api_used": False,
        },
    }
    json.dumps(payload, sort_keys=True)
    return payload
