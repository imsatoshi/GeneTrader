"""Read-only data coverage gate for Bollinger Evolver evaluation safety."""

from __future__ import annotations

from typing import Any, Mapping

from bollinger_evolver.evaluators import sanitize_mapping


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple, set)) else []


def _unique_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _entry_key(entry: Mapping[str, Any]) -> tuple[str, str]:
    return str(entry.get("pair", "")), str(entry.get("timeframe", ""))


def _to_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def evaluate_data_coverage_gate(
    manifest: dict | None,
    required_pairs: list[str] | None = None,
    required_timeframes: list[str] | None = None,
    min_candles_per_pair_timeframe: int = 100,
    max_gap_ratio: float = 0.02,
    allow_invalid_ohlc: bool = False,
) -> dict[str, Any]:
    """Evaluate whether local data coverage is safe enough for candidate scoring.

    The gate is intentionally read-only. It consumes an already-built manifest and
    returns an explainable pass/fail payload for evaluators and artifacts.
    """

    if manifest is None:
        return {
            "status": "MISSING",
            "allowed_for_evaluation": False,
            "required_pairs": list(required_pairs or []),
            "required_timeframes": list(required_timeframes or []),
            "checked_pairs": [],
            "checked_timeframes": [],
            "fail_reasons": ["data_quality_manifest_missing"],
            "warnings": [],
            "coverage_summary": {
                "pair_timeframe_count": 0,
                "missing_pair_timeframes": [],
                "low_candle_count": [],
                "gap_issues": [],
                "invalid_ohlc_issues": [],
            },
            "readOnly": True,
        }

    safe_manifest = sanitize_mapping(manifest)
    entries = [
        entry
        for entry in _as_list(safe_manifest.get("entries"))
        if isinstance(entry, Mapping)
    ]
    checked_pairs = _unique_strings(
        _as_list(safe_manifest.get("pairs"))
        or [entry.get("pair") for entry in entries if entry.get("pair")]
    )
    checked_timeframes = _unique_strings(
        _as_list(safe_manifest.get("timeframes"))
        or [entry.get("timeframe") for entry in entries if entry.get("timeframe")]
    )
    required_pairs_list = _unique_strings(list(required_pairs or checked_pairs))
    required_timeframes_list = _unique_strings(list(required_timeframes or checked_timeframes))
    entries_by_key = {_entry_key(entry): entry for entry in entries}

    missing_pair_timeframes: list[dict[str, str]] = []
    low_candle_count: list[dict[str, Any]] = []
    gap_issues: list[dict[str, Any]] = []
    invalid_ohlc_issues: list[dict[str, Any]] = []
    fail_reasons: list[str] = []
    warnings: list[str] = []

    for pair in required_pairs_list:
        for timeframe in required_timeframes_list:
            entry = entries_by_key.get((pair, timeframe))
            if entry is None or entry.get("status") == "missing":
                missing_pair_timeframes.append({"pair": pair, "timeframe": timeframe})
                continue

            row_count = _to_int(entry.get("row_count"))
            if row_count < int(min_candles_per_pair_timeframe):
                low_candle_count.append(
                    {"pair": pair, "timeframe": timeframe, "row_count": row_count}
                )

            invalid_count = _to_int(entry.get("invalid_ohlc_count"))
            if invalid_count > 0:
                invalid_ohlc_issues.append(
                    {"pair": pair, "timeframe": timeframe, "invalid_ohlc_count": invalid_count}
                )

            gap_count = _to_int(entry.get("gap_count"))
            gap_ratio = gap_count / max(row_count, 1)
            if gap_ratio > float(max_gap_ratio):
                gap_issues.append(
                    {
                        "pair": pair,
                        "timeframe": timeframe,
                        "gap_count": gap_count,
                        "gap_ratio": gap_ratio,
                    }
                )

    if missing_pair_timeframes:
        fail_reasons.append("missing_pair_timeframe")
    if low_candle_count:
        fail_reasons.append("low_candle_count")
    if invalid_ohlc_issues and not allow_invalid_ohlc:
        fail_reasons.append("invalid_ohlc")
    elif invalid_ohlc_issues:
        warnings.append("invalid_ohlc_allowed")
    if gap_issues:
        fail_reasons.append("excessive_gap_ratio")

    manifest_status = safe_manifest.get("status")
    if manifest_status in {"missing", "partial"} and not fail_reasons:
        warnings.append(f"manifest_status_{manifest_status}")

    status = "PASS"
    if fail_reasons:
        status = "FAIL"
    elif warnings:
        status = "WARN"

    return {
        "status": status,
        "allowed_for_evaluation": status in {"PASS", "WARN"},
        "required_pairs": required_pairs_list,
        "required_timeframes": required_timeframes_list,
        "checked_pairs": checked_pairs,
        "checked_timeframes": checked_timeframes,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "coverage_summary": {
            "pair_timeframe_count": len(entries),
            "missing_pair_timeframes": missing_pair_timeframes,
            "low_candle_count": low_candle_count,
            "gap_issues": gap_issues,
            "invalid_ohlc_issues": invalid_ohlc_issues,
        },
        "readOnly": True,
    }
