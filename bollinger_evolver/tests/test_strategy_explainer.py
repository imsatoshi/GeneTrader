"""Tests for custom strategy explainability reports."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.fixtures.custom_strategy_fixtures import get_custom_strategy_fixture
from bollinger_evolver.risk_governor import apply_risk_governor
from bollinger_evolver.strategy_explainer import build_strategy_explainability_report
from bollinger_evolver.trading_system_adapter import build_position_sizing_preview, build_trading_system_config


class TestStrategyExplainer(unittest.TestCase):
    def test_strategy_explainer_warns_for_high_leverage(self) -> None:
        fixture = get_custom_strategy_fixture("high_leverage_high_drawdown")
        trading_config = build_trading_system_config(fixture["strategy_config"])
        preview = build_position_sizing_preview(trading_config, equity=10_000.0)
        advice = apply_risk_governor(fixture["strategy_config"], fixture["metrics"])

        report = build_strategy_explainability_report(
            fixture["strategy_config"],
            metrics=fixture["metrics"],
            risk_governor=advice,
            position_sizing_preview=preview,
        )

        self.assertIn("high_leverage_strategy", report["warnings"])
        self.assertIn("drawdown_requires_risk_review", report["warnings"])
        self.assertIn("risk_governor:reduced_risk_after_drawdown", report["warnings"])

    def test_strategy_explainer_describes_low_drawdown_stability(self) -> None:
        fixture = get_custom_strategy_fixture("low_leverage_low_drawdown")

        report = build_strategy_explainability_report(
            fixture["strategy_config"],
            metrics={**fixture["metrics"], "stability_score": 0.86},
        )

        self.assertIn("Low-drawdown", report["summary"])
        self.assertEqual(report["warnings"], [])

    def test_strategy_explainer_includes_fitness_explanation(self) -> None:
        fixture = get_custom_strategy_fixture("safe_default")

        report = build_strategy_explainability_report(
            fixture["strategy_config"],
            fitness_components={
                "final_fitness": 0.812,
                "drawdown_penalty": 0.05,
                "overfit_penalty": 0.02,
                "stability_component": 0.14,
            },
        )

        self.assertIn("final_fitness=0.812", report["fitness_explanation"])
        self.assertIn("drawdown_penalty_applied", report["fitness_explanation"])
        self.assertIn("overfit_penalty_applied", report["fitness_explanation"])

    def test_strategy_explainer_output_is_json_serializable(self) -> None:
        fixture = get_custom_strategy_fixture("safe_default")

        report = build_strategy_explainability_report(fixture["strategy_config"])

        encoded = json.dumps(report, sort_keys=True)
        self.assertIn("strategy-explainability/v1", encoded)


if __name__ == "__main__":
    unittest.main()
