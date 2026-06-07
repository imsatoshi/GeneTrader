"""Tests for mock loss-streak risk control."""

from __future__ import annotations

import copy
import json
import unittest

from bollinger_evolver.loss_streak_control import LossStreakControlConfig, apply_loss_streak_control


def _config():
    return {
        "strategy_id": "loss-streak-test",
        "risk_per_trade": 0.02,
        "leverage": 3.0,
        "execution_controls": {"cooldown_candles": 4},
    }


class TestLossStreakControl(unittest.TestCase):
    def test_loss_streak_below_threshold_does_not_trigger(self) -> None:
        result = apply_loss_streak_control(_config(), 2)

        self.assertFalse(result["triggered"])
        self.assertEqual(result["actions"], [])
        self.assertEqual(result["adjusted"]["risk_per_trade"], 0.02)

    def test_loss_streak_at_threshold_reduces_risk(self) -> None:
        result = apply_loss_streak_control(
            _config(),
            4,
            config=LossStreakControlConfig(trigger_loss_streak=4, risk_multiplier=0.5, leverage_multiplier=0.5),
        )

        self.assertTrue(result["triggered"])
        self.assertEqual(result["adjusted"]["risk_per_trade"], 0.01)
        self.assertEqual(result["adjusted"]["leverage"], 1.5)
        self.assertIn("risk_reduced", [item["code"] for item in result["actions"]])

    def test_loss_streak_applies_cooldown(self) -> None:
        result = apply_loss_streak_control(
            _config(),
            5,
            config=LossStreakControlConfig(trigger_loss_streak=4, cooldown_increment=10),
        )

        self.assertEqual(result["adjusted"]["execution_controls"]["cooldown_candles"], 14)
        self.assertIn("cooldown_applied", [item["code"] for item in result["actions"]])

    def test_loss_streak_does_not_mutate_original_config(self) -> None:
        original = _config()
        snapshot = copy.deepcopy(original)

        result = apply_loss_streak_control(original, 5)

        self.assertNotEqual(result["adjusted"], original)
        self.assertEqual(original, snapshot)

    def test_loss_streak_output_is_json_serializable(self) -> None:
        result = apply_loss_streak_control(_config(), 5)

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("loss-streak-control/v1", encoded)


if __name__ == "__main__":
    unittest.main()
