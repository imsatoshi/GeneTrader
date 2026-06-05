"""Read-only offline data readiness gate for required Bollinger datasets."""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bollinger_evolver.data_manifest import (
    build_offline_data_manifest,
    detect_data_file_format,
    infer_pair_timeframe_from_path,
)
from bollinger_evolver.evaluators import sanitize_mapping


SCHEMA_VERSION = "offline_data_manifest.v1"
DEFAULT_SYMBOL = "BTC/USDT"
DEFAULT_REQUIRED_TIMEFRAMES = ["15m", "1h", "4h"]
DEFAULT_MIN_CANDLES = 100
ACCEPTED_FORMATS = {"json", "jsonl", "json.gz", "csv", "feather", "parquet"}
INVENTORY_TIMEFRAME_RE = re.compile(r"^\d+[mhdwM]$")
INVENTORY_PAIR_RE = re.compile(r"^[A-Z0-9]+/[A-Z0-9]+$")
PAIR_SYMBOL_RE = re.compile(r"^(?P<base>[A-Za-z0-9]+)[/_-](?P<quote>[A-Za-z0-9]+)$")
TIMEFRAME_RE = re.compile(r"^(?P<count>\d+)(?P<unit>[mhdwMHDW])$")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (_project_root() / path).resolve()


def _normalize_required_timeframes(value: list[str] | tuple[str, ...] | None) -> list[str]:
    return [
        normalized
        for item in (value or DEFAULT_REQUIRED_TIMEFRAMES)
        if (normalized := normalize_timeframe(item)) is not None
    ]


def normalize_pair_symbol(value: Any) -> str | None:
    """Normalize a simple spot pair token to BASE/QUOTE form."""

    text = str(value).strip()
    match = PAIR_SYMBOL_RE.match(text)
    if match is None:
        return None
    return f"{match.group('base').upper()}/{match.group('quote').upper()}"


def normalize_timeframe(value: Any) -> str | None:
    """Normalize a timeframe token to lowercase count+unit form."""

    text = str(value).strip()
    match = TIMEFRAME_RE.match(text)
    if match is None:
        return None
    return f"{match.group('count')}{match.group('unit').lower()}"


def _read_first_json_row(path: Path) -> Any:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, list) and payload:
        return payload[0]
    return None


def _read_first_jsonl_row(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                return json.loads(text)
    except (OSError, json.JSONDecodeError):
        return None
    return None


def _read_csv_columns(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [column.strip() for column in (reader.fieldnames or [])]
    except OSError:
        return []


def _read_pandas_columns(path: Path, loader_name: str) -> list[str]:
    try:
        import pandas as pd
    except Exception:
        return []
    loader = getattr(pd, loader_name, None)
    if loader is None:
        return []
    try:
        dataframe = loader(path)
    except Exception:
        return []
    return [str(column).strip() for column in dataframe.columns]


def _schema_flags_from_row(row: Any) -> tuple[bool, bool]:
    if isinstance(row, Mapping):
        keys = {str(key).lower() for key in row.keys()}
        has_timestamp = bool({"timestamp", "date", "datetime", "time"} & keys)
        has_ohlcv = {"open", "high", "low", "close", "volume"}.issubset(keys)
        return has_timestamp, has_ohlcv
    if isinstance(row, list):
        return len(row) >= 1, len(row) >= 6
    return False, False


def _inspect_file_schema(path: Path, file_format: str) -> dict[str, Any]:
    has_timestamp = False
    has_ohlcv = False
    no_obvious_empty_file = path.exists() and path.stat().st_size > 0

    if file_format == "json":
        has_timestamp, has_ohlcv = _schema_flags_from_row(_read_first_json_row(path))
    elif file_format == "jsonl":
        has_timestamp, has_ohlcv = _schema_flags_from_row(_read_first_jsonl_row(path))
    elif file_format == "csv":
        columns = {column.lower() for column in _read_csv_columns(path)}
        has_timestamp = bool({"timestamp", "date", "datetime", "time"} & columns)
        has_ohlcv = {"open", "high", "low", "close", "volume"}.issubset(columns)
    elif file_format == "feather":
        columns = {column.lower() for column in _read_pandas_columns(path, "read_feather")}
        has_timestamp = bool({"timestamp", "date", "datetime", "time"} & columns)
        has_ohlcv = {"open", "high", "low", "close", "volume"}.issubset(columns)
    elif file_format == "parquet":
        columns = {column.lower() for column in _read_pandas_columns(path, "read_parquet")}
        has_timestamp = bool({"timestamp", "date", "datetime", "time"} & columns)
        has_ohlcv = {"open", "high", "low", "close", "volume"}.issubset(columns)

    return {
        "has_timestamp_column": has_timestamp,
        "has_ohlcv_columns": has_ohlcv,
        "no_obvious_empty_file": no_obvious_empty_file,
    }


def _discover_candidate_files(
    data_dir: Path,
    symbol: str,
    required_timeframes: list[str],
) -> list[dict[str, Any]]:
    if not data_dir.exists() or not data_dir.is_dir():
        return []

    candidates: list[dict[str, Any]] = []
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        pair, timeframe = infer_pair_timeframe_from_path(path)
        if pair != symbol or timeframe not in required_timeframes:
            continue
        file_format = detect_data_file_format(path)
        accepted = file_format in ACCEPTED_FORMATS
        candidates.append(
            {
                "path": str(path),
                "pair": pair,
                "timeframe": timeframe,
                "detected_format": file_format,
                "accepted_format": accepted,
            }
        )
    return candidates


def _entry_lookup(manifest: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    entries: dict[tuple[str, str], Mapping[str, Any]] = {}
    for entry in manifest.get("pair_timeframes") or []:
        if not isinstance(entry, Mapping):
            continue
        pair = str(entry.get("pair", ""))
        timeframe = str(entry.get("timeframe", ""))
        entries[(pair, timeframe)] = entry
    return entries


def _requirement_error(code: str, **details: Any) -> dict[str, Any]:
    return {"code": code, **details}


def load_offline_data_requirements(path: str | Path) -> dict[str, Any]:
    """Load offline data pair/timeframe requirements from a JSON object file."""

    requirements_path = Path(path)
    if not requirements_path.exists():
        raise FileNotFoundError(requirements_path)
    try:
        payload = json.loads(requirements_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("requirements_json_invalid") from exc
    if not isinstance(payload, dict):
        raise ValueError("requirements_json_must_be_object")
    return payload


def extract_data_gate_error_codes(errors: list[Any]) -> list[str]:
    """Return stable machine-readable codes from mixed string/dict gate errors."""

    codes: list[str] = []
    for error in errors:
        if isinstance(error, Mapping):
            code = error.get("code")
            codes.append(str(code or "unknown_error"))
        else:
            codes.append(str(error))
    return codes


def _is_safe_relative_dataset_path(path_value: str) -> bool:
    dataset_path = Path(path_value)
    if dataset_path.is_absolute():
        return False
    if re.match(r"^[A-Za-z]:[\\/]", path_value):
        return False
    return ".." not in dataset_path.parts


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _normalize_requirements(requirements: Mapping[str, Any] | None) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    if requirements is None:
        return [], [], []
    if not isinstance(requirements, Mapping):
        return [], [], [_requirement_error("requirements_invalid")]

    pairs = requirements.get("pairs")
    timeframes = requirements.get("timeframes")
    errors: list[dict[str, Any]] = []

    if not isinstance(pairs, list):
        errors.append(_requirement_error("requirements_invalid", field="pairs"))
        pairs_list: list[str] = []
    else:
        pairs_list = []
        for pair in pairs:
            normalized_pair = normalize_pair_symbol(pair)
            if normalized_pair is None:
                errors.append(_requirement_error("requirements_pair_invalid", pair=str(pair)))
                continue
            pairs_list.append(normalized_pair)
        if not pairs:
            errors.append(_requirement_error("requirements_pairs_empty"))

    if not isinstance(timeframes, list):
        errors.append(_requirement_error("requirements_invalid", field="timeframes"))
        timeframes_list: list[str] = []
    else:
        timeframes_list = []
        for timeframe in timeframes:
            normalized_timeframe = normalize_timeframe(timeframe)
            if normalized_timeframe is None:
                errors.append(
                    _requirement_error("requirements_timeframe_invalid", timeframe=str(timeframe))
                )
                continue
            timeframes_list.append(normalized_timeframe)
        if not timeframes_list:
            errors.append(_requirement_error("requirements_timeframes_empty"))

    return pairs_list, timeframes_list, errors


def _normalize_requirement_date_range(
    requirements: Mapping[str, Any] | None,
) -> tuple[datetime | None, datetime | None, list[dict[str, Any]]]:
    if not isinstance(requirements, Mapping):
        return None, None, []
    start_value = requirements.get("start")
    end_value = requirements.get("end")
    errors: list[dict[str, Any]] = []
    start = _parse_iso_datetime(start_value) if start_value is not None else None
    end = _parse_iso_datetime(end_value) if end_value is not None else None
    if start_value is not None and start is None:
        errors.append(_requirement_error("requirements_start_invalid"))
    if end_value is not None and end is None:
        errors.append(_requirement_error("requirements_end_invalid"))
    if start is not None and end is not None and start > end:
        errors.append(_requirement_error("requirements_date_range_invalid"))
    return start, end, errors


def check_manifest_requirements(
    manifest: Mapping[str, Any],
    requirements: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check required pair/timeframe coverage using inventory manifest metadata."""

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if requirements is None:
        return {"ok": True, "errors": errors, "error_codes": [], "warnings": warnings}
    if not isinstance(manifest, Mapping):
        errors = [_requirement_error("manifest_not_mapping")]
        return {
            "ok": False,
            "errors": errors,
            "error_codes": extract_data_gate_error_codes(errors),
            "warnings": warnings,
        }

    pairs, timeframes, requirement_errors = _normalize_requirements(requirements)
    required_start, required_end, date_requirement_errors = _normalize_requirement_date_range(requirements)
    requirement_errors.extend(date_requirement_errors)
    errors.extend(requirement_errors)
    if requirement_errors:
        return sanitize_mapping(
            {
                "ok": False,
                "errors": errors,
                "error_codes": extract_data_gate_error_codes(errors),
                "warnings": warnings,
            }
        )

    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        errors.append(_requirement_error("datasets_not_list"))
        return sanitize_mapping(
            {
                "ok": False,
                "errors": errors,
                "error_codes": extract_data_gate_error_codes(errors),
                "warnings": warnings,
            }
        )

    available: set[tuple[str, str]] = set()
    counts: dict[tuple[str, str], int] = {}
    datasets_by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for dataset in datasets:
        if not isinstance(dataset, Mapping):
            continue
        pair = dataset.get("pair")
        timeframe = dataset.get("timeframe")
        if isinstance(pair, str) and isinstance(timeframe, str):
            available.add((pair, timeframe))
            counts[(pair, timeframe)] = counts.get((pair, timeframe), 0) + 1
            datasets_by_key.setdefault((pair, timeframe), []).append(dataset)

    for pair in pairs:
        for timeframe in timeframes:
            if (pair, timeframe) not in available:
                errors.append(
                    _requirement_error(
                        "missing_required_dataset",
                        pair=pair,
                        timeframe=timeframe,
                    )
                )
            elif counts.get((pair, timeframe), 0) > 1:
                warnings.append(
                    _requirement_error(
                        "duplicate_dataset_coverage",
                        pair=pair,
                        timeframe=timeframe,
                        count=counts[(pair, timeframe)],
                    )
                )
            elif required_start is not None or required_end is not None:
                dataset = datasets_by_key[(pair, timeframe)][0]
                dataset_start = _parse_iso_datetime(dataset.get("start"))
                dataset_end = _parse_iso_datetime(dataset.get("end"))
                if dataset_start is None or dataset_end is None:
                    errors.append(
                        _requirement_error(
                            "dataset_date_range_missing",
                            pair=pair,
                            timeframe=timeframe,
                        )
                    )
                elif required_start is not None and dataset_start > required_start:
                    errors.append(
                        _requirement_error(
                            "dataset_starts_too_late",
                            pair=pair,
                            timeframe=timeframe,
                        )
                    )
                elif required_end is not None and dataset_end < required_end:
                    errors.append(
                        _requirement_error(
                            "dataset_ends_too_early",
                            pair=pair,
                            timeframe=timeframe,
                        )
                    )

    return sanitize_mapping(
        {
            "ok": not errors,
            "errors": errors,
            "error_codes": extract_data_gate_error_codes(errors),
            "warnings": warnings,
        }
    )


def build_requirements_coverage_matrix(
    manifest: Mapping[str, Any],
    requirements: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a sorted pair x timeframe coverage matrix from manifest metadata."""

    if not isinstance(manifest, Mapping):
        return {
            "ok": False,
            "errors": [_requirement_error("manifest_not_mapping")],
            "pairs": [],
            "timeframes": [],
            "matrix": [],
        }

    pairs, timeframes, requirement_errors = _normalize_requirements(requirements)
    if requirement_errors:
        return sanitize_mapping(
            {
                "ok": False,
                "errors": requirement_errors,
                "pairs": [],
                "timeframes": [],
                "matrix": [],
            }
        )

    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        return {
            "ok": False,
            "errors": [_requirement_error("datasets_not_list")],
            "pairs": [],
            "timeframes": [],
            "matrix": [],
        }

    available: set[tuple[str, str]] = set()
    for dataset in datasets:
        if not isinstance(dataset, Mapping):
            continue
        pair = dataset.get("pair")
        timeframe = dataset.get("timeframe")
        if isinstance(pair, str) and isinstance(timeframe, str):
            available.add((pair, timeframe))

    sorted_pairs = sorted(set(pairs))
    sorted_timeframes = sorted(set(timeframes))
    matrix = []
    for pair in sorted_pairs:
        cells = []
        for timeframe in sorted_timeframes:
            present = (pair, timeframe) in available
            cells.append({"timeframe": timeframe, "status": "present" if present else "missing"})
        matrix.append({"pair": pair, "cells": cells})

    return sanitize_mapping(
        {
            "ok": True,
            "errors": [],
            "pairs": sorted_pairs,
            "timeframes": sorted_timeframes,
            "matrix": matrix,
        }
    )


def run_inventory_manifest_gate(
    manifest: Mapping[str, Any],
    requirements: Mapping[str, Any] | None = None,
    *,
    min_candles_per_dataset: int | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Validate an inventory-generated manifest without reading dataset contents."""

    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(manifest, Mapping):
        errors = ["manifest_not_mapping"]
        return {
            "ok": False,
            "errors": errors,
            "error_codes": extract_data_gate_error_codes(errors),
            "warnings": warnings,
        }

    datasets = manifest.get("datasets")
    if not isinstance(datasets, list):
        errors = ["datasets_not_list"]
        return {
            "ok": False,
            "errors": errors,
            "error_codes": extract_data_gate_error_codes(errors),
            "warnings": warnings,
        }
    if not datasets:
        coverage = check_manifest_requirements(manifest, requirements)
        coverage_matrix = (
            build_requirements_coverage_matrix(manifest, requirements)
            if requirements is not None
            else None
        )
        return sanitize_mapping(
            {
                "ok": False,
                "errors": ["datasets_empty", *coverage["errors"]],
                "error_codes": extract_data_gate_error_codes(
                    ["datasets_empty", *coverage["errors"]]
                ),
                "warnings": [*warnings, *coverage["warnings"]],
                "requirements": coverage,
                "coverage_matrix": coverage_matrix,
            }
        )

    root_value = manifest.get("root")
    root_path = Path(str(root_value)).resolve() if root_value else None

    for index, dataset in enumerate(datasets):
        if not isinstance(dataset, Mapping):
            errors.append(f"datasets[{index}].not_mapping")
            continue

        path_value = dataset.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"datasets[{index}].path_missing")
            continue

        dataset_path = Path(path_value)
        path_is_safe = _is_safe_relative_dataset_path(path_value)
        if not path_is_safe:
            errors.append(f"datasets[{index}].dataset_path_unsafe")

        file_format = dataset.get("format")
        if file_format not in ACCEPTED_FORMATS:
            errors.append(f"datasets[{index}].format_unsupported")

        size_bytes = dataset.get("size_bytes")
        if not isinstance(size_bytes, int) or size_bytes <= 0:
            errors.append(f"datasets[{index}].size_bytes_not_positive")

        pair = dataset.get("pair")
        if pair is not None and not (
            isinstance(pair, str) and INVENTORY_PAIR_RE.match(pair)
        ):
            errors.append(f"datasets[{index}].pair_invalid")

        timeframe = dataset.get("timeframe")
        if timeframe is not None and not (
            isinstance(timeframe, str) and INVENTORY_TIMEFRAME_RE.match(timeframe)
        ):
            errors.append(f"datasets[{index}].timeframe_invalid")

        if strict and (pair is None or timeframe is None):
            errors.append(f"datasets[{index}].pair_timeframe_unknown")

        probe = dataset.get("probe")
        row_count: Any = dataset.get("row_count")
        if isinstance(probe, Mapping):
            if probe.get("has_ohlcv_columns") is False:
                errors.append(f"datasets[{index}].probe_missing_ohlcv_columns")
            row_count = probe.get("row_count_estimate", row_count)

        if min_candles_per_dataset is not None:
            if not isinstance(row_count, int):
                warnings.append(f"datasets[{index}].row_count_unknown")
            elif row_count < min_candles_per_dataset:
                errors.append(f"datasets[{index}].row_count_below_minimum")

        start = dataset.get("start")
        end = dataset.get("end")
        parsed_start = _parse_iso_datetime(start) if start is not None else None
        parsed_end = _parse_iso_datetime(end) if end is not None else None
        if start is not None and parsed_start is None:
            errors.append(f"datasets[{index}].start_date_invalid")
        if end is not None and parsed_end is None:
            errors.append(f"datasets[{index}].end_date_invalid")
        if parsed_start is not None and parsed_end is not None and parsed_start > parsed_end:
            errors.append(f"datasets[{index}].date_range_invalid")

        if root_path is not None and path_is_safe:
            full_path = root_path / dataset_path
            if not full_path.exists():
                errors.append(f"datasets[{index}].file_missing")
            elif full_path.stat().st_size <= 0:
                errors.append(f"datasets[{index}].file_empty")

    coverage = check_manifest_requirements(manifest, requirements)
    coverage_matrix = (
        build_requirements_coverage_matrix(manifest, requirements)
        if requirements is not None
        else None
    )
    strict_duplicate_errors: list[Any] = []
    if strict:
        strict_duplicate_errors = [
            {**warning, "code": "duplicate_dataset_coverage"}
            for warning in coverage["warnings"]
            if isinstance(warning, Mapping) and warning.get("code") == "duplicate_dataset_coverage"
        ]
    combined_errors: list[Any] = [*errors, *coverage["errors"], *strict_duplicate_errors]
    combined_warnings: list[Any] = [*warnings, *coverage["warnings"]]
    return sanitize_mapping(
        {
            "ok": not combined_errors,
            "errors": combined_errors,
            "error_codes": extract_data_gate_error_codes(combined_errors),
            "warnings": combined_warnings,
            "requirements": coverage,
            "coverage_matrix": coverage_matrix,
        }
    )


def run_offline_data_gate(
    data_dir: str | Path = "user_data/data",
    symbol: str = DEFAULT_SYMBOL,
    required_timeframes: list[str] | None = None,
    min_candles_per_pair_timeframe: int = DEFAULT_MIN_CANDLES,
) -> dict[str, Any]:
    """Evaluate whether local files satisfy the minimum offline data contract."""

    resolved_data_dir = _resolve_path(data_dir)
    normalized_symbol = normalize_pair_symbol(symbol)
    if normalized_symbol is None:
        return sanitize_mapping(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "FAIL",
                "allowed_for_evaluation": False,
                "symbol": symbol,
                "required_timeframes": _normalize_required_timeframes(required_timeframes),
                "detected_files": [],
                "missing_timeframes": [],
                "format_checks": {"accepted_format": False, "detected_format": None},
                "quality_checks": {},
                "blocked_reasons": ["invalid_symbol"],
                "safe_next_action": "prepare_offline_data_files",
                "readOnly": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    raw_timeframes = list(required_timeframes or DEFAULT_REQUIRED_TIMEFRAMES)
    invalid_timeframes = [
        str(item) for item in raw_timeframes if normalize_timeframe(item) is None
    ]
    timeframes = _normalize_required_timeframes(raw_timeframes)
    if invalid_timeframes:
        return sanitize_mapping(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "FAIL",
                "allowed_for_evaluation": False,
                "symbol": normalized_symbol,
                "required_timeframes": raw_timeframes,
                "detected_files": [],
                "missing_timeframes": [],
                "format_checks": {"accepted_format": False, "detected_format": None},
                "quality_checks": {},
                "blocked_reasons": ["invalid_timeframe"],
                "invalid_timeframes": invalid_timeframes,
                "safe_next_action": "prepare_offline_data_files",
                "readOnly": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    detected_files = _discover_candidate_files(resolved_data_dir, normalized_symbol, timeframes)
    accepted_files = [item for item in detected_files if item["accepted_format"]]
    unsupported_files = [item for item in detected_files if not item["accepted_format"]]

    manifest = build_offline_data_manifest(
        str(resolved_data_dir),
        pairs=[normalized_symbol],
        timeframes=timeframes,
        write_report=False,
    )
    entries_by_key = _entry_lookup(manifest)

    missing_timeframes: list[str] = []
    blocked_reasons: list[str] = []
    partial_reasons: list[str] = []
    schema_checks: list[dict[str, Any]] = []

    if not resolved_data_dir.exists():
        blocked_reasons.append("data_dir_not_found")
    elif not any(resolved_data_dir.iterdir()):
        blocked_reasons.append("no_data_files_found")

    for timeframe in timeframes:
        accepted_for_timeframe = [
            item for item in accepted_files if item["timeframe"] == timeframe
        ]
        unsupported_for_timeframe = [
            item for item in unsupported_files if item["timeframe"] == timeframe
        ]
        if not accepted_for_timeframe:
            missing_timeframes.append(timeframe)
            if unsupported_for_timeframe:
                blocked_reasons.append("unsupported_format")
            continue

        selected_file = Path(str(accepted_for_timeframe[0]["path"]))
        file_format = str(accepted_for_timeframe[0]["detected_format"])
        schema = _inspect_file_schema(selected_file, file_format)
        entry = entries_by_key.get((normalized_symbol, timeframe), {})
        row_count = int(entry.get("row_count", 0) or 0)
        missing_ohlc_count = int(entry.get("missing_ohlc_count", 0) or 0)
        invalid_ohlc_count = int(entry.get("invalid_ohlc_count", 0) or 0)

        row_count_ok = row_count >= int(min_candles_per_pair_timeframe)
        quality = {
            "timeframe": timeframe,
            "file": str(selected_file),
            "detected_format": file_format,
            "has_timestamp_column": bool(schema["has_timestamp_column"]),
            "has_ohlcv_columns": bool(schema["has_ohlcv_columns"]),
            "row_count": row_count,
            "row_count_ok": row_count_ok,
            "no_obvious_empty_file": bool(schema["no_obvious_empty_file"]) and row_count > 0,
            "missing_ohlc_count": missing_ohlc_count,
            "invalid_ohlc_count": invalid_ohlc_count,
        }
        schema_checks.append(quality)

        if not quality["no_obvious_empty_file"]:
            partial_reasons.append("empty_file")
        if not quality["has_timestamp_column"]:
            partial_reasons.append("missing_timestamp_column")
        if not quality["has_ohlcv_columns"]:
            partial_reasons.append("missing_ohlcv_columns")
        if not row_count_ok:
            partial_reasons.append("low_candle_count")
        if missing_ohlc_count:
            partial_reasons.append("missing_ohlc")
        if invalid_ohlc_count:
            partial_reasons.append("invalid_ohlc")

    if missing_timeframes:
        blocked_reasons.append("missing_timeframe")

    unique_blocked_reasons = sorted(set(blocked_reasons))
    unique_partial_reasons = sorted(set(partial_reasons))

    status = "READY"
    if unique_blocked_reasons:
        status = "FAIL"
    elif unique_partial_reasons:
        status = "PARTIAL"

    detected_formats = sorted(
        {
            str(item["detected_format"])
            for item in accepted_files
            if item.get("detected_format")
        }
    )

    result = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "allowed_for_evaluation": status == "READY",
        "symbol": normalized_symbol,
        "required_timeframes": timeframes,
        "min_candles_per_pair_timeframe": int(min_candles_per_pair_timeframe),
        "data_dir": str(resolved_data_dir),
        "detected_files": detected_files,
        "missing_timeframes": missing_timeframes,
        "format_checks": {
            "accepted_format": len(accepted_files) >= len(timeframes) and not unsupported_files,
            "detected_format": detected_formats[0] if len(detected_formats) == 1 else None,
            "detected_formats": detected_formats,
            "unsupported_files": unsupported_files,
        },
        "quality_checks": {
            "has_timestamp_column": bool(schema_checks)
            and all(item["has_timestamp_column"] for item in schema_checks),
            "has_ohlcv_columns": bool(schema_checks)
            and all(item["has_ohlcv_columns"] for item in schema_checks),
            "row_count_ok": bool(schema_checks)
            and all(item["row_count_ok"] for item in schema_checks),
            "no_obvious_empty_file": bool(schema_checks)
            and all(item["no_obvious_empty_file"] for item in schema_checks),
            "per_timeframe": schema_checks,
        },
        "blocked_reasons": unique_blocked_reasons or unique_partial_reasons,
        "safe_next_action": "ready_for_preflight" if status == "READY" else "prepare_offline_data_files",
        "manifest_status": manifest.get("status"),
        "readOnly": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return sanitize_mapping(result)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the read-only Bollinger Evolver offline data gate.",
    )
    parser.add_argument("--data-dir", default="user_data/data")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=DEFAULT_REQUIRED_TIMEFRAMES,
        help="Required timeframes, default: 15m 1h 4h",
    )
    parser.add_argument("--min-candles", type=int, default=DEFAULT_MIN_CANDLES)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    result = run_offline_data_gate(
        data_dir=args.data_dir,
        symbol=args.symbol,
        required_timeframes=list(args.timeframes),
        min_candles_per_pair_timeframe=args.min_candles,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
