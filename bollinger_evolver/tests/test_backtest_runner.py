"""Tests for the Bollinger backtest subprocess adapter."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.runners.backtest_runner import (
    find_backtest_result_file,
    parse_backtest_metrics,
    run_backtest,
)


def _sample_payload() -> dict:
    return {
        "strategy": {
            "BollingerResonance_Gen001_Ind001": {
                "total_profit": 0.12,
                "profit_total_abs": 123.45,
                "profit_total_pct": 12.0,
                "max_drawdown": 0.08,
                "profit_factor": 1.7,
                "sharpe": 1.2,
                "sortino": 1.8,
                "calmar": 1.4,
                "wins": 7,
                "losses": 3,
                "avg_trade_duration": "01:30:00",
            }
        },
        "strategy_comparison": [
            {
                "key": "BollingerResonance_Gen001_Ind001",
                "trade_count": 10,
                "win_rate": 0.7,
            }
        ],
        "metadata": {"note": "test"},
    }


def _export_path_from_command(command: list[str]) -> Path:
    export_index = command.index("--export-filename")
    return Path(command[export_index + 1])


class TestParseBacktestMetrics(unittest.TestCase):
    def test_parse_metrics_extracts_common_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            result_path.write_text(json.dumps(_sample_payload()), encoding="utf-8")

            metrics = parse_backtest_metrics(str(result_path))

        self.assertEqual(metrics["total_profit"], 0.12)
        self.assertEqual(metrics["profit_total_abs"], 123.45)
        self.assertEqual(metrics["max_drawdown"], 0.08)
        self.assertEqual(metrics["trade_count"], 10)
        self.assertEqual(metrics["win_rate"], 0.7)
        self.assertEqual(metrics["avg_trade_duration"], "01:30:00")

    def test_parse_metrics_handles_missing_fields_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            result_path.write_text(json.dumps({"strategy": {"demo": {}}}), encoding="utf-8")

            metrics = parse_backtest_metrics(str(result_path))

        self.assertIsNone(metrics["total_profit"])
        self.assertIsNone(metrics["trade_count"])
        self.assertNotIn("parse_error", metrics)

    def test_parse_metrics_returns_parse_error_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            result_path.write_text("{not-json}", encoding="utf-8")

            metrics = parse_backtest_metrics(str(result_path))

        self.assertIn("parse_error", metrics)


class TestFindBacktestResultFile(unittest.TestCase):
    def test_finds_expected_file_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)
            result_path = export_dir / "expected.json"
            result_path.write_text("{}", encoding="utf-8")

            found = find_backtest_result_file(str(export_dir), str(result_path))

        self.assertEqual(found, str(result_path))

    def test_finds_latest_json_when_expected_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir)
            older = export_dir / "older.json"
            newer = export_dir / "newer.json"
            older.write_text("{}", encoding="utf-8")
            newer.write_text("{}", encoding="utf-8")

            found = find_backtest_result_file(str(export_dir), "missing.json")

        self.assertEqual(found, str(newer))


class TestRunBacktest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.config_path = self.workspace / "config.json"
        self.config_path.write_text("{}", encoding="utf-8")
        self.strategy_path = self.workspace / "strategies"
        self.strategy_path.mkdir(parents=True, exist_ok=True)
        self.export_dir = self.workspace / "exports"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_command_is_list_and_shell_false(self) -> None:
        payload = _sample_payload()

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            export_path = _export_path_from_command(command)
            export_path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch("bollinger_evolver.runners.backtest_runner.subprocess.run", side_effect=fake_run) as mocked_run:
            result = run_backtest(
                strategy_name="BollingerResonance_Gen001_Ind001",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                timeframe="15m",
                strategy_path=str(self.strategy_path),
                export_dir=str(self.export_dir),
            )

        self.assertTrue(result["success"])
        called_command = mocked_run.call_args.args[0]
        self.assertIsInstance(called_command, list)
        self.assertFalse(mocked_run.call_args.kwargs["shell"])
        self.assertIn("--strategy-path", called_command)
        self.assertIn(str(self.strategy_path.resolve()), called_command)

    def test_command_contains_core_fields_and_extra_args(self) -> None:
        payload = _sample_payload()

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            export_path = _export_path_from_command(command)
            export_path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch("bollinger_evolver.runners.backtest_runner.subprocess.run", side_effect=fake_run):
            result = run_backtest(
                strategy_name="BollingerResonance_Gen002_Ind003",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                timeframe="1h",
                export_dir=str(self.export_dir),
                extra_args={
                    "pairs": ["BTC/USDT", "ETH/USDT"],
                    "fee": 0.001,
                    "stake_amount": 100,
                    "max_open_trades": 3,
                    "api_secret": "should-not-appear",
                },
            )

        command = result["command"]
        self.assertIn("freqtrade", command)
        self.assertIn("backtesting", command)
        self.assertIn("BollingerResonance_Gen002_Ind003", command)
        self.assertIn("20240101-20240201", command)
        self.assertIn("1h", command)
        self.assertIn("--pairs", command)
        self.assertIn("BTC/USDT", command)
        self.assertIn("--stake-amount", command)
        self.assertNotIn("should-not-appear", command)
        self.assertNotIn("--api-secret", command)

    def test_default_export_dir_is_created(self) -> None:
        payload = _sample_payload()
        default_export_dir = self.workspace / "default_exports"

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            export_path = _export_path_from_command(command)
            export_path.parent.mkdir(parents=True, exist_ok=True)
            export_path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch("bollinger_evolver.runners.backtest_runner.DEFAULT_EXPORT_DIR", default_export_dir):
            with patch("bollinger_evolver.runners.backtest_runner.subprocess.run", side_effect=fake_run):
                result = run_backtest(
                    strategy_name="BollingerResonance_Gen001_Ind001",
                    config_path=str(self.config_path),
                    timerange="20240101-20240201",
                )

        self.assertTrue(default_export_dir.exists())
        self.assertTrue(result["raw_result_path"].startswith(str(default_export_dir)))

    def test_nonzero_returncode_returns_failure_and_stderr(self) -> None:
        with patch(
            "bollinger_evolver.runners.backtest_runner.subprocess.run",
            return_value=subprocess.CompletedProcess(["freqtrade"], 2, stdout="", stderr="boom"),
        ):
            result = run_backtest(
                strategy_name="BollingerResonance_Gen001_Ind001",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                export_dir=str(self.export_dir),
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["returncode"], 2)
        self.assertEqual(result["stderr"], "boom")
        self.assertEqual(result["error"], "boom")

    def test_file_not_found_returns_failure(self) -> None:
        with patch(
            "bollinger_evolver.runners.backtest_runner.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            result = run_backtest(
                strategy_name="BollingerResonance_Gen001_Ind001",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                export_dir=str(self.export_dir),
            )

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])

    def test_timeout_returns_failure(self) -> None:
        with patch(
            "bollinger_evolver.runners.backtest_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["freqtrade"], timeout=10, output="partial", stderr="late"),
        ):
            result = run_backtest(
                strategy_name="BollingerResonance_Gen001_Ind001",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                export_dir=str(self.export_dir),
                timeout_seconds=10,
            )

        self.assertFalse(result["success"])
        self.assertEqual(result["stdout"], "partial")
        self.assertEqual(result["stderr"], "late")
        self.assertIn("timed out", result["error"])

    def test_invalid_json_returns_parse_error(self) -> None:
        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            export_path = _export_path_from_command(command)
            export_path.write_text("{not-json}", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with patch("bollinger_evolver.runners.backtest_runner.subprocess.run", side_effect=fake_run):
            result = run_backtest(
                strategy_name="BollingerResonance_Gen001_Ind001",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                export_dir=str(self.export_dir),
            )

        self.assertFalse(result["success"])
        self.assertIn("parse_error", result["metrics"])
        self.assertIsNotNone(result["error"])

    def test_successful_run_parses_metrics_and_preserves_stdout(self) -> None:
        payload = _sample_payload()

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            export_path = _export_path_from_command(command)
            export_path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, stdout="done", stderr="")

        with patch("bollinger_evolver.runners.backtest_runner.subprocess.run", side_effect=fake_run):
            result = run_backtest(
                strategy_name="BollingerResonance_Gen001_Ind001",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                export_dir=str(self.export_dir),
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["stdout"], "done")
        self.assertEqual(result["metrics"]["trade_count"], 10)
        self.assertEqual(result["metrics"]["max_drawdown"], 0.08)

    def test_missing_result_file_is_failure_even_on_zero_returncode(self) -> None:
        with patch(
            "bollinger_evolver.runners.backtest_runner.subprocess.run",
            return_value=subprocess.CompletedProcess(["freqtrade"], 0, stdout="ok", stderr=""),
        ):
            result = run_backtest(
                strategy_name="BollingerResonance_Gen001_Ind001",
                config_path=str(self.config_path),
                timerange="20240101-20240201",
                export_dir=str(self.export_dir),
            )

        self.assertFalse(result["success"])
        self.assertIn("result file was not found", result["error"])


if __name__ == "__main__":
    unittest.main()
