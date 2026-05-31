"""Load and validate Bollinger Evolver configuration.

This loader is intentionally independent from GeneTrader's existing
``config.settings.Settings`` path so future Bollinger work can evolve without
changing the current production configuration contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable


class BollingerConfigError(Exception):
    """Raised when the Bollinger Evolver config is missing or invalid."""


REQUIRED_FIELDS = {
    "base_timeframe",
    "informative_timeframes",
    "market_filter_pair",
    "population_size",
    "generations",
    "crossover_prob",
    "mutation_prob",
    "pool_processes",
    "enable_walk_forward",
    "walk_forward_train_weeks",
    "walk_forward_test_weeks",
    "min_trades_per_week",
    "max_drawdown_limit",
    "min_profit_factor",
    "random_seed",
}


def _require_type(config: Dict[str, Any], field_name: str, expected_type: Any) -> None:
    value = config[field_name]
    if not isinstance(value, expected_type):
        expected_name = (
            expected_type.__name__
            if hasattr(expected_type, "__name__")
            else str(expected_type)
        )
        raise BollingerConfigError(
            f"Field '{field_name}' must be of type {expected_name}, "
            f"got {type(value).__name__}."
        )


def _require_numeric_range(
    config: Dict[str, Any],
    field_name: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> None:
    value = config[field_name]
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BollingerConfigError(
            f"Field '{field_name}' must be numeric, got {type(value).__name__}."
        )
    if minimum is not None and value < minimum:
        raise BollingerConfigError(
            f"Field '{field_name}' must be >= {minimum}, got {value}."
        )
    if maximum is not None and value > maximum:
        raise BollingerConfigError(
            f"Field '{field_name}' must be <= {maximum}, got {value}."
        )


def _require_string_list(config: Dict[str, Any], field_name: str) -> None:
    value = config[field_name]
    if not isinstance(value, list) or not value:
        raise BollingerConfigError(
            f"Field '{field_name}' must be a non-empty list of strings."
        )
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise BollingerConfigError(
            f"Field '{field_name}' must contain only non-empty strings."
        )


def validate_bollinger_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a parsed Bollinger Evolver config dictionary."""

    missing_fields = sorted(REQUIRED_FIELDS.difference(config.keys()))
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise BollingerConfigError(f"Missing required config fields: {missing}")

    _require_type(config, "base_timeframe", str)
    _require_string_list(config, "informative_timeframes")
    _require_type(config, "market_filter_pair", str)
    _require_type(config, "enable_walk_forward", bool)

    _require_numeric_range(config, "population_size", minimum=1)
    _require_numeric_range(config, "generations", minimum=1)
    _require_numeric_range(config, "crossover_prob", minimum=0.0, maximum=1.0)
    _require_numeric_range(config, "mutation_prob", minimum=0.0, maximum=1.0)
    _require_numeric_range(config, "pool_processes", minimum=1)
    _require_numeric_range(config, "walk_forward_train_weeks", minimum=1)
    _require_numeric_range(config, "walk_forward_test_weeks", minimum=1)
    _require_numeric_range(config, "min_trades_per_week", minimum=0.0)
    _require_numeric_range(config, "max_drawdown_limit", minimum=0.0, maximum=1.0)
    _require_numeric_range(config, "min_profit_factor", minimum=0.0)
    _require_numeric_range(config, "random_seed", minimum=0)

    return config


def load_bollinger_config(config_path: str | Path) -> Dict[str, Any]:
    """Load and validate a Bollinger Evolver JSON config file."""

    path = Path(config_path)
    if not path.exists():
        raise BollingerConfigError(f"Configuration file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BollingerConfigError(f"Invalid JSON in configuration file: {exc}") from exc

    if not isinstance(data, dict):
        raise BollingerConfigError("Top-level configuration must be a JSON object.")

    return validate_bollinger_config(data)
