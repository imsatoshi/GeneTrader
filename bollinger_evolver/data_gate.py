"""Read-only offline data readiness gate for required Bollinger datasets."""

from __future__ import annotations

import argparse
import csv
import json
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
ACCEPTED_FORMATS = {"json", "jsonl", "csv", "feather", "parquet"}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (_project_root() / path).resolve()


def _normalize_required_timeframes(value: list[str] | tuple[str, ...] | None) -> list[str]:
    return list(value or DEFAULT_REQUIRED_TIMEFRAMES)


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


def run_offline_data_gate(
    data_dir: str | Path = "user_data/data",
    symbol: str = DEFAULT_SYMBOL,
    required_timeframes: list[str] | None = None,
    min_candles_per_pair_timeframe: int = DEFAULT_MIN_CANDLES,
) -> dict[str, Any]:
    """Evaluate whether local files satisfy the minimum offline data contract."""

    resolved_data_dir = _resolve_path(data_dir)
    timeframes = _normalize_required_timeframes(required_timeframes)
    detected_files = _discover_candidate_files(resolved_data_dir, symbol, timeframes)
    accepted_files = [item for item in detected_files if item["accepted_format"]]
    unsupported_files = [item for item in detected_files if not item["accepted_format"]]

    manifest = build_offline_data_manifest(
        str(resolved_data_dir),
        pairs=[symbol],
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
        entry = entries_by_key.get((symbol, timeframe), {})
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
        "symbol": symbol,
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
