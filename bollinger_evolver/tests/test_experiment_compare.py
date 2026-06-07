"""Tests for mock experiment comparison engine."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.experiment_compare import compare_experiment_summaries


def _summary(**overrides):
    data = {
        "run_id": "run-a",
        "best_fitness": 0.50,
        "max_drawdown": 0.12,
        "stability_score": 0.80,
        "notes": "mock",
    }
    data.update(overrides)
    return data


class TestExperimentCompare(unittest.TestCase):
    def test_experiment_compare_selects_best_by_fitness(self) -> None:
        result = compare_experiment_summaries(
            [
                _summary(run_id="run-a", best_fitness=0.4),
                _summary(run_id="run-b", best_fitness=0.9),
            ]
        )

        self.assertEqual(result["best_by_fitness"]["run_id"], "run-b")
        self.assertEqual(result["run_count"], 2)

    def test_experiment_compare_selects_best_by_drawdown(self) -> None:
        result = compare_experiment_summaries(
            [
                _summary(run_id="run-a", max_drawdown=0.20),
                _summary(run_id="run-b", max_drawdown=0.07),
            ]
        )

        self.assertEqual(result["best_by_drawdown"]["run_id"], "run-b")

    def test_experiment_compare_selects_best_by_stability(self) -> None:
        result = compare_experiment_summaries(
            [
                _summary(run_id="run-a", stability_score=0.70),
                _summary(run_id="run-b", stability_score=0.95),
            ]
        )

        self.assertEqual(result["best_by_stability"]["run_id"], "run-b")

    def test_experiment_compare_ranked_order_is_stable(self) -> None:
        result = compare_experiment_summaries(
            [
                _summary(run_id="run-a", best_fitness=0.8, max_drawdown=0.10),
                _summary(run_id="run-b", best_fitness=0.8, max_drawdown=0.10),
            ]
        )

        self.assertEqual([item["run_id"] for item in result["ranked"]], ["run-a", "run-b"])
        self.assertEqual([item["rank"] for item in result["ranked"]], [1, 2])

    def test_experiment_compare_output_is_json_serializable(self) -> None:
        result = compare_experiment_summaries([_summary()])

        encoded = json.dumps(result, sort_keys=True)
        self.assertIn("experiment-comparison/v1", encoded)

    def test_experiment_compare_missing_field_fails_clearly(self) -> None:
        summary = _summary()
        summary.pop("max_drawdown")

        with self.assertRaisesRegex(ValueError, "experiment_summary_missing_field:max_drawdown"):
            compare_experiment_summaries([summary])


if __name__ == "__main__":
    unittest.main()
