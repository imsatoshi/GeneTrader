"""Disabled Freqtrade adapter boundary.

This module defines the future real-backtest request shape and a fail-closed
adapter skeleton. It never imports Freqtrade or starts a subprocess.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from bollinger_evolver.execution_gate import validate_real_backtest_execution_gate


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
