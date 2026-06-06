"""Fail-closed real Freqtrade backtest adapter skeleton.

This module documents the future real adapter boundary while keeping execution
disabled. It validates the sandbox gate and returns JSON-safe diagnostics, but
it does not import Freqtrade or start external processes.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from bollinger_evolver.execution_gate import validate_real_backtest_execution_gate
from bollinger_evolver.freqtrade_adapter import (
    ExecutionNotAllowed,
    FreqtradeAdapterRequest,
    RealBacktestExecutionDisabled,
    request_to_json_safe_dict,
)


@dataclass(frozen=True)
class RealBacktestSandboxGate:
    """JSON-safe gate snapshot for a future real adapter call."""

    request: FreqtradeAdapterRequest
    env: Mapping[str, str] | None = None

    def validate(self) -> dict[str, Any]:
        return build_real_backtest_sandbox_gate(self.request, env=self.env)


def build_real_backtest_sandbox_gate(
    request: FreqtradeAdapterRequest,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a serializable fail-closed gate report for the real adapter."""

    gate = validate_real_backtest_execution_gate(request, env=env)
    report: dict[str, Any] = {
        "adapter": "real_freqtrade_backtest_skeleton",
        "enabled": False,
        "gate": gate,
        "request": request_to_json_safe_dict(request),
    }
    json.dumps(report, sort_keys=True)
    return report


class RealBacktestAdapterSkeleton:
    """Disabled skeleton for the future real Freqtrade backtest adapter."""

    def prepare(
        self,
        request: FreqtradeAdapterRequest,
        *,
        env: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return build_real_backtest_sandbox_gate(request, env=env)

    def run_backtest(
        self,
        request: FreqtradeAdapterRequest,
        *,
        env: Mapping[str, str] | None = None,
    ) -> object:
        report = self.prepare(request, env=env)
        gate = report["gate"]
        if not gate["ok"]:
            raise ExecutionNotAllowed(";".join(str(error) for error in gate["errors"]))
        raise RealBacktestExecutionDisabled("real_freqtrade_backtest_adapter_disabled")


RealFreqtradeBacktestAdapter = RealBacktestAdapterSkeleton
