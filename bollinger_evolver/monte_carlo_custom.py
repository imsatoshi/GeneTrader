"""Custom strategy Monte Carlo perturbation scaffold."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.backtest_adapter import generate_synthetic_trades
from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome, custom_strategy_config_from_genome
from bollinger_evolver.monte_carlo import MonteCarloConfig, run_monte_carlo_stress_test


@dataclass(frozen=True)
class CustomMonteCarloConfig:
    runs: int = 100
    seed: int = 0
    trade_count: int = 100
    perturbation: float = 0.001
    pair: str = "BTC/USDT"
    timeframe: str = "1h"


def run_custom_monte_carlo(
    genome: CustomStrategyGenome,
    *,
    config: CustomMonteCarloConfig | None = None,
) -> dict[str, Any]:
    """Generate synthetic trades for one custom genome and stress them."""

    active = config or CustomMonteCarloConfig()
    strategy_config = custom_strategy_config_from_genome(genome)
    trades = generate_synthetic_trades(
        strategy_config,
        pair=active.pair,
        timeframe=active.timeframe,
        trade_count=active.trade_count,
        seed=active.seed,
    )
    stress = run_monte_carlo_stress_test(
        [trade.to_dict() for trade in trades],
        config=MonteCarloConfig(
            runs=active.runs,
            seed=active.seed,
            perturbation=active.perturbation,
        ),
    )
    payload = {
        "schema_version": "custom-monte-carlo/v1",
        "source": "custom-strategy-synthetic-trades",
        "genome_id": genome.genome_id,
        "trade_count": len(trades),
        "monte_carlo": stress,
        "config": asdict(active),
    }
    json.dumps(payload, sort_keys=True)
    return payload
