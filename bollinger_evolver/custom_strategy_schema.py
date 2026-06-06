"""Custom strategy genome schema for mock-first strategy abstraction.

This module defines parameter bounds and JSON-safe mapping for a future custom
trading system. It does not run backtests, import Freqtrade, or access an
exchange.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True)
class CustomStrategyGenome:
    genome_id: str
    entry_bb_window: int = 20
    entry_bb_stddev: float = 2.0
    entry_rsi_period: int = 14
    entry_rsi_max: float = 35.0
    exit_take_profit_pct: float = 0.08
    exit_stop_loss_pct: float = 0.03
    trailing_stop_pct: float = 0.02
    add_position_threshold_pct: float = 0.025
    reduce_position_threshold_pct: float = 0.04
    max_additions: int = 2
    leverage: float = 1.0
    risk_per_trade: float = 0.01
    max_portfolio_exposure: float = 0.30
    cooldown_candles: int = 3

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


@dataclass(frozen=True)
class ParameterBound:
    minimum: float
    maximum: float
    kind: str = "float"

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


@dataclass(frozen=True)
class CustomStrategyBounds:
    entry_bb_window: ParameterBound = ParameterBound(10, 80, "int")
    entry_bb_stddev: ParameterBound = ParameterBound(1.2, 3.5, "float")
    entry_rsi_period: ParameterBound = ParameterBound(5, 40, "int")
    entry_rsi_max: ParameterBound = ParameterBound(10.0, 55.0, "float")
    exit_take_profit_pct: ParameterBound = ParameterBound(0.01, 0.25, "float")
    exit_stop_loss_pct: ParameterBound = ParameterBound(0.005, 0.12, "float")
    trailing_stop_pct: ParameterBound = ParameterBound(0.0, 0.08, "float")
    add_position_threshold_pct: ParameterBound = ParameterBound(0.0, 0.08, "float")
    reduce_position_threshold_pct: ParameterBound = ParameterBound(0.0, 0.15, "float")
    max_additions: ParameterBound = ParameterBound(0, 3, "int")
    leverage: ParameterBound = ParameterBound(1.0, 3.0, "float")
    risk_per_trade: ParameterBound = ParameterBound(0.001, 0.02, "float")
    max_portfolio_exposure: ParameterBound = ParameterBound(0.05, 0.60, "float")
    cooldown_candles: ParameterBound = ParameterBound(0, 72, "int")

    def to_dict(self) -> dict[str, dict[str, float | str]]:
        return {field.name: getattr(self, field.name).to_dict() for field in fields(self)}


CUSTOM_STRATEGY_PARAMETER_NAMES: tuple[str, ...] = tuple(field.name for field in fields(CustomStrategyBounds))


def _finite_float(value: Any, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name}_must_be_numeric")
    numeric = float(value)
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        raise ValueError(f"{field_name}_must_be_finite")
    return numeric


def _coerce_genome(genome: CustomStrategyGenome | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(genome, CustomStrategyGenome):
        return genome.to_dict()
    if not isinstance(genome, Mapping):
        raise TypeError("custom_strategy_genome_must_be_mapping_or_dataclass")
    return dict(genome)


def validate_custom_strategy_genome(
    genome: CustomStrategyGenome | Mapping[str, Any],
    *,
    bounds: CustomStrategyBounds | None = None,
) -> None:
    """Validate a custom strategy genome against explicit parameter bounds."""

    data = _coerce_genome(genome)
    expected = {"genome_id", *CUSTOM_STRATEGY_PARAMETER_NAMES}
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(f"invalid_custom_strategy_genome_fields: missing={missing}, unknown={unknown}")
    if not isinstance(data["genome_id"], str) or not data["genome_id"].strip():
        raise ValueError("genome_id_required")

    active_bounds = bounds or CustomStrategyBounds()
    for name in CUSTOM_STRATEGY_PARAMETER_NAMES:
        bound = getattr(active_bounds, name)
        value = data[name]
        numeric = _finite_float(value, field_name=name)
        if bound.kind == "int" and not isinstance(value, int):
            raise ValueError(f"{name}_must_be_int")
        if bound.kind not in {"int", "float"}:
            raise ValueError(f"{name}_unsupported_bound_kind")
        if not bound.minimum <= numeric <= bound.maximum:
            raise ValueError(f"{name}_out_of_bounds")

    if float(data["exit_stop_loss_pct"]) >= float(data["exit_take_profit_pct"]):
        raise ValueError("stoploss_must_be_below_takeprofit")
    if float(data["max_portfolio_exposure"]) > 1.0:
        raise ValueError("max_portfolio_exposure_must_not_exceed_one")

    json.dumps(data, sort_keys=True)


def custom_strategy_config_from_genome(
    genome: CustomStrategyGenome | Mapping[str, Any],
    *,
    bounds: CustomStrategyBounds | None = None,
) -> dict[str, Any]:
    """Map a validated custom strategy genome to a JSON-safe StrategyConfig."""

    validate_custom_strategy_genome(genome, bounds=bounds)
    data = _coerce_genome(genome)
    config: dict[str, Any] = {
        "schema_version": "custom-strategy/v1",
        "genome_id": str(data["genome_id"]),
        "entry": {
            "bollinger_window": int(data["entry_bb_window"]),
            "bollinger_stddev": float(data["entry_bb_stddev"]),
            "rsi_period": int(data["entry_rsi_period"]),
            "rsi_max": float(data["entry_rsi_max"]),
        },
        "exit": {
            "take_profit_pct": float(data["exit_take_profit_pct"]),
            "stop_loss_pct": float(data["exit_stop_loss_pct"]),
            "trailing_stop_pct": float(data["trailing_stop_pct"]),
        },
        "position_sizing": {
            "add_position_threshold_pct": float(data["add_position_threshold_pct"]),
            "reduce_position_threshold_pct": float(data["reduce_position_threshold_pct"]),
            "max_additions": int(data["max_additions"]),
            "leverage": float(data["leverage"]),
            "risk_per_trade": float(data["risk_per_trade"]),
            "max_portfolio_exposure": float(data["max_portfolio_exposure"]),
        },
        "execution_controls": {
            "cooldown_candles": int(data["cooldown_candles"]),
            "real_execution_enabled": False,
            "dry_run_only": True,
        },
        "constraints": {
            "no_freqtrade_execution": True,
            "no_exchange_api": True,
            "risk_governor_advisory_only": True,
        },
        "parameters": {name: data[name] for name in CUSTOM_STRATEGY_PARAMETER_NAMES},
        "bounds": (bounds or CustomStrategyBounds()).to_dict(),
        "bollinger_window": int(data["entry_bb_window"]),
        "bollinger_stddev": float(data["entry_bb_stddev"]),
        "stoploss": float(data["exit_stop_loss_pct"]),
        "takeprofit": float(data["exit_take_profit_pct"]),
        "leverage": float(data["leverage"]),
        "risk_per_trade": float(data["risk_per_trade"]),
        "max_portfolio_exposure": float(data["max_portfolio_exposure"]),
    }
    json.dumps(config, sort_keys=True)
    return config
