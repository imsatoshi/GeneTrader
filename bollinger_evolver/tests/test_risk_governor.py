"""Tests for advisory leverage and position-sizing governor."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.fitness import MockBacktestMetrics, risk_governor_metrics_from_mock_metrics
from bollinger_evolver.custom_strategy_schema import CustomStrategyGenome, custom_strategy_config_from_genome
from bollinger_evolver.risk_governor import RiskGovernorConfig, apply_risk_governor
from bollinger_evolver.strategy_factory import StrategyConfig, risk_governor_advice_for_strategy_config


def _strategy(**overrides) -> StrategyConfig:
    data = {
        "genome_id": "risk-test",
        "bollinger_window": 20,
        "bollinger_stddev": 2.0,
        "stoploss": 0.03,
        "takeprofit": 0.08,
        "leverage": 1.0,
        "risk_per_trade": 0.01,
        "parameters": {"bb_window": 20, "bb_stddev": 2.0},
    }
    data.update(overrides)
    return StrategyConfig(**data)


class TestRiskGovernor(unittest.TestCase):
    def test_risk_governor_clamps_excess_leverage(self) -> None:
        result = apply_risk_governor(_strategy(leverage=8.0), {"drawdown": 0.01})

        self.assertEqual(result["adjusted_leverage"], 3.0)
        self.assertIn("clamped_leverage_to_max", result["actions"])

    def test_risk_governor_clamps_excess_risk_per_trade(self) -> None:
        result = apply_risk_governor(_strategy(risk_per_trade=0.08), {"drawdown": 0.01})

        self.assertEqual(result["adjusted_risk_per_trade"], 0.02)
        self.assertIn("clamped_risk_per_trade_to_max", result["actions"])

    def test_risk_governor_reduces_risk_after_drawdown(self) -> None:
        result = apply_risk_governor(_strategy(risk_per_trade=0.018), {"drawdown": 0.16})

        self.assertLess(result["adjusted_risk_per_trade"], 0.018)
        self.assertIn("reduced_risk_after_drawdown", result["actions"])

    def test_risk_governor_reduces_risk_after_loss_streak(self) -> None:
        result = apply_risk_governor(_strategy(risk_per_trade=0.018), {"max_consecutive_losses": 7})

        self.assertLess(result["adjusted_risk_per_trade"], 0.018)
        self.assertIn("reduced_risk_after_loss_streak", result["actions"])

    def test_risk_governor_output_is_json_serializable(self) -> None:
        strategy = _strategy(leverage=5.0, risk_per_trade=0.03)
        metrics = MockBacktestMetrics(
            profit=0.1,
            drawdown=0.11,
            sharpe=1.2,
            win_rate=0.55,
            max_consecutive_losses=5,
        )

        result = risk_governor_advice_for_strategy_config(
            strategy,
            risk_governor_metrics_from_mock_metrics(metrics),
            config=RiskGovernorConfig(max_leverage=2.0),
        )

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("risk-governor/v1", encoded)
        self.assertEqual(strategy.leverage, 5.0)

    def test_risk_governor_accepts_custom_strategy_config_mapping(self) -> None:
        custom_config = custom_strategy_config_from_genome(
            CustomStrategyGenome(genome_id="custom-risk", leverage=6.0, risk_per_trade=0.04)
        )

        result = apply_risk_governor(
            custom_config,
            {"drawdown": 0.12, "max_consecutive_losses": 6},
            config=RiskGovernorConfig(max_leverage=3.0, max_risk_per_trade=0.02),
        )

        self.assertEqual(result["adjusted_leverage"], 3.0)
        self.assertLessEqual(result["adjusted_risk_per_trade"], 0.01)
        self.assertEqual(custom_config["leverage"], 6.0)


if __name__ == "__main__":
    unittest.main()
