"""Risk governor for leverage and position sizing recommendations.

The governor is advisory only: it does not mutate StrategyConfig instances,
place orders, or change fitness scoring. It returns a JSON-safe adjustment
report that callers can inspect before deciding how to apply constraints.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RiskGovernorConfig:
    max_leverage: float = 3.0
    max_risk_per_trade: float = 0.02
    max_portfolio_exposure: float = 0.30
    drawdown_cutoff: float = 0.10
    loss_streak_cutoff: int = 4
    drawdown_risk_multiplier: float = 0.50
    loss_streak_risk_multiplier: float = 0.50


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}_must_be_numeric")
    numeric = float(value)
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        raise ValueError(f"{field_name}_must_be_finite")
    return numeric


def _non_negative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name}_must_be_int")
    if value < 0:
        raise ValueError(f"{field_name}_must_be_non_negative")
    return value


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _metrics_snapshot(metrics: Any) -> dict[str, float | int]:
    return {
        "drawdown": _finite_float(_get_value(metrics, "drawdown", _get_value(metrics, "max_drawdown", 0.0)), field_name="drawdown"),
        "max_consecutive_losses": _non_negative_int(
            int(_get_value(metrics, "max_consecutive_losses", _get_value(metrics, "max_loss_streak", 0)) or 0),
            field_name="max_consecutive_losses",
        ),
    }


def apply_risk_governor(
    strategy_config: Any,
    metrics: Any,
    *,
    config: RiskGovernorConfig | None = None,
) -> dict[str, Any]:
    """Return JSON-safe leverage and risk-per-trade adjustment advice."""

    active_config = config or RiskGovernorConfig()
    original_leverage = _finite_float(_get_value(strategy_config, "leverage", 1.0), field_name="leverage")
    original_risk = _finite_float(
        _get_value(strategy_config, "risk_per_trade", 0.0),
        field_name="risk_per_trade",
    )
    adjusted_leverage = _clamp(original_leverage, 0.0, active_config.max_leverage)
    adjusted_risk = _clamp(original_risk, 0.0, active_config.max_risk_per_trade)
    snapshot = _metrics_snapshot(metrics)
    actions: list[str] = []

    if adjusted_leverage < original_leverage:
        actions.append("clamped_leverage_to_max")
    if adjusted_risk < original_risk:
        actions.append("clamped_risk_per_trade_to_max")

    if float(snapshot["drawdown"]) > active_config.drawdown_cutoff:
        adjusted_risk = min(adjusted_risk, active_config.max_risk_per_trade * active_config.drawdown_risk_multiplier)
        actions.append("reduced_risk_after_drawdown")
    if int(snapshot["max_consecutive_losses"]) > active_config.loss_streak_cutoff:
        adjusted_risk = min(
            adjusted_risk,
            active_config.max_risk_per_trade * active_config.loss_streak_risk_multiplier,
        )
        actions.append("reduced_risk_after_loss_streak")

    adjusted_exposure = min(active_config.max_portfolio_exposure, adjusted_leverage * adjusted_risk)
    original_exposure = original_leverage * original_risk
    result = {
        "schema_version": "risk-governor/v1",
        "strategy_id": str(_get_value(strategy_config, "genome_id", "unknown")),
        "original_leverage": round(original_leverage, 10),
        "adjusted_leverage": round(adjusted_leverage, 10),
        "original_risk_per_trade": round(original_risk, 10),
        "adjusted_risk_per_trade": round(adjusted_risk, 10),
        "original_portfolio_exposure": round(original_exposure, 10),
        "adjusted_portfolio_exposure": round(adjusted_exposure, 10),
        "metrics": snapshot,
        "limits": asdict(active_config),
        "actions": actions,
        "explanation": [
            "advisory_only_no_strategy_mutation",
            *actions,
        ],
    }
    json.dumps(result, sort_keys=True)
    return result
