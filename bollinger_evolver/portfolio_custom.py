"""Custom strategy multi-pair portfolio mock evaluation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome, custom_strategy_config_from_genome
from bollinger_evolver.portfolio_evaluator import evaluate_mock_portfolio


@dataclass(frozen=True)
class CustomPortfolioConfig:
    pairs: tuple[str, ...] = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
    timeframe: str = "1h"
    seed: int = 0
    trade_count: int = 100


def evaluate_custom_portfolio(
    genome: CustomStrategyGenome,
    *,
    config: CustomPortfolioConfig | None = None,
) -> dict[str, Any]:
    """Evaluate a custom strategy config across mock portfolio pairs."""

    active = config or CustomPortfolioConfig()
    strategy_config = custom_strategy_config_from_genome(genome)
    portfolio = evaluate_mock_portfolio(
        strategy_config,
        pairs=active.pairs,
        timeframe=active.timeframe,
        seed=active.seed,
        trade_count=active.trade_count,
    )
    payload = {
        "schema_version": "custom-portfolio/v1",
        "source": "custom-strategy-mock-portfolio",
        "genome_id": genome.genome_id,
        "strategy_config": strategy_config,
        "portfolio": portfolio,
        "config": asdict(active),
    }
    json.dumps(payload, sort_keys=True)
    return payload
