"""Monte Carlo stress testing for synthetic trade sequences."""

from __future__ import annotations

import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MonteCarloConfig:
    runs: int = 100
    seed: int = 0
    perturbation: float = 0.0
    failure_profit_threshold: float = 0.0
    failure_drawdown_threshold: float = 0.25


def _trade_return(item: Any) -> float:
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return float(item)
    if isinstance(item, Mapping):
        for key in ("pnl_pct", "return_pct", "profit_ratio"):
            if key in item:
                return float(item[key])
    for key in ("pnl_pct", "return_pct", "profit_ratio"):
        if hasattr(item, key):
            return float(getattr(item, key))
    raise ValueError("trade_return_missing")


def _returns(trades: Sequence[Any]) -> list[float]:
    values = [_trade_return(item) for item in trades]
    if not values:
        raise ValueError("trades_required")
    return values


def _profit_and_drawdown(returns: Sequence[float]) -> tuple[float, float]:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        equity = max(0.000001, equity * (1.0 + float(value)))
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
    return equity - 1.0, max_drawdown


def _percentile(sorted_values: Sequence[float], percentile: float) -> float:
    if not sorted_values:
        raise ValueError("percentile_values_required")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def run_monte_carlo_stress_test(
    trades: Sequence[Any],
    *,
    config: MonteCarloConfig | None = None,
) -> dict[str, Any]:
    """Bootstrap synthetic trade returns and summarize robustness."""

    active_config = config or MonteCarloConfig()
    if active_config.runs <= 0:
        raise ValueError("runs_must_be_positive")
    base_returns = _returns(trades)
    rng = random.Random(active_config.seed)
    profits: list[float] = []
    drawdowns: list[float] = []
    failures = 0

    for _ in range(active_config.runs):
        sampled = [base_returns[rng.randrange(len(base_returns))] for _ in base_returns]
        rng.shuffle(sampled)
        if active_config.perturbation:
            sampled = [
                value + rng.uniform(-active_config.perturbation, active_config.perturbation)
                for value in sampled
            ]
        profit, drawdown = _profit_and_drawdown(sampled)
        profits.append(profit)
        drawdowns.append(drawdown)
        if profit < active_config.failure_profit_threshold or drawdown > active_config.failure_drawdown_threshold:
            failures += 1

    sorted_profits = sorted(profits)
    sorted_drawdowns = sorted(drawdowns)
    result = {
        "schema_version": "monte-carlo-stress/v1",
        "source": "synthetic-trade-sequence",
        "runs": int(active_config.runs),
        "profit_p05": round(_percentile(sorted_profits, 0.05), 6),
        "profit_median": round(_percentile(sorted_profits, 0.50), 6),
        "profit_p95": round(_percentile(sorted_profits, 0.95), 6),
        "drawdown_p05": round(_percentile(sorted_drawdowns, 0.05), 6),
        "drawdown_median": round(_percentile(sorted_drawdowns, 0.50), 6),
        "drawdown_p95": round(_percentile(sorted_drawdowns, 0.95), 6),
        "failure_rate": round(failures / active_config.runs, 6),
        "config": asdict(active_config),
    }
    json.dumps(result, sort_keys=True)
    return result
