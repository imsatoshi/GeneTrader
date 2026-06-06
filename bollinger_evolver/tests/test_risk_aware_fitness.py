"""Focused tests for risk-aware mock GA fitness scoring."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.fitness import (
    RiskAwareFitnessConfig,
    calculate_risk_aware_fitness,
    calculate_risk_aware_fitness_breakdown,
)


class TestRiskAwareFitness(unittest.TestCase):
    def test_risk_aware_fitness_rewards_profit(self) -> None:
        low_profit = calculate_risk_aware_fitness(
            profit=0.05,
            drawdown=0.05,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
        )
        high_profit = calculate_risk_aware_fitness(
            profit=0.25,
            drawdown=0.05,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
        )

        self.assertGreater(high_profit, low_profit)

    def test_risk_aware_fitness_penalizes_drawdown(self) -> None:
        low_drawdown = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.04,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
        )
        high_drawdown = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.35,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
        )

        self.assertLess(high_drawdown, low_drawdown)

    def test_risk_aware_fitness_penalizes_excess_leverage(self) -> None:
        conservative = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
        )
        levered = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=8.0,
            risk_per_trade=0.01,
        )

        self.assertLess(levered, conservative)

    def test_risk_aware_fitness_penalizes_excess_risk_per_trade(self) -> None:
        low_risk = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
        )
        high_risk = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.08,
        )

        self.assertLess(high_risk, low_risk)

    def test_risk_aware_fitness_penalizes_loss_streak(self) -> None:
        low_streak = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
            max_loss_streak=1,
        )
        high_streak = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
            max_loss_streak=9,
        )

        self.assertLess(high_streak, low_streak)

    def test_low_drawdown_strategy_can_beat_high_profit_high_risk_strategy(self) -> None:
        conservative = calculate_risk_aware_fitness(
            profit=0.16,
            drawdown=0.04,
            sharpe=1.2,
            win_rate=0.58,
            leverage=2.0,
            risk_per_trade=0.01,
            max_loss_streak=1,
        )
        risky = calculate_risk_aware_fitness(
            profit=0.55,
            drawdown=0.45,
            sharpe=1.2,
            win_rate=0.58,
            leverage=9.0,
            risk_per_trade=0.08,
            max_loss_streak=8,
        )

        self.assertLess(risky, conservative)

    def test_fitness_breakdown_contains_expected_components(self) -> None:
        breakdown = calculate_risk_aware_fitness_breakdown(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=5.0,
            risk_per_trade=0.04,
            max_loss_streak=3,
        )

        self.assertEqual(
            set(breakdown),
            {
                "profit_component",
                "sharpe_component",
                "win_rate_component",
                "drawdown_penalty",
                "leverage_penalty",
                "risk_per_trade_penalty",
                "loss_streak_penalty",
                "stability_component",
                "overfit_penalty",
                "train_validation_gap",
                "validation_test_gap",
                "final_fitness",
            },
        )

    def test_fitness_breakdown_is_json_serializable(self) -> None:
        breakdown = calculate_risk_aware_fitness_breakdown(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=5.0,
            risk_per_trade=0.04,
            max_loss_streak=3,
        )

        json.dumps(breakdown, sort_keys=True)

    def test_default_config_is_stable(self) -> None:
        config = RiskAwareFitnessConfig()

        self.assertEqual(config.max_preferred_leverage, 3.0)
        self.assertEqual(config.max_preferred_risk_per_trade, 0.02)

    def test_custom_config_changes_fitness(self) -> None:
        default_score = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=8.0,
            risk_per_trade=0.04,
            max_loss_streak=3,
        )
        strict_score = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.08,
            sharpe=1.0,
            win_rate=0.55,
            leverage=8.0,
            risk_per_trade=0.04,
            max_loss_streak=3,
            config=RiskAwareFitnessConfig(leverage_penalty_weight=1.0),
        )

        self.assertLess(strict_score, default_score)

    def test_fitness_penalizes_train_validation_gap(self) -> None:
        stable = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.05,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
            stability_score=0.9,
            train_validation_gap=0.01,
            validation_test_gap=0.01,
        )
        overfit = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.05,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
            stability_score=0.9,
            train_validation_gap=0.25,
            validation_test_gap=0.01,
        )

        self.assertLess(overfit, stable)

    def test_fitness_rewards_stable_walk_forward_metrics(self) -> None:
        stable = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.05,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
            stability_score=0.95,
            train_validation_gap=0.01,
            validation_test_gap=0.01,
        )
        unstable = calculate_risk_aware_fitness(
            profit=0.2,
            drawdown=0.05,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
            stability_score=0.35,
            train_validation_gap=0.08,
            validation_test_gap=0.08,
        )

        self.assertGreater(stable, unstable)

    def test_overfit_penalty_appears_in_fitness_components(self) -> None:
        breakdown = calculate_risk_aware_fitness_breakdown(
            profit=0.2,
            drawdown=0.05,
            sharpe=1.0,
            win_rate=0.55,
            leverage=2.0,
            risk_per_trade=0.01,
            stability_score=0.5,
            train_validation_gap=0.1,
            validation_test_gap=0.2,
        )

        self.assertIn("stability_component", breakdown)
        self.assertIn("overfit_penalty", breakdown)
        self.assertIn("train_validation_gap", breakdown)
        self.assertIn("validation_test_gap", breakdown)
        self.assertGreater(breakdown["overfit_penalty"], 0.0)


if __name__ == "__main__":
    unittest.main()
