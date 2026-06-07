"""Tests for mock account-level risk budget simulation."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.risk_budget import RiskBudgetConfig, simulate_risk_budget


class TestRiskBudgetSimulator(unittest.TestCase):
    def test_risk_budget_allows_within_limits(self) -> None:
        result = simulate_risk_budget(
            [
                {"pair": "BTC/USDT", "exposure": 0.10, "leverage": 2.0},
                {"pair": "ETH/USDT", "exposure": 0.08, "leverage": 1.5},
            ]
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["total_exposure"], 0.18)
        self.assertEqual(result["violations"], [])

    def test_risk_budget_fails_when_portfolio_exposure_exceeds_limit(self) -> None:
        result = simulate_risk_budget(
            [{"pair": "BTC/USDT", "exposure": 0.35, "leverage": 1.0}],
            config=RiskBudgetConfig(max_portfolio_exposure=0.30),
        )

        self.assertFalse(result["ok"])
        self.assertIn("portfolio_exposure_exceeded", [item["code"] for item in result["violations"]])

    def test_risk_budget_fails_when_pair_exposure_exceeds_limit(self) -> None:
        result = simulate_risk_budget(
            [
                {"pair": "BTC/USDT", "exposure": 0.10, "leverage": 1.0},
                {"pair": "BTC/USDT", "exposure": 0.08, "leverage": 1.0},
            ],
            config=RiskBudgetConfig(max_pair_exposure=0.15),
        )

        self.assertFalse(result["ok"])
        self.assertIn("pair_exposure_exceeded", [item["code"] for item in result["violations"]])

    def test_risk_budget_warns_when_leverage_usage_exceeds_limit(self) -> None:
        result = simulate_risk_budget(
            [{"pair": "SOL/USDT", "exposure": 0.20, "leverage": 8.0}],
            config=RiskBudgetConfig(max_portfolio_exposure=0.30, max_pair_exposure=0.30, max_leverage_usage=1.0),
        )

        self.assertTrue(result["ok"])
        self.assertIn("leverage_usage_exceeded", [item["code"] for item in result["warnings"]])

    def test_risk_budget_recommends_reduction_after_loss_streak(self) -> None:
        result = simulate_risk_budget(
            [{"pair": "ETH/USDT", "exposure": 0.05, "leverage": 2.0}],
            loss_streak=5,
        )

        self.assertEqual(result["adjusted_risk_multiplier"], 0.5)
        self.assertIn("reduce_risk_after_loss_streak", [item["code"] for item in result["recommendations"]])

    def test_risk_budget_output_is_json_serializable(self) -> None:
        result = simulate_risk_budget([{"pair": "BTC/USDT", "exposure": 0.10, "leverage": 1.0}])

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("risk-budget-simulation/v1", encoded)


if __name__ == "__main__":
    unittest.main()
