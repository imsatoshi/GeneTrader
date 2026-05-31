"""Backtest-based fitness evaluation for Bollinger Evolver."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from bollinger_evolver.runners import run_backtest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVALUATION_DIR = (PROJECT_ROOT / "results" / "bollinger_evolver" / "evaluations").resolve()
SENSITIVE_KEYWORDS = (
    "secret",
    "api_secret",
    "api_key",
    "apikey",
    "token",
    "password",
    "passwd",
    "private_key",
    "wallet",
    "mnemonic",
    "seed",
    "auth",
    "credential",
)
RUNNER_ARG_WHITELIST = {
    "pairs",
    "fee",
    "stake_amount",
    "dry_run_wallet",
    "max_open_trades",
}


@dataclass(frozen=True)
class FitnessConfig:
    strategy: str
    config_path: Path | str
    timerange: str | None = None
    timeframe: str | None = None
    pairs: tuple[str, ...] = ()
    result_dir: Path | str = "results/bollinger_evolver/backtests"
    timeout_seconds: int = 300
    profit_weight: float = 1.0
    sharpe_weight: float = 0.25
    drawdown_weight: float = 1.0
    winrate_weight: float = 0.05
    trade_count_weight: float = 0.01
    min_trades: int = 1
    max_drawdown_pct: float | None = None
    failed_score: float = -1_000_000.0


@dataclass(frozen=True)
class FitnessResult:
    success: bool
    fitness_score: float
    metrics: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    reason: str | None = None
    backtest_result: dict[str, Any] = field(default_factory=dict)
    artifact_path: str | None = None


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key).lower()
    return any(fragment in normalized for fragment in SENSITIVE_KEYWORDS)


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return sanitize_mapping(value)
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return 0.0
    return str(value)


def sanitize_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively remove sensitive keys and JSON-unsafe values from mappings."""

    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if _is_sensitive_key(str(key)):
            continue
        sanitized[str(key)] = _make_json_safe(value)
    return sanitized


def _coerce_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            numeric = float(text)
        except ValueError:
            return default
    else:
        return default

    if not math.isfinite(numeric):
        return default
    return numeric


def _normalize_percentage(value: Any) -> float:
    numeric = _coerce_float(value, default=0.0)
    if abs(numeric) <= 1.0:
        return round(numeric * 100.0, 10)
    return round(numeric, 10)


def _normalize_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else default
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except ValueError:
            return default
    return default


def _pick_metric(metrics: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in metrics:
            return metrics[key]
    return None


def build_backtest_params(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Build safe runner extra args from a GA candidate mapping."""

    params: dict[str, Any] = {}
    for key in RUNNER_ARG_WHITELIST:
        if key not in candidate or _is_sensitive_key(key):
            continue
        value = candidate[key]
        if value is None:
            continue
        if key == "pairs":
            if isinstance(value, (list, tuple, set)):
                pairs = [str(item) for item in value if item is not None]
                if pairs:
                    params[key] = pairs
            continue
        if key == "max_open_trades":
            params[key] = _normalize_int(value, default=0)
            continue
        params[key] = _coerce_float(value, default=0.0)
    return params


def normalize_backtest_metrics(raw_metrics: Mapping[str, Any]) -> dict[str, float]:
    """Normalize common backtest metric aliases into a stable schema."""

    if not isinstance(raw_metrics, Mapping):
        raw_metrics = {}

    normalized = {
        "total_profit_pct": _normalize_percentage(
            _pick_metric(raw_metrics, "total_profit_pct", "profit_total_pct", "profit_total", "total_profit")
        ),
        "max_drawdown_pct": abs(
            _normalize_percentage(
                _pick_metric(raw_metrics, "max_drawdown_pct", "max_drawdown", "drawdown")
            )
        ),
        "sharpe": _coerce_float(_pick_metric(raw_metrics, "sharpe", "sharpe_ratio"), default=0.0),
        "sortino": _coerce_float(_pick_metric(raw_metrics, "sortino", "sortino_ratio"), default=0.0),
        "winrate": _normalize_percentage(
            _pick_metric(raw_metrics, "winrate", "win_rate", "winning_rate")
        ),
        "trade_count": float(
            _normalize_int(
                _pick_metric(raw_metrics, "trade_count", "total_trades", "trades"),
                default=0,
            )
        ),
        "profit_factor": _coerce_float(_pick_metric(raw_metrics, "profit_factor"), default=0.0),
    }
    return normalized


def compute_fitness_score(
    metrics: Mapping[str, Any],
    config: FitnessConfig,
) -> float:
    """Compute a deterministic scalar fitness score from normalized metrics."""

    if not isinstance(metrics, Mapping):
        return float(config.failed_score)

    normalized = normalize_backtest_metrics(metrics)
    trade_count = normalized["trade_count"]
    max_drawdown_pct = normalized["max_drawdown_pct"]

    if trade_count < float(config.min_trades):
        return float(config.failed_score) / 2.0
    if config.max_drawdown_pct is not None and max_drawdown_pct > float(config.max_drawdown_pct):
        return float(config.failed_score) / 4.0

    score = (
        normalized["total_profit_pct"] * float(config.profit_weight)
        + normalized["sharpe"] * float(config.sharpe_weight)
        + normalized["winrate"] * float(config.winrate_weight)
        + trade_count * float(config.trade_count_weight)
        - abs(max_drawdown_pct) * float(config.drawdown_weight)
    )
    if not math.isfinite(score):
        return float(config.failed_score)
    return float(score)


def _summarize_backtest_result(backtest_result: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(backtest_result, Mapping):
        return {}

    summary = {
        "success": backtest_result.get("success"),
        "strategy_name": backtest_result.get("strategy_name"),
        "timerange": backtest_result.get("timerange"),
        "timeframe": backtest_result.get("timeframe"),
        "command": backtest_result.get("command"),
        "returncode": backtest_result.get("returncode"),
        "metrics": backtest_result.get("metrics"),
        "raw_result_path": backtest_result.get("raw_result_path"),
        "error": backtest_result.get("error"),
    }
    return sanitize_mapping(summary)


def _build_failure_result(
    candidate: Mapping[str, Any],
    config: FitnessConfig,
    reason: str,
    backtest_result: Mapping[str, Any] | None = None,
) -> FitnessResult:
    return FitnessResult(
        success=False,
        fitness_score=float(config.failed_score),
        metrics={},
        params=sanitize_mapping(candidate),
        reason=reason,
        backtest_result=_summarize_backtest_result(backtest_result or {}),
    )


def _constraint_reason(metrics: Mapping[str, float], config: FitnessConfig) -> str | None:
    trade_count = metrics.get("trade_count", 0.0)
    if trade_count < float(config.min_trades):
        return f"trade_count_below_minimum: {trade_count} < {config.min_trades}"

    max_drawdown_pct = metrics.get("max_drawdown_pct", 0.0)
    if config.max_drawdown_pct is not None and max_drawdown_pct > float(config.max_drawdown_pct):
        return (
            f"max_drawdown_above_limit: {max_drawdown_pct} > {float(config.max_drawdown_pct)}"
        )
    return None


def evaluate_candidate(
    candidate: Mapping[str, Any],
    fitness_config: FitnessConfig,
    runner: Callable[..., Any] | None = None,
    artifact_dir: Path | str | None = None,
) -> FitnessResult:
    """Evaluate one GA candidate via the Task 07 backtest runner."""

    if not isinstance(candidate, Mapping):
        return _build_failure_result(
            {},
            fitness_config,
            "invalid_candidate: candidate must be a mapping",
        )

    runner_callable = runner or run_backtest
    sanitized_params = sanitize_mapping(candidate)
    extra_args = build_backtest_params(candidate)
    if fitness_config.pairs and "pairs" not in extra_args:
        extra_args["pairs"] = [str(pair) for pair in fitness_config.pairs]

    timeframe = str(candidate.get("timeframe") or fitness_config.timeframe or "15m")
    timerange = str(fitness_config.timerange or "")
    backtest_result = runner_callable(
        strategy_name=str(fitness_config.strategy),
        config_path=str(fitness_config.config_path),
        timerange=timerange,
        timeframe=timeframe,
        export_dir=str(fitness_config.result_dir),
        extra_args=extra_args,
        timeout_seconds=int(fitness_config.timeout_seconds),
    )

    if not isinstance(backtest_result, Mapping):
        result = _build_failure_result(
            candidate,
            fitness_config,
            "backtest_runner_failed: invalid runner result",
        )
    elif not backtest_result.get("success"):
        error = str(backtest_result.get("error") or "unknown runner failure")
        result = _build_failure_result(
            candidate,
            fitness_config,
            f"backtest_runner_failed: {error}",
            backtest_result=backtest_result,
        )
    else:
        raw_metrics = backtest_result.get("metrics", {})
        normalized_metrics = normalize_backtest_metrics(raw_metrics)
        fitness_score = compute_fitness_score(normalized_metrics, fitness_config)
        result = FitnessResult(
            success=True,
            fitness_score=fitness_score,
            metrics=normalized_metrics,
            params=sanitized_params,
            reason=_constraint_reason(normalized_metrics, fitness_config),
            backtest_result=_summarize_backtest_result(backtest_result),
        )

    if artifact_dir is not None:
        artifact_path = write_evaluation_artifact(result, artifact_dir)
        result = replace(result, artifact_path=str(artifact_path))
    return result


def write_evaluation_artifact(
    result: FitnessResult,
    output_dir: Path | str = DEFAULT_EVALUATION_DIR,
    run_id: str | None = None,
) -> Path:
    """Write a JSON artifact for one evaluation result."""

    destination = Path(output_dir)
    if not destination.is_absolute():
        destination = (PROJECT_ROOT / destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_payload = {
        "success": bool(result.success),
        "fitness_score": float(result.fitness_score),
        "params": sanitize_mapping(result.params),
        "metrics": sanitize_mapping(result.metrics),
        "reason": result.reason,
        "backtest_artifact_path": result.backtest_result.get("raw_result_path"),
        "backtest_result": _summarize_backtest_result(result.backtest_result),
        "created_at": created_at,
    }

    if run_id:
        safe_payload["run_id"] = str(run_id)

    digest = hashlib.sha256(
        json.dumps(safe_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    artifact_path = destination / f"evaluation-{timestamp}-{digest}.json"
    artifact_path.write_text(
        json.dumps(safe_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return artifact_path
