"""Tests for Monte Carlo stress testing on synthetic trades."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.monte_carlo import MonteCarloConfig, run_monte_carlo_stress_test


TRADES = [
    {"pnl_pct": 0.02},
    {"pnl_pct": -0.01},
    {"pnl_pct": 0.015},
    {"pnl_pct": -0.03},
    {"pnl_pct": 0.025},
    {"pnl_pct": 0.01},
]


class TestMonteCarlo(unittest.TestCase):
    def test_monte_carlo_is_deterministic_with_seed(self) -> None:
        config = MonteCarloConfig(runs=50, seed=123, perturbation=0.001)

        first = run_monte_carlo_stress_test(TRADES, config=config)
        second = run_monte_carlo_stress_test(TRADES, config=config)

        self.assertEqual(first, second)

    def test_monte_carlo_returns_distribution_summary(self) -> None:
        result = run_monte_carlo_stress_test(TRADES, config=MonteCarloConfig(runs=25, seed=7))

        self.assertEqual(result["runs"], 25)
        self.assertIn("profit_p05", result)
        self.assertIn("profit_median", result)
        self.assertIn("drawdown_p95", result)

    def test_monte_carlo_failure_rate_between_zero_and_one(self) -> None:
        result = run_monte_carlo_stress_test(
            TRADES,
            config=MonteCarloConfig(runs=50, seed=9, failure_drawdown_threshold=0.02),
        )

        self.assertGreaterEqual(result["failure_rate"], 0.0)
        self.assertLessEqual(result["failure_rate"], 1.0)

    def test_monte_carlo_result_is_json_serializable(self) -> None:
        result = run_monte_carlo_stress_test(TRADES, config=MonteCarloConfig(runs=10, seed=2))

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("monte-carlo-stress/v1", encoded)


if __name__ == "__main__":
    unittest.main()
