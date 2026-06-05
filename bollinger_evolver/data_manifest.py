"""Offline local data manifest builder for Bollinger Evolver readiness checks."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from bollinger_evolver.data_quality import evaluate_data_coverage_gate
from bollinger_evolver.evaluators import sanitize_mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".runtime" / "bollinger_evolver" / "data_manifests"
SUPPORTED_SUFFIXES = {".json", ".jsonl", ".csv", ".feather", ".parquet"}
TIMEFRAME_MS = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
    "1w": 7 * 24 * 60 * 60_000,
    "1M": 30 * 24 * 60 * 60_000,
}
TIMEFRAME_ORDER = tuple(TIMEFRAME_MS.keys())
DEFAULT_MIN_CANDLES = 100


def _resolve_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def _coerce_timestamp_ms(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
    else:
        text = str(value).strip()
        if not text:
            return None
        try:
            timestamp = float(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                return int(parsed.timestamp() * 1000)
            except ValueError:
                return None
    if timestamp > 10_000_000_000:
        return int(timestamp)
    return int(timestamp * 1000)


def _isoformat_ms(timestamp_ms: int | None) -> str | None:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def _extract_candle_from_mapping(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": (
            row.get("timestamp")
            or row.get("date")
            or row.get("datetime")
            or row.get("time")
        ),
        "open": row.get("open"),
        "high": row.get("high"),
        "low": row.get("low"),
        "close": row.get("close"),
        "volume": row.get("volume"),
    }


def _extract_candle(row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return {key: _normalize_scalar(value) for key, value in _extract_candle_from_mapping(row).items()}
    if isinstance(row, list) and len(row) >= 6:
        return {
            "timestamp": _normalize_scalar(row[0]),
            "open": _normalize_scalar(row[1]),
            "high": _normalize_scalar(row[2]),
            "low": _normalize_scalar(row[3]),
            "close": _normalize_scalar(row[4]),
            "volume": _normalize_scalar(row[5]),
        }
    if isinstance(row, list) and len(row) >= 5:
        return {
            "timestamp": _normalize_scalar(row[0]),
            "open": _normalize_scalar(row[1]),
            "high": _normalize_scalar(row[2]),
            "low": _normalize_scalar(row[3]),
            "close": _normalize_scalar(row[4]),
            "volume": None,
        }
    return {
        "timestamp": None,
        "open": None,
        "high": None,
        "low": None,
        "close": None,
        "volume": None,
    }


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _missing_ohlc(candle: Mapping[str, Any]) -> bool:
    return any(candle.get(field) in (None, "") for field in ("open", "high", "low", "close"))


def _invalid_ohlc(candle: Mapping[str, Any]) -> bool:
    open_price = _coerce_float(candle.get("open"))
    high_price = _coerce_float(candle.get("high"))
    low_price = _coerce_float(candle.get("low"))
    close_price = _coerce_float(candle.get("close"))
    if None in {open_price, high_price, low_price, close_price}:
        return True
    if high_price < low_price:
        return True
    if high_price < max(open_price, close_price):
        return True
    if low_price > min(open_price, close_price):
        return True
    return False


def detect_data_file_format(path: str | Path) -> str:
    file_path = Path(path)
    suffixes = [suffix.lower() for suffix in file_path.suffixes]
    if not suffixes:
        return "unknown"
    if suffixes[-1] == ".json":
        return "json"
    if suffixes[-1] == ".jsonl":
        return "jsonl"
    if suffixes[-1] == ".csv":
        return "csv"
    if suffixes[-1] == ".feather":
        return "feather"
    if suffixes[-1] == ".parquet":
        return "parquet"
    return "unknown"


def _parse_json_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [_extract_candle(row) for row in data]


def _parse_jsonl_file(path: Path) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            candles.append(_extract_candle(json.loads(text)))
    return candles


def _parse_csv_file(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [_extract_candle(row) for row in reader]


def _parse_pandas_file(path: Path, loader_name: str) -> list[dict[str, Any]]:
    try:
        import pandas as pd
    except Exception:
        return []
    loader = getattr(pd, loader_name, None)
    if loader is None:
        return []
    dataframe = loader(path)
    return [_extract_candle(record) for record in dataframe.to_dict("records")]


def parse_candles_from_file(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    file_format = detect_data_file_format(file_path)
    if file_format == "json":
        return _parse_json_file(file_path)
    if file_format == "jsonl":
        return _parse_jsonl_file(file_path)
    if file_format == "csv":
        return _parse_csv_file(file_path)
    if file_format == "feather":
        return _parse_pandas_file(file_path, "read_feather")
    if file_format == "parquet":
        return _parse_pandas_file(file_path, "read_parquet")
    return []


def _normalize_pair_token(token: str) -> str | None:
    clean = token.strip().replace(":", "_")
    if not clean:
        return None
    for separator in ("_", "-"):
        if separator in clean:
            left, right = clean.split(separator, 1)
            if left and right:
                return f"{left.upper()}/{right.upper()}"
    return None


def infer_pair_timeframe_from_path(path: str | Path) -> tuple[str | None, str | None]:
    file_path = Path(path)
    searchable_parts: list[str] = [file_path.stem]
    searchable_parts.extend(parent.name for parent in file_path.parents if parent.name)

    timeframe: str | None = None
    pair: str | None = None

    for part in searchable_parts:
        lowered = part.lower()
        for candidate in TIMEFRAME_ORDER:
            if lowered.endswith(f"-{candidate.lower()}") or lowered.endswith(f"_{candidate.lower()}"):
                timeframe = candidate
                pair_token = part[: -(len(candidate) + 1)]
                pair = _normalize_pair_token(pair_token)
                if pair is not None:
                    return pair, timeframe
            if lowered == candidate.lower():
                timeframe = candidate

    if timeframe is None:
        for part in searchable_parts:
            lowered = part.lower()
            for candidate in TIMEFRAME_ORDER:
                if candidate.lower() in lowered:
                    timeframe = candidate
                    break
            if timeframe:
                break

    if pair is None:
        for part in searchable_parts:
            inferred = _normalize_pair_token(part)
            if inferred is not None:
                pair = inferred
                break

    return pair, timeframe


def analyze_candles(candles: list[dict[str, Any]], timeframe: str | None = None) -> dict[str, Any]:
    timestamps: list[int] = []
    duplicate_timestamp_count = 0
    out_of_order_count = 0
    missing_ohlc_count = 0
    invalid_ohlc_count = 0
    previous_timestamp: int | None = None
    seen: set[int] = set()

    for candle in candles:
        timestamp_ms = _coerce_timestamp_ms(candle.get("timestamp"))
        if timestamp_ms is not None:
            if previous_timestamp is not None and timestamp_ms < previous_timestamp:
                out_of_order_count += 1
            previous_timestamp = timestamp_ms
            if timestamp_ms in seen:
                duplicate_timestamp_count += 1
            else:
                seen.add(timestamp_ms)
            timestamps.append(timestamp_ms)

        if _missing_ohlc(candle):
            missing_ohlc_count += 1
            invalid_ohlc_count += 1
        elif _invalid_ohlc(candle):
            invalid_ohlc_count += 1

    unique_sorted = sorted(seen)
    expected_ms = TIMEFRAME_MS.get(timeframe or "")
    gap_count = 0
    largest_gap_ms = 0
    if expected_ms and len(unique_sorted) >= 2:
        for earlier, later in zip(unique_sorted, unique_sorted[1:]):
            gap_ms = later - earlier
            if gap_ms > expected_ms:
                gap_count += 1
                if gap_ms > largest_gap_ms:
                    largest_gap_ms = gap_ms

    candle_count = len(candles)
    gap_ratio = gap_count / max(candle_count, 1)
    status = "PASS"
    if invalid_ohlc_count or missing_ohlc_count:
        status = "FAIL"
    elif duplicate_timestamp_count or out_of_order_count or gap_count:
        status = "WARN"

    return {
        "candle_count": candle_count,
        "row_count": candle_count,
        "min_timestamp": _isoformat_ms(min(unique_sorted) if unique_sorted else None),
        "max_timestamp": _isoformat_ms(max(unique_sorted) if unique_sorted else None),
        "duplicate_timestamp_count": duplicate_timestamp_count,
        "out_of_order_count": out_of_order_count,
        "missing_ohlc_count": missing_ohlc_count,
        "invalid_ohlc_count": invalid_ohlc_count,
        "gap_count": gap_count,
        "largest_gap_ms": largest_gap_ms,
        "gap_ratio": gap_ratio,
        "status": status,
    }


def _entry_from_missing(pair: str, timeframe: str) -> dict[str, Any]:
    return {
        "pair": pair,
        "timeframe": timeframe,
        "status": "missing",
        "file": None,
        "row_count": 0,
        "gap_count": 0,
        "invalid_ohlc_count": 0,
    }


def _manifest_status(entries: list[dict[str, Any]], errors: list[str]) -> str:
    if errors:
        return "FAIL"
    if not entries:
        return "EMPTY"
    statuses = {entry["status"] for entry in entries}
    if statuses == {"missing"}:
        return "EMPTY"
    if "limited" in statuses or "missing" in statuses:
        return "WARN"
    return "PASS"


def _collect_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and detect_data_file_format(path) in {"json", "jsonl", "csv", "feather", "parquet"}:
            files.append(path)
    return sorted(files)


def _markdown_report(manifest: Mapping[str, Any]) -> str:
    lines = [
        "# Offline Data Manifest Coverage Report",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Data dir: `{manifest['data_dir']}`",
        f"- Pair/timeframe count: `{manifest['coverage_summary']['pair_timeframe_count']}`",
        "",
        "## Coverage",
    ]
    for item in manifest["pair_timeframes"]:
        lines.extend(
            [
                f"- `{item['pair']}` `{item['timeframe']}`: `{item['status']}`",
                f"  - candles: `{item['candle_count']}`",
                f"  - invalid_ohlc_count: `{item['invalid_ohlc_count']}`",
                f"  - gap_count: `{item['gap_count']}`",
            ]
        )
    if manifest["warnings"]:
        lines.extend(["", "## Warnings", *[f"- {warning}" for warning in manifest["warnings"]]])
    if manifest["errors"]:
        lines.extend(["", "## Errors", *[f"- {error}" for error in manifest["errors"]]])
    return "\n".join(lines) + "\n"


def build_offline_data_manifest(
    data_dir: str,
    pairs: list[str] | None = None,
    timeframes: list[str] | None = None,
    output_dir: str | None = ".runtime/bollinger_evolver/data_manifests",
    write_report: bool = True,
) -> dict[str, Any]:
    resolved_data_dir = _resolve_path(data_dir)
    resolved_output_dir = _resolve_path(output_dir) if output_dir is not None else None
    requested_pairs = list(pairs or [])
    requested_timeframes = list(timeframes or [])
    warnings: list[str] = []
    errors: list[str] = []

    if resolved_data_dir is None or not resolved_data_dir.exists():
        result = {
            "status": "FAIL",
            "readOnly": True,
            "data_dir": str(resolved_data_dir) if resolved_data_dir else str(data_dir),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pairs_requested": requested_pairs,
            "timeframes_requested": requested_timeframes,
            "pairs_found": [],
            "timeframes_found": [],
            "pair_timeframes": [],
            "entries": [],
            "coverage_summary": {
                "pair_timeframe_count": 0,
                "missing_pair_timeframes": [],
                "low_candle_count": [],
                "gap_issues": [],
                "invalid_ohlc_issues": [],
            },
            "manifest_path": None,
            "markdown_path": None,
            "warnings": [],
            "errors": ["data_dir_not_found"],
        }
        return sanitize_mapping(result)

    files = _collect_files(resolved_data_dir)
    if not files:
        result = {
            "status": "EMPTY",
            "readOnly": True,
            "data_dir": str(resolved_data_dir),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pairs_requested": requested_pairs,
            "timeframes_requested": requested_timeframes,
            "pairs_found": [],
            "timeframes_found": [],
            "pair_timeframes": [],
            "entries": [],
            "coverage_summary": {
                "pair_timeframe_count": 0,
                "missing_pair_timeframes": [],
                "low_candle_count": [],
                "gap_issues": [],
                "invalid_ohlc_issues": [],
            },
            "manifest_path": None,
            "markdown_path": None,
            "warnings": ["no_data_files_found"],
            "errors": [],
        }
        return sanitize_mapping(result)

    pair_timeframes: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    pairs_found: set[str] = set()
    timeframes_found: set[str] = set()
    found_keys: set[tuple[str, str]] = set()
    low_candle_count: list[dict[str, Any]] = []
    gap_issues: list[dict[str, Any]] = []
    invalid_ohlc_issues: list[dict[str, Any]] = []

    for file_path in files:
        pair, timeframe = infer_pair_timeframe_from_path(file_path)
        if requested_pairs and pair not in requested_pairs:
            continue
        if requested_timeframes and timeframe not in requested_timeframes:
            continue

        file_format = detect_data_file_format(file_path)
        try:
            candles = parse_candles_from_file(file_path)
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"parse_failed:{file_path.name}:{type(exc).__name__}")
            candles = []
        analysis = analyze_candles(candles, timeframe=timeframe)
        normalized_pair = pair or "UNKNOWN"
        normalized_timeframe = timeframe or "unknown"
        pairs_found.add(normalized_pair)
        timeframes_found.add(normalized_timeframe)
        found_keys.add((normalized_pair, normalized_timeframe))

        if analysis["candle_count"] < DEFAULT_MIN_CANDLES:
            low_candle_count.append(
                {
                    "pair": normalized_pair,
                    "timeframe": normalized_timeframe,
                    "row_count": analysis["candle_count"],
                }
            )
        if analysis["gap_count"] > 0:
            gap_issues.append(
                {
                    "pair": normalized_pair,
                    "timeframe": normalized_timeframe,
                    "gap_count": analysis["gap_count"],
                    "gap_ratio": analysis["gap_ratio"],
                }
            )
        if analysis["invalid_ohlc_count"] > 0:
            invalid_ohlc_issues.append(
                {
                    "pair": normalized_pair,
                    "timeframe": normalized_timeframe,
                    "invalid_ohlc_count": analysis["invalid_ohlc_count"],
                }
            )

        pair_timeframe_entry = {
            "pair": normalized_pair,
            "timeframe": normalized_timeframe,
            "file_path": str(file_path),
            "file_format": file_format,
            **analysis,
        }
        pair_timeframes.append(pair_timeframe_entry)
        entries.append(
            {
                "pair": normalized_pair,
                "timeframe": normalized_timeframe,
                "status": "ready" if analysis["status"] == "PASS" else "limited",
                "file": str(file_path),
                "row_count": analysis["row_count"],
                "gap_count": analysis["gap_count"],
                "invalid_ohlc_count": analysis["invalid_ohlc_count"],
            }
        )

    missing_pair_timeframes: list[dict[str, str]] = []
    for pair in requested_pairs:
        for timeframe in requested_timeframes:
            if (pair, timeframe) not in found_keys:
                missing_pair_timeframes.append({"pair": pair, "timeframe": timeframe})
                entries.append(_entry_from_missing(pair, timeframe))

    manifest_status = _manifest_status(entries, errors)
    if missing_pair_timeframes and manifest_status == "PASS":
        manifest_status = "WARN"

    manifest: dict[str, Any] = {
        "status": manifest_status,
        "readOnly": True,
        "data_dir": str(resolved_data_dir),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pairs_requested": requested_pairs,
        "timeframes_requested": requested_timeframes,
        "pairs_found": sorted(pairs_found),
        "timeframes_found": sorted(timeframes_found),
        "pair_timeframes": pair_timeframes,
        "entries": entries,
        "pairs": requested_pairs or sorted(pairs_found),
        "timeframes": requested_timeframes or sorted(
            timeframe for timeframe in timeframes_found if timeframe != "unknown"
        ),
        "coverage_summary": {
            "pair_timeframe_count": len(entries),
            "missing_pair_timeframes": missing_pair_timeframes,
            "low_candle_count": low_candle_count,
            "gap_issues": gap_issues,
            "invalid_ohlc_issues": invalid_ohlc_issues,
        },
        "manifest_path": None,
        "markdown_path": None,
        "warnings": warnings,
        "errors": errors,
    }

    if write_report and resolved_output_dir is not None:
        resolved_output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        manifest_path = resolved_output_dir / f"offline_data_manifest_{stamp}.json"
        markdown_path = resolved_output_dir / f"offline_data_manifest_{stamp}.md"
        manifest_path.write_text(json.dumps(sanitize_mapping(manifest), indent=2, sort_keys=True), encoding="utf-8")
        markdown_path.write_text(_markdown_report(manifest), encoding="utf-8")
        manifest["manifest_path"] = str(manifest_path)
        manifest["markdown_path"] = str(markdown_path)

    return sanitize_mapping(manifest)
