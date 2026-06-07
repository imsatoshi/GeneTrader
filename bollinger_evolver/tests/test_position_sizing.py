"""Tests for Bollinger Resonance position sizing helpers."""

from __future__ import annotations

import math
import json
import unittest

from bollinger_evolver.position_sizing import calculate_position_size
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES
from bollinger_evolver.strategies.position_sizing import (
    calculate_dca_stake,
    calculate_leverage,
    calculate_stake_amount,
    calculate_stoploss_from_atr,
    clip_float,
    score_to_risk_fraction,
    should_reduce_position,
)


class TestClipFloat(unittest.TestCase):
    def test_clip_float_bounds_numeric_values(self) -> None:
        self.assertEqual(clip_float(5.0, 0.0, 3.0), 3.0)
        self.assertEqual(clip_float(-1.0, 0.0, 3.0), 0.0)

    def test_clip_float_handles_nan_safely(self) -> None:
        self.assertEqual(clip_float(math.nan, 1.0, 3.0), 1.0)


class TestRiskMapping(unittest.TestCase):
    def test_score_below_sixty_has_zero_risk(self) -> None:
        self.assertEqual(score_to_risk_fraction(59.9, DEFAULT_GENES), 0.0)

    def test_score_buckets_map_to_configured_risk_fractions(self) -> None:
        self.assertEqual(score_to_risk_fraction(65.0, DEFAULT_GENES), 0.0025)
        self.assertEqual(score_to_risk_fraction(75.0, DEFAULT_GENES), 0.005)
        self.assertEqual(score_to_risk_fraction(85.0, DEFAULT_GENES), 0.008)
        self.assertEqual(score_to_risk_fraction(95.0, DEFAULT_GENES), 0.01)

    def test_risk_never_exceeds_max_position_risk(self) -> None:
        genes = dict(DEFAULT_GENES)
        genes["risk_high_score"] = 0.05
        genes["max_position_risk"] = 0.01

        self.assertEqual(score_to_risk_fraction(85.0, genes), 0.01)


class TestStakeAmount(unittest.TestCase):
    def test_low_score_returns_zero_stake(self) -> None:
        stake = calculate_stake_amount(1000.0, 40.0, 0.02, DEFAULT_GENES)
        self.assertEqual(stake, 0.0)

    def test_stake_uses_risk_budget_divided_by_stop_distance(self) -> None:
        stake = calculate_stake_amount(1000.0, 75.0, 0.05, DEFAULT_GENES)
        self.assertEqual(stake, 100.0)

    def test_stake_is_capped_by_max_stake_and_available_stake(self) -> None:
        stake = calculate_stake_amount(
            1000.0,
            95.0,
            0.001,
            DEFAULT_GENES,
            max_stake=250.0,
        )
        self.assertEqual(stake, 250.0)

    def test_stake_below_unreachable_minimum_returns_zero(self) -> None:
        stake = calculate_stake_amount(
            100.0,
            65.0,
            0.5,
            DEFAULT_GENES,
            min_stake=5.0,
            max_stake=2.0,
        )
        self.assertEqual(stake, 0.0)


class TestDcaStake(unittest.TestCase):
    def test_first_dca_trigger_uses_first_multiplier(self) -> None:
        stake = calculate_dca_stake(
            current_stake=100.0,
            score=80.0,
            current_profit=-0.04,
            successful_entries=1,
            has_open_orders=False,
            four_hour_regime_ok=True,
            genes=DEFAULT_GENES,
        )
        self.assertEqual(stake, 50.0)

    def test_deeper_dca_trigger_uses_second_multiplier(self) -> None:
        stake = calculate_dca_stake(
            current_stake=100.0,
            score=80.0,
            current_profit=-0.08,
            successful_entries=1,
            has_open_orders=False,
            four_hour_regime_ok=True,
            genes=DEFAULT_GENES,
        )
        self.assertEqual(stake, 75.0)

    def test_dca_rejects_open_orders_low_score_bad_regime_and_order_cap(self) -> None:
        base = {
            "current_stake": 100.0,
            "score": 80.0,
            "current_profit": -0.04,
            "successful_entries": 1,
            "has_open_orders": False,
            "four_hour_regime_ok": True,
            "genes": DEFAULT_GENES,
        }

        self.assertIsNone(calculate_dca_stake(**{**base, "has_open_orders": True}))
        self.assertIsNone(calculate_dca_stake(**{**base, "score": 70.0}))
        self.assertIsNone(calculate_dca_stake(**{**base, "four_hour_regime_ok": False}))
        self.assertIsNone(calculate_dca_stake(**{**base, "successful_entries": 3}))


class TestReducePosition(unittest.TestCase):
    def test_reduce_signal_exits_when_score_collapses(self) -> None:
        self.assertEqual(should_reduce_position(20.0), "exit")

    def test_reduce_signal_halves_once_when_score_fades(self) -> None:
        self.assertEqual(should_reduce_position(45.0), "reduce_half")
        self.assertIsNone(should_reduce_position(45.0, already_reduced=True))

    def test_reduce_signal_holds_when_score_is_healthy(self) -> None:
        self.assertIsNone(should_reduce_position(55.0))


class TestStoplossAndLeverage(unittest.TestCase):
    def test_atr_stoploss_is_negative_and_capped_by_max_risk(self) -> None:
        stoploss = calculate_stoploss_from_atr(
            atr=5.0,
            current_rate=100.0,
            atr_stop_mult=2.0,
            max_position_risk=0.03,
        )
        self.assertEqual(stoploss, -0.03)

    def test_invalid_atr_stoploss_falls_back_to_max_risk(self) -> None:
        stoploss = calculate_stoploss_from_atr(
            atr=0.0,
            current_rate=100.0,
            atr_stop_mult=2.0,
            max_position_risk=0.01,
        )
        self.assertEqual(stoploss, -0.01)

    def test_spot_leverage_is_always_one(self) -> None:
        self.assertEqual(calculate_leverage(95.0, 10.0, "spot", DEFAULT_GENES), 1.0)

    def test_futures_leverage_uses_score_buckets_and_caps(self) -> None:
        self.assertEqual(calculate_leverage(65.0, 10.0, "futures", DEFAULT_GENES), 1.0)
        self.assertEqual(calculate_leverage(75.0, 10.0, "futures", DEFAULT_GENES), 2.0)
        self.assertEqual(calculate_leverage(90.0, 10.0, "futures", DEFAULT_GENES), 3.0)
        self.assertEqual(calculate_leverage(90.0, 2.0, "futures", DEFAULT_GENES), 2.0)


class TestMockPositionSizingEngine(unittest.TestCase):
    def test_calculate_position_size_uses_risk_budget_and_leverage(self) -> None:
        result = calculate_position_size(
            equity=1000.0,
            risk_per_trade=0.01,
            stoploss_pct=0.01,
            leverage=3.0,
        )

        self.assertEqual(result["position_value"], 1000.0)
        self.assertAlmostEqual(result["margin_required"], 333.3333333333)
        self.assertEqual(result["risk_amount"], 10.0)
        self.assertEqual(result["leverage"], 3.0)

    def test_calculate_position_size_rejects_zero_stoploss(self) -> None:
        with self.assertRaisesRegex(ValueError, "stoploss_pct"):
            calculate_position_size(equity=1000.0, risk_per_trade=0.01, stoploss_pct=0.0, leverage=1.0)

    def test_calculate_position_size_rejects_non_positive_leverage(self) -> None:
        with self.assertRaisesRegex(ValueError, "leverage"):
            calculate_position_size(equity=1000.0, risk_per_trade=0.01, stoploss_pct=0.02, leverage=0.0)

    def test_calculate_position_size_rejects_risk_outside_zero_to_one(self) -> None:
        with self.assertRaisesRegex(ValueError, "risk_per_trade"):
            calculate_position_size(equity=1000.0, risk_per_trade=1.2, stoploss_pct=0.02, leverage=1.0)

    def test_calculate_position_size_applies_max_position_value(self) -> None:
        result = calculate_position_size(
            equity=1000.0,
            risk_per_trade=0.02,
            stoploss_pct=0.01,
            leverage=2.0,
            max_position_value=500.0,
        )

        self.assertEqual(result["position_value"], 500.0)
        self.assertEqual(result["risk_amount"], 5.0)
        self.assertIn("max_position_value_applied", result["warnings"])

    def test_calculate_position_size_output_is_json_serializable(self) -> None:
        result = calculate_position_size(equity=1000.0, risk_per_trade=0.01, stoploss_pct=0.02, leverage=2.0)

        encoded = json.dumps(result, sort_keys=True)

        self.assertIn("position-sizing/v1", encoded)


if __name__ == "__main__":
    unittest.main()
