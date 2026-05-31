"""Freqtrade backtesting subprocess adapter for Bollinger Evolver."""

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPORT_DIR = (PROJECT_ROOT / "results" / "bollinger_evolver" / "backtests").resolve()
SECRET_KEYWORDS = ("secret", "token", "password", "passphrase", "api_key", "apikey")


def _resolve_path(path_value: str | None, default: Path | None = None) -> Path | None:
    if path_value is None:
        return default
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    return candidate.resolve()


def _slugify(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value)


def _is_secret_key(key: str) -> bool:
    normalized = str(key).lower()
    return any(keyword in normalized for keyword in SECRET_KEYWORDS)


def _normalize_flag_name(key: str) -> str:
    if key.startswith("--"):
        return key
    return "--" + key.strip().replace("_", "-")


def _flatten_values(values: Iterable[Any]) -> list[str]:
    flattened: list[str] = []
    for item in values:
        if item is None:
            continue
        flattened.append(str(item))
    return flattened


def _build_extra_args(extra_args: dict[str, Any] | None) -> list[str]:
    if not extra_args:
        return []

    args: list[str] = []
    for key, value in extra_args.items():
        if _is_secret_key(key):
            continue
        if value is None or value is False:
            continue

        flag = _normalize_flag_name(str(key))
        if value is True:
            args.append(flag)
            continue
        if isinstance(value, (list, tuple)):
            flattened = _flatten_values(value)
            if flattened:
                args.append(flag)
                args.extend(flattened)
            continue

        args.extend([flag, str(value)])
    return args


def _build_export_filename(strategy_name: str, timerange: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    unique_suffix = uuid.uuid4().hex[:8]
    strategy_slug = _slugify(strategy_name)
    timerange_slug = _slugify(timerange)
    return f"{strategy_slug}_{timerange_slug}_{timestamp}_{unique_suffix}.json"


def _extract_scalar(data: Any, candidate_keys: tuple[str, ...]) -> Any:
    if isinstance(data, dict):
        for key in candidate_keys:
            if key in data and not isinstance(data[key], (dict, list)):
                return data[key]
        for value in data.values():
            found = _extract_scalar(value, candidate_keys)
            if found is not None:
                return found
        return None

    if isinstance(data, list):
        for item in data:
            found = _extract_scalar(item, candidate_keys)
            if found is not None:
                return found
    return None


def _extract_trade_count(data: Any) -> int | None:
    direct = _extract_scalar(data, ("trade_count", "total_trades", "trades"))
    if isinstance(direct, (int, float)) and not isinstance(direct, bool):
        return int(direct)

    wins = _extract_scalar(data, ("wins", "winning_trades"))
    losses = _extract_scalar(data, ("losses", "losing_trades"))
    draws = _extract_scalar(data, ("draws", "draw_trades"))
    if all(isinstance(value, (int, float)) for value in (wins, losses)):
        draw_count = int(draws) if isinstance(draws, (int, float)) else 0
        return int(wins) + int(losses) + draw_count
    return None


def _extract_win_rate(data: Any, trade_count: int | None) -> float | None:
    direct = _extract_scalar(data, ("win_rate", "winrate", "winning_rate"))
    if isinstance(direct, (int, float)) and not isinstance(direct, bool):
        return float(direct)

    wins = _extract_scalar(data, ("wins", "winning_trades"))
    if trade_count and isinstance(wins, (int, float)):
        return float(wins) / float(trade_count)
    return None


def parse_backtest_metrics(result_path: str) -> dict[str, Any]:
    """Parse common backtest metrics from a Freqtrade JSON export."""

    path = Path(result_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"parse_error": f"result file not found: {path}", "raw_keys": []}
    except json.JSONDecodeError as exc:
        return {"parse_error": f"invalid json: {exc}", "raw_keys": []}
    except OSError as exc:
        return {"parse_error": f"unable to read result file: {exc}", "raw_keys": []}

    trade_count = _extract_trade_count(payload)
    metrics = {
        "total_profit": _extract_scalar(payload, ("total_profit", "profit_total")),
        "profit_total_abs": _extract_scalar(payload, ("profit_total_abs", "absolute_profit")),
        "profit_total_pct": _extract_scalar(
            payload,
            ("profit_total_pct", "total_profit_pct", "profit_pct"),
        ),
        "max_drawdown": _extract_scalar(payload, ("max_drawdown", "drawdown_max")),
        "profit_factor": _extract_scalar(payload, ("profit_factor",)),
        "sharpe": _extract_scalar(payload, ("sharpe", "sharpe_ratio")),
        "sortino": _extract_scalar(payload, ("sortino", "sortino_ratio")),
        "calmar": _extract_scalar(payload, ("calmar", "calmar_ratio")),
        "trade_count": trade_count,
        "win_rate": _extract_win_rate(payload, trade_count),
        "avg_trade_duration": _extract_scalar(
            payload,
            ("avg_trade_duration", "average_trade_duration"),
        ),
        "raw_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
    }
    return metrics


def find_backtest_result_file(
    export_dir: str,
    expected_export_file: str | None = None,
) -> str | None:
    """Find a backtest JSON export file, preferring an expected file path."""

    directory = Path(export_dir)
    if not directory.exists() or not directory.is_dir():
        return None

    if expected_export_file:
        expected_path = Path(expected_export_file)
        if not expected_path.is_absolute():
            expected_path = (directory / expected_path.name).resolve()
        if expected_path.exists():
            return str(expected_path)

    json_files = sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not json_files:
        return None

    if expected_export_file:
        expected_name = Path(expected_export_file).name
        for file_path in json_files:
            if file_path.name == expected_name:
                return str(file_path)

    return str(json_files[0])


def run_backtest(
    strategy_name: str,
    config_path: str,
    timerange: str,
    timeframe: str = "15m",
    strategy_path: str | None = None,
    export_dir: str | None = None,
    extra_args: dict[str, Any] | None = None,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    """Run freqtrade backtesting as a subprocess and parse the JSON export."""

    resolved_export_dir = _resolve_path(export_dir, default=DEFAULT_EXPORT_DIR)
    assert resolved_export_dir is not None
    resolved_export_dir.mkdir(parents=True, exist_ok=True)

    resolved_config_path = _resolve_path(config_path)
    assert resolved_config_path is not None
    resolved_strategy_path = _resolve_path(strategy_path) if strategy_path else None
    export_filename = _build_export_filename(strategy_name, timerange)
    export_path = resolved_export_dir / export_filename

    command = [
        "freqtrade",
        "backtesting",
        "--config",
        str(resolved_config_path),
        "--strategy",
        str(strategy_name),
        "--timeframe",
        str(timeframe),
        "--timerange",
        str(timerange),
        "--export",
        "trades",
        "--export-filename",
        str(export_path),
    ]
    if resolved_strategy_path is not None:
        command.extend(["--strategy-path", str(resolved_strategy_path)])
    command.extend(_build_extra_args(extra_args))

    result = {
        "success": False,
        "strategy_name": strategy_name,
        "timerange": timerange,
        "timeframe": timeframe,
        "command": command,
        "returncode": None,
        "metrics": {},
        "raw_result_path": str(export_path),
        "stdout": "",
        "stderr": "",
        "error": None,
    }

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        result["stdout"] = exc.stdout or ""
        result["stderr"] = exc.stderr or ""
        result["error"] = f"backtest timed out after {timeout_seconds} seconds"
        return result
    except FileNotFoundError:
        result["error"] = "freqtrade executable not found"
        return result
    except Exception as exc:
        result["error"] = str(exc)
        return result

    result["returncode"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr

    found_result_path = find_backtest_result_file(
        str(resolved_export_dir),
        expected_export_file=str(export_path),
    )
    if found_result_path is not None:
        result["raw_result_path"] = found_result_path
        result["metrics"] = parse_backtest_metrics(found_result_path)

    if completed.returncode != 0:
        result["error"] = completed.stderr.strip() or f"freqtrade exited with code {completed.returncode}"
        return result

    if found_result_path is None:
        result["error"] = "backtest completed but result file was not found"
        return result

    if result["metrics"].get("parse_error"):
        result["error"] = result["metrics"]["parse_error"]
        return result

    result["success"] = True
    return result
