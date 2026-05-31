"""Tests for the mock-first GA session runner."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from bollinger_evolver.ga.runner import GASessionConfig, run_ga_session
from bollinger_evolver.strategy_factory import GENERATED_ROOT
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


def _valid_genes(**overrides: object) -> dict:
    genes = dict(DEFAULT_GENES)
    genes.update(overrides)
    return genes


def _bad_manifest() -> dict:
    return {
        "status": "partial",
        "pairs": ["BTC/USDT"],
        "timeframes": ["15m"],
        "entries": [
            {
                "pair": "BTC/USDT",
                "timeframe": "15m",
                "status": "ready",
                "row_count": 5,
                "gap_count": 0,
                "invalid_ohlc_count": 0,
            }
        ],
    }


class TestGARunner(unittest.TestCase):
    def tearDown(self) -> None:
        for path in getattr(self, "_strategy_dirs", []):
            if path.exists():
                shutil.rmtree(path)

    def _track_strategy_dir(self) -> Path:
        if not hasattr(self, "_strategy_dirs"):
            self._strategy_dirs = []
        path = GENERATED_ROOT / f"test_ga_runner_{uuid.uuid4().hex}"
        self._strategy_dirs.append(path)
        return path

    def _config(self, temp_dir: str, **overrides: object) -> GASessionConfig:
        base = {
            "generations": 2,
            "population_size": 3,
            "seed": 101,
            "run_id": f"session-{uuid.uuid4().hex[:8]}",
            "output_root": Path(temp_dir) / "session",
            "strategy_output_dir": self._track_strategy_dir(),
            "evaluation_mode": "mock",
            "allow_real_backtest": False,
        }
        base.update(overrides)
        return GASessionConfig(**base)

    def test_runner_executes_mock_session_and_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga_session(self._config(temp_dir))
            self.assertTrue(Path(result.session_summary_path).exists())
            summary = json.loads(Path(result.session_summary_path).read_text(encoding="utf-8"))
            self.assertTrue(Path(result.report_json_path).exists())
            self.assertTrue(Path(result.report_markdown_path).exists())

        self.assertTrue(result.success)
        self.assertEqual(summary["run_id"], result.run_id)
        self.assertIn("run_summary", summary)
        self.assertIn("generation_summaries", summary)
        self.assertIn("final_best", summary)
        self.assertIn("dataQualityGate", summary)
        self.assertEqual(len(summary["generation_summaries"]), 2)
        self.assertTrue(summary["mock_first"])
        self.assertEqual(summary["session_report_path"], result.report_json_path)
        self.assertEqual(summary["session_report_markdown_path"], result.report_markdown_path)

    def test_runner_blocks_when_preflight_data_gate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga_session(
                self._config(
                    temp_dir,
                    data_coverage_manifest=_bad_manifest(),
                )
            )

        self.assertFalse(result.success)
        self.assertIsNone(result.orchestrator_result)
        self.assertEqual(result.reason, "data_quality_gate_failed")
        self.assertFalse(result.session_summary["dataQualityGate"]["allowed_for_evaluation"])
        self.assertIsNone(result.session_summary["final_best"])

    def test_runner_final_best_matches_consolidated_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga_session(self._config(temp_dir))
            summary = result.session_summary
            final_best_path = Path(summary["final_best_path"])
            final_best = json.loads(final_best_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["final_best"]["genes_hash"], final_best["genes_hash"])
        self.assertEqual(summary["final_best"]["strategy_name"], final_best["strategy_name"])

    def test_runner_respects_initial_population_and_failed_candidates_do_not_win(self) -> None:
        population = [
            dict(_valid_genes(bb_period_15m=20), api_key="secret-a"),
            _valid_genes(bb_period_15m=35),
            _valid_genes(bb_period_15m=50),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga_session(
                self._config(temp_dir, fail_individual_indexes=(0,)),
                initial_population=population,
            )

        self.assertTrue(result.success)
        serialized = json.dumps(result.session_summary, sort_keys=True)
        self.assertNotIn("secret-a", serialized)
        self.assertNotEqual(
            result.session_summary["final_best"]["genes"].get("bb_period_15m"),
            20,
        )

    def test_runner_keeps_real_backtest_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga_session(
                self._config(temp_dir, allow_real_backtest=True)
            )

        self.assertTrue(result.session_summary["allow_real_backtest"] is False)
        self.assertTrue(result.success)

    def test_runner_can_disable_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga_session(
                self._config(temp_dir, generate_report=False)
            )

        self.assertIsNone(result.report_json_path)
        self.assertIsNone(result.report_markdown_path)
        self.assertNotIn("session_report_path", result.session_summary)
        self.assertNotIn("session_report_markdown_path", result.session_summary)


if __name__ == "__main__":
    unittest.main()
