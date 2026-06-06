"""Tests for custom strategy regression fixtures."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.custom_strategy_schema import validate_custom_strategy_genome
from bollinger_evolver.fitness import calculate_risk_aware_fitness_breakdown
from bollinger_evolver.fixtures.custom_strategy_fixtures import (
    get_custom_strategy_fixture,
    get_custom_strategy_fixtures,
)
from bollinger_evolver.risk_governor import apply_risk_governor


class TestCustomStrategyFixtures(unittest.TestCase):
    def test_safe_default_fixture_validates(self) -> None:
        fixture = get_custom_strategy_fixture("safe_default")

        validate_custom_strategy_genome(fixture["genome"])

        self.assertEqual(fixture["strategy_config"]["schema_version"], "custom-strategy/v1")

    def test_high_risk_fixture_triggers_risk_governor(self) -> None:
        fixture = get_custom_strategy_fixture("high_leverage_high_drawdown")

        advice = apply_risk_governor(fixture["strategy_config"], fixture["metrics"])

        self.assertIn("reduced_risk_after_drawdown", advice["actions"])
        self.assertIn("reduced_risk_after_loss_streak", advice["actions"])
        self.assertLess(advice["adjusted_risk_per_trade"], advice["original_risk_per_trade"])

    def test_low_drawdown_fixture_has_better_risk_adjusted_profile(self) -> None:
        low = get_custom_strategy_fixture("low_leverage_low_drawdown")
        stress = get_custom_strategy_fixture("loss_streak_stress")

        low_score = calculate_risk_aware_fitness_breakdown(
            profit=low["metrics"]["profit"],
            drawdown=low["metrics"]["drawdown"],
            sharpe=low["metrics"]["sharpe"],
            win_rate=low["metrics"]["win_rate"],
            leverage=low["genome"]["leverage"],
            risk_per_trade=low["genome"]["risk_per_trade"],
            max_loss_streak=low["metrics"]["max_consecutive_losses"],
        )["final_fitness"]
        stress_score = calculate_risk_aware_fitness_breakdown(
            profit=stress["metrics"]["profit"],
            drawdown=stress["metrics"]["drawdown"],
            sharpe=stress["metrics"]["sharpe"],
            win_rate=stress["metrics"]["win_rate"],
            leverage=stress["genome"]["leverage"],
            risk_per_trade=stress["genome"]["risk_per_trade"],
            max_loss_streak=stress["metrics"]["max_consecutive_losses"],
        )["final_fitness"]

        self.assertGreater(low_score, stress_score)

    def test_all_fixtures_are_json_serializable(self) -> None:
        fixtures = get_custom_strategy_fixtures()

        encoded = json.dumps(fixtures, sort_keys=True)

        self.assertIn("portfolio_balanced", encoded)
        self.assertEqual(
            set(fixtures),
            {
                "safe_default",
                "high_leverage_high_drawdown",
                "low_leverage_low_drawdown",
                "loss_streak_stress",
                "portfolio_balanced",
            },
        )


if __name__ == "__main__":
    unittest.main()
