"""Tests for the real backtest evaluation adapter safe mode."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from bollinger_evolver.evaluators import FitnessConfig
from bollinger_evolver.ga import GenerationConfig, run_generation
from bollinger_evolver.ga.backtest_evaluation_adapter import (
    BacktestEvaluationAdapter,
    calculate_basic_backtest_fitness,
)
from bollinger_evolver.strategy_factory import GENERATED_ROOT
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


def _valid_genes(**overrides: object) -> dict:
    genes = dict(DEFAULT_GENES)
    genes.update(overrides)
    return genes


def _fitness_config() -> FitnessConfig:
    return FitnessConfig(
        strategy="BollingerResonance_Gen001_Ind001",
        config_path="config.json",
        timerange="20240101-20240201",
        timeframe="15m",
        pairs=("BTC/USDT",),
        result_dir="results/bollinger_evolver/backtests",
        timeout_seconds=120,
        failed_score=-1_000_000.0,
    )


def _good_manifest() -> dict:
    return {
        "status": "ready",
        "pairs": ["BTC/USDT"],
        "timeframes": ["15m"],
        "expected_file_count": 1,
        "missing_count": 0,
        "limited_count": 0,
        "invalid_ohlc_count": 0,
        "gap_count": 0,
        "entries": [
            {
                "pair": "BTC/USDT",
                "timeframe": "15m",
                "status": "ready",
                "row_count": 500,
                "gap_count": 0,
                "invalid_ohlc_count": 0,
            }
        ],
    }


class TestCalculateBasicBacktestFitness(unittest.TestCase):
    def test_accepts_profitable_metrics(self) -> None:
        fitness, breakdown = calculate_basic_backtest_fitness(
            {
                "profit_total_pct": 12.0,
                "max_drawdown": 4.0,
                "profit_factor": 1.6,
                "trade_count": 20,
            }
        )

        self.assertIsInstance(fitness, float)
        self.assertTrue(breakdown["accepted"])
        self.assertEqual(breakdown["reason"], "accepted")

    def test_rejects_nonpositive_profit(self) -> None:
        fitness, breakdown = calculate_basic_backtest_fitness(
            {
                "profit_total_pct": 0.0,
                "max_drawdown": 4.0,
                "profit_factor": 1.6,
                "trade_count": 20,
            }
        )

        self.assertIsNone(fitness)
        self.assertEqual(breakdown["reason"], "nonpositive_total_profit")

    def test_rejects_low_trade_count(self) -> None:
        fitness, breakdown = calculate_basic_backtest_fitness(
            {
                "profit_total_pct": 12.0,
                "max_drawdown": 4.0,
                "profit_factor": 1.6,
                "trade_count": 0,
            }
        )

        self.assertIsNone(fitness)
        self.assertEqual(breakdown["reason"], "low_trade_count")

    def test_rejects_low_profit_factor(self) -> None:
        fitness, breakdown = calculate_basic_backtest_fitness(
            {
                "profit_total_pct": 12.0,
                "max_drawdown": 4.0,
                "profit_factor": 0.9,
                "trade_count": 20,
            }
        )

        self.assertIsNone(fitness)
        self.assertEqual(breakdown["reason"], "low_profit_factor")

    def test_rejects_excessive_drawdown(self) -> None:
        fitness, breakdown = calculate_basic_backtest_fitness(
            {
                "profit_total_pct": 12.0,
                "max_drawdown": 80.0,
                "profit_factor": 1.6,
                "trade_count": 20,
            }
        )

        self.assertIsNone(fitness)
        self.assertEqual(breakdown["reason"], "max_drawdown_too_high")


class TestBacktestEvaluationAdapter(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy_output_dir = GENERATED_ROOT / f"test_backtest_adapter_{uuid.uuid4().hex}"
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.config_path = self.workspace / "config.json"
        self.config_path.write_text("{}", encoding="utf-8")
        self.export_dir = self.workspace / "exports"

    def tearDown(self) -> None:
        if self.strategy_output_dir.exists():
            shutil.rmtree(self.strategy_output_dir)
        self.temp_dir.cleanup()

    def _adapter(self, **overrides: object) -> BacktestEvaluationAdapter:
        base = {
            "config_path": str(self.config_path),
            "timerange": "20240101-20240201",
            "strategy_output_dir": self.strategy_output_dir,
            "export_dir": self.export_dir,
            "overwrite": True,
            "data_coverage_manifest": _good_manifest(),
            "required_pairs": ["BTC/USDT"],
            "required_timeframes": ["15m"],
        }
        base.update(overrides)
        return BacktestEvaluationAdapter(**base)

    def test_default_disabled_generates_strategy_but_does_not_call_runner(self) -> None:
        def forbidden_runner(**_: object) -> dict:
            raise AssertionError("runner must not be called when real backtest is disabled")

        result = self._adapter(runner=forbidden_runner).evaluate(
            _valid_genes(),
            generation=1,
            individual_index=2,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "real_backtest_disabled")
        self.assertIsNone(result["fitness"])
        self.assertEqual(result["fitness_score"], -1_000_000.0)
        self.assertFalse(result["mock_evaluation"])
        self.assertFalse(result["real_backtest"])
        self.assertFalse(result["metrics"]["mock"])
        self.assertFalse(result["metrics"]["real_backtest"])
        self.assertTrue(result["metrics"]["dataQualityGate"]["allowed_for_evaluation"])
        self.assertTrue(Path(result["strategy_path"]).exists())

    def test_data_quality_gate_failed_does_not_call_runner(self) -> None:
        def forbidden_runner(**_: object) -> dict:
            raise AssertionError("runner must not be called when data quality gate fails")

        manifest = _good_manifest()
        manifest["entries"][0]["row_count"] = 5
        result = self._adapter(
            allow_real_backtest=True,
            runner=forbidden_runner,
            data_coverage_manifest=manifest,
        ).evaluate(_valid_genes(), generation=1, individual_index=0)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "data_quality_gate_failed")
        self.assertIsNone(result["strategy_path"])
        self.assertFalse(result["metrics"]["dataQualityGate"]["allowed_for_evaluation"])

    def test_enabled_real_backtest_calls_runner_and_returns_fitness(self) -> None:
        calls: list[dict] = []

        def fake_runner(**kwargs: object) -> dict:
            calls.append(dict(kwargs))
            return {
                "success": True,
                "metrics": {
                    "profit_total_pct": 15.0,
                    "max_drawdown": 3.0,
                    "profit_factor": 1.8,
                    "trade_count": 30,
                },
            }

        result = self._adapter(
            allow_real_backtest=True,
            runner=fake_runner,
        ).evaluate(_valid_genes(), generation=3, individual_index=4)

        self.assertEqual(len(calls), 1)
        self.assertTrue(result["success"])
        self.assertTrue(result["real_backtest"])
        self.assertFalse(result["mock_evaluation"])
        self.assertIsInstance(result["fitness"], float)
        self.assertEqual(result["fitness"], result["fitness_score"])
        self.assertEqual(result["strategy_name"], "BollingerResonance_Gen003_Ind004")
        self.assertTrue(Path(result["strategy_path"]).exists())
        self.assertIn("genes_hash", result)
        self.assertFalse(result["metrics"]["mock"])
        self.assertTrue(result["metrics"]["real_backtest"])
        self.assertEqual(calls[0]["strategy_name"], result["strategy_name"])
        self.assertEqual(calls[0]["strategy_path"], result["strategy_path"])

    def test_runner_failure_returns_failed_result(self) -> None:
        def fake_runner(**_: object) -> dict:
            return {"success": False, "error": "freqtrade executable not found", "metrics": {}}

        result = self._adapter(
            allow_real_backtest=True,
            runner=fake_runner,
        ).evaluate(_valid_genes(), generation=1, individual_index=0)

        self.assertFalse(result["success"])
        self.assertIsNone(result["fitness"])
        self.assertEqual(result["fitness_score"], -1_000_000.0)
        self.assertEqual(result["error"], "freqtrade executable not found")
        self.assertTrue(result["metrics"]["real_backtest"])

    def test_successful_runner_with_insufficient_metrics_fails_clearly(self) -> None:
        def fake_runner(**_: object) -> dict:
            return {"success": True, "metrics": {"profit_total_pct": 12.0}}

        result = self._adapter(
            allow_real_backtest=True,
            runner=fake_runner,
        ).evaluate(_valid_genes(), generation=1, individual_index=0)

        self.assertFalse(result["success"])
        self.assertIsNone(result["fitness"])
        self.assertEqual(result["error"], "missing_trade_count")
        self.assertIn("fitness_breakdown", result["metrics"])

    def test_invalid_genes_fail_before_runner(self) -> None:
        calls: list[dict] = []

        def fake_runner(**kwargs: object) -> dict:
            calls.append(dict(kwargs))
            return {"success": True, "metrics": {}}

        genes = _valid_genes()
        genes.pop("mode")
        result = self._adapter(
            allow_real_backtest=True,
            runner=fake_runner,
        ).evaluate(genes, generation=1, individual_index=0)

        self.assertFalse(result["success"])
        self.assertEqual(calls, [])
        self.assertIsNone(result["strategy_path"])
        self.assertIsNone(result["fitness"])

    def test_sensitive_fields_are_filtered_from_result_and_runner_args(self) -> None:
        runner_calls: list[dict] = []

        def fake_runner(**kwargs: object) -> dict:
            runner_calls.append(dict(kwargs))
            return {
                "success": True,
                "metrics": {
                    "profit_total_pct": 10.0,
                    "max_drawdown": 2.0,
                    "profit_factor": 1.5,
                    "trade_count": 12,
                    "api_secret": "metric-secret",
                },
                "token": "runner-secret",
            }

        result = self._adapter(
            allow_real_backtest=True,
            runner=fake_runner,
            extra_args={"fee": 0.001, "api_key": "arg-secret", "webhook": "hook-secret"},
        ).evaluate(
            dict(_valid_genes(), token="candidate-secret", private_key="private-secret"),
            generation=1,
            individual_index=0,
        )

        serialized = json.dumps(result, sort_keys=True, default=str)
        self.assertNotIn("candidate-secret", serialized)
        self.assertNotIn("private-secret", serialized)
        self.assertNotIn("runner-secret", serialized)
        self.assertNotIn("metric-secret", serialized)
        self.assertEqual(runner_calls[0]["extra_args"], {"fee": 0.001})

    def test_generated_strategy_source_compiles(self) -> None:
        result = self._adapter().evaluate(_valid_genes(), generation=2, individual_index=5)
        source = Path(result["strategy_path"]).read_text(encoding="utf-8")

        compile(source, result["strategy_path"], "exec")

    def test_disabled_adapter_does_not_create_champion_in_generation_runner(self) -> None:
        adapter = self._adapter()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [_valid_genes(), _valid_genes(bb_period_15m=30)],
                _fitness_config(),
                GenerationConfig(
                    generation_index=1,
                    output_dir=Path(temp_dir) / "generations",
                    best_dir=Path(temp_dir) / "best",
                ),
                evaluator=adapter,
            )

        self.assertFalse(result.success)
        self.assertIsNone(result.best)
        self.assertEqual(result.reason, "no_successful_individuals")
        self.assertEqual(result.success_count, 0)


if __name__ == "__main__":
    unittest.main()
