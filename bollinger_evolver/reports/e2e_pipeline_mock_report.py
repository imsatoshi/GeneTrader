"""Mock-first end-to-end pipeline report builder.

The report builder consumes local mock GA optimization output and reshapes it
into a stable review contract. It does not run Freqtrade, connect to exchanges,
or write files.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.ga_optimization_custom import (
    CustomOptimizationConfig,
    run_custom_ga_optimization,
)


SCHEMA_VERSION = "e2e-mock-pipeline-report/v1"


@dataclass(frozen=True)
class E2EMockPipelineReportConfig:
    run_id: str = "e2e-mock-pipeline"
    population_size: int = 6
    generations: int = 1
    seed: int = 325
    top_n: int = 3
    trade_count: int = 40
    pairs: tuple[str, ...] = ("BTC/USDT", "ETH/USDT")
    timeframe: str = "1h"
    monte_carlo_runs: int = 20


def _frontend_contract_section(payload: dict[str, Any]) -> dict[str, Any]:
    leaderboard = payload["leaderboard"]
    fitness_series = payload["fitness_series"]
    robustness = payload["robustness_summary"]
    return {
        "schema_version": "frontend-contract-summary/v1",
        "run_id": payload["run_id"],
        "leaderboard_rows": len(leaderboard),
        "fitness_points": len(fitness_series),
        "has_risk_summary": bool(payload.get("risk_governor")),
        "has_walk_forward": "walk_forward" in robustness,
        "has_monte_carlo": "monte_carlo" in robustness,
        "has_portfolio": "portfolio" in robustness,
        "required_frontend_fields": {
            "leaderboard": ["rank", "genome_id", "fitness", "profit", "drawdown"],
            "fitness_series": ["generation", "best_fitness", "average_fitness"],
            "risk_summary": ["schema_version", "adjustments", "warnings"],
            "portfolio": ["portfolio_profit", "portfolio_drawdown", "pair_results"],
        },
    }


def build_e2e_mock_pipeline_report(
    config: E2EMockPipelineReportConfig | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe mock E2E report without writing files."""

    active = config or E2EMockPipelineReportConfig()
    optimization = run_custom_ga_optimization(
        CustomOptimizationConfig(
            run_id=active.run_id,
            population_size=active.population_size,
            generations=active.generations,
            seed=active.seed,
            top_n=active.top_n,
            trade_count=active.trade_count,
            pairs=active.pairs,
            timeframe=active.timeframe,
            monte_carlo_runs=active.monte_carlo_runs,
        )
    )
    robustness = optimization["robustness_summary"]
    report = {
        "schema_version": SCHEMA_VERSION,
        "source": "mock-first",
        "run_id": active.run_id,
        "sections": {
            "ga": {
                "schema_version": optimization["schema_version"],
                "generation": optimization["generation"],
                "population_size": optimization["population_size"],
                "best_fitness": optimization["best_fitness"],
                "average_fitness": optimization["average_fitness"],
                "optimization_score": optimization["optimization_score"],
                "leaderboard": optimization["leaderboard"],
                "fitness_series": optimization["fitness_series"],
            },
            "risk": {
                "risk_governor": optimization["risk_governor"],
                "fitness_components": optimization["fitness_components"],
                "best_adjusted_strategy_config": optimization["best_adjusted_strategy_config"],
            },
            "walk_forward": robustness["walk_forward"],
            "monte_carlo": robustness["monte_carlo"],
            "portfolio": robustness["portfolio"],
            "frontend_contract": _frontend_contract_section(optimization),
        },
        "config": asdict(active),
        "safety": {
            "real_backtest_used": False,
            "freqtrade_used": False,
            "exchange_api_used": False,
            "download_data_used": False,
            "deployment_used": False,
            "rollback_used": False,
        },
    }
    json.dumps(report, sort_keys=True)
    return report
