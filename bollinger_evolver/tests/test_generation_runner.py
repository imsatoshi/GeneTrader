"""Tests for Bollinger Evolver generation runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bollinger_evolver.evaluators import FitnessConfig, FitnessResult
from bollinger_evolver.ga import (
    GenerationConfig,
    candidate_id,
    run_generation,
)


def _fitness_config(**overrides: object) -> FitnessConfig:
    base = {
        "strategy": "BollingerResonance_Gen001_Ind001",
        "config_path": "config.json",
        "timerange": "20240101-20240201",
        "timeframe": "15m",
        "pairs": ("BTC/USDT",),
        "result_dir": "results/bollinger_evolver/backtests",
        "timeout_seconds": 120,
        "failed_score": -1_000_000.0,
    }
    base.update(overrides)
    return FitnessConfig(**base)


def _generation_config(temp_dir: str, **overrides: object) -> GenerationConfig:
    base = {
        "generation_index": 1,
        "run_id": "run-test-001",
        "output_dir": Path(temp_dir) / "generations",
        "best_dir": Path(temp_dir) / "best",
        "failed_score": -1_000_000.0,
        "sort_descending": True,
        "persist_individuals": True,
        "persist_best": True,
    }
    base.update(overrides)
    return GenerationConfig(**base)


def _result(score: float, *, success: bool = True, reason: str | None = None) -> FitnessResult:
    return FitnessResult(
        success=success,
        fitness_score=score,
        metrics={"score": score},
        params={"bb_window": 400},
        reason=reason,
        artifact_path=f"artifact-{score}.json",
    )


class TestCandidateId(unittest.TestCase):
    def test_candidate_id_is_deterministic(self) -> None:
        candidate = {"bb_window": 400, "bb_std": 2.0}
        self.assertEqual(candidate_id(candidate), candidate_id(candidate))

    def test_candidate_id_ignores_sensitive_fields(self) -> None:
        first = {"bb_window": 400, "api_secret": "abc"}
        second = {"bb_window": 400, "api_secret": "xyz"}
        self.assertEqual(candidate_id(first), candidate_id(second))

    def test_candidate_id_handles_non_json_serializable_values(self) -> None:
        candidate = {"bb_window": 400, "note": object()}
        self.assertTrue(candidate_id(candidate).startswith("candidate-"))


class TestRunGeneration(unittest.TestCase):
    def test_run_generation_evaluates_population_and_sorts_by_fitness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

            def evaluator(candidate: dict, _: FitnessConfig) -> FitnessResult:
                scores = {"a": 10.0, "b": 30.0, "c": 20.0}
                return _result(scores[candidate["id"]])

            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=evaluator,
            )

        self.assertTrue(result.success)
        self.assertEqual([item.fitness_score for item in result.individuals], [30.0, 20.0, 10.0])
        self.assertEqual(result.best.fitness_score, 30.0)
        self.assertEqual(result.best.index, 1)

    def test_partial_failures_do_not_interrupt_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"id": "a"}, {"id": "b"}, {"id": "c"}]

            def evaluator(candidate: dict, _: FitnessConfig) -> FitnessResult:
                if candidate["id"] == "b":
                    return _result(-1_000_000.0, success=False, reason="runner failed")
                return _result(25.0 if candidate["id"] == "a" else 15.0)

            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=evaluator,
            )

        self.assertTrue(result.success)
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failure_count, 1)
        self.assertEqual(result.best.fitness_score, 25.0)

    def test_evaluator_exception_does_not_interrupt_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"id": "a"}, {"id": "b"}]

            def evaluator(candidate: dict, _: FitnessConfig) -> FitnessResult:
                if candidate["id"] == "b":
                    raise RuntimeError("boom")
                return _result(12.0)

            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=evaluator,
            )

        self.assertTrue(result.success)
        failed = [item for item in result.individuals if not item.success][0]
        self.assertIn("evaluator_exception", failed.reason or "")

    def test_all_failed_results_in_no_successful_individuals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"id": "a"}, {"id": "b"}]

            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=lambda *_: _result(-1_000_000.0, success=False, reason="fail"),
            )

        self.assertFalse(result.success)
        self.assertIsNone(result.best)
        self.assertEqual(result.reason, "no_successful_individuals")
        self.assertIsNone(result.best_path)

    def test_empty_population_returns_empty_population_reason(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation([], _fitness_config(), _generation_config(temp_dir))

        self.assertFalse(result.success)
        self.assertEqual(result.reason, "empty_population")
        self.assertEqual(result.population_size, 0)

    def test_invalid_candidate_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"id": "a"}, ["invalid"], {"id": "b"}]

            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=lambda *_: _result(5.0),
            )

        self.assertEqual(result.failure_count, 1)
        invalid = [item for item in result.individuals if not item.success][0]
        self.assertIn("invalid_candidate", invalid.reason or "")

    def test_mapping_fitness_result_is_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"id": "a"}]

            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=lambda *_: {
                    "success": True,
                    "fitness_score": 7.5,
                    "metrics": {"profit": 1},
                    "reason": None,
                    "artifact_path": "artifact.json",
                },
            )

        self.assertTrue(result.success)
        self.assertEqual(result.best.fitness_score, 7.5)

    def test_invalid_evaluator_return_type_becomes_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [{"id": "a"}],
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=lambda *_: "bad",
            )

        self.assertFalse(result.best.success if result.best else False)
        self.assertEqual(result.failure_count, 1)

    def test_run_id_is_generated_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [{"id": "a"}],
                _fitness_config(),
                _generation_config(temp_dir, run_id=None),
                evaluator=lambda *_: _result(9.0),
            )

        self.assertTrue(result.run_id.startswith("run-"))

    def test_persist_best_false_skips_best_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [{"id": "a"}],
                _fitness_config(),
                _generation_config(temp_dir, persist_best=False),
                evaluator=lambda *_: _result(9.0),
            )

        self.assertIsNone(result.best_path)

    def test_persist_individuals_false_omits_individuals_from_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [{"id": "a"}],
                _fitness_config(),
                _generation_config(temp_dir, persist_individuals=False),
                evaluator=lambda *_: _result(9.0),
            )
            summary = json.loads(Path(result.summary_path).read_text(encoding="utf-8"))

        self.assertEqual(summary["individuals"], [])

    def test_summary_and_best_artifacts_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [{"id": "a"}],
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=lambda *_: _result(11.0),
            )

            summary_path = Path(result.summary_path)
            best_path = Path(result.best_path)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            best = json.loads(best_path.read_text(encoding="utf-8"))
            self.assertTrue(summary_path.exists())
            self.assertTrue(best_path.exists())
            self.assertEqual(summary["best_fitness_score"], 11.0)
            self.assertEqual(best["fitness_score"], 11.0)

    def test_summary_and_best_do_not_contain_sensitive_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"bb_window": 400, "api_secret": "abc", "token": "123"}]
            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=lambda *_: _result(13.0),
            )
            summary_text = Path(result.summary_path).read_text(encoding="utf-8")
            best_text = Path(result.best_path).read_text(encoding="utf-8")

        self.assertNotIn("abc", summary_text)
        self.assertNotIn("123", summary_text)
        self.assertNotIn("abc", best_text)
        self.assertNotIn("123", best_text)

    def test_generation_filename_contains_zero_padded_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_generation(
                [{"id": "a"}],
                _fitness_config(),
                _generation_config(temp_dir, generation_index=7),
                evaluator=lambda *_: _result(8.0),
            )

        self.assertIn("generation-000007-", Path(result.summary_path).name)

    def test_candidate_id_in_artifacts_ignores_sensitive_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            population = [{"bb_window": 400, "api_secret": "abc"}]
            result = run_generation(
                population,
                _fitness_config(),
                _generation_config(temp_dir),
                evaluator=lambda *_: _result(9.0),
            )
            summary = json.loads(Path(result.summary_path).read_text(encoding="utf-8"))

        self.assertEqual(
            summary["best_candidate_id"],
            candidate_id({"bb_window": 400, "api_secret": "different"}),
        )


if __name__ == "__main__":
    unittest.main()
