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


if __name__ == "__main__":
    unittest.main()
