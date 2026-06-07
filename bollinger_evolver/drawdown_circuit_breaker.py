"""Mock drawdown circuit breaker simulator."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal


Action = Literal["reduce_risk", "pause_trading", "none"]


@dataclass(frozen=True)
class DrawdownCircuitBreakerConfig:
    reduce_risk_drawdown: float = 0.10
    pause_trading_drawdown: float = 0.20


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"drawdown_field_must_be_numeric:{field_name}")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"drawdown_field_must_be_finite:{field_name}")
    return numeric


def simulate_drawdown_circuit_breaker(
    equity_curve: Sequence[float],
    *,
    config: DrawdownCircuitBreakerConfig | None = None,
) -> dict[str, Any]:
    """Evaluate an equity curve against mock drawdown thresholds."""

    if isinstance(equity_curve, (str, bytes)) or not isinstance(equity_curve, Sequence):
        raise ValueError("equity_curve_must_be_sequence")

    active_config = config or DrawdownCircuitBreakerConfig()
    if active_config.reduce_risk_drawdown < 0.0 or active_config.pause_trading_drawdown < 0.0:
        raise ValueError("drawdown_thresholds_must_be_non_negative")
    if active_config.pause_trading_drawdown < active_config.reduce_risk_drawdown:
        raise ValueError("pause_drawdown_must_be_at_least_reduce_drawdown")

    peak = 0.0
    max_drawdown = 0.0
    max_drawdown_index: int | None = None
    for index, value in enumerate(equity_curve):
        equity = _finite_float(value, field_name="equity")
        if equity <= 0.0:
            raise ValueError("equity_curve_values_must_be_positive")
        peak = max(peak, equity)
        drawdown = 0.0 if peak <= 0.0 else (peak - equity) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            max_drawdown_index = index

    action: Action = "none"
    if max_drawdown >= active_config.pause_trading_drawdown:
        action = "pause_trading"
    elif max_drawdown >= active_config.reduce_risk_drawdown:
        action = "reduce_risk"

    result = {
        "schema_version": "drawdown-circuit-breaker/v1",
        "triggered": action != "none",
        "trigger_index": max_drawdown_index if action != "none" else None,
        "max_drawdown": round(max_drawdown, 10),
        "action": action,
        "thresholds": asdict(active_config),
    }
    json.dumps(result, sort_keys=True)
    return result
