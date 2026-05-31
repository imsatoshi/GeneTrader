"""Metrics-focused regression tests for the Bollinger Evolver runner CLI."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from bollinger_evolver.ga.runner import GASessionConfig, run_ga_session
from bollinger_evolver.ga.runner_cli import main
from bollinger_evolver.strategy_factory import GENERATED_ROOT


class TestGARunnerCliMetrics(unittest.TestCase):
    def tearDown(self) -> None:
        for path in getattr(self, "_generated_dirs", []):
            if path.exists():
                shutil.rmtree(path)

    def _track_generated_dir(self, run_id: str) -> None:
        if not hasattr(self, "_generated_dirs"):
            self._generated_dirs = []
        self._generated_dirs.append(GENERATED_ROOT / "cli_sessions" / run_id)
        self._generated_dirs.append(GENERATED_ROOT / "ga_sessions" / run_id)

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

    def _write_manifest(self, root: Path) -> Path:
        manifest_path = root / "manifest.json"
        entries = []
        for timeframe in ("15m", "1h", "4h"):
            entries.append(
                {
                    "pair": "BTC/USDT",
                    "timeframe": timeframe,
                    "status": "ready",
                    "row_count": 500,
                    "gap_count": 0,
                    "invalid_ohlc_count": 0,
                }
            )
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

    def test_cli_run_writes_complete_session_metrics_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            manifest = self._write_manifest(root)
            run_id = "cli-metrics"
            self._track_generated_dir(run_id)

            code, stdout, stderr = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--data-manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    run_id,
                ]
            )
            summary = json.loads(
                (root / "out" / run_id / "session_summary.json").read_text(encoding="utf-8")
            )
            self.assertTrue(Path(summary["session_report_path"]).exists())
            self.assertTrue(Path(summary["session_report_markdown_path"]).exists())

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("status: PASS", stdout)
        self.assertEqual(summary["session_id"], run_id)
        self.assertTrue(summary["mock_evaluation"])
        self.assertFalse(summary["real_backtest"])
        self.assertIn("created_at", summary)
        self.assertIn("dataQualityGate", summary)
        self.assertIn("run_summary", summary)
        self.assertIn("generation_summaries", summary)
        self.assertIn("final_best", summary)
        self.assertIn("session_report_path", summary)
        self.assertIn("session_report_markdown_path", summary)
        self.assertIsInstance(summary["generation_summaries"], list)
        self.assertGreaterEqual(len(summary["generation_summaries"]), 1)

    def test_cli_metrics_match_runner_api_core_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            manifest = self._write_manifest(root)
            run_id = "consistency"
            self._track_generated_dir(run_id)

            cli_code, _stdout, _stderr = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--data-manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "cli-out"),
                    "--run-id",
                    run_id,
                ]
            )
            cli_summary = json.loads(
                (root / "cli-out" / run_id / "session_summary.json").read_text(encoding="utf-8")
            )

            api_result = run_ga_session(
                GASessionConfig(
                    generations=2,
                    population_size=4,
                    seed=42,
                    run_id=run_id,
                    output_root=root / "api-out",
                    strategy_output_dir=GENERATED_ROOT / "ga_sessions" / run_id,
                    data_coverage_manifest=json.loads(manifest.read_text(encoding="utf-8")),
                    required_pairs=("BTC/USDT",),
                    required_timeframes=("15m", "1h", "4h"),
                )
            )
            api_summary = api_result.session_summary

        self.assertEqual(cli_code, 0)
        self.assertEqual(cli_summary["status"], api_summary["status"])
        self.assertEqual(cli_summary["mock_evaluation"], api_summary["mock_evaluation"])
        self.assertEqual(cli_summary["real_backtest"], api_summary["real_backtest"])
        self.assertEqual(cli_summary["completed"], api_summary["completed"])
        self.assertEqual(cli_summary["generations_requested"], api_summary["generations_requested"])
        self.assertEqual(cli_summary["population_size"], api_summary["population_size"])
        self.assertEqual(
            cli_summary["dataQualityGate"]["allowed_for_evaluation"],
            api_summary["dataQualityGate"]["allowed_for_evaluation"],
        )

    def test_dry_run_writes_preflight_summary_without_ga_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            manifest = self._write_manifest(root)
            run_id = "dry-run-metrics"
            self._track_generated_dir(run_id)

            code, stdout, _stderr = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--data-manifest",
                    str(manifest),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    run_id,
                    "--dry-run",
                ]
            )
            summary = json.loads(
                (root / "out" / run_id / "session_summary.json").read_text(encoding="utf-8")
            )

        self.assertEqual(code, 0)
        self.assertIn("status: PASS", stdout)
        self.assertTrue(summary["dry_run"])
        self.assertNotIn("run_summary", summary)
        self.assertNotIn("generation_summaries", summary)
        self.assertNotIn("final_best", summary)

    def test_manifest_missing_blocks_cli_session_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root)
            run_id = "blocked-metrics"
            self._track_generated_dir(run_id)

            code, stdout, _stderr = self._run_cli(
                [
                    "--config",
                    str(config),
                    "--output-root",
                    str(root / "out"),
                    "--run-id",
                    run_id,
                ]
            )
            summary = json.loads(
                (root / "out" / run_id / "session_summary.json").read_text(encoding="utf-8")
            )
            self.assertTrue(Path(summary["session_report_path"]).exists())
            self.assertTrue(Path(summary["session_report_markdown_path"]).exists())

        self.assertEqual(code, 1)
        self.assertIn("status: BLOCKED", stdout)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertFalse(summary["dataQualityGate"]["allowed_for_evaluation"])
        self.assertIsNone(summary["run_summary"])
        self.assertIsNone(summary["final_best"])

    def test_rejects_live_and_secret_flags_in_metrics_path(self) -> None:
        code, _stdout, stderr = self._run_cli(["--secret", "abc"])

        self.assertEqual(code, 2)
        self.assertIn("unsupported_live_or_secret_argument", stderr)
        self.assertNotIn("abc", stderr)


if __name__ == "__main__":
    unittest.main()
