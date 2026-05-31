"""Standalone Bollinger resonance scoring functions."""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np
import pandas as pd


DEFAULT_SCORE_GENES = {
    "w_4h": 0.30,
    "w_1h": 0.20,
    "w_15m": 0.20,
    "w_btc": 0.10,
    "w_volatility": 0.10,
    "w_momentum": 0.10,
    "mode": "hybrid",
}


def _merged_genes(genes: Mapping[str, Any] | None) -> dict:
    merged = dict(DEFAULT_SCORE_GENES)
    if genes:
        merged.update(genes)
    return merged


def _value(row: pd.Series, key: str, default: float = 0.0) -> float:
    value = row.get(key, default)
    if value is None:
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(numeric) or math.isinf(numeric):
        return default
    return numeric


def _safe_bool(value: bool) -> float:
    return 1.0 if value else 0.0


def _unit(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return float(np.clip(value, 0.0, 1.0))


def clip_score(value: float) -> float:
    """Clip a score to the 0-100 range with NaN/inf safety."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(numeric) or math.isinf(numeric):
        return 0.0
    return float(np.clip(numeric, 0.0, 100.0))


def _select_mode_trigger(
    mean_reversion_score: float,
    breakout_score: float,
    genes: Mapping[str, Any],
) -> float:
    mode = str(genes.get("mode", "hybrid"))
    if mode == "mean_reversion":
        return mean_reversion_score
    if mode == "breakout":
        return breakout_score
    return (mean_reversion_score + breakout_score) / 2.0


def _trend_long_4h(row: pd.Series) -> float:
    return (
        0.45 * _safe_bool(_value(row, "close") > _value(row, "bb_mid_4h"))
        + 0.25 * _safe_bool(_value(row, "bb_mid_slope_4h") > 0)
        + 0.30 * _unit((_value(row, "rsi_4h", 50.0) - 45.0) / 30.0)
    )


def _trend_short_4h(row: pd.Series) -> float:
    return (
        0.45 * _safe_bool(_value(row, "close") < _value(row, "bb_mid_4h"))
        + 0.25 * _safe_bool(_value(row, "bb_mid_slope_4h") < 0)
        + 0.30 * _unit((55.0 - _value(row, "rsi_4h", 50.0)) / 30.0)
    )


def _structure_long_1h(row: pd.Series) -> float:
    return (
        0.45 * _safe_bool(_value(row, "close") > _value(row, "bb_mid_1h"))
        + 0.25 * _safe_bool(_value(row, "bb_mid_slope_1h") >= 0)
        + 0.30 * _unit((_value(row, "rsi_1h", 50.0) - 45.0) / 30.0)
    )


def _structure_short_1h(row: pd.Series) -> float:
    return (
        0.45 * _safe_bool(_value(row, "close") < _value(row, "bb_mid_1h"))
        + 0.25 * _safe_bool(_value(row, "bb_mid_slope_1h") <= 0)
        + 0.30 * _unit((55.0 - _value(row, "rsi_1h", 50.0)) / 30.0)
    )


def _trigger_long_15m(row: pd.Series, genes: Mapping[str, Any]) -> float:
    mean_reversion = (
        0.50 * _safe_bool(_value(row, "bb_percent_b_15m", 0.5) <= 0.35)
        + 0.25 * _safe_bool(_value(row, "close") >= _value(row, "previous_close"))
        + 0.25 * _safe_bool(_value(row, "close") >= _value(row, "bb_mid_15m"))
    )
    breakout = (
        0.50 * _safe_bool(_value(row, "close") > _value(row, "bb_upper_15m"))
        + 0.25 * _safe_bool(_value(row, "bb_mid_slope_15m") > 0)
        + 0.25 * _safe_bool(_value(row, "volume") >= _value(row, "volume_mean_15m"))
    )
    return _select_mode_trigger(mean_reversion, breakout, genes)


def _trigger_short_15m(row: pd.Series, genes: Mapping[str, Any]) -> float:
    mean_reversion = (
        0.50 * _safe_bool(_value(row, "bb_percent_b_15m", 0.5) >= 0.65)
        + 0.25 * _safe_bool(_value(row, "close") <= _value(row, "previous_close"))
        + 0.25 * _safe_bool(_value(row, "close") <= _value(row, "bb_mid_15m"))
    )
    breakout = (
        0.50 * _safe_bool(_value(row, "close") < _value(row, "bb_lower_15m"))
        + 0.25 * _safe_bool(_value(row, "bb_mid_slope_15m") < 0)
        + 0.25 * _safe_bool(_value(row, "volume") >= _value(row, "volume_mean_15m"))
    )
    return _select_mode_trigger(mean_reversion, breakout, genes)


def _btc_long_filter(row: pd.Series) -> float:
    return (
        0.40 * _safe_bool(_value(row, "btc_bb_mid_slope_4h") >= 0)
        + 0.30 * _safe_bool(_value(row, "btc_bb_mid_slope_1h") >= 0)
        + 0.30 * _unit((_value(row, "btc_rsi_1h", 50.0) - 42.0) / 28.0)
    )


def _btc_short_filter(row: pd.Series) -> float:
    return (
        0.40 * _safe_bool(_value(row, "btc_bb_mid_slope_4h") <= 0)
        + 0.30 * _safe_bool(_value(row, "btc_bb_mid_slope_1h") <= 0)
        + 0.30 * _unit((58.0 - _value(row, "btc_rsi_1h", 50.0)) / 28.0)
    )


def _momentum_long(row: pd.Series) -> float:
    return _unit(
        ((_value(row, "rsi_15m", 50.0) - 45.0) / 30.0
         + (_value(row, "rsi_1h", 50.0) - 45.0) / 30.0)
        / 2.0
    )


def _momentum_short(row: pd.Series) -> float:
    return _unit(
        ((55.0 - _value(row, "rsi_15m", 50.0)) / 30.0
         + (55.0 - _value(row, "rsi_1h", 50.0)) / 30.0)
        / 2.0
    )


def _weight_total(genes: Mapping[str, Any]) -> float:
    total = sum(
        max(0.0, float(genes.get(key, 0.0)))
        for key in ("w_4h", "w_1h", "w_15m", "w_btc", "w_volatility", "w_momentum")
    )
    return total if total > 0 else 1.0


def calculate_volatility_score(row: pd.Series, genes: dict) -> float:
    """Score whether current Bollinger width is tradable rather than extreme."""

    width = _value(row, "bb_width_15m", 0.0)
    raw = 1.0 - abs(width - 0.08) / 0.08
    return clip_score(_unit(raw) * 100.0)


def calculate_market_regime_score(row: pd.Series, genes: dict) -> float:
    """Score broad long-biased market regime using 4h, 1h, and BTC context."""

    regime = (
        0.40 * _safe_bool(_value(row, "close") > _value(row, "bb_mid_4h"))
        + 0.20 * _safe_bool(_value(row, "bb_mid_slope_4h") > 0)
        + 0.20 * _safe_bool(_value(row, "close") > _value(row, "bb_mid_1h"))
        + 0.20 * _safe_bool(_value(row, "btc_bb_mid_slope_4h") > 0)
    )
    return clip_score(regime * 100.0)


def calculate_long_resonance_score(row: pd.Series, genes: dict) -> float:
    """Calculate a long-side Bollinger resonance score from one indicator row."""

    config = _merged_genes(genes)
    score = (
        float(config["w_4h"]) * _trend_long_4h(row)
        + float(config["w_1h"]) * _structure_long_1h(row)
        + float(config["w_15m"]) * _trigger_long_15m(row, config)
        + float(config["w_btc"]) * _btc_long_filter(row)
        + float(config["w_volatility"]) * (calculate_volatility_score(row, config) / 100.0)
        + float(config["w_momentum"]) * _momentum_long(row)
    ) / _weight_total(config)
    return clip_score(score * 100.0)


def calculate_short_resonance_score(row: pd.Series, genes: dict) -> float:
    """Calculate a short-side Bollinger resonance score from one indicator row."""

    config = _merged_genes(genes)
    score = (
        float(config["w_4h"]) * _trend_short_4h(row)
        + float(config["w_1h"]) * _structure_short_1h(row)
        + float(config["w_15m"]) * _trigger_short_15m(row, config)
        + float(config["w_btc"]) * _btc_short_filter(row)
        + float(config["w_volatility"]) * (calculate_volatility_score(row, config) / 100.0)
        + float(config["w_momentum"]) * _momentum_short(row)
    ) / _weight_total(config)
    return clip_score(score * 100.0)
