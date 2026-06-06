"""Tests for custom strategy GA optimization entrypoint."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.ga_optimization_custom import CustomOptimizationConfig, run_custom_ga_optimization


class TestCustomGAOptimization(unittest.TestCase):
    def test_custom_ga_optimization_returns_json_safe_summary(self) -> None:
        result = run_custom_ga_optimization(CustomOptimizationConfig(population_size=6, generations=2, seed=21))

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("custom-ga-optimization/v1", encoded)
        self.assertEqual(result["status"], "completed")

    def test_custom_ga_optimization_is_deterministic_with_seed(self) -> None:
        config = CustomOptimizationConfig(population_size=6, generations=2, seed=22, monte_carlo_runs=20)

        first = run_custom_ga_optimization(config)
        second = run_custom_ga_optimization(config)

        self.assertEqual(first["best_fitness"], second["best_fitness"])
        self.assertEqual(first["fitness_series"], second["fitness_series"])
        self.assertEqual(first["optimization_score"], second["optimization_score"])

    def test_custom_ga_optimization_contains_leaderboard(self) -> None:
        result = run_custom_ga_optimization(CustomOptimizationConfig(population_size=8, generations=2, seed=23, top_n=4))

        self.assertEqual(len(result["leaderboard"]), 4)
        scores = [entry["fitness"] for entry in result["leaderboard"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_custom_ga_optimization_contains_fitness_series(self) -> None:
        result = run_custom_ga_optimization(CustomOptimizationConfig(population_size=6, generations=3, seed=24))

        self.assertEqual([item["generation"] for item in result["fitness_series"]], [1, 2, 3])

    def test_custom_ga_optimization_contains_risk_governor_adjustments(self) -> None:
        result = run_custom_ga_optimization(CustomOptimizationConfig(population_size=6, generations=2, seed=25))

        self.assertIn("risk-governor/v1", json.dumps(result["risk_governor"], sort_keys=True))
        self.assertTrue(result["best_adjusted_strategy_config"]["risk_governor_applied"])

    def test_custom_ga_optimization_contains_robustness_summary(self) -> None:
        result = run_custom_ga_optimization(
            CustomOptimizationConfig(
                population_size=6,
                generations=2,
                seed=26,
                pairs=("BTC/USDT", "ETH/USDT"),
                monte_carlo_runs=20,
            )
        )

        self.assertIn("walk_forward", result["robustness_summary"])
        self.assertIn("monte_carlo", result["robustness_summary"])
        self.assertIn("portfolio", result["robustness_summary"])
        self.assertEqual(set(result["robustness_summary"]["portfolio"]["portfolio"]["pair_results"]), {"BTC/USDT", "ETH/USDT"})

    def test_custom_ga_optimization_does_not_use_real_execution(self) -> None:
        result = run_custom_ga_optimization(CustomOptimizationConfig(population_size=6, generations=2, seed=27))

        self.assertFalse(result["safety"]["real_backtest_used"])
        self.assertFalse(result["safety"]["freqtrade_used"])
        self.assertFalse(result["safety"]["exchange_api_used"])


if __name__ == "__main__":
    unittest.main()
