"""Tests for the disabled Freqtrade adapter boundary."""

from __future__ import annotations

import builtins
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.freqtrade_adapter import (
    ExecutionNotAllowed,
    FreqtradeAdapterRequest,
    RealBacktestAdapter,
    RealBacktestExecutionDisabled,
    request_to_json_safe_dict,
)


def _request(**overrides):
    data = {
        "strategy_config": {"bb_window": 20},
        "genome": {"genome_id": "candidate-1"},
        "pair": "BTC/USDT",
        "timeframe": "5m",
        "timerange": "20240101-20240201",
        "run_id": "stage-096",
        "dry_run_only": True,
        "output_root": "tmp-stage-096",
        "approval": {"execution_allowed": True},
    }
    data.update(overrides)
    return FreqtradeAdapterRequest(**data)


class TestFreqtradeAdapterBoundary(unittest.TestCase):
    def test_real_adapter_disabled_by_default(self) -> None:
        with self.assertRaises(ExecutionNotAllowed):
            RealBacktestAdapter().run_backtest(_request(), env={})

    def test_real_adapter_remains_disabled_even_when_gate_passes(self) -> None:
        with self.assertRaises(RealBacktestExecutionDisabled):
            RealBacktestAdapter().run_backtest(
                _request(),
                env={"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1"},
            )

    def test_real_adapter_does_not_import_freqtrade(self) -> None:
        real_import = builtins.__import__

        def guard(name, *args, **kwargs):
            if name == "freqtrade" or name.startswith("freqtrade."):
                raise AssertionError("freqtrade import attempted")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", guard):
            with self.assertRaises(ExecutionNotAllowed):
                RealBacktestAdapter().run_backtest(_request(), env={})

    def test_real_adapter_does_not_call_subprocess(self) -> None:
        with patch("subprocess.run") as mocked_run:
            with self.assertRaises(ExecutionNotAllowed):
                RealBacktestAdapter().run_backtest(_request(), env={})

        self.assertFalse(mocked_run.called)

    def test_request_is_json_serializable(self) -> None:
        request = _request()
        encoded = json.dumps(request.to_dict(), sort_keys=True)

        self.assertIn("stage-096", encoded)
        self.assertNotIn("Path", encoded)

    def test_request_rejects_non_json_safe_values(self) -> None:
        with self.assertRaises(TypeError):
            request_to_json_safe_dict({"output_root": Path("not-json-safe")})

    def test_no_secret_fields_in_request_or_result(self) -> None:
        request = _request(strategy_config={"bb_window": 20})
        encoded_request = json.dumps(request.to_dict(), sort_keys=True).lower()

        self.assertNotIn("api_key", encoded_request)
        self.assertNotIn("secret", encoded_request)
        self.assertNotIn("token", encoded_request)
        with self.assertRaises(ExecutionNotAllowed) as caught:
            RealBacktestAdapter().run_backtest(_request(strategy_config={"api_key": "bad"}), env={})

        self.assertNotIn("bad", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
