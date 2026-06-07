"""Mock account-level risk budget simulator.

This module only evaluates local position dictionaries. It does not read
accounts, place orders, connect to exchanges, or mutate strategy state.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any


SCHEMA_VERSION = "risk-budget-simulation/v1"


@dataclass(frozen=True)
class RiskBudgetConfig:
    max_portfolio_exposure: float = 0.30
    max_pair_exposure: float = 0.15
    max_leverage_usage: float = 1.00
    loss_streak_cutoff: int = 4
    loss_streak_risk_multiplier: float = 0.50


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"risk_budget_field_must_be_numeric:{field_name}")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"risk_budget_field_must_be_finite:{field_name}")
    return numeric


def _validate_position(position: Mapping[str, Any]) -> dict[str, Any]:
    if "pair" not in position:
        raise ValueError("risk_budget_position_missing_field:pair")
    if "exposure" not in position:
        raise ValueError("risk_budget_position_missing_field:exposure")
    pair = str(position["pair"]).strip()
    if not pair:
        raise ValueError("risk_budget_pair_required")
    exposure = _finite_float(position["exposure"], field_name="exposure")
    leverage = _finite_float(position.get("leverage", 1.0), field_name="leverage")
    if exposure < 0.0:
        raise ValueError("risk_budget_exposure_must_be_non_negative")
    if leverage < 0.0:
        raise ValueError("risk_budget_leverage_must_be_non_negative")
    return {
        "pair": pair,
        "exposure": exposure,
        "leverage": leverage,
    }


def simulate_risk_budget(
    positions: Sequence[Mapping[str, Any]],
    *,
    config: RiskBudgetConfig | None = None,
    loss_streak: int = 0,
) -> dict[str, Any]:
    """Return a JSON-safe account risk budget simulation for mock positions."""

    if isinstance(positions, (str, bytes)) or not isinstance(positions, Sequence):
        raise ValueError("risk_budget_positions_must_be_sequence")
    if isinstance(loss_streak, bool) or not isinstance(loss_streak, int) or loss_streak < 0:
        raise ValueError("risk_budget_loss_streak_must_be_non_negative_int")

    active_config = config or RiskBudgetConfig()
    pair_exposures: dict[str, float] = defaultdict(float)
    leverage_usage = 0.0
    for position in positions:
        if not isinstance(position, Mapping):
            raise ValueError("risk_budget_position_must_be_mapping")
        validated = _validate_position(position)
        pair_exposures[validated["pair"]] += validated["exposure"]
        leverage_usage += validated["exposure"] * validated["leverage"]

    rounded_pair_exposures = {
        pair: round(exposure, 10)
        for pair, exposure in sorted(pair_exposures.items())
    }
    total_exposure = sum(pair_exposures.values())
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    if total_exposure > active_config.max_portfolio_exposure:
        violations.append(
            {
                "code": "portfolio_exposure_exceeded",
                "actual": round(total_exposure, 10),
                "limit": active_config.max_portfolio_exposure,
            }
        )
        recommendations.append({"code": "reduce_total_exposure"})

    for pair, exposure in sorted(pair_exposures.items()):
        if exposure > active_config.max_pair_exposure:
            violations.append(
                {
                    "code": "pair_exposure_exceeded",
                    "pair": pair,
                    "actual": round(exposure, 10),
                    "limit": active_config.max_pair_exposure,
                }
            )
            recommendations.append({"code": "reduce_pair_exposure", "pair": pair})

    if leverage_usage > active_config.max_leverage_usage:
        warnings.append(
            {
                "code": "leverage_usage_exceeded",
                "actual": round(leverage_usage, 10),
                "limit": active_config.max_leverage_usage,
            }
        )
        recommendations.append({"code": "reduce_leverage_usage"})

    adjusted_risk_multiplier = 1.0
    if loss_streak >= active_config.loss_streak_cutoff:
        adjusted_risk_multiplier = active_config.loss_streak_risk_multiplier
        recommendations.append(
            {
                "code": "reduce_risk_after_loss_streak",
                "loss_streak": loss_streak,
                "risk_multiplier": adjusted_risk_multiplier,
            }
        )

    result = {
        "schema_version": SCHEMA_VERSION,
        "ok": not violations,
        "total_exposure": round(total_exposure, 10),
        "pair_exposures": rounded_pair_exposures,
        "leverage_usage": round(leverage_usage, 10),
        "adjusted_risk_multiplier": round(adjusted_risk_multiplier, 10),
        "violations": violations,
        "warnings": warnings,
        "recommendations": recommendations,
        "limits": asdict(active_config),
    }
    json.dumps(result, sort_keys=True)
    return result
