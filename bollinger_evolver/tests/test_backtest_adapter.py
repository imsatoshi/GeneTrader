"""Tests for the mock synthetic backtest adapter."""

from __future__ import annotations

from dataclasses import asdict
import json
import random
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.backtest_adapter import (
    AdapterBackedMockEvaluator,
    MockBacktestAdapter,
    MockBacktestEvaluator,
    NormalizedBacktestResult,
    SyntheticTrade,
    calculate_backtest_metrics,
    generate_synthetic_trades,
    run_mock_backtest,
    validate_normalized_backtest_result,
)
from bollinger_evolver.artifact_export import write_all_generation_artifacts
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.genome import Genome, create_population
from bollinger_evolver.session_summary import build_ga_session_summary
from bollinger_evolver.strategy_factory import strategy_config_from_genome


def _moderate_genome(genome_id: str = "moderate") -> Genome:
    return Genome(
        genome_id=genome_id,
        parameters={
            "bb_window": 34,
            "bb_stddev": 2.1,
            "stop_loss_pct": 0.03,
            "take_profit_pct": 0.08,
            "leverage": 2.0,
            "risk_per_trade": 0.01,
        },
    )


class TestSyntheticTrades(unittest.TestCase):
    def test_generate_synthetic_trades_is_deterministic(self) -> None:
        config = strategy_config_from_genome(_moderate_genome())

        first = generate_synthetic_trades(config, trade_count=12, seed=7)
        second = generate_synthetic_trades(config, trade_count=12, seed=7)

        self.assertEqual(first, second)

    def test_generate_synthetic_trades_returns_requested_count(self) -> None:
        config = strategy_config_from_genome(_moderate_genome())

        trades = generate_synthetic_trades(config, trade_count=17, seed=3)

        self.assertEqual(len(trades), 17)
        self.assertTrue(all(isinstance(trade, SyntheticTrade) for trade in trades))

    def test_trade_entries_are_json_safe(self) -> None:
        config = strategy_config_from_genome(_moderate_genome())
        trades = generate_synthetic_trades(config, trade_count=3, seed=1)

        encoded = json.dumps([trade.to_dict() for trade in trades], sort_keys=True)

        self.assertIn("pnl_pct", encoded)
        self.assertIn("BTC/USDT", encoded)


class TestBacktestMetrics(unittest.TestCase):
    def test_calculate_backtest_metrics_contains_required_fields(self) -> None:
        config = strategy_config_from_genome(_moderate_genome())
        trades = generate_synthetic_trades(config, trade_count=20, seed=9)

        metrics = calculate_backtest_metrics(trades, leverage=2.0, risk_per_trade=0.01)

        self.assertEqual(
            set(metrics),
            {"profit", "drawdown", "sharpe", "win_rate", "max_loss_streak", "trade_count"},
        )

    def test_calculate_backtest_metrics_computes_win_rate(self) -> None:
        trades = [
            SyntheticTrade("t1", "BTC/USDT", "1h", 0, 1, "long", 100, 101, 0.01, 1, 0.01, 0.01),
            SyntheticTrade("t2", "BTC/USDT", "1h", 2, 3, "long", 100, 99, -0.01, 1, 0.01, -0.01),
            SyntheticTrade("t3", "BTC/USDT", "1h", 4, 5, "long", 100, 102, 0.02, 1, 0.01, 0.02),
        ]

        metrics = calculate_backtest_metrics(trades, leverage=1.0, risk_per_trade=0.01)

        self.assertEqual(metrics["win_rate"], 0.666667)

    def test_calculate_backtest_metrics_computes_max_loss_streak(self) -> None:
        trades = [
            SyntheticTrade(f"t{index}", "BTC/USDT", "1h", index, index + 1, "long", 100, 99, -0.01, 1, 0.01, -0.01)
            for index in range(3)
        ]
        trades.append(SyntheticTrade("t4", "BTC/USDT", "1h", 4, 5, "long", 100, 101, 0.01, 1, 0.01, 0.01))

        metrics = calculate_backtest_metrics(trades, leverage=1.0, risk_per_trade=0.01)

        self.assertEqual(metrics["max_loss_streak"], 3)

    def test_calculate_backtest_metrics_computes_drawdown(self) -> None:
        trades = [
            SyntheticTrade("t1", "BTC/USDT", "1h", 0, 1, "long", 100, 110, 0.1, 1, 0.01, 0.1),
            SyntheticTrade("t2", "BTC/USDT", "1h", 2, 3, "long", 100, 80, -0.2, 1, 0.01, -0.2),
        ]

        metrics = calculate_backtest_metrics(trades, leverage=1.0, risk_per_trade=0.01)

        self.assertGreater(metrics["drawdown"], 0.0)


class TestMockBacktestAdapter(unittest.TestCase):
    def test_normalized_backtest_result_is_frozen_and_json_safe(self) -> None:
        result = NormalizedBacktestResult(
            profit=0.2,
            sharpe=1.1,
            win_rate=0.55,
            max_drawdown=0.08,
            total_trades=20,
            max_consecutive_losses=3,
            leverage=2.0,
            risk_per_trade=0.01,
        )

        encoded = json.dumps(asdict(result), sort_keys=True)

        self.assertIn("max_drawdown", encoded)
        with self.assertRaises(Exception):
            result.profit = 0.3  # type: ignore[misc]

    def test_validate_normalized_backtest_result_rejects_invalid_values(self) -> None:
        invalid = NormalizedBacktestResult(
            profit=0.2,
            sharpe=1.1,
            win_rate=1.5,
            max_drawdown=0.08,
            total_trades=20,
            max_consecutive_losses=3,
            leverage=2.0,
            risk_per_trade=0.01,
        )

        with self.assertRaises(ValueError):
            validate_normalized_backtest_result(invalid)

    def test_mock_backtest_adapter_is_deterministic(self) -> None:
        adapter = MockBacktestAdapter(seed=17, trade_count=30)
        genome = {
            "genome_id": "contract-genome",
            "bb_period": 20,
            "bb_stddev": 2.0,
            "stop_loss": 0.02,
            "take_profit": 0.04,
            "leverage": 1.0,
            "risk_per_trade": 0.01,
        }

        first = adapter.run_backtest(genome)
        second = adapter.run_backtest(genome)

        self.assertEqual(first, second)

    def test_mock_backtest_adapter_result_is_json_safe_and_bounded(self) -> None:
        result = MockBacktestAdapter(seed=18, trade_count=25).run_backtest(
            {
                "bb_period": 20,
                "bb_stddev": 2.0,
                "stop_loss": 0.02,
                "take_profit": 0.04,
                "leverage": 1.0,
                "risk_per_trade": 0.01,
            }
        )

        json.dumps(asdict(result), sort_keys=True)
        self.assertGreaterEqual(result.win_rate, 0.0)
        self.assertLessEqual(result.win_rate, 1.0)
        self.assertGreaterEqual(result.max_drawdown, 0.0)
        self.assertLessEqual(result.max_drawdown, 1.0)
        self.assertGreaterEqual(result.total_trades, 0)
        self.assertGreaterEqual(result.max_consecutive_losses, 0)
        self.assertGreaterEqual(result.leverage, 0.0)
        self.assertGreaterEqual(result.risk_per_trade, 0.0)

    def test_high_risk_genome_produces_worse_risk_profile(self) -> None:
        adapter = MockBacktestAdapter(seed=19, trade_count=80)
        conservative = {
            "bb_period": 20,
            "bb_stddev": 2.0,
            "stop_loss": 0.02,
            "take_profit": 0.04,
            "leverage": 1.0,
            "risk_per_trade": 0.01,
        }
        aggressive = {
            "bb_period": 5,
            "bb_stddev": 4.0,
            "stop_loss": 0.10,
            "take_profit": 0.20,
            "leverage": 10.0,
            "risk_per_trade": 0.08,
        }

        conservative_result = adapter.run_backtest(conservative)
        aggressive_result = adapter.run_backtest(aggressive)

        self.assertGreater(aggressive_result.max_drawdown, conservative_result.max_drawdown)
        self.assertGreaterEqual(
            aggressive_result.max_consecutive_losses,
            conservative_result.max_consecutive_losses,
        )
        self.assertGreater(aggressive_result.leverage, conservative_result.leverage)
        self.assertGreater(aggressive_result.risk_per_trade, conservative_result.risk_per_trade)

    def test_adapter_backed_evaluator_output_shape(self) -> None:
        genome = _moderate_genome()

        evaluation = AdapterBackedMockEvaluator(
            MockBacktestAdapter(seed=20, trade_count=30)
        ).evaluate(genome)

        self.assertIsInstance(evaluation.fitness, float)
        self.assertIn("final_fitness", evaluation.metrics.fitness_components)
        self.assertGreaterEqual(evaluation.metrics.max_consecutive_losses, 0)
        self.assertGreaterEqual(evaluation.metrics.leverage, 0.0)
        self.assertGreaterEqual(evaluation.metrics.risk_per_trade, 0.0)

    def test_adapter_backed_ga_execution_e2e_artifact_smoke(self) -> None:
        result = run_ga_execution(
            GAExecutionConfig(population_size=5, generations=2, seed=22),
            evaluator=AdapterBackedMockEvaluator(MockBacktestAdapter(seed=22, trade_count=18)),
        )
        summary = build_ga_session_summary(result, top_n=3, run_id="adapter-contract-smoke")
        scores = [entry["fitness"] for entry in summary["leaderboard"]]

        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([entry["generation"] for entry in summary["fitness_series"]], [1, 2])
        self.assertIn("fitness_components", summary["leaderboard"][0])
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_all_generation_artifacts(result, tmp, top_n=3, run_id="adapter-contract-smoke")
            loaded = [json.loads(Path(path).read_text(encoding="utf-8")) for path in paths]

        self.assertEqual([item["generation"] for item in loaded], [1, 2])
        self.assertIn("risk_per_trade", loaded[-1]["genomes"][0])

    def test_run_mock_backtest_returns_json_safe_result(self) -> None:
        config = strategy_config_from_genome(_moderate_genome())

        result = run_mock_backtest(config, trade_count=10, seed=2)

        encoded = json.dumps(result.to_dict(), sort_keys=True)
        self.assertIn("mock-backtest-result/v1", encoded)

    def test_run_mock_backtest_includes_risk_aware_fitness_components(self) -> None:
        result = run_mock_backtest(_moderate_genome(), trade_count=20, seed=4)

        self.assertIn("drawdown_penalty", result.fitness_components)
        self.assertEqual(result.fitness, result.fitness_components["final_fitness"])

    def test_high_leverage_strategy_gets_penalized_vs_moderate_leverage(self) -> None:
        moderate = _moderate_genome("moderate")
        aggressive = Genome(
            genome_id="aggressive",
            parameters={**moderate.parameters, "leverage": 8.0, "risk_per_trade": 0.04},
        )

        moderate_result = run_mock_backtest(moderate, trade_count=80, seed=11)
        aggressive_result = run_mock_backtest(aggressive, trade_count=80, seed=11)

        self.assertLess(aggressive_result.fitness, moderate_result.fitness)

    def test_mock_backtest_evaluator_can_evaluate_genome(self) -> None:
        genome = create_population(1, random.Random(5))[0]

        evaluation = MockBacktestEvaluator(seed=5, trade_count=24).evaluate(genome)

        self.assertEqual(evaluation.genome, genome)
        self.assertEqual(evaluation.fitness, evaluation.metrics.fitness_components["final_fitness"])
        self.assertGreaterEqual(evaluation.metrics.max_consecutive_losses, 0)

    def test_ga_execution_can_use_mock_backtest_evaluator(self) -> None:
        evaluator = MockBacktestEvaluator(seed=21, trade_count=16)
        result = run_ga_execution(
            GAExecutionConfig(population_size=5, generations=2, seed=21),
            evaluator=evaluator,
        )

        self.assertEqual(len(result.generations), 2)
        self.assertIsNotNone(result.final_best)
        self.assertEqual(len(result.generations[-1].evaluations), 5)


if __name__ == "__main__":
    unittest.main()
