"""Disabled Freqtrade adapter boundary.

This module defines the future real-backtest request shape and a fail-closed
adapter skeleton. It never imports Freqtrade or starts a subprocess.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from bollinger_evolver.backtest_adapter import NormalizedBacktestResult, validate_normalized_backtest_result
from bollinger_evolver.execution_gate import validate_real_backtest_execution_gate
from bollinger_evolver.freqtrade_result_parser import parse_freqtrade_result_payload


SENSITIVE_CONFIG_KEYS = frozenset(
    {
        "api_key",
        "api_secret",
        "apikey",
        "key",
        "private_key",
        "secret",
        "token",
        "password",
        "webhook_url",
        "webhookurl",
        "url",
    }
)
SENSITIVE_ENV_MARKERS = frozenset(
    {
        "api_key",
        "apikey",
        "api_secret",
        "credential",
        "password",
        "private_key",
        "secret",
        "token",
    }
)
ALLOWED_ENV_KEYS = frozenset({"PATH", "PYTHONPATH", "SYSTEMROOT", "TEMP", "TMP"})
FORBIDDEN_FREQTRADE_COMMANDS = frozenset({"trade", "live", "hyperopt", "download-data", "download_data"})
REDACTED = "<redacted>"


class RealBacktestExecutionDisabled(RuntimeError):
    """Raised when real Freqtrade execution is requested before implementation."""


class ExecutionNotAllowed(RealBacktestExecutionDisabled):
    """Raised when the execution gate rejects a request."""


@dataclass(frozen=True)
class FreqtradeAdapterRequest:
    strategy_config: Mapping[str, Any]
    pair: str
    timeframe: str
    timerange: str
    run_id: str
    dry_run_only: bool = True
    output_root: str = ""
    command: str = "backtesting"
    cwd: str = ""
    genome: Mapping[str, Any] = field(default_factory=dict)
    approval: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return request_to_json_safe_dict(self)


def _json_safe(value: Any, *, path: str = "value") -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item, path=f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item, path=f"{path}[]") for item in value]
    raise TypeError(f"{path}_must_be_json_safe")


def request_to_json_safe_dict(request: FreqtradeAdapterRequest | Mapping[str, Any]) -> dict[str, Any]:
    raw = asdict(request) if isinstance(request, FreqtradeAdapterRequest) else dict(request)
    data = _json_safe(raw, path="request")
    json.dumps(data, sort_keys=True)
    return data


def _is_sensitive_key(key: object) -> bool:
    text = str(key).lower()
    return any(marker in text for marker in SENSITIVE_CONFIG_KEYS)


def _contains_sensitive_text(value: object) -> bool:
    text = str(value).lower()
    return any(marker in text for marker in SENSITIVE_ENV_MARKERS)


def _redact_sandbox_config(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if _is_sensitive_key(key) else _redact_sandbox_config(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_redact_sandbox_config(item) for item in value]
    return _json_safe(value, path="config")


def build_sandbox_config(base_config: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe, redacted Freqtrade config for sandbox review."""

    if not isinstance(base_config, Mapping):
        raise TypeError("base_config_must_be_mapping")
    if base_config.get("dry_run") is False:
        raise ValueError("live_trading_config_not_allowed")
    if base_config.get("live_mode") is True:
        raise ValueError("live_trading_config_not_allowed")
    if str(base_config.get("trading_mode", "")).lower() in {"live", "real", "production"}:
        raise ValueError("live_trading_config_not_allowed")

    config = _redact_sandbox_config(base_config)
    if not isinstance(config, dict):
        raise TypeError("sandbox_config_must_be_mapping")
    config["dry_run"] = True
    config["cancel_open_orders_on_exit"] = False
    config.setdefault("internals", {})
    json.dumps(config, sort_keys=True)
    return config


def _resolve_allowed_output_root(output_root: str, allowed_output_roots: Sequence[str | Path]) -> Path:
    if not isinstance(output_root, str) or not output_root.strip():
        raise ValueError("output_root_required")
    candidate = Path(output_root).resolve()
    if candidate.parent == candidate:
        raise ValueError("output_root_must_not_be_disk_root")
    if _contains_sensitive_text(candidate):
        raise ValueError("output_root_must_not_contain_secret_markers")
    allowed = tuple(Path(root).resolve() for root in allowed_output_roots)
    if not allowed:
        raise ValueError("allowed_output_roots_required")
    if not any(candidate == root or candidate.is_relative_to(root) for root in allowed):
        raise ValueError("output_root_not_allowlisted")
    return candidate


def _safe_env(env: Mapping[str, str] | None) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in dict(env or {}).items():
        key_text = str(key)
        value_text = str(value)
        if key_text not in ALLOWED_ENV_KEYS:
            continue
        if _contains_sensitive_text(key_text) or _contains_sensitive_text(value_text):
            continue
        safe[key_text] = value_text
    return safe


def build_freqtrade_command_spec(
    request: FreqtradeAdapterRequest,
    *,
    sandbox_config: Mapping[str, Any],
    allowed_output_roots: Sequence[str | Path],
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build a safe Freqtrade backtesting command spec without executing it."""

    if request.command.lower() in FORBIDDEN_FREQTRADE_COMMANDS:
        raise ValueError("forbidden_freqtrade_command")
    if request.command.lower() != "backtesting":
        raise ValueError("freqtrade_command_must_be_backtesting")
    if request.dry_run_only is not True:
        raise ValueError("dry_run_only_required")
    config = build_sandbox_config(sandbox_config)
    if config.get("dry_run") is not True:
        raise ValueError("sandbox_config_must_be_dry_run")

    output_root = _resolve_allowed_output_root(request.output_root, allowed_output_roots)
    cwd = Path(request.cwd).resolve() if request.cwd else output_root
    if not (cwd == output_root or cwd.is_relative_to(output_root) or output_root.is_relative_to(cwd)):
        raise ValueError("cwd_must_be_related_to_output_root")

    args = [
        "freqtrade",
        "backtesting",
        "--pairs",
        request.pair,
        "--timeframe",
        request.timeframe,
        "--timerange",
        request.timerange,
        "--backtest-directory",
        str(output_root),
        "--export",
        "trades",
    ]
    if any(str(arg).lower() in FORBIDDEN_FREQTRADE_COMMANDS for arg in args):
        raise ValueError("forbidden_freqtrade_command")
    if any(_contains_sensitive_text(arg) for arg in args):
        raise ValueError("secret_like_arg_not_allowed")

    spec = {
        "args": args,
        "cwd": str(cwd),
        "env": _safe_env(env),
        "shell": False,
    }
    json.dumps(spec, sort_keys=True)
    return spec


DEFAULT_FAKE_FREQTRADE_PAYLOAD: dict[str, Any] = {
    "profit_total": 0.118,
    "max_drawdown": 0.072,
    "sharpe": 1.25,
    "winrate": 0.56,
    "total_trades": 32,
    "max_consecutive_losses": 2,
    "leverage": 1.0,
    "risk_per_trade": 0.01,
}


class FakeFreqtradeRunner:
    """In-memory runner for adapter boundary tests.

    It accepts a command spec and returns a fixed JSON-like payload. It never
    starts a process and never writes output files.
    """

    def __init__(self, payload: Mapping[str, Any] | None = None) -> None:
        self.payload = dict(payload or DEFAULT_FAKE_FREQTRADE_PAYLOAD)
        self.calls: list[dict[str, Any]] = []

    def run(self, command_spec: Mapping[str, Any]) -> Mapping[str, Any]:
        args = command_spec.get("args")
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise ValueError("fake_runner_args_must_be_list_strings")
        if command_spec.get("shell") is not False:
            raise ValueError("fake_runner_shell_must_be_false")
        self.calls.append(dict(command_spec))
        return dict(self.payload)


def run_fake_freqtrade_backtest_boundary(
    request: FreqtradeAdapterRequest,
    *,
    base_config: Mapping[str, Any],
    allowed_output_roots: Sequence[str | Path],
    runner: FakeFreqtradeRunner | None = None,
    env: Mapping[str, str] | None = None,
) -> NormalizedBacktestResult:
    """Run the no-process adapter boundary with an in-memory fake runner."""

    gate = validate_real_backtest_execution_gate(request, env=env)
    if not gate["ok"]:
        raise ExecutionNotAllowed(";".join(str(error) for error in gate["errors"]))
    sandbox_config = build_sandbox_config(base_config)
    command_spec = build_freqtrade_command_spec(
        request,
        sandbox_config=sandbox_config,
        allowed_output_roots=allowed_output_roots,
        env=env,
    )
    active_runner = runner or FakeFreqtradeRunner()
    payload = active_runner.run(command_spec)
    parsed = parse_freqtrade_result_payload(payload)
    metadata = dict(parsed.metadata)
    metadata.update(
        {
            "source": "freqtrade_fake_runner_boundary",
            "run_id": request.run_id,
            "pair": request.pair,
            "timeframe": request.timeframe,
            "command_args_count": len(command_spec["args"]),
            "real_process_started": False,
            "real_output_directory_written": False,
        }
    )
    return validate_normalized_backtest_result(
        NormalizedBacktestResult(
            profit=parsed.profit,
            sharpe=parsed.sharpe,
            win_rate=parsed.win_rate,
            max_drawdown=parsed.max_drawdown,
            total_trades=parsed.total_trades,
            max_consecutive_losses=parsed.max_consecutive_losses,
            leverage=parsed.leverage,
            risk_per_trade=parsed.risk_per_trade,
            metadata=metadata,
        )
    )


class FakeRunnerFreqtradeAdapter:
    """BacktestAdapter-compatible fake runner boundary."""

    def __init__(
        self,
        request_template: FreqtradeAdapterRequest,
        *,
        base_config: Mapping[str, Any],
        allowed_output_roots: Sequence[str | Path],
        runner: FakeFreqtradeRunner | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.request_template = request_template
        self.base_config = dict(base_config)
        self.allowed_output_roots = tuple(allowed_output_roots)
        self.runner = runner or FakeFreqtradeRunner()
        self.env = dict(env or {})

    def run_backtest(self, genome: Mapping[str, Any]) -> NormalizedBacktestResult:
        request = replace(
            self.request_template,
            strategy_config=dict(genome),
            genome=dict(genome),
        )
        return run_fake_freqtrade_backtest_boundary(
            request,
            base_config=self.base_config,
            allowed_output_roots=self.allowed_output_roots,
            runner=self.runner,
            env=self.env,
        )


class RealBacktestAdapter:
    """Boundary skeleton for future real Freqtrade backtests.

    The skeleton is intentionally disabled even when the execution gate is
    satisfied. A later opt-in stage can replace this with a real implementation.
    """

    def run_backtest(
        self,
        request: FreqtradeAdapterRequest,
        *,
        env: Mapping[str, str] | None = None,
    ) -> object:
        gate = validate_real_backtest_execution_gate(request, env=env)
        if not gate["ok"]:
            raise ExecutionNotAllowed(";".join(str(error) for error in gate["errors"]))
        raise RealBacktestExecutionDisabled("real_freqtrade_backtest_adapter_disabled")
