"""Adapter from custom StrategyConfig into a JSON-safe trading-system config.

The adapter only builds and writes inert configuration payloads. It does not
import Freqtrade, call subprocesses, place orders, download data, or read
secrets.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bollinger_evolver.risk_governor import RiskGovernorConfig


CONFIG_FILENAME = "trading_system_config.json"
SENSITIVE_FIELD_MARKERS = (
    "api_key",
    "api_secret",
    "secret",
    "token",
    "password",
    "private_key",
    "webhook",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _json_safe_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _contains_sensitive_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            if not lowered.startswith("no_") and any(marker in lowered for marker in SENSITIVE_FIELD_MARKERS):
                return True
            if _contains_sensitive_field(item):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_sensitive_field(item) for item in value)
    return False


def _require_mapping(value: Any, *, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name}_must_be_mapping")
    return value


def _get_number(source: Mapping[str, Any], key: str, *, default: float | None = None) -> float:
    value = source.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key}_must_be_numeric")
    numeric = float(value)
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        raise ValueError(f"{key}_must_be_finite")
    return numeric


def _get_int(source: Mapping[str, Any], key: str, *, default: int | None = None) -> int:
    value = source.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key}_must_be_int")
    return int(value)


def build_trading_system_config(strategy_config: Mapping[str, Any]) -> dict[str, Any]:
    """Build a JSON-safe config dict for the future custom trading system."""

    source = _require_mapping(strategy_config, field_name="strategy_config")
    if _contains_sensitive_field(source):
        raise ValueError("strategy_config_contains_secret_field")

    entry = _require_mapping(source.get("entry"), field_name="entry")
    exit_config = _require_mapping(source.get("exit"), field_name="exit")
    position = _require_mapping(source.get("position_sizing"), field_name="position_sizing")
    execution = _require_mapping(source.get("execution_controls"), field_name="execution_controls")
    risk_defaults = RiskGovernorConfig()

    leverage = _get_number(position, "leverage", default=_get_number(source, "leverage", default=1.0))
    risk_per_trade = _get_number(
        position,
        "risk_per_trade",
        default=_get_number(source, "risk_per_trade", default=0.01),
    )
    max_additions = _get_int(position, "max_additions", default=0)
    max_open_positions = max(1, 1 + max_additions)
    stoploss = _get_number(exit_config, "stop_loss_pct")
    takeprofit = _get_number(exit_config, "take_profit_pct")
    if stoploss >= takeprofit:
        raise ValueError("stoploss_must_be_below_takeprofit")

    payload = {
        "schema_version": "custom-trading-system-config/v1",
        "source": "custom-strategy-schema",
        "strategy_id": str(source.get("genome_id", "unknown")),
        "entry": {
            "bollinger": {
                "window": _get_int(entry, "bollinger_window"),
                "stddev": _get_number(entry, "bollinger_stddev"),
            },
            "rsi": {
                "period": _get_int(entry, "rsi_period"),
                "max": _get_number(entry, "rsi_max"),
            },
        },
        "exit": {
            "stoploss_pct": stoploss,
            "takeprofit_pct": takeprofit,
            "trailing_stop_pct": _get_number(exit_config, "trailing_stop_pct"),
        },
        "position": {
            "base_leverage": leverage,
            "max_leverage": min(leverage, risk_defaults.max_leverage),
            "risk_per_trade": risk_per_trade,
            "max_open_positions": max_open_positions,
            "max_additions": max_additions,
            "add_position_threshold_pct": _get_number(position, "add_position_threshold_pct"),
            "reduce_position_threshold_pct": _get_number(position, "reduce_position_threshold_pct"),
        },
        "risk_control": {
            "max_portfolio_exposure": _get_number(position, "max_portfolio_exposure"),
            "drawdown_cutoff": risk_defaults.drawdown_cutoff,
            "loss_streak_cutoff": risk_defaults.loss_streak_cutoff,
            "cooldown_candles": _get_int(execution, "cooldown_candles"),
        },
        "execution": {
            "dry_run_only": True,
            "real_trading_enabled": False,
            "download_data_enabled": False,
            "deployment_enabled": False,
            "rollback_enabled": False,
        },
        "constraints": {
            "no_exchange_api": True,
            "no_real_orders": True,
            "no_freqtrade_subprocess": True,
            "no_secret_fields": True,
        },
    }
    if _contains_sensitive_field(payload):
        raise ValueError("trading_system_config_contains_secret_field")
    return _json_safe_copy(payload)


def _resolve_config_output_path(output_path: str | Path) -> Path:
    if output_path is None or not str(output_path).strip():
        raise ValueError("trading_system_config_output_required")
    requested = Path(output_path).resolve()
    root = _repo_root().resolve()
    if requested == root:
        raise ValueError("trading_system_config_output_must_not_be_repo_root")
    destination = requested if requested.suffix.lower() == ".json" else requested / CONFIG_FILENAME
    disallowed_roots = (
        root / ".runtime",
        root / ".workflow",
        root / "user_data" / "data",
        root / "user_data" / "strategies",
        root / "strategies",
        root / "strategy",
    )
    if destination.name.lower() == ".env":
        raise ValueError("trading_system_config_output_disallowed")
    if any(destination == item or _is_relative_to(destination, item) for item in disallowed_roots):
        raise ValueError("trading_system_config_output_disallowed")
    return destination


def write_trading_system_config(config: Mapping[str, Any], output_path: str | Path) -> Path:
    """Write one inert trading-system config JSON file into an explicit safe path."""

    payload = _json_safe_copy(config)
    if _contains_sensitive_field(payload):
        raise ValueError("trading_system_config_contains_secret_field")
    destination = _resolve_config_output_path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return destination
