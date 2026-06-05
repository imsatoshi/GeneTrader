"""Build offline data requirements from Bollinger Evolver config payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.data_gate import normalize_pair_symbol, normalize_timeframe
from bollinger_evolver.evaluators import sanitize_mapping


def _extract_config_pairs(config: Mapping[str, Any]) -> list[str]:
    raw_pairs = config.get("pairs")
    if raw_pairs is None:
        raw_pairs = config.get("pair_whitelist")
    if raw_pairs is None and config.get("market_filter_pair") is not None:
        raw_pairs = [config.get("market_filter_pair")]
    if not isinstance(raw_pairs, list):
        raise ValueError("config_pairs_missing")
    pairs = []
    for pair in raw_pairs:
        normalized = normalize_pair_symbol(pair)
        if normalized is None:
            raise ValueError("config_pair_invalid")
        pairs.append(normalized)
    if not pairs:
        raise ValueError("config_pairs_missing")
    return sorted(set(pairs))


def _extract_config_timeframes(config: Mapping[str, Any]) -> list[str]:
    raw_timeframes: list[Any] = []
    if config.get("base_timeframe") is not None:
        raw_timeframes.append(config.get("base_timeframe"))
    informative = config.get("informative_timeframes")
    if isinstance(informative, list):
        raw_timeframes.extend(informative)
    if not raw_timeframes:
        raise ValueError("config_timeframes_missing")
    timeframes = []
    for timeframe in raw_timeframes:
        normalized = normalize_timeframe(timeframe)
        if normalized is None:
            raise ValueError("config_timeframe_invalid")
        timeframes.append(normalized)
    return sorted(set(timeframes))


def build_offline_requirements_from_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Derive offline data pair/timeframe requirements from a GA config object."""

    if not isinstance(config, Mapping):
        raise ValueError("config_must_be_object")
    return sanitize_mapping(
        {
            "pairs": _extract_config_pairs(config),
            "timeframes": _extract_config_timeframes(config),
        }
    )


def load_offline_requirements_from_config(path: str | Path) -> dict[str, Any]:
    """Load a JSON config file and derive offline data requirements."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("config_json_invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("config_must_be_object")
    return build_offline_requirements_from_config(payload)
