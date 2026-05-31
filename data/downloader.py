import os
import sys
from pathlib import Path
import json

project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

import subprocess
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from config.settings import settings
from utils.logging_config import logger


MANIFEST_FILENAME = "data_coverage_manifest.json"
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


def _pair_file_stem(pair: str) -> str:
    return pair.replace("/", "_").replace(":", "_")


def _coerce_timestamp_ms(value: Any) -> Optional[int]:
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


def _extract_candle(row: Any) -> Dict[str, Any]:
    if isinstance(row, dict):
        return {
            "timestamp": row.get("date") or row.get("timestamp") or row.get("time"),
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
        }
    if isinstance(row, list) and len(row) >= 5:
        return {
            "timestamp": row[0],
            "open": row[1],
            "high": row[2],
            "low": row[3],
            "close": row[4],
        }
    return {"timestamp": None, "open": None, "high": None, "low": None, "close": None}


def _is_invalid_ohlc(candle: Dict[str, Any]) -> bool:
    try:
        open_price = float(candle["open"])
        high_price = float(candle["high"])
        low_price = float(candle["low"])
        close_price = float(candle["close"])
    except (TypeError, ValueError):
        return True
    if min(open_price, high_price, low_price, close_price) <= 0:
        return True
    return high_price < max(open_price, close_price, low_price) or low_price > min(open_price, close_price, high_price)


def find_data_file(data_dir: str, pair: str, timeframe: str) -> Optional[Path]:
    pair_stem = _pair_file_stem(pair)
    root = Path(data_dir)
    patterns = [
        f"{pair_stem}-{timeframe}.json",
        f"{pair_stem}-{timeframe}.json.gz",
        f"{pair_stem}-{timeframe}.feather",
        f"{pair_stem}-{timeframe}.parquet",
    ]
    for pattern in patterns:
        matches = sorted(root.rglob(pattern))
        if matches:
            return matches[0]
    matches = sorted(root.rglob(f"*{pair_stem}*{timeframe}*"))
    return matches[0] if matches else None


def analyze_ohlcv_json_file(path: Path, timeframe: str, start_date: Optional[date] = None) -> Dict[str, Any]:
    expected_ms = TIMEFRAME_MS.get(timeframe)
    analysis = {
        "row_count": 0,
        "min_timestamp": None,
        "max_timestamp": None,
        "gap_count": 0,
        "invalid_ohlc_count": 0,
        "covers_start_date": None,
        "parse_error": None,
    }
    if path.suffix not in {".json"}:
        analysis["parse_error"] = "coverage_details_unsupported_file_type"
        return analysis
    try:
        with open(path, "r", encoding="utf-8") as handle:
            rows = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        analysis["parse_error"] = str(exc)
        return analysis
    if not isinstance(rows, list):
        analysis["parse_error"] = "expected_json_list"
        return analysis

    timestamps: List[int] = []
    for row in rows:
        candle = _extract_candle(row)
        timestamp_ms = _coerce_timestamp_ms(candle["timestamp"])
        if timestamp_ms is not None:
            timestamps.append(timestamp_ms)
        if _is_invalid_ohlc(candle):
            analysis["invalid_ohlc_count"] += 1

    timestamps.sort()
    analysis["row_count"] = len(rows)
    if timestamps:
        analysis["min_timestamp"] = timestamps[0]
        analysis["max_timestamp"] = timestamps[-1]
        if expected_ms:
            for previous, current in zip(timestamps, timestamps[1:]):
                if current - previous > expected_ms * 1.5:
                    analysis["gap_count"] += 1
        if start_date:
            requested_start = datetime.combine(start_date, datetime.min.time(), timezone.utc)
            analysis["covers_start_date"] = timestamps[0] <= int(requested_start.timestamp() * 1000)
    return analysis


def build_coverage_manifest(
    config_file: str,
    data_dir: str,
    timeframes: List[str],
    start_date: Optional[date] = None,
) -> Dict[str, Any]:
    with open(config_file, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    pairs = config.get("exchange", {}).get("pair_whitelist", [])
    entries = []
    missing_count = 0
    limited_count = 0
    invalid_ohlc_count = 0
    gap_count = 0

    for pair in pairs:
        for timeframe in timeframes:
            data_file = find_data_file(data_dir, pair, timeframe)
            if data_file is None:
                missing_count += 1
                entries.append({
                    "pair": pair,
                    "timeframe": timeframe,
                    "status": "missing",
                    "file": None,
                    "row_count": 0,
                    "gap_count": 0,
                    "invalid_ohlc_count": 0,
                    "covers_start_date": None,
                })
                continue
            analysis = analyze_ohlcv_json_file(data_file, timeframe, start_date)
            invalid_ohlc_count += int(analysis["invalid_ohlc_count"])
            gap_count += int(analysis["gap_count"])
            status = "ready"
            if analysis["parse_error"]:
                status = "limited"
            if analysis["invalid_ohlc_count"] or analysis["gap_count"]:
                status = "limited"
            if analysis["covers_start_date"] is False:
                status = "limited"
            if status != "ready":
                limited_count += 1
            entries.append({
                "pair": pair,
                "timeframe": timeframe,
                "status": status,
                "file": str(data_file),
                **analysis,
            })

    total_expected = len(pairs) * len(timeframes)
    if total_expected == 0 or missing_count == total_expected:
        status = "missing"
    elif missing_count or limited_count or invalid_ohlc_count or gap_count:
        status = "partial"
    else:
        status = "ready"
    return {
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_start_date": start_date.isoformat() if start_date else None,
        "data_dir": str(Path(data_dir)),
        "pairs": pairs,
        "timeframes": timeframes,
        "expected_file_count": total_expected,
        "missing_count": missing_count,
        "limited_count": limited_count,
        "invalid_ohlc_count": invalid_ohlc_count,
        "gap_count": gap_count,
        "entries": entries,
    }


def write_coverage_manifest(manifest: Dict[str, Any], data_dir: str) -> Path:
    manifest_path = Path(data_dir) / MANIFEST_FILENAME
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    return manifest_path


def load_coverage_manifest(data_dir: str) -> Dict[str, Any]:
    manifest_path = Path(data_dir) / MANIFEST_FILENAME
    with open(manifest_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def coverage_manifest_is_ready(manifest: Dict[str, Any]) -> bool:
    return manifest.get("status") == "ready" and not manifest.get("missing_count")

class DataDownloader:
    def __init__(self):
        self.config_file = settings.config_file
        self.data_dir = settings.data_dir
        self.freqtrade_path = settings.freqtrade_path
        self.timeframes = ["1m", "5m", "15m", "1h", "4h", "1d", "1w", "1M"]

    def download_data(self, start_date: date):
        timerange = f"{start_date.strftime('%Y%m%d')}-"
        
        command = [
            self.freqtrade_path,
            "download-data",
            "--config", self.config_file,
            "--datadir", self.data_dir,
            "--timerange", timerange,
            "-t", *self.timeframes
        ]

        logger.info(f"Downloading data with command: {' '.join(command)}")
        
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            manifest = build_coverage_manifest(
                self.config_file,
                self.data_dir,
                self.timeframes,
                start_date,
            )
            write_coverage_manifest(manifest, self.data_dir)
            logger.info("Data download completed successfully")
            logger.info(f"Data coverage status: {manifest['status']}")
            logger.debug(result.stdout)
            return manifest
        except subprocess.CalledProcessError as e:
            logger.error(f"Error downloading data: {e}")
            logger.error(f"Command output: {e.output}")
            raise

def download_data(start_date: date):
    downloader = DataDownloader()
    return downloader.download_data(start_date)

if __name__ == "__main__":
    # For testing purposes
    from datetime import datetime
    start = datetime(2024, 1, 1).date()
    download_data(start)
