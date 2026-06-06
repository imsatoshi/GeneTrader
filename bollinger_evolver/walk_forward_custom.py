"""Custom strategy walk-forward integration over mock segments."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome, custom_strategy_config_from_genome
from bollinger_evolver.fitness import calculate_risk_aware_fitness_breakdown
from bollinger_evolver.walk_forward import WalkForwardConfig, run_mock_walk_forward_evaluation


@dataclass(frozen=True)
class CustomWalkForwardConfig:
    base_seed: int = 0
    trade_count: int = 100
    pair: str = "BTC/USDT"
    timeframe: str = "1h"


def evaluate_custom_walk_forward(
    genome: CustomStrategyGenome,
    *,
    config: CustomWalkForwardConfig | None = None,
) -> dict[str, Any]:
    """Run train/validation/test mock segments and calculate overfit-aware fitness."""

    active = config or CustomWalkForwardConfig()
    strategy_config = custom_strategy_config_from_genome(genome)
    walk_forward = run_mock_walk_forward_evaluation(
        strategy_config,
        config=WalkForwardConfig(
            base_seed=active.base_seed,
            trade_count=active.trade_count,
            pair=active.pair,
            timeframe=active.timeframe,
        ),
    )
    validation = walk_forward["validation"]
    fitness_components = calculate_risk_aware_fitness_breakdown(
        profit=float(validation["profit"]),
        drawdown=float(validation["max_drawdown"]),
        sharpe=float(validation["sharpe"]),
        win_rate=float(validation["win_rate"]),
        leverage=float(validation["leverage"]),
        risk_per_trade=float(validation["risk_per_trade"]),
        max_loss_streak=int(validation["max_consecutive_losses"]),
        stability_score=float(walk_forward["stability_score"]),
        train_validation_gap=float(walk_forward["train_validation_gap"]),
        validation_test_gap=float(walk_forward["validation_test_gap"]),
    )
    payload = {
        "schema_version": "custom-walk-forward/v1",
        "source": "custom-strategy-mock-walk-forward",
        "genome_id": genome.genome_id,
        "strategy_config": strategy_config,
        "walk_forward": walk_forward,
        "fitness_components": fitness_components,
        "config": asdict(active),
    }
    json.dumps(payload, sort_keys=True)
    return payload
