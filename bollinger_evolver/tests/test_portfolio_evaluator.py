"""Tests for mock multi-pair portfolio evaluation."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.portfolio_evaluator import evaluate_mock_portfolio


STRATEGY_CONFIG = {
    "genome_id": "portfolio-test",
    "bb_window": 24,
    "bb_stddev": 2.1,
    "stop_loss_pct": 0.03,
    "take_profit_pct": 0.08,
    "leverage": 1.5,
    "risk_per_trade": 0.01,
}
PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


class TestPortfolioEvaluator(unittest.TestCase):
    def test_portfolio_evaluator_runs_multiple_pairs(self) -> None:
        result = evaluate_mock_portfolio(STRATEGY_CONFIG, pairs=PAIRS, seed=11, trade_count=20)

        self.assertEqual(result["pairs"], PAIRS)
        self.assertEqual(len(result["pair_results"]), 3)

    def test_portfolio_result_contains_pair_results(self) -> None:
        result = evaluate_mock_portfolio(STRATEGY_CONFIG, pairs=PAIRS, seed=12, trade_count=20)

        self.assertIn("BTC/USDT", result["pair_results"])
        self.assertIn("profit", result["pair_results"]["BTC/USDT"])
        self.assertIn("max_drawdown", result["pair_results"]["BTC/USDT"])

    def test_portfolio_drawdown_is_aggregated(self) -> None:
        result = evaluate_mock_portfolio(STRATEGY_CONFIG, pairs=PAIRS, seed=13, trade_count=20)
        max_pair_drawdown = max(item["max_drawdown"] for item in result["pair_results"].values())

        self.assertGreaterEqual(result["portfolio_drawdown"], 0.0)
        self.assertLessEqual(result["portfolio_drawdown"], 1.0)
        self.assertGreaterEqual(result["portfolio_drawdown"], min(max_pair_drawdown, result["portfolio_drawdown"]))

    def test_portfolio_result_is_json_serializable(self) -> None:
        result = evaluate_mock_portfolio(STRATEGY_CONFIG, pairs=PAIRS, seed=14, trade_count=20)

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("mock-portfolio-evaluation/v1", encoded)
        self.assertIn("correlation_penalty", result)


if __name__ == "__main__":
    unittest.main()
