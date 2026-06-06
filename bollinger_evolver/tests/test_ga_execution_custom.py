"""Tests for custom strategy GA execution scaffold."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.ga_execution_custom import (
    CustomGAExecutionConfig,
    build_custom_ga_session_summary,
    evaluate_custom_genome,
    run_custom_ga_execution,
)
from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome
from bollinger_evolver.risk_governor import RiskGovernorConfig


class TestCustomGAExecution(unittest.TestCase):
    def test_custom_ga_execution_runs_mock_first(self) -> None:
        result = run_custom_ga_execution(CustomGAExecutionConfig(population_size=6, generations=2, seed=42))

        self.assertEqual(len(result.generations), 2)
        self.assertIsNotNone(result.final_best)
        self.assertIn("mock-backtest-result/v1", json.dumps(result.final_best.to_dict(), sort_keys=True))

    def test_custom_ga_session_summary_has_leaderboard_and_fitness_series(self) -> None:
        result = run_custom_ga_execution(CustomGAExecutionConfig(population_size=5, generations=3, seed=7, top_n=3))
        summary = build_custom_ga_session_summary(result)

        self.assertEqual(summary["schema_version"], "custom-ga-session-summary/v1")
        self.assertEqual(len(summary["fitness_series"]), 3)
        self.assertLessEqual(len(summary["leaderboard"]), 3)
        self.assertEqual(summary["source"], "custom-strategy-mock-ga")

    def test_custom_ga_evaluation_applies_risk_governor(self) -> None:
        evaluation = evaluate_custom_genome(
            CustomStrategyGenome(genome_id="risk-heavy", leverage=3.0, risk_per_trade=0.02),
            seed=11,
            risk_config=RiskGovernorConfig(max_leverage=2.0, max_risk_per_trade=0.01),
        )

        self.assertTrue(evaluation.adjusted_strategy_config["risk_governor_applied"])
        self.assertLessEqual(evaluation.adjusted_strategy_config["leverage"], 2.0)
        self.assertLessEqual(evaluation.adjusted_strategy_config["risk_per_trade"], 0.01)
        self.assertIn("risk-governor/v1", json.dumps(evaluation.to_dict(), sort_keys=True))

    def test_custom_ga_result_is_json_serializable(self) -> None:
        result = run_custom_ga_execution(CustomGAExecutionConfig(population_size=4, generations=1, seed=3))

        encoded = json.dumps(build_custom_ga_session_summary(result), sort_keys=True)
        self.assertIn("custom-ga-seed-3", encoded)


if __name__ == "__main__":
    unittest.main()
