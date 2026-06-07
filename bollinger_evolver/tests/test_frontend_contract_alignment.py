"""Python-to-frontend contract alignment tests.

These tests model the frontend camelCase adapter expectations without reaching
for a backend, filesystem API, or real exchange data.
"""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from typing import Any, Mapping

from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.ga_optimization_custom import (
    CustomOptimizationConfig,
    run_custom_ga_optimization,
)
from bollinger_evolver.session_summary import build_ga_session_summary
from bollinger_evolver.strategy_explainer import build_strategy_explainability_report
from bollinger_evolver.trading_system_adapter import build_position_sizing_preview, build_trading_system_config


GA_REQUIRED_FIELDS = (
    "schema_version",
    "source",
    "run_id",
    "generation",
    "population_size",
    "best_fitness",
    "average_fitness",
    "diversity",
    "best_genome",
    "fitness_series",
    "leaderboard",
)
FITNESS_POINT_REQUIRED_FIELDS = ("generation", "best_fitness", "average_fitness", "diversity")
LEADERBOARD_REQUIRED_FIELDS = (
    "rank",
    "genome_id",
    "fitness",
    "profit",
    "drawdown",
    "sharpe",
    "win_rate",
    "fitness_components",
    "genome",
)
CUSTOM_LEADERBOARD_REQUIRED_FIELDS = (
    "rank",
    "genome",
    "mock_backtest",
    "risk_governor",
    "fitness",
    "fitness_components",
)
CUSTOM_RUN_REQUIRED_FIELDS = (
    "run_id",
    "fitness_series",
    "leaderboard",
    "best_genome",
    "best_strategy_config",
    "risk_governor",
    "fitness_components",
    "robustness_summary",
)
POSITION_SIZING_REQUIRED_FIELDS = (
    "schema_version",
    "position_value",
    "margin_required",
    "risk_amount",
    "leverage",
    "warnings",
)
EXPLAINABILITY_REQUIRED_FIELDS = (
    "schema_version",
    "summary",
    "entry_logic",
    "exit_logic",
    "risk_logic",
    "warnings",
    "fitness_explanation",
)


def _require_fields(payload: Mapping[str, Any], fields: tuple[str, ...], *, context: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ValueError(f"missing_frontend_contract_field:{context}:{','.join(missing)}")


def _adapt_leaderboard_entry(item: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(item, LEADERBOARD_REQUIRED_FIELDS, context="leaderboard")
    return {
        "rank": item["rank"],
        "genomeId": item["genome_id"],
        "fitness": item["fitness"],
        "profit": item["profit"],
        "drawdown": item["drawdown"],
        "sharpe": item["sharpe"],
        "winRate": item["win_rate"],
        "fitnessComponents": item["fitness_components"],
        "maxLossStreak": item.get("max_consecutive_losses"),
        "leverage": item.get("leverage"),
        "riskPerTrade": item.get("risk_per_trade"),
        "genome": item["genome"],
    }


def _adapt_custom_leaderboard_entry(item: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(item, CUSTOM_LEADERBOARD_REQUIRED_FIELDS, context="custom_leaderboard")
    genome = item["genome"]
    mock_backtest = item["mock_backtest"]
    _require_fields(genome, ("genome_id",), context="custom_leaderboard_genome")
    _require_fields(
        mock_backtest,
        ("profit", "drawdown", "sharpe", "win_rate", "risk_per_trade", "leverage"),
        context="custom_leaderboard_mock_backtest",
    )
    return {
        "rank": item["rank"],
        "genomeId": genome["genome_id"],
        "fitness": item["fitness"],
        "profit": mock_backtest["profit"],
        "drawdown": mock_backtest["drawdown"],
        "sharpe": mock_backtest["sharpe"],
        "winRate": mock_backtest["win_rate"],
        "fitnessComponents": item["fitness_components"],
        "leverage": mock_backtest["leverage"],
        "riskPerTrade": mock_backtest["risk_per_trade"],
        "riskGovernor": item["risk_governor"],
        "genome": genome,
    }


def adapt_ga_session_summary_for_frontend(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Map the Python GA session summary shape to frontend camelCase fields."""

    _require_fields(summary, GA_REQUIRED_FIELDS, context="summary")
    for item in summary["fitness_series"]:
        _require_fields(item, FITNESS_POINT_REQUIRED_FIELDS, context="fitness_series")
    return {
        "schemaVersion": summary["schema_version"],
        "source": summary["source"],
        "runId": summary["run_id"],
        "generation": summary["generation"],
        "populationSize": summary["population_size"],
        "bestFitness": summary["best_fitness"],
        "averageFitness": summary["average_fitness"],
        "diversity": summary["diversity"],
        "bestGenome": summary["best_genome"],
        "fitnessSeries": [
            {
                "generation": item["generation"],
                "bestFitness": item["best_fitness"],
                "averageFitness": item["average_fitness"],
                "diversity": item["diversity"],
            }
            for item in summary["fitness_series"]
        ],
        "leaderboard": [_adapt_leaderboard_entry(item) for item in summary["leaderboard"]],
    }


def adapt_custom_robustness_summary_for_frontend(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, ("robustness_summary", "risk_governor", "fitness_components"), context="custom")
    robustness = payload["robustness_summary"]
    _require_fields(robustness, ("walk_forward", "monte_carlo", "portfolio"), context="robustness")
    return {
        "riskGovernor": payload["risk_governor"],
        "fitnessComponents": payload["fitness_components"],
        "robustnessSummary": {
            "walkForward": robustness["walk_forward"],
            "monteCarlo": robustness["monte_carlo"],
            "portfolio": robustness["portfolio"],
        },
    }


def adapt_custom_run_detail_for_frontend(payload: Mapping[str, Any]) -> dict[str, Any]:
    _require_fields(payload, CUSTOM_RUN_REQUIRED_FIELDS, context="custom_detail")
    robustness = payload["robustness_summary"]
    _require_fields(robustness, ("walk_forward", "monte_carlo", "portfolio"), context="custom_detail_robustness")
    portfolio_wrapper = robustness["portfolio"]
    _require_fields(portfolio_wrapper, ("portfolio",), context="portfolio_wrapper")
    portfolio = portfolio_wrapper["portfolio"]
    _require_fields(portfolio, ("portfolio_profit", "portfolio_drawdown", "pair_results"), context="portfolio")

    trading_system_config = build_trading_system_config(payload["best_strategy_config"])
    position_sizing = build_position_sizing_preview(trading_system_config, equity=10_000.0)
    _require_fields(position_sizing, POSITION_SIZING_REQUIRED_FIELDS, context="position_sizing")
    explainability = build_strategy_explainability_report(
        payload["best_strategy_config"],
        metrics={
            "drawdown": portfolio["portfolio_drawdown"],
            "stability_score": robustness["walk_forward"]["walk_forward"]["stability_score"],
        },
        risk_governor=payload["risk_governor"],
        position_sizing_preview=position_sizing,
        fitness_components=payload["fitness_components"],
    )
    _require_fields(explainability, EXPLAINABILITY_REQUIRED_FIELDS, context="explainability")

    return {
        "runId": payload["run_id"],
        "leaderboard": [_adapt_custom_leaderboard_entry(item) for item in payload["leaderboard"]],
        "fitnessSeries": [
            {
                "generation": item["generation"],
                "bestFitness": item["best_fitness"],
                "averageFitness": item["average_fitness"],
            }
            for item in payload["fitness_series"]
        ],
        "riskSummary": payload["risk_governor"],
        "portfolioSummary": {
            "portfolioProfit": portfolio["portfolio_profit"],
            "portfolioDrawdown": portfolio["portfolio_drawdown"],
            "pairResults": portfolio["pair_results"],
        },
        "strategyDetail": {
            "bestGenome": payload["best_genome"],
            "strategyConfig": payload["best_strategy_config"],
            "tradingSystemConfig": trading_system_config,
        },
        "positionSizingPreview": position_sizing,
        "explainabilitySummary": explainability,
    }


class TestFrontendContractAlignment(unittest.TestCase):
    def _summary(self) -> dict[str, Any]:
        result = run_ga_execution(GAExecutionConfig(population_size=5, generations=2, seed=200))
        return build_ga_session_summary(result, top_n=3, run_id="frontend-contract-run")

    def test_ga_session_summary_maps_to_frontend_contract(self) -> None:
        adapted = adapt_ga_session_summary_for_frontend(self._summary())

        self.assertEqual(adapted["schemaVersion"], "ga-session-summary/v1")
        self.assertEqual(adapted["runId"], "frontend-contract-run")
        self.assertEqual(adapted["populationSize"], 5)
        self.assertIn("fitnessSeries", adapted)
        self.assertIn("leaderboard", adapted)
        json.dumps(adapted, sort_keys=True)

    def test_leaderboard_maps_to_frontend_contract(self) -> None:
        adapted = adapt_ga_session_summary_for_frontend(self._summary())
        entry = adapted["leaderboard"][0]

        self.assertIn("genomeId", entry)
        self.assertIn("winRate", entry)
        self.assertIn("fitnessComponents", entry)
        self.assertIn("riskPerTrade", entry)

    def test_fitness_series_maps_to_frontend_contract(self) -> None:
        adapted = adapt_ga_session_summary_for_frontend(self._summary())
        point = adapted["fitnessSeries"][0]

        self.assertEqual(set(point), {"generation", "bestFitness", "averageFitness", "diversity"})

    def test_missing_ga_session_field_fails_clearly(self) -> None:
        payload = deepcopy(self._summary())
        payload.pop("run_id")

        with self.assertRaisesRegex(ValueError, "missing_frontend_contract_field:summary:run_id"):
            adapt_ga_session_summary_for_frontend(payload)

    def test_missing_leaderboard_field_fails_clearly(self) -> None:
        payload = deepcopy(self._summary())
        payload["leaderboard"][0].pop("genome_id")

        with self.assertRaisesRegex(ValueError, "missing_frontend_contract_field:leaderboard:genome_id"):
            adapt_ga_session_summary_for_frontend(payload)

    def test_custom_risk_and_robustness_summary_maps_to_frontend_contract(self) -> None:
        payload = run_custom_ga_optimization(
            CustomOptimizationConfig(
                population_size=6,
                generations=1,
                seed=202,
                monte_carlo_runs=10,
                pairs=("BTC/USDT", "ETH/USDT"),
            )
        )

        adapted = adapt_custom_robustness_summary_for_frontend(payload)

        self.assertIn("riskGovernor", adapted)
        self.assertIn("fitnessComponents", adapted)
        self.assertIn("walkForward", adapted["robustnessSummary"])
        self.assertIn("monteCarlo", adapted["robustnessSummary"])
        self.assertIn("portfolio", adapted["robustnessSummary"])
        json.dumps(adapted, sort_keys=True)

    def test_custom_strategy_detail_maps_to_frontend_contract(self) -> None:
        payload = run_custom_ga_optimization(
            CustomOptimizationConfig(
                run_id="frontend-custom-detail",
                population_size=6,
                generations=1,
                seed=327,
                monte_carlo_runs=10,
                pairs=("BTC/USDT", "ETH/USDT"),
            )
        )

        adapted = adapt_custom_run_detail_for_frontend(payload)

        self.assertEqual(adapted["runId"], "frontend-custom-detail")
        self.assertIn("leaderboard", adapted)
        self.assertIn("fitnessSeries", adapted)
        self.assertIn("riskSummary", adapted)
        self.assertIn("portfolioSummary", adapted)
        self.assertIn("strategyDetail", adapted)
        self.assertIn("positionSizingPreview", adapted)
        self.assertIn("explainabilitySummary", adapted)
        self.assertIn("portfolioDrawdown", adapted["portfolioSummary"])
        self.assertIn("position_value", adapted["positionSizingPreview"])
        self.assertIn("fitness_explanation", adapted["explainabilitySummary"])
        json.dumps(adapted, sort_keys=True)

    def test_missing_custom_strategy_detail_field_fails_clearly(self) -> None:
        payload = run_custom_ga_optimization(
            CustomOptimizationConfig(
                run_id="frontend-custom-detail-missing",
                population_size=6,
                generations=1,
                seed=328,
                monte_carlo_runs=10,
            )
        )
        payload.pop("best_strategy_config")

        with self.assertRaisesRegex(ValueError, "missing_frontend_contract_field:custom_detail:best_strategy_config"):
            adapt_custom_run_detail_for_frontend(payload)


if __name__ == "__main__":
    unittest.main()
