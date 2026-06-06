"""Static custom strategy fixtures for regression tests and frontend mocks."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from bollinger_evolver.custom_strategy_schema import (
    CustomStrategyGenome,
    custom_strategy_config_from_genome,
    validate_custom_strategy_genome,
)


@dataclass(frozen=True)
class CustomStrategyFixture:
    name: str
    genome: CustomStrategyGenome
    metrics: dict[str, int | float]
    description: str

    def to_dict(self) -> dict[str, Any]:
        validate_custom_strategy_genome(self.genome)
        payload = {
            "name": self.name,
            "description": self.description,
            "genome": self.genome.to_dict(),
            "strategy_config": custom_strategy_config_from_genome(self.genome),
            "metrics": dict(self.metrics),
        }
        json.dumps(payload, sort_keys=True)
        return payload


FIXTURES: tuple[CustomStrategyFixture, ...] = (
    CustomStrategyFixture(
        name="safe_default",
        genome=CustomStrategyGenome(genome_id="fixture-safe-default"),
        metrics={
            "profit": 0.12,
            "drawdown": 0.07,
            "sharpe": 1.4,
            "win_rate": 0.56,
            "max_consecutive_losses": 2,
        },
        description="Conservative baseline custom Bollinger/RSI strategy.",
    ),
    CustomStrategyFixture(
        name="high_leverage_high_drawdown",
        genome=CustomStrategyGenome(
            genome_id="fixture-high-risk",
            leverage=3.0,
            risk_per_trade=0.02,
            max_portfolio_exposure=0.55,
            max_additions=3,
        ),
        metrics={
            "profit": 0.16,
            "drawdown": 0.18,
            "sharpe": 0.6,
            "win_rate": 0.48,
            "max_consecutive_losses": 7,
        },
        description="Schema-valid high risk fixture expected to trigger RiskGovernor reductions.",
    ),
    CustomStrategyFixture(
        name="low_leverage_low_drawdown",
        genome=CustomStrategyGenome(
            genome_id="fixture-low-drawdown",
            leverage=1.5,
            risk_per_trade=0.008,
            max_portfolio_exposure=0.20,
            exit_stop_loss_pct=0.02,
            exit_take_profit_pct=0.07,
        ),
        metrics={
            "profit": 0.10,
            "drawdown": 0.04,
            "sharpe": 1.8,
            "win_rate": 0.58,
            "max_consecutive_losses": 1,
        },
        description="Lower risk fixture with a better risk-adjusted profile.",
    ),
    CustomStrategyFixture(
        name="loss_streak_stress",
        genome=CustomStrategyGenome(
            genome_id="fixture-loss-streak",
            leverage=2.0,
            risk_per_trade=0.015,
            cooldown_candles=12,
        ),
        metrics={
            "profit": 0.02,
            "drawdown": 0.12,
            "sharpe": 0.2,
            "win_rate": 0.42,
            "max_consecutive_losses": 8,
        },
        description="Stress fixture for consecutive-loss risk behavior.",
    ),
    CustomStrategyFixture(
        name="portfolio_balanced",
        genome=CustomStrategyGenome(
            genome_id="fixture-portfolio-balanced",
            entry_bb_window=30,
            entry_bb_stddev=2.2,
            leverage=2.0,
            risk_per_trade=0.012,
            max_portfolio_exposure=0.30,
            max_additions=1,
        ),
        metrics={
            "profit": 0.14,
            "drawdown": 0.06,
            "sharpe": 1.6,
            "win_rate": 0.54,
            "max_consecutive_losses": 2,
        },
        description="Balanced fixture intended for multi-pair portfolio checks.",
    ),
)


def get_custom_strategy_fixtures() -> dict[str, dict[str, Any]]:
    """Return JSON-safe custom strategy fixtures keyed by fixture name."""

    fixtures = {fixture.name: fixture.to_dict() for fixture in FIXTURES}
    json.dumps(fixtures, sort_keys=True)
    return deepcopy(fixtures)


def get_custom_strategy_fixture(name: str) -> dict[str, Any]:
    """Return one JSON-safe custom strategy fixture."""

    fixtures = get_custom_strategy_fixtures()
    if name not in fixtures:
        raise KeyError(f"unknown_custom_strategy_fixture:{name}")
    return fixtures[name]
