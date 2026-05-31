"""Tests for the Bollinger Evolver multi-generation orchestrator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.evaluators import FitnessConfig, FitnessResult
from bollinger_evolver.ga import (
    GAOrchestratorConfig,
    GenerationConfig,
    GenerationResult,
    IndividualEvaluation,
    run_ga,
)
from bollinger_evolver.gene_space import load_gene_space, validate_genes
from bollinger_evolver.strategies.indicator_helpers import DEFAULT_GENES


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


def _orchestrator_config(temp_dir: str, **overrides: object) -> GAOrchestratorConfig:
    base = {
        "generations": 3,
        "population_size": 3,
        "run_id": "run-orch-001",
        "seed": 42,
        "run_output_dir": Path(temp_dir) / "runs",
        "generation_output_dir": Path(temp_dir) / "generations",
        "best_output_dir": Path(temp_dir) / "best",
        "elite_count": 1,
        "mutation_rate": 0.2,
        "crossover_rate": 0.8,
        "persist_run_summary": True,
        "persist_final_best": True,
        "mode": "mock",
    }
    base.update(overrides)
    return GAOrchestratorConfig(**base)


def _generation_result(
    generation_index: int,
    candidates: list[dict],
    scores: list[float],
    *,
    success_flags: list[bool] | None = None,
    reason: str | None = None,
) -> GenerationResult:
    flags = success_flags or [True] * len(candidates)
    individuals = [
        IndividualEvaluation(
            index=index,
            candidate_id=f"candidate-{generation_index}-{index}",
            success=flags[index],
            fitness_score=scores[index],
            candidate=candidates[index],
            metrics={"fitness": scores[index]},
            reason=None if flags[index] else "failed",
            artifact_path=None,
        )
        for index in range(len(candidates))
    ]
    successful = [item for item in individuals if item.success]
    return GenerationResult(
        success=bool(successful),
        run_id="run-orch-001",
        generation_index=generation_index,
        population_size=len(candidates),
        evaluated_count=len(candidates),
        success_count=len(successful),
        failure_count=len(candidates) - len(successful),
        best=successful[0] if successful else None,
        individuals=individuals,
        reason=reason or (None if successful else "no_successful_individuals"),
    )


class TestGAOrchestrator(unittest.TestCase):
    def _initial_population(self) -> list[dict]:
        first = dict(DEFAULT_GENES)
        second = dict(DEFAULT_GENES)
        third = dict(DEFAULT_GENES)
        second["bb_period_15m"] = 35
        third["bb_period_15m"] = 50
        return [first, second, third]

    def test_run_ga_runs_multiple_generations_and_tracks_global_best(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            calls: list[int] = []

            def generation_runner(population, fitness_config, generation_config, evaluator=None):
                calls.append(generation_config.generation_index)
                scores_by_generation = {
                    1: [10.0, 8.0, 6.0],
                    2: [12.0, 9.0, 7.0],
                    3: [11.0, 10.0, 5.0],
                }
                candidates = [dict(item) for item in population]
                candidates = sorted(candidates, key=lambda item: item.get("bb_period_15m", 0), reverse=True)
                return _generation_result(
                    generation_config.generation_index,
                    candidates,
                    scores_by_generation[generation_config.generation_index],
                )

            result = run_ga(
                initial_population=self._initial_population(),
                fitness_config=_fitness_config(),
                orchestrator_config=_orchestrator_config(temp_dir),
                generation_runner=generation_runner,
            )

            self.assertTrue(result.success)
            self.assertEqual(calls, [1, 2, 3])
            self.assertEqual(result.best_fitness_score, 12.0)
            self.assertEqual(result.best_generation_index, 2)

    def test_empty_initial_population_returns_reason(self) -> None:
        result = run_ga([], _fitness_config(), _orchestrator_config("C:\\temp"))
        self.assertFalse(result.success)
        self.assertEqual(result.reason, "empty_initial_population")

    def test_invalid_generation_count_returns_reason(self) -> None:
        result = run_ga(
            [{"bb_period_15m": 20}],
            _fitness_config(),
            _orchestrator_config("C:\\temp", generations=0),
        )
        self.assertFalse(result.success)
        self.assertEqual(result.reason, "invalid_generation_count")

    def test_no_successful_generation_stops_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def generation_runner(population, fitness_config, generation_config, evaluator=None):
                if generation_config.generation_index == 1:
                    return _generation_result(1, population, [10.0, 8.0, 6.0])
                return _generation_result(
                    2,
                    population,
                    [-1.0, -2.0, -3.0],
                    success_flags=[False, False, False],
                )

            result = run_ga(
                self._initial_population(),
                _fitness_config(),
                _orchestrator_config(temp_dir),
                generation_runner=generation_runner,
            )

            self.assertFalse(result.success)
            self.assertEqual(result.completed, 2)
            self.assertEqual(result.reason, "no_successful_individuals")

    def test_run_summary_and_final_best_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga(
                self._initial_population(),
                _fitness_config(),
                _orchestrator_config(temp_dir),
                generation_runner=lambda population, *_args, **_kwargs: _generation_result(
                    1 if len(population) == 3 else 2,
                    population,
                    [9.0, 8.0, 7.0],
                ),
            )

            run_summary = json.loads(Path(result.run_summary_path).read_text(encoding="utf-8"))
            final_best = json.loads(Path(result.final_best_path).read_text(encoding="utf-8"))
            self.assertEqual(run_summary["best_fitness_score"], 9.0)
            self.assertEqual(final_best["best_fitness_score"], 9.0)
            self.assertIn("best_genes", run_summary)
            self.assertIn("genes", final_best)
            validate_genes(final_best["genes"], load_gene_space())

    def test_deterministic_seed_yields_same_best_candidate(self) -> None:
        def generation_runner(population, fitness_config, generation_config, evaluator=None):
            scored = sorted(population, key=lambda item: item["bb_period_15m"], reverse=True)
            scores = [float(item["bb_period_15m"]) for item in scored]
            return _generation_result(generation_config.generation_index, scored, scores)

        config = _orchestrator_config("C:\\temp", persist_run_summary=False, persist_final_best=False)
        initial_population = self._initial_population()

        first = run_ga(initial_population, _fitness_config(), config, generation_runner=generation_runner)
        second = run_ga(initial_population, _fitness_config(), config, generation_runner=generation_runner)

        self.assertEqual(first.best_candidate, second.best_candidate)
        self.assertEqual(first.best_fitness_score, second.best_fitness_score)

    def test_persist_run_summary_false_skips_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga(
                self._initial_population(),
                _fitness_config(),
                _orchestrator_config(temp_dir, persist_run_summary=False),
                generation_runner=lambda population, fitness_config, generation_config, evaluator=None: _generation_result(
                    generation_config.generation_index,
                    population,
                    [9.0, 8.0, 7.0],
                ),
            )

        self.assertIsNone(result.run_summary_path)

    def test_persist_final_best_false_skips_final_best(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_ga(
                self._initial_population(),
                _fitness_config(),
                _orchestrator_config(temp_dir, persist_final_best=False),
                generation_runner=lambda population, fitness_config, generation_config, evaluator=None: _generation_result(
                    generation_config.generation_index,
                    population,
                    [9.0, 8.0, 7.0],
                ),
            )

        self.assertIsNone(result.final_best_path)

    def test_artifacts_do_not_include_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [dict(DEFAULT_GENES, api_secret="abc")] * 3
            result = run_ga(
                population,
                _fitness_config(),
                _orchestrator_config(temp_dir),
                generation_runner=lambda population, fitness_config, generation_config, evaluator=None: _generation_result(
                    generation_config.generation_index,
                    population,
                    [9.0, 8.0, 7.0],
                ),
            )
            run_summary_text = Path(result.run_summary_path).read_text(encoding="utf-8")
            final_best_text = Path(result.final_best_path).read_text(encoding="utf-8")

        self.assertNotIn("abc", run_summary_text)
        self.assertNotIn("abc", final_best_text)

    def test_generation_runner_injection_receives_evaluator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            seen = {}

            def evaluator(candidate, fitness_config):
                return FitnessResult(success=True, fitness_score=1.0)

            def generation_runner(population, fitness_config, generation_config, evaluator=None):
                seen["evaluator"] = evaluator
                return _generation_result(generation_config.generation_index, population, [9.0, 8.0, 7.0])

            run_ga(
                self._initial_population(),
                _fitness_config(),
                _orchestrator_config(temp_dir),
                evaluator=evaluator,
                generation_runner=generation_runner,
            )

        self.assertIs(seen["evaluator"], evaluator)


if __name__ == "__main__":
    unittest.main()
