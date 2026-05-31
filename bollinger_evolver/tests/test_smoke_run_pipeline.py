"""End-to-end smoke run tests for the Bollinger Evolver GA pipeline."""

from __future__ import annotations

import importlib
import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from bollinger_evolver.ga.smoke_run_pipeline import (
    SmokeRunConfig,
    build_position_sizing_snapshot,
    run_smoke_ga_pipeline,
)
from bollinger_evolver.strategy_factory import GENERATED_ROOT
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


def _strategy_dir() -> Path:
    return GENERATED_ROOT / f"test_smoke_pipeline_{uuid.uuid4().hex}"


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


class TestSmokeRunPipeline(unittest.TestCase):
    def tearDown(self) -> None:
        for path in getattr(self, "_strategy_dirs", []):
            if path.exists():
                shutil.rmtree(path)

    def _track_strategy_dir(self) -> Path:
        if not hasattr(self, "_strategy_dirs"):
            self._strategy_dirs = []
        path = _strategy_dir()
        self._strategy_dirs.append(path)
        return path

    def _config(self, temp_dir: str, **overrides: object) -> SmokeRunConfig:
        base = {
            "generations": 2,
            "population_size": 4,
            "seed": 77,
            "run_id": f"smoke-{uuid.uuid4().hex[:8]}",
            "output_root": Path(temp_dir) / "smoke",
            "strategy_output_dir": self._track_strategy_dir(),
        }
        base.update(overrides)
        return SmokeRunConfig(**base)

    def test_two_generation_mock_smoke_run_writes_traceable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_smoke_ga_pipeline(self._config(temp_dir))
            run_summary = json.loads(Path(result.run_summary_path).read_text(encoding="utf-8"))
            final_best = json.loads(Path(result.final_best_path).read_text(encoding="utf-8"))

        self.assertTrue(result.success)
        self.assertEqual(result.completed, 2)
        self.assertEqual(len(result.generation_results), 2)
        self.assertIn("genes", final_best)
        self.assertIn("bb_period_15m", final_best["genes"])
        self.assertIsInstance(final_best["genes_hash"], str)
        self.assertTrue(final_best["strategy_name"].startswith("BollingerResonance_Gen"))
        self.assertTrue(Path(final_best["strategy_path"]).exists())
        self.assertTrue(final_best["mock_evaluation"])
        self.assertIn("position_sizing", final_best["metrics"])
        self.assertIn("custom_stake_amount", final_best["metrics"]["position_sizing"])
        self.assertEqual(len(run_summary["generation_results"]), 2)
        self.assertTrue(run_summary["mock_evaluation"])

    def test_failed_individual_does_not_become_champion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_smoke_ga_pipeline(
                self._config(temp_dir, fail_individual_indexes=(0,))
            )
            final_best = json.loads(Path(result.final_best_path).read_text(encoding="utf-8"))

        self.assertTrue(result.success)
        self.assertNotIn("forced_failure", final_best["metrics"])
        self.assertNotEqual(final_best.get("reason"), "forced_smoke_failure")
        self.assertTrue(all(item.best is None or item.best.success for item in result.generation_results))

    def test_sensitive_fields_do_not_enter_artifacts(self) -> None:
        initial_population = [
            dict(_valid_genes(bb_period_15m=20), api_key="secret-a", token="secret-b"),
            _valid_genes(bb_period_15m=35),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_smoke_ga_pipeline(
                self._config(temp_dir, population_size=3),
                initial_population=initial_population,
            )
            run_summary_text = Path(result.run_summary_path).read_text(encoding="utf-8")
            final_best_text = Path(result.final_best_path).read_text(encoding="utf-8")

        self.assertNotIn("secret-a", run_summary_text)
        self.assertNotIn("secret-b", run_summary_text)
        self.assertNotIn("secret-a", final_best_text)
        self.assertNotIn("secret-b", final_best_text)

    def test_deterministic_seed_reproduces_best_fitness_and_gene_hash(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = run_smoke_ga_pipeline(
                self._config(first_dir, seed=202, run_id="det-a")
            )
            second = run_smoke_ga_pipeline(
                self._config(second_dir, seed=202, run_id="det-b")
            )

        self.assertEqual(first.best_fitness_score, second.best_fitness_score)
        self.assertEqual(first.best_candidate["genes_hash"], second.best_candidate["genes_hash"])

    def test_backtest_disabled_mode_stops_safely_without_successful_champion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_smoke_ga_pipeline(
                self._config(
                    temp_dir,
                    evaluation_mode="backtest_disabled",
                    allow_real_backtest=False,
                    population_size=2,
                )
            )

        self.assertFalse(result.success)
        self.assertEqual(result.completed, 1)
        self.assertIsNone(result.best_candidate)
        self.assertEqual(result.reason, "no_successful_individuals")

    def test_backtest_disabled_mode_rejects_real_backtest_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "backtest_disabled mode cannot enable"):
                run_smoke_ga_pipeline(
                    self._config(
                        temp_dir,
                        evaluation_mode="backtest_disabled",
                        allow_real_backtest=True,
                        population_size=2,
                    )
                )

    def test_data_quality_gate_failure_prevents_final_best(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_smoke_ga_pipeline(
                self._config(
                    temp_dir,
                    population_size=2,
                    data_coverage_manifest=_bad_manifest(),
                )
            )

        self.assertFalse(result.success)
        self.assertIsNone(result.best_candidate)
        self.assertEqual(result.reason, "no_successful_individuals")

    def test_position_sizing_snapshot_contains_expected_strategy_controls(self) -> None:
        snapshot = build_position_sizing_snapshot(
            _valid_genes(),
            {"win_rate": 85.0},
        )

        self.assertIn("custom_stake_amount", snapshot)
        self.assertIn("adjust_trade_position", snapshot)
        self.assertIn("leverage", snapshot)
        self.assertIn("stoploss", snapshot)
        self.assertLessEqual(snapshot["leverage"], DEFAULT_GENES["max_strategy_leverage"])
        self.assertLessEqual(snapshot["stoploss"], 0.0)

    def test_module_imports_cleanly(self) -> None:
        module = importlib.import_module("bollinger_evolver.ga.smoke_run_pipeline")

        self.assertTrue(hasattr(module, "run_smoke_ga_pipeline"))


if __name__ == "__main__":
    unittest.main()
