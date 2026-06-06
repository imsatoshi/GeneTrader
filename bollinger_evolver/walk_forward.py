"""Mock walk-forward evaluation for GA robustness checks."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.backtest_adapter import MockBacktestAdapter, NormalizedBacktestResult


SEGMENTS = ("train", "validation", "test")


@dataclass(frozen=True)
class WalkForwardConfig:
    base_seed: int = 0
    trade_count: int = 100
    pair: str = "BTC/USDT"
    timeframe: str = "1h"


def _result_snapshot(result: NormalizedBacktestResult) -> dict[str, Any]:
    return {
        "profit": float(result.profit),
        "sharpe": float(result.sharpe),
        "win_rate": float(result.win_rate),
        "max_drawdown": float(result.max_drawdown),
        "total_trades": int(result.total_trades),
        "max_consecutive_losses": int(result.max_consecutive_losses),
        "leverage": float(result.leverage),
        "risk_per_trade": float(result.risk_per_trade),
        "metadata": dict(result.metadata),
    }


def _metric_values(segment_results: Sequence[Mapping[str, Any]], metric_name: str) -> list[float]:
    return [float(item[metric_name]) for item in segment_results]


def calculate_stability_score(segment_results: Sequence[Mapping[str, Any]]) -> float:
    """Return a 0..1 score that penalizes metric drift across segments."""

    if not segment_results:
        return 0.0
    drift = 0.0
    weights = {
        "profit": 1.0,
        "sharpe": 0.20,
        "win_rate": 0.75,
        "max_drawdown": 1.25,
    }
    for metric_name, weight in weights.items():
        values = _metric_values(segment_results, metric_name)
        drift += (max(values) - min(values)) * weight
    return round(max(0.0, min(1.0, 1.0 - drift)), 6)


def run_mock_walk_forward_evaluation(
    genome: Mapping[str, Any],
    *,
    config: WalkForwardConfig | None = None,
) -> dict[str, Any]:
    """Evaluate a genome over train/validation/test mock segments."""

    active_config = config or WalkForwardConfig()
    if not isinstance(genome, Mapping):
        raise TypeError("genome_must_be_mapping")
    segment_payloads: dict[str, dict[str, Any]] = {}
    ordered_results: list[dict[str, Any]] = []
    for index, segment in enumerate(SEGMENTS):
        adapter = MockBacktestAdapter(
            pair=active_config.pair,
            timeframe=active_config.timeframe,
            trade_count=active_config.trade_count,
            seed=active_config.base_seed + index,
        )
        snapshot = _result_snapshot(adapter.run_backtest(genome))
        snapshot["segment"] = segment
        snapshot["seed"] = active_config.base_seed + index
        segment_payloads[segment] = snapshot
        ordered_results.append(snapshot)

    payload = {
        "schema_version": "mock-walk-forward/v1",
        "source": "mock-backtest-adapter",
        "config": asdict(active_config),
        "train": segment_payloads["train"],
        "validation": segment_payloads["validation"],
        "test": segment_payloads["test"],
        "stability_score": calculate_stability_score(ordered_results),
    }
    json.dumps(payload, sort_keys=True)
    return payload
