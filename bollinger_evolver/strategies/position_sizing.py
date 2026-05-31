"""Position sizing helpers for the Bollinger Resonance strategy."""

from __future__ import annotations

import math
from typing import Any, Mapping


def _finite_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(numeric):
        return default
    return numeric


def clip_float(value: float, min_value: float, max_value: float) -> float:
    """Clip a numeric value into an inclusive range."""

    lower = float(min_value)
    upper = float(max_value)
    if lower > upper:
        raise ValueError("min_value cannot be greater than max_value.")
    numeric = _finite_float(value, default=lower)
    return max(lower, min(upper, numeric))


def _gene_float(genes: Mapping[str, Any], name: str, default: float) -> float:
    return _finite_float(genes.get(name, default), default=default)


def _gene_int(genes: Mapping[str, Any], name: str, default: int) -> int:
    return int(_finite_float(genes.get(name, default), default=float(default)))


def score_to_risk_fraction(score: float, genes: Mapping[str, Any]) -> float:
    """Map a 0-100 resonance score into a capped risk fraction."""

    numeric_score = _finite_float(score, default=0.0)
    max_position_risk = max(0.0, _gene_float(genes, "max_position_risk", 0.01))

    if numeric_score < 60.0:
        risk_fraction = 0.0
    elif numeric_score < 70.0:
        risk_fraction = _gene_float(genes, "risk_low_score", 0.0025)
    elif numeric_score < 80.0:
        risk_fraction = _gene_float(genes, "risk_mid_score", 0.005)
    elif numeric_score < 90.0:
        risk_fraction = _gene_float(genes, "risk_high_score", 0.008)
    else:
        risk_fraction = max_position_risk

    return clip_float(risk_fraction, 0.0, max_position_risk)


def calculate_stake_amount(
    available_stake: float,
    score: float,
    stop_distance_ratio: float,
    genes: Mapping[str, Any],
    min_stake: float | None = None,
    max_stake: float | None = None,
) -> float:
    """Calculate a conservative stake size from risk budget and stop distance."""

    available = max(0.0, _finite_float(available_stake, default=0.0))
    if available <= 0.0:
        return 0.0

    risk_fraction = score_to_risk_fraction(score, genes)
    if risk_fraction <= 0.0:
        return 0.0

    stop_distance = _finite_float(stop_distance_ratio, default=0.0)
    if stop_distance <= 0.0:
        stop_distance = max(0.001, _gene_float(genes, "max_position_risk", 0.01))

    risk_capital = available * risk_fraction
    raw_stake = risk_capital / stop_distance

    stake_cap = available
    if max_stake is not None:
        stake_cap = min(stake_cap, max(0.0, _finite_float(max_stake, default=0.0)))

    if raw_stake <= 0.0 or stake_cap <= 0.0:
        return 0.0

    if min_stake is not None:
        minimum = max(0.0, _finite_float(min_stake, default=0.0))
        if 0.0 < raw_stake < minimum:
            return minimum if minimum <= stake_cap else 0.0

    return clip_float(raw_stake, 0.0, stake_cap)


def calculate_dca_stake(
    current_stake: float,
    score: float,
    current_profit: float,
    successful_entries: int,
    has_open_orders: bool,
    four_hour_regime_ok: bool,
    genes: Mapping[str, Any],
) -> float | None:
    """Return an additional DCA stake when drawdown and score gates agree."""

    if has_open_orders or not four_hour_regime_ok:
        return None

    max_dca_orders = max(0, _gene_int(genes, "max_dca_orders", 2))
    if successful_entries <= 0 or successful_entries > max_dca_orders:
        return None

    if _finite_float(score, default=0.0) < _gene_float(genes, "dca_score_min", 75.0):
        return None

    profit = _finite_float(current_profit, default=0.0)
    trigger_1 = _gene_float(genes, "dca_drawdown_trigger_1", -0.03)
    trigger_2 = _gene_float(genes, "dca_drawdown_trigger_2", -0.06)
    stake = max(0.0, _finite_float(current_stake, default=0.0))

    if stake <= 0.0:
        return None
    if profit <= trigger_2:
        return stake * clip_float(_gene_float(genes, "dca_size_mult_2", 0.75), 0.0, 5.0)
    if profit <= trigger_1:
        return stake * clip_float(_gene_float(genes, "dca_size_mult_1", 0.5), 0.0, 5.0)
    return None


def should_reduce_position(score: float, already_reduced: bool = False) -> str | None:
    """Return a conservative reduce/exit action when resonance fades."""

    numeric_score = _finite_float(score, default=0.0)
    if numeric_score < 35.0:
        return "exit"
    if numeric_score < 50.0 and not already_reduced:
        return "reduce_half"
    return None


def calculate_leverage(
    score: float,
    max_leverage: float,
    trading_mode: str | None,
    genes: Mapping[str, Any],
) -> float:
    """Calculate bounded leverage for futures mode, or 1x for spot mode."""

    if str(trading_mode or "spot").lower() != "futures":
        return 1.0

    numeric_score = _finite_float(score, default=0.0)
    exchange_max = max(1.0, _finite_float(max_leverage, default=1.0))
    strategy_max = max(1.0, _gene_float(genes, "max_strategy_leverage", 3.0))
    allowed_max = min(exchange_max, strategy_max)

    if numeric_score >= 85.0:
        desired = 3.0
    elif numeric_score >= 70.0:
        desired = 2.0
    else:
        desired = 1.0
    return clip_float(desired, 1.0, allowed_max)


def calculate_stoploss_from_atr(
    atr: float,
    current_rate: float,
    atr_stop_mult: float,
    max_position_risk: float,
) -> float:
    """Convert ATR distance into a negative Freqtrade stoploss ratio."""

    max_risk = max(0.0, _finite_float(max_position_risk, default=0.01))
    rate = _finite_float(current_rate, default=0.0)
    atr_value = _finite_float(atr, default=0.0)
    multiplier = max(0.0, _finite_float(atr_stop_mult, default=2.0))

    if max_risk <= 0.0:
        return 0.0
    if rate <= 0.0 or atr_value <= 0.0:
        return -max_risk

    stop_distance = (atr_value * multiplier) / rate
    return -clip_float(stop_distance, 0.0, max_risk)
