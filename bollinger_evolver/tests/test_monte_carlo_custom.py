"""Tests for custom Monte Carlo perturbation scaffold."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome
from bollinger_evolver.monte_carlo_custom import CustomMonteCarloConfig, run_custom_monte_carlo


class TestCustomMonteCarlo(unittest.TestCase):
    def test_custom_monte_carlo_returns_distribution_summary(self) -> None:
        result = run_custom_monte_carlo(
            CustomStrategyGenome(genome_id="mc-custom"),
            config=CustomMonteCarloConfig(runs=20, seed=9, trade_count=30),
        )

        self.assertEqual(result["monte_carlo"]["runs"], 20)
        self.assertIn("failure_rate", result["monte_carlo"])
        self.assertGreater(result["trade_count"], 0)

    def test_custom_monte_carlo_is_json_serializable(self) -> None:
        result = run_custom_monte_carlo(CustomStrategyGenome(genome_id="mc-json"))

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("custom-monte-carlo/v1", encoded)


if __name__ == "__main__":
    unittest.main()
