"""Tests for custom portfolio mock evaluation."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome
from bollinger_evolver.portfolio_custom import CustomPortfolioConfig, evaluate_custom_portfolio


class TestCustomPortfolio(unittest.TestCase):
    def test_custom_portfolio_runs_multiple_pairs(self) -> None:
        result = evaluate_custom_portfolio(
            CustomStrategyGenome(genome_id="portfolio-custom"),
            config=CustomPortfolioConfig(pairs=("BTC/USDT", "ETH/USDT"), seed=12, trade_count=20),
        )

        self.assertEqual(set(result["portfolio"]["pair_results"]), {"BTC/USDT", "ETH/USDT"})
        self.assertIn("portfolio_profit", result["portfolio"])
        self.assertIn("correlation_penalty", result["portfolio"])

    def test_custom_portfolio_is_json_serializable(self) -> None:
        result = evaluate_custom_portfolio(CustomStrategyGenome(genome_id="portfolio-json"))

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("custom-portfolio/v1", encoded)


if __name__ == "__main__":
    unittest.main()
