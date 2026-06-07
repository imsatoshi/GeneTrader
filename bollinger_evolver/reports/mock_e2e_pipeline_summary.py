"""JSON-safe mock E2E pipeline summary for frontend and audit consumers.

This module summarizes existing mock-first pipeline output. It does not run
Freqtrade, connect to exchanges, download data, deploy, rollback, or write
files.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from bollinger_evolver.ga_optimization_custom import (
    CustomOptimizationConfig,
    run_custom_ga_optimization,
)


SCHEMA_VERSION = "mock-e2e-pipeline-summary/v1"
GOLDEN_RISK_FIXTURES = (
    "safe_default.json",
    "high_leverage.json",
    "high_drawdown.json",
    "loss_streak.json",
    "portfolio_exposure_breach.json",
    "monte_carlo_failure.json",
    "walk_forward_overfit.json",
    "risk_scenario_panel_sample.json",
    "local_health_enhanced_sample.json",
    "mock_e2e_pipeline_summary_sample.json",
)


@dataclass(frozen=True)
class MockE2EPipelineSummaryConfig:
    run_id: str = "mock-e2e-summary"
    population_size: int = 6
    generations: int = 1
    seed: int = 384
    top_n: int = 3
    trade_count: int = 30
    pairs: tuple[str, ...] = ("BTC/USDT", "ETH/USDT")
    timeframe: str = "1h"
    monte_carlo_runs: int = 20


def _metric_summary(payload: dict[str, Any]) -> dict[str, Any]:
    robustness = payload["robustness_summary"]
    walk_forward = robustness["walk_forward"]["walk_forward"]
    monte_carlo = robustness["monte_carlo"]["monte_carlo"]
    portfolio = robustness["portfolio"]["portfolio"]
    return {
        "best_fitness": float(payload["best_fitness"]),
        "average_fitness": float(payload["average_fitness"]),
        "optimization_score": float(payload["optimization_score"]),
        "stability_score": float(walk_forward["stability_score"]),
        "failure_rate": float(monte_carlo["failure_rate"]),
        "portfolio_profit": float(portfolio["portfolio_profit"]),
        "portfolio_drawdown": float(portfolio["portfolio_drawdown"]),
        "leaderboard_rows": len(payload["leaderboard"]),
        "fitness_points": len(payload["fitness_series"]),
    }


def _session_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "mock-e2e-session-summary/v1",
        "run_id": payload["run_id"],
        "generation": int(payload["generation"]),
        "population_size": int(payload["population_size"]),
        "best_fitness": float(payload["best_fitness"]),
        "average_fitness": float(payload["average_fitness"]),
        "best_genome_id": payload["best_genome"]["genome_id"],
        "leaderboard": payload["leaderboard"],
        "fitness_series": payload["fitness_series"],
    }


def _risk_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    robustness = payload["robustness_summary"]
    walk_forward = robustness["walk_forward"]["walk_forward"]
    monte_carlo = robustness["monte_carlo"]["monte_carlo"]
    portfolio = robustness["portfolio"]["portfolio"]
    pair_results = portfolio["pair_results"]
    max_loss_streak = max(int(result["max_consecutive_losses"]) for result in pair_results.values())
    risk_governor = payload["risk_governor"]
    warnings = [str(item) for item in risk_governor.get("warnings", [])]
    return {
        "schema_version": "mock-e2e-risk-metrics/v1",
        "risk_governor_adjustments": len(risk_governor.get("adjustments", [])),
        "risk_governor_warnings": warnings,
        "warning_count": len(warnings),
        "max_drawdown": float(portfolio["portfolio_drawdown"]),
        "max_loss_streak": max_loss_streak,
        "stability_score": float(walk_forward["stability_score"]),
        "train_validation_gap": float(walk_forward["train_validation_gap"]),
        "validation_test_gap": float(walk_forward["validation_test_gap"]),
        "monte_carlo_failure_rate": float(monte_carlo["failure_rate"]),
        "monte_carlo_drawdown_p95": float(monte_carlo["drawdown_p95"]),
        "leverage": float(payload["best_strategy_config"]["position_sizing"]["leverage"]),
        "risk_per_trade": float(payload["best_strategy_config"]["position_sizing"]["risk_per_trade"]),
        "max_portfolio_exposure": float(
            payload["best_strategy_config"]["position_sizing"]["max_portfolio_exposure"]
        ),
    }


def _portfolio_summary(payload: dict[str, Any]) -> dict[str, Any]:
    portfolio = payload["robustness_summary"]["portfolio"]["portfolio"]
    return {
        "schema_version": "mock-e2e-portfolio-summary/v1",
        "portfolio_profit": float(portfolio["portfolio_profit"]),
        "portfolio_drawdown": float(portfolio["portfolio_drawdown"]),
        "correlation_penalty": float(portfolio["correlation_penalty"]),
        "pair_results": portfolio["pair_results"],
    }


def _golden_fixture_coverage() -> dict[str, Any]:
    return {
        "schema_version": "golden-fixture-coverage/v1",
        "fixture_count": len(GOLDEN_RISK_FIXTURES),
        "fixtures": list(GOLDEN_RISK_FIXTURES),
        "required_schema_version_field": True,
        "json_safe": True,
    }


def _artifact_contract(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "mock-e2e-artifact-contract/v1",
        "run_id": payload["run_id"],
        "session_summary_fields": [
            "run_id",
            "generation",
            "population_size",
            "best_fitness",
            "leaderboard",
            "fitness_series",
        ],
        "artifact_sections": [
            "session_summary",
            "risk_metrics",
            "portfolio",
            "frontend_contract",
            "golden_fixture_coverage",
        ],
        "file_write_used": False,
    }


def _module_summary(payload: dict[str, Any]) -> list[dict[str, Any]]:
    robustness = payload["robustness_summary"]
    return [
        {
            "module": "ga",
            "schema_version": payload["schema_version"],
            "status": "PASS",
            "mock_only": True,
            "records": len(payload["leaderboard"]),
        },
        {
            "module": "risk",
            "schema_version": payload["risk_governor"]["schema_version"],
            "status": "PASS",
            "mock_only": True,
            "records": len(payload["risk_governor"].get("adjustments", [])),
        },
        {
            "module": "walk_forward",
            "schema_version": robustness["walk_forward"]["schema_version"],
            "status": "PASS",
            "mock_only": True,
            "records": len(
                [
                    name
                    for name in ("train", "validation", "test")
                    if name in robustness["walk_forward"]["walk_forward"]
                ]
            ),
        },
        {
            "module": "monte_carlo",
            "schema_version": robustness["monte_carlo"]["schema_version"],
            "status": "PASS",
            "mock_only": True,
            "records": int(robustness["monte_carlo"]["monte_carlo"]["runs"]),
        },
        {
            "module": "portfolio",
            "schema_version": robustness["portfolio"]["schema_version"],
            "status": "PASS",
            "mock_only": True,
            "records": len(robustness["portfolio"]["portfolio"]["pair_results"]),
        },
        {
            "module": "frontend_contract",
            "schema_version": "frontend-contract-summary/v1",
            "status": "PASS",
            "mock_only": True,
            "records": len(payload["leaderboard"]) + len(payload["fitness_series"]),
        },
    ]


def build_mock_e2e_pipeline_summary(
    config: MockE2EPipelineSummaryConfig | None = None,
) -> dict[str, Any]:
    """Build a compact JSON-safe mock pipeline summary without file writes."""

    active = config or MockE2EPipelineSummaryConfig()
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
    summary = {
        "schema_version": SCHEMA_VERSION,
        "source": "mock-first",
        "run_id": active.run_id,
        "status": "PASS",
        "metrics": _metric_summary(optimization),
        "session_summary": _session_summary(optimization),
        "risk_metrics": _risk_metrics(optimization),
        "portfolio": _portfolio_summary(optimization),
        "modules": _module_summary(optimization),
        "frontend_contract": {
            "leaderboard": ["rank", "genome_id", "fitness", "profit", "drawdown"],
            "fitness_series": ["generation", "best_fitness", "average_fitness"],
            "risk_summary": ["schema_version", "adjustments", "warnings"],
            "robustness_summary": ["walk_forward", "monte_carlo", "portfolio"],
        },
        "golden_fixture_coverage": _golden_fixture_coverage(),
        "artifact_contract": _artifact_contract(optimization),
        "config": asdict(active),
        "safety": {
            "real_backtest_used": False,
            "freqtrade_used": False,
            "download_data_used": False,
            "hyperopt_used": False,
            "exchange_api_used": False,
            "deployment_used": False,
            "rollback_used": False,
            "file_write_used": False,
        },
    }
    json.dumps(summary, sort_keys=True)
    return summary
