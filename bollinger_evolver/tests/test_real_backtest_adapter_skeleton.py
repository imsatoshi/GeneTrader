"""Tests for the fail-closed real backtest adapter skeleton."""

from __future__ import annotations

import builtins
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.freqtrade_adapter import (
    ExecutionNotAllowed,
    FreqtradeAdapterRequest,
    RealBacktestExecutionDisabled,
)
from bollinger_evolver.real_backtest_adapter import (
    RealBacktestAdapterSkeleton,
    RealBacktestSandboxGate,
    build_real_backtest_sandbox_gate,
)


ENABLE_ENV = {"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1", "PATH": "bin"}


def _request(root: Path) -> FreqtradeAdapterRequest:
    return FreqtradeAdapterRequest(
        strategy_config={"bb_window": 20},
        pair="BTC/USDT",
        timeframe="5m",
        timerange="20240101-20240201",
        run_id="stage-114",
        dry_run_only=True,
        output_root=str(root / "real-adapter-out"),
        approval={"execution_allowed": True},
    )


class TestRealBacktestAdapterSkeleton(unittest.TestCase):
    def test_real_backtest_adapter_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = _request(Path(tmp))

            with self.assertRaises(RealBacktestExecutionDisabled):
                RealBacktestAdapterSkeleton().run_backtest(request, env=ENABLE_ENV)

    def test_real_backtest_adapter_fails_when_gate_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = _request(Path(tmp))

            with self.assertRaises(ExecutionNotAllowed):
                RealBacktestAdapterSkeleton().run_backtest(request, env={})

    def test_real_backtest_adapter_does_not_import_freqtrade(self) -> None:
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "freqtrade" or name.startswith("freqtrade."):
                raise AssertionError("real adapter skeleton must not import freqtrade")
            return original_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            request = _request(Path(tmp))
            with patch.object(builtins, "__import__", guarded_import):
                report = RealBacktestAdapterSkeleton().prepare(request, env=ENABLE_ENV)

        self.assertFalse(report["enabled"])

    def test_real_backtest_adapter_does_not_call_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = _request(Path(tmp))
            with patch("subprocess.run") as mocked_run:
                with self.assertRaises(RealBacktestExecutionDisabled):
                    RealBacktestAdapterSkeleton().run_backtest(request, env=ENABLE_ENV)

        self.assertFalse(mocked_run.called)

    def test_real_backtest_sandbox_gate_report_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = _request(Path(tmp))
            report = build_real_backtest_sandbox_gate(request, env=ENABLE_ENV)

        encoded = json.dumps(report, sort_keys=True)
        self.assertIn("real_freqtrade_backtest_skeleton", encoded)
        self.assertFalse(report["enabled"])

    def test_real_backtest_sandbox_gate_dataclass_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = _request(Path(tmp))
            report = RealBacktestSandboxGate(request=request, env={}).validate()

        self.assertFalse(report["gate"]["ok"])
        self.assertIn("real_freqtrade_backtest_env_not_enabled", report["gate"]["errors"])


if __name__ == "__main__":
    unittest.main()
