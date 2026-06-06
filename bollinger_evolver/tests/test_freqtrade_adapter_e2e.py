"""Fake-runner E2E tests for the Freqtrade adapter boundary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.backtest_adapter import AdapterBackedMockEvaluator, NormalizedBacktestResult
from bollinger_evolver.freqtrade_adapter import (
    ExecutionNotAllowed,
    FakeFreqtradeRunner,
    FakeRunnerFreqtradeAdapter,
    FreqtradeAdapterRequest,
    run_fake_freqtrade_backtest_boundary,
)
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution


ENABLE_ENV = {"GENETRADER_ENABLE_REAL_FREQTRADE_BACKTEST": "1", "PATH": "bin"}


def _request(root: Path) -> FreqtradeAdapterRequest:
    return FreqtradeAdapterRequest(
        strategy_config={"bb_window": 20},
        pair="BTC/USDT",
        timeframe="5m",
        timerange="20240101-20240201",
        run_id="stage-099",
        dry_run_only=True,
        output_root=str(root / "freqtrade-out"),
        approval={"execution_allowed": True},
    )


class TestFreqtradeAdapterE2E(unittest.TestCase):
    def test_fake_runner_e2e_does_not_call_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("subprocess.run") as mocked_run:
                result = run_fake_freqtrade_backtest_boundary(
                    _request(root),
                    base_config={"dry_run": True},
                    allowed_output_roots=(root,),
                    env=ENABLE_ENV,
                )

        self.assertIsInstance(result, NormalizedBacktestResult)
        self.assertFalse(mocked_run.called)

    def test_fake_runner_e2e_respects_execution_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ExecutionNotAllowed):
                run_fake_freqtrade_backtest_boundary(
                    _request(root),
                    base_config={"dry_run": True},
                    allowed_output_roots=(root,),
                    env={},
                )

    def test_fake_runner_e2e_returns_normalized_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_fake_freqtrade_backtest_boundary(
                _request(root),
                base_config={"dry_run": True, "exchange": {"api_key": "redact-me"}},
                allowed_output_roots=(root,),
                runner=FakeFreqtradeRunner(),
                env=ENABLE_ENV,
            )

        self.assertEqual(result.total_trades, 32)
        self.assertEqual(result.max_consecutive_losses, 2)
        self.assertEqual(result.metadata["source"], "freqtrade_fake_runner_boundary")
        self.assertFalse(result.metadata["real_process_started"])

    def test_fake_runner_e2e_can_feed_ga_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FakeRunnerFreqtradeAdapter(
                _request(root),
                base_config={"dry_run": True},
                allowed_output_roots=(root,),
                env=ENABLE_ENV,
            )
            evaluator = AdapterBackedMockEvaluator(adapter)

            result = run_ga_execution(GAExecutionConfig(population_size=4, generations=2, seed=99), evaluator=evaluator)

        self.assertEqual([item.generation for item in result.generations], [1, 2])
        self.assertIsNotNone(result.final_best)
        self.assertGreaterEqual(result.final_best.fitness, 0.0)

    def test_fake_runner_e2e_does_not_write_outside_tempdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_root = root / "freqtrade-out"

            run_fake_freqtrade_backtest_boundary(
                _request(root),
                base_config={"dry_run": True},
                allowed_output_roots=(root,),
                env=ENABLE_ENV,
            )

            self.assertFalse(output_root.exists())
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
