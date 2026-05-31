"""Pure pandas helpers for the Bollinger Resonance strategy template."""

from __future__ import annotations

from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd

from bollinger_evolver.scoring.resonance import (
    calculate_long_resonance_score,
    calculate_market_regime_score,
    calculate_short_resonance_score,
    calculate_volatility_score,
)


DEFAULT_GENES: Dict[str, Any] = {
    "bb_period_15m": 20,
    "bb_std_15m": 2.0,
    "bb_period_1h": 20,
    "bb_std_1h": 2.0,
    "bb_period_4h": 20,
    "bb_std_4h": 2.2,
    "w_4h": 0.30,
    "w_1h": 0.20,
    "w_15m": 0.20,
    "w_btc": 0.10,
    "w_volatility": 0.10,
    "w_momentum": 0.10,
    "min_long_score": 60.0,
    "min_short_score": 60.0,
    "mode": "hybrid",
    "risk_low_score": 0.0025,
    "risk_mid_score": 0.005,
    "risk_high_score": 0.008,
    "max_position_risk": 0.01,
    "max_dca_orders": 2,
    "dca_score_min": 75.0,
    "atr_stop_mult": 2.0,
    "dca_drawdown_trigger_1": -0.03,
    "dca_drawdown_trigger_2": -0.06,
    "dca_size_mult_1": 0.5,
    "dca_size_mult_2": 0.75,
    "max_strategy_leverage": 3.0,
}


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace(0, np.nan)
    return numerator.divide(denominator)


def _rolling_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()
    rs = _safe_divide(avg_gain, avg_loss)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _rolling_atr(dataframe: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = dataframe["close"].shift(1)
    true_range = pd.concat(
        [
            dataframe["high"] - dataframe["low"],
            (dataframe["high"] - previous_close).abs(),
            (dataframe["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def compute_bollinger_features(
    dataframe: pd.DataFrame,
    *,
    period: int,
    std_dev: float,
    suffix: str,
    volume_window: int = 20,
    rsi_period: int = 14,
    atr_period: int = 14,
) -> pd.DataFrame:
    """Compute Bollinger, ATR, RSI, and volume features for one timeframe."""

    df = dataframe.copy()
    close = df["close"]

    rolling_mean = close.rolling(window=period, min_periods=period).mean()
    rolling_std = close.rolling(window=period, min_periods=period).std(ddof=0)
    bb_upper = rolling_mean + (rolling_std * std_dev)
    bb_lower = rolling_mean - (rolling_std * std_dev)
    bb_span = (bb_upper - bb_lower).replace(0, np.nan)

    df[f"bb_mid_{suffix}"] = rolling_mean
    df[f"bb_upper_{suffix}"] = bb_upper
    df[f"bb_lower_{suffix}"] = bb_lower
    df[f"bb_width_{suffix}"] = _safe_divide(bb_upper - bb_lower, rolling_mean).fillna(0.0)
    df[f"bb_percent_b_{suffix}"] = _safe_divide(close - bb_lower, bb_span).fillna(0.5)
    df[f"bb_mid_slope_{suffix}"] = rolling_mean.diff().fillna(0.0)
    df[f"atr_{suffix}"] = _rolling_atr(df, period=atr_period).fillna(0.0)
    df[f"rsi_{suffix}"] = _rolling_rsi(close, period=rsi_period).fillna(50.0)
    df[f"volume_mean_{suffix}"] = (
        df["volume"].rolling(window=volume_window, min_periods=1).mean().fillna(0.0)
    )
    return df


def merge_informative_features(
    base_dataframe: pd.DataFrame,
    informative_dataframe: pd.DataFrame,
    feature_columns: Iterable[str],
) -> pd.DataFrame:
    """Backward-merge informative features by date without future leakage."""

    base = base_dataframe.copy()
    feature_columns = list(feature_columns)

    if informative_dataframe.empty:
        for column in feature_columns:
            base[column] = np.nan
        return base

    informative = informative_dataframe[["date", *feature_columns]].copy()
    merged = pd.merge_asof(
        base.sort_values("date"),
        informative.sort_values("date"),
        on="date",
        direction="backward",
    )
    return merged.sort_index()


def compute_resonance_scores(
    dataframe: pd.DataFrame,
    genes: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Compute long/short resonance scores and supporting regime metrics."""

    df = dataframe.copy()
    score_genes = dict(DEFAULT_GENES)
    if genes:
        score_genes.update(genes)

    df["previous_close"] = df["close"].shift(1)
    df["market_regime_score"] = df.apply(
        lambda row: calculate_market_regime_score(row, score_genes),
        axis=1,
    )
    df["volatility_score"] = df.apply(
        lambda row: calculate_volatility_score(row, score_genes),
        axis=1,
    )
    df["resonance_long_score"] = df.apply(
        lambda row: calculate_long_resonance_score(row, score_genes),
        axis=1,
    )
    df["resonance_short_score"] = df.apply(
        lambda row: calculate_short_resonance_score(row, score_genes),
        axis=1,
    )
    df = df.drop(columns=["previous_close"])
    return df


def apply_entry_logic(
    dataframe: pd.DataFrame,
    genes: Dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Create entry signals and tags from resonance scores."""

    config = dict(DEFAULT_GENES)
    if genes:
        config.update(genes)

    df = dataframe.copy()
    df["enter_long"] = 0
    df["enter_short"] = 0
    df["enter_tag"] = ""

    long_score = df["resonance_long_score"].fillna(0.0)
    short_score = df["resonance_short_score"].fillna(0.0)
    long_condition = (long_score >= float(config["min_long_score"])) & (long_score > short_score)
    short_condition = (short_score >= float(config["min_short_score"])) & (short_score > long_score)

    mode_label = str(config["mode"])
    long_tags = "long_" + mode_label + "_score_" + long_score.round().astype(int).astype(str)
    short_tags = "short_" + mode_label + "_score_" + short_score.round().astype(int).astype(str)

    df.loc[long_condition, "enter_long"] = 1
    df.loc[short_condition, "enter_short"] = 1
    df.loc[long_condition, "enter_tag"] = long_tags[long_condition]
    df.loc[short_condition, "enter_tag"] = short_tags[short_condition]
    return df


def apply_exit_logic(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Create conservative score-faded exit signals."""

    df = dataframe.copy()
    df["exit_long"] = 0
    df["exit_short"] = 0
    df["exit_tag"] = ""

    long_exit = df["resonance_long_score"].fillna(0.0) < 45.0
    short_exit = df["resonance_short_score"].fillna(0.0) < 45.0

    df.loc[long_exit, "exit_long"] = 1
    df.loc[short_exit, "exit_short"] = 1
    df.loc[long_exit, "exit_tag"] = "long_score_faded"
    df.loc[short_exit, "exit_tag"] = "short_score_faded"
    return df
