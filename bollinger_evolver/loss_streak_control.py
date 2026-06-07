"""Mock loss-streak based risk reducer."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class LossStreakControlConfig:
    trigger_loss_streak: int = 4
    risk_multiplier: float = 0.50
    leverage_multiplier: float = 0.75
    cooldown_increment: int = 12
    min_risk_per_trade: float = 0.001
    min_leverage: float = 1.0


def _json_clone(value: Any, *, error_code: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(error_code) from exc


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"loss_streak_field_must_be_numeric:{field_name}")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"loss_streak_field_must_be_finite:{field_name}")
    return numeric


def _non_negative_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"loss_streak_field_must_be_int:{field_name}")
    if value < 0:
        raise ValueError(f"loss_streak_field_must_be_non_negative:{field_name}")
    return value


def _current_cooldown(strategy_config: Mapping[str, Any]) -> int:
    controls = strategy_config.get("execution_controls", {})
    if isinstance(controls, Mapping):
        value = controls.get("cooldown_candles", strategy_config.get("cooldown_candles", 0))
    else:
        value = strategy_config.get("cooldown_candles", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("loss_streak_field_must_be_int:cooldown_candles")
    return max(0, value)


def apply_loss_streak_control(
    strategy_config: Mapping[str, Any],
    loss_streak: int,
    *,
    config: LossStreakControlConfig | None = None,
) -> dict[str, Any]:
    """Return advisory risk reductions after a mock consecutive-loss streak."""

    if not isinstance(strategy_config, Mapping):
        raise ValueError("strategy_config_must_be_mapping")
    active_config = config or LossStreakControlConfig()
    normalized_loss_streak = _non_negative_int(loss_streak, field_name="loss_streak")
    original = _json_clone(dict(strategy_config), error_code="strategy_config_not_json_safe")
    adjusted = _json_clone(original, error_code="strategy_config_not_json_safe")
    actions: list[dict[str, Any]] = []

    if normalized_loss_streak >= active_config.trigger_loss_streak:
        original_risk = _finite_float(original.get("risk_per_trade", 0.0), field_name="risk_per_trade")
        original_leverage = _finite_float(original.get("leverage", 1.0), field_name="leverage")
        adjusted_risk = max(active_config.min_risk_per_trade, original_risk * active_config.risk_multiplier)
        adjusted_leverage = max(active_config.min_leverage, original_leverage * active_config.leverage_multiplier)
        adjusted["risk_per_trade"] = round(adjusted_risk, 10)
        adjusted["leverage"] = round(adjusted_leverage, 10)
        actions.append({"code": "risk_reduced", "risk_multiplier": active_config.risk_multiplier})
        actions.append({"code": "leverage_reduced", "leverage_multiplier": active_config.leverage_multiplier})

        controls = adjusted.get("execution_controls")
        if not isinstance(controls, dict):
            controls = {}
            adjusted["execution_controls"] = controls
        controls["cooldown_candles"] = _current_cooldown(original) + active_config.cooldown_increment
        actions.append({"code": "cooldown_applied", "cooldown_increment": active_config.cooldown_increment})

    result = {
        "schema_version": "loss-streak-control/v1",
        "loss_streak": normalized_loss_streak,
        "triggered": bool(actions),
        "actions": actions,
        "original": original,
        "adjusted": adjusted,
        "limits": asdict(active_config),
    }
    json.dumps(result, sort_keys=True)
    return result
