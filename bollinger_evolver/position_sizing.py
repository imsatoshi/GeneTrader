"""Mock position sizing math for custom strategy previews.

This module performs local arithmetic only. It does not read account balances,
query exchanges, place orders, or invoke Freqtrade.
"""

from __future__ import annotations

import json
import math
from typing import Any


SCHEMA_VERSION = "position-sizing/v1"


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}_must_be_numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{field_name}_must_be_finite")
    return numeric


def calculate_position_size(
    *,
    equity: float,
    risk_per_trade: float,
    stoploss_pct: float,
    leverage: float,
    max_position_value: float | None = None,
) -> dict[str, Any]:
    """Calculate mock position value, margin, and at-risk amount."""

    numeric_equity = _finite_float(equity, field_name="equity")
    numeric_risk_per_trade = _finite_float(risk_per_trade, field_name="risk_per_trade")
    numeric_stoploss_pct = _finite_float(stoploss_pct, field_name="stoploss_pct")
    numeric_leverage = _finite_float(leverage, field_name="leverage")

    if numeric_equity < 0.0:
        raise ValueError("equity_must_be_non_negative")
    if not 0.0 <= numeric_risk_per_trade <= 1.0:
        raise ValueError("risk_per_trade_must_be_between_zero_and_one")
    if numeric_stoploss_pct <= 0.0:
        raise ValueError("stoploss_pct_must_be_greater_than_zero")
    if numeric_leverage <= 0.0:
        raise ValueError("leverage_must_be_greater_than_zero")

    warnings: list[str] = []
    risk_budget = numeric_equity * numeric_risk_per_trade
    raw_position_value = risk_budget / numeric_stoploss_pct
    position_value = raw_position_value

    if max_position_value is not None:
        numeric_max_position_value = _finite_float(max_position_value, field_name="max_position_value")
        if numeric_max_position_value < 0.0:
            raise ValueError("max_position_value_must_be_non_negative")
        if raw_position_value > numeric_max_position_value:
            position_value = numeric_max_position_value
            warnings.append("max_position_value_applied")

    risk_amount = position_value * numeric_stoploss_pct
    margin_required = position_value / numeric_leverage
    if numeric_risk_per_trade >= 0.02:
        warnings.append("risk_per_trade_near_upper_bound")
    if numeric_leverage >= 3.0:
        warnings.append("high_leverage")

    result = {
        "schema_version": SCHEMA_VERSION,
        "position_value": round(position_value, 10),
        "margin_required": round(margin_required, 10),
        "risk_amount": round(risk_amount, 10),
        "leverage": round(numeric_leverage, 10),
        "warnings": warnings,
    }
    json.dumps(result, sort_keys=True)
    return result
