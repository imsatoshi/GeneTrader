"""Tests for standalone Bollinger resonance scoring."""

from __future__ import annotations

import math
import unittest

import numpy as np
import pandas as pd

from bollinger_evolver.scoring.resonance import (
    calculate_long_resonance_score,
    calculate_market_regime_score,
    calculate_short_resonance_score,
    calculate_volatility_score,
    clip_score,
)
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


def _base_row(**overrides) -> pd.Series:
    values = {
        "close": 100.0,
        "previous_close": 99.0,
        "volume": 1200.0,
        "bb_mid_15m": 98.0,
        "bb_upper_15m": 105.0,
        "bb_lower_15m": 92.0,
        "bb_width_15m": 0.08,
        "bb_percent_b_15m": 0.45,
        "bb_mid_slope_15m": 0.2,
        "rsi_15m": 58.0,
        "volume_mean_15m": 1000.0,
        "bb_mid_1h": 97.0,
        "bb_mid_slope_1h": 0.15,
        "rsi_1h": 60.0,
        "bb_mid_4h": 95.0,
        "bb_mid_slope_4h": 0.25,
        "rsi_4h": 62.0,
        "btc_bb_mid_slope_1h": 0.1,
        "btc_rsi_1h": 58.0,
        "btc_bb_mid_slope_4h": 0.2,
        "btc_rsi_4h": 60.0,
    }
    values.update(overrides)
    return pd.Series(values)


class TestClipScore(unittest.TestCase):
    def test_clips_range_and_handles_nan(self) -> None:
        self.assertEqual(clip_score(-10), 0.0)
        self.assertEqual(clip_score(150), 100.0)
        self.assertEqual(clip_score(math.nan), 0.0)
        self.assertEqual(clip_score("bad"), 0.0)


class TestResonanceScoring(unittest.TestCase):
    def test_long_score_prefers_bullish_row(self) -> None:
        bullish = _base_row()
        bearish = _base_row(
            close=90.0,
            previous_close=91.0,
            bb_mid_1h=95.0,
            bb_mid_4h=96.0,
            bb_mid_slope_1h=-0.1,
            bb_mid_slope_4h=-0.2,
            rsi_15m=35.0,
            rsi_1h=38.0,
            rsi_4h=36.0,
            btc_bb_mid_slope_1h=-0.1,
            btc_bb_mid_slope_4h=-0.2,
            btc_rsi_1h=35.0,
        )

        self.assertGreater(
            calculate_long_resonance_score(bullish, DEFAULT_GENES),
            calculate_long_resonance_score(bearish, DEFAULT_GENES),
        )

    def test_short_score_prefers_bearish_row(self) -> None:
        bullish = _base_row()
        bearish = _base_row(
            close=90.0,
            previous_close=91.0,
            bb_mid_15m=94.0,
            bb_lower_15m=91.0,
            bb_percent_b_15m=0.75,
            bb_mid_1h=95.0,
            bb_mid_4h=96.0,
            bb_mid_slope_15m=-0.2,
            bb_mid_slope_1h=-0.1,
            bb_mid_slope_4h=-0.2,
            rsi_15m=35.0,
            rsi_1h=38.0,
            rsi_4h=36.0,
            btc_bb_mid_slope_1h=-0.1,
            btc_bb_mid_slope_4h=-0.2,
            btc_rsi_1h=35.0,
        )

        self.assertGreater(
            calculate_short_resonance_score(bearish, DEFAULT_GENES),
            calculate_short_resonance_score(bullish, DEFAULT_GENES),
        )

    def test_scores_are_clipped_and_nan_safe(self) -> None:
        row = _base_row(close=np.nan, bb_width_15m=np.nan, rsi_1h=np.nan)
        for scorer in (
            calculate_long_resonance_score,
            calculate_short_resonance_score,
            calculate_market_regime_score,
            calculate_volatility_score,
        ):
            score = scorer(row, DEFAULT_GENES)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 100.0)

    def test_market_regime_and_volatility_scores(self) -> None:
        row = _base_row()
        self.assertGreater(calculate_market_regime_score(row, DEFAULT_GENES), 0.0)
        self.assertEqual(calculate_volatility_score(row, DEFAULT_GENES), 100.0)
