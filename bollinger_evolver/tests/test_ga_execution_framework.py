"""Tests for the lightweight mock-first GA execution framework."""

from __future__ import annotations

import json
import random
import unittest

from bollinger_evolver.backtest_adapter import MockBacktestEvaluator
from bollinger_evolver.fitness import MockEvaluator
from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.genome import create_population, validate_genome
from bollinger_evolver.session_summary import build_ga_session_summary


class TestGenomePopulation(unittest.TestCase):
    def test_population_generation_returns_requested_count(self) -> None:
        population = create_population(6, random.Random(42))

        self.assertEqual(len(population), 6)
        for genome in population:
            validate_genome(genome)

    def test_population_generation_is_seeded(self) -> None:
        first = create_population(4, random.Random(7))
        second = create_population(4, random.Random(7))

        self.assertEqual(first, second)


class TestMockEvaluator(unittest.TestCase):
    def test_evaluator_returns_reproducible_metrics(self) -> None:
        genome = create_population(1, random.Random(11))[0]

        first = MockEvaluator(seed=99).evaluate(genome)
        second = MockEvaluator(seed=99).evaluate(genome)

        self.assertEqual(first.metrics, second.metrics)
        self.assertEqual(first.fitness, second.fitness)
        self.assertGreaterEqual(first.metrics.win_rate, 0.0)
        self.assertLessEqual(first.metrics.drawdown, 0.85)

    def test_mock_evaluator_returns_risk_aware_fields(self) -> None:
        genome = create_population(1, random.Random(14))[0]

        result = MockEvaluator(seed=14).evaluate(genome)

        self.assertGreaterEqual(result.metrics.max_consecutive_losses, 0)
        self.assertGreaterEqual(result.metrics.leverage, 1.0)
        self.assertGreaterEqual(result.metrics.risk_per_trade, 0.0)
        self.assertIn("drawdown_penalty", result.metrics.fitness_components)
        self.assertEqual(result.fitness, result.metrics.fitness_components["final_fitness"])


class TestGAExecutionLoop(unittest.TestCase):
    def test_generation_loop_evaluates_each_generation(self) -> None:
        config = GAExecutionConfig(population_size=8, generations=3, seed=123)

        result = run_ga_execution(config)

        self.assertEqual(len(result.generations), 3)
        self.assertIsNotNone(result.final_best)
        for generation in result.generations:
            self.assertEqual(len(generation.population), 8)
            self.assertEqual(len(generation.evaluations), 8)
            self.assertIsInstance(generation.best.fitness, float)
            self.assertGreaterEqual(generation.diversity, 0.0)
            self.assertLessEqual(generation.diversity, 1.0)
            self.assertEqual(
                generation.best.fitness,
                max(item.fitness for item in generation.evaluations),
            )

    def test_generation_loop_is_seeded(self) -> None:
        config = GAExecutionConfig(population_size=6, generations=2, seed=55)

        first = run_ga_execution(config)
        second = run_ga_execution(config)

        self.assertEqual(first.final_best.to_dict(), second.final_best.to_dict())
        self.assertEqual(
            [item.best.fitness for item in first.generations],
            [item.best.fitness for item in second.generations],
        )

    def test_leaderboard_fitness_remains_sorted_after_risk_penalties(self) -> None:
        result = run_ga_execution(GAExecutionConfig(population_size=8, generations=2, seed=88))

        for generation in result.generations:
            scores = [item.fitness for item in generation.evaluations]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_run_ga_execution_accepts_custom_evaluator(self) -> None:
        evaluator = MockBacktestEvaluator(seed=31, trade_count=12)

        result = run_ga_execution(
            GAExecutionConfig(population_size=5, generations=2, seed=31),
            evaluator=evaluator,
        )

        self.assertEqual(len(result.generations), 2)
        self.assertIn("drawdown_penalty", result.final_best.metrics.fitness_components)

    def test_run_ga_execution_with_mock_backtest_evaluator_is_deterministic(self) -> None:
        config = GAExecutionConfig(population_size=5, generations=2, seed=44)

        first = run_ga_execution(config, evaluator=MockBacktestEvaluator(seed=44, trade_count=10))
        second = run_ga_execution(config, evaluator=MockBacktestEvaluator(seed=44, trade_count=10))

        self.assertEqual(first.final_best.to_dict(), second.final_best.to_dict())

    def test_mock_backtest_ga_execution_produces_session_summary_compatible_result(self) -> None:
        result = run_ga_execution(
            GAExecutionConfig(population_size=5, generations=2, seed=52),
            evaluator=MockBacktestEvaluator(seed=52, trade_count=10),
        )

        summary = build_ga_session_summary(result)

        self.assertEqual(summary["schema_version"], "ga-session-summary/v1")
        self.assertIn("fitness_components", summary["leaderboard"][0])
        json.dumps(summary, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
