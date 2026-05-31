"""Tests for the Bollinger Resonance strategy template."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from bollinger_evolver.strategies.indicator_helpers import (
    DEFAULT_GENES,
    apply_entry_logic,
    compute_bollinger_features,
    compute_resonance_scores,
)

try:
    from user_data.strategies.BollingerResonanceStrategy import BollingerResonanceStrategy

    STRATEGY_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - environment dependent
    BollingerResonanceStrategy = None
    STRATEGY_IMPORT_ERROR = exc


def _make_ohlcv_dataframe(length: int = 500) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=length, freq="15min")
    base = np.linspace(100.0, 140.0, num=length)
    wave = np.sin(np.linspace(0.0, 20.0, num=length))
    close = base + wave
    return pd.DataFrame(
        {
            "date": index,
            "open": close - 0.3,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": np.linspace(1000.0, 1800.0, num=length),
        }
    )


def _score_ready_dataframe(rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "resonance_long_score": [20.0, 78.0, 40.0][:rows],
            "resonance_short_score": [20.0, 22.0, 82.0][:rows],
        }
    )


@unittest.skipIf(STRATEGY_IMPORT_ERROR is not None, f"freqtrade import unavailable: {STRATEGY_IMPORT_ERROR}")
class TestStrategyImportAndStructure(unittest.TestCase):
    def test_strategy_class_imports(self) -> None:
        self.assertIsNotNone(BollingerResonanceStrategy)

    def test_default_genes_contains_core_fields(self) -> None:
        required_fields = {
            "bb_period_15m",
            "bb_std_15m",
            "bb_period_1h",
            "bb_std_1h",
            "bb_period_4h",
            "bb_std_4h",
            "w_4h",
            "w_1h",
            "w_15m",
            "w_btc",
            "w_volatility",
            "w_momentum",
            "min_long_score",
            "min_short_score",
            "mode",
            "risk_low_score",
            "risk_mid_score",
            "risk_high_score",
            "max_position_risk",
            "max_dca_orders",
            "dca_score_min",
            "atr_stop_mult",
            "dca_drawdown_trigger_1",
            "dca_drawdown_trigger_2",
            "dca_size_mult_1",
            "dca_size_mult_2",
            "max_strategy_leverage",
        }
        self.assertTrue(required_fields.issubset(BollingerResonanceStrategy.DEFAULT_GENES.keys()))

    def test_strategy_static_properties(self) -> None:
        self.assertEqual(BollingerResonanceStrategy.timeframe, "15m")
        self.assertTrue(BollingerResonanceStrategy.can_short)

    def test_informative_pairs_include_1h_4h_and_btc_filter(self) -> None:
        strategy = BollingerResonanceStrategy({})
        strategy.dp = SimpleNamespace(current_whitelist=lambda: ["ETH/USDT", "BTC/USDT"])
        pairs = strategy.informative_pairs()

        self.assertIn(("ETH/USDT", "1h"), pairs)
        self.assertIn(("ETH/USDT", "4h"), pairs)
        self.assertIn(("BTC/USDT", "1h"), pairs)
        self.assertIn(("BTC/USDT", "4h"), pairs)


class TestIndicatorHelpers(unittest.TestCase):
    def test_indicator_helper_generates_required_columns(self) -> None:
        dataframe = _make_ohlcv_dataframe()
        result = compute_bollinger_features(
            dataframe,
            period=20,
            std_dev=2.0,
            suffix="15m",
        )

        expected_columns = {
            "bb_mid_15m",
            "bb_upper_15m",
            "bb_lower_15m",
            "bb_width_15m",
            "bb_percent_b_15m",
            "bb_mid_slope_15m",
            "atr_15m",
            "rsi_15m",
            "volume_mean_15m",
        }
        self.assertTrue(expected_columns.issubset(result.columns))

    def test_score_is_clipped_to_zero_to_hundred(self) -> None:
        dataframe = _make_ohlcv_dataframe()
        dataframe = compute_bollinger_features(dataframe, period=20, std_dev=2.0, suffix="15m")
        dataframe["bb_mid_1h"] = 1e-9
        dataframe["bb_upper_1h"] = 1e9
        dataframe["bb_lower_1h"] = -1e9
        dataframe["bb_width_1h"] = 999.0
        dataframe["bb_percent_b_1h"] = 999.0
        dataframe["bb_mid_slope_1h"] = 999.0
        dataframe["atr_1h"] = 999.0
        dataframe["rsi_1h"] = 999.0
        dataframe["volume_mean_1h"] = 999.0
        dataframe["bb_mid_4h"] = 1e-9
        dataframe["bb_upper_4h"] = 1e9
        dataframe["bb_lower_4h"] = -1e9
        dataframe["bb_width_4h"] = 999.0
        dataframe["bb_percent_b_4h"] = 999.0
        dataframe["bb_mid_slope_4h"] = 999.0
        dataframe["atr_4h"] = 999.0
        dataframe["rsi_4h"] = 999.0
        dataframe["volume_mean_4h"] = 999.0
        dataframe["btc_bb_mid_1h"] = 999.0
        dataframe["btc_bb_mid_slope_1h"] = 999.0
        dataframe["btc_rsi_1h"] = 999.0
        dataframe["btc_bb_mid_4h"] = 999.0
        dataframe["btc_bb_mid_slope_4h"] = 999.0
        dataframe["btc_rsi_4h"] = 999.0

        scored = compute_resonance_scores(dataframe, DEFAULT_GENES)

        self.assertTrue(scored["resonance_long_score"].between(0, 100).all())
        self.assertTrue(scored["resonance_short_score"].between(0, 100).all())
        self.assertTrue(scored["market_regime_score"].between(0, 100).all())
        self.assertTrue(scored["volatility_score"].between(0, 100).all())

    def test_nan_input_does_not_crash(self) -> None:
        dataframe = _make_ohlcv_dataframe()
        dataframe.loc[:, ["open", "high", "low", "close", "volume"]] = np.nan
        result = compute_bollinger_features(dataframe, period=20, std_dev=2.0, suffix="15m")

        for column in [
            "bb_width_15m",
            "bb_percent_b_15m",
            "bb_mid_slope_15m",
            "atr_15m",
            "rsi_15m",
            "volume_mean_15m",
        ]:
            self.assertIn(column, result.columns)


class TestEntryLogic(unittest.TestCase):
    def test_low_scores_do_not_open_positions(self) -> None:
        dataframe = pd.DataFrame(
            {
                "resonance_long_score": [30.0],
                "resonance_short_score": [20.0],
            }
        )
        result = apply_entry_logic(dataframe, DEFAULT_GENES)
        self.assertEqual(int(result.loc[0, "enter_long"]), 0)
        self.assertEqual(int(result.loc[0, "enter_short"]), 0)

    def test_high_long_score_opens_only_long(self) -> None:
        dataframe = pd.DataFrame(
            {
                "resonance_long_score": [78.0],
                "resonance_short_score": [30.0],
            }
        )
        result = apply_entry_logic(dataframe, DEFAULT_GENES)
        self.assertEqual(int(result.loc[0, "enter_long"]), 1)
        self.assertEqual(int(result.loc[0, "enter_short"]), 0)

    def test_high_short_score_opens_only_short(self) -> None:
        dataframe = pd.DataFrame(
            {
                "resonance_long_score": [25.0],
                "resonance_short_score": [85.0],
            }
        )
        result = apply_entry_logic(dataframe, DEFAULT_GENES)
        self.assertEqual(int(result.loc[0, "enter_long"]), 0)
        self.assertEqual(int(result.loc[0, "enter_short"]), 1)

    def test_equal_scores_open_neither_side(self) -> None:
        dataframe = pd.DataFrame(
            {
                "resonance_long_score": [80.0],
                "resonance_short_score": [80.0],
            }
        )
        result = apply_entry_logic(dataframe, DEFAULT_GENES)
        self.assertEqual(int(result.loc[0, "enter_long"]), 0)
        self.assertEqual(int(result.loc[0, "enter_short"]), 0)

    def test_enter_tag_contains_direction_mode_and_score(self) -> None:
        dataframe = pd.DataFrame(
            {
                "resonance_long_score": [78.0],
                "resonance_short_score": [20.0],
            }
        )
        result = apply_entry_logic(dataframe, DEFAULT_GENES)
        tag = result.loc[0, "enter_tag"]
        self.assertIn("long", tag)
        self.assertIn(DEFAULT_GENES["mode"], tag)
        self.assertIn("78", tag)
