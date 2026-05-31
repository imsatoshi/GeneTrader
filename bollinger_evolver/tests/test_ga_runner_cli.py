"""Tests for the Bollinger Evolver runner CLI."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from bollinger_evolver.ga.runner_cli import main
from bollinger_evolver.strategy_factory import GENERATED_ROOT


class TestGARunnerCli(unittest.TestCase):
    def tearDown(self) -> None:
        for path in getattr(self, "_generated_dirs", []):
            if path.exists():
                shutil.rmtree(path)

    def _track_generated_dir(self, run_id: str) -> None:
        if not hasattr(self, "_generated_dirs"):
            self._generated_dirs = []
        self._generated_dirs.append(GENERATED_ROOT / "cli_sessions" / run_id)

    def _write_config(self, root: Path) -> Path:
        config_path = root / "ga_bollinger_resonance.json"
        config_path.write_text(
            json.dumps(
                {
                    "base_timeframe": "15m",
                    "informative_timeframes": ["1h", "4h"],
                    "market_filter_pair": "BTC/USDT",
                    "population_size": 4,
                    "generations": 2,
                    "crossover_prob": 0.8,
                    "mutation_prob": 0.2,
                    "pool_processes": 2,
                    "enable_walk_forward": True,
                    "walk_forward_train_weeks": 26,
                    "walk_forward_test_weeks": 4,
                    "min_trades_per_week": 0.5,
                    "max_drawdown_limit": 0.35,
                    "min_profit_factor": 1.0,
                    "random_seed": 42,
                }
            ),
            encoding="utf-8",
        )
        return config_path

    def _write_manifest(self, root: Path, **entry_overrides: object) -> Path:
        manifest_path = root / "manifest.json"
        entries = []
        for timeframe in ("15m", "1h", "4h"):
            entry = {
                "pair": "BTC/USDT",
                "timeframe": timeframe,
                "status": "ready",
                "row_count": 500,
                "gap_count": 0,
                "invalid_ohlc_count": 0,
            }
            entry.update(entry_overrides)
            entries.append(entry)
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "ready",
                    "pairs": ["BTC/USDT"],
                    "timeframes": ["15m", "1h", "4h"],
                    "entries": entries,
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def _run_cli(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_help_returns_zero(self) -> None:
        code, stdout, stderr = self._run_cli(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("mock-first", stdout.lower())
        self.assertEqual(stderr, "")

    def test_dry_run_validates_without_running_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            manifest = self._write_manifest(root)
            self._track_generated_dir("dryrun")
            with patch("bollinger_evolver.ga.runner_cli.run_ga_session") as runner:
                code, stdout, _ = self._run_cli(
                    [
                        "--config",
                        str(config),
                        "--data-manifest",
                        str(manifest),
                        "--output-root",
                        str(root / "out"),
                        "--run-id",
                        "dryrun",
                        "--dry-run",
                    ]
                )

        self.assertEqual(code, 0)
        runner.assert_not_called()
        self.assertIn("status: PASS", stdout)

    def test_default_manifest_missing_blocks_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            self._track_generated_dir("blocked")
            code, stdout, _ = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    "blocked",
                ]
            )
            summary_path = root / "out" / "blocked" / "session_summary.json"
            self.assertTrue(summary_path.exists())

        self.assertEqual(code, 1)
        self.assertIn("status: BLOCKED", stdout)

    def test_disable_data_quality_gate_runs_mock_session_and_marks_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            self._track_generated_dir("session")
            code, stdout, _ = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    "session",
                    "--disable-data-quality-gate",
                ]
            )
            summary = json.loads((root / "out" / "session" / "session_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(code, 0)
        self.assertIn("real_backtest: false", stdout)
        self.assertIn("session_report:", stdout)
        self.assertIn("session_report_md:", stdout)
        self.assertIn("warning: dataQualityGateDisabled=true", stdout)
        self.assertTrue(summary["dataQualityGateDisabled"])
        self.assertEqual(summary["status"], "PASS")

    def test_cli_writes_session_summary_under_session_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            manifest = self._write_manifest(root)
            self._track_generated_dir("session-dir")
            code, _stdout, _stderr = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--data-manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    "session-dir",
                ]
            )
            self.assertTrue((root / "out" / "session-dir" / "session_summary.json").exists())

        self.assertEqual(code, 0)

    def test_rejects_allow_real_backtest_argument(self) -> None:
        code, _stdout, stderr = self._run_cli(["--allow-real-backtest"])
        self.assertEqual(code, 2)
        self.assertIn("unsupported_live_or_secret_argument", stderr)

    def test_rejects_live_argument(self) -> None:
        code, _stdout, stderr = self._run_cli(["--live"])
        self.assertEqual(code, 2)
        self.assertIn("unsupported_live_or_secret_argument", stderr)

    def test_rejects_secret_arguments(self) -> None:
        code, _stdout, stderr = self._run_cli(["--api-key", "secret-value"])
        self.assertEqual(code, 2)
        self.assertIn("unsupported_live_or_secret_argument", stderr)
        self.assertNotIn("secret-value", stderr)

    def test_cli_does_not_print_sensitive_manifest_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            manifest = self._write_manifest(root, api_secret="hidden-secret")
            self._track_generated_dir("sensitive")
            code, stdout, stderr = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--data-manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    "sensitive",
                    "--dry-run",
                ]
            )

        self.assertEqual(code, 0)
        self.assertNotIn("hidden-secret", stdout)
        self.assertNotIn("hidden-secret", stderr)

    def test_no_report_skips_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            manifest = self._write_manifest(root)
            self._track_generated_dir("no-report")
            code, stdout, _ = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--data-manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    "no-report",
                    "--no-report",
                ]
            )
            summary = json.loads(
                (root / "out" / "no-report" / "session_summary.json").read_text(encoding="utf-8")
            )

        self.assertEqual(code, 0)
        self.assertNotIn("session_report:", stdout)
        self.assertNotIn("session_report_md:", stdout)
        self.assertNotIn("session_report_path", summary)
        self.assertNotIn("session_report_markdown_path", summary)


if __name__ == "__main__":
    unittest.main()
