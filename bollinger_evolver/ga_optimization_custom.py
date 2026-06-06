"""Custom strategy GA optimization entrypoint for mock-first pipelines."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.custom_strategy_schema import custom_strategy_config_from_genome
from bollinger_evolver.ga_execution_custom import (
    CustomGAExecutionConfig,
    build_custom_ga_session_summary,
    run_custom_ga_execution,
)
from bollinger_evolver.monte_carlo_custom import CustomMonteCarloConfig, run_custom_monte_carlo
from bollinger_evolver.portfolio_custom import CustomPortfolioConfig, evaluate_custom_portfolio
from bollinger_evolver.walk_forward_custom import CustomWalkForwardConfig, evaluate_custom_walk_forward


@dataclass(frozen=True)
class CustomOptimizationConfig:
    run_id: str = "custom-ga-run"
    population_size: int = 30
    generations: int = 5
    seed: int = 42
    top_n: int = 10
    trade_count: int = 100
    pairs: tuple[str, ...] = ("BTC/USDT",)
    timeframe: str = "1h"
    monte_carlo_runs: int = 100


def _optimization_score(
    *,
    best_fitness: float,
    walk_forward: dict[str, Any],
    monte_carlo: dict[str, Any],
    portfolio: dict[str, Any],
) -> float:
    stability = float(walk_forward["walk_forward"]["stability_score"])
    failure_rate = float(monte_carlo["monte_carlo"]["failure_rate"])
    portfolio_drawdown = float(portfolio["portfolio"]["portfolio_drawdown"])
    return round(best_fitness + (0.20 * stability) - failure_rate - (0.50 * portfolio_drawdown), 6)


def run_custom_ga_optimization(
    config: CustomOptimizationConfig | None = None,
) -> dict[str, Any]:
    """Run custom strategy optimization through mock-only robustness checks."""

    active = config or CustomOptimizationConfig()
    if active.population_size <= 0:
        raise ValueError("population_size_must_be_positive")
    if active.generations <= 0:
        raise ValueError("generations_must_be_positive")
    if active.top_n <= 0:
        raise ValueError("top_n_must_be_positive")
    if not active.pairs:
        raise ValueError("pairs_required")

    ga_result = run_custom_ga_execution(
        CustomGAExecutionConfig(
            population_size=active.population_size,
            generations=active.generations,
            seed=active.seed,
            top_n=active.top_n,
            pair=active.pairs[0],
            timeframe=active.timeframe,
            trade_count=active.trade_count,
        ),
        run_id=active.run_id,
    )
    session_summary = build_custom_ga_session_summary(ga_result, top_n=active.top_n)
    best_evaluation = ga_result.final_best
    if best_evaluation is None:
        raise ValueError("custom_ga_result_has_no_best_evaluation")
    best_genome = best_evaluation.genome
    best_strategy_config = custom_strategy_config_from_genome(best_genome)

    walk_forward = evaluate_custom_walk_forward(
        best_genome,
        config=CustomWalkForwardConfig(
            base_seed=active.seed,
            trade_count=active.trade_count,
            pair=active.pairs[0],
            timeframe=active.timeframe,
        ),
    )
    monte_carlo = run_custom_monte_carlo(
        best_genome,
        config=CustomMonteCarloConfig(
            runs=active.monte_carlo_runs,
            seed=active.seed,
            trade_count=active.trade_count,
            pair=active.pairs[0],
            timeframe=active.timeframe,
        ),
    )
    portfolio = evaluate_custom_portfolio(
        best_genome,
        config=CustomPortfolioConfig(
            pairs=active.pairs,
            timeframe=active.timeframe,
            seed=active.seed,
            trade_count=active.trade_count,
        ),
    )
    best_fitness = float(session_summary["best_fitness"] or 0.0)
    payload = {
        "schema_version": "custom-ga-optimization/v1",
        "source": "mock-custom-strategy-ga",
        "run_id": active.run_id,
        "status": "completed",
        "generation": int(session_summary["generation"]),
        "population_size": active.population_size,
        "best_fitness": best_fitness,
        "average_fitness": float(ga_result.generations[-1].average_fitness),
        "optimization_score": _optimization_score(
            best_fitness=best_fitness,
            walk_forward=walk_forward,
            monte_carlo=monte_carlo,
            portfolio=portfolio,
        ),
        "fitness_series": session_summary["fitness_series"],
        "leaderboard": session_summary["leaderboard"],
        "best_genome": session_summary["best_genome"],
        "best_strategy_config": best_strategy_config,
        "best_adjusted_strategy_config": best_evaluation.adjusted_strategy_config,
        "risk_governor": best_evaluation.risk_governor,
        "fitness_components": dict(best_evaluation.fitness_components),
        "robustness_summary": {
            "walk_forward": walk_forward,
            "monte_carlo": monte_carlo,
            "portfolio": portfolio,
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
    json.dumps(payload, sort_keys=True)
    return payload
