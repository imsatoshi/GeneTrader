"""Tests for GA session summary generation."""

from __future__ import annotations

import json
import unittest

from bollinger_evolver.ga_execution import GAExecutionConfig, run_ga_execution
from bollinger_evolver.session_summary import build_ga_session_summary, to_jsonable_ga_session_summary


def _execution_result():
    return run_ga_execution(GAExecutionConfig(population_size=8, generations=3, seed=2026))


class TestGASessionSummary(unittest.TestCase):
    def test_build_ga_session_summary_has_required_top_level_fields(self) -> None:
        summary = build_ga_session_summary(_execution_result(), run_id="mock-run-001")

        self.assertEqual(summary["schema_version"], "ga-session-summary/v1")
        self.assertEqual(summary["source"], "mock-ga-execution")
        self.assertEqual(summary["run_id"], "mock-run-001")
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["generation"], 3)
        self.assertEqual(summary["population_size"], 8)
        self.assertIn("best_fitness", summary)
        self.assertIn("average_fitness", summary)
        self.assertIn("diversity", summary)
        self.assertIn("best_genome", summary)
        self.assertIn("fitness_series", summary)
        self.assertIn("leaderboard", summary)

    def test_build_ga_session_summary_is_json_serializable(self) -> None:
        summary = build_ga_session_summary(_execution_result())

        encoded = json.dumps(summary, sort_keys=True)

        self.assertIn("ga-session-summary/v1", encoded)

    def test_leaderboard_is_sorted_by_fitness_desc(self) -> None:
        summary = build_ga_session_summary(_execution_result())
        scores = [item["fitness"] for item in summary["leaderboard"]]

        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_leaderboard_rank_starts_at_one(self) -> None:
        summary = build_ga_session_summary(_execution_result())

        self.assertEqual(summary["leaderboard"][0]["rank"], 1)
        self.assertEqual(
            [item["rank"] for item in summary["leaderboard"]],
            list(range(1, len(summary["leaderboard"]) + 1)),
        )

    def test_top_n_limits_leaderboard(self) -> None:
        summary = build_ga_session_summary(_execution_result(), top_n=3)

        self.assertEqual(len(summary["leaderboard"]), 3)

    def test_best_genome_matches_top_leaderboard_entry(self) -> None:
        summary = build_ga_session_summary(_execution_result())

        self.assertEqual(summary["best_genome"], summary["leaderboard"][0]["genome"])
        self.assertEqual(summary["best_fitness"], summary["leaderboard"][0]["fitness"])

    def test_fitness_series_contains_generation_metrics(self) -> None:
        summary = build_ga_session_summary(_execution_result())

        self.assertEqual(len(summary["fitness_series"]), 3)
        self.assertEqual(
            set(summary["fitness_series"][0]),
            {"generation", "best_fitness", "average_fitness", "diversity"},
        )

    def test_summary_works_with_run_ga_execution_result(self) -> None:
        result = _execution_result()
        summary = build_ga_session_summary(result)

        self.assertEqual(summary["generation"], result.generations[-1].generation)
        self.assertEqual(summary["average_fitness"], result.generations[-1].average_fitness)

    def test_to_jsonable_converts_non_json_objects(self) -> None:
        summary = to_jsonable_ga_session_summary({"value": object()})

        json.dumps(summary)
        self.assertIsInstance(summary["value"], str)


if __name__ == "__main__":
    unittest.main()
