"""Tests for formal Bollinger Evolver fitness scoring."""

from __future__ import annotations

import math
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from bollinger_evolver.evaluators import FitnessConfig
from bollinger_evolver.ga.backtest_evaluation_adapter import BacktestEvaluationAdapter
from bollinger_evolver.ga.evaluation_pipeline import MockStrategyEvaluator
from bollinger_evolver.ga.generation_runner import GenerationConfig, run_generation
from bollinger_evolver.scoring.fitness import calculate_fitness
from bollinger_evolver.strategy_factory import GENERATED_ROOT
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


def _good_metrics(**overrides: object) -> dict:
    metrics = {
        "total_profit": 0.18,
        "profit_total_abs": 180.0,
        "profit_total_pct": 18.0,
        "max_drawdown": 0.08,
        "profit_factor": 1.7,
        "sharpe": 1.2,
        "sortino": 1.5,
        "calmar": 2.25,
        "trade_count": 60,
        "win_rate": 0.58,
        "avg_trade_duration": "01:20:00",
    }
    metrics.update(overrides)
    return metrics


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


class TestFitnessScoring(unittest.TestCase):
    def test_profitable_low_drawdown_enough_trades_is_accepted(self) -> None:
        fitness, breakdown = calculate_fitness(_good_metrics())

        self.assertIsInstance(fitness, float)
        self.assertTrue(breakdown["accepted"])
        self.assertIsNone(breakdown["reject_reason"])
        self.assertIn("profit_score", breakdown["scores"])
        self.assertIn("drawdown_penalty", breakdown["penalties"])

    def test_low_trade_count_hard_rejects(self) -> None:
        fitness, breakdown = calculate_fitness(_good_metrics(trade_count=5))

        self.assertIsNotNone(fitness)
        self.assertFalse(breakdown["accepted"])
        self.assertIn("trade_count_below_min", breakdown["hard_rejects"])

    def test_low_profit_factor_hard_rejects(self) -> None:
        _, breakdown = calculate_fitness(_good_metrics(profit_factor=0.9))

        self.assertFalse(breakdown["accepted"])
        self.assertEqual(breakdown["reject_reason"], "profit_factor_below_min")

    def test_excessive_drawdown_hard_rejects(self) -> None:
        _, breakdown = calculate_fitness(_good_metrics(max_drawdown=0.5))

        self.assertFalse(breakdown["accepted"])
        self.assertIn("max_drawdown_above_limit", breakdown["hard_rejects"])

    def test_nonpositive_total_profit_hard_rejects(self) -> None:
        _, breakdown = calculate_fitness(_good_metrics(total_profit=-0.01, profit_total_pct=-1.0))

        self.assertFalse(breakdown["accepted"])
        self.assertIn("nonpositive_total_profit", breakdown["hard_rejects"])

    def test_nonpositive_oos_profit_hard_rejects_when_present(self) -> None:
        _, breakdown = calculate_fitness(_good_metrics(oos_profit=0.0))

        self.assertFalse(breakdown["accepted"])
        self.assertIn("oos_profit_below_min", breakdown["hard_rejects"])

    def test_train_oos_gap_penalizes_otherwise_valid_strategy(self) -> None:
        clean_fitness, clean_breakdown = calculate_fitness(_good_metrics(oos_profit=0.12))
        gap_fitness, gap_breakdown = calculate_fitness(
            _good_metrics(oos_profit=0.12, train_profit=0.8, train_oos_gap=0.6)
        )

        self.assertTrue(clean_breakdown["accepted"])
        self.assertTrue(gap_breakdown["accepted"])
        self.assertGreater(gap_breakdown["penalties"]["train_oos_gap_penalty"], 0.0)
        self.assertLess(gap_fitness, clean_fitness)

    def test_bad_worst_window_profit_hard_rejects(self) -> None:
        _, breakdown = calculate_fitness(_good_metrics(worst_window_profit=-0.25))

        self.assertFalse(breakdown["accepted"])
        self.assertIn("worst_window_profit_below_min", breakdown["hard_rejects"])

    def test_high_turnover_penalizes_fitness(self) -> None:
        normal_fitness, _ = calculate_fitness(_good_metrics(turnover=100))
        churn_fitness, churn_breakdown = calculate_fitness(_good_metrics(turnover=1000))

        self.assertGreater(churn_breakdown["penalties"]["turnover_penalty"], 0.0)
        self.assertLess(churn_fitness, normal_fitness)

    def test_nan_and_inf_inputs_do_not_return_nan_fitness(self) -> None:
        fitness, breakdown = calculate_fitness(
            {
                "total_profit": math.inf,
                "profit_factor": math.nan,
                "max_drawdown": math.inf,
                "trade_count": 60,
            }
        )

        self.assertFalse(breakdown["accepted"])
        self.assertIsNotNone(fitness)
        self.assertTrue(math.isfinite(float(fitness)))

    def test_missing_fields_conservatively_reject(self) -> None:
        _, breakdown = calculate_fitness({"total_profit": 0.1})

        self.assertFalse(breakdown["accepted"])
        self.assertIn("missing_trade_count", breakdown["hard_rejects"])

    def test_data_quality_gate_false_hard_rejects(self) -> None:
        _, breakdown = calculate_fitness(
            _good_metrics(
                dataQualityGate={
                    "status": "FAIL",
                    "allowed_for_evaluation": False,
                    "fail_reasons": ["low_candle_count"],
                }
            )
        )

        self.assertFalse(breakdown["accepted"])
        self.assertIn("data_quality_gate_failed", breakdown["hard_rejects"])

    def test_mock_metrics_preserve_mock_flag_in_breakdown(self) -> None:
        _, breakdown = calculate_fitness(_good_metrics(mock=True))

        self.assertTrue(breakdown["raw_metrics"]["mock"])

    def test_walk_forward_result_affects_stability_score(self) -> None:
        stable_fitness, stable_breakdown = calculate_fitness(
            _good_metrics(oos_profit=0.12),
            walk_forward_result={
                "summary": {"avg_oos_profit": 0.12, "worst_oos_profit": -0.05, "pass_rate": 1.0},
                "windows": [],
            },
        )
        weak_fitness, weak_breakdown = calculate_fitness(
            _good_metrics(oos_profit=0.12),
            walk_forward_result={
                "summary": {"avg_oos_profit": 0.12, "worst_oos_profit": -0.10, "pass_rate": 0.25},
                "windows": [],
            },
        )

        self.assertTrue(stable_breakdown["accepted"])
        self.assertTrue(weak_breakdown["accepted"])
        self.assertLess(weak_breakdown["scores"]["stability_score"], stable_breakdown["scores"]["stability_score"])
        self.assertLess(weak_fitness, stable_fitness)


class TestFitnessIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.strategy_output_dir = GENERATED_ROOT / f"test_fitness_{uuid.uuid4().hex}"

    def tearDown(self) -> None:
        if self.strategy_output_dir.exists():
            shutil.rmtree(self.strategy_output_dir)

    def test_accepted_false_mapping_does_not_become_generation_champion(self) -> None:
        def fake_evaluator(candidate: dict, fitness_config: FitnessConfig, **_: object) -> dict:
            if candidate["id"] == "bad":
                return {
                    "success": True,
                    "fitness": 999.0,
                    "fitness_score": 999.0,
                    "metrics": {
                        "fitness_breakdown": {
                            "accepted": False,
                            "reject_reason": "profit_factor_below_min",
                        }
                    },
                    "genes": {"id": "bad"},
                    "params": {},
                }
            return {
                "success": True,
                "fitness": 1.0,
                "fitness_score": 1.0,
                "metrics": {
                    "fitness_breakdown": {
                        "accepted": True,
                        "reject_reason": None,
                    }
                },
                "genes": {"id": "good"},
                "params": {},
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [{"id": "bad"}, {"id": "good"}],
                _fitness_config(),
                GenerationConfig(
                    generation_index=1,
                    output_dir=Path(temp_dir) / "generations",
                    best_dir=Path(temp_dir) / "best",
                ),
                evaluator=fake_evaluator,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.best.candidate["id"], "good")

    def test_mock_evaluator_returns_fitness_breakdown(self) -> None:
        evaluator = MockStrategyEvaluator(
            seed=123,
            strategy_output_dir=self.strategy_output_dir,
            overwrite=True,
            data_coverage_manifest=_good_manifest(),
            required_pairs=["BTC/USDT"],
            required_timeframes=["15m"],
        )
        result = evaluator.evaluate(
            dict(DEFAULT_GENES),
            generation=1,
            output_root=str(self.strategy_output_dir),
            individual_index=1,
        )

        self.assertTrue(result["success"])
        self.assertIn("fitness_breakdown", result["metrics"])
        self.assertTrue(result["metrics"]["fitness_breakdown"]["accepted"])

    def test_backtest_adapter_returns_fitness_breakdown(self) -> None:
        def fake_runner(**_: object) -> dict:
            return {"success": True, "metrics": _good_metrics(real_backtest=True)}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text("{}", encoding="utf-8")
            adapter = BacktestEvaluationAdapter(
                config_path=str(config_path),
                timerange="20240101-20240201",
                strategy_output_dir=self.strategy_output_dir,
                export_dir=Path(temp_dir) / "exports",
                allow_real_backtest=True,
                runner=fake_runner,
                overwrite=True,
                data_coverage_manifest=_good_manifest(),
                required_pairs=["BTC/USDT"],
                required_timeframes=["15m"],
            )
            result = adapter.evaluate(dict(DEFAULT_GENES), generation=1, individual_index=1)

        self.assertTrue(result["success"])
        self.assertIn("fitness_breakdown", result["metrics"])
        self.assertTrue(result["metrics"]["fitness_breakdown"]["accepted"])


if __name__ == "__main__":
    unittest.main()
